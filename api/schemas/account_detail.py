# api/schemas/account_detail.py : Pydantic models for account detail analysis and graph generation

from pydantic import BaseModel


class AccountAnalysisRequest(BaseModel):
    account: str
    typology: str 
    rules_fired: list[str]
    total_flagged: float
    alert_count: int
    ml_anomaly_score: float | None = None
    ml_priority: str | None = None
    ml_reason_signals: list[str] | None = None

class AccountGraphRequest(BaseModel):
    account: str
    sample: int


