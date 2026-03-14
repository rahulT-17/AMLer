# main.py / entry point for the AMLer application

import asyncio
from sqlalchemy import select
from llm_layer import analyze_with_llm
from db import AsyncSessionLocal
from policy_rules_model import PolicyRule, ThresholdRule, FormatRule, FrequencyRule, ChainRule
from transaction_loader import load_transactions
from compliance.compliance_runner import run_compliance
from collections import Counter
from typology import group_alerts_by_account


async def main():
    # STEP 1 — load transactions
    transactions = load_transactions(sample=5000)
    print(f"Loaded: {len(transactions)} transactions")

    async with AsyncSessionLocal() as session:
        # STEP 2 — load rules
        result = await session.execute(select(PolicyRule))
        rules = result.scalars().all()
        loaded_rules = []
        for rule in rules:
            await session.refresh(rule)
            loaded_rules.append(rule)

        # STEP 3 — run compliance
        alerts = await run_compliance(loaded_rules, transactions)
        print(f"Alerts with transaction: {sum(1 for a in alerts if a.get('transaction'))}")
        print(f"Alerts without transaction: {sum(1 for a in alerts if not a.get('transaction'))}")
        print(f"Total alerts: {len(alerts)}")

    # STEP 4 — group by account + detect typology
    grouped = group_alerts_by_account(alerts)

    account_counts = Counter(
    a['transaction']['account'] 
    for a in alerts 
    if a.get('transaction')
)
    print("Top 10 accounts by alert count:")
    for acc, count in account_counts.most_common(10):
        print(f"  {acc}: {count} alerts")

    print(f"Suspicious accounts: {len(grouped)}")
    print("=" * 50)
    print(f"Suspicious accounts: {len(grouped)}")

    for account, result in list(grouped.items())[:5]:
        print(f"Account: {account}")
        print(f"Typology: {result.typology}")
        print(f"Rules fired: {result.rule_names_fired}")
        print(f"Total flagged: ${result.total_amount_flagged:,.2f}")
        typologies = Counter(r.typology for r in grouped.values())
        print(f"Typology breakdown: {dict(typologies)}")
        print("-" * 30)

    # step 5 — send to LLM for analysis
    # test on highest priority account — SMURFING
    print("\nRunning LLM analysis on high priority accounts...")
    for account, result in grouped.items():
        if result.typology in ["SMURFING", "LAYERING"]:
            analysis = await analyze_with_llm(result)
            result.llm_analysis = analysis['reasoning']
            result.recommendation = analysis['recommendation']
            result.risk_level = analysis['risk_level']
            
            print(f"\nAccount: {result.account}")
            print(f"Typology: {result.typology}")
            print(f"Risk: {result.risk_level}")
            print(f"Reasoning: {result.llm_analysis}")
            print(f"Recommendation: {result.recommendation}")
            print("-" * 50)
if __name__ == "__main__":
    asyncio.run(main())