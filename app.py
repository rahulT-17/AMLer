# app.py / entry point for the AMLer application

from fastapi import FastAPI
from sqlalchemy import select
from db import AsyncSessionLocal
from policy_rules_model import PolicyRule
from transaction_loader import load_transactions
from compliance.compliance_runner import run_compliance

app = FastAPI(title="AML Detection Engine")

@app.post("/run_compliance")
async def run_compliance_endpoint(sample: int= 1000):
    # STEP 1 — load transactions
    transactions = load_transactions(sample=sample)
    
    async with AsyncSessionLocal() as session:
        # STEP 2 — load rules from DB
        result = await session.execute(select(PolicyRule))
        rules = result.scalars().all()

        for rule in rules:
            await session.refresh(rule)  # ensure all attributes are loaded before session closes
    
    # STEP 3 — run compliance
    alerts = await run_compliance(rules, transactions)

    flagged = [a['transaction'] for a in alerts if 'transaction' in a]
    true_positives = len([t for t in flagged if t['is_laundering'] == 1])
    false_positives = len([t for t in flagged if t['is_laundering'] == 0])
    total = len(flagged)

    precision = true_positives / total if total > 0 else 0
    
    return {
        "total_alerts": len(alerts),
        "true_positives": true_positives,
        "false_positives": false_positives,
        "precision": round(precision, 3),
        "alerts": alerts
    }
