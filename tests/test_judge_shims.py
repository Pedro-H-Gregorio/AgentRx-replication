"""Contract tests for the judge shims (judge-backends spec, task 2.3).

Pins the Copilot-CLI contract the AgentRx copilot client relies on: accept the
flags, read the prompt from stdin, print the verdict to stdout, answer
`--version`. Guards against the shims drifting from `copilot_cli.py`.
"""

from __future__ import annotations

import http.server
import json
import subprocess
import threading
from pathlib import Path

import pytest

SHIM_DIR = Path(__file__).resolve().parent.parent / "scripts" / "judge_shims"
CLI_FLAGS = ["-s", "--no-ask-user", "--allow-all", "--output-format", "text"]


def _run(name: str, *args: str, stdin: str = "", env: dict | None = None):
    return subprocess.run(
        [str(SHIM_DIR / name), *args],
        input=stdin,
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )


@pytest.mark.parametrize("name", ["stub", "openai", "codex"])
def test_version_exits_zero(name: str) -> None:
    proc = _run(name, "--version")
    assert proc.returncode == 0
    assert proc.stdout.strip()


def test_stub_emits_valid_verdict() -> None:
    proc = _run("stub", *CLI_FLAGS, "--model", "whatever", stdin="a trajectory")
    assert proc.returncode == 0
    verdict = json.loads(proc.stdout)
    assert isinstance(verdict["failure_case"], int)
    assert isinstance(verdict["index"], int)


def test_stub_is_deterministic() -> None:
    a = _run("stub", *CLI_FLAGS, stdin="prompt one")
    b = _run("stub", *CLI_FLAGS, stdin="prompt two")
    assert a.stdout == b.stdout


def test_openai_missing_base_url_fails_empty() -> None:
    proc = _run("openai", *CLI_FLAGS, stdin="x", env={"PATH": "/usr/bin:/bin"})
    assert proc.returncode != 0
    assert proc.stdout.strip() == ""


def _serve_429_then_200(fail_times: int):
    """Local endpoint: first *fail_times* POSTs return 429, then a 200 verdict."""
    state = {"n": 0}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            self.rfile.read(int(self.headers.get("Content-Length", 0)))
            state["n"] += 1
            if state["n"] <= fail_times:
                self.send_response(429)
                self.send_header("Retry-After", "1")
                self.end_headers()
                self.wfile.write(b"{}")
            else:
                body = json.dumps(
                    {"choices": [{"message": {"content": "VERDICT-OK"}}]}
                ).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(body)

        def log_message(self, *args):  # silence
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def test_openai_retries_on_429_then_succeeds(tmp_path) -> None:
    server = _serve_429_then_200(fail_times=2)
    port = server.server_address[1]
    meta = tmp_path / "judge_meta.json"
    try:
        proc = _run(
            "openai",
            *CLI_FLAGS,
            stdin="prompt",
            env={
                "PATH": "/usr/bin:/bin",
                "JUDGE_BASE_URL": f"http://127.0.0.1:{port}",
                "JUDGE_MODEL": "m",
                "JUDGE_MAX_RETRIES": "5",
                "JUDGE_RETRY_BASE_SECONDS": "1",
                "JUDGE_META_FILE": str(meta),
            },
        )
    finally:
        server.shutdown()
    assert proc.returncode == 0
    assert proc.stdout.strip() == "VERDICT-OK"
    assert json.loads(meta.read_text())["retries"] == 2
