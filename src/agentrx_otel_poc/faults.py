from __future__ import annotations

from agentrx_otel_poc.runtime_logging import RunLogger


class CatalogServiceTimeoutError(TimeoutError):
    """Timeout raised by the simulated catalog dependency."""


def maybe_raise_system_timeout(
    fault_type: str | None, logger: RunLogger | None = None
) -> None:
    if fault_type == "system_timeout":
        if logger:
            logger.warning(
                "upstream.timeout",
                "Catalog service request timed out",
                upstream_service="catalog-service",
                timeout_ms=30000,
                error_type=CatalogServiceTimeoutError.__name__,
            )
        raise CatalogServiceTimeoutError(
            "Catalog service request timed out after 30000ms"
        )
