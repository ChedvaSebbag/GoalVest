"""קטלוג מוצרים וניהול מוצר של הסוכן. ראו docs/08 §8.4."""

from decimal import Decimal, InvalidOperation
from pathlib import Path
from uuid import UUID

from flask import Blueprint, current_app, jsonify, request, send_file
from flask_jwt_extended import get_jwt
from goalvest_core import BusinessRuleViolation, Forbidden, NotFound
from goalvest_core.products import MAX_DOCUMENT_BYTES
from pydantic import ValidationError

from app.auth.require_role import require_role
from app.bootstrap import build_command_bus
from app.commands.products import CreateProduct, DeactivateProduct, UpdateProduct, UploadProductDocument
from app.controllers.errors import error_response, rule_response, validation_response
from app.controllers.http import actor_id, command_id, correlation_id, missing_command_id, parse_body
from app.infrastructure.db import get_db
from app.products.schemas import DeactivateBody, ProductBody
from app.products.storage import resolve_stored
from app.queries.products import get_document, get_product, list_documents, list_products, product_institution

products_bp = Blueprint("products", __name__)
_MEDIA = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def _dispatch(command):
    try:
        result = build_command_bus(get_db(), current_app.extensions["projections"]).dispatch(command)
    except NotFound as exc:
        return error_response(404, exc.code, str(exc))
    except Forbidden as exc:
        return error_response(403, exc.code, str(exc))
    except BusinessRuleViolation as exc:
        return rule_response(exc)
    return jsonify({"id": str(result.id), "version": result.version}), 201


@products_bp.get("/products")
@require_role("INVESTOR", "AGENT")
def read_products():
    parsed, error = _list_args()
    if error is not None:
        return error
    role, institution = _viewer()
    try:
        page = list_products(get_db(), viewer_role=role, viewer_institution=institution, **parsed)
    except BusinessRuleViolation as exc:
        return rule_response(exc)
    return jsonify(page)


@products_bp.get("/products/<uuid:product_id>")
@require_role("INVESTOR", "AGENT")
def read_product(product_id: UUID):
    product = get_product(get_db(), product_id)
    if product is None:
        return error_response(404, "NOT_FOUND", "הפריט לא נמצא")
    return jsonify(product)


@products_bp.post("/agent/products")
@require_role("AGENT")
def post_product():
    body, error = parse_body(ProductBody)
    if error is not None:
        return error
    key = command_id()
    if key is None:
        return missing_command_id()
    return _dispatch(CreateProduct(
        command_id=key,
        actor_id=actor_id(),
        data=body.as_kwargs(),
        correlation_id=correlation_id(),
    ))


@products_bp.put("/agent/products/<uuid:product_id>")
@require_role("AGENT")
def put_product(product_id: UUID):
    body, error = parse_body(ProductBody)
    if error is not None:
        return error
    key = command_id()
    if key is None:
        return missing_command_id()
    return _dispatch(UpdateProduct(
        command_id=key,
        actor_id=actor_id(),
        product_id=product_id,
        data=body.as_kwargs(),
        correlation_id=correlation_id(),
    ))


@products_bp.post("/agent/products/<uuid:product_id>/deactivate")
@require_role("AGENT")
def post_deactivate(product_id: UUID):
    payload = request.get_json(silent=True)
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        return error_response(400, "VALIDATION_ERROR", "הקלט אינו תקין")
    try:
        body = DeactivateBody.model_validate(payload)
    except ValidationError as exc:
        return validation_response(exc)
    key = command_id()
    if key is None:
        return missing_command_id()
    return _dispatch(DeactivateProduct(
        command_id=key,
        actor_id=actor_id(),
        product_id=product_id,
        reason=body.reason,
        correlation_id=correlation_id(),
    ))


