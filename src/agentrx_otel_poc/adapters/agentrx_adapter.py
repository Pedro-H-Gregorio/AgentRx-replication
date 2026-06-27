from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentrx_otel_poc.runtime_logging import RunLogger


def _step_spans(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        span
        for span in payload.get("spans", [])
        if "experiment.step_index" in span.get("attributes", {})
    ]


def _status_from_otel(span: dict[str, Any]) -> str:
    code = span.get("status", {}).get("status_code")
    attrs = span.get("attributes", {})
    if code == "ERROR" or attrs.get("error.type"):
        return "ERROR"
    return "SUCCESS"


def _observation_from_span(span: dict[str, Any]) -> str:
    attrs = span.get("attributes", {})
    error_type = attrs.get("error.type")
    if error_type:
        return f"{span['name']} failed with {error_type}: {attrs.get('error.message', '')}".strip()
    return f"{span['name']} completed successfully."


def _message_from_span(span: dict[str, Any]) -> str:
    attrs = span.get("attributes", {})
    agent = attrs.get("gen_ai.agent.name", span["name"])
    operation = attrs.get("gen_ai.operation.name", span["name"])
    status = _status_from_otel(span)
    events = [e["name"] for e in span.get("events", [])]
    step_index = int(attrs.get("experiment.step_index", 0))

    lines = [
        f"Step-{step_index}",
        f"Agent: {agent}",
        f"Operation: {operation}",
        f"Status: {status}",
        f"Observation: {_observation_from_span(span)}",
    ]

    tool_name = attrs.get("tool.name")
    if tool_name:
        lines.append(f"Tool: {tool_name}")
    if attrs.get("error.type"):
        lines.append(f"Error type: {attrs['error.type']}")
    if attrs.get("error.message"):
        lines.append(f"Error message: {attrs['error.message']}")
    if events:
        lines.append(f"Events: {', '.join(events)}")

    lines.extend(
        [
            f"OTel trace_id: {span['trace_id']}",
            f"OTel span_id: {span['span_id']}",
            f"Duration ms: {span['duration_ms']}",
        ]
    )
    return "\n".join(lines)


def convert_otel_to_agentrx_trajectory(
    payload: dict[str, Any],
    output_path: Path,
    *,
    logger: RunLogger | None = None,
) -> dict[str, Any]:
    """Converte OTel JSON local para uma trajetória raw no formato flash do AgentRx."""
    spans = _step_spans(payload)
    if logger:
        logger.info(
            "artifact.write.start",
            "Building AgentRx trajectory from OTel payload",
            artifact_kind="agentrx_trajectory",
            output_path=output_path,
            spans=len(spans),
        )

    step_events: list[dict[str, Any]] = []
    for span in spans:
        attrs = span.get("attributes", {})
        step_index = int(attrs.get("experiment.step_index", len(step_events) + 1))
        agent = attrs.get("gen_ai.agent.name", span["name"])
        step_events.append(
            {
                "type": "OrchestrationEvent",
                "source": f"{agent} (Step-{step_index})",
                "message": _message_from_span(span),
                "otel": {
                    "trace_id": span["trace_id"],
                    "span_id": span["span_id"],
                    "parent_span_id": span["parent_span_id"],
                    "duration_ms": span["duration_ms"],
                },
            }
        )

    step_events.sort(key=lambda e: int(e["source"].rsplit("Step-", 1)[1].rstrip(")")))
    events = [
        {
            "type": "OrchestrationEvent",
            "source": "Orchestrator (thought)",
            "message": f"Initial plan: {payload['task']}",
        },
        *step_events,
    ]
    agentrx_input = {
        "trajectory_id": payload["run_id"],
        "instruction": payload["task"],
        "events": events,
        "metadata": {
            "task_id": payload.get("task_id"),
            "domain": "custom_langgraph_mas",
            "task_domain": (payload.get("task_metadata") or {}).get("domain"),
            "source_schema": payload.get("schema"),
            "run_status": payload.get("status"),
        },
    }

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        chars_written = output_path.write_text(
            json.dumps(agentrx_input, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        if logger:
            logger.exception(
                "artifact.write.failed",
                "Failed to write AgentRx trajectory",
                artifact_kind="agentrx_trajectory",
                output_path=output_path,
            )
        raise

    if logger:
        logger.info(
            "artifact.write.done",
            "AgentRx trajectory written",
            artifact_kind="agentrx_trajectory",
            output_path=output_path,
            steps=len(step_events),
            chars_written=chars_written,
        )

    return agentrx_input
