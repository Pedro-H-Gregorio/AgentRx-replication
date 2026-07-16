from __future__ import annotations

import time

from langchain_openai import ChatOpenAI
from openai import APIStatusError, APITimeoutError, RateLimitError

from agentrx_otel_poc.runtime_logging import RunLogger
from agentrx_otel_poc.settings import Settings

ZERO_USAGE: dict[str, int] = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
# 5xx worth retrying; 429 is RateLimitError (handled apart); other 4xx are not.
_RETRYABLE_STATUS = {500, 502, 503, 504}


def _client(
    model: str, base_url: str | None, api_key: str, settings: Settings
) -> ChatOpenAI:
    """OpenAI-compatible client (e.g. a local model via a `/v1` endpoint)."""
    # CONTRACT: max_retries stays 0 — retries live in `_invoke` so they honor our
    # backoff policy, log per attempt, and never double-wait with the SDK's own.
    return ChatOpenAI(
        model=model,
        api_key=api_key or "not-needed",
        base_url=base_url,
        temperature=settings.llm_temperature,
        timeout=settings.llm_timeout_seconds,
        max_retries=0,
    )


def _is_retryable(exc: Exception) -> bool:
    """Transient transport noise: 429, retryable 5xx, or a timeout."""
    if isinstance(exc, (RateLimitError, APITimeoutError)):
        return True
    if isinstance(exc, APIStatusError):
        return exc.status_code in _RETRYABLE_STATUS
    return False


def _retry_after(exc: Exception) -> float | None:
    """`Retry-After` seconds from the response headers, if numeric."""
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    value = headers.get("retry-after") if headers else None
    if value and str(value).strip().replace(".", "", 1).isdigit():
        return float(value)
    return None


def _wait_seconds(exc: Exception, attempt: int, settings: Settings) -> float:
    """Honor Retry-After if present, else exponential base×2^attempt, both capped."""
    cap = settings.agent_retry_max_seconds
    after = _retry_after(exc)
    if after is not None:
        return min(after, cap)
    return min(settings.agent_retry_base_seconds * (2**attempt), cap)


def _invoke_with_backoff(
    client: ChatOpenAI,
    prompt: str,
    settings: Settings,
    *,
    model: str,
    logger: RunLogger | None,
):
    """Invoke the client, retrying transport noise (429/5xx/connection) with
    backoff. Non-retryable errors and the final failure propagate to the caller."""
    for attempt in range(settings.agent_max_retries + 1):
        try:
            return client.invoke(prompt)
        except Exception as exc:
            if not _is_retryable(exc) or attempt == settings.agent_max_retries:
                if logger:
                    logger.exception(
                        "llm.request.failed", "LLM request failed", model=model
                    )
                raise
            wait = _wait_seconds(exc, attempt, settings)
            if logger:
                logger.info(
                    "llm.request.retry",
                    "Transport error; backing off before retry",
                    model=model,
                    attempt=attempt + 1,
                    max_retries=settings.agent_max_retries,
                    wait_seconds=round(wait, 1),
                )
            time.sleep(wait)
    raise RuntimeError("unreachable")


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
    client = _client(model, base_url, api_key, settings)
    response = _invoke_with_backoff(
        client, prompt, settings, model=model, logger=logger
    )
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
