"""tasks.py loads scenarios from benchmark_30.json (no hardcoded task dict)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentrx_otel_poc import tasks
from agentrx_otel_poc.tasks import build_ground_truth, get_task_spec, load_benchmark

ROOT = Path(__file__).resolve().parent.parent
BENCHMARK = ROOT / "data" / "benchmark" / "benchmark_30.json"


def test_loads_all_scenarios() -> None:
    expected = {s["task_id"] for s in json.loads(BENCHMARK.read_text(encoding="utf-8"))}
    assert set(load_benchmark()) == expected


def test_get_by_task_id_roundtrip() -> None:
    task_id = next(iter(load_benchmark()))
    spec = get_task_spec(task_id)
    assert spec.task_id == task_id
    assert spec.domain == "product_catalog"


def test_unknown_task_id_raises() -> None:
    with pytest.raises(ValueError):
        get_task_spec("does_not_exist")


def test_no_hardcoded_task_dict() -> None:
    assert not hasattr(tasks, "TASKS")


def test_ground_truth_matches_injection_node() -> None:
    spec = get_task_spec(next(iter(load_benchmark())))
    gt = build_ground_truth(spec)
    assert gt["failure_category"] == spec.target_fault_category
    assert gt["critical_failure_step"] == tasks.NODE_STEP[spec.injection_node]
