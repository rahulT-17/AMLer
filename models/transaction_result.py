# models / transaction_result.py : this file defines the TransactionResult class which is used to store the result of evaluating a transaction against a rule

from dataclasses import dataclass, field
from typing import List, Optional 

@dataclass
class TransactionResult :

    account : str
    alerts: List[dict]  = field(default_factory= list)
    rule_names_fired: List[str] = field(default_factory= list)
    total_amount_flagged: float = 0.0
    typology: Optional[str] = None
    risk_level: Optional[str] = None
    llm_analysis: Optional[str] = None
    recommendation: Optional[str] = None