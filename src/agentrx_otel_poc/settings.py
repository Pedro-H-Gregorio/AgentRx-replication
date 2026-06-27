import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    use_llm: bool = os.getenv("USE_LLM", "false").lower() == "true"
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    openai_base_url: str | None = os.getenv("OPENAI_BASE_URL") or os.getenv(
        "OPENAI_API_BASE"
    )
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0"))
    llm_timeout_seconds: float = float(os.getenv("LLM_TIMEOUT_SECONDS", "30"))
    run_id: str = os.getenv("RUN_ID", "run_001")
    task_id: str = os.getenv("TASK_ID", "catalog_dell_price_filter")
    fault_type: str = os.getenv("FAULT_TYPE", "system_timeout")
    otel_service_name: str = os.getenv("OTEL_SERVICE_NAME", "agentrx-otel-poc")
