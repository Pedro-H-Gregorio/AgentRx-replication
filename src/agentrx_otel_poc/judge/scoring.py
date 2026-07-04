"""Score a judge verdict against local ground truth (judge-validation spec).

The judge stays blind (no `--ground-truth`); scoring is entirely ours, from
`data/internal/ground_truth/`. When a report lists several failures the
prediction replicates AgentRx's `compute_stats`/`analysis()` exactly: category =
mode of the failure cases, step = round(mean of the step numbers). No-error (0)
and inconclusive (10) count as a category miss; raw values are preserved.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from statistics import mean

# AgentRx FailureCase enum value → benchmark fault category (5 injectable ones).
FAILURE_CASE_TO_CATEGORY = {
    1: "Instruction/Plan Adherence Failure",
    2: "Invention of New Information",
    3: "Invalid Invocation",
    4: "Misinterpretation of Tool Output",
    9: "System Failure",
}


def predict(failures: list[dict]) -> tuple[str | None, int | None, list[int]]:
    """Return (predicted_category, predicted_step, raw_failure_cases).

    Mirrors compute_stats: category = mode (Counter.most_common), step =
    round(mean). Category is None when the modal case is not an injectable one
    (0 no-error, 5-8 other taxonomies, 10 inconclusive).
    """
    cases = [int(f["failure_case"]) for f in failures]
    steps = [int(f["step_number"]) for f in failures]
    if not cases:
        return None, None, []
    modal_case = Counter(cases).most_common(1)[0][0]
    category = FAILURE_CASE_TO_CATEGORY.get(modal_case)
    step = round(mean(steps)) if steps else None
    return category, step, cases


def failures_for(run1_path: Path, run_id: str) -> list[dict]:
    """Extract the report failures for *run_id* from a judge `run1.json`."""
    blob = json.loads(run1_path.read_text(encoding="utf-8"))
    reports = blob.get("detailed_results", []) if isinstance(blob, dict) else blob
    for report in reports:
        if str(report.get("task_id")) == run_id:
            return list(report.get("failures", []))
    # Single-trajectory run dir: fall back to the sole report if ids drift.
    if len(reports) == 1:
        return list(reports[0].get("failures", []))
    return []


def has_verdict(run1_path: Path, run_id: str) -> bool:
    """True iff the judge produced ≥1 failure for *run_id* (a real verdict).

    An empty failures list means the judge returned nothing (e.g. an
    unauthenticated backend or an empty LLM response) — that is NOT a verdict.
    A legitimate "no error" verdict still carries one failure (failure_case 0).
    """
    if not run1_path.exists():
        return False
    try:
        return bool(failures_for(run1_path, run_id))
    except (ValueError, OSError):
        return False


def score(run1_path: Path, ground_truth: dict, run_id: str) -> dict:
    """Compare the judge verdict to ground truth → an index-row fragment."""
    failures = failures_for(run1_path, run_id)
    category, step, cases = predict(failures)
    gt_category = ground_truth["failure_category"]
    gt_step = ground_truth["critical_failure_step"]
    return {
        "predicted_category": category,
        "predicted_step": step,
        "raw_failure_cases": cases,
        "gt_category": gt_category,
        "gt_step": gt_step,
        "hit_category": category == gt_category,
        "hit_step": step == gt_step,
    }
