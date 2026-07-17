"""OTel→IR builders for the two arms (canonical AgentRx IR: role/content only)."""

from __future__ import annotations

import json
from typing import Any

from .content_lines import semantic_fields, semantic_lines, telemetry_block
from .parser import ParsedTrajectory


def _wrap(trajectory: ParsedTrajectory, contents: list[str]) -> dict[str, Any]:
    steps = [
        {
            "index": step.step_index,
            "substeps": [{"sub_index": 1, "role": step.agent_name, "content": content}],
        }
        for step, content in zip(trajectory.steps, contents)
    ]
    return {
        "trajectory_id": trajectory.trajectory_id,
        "instruction": trajectory.instruction,
        "steps": steps,
    }


def build_prose_ir(trajectory: ParsedTrajectory) -> dict[str, Any]:
    """Arm B: `content` is prose, one semantic fact per line (no telemetry)."""
    contents = ["\n".join(semantic_lines(step)) for step in trajectory.steps]
    return _wrap(trajectory, contents)


def build_json_ir(trajectory: ParsedTrajectory) -> dict[str, Any]:
    """Arm A: `content` is a JSON string with the semantic facts + a `telemetry` object."""
    contents = [
        json.dumps(
            {**semantic_fields(step), "telemetry": telemetry_block(step)},
            ensure_ascii=False,
        )
        for step in trajectory.steps
    ]
    return _wrap(trajectory, contents)
