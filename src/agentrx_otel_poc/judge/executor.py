"""Run one rep through the AgentRx judge as a black box (subprocess + files).

Pre-plants the arm trajectory as `<run_dir>/trajectory_ir.json` (byte-identical
copy) so AgentRx's IR stage is skipped — the domain converter never touches our
canonical IR (judge-execution spec). Then shells out to `AgentRx/run.py
--stage judge`. The submodule is never imported.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from .config import ROOT, JudgeConfig
from .scoring import has_verdict

AGENTRX_RUN = ROOT / "AgentRx" / "run.py"


@dataclass(frozen=True)
class RepResult:
    status: str
    run1_path: Path
    detail: str = ""
    log_path: Path | None = None


def _run1_path(run_dir: Path) -> Path:
    return run_dir / "judge_output" / "runs" / "run1.json"


def _text(value: object) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return value or ""


def _write_log(run_dir: Path, cmd: list[str], stdout: object, stderr: object) -> Path:
    """Persist the full AgentRx output so the judge run is observable."""
    log_path = run_dir / "agentrx.log"
    log_path.write_text(
        f"$ {' '.join(cmd)}\n\n=== stdout ===\n{_text(stdout)}\n"
        f"=== stderr ===\n{_text(stderr)}\n",
        encoding="utf-8",
    )
    return log_path


def _retries(run_dir: Path) -> int:
    """Retry count a shim recorded for this rep (judge_meta.json), else 0."""
    meta = run_dir / "judge_meta.json"
    if not meta.exists():
        return 0
    try:
        return int(json.loads(meta.read_text(encoding="utf-8")).get("retries", 0))
    except (ValueError, OSError):
        return 0


def run_rep(
    run_dir: Path, traj_path: Path, config: JudgeConfig, *, force: bool = False
) -> RepResult:
    run1 = _run1_path(run_dir)
    run_id = traj_path.stem
    # A rerun skips only a *real* verdict; an empty one (auth/rate-limit failure)
    # is re-judged, never silently kept.
    if not force and has_verdict(run1, run_id):
        return RepResult("skipped", run1)

    run_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(traj_path, run_dir / "trajectory_ir.json")

    # A shim may drop `{"effective_model": ...}` here (the model actually served,
    # unknown to config when JUDGE_MODEL is empty or the provider renames it).
    meta_file = run_dir / "judge_meta.json"
    meta_file.unlink(missing_ok=True)
    env = config.subprocess_env()
    env["JUDGE_META_FILE"] = str(meta_file)

    cmd = [
        sys.executable,
        str(AGENTRX_RUN),
        str(traj_path),
        "--stage",
        "judge",
        "--run-dir",
        str(run_dir),
        "--endpoint",
        "copilot",
    ]
    try:
        proc = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=config.timeout_seconds + 60,
        )
    except subprocess.TimeoutExpired as exc:
        log = _write_log(run_dir, cmd, exc.stdout or "", exc.stderr or "")
        return RepResult("error", run1, "timeout", log)
    except OSError as exc:
        log = _write_log(run_dir, cmd, "", str(exc))
        return RepResult("error", run1, f"spawn failed: {exc}", log)

    log = _write_log(run_dir, cmd, proc.stdout, proc.stderr)
    if proc.returncode != 0:
        return RepResult("error", run1, _tail(proc.stderr), log)
    if not run1.exists():
        return RepResult("error", run1, "no run1.json produced", log)
    if not has_verdict(run1, run_id):
        # Valid JSON but zero failures → the judge returned nothing (empty
        # response / unauthenticated backend). Flag it so ONLY=errors retries it.
        return RepResult(
            "error", run1, "empty verdict (judge returned no failure)", log
        )
    retries = _retries(run_dir)
    detail = f"retries={retries}" if retries else ""
    return RepResult("ok", run1, detail, log)


def _tail(text: str, limit: int = 300) -> str:
    return (text or "").strip()[-limit:]
