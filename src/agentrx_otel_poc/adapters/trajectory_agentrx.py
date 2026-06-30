"""Arm B — AgentRx-style trajectory (faithful prose, NO telemetry) (PRD-04 §5)."""

from __future__ import annotations

from typing import Any

from .ir import build_ir
from .parser import ParsedTrajectory


def build(trajectory: ParsedTrajectory) -> dict[str, Any]:
    return build_ir(trajectory, include_telemetry=False)
