# evalutors / base.py 
from abc import ABC, abstractmethod

class BaseEvaluator(ABC) :
    
    def __init__(self,rule):
        
        self.rule = rule

    @abstractmethod
    async def evaluate(self, transactions) -> list :
        """Every evaluator must implement this method to evaluate a transaction 
        against the rule and return a list of alerts (if any)
        
        here the transactions is a list of transaction dicts,
        and the rule is the policy rule object that contains the parameters for evaluation."""

        pass