"""Run one scenario end-to-end → raw OTel trace + ground truth (PRD-04/06).

The raw `.otel.json` is the single source of truth; the two trajectories are
derived from it by the adapters. The fault to inject is derived from the
scenario's own target category (scripted injection, deterministic ground truth).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agentrx_otel_poc.faults import CATEGORY_TO_FAULT
from agentrx_otel_poc.runtime_logging import configure_logging
from agentrx_otel_poc.settings import Settings
from agentrx_otel_poc.state import ExperimentState
from agentrx_otel_poc.tasks import (
    build_ground_truth,
    get_task_spec,
    write_ground_truth_json,
)
from agentrx_otel_poc.telemetry import configure_tracer, set_success, write_otel_json

from .builder import build_graph
from .context import GraphContext

DATA = Path(__file__).resolve().parents[3] / "data" / "internal"


def run_scenario(
    task_id: str,
    *,
    settings: Settings | None = None,
    run_id: str | None = None,
    inject: bool = True,
) -> dict[str, Any]:
    settings = settings or Settings()
    spec = get_task_spec(task_id)
    rid = run_id or task_id
    fault_type = CATEGORY_TO_FAULT[spec.target_fault_category] if inject else None
    logger = configure_logging(rid, log_dir=DATA / "logs")
    tracer, exporter, provider = configure_tracer(settings.otel_service_name, rid)
    ctx = GraphContext(settings, spec, tracer, logger, fault_type)
    graph = build_graph(ctx).compile()

    state: ExperimentState = {
        "run_id": rid,
        "task_id": spec.task_id,
        "task": spec.user_request,
        "expected_result": spec.expected_result,
        "success_criteria": spec.success_criteria,
        "tool_name": spec.tool_name,
        "expected_answer": spec.expected_answer,
        "fault_type": fault_type,
        "status": "RUNNING",
        "error": None,
    }
    with tracer.start_as_current_span("run.experiment") as span:
        span.set_attribute("experiment.operation_type", "workflow")
        span.set_attribute("experiment.run_id", rid)
        span.set_attribute("task.id", spec.task_id)
        span.set_attribute("task.domain", spec.domain)
        span.set_attribute("task.input", spec.user_request)
        span.set_attribute("gen_ai.agent.framework", "langgraph")
        final = graph.invoke(state)
        span.set_attribute("run.status", final.get("status", "UNKNOWN"))
        set_success(span)
    provider.force_flush()

    payload = write_otel_json(
        DATA / "otel" / f"{rid}.otel.json",
        run_id=rid,
        task_id=spec.task_id,
        task=spec.user_request,
        task_metadata=spec.to_dict(),
        exporter=exporter,
        ground_truth=None,
        run_status=final.get("status", "SUCCESS"),
        logger=logger.child("telemetry"),
    )
    if inject:
        ground_truth = build_ground_truth(spec)
        write_ground_truth_json(
            ground_truth,
            DATA / "ground_truth" / f"{rid}.ground_truth.json",
            logger=logger.child("ground_truth"),
        )
    return payload
