"""Product – קטלוג מוצר ומסמך שהועלה. ראו docs/03 §3.4–3.5 ו-docs/07 §7.3."""

import re
from decimal import Decimal, InvalidOperation
from uuid import UUID, uuid4

from goalvest_core.aggregate import AggregateRoot
from goalvest_core.errors import BusinessRuleViolation
from goalvest_core.event import Event
from goalvest_core.goals import LIQUIDITY
from goalvest_core.products.files import display_name, inspect_document

PRODUCT_TYPES = frozenset({"HISHTALMUT", "GEMEL_INVESTMENT", "SAVINGS_POLICY", "STOCK", "ETF"})
MARKET_TYPES = frozenset({"STOCK", "ETF"})
DOC_TYPES = frozenset({"POLICY_TERMS", "QUARTERLY_REPORT", "TAX_RULES", "MARKET_REPORT"})
CHANNEL_TYPES = {
    "CAPITAL_MARKET": frozenset({"STOCK", "ETF"}),
    "HISHTALMUT": frozenset({"HISHTALMUT"}),
    "GEMEL_POLICY": frozenset({"GEMEL_INVESTMENT", "SAVINGS_POLICY"}),
}
MONEY = Decimal("0.01")
_SYMBOL = re.compile(r"^[A-Z0-9][A-Z0-9.\-]{0,19}$")
_RATE_MIN = Decimal(-100)
_RATE_MAX = Decimal(500)


class Product(AggregateRoot):
    aggregate_type = "Product"

    def __init__(self, aggregate_id: UUID | None = None) -> None:
        super().__init__(aggregate_id)
        self.institution_id: UUID | None = None
        self.product_type = ""
        self.name = ""
        self.track = ""
        self.symbol: str | None = None
        self.fee_deposit = Decimal(0)
        self.fee_assets = Decimal(0)
        self.return_1y = Decimal(0)
        self.return_3y = Decimal(0)
        self.return_5y = Decimal(0)
        self.std_dev = Decimal(0)
        self.risk_level = 0
        self.liquidity = ""
        self.liquidity_terms = ""
        self.tax_notes = ""
        self.min_deposit = Decimal(0)
        self.description = ""
        self.status = ""
        self._document_ids: set[str] = set()

    def create(
        self,
        *,
        institution_id: UUID,
        known_institutions: set[str],
        metadata: dict | None = None,
        **fields: object,
    ) -> None:
        if self.version != 0:
            raise BusinessRuleViolation("המוצר כבר קיים", code="PRODUCT_EXISTS")
        if str(institution_id) not in known_institutions:
            _invalid("יש לבחור גוף מהרשימה", "institutionId", "INVALID_INSTITUTION")
        payload = _product_fields(fields)
        payload["institution_id"] = str(institution_id)
        self._record("ProductCreated", payload, metadata)

    def update(self, *, metadata: dict | None = None, **fields: object) -> None:
        self._ensure_active()
        incoming = _product_fields(fields)
        changed = {key: value for key, value in incoming.items() if value != _current(self)[key]}
        if changed:
            self._record("ProductUpdated", changed, metadata)

    def deactivate(self, reason: str = "", metadata: dict | None = None) -> None:
        self._ensure_active()
        self._record("ProductDeactivated", {"reason": reason.strip()[:300]}, metadata)

    def upload_document(
        self,
        *,
        content: bytes,
        original_name: str,
        doc_type: str,
        metadata: dict | None = None,
    ) -> None:
        self._ensure_active()
        if doc_type not in DOC_TYPES:
            _invalid("יש לבחור סוג מסמך", "docType", "INVALID_DOC_TYPE")
        extension, digest = inspect_document(content)
        document_id = uuid4()
        self._record(
            "ProductDocumentUploaded",
            {
                "document_id": str(document_id),
                "file_name": display_name(original_name, extension),
                "stored_name": f"{document_id}.{extension}",
                "doc_type": doc_type,
                "storage_path": f"{document_id}.{extension}",
                "sha256": digest,
                "size_bytes": len(content),
            },
            metadata,
        )

    def mark_document_indexed(
        self,
        *,
        document_id: str,
        chunks_count: int,
        embedding_model: str,
        metadata: dict | None = None,
    ) -> None:
        self._require_document(document_id)
        if isinstance(chunks_count, bool) or not isinstance(chunks_count, int) or chunks_count < 1:
            _invalid("מספר הקטעים אינו תקין", "chunksCount", "INVALID_CHUNKS")
        model = embedding_model.strip()
        if not model:
            _invalid("חסר מודל הטמעה", "embeddingModel", "INVALID_MODEL")
        self._record(
            "ProductDocumentIndexed",
            {"document_id": document_id, "chunks_count": chunks_count, "embedding_model": model},
            metadata,
        )

    def mark_document_index_failed(self, *, document_id: str, error: str, metadata: dict | None = None) -> None:
        self._require_document(document_id)
        message = error.strip()
        if not message:
            _invalid("חסר תיאור שגיאה", "error", "INVALID_ERROR")
        self._record(
            "ProductDocumentIndexFailed",
            {"document_id": document_id, "error": message[:300]},
            metadata,
        )

    def _require_document(self, document_id: str) -> None:
        if document_id not in self._document_ids:
            raise BusinessRuleViolation("המסמך לא נמצא על המוצר", code="DOCUMENT_NOT_FOUND")

    def _ensure_active(self) -> None:
        if self.status != "ACTIVE":
            raise BusinessRuleViolation("המוצר מושבת", code="PRODUCT_INACTIVE")

    def _when(self, event: Event) -> None:
        payload = event.payload
        if event.event_type == "ProductCreated":
            self.institution_id = UUID(str(payload["institution_id"]))
            self.status = "ACTIVE"
            _apply(self, payload)
            return
        if event.event_type == "ProductUpdated":
            _apply(self, payload)
            return
        if event.event_type == "ProductDeactivated":
            self.status = "INACTIVE"
            return
        if event.event_type == "ProductDocumentUploaded":
            self._document_ids.add(str(payload["document_id"]))
            return
        if event.event_type in {"ProductDocumentIndexed", "ProductDocumentIndexFailed"}:
            return
        raise NotImplementedError(f"Product אינו מטפל ב-{event.event_type}")


