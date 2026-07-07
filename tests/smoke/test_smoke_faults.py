"""One smoke test per fault category (PRD-03 §6): runs 1 scenario end-to-end."""

from __future__ import annotations

import json

import pytest

from agentrx_otel_poc import paths
from agentrx_otel_poc.adapters.derive import derive_arms
from agentrx_otel_poc.graph.runner import run_scenario
from agentrx_otel_poc.mock_tools import tool_parameters
from agentrx_otel_poc.settings import Settings
from agentrx_otel_poc.tasks import (
    NODE_STEP,
    build_ground_truth,
    get_task_spec,
    load_benchmark,
)

TEST_MAS = "__pytest__"  # isolated corpus — never touches a real MAS corpus
SETTINGS = Settings(use_llm=False, mas_id=TEST_MAS)

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


def _step_attr(payload: dict, index: int, attr: str) -> str:
    for span in payload["spans"]:
        attrs = span.get("attributes", {})
        if attrs.get("experiment.step_index") == index:
            return str(attrs.get(attr, ""))
    return ""


def _step_content(ir: dict, index: int) -> str:
    step = next(s for s in ir["steps"] if s["index"] == index)
    return step["substeps"][0]["content"]


def _exception_trace(payload: dict) -> tuple[str, str]:
    """Return (exception.type, exception.stacktrace) from the raw error span."""
    for span in payload["spans"]:
        for event in span.get("events", []):
            if event["name"] == "exception":
                attrs = event.get("attributes", {})
                return (
                    str(attrs.get("exception.type", "")),
                    str(attrs.get("exception.stacktrace", "")),
                )
    return "", ""


def _cleanup(run_id: str) -> None:
    (paths.otel_dir(TEST_MAS) / f"{run_id}.otel.json").unlink(missing_ok=True)
    (paths.ground_truth_dir(TEST_MAS) / f"{run_id}.ground_truth.json").unlink(
        missing_ok=True
    )
    (paths.logs_dir(TEST_MAS) / f"{run_id}.log").unlink(missing_ok=True)
    (paths.manifests_dir(TEST_MAS) / f"{run_id}.json").unlink(missing_ok=True)


@pytest.mark.parametrize(
    "category,node,expect_failed", CASES, ids=[c[0] for c in CASES]
)
def test_smoke_fault(category: str, node: str, expect_failed: bool) -> None:
    task_id = _first_task(category)
    run_id = f"{task_id}__smoke"
    payload = run_scenario(task_id, settings=SETTINGS, run_id=run_id, inject=True)
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
        # arm A content is a JSON string with a telemetry block; arm B stays prose
        a0 = json.loads(arm_a["steps"][0]["substeps"][0]["content"])
        assert "telemetry" in a0
        assert not arm_b["steps"][0]["substeps"][0]["content"].lstrip().startswith("{")
        # execution context is present at the cause-step boundary in raw OTel
        # and is surfaced as semantic content in both arms.
        step1_json = json.loads(_step_content(arm_a, 1))
        step2_json = json.loads(_step_content(arm_a, 2))
        step1_prose = _step_content(arm_b, 1)
        step2_prose = _step_content(arm_b, 2)
        assert json.loads(_step_attr(payload, 1, "plan.query_json"))
        assert _step_attr(payload, 1, "plan.text")
        assert json.loads(_step_attr(payload, 2, "gen_ai.tool.parameters")) == (
            tool_parameters(get_task_spec(task_id).tool_operation)
        )
        assert "plan_query" in step1_json
        assert "plan" in step1_json
        assert "tool_parameters" in step2_json
        assert "Plan query:" in step1_prose
        assert "Plan:" in step1_prose
        assert "Tool parameters:" in step2_prose
        # outcome is FAILED for surface faults
        if expect_failed:
            assert payload["status"] == "FAILED"
        # Executor faults keep the tool output valid (the fault is in the Executor)
        if node == "Executor":
            assert _tool_result(payload).get("ok") is True
        answer = _step_attr(payload, 4, "agent.output_message")
        # Invention fabricates ungrounded info (cites a non-existent record);
        # Misinterpretation mis-reads valid evidence and never invents a record id.
        if category == "Invention of New Information":
            assert "0000000000" in answer
        if category == "Misinterpretation of Tool Output":
            assert "0000000000" not in answer
        # Plan Adherence must actually violate the query (args != default).
        if category == "Instruction/Plan Adherence Failure":
            args = json.loads(_step_attr(payload, 3, "tool.args_json") or "{}")
            assert args != dict(get_task_spec(task_id).default_tool_args)
    finally:
        _cleanup(run_id)


def test_system_failure_stacktrace_is_clean_at_source() -> None:
    """2A: the raw OTel stacktrace names only application frames, never the
    injection code or the category — so no leak reaches the derivation step."""
    task_id = _first_task("System Failure")
    run_id = f"{task_id}__stacktrace"
    payload = run_scenario(task_id, settings=SETTINGS, run_id=run_id, inject=True)
    try:
        etype, trace = _exception_trace(payload)
        assert trace, "System Failure must record an exception stacktrace"
        for token in ("faults", "operators.py", "_system_failure", "maybe_raise"):
            assert token not in trace and token not in etype, (
                f"leak token {token!r} in raw stacktrace"
            )
        assert "System Failure" not in trace  # never names the category
    finally:
        _cleanup(run_id)


def test_arm_a_stacktrace_present_and_normalized() -> None:
    """GAP-1/GAP-2: arm A surfaces the stacktrace, normalized to a machine-agnostic,
    experiment-neutral form (relative `src/` path, bare exception header); arm B has
    none."""
    task_id = _first_task("System Failure")
    run_id = f"{task_id}__norm"
    payload = run_scenario(task_id, settings=SETTINGS, run_id=run_id, inject=True)
    try:
        arm_a, arm_b = derive_arms(payload)
        step3 = next(s for s in arm_a["steps"] if s["index"] == 3)
        telemetry = json.loads(step3["substeps"][0]["content"])["telemetry"]
        trace = telemetry.get("stacktrace")
        assert trace, "arm A error step must carry a stacktrace"
        # normalized: no absolute machine path, no experiment-context or mock hints
        for hint in ("/home/", "replicacao-agentrx", "mestrado", "mock_tools"):
            assert hint not in trace, f"un-normalized stacktrace still has {hint!r}"
        assert 'File "src/' in trace  # relative frame path kept
        # arm B never carries a stacktrace
        for step in arm_b["steps"]:
            assert "Traceback" not in step["substeps"][0]["content"]
    finally:
        _cleanup(run_id)
