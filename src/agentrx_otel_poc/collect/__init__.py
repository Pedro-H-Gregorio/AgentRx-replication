"""Neutral collection of judge verdicts into the PRD-10 result CSVs (C7).

Reads `data/internal/agentrx/<experiment_id>/` and writes the three CSVs under
`data/experiment/results/<experiment_id>/`. Aggregation replicates AgentRx's
`compute_stats` (flat pooling of the ok reps' failures); no analytical choice is
made here. The `agentrx` package is never imported.
"""

from __future__ import annotations

from .reader import CollectError
from .run import RESULTS_ROOT, collect, collect_experiment

__all__ = ["CollectError", "RESULTS_ROOT", "collect", "collect_experiment"]
