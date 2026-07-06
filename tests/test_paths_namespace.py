"""Corpus namespace resolution (project-structure spec, ADR-0013).

The mas_id is the effective config value used literally (case/dots preserved),
only folding path-breaking chars. Two models resolve to disjoint roots, so a run
with a different agent model never overwrites a prior corpus.
"""

from __future__ import annotations

from agentrx_otel_poc import paths
from agentrx_otel_poc.settings import Settings


def test_default_is_agent_model_literal() -> None:
    assert paths.resolve_mas_id(Settings(agent_model="Llama3.1-8B")) == "Llama3.1-8B"
    assert paths.resolve_mas_id(Settings(agent_model="Qwen2.5-14B")) == "Qwen2.5-14B"


def test_mas_id_env_overrides_agent_model() -> None:
    s = Settings(agent_model="Llama3.1-8B", mas_id="experiment-a")
    assert paths.resolve_mas_id(s) == "experiment-a"


def test_path_breaking_chars_are_folded() -> None:
    # OpenRouter-style names with '/' and ':' must become a single dir segment.
    got = paths.resolve_mas_id(Settings(agent_model="qwen/qwen-2.5-72b:free"))
    assert got == "qwen-qwen-2.5-72b-free"
    assert "/" not in got and ":" not in got


def test_two_models_do_not_collide() -> None:
    a = paths.mas_root(paths.resolve_mas_id(Settings(agent_model="llama")))
    b = paths.mas_root(paths.resolve_mas_id(Settings(agent_model="qwen")))
    assert a != b
    assert a.name == "llama" and b.name == "qwen"
    # every subdir of the corpus is disjoint between the two models
    for sub in (paths.otel_dir, paths.ground_truth_dir, paths.agentrx_root):
        assert sub("llama") != sub("qwen")


def test_results_root_follows_mas_id() -> None:
    assert paths.results_root("llama").name == "llama"
    assert paths.results_root("llama") != paths.results_root("qwen")
