"""Product: יצירה, עדכון, השבתה ודחיית קובץ שאינו PDF/DOCX."""

import io
import zipfile
from decimal import Decimal
from uuid import uuid4

import pytest
from app.reference.institutions import INSTITUTIONS
from goalvest_core import BusinessRuleViolation
from goalvest_core.products import MAX_DOCUMENT_BYTES, Product
from goalvest_core.products.product import _product_fields

INSTITUTION = INSTITUTIONS[0].id


def _fields(**overrides):
    data = {
        "product_type": "HISHTALMUT",
        "name": "אופק השתלמות",
        "track": "מחקה S&P 500",
        "symbol": None,
        "fee_deposit": Decimal("0.00"),
        "fee_assets": Decimal("0.55"),
        "return_1y": Decimal("14.80"),
        "return_3y": Decimal("11.20"),
        "return_5y": Decimal("10.40"),
        "std_dev": Decimal("15.10"),
        "risk_level": 5,
        "liquidity": "PARTIAL",
        "liquidity_terms": "הנזילות חלקית ותלויה בוותק.",
        "tax_notes": "כללי המס נקבעים לפי הדין העדכני.",
        "min_deposit": Decimal("0.00"),
        "description": "מסלול מחקה להמחשה.",
    }
    data.update(overrides)
    return data


def _product(**overrides) -> Product:
    product = Product()
    product.create(institution_id=INSTITUTION, known_institutions={str(INSTITUTION)}, **_fields(**overrides))
    return product


def _reload(product: Product) -> Product:
    return Product.from_events(product.uncommitted_events)


def test_given_valid_input_when_create_then_product_created():
    product = _product()
    event = product.uncommitted_events[0]
    assert event.event_type == "ProductCreated"
    assert event.schema_version == 1
    assert event.payload["type"] == "HISHTALMUT"
    assert event.payload["track"] == "מחקה S&P 500"
    assert event.payload["institution_id"] == str(INSTITUTION)
    assert product.status == "ACTIVE"


def test_invalid_risk_records_no_event():
    product = Product()
    with pytest.raises(BusinessRuleViolation) as caught:
        product.create(institution_id=INSTITUTION, known_institutions={str(INSTITUTION)}, **_fields(risk_level=8))
    assert caught.value.code == "INVALID_RISK"
    assert product.uncommitted_events == ()


def test_stock_requires_symbol_and_fund_rejects_one():
    stock = _product(product_type="STOCK", symbol="TEVA.TA", track="תל אביב", name="טבע")
    assert stock.uncommitted_events[0].payload["symbol"] == "TEVA.TA"
    with pytest.raises(BusinessRuleViolation) as caught:
        _product_fields(_fields(symbol="SPY"))
    assert caught.value.code == "INVALID_SYMBOL"


def test_update_records_only_changed_fields():
    product = _reload(_product())
    product.update(**_fields(fee_assets=Decimal("0.40")))
    event = product.uncommitted_events[0]
    assert event.event_type == "ProductUpdated"
    assert event.payload == {"fee_assets": Decimal("0.40")}


def test_deactivate_then_update_is_rejected():
    created = _product()
    history = list(created.uncommitted_events)
    product = Product.from_events(history)
    product.deactivate("הוחלף")
    history.extend(product.uncommitted_events)
    saved = Product.from_events(history)
    assert saved.status == "INACTIVE"
    with pytest.raises(BusinessRuleViolation) as caught:
        saved.update(**_fields())
    assert caught.value.code == "PRODUCT_INACTIVE"


def test_exe_renamed_to_pdf_is_rejected_and_pdf_is_accepted():
    product = _reload(_product())
    with pytest.raises(BusinessRuleViolation) as caught:
        product.upload_document(content=b"MZ" + b"\x00" * 64, original_name="report.pdf", doc_type="POLICY_TERMS")
    assert caught.value.code == "INVALID_FILE"
    assert product.uncommitted_events == ()
    product.upload_document(content=b"%PDF-1.4\n", original_name="report.pdf", doc_type="POLICY_TERMS")
    payload = product.uncommitted_events[0].payload
    assert product.uncommitted_events[0].event_type == "ProductDocumentUploaded"
    assert payload["stored_name"].endswith(".pdf")
    assert payload["file_name"] == "report.pdf"
    assert "report" not in payload["stored_name"]


def test_file_over_10mb_is_rejected():
    product = _reload(_product())
    content = b"%PDF-" + b"0" * MAX_DOCUMENT_BYTES
    with pytest.raises(BusinessRuleViolation) as caught:
        product.upload_document(content=content, original_name="big.pdf", doc_type="TAX_RULES")
    assert caught.value.code == "INVALID_FILE"


def test_docx_magic_is_accepted():
    product = _reload(_product())
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("word/document.xml", "<w:document/>")
    product.upload_document(content=buffer.getvalue(), original_name="תנאים.docx", doc_type="QUARTERLY_REPORT")
    assert product.uncommitted_events[0].payload["stored_name"].endswith(".docx")
    assert product.uncommitted_events[0].payload["doc_type"] == "QUARTERLY_REPORT"


def test_index_events_require_an_uploaded_document():
    created = _product()
    history = list(created.uncommitted_events)
    product = Product.from_events(history)
    with pytest.raises(BusinessRuleViolation) as caught:
        product.mark_document_indexed(document_id="missing", chunks_count=2, embedding_model="bge-m3")
    assert caught.value.code == "DOCUMENT_NOT_FOUND"
    product.upload_document(content=b"%PDF-1.4\n", original_name="report.pdf", doc_type="POLICY_TERMS")
    document_id = product.uncommitted_events[0].payload["document_id"]
    history.extend(product.uncommitted_events)
    saved = Product.from_events(history)
    saved.mark_document_indexed(document_id=document_id, chunks_count=2, embedding_model="bge-m3")
    indexed = saved.uncommitted_events[0]
    assert indexed.event_type == "ProductDocumentIndexed"
    assert indexed.payload["chunks_count"] == 2
    saved.mark_document_index_failed(document_id=document_id, error="נדרש מסמך עם טקסט")
    assert saved.uncommitted_events[1].event_type == "ProductDocumentIndexFailed"


def test_unknown_institution_is_rejected():
    with pytest.raises(BusinessRuleViolation) as caught:
        Product().create(institution_id=uuid4(), known_institutions=set(), **_fields())
    assert caught.value.code == "INVALID_INSTITUTION"
