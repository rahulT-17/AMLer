# app.py — AML Compliance Agent API

import asyncio
from fastapi import FastAPI

from sqlalchemy import select
from db import AsyncSessionLocal

from policy_rules_model import PolicyRule

from evaluate import evaluate 
from transaction_loader import load_transactions
from compliance.compliance_runner import run_compliance
from typology import group_alerts_by_account
from llm_layer import analyze_with_llm
from collections import Counter
from evaluate import evaluate as run_evaluate

app = FastAPI(title="AML Compliance Agent")

@app.post("/analyze")
async def analyze(sample: int = 1000):
    
    # STEP 1 — load transactions
    transactions = load_transactions(sample=sample)

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

    # STEP 4 — group by account + typology
    grouped = group_alerts_by_account(alerts)

    # STEP 5 — LLM analysis on high priority only
    high_priority = []
    for account, result in grouped.items():
        if result.typology in ["SMURFING", "LAYERING"]:
            analysis = await analyze_with_llm(result)
            result.llm_analysis = analysis['reasoning']
            result.recommendation = analysis['recommendation']
            result.risk_level = analysis['risk_level']
            high_priority.append({
                "account": result.account,
                "typology": result.typology,
                "risk_level": result.risk_level,
                "rules_fired": result.rule_names_fired,
                "total_flagged": result.total_amount_flagged,
                "reasoning": result.llm_analysis,
                "recommendation": result.recommendation
            })

    # STEP 6 — build all accounts list
    all_accounts = [
        {
            "account": r.account,
            "typology": r.typology,
            "rules_fired": r.rule_names_fired,
            "total_flagged": r.total_amount_flagged,
            "alert_count": len(r.alerts)
        }
        for r in grouped.values()
    ]

    # STEP 7 — return summary
    typology_breakdown = dict(Counter(
        r.typology for r in grouped.values()
    ))

    return {
        "total_suspicious_accounts": len(grouped),
        "typology_breakdown": typology_breakdown,
        "high_priority_accounts": high_priority,
        "all_accounts": all_accounts,
        "total_alerts": len(alerts)
    }

@app.get("/evaluate") 
async def evaluate_endpoint() :
    return await run_evaluate()