"""Optional agent LLM step (USE_LLM toggle), kept category-blind (R5).

With `USE_LLM=true` the agent model phrases a step and reports real token usage;
otherwise the deterministic fallback is used (zero tokens). The fault operators
govern the experiment's structure regardless — this only affects prose + telemetry.
The prompt is built from step data only; it never receives the fault category.

A step degrades to the deterministic template only when the LLM fails after
backoff (`llm.py`) or returns empty. That degradation is either counted
(`fallback_steps`, tolerant mode) or aborts the run (`USE_LLM_STRICT`, corpus
generation) — never a silent mix of LLM and template prose.
"""

from __future__ import annotations

from agentrx_otel_poc.llm import ZERO_USAGE, invoke_agent
from agentrx_otel_poc.runtime_logging import RunLogger

from .context import GraphContext


class AgentLLMError(RuntimeError):
    """Raised in strict mode when the agent LLM fails — aborts the run high."""


def _degrade(
    ctx: GraphContext, label: str, reason: str, fallback: str, logger: RunLogger | None
) -> tuple[str, dict[str, int]]:
    """Strict → abort the run; tolerant → count the fallback and use the template."""
    if ctx.settings.use_llm_strict:
        raise AgentLLMError(
            f"{label}: agent LLM failed ({reason}); USE_LLM_STRICT aborts the run"
        )
    ctx.llm_stats.fallback_steps += 1
    if logger:
        logger.warning(
            "llm.request.fallback",
            "Agent LLM degraded to deterministic template",
            label=label,
            reason=reason,
        )
    return fallback, dict(ZERO_USAGE)


def agent_message(
    ctx: GraphContext,
    prompt: str,
    fallback: str,
    *,
    label: str = "agent",
    logger: RunLogger | None = None,
) -> tuple[str, dict[str, int]]:
    """Return (text, token_usage) for a step's natural-language output."""
    if not ctx.settings.use_llm:
        return fallback, dict(ZERO_USAGE)
    try:
        text, usage = invoke_agent(ctx.settings, prompt, logger=logger)
    except Exception as exc:  # noqa: BLE001 (transport failed after backoff)
        return _degrade(ctx, label, f"transport failure: {exc}", fallback, logger)
    if not text.strip():
        if logger:
            logger.warning(
                "llm.request.empty", "Agent LLM returned empty text", label=label
            )
        return _degrade(ctx, label, "empty response", fallback, logger)
    return text.strip(), usage
