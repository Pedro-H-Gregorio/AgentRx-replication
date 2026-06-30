"""Immutable per-run context threaded through the graph nodes."""

from __future__ import annotations

from dataclasses import dataclass

from opentelemetry import trace

from agentrx_otel_poc.runtime_logging import RunLogger
from agentrx_otel_poc.settings import Settings
from agentrx_otel_poc.tasks import TaskSpec


@dataclass(frozen=True)
class GraphContext:
    settings: Settings
    task_spec: TaskSpec
    tracer: trace.Tracer
    logger: RunLogger
    fault_type: str | None
