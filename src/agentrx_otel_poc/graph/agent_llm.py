"""Optional agent LLM step (USE_LLM toggle), kept category-blind (R5).

With `USE_LLM=true` the agent model phrases a step and reports real token usage;
otherwise the deterministic fallback is used (zero tokens). The fault operators
govern the experiment's structure regardless — this only affects prose + telemetry.
The prompt is built from step data only; it never receives the fault category.
"""

from __future__ import annotations

from agentrx_otel_poc.llm import ZERO_USAGE, invoke_agent
from agentrx_otel_poc.runtime_logging import RunLogger

from .context import GraphContext


def agent_message(
    ctx: GraphContext,
    prompt: str,
    fallback: str,
    *,
    logger: RunLogger | None = None,
) -> tuple[str, dict[str, int]]:
    """Return (text, token_usage) for a step's natural-language output."""
    if not ctx.settings.use_llm:
        return fallback, dict(ZERO_USAGE)
    try:
        text, usage = invoke_agent(ctx.settings, prompt, logger=logger)
        return (text.strip() or fallback), usage
    except Exception:  # noqa: BLE001 (a flaky agent must not abort the run)
        if logger:
            logger.exception(
                "agent.llm.failed", "Agent LLM failed; using deterministic fallback"
            )
        return fallback, dict(ZERO_USAGE)
