"""Leakage prevention (PRD-06 R1/R2): strip ground-truth markers from parsed steps.

Removes the `fault.injected` event and any attribute/stacktrace that reveals the
injection code, before either arm is rendered. The raw `.otel.json` keeps it all;
only the derived trajectories are cleaned.
"""

from __future__ import annotations

from .parser import ParsedStep, ParsedTrajectory

_LEAK_EVENTS = {"fault.injected"}
_LEAK_ATTRS = {"exception.stacktrace"}
_LEAK_TOKENS = (
    "fault.injected",
    "experiment.fault",
    "faults.py",
    "operators.py",
    "maybe_raise",
    "/faults",
    "faults/",
)


def _is_leak(value: object) -> bool:
    return isinstance(value, str) and any(tok in value for tok in _LEAK_TOKENS)


def sanitize_step(step: ParsedStep) -> ParsedStep:
    clean_events = []
    for event in step.events:
        if event.get("name") in _LEAK_EVENTS:
            continue
        attrs = {}
        for key, value in (event.get("attributes") or {}).items():
            if key in _LEAK_ATTRS or _is_leak(value):
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
