"""Category-blind span helpers.

`render`-style helpers receive only step data (messages, role, operation, tool
result). They never receive `target_fault_category`/`injection_node`; the same
helpers serve the happy path and the fault path. The only category-bearing call
is `emit_fault`, which writes the structured `fault.injected` event to the raw
span (stripped from trajectories later) — not free-text rendered into content.
"""

from __future__ import annotations

import json
from typing import Any

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from agentrx_otel_poc.telemetry import add_step, set_error, set_success

__all__ = [
    "dumps",
    "begin",
    "io",
    "set_usage",
    "emit_fault",
    "mark_error",
    "set_success",
    "set_error",
]


def dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def begin(
    span: trace.Span,
    step_index: int,
    agent_name: str,
    operation: str,
    role: str,
    operation_type: str,
    model: str = "",
) -> None:
    """Set the common per-step attributes from step data only (no ground truth)."""
    add_step(span, step_index, agent_name, operation)
    span.set_attribute("experiment.operation_type", operation_type)
    span.set_attribute("agent.role", role)
    span.set_attribute("gen_ai.request.model", model)
    for kind in ("input", "output", "total"):
        span.set_attribute(f"gen_ai.usage.{kind}_tokens", 0)


def io(span: trace.Span, input_message: str, output_message: str) -> None:
    span.set_attribute("agent.input_message", input_message)
    span.set_attribute("agent.output_message", output_message)


def set_usage(span: trace.Span, usage: dict[str, int]) -> None:
    """Override the token counts with the real usage from an agent LLM call."""
    for kind in ("input", "output", "total"):
        span.set_attribute(
            f"gen_ai.usage.{kind}_tokens", int(usage.get(f"{kind}_tokens", 0))
        )


def emit_fault(span: trace.Span, operator: Any) -> None:
    """Record the ground-truth injection marker in the raw span (stripped later)."""
    span.add_event(
        "fault.injected", {"category": operator.category, "node": operator.node}
    )


def mark_error(span: trace.Span, error_type: str, message: str) -> None:
    """Mark a handled (non-exception) error, e.g. a tool rejecting a bad call."""
    span.set_status(Status(StatusCode.ERROR, message))
    span.set_attribute("error.type", error_type)
    span.set_attribute("error.message", message)
