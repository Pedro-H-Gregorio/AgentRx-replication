"""Immutable per-run context threaded through the graph nodes."""

from __future__ import annotations

from dataclasses import dataclass, field

from opentelemetry import trace

from agentrx_otel_poc.runtime_logging import RunLogger
from agentrx_otel_poc.settings import Settings
from agentrx_otel_poc.tasks import TaskSpec


@dataclass
class LLMStats:
    """Mutable per-run accumulator (the frozen context holds a reference to it).

    `fallback_steps` counts steps that degraded from LLM prose to the
    deterministic template with USE_LLM=true — the audit signal that the corpus
    is not pure LLM prose (0 with USE_LLM=false, where template is the norm).
    """

    fallback_steps: int = 0


@dataclass(frozen=True)
class GraphContext:
    settings: Settings
    task_spec: TaskSpec
    tracer: trace.Tracer
    logger: RunLogger
    fault_type: str | None
    llm_stats: LLMStats = field(default_factory=LLMStats)
