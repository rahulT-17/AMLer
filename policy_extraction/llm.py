"""LLM-first policy rule extraction.

This module uses the LLM only for *candidate rule generation*.
The model decides whether a clause is an executable rule and, if so,
returns structured JSON that we validate before turning it into an
ExtractedPolicyRule.

Important design choice:
- the LLM may suggest candidate rules
- Python still owns schema validation and safety checks
- invalid LLM output is rejected so the runtime pipeline stays predictable
"""

import json
from typing import Any

import httpx

from models.policy_ingestion import (
    ExtractedPolicyRule,
    PolicyClause,
    PolicyRuleLifecycle,
)
from settings import settings

ALLOWED_RULE_TYPES = {"THRESHOLD", "FORMAT", "FREQUENCY", "CHAIN"}
ALLOWED_SEVERITIES = {"LOW", "MEDIUM", "HIGH"}
ALLOWED_OPERATORS = {">", "<", ">=", "<=", "==", "!="}

# These are the execution-friendly field names the current rule engine already
# understands. Restricting the LLM to this small vocabulary keeps extraction
# aligned with the existing evaluators instead of inventing new fields.
ALLOWED_FIELD_TARGETS = {
    "THRESHOLD": {"amount_paid"},
    "FORMAT": {"payment_currency"},
}

ALLOWED_GROUP_BY_FIELDS = {"account"}

SYSTEM_PROMPT = """You are a compliance policy rule extraction engine.

You will be given exactly one policy clause from an AML policy document.

Your task:
1. Decide whether the clause is an executable compliance rule.
2. If it is executable, classify it into exactly one supported rule type:
   - THRESHOLD
   - FORMAT
   - FREQUENCY
   - CHAIN
3. Extract only the fields needed for that rule type.
4. Return ONLY valid JSON. No markdown, no code fences, no explanation outside JSON.

Rules:
- If the clause is only a heading, background text, or vague guidance, return:
  {"is_rule": false, "reasoning": "..."}
- Do not invent unsupported rule types.
- Do not invent fields outside the schema.
- Use null for fields that do not apply.
- Prefer precision over recall: if unsure, return is_rule=false.
- Use only these execution-friendly field names:
  - THRESHOLD.field_target -> amount_paid
  - FORMAT.field_target -> payment_currency
  - FREQUENCY.group_by_field -> account
- If the clause mentions ACH format or ACH descriptions, use:
  - rule_type = FORMAT
  - field_target = payment_currency
  - pattern = ACH$
- Do not invent fields like payment_description or natural-language patterns
  like "expected ACH format". Return machine-usable values only.

Return JSON in exactly this shape:
{
  "is_rule": true,
  "rule_type": "THRESHOLD|FORMAT|FREQUENCY|CHAIN",
  "name": "string",
  "severity": "LOW|MEDIUM|HIGH",
  "field_target": "string|null",
  "operator": ">|<|>=|<=|==|!=|null",
  "threshold_value": "string|null",
  "pattern": "string|null",
  "group_by_field": "string|null",
  "min_count": "integer|null",
  "time_window_hours": "integer|null",
  "min_hops": "integer|null",
  "max_hops": "integer|null",
  "detect_cycles": "boolean|null",
  "reasoning": "short explanation"
}

If the clause is not an executable rule, return:
{
  "is_rule": false,
  "reasoning": "short explanation"
}
"""


def _clean_json_response(raw_text: str) -> dict[str, Any]:
    """Extract the JSON body even if the model adds fences or extra text."""
    clean = raw_text.strip()

    if clean.startswith("```"):
        clean = clean.replace("```json", "").replace("```", "").strip()

    start = clean.find("{")
    end = clean.rfind("}")
    if start != -1 and end != -1 and end > start:
        clean = clean[start:end + 1]

    return json.loads(clean)


def _required_fields_present(payload: dict[str, Any]) -> bool:
    """Check that each rule type includes the minimum executable fields."""
    rule_type = payload.get("rule_type")

    required_by_type = {
        "THRESHOLD": ["field_target", "operator", "threshold_value"],
        "FORMAT": ["field_target", "pattern"],
        "FREQUENCY": ["group_by_field", "min_count"],
        "CHAIN": ["min_hops", "max_hops", "detect_cycles"],
    }

    required_fields = required_by_type.get(rule_type)
    if required_fields is None:
        return False

    for field in required_fields:
        if payload.get(field) is None:
            return False

    return True


