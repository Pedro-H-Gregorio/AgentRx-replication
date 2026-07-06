"""Collector golden + determinism + neutrality (metrics-collection spec).

The golden fixture (`tests/fixtures/golden/`) is self-contained: its own
trajectory + ground truth + a 3-rep experiment (rep3 multi-failure). The expected
CSVs are cross-checked against the hand-computed lines in
`docs/examples/metrics-reference.md` (GAP-3: the frozen expected must agree with
an oracle independent of the collector, not just a capture of a past run).

Also proves byte-determinism, that a `skipped` rep (a valid verdict from an
earlier idempotent judge run) is pooled like `ok` (GAP-1), that an `error` rep
lowers `n_judge_runs` without dropping the row, and that `judge_model` follows
the reps' `effective_model` with a manifest fallback (GAP-2).
"""

from __future__ import annotations

import json
from pathlib import Path

from agentrx_otel_poc.collect.aggregate import (
    metricas_row,
    runs_long_rows,
    trajectory_index_row,
)
from agentrx_otel_poc.collect.csv_writer import TRAJECTORY_INDEX_COLUMNS, write_csv
from agentrx_otel_poc.collect.reader import PairData, RepData, load_experiment

GOLDEN = Path(__file__).parent / "fixtures" / "golden"
EXP = GOLDEN / "experiment"
DATA_INTERNAL = GOLDEN / "data_internal"
EXPECTED = GOLDEN / "expected"
REFERENCE_DOC = (
    Path(__file__).parent.parent / "docs" / "examples" / "metrics-reference.md"
)


def test_golden_runs_long(tmp_path) -> None:
    pairs = load_experiment(EXP, DATA_INTERNAL)
    rows = [r for p in pairs for r in runs_long_rows(p)]
    got = write_csv(tmp_path, "runs_long.csv", rows).read_text(encoding="utf-8")
    assert got == (EXPECTED / "runs_long.csv").read_text(encoding="utf-8")


def test_golden_metricas(tmp_path) -> None:
    pairs = load_experiment(EXP, DATA_INTERNAL)
    rows = [metricas_row(p) for p in pairs]
    got = write_csv(tmp_path, "metricas.csv", rows).read_text(encoding="utf-8")
    assert got == (EXPECTED / "metricas.csv").read_text(encoding="utf-8")


def test_expected_matches_reference_doc() -> None:
    """Every hand-computed data line in the doc must appear in the frozen expected
    CSVs — the independent oracle that breaks the golden's self-reference (GAP-3)."""
    doc_lines = [
        ln
        for ln in REFERENCE_DOC.read_text(encoding="utf-8").splitlines()
        if ln.startswith("gold01,")
    ]
    assert len(doc_lines) == 4  # 3 runs_long rows + 1 metricas row
    frozen = (EXPECTED / "runs_long.csv").read_text(encoding="utf-8") + (
        EXPECTED / "metricas.csv"
    ).read_text(encoding="utf-8")
    for line in doc_lines:
        assert line in frozen, f"doc line not reproduced in expected CSV:\n{line}"


def test_golden_trajectory_index_minus_sent_at() -> None:
    pairs = load_experiment(EXP, DATA_INTERNAL)
    row = trajectory_index_row(pairs[0])
    assert row["run_id"] == "gold01"
    assert row["scenario_id"] == "gold01"
    assert row["arm"] == "telemetry"
    # paths carry the corpus namespace (the fixture's data_internal dir name).
    mas = DATA_INTERNAL.name
    assert (
        row["trajectory_path"]
        == f"data/internal/{mas}/trajectory_telemetry/gold01.json"
    )
    assert row["otel_path"] == f"data/internal/{mas}/otel/gold01.otel.json"
    assert row["n_steps"] == 5
    # sent_at is an mtime (stable per artifact set, not a hand-frozen value)
    assert set(TRAJECTORY_INDEX_COLUMNS) == set(row)


def test_determinism_byte_identical(tmp_path) -> None:
    pairs = load_experiment(EXP, DATA_INTERNAL)
    rows = [metricas_row(p) for p in pairs]
    a = write_csv(tmp_path / "a", "metricas.csv", rows).read_bytes()
    b = write_csv(tmp_path / "b", "metricas.csv", rows).read_bytes()
    assert a == b


def _plant(dest: Path, reps: list[tuple[int, str, str | None]], model: str) -> None:
    """Plant a gold01/telemetry experiment. reps = [(rep, status, effective_model)];
    a run1.json is written for every verdict status (`ok`/`skipped`)."""
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "manifest.json").write_text(
        json.dumps({"judge_model": model}), encoding="utf-8"
    )
    index = [
        {
            "run_id": "gold01",
            "arm": "telemetry",
            "rep": rep,
            "status": status,
            "run_dir": f"telemetry/gold01/rep{rep}",
            "effective_model": eff,
        }
        for rep, status, eff in reps
    ]
    (dest / "runs_index.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in index), encoding="utf-8"
    )
    for rep, status, _ in reps:
        if status not in {"ok", "skipped"}:
            continue
        runs = dest / "telemetry" / "gold01" / f"rep{rep}" / "judge_output" / "runs"
        runs.mkdir(parents=True, exist_ok=True)
        (runs / "run1.json").write_text(
            json.dumps(
                {
                    "detailed_results": [
                        {
                            "task_id": "gold01",
                            "failures": [
                                {
                                    "task_id": "gold01",
                                    "failure_case": 3,
                                    "step_number": 2,
                                }
                            ],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )


def test_skipped_rep_is_pooled_like_ok(tmp_path) -> None:
    # GAP-1: an idempotent judge rerun labels prior valid reps `skipped`; they must
    # still count. 1 ok + 2 skipped → all three pooled.
    exp = tmp_path / "judge-skip"
    _plant(exp, [(1, "ok", None), (2, "skipped", None), (3, "skipped", None)], "m")
    pairs = load_experiment(exp, DATA_INTERNAL)
    assert len(pairs) == 1
    assert metricas_row(pairs[0])["n_judge_runs"] == 3
    assert pairs[0].n_error_reps == 0


def test_error_rep_reduces_n_without_dropping(tmp_path) -> None:
    exp = tmp_path / "judge-golden-err"
    _plant(exp, [(1, "ok", None), (2, "ok", None), (3, "error", None)], "golden-judge")
    pairs = load_experiment(exp, DATA_INTERNAL)
    assert len(pairs) == 1
    assert metricas_row(pairs[0])["n_judge_runs"] == 2  # error excluded from pool
    assert pairs[0].n_error_reps == 1  # but counted, not silently dropped


def test_judge_model_prefers_effective_model(tmp_path) -> None:
    # GAP-2: manifest JUDGE_MODEL empty (backend picked the model server-side);
    # judge_model must come from the reps' effective_model, not the empty manifest.
    exp = tmp_path / "judge-eff"
    _plant(exp, [(1, "ok", "gpt-5.5"), (2, "ok", "gpt-5.5")], "")
    pairs = load_experiment(exp, DATA_INTERNAL)
    assert metricas_row(pairs[0])["judge_model"] == "gpt-5.5"


def test_out_of_scope_prediction_is_named_in_csvs() -> None:
    # A verdict outside the 5 injectable categories (5 = Intent-Plan Misalignment)
    # carries its full name in both CSVs instead of a blank, and still counts as a
    # category miss (int-based comparison).
    pair = PairData(
        run_id="q99",
        arm="telemetry",
        n_steps=5,
        ground_truth={"failure_category": "System Failure", "critical_failure_step": 3},
        judge_model="m",
    )
    pair.reps = [RepData(1, "telemetry/q99/rep1", [(5, 2)], None, 0.0)]
    long = runs_long_rows(pair)[0]
    assert long["pred_category"] == 5
    assert long["pred_category_name"] == "Intent-Plan Misalignment"
    metric = metricas_row(pair)
    assert metric["most_common_category"] == 5
    assert metric["most_common_category_name"] == "Intent-Plan Misalignment"
    assert metric["cat_acc_critical"] == 0  # out of scope → miss
