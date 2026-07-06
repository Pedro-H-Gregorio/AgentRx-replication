"""Black-box orchestration of the AgentRx judge (C6).

Runs the 2-arm trajectories through `AgentRx/run.py --stage judge` by subprocess
(never importing `agentrx`), selects the judge backend via `JUDGE_*` env, and
writes results under `data/internal/<mas_id>/agentrx/<judge_id>/` for the CSV step.
"""

from __future__ import annotations

from .config import JudgeConfig, JudgeConfigError
from .experiment import Selection, run_experiment
from .planner import smoke_scenarios

__all__ = [
    "JudgeConfig",
    "JudgeConfigError",
    "Selection",
    "run_experiment",
    "smoke_scenarios",
]
