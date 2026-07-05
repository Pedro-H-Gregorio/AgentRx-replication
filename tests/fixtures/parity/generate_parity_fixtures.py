#!/usr/bin/env python3
"""ONE-TIME generator of the numeric-parity fixture (not run in CI).

Provenance: builds AgentRx's own `Report.compute_stats()` outputs so the
collector's re-implementation can be checked against them WITHOUT importing
`agentrx` in the test path (regra 6 / PRD-07 §8). Re-run only to regenerate the
fixture after a submodule bump; the committed `compute_stats_cases.json` is the
oracle the offline test reads.

Usage (from repo root):
    git -C AgentRx rev-parse HEAD                 # record the commit below
    uv run python tests/fixtures/parity/generate_parity_fixtures.py

AgentRx submodule commit when last generated:
    f228165bfec60a801fd5fedd9d8ffe0f9de0c69d
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "AgentRx"))

from agentrx.judge.judge import Failure, Report  # noqa: E402

# (name, pooled failures [(case, step)], gt (case, step), trajectory_length)
CASES = [
    ("single_hit", [(9, 3)], (9, 3), 5),
    ("multi_failure_pool", [(3, 2), (3, 2), (3, 3), (9, 4)], (3, 2), 5),
    ("mode_tie", [(3, 2), (9, 2)], (3, 2), 4),
    ("inconclusive", [(10, 4)], (3, 2), 6),
    ("no_error", [(0, 1)], (9, 3), 5),
    ("category_miss", [(4, 3)], (9, 3), 7),
]


def _expected(failures: list, gt: tuple, length: int) -> dict:
    report = Report("t", trajectory_length=length)
    for case, step in failures:
        report.add_failure(Failure("t", case, "d", step))
    report.compute_stats(Failure("t", gt[0], "gt", gt[1]))
    step_mean = report.step_mean
    gt_step = gt[1]
    distance = abs(step_mean - gt_step)
    return {
        "most_common_failure": int(report.most_common_failure),
        "step_mean": step_mean,
        "step_median": report.step_median,
        "category_std": report.std_dev,
        "step_std": report.step_std_dev,
        "failure_case_accuracy": report.failure_case_accuracy,
        "step_mae": report.step_mae,
        "step_acc_exact": int(round(step_mean) == gt_step),
        "step_acc_tol1": int(abs(round(step_mean) - gt_step) <= 1),
        "step_acc_tol3": int(abs(round(step_mean) - gt_step) <= 3),
        "step_acc_tol5": int(abs(round(step_mean) - gt_step) <= 5),
        "avg_step_distance": distance,
        "avg_step_distance_norm": distance / length,
    }


def main() -> int:
    cases = [
        {
            "name": name,
            "failures": [[c, s] for c, s in failures],
            "gt_case": gt[0],
            "gt_step": gt[1],
            "trajectory_length": length,
            "expected": _expected(failures, gt, length),
        }
        for name, failures, gt, length in CASES
    ]
    out = {
        "_provenance": "AgentRx Report.compute_stats() + analysis() step logic; "
        "commit f228165bfec60a801fd5fedd9d8ffe0f9de0c69d; "
        "regenerate via generate_parity_fixtures.py",
        "cases": cases,
    }
    path = Path(__file__).parent / "compute_stats_cases.json"
    path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(cases)} parity cases to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
