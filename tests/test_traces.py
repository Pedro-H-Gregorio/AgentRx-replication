"""Validator for simulated traces: fault.injected at the right node + ground truth."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentrx_otel_poc.tasks import NODE_STEP, load_benchmark

ROOT = Path(__file__).resolve().parent.parent
OTEL_DIR = ROOT / "data" / "internal" / "otel"
GT_DIR = ROOT / "data" / "internal" / "ground_truth"


def _scenarios_with_traces() -> list[tuple[str, dict]]:
    benchmark = load_benchmark()
    pairs = []
    for task_id, spec in benchmark.items():
        otel = OTEL_DIR / f"{task_id}.otel.json"
        if otel.exists():
            pairs.append((task_id, spec))
    return pairs


PAIRS = _scenarios_with_traces()


def test_traces_exist() -> None:
    assert PAIRS, "no traces found — run `make simulate` first"


@pytest.mark.parametrize("task_id_spec", PAIRS, ids=lambda p: p[0])
def test_fault_injected_at_expected_node(task_id_spec) -> None:
    task_id, spec = task_id_spec
    payload = json.loads(
        (OTEL_DIR / f"{task_id}.otel.json").read_text(encoding="utf-8")
    )
    nodes = [
        event["attributes"]["node"]
        for span in payload["spans"]
        for event in span.get("events", [])
        if event["name"] == "fault.injected"
    ]
    assert nodes == [spec.injection_node], f"{task_id}: fault.injected nodes {nodes}"


@pytest.mark.parametrize("task_id_spec", PAIRS, ids=lambda p: p[0])
def test_ground_truth_matches(task_id_spec) -> None:
    task_id, spec = task_id_spec
    gt = json.loads(
        (GT_DIR / f"{task_id}.ground_truth.json").read_text(encoding="utf-8")
    )
    assert gt["failure_category"] == spec.target_fault_category
    assert gt["critical_failure_step"] == NODE_STEP[spec.injection_node]
