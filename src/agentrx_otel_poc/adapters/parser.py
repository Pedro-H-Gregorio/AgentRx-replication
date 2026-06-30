"""The single OTel→IR parser (PRD-04 §3): the only place that orders/slices steps.

Both trajectory arms consume `ParsedStep`s from here, so step ordering and slicing
are identical across arms by construction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ParsedStep:
    step_index: int
    agent_name: str
    operation: str
    role: str
    status: str
    input_message: str
    output_message: str
    tool_name: str | None
    tool_args_json: str | None
    tool_result_json: str | None
    error_type: str | None
    error_message: str | None
    reasoning_summary: str | None
    validation_status: str | None
    validation_reason: str | None
    constraint_violations_json: str | None
    events: list[dict[str, Any]] = field(default_factory=list)
    telemetry: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedTrajectory:
    trajectory_id: str
    instruction: str
    steps: list[ParsedStep]


def _telemetry(span: dict[str, Any], attrs: dict[str, Any]) -> dict[str, Any]:
    status = span.get("status", {}) or {}
    return {
        "duration_ms": span.get("duration_ms"),
        "input_tokens": attrs.get("gen_ai.usage.input_tokens"),
        "output_tokens": attrs.get("gen_ai.usage.output_tokens"),
        "total_tokens": attrs.get("gen_ai.usage.total_tokens"),
        "model": attrs.get("gen_ai.request.model"),
        "span_id": span.get("span_id"),
        "parent_span_id": span.get("parent_span_id"),
        "trace_id": span.get("trace_id"),
        "otel_status": status.get("status_code"),
        "kind": span.get("kind"),
        "peer_service": attrs.get("peer.service"),
        "rpc_system": attrs.get("rpc.system"),
        "http_method": attrs.get("http.request.method"),
    }


def parse(payload: dict[str, Any]) -> ParsedTrajectory:
    steps: list[ParsedStep] = []
    for span in payload.get("spans", []):
        attrs = span.get("attributes", {}) or {}
        index = attrs.get("experiment.step_index")
        if index is None:
            continue  # skip the workflow root span (no step index)
        status = span.get("status", {}) or {}
        steps.append(
            ParsedStep(
                step_index=int(index),
                agent_name=str(attrs.get("gen_ai.agent.name", span.get("name", ""))),
                operation=str(attrs.get("gen_ai.operation.name", "")),
                role=str(attrs.get("agent.role", "")),
                status=str(status.get("status_code", "")),
                input_message=str(attrs.get("agent.input_message", "")),
                output_message=str(attrs.get("agent.output_message", "")),
                tool_name=attrs.get("tool.name"),
                tool_args_json=attrs.get("tool.args_json"),
                tool_result_json=attrs.get("tool.result_json"),
                error_type=attrs.get("error.type"),
                error_message=attrs.get("error.message"),
                reasoning_summary=attrs.get("agent.reasoning_summary"),
                validation_status=attrs.get("validation.status"),
                validation_reason=attrs.get("validation.reason"),
                constraint_violations_json=attrs.get("constraint.violations_json"),
                events=[dict(e) for e in span.get("events", [])],
                telemetry=_telemetry(span, attrs),
            )
        )
    steps.sort(key=lambda s: s.step_index)
    metadata = payload.get("task_metadata") or {}
    instruction = payload.get("task") or metadata.get("user_request", "")
    return ParsedTrajectory(str(payload.get("run_id", "")), str(instruction), steps)
