"""Execution-context observability for cause-step localization."""

from __future__ import annotations

import json

from agentrx_otel_poc import paths
from agentrx_otel_poc.adapters.content_lines import render_prose
from agentrx_otel_poc.adapters.derive import derive_arms
from agentrx_otel_poc.graph.runner import run_scenario
from agentrx_otel_poc.mock_tools import tool_parameters
from agentrx_otel_poc.settings import Settings
from agentrx_otel_poc.tasks import NODE_STEP, load_benchmark

TEST_MAS = "__pytest__"
SETTINGS = Settings(use_llm=False, mas_id=TEST_MAS)
LEAK_TOKENS = (
    "fault.injected",
    "experiment.fault",
    "faults.",
    "System Failure",
    "Invalid Invocation",
    "Misinterpretation of Tool Output",
    "Invention of New Information",
    "Instruction/Plan Adherence Failure",
)


def _first_task(category: str) -> str:
    return next(
        t for t, s in load_benchmark().items() if s.target_fault_category == category
    )


def _first_task_not(category: str) -> str:
    return next(
        t for t, s in load_benchmark().items() if s.target_fault_category != category
    )


def _attrs(payload: dict, step_index: int) -> dict:
    return next(
        span.get("attributes", {})
        for span in payload["spans"]
        if span.get("attributes", {}).get("experiment.step_index") == step_index
    )


def _arm_b_by_index(payload: dict) -> dict[int, str]:
    _, arm_b = derive_arms(payload)
    return {s["index"]: s["substeps"][0]["content"] for s in arm_b["steps"]}


def _cleanup(*run_ids: str) -> None:
    for run_id in run_ids:
        (paths.otel_dir(TEST_MAS) / f"{run_id}.otel.json").unlink(missing_ok=True)
        (paths.ground_truth_dir(TEST_MAS) / f"{run_id}.ground_truth.json").unlink(
            missing_ok=True
        )
        (paths.logs_dir(TEST_MAS) / f"{run_id}.log").unlink(missing_ok=True)
        (paths.manifests_dir(TEST_MAS) / f"{run_id}.json").unlink(missing_ok=True)


def test_tool_contract_is_declared_by_operation() -> None:
    assert tool_parameters("catalog.search") == {
        "product_type": {"type": "string", "required": True}
    }
    assert tool_parameters("catalog.get_details") == {
        "product_id": {"type": "string", "required": True},
        "item_id": {"type": "string", "required": True},
    }


def test_researcher_records_same_tool_contract_with_and_without_fault() -> None:
    task_id = _first_task("Invalid Invocation")
    fault_run = f"{task_id}__ctx_fault"
    clean_run = f"{task_id}__ctx_clean"
    faulted = run_scenario(task_id, settings=SETTINGS, run_id=fault_run, inject=True)
    clean = run_scenario(task_id, settings=SETTINGS, run_id=clean_run, inject=False)
    try:
        fault_contract = json.loads(_attrs(faulted, 2)["gen_ai.tool.parameters"])
        clean_contract = json.loads(_attrs(clean, 2)["gen_ai.tool.parameters"])
        assert fault_contract == clean_contract
        assert fault_contract == tool_parameters(
            load_benchmark()[task_id].tool_operation
        )
    finally:
        _cleanup(fault_run, clean_run)


def test_coordinator_records_plan_query_for_plan_and_non_plan_runs() -> None:
    plan_task = _first_task("Instruction/Plan Adherence Failure")
    other_task = _first_task_not("Instruction/Plan Adherence Failure")
    plan_fault_run = f"{plan_task}__ctx_plan_fault"
    plan_clean_run = f"{plan_task}__ctx_plan_clean"
    other_fault_run = f"{other_task}__ctx_other_fault"
    other_clean_run = f"{other_task}__ctx_other_clean"
    plan_faulted = run_scenario(
        plan_task, settings=SETTINGS, run_id=plan_fault_run, inject=True
    )
    plan_clean = run_scenario(
        plan_task, settings=SETTINGS, run_id=plan_clean_run, inject=False
    )
    other_faulted = run_scenario(
        other_task, settings=SETTINGS, run_id=other_fault_run, inject=True
    )
    other_clean = run_scenario(
        other_task, settings=SETTINGS, run_id=other_clean_run, inject=False
    )
    try:
        plan_fault_query = json.loads(_attrs(plan_faulted, 1)["plan.query_json"])
        plan_clean_query = json.loads(_attrs(plan_clean, 1)["plan.query_json"])
        other_fault_query = json.loads(_attrs(other_faulted, 1)["plan.query_json"])
        other_clean_query = json.loads(_attrs(other_clean, 1)["plan.query_json"])
        assert plan_fault_query != plan_clean_query
        assert other_fault_query == other_clean_query
        assert _attrs(plan_faulted, 1)["plan.text"]
    finally:
        _cleanup(plan_fault_run, plan_clean_run, other_fault_run, other_clean_run)


def test_new_execution_context_reaches_both_trajectory_arms_without_leaks() -> None:
    task_id = _first_task("Invalid Invocation")
    run_id = f"{task_id}__ctx_arms"
    payload = run_scenario(task_id, settings=SETTINGS, run_id=run_id, inject=True)
    try:
        arm_a, arm_b = derive_arms(payload)
        step1_a = json.loads(arm_a["steps"][0]["substeps"][0]["content"])
        step2_a = json.loads(arm_a["steps"][1]["substeps"][0]["content"])
        step1_b = arm_b["steps"][0]["substeps"][0]["content"]
        step2_b = arm_b["steps"][1]["substeps"][0]["content"]
        assert "plan_query" in step1_a
        assert "plan" in step1_a
        assert "tool_parameters" in step2_a
        assert "Plan query:" in step1_b
        assert "Plan:" in step1_b
        assert "Tool parameters:" in step2_b
        for json_step, prose_step in zip(arm_a["steps"], arm_b["steps"]):
            facts = json.loads(json_step["substeps"][0]["content"])
            facts.pop("telemetry")
            assert (
                "\n".join(render_prose(facts)) == prose_step["substeps"][0]["content"]
            )
        combined = json.dumps((arm_a, arm_b), ensure_ascii=False)
        for token in LEAK_TOKENS:
            assert token not in combined
    finally:
        _cleanup(run_id)


def test_unaffected_steps_remain_identical_with_new_context_fields() -> None:
    benchmark = load_benchmark()
    task_id = _first_task("Misinterpretation of Tool Output")
    injection_step = NODE_STEP[benchmark[task_id].injection_node]
    fault_run = f"{task_id}__ctx_r5_fault"
    clean_run = f"{task_id}__ctx_r5_clean"
    faulted = run_scenario(task_id, settings=SETTINGS, run_id=fault_run, inject=True)
    clean = run_scenario(task_id, settings=SETTINGS, run_id=clean_run, inject=False)
    try:
        with_fault = _arm_b_by_index(faulted)
        without_fault = _arm_b_by_index(clean)
        for index, content in with_fault.items():
            if index < injection_step:
                assert content == without_fault[index], (
                    f"pre-injection step {index} differs"
                )
        assert with_fault[injection_step] != without_fault[injection_step]
    finally:
        _cleanup(fault_run, clean_run)


def test_executor_no_longer_records_empty_reasoning_summary() -> None:
    task_id = _first_task("System Failure")
    run_id = f"{task_id}__ctx_reasoning"
    payload = run_scenario(task_id, settings=SETTINGS, run_id=run_id, inject=True)
    try:
        for span in payload["spans"]:
            assert "agent.reasoning_summary" not in span.get("attributes", {})
    finally:
        _cleanup(run_id)
