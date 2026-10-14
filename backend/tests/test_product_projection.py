"""אירוע מוצר → שורה ב-rm_products או ב-rm_product_documents."""

from decimal import Decimal

import sqlalchemy as sa
from app.bootstrap import build_dispatcher
from app.infrastructure.event_store import EventStoreRepository
from app.infrastructure.tables import rm_product_documents, rm_products
from app.reference.institutions import INSTITUTIONS
from goalvest_core.products import Product

INSTITUTION = INSTITUTIONS[0]


def _fields(**overrides):
    data = {
        "product_type": "ETF",
        "name": "SPDR S&P 500",
        "track": "S&P 500",
        "symbol": "SPY",
        "fee_deposit": Decimal("0.00"),
        "fee_assets": Decimal("0.09"),
        "return_1y": Decimal("16.20"),
        "return_3y": Decimal("12.40"),
        "return_5y": Decimal("11.10"),
        "std_dev": Decimal("15.80"),
        "risk_level": 5,
        "liquidity": "HIGH",
        "liquidity_terms": "אפשר למשוך בלי תקופת נעילה.",
        "tax_notes": "רווח חייב במס רווחי הון לפי הדין.",
        "min_deposit": Decimal("0.00"),
        "description": "תעודת סל להמחשה.",
    }
    data.update(overrides)
    return data


def test_create_update_deactivate_and_upload_project_read_models(session):
    product = Product()
    product.create(institution_id=INSTITUTION.id, known_institutions={str(INSTITUTION.id)}, **_fields())
    repo = EventStoreRepository(session, build_dispatcher())
    repo.append(product.aggregate_id, 0, product.uncommitted_events)
    session.commit()
    row = session.execute(sa.select(rm_products)).mappings().one()
    assert row["name"] == "SPDR S&P 500"
    assert row["institution_name"] == INSTITUTION.name
    assert row["is_active"] is True
    assert "s&p" in row["search_text"]
    assert "spy" in row["search_text"]

    updated = Product.from_events(repo.load(product.aggregate_id, "Product"))
    updated.update(**_fields(fee_assets=Decimal("0.03")))
    repo.append(updated.aggregate_id, updated.version - 1, updated.uncommitted_events)
    session.commit()
    row = session.execute(sa.select(rm_products)).mappings().one()
    assert row["fee_assets"] == Decimal("0.03")

    current = Product.from_events(repo.load(product.aggregate_id, "Product"))
    current.upload_document(content=b"%PDF-1.4\n", original_name="מדיניות.pdf", doc_type="POLICY_TERMS")
    repo.append(current.aggregate_id, current.version - 1, current.uncommitted_events)
    session.commit()
    document = session.execute(sa.select(rm_product_documents)).mappings().one()
    assert document["product_id"] == product.aggregate_id
    assert document["index_status"] == "PENDING_INDEX"
    assert document["chunks_count"] is None
    assert document["stored_name"].endswith(".pdf")
    assert document["file_name"] == "מדיניות.pdf"

    deactivated = Product.from_events(repo.load(product.aggregate_id, "Product"))
    deactivated.deactivate("לא משווק")
    repo.append(deactivated.aggregate_id, deactivated.version - 1, deactivated.uncommitted_events)
    session.commit()
    row = session.execute(sa.select(rm_products)).mappings().one()
    assert row["is_active"] is False
    assert row["product_id"] == product.aggregate_id
