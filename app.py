# app.py : AML Compliance Agent API

import asyncio
from collections import Counter, defaultdict

from fastapi import FastAPI
from sqlalchemy import select
from pydantic import BaseModel

from typing import Any
from compliance.compliance_runner import run_compliance
from core.db import AsyncSessionLocal
from evaluate import evaluate
from evaluate import evaluate as run_evaluate
from llm_layer import analyze_with_llm
from ml_layer import enrich_grouped_with_ml
from policy_rules_model import PolicyRule
from transaction_loader import load_transactions
from typology import group_alerts_by_account

app = FastAPI(title="AML Compliance Agent")


@app.post("/analyze")
async def analyze(sample: int = 1000, include_llm: bool = False):

    # STEP 1 : load transactions
    transactions = load_transactions(sample=sample)

    async with AsyncSessionLocal() as session:

        # STEP 2 : load rules
        result = await session.execute(select(PolicyRule))
        rules = result.scalars().all()
        loaded_rules = []
        for rule in rules:
            await session.refresh(rule)
            loaded_rules.append(rule)

        # STEP 3 : run compliance
        alerts = await run_compliance(loaded_rules, transactions)

    # STEP 4 : group by account + typology
    grouped = group_alerts_by_account(alerts)
    grouped = enrich_grouped_with_ml(grouped)

    """STEP 5 : for maintaining latency and ensure the separation of concerns,
    im not sending llm analysis to /analyze endpoint response,
    but instead will keep it in a separate list that can be used for a /prioritize endpoint or similar in the future. 
    This way we can run LLM analysis asynchronously and not block the main analysis flow."""

    high_priority = []

    if include_llm:
        llm_candidates = [
        result
        for result in grouped.values()
        if result.typology in ["SMURFING", "LAYERING"]
    ]

        llm_candidates.sort(
            key=lambda r: (
                r.ml_anomaly_score if r.ml_anomaly_score is not None else 0.0,
                r.total_amount_flagged,
            ),
            reverse=True,
        )

        llm_candidates = llm_candidates[:5]

        for result in llm_candidates:
            analysis = await analyze_with_llm(result)
            result.llm_analysis = analysis["reasoning"]
            result.recommendation = analysis["recommendation"]
            result.risk_level = analysis["risk_level"]
            high_priority.append({
                "account": result.account,
                "typology": result.typology,
                "risk_level": result.risk_level,
                "rules_fired": result.rule_names_fired,
                "total_flagged": result.total_amount_flagged,
                "reasoning": result.llm_analysis,
                "recommendation": result.recommendation,
                "ml_anomaly_score": result.ml_anomaly_score,
                "ml_priority": result.ml_priority,
                "ml_reason_signals": result.ml_reason_signals,
            })

    sorted_results = sorted(
        grouped.values(),
        key=lambda r: (
            r.ml_anomaly_score if r.ml_anomaly_score is not None else 0.0,
            r.total_amount_flagged,
        ),
        reverse=True,
    )
    # STEP 6 : build all accounts list
    all_accounts = [
        {
            "account": r.account,
            "typology": r.typology,
            "rules_fired": r.rule_names_fired,
            "total_flagged": r.total_amount_flagged,
            "alert_count": len(r.alerts),
            "ml_anomaly_score": r.ml_anomaly_score,
            "ml_priority": r.ml_priority,
            "ml_reason_signals": r.ml_reason_signals,
        }
        for r in sorted_results
    ]

    # STEP 7 : return summary
    typology_breakdown = dict(Counter(
        r.typology for r in grouped.values()
    ))

    return {
        "total_suspicious_accounts": len(grouped),
        "typology_breakdown": typology_breakdown,
        "high_priority_accounts": high_priority,
        "all_accounts": all_accounts,
        "total_alerts": len(alerts),
    }


# AccountAnlysisRequest model for future use in /account-analysis endpoint
class AccountAnalysisRequest(BaseModel):
    account: str
    typology: str 
    rules_fired: list[str]
    total_flagged: float
    alert_count: int
    ml_anomaly_score: float | None = None
    ml_priority: str | None = None
    ml_reason_signals: list[str] | None = None

