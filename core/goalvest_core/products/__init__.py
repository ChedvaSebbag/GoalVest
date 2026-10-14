"""מוצר בקטלוג."""

from goalvest_core.products.files import MAX_DOCUMENT_BYTES, display_name, inspect_document
from goalvest_core.products.product import (
    CHANNEL_TYPES,
    DOC_TYPES,
    MARKET_TYPES,
    PRODUCT_TYPES,
    Product,
)

__all__ = [
    "CHANNEL_TYPES",
    "DOC_TYPES",
    "MARKET_TYPES",
    "MAX_DOCUMENT_BYTES",
    "PRODUCT_TYPES",
    "Product",
    "display_name",
    "inspect_document",
]
