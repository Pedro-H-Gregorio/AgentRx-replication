"""Turn one experiment's PairData into the three CSVs' row dicts.

The aggregation replicates AgentRx's `compute_stats`/`analysis()`: the failures
of every ok rep of a (scenario, arm) are pooled flat, then category = mode and
step = round(mean) over the pool. Formulas follow the PRD-10 result dictionary. This module
makes no analytical choice — no test, no ranking, no row dropped.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from statistics import mean, median, stdev

from .categories import case_of, name_of
from .reader import PairData


def _round6(value: float) -> float:
    """Fixed precision so CSV bytes are stable across runs/platforms."""
    return round(float(value), 6)


def _pool(pair: PairData) -> tuple[list[int], list[int]]:
    cases = [c for rep in pair.reps for c, _ in rep.failures]
    steps = [s for rep in pair.reps for _, s in rep.failures]
    return cases, steps


def _rep_prediction(failures: list[tuple[int, int]]) -> tuple[int | None, int | None]:
    """Per-rep modal case + round(mean step) (D24), for the runs_long row."""
    if not failures:
        return None, None
    cases = [c for c, _ in failures]
    steps = [s for _, s in failures]
    return Counter(cases).most_common(1)[0][0], round(mean(steps))


def runs_long_rows(pair: PairData) -> list[dict]:
    rows = []
    for rep in pair.reps:
        case, step = _rep_prediction(rep.failures)
        rows.append(
            {
                "scenario_id": pair.run_id,
                "arm": pair.arm,
                "judge_idx": rep.rep,
                "pred_step": step,
                "pred_category": case,
                "pred_category_name": name_of(case),
                "raw_failures_json": [{"case": c, "step": s} for c, s in rep.failures],
                "agentrx_run_name": rep.run_dir,
            }
        )
    return rows


def trajectory_index_row(pair: PairData) -> dict:
    sent = min(rep.run1_mtime for rep in pair.reps)
    sent_at = datetime.fromtimestamp(sent, tz=timezone.utc).isoformat(
        timespec="seconds"
    )
    rel = f"data/internal/{pair.mas_id}"
    return {
        "run_id": pair.run_id,
        "scenario_id": pair.run_id,
        "arm": pair.arm,
        "trajectory_path": f"{rel}/trajectory_{pair.arm}/{pair.run_id}.json",
        "otel_path": f"{rel}/otel/{pair.run_id}.otel.json",
        "n_steps": pair.n_steps,
        "sent_at": sent_at,
    }


def _gt(pair: PairData) -> tuple[int, int, list[dict]]:
    gt = pair.ground_truth
    gt_case = case_of(gt["failure_category"])
    gt_step = int(gt["critical_failure_step"])
    # MAS injects one fault ⇒ the annotated-failure set is the single critical one
    # (PRD-07 §6); any/earliest/terminal collapse to it.
    failures = [{"step": gt_step, "category": gt_case}]
    return gt_case, gt_step, failures


def metricas_row(pair: PairData) -> dict:
    cases, steps = _pool(pair)
    gt_case, gt_step, gt_failures = _gt(pair)
    modal = Counter(cases).most_common(1)[0][0] if cases else None
    step_mean = mean(steps) if steps else 0.0
    distance = abs(step_mean - gt_step)
    gt_cats = {f["category"] for f in gt_failures}
    return {
        "scenario_id": pair.run_id,
        "arm": pair.arm,
        "n_judge_runs": len(pair.reps),
        "trajectory_length": pair.n_steps,
        "gt_step": gt_step,
        "gt_category": gt_case,
        "gt_category_name": name_of(gt_case),
        "gt_failures_json": gt_failures,
        "gt_earliest_category": gt_case,
        "gt_terminal_category": gt_case,
        "most_common_category": modal,
        "most_common_category_name": name_of(modal),
        "step_mean": _round6(step_mean),
        "step_median": _round6(median(steps)) if steps else 0.0,
        "category_std": _round6(stdev(cases)) if len(cases) > 1 else 0.0,
        "step_std": _round6(stdev(steps)) if len(steps) > 1 else 0.0,
        "failure_case_accuracy_perrun": _round6(
            sum(c == gt_case for c in cases) / len(cases)
        )
        if cases
        else 0.0,
        "step_mae": _round6(mean(abs(s - gt_step) for s in steps)) if steps else 0.0,
        "step_acc_exact": int(round(step_mean) == gt_step),
        "step_acc_tol1": int(abs(round(step_mean) - gt_step) <= 1),
        "step_acc_tol3": int(abs(round(step_mean) - gt_step) <= 3),
        "step_acc_tol5": int(abs(round(step_mean) - gt_step) <= 5),
        "avg_step_distance": _round6(distance),
        "avg_step_distance_norm": _round6(distance / pair.n_steps)
        if pair.n_steps
        else 0.0,
        "cat_acc_critical": int(modal == gt_case),
        "cat_acc_any": int(modal in gt_cats),
        "cat_acc_earliest": int(modal == gt_case),
        "cat_acc_terminal": int(modal == gt_case),
        "judge_model": pair.judge_model,
        "agentrx_run_name": f"{pair.arm}/{pair.run_id}",
    }
