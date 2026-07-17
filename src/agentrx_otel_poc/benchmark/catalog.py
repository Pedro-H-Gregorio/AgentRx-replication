"""Read-only access to the vendored tau-bench product catalog."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Variant:
    item_id: str
    options: dict[str, str]
    available: bool
    price: float


@dataclass(frozen=True)
class Product:
    product_id: str
    product_type: str
    variants: tuple[Variant, ...]

    def available_variants(self) -> list[Variant]:
        """Available variants sorted by item_id (why: stable, reproducible picks)."""
        return sorted(
            (v for v in self.variants if v.available), key=lambda v: v.item_id
        )


def load_catalog(path: str | Path) -> list[Product]:
    """Load the catalog into sorted `Product`s (sorted by product_id)."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    products: list[Product] = []
    for pid in sorted(raw):
        entry = raw[pid]
        variants = tuple(
            Variant(
                item_id=str(vid),
                options={str(k): str(val) for k, val in v["options"].items()},
                available=bool(v["available"]),
                price=float(v["price"]),
            )
            for vid, v in sorted(entry["variants"].items())
        )
        products.append(
            Product(
                product_id=str(entry["product_id"]),
                product_type=str(entry["name"]),
                variants=variants,
            )
        )
    return products


def option_value_split(
    product: Product,
) -> tuple[str, str, float, list[Variant]] | None:
    """Pick a deterministic (option, value, threshold, above) for the T3 template.

    The threshold is the median price of the variants matching (option, value);
    `above` are those strictly above it — guaranteed non-empty when returned.
    """
    groups: dict[tuple[str, str], list[Variant]] = defaultdict(list)
    for v in product.available_variants():
        for opt in sorted(v.options):
            groups[(opt, v.options[opt])].append(v)
    for key in sorted(groups):
        matching = groups[key]
        if len(matching) < 2:
            continue
        prices = sorted(v.price for v in matching)
        mid = len(prices) // 2
        median = prices[mid] if len(prices) % 2 else (prices[mid - 1] + prices[mid]) / 2
        threshold = round(median, 2)
        above = sorted(
            (v for v in matching if v.price > threshold), key=lambda v: v.item_id
        )
        if above:
            opt, val = key
            return opt, val, threshold, above
    return None
