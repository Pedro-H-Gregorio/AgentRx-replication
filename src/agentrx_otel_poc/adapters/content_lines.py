"""Per-step content: semantic facts (both arms) and the telemetry block (arm A).

`semantic_fields` is the single source of the semantic facts, so the prose renderer
(`semantic_lines`, arm B) and the JSON builder (arm A) encode the *same* facts by
construction — that is what the semantic-parity check verifies (PRD-06 §8). The
`telemetry` block is arm A only: it never becomes a structured IR field (invariant
#6); it lives inside the `content` string, now as JSON instead of free text.
"""

from __future__ import annotations

import re
from typing import Any

from .parser import ParsedStep

_STACKTRACE_ATTR = "exception.stacktrace"
# Machine-specific `File ".../src/pkg/mod.py"` → `File "src/pkg/mod.py"` (drops the
# absolute prefix: home dir, `mestrado`, `replicacao-agentrx` — experiment-context
# hints and non-reproducible bytes). The `src/`-relative path is kept (realistic).
_ABS_PATH = re.compile(r'File "[^"]*?/(src/[^"]*)"')
# Fully-qualified exception header `pkg.mod.SomeError: msg` → `SomeError: msg`
# (mirrors the bare `exception.type`; drops `mock_tools` and the module path).
_FQN_HEADER = re.compile(r"(?m)^[A-Za-z_][\w.]*\.(\w+): ")


def semantic_fields(step: ParsedStep) -> dict[str, Any]:
    """The semantic facts shared by both arms (PRD-06 §5), ordered for stable output.

    Only fields present in the step appear (matching the prose renderer's optionality),
    so a happy-path step and a fault step both use the same template — no marker ever
    denounces the injected category (invariant #7).
    """
    fields: dict[str, Any] = {"agent": step.agent_name, "operation": step.operation}
    if step.role:
        fields["role"] = step.role
    fields["status"] = step.status
    if step.tool_name:
        fields["tool_name"] = step.tool_name
    if step.tool_parameters_json:
        fields["tool_parameters"] = step.tool_parameters_json
    if step.tool_args_json:
        fields["tool_args"] = step.tool_args_json
    if step.tool_result_json:
        fields["tool_result"] = step.tool_result_json
    if step.error_type:
        fields["error"] = {"type": step.error_type, "message": step.error_message or ""}
    if step.plan_query_json:
        fields["plan_query"] = step.plan_query_json
    if step.plan_text:
        fields["plan"] = step.plan_text
    if step.input_message:
        fields["input"] = step.input_message
    if step.output_message:
        fields["output"] = step.output_message
    if step.validation_status:
        fields["validation"] = {
            "status": step.validation_status,
            "reason": step.validation_reason or "",
        }
    if step.constraint_violations_json:
        fields["constraints"] = step.constraint_violations_json
    return fields


_PROSE_LINE: dict[str, Any] = {
    "agent": lambda v: f"Agent: {v}",
    "operation": lambda v: f"Operation: {v}",
    "role": lambda v: f"Role: {v}",
    "status": lambda v: f"Status: {v}",
    "tool_name": lambda v: f"Tool: {v}",
    "tool_parameters": lambda v: f"Tool parameters: {v}",
    "tool_args": lambda v: f"Tool args: {v}",
    "tool_result": lambda v: f"Tool result: {v}",
    "error": lambda v: f"Error: {v['type']}: {v['message']}",
    "plan_query": lambda v: f"Plan query: {v}",
    "plan": lambda v: f"Plan: {v}",
    "input": lambda v: f"Input: {v}",
    "output": lambda v: f"Output: {v}",
    "validation": lambda v: f"Validation: {v['status']} - {v['reason']}",
    "constraints": lambda v: f"Constraints: {v}",
}


def render_prose(fields: dict[str, Any]) -> list[str]:
    """Render a semantic-fields dict as prose lines. Shared by the arm-B renderer and
    the parity check, so 'arm A's facts rendered as prose == arm B' is a real test."""
    return [_PROSE_LINE[key](value) for key, value in fields.items()]


def semantic_lines(step: ParsedStep) -> list[str]:
    """Arm B (prose): render the semantic facts, one field per line (baseline do artigo)."""
    return render_prose(semantic_fields(step))


def telemetry_block(step: ParsedStep) -> dict[str, Any]:
    """Arm A only (PRD-06 §6): duration, tokens, ids, events with attributes, infra e,
    em passos de erro, o stacktrace (já sanitizado na fase `sanitize`)."""
    t = step.telemetry
    block: dict[str, Any] = {
        "duration_ms": t.get("duration_ms"),
        "tokens": {
            "input": t.get("input_tokens"),
            "output": t.get("output_tokens"),
            "total": t.get("total_tokens"),
        },
        "model": t.get("model"),
        "span": {
            "span_id": t.get("span_id"),
            "parent_span_id": t.get("parent_span_id"),
            "trace_id": t.get("trace_id"),
        },
        "otel_status": t.get("otel_status"),
        "kind": t.get("kind"),
    }
    events = _events_with_attrs(step.events)
    if events:
        block["events"] = events
    infra = {
        key: value
        for key, value in (
            ("peer_service", t.get("peer_service")),
            ("rpc_system", t.get("rpc_system")),
            ("http_method", t.get("http_method")),
        )
        if value
    }
    if infra:
        block["infra"] = infra
    stacktrace = _stacktrace(step.events)
    if stacktrace:
        block["stacktrace"] = stacktrace
    return block


def _events_with_attrs(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Events as {name, attributes} — the promoted stacktrace attribute is omitted here
    (it surfaces once, as the block's `stacktrace`)."""
    out: list[dict[str, Any]] = []
    for event in events:
        attrs = {
            key: value
            for key, value in (event.get("attributes") or {}).items()
            if key != _STACKTRACE_ATTR
        }
        out.append({"name": event.get("name"), "attributes": attrs})
    return out


def _stacktrace(events: list[dict[str, Any]]) -> str | None:
    for event in events:
        if event.get("name") == "exception":
            trace = (event.get("attributes") or {}).get(_STACKTRACE_ATTR)
            if isinstance(trace, str) and trace:
                return _normalize_stacktrace(trace)
    return None


def _normalize_stacktrace(trace: str) -> str:
    """Strip machine-specific paths and module prefixes so the stacktrace reads like a
    generic application trace — reproducible across machines and free of
    experiment-context hints (GAP-1). The `src/`-relative frame path is preserved."""
    trace = _ABS_PATH.sub(r'File "\1"', trace)
    return _FQN_HEADER.sub(r"\1: ", trace)