def _current(product: Product) -> dict:
    return {
        "type": product.product_type,
        "name": product.name,
        "track": product.track,
        "symbol": product.symbol,
        "fee_deposit": product.fee_deposit,
        "fee_assets": product.fee_assets,
        "return_1y": product.return_1y,
        "return_3y": product.return_3y,
        "return_5y": product.return_5y,
        "std_dev": product.std_dev,
        "risk_level": product.risk_level,
        "liquidity": product.liquidity,
        "liquidity_terms": product.liquidity_terms,
        "tax_notes": product.tax_notes,
        "min_deposit": product.min_deposit,
        "description": product.description,
    }


def _apply(product: Product, payload: dict) -> None:
    if "type" in payload:
        product.product_type = payload["type"]
    if "name" in payload:
        product.name = payload["name"]
    if "track" in payload:
        product.track = payload["track"]
    if "symbol" in payload:
        product.symbol = payload["symbol"] or None
    if "fee_deposit" in payload:
        product.fee_deposit = _money(payload["fee_deposit"])
    if "fee_assets" in payload:
        product.fee_assets = _money(payload["fee_assets"])
    if "return_1y" in payload:
        product.return_1y = _money(payload["return_1y"])
    if "return_3y" in payload:
        product.return_3y = _money(payload["return_3y"])
    if "return_5y" in payload:
        product.return_5y = _money(payload["return_5y"])
    if "std_dev" in payload:
        product.std_dev = _money(payload["std_dev"])
    if "risk_level" in payload:
        product.risk_level = int(payload["risk_level"])
    if "liquidity" in payload:
        product.liquidity = payload["liquidity"]
    if "liquidity_terms" in payload:
        product.liquidity_terms = payload["liquidity_terms"]
    if "tax_notes" in payload:
        product.tax_notes = payload["tax_notes"]
    if "min_deposit" in payload:
        product.min_deposit = _money(payload["min_deposit"])
    if "description" in payload:
        product.description = payload["description"]


