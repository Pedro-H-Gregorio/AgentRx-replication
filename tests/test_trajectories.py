"""Validator for the 2 arms: non-leakage (R1/R2), semantic parity (R4), IR validity.

Arm A is now a JSON string with a `telemetry` block; arm B stays prose (baseline do
artigo). Parity is checked at the semantic level: arm A's facts, minus telemetry,
rendered as prose, must equal arm B verbatim.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentrx_otel_poc import paths
from agentrx_otel_poc.adapters.content_lines import render_prose
from agentrx_otel_poc.settings import Settings

ROOT = Path(__file__).resolve().parent.parent
# Validate the 2 arms of the current MAS corpus (data/internal/<mas_id>/).
_MAS = paths.resolve_mas_id(Settings())
TELEMETRY_DIR = paths.trajectory_dir(_MAS, "telemetry")
AGENTRX_DIR = paths.trajectory_dir(_MAS, "agentrx")

# Kept in sync with sanitize._LEAK_TOKENS (the dotted `faults.` guards the enriched
# event attributes, e.g. a fully-qualified `exception.type`).
LEAK_TOKENS = (
    "fault.injected",
    "experiment.fault",
    "faults.py",
    "faults.",
    "operators.py",
    "maybe_raise",
    "_system_failure",
)

RUN_IDS = (
    sorted(p.stem for p in TELEMETRY_DIR.glob("*.json"))
    if TELEMETRY_DIR.exists()
    else []
)


def _load(directory: Path, run_id: str) -> dict:
    return json.loads((directory / f"{run_id}.json").read_text(encoding="utf-8"))


def _content(step: dict) -> str:
    return step["substeps"][0]["content"]


def test_arms_exist() -> None:
    assert RUN_IDS, "no trajectories — run `make derive` first"


@pytest.mark.parametrize("run_id", RUN_IDS)
def test_no_leakage(run_id: str) -> None:
    for directory in (TELEMETRY_DIR, AGENTRX_DIR):
        blob = (directory / f"{run_id}.json").read_text(encoding="utf-8")
        for token in LEAK_TOKENS:
            assert token not in blob, (
                f"{run_id}: '{token}' leaked into {directory.name}"
            )


@pytest.mark.parametrize("run_id", RUN_IDS)
def test_no_absolute_machine_paths(run_id: str) -> None:
    """GAP-1: a normalized stacktrace must not carry an absolute machine path (a
    non-reproducible, experiment-revealing hint)."""
    for directory in (TELEMETRY_DIR, AGENTRX_DIR):
        blob = (directory / f"{run_id}.json").read_text(encoding="utf-8")
        assert "/home/" not in blob, (
            f"{run_id}: absolute path leaked into {directory.name}"
        )


@pytest.mark.parametrize("run_id", RUN_IDS)
def test_semantic_parity(run_id: str) -> None:
    """Arm A carries the same semantic facts as arm B; it differs only by the JSON
    serialization and the extra `telemetry` object."""
    arm_a, arm_b = _load(TELEMETRY_DIR, run_id), _load(AGENTRX_DIR, run_id)
    assert len(arm_a["steps"]) == len(arm_b["steps"])
    for step_a, step_b in zip(arm_a["steps"], arm_b["steps"]):
        facts = json.loads(_content(step_a))
        assert "telemetry" in facts, f"{run_id}: arm A step lost its telemetry block"
        facts.pop("telemetry")
        # arm A facts, rendered as prose, must reproduce arm B exactly.
        assert "\n".join(render_prose(facts)) == _content(step_b), (
            f"{run_id}: semantic facts diverge between arms"
        )


@pytest.mark.parametrize("run_id", RUN_IDS)
def test_arm_b_has_no_telemetry(run_id: str) -> None:
    """Arm B stays prose (no JSON, no telemetry lines)."""
    arm_b = _load(AGENTRX_DIR, run_id)
    for step in arm_b["steps"]:
        content = _content(step)
        assert not content.lstrip().startswith("{"), f"{run_id}: arm B looks like JSON"
        assert "Traceback" not in content, f"{run_id}: arm B carries a stacktrace"


AGENTRX_SUBMODULE = ROOT / "AgentRx"


@pytest.mark.parametrize("run_id", RUN_IDS)
def test_validates_against_agentrx_ir(run_id: str) -> None:
    if not AGENTRX_SUBMODULE.exists():
        pytest.skip("AgentRx submodule not initialized (git submodule update --init)")
    # Submodule present → a broken import is a real failure, never a silent skip.
    from agentrx.ir.trajectory_ir import validate_ir

    for directory in (TELEMETRY_DIR, AGENTRX_DIR):
        validate_ir(_load(directory, run_id))
