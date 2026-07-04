#!/usr/bin/env python3
"""Run the 2-arm trajectories through the AgentRx judge (C6). Thin CLI.

Backend comes from the environment (`JUDGE_BACKEND`, …); the flags only slice
the matrix. Without slices it judges every trajectory in both arm directories,
skipping reps that already hold a valid verdict.

  python scripts/run_judge.py                     # all trajectories, 3 reps
  python scripts/run_judge.py --fault "System Failure" --arms telemetry --reps 1
  python scripts/run_judge.py --only-errors       # redo only failed reps
  python scripts/run_judge.py --smoke             # 1 scenario/category, 1 rep
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from agentrx_otel_poc.judge import (  # noqa: E402
    JudgeConfig,
    JudgeConfigError,
    Selection,
    run_experiment,
    smoke_scenarios,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arms", nargs="+", choices=["telemetry", "agentrx"])
    parser.add_argument("--scenarios", nargs="+", help="run_ids to judge")
    parser.add_argument("--fault", help="filter by target fault category")
    parser.add_argument("--reps", type=int, default=3)
    parser.add_argument("--only-errors", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--smoke", action="store_true", help="1 scenario per category, 1 rep"
    )
    parser.add_argument(
        "--preflight",
        action="store_true",
        help="probe the backend (auth/model) before the matrix; abort on failure",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    scenarios = smoke_scenarios() if args.smoke else args.scenarios
    reps = 1 if args.smoke else args.reps
    selection = Selection(
        arms=args.arms,
        scenarios=scenarios,
        fault=args.fault,
        reps=reps,
        only_errors=args.only_errors,
        force=args.force,
    )
    config = JudgeConfig.from_settings()
    if args.preflight:
        try:
            config.validate()
        except JudgeConfigError as exc:
            print(f"[judge] config error: {exc}", file=sys.stderr)
            return 2
        error = config.preflight()
        if error:
            print(f"[judge] preflight failed: {error}", file=sys.stderr)
            return 3
        print(f"[judge] preflight ok: backend {config.backend!r} responds")
    try:
        result = run_experiment(config, selection)
    except JudgeConfigError as exc:
        print(f"[judge] config error: {exc}", file=sys.stderr)
        return 2
    print(f"[judge] done: {result['reps']} rep(s) indexed at {result['exp_dir']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
