from __future__ import annotations

import json
import re
from typing import Any

from langchain_openai import ChatOpenAI

from agentrx_otel_poc.runtime_logging import RunLogger
from agentrx_otel_poc.settings import Settings

ZERO_USAGE: dict[str, int] = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}


def _client(
    model: str, base_url: str | None, api_key: str, settings: Settings
) -> ChatOpenAI:
    """OpenAI or OpenAI-compatible client (e.g. a local model via an /v1 endpoint)."""
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


def invoke_llm(
    settings: Settings, prompt: str, *, logger: RunLogger | None = None
) -> tuple[str, dict[str, int]]:
    """Invoke the OpenAI-configured model (`OPENAI_*`)."""
    if not settings.openai_api_key:
        raise RuntimeError(
            "OPENAI_API_KEY não definido. Use USE_LLM=false ou configure .env"
        )
    return _invoke(
        settings.openai_model,
        settings.openai_base_url,
        settings.openai_api_key,
        settings,
        prompt,
        logger=logger,
    )


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


def build_llm(settings: Settings) -> ChatOpenAI:
    return _client(
        settings.openai_model,
        settings.openai_base_url,
        settings.openai_api_key,
        settings,
    )


def summarize_with_llm(
    settings: Settings, prompt: str, *, logger: RunLogger | None = None
) -> tuple[str, dict[str, int]]:
    return invoke_llm(settings, prompt, logger=logger)


def parse_json_object(content: str) -> dict[str, Any]:
    text = content.strip()
    if text.startswith("```"):
        match = re.search(
            r"```(?:json)?\s*(.*?)\s*```", text, flags=re.DOTALL | re.IGNORECASE
        )
        if match:
            text = match.group(1).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end < start:
            raise
        parsed = json.loads(text[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("LLM response must be a JSON object")
    return parsed
