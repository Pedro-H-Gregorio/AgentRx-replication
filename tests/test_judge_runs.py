"""validate-judge: check on-disk judge experiments (judge-execution spec).

Runs after `make judge`/`make smoke-judge`. Skips when no experiment exists yet
(judging is opt-in and expensive). For each index row: the run dir exists, an
`ok` rep has a valid verdict, no ground truth leaked into the run dir, the index
matches disk, and predicted categories are in the known taxonomy.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentrx_otel_poc.judge.scoring import FAILURE_CASE_NAMES

ROOT = Path(__file__).resolve().parent.parent
DATA_INTERNAL = ROOT / "data" / "internal"
# Predictions carry the FULL taxonomy name (out-of-scope verdicts are named, not
# blank); a legacy index may still hold a scope name (subset) or null.
VALID_CATEGORIES = set(FAILURE_CASE_NAMES.values())
GT_MARKERS = ("fault_mode", "target_fault_category", "critical_failure_step")

# Experiments live at data/internal/<mas_id>/agentrx/<judge_id>/ (ADR-0013).
EXPERIMENTS = (
    [p.parent for p in DATA_INTERNAL.glob("*/agentrx/*/runs_index.jsonl")]
    if DATA_INTERNAL.exists()
    else []
)


def _exp_id(exp_dir: Path) -> str:
    return f"{exp_dir.parent.parent.name}/{exp_dir.name}"  # <mas_id>/<judge_id>


def _rows(exp_dir: Path) -> list[dict]:
    index = exp_dir / "runs_index.jsonl"
    return [json.loads(x) for x in index.read_text(encoding="utf-8").splitlines() if x]


def test_experiments_or_skip() -> None:
    if not EXPERIMENTS:
        pytest.skip("no judge experiment yet — run `make judge` or `make smoke-judge`")


@pytest.mark.parametrize("exp_dir", EXPERIMENTS, ids=_exp_id)
def test_index_matches_disk(exp_dir: Path) -> None:
    rows = _rows(exp_dir)
    rep_dirs = {str(p.relative_to(exp_dir)) for p in exp_dir.glob("*/*/rep*")}
    assert {r["run_dir"] for r in rows} == rep_dirs


@pytest.mark.parametrize("exp_dir", EXPERIMENTS, ids=_exp_id)
def test_rows_are_consistent(exp_dir: Path) -> None:
    for row in _rows(exp_dir):
        run_dir = exp_dir / row["run_dir"]
        assert run_dir.is_dir(), f"missing run dir: {row['run_dir']}"
        if row["status"] == "ok":
            run1 = run_dir / "judge_output" / "runs" / "run1.json"
            json.loads(run1.read_text(encoding="utf-8"))  # valid JSON
        if row.get("predicted_category") is not None:
            assert row["predicted_category"] in VALID_CATEGORIES


@pytest.mark.parametrize("exp_dir", EXPERIMENTS, ids=_exp_id)
def test_no_ground_truth_leaked(exp_dir: Path) -> None:
    for run1 in exp_dir.glob("*/*/rep*/judge_output/runs/run1.json"):
        blob = run1.read_text(encoding="utf-8")
        for marker in GT_MARKERS:
            assert marker not in blob, f"GT marker {marker!r} leaked into {run1}"
