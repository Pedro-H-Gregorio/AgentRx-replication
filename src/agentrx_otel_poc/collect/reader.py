"""Load one judge experiment from disk into plain, collector-ready structures."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from agentrx_otel_poc.judge.config import ROOT
from agentrx_otel_poc.judge.scoring import failures_for

DATA_INTERNAL = ROOT / "data" / "internal"
VERDICT_STATUS = {"ok", "skipped"}


class CollectError(RuntimeError):
    """Raised when an experiment on disk is inconsistent (fail loud, never guess)."""


@dataclass(frozen=True)
class RepData:
    rep: int
    run_dir: str
    failures: list[tuple[int, int]]
    effective_model: str | None
    run1_mtime: float


@dataclass
class PairData:
    """Every verdict-carrying rep of one (arm, run_id) trajectory, plus context."""

    run_id: str
    arm: str
    reps: list[RepData] = field(default_factory=list)
    n_error_reps: int = 0
    ground_truth: dict = field(default_factory=dict)
    n_steps: int = 0
    judge_model: str = ""
    mas_id: str = ""


def _rows(exp_dir: Path) -> list[dict]:
    index = exp_dir / "runs_index.jsonl"
    if not index.exists():
        raise CollectError(f"no runs_index.jsonl in {exp_dir}")
    return [json.loads(x) for x in index.read_text(encoding="utf-8").splitlines() if x]


def _rep_failures(exp_dir: Path, run_dir: str, run_id: str) -> list[tuple[int, int]]:
    run1 = exp_dir / run_dir / "judge_output" / "runs" / "run1.json"
    return [
        (int(f["failure_case"]), int(f["step_number"]))
        for f in failures_for(run1, run_id)
    ]


def _n_steps(data_internal: Path, arm: str, run_id: str) -> int:
    traj = data_internal / f"trajectory_{arm}" / f"{run_id}.json"
    data = json.loads(traj.read_text(encoding="utf-8"))
    return len(data.get("steps", []))


def _resolve_model(pair: PairData, manifest_model: str) -> str:
    """The model that judged this pair: the reps' uniform effective_model, else
    the manifest's (GAP-2). Divergent effective models are an integrity error."""
    models = {rep.effective_model for rep in pair.reps if rep.effective_model}
    if len(models) > 1:
        raise CollectError(
            f"{pair.arm}/{pair.run_id}: reps disagree on effective_model {sorted(models)}"
        )
    return models.pop() if models else manifest_model


def load_experiment(
    exp_dir: Path, data_internal: Path = DATA_INTERNAL
) -> list[PairData]:
    """Pairs with ≥1 verdict rep (`ok`/`skipped`); `error` reps are counted."""
    manifest = json.loads((exp_dir / "manifest.json").read_text(encoding="utf-8"))
    manifest_model = manifest.get("judge_model") or ""
    pairs: dict[tuple[str, str], PairData] = {}
    for row in _rows(exp_dir):
        key = (row["arm"], row["run_id"])
        pair = pairs.setdefault(key, PairData(run_id=row["run_id"], arm=row["arm"]))
        if row.get("status") not in VERDICT_STATUS:
            pair.n_error_reps += 1
            continue
        run1 = exp_dir / row["run_dir"] / "judge_output" / "runs" / "run1.json"
        pair.reps.append(
            RepData(
                rep=int(row["rep"]),
                run_dir=row["run_dir"],
                failures=_rep_failures(exp_dir, row["run_dir"], row["run_id"]),
                effective_model=row.get("effective_model"),
                run1_mtime=run1.stat().st_mtime if run1.exists() else 0.0,
            )
        )
    with_verdict = [p for p in pairs.values() if p.reps]
    gt_dir = data_internal / "ground_truth"
    mas_id = data_internal.name
    for pair in with_verdict:
        pair.reps.sort(key=lambda r: r.rep)
        pair.judge_model = _resolve_model(pair, manifest_model)
        pair.mas_id = mas_id
        gt_path = gt_dir / f"{pair.run_id}.ground_truth.json"
        pair.ground_truth = json.loads(gt_path.read_text(encoding="utf-8"))
        pair.n_steps = _n_steps(data_internal, pair.arm, pair.run_id)
    fully_errored = [p for p in pairs.values() if not p.reps]
    if fully_errored:
        names = ", ".join(f"{p.arm}/{p.run_id}" for p in fully_errored)
        print(f"[collect]   excluded (no valid verdict): {names}")
    return sorted(with_verdict, key=lambda p: (p.arm, p.run_id))
