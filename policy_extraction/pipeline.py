"""Extraction pipeline orchestration.

This module coordinates all active clause-to-rule extractors. As more rule
families are added, this file becomes the place that decides which extractor
is tried and in what order.
"""

from models.policy_ingestion import ExtractedPolicyRule, PolicyClause

from .threshold import extract_threshold_rule
from .format import extract_format_rule


def extract_rules_from_clauses(clauses: list[PolicyClause],) -> list[ExtractedPolicyRule]:
    
    """Run the available extractors across a list of PolicyClause objects."""

    extracted_rules: list[ExtractedPolicyRule] = []

    for clause in clauses:
        # For v1 we only have threshold extraction. Later this loop can try
        # format, frequency, and chain extractors too.
        threshold_rule = extract_threshold_rule(clause)

        if threshold_rule is not None:
            extracted_rules.append(threshold_rule)

        format_rule = extract_format_rule(clause)
        if format_rule is not None:
            extracted_rules.append(format_rule)

    return extracted_rules
