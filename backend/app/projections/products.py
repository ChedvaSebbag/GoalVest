"""ProductCreated, ProductUpdated, ProductDeactivated ו-ProductDocumentUploaded אל טבלאות הקריאה."""

from uuid import UUID

import sqlalchemy as sa
from goalvest_core import Event
from sqlalchemy.orm import Session

from app.infrastructure.serialization import to_naive_utc
from app.infrastructure.tables import rm_product_documents, rm_products
from app.projections.values import as_money
from app.reference.institutions import find_institution

_COLUMNS = {
    "type": lambda value: value,
    "name": lambda value: value,
    "track": lambda value: value,
    "symbol": lambda value: value,
    "fee_deposit": as_money,
    "fee_assets": as_money,
    "return_1y": as_money,
    "return_3y": as_money,
    "return_5y": as_money,
    "std_dev": as_money,
    "risk_level": lambda value: int(value),
    "liquidity": lambda value: value,
    "liquidity_terms": lambda value: value,
    "tax_notes": lambda value: value,
    "min_deposit": as_money,
    "description": lambda value: value,
}


def project_product_created(event: Event, session: Session) -> None:
    payload = event.payload
    institution_id = UUID(str(payload["institution_id"]))
    institution_name = _institution_name(institution_id)
    session.execute(
        sa.insert(rm_products).values(
            product_id=event.aggregate_id,
            institution_id=institution_id,
            institution_name=institution_name,
            is_active=True,
            search_text=_search(payload["name"], institution_name, payload["track"], payload.get("symbol")),
            updated_at=to_naive_utc(event.occurred_at),
            **{column: cast(payload[column]) for column, cast in _COLUMNS.items()},
        )
    )


def project_product_updated(event: Event, session: Session) -> None:
    row = session.execute(
        sa.select(rm_products).where(rm_products.c.product_id == event.aggregate_id)
    ).mappings().one()
    changes = {column: cast(event.payload[column]) for column, cast in _COLUMNS.items() if column in event.payload}
    name = changes.get("name", row["name"])
    track = changes.get("track", row["track"])
    symbol = changes["symbol"] if "symbol" in changes else row["symbol"]
    changes["search_text"] = _search(name, row["institution_name"], track, symbol)
    changes["updated_at"] = to_naive_utc(event.occurred_at)
    session.execute(sa.update(rm_products).where(rm_products.c.product_id == event.aggregate_id).values(**changes))


def project_product_deactivated(event: Event, session: Session) -> None:
    session.execute(
        sa.update(rm_products)
        .where(rm_products.c.product_id == event.aggregate_id)
        .values(is_active=False, updated_at=to_naive_utc(event.occurred_at))
    )


def project_document_uploaded(event: Event, session: Session) -> None:
    payload = event.payload
    session.execute(
        sa.insert(rm_product_documents).values(
            document_id=UUID(str(payload["document_id"])),
            product_id=event.aggregate_id,
            file_name=payload["file_name"],
            stored_name=payload["stored_name"],
            doc_type=payload["doc_type"],
            storage_path=payload["storage_path"],
            sha256=payload["sha256"],
            size_bytes=int(payload["size_bytes"]),
            index_status="PENDING_INDEX",
            chunks_count=None,
            uploaded_at=to_naive_utc(event.occurred_at),
        )
    )
    session.execute(
        sa.update(rm_products)
        .where(rm_products.c.product_id == event.aggregate_id)
        .values(updated_at=to_naive_utc(event.occurred_at))
    )


def _institution_name(institution_id: UUID) -> str:
    institution = find_institution(institution_id)
    return institution.name if institution is not None else str(institution_id)


def _search(name: object, institution_name: object, track: object, symbol: object) -> str:
    parts = [name, institution_name, track, symbol or ""]
    return " ".join(str(part) for part in parts if part).lower()
