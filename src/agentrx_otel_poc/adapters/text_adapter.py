from __future__ import annotations

from pathlib import Path
from typing import Any

from agentrx_otel_poc.runtime_logging import RunLogger


def _step_spans(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        span
        for span in payload.get("spans", [])
        if "experiment.step_index" in span.get("attributes", {})
    ]


def convert_otel_to_text_baseline(
    payload: dict[str, Any],
    output_path: Path,
    *,
    logger: RunLogger | None = None,
) -> str:
    """Gera baseline textual derivado da mesma telemetria.

    Remove IDs, hierarquia de spans, duração e métricas. Preserva apenas a narrativa
    textual mínima da execução. Isso evita comparar trajetórias diferentes.
    """
    if logger:
        spans = _step_spans(payload)
        logger.info(
            "artifact.write.start",
            "Building text baseline from OTel payload",
            artifact_kind="text_baseline",
            output_path=output_path,
            spans=len(spans),
        )
    else:
        spans = _step_spans(payload)

    lines = [f"Task: {payload['task']}", ""]
    spans = sorted(
        spans, key=lambda s: int(s["attributes"].get("experiment.step_index", 9999))
    )
    for span in spans:
        attrs = span.get("attributes", {})
        agent = attrs.get("gen_ai.agent.name", span["name"])
        op = attrs.get("gen_ai.operation.name", span["name"])
        if attrs.get("error.type"):
            lines.append(
                f"The {agent} attempted to perform {op}, but the operation failed."
            )
        else:
            lines.append(f"The {agent} performed {op}.")
        for event in span.get("events", []):
            event_name = event["name"].replace("_", " ")
            if event_name in {
                "dependency call failed",
                "validation failed",
                "retry triggered",
            }:
                lines.append(f"An event occurred: {event_name}.")
    text = "\n".join(lines) + "\n"

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        chars_written = output_path.write_text(text, encoding="utf-8")
    except Exception:
        if logger:
            logger.exception(
                "artifact.write.failed",
                "Failed to write text baseline",
                artifact_kind="text_baseline",
                output_path=output_path,
            )
        raise

    if logger:
        logger.info(
            "artifact.write.done",
            "Text baseline written",
            artifact_kind="text_baseline",
            output_path=output_path,
            lines=len(lines),
            chars_written=chars_written,
        )

    return text