@products_bp.post("/agent/products/<uuid:product_id>/documents")
@require_role("AGENT")
def post_document(product_id: UUID):
    uploaded = request.files.get("file")
    doc_type = (request.form.get("docType") or "").strip()
    if uploaded is None:
        return error_response(400, "VALIDATION_ERROR", "הקלט אינו תקין", {"file": "יש לבחור קובץ"})
    if not doc_type:
        return error_response(400, "VALIDATION_ERROR", "הקלט אינו תקין", {"docType": "יש לבחור סוג מסמך"})
    key = command_id()
    if key is None:
        return missing_command_id()
    content = uploaded.stream.read(MAX_DOCUMENT_BYTES + 1)
    return _dispatch(UploadProductDocument(
        command_id=key,
        actor_id=actor_id(),
        product_id=product_id,
        content=content,
        original_name=uploaded.filename or "",
        doc_type=doc_type,
        storage_dir=current_app.config["DOCUMENT_STORAGE_DIR"],
        correlation_id=correlation_id(),
    ))


@products_bp.get("/agent/products/<uuid:product_id>/documents")
@require_role("AGENT")
def read_documents(product_id: UUID):
    session = get_db()
    institution = product_institution(session, product_id)
    if institution is None:
        return error_response(404, "NOT_FOUND", "הפריט לא נמצא")
    _, own = _viewer()
    if own != institution:
        return error_response(403, "FORBIDDEN", "אפשר לנהל רק מוצרים של הגוף שלך")
    return jsonify({"items": list_documents(session, product_id)})


@products_bp.get("/documents/<uuid:document_id>/download")
@require_role("INVESTOR", "AGENT")
def download_document(document_id: UUID):
    document = get_document(get_db(), document_id)
    if document is None:
        return error_response(404, "NOT_FOUND", "הפריט לא נמצא")
    path = resolve_stored(Path(current_app.config["DOCUMENT_STORAGE_DIR"]), document["storedName"])
    if not path.is_file():
        return error_response(404, "NOT_FOUND", "הפריט לא נמצא")
    return send_file(
        path,
        mimetype=_MEDIA.get(path.suffix, "application/octet-stream"),
        download_name=document["fileName"],
        as_attachment=True,
    )


def _viewer() -> tuple[str | None, UUID | None]:
    claims = get_jwt()
    raw = claims.get("institution_id")
    try:
        institution = UUID(raw) if raw else None
    except ValueError:
        institution = None
    role = claims.get("role")
    return role if isinstance(role, str) else None, institution


def _list_args() -> tuple[dict | None, object]:
    try:
        page = int(request.args.get("page", "1"))
        page_size = int(request.args.get("pageSize", "20"))
        risk_min = _optional_int("riskMin")
        risk_max = _optional_int("riskMax")
        max_fee = _optional_decimal("maxFee")
        min_return = _optional_decimal("minReturn3y")
    except ValueError:
        return None, error_response(400, "VALIDATION_ERROR", "הקלט אינו תקין")
    institution = request.args.get("institutionId")
    try:
        institution_id = UUID(institution) if institution else None
    except ValueError:
        return None, error_response(400, "VALIDATION_ERROR", "הקלט אינו תקין", {"institutionId": "גוף לא מוכר"})
    return {
        "q": request.args.get("q", ""),
        "types": [item for item in request.args.getlist("type") if item],
        "risk_min": risk_min,
        "risk_max": risk_max,
        "max_fee": max_fee,
        "min_return_3y": min_return,
        "liquidity": request.args.get("liquidity") or None,
        "institution_id": institution_id,
        "page": page,
        "page_size": page_size,
        "sort": request.args.get("sort", "name,asc"),
        "include_inactive": request.args.get("includeInactive", "").lower() == "true",
    }, None


def _optional_int(name: str) -> int | None:
    raw = request.args.get(name)
    if raw is None or raw == "":
        return None
    return int(raw)


def _optional_decimal(name: str) -> Decimal | None:
    raw = request.args.get(name)
    if raw is None or raw == "":
        return None
    try:
        return Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError(name) from exc
