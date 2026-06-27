from __future__ import annotations

import json
import re
from typing import Any

from langchain_openai import ChatOpenAI

from agentrx_otel_poc.settings import Settings
from agentrx_otel_poc.runtime_logging import RunLogger


def build_llm(settings: Settings) -> ChatOpenAI:
    """Cria cliente OpenAI ou OpenAI-compatible.

    Para endpoint oficial:
        OPENAI_BASE_URL=https://api.openai.com/v1

    Para endpoint compatível:
        OPENAI_BASE_URL=https://sua-url/v1
        OPENAI_API_KEY=...

    Observação: provedores compatíveis podem retornar metadados fora do padrão OpenAI.
    """
    if not settings.openai_api_key:
        raise RuntimeError(
            "OPENAI_API_KEY não definido. Use USE_LLM=false ou configure .env"
        )

    return ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        temperature=settings.llm_temperature,
        timeout=settings.llm_timeout_seconds,
        max_retries=0,
    )


def invoke_llm(
    settings: Settings,
    prompt: str,
    *,
    logger: RunLogger | None = None,
) -> tuple[str, dict[str, int]]:
    """Retorna conteúdo e uso de tokens quando disponível."""
    if logger:
        logger.info(
            "llm.request.start",
            "Submitting prompt to LLM",
            model=settings.openai_model,
            prompt_chars=len(prompt),
            temperature=settings.llm_temperature,
            timeout_seconds=settings.llm_timeout_seconds,
            base_url=settings.openai_base_url or "default",
        )

    if not settings.openai_api_key:
        error = RuntimeError(
            "OPENAI_API_KEY não definido. Use USE_LLM=false ou configure .env"
        )
        if logger:
            logger.error(
                "llm.request.failed",
                "LLM request aborted before client creation",
                model=settings.openai_model,
                reason="missing_api_key",
            )
        raise error

    try:
        llm = build_llm(settings)
        response = llm.invoke(prompt)
    except Exception:
        if logger:
            logger.exception(
                "llm.request.failed",
                "LLM request failed",
                model=settings.openai_model,
                prompt_chars=len(prompt),
            )
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
            model=settings.openai_model,
            input_tokens=tokens["input_tokens"],
            output_tokens=tokens["output_tokens"],
            total_tokens=tokens["total_tokens"],
            response_chars=len(content),
        )

    return content, tokens


def summarize_with_llm(
    settings: Settings,
    prompt: str,
    *,
    logger: RunLogger | None = None,
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
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end < start:
            raise
        parsed = json.loads(text[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("LLM response must be a JSON object")
    return parsed
