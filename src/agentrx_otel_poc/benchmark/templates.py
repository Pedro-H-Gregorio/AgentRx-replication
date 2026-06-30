"""The 5 read-only question templates (T1–T5), computed from the catalog.

Each builder returns the template-specific fields of a scenario, including the
computed `expected_answer` (ground truth of success). Questions are in English.
"""

from __future__ import annotations

from .catalog import Product, option_value_split

TOOL = "ProductCatalogSearch"

TEMPLATE_IDS = {
    "T1": "T1_cheapest",
    "T2": "T2_count",
    "T3": "T3_spec_filter",
    "T4": "T4_item_option",
    "T5": "T5_item_price",
}


def slug(text: str) -> str:
    return text.lower().replace(" ", "_").replace("-", "_")


def supports(product: Product, template: str) -> bool:
    """Whether *product* can host *template* with a non-trivial answer."""
    if template in ("T1", "T2", "T4", "T5"):
        return bool(product.available_variants())
    if template == "T3":
        return option_value_split(product) is not None
    return False


def build(product: Product, template: str) -> dict:
    """Return the template-specific scenario fields for (product, template)."""
    builder = _BUILDERS[template]
    return builder(product)


def _t1(product: Product) -> dict:
    cheapest = min(product.available_variants(), key=lambda v: (v.price, v.item_id))
    ptype = product.product_type
    return {
        "user_request": f"What is the cheapest available {ptype}?",
        "tool_operation": "catalog.search",
        "default_tool_args": {
            "product_type": ptype,
            "available_only": True,
            "sort": "price_asc",
        },
        "expected_result": (
            f"The cheapest available {ptype} is item {cheapest.item_id} "
            f"at ${cheapest.price:.2f}."
        ),
        "expected_answer": {"item_id": cheapest.item_id, "price": cheapest.price},
        "template_id": TEMPLATE_IDS["T1"],
    }


def _t2(product: Product) -> dict:
    available = product.available_variants()
    ptype = product.product_type
    return {
        "user_request": f"How many {ptype} options are available?",
        "tool_operation": "catalog.search",
        "default_tool_args": {
            "product_type": ptype,
            "available_only": True,
            "op": "count",
        },
        "expected_result": f"There are {len(available)} available {ptype} options.",
        "expected_answer": {"count": len(available)},
        "template_id": TEMPLATE_IDS["T2"],
    }


def _t3(product: Product) -> dict:
    opt, val, threshold, above = option_value_split(product)
    ptype = product.product_type
    item_ids = [v.item_id for v in above]
    return {
        "user_request": (
            f"Which available {ptype} with {opt}={val} cost more than ${threshold:.2f}?"
        ),
        "tool_operation": "catalog.search",
        "default_tool_args": {
            "product_type": ptype,
            opt: val,
            "price_min": threshold,
            "available_only": True,
        },
        "expected_result": (
            f"{len(item_ids)} available {ptype} ({opt}={val}) priced above "
            f"${threshold:.2f}."
        ),
        "expected_answer": {"item_ids": item_ids, "count": len(item_ids)},
        "template_id": TEMPLATE_IDS["T3"],
    }


def _t4(product: Product) -> dict:
    variant = product.available_variants()[0]
    opt = sorted(variant.options)[0]
    val = variant.options[opt]
    ptype = product.product_type
    return {
        "user_request": f"Does item {variant.item_id} of the {ptype} have {opt}={val}?",
        "tool_operation": "catalog.get_details",
        "default_tool_args": {
            "product_id": product.product_id,
            "item_id": variant.item_id,
        },
        "expected_result": f"Item {variant.item_id} has {opt}={val}.",
        "expected_answer": {"answer": variant.options.get(opt) == val},
        "template_id": TEMPLATE_IDS["T4"],
    }


def _t5(product: Product) -> dict:
    variant = product.available_variants()[0]
    return {
        "user_request": f"What is the price of item {variant.item_id}?",
        "tool_operation": "catalog.get_details",
        "default_tool_args": {
            "product_id": product.product_id,
            "item_id": variant.item_id,
        },
        "expected_result": f"Item {variant.item_id} is priced at ${variant.price:.2f}.",
        "expected_answer": {"price": variant.price},
        "template_id": TEMPLATE_IDS["T5"],
    }


_BUILDERS = {"T1": _t1, "T2": _t2, "T3": _t3, "T4": _t4, "T5": _t5}
