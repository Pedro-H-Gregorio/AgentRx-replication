from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_LOGGER_NAME = "agentrx_otel_poc"
DEFAULT_LOG_FORMAT = (
    "%(asctime)s | %(levelname)s | %(name)s | run_id=%(run_id)s | "
    "component=%(component)s | event=%(event)s | %(message)s"
)
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
DEFAULT_LOG_DIR = Path("data") / "logs"


class _ContextFilter(logging.Filter):
    def __init__(self, *, run_id: str, component: str = "-", event: str = "-") -> None:
        super().__init__()
        self._defaults = {
            "run_id": run_id,
            "component": component,
            "event": event,
        }

    def filter(self, record: logging.LogRecord) -> bool:
        for key, default in self._defaults.items():
            if not hasattr(record, key):
                setattr(record, key, default)
        return True


def _resolve_level(level: str | int | None) -> int:
    if isinstance(level, int):
        return level
    if level is None:
        level = os.getenv("LOG_LEVEL", "INFO")
    if isinstance(level, str):
        resolved = logging.getLevelName(level.upper())
        if isinstance(resolved, int):
            return resolved
    return logging.INFO


def _safe_scalar(value: Any) -> str:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, str):
        text = value.replace("\n", "\\n")
        if len(text) > 240:
            text = f"{text[:237]}..."
        if not text:
            return '""'
        if any(ch.isspace() for ch in text) or any(
            ch in text for ch in ['"', "'", "=", "|"]
        ):
            return json.dumps(text, ensure_ascii=False)
        return text
    if isinstance(value, (dict, list, tuple, set)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return str(value)


def _format_fields(fields: dict[str, Any]) -> str:
    parts: list[str] = []
    reserved = {"run_id", "component", "event"}
    for key in sorted(fields):
        if key in reserved:
            continue
        value = fields[key]
        if value is None:
            continue
        parts.append(f"{key}={_safe_scalar(value)}")
    return " ".join(parts)


@dataclass(frozen=True)
class RunLogger:
    logger: logging.Logger
    run_id: str
    component: str

    def child(self, component: str) -> "RunLogger":
        return RunLogger(
            logger=logging.getLogger(f"{self.logger.name}.{component}"),
            run_id=self.run_id,
            component=component,
        )

    def debug(self, event: str, message: str | None = None, **fields: Any) -> None:
        self._log(logging.DEBUG, event, message, **fields)

    def info(self, event: str, message: str | None = None, **fields: Any) -> None:
        self._log(logging.INFO, event, message, **fields)

    def warning(self, event: str, message: str | None = None, **fields: Any) -> None:
        self._log(logging.WARNING, event, message, **fields)

    def error(self, event: str, message: str | None = None, **fields: Any) -> None:
        self._log(logging.ERROR, event, message, **fields)

    def exception(self, event: str, message: str | None = None, **fields: Any) -> None:
        self._log(logging.ERROR, event, message, exc_info=True, **fields)

    def _log(
        self,
        level: int,
        event: str,
        message: str | None = None,
        *,
        exc_info: bool
        | BaseException
        | tuple[type[BaseException], BaseException, Any] = False,
        **fields: Any,
    ) -> None:
        extra = {
            "run_id": self.run_id,
            "component": self.component,
            "event": event,
        }
        rendered_message = message or ""
        rendered_fields = _format_fields(fields)
        if rendered_fields:
            rendered_message = (
                f"{rendered_message} | {rendered_fields}"
                if rendered_message
                else rendered_fields
            )
        self.logger.log(
            level, rendered_message, extra=extra, exc_info=exc_info, stacklevel=3
        )


def configure_logging(
    run_id: str,
    *,
    level: str | int | None = None,
    logger_name: str = DEFAULT_LOGGER_NAME,
    log_dir: Path = DEFAULT_LOG_DIR,
) -> RunLogger:
    root_logger = logging.getLogger()
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)
        handler.close()

    root_logger.setLevel(_resolve_level(level))
    root_logger.propagate = False

    formatter = logging.Formatter(DEFAULT_LOG_FORMAT, datefmt=DEFAULT_DATE_FORMAT)
    context_filter = _ContextFilter(run_id=run_id)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    stream_handler.addFilter(context_filter)
    root_logger.addHandler(stream_handler)

    log_dir.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_dir / f"{run_id}.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.addFilter(_ContextFilter(run_id=run_id))
    root_logger.addHandler(file_handler)

    logging.captureWarnings(True)

    return RunLogger(logging.getLogger(logger_name), run_id=run_id, component="run")
