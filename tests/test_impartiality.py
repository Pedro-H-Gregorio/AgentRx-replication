"""R5 impartiality: category-blind renderer (static) + template invariance (dynamic).

The static test (source-level renderer blindness) is the always-valid weak guard.
The dynamic byte-equality test presupposes the deterministic agent, so it is gated
on `USE_LLM`: with `USE_LLM=true` the prose is LLM-generated and not byte-stable,
so it skips and the static guard carries R5 (PRD-08 D31).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from agentrx_otel_poc.adapters.derive import derive_arms
from agentrx_otel_poc.graph.runner import DATA, run_scenario
from agentrx_otel_poc.settings import Settings
from agentrx_otel_poc.tasks import NODE_STEP, load_benchmark

ROOT = Path(__file__).resolve().parent.parent
SPANS_SRC = ROOT / "src" / "agentrx_otel_poc" / "graph" / "spans.py"
NODES_DIR = ROOT / "src" / "agentrx_otel_poc" / "graph" / "nodes"


def test_renderer_is_category_blind_static() -> None:
    # The renderer/nodes must never *access* the ground-truth attributes (docstrings
    # may mention them); we forbid the attribute-access form.
    sources = [SPANS_SRC.read_text(encoding="utf-8")]
    sources += [p.read_text(encoding="utf-8") for p in NODES_DIR.glob("*.py")]
    for src in sources:
        assert ".target_fault_category" not in src
        assert ".injection_node" not in src


def _arm_b_by_index(payload: dict) -> dict[int, str]:
    _, arm_b = derive_arms(payload)
    return {s["index"]: s["substeps"][0]["content"] for s in arm_b["steps"]}


def _cleanup(run_id: str) -> None:
    (DATA / "otel" / f"{run_id}.otel.json").unlink(missing_ok=True)
    (DATA / "ground_truth" / f"{run_id}.ground_truth.json").unlink(missing_ok=True)
    (DATA / "logs" / f"{run_id}.log").unlink(missing_ok=True)
    (DATA / "manifests" / f"{run_id}.json").unlink(missing_ok=True)


@pytest.mark.skipif(
    Settings().use_llm,
    reason="strong byte-equality needs the deterministic agent; with USE_LLM=true "
    "the weak static renderer-blindness test guards R5 (PRD-08 D31)",
)
def test_unaffected_steps_identical_with_and_without_fault() -> None:
    benchmark = load_benchmark()
    task_id = next(
        t
        for t, s in benchmark.items()
        if s.target_fault_category == "Misinterpretation of Tool Output"
    )
    injection_step = NODE_STEP[benchmark[task_id].injection_node]
    faulted = run_scenario(task_id, run_id=f"{task_id}__rf", inject=True)
    clean = run_scenario(task_id, run_id=f"{task_id}__rc", inject=False)
    try:
        with_fault = _arm_b_by_index(faulted)
        without_fault = _arm_b_by_index(clean)
        # Steps BEFORE the injection cannot be affected → must be byte-identical
        # (proves no step anticipates/markets the targeted category). The injected
        # step itself must differ; downstream steps legitimately consume its output.
        for index, content in with_fault.items():
            if index < injection_step:
                assert content == without_fault[index], (
                    f"pre-injection step {index} differs"
                )
        assert with_fault[injection_step] != without_fault[injection_step]
    finally:
        _cleanup(f"{task_id}__rf")
        _cleanup(f"{task_id}__rc")
