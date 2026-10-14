"""API מוצרים: חיפוש, 400, 403, TC-16 ו-TC-18."""

import io
import zipfile
from uuid import uuid4

import pytest
import sqlalchemy as sa
from app import create_app
from app.bootstrap import build_command_bus
from app.config import Config
from app.infrastructure.db import get_db
from app.infrastructure.tables import metadata, rm_product_documents, rm_products
from app.reference.institutions import INSTITUTIONS
from flask import current_app
from scripts.seed import run_seed
from sqlalchemy import create_engine
from sqlalchemy.dialects import mssql
from sqlalchemy.pool import StaticPool


@pytest.fixture
def client(tmp_path):
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    metadata.create_all(engine)

    class TestConfig(Config):
        DB_ENGINE = engine
        JWT_SECRET = "unit-test-jwt-secret-0123456789abcd"
        RATELIMIT_ENABLED = False
        TESTING = True
        DOCUMENT_STORAGE_DIR = str(tmp_path)

    app = create_app(TestConfig)
    yield app.test_client()
    engine.dispose()


def _headers(token=None):
    headers = {"Idempotency-Key": str(uuid4())}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _register(client, **overrides):
    body = {
        "fullName": "נועה לוי",
        "email": "noa@mail.com",
        "phone": "0501234567",
        "password": "Secret12",
        "role": "INVESTOR",
    }
    body.update(overrides)
    return client.post("/api/auth/register", json=body, headers=_headers())


def _token(client, email="noa@mail.com", password="Secret12"):
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.get_json()["accessToken"]


def _agent(client, email, institution):
    created = _register(
        client,
        email=email,
        fullName="סוכן דמו",
        role="AGENT",
        institutionId=str(institution.id),
        licenseNo="LIC-9",
    )
    assert created.status_code == 201
    return _token(client, email)


def _product(**overrides):
    body = {
        "type": "HISHTALMUT",
        "name": "אופק השתלמות",
        "track": "מסלול כללי",
        "feeDeposit": "0.00",
        "feeAssets": "0.80",
        "return1y": "7.20",
        "return3y": "6.10",
        "return5y": "5.40",
        "stdDev": "8.50",
        "riskLevel": 3,
        "liquidity": "PARTIAL",
        "liquidityTerms": "הנזילות חלקית ותלויה בוותק.",
        "taxNotes": "כללי המס נקבעים לפי הדין העדכני.",
        "minDeposit": "0.00",
        "description": "קרן להמחשה.",
    }
    body.update(overrides)
    return body


def _docx() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("word/document.xml", "<w:document/>")
    return buffer.getvalue()


def test_catalog_query_compiles_for_sql_server():
    from app.queries.products import _filters

    filters = _filters(
        q="",
        types=[],
        risk_min=None,
        risk_max=None,
        max_fee=None,
        min_return_3y=None,
        liquidity=None,
        institution_id=None,
        include_inactive=False,
        viewer_role="INVESTOR",
        viewer_institution=None,
    )
    stmt = sa.select(rm_products).where(*filters)
    sql = str(stmt.compile(dialect=mssql.dialect()))
    assert "IS 1" not in sql
    assert "IS 0" not in sql


def test_investor_lists_filters_and_reads_details(client):
    token = _agent(client, "agent@mail.com", INSTITUTIONS[0])
    assert client.post("/api/agent/products", json=_product(), headers=_headers(token)).status_code == 201
    assert client.post(
        "/api/agent/products",
        json=_product(type="ETF", name="Invesco QQQ", track="נאסד\"ק 100", symbol="QQQ", liquidity="HIGH", riskLevel=6),
        headers=_headers(token),
    ).status_code == 201
    assert _register(client).status_code == 201
    investor = _token(client)

    listed = client.get("/api/products", query_string={"q": "QQQ", "type": "CAPITAL_MARKET"}, headers=_headers(investor))
    assert listed.status_code == 200
    body = listed.get_json()
    assert body["total"] == 1
    assert body["items"][0]["symbol"] == "QQQ"
    assert body["pageSize"] == 20

    product_id = body["items"][0]["productId"]
    details = client.get(f"/api/products/{product_id}", headers=_headers(investor))
    assert details.status_code == 200
    payload = details.get_json()
    assert payload["documents"] == []
    assert payload["fit"] is None
    assert payload["agents"][0]["fullName"] == "סוכן דמו"
    assert client.get("/api/products").status_code == 401