def _product_fields(fields: dict) -> dict:
    product_type = _one(fields.get("product_type"), PRODUCT_TYPES, "type", "יש לבחור סוג מוצר", "INVALID_TYPE")
    name = _text(fields.get("name"), "name", "יש להזין שם מוצר", "INVALID_NAME", minimum=2, maximum=120)
    track = _text(fields.get("track"), "track", "יש להזין מסלול", "INVALID_TRACK", minimum=1, maximum=120)
    symbol = _symbol(fields.get("symbol"), product_type)
    fee_deposit = _fee(fields.get("fee_deposit"), "feeDeposit", "INVALID_FEE_DEPOSIT")
    fee_assets = _fee(fields.get("fee_assets"), "feeAssets", "INVALID_FEE_ASSETS")
    return_1y = _rate(fields.get("return_1y"), "return1y", "INVALID_RETURN")
    return_3y = _rate(fields.get("return_3y"), "return3y", "INVALID_RETURN")
    return_5y = _rate(fields.get("return_5y"), "return5y", "INVALID_RETURN")
    std_dev = _non_negative_rate(fields.get("std_dev"), "stdDev", "INVALID_STD_DEV")
    risk_level = _risk(fields.get("risk_level"))
    liquidity = _one(fields.get("liquidity"), LIQUIDITY, "liquidity", "יש לבחור נזילות", "INVALID_LIQUIDITY")
    liquidity_terms = _text(
        fields.get("liquidity_terms"), "liquidityTerms", "יש לתאר את תנאי הנזילות", "INVALID_LIQUIDITY_TERMS", 2, 500,
    )
    tax_notes = _text(fields.get("tax_notes"), "taxNotes", "יש לתאר את תנאי המס", "INVALID_TAX_NOTES", 2, 500)
    min_deposit = _non_negative_money(fields.get("min_deposit"), "minDeposit", "INVALID_MIN_DEPOSIT")
    description = _text(fields.get("description"), "description", "יש להזין תיאור", "INVALID_DESCRIPTION", 2, 2000)
    return {
        "type": product_type,
        "name": name,
        "track": track,
        "symbol": symbol,
        "fee_deposit": fee_deposit,
        "fee_assets": fee_assets,
        "return_1y": return_1y,
        "return_3y": return_3y,
        "return_5y": return_5y,
        "std_dev": std_dev,
        "risk_level": risk_level,
        "liquidity": liquidity,
        "liquidity_terms": liquidity_terms,
        "tax_notes": tax_notes,
        "min_deposit": min_deposit,
        "description": description,
    }


def _symbol(value: object, product_type: str) -> str | None:
    raw = "" if value is None else value
    if not isinstance(raw, str):
        _invalid("סימול המנייה אינו תקין", "symbol", "INVALID_SYMBOL")
    symbol = raw.strip().upper()
    if product_type in MARKET_TYPES:
        if not _SYMBOL.match(symbol):
            _invalid("למנייה או לתעודת סל חובה סימול", "symbol", "INVALID_SYMBOL")
        return symbol
    if symbol:
        _invalid("סימול מתאים רק למנייה או לתעודת סל", "symbol", "INVALID_SYMBOL")
    return None


def _risk(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 7:
        _invalid("רמת הסיכון היא מספר מ-1 עד 7", "riskLevel", "INVALID_RISK")
    return value


def _fee(value: object, field: str, code: str) -> Decimal:
    amount = _decimal(value, field, code, "דמי הניהול אינם תקינים")
    if amount < 0 or amount > Decimal(100):
        _invalid("דמי הניהול אינם תקינים", field, code)
    return amount


def _rate(value: object, field: str, code: str) -> Decimal:
    amount = _decimal(value, field, code, "התשואה אינה תקינה")
    if amount < _RATE_MIN or amount > _RATE_MAX:
        _invalid("התשואה אינה תקינה", field, code)
    return amount


def _non_negative_rate(value: object, field: str, code: str) -> Decimal:
    amount = _decimal(value, field, code, "סטיית התקן אינה תקינה")
    if amount < 0 or amount > Decimal(100):
        _invalid("סטיית התקן אינה תקינה", field, code)
    return amount


def _non_negative_money(value: object, field: str, code: str) -> Decimal:
    amount = _decimal(value, field, code, "הסכום אינו תקין")
    if amount < 0:
        _invalid("הסכום אינו יכול להיות שלילי", field, code)
    return amount


def _money(value: object) -> Decimal:
    amount = value if isinstance(value, Decimal) else Decimal(str(value))
    return amount.quantize(MONEY)


def _decimal(value: object, field: str, code: str, message: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, Decimal, str)):
        _invalid(message, field, code)
    try:
        return _money(value)
    except (InvalidOperation, ValueError):
        _invalid(message, field, code)
    raise AssertionError


def _text(value: object, field: str, message: str, code: str, minimum: int, maximum: int) -> str:
    if not isinstance(value, str):
        _invalid(message, field, code)
    cleaned = value.strip()
    if not minimum <= len(cleaned) <= maximum:
        _invalid(message, field, code)
    return cleaned


def _one(value: object, options: frozenset[str], field: str, message: str, code: str) -> str:
    if not isinstance(value, str) or value not in options:
        _invalid(message, field, code)
    return value


def _invalid(message: str, field: str, code: str) -> None:
    raise BusinessRuleViolation(message, code=code, fields={field: message})
