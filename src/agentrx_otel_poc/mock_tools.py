from __future__ import annotations

from agentrx_otel_poc.faults import maybe_raise_system_timeout
from agentrx_otel_poc.runtime_logging import RunLogger


MOCK_PRODUCTS = [
    {"brand": "Dell", "model": "Dell Inspiron 15", "price_brl": 4399},
    {"brand": "Dell", "model": "Dell G15", "price_brl": 6299},
    {"brand": "Dell", "model": "Dell XPS 13", "price_brl": 8999},
    {"brand": "Lenovo", "model": "IdeaPad Gaming 3", "price_brl": 5599},
]


def search_products(
    brand: str,
    price_min_brl: int,
    fault_type: str | None = None,
    *,
    logger: RunLogger | None = None,
) -> list[dict]:
    normalized_brand = brand.strip().lower()
    if logger:
        logger.info(
            "tool.search.start",
            "Searching product catalog",
            brand=brand,
            price_min_brl=price_min_brl,
        )

    maybe_raise_system_timeout(fault_type, logger=logger)
    products = [
        p
        for p in MOCK_PRODUCTS
        if p["brand"].lower() == normalized_brand and p["price_brl"] > price_min_brl
    ]

    if logger:
        logger.info(
            "tool.search.success",
            "Product catalog search completed",
            result_count=len(products),
        )

    return products
