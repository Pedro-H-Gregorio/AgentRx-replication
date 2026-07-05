"""Collect one or all judge experiments on disk into the three PRD-10 CSVs.

Neutral by construction: it reads `data/internal/agentrx/<experiment_id>/` and
writes `data/experiment/results/<experiment_id>/{runs_long,trajectory_index,
metricas}.csv`. No statistic, no A/B comparison, no row weighting — just the
dictionary's formulas. Error reps are surfaced (`n_judge_runs` and stdout),
never dropped silently.
"""

from __future__ import annotations

from pathlib import Path

from agentrx_otel_poc.judge.config import OUTPUT_ROOT, ROOT

from .aggregate import metricas_row, runs_long_rows, trajectory_index_row
from .csv_writer import write_csv
from .reader import load_experiment

RESULTS_ROOT = ROOT / "data" / "experiment" / "results"


def _experiment_dirs(only: str | None) -> list[Path]:
    if only:
        exp = OUTPUT_ROOT / only
        if not (exp / "runs_index.jsonl").exists():
            raise FileNotFoundError(f"no experiment {only!r} in {OUTPUT_ROOT}")
        return [exp]
    return sorted(p.parent for p in OUTPUT_ROOT.glob("*/runs_index.jsonl"))


def collect_experiment(exp_dir: Path) -> dict:
    pairs = load_experiment(exp_dir)
    long_rows = [row for pair in pairs for row in runs_long_rows(pair)]
    index_rows = [trajectory_index_row(pair) for pair in pairs]
    metric_rows = [metricas_row(pair) for pair in pairs]

    out_dir = RESULTS_ROOT / exp_dir.name
    write_csv(out_dir, "runs_long.csv", long_rows)
    write_csv(out_dir, "trajectory_index.csv", index_rows)
    write_csv(out_dir, "metricas.csv", metric_rows)

    errors = sum(pair.n_error_reps for pair in pairs)
    print(
        f"[collect] {exp_dir.name}: {len(pairs)} trajectory×arm, "
        f"{len(long_rows)} judge run(s), {errors} error rep(s) -> {out_dir}"
    )
    return {"experiment": exp_dir.name, "pairs": len(pairs), "out_dir": str(out_dir)}


def collect(only: str | None = None) -> list[dict]:
    exps = _experiment_dirs(only)
    if not exps:
        print(f"[collect] no experiments under {OUTPUT_ROOT}")
        return []
    return [collect_experiment(exp) for exp in exps]
