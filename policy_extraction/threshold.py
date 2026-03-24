"""Threshold-rule extraction logic.

This module owns one rule family only: threshold-style clauses such as
"transactions above $10,000 must be flagged". Keeping one rule family per
file makes the extraction side mirror the evaluator side of the system.
"""

import re

from models.policy_ingestion import (
    ExtractedPolicyRule,
    PolicyClause,
    PolicyRuleLifecycle,
)


def extract_threshold_rule(clause: PolicyClause) -> ExtractedPolicyRule | None:
    """Convert one threshold-like PolicyClause into a draft rule.

    Returns `None` when the clause does not clearly describe a threshold rule.
    This keeps the extractor selective instead of forcing every clause into a
    rule shape.
    """
    text = clause.text.lower()

    # Map common policy language to the operator vocabulary already used by
    # the existing threshold evaluator.
    phrase_to_operator = {
        "greater than or equal to": ">=",
        "less than or equal to": "<=",
        "at least": ">=",
        "at most": "<=",
        "greater than": ">",
        "less than": "<",
        "above": ">",
        "over": ">",
        "below": "<",
        "under": "<",
    }

    operator = None
    matched_phrase = None

    for phrase, mapped_operator in phrase_to_operator.items():
        if phrase in text:
            operator = mapped_operator
            matched_phrase = phrase
            break

    # If no threshold phrase is present, this clause does not belong to the
    # threshold extractor.
    if operator is None:
        return None

    # Extract the numeric amount from policy text such as "$10,000".
    amount_match = re.search(r"\$?\s*([\d,]+(?:\.\d+)?)", clause.text)
    if not amount_match:
        return None

    raw_amount = amount_match.group(1)
    # Store a clean numeric string because the runtime evaluator later casts
    # threshold_value to float.
    threshold_value = raw_amount.replace(",", "")

    severity = (
        "HIGH"
        if any(word in text for word in ["must", "shall", "required"])
        else "MEDIUM"
    )

    operator_slug = {
        ">": "gt",
        "<": "lt",
        ">=": "gte",
        "<=": "lte",
        "==": "eq",
        "!=": "neq",
    }[operator]

    # Deterministic names make extracted rules easier to inspect and compare.
    rule_name = f"threshold_amount_paid_{operator_slug}_{threshold_value}"

    return ExtractedPolicyRule(
        name=rule_name,
        rule_type="THRESHOLD",
        source_text=clause.text,
        source_document=clause.source_document,
        page_number=clause.page_number,
        section_heading=clause.section_heading,
        severity=severity,
        status=PolicyRuleLifecycle.DRAFT,
        field_target="amount_paid",
        operator=operator,
        threshold_value=threshold_value,
        metadata={"matched_phrase": matched_phrase},
    )
