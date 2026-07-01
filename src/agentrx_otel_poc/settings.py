import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    use_llm: bool = os.getenv("USE_LLM", "false").lower() == "true"
    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0"))
    llm_timeout_seconds: float = float(os.getenv("LLM_TIMEOUT_SECONDS", "30"))
    # MAS agent model is parametrizable and recorded in each run manifest (PRD-00 §4.1).
    # Used only when USE_LLM=true; otherwise the agent runs deterministically.
    agent_model: str = os.getenv("AGENT_MODEL", "Llama3.1-8B")
    agent_base_url: str | None = os.getenv("AGENT_BASE_URL")
    agent_api_key: str = os.getenv("AGENT_API_KEY", "ollama")
    otel_service_name: str = os.getenv("OTEL_SERVICE_NAME", "agentrx-otel-poc")
