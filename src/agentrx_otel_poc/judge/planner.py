"""Build the judge matrix: which (arm, run_id, rep) triples to run.

Without filters the plan covers every trajectory present in both arm
directories × N reps. Filters (`scenarios`, `fault`, `arms`, `reps`) slice it;
`only_errors` is applied later by the experiment against the run index.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .config import ROOT

ARM_DIRS = {
    "telemetry": ROOT / "data" / "internal" / "trajectory_telemetry",
    "agentrx": ROOT / "data" / "internal" / "trajectory_agentrx",
}
GT_DIR = ROOT / "data" / "internal" / "ground_truth"
BENCHMARK = ROOT / "data" / "benchmark" / "benchmark_30.json"


@dataclass(frozen=True)
class RepTask:
    arm: str
    run_id: str
    rep: int
    traj_path: Path
    gt_path: Path


def fault_category_map() -> dict[str, str]:
    """run_id → target_fault_category, from the benchmark (for the --fault filter)."""
    scenarios = json.loads(BENCHMARK.read_text(encoding="utf-8"))
    return {s["task_id"]: s["target_fault_category"] for s in scenarios}


def _run_ids(arm: str) -> list[str]:
    return sorted(p.stem for p in ARM_DIRS[arm].glob("*.json"))


def smoke_scenarios() -> list[str]:
    """One run_id per fault category (first by run_id) — the smoke slice."""
    by_fault = fault_category_map()
    first: dict[str, str] = {}
    for run_id in sorted(by_fault):
        first.setdefault(by_fault[run_id], run_id)
    return sorted(first.values())


def _selected_run_ids(
    arm: str, wanted: set[str] | None, fault: str | None, by_fault: dict[str, str]
) -> list[str]:
    run_ids = _run_ids(arm)
    if wanted is not None:
        run_ids = [r for r in run_ids if r in wanted]
    if fault:
        run_ids = [r for r in run_ids if by_fault.get(r) == fault]
    return run_ids


def build_plan(
    *,
    arms: list[str] | None = None,
    scenarios: list[str] | None = None,
    fault: str | None = None,
    reps: int = 3,
) -> list[RepTask]:
    arms = arms or list(ARM_DIRS)
    unknown = set(arms) - set(ARM_DIRS)
    if unknown:
        raise ValueError(f"unknown arm(s): {sorted(unknown)}; valid: {list(ARM_DIRS)}")
    wanted = set(scenarios) if scenarios else None
    by_fault = fault_category_map() if fault else {}

    tasks: list[RepTask] = []
    for arm in arms:
        for run_id in _selected_run_ids(arm, wanted, fault, by_fault):
            for rep in range(1, reps + 1):
                tasks.append(
                    RepTask(
                        arm=arm,
                        run_id=run_id,
                        rep=rep,
                        traj_path=ARM_DIRS[arm] / f"{run_id}.json",
                        gt_path=GT_DIR / f"{run_id}.ground_truth.json",
                    )
                )
    return tasks
