# Evalutors / Threshold Evaluator : this will handle the threshold policy rules and evaluate them against the data

""" loop every transaction, check if a field value breaks the rule's condition, collect and return all violations."""

from .base import BaseEvaluator

class ThresholdEvaluator(BaseEvaluator) :

    def __init__(self, rule):
        self.rule = rule

    async def evaluate(self, transactions) -> list :
        """Evaluate the transactions against the threshold rule and return a list of alerts (if any)"""
        
        operator = self.rule.operator
        alerts = []
        
        for transaction in transactions :

            field_value = transaction.get(self.rule.field_target)

            if field_value is None :
                continue # skip if the target field is not present in the transaction
            # Convert to numeric if possible for comparison

            try :
                field_value = float(field_value)
                threshold_value = float(self.rule.threshold_value)
            except ValueError :
                continue # skip if values cannot be converted to numeric

            alert_triggered = False

            if operator == ">" and field_value > threshold_value :
                alert_triggered = True
            elif operator == "<" and field_value < threshold_value :
                alert_triggered = True
            elif operator == ">=" and field_value >= threshold_value :
                alert_triggered = True
            elif operator == "<=" and field_value <= threshold_value :
                alert_triggered = True
            elif operator == "==" and field_value == threshold_value :
                alert_triggered = True
            elif operator == "!=" and field_value != threshold_value :
                alert_triggered = True

            if alert_triggered :
                alerts.append({
                    "rule_id" : self.rule.rule_id,
                    "rule_name": self.rule.name,
                    "transaction" : transaction,
                    "message" : f"Threshold rule violated: {self.rule.source_text}",
                    "severity" : self.rule.severity
                })
            
        return alerts
