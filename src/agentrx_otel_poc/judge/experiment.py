"""Drive the judge matrix: sequential, resumable, tolerant of per-rep failure."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from .config import JudgeConfig
from .executor import RepResult, run_rep
from .planner import RepTask, build_plan
from .report import rebuild_index, summarize, write_index, write_manifest

VERBOSE = os.getenv("JUDGE_VERBOSE", "").lower() in ("1", "true", "yes")


@dataclass(frozen=True)
class Selection:
    arms: list[str] | None = None
    scenarios: list[str] | None = None
    fault: str | None = None
    reps: int = 3
    only_errors: bool = False
    force: bool = False


def _error_keys(exp_dir: Path) -> set[tuple[str, str, int]]:
    index = exp_dir / "runs_index.jsonl"
    if not index.exists():
        return set()
    keys: set[tuple[str, str, int]] = set()
    for line in index.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row.get("status") == "error":
            keys.add((row["arm"], row["run_id"], int(row["rep"])))
    return keys


def _rep_dir(exp_dir: Path, task: RepTask) -> Path:
    return exp_dir / task.arm / task.run_id / f"rep{task.rep}"


_PROBLEM_MARKERS = ("[WARN]", "[ERROR]", "No authentication", "Empty response")


def _echo_log(result: RepResult, tail_lines: int = 15) -> None:
    """Surface the AgentRx output in the terminal.

    Always prints the log path. On error (or JUDGE_VERBOSE=1) prints the tail;
    otherwise prints any WARN/ERROR lines so problems show even when a rep is
    (currently) classified `ok` — e.g. an unauthenticated judge (see task 7.1).
    Full log lives at `<run_dir>/agentrx.log`.
    """
    if result.log_path is None or not result.log_path.exists():
        return
    print(f"        log: {result.log_path}")
    lines = result.log_path.read_text(encoding="utf-8").splitlines()
    if VERBOSE:
        chosen = lines
    elif result.status == "error":
        chosen = lines[-tail_lines:]
    else:
        chosen = [ln for ln in lines if any(m in ln for m in _PROBLEM_MARKERS)]
    for line in chosen:
        print(f"        | {line}")


def run_experiment(config: JudgeConfig, selection: Selection) -> dict:
    config.validate()
    exp_dir = config.output_root() / config.experiment_id()
    write_manifest(exp_dir, config, selection.__dict__)

    plan = build_plan(
        config.mas_id,
        arms=selection.arms,
        scenarios=selection.scenarios,
        fault=selection.fault,
        reps=selection.reps,
    )
    if selection.only_errors:
        errors = _error_keys(exp_dir)
        plan = [t for t in plan if (t.arm, t.run_id, t.rep) in errors]

    print(f"[judge] experiment {config.experiment_id()} — {len(plan)} rep(s)")
    session_status: dict[tuple[str, str, int], str] = {}
    for i, task in enumerate(plan, 1):
        result = run_rep(
            _rep_dir(exp_dir, task), task.traj_path, config, force=selection.force
        )
        session_status[(task.arm, task.run_id, task.rep)] = result.status
        tag = result.detail and f" ({result.detail})" or ""
        print(
            f"[judge] {i}/{len(plan)} {task.arm}/{task.run_id} rep{task.rep}"
            f" -> {result.status}{tag}"
        )
        _echo_log(result)

    rows = rebuild_index(exp_dir, session_status)
    write_index(exp_dir, rows)
    print("\n" + summarize(rows) + "\n")
    return {"exp_dir": str(exp_dir), "reps": len(rows)}
