import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    use_llm: bool = os.getenv("USE_LLM", "false").lower() == "true"
    # Strict mode prevents a mixed LLM/template corpus after a transport failure.
    use_llm_strict: bool = os.getenv("USE_LLM_STRICT", "false").lower() == "true"
    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0"))
    llm_timeout_seconds: float = float(os.getenv("LLM_TIMEOUT_SECONDS", "30"))
    # Transport retries honor Retry-After, then capped exponential backoff.
    agent_max_retries: int = int(os.getenv("AGENT_MAX_RETRIES", "5"))
    agent_retry_base_seconds: float = float(os.getenv("AGENT_RETRY_BASE_SECONDS", "5"))
    agent_retry_max_seconds: float = float(os.getenv("AGENT_RETRY_MAX_SECONDS", "120"))
    # Used only with USE_LLM=true and recorded in the run manifest.
    agent_model: str = os.getenv("AGENT_MODEL", "Llama3.1-8B")
    # Empty resolves from effective agent_model, including programmatic runs.
    mas_id: str = os.getenv("MAS_ID", "")
    agent_base_url: str | None = os.getenv("AGENT_BASE_URL")
    agent_api_key: str = os.getenv("AGENT_API_KEY", "ollama")
    otel_service_name: str = os.getenv("OTEL_SERVICE_NAME", "agentrx-otel-poc")
    # Backend and model are recorded in the judge manifest.
    judge_backend: str = os.getenv("JUDGE_BACKEND", "stub")
    judge_model: str = os.getenv("JUDGE_MODEL", "")
    judge_base_url: str | None = os.getenv("JUDGE_BASE_URL")
    judge_api_key: str = os.getenv("JUDGE_API_KEY", "")
    judge_timeout_seconds: float = float(os.getenv("JUDGE_TIMEOUT_SECONDS", "600"))
    judge_temperature: float = float(os.getenv("JUDGE_TEMPERATURE", "0"))
    judge_reps: int = int(os.getenv("JUDGE_REPS", "3"))
