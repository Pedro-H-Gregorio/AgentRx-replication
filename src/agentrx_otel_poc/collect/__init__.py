"""Neutral collection of judge verdicts into the PRD-10 result CSVs (C7).

Reads `data/internal/<mas_id>/agentrx/<judge_id>/` and writes the three CSVs under
`data/experiment/results/<mas_id>/<judge_id>/`. Aggregation replicates AgentRx's
`compute_stats` (flat pooling of the verdict reps' failures); no analytical choice
is made here. The `agentrx` package is never imported.
"""

from __future__ import annotations

from .reader import CollectError
from .run import collect, collect_experiment

__all__ = ["CollectError", "collect", "collect_experiment"]
