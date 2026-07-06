"""Weak R5 test for USE_LLM=true: no category markers leak into the trajectories.

Uses a deterministic stub agent (no network) so the test is reproducible. Proves
the LLM path runs (tokens > 0) yet the derived trajectories contain no term that
would betray the targeted fault category.
"""

from __future__ import annotations

import json

import pytest

from agentrx_otel_poc import paths
from agentrx_otel_poc.adapters.derive import derive_arms
from agentrx_otel_poc.graph import runner
from agentrx_otel_poc.settings import Settings
from agentrx_otel_poc.tasks import load_benchmark

TEST_MAS = "__pytest__"  # isolated corpus — never touches a real MAS corpus

FORBIDDEN = {
    "System Failure": ["system failure", "injected fault"],
    "Invalid Invocation": ["invalid invocation", "malformed by"],
    "Misinterpretation of Tool Output": ["misinterpret", "misread"],
    "Invention of New Information": ["invention", "fabricat", "hallucinat"],
    "Instruction/Plan Adherence Failure": ["plan adherence", "violated constraint"],
}


def _stub_agent(settings, prompt, *, logger=None):
    return "The agent processed the step.", {
        "input_tokens": 5,
        "output_tokens": 5,
        "total_tokens": 10,
    }


def _cleanup(run_id: str) -> None:
    (paths.otel_dir(TEST_MAS) / f"{run_id}.otel.json").unlink(missing_ok=True)
    (paths.ground_truth_dir(TEST_MAS) / f"{run_id}.ground_truth.json").unlink(
        missing_ok=True
    )
    (paths.logs_dir(TEST_MAS) / f"{run_id}.log").unlink(missing_ok=True)
    (paths.manifests_dir(TEST_MAS) / f"{run_id}.json").unlink(missing_ok=True)


@pytest.mark.parametrize("category", list(FORBIDDEN), ids=list(FORBIDDEN))
def test_no_category_markers_with_llm(monkeypatch, category: str) -> None:
    monkeypatch.setattr("agentrx_otel_poc.graph.agent_llm.invoke_agent", _stub_agent)
    task_id = next(
        t for t, s in load_benchmark().items() if s.target_fault_category == category
    )
    run_id = f"{task_id}__r5w"
    payload = runner.run_scenario(
        task_id,
        settings=Settings(use_llm=True, mas_id=TEST_MAS),
        run_id=run_id,
        inject=True,
    )
    try:
        arm_a, arm_b = derive_arms(payload)
        blob = (json.dumps(arm_a) + json.dumps(arm_b)).lower()
        for term in FORBIDDEN[category]:
            assert term not in blob, f"{category}: '{term}' leaked with USE_LLM=true"
        # the LLM path actually ran (real token usage recorded)
        assert any(
            s["attributes"].get("gen_ai.usage.total_tokens", 0) > 0
            for s in payload["spans"]
        )
    finally:
        _cleanup(run_id)
