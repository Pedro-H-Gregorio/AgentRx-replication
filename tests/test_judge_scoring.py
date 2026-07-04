"""Scoring unit tests (judge-validation spec, tasks 3.3/4.3).

Covers the AgentRx-replicating prediction (mode + round-mean), the FailureCase
mapping, inconclusive handling, and hit/miss against ground truth.
"""

from __future__ import annotations

import json

import pytest

from agentrx_otel_poc.judge.config import JudgeConfig, JudgeConfigError
from agentrx_otel_poc.judge.report import rebuild_index
from agentrx_otel_poc.judge.scoring import (
    FAILURE_CASE_TO_CATEGORY,
    has_verdict,
    predict,
    score,
)


def _write_run1(rep_dir, failures: list[dict], run_id: str = "q01") -> None:
    runs = rep_dir / "judge_output" / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    (runs / "run1.json").write_text(
        json.dumps({"detailed_results": [{"task_id": run_id, "failures": failures}]})
    )


def _failures(*pairs: tuple[int, int]) -> list[dict]:
    return [{"failure_case": c, "step_number": s} for c, s in pairs]


def test_predict_single_failure() -> None:
    cat, step, cases = predict(_failures((9, 3)))
    assert (cat, step, cases) == ("System Failure", 3, [9])


def test_predict_mode_and_round_mean() -> None:
    # cases {3,3,9} → mode 3 (Invalid Invocation); steps {2,2,5} → round(3.0)=3
    cat, step, _ = predict(_failures((3, 2), (3, 2), (9, 5)))
    assert cat == "Invalid Invocation"
    assert step == 3


def test_predict_inconclusive_is_miss() -> None:
    cat, step, cases = predict(_failures((10, 4)))
    assert cat is None
    assert cases == [10]


def test_mapping_covers_five_categories() -> None:
    assert set(FAILURE_CASE_TO_CATEGORY) == {1, 2, 3, 4, 9}


def test_score_hit(tmp_path) -> None:
    run1 = tmp_path / "run1.json"
    run1.write_text(
        json.dumps(
            {"detailed_results": [{"task_id": "q01", "failures": _failures((9, 3))}]}
        )
    )
    gt = {"failure_category": "System Failure", "critical_failure_step": 3}
    result = score(run1, gt, "q01")
    assert result["hit_category"] and result["hit_step"]


def test_score_miss_category(tmp_path) -> None:
    run1 = tmp_path / "run1.json"
    run1.write_text(
        json.dumps(
            {"detailed_results": [{"task_id": "q01", "failures": _failures((4, 3))}]}
        )
    )
    gt = {"failure_category": "System Failure", "critical_failure_step": 3}
    result = score(run1, gt, "q01")
    assert result["hit_category"] is False
    assert result["hit_step"] is True


def _cfg(**kw) -> JudgeConfig:
    base = dict(
        backend="stub", model="", base_url=None, timeout_seconds=600, temperature=0
    )
    base.update(kw)
    return JudgeConfig(**base)


def test_config_openai_requires_base_url() -> None:
    with pytest.raises(JudgeConfigError):
        _cfg(backend="openai", base_url=None).validate()


def test_config_experiment_id_slug() -> None:
    cfg = _cfg(backend="openai", base_url="http://x/v1", model="qwen2.5:14b")
    assert cfg.experiment_id() == "judge-openai-qwen2-5-14b"


def test_has_verdict_distinguishes_empty_from_no_error(tmp_path) -> None:
    empty = tmp_path / "empty.json"
    empty.write_text(
        json.dumps({"detailed_results": [{"task_id": "q01", "failures": []}]})
    )
    no_error = tmp_path / "noerror.json"
    no_error.write_text(
        json.dumps(
            {"detailed_results": [{"task_id": "q01", "failures": _failures((0, 0))}]}
        )
    )
    assert has_verdict(empty, "q01") is False  # judge returned nothing
    assert has_verdict(no_error, "q01") is True  # legit "no error" is a verdict


def test_rebuild_index_flags_empty_verdict_as_error(tmp_path) -> None:
    # exp_dir/<arm>/<run_id>/rep1/... — empty verdict must not read as ok.
    _write_run1(tmp_path / "telemetry" / "q01" / "rep1", failures=[])
    _write_run1(tmp_path / "telemetry" / "q02" / "rep1", failures=_failures((9, 3)))
    rows = {r["run_id"]: r for r in rebuild_index(tmp_path, session_status={})}
    assert rows["q01"]["status"] == "error"
    assert rows["q02"]["status"] == "ok"
