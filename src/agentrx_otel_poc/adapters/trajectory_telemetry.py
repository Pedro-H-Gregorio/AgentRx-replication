"""Arm A — trajectory WITH telemetry (PRD-04 §4)."""

from __future__ import annotations

from typing import Any

from .ir import build_json_ir
from .parser import ParsedTrajectory


def build(trajectory: ParsedTrajectory) -> dict[str, Any]:
    return build_json_ir(trajectory)
