"""The simulated MAS graph (Coordinator → Researcher → Tool → Executor → Evaluator)."""

from __future__ import annotations

from .builder import build_graph
from .context import GraphContext
from .runner import run_scenario

__all__ = ["build_graph", "GraphContext", "run_scenario"]
