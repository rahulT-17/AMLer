# llm_layer.py — LLM reasoning layer for AML compliance agent

# import libraries and dependencies:
import httpx
import json
from typing import Any

from core.config import settings

from models.transaction_result import TransactionResult


SYSTEM_PROMPT = """You are a senior AML compliance analyst at a financial intelligence unit.
You will be given details about a suspicious account flagged by our detection system.

Your job is to analyze the account and return ONLY a valid JSON object — no explanation, 
no markdown, no code blocks. Just raw JSON.

Instructions for your analysis:
- Use the provided data about the account, including typology, rules fired, total amount flagged, and number of suspicious transactions.
- Assess the risk level of the account based on the evidence.
- Use the anomaly score as supporting context, not as sole proof of laundering.

Return exactly this structure:
{
    "typology": "one of: STRUCTURING / SMURFING / LAYERING / PLACEMENT / UNKNOWN",
    "risk_level": "one of: LOW / MEDIUM / HIGH / CRITICAL",
    "reasoning": "2-3 sentences explaining why this account is suspicious",
    "recommendation": "specific action: FREEZE_ACCOUNT / FILE_SAR / MONITOR / DISMISS"
}

Risk level guidelines:
- CRITICAL: multiple typologies, high amounts, clear laundering pattern
- HIGH: strong single typology signal, significant amounts
- MEDIUM: weak signal, could be legitimate
- LOW: minimal evidence, likely false positive"""


async def analyze_with_llm(result: TransactionResult | dict[str, Any]) -> dict:
    """
    Send either a grouped TransactionResult or a compact account-summary
    payload to LM Studio and get back structured AML analysis.
    """

    # The LLM layer now supports both:
    # 1. the original grouped TransactionResult objects from the batch flow
    # 2. the lighter account-summary payload used by the on-demand detail view
    if isinstance(result, dict):
        account = result.get("account", "UNKNOWN")
        typology = result.get("typology", "UNKNOWN")
        rules_fired = result.get("rules_fired") or result.get("rule_names_fired") or []
        total_flagged = float(result.get("total_flagged", result.get("total_amount_flagged", 0.0)) or 0.0)
        alert_count = int(result.get("alert_count", 0) or 0)
        ml_anomaly_score = result.get("ml_anomaly_score")
        ml_priority = result.get("ml_priority")
        ml_reason_signals = result.get("ml_reason_signals") or []
    else:
        account = result.account
        typology = result.typology
        rules_fired = result.rule_names_fired
        total_flagged = result.total_amount_flagged
        alert_count = len(result.alerts)
        ml_anomaly_score = result.ml_anomaly_score
        ml_priority = result.ml_priority
        ml_reason_signals = result.ml_reason_signals

    # BUILD USER PROMPT from TransactionResult data
    user_prompt = f"""
Suspicious Account Analysis Request:

Account ID: {account}
Detected Typology: {typology}
Rules Fired: {', '.join(rules_fired)}
Total Amount Flagged: ${total_flagged:,.2f}
Number of Suspicious Transactions: {alert_count}
ML Anomaly Score: {ml_anomaly_score if ml_anomaly_score is not None else "N/A"}
ML Priority: {ml_priority or "N/A"}
ML Signals: {", ".join(ml_reason_signals) if ml_reason_signals else "None"}

Analyze this account and return your JSON assessment.


"""

    # BUILD MESSAGES
    messages = [
      {
        "role": "user",
        "content": f"{SYSTEM_PROMPT}\n\n{user_prompt}"
      }
    ]

    # CALL LM STUDIO
    try:
        async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
            response = await client.post(
                settings.llm_base_url,
                json={
                    "model": settings.llm_model,
                    "messages": messages,
                    "max_tokens": 150,
                    "temperature": 0.1  # low temperature = consistent output
                }
            )

        # PARSE RESPONSE
        data = response.json()
        raw_text = data["choices"][0]["message"]["content"]

        # Extract the JSON body even if the model adds fences or extra text.
        clean = raw_text.strip()
        if clean.startswith("```"):
            clean = clean.replace("```json", "").replace("```", "").strip()

        start = clean.find("{")
        end = clean.rfind("}")
        if start != -1 and end != -1 and end > start:
            clean = clean[start:end + 1]

        return json.loads(clean)

    except json.JSONDecodeError:
        print("Raw LLM response that failed JSON parsing:")
        print(raw_text)
        return {
            "typology": typology,
            "risk_level": "UNKNOWN",
            "reasoning": "LLM returned unparseable response",
            "recommendation": "MANUAL_REVIEW"
        }
    except Exception as e:
        print(f"Full error: {type(e).__name__}: {e}")
        return {
            "typology": typology,
            "risk_level": "UNKNOWN",
            "reasoning": f"LLM call failed: {str(e)}",
            "recommendation": "MANUAL_REVIEW"
        }
