"""Build the judge matrix: which (arm, run_id, rep) triples to run.

Without filters the plan covers every trajectory present in both arm
directories × N reps. Filters (`scenarios`, `fault`, `arms`, `reps`) slice it;
`only_errors` is applied later by the experiment against the run index.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from agentrx_otel_poc import paths

from .config import ROOT

ARMS = ("telemetry", "agentrx")
BENCHMARK = ROOT / "data" / "benchmark" / "benchmark_30.json"


def arm_dirs(mas_id: str) -> dict[str, Path]:
    """Trajectory dir per arm, rooted at the MAS corpus `mas_id`."""
    return {arm: paths.trajectory_dir(mas_id, arm) for arm in ARMS}


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


def _run_ids(arm_dir: Path) -> list[str]:
    return sorted(p.stem for p in arm_dir.glob("*.json"))


def smoke_scenarios() -> list[str]:
    """One run_id per fault category (first by run_id) — the smoke slice."""
    by_fault = fault_category_map()
    first: dict[str, str] = {}
    for run_id in sorted(by_fault):
        first.setdefault(by_fault[run_id], run_id)
    return sorted(first.values())


def _selected_run_ids(
    arm_dir: Path, wanted: set[str] | None, fault: str | None, by_fault: dict[str, str]
) -> list[str]:
    run_ids = _run_ids(arm_dir)
    if wanted is not None:
        run_ids = [r for r in run_ids if r in wanted]
    if fault:
        run_ids = [r for r in run_ids if by_fault.get(r) == fault]
    return run_ids


def build_plan(
    mas_id: str,
    *,
    arms: list[str] | None = None,
    scenarios: list[str] | None = None,
    fault: str | None = None,
    reps: int = 3,
) -> list[RepTask]:
    dirs = arm_dirs(mas_id)
    gt_dir = paths.ground_truth_dir(mas_id)
    arms = arms or list(dirs)
    unknown = set(arms) - set(dirs)
    if unknown:
        raise ValueError(f"unknown arm(s): {sorted(unknown)}; valid: {list(dirs)}")
    wanted = set(scenarios) if scenarios else None
    by_fault = fault_category_map() if fault else {}

    tasks: list[RepTask] = []
    for arm in arms:
        for run_id in _selected_run_ids(dirs[arm], wanted, fault, by_fault):
            for rep in range(1, reps + 1):
                tasks.append(
                    RepTask(
                        arm=arm,
                        run_id=run_id,
                        rep=rep,
                        traj_path=dirs[arm] / f"{run_id}.json",
                        gt_path=gt_dir / f"{run_id}.ground_truth.json",
                    )
                )
    return tasks
