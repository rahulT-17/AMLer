# Evalutors / Frequency Evaluator : this will handle the frequency policy rules and evaluate them against the data.

from .base import BaseEvaluator

class FrequencyEvaluator(BaseEvaluator) :
    def __init__(self, rule):
        self.rule = rule

    """  what's happening here :

    **Step 1 — Grouping:**
    Loop every transaction and bucket them by account. If 50 transactions share the same sender `ACC_A`, they all go into `grouped["ACC_A"]`. Result is a dict of account → list of transactions.

    **Step 2 — Counterparty flip:**
    If we're watching senders (`From Bank`), the suspicious signal is how many *different receivers* they're sending to. So we flip to `To Bank` to find counterparties. Vice versa for receivers.

    **Step 3 — Distinct count check:**
    For each account, collect all counterparties into a **set** — sets automatically remove duplicates, so you get distinct count for free. If that set is bigger than `min_count` 
    — this account is fanning out to too many distinct destinations. Flag every transaction it made.

    """

    async def evaluate(self, transactions) -> list :
        """Evaluate the transactions against the frequency rule and return a list of alerts (if any)"""
        
        alerts = []
        # step 1 : group transactions by the target field (e.g. sender or receiver)
        grouped = {}

        for transaction in transactions :
            key = transaction.get(self.rule.group_by_field)

            if key is None :
                continue # skip if the group by field is not present in the transaction

            if key not in grouped :
                grouped[key] = []
            
            grouped[key].append(transaction)

        # step 2 : determine the counterparty field :
        if self.rule.group_by_field == "account" :
            counterparty_field = "account.1"
        else :
            counterparty_field = "account"

        # step 3 : check each account for distinct counterparty violations
        for account , txns in grouped.items() :
            counterparties = set()

            for txn in txns :                                    # loop through transactions for this account and collect distinct counterparties
                counterparty = txn.get(counterparty_field)

                if counterparty :
                    counterparties.add(counterparty)
            
            if len(counterparties) >= self.rule.min_count :  
                    alerts.append({
                        "rule_id" : self.rule.rule_id,
                        "rule_name": self.rule.name,
                        "account" : account,
                        "message" : f"Frequency rule violated: {self.rule.source_text}",
                        "severity" : self.rule.severity
                    })

        return alerts