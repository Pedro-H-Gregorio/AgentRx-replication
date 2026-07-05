"""Deterministic CSV writing: fixed column order, fixed row sort, stable cells.

The three schemas match PRD-10 exactly. JSON-valued cells are serialized with
sorted keys and no spaces so two runs over the same inputs produce byte-identical
files (the collector's determinism guarantee).
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

RUNS_LONG_COLUMNS = [
    "scenario_id",
    "arm",
    "judge_idx",
    "pred_step",
    "pred_category",
    "pred_category_name",
    "raw_failures_json",
    "agentrx_run_name",
]

TRAJECTORY_INDEX_COLUMNS = [
    "run_id",
    "scenario_id",
    "arm",
    "trajectory_path",
    "otel_path",
    "n_steps",
    "sent_at",
]

METRICAS_COLUMNS = [
    "scenario_id",
    "arm",
    "n_judge_runs",
    "trajectory_length",
    "gt_step",
    "gt_category",
    "gt_category_name",
    "gt_failures_json",
    "gt_earliest_category",
    "gt_terminal_category",
    "most_common_category",
    "most_common_category_name",
    "step_mean",
    "step_median",
    "category_std",
    "step_std",
    "failure_case_accuracy_perrun",
    "step_mae",
    "step_acc_exact",
    "step_acc_tol1",
    "step_acc_tol3",
    "step_acc_tol5",
    "avg_step_distance",
    "avg_step_distance_norm",
    "cat_acc_critical",
    "cat_acc_any",
    "cat_acc_earliest",
    "cat_acc_terminal",
    "judge_model",
    "agentrx_run_name",
]

_SORT_KEYS = {
    "runs_long.csv": ("scenario_id", "arm", "judge_idx"),
    "trajectory_index.csv": ("arm", "run_id"),
    "metricas.csv": ("scenario_id", "arm"),
}
_COLUMNS = {
    "runs_long.csv": RUNS_LONG_COLUMNS,
    "trajectory_index.csv": TRAJECTORY_INDEX_COLUMNS,
    "metricas.csv": METRICAS_COLUMNS,
}


def _cell(value: object) -> object:
    """JSON values → compact sorted-key strings; None → ''; else pass through."""
    if value is None:
        return ""
    if isinstance(value, (list, dict)):
        return json.dumps(value, sort_keys=True, separators=(",", ":"))
    return value


def write_csv(out_dir: Path, name: str, rows: list[dict]) -> Path:
    columns = _COLUMNS[name]
    keys = _SORT_KEYS[name]
    ordered = sorted(rows, key=lambda r: tuple(str(r[k]) for k in keys))
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    for row in ordered:
        writer.writerow({c: _cell(row.get(c)) for c in columns})
    path = out_dir / name
    out_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(buffer.getvalue(), encoding="utf-8")
    return path
