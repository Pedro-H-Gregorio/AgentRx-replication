"""Shared OTel→IR builder for both arms (canonical AgentRx IR: role/content only).

The only difference between arms is whether telemetry lines are appended — telemetry
never becomes a structured IR field (invariant #6); it lives inside `content` text.
"""

from __future__ import annotations

from typing import Any

from .content_lines import semantic_lines, telemetry_lines
from .parser import ParsedTrajectory


def build_ir(
    trajectory: ParsedTrajectory, *, include_telemetry: bool
) -> dict[str, Any]:
    steps = []
    for step in trajectory.steps:
        lines = semantic_lines(step)
        if include_telemetry:
            lines = lines + telemetry_lines(step)
        steps.append(
            {
                "index": step.step_index,
                "substeps": [
                    {
                        "sub_index": 1,
                        "role": step.agent_name,
                        "content": "\n".join(lines),
                    }
                ],
            }
        )
    return {
        "trajectory_id": trajectory.trajectory_id,
        "instruction": trajectory.instruction,
        "steps": steps,
    }
