"""קריאה מ-rm_products ומ-rm_product_documents. אין טעינת Aggregate."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

import sqlalchemy as sa
from goalvest_core import BusinessRuleViolation
from goalvest_core.goals import LIQUIDITY
from goalvest_core.products import CHANNEL_TYPES, PRODUCT_TYPES
from sqlalchemy.orm import Session

from app.infrastructure.tables import rm_product_documents, rm_products, rm_users

_PAGE_SIZE = 20
_SORTS = {
    "name": rm_products.c.name,
    "type": rm_products.c.type,
    "track": rm_products.c.track,
    "institution": rm_products.c.institution_name,
    "return1y": rm_products.c.return_1y,
    "return3y": rm_products.c.return_3y,
    "return5y": rm_products.c.return_5y,
    "feeAssets": rm_products.c.fee_assets,
    "feeDeposit": rm_products.c.fee_deposit,
    "stdDev": rm_products.c.std_dev,
    "riskLevel": rm_products.c.risk_level,
    "liquidity": rm_products.c.liquidity,
}


def list_products(
    session: Session,
    *,
    q: str = "",
    types: list[str] | None = None,
    risk_min: int | None = None,
    risk_max: int | None = None,
    max_fee: Decimal | None = None,
    min_return_3y: Decimal | None = None,
    liquidity: str | None = None,
    institution_id: UUID | None = None,
    page: int = 1,
    page_size: int = _PAGE_SIZE,
    sort: str = "name,asc",
    include_inactive: bool = False,
    viewer_role: str | None = None,
    viewer_institution: UUID | None = None,
) -> dict:
    if page < 1:
        _invalid("מספר העמוד אינו תקין", "page", "INVALID_PAGE")
    if page_size < 1:
        _invalid("גודל העמוד אינו תקין", "pageSize", "INVALID_PAGE")
    size = min(page_size, _PAGE_SIZE)
    filters = _filters(
        q=q,
        types=types or [],
        risk_min=risk_min,
        risk_max=risk_max,
        max_fee=max_fee,
        min_return_3y=min_return_3y,
        liquidity=liquidity,
        institution_id=institution_id,
        include_inactive=include_inactive,
        viewer_role=viewer_role,
        viewer_institution=viewer_institution,
    )
    total = session.execute(sa.select(sa.func.count()).select_from(rm_products).where(*filters)).scalar_one()
    rows = session.execute(
        sa.select(rm_products)
        .where(*filters)
        .order_by(*_order(sort))
        .offset((page - 1) * size)
        .limit(size)
    ).mappings()
    return {
        "items": [_summary(row) for row in rows],
        "page": page,
        "pageSize": size,
        "total": int(total),
    }


def get_product(session: Session, product_id: UUID) -> dict | None:
    row = session.execute(sa.select(rm_products).where(rm_products.c.product_id == product_id)).mappings().first()
    if row is None:
        return None
    body = _summary(row)
    body.update({
        "liquidityTerms": row["liquidity_terms"],
        "taxNotes": row["tax_notes"],
        "description": row["description"],
        "documents": _documents(session, product_id),
        "agents": _agents(session, row["institution_id"]),
        "fit": None,
    })
    return body


def list_documents(session: Session, product_id: UUID) -> list[dict] | None:
    exists = session.execute(
        sa.select(rm_products.c.product_id).where(rm_products.c.product_id == product_id)
    ).first()
    if exists is None:
        return None
    return _documents(session, product_id)


def product_institution(session: Session, product_id: UUID) -> UUID | None:
    row = session.execute(
        sa.select(rm_products.c.institution_id).where(rm_products.c.product_id == product_id)
    ).first()
    return None if row is None else row[0]


def get_document(session: Session, document_id: UUID) -> dict | None:
    row = session.execute(
        sa.select(rm_product_documents).where(rm_product_documents.c.document_id == document_id)
    ).mappings().first()
    if row is None:
        return None
    return {"fileName": row["file_name"], "storedName": row["stored_name"]}


def _filters(**query) -> list:
    filters: list = []
    text = query["q"].strip().lower()
    if text:
        filters.append(sa.func.lower(rm_products.c.search_text).like(_like(text), escape="\\"))
    selected = _types(query["types"])
    if selected:
        filters.append(rm_products.c.type.in_(selected))
    risk_min = _risk_bound(query["risk_min"], "riskMin")
    risk_max = _risk_bound(query["risk_max"], "riskMax")
    if risk_min is not None and risk_max is not None and risk_min > risk_max:
        _invalid("טווח הסיכון אינו תקין", "riskMin", "INVALID_RISK")
    if risk_min is not None:
        filters.append(rm_products.c.risk_level >= risk_min)
    if risk_max is not None:
        filters.append(rm_products.c.risk_level <= risk_max)
    if query["max_fee"] is not None:
        filters.append(rm_products.c.fee_assets <= query["max_fee"])
    if query["min_return_3y"] is not None:
        filters.append(rm_products.c.return_3y >= query["min_return_3y"])
    if query["liquidity"]:
        if query["liquidity"] not in LIQUIDITY:
            _invalid("נזילות לא מוכרת", "liquidity", "INVALID_LIQUIDITY")
        filters.append(rm_products.c.liquidity == query["liquidity"])
    own_catalog = (
        query["include_inactive"] and query["viewer_role"] == "AGENT" and query["viewer_institution"] is not None
    )
    if own_catalog:
        filters.append(rm_products.c.institution_id == query["viewer_institution"])
    else:
        filters.append(rm_products.c.is_active == sa.true())
        if query["institution_id"] is not None:
            filters.append(rm_products.c.institution_id == query["institution_id"])
    return filters


def _types(values: list[str]) -> set[str]:
    selected: set[str] = set()
    for value in values:
        if value in CHANNEL_TYPES:
            selected.update(CHANNEL_TYPES[value])
        elif value in PRODUCT_TYPES:
            selected.add(value)
        elif value:
            _invalid("סוג אפיק לא מוכר", "type", "INVALID_TYPE")
    return selected


def _risk_bound(value: int | None, field: str) -> int | None:
    if value is None:
        return None
    if not 1 <= value <= 7:
        _invalid("רמת הסיכון היא מספר מ-1 עד 7", field, "INVALID_RISK")
    return value


def _order(sort: str) -> tuple:
    field, _, direction = sort.partition(",")
    column = _SORTS.get(field)
    if column is None or direction not in {"asc", "desc", ""}:
        _invalid("מיון לא מוכר", "sort", "INVALID_SORT")
    ordered = column.desc() if direction == "desc" else column.asc()
    return ordered, rm_products.c.product_id.asc()


def _summary(row) -> dict:
    return {
        "productId": str(row["product_id"]),
        "type": row["type"],
        "name": row["name"],
        "institutionId": str(row["institution_id"]),
        "institutionName": row["institution_name"],
        "track": row["track"],
        "symbol": row["symbol"],
        "feeDeposit": _decimal(row["fee_deposit"]),
        "feeAssets": _decimal(row["fee_assets"]),
        "return1y": _decimal(row["return_1y"]),
        "return3y": _decimal(row["return_3y"]),
        "return5y": _decimal(row["return_5y"]),
        "stdDev": _decimal(row["std_dev"]),
        "riskLevel": int(row["risk_level"]),
        "liquidity": row["liquidity"],
        "minDeposit": _decimal(row["min_deposit"]),
        "isActive": bool(row["is_active"]),
    }


def _documents(session: Session, product_id: UUID) -> list[dict]:
    rows = session.execute(
        sa.select(rm_product_documents)
        .where(rm_product_documents.c.product_id == product_id)
        .order_by(rm_product_documents.c.uploaded_at.asc())
    ).mappings()
    return [_document(row) for row in rows]


def _document(row) -> dict:
    chunks = row["chunks_count"]
    return {
        "documentId": str(row["document_id"]),
        "fileName": row["file_name"],
        "docType": row["doc_type"],
        "indexStatus": row["index_status"],
        "chunksCount": int(chunks) if chunks is not None else None,
        "uploadedAt": _timestamp(row["uploaded_at"]),
    }


def _agents(session: Session, institution_id: UUID) -> list[dict]:
    rows = session.execute(
        sa.select(rm_users.c.user_id, rm_users.c.full_name)
        .where(
            rm_users.c.role == "AGENT",
            rm_users.c.institution_id == institution_id,
            rm_users.c.status == "ACTIVE",
        )
        .order_by(rm_users.c.full_name.asc())
    ).mappings()
    return [{"id": str(row["user_id"]), "fullName": row["full_name"]} for row in rows]


def _like(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _decimal(value: object) -> str:
    amount = Decimal(str(value)).quantize(Decimal("0.01"))
    return format(amount, "f")


def _timestamp(value: object) -> str:
    if isinstance(value, datetime):
        text = value.isoformat()
        return text if text.endswith("Z") or "+" in text else f"{text}Z"
    return str(value)


def _invalid(message: str, field: str, code: str) -> None:
    raise BusinessRuleViolation(message, code=code, fields={field: message})
