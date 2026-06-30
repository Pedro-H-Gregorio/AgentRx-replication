"""Scripted fault operators selectable by fault_type (PRD-03)."""

from __future__ import annotations

from . import operators  # noqa: F401  (import registers the 5 operators)
from .base import (
    CATEGORY_TO_FAULT,
    CatalogServiceTimeoutError,
    FaultOperator,
    for_node,
    select,
)

__all__ = [
    "CATEGORY_TO_FAULT",
    "CatalogServiceTimeoutError",
    "FaultOperator",
    "for_node",
    "select",
]