def _normalize_payload(clause: PolicyClause, payload: dict[str, Any]) -> dict[str, Any]:
    """Coerce common LLM variations back into our supported schema.

    The LLM is allowed to be semantically helpful, but the rule engine is not.
    This function narrows slightly-imperfect LLM output back to the vocabulary
    the current evaluators already understand.
    """
    rule_type = payload.get("rule_type")
    text = clause.text.lower()

    if isinstance(payload.get("severity"), str):
        payload["severity"] = payload["severity"].upper()

    if isinstance(payload.get("operator"), str):
        payload["operator"] = payload["operator"].strip()

    if rule_type == "THRESHOLD":
        # Threshold rules in the current engine compare transaction amounts, so
        # we normalize the target field to the existing evaluator field name.
        payload["field_target"] = "amount_paid"

        if payload.get("threshold_value") is not None:
            payload["threshold_value"] = str(payload["threshold_value"]).replace(",", "")

    if rule_type == "FORMAT":
        # The current format evaluator only has a useful first-class mapping for
        # ACH-like payment currency checks, so we keep this scope intentionally
        # narrow for now.
        payload["field_target"] = "payment_currency"

        if "ach" in text:
            payload["pattern"] = r"ACH$"

    if rule_type == "FREQUENCY":
        payload["group_by_field"] = "account"

        if payload.get("min_count") is not None:
            try:
                payload["min_count"] = int(payload["min_count"])
            except (TypeError, ValueError):
                payload["min_count"] = None

        if payload.get("time_window_hours") is not None:
            try:
                payload["time_window_hours"] = int(payload["time_window_hours"])
            except (TypeError, ValueError):
                payload["time_window_hours"] = None

    if rule_type == "CHAIN":
        for field in ["min_hops", "max_hops"]:
            if payload.get(field) is not None:
                try:
                    payload[field] = int(payload[field])
                except (TypeError, ValueError):
                    payload[field] = None

    if not payload.get("name") and rule_type == "THRESHOLD":
        operator_slug = {
            ">": "gt",
            "<": "lt",
            ">=": "gte",
            "<=": "lte",
            "==": "eq",
            "!=": "neq",
        }.get(payload.get("operator"), "rule")
        threshold_value = payload.get("threshold_value") or "unknown"
        payload["name"] = f"threshold_amount_paid_{operator_slug}_{threshold_value}"

    if not payload.get("name") and rule_type == "FORMAT":
        payload["name"] = "format_payment_currency_ach"

    return payload


def _validate_payload(payload: dict[str, Any]) -> bool:
    """Reject LLM output that does not fit the current execution schema."""
    if payload.get("is_rule") is not True:
        return False

    rule_type = payload.get("rule_type")
    if rule_type not in ALLOWED_RULE_TYPES:
        return False

    severity = payload.get("severity")
    if severity not in ALLOWED_SEVERITIES:
        return False

    operator = payload.get("operator")
    if rule_type == "THRESHOLD" and operator not in ALLOWED_OPERATORS:
        return False

    if not _required_fields_present(payload):
        return False

    if rule_type in ALLOWED_FIELD_TARGETS:
        if payload.get("field_target") not in ALLOWED_FIELD_TARGETS[rule_type]:
            return False

    if rule_type == "FORMAT":
        if payload.get("pattern") != r"ACH$":
            return False

    if rule_type == "FREQUENCY":
        if payload.get("group_by_field") not in ALLOWED_GROUP_BY_FIELDS:
            return False

    if not payload.get("name"):
        return False

    return True


def _build_rule_from_payload(
    clause: PolicyClause, payload: dict[str, Any]
) -> ExtractedPolicyRule:
    """Map validated JSON into the shared ingestion dataclass."""
    return ExtractedPolicyRule(
        name=payload["name"],
        rule_type=payload["rule_type"],
        source_text=clause.text,
        source_document=clause.source_document,
        severity=payload["severity"],
        status=PolicyRuleLifecycle.DRAFT,
        page_number=clause.page_number,
        section_heading=clause.section_heading,
        field_target=payload.get("field_target"),
        operator=payload.get("operator"),
        threshold_value=payload.get("threshold_value"),
        pattern=payload.get("pattern"),
        group_by_field=payload.get("group_by_field"),
        min_count=payload.get("min_count"),
        time_window_hours=payload.get("time_window_hours"),
        min_hops=payload.get("min_hops"),
        max_hops=payload.get("max_hops"),
        detect_cycles=payload.get("detect_cycles"),
        metadata={"llm_reasoning": payload.get("reasoning")},
    )


def extract_rule_with_llm(clause: PolicyClause) -> ExtractedPolicyRule | None:
    """Use the LLM to classify one clause and return a draft extracted rule.

    Returning `None` is a normal outcome here:
    - the clause may not be a rule
    - the LLM output may fail validation
    - the heuristic fallback can still try afterwards
    """

    user_prompt = f"""
Policy Clause:
"{clause.text}"

Source Document: {clause.source_document}
Page Number: {clause.page_number}
Section Heading: {clause.section_heading or "None"}

Extract the clause as JSON.
"""

    messages = [
        {
            "role": "user",
            "content": f"{SYSTEM_PROMPT}\n\n{user_prompt}",
        }
    ]

    try:
        with httpx.Client(timeout=settings.llm_timeout_seconds) as client:
            response = client.post(
                settings.llm_base_url,
                json={
                    "model": settings.llm_model,
                    "messages": messages,
                    "max_tokens": 250,
                    "temperature": 0.1,
                },
            )

        data = response.json()
        raw_text = data["choices"][0]["message"]["content"]
        payload = _clean_json_response(raw_text)
        payload = _normalize_payload(clause, payload)

        if payload.get("is_rule") is not True:
            return None

        if not _validate_payload(payload):
            return None

        return _build_rule_from_payload(clause, payload)

    except Exception as exc:
        print(f"LLM extraction failed for clause {clause.clause_id}: {exc}")
        return None
