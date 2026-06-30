"""One smoke test per fault category (PRD-03 §6): runs 1 scenario end-to-end."""

from __future__ import annotations

import json

import pytest

from agentrx_otel_poc.adapters.derive import derive_arms
from agentrx_otel_poc.graph.runner import DATA, run_scenario
from agentrx_otel_poc.tasks import (
    NODE_STEP,
    build_ground_truth,
    get_task_spec,
    load_benchmark,
)

# (category, expected injection node, expects a FAILED run)
CASES = [
    ("System Failure", "Tool", True),
    ("Invalid Invocation", "Researcher", True),
    ("Misinterpretation of Tool Output", "Executor", False),
    ("Invention of New Information", "Executor", False),
    ("Instruction/Plan Adherence Failure", "Coordinator", False),
]


def _first_task(category: str) -> str:
    return next(
        t for t, s in load_benchmark().items() if s.target_fault_category == category
    )


def _tool_result(payload: dict) -> dict:
    for span in payload["spans"]:
        attrs = span.get("attributes", {})
        if attrs.get("experiment.step_index") == 3:
            return json.loads(attrs.get("tool.result_json", "{}"))
    return {}


def _fault_nodes(payload: dict) -> list[str]:
    return [
        e["attributes"]["node"]
        for s in payload["spans"]
        for e in s.get("events", [])
        if e["name"] == "fault.injected"
    ]


def _cleanup(run_id: str) -> None:
    (DATA / "otel" / f"{run_id}.otel.json").unlink(missing_ok=True)
    (DATA / "ground_truth" / f"{run_id}.ground_truth.json").unlink(missing_ok=True)
    (DATA / "logs" / f"{run_id}.log").unlink(missing_ok=True)


@pytest.mark.parametrize(
    "category,node,expect_failed", CASES, ids=[c[0] for c in CASES]
)
def test_smoke_fault(category: str, node: str, expect_failed: bool) -> None:
    task_id = _first_task(category)
    run_id = f"{task_id}__smoke"
    payload = run_scenario(task_id, run_id=run_id, inject=True)
    try:
        # fault.injected emitted once, at the expected node
        assert _fault_nodes(payload) == [node]
        # ground truth points to the right step/category
        gt = build_ground_truth(get_task_spec(task_id))
        assert gt["critical_failure_step"] == NODE_STEP[node]
        assert gt["failure_category"] == category
        # both trajectories derive without error
        arm_a, arm_b = derive_arms(payload)
        assert arm_a["steps"] and arm_b["steps"]
        # outcome is FAILED for surface faults
        if expect_failed:
            assert payload["status"] == "FAILED"
        # Executor faults keep the tool output valid (the fault is in the Executor)
        if node == "Executor":
            assert _tool_result(payload).get("ok") is True
    finally:
        _cleanup(run_id)
