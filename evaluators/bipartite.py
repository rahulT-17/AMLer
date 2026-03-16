# Bipartite Rule Evaluator

from .base import BaseEvaluator

class BipartiteEvaluator(BaseEvaluator) :
    def __init__(self, rule):
        self.rule = rule

    async def evaluate(self, transactions) -> list :

        alerts = []

        for transaction in transactions :
            is_violation = False

            if self.rule.check_type == "same_account" :
                is_violation = transaction["account"] == transaction["account.1"]

            elif self.rule.check_type == "same_bank":
                is_violation = transaction["from_bank"] == transaction["to_bank"]

            elif self.rule.check_type == "both":
                is_violation = (transaction["account"] == transaction["account.1"] and 
                                  transaction["from_bank"] == transaction["to_bank"])
                
            if is_violation :
                alerts.append({
                    "rule_id" : self.rule.rule_id,
                    "transaction" : transaction,
                    "message" : f"Bipartite rule violated: {self.rule.source_text}",
                    "severity" : self.rule.severity
                })
                
        return alerts
