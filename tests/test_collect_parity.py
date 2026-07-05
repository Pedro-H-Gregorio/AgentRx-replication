"""Numeric parity vs AgentRx `compute_stats`/`analysis()` (metrics-collection spec).

Reads the versioned fixture generated once from the submodule (see
`tests/fixtures/parity/generate_parity_fixtures.py`) and checks the collector's
re-implementation reproduces it. Runs fully offline — `agentrx` is NOT imported
here (regra 6). Covers 1 failure/rep, multi-failure pooling, mode tie, and
categories outside the five injectable ones.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentrx_otel_poc.collect.aggregate import metricas_row
from agentrx_otel_poc.collect.categories import name_of
from agentrx_otel_poc.collect.reader import PairData, RepData

FIXTURE = Path(__file__).parent / "fixtures" / "parity" / "compute_stats_cases.json"
CASES = json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"]


def _pair(case: dict) -> PairData:
    failures = [(c, s) for c, s in case["failures"]]
    pair = PairData(
        run_id="t",
        arm="telemetry",
        n_steps=case["trajectory_length"],
        ground_truth={
            "failure_category": name_of(case["gt_case"]),
            "critical_failure_step": case["gt_step"],
        },
    )
    pair.reps = [RepData(1, "x", failures, None, 0.0)]
    return pair


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_aggregate_matches_agentrx(case: dict) -> None:
    row = metricas_row(_pair(case))
    exp = case["expected"]
    assert row["most_common_category"] == exp["most_common_failure"]
    for ours, theirs in [
        ("step_mean", "step_mean"),
        ("step_median", "step_median"),
        ("category_std", "category_std"),
        ("step_std", "step_std"),
        ("failure_case_accuracy_perrun", "failure_case_accuracy"),
        ("step_mae", "step_mae"),
        ("avg_step_distance", "avg_step_distance"),
        ("avg_step_distance_norm", "avg_step_distance_norm"),
    ]:
        assert row[ours] == pytest.approx(exp[theirs], abs=1e-6), ours
    for field in ("step_acc_exact", "step_acc_tol1", "step_acc_tol3", "step_acc_tol5"):
        assert row[field] == exp[field], field
    # analysis() category rule: most_common == gt (str compare on the int value)
    assert row["cat_acc_critical"] == int(exp["most_common_failure"] == case["gt_case"])
