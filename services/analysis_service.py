
from sqlalchemy import select
from collections import Counter
from compliance.compliance_runner import run_compliance
from typology import group_alerts_by_account    
from ml_layer import enrich_grouped_with_ml
from policy_rules_model import PolicyRule
from llm_layer import analyze_with_llm

from core.db import AsyncSessionLocal
from transaction_loader import load_transactions


async def run_analysis(sample: int = 1000, include_llm: bool = False):

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
