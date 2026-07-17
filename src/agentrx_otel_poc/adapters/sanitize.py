"""Leakage prevention: strip ground-truth markers from parsed steps."""

from __future__ import annotations

from .parser import ParsedStep, ParsedTrajectory

_LEAK_EVENTS = {"fault.injected"}
_EXCEPTION_TYPE_ATTR = "exception.type"
_LEAK_TOKENS = (
    "fault.injected",
    "experiment.fault",
    "faults.py",
    "faults.",
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
