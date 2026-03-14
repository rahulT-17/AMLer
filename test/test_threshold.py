# test_threshold.py

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import asyncio
from evaluators.threshold import ThresholdEvaluator

# fake rule
class FakeRule:
    rule_id = 1
    field_target = "Amount"
    operator = ">"
    threshold_value = "10000"
    severity = "HIGH"
    source_text = "Amount exceeds 10000"

# fake transactions
transactions = [
    {"Amount": "15000", "From Bank": "ACC_A", "To Bank": "ACC_B"},
    {"Amount": "5000", "From Bank": "ACC_C", "To Bank": "ACC_D"},
]

async def test():
    evaluator = ThresholdEvaluator(FakeRule())
    alerts = await evaluator.evaluate(transactions)
    print(alerts)

asyncio.run(test())