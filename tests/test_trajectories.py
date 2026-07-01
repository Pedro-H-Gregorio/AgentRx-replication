"""Validator for the 2 arms: non-leakage (R1/R2), parity (R4), IR validity."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TELEMETRY_DIR = ROOT / "data" / "internal" / "trajectory_telemetry"
AGENTRX_DIR = ROOT / "data" / "internal" / "trajectory_agentrx"

LEAK_TOKENS = (
    "fault.injected",
    "experiment.fault",
    "faults.py",
    "operators.py",
    "maybe_raise",
)
TELEMETRY_PREFIXES = (
    "duration_ms=",
    "tokens in/out/total=",
    "model=",
    "span_id=",
    "otel_status=",
    "events=[",
    "infra=",
)

RUN_IDS = (
    sorted(p.stem for p in TELEMETRY_DIR.glob("*.json"))
    if TELEMETRY_DIR.exists()
    else []
)


def _load(directory: Path, run_id: str) -> dict:
    return json.loads((directory / f"{run_id}.json").read_text(encoding="utf-8"))


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
def test_parity_a_minus_telemetry_equals_b(run_id: str) -> None:
    arm_a, arm_b = _load(TELEMETRY_DIR, run_id), _load(AGENTRX_DIR, run_id)
    assert len(arm_a["steps"]) == len(arm_b["steps"])
    for step_a, step_b in zip(arm_a["steps"], arm_b["steps"]):
        a_lines = step_a["substeps"][0]["content"].split("\n")
        b_lines = step_b["substeps"][0]["content"].split("\n")
        # B equals the semantic prefix of A …
        assert a_lines[: len(b_lines)] == b_lines
        # … and every extra line in A is a telemetry line.
        for extra in a_lines[len(b_lines) :]:
            assert extra.startswith(TELEMETRY_PREFIXES), (
                f"{run_id}: non-telemetry extra {extra!r}"
            )


AGENTRX_SUBMODULE = ROOT / "AgentRx"


@pytest.mark.parametrize("run_id", RUN_IDS)
def test_validates_against_agentrx_ir(run_id: str) -> None:
    if not AGENTRX_SUBMODULE.exists():
        pytest.skip("AgentRx submodule not initialized (git submodule update --init)")
    # Submodule present → a broken import is a real failure, never a silent skip.
    from agentrx.ir.trajectory_ir import validate_ir

    for directory in (TELEMETRY_DIR, AGENTRX_DIR):
        validate_ir(_load(directory, run_id))
