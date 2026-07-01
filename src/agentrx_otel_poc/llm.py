from __future__ import annotations

from langchain_openai import ChatOpenAI

from agentrx_otel_poc.runtime_logging import RunLogger
from agentrx_otel_poc.settings import Settings

ZERO_USAGE: dict[str, int] = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}


def _client(
    model: str, base_url: str | None, api_key: str, settings: Settings
) -> ChatOpenAI:
    """OpenAI-compatible client (e.g. a local model via a `/v1` endpoint)."""
    return ChatOpenAI(
        model=model,
        api_key=api_key or "not-needed",
        base_url=base_url,
        temperature=settings.llm_temperature,
        timeout=settings.llm_timeout_seconds,
        max_retries=0,
    )


def _invoke(
    model: str,
    base_url: str | None,
    api_key: str,
    settings: Settings,
    prompt: str,
    *,
    logger: RunLogger | None,
) -> tuple[str, dict[str, int]]:
    if logger:
        logger.info(
            "llm.request.start",
            "Submitting prompt to LLM",
            model=model,
            prompt_chars=len(prompt),
            base_url=base_url or "default",
        )
    try:
        response = _client(model, base_url, api_key, settings).invoke(prompt)
    except Exception:
        if logger:
            logger.exception("llm.request.failed", "LLM request failed", model=model)
        raise
    usage = getattr(response, "usage_metadata", None) or {}
    tokens = {
        "input_tokens": int(usage.get("input_tokens", 0) or 0),
        "output_tokens": int(usage.get("output_tokens", 0) or 0),
        "total_tokens": int(usage.get("total_tokens", 0) or 0),
    }
    content = str(response.content)
    if logger:
        logger.info(
            "llm.request.success",
            "LLM response received",
            model=model,
            total_tokens=tokens["total_tokens"],
            response_chars=len(content),
        )
    return content, tokens


def invoke_agent(
    settings: Settings, prompt: str, *, logger: RunLogger | None = None
) -> tuple[str, dict[str, int]]:
    """Invoke the MAS agent model (`AGENT_MODEL`/`AGENT_BASE_URL`/`AGENT_API_KEY`)."""
    return _invoke(
        settings.agent_model,
        settings.agent_base_url,
        settings.agent_api_key,
        settings,
        prompt,
        logger=logger,
    )
