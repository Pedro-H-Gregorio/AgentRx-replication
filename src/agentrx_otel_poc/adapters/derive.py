"""Derive both trajectory arms from one raw OTel payload (PRD-04).

Pipeline: parse → sanitize (R1/R2) → build arm A (telemetry) and arm B (prose).
Telemetry and prose arms carry identical semantics; they differ only in the
telemetry lines (parity, PRD-06 §8).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import trajectory_agentrx, trajectory_telemetry
from .parser import parse
from .sanitize import sanitize


def derive_arms(payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return (arm_a_telemetry, arm_b_agentrx) IR dicts from a raw OTel payload."""
    trajectory = sanitize(parse(payload))
    return trajectory_telemetry.build(trajectory), trajectory_agentrx.build(trajectory)


def _write(ir: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(ir, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def derive_to_files(
    payload: dict[str, Any], telemetry_path: Path, agentrx_path: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    arm_a, arm_b = derive_arms(payload)
    _write(arm_a, telemetry_path)
    _write(arm_b, agentrx_path)
    return arm_a, arm_b
