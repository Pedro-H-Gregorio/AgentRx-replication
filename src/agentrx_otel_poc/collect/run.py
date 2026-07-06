"""Collect one or all judge experiments on disk into the three PRD-10 CSVs.

Neutral by construction: it reads `data/internal/<mas_id>/agentrx/<judge_id>/` and
writes `data/experiment/results/<mas_id>/<judge_id>/{runs_long,trajectory_index,
metricas}.csv`. No statistic, no A/B comparison, no row weighting — just the
dictionary's formulas. Error reps are surfaced (`n_judge_runs` and stdout),
never dropped silently.
"""

from __future__ import annotations

from pathlib import Path

from agentrx_otel_poc import paths
from agentrx_otel_poc.settings import Settings

from .aggregate import metricas_row, runs_long_rows, trajectory_index_row
from .csv_writer import write_csv
from .reader import load_experiment


def _experiment_dirs(only: str | None, mas_id: str) -> list[Path]:
    agentrx = paths.agentrx_root(mas_id)
    if only:
        exp = agentrx / only
        if not (exp / "runs_index.jsonl").exists():
            raise FileNotFoundError(f"no experiment {only!r} in {agentrx}")
        return [exp]
    return sorted(p.parent for p in agentrx.glob("*/runs_index.jsonl"))


def collect_experiment(exp_dir: Path) -> dict:
    # exp_dir = <mas_id>/agentrx/<judge_id>: the corpus root is two levels up.
    mas_root = exp_dir.parent.parent
    mas_id = mas_root.name
    pairs = load_experiment(exp_dir, mas_root)
    long_rows = [row for pair in pairs for row in runs_long_rows(pair)]
    index_rows = [trajectory_index_row(pair) for pair in pairs]
    metric_rows = [metricas_row(pair) for pair in pairs]

    out_dir = paths.results_root(mas_id) / exp_dir.name
    write_csv(out_dir, "runs_long.csv", long_rows)
    write_csv(out_dir, "trajectory_index.csv", index_rows)
    write_csv(out_dir, "metricas.csv", metric_rows)

    errors = sum(pair.n_error_reps for pair in pairs)
    label = f"{mas_id}/{exp_dir.name}"
    print(
        f"[collect] {label}: {len(pairs)} trajectory×arm, "
        f"{len(long_rows)} judge run(s), {errors} error rep(s) -> {out_dir}"
    )
    return {"experiment": label, "pairs": len(pairs), "out_dir": str(out_dir)}


def collect(only: str | None = None, mas_id: str | None = None) -> list[dict]:
    mas_id = mas_id or paths.resolve_mas_id(Settings())
    exps = _experiment_dirs(only, mas_id)
    if not exps:
        print(f"[collect] no experiments under {paths.agentrx_root(mas_id)}")
        return []
    return [collect_experiment(exp) for exp in exps]
