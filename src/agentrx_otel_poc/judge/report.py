"""Manifest, run index (rebuilt from disk), and the per-category summary.

The index is the C7 hand-off: one JSONL line per rep. It is reconstructed by
scanning the experiment tree so it always mirrors disk, never drifting from a
stale in-memory list (judge-execution spec).
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path

from .config import ROOT, JudgeConfig
from .planner import GT_DIR
from .scoring import has_verdict, score


def _git_sha(cwd: Path) -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return out.stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def write_manifest(exp_dir: Path, config: JudgeConfig, selection: dict) -> None:
    exp_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "experiment_id": config.experiment_id(),
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "repo_git_sha": _git_sha(ROOT),
        "agentrx_git_sha": _git_sha(ROOT / "AgentRx"),
        "selection": selection,
        **config.manifest_fields(),
    }
    (exp_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )


def _meta(rep_dir: Path) -> dict:
    """Shim-reported metadata for a rep (effective_model, retries), else {}."""
    meta = rep_dir / "judge_meta.json"
    if not meta.exists():
        return {}
    try:
        return json.loads(meta.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}


def rebuild_index(exp_dir: Path, session_status: dict) -> list[dict]:
    """Scan every rep dir under *exp_dir* → sorted index rows (disk is truth)."""
    rows: list[dict] = []
    for rep_dir in exp_dir.glob("*/*/rep*"):
        if not rep_dir.is_dir():
            continue
        arm, run_id, rep = rep_dir.parent.parent.name, rep_dir.parent.name, rep_dir.name
        key = (arm, run_id, int(rep[3:]))
        run1 = rep_dir / "judge_output" / "runs" / "run1.json"
        valid = has_verdict(run1, run_id)
        meta = _meta(rep_dir)
        row = {
            "run_id": run_id,
            "arm": arm,
            "rep": key[2],
            "status": session_status.get(key) or ("ok" if valid else "error"),
            "run_dir": str(rep_dir.relative_to(exp_dir)),
            "effective_model": meta.get("effective_model"),
            "retries": meta.get("retries", 0),
        }
        gt_path = GT_DIR / f"{run_id}.ground_truth.json"
        if valid and gt_path.exists():
            gt = json.loads(gt_path.read_text(encoding="utf-8"))
            row.update(score(run1, gt, run_id))
        rows.append(row)
    rows.sort(key=lambda r: (r["arm"], r["run_id"], r["rep"]))
    return rows


def write_index(exp_dir: Path, rows: list[dict]) -> Path:
    path = exp_dir / "runs_index.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    return path


def summarize(rows: list[dict]) -> str:
    """Per-category sanity table: reps, category hits, step hits, errors."""
    cats: dict[str, dict[str, int]] = {}
    for row in rows:
        cat = row.get("gt_category", "?")
        agg = cats.setdefault(cat, {"reps": 0, "cat": 0, "step": 0, "err": 0})
        agg["reps"] += 1
        if row["status"] == "error":
            agg["err"] += 1
        if row.get("hit_category"):
            agg["cat"] += 1
        if row.get("hit_step"):
            agg["step"] += 1
    header = f"{'fault category':<38}{'reps':>5}{'cat_hit':>9}{'step_hit':>9}{'err':>5}"
    lines = [header, "-" * len(header)]
    for cat in sorted(cats):
        a = cats[cat]
        lines.append(f"{cat:<38}{a['reps']:>5}{a['cat']:>9}{a['step']:>9}{a['err']:>5}")
    return "\n".join(lines)
