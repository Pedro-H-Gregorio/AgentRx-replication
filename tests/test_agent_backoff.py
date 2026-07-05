"""Agent LLM transport backoff (agent-llm-resilience spec).

Drives the real `invoke_agent` against a local mock OpenAI-compatible server.
Covers: 429→429→200 retried; `Retry-After` honored over the exponential base;
exponential growth capped; 401 not retried; connection refused (service down)
not retried (fails fast to the fallback/strict path); timeout classified as
retryable. Also guards `max_retries=0` on the SDK client (no double-waiting).
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import httpx
import pytest
from openai import APIConnectionError, APITimeoutError

from agentrx_otel_poc import llm
from agentrx_otel_poc.settings import Settings

_RESPONSE = {
    "id": "x",
    "object": "chat.completion",
    "model": "mock",
    "choices": [
        {"index": 0, "message": {"role": "assistant", "content": "hi from llm"}}
    ],
    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
}


class _Handler(BaseHTTPRequestHandler):
    script: list[tuple[int, int | None]] = []  # (status, Retry-After or None)

    def log_message(self, *_a) -> None:  # silence the test server
        pass

    def do_POST(self) -> None:  # noqa: N802 (BaseHTTPRequestHandler API)
        self.rfile.read(int(self.headers.get("Content-Length", 0)))
        code, retry_after = (
            type(self).script.pop(0) if type(self).script else (200, None)
        )
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        if retry_after is not None:
            self.send_header("Retry-After", str(retry_after))
        self.end_headers()
        body = _RESPONSE if code == 200 else {"error": {"message": "boom"}}
        self.wfile.write(json.dumps(body).encode())


def _serve(script: list[tuple[int, int | None]]) -> tuple[HTTPServer, str]:
    handler = type("H", (_Handler,), {"script": list(script)})
    server = HTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}/v1"


def _settings(base_url: str, *, base: float = 0, cap: float = 0) -> Settings:
    return Settings(
        use_llm=True,
        agent_model="mock",
        agent_base_url=base_url,
        agent_api_key="test",
        agent_max_retries=5,
        agent_retry_base_seconds=base,
        agent_retry_max_seconds=cap,
        llm_timeout_seconds=5,
    )


def _run(monkeypatch, script, **settings_kw) -> tuple[str, dict, list[float]]:
    waits: list[float] = []
    monkeypatch.setattr(llm.time, "sleep", waits.append)
    server, base_url = _serve(script)
    try:
        text, usage = llm.invoke_agent(_settings(base_url, **settings_kw), "prompt")
    finally:
        server.shutdown()
    return text, usage, waits


def test_retries_429_then_succeeds(monkeypatch) -> None:
    text, usage, waits = _run(monkeypatch, [(429, None), (429, None), (200, None)])
    assert text == "hi from llm"
    assert usage["total_tokens"] == 2
    assert len(waits) == 2  # two retries before the 200


def test_retry_after_header_beats_exponential_base(monkeypatch) -> None:
    # base=99 would wait 99s; the header (7s) must win (spec: Retry-After honored).
    _, _, waits = _run(monkeypatch, [(429, 7), (200, None)], base=99, cap=120)
    assert waits == [7.0]


def test_exponential_growth_respects_base_and_cap(monkeypatch) -> None:
    script = [(429, None), (429, None), (429, None), (200, None)]
    _, _, waits = _run(monkeypatch, script, base=3, cap=10)
    assert waits == [3.0, 6.0, 10.0]  # 3×2^2=12 → capped at 10


def test_auth_error_is_not_retried(monkeypatch) -> None:
    waits: list[float] = []
    monkeypatch.setattr(llm.time, "sleep", waits.append)
    server, base_url = _serve([(401, None), (200, None)])  # the 200 must go unused
    try:
        with pytest.raises(Exception):  # noqa: B017 (any auth error, no retry)
            llm.invoke_agent(_settings(base_url), "prompt")
    finally:
        server.shutdown()
    assert waits == []  # 401 is not transport noise → no backoff


def test_connection_refused_is_not_retried(monkeypatch) -> None:
    # GAP-A: a DOWN endpoint must fail fast (no ~155s of exponential waiting) —
    # waiting does not bring a dead service back; fallback/strict handles it.
    waits: list[float] = []
    monkeypatch.setattr(llm.time, "sleep", waits.append)
    settings = _settings("http://127.0.0.1:9/v1", base=5, cap=120)  # nothing listens
    with pytest.raises(APIConnectionError):
        llm.invoke_agent(settings, "prompt")
    assert waits == []  # zero retries despite agent_max_retries=5


def test_timeout_is_retryable_but_plain_connection_error_is_not() -> None:
    request = httpx.Request("POST", "http://mock/v1/chat/completions")
    assert llm._is_retryable(APITimeoutError(request=request)) is True
    assert llm._is_retryable(APIConnectionError(request=request)) is False


def test_client_built_with_no_sdk_retries() -> None:
    # Guard against double-waiting: our loop owns retries, the SDK must not.
    client = llm._client("mock", "http://x/v1", "k", _settings("http://x/v1"))
    assert client.max_retries == 0