def test_other_institution_is_forbidden_and_invalid_input_is_400(client):
    owner = _agent(client, "owner@mail.com", INSTITUTIONS[0])
    other = _agent(client, "other@mail.com", INSTITUTIONS[1])
    created = client.post("/api/agent/products", json=_product(name="מוצר מגדל"), headers=_headers(owner))
    assert created.status_code == 201
    product_id = created.get_json()["id"]

    forbidden = client.put(f"/api/agent/products/{product_id}", json=_product(name="ניסיון"), headers=_headers(other))
    assert forbidden.status_code == 403
    upload = client.post(
        f"/api/agent/products/{product_id}/documents",
        data={"file": (io.BytesIO(b"%PDF-1.4\n"), "a.pdf"), "docType": "POLICY_TERMS"},
        headers=_headers(other),
    )
    assert upload.status_code == 403

    assert _register(client).status_code == 201
    investor = _token(client)
    assert client.post("/api/agent/products", json=_product(), headers=_headers(investor)).status_code == 403
    invalid = client.post("/api/agent/products", json=_product(name=" "), headers=_headers(owner))
    assert invalid.status_code == 400
    assert "name" in invalid.get_json()["error"]["fields"]


def test_tc16_exe_renamed_to_pdf_is_rejected(client, tmp_path):
    token = _agent(client, "agent@mail.com", INSTITUTIONS[0])
    created = client.post("/api/agent/products", json=_product(), headers=_headers(token))
    product_id = created.get_json()["id"]
    rejected = client.post(
        f"/api/agent/products/{product_id}/documents",
        data={"file": (io.BytesIO(b"MZ" + b"\x00" * 128), "report.pdf"), "docType": "POLICY_TERMS"},
        headers=_headers(token),
    )
    assert rejected.status_code == 400
    assert rejected.get_json()["error"]["code"] == "VALIDATION_ERROR"
    assert list(tmp_path.iterdir()) == []

    accepted = client.post(
        f"/api/agent/products/{product_id}/documents",
        data={"file": (io.BytesIO(b"%PDF-1.4\n"), "report.pdf"), "docType": "POLICY_TERMS"},
        headers=_headers(token),
    )
    assert accepted.status_code == 201
    stored = list(tmp_path.iterdir())
    assert len(stored) == 1
    assert stored[0].suffix == ".pdf"
    assert stored[0].stem != "report"

    docx = client.post(
        f"/api/agent/products/{product_id}/documents",
        data={"file": (io.BytesIO(_docx()), "notes.docx"), "docType": "MARKET_REPORT"},
        headers=_headers(token),
    )
    assert docx.status_code == 201
    details = client.get(f"/api/products/{product_id}", headers=_headers(token))
    documents = details.get_json()["documents"]
    assert [item["indexStatus"] for item in documents] == ["PENDING_INDEX", "PENDING_INDEX"]
    download = client.get(f"/api/documents/{documents[0]['documentId']}/download", headers=_headers(token))
    assert download.status_code == 200
    assert download.data.startswith(b"%PDF")
    with client.application.app_context():
        count = get_db().execute(sa.select(sa.func.count()).select_from(rm_product_documents)).scalar_one()
    assert count == 2


def test_tc18_search_sp_returns_every_matching_track(client):
    with client.application.app_context():
        session = get_db()
        run_seed(session, build_command_bus(session, current_app.extensions["projections"]))
    assert _register(client, email="reader@mail.com").status_code == 201
    token = _token(client, "reader@mail.com")
    response = client.get("/api/products", query_string={"q": "S&P", "pageSize": "20"}, headers=_headers(token))
    assert response.status_code == 200
    body = response.get_json()
    assert body["total"] >= 3
    assert body["total"] == len(body["items"])
    assert all("s&p" in f"{item['track']} {item['name']} {item['symbol'] or ''}".lower() for item in body["items"])
    symbols = {item["symbol"] for item in body["items"]}
    assert "SPY" in symbols
    assert "QQQ" not in symbols
    assert "TEVA.TA" not in symbols


def test_deactivate_hides_product_from_catalog_but_not_from_agent(client):
    token = _agent(client, "agent@mail.com", INSTITUTIONS[0])
    created = client.post("/api/agent/products", json=_product(name="יוסר מהקטלוג"), headers=_headers(token))
    product_id = created.get_json()["id"]
    assert client.post(f"/api/agent/products/{product_id}/deactivate", json={}, headers=_headers(token)).status_code == 201
    catalog = client.get("/api/products", query_string={"q": "יוסר"}, headers=_headers(token))
    assert catalog.get_json()["total"] == 0
    mine = client.get("/api/products", query_string={"includeInactive": "true"}, headers=_headers(token))
    assert mine.get_json()["total"] == 1
    assert mine.get_json()["items"][0]["isActive"] is False
