"""Arm B — AgentRx-style trajectory (faithful prose, NO telemetry) (PRD-04 §5)."""

from __future__ import annotations

from typing import Any

from .ir import build_prose_ir
from .parser import ParsedTrajectory


def build(trajectory: ParsedTrajectory) -> dict[str, Any]:
    return build_prose_ir(trajectory)
