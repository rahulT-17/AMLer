# app.py : AML Compliance Agent API




from fastapi import FastAPI

from api.schemas.account_detail import AccountAnalysisRequest, AccountGraphRequest
from services.account_detail_service import load_grouped_results, build_account_graph_payload
from services.analysis_service import run_analysis
from typing import Any

from evaluate import evaluate as run_evaluate

from llm_layer import analyze_with_llm


app = FastAPI(title="AML Compliance Agent")

@app.post("/analyze")
async def analyze_endpoint(sample: int, include_llm: bool):
    return await run_analysis(sample=sample, include_llm=include_llm)
    # For simplicity, this endpoint runs the full analysis pipeline on demand.

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
