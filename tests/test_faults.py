"""Unit checks for the fault operators (selection, no-op, model-independence)."""

from __future__ import annotations


from agentrx_otel_poc.faults import CATEGORY_TO_FAULT, for_node, select
from agentrx_otel_poc.settings import Settings
from agentrx_otel_poc.tasks import build_ground_truth, get_task_spec, load_benchmark


def _first(category: str) -> str:
    return next(
        tid
        for tid, s in load_benchmark().items()
        if s.target_fault_category == category
    )


def test_every_category_has_an_operator() -> None:
    for category, fault_type in CATEGORY_TO_FAULT.items():
        operator = select(fault_type)
        assert operator is not None
        assert operator.category == category


def test_operator_is_no_op_outside_target_node() -> None:
    operator = select("plan_adherence")  # targets Coordinator
    assert for_node("plan_adherence", "Coordinator") is operator
    assert for_node("plan_adherence", "Tool") is None
    assert select("") is None


def test_ground_truth_independent_of_agent_model() -> None:
    spec = get_task_spec(_first("System Failure"))
    gt_a = build_ground_truth(spec)
    gt_b = build_ground_truth(spec)
    # The localization ground truth is by construction (no model in the inputs).
    assert gt_a == gt_b
    assert Settings(agent_model="A") != Settings(agent_model="B")
    assert gt_a["failure_category"] == "System Failure"
    assert gt_a["fault_mode"] == CATEGORY_TO_FAULT["System Failure"]
