from fastapi import  APIRouter

from api.schemas.account_detail import AccountAnalysisRequest, AccountGraphRequest
from services.account_detail_service import load_grouped_results, build_account_graph_payload

from typing  import Any

from llm_layer import analyze_with_llm

router = APIRouter()

@router.post("/account-analysis")
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

@router.post("/account-graph")
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