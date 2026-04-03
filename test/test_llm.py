from models.policy_ingestion import PolicyClause
from policy_extraction import extract_rules_from_clauses
from policy_extraction.llm import extract_rule_with_llm
from policy_ingestion_service import extract_pdf_pages, build_policy_clauses


def print_section(title: str) -> None:
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def test_single_clause(clause: PolicyClause) -> None:
    print_section(f"Single Clause Test: {clause.clause_id}")
    print(f"text: {clause.text}")
    rule = extract_rule_with_llm(clause)
    print("result:")
    print(rule)


def test_full_pdf(pdf_path: str) -> None:
    print_section(f"Full PDF Test: {pdf_path}")

    pages = extract_pdf_pages(pdf_path)
    clauses = build_policy_clauses(pdf_path, pages)
    rules = extract_rules_from_clauses(clauses)

    print(f"pages: {len(pages)}")
    print(f"clauses: {len(clauses)}")
    print(f"rules: {len(rules)}")

    print("\nExtracted Rules:")
    for rule in rules:
        print(rule)


if __name__ == "__main__":
    threshold_clause = PolicyClause(
        clause_id="threshold_1",
        text="Transactions above $10,000 must be flagged for review.",
        source_document="sample_policy.pdf",
        page_number=1,
        section_heading="Reporting Thresholds",
    )

    format_clause = PolicyClause(
        clause_id="format_1",
        text="ACH payment descriptions must match the expected ACH format.",
        source_document="sample_policy.pdf",
        page_number=1,
        section_heading="ACH Monitoring",
    )

    non_rule_clause = PolicyClause(
        clause_id="heading_1",
        text="Reporting Thresholds",
        source_document="sample_policy.pdf",
        page_number=1,
        section_heading=None,
    )

    test_single_clause(threshold_clause)
    test_single_clause(format_clause)
    test_single_clause(non_rule_clause)

    test_full_pdf(r"C:\Users\rahul\Documents\AMLer\documentation\sample_policy.pdf")
    test_full_pdf(r"C:\Users\rahul\Documents\AMLer\documentation\sample_policy_edge_cases.pdf")
