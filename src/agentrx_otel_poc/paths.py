"""Single source of truth for run-artifact paths, rooted per MAS model.

Every corpus lives under `data/internal/<mas_id>/` so running the MAS with a
different agent model never overwrites a prior corpus (ADR-0013). The `mas_id`
is the effective config value — `MAS_ID` env, else `AGENT_MODEL` — used
**literally** (case and dots preserved: `Llama3.1-8B` → `data/internal/Llama3.1-8B/`),
only sanitizing path-breaking characters (`/ \\ : whitespace` → `-`). It is
resolved from the `Settings` passed to the run, so a programmatic run with
another model lands in the right namespace.
"""

from __future__ import annotations

import re
from pathlib import Path

from agentrx_otel_poc.settings import Settings

ROOT = Path(__file__).resolve().parents[2]
DATA_INTERNAL = ROOT / "data" / "internal"
EXPERIMENT_RESULTS = ROOT / "data" / "experiment" / "results"


def resolve_mas_id(settings: Settings) -> str:
    """Corpus namespace: `MAS_ID` if set, else `AGENT_MODEL`, used literally with
    only path-breaking chars folded to '-' (keeps case/dots readable)."""
    raw = settings.mas_id or settings.agent_model
    return re.sub(r"[/\\:\s]+", "-", raw.strip()).strip("-")


def mas_root(mas_id: str) -> Path:
    return DATA_INTERNAL / mas_id


def otel_dir(mas_id: str) -> Path:
    return mas_root(mas_id) / "otel"


def trajectory_dir(mas_id: str, arm: str) -> Path:
    return mas_root(mas_id) / f"trajectory_{arm}"


def ground_truth_dir(mas_id: str) -> Path:
    return mas_root(mas_id) / "ground_truth"


def logs_dir(mas_id: str) -> Path:
    return mas_root(mas_id) / "logs"


def manifests_dir(mas_id: str) -> Path:
    return mas_root(mas_id) / "manifests"


def agentrx_root(mas_id: str) -> Path:
    return mas_root(mas_id) / "agentrx"


def results_root(mas_id: str) -> Path:
    return EXPERIMENT_RESULTS / mas_id
