"""Fallback accounting + strict mode (agent-llm-resilience spec).

Unit-tests `agent_message` degradation (tolerant counts, strict aborts, empty is
a degradation, USE_LLM=false is inert) and integration-tests that the run
manifest records `fallback_steps`/`use_llm_strict`, and that strict mode aborts a
run before any trajectory is written (no mixed corpus).
"""

from __future__ import annotations

import json
import types
from pathlib import Path

import pytest

from agentrx_otel_poc import paths
from agentrx_otel_poc.graph import agent_llm
from agentrx_otel_poc.graph.agent_llm import AgentLLMError, agent_message
from agentrx_otel_poc.graph.context import LLMStats
from agentrx_otel_poc.graph.runner import run_scenario
from agentrx_otel_poc.settings import Settings
from agentrx_otel_poc.tasks import load_benchmark

UNREACHABLE = "http://127.0.0.1:9/v1"  # port 9 (discard): connection refused, instant
TEST_MAS = "__pytest__"  # isolated corpus — never touches a real MAS corpus


def _ctx(**settings_kw):
    base = dict(use_llm=True, agent_max_retries=0, agent_base_url=UNREACHABLE)
    base.update(settings_kw)
    return types.SimpleNamespace(settings=Settings(**base), llm_stats=LLMStats())


def test_tolerant_counts_fallback_on_transport_failure(monkeypatch) -> None:
    def boom(*_a, **_k):
        raise RuntimeError("transport down")

    monkeypatch.setattr(agent_llm, "invoke_agent", boom)
    ctx = _ctx(use_llm_strict=False)
    text, usage = agent_message(ctx, "p", "TEMPLATE", label="Coordinator")
    assert text == "TEMPLATE"
    assert usage["total_tokens"] == 0
    assert ctx.llm_stats.fallback_steps == 1


def test_empty_response_is_a_counted_degradation(monkeypatch) -> None:
    monkeypatch.setattr(agent_llm, "invoke_agent", lambda *a, **k: ("   ", {}))
    ctx = _ctx(use_llm_strict=False)
    text, _ = agent_message(ctx, "p", "TEMPLATE", label="Researcher")
    assert text == "TEMPLATE"
    assert ctx.llm_stats.fallback_steps == 1


def test_strict_raises_with_node_label(monkeypatch) -> None:
    def boom(*_a, **_k):
        raise RuntimeError("429 exhausted")

    monkeypatch.setattr(agent_llm, "invoke_agent", boom)
    ctx = _ctx(use_llm_strict=True)
    with pytest.raises(AgentLLMError, match="Executor"):
        agent_message(ctx, "p", "TEMPLATE", label="Executor")
    assert ctx.llm_stats.fallback_steps == 0  # strict never falls back


def test_strict_raises_on_empty_response(monkeypatch) -> None:
    # Both degradation paths must abort in strict mode — empty is the second one.
    monkeypatch.setattr(agent_llm, "invoke_agent", lambda *a, **k: ("   ", {}))
    ctx = _ctx(use_llm_strict=True)
    with pytest.raises(AgentLLMError, match="empty response"):
        agent_message(ctx, "p", "TEMPLATE", label="Researcher")
    assert ctx.llm_stats.fallback_steps == 0


def test_use_llm_false_is_inert(monkeypatch) -> None:
    def fail(*_a, **_k):
        raise AssertionError("invoke_agent must not be called with USE_LLM=false")

    monkeypatch.setattr(agent_llm, "invoke_agent", fail)
    ctx = _ctx(use_llm=False)
    text, usage = agent_message(ctx, "p", "TEMPLATE", label="Coordinator")
    assert text == "TEMPLATE"
    assert usage["total_tokens"] == 0
    assert ctx.llm_stats.fallback_steps == 0


def _cleanup(run_id: str) -> None:
    (paths.otel_dir(TEST_MAS) / f"{run_id}.otel.json").unlink(missing_ok=True)
    (paths.ground_truth_dir(TEST_MAS) / f"{run_id}.ground_truth.json").unlink(
        missing_ok=True
    )
    (paths.logs_dir(TEST_MAS) / f"{run_id}.log").unlink(missing_ok=True)
    (paths.manifests_dir(TEST_MAS) / f"{run_id}.json").unlink(missing_ok=True)


def _manifest(run_id: str) -> dict:
    return json.loads(
        (paths.manifests_dir(TEST_MAS) / f"{run_id}.json").read_text(encoding="utf-8")
    )


def test_manifest_records_zero_fallback_when_deterministic() -> None:
    task_id = next(iter(load_benchmark()))
    run_id = "test_harden__det"
    # Explicit settings: the test must not depend on the developer's .env.
    settings = Settings(use_llm=False, use_llm_strict=False, mas_id=TEST_MAS)
    try:
        run_scenario(task_id, settings=settings, run_id=run_id)
        manifest = _manifest(run_id)
        assert manifest["fallback_steps"] == 0
        assert manifest["use_llm_strict"] is False
    finally:
        _cleanup(run_id)


def test_manifest_counts_every_degraded_step_tolerant() -> None:
    task_id = next(iter(load_benchmark()))
    run_id = "test_harden__degraded"
    settings = Settings(
        use_llm=True,
        use_llm_strict=False,
        agent_base_url=UNREACHABLE,
        agent_max_retries=0,
        mas_id=TEST_MAS,
    )
    try:
        run_scenario(task_id, settings=settings, run_id=run_id)
        # the four agent nodes (Coordinator/Researcher/Executor/Evaluator) degrade
        assert _manifest(run_id)["fallback_steps"] == 4
    finally:
        _cleanup(run_id)


def test_strict_aborts_run_before_writing_trajectory() -> None:
    task_id = next(iter(load_benchmark()))
    run_id = "test_harden__strict"
    settings = Settings(
        use_llm=True,
        use_llm_strict=True,
        agent_base_url=UNREACHABLE,
        agent_max_retries=0,
        mas_id=TEST_MAS,
    )
    try:
        with pytest.raises(AgentLLMError):
            run_scenario(task_id, settings=settings, run_id=run_id)
        otel = paths.otel_dir(TEST_MAS) / f"{run_id}.otel.json"
        assert not otel.exists()  # no mixed corpus
    finally:
        _cleanup(run_id)
