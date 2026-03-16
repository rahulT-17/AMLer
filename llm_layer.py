# llm_layer.py — LLM reasoning layer for AML compliance agent

import httpx
import json
from models.transaction_result import TransactionResult

SYSTEM_PROMPT = """You are a senior AML compliance analyst at a financial intelligence unit.
You will be given details about a suspicious account flagged by our detection system.

Your job is to analyze the account and return ONLY a valid JSON object — no explanation, 
no markdown, no code blocks. Just raw JSON.

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


async def analyze_with_llm(result: TransactionResult) -> dict:
    """
    Send a TransactionResult to LM Studio and get back
    structured AML analysis.
    """

    # BUILD USER PROMPT from TransactionResult data
    user_prompt = f"""
Suspicious Account Analysis Request:

Account ID: {result.account}
Detected Typology: {result.typology}
Rules Fired: {', '.join(result.rule_names_fired)}
Total Amount Flagged: ${result.total_amount_flagged:,.2f}
Number of Suspicious Transactions: {len(result.alerts)}

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
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                "http://localhost:1234/v1/chat/completions",
                json={
                    "model": "mistralai/mistral-7b-instruct-v0.3",
                    "messages": messages,
                    "max_tokens": 150,
                    "temperature": 0.1  # low temperature = consistent output
                }
            )

        # PARSE RESPONSE
        data = response.json()
        raw_text = data["choices"][0]["message"]["content"]

        # clean and parse JSON
        clean = raw_text.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]

        return json.loads(clean)

    except json.JSONDecodeError:
        return {
            "typology": result.typology,
            "risk_level": "UNKNOWN",
            "reasoning": "LLM returned unparseable response",
            "recommendation": "MANUAL_REVIEW"
        }
    except Exception as e:
        print(f"Full error: {type(e).__name__}: {e}")
        return {
            "typology": result.typology,
            "risk_level": "UNKNOWN",
            "reasoning": f"LLM call failed: {str(e)}",
            "recommendation": "MANUAL_REVIEW"
        }