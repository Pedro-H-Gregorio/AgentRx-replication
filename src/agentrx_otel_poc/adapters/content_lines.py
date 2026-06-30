"""Build per-step `content` lines: semantic (both arms) and telemetry (arm A only).

Telemetry lines are generated separately and appended after the semantic lines,
so the parity check (PRD-06 §8) is a mechanical removal of a known line set.
"""

from __future__ import annotations

from .parser import ParsedStep


def semantic_lines(step: ParsedStep) -> list[str]:
    """Lines shared by both arms (PRD-06 §5): role, operation, observation, tool…"""
    lines = [f"Agent: {step.agent_name}", f"Operation: {step.operation}"]
    if step.role:
        lines.append(f"Role: {step.role}")
    lines.append(f"Status: {step.status}")
    if step.tool_name:
        lines.append(f"Tool: {step.tool_name}")
    if step.tool_args_json:
        lines.append(f"Tool args: {step.tool_args_json}")
    if step.tool_result_json:
        lines.append(f"Tool result: {step.tool_result_json}")
    if step.error_type:
        lines.append(f"Error: {step.error_type}: {step.error_message or ''}")
    if step.reasoning_summary:
        lines.append(f"Reasoning: {step.reasoning_summary}")
    if step.input_message:
        lines.append(f"Input: {step.input_message}")
    if step.output_message:
        lines.append(f"Output: {step.output_message}")
    if step.validation_status:
        lines.append(
            f"Validation: {step.validation_status} - {step.validation_reason or ''}"
        )
    if step.constraint_violations_json:
        lines.append(f"Constraints: {step.constraint_violations_json}")
    return lines


def telemetry_lines(step: ParsedStep) -> list[str]:
    """Lines exclusive to arm A (PRD-06 §6): duration, tokens, ids, events, infra."""
    t = step.telemetry
    lines = [
        f"duration_ms={t.get('duration_ms')}",
        f"tokens in/out/total={t.get('input_tokens')}/{t.get('output_tokens')}/{t.get('total_tokens')}",
        f"model={t.get('model')}",
        f"span_id={t.get('span_id')} parent_span_id={t.get('parent_span_id')} trace_id={t.get('trace_id')}",
        f"otel_status={t.get('otel_status')} kind={t.get('kind')}",
    ]
    event_names = [str(e.get("name")) for e in step.events]
    if event_names:
        lines.append(f"events=[{', '.join(event_names)}]")
    infra = [
        str(x)
        for x in (t.get("peer_service"), t.get("rpc_system"), t.get("http_method"))
        if x
    ]
    if infra:
        lines.append("infra=" + " ".join(infra))
    return lines
