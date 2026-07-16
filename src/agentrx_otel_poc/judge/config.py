"""Judge run configuration: backend selection, subprocess env, experiment id.

Translates the project's `JUDGE_*` settings into the `AGENT_VERIFY_COPILOT_*`
environment the AgentRx copilot client reads, without the user ever touching
`AGENT_VERIFY_*` directly.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from agentrx_otel_poc import paths
from agentrx_otel_poc.settings import Settings

ROOT = Path(__file__).resolve().parents[3]
SHIM_DIR = ROOT / "scripts" / "judge_shims"
COPILOT_BACKEND = "copilot"


class JudgeConfigError(ValueError):
    """Raised when the judge backend config is invalid (fail before any rep)."""


@dataclass(frozen=True)
class JudgeConfig:
    backend: str
    model: str
    base_url: str | None
    timeout_seconds: float
    temperature: float
    mas_id: str  # corpus namespace this judge run reads/writes (ADR-0013)

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> JudgeConfig:
        s = settings or Settings()
        return cls(
            backend=s.judge_backend.strip().lower(),
            model=s.judge_model.strip(),
            base_url=(s.judge_base_url or None),
            timeout_seconds=s.judge_timeout_seconds,
            temperature=s.judge_temperature,
            mas_id=paths.resolve_mas_id(s),
        )

    def output_root(self) -> Path:
        """`data/internal/<mas_id>/agentrx/` — where this run's experiments live."""
        return paths.agentrx_root(self.mas_id)

    def shim_path(self) -> Path | None:
        """Absolute path to the shim binary, or None for the real Copilot CLI."""
        if self.backend == COPILOT_BACKEND:
            return None
        shim = SHIM_DIR / self.backend
        return shim if shim.exists() else None

    def validate(self) -> None:
        if self.backend == COPILOT_BACKEND:
            if not self._copilot_resolvable():
                raise JudgeConfigError(
                    "JUDGE_BACKEND=copilot but the Copilot CLI is not resolvable "
                    "(install it on PATH or set AGENT_VERIFY_COPILOT_BIN)"
                )
            return
        if self.backend == "openai" and not self.base_url:
            raise JudgeConfigError("JUDGE_BACKEND=openai requires JUDGE_BASE_URL")
        shim = self.shim_path()
        if shim is None or not os.access(shim, os.X_OK):
            known = sorted(p.name for p in SHIM_DIR.iterdir() if p.is_file())
            raise JudgeConfigError(
                f"unknown JUDGE_BACKEND {self.backend!r}: no executable shim at "
                f"{SHIM_DIR / self.backend} (available: 'copilot', {known})"
            )

    @staticmethod
    def _copilot_resolvable() -> bool:
        override = os.getenv("AGENT_VERIFY_COPILOT_BIN")
        if override and os.access(override, os.X_OK):
            return True
        return shutil.which("copilot") is not None

    def _binary(self) -> str | None:
        """The executable AgentRx would invoke as the judge (shim or real CLI)."""
        shim = self.shim_path()
        if shim is not None:
            return str(shim)
        override = os.getenv("AGENT_VERIFY_COPILOT_BIN")
        if override and os.access(override, os.X_OK):
            return override
        return shutil.which("copilot")

    def preflight(self) -> str | None:
        """Probe the backend with a trivial prompt; return an error msg or None.

        Catches broken auth / wrong model before running a whole matrix — the
        judge binary responds empty in those cases, which is invisible until a
        rep fails. Reuses the exact invocation AgentRx uses (same env, flags).
        """
        binary = self._binary()
        if binary is None:
            return f"judge backend {self.backend!r}: no runnable binary found"
        cmd = [binary, "-s", "--no-ask-user", "--allow-all", "--output-format", "text"]
        if self.model:
            cmd += ["--model", self.model]
        try:
            proc = subprocess.run(
                cmd,
                input="Reply with the single word: ok",
                env=self.subprocess_env(),
                capture_output=True,
                text=True,
                timeout=min(self.timeout_seconds, 120),
            )
        except (subprocess.SubprocessError, OSError) as exc:
            return f"judge backend probe failed: {exc}"
        if proc.returncode != 0 or not proc.stdout.strip():
            return (
                f"judge backend probe returned nothing "
                f"(exit {proc.returncode}): {proc.stderr.strip()[-200:]}"
            )
        return None

    def experiment_id(self) -> str:
        """Config-derived id (not a timestamp) so reruns resume the same tree.

        The stub is model-agnostic, so its id omits the model slug.
        """
        if self.backend == "stub":
            return "judge-stub"
        slug = re.sub(r"[^a-z0-9]+", "-", self.model.lower()).strip("-")
        return f"judge-{self.backend}" + (f"-{slug}" if slug else "")

    def subprocess_env(self) -> dict[str, str]:
        """Env for `AgentRx/run.py`: map JUDGE_* → AGENT_VERIFY_COPILOT_*."""
        env = os.environ.copy()
        env["AGENT_VERIFY_ENDPOINT_TYPE"] = "copilot"
        env["AGENT_VERIFY_COPILOT_TIMEOUT"] = str(int(self.timeout_seconds))
        if self.model:
            env["AGENT_VERIFY_COPILOT_MODEL"] = self.model
        shim = self.shim_path()
        if shim is not None:
            env["AGENT_VERIFY_COPILOT_BIN"] = str(shim)
        return env

    def manifest_fields(self) -> dict[str, object]:
        return {
            "mas_id": self.mas_id,
            "judge_backend": self.backend,
            "judge_model": self.model or None,
            "judge_base_url": self.base_url if self.backend == "openai" else None,
            # The Copilot CLI does not expose temperature (ADR-0011 / OQ4).
            "judge_temperature": self.temperature
            if self.backend == "openai"
            else "unknown",
        }
