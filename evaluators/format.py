# evaluators / Format Evaluator : this will handle the format policy rules and evaluate them against the data

""" loop every transaction, check if a field value breaks the rule's condition, collect and return all violations."""
import re
from .base import BaseEvaluator

class FormatEvaluator(BaseEvaluator) :  
    
    def __init__(self, rule):
        self.rule = rule

    async def evaluate(self, transactions):
        alerts = []

        for transaction in transactions:
            field_value = transaction.get(self.rule.field_target)

            if field_value is None :
                continue    

            result = re.match(self.rule.pattern, str(field_value)) 

            if not result:  # if the pattern does not match, it's a violation
                alerts.append({
                    "rule_id": self.rule.rule_id,
                    "rule_name": self.rule.name,
                    "transaction": transaction,
                    "field": self.rule.field_target,
                    "value": field_value,
                    "reason": f"Value '{field_value}' does not match pattern '{self.rule.pattern}'"
                })
        return alerts
