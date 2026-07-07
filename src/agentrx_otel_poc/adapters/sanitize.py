"""Leakage prevention (PRD-06 R1/R2): strip ground-truth markers from parsed steps.

Removes the `fault.injected` event and any attribute value that reveals the injection
code, before either arm is rendered. Since the System Failure stacktrace is now clean
at the source (2A), it is kept — but still scrubbed defensively: any value carrying a
leak token is dropped, and the event `exception.type` FQN is reduced to the bare class
name (mirroring the span `error.type`). The raw `.otel.json` keeps everything; only the
derived trajectories are cleaned.
"""

from __future__ import annotations

from .parser import ParsedStep, ParsedTrajectory

_LEAK_EVENTS = {"fault.injected"}
_EXCEPTION_TYPE_ATTR = "exception.type"
_LEAK_TOKENS = (
    "fault.injected",
    "experiment.fault",
    "faults.py",
    "faults.",  # dotted module path, e.g. `...faults.base.CatalogServiceTimeoutError`
    "operators.py",
    "maybe_raise",
    "/faults",
    "faults/",
)


def _is_leak(value: object) -> bool:
    return isinstance(value, str) and any(tok in value for tok in _LEAK_TOKENS)


def _bare_type(value: object) -> object:
    """Reduce a fully-qualified exception type to its bare class name."""
    return value.rsplit(".", 1)[-1] if isinstance(value, str) else value


def sanitize_step(step: ParsedStep) -> ParsedStep:
    clean_events = []
    for event in step.events:
        if event.get("name") in _LEAK_EVENTS:
            continue
        attrs = {}
        for key, value in (event.get("attributes") or {}).items():
            if key == _EXCEPTION_TYPE_ATTR:
                value = _bare_type(value)
            if _is_leak(value):
                continue
            attrs[key] = value
        clean_events.append({"name": event.get("name"), "attributes": attrs})
    step.events = clean_events
    if _is_leak(step.error_message):
        step.error_message = None
    return step


def sanitize(trajectory: ParsedTrajectory) -> ParsedTrajectory:
    for step in trajectory.steps:
        sanitize_step(step)
    return trajectory
