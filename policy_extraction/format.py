"""Format-rule extraction logic.

This module owns format-style clauses such as
"non-standard ACH payment descriptions should be flagged".
"""

from models.policy_ingestion import (
    ExtractedPolicyRule,
    PolicyClause,
    PolicyRuleLifecycle,
)


def extract_format_rule(clause: PolicyClause) -> ExtractedPolicyRule | None:
    """Convert one format-like clause into a draft rule."""

    text = clause.text.lower()

    # Require language that actually describes a value format or structure.
    strong_format_phrases = [
        "format",
        "payment descriptions",
        "payment description",
        "non-standard",
        "must match",
        "should match",
        "expected format",
        "payment type",
        "standard",
        "description",
        "pattern",
    ]

    if not any(phrase in text for phrase in strong_format_phrases):
        return None

    field_target = "payment_currency"
    pattern = None

    # Keep the first v1 mapping narrow and explicit.
    if "ach" in text:
        pattern = r"ACH$"

    if pattern is None:
        return None

    severity = (
        "HIGH"
        if any(word in text for word in ["must", "shall", "required", "flagged"])
        else "MEDIUM"
    )

    rule_name = f"format_{field_target}_{pattern.replace('$', 'end').replace('\\', '')}"

    return ExtractedPolicyRule(
        name=rule_name,
        rule_type="FORMAT",
        source_text=clause.text,
        source_document=clause.source_document,
        page_number=clause.page_number,
        section_heading=clause.section_heading,
        severity=severity,
        status=PolicyRuleLifecycle.DRAFT,
        field_target=field_target,
        pattern=pattern,
        metadata={"matched_family": "ach_format"},
    )
