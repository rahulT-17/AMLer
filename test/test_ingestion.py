from policy_extraction import extract_rules_from_clauses
from policy_ingestion_service import extract_pdf_pages, build_policy_clauses

pdf_path = r"C:\Users\rahul\Documents\AMLer\documentation\sample_policy_edge_cases.pdf"

pages = extract_pdf_pages(pdf_path)
clauses = build_policy_clauses(pdf_path, pages)
rules = extract_rules_from_clauses(clauses)

print(f"pages: {len(pages)}")
print(f"clauses: {len(clauses)}")
print(f"rules: {len(rules)}")

print("\nExtracted Rules:")
for rule in rules:
    print(rule)
