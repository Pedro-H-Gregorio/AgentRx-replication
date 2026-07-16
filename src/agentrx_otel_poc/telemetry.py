from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Sequence

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import (
    SimpleSpanProcessor,
    SpanExporter,
    SpanExportResult,
)
from opentelemetry.trace import Status, StatusCode

from agentrx_otel_poc.runtime_logging import RunLogger


class InMemoryJsonSpanExporter(SpanExporter):
    def __init__(self) -> None:
        self.spans: list[ReadableSpan] = []

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        self.spans.extend(spans)
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        return None

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True


def configure_tracer(
    service_name: str, run_id: str
) -> tuple[trace.Tracer, InMemoryJsonSpanExporter, TracerProvider]:
    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": "0.1.0",
            "deployment.environment.name": "experiment",
            "experiment.run_id": run_id,
        }
    )
    provider = TracerProvider(resource=resource)
    exporter = InMemoryJsonSpanExporter()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    # Use a provider-bound tracer (not the global one): the global TracerProvider
    # can only be set once per process, but we run many scenarios in one process.
    return provider.get_tracer("agentrx_otel_poc"), exporter, provider


def set_success(span: trace.Span) -> None:
    span.set_status(Status(StatusCode.OK))


def set_error(span: trace.Span, exc: Exception) -> None:
    span.record_exception(exc)
    span.set_status(Status(StatusCode.ERROR, str(exc)))
    span.set_attribute("error.type", exc.__class__.__name__)
    span.set_attribute("error.message", str(exc))


def add_step(
    span: trace.Span, step_index: int, agent_name: str, operation: str
) -> None:
    span.set_attribute("experiment.step_index", step_index)
    span.set_attribute("gen_ai.agent.name", agent_name)
    span.set_attribute("gen_ai.operation.name", operation)


def serialize_span(span: ReadableSpan) -> dict[str, Any]:
    ctx = span.get_span_context()
    parent = span.parent
    duration_ms = (
        (span.end_time - span.start_time) / 1_000_000 if span.end_time else None
    )

    attrs = dict(span.attributes or {})
    events = []
    for event in span.events:
        events.append(
            {
                "name": event.name,
                "timestamp_unix_ns": event.timestamp,
                "attributes": dict(event.attributes or {}),
            }
        )

    return {
        "name": span.name,
        "trace_id": f"{ctx.trace_id:032x}",
        "span_id": f"{ctx.span_id:016x}",
        "parent_span_id": f"{parent.span_id:016x}" if parent else None,
        "kind": span.kind.name,
        "start_time_unix_ns": span.start_time,
        "end_time_unix_ns": span.end_time,
        "duration_ms": duration_ms,
        "status": {
            "status_code": span.status.status_code.name,
            "description": span.status.description,
        },
        "attributes": attrs,
        "events": events,
    }


def write_otel_json(
    path: Path,
    *,
    run_id: str,
    task_id: str,
    task: str,
    task_metadata: dict[str, Any] | None,
    exporter: InMemoryJsonSpanExporter,
    ground_truth: dict[str, Any] | None,
    run_status: str,
    logger: RunLogger | None = None,
) -> dict[str, Any]:
    # Serialize closed spans in step order for deterministic trace output.
    serialized = [serialize_span(s) for s in exporter.spans]
    serialized.sort(
        key=lambda s: int(s["attributes"].get("experiment.step_index", 9999))
    )

    if logger:
        logger.info(
            "artifact.write.start",
            "Building OTel JSON payload",
            artifact_kind="otel_json",
            output_path=path,
            spans=len(serialized),
            run_status=run_status,
        )

    payload = {
        "schema": "otel-json-local-v0",
        "run_id": run_id,
        "task_id": task_id,
        "task": task,
        "task_metadata": task_metadata,
        "created_at_unix_ms": int(time.time() * 1000),
        "status": run_status,
        "spans": serialized,
    }
    if ground_truth:
        payload["ground_truth"] = ground_truth

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        chars_written = path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        if logger:
            logger.exception(
                "artifact.write.failed",
                "Failed to write OTel JSON",
                artifact_kind="otel_json",
                output_path=path,
            )
        raise

    if logger:
        logger.info(
            "artifact.write.done",
            "OTel JSON written",
            artifact_kind="otel_json",
            output_path=path,
            spans=len(serialized),
            chars_written=chars_written,
            run_status=run_status,
        )

    return payload
