"""CSV integrity = `make validate-csv` (metrics-collection spec, PRD-10).

Runs over whatever experiments exist under `data/experiment/results/`; skips
when none (collecting is opt-in). For each experiment: the three CSVs join on
(scenario_id, arm) without orphans; bool01/accuracy/category ranges hold;
`avg_step_distance_norm` uses the index `n_steps`; and every `metricas` row
reconstructs from the `runs_long` rows of the same pair by re-pooling
`raw_failures_json` (independent of the collector code).
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from statistics import mean

import pytest

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "data" / "experiment" / "results"
EXPERIMENTS = (
    [p.parent for p in RESULTS.glob("*/*/metricas.csv")] if RESULTS.exists() else []
)


def _exp_id(exp_dir: Path) -> str:
    return f"{exp_dir.parent.name}/{exp_dir.name}"


BOOL01 = (
    "step_acc_exact",
    "step_acc_tol1",
    "step_acc_tol3",
    "step_acc_tol5",
    "cat_acc_critical",
    "cat_acc_any",
    "cat_acc_earliest",
    "cat_acc_terminal",
)


def _read(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_experiments_or_skip() -> None:
    if not EXPERIMENTS:
        pytest.skip("no CSVs yet — run `make collect`")


@pytest.mark.parametrize("exp", EXPERIMENTS, ids=_exp_id)
def test_join_without_orphans(exp: Path) -> None:
    metric = {(r["scenario_id"], r["arm"]) for r in _read(exp / "metricas.csv")}
    index = {(r["scenario_id"], r["arm"]) for r in _read(exp / "trajectory_index.csv")}
    longk = {(r["scenario_id"], r["arm"]) for r in _read(exp / "runs_long.csv")}
    assert metric == index, "metricas vs trajectory_index pairs differ"
    assert longk <= metric, "runs_long has a pair absent from metricas"


@pytest.mark.parametrize("exp", EXPERIMENTS, ids=_exp_id)
def test_ranges(exp: Path) -> None:
    for row in _read(exp / "metricas.csv"):
        for col in BOOL01:
            assert row[col] in {"0", "1"}, f"{col}={row[col]!r}"
        assert 0.0 <= float(row["failure_case_accuracy_perrun"]) <= 1.0
        assert 1 <= int(row["gt_category"]) <= 10
        assert 0 <= int(row["most_common_category"]) <= 10


@pytest.mark.parametrize("exp", EXPERIMENTS, ids=_exp_id)
def test_norm_uses_index_n_steps(exp: Path) -> None:
    n_steps = {
        (r["scenario_id"], r["arm"]): int(r["n_steps"])
        for r in _read(exp / "trajectory_index.csv")
    }
    for row in _read(exp / "metricas.csv"):
        length = n_steps[(row["scenario_id"], row["arm"])]
        assert int(row["trajectory_length"]) == length
        expected = float(row["avg_step_distance"]) / length
        assert float(row["avg_step_distance_norm"]) == pytest.approx(expected, abs=1e-6)


@pytest.mark.parametrize("exp", EXPERIMENTS, ids=_exp_id)
def test_metricas_reconstructs_from_runs_long(exp: Path) -> None:
    pools: dict[tuple[str, str], list[tuple[int, int]]] = {}
    for row in _read(exp / "runs_long.csv"):
        key = (row["scenario_id"], row["arm"])
        for f in json.loads(row["raw_failures_json"]):
            pools.setdefault(key, []).append((f["case"], f["step"]))
    for row in _read(exp / "metricas.csv"):
        pool = pools[(row["scenario_id"], row["arm"])]
        cases = [c for c, _ in pool]
        steps = [s for _, s in pool]
        assert Counter(cases).most_common(1)[0][0] == int(row["most_common_category"])
        assert mean(steps) == pytest.approx(float(row["step_mean"]), abs=1e-6)
