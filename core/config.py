# settings.py — Configuration management for AML Compliance Agent

from dataclasses import dataclass
from pathlib import Path
import os


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / ".env"


def _load_env_file() -> None:
    if not ENV_FILE.exists():
        return

    for raw_line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        # Keep real environment variables higher priority than the file.
        os.environ.setdefault(key, value)


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


_load_env_file()


@dataclass(frozen=True)
class Settings:
    database_url: str
    sql_echo: bool
    llm_enabled: bool
    llm_base_url: str
    llm_model: str
    llm_timeout_seconds: float
    api_base_url: str
    default_sample_size: int


settings = Settings(
    database_url=os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:your_password@localhost:5432/aml_compliance",
    ),
    sql_echo=_get_bool("SQL_ECHO", False),
    llm_enabled=_get_bool("LLM_ENABLED", True),
    llm_base_url=os.getenv("LLM_BASE_URL", "http://localhost:1234/v1/chat/completions"),
    llm_model=os.getenv("LLM_MODEL", "mistralai/mistral-7b-instruct-v0.3"),
    llm_timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "120")),
    api_base_url=os.getenv("API_BASE_URL", "http://localhost:8000"),
    default_sample_size=int(os.getenv("DEFAULT_SAMPLE_SIZE", "5000")),
)
