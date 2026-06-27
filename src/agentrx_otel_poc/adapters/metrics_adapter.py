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


def _parse_json_attr(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _status_from_span(span: dict[str, Any]) -> str:
    attrs = span.get("attributes", {})
    status_code = span.get("status", {}).get("status_code")
    if status_code == "ERROR" or attrs.get("error.type"):
        return "ERROR"
    return "SUCCESS"


def build_metrics_payload(payload: dict[str, Any]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []

    spans = sorted(
        _step_spans(payload),
        key=lambda span: _safe_int(
            span.get("attributes", {}).get("experiment.step_index"), 9999
        ),
    )
    for span in spans:
        attrs = span.get("attributes", {})
        rows.append(
            {
                "run_id": payload["run_id"],
                "trace_id": span["trace_id"],
                "task_id": payload.get("task_id", payload["run_id"]),
                "step_number": _safe_int(attrs.get("experiment.step_index")),
                "agent_name": attrs.get("gen_ai.agent.name", span["name"]),
                "operation_type": attrs.get("experiment.operation_type"),
                "operation_name": attrs.get("gen_ai.operation.name", span["name"]),
                "input_message": attrs.get("agent.input_message", ""),
                "output_message": attrs.get("agent.output_message", ""),
                "tool_name": attrs.get("tool.name"),
                "tool_args": _parse_json_attr(attrs.get("tool.args_json"), None),
                "tool_result": _parse_json_attr(attrs.get("tool.result_json"), None),
                "status": _status_from_span(span),
                "error_type": attrs.get("error.type"),
                "error_message": attrs.get("error.message"),
                "duration_ms": span.get("duration_ms"),
                "input_tokens": _safe_int(attrs.get("gen_ai.usage.input_tokens")),
                "output_tokens": _safe_int(attrs.get("gen_ai.usage.output_tokens")),
                "constraint_violations": _parse_json_attr(
                    attrs.get("constraint.violations_json"), []
                ),
                "validation_status": attrs.get("validation.status"),
                "validation_reason": attrs.get("validation.reason"),
            }
        )

    return {
        "schema": "agentrx-otel-observational-metrics-v0",
        "run_id": payload["run_id"],
        "task_id": payload.get("task_id", payload["run_id"]),
        "task": payload["task"],
        "status": payload.get("status"),
        "metrics": rows,
        "totals": {
            "steps": len(rows),
            "errors": sum(1 for row in rows if row["status"] == "ERROR"),
            "input_tokens": sum(row["input_tokens"] for row in rows),
            "output_tokens": sum(row["output_tokens"] for row in rows),
            "duration_ms": sum(float(row["duration_ms"] or 0) for row in rows),
        },
    }


def write_metrics_json(
    payload: dict[str, Any],
    output_path: Path,
    *,
    logger: RunLogger | None = None,
) -> dict[str, Any]:
    if logger:
        logger.info(
            "artifact.write.start",
            "Building metrics payload from OTel spans",
            artifact_kind="metrics_json",
            output_path=output_path,
            spans=len(payload.get("spans", [])),
        )

    metrics_payload = build_metrics_payload(payload)

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        chars_written = output_path.write_text(
            json.dumps(metrics_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        if logger:
            logger.exception(
                "artifact.write.failed",
                "Failed to write metrics JSON",
                artifact_kind="metrics_json",
                output_path=output_path,
            )
        raise

    if logger:
        logger.info(
            "artifact.write.done",
            "Metrics JSON written",
            artifact_kind="metrics_json",
            output_path=output_path,
            rows=len(metrics_payload["metrics"]),
            chars_written=chars_written,
        )

    return metrics_payload