class AccountGraphRequest(BaseModel):
    account: str
    sample: int


async def load_grouped_results(sample: int):
    transactions = load_transactions(sample=sample)

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(PolicyRule))
        rules = result.scalars().all()
        loaded_rules = []
        for rule in rules:
            await session.refresh(rule)
            loaded_rules.append(rule)

        alerts = await run_compliance(loaded_rules, transactions)

    grouped = group_alerts_by_account(alerts)
    grouped = enrich_grouped_with_ml(grouped)

    return grouped


def build_account_graph_payload(result):
    selected_account = result.account
    nodes = {}
    edge_groups = defaultdict(lambda: {"count": 0, "total_amount": 0.0, "timestamps": []})

    nodes[selected_account] = {
        "id": selected_account,
        "label": selected_account,
        "title": "Selected suspicious account",
        "color": "#E24B4A",
        "size": 30
    }

    for txn in result.transactions:
        sender = txn.get("account")
        receiver = txn.get("account.1")
        amount = txn.get("amount_paid", 0)
        timestamp = txn.get("timestamp", "Unknown time")

        if not sender or not receiver:
            continue

        if sender not in nodes:
            nodes[sender] = {
                "id": sender,
                "label": sender,
                "title": f"Account: {sender}",
                "color": "#CBD5E1",
                "size": 10
            }

        if receiver not in nodes:
            nodes[receiver] = {
                "id": receiver,
                "label": receiver,
                "title": f"Account: {receiver}",
                "color": "#CBD5E1",
                "size": 10
            }
        
        try:
            numeric_amount = float(amount)
        except (TypeError, ValueError):
            numeric_amount = 0.0

        edge_key = (sender, receiver)
        edge_groups[edge_key]["count"] += 1
        edge_groups[edge_key]["total_amount"] += numeric_amount
        edge_groups[edge_key]["timestamps"].append(timestamp)

    edges = []
    for (sender, receiver), edge_data in edge_groups.items():
        latest_timestamp = edge_data["timestamps"][-1] if edge_data["timestamps"] else "Unknown time"
        transfer_count = edge_data["count"]
        total_amount = edge_data["total_amount"]

        edges.append(
            {
                "from": sender,
                "to": receiver,
                "label": f"{transfer_count} txns",
                "title": (
                    f"Suspicious transfers: {transfer_count} | "
                    f"Total amount: ${total_amount:,.2f} | "
                    f"Latest time: {latest_timestamp}"
                ),
                "value": max(total_amount, 1),
                "transaction_count": transfer_count,
                "total_amount": total_amount,
            }
        )

    return {
        "account": selected_account,
        "nodes": list(nodes.values()),
        "edges": edges,
    }



# Separate endpoint for LLM analysis of individual accounts, which can be called from a UI or as part of a prioritization workflow.
@app.post("/account-analysis")
async def account_analysis(payload: AccountAnalysisRequest):
    # The on-demand account-detail flow sends a compact account summary rather
    # than the full grouped result object used during the batch pipeline.
    account_context : dict[str, Any] = {
        "account": payload.account,
        "typology": payload.typology,
        "rules_fired": payload.rules_fired,
        "total_flagged": payload.total_flagged,
        "alert_count": payload.alert_count,
        "ml_anomaly_score": payload.ml_anomaly_score,
        "ml_priority": payload.ml_priority,
        "ml_reason_signals": payload.ml_reason_signals or [],
    }
    
    analysis = await analyze_with_llm(account_context)

    return {
        "account": payload.account,
        "risk_level": analysis["risk_level"],
        "reasoning": analysis["reasoning"],
        "recommendation": analysis["recommendation"]
    }

@app.post("/account-graph")
async def account_graph(payload: AccountGraphRequest):
    grouped = await load_grouped_results(payload.sample)
    result = grouped.get(payload.account)

    if result is None:
        return {
            "account": payload.account,
            "nodes": [],
            "edges": [],
        }

    return build_account_graph_payload(result)

@app.get("/evaluate")
async def evaluate_endpoint():
    return await run_evaluate()
