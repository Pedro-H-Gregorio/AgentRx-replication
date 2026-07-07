"""Mock `ProductCatalogSearch` over the vendored tau-bench catalog (read-only).

Structured JSON on success; `{"ok": false, "error": {...}}` on a malformed call.
No fault logic lives here — faults are injected by the graph nodes (see faults/).
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


class CatalogServiceTimeoutError(TimeoutError):
    """Timeout the catalog service can raise.

    Domain error type (not fault logic): the System Failure injection sets a
    state marker and the Tool node raises this at the dependency boundary, so the
    captured stacktrace names application frames — never the injection module.
    """


_CATALOG = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "external"
    / "taubench_retail"
    / "products.json"
)
_KNOWN_ARGS = {"product_type", "price_min", "available_only", "sort", "op"}
_TOOL_PARAMETERS: dict[str, dict[str, dict[str, Any]]] = {
    "catalog.search": {
        "product_type": {"type": "string", "required": True},
    },
    "catalog.get_details": {
        "product_id": {"type": "string", "required": True},
        "item_id": {"type": "string", "required": True},
    },
}


@lru_cache(maxsize=4)
def _load(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _error(error_type: str, message: str) -> dict[str, Any]:
    return {"ok": False, "error": {"type": error_type, "message": message}}


def _variants_of_type(
    catalog: dict[str, Any], product_type: str
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for entry in catalog.values():
        if entry["name"] != product_type:
            continue
        for vid, variant in entry["variants"].items():
            items.append(
                {
                    "item_id": str(vid),
                    "price": float(variant["price"]),
                    "available": bool(variant["available"]),
                    "options": {str(k): str(v) for k, v in variant["options"].items()},
                }
            )
    return items


def catalog_search(
    args: dict[str, Any], *, catalog_path: str | Path | None = None
) -> dict:
    catalog = _load(str(catalog_path or _CATALOG))
    product_type = args.get("product_type")
    if not isinstance(product_type, str) or not product_type:
        return _error("SchemaError", "catalog.search requires a string product_type")
    items = _variants_of_type(catalog, product_type)
    if args.get("available_only"):
        items = [i for i in items if i["available"]]
    for key, value in args.items():
        if key not in _KNOWN_ARGS:
            items = [i for i in items if i["options"].get(key) == value]
    price_min = args.get("price_min")
    if isinstance(price_min, (int, float)):
        items = [i for i in items if i["price"] > price_min]
    if args.get("sort") == "price_asc":
        items = sorted(items, key=lambda i: (i["price"], i["item_id"]))
    else:
        items = sorted(items, key=lambda i: i["item_id"])
    return {
        "ok": True,
        "operation": "catalog.search",
        "query": args,
        "items": items,
        "count": len(items),
    }


def catalog_get_details(
    args: dict[str, Any], *, catalog_path: str | Path | None = None
) -> dict:
    catalog = _load(str(catalog_path or _CATALOG))
    product_id, item_id = args.get("product_id"), args.get("item_id")
    if not isinstance(product_id, str) or not isinstance(item_id, str):
        return _error(
            "SchemaError", "catalog.get_details requires string product_id and item_id"
        )
    entry = catalog.get(product_id)
    if not entry:
        return _error("NotFound", f"product_id {product_id} not found")
    variant = entry["variants"].get(item_id)
    if not variant:
        return _error("NotFound", f"item_id {item_id} not found")
    detail = {
        "item_id": item_id,
        "price": float(variant["price"]),
        "available": bool(variant["available"]),
        "options": {str(k): str(v) for k, v in variant["options"].items()},
    }
    return {
        "ok": True,
        "operation": "catalog.get_details",
        "query": args,
        "items": [detail],
        "count": 1,
    }


def run_tool(
    operation: str, args: dict[str, Any], *, catalog_path: str | Path | None = None
) -> dict:
    """Dispatch a tool operation to the matching catalog function."""
    if operation == "catalog.get_details":
        return catalog_get_details(args, catalog_path=catalog_path)
    return catalog_search(args, catalog_path=catalog_path)


def tool_parameters(operation: str) -> dict[str, dict[str, Any]]:
    """Return the static input contract for a catalog operation."""
    try:
        params = _TOOL_PARAMETERS[operation]
    except KeyError as exc:
        raise ValueError(f"Unknown tool operation: {operation}") from exc
    return {name: dict(schema) for name, schema in params.items()}
