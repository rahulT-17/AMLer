"""Extraction pipeline orchestration.

This module coordinates all active clause-to-rule extractors. As more rule
families are added, this file becomes the place that decides which extractor
is tried and in what order.
"""

from models.policy_ingestion import ExtractedPolicyRule, PolicyClause

from .threshold import extract_threshold_rule
from .format import extract_format_rule

from .llm import extract_rule_with_llm

def extract_rules_from_clauses(
    clauses: list[PolicyClause],
) -> list[ExtractedPolicyRule]:
    """Run LLM-first extraction, then fall back to heuristics."""

    extracted_rules: list[ExtractedPolicyRule] = []

    for clause in clauses:
        llm_rule = extract_rule_with_llm(clause)
        if llm_rule is not None:
            extracted_rules.append(llm_rule)
            continue

        threshold_rule = extract_threshold_rule(clause)
        if threshold_rule is not None:
            extracted_rules.append(threshold_rule)
            continue

        format_rule = extract_format_rule(clause)
        if format_rule is not None:
            extracted_rules.append(format_rule)

    return extracted_rules