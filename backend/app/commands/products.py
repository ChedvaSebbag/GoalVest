"""יצירה, עדכון, השבתה והעלאת מסמך. הגוף נלקח מהסוכן המחובר."""

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from goalvest_core import Forbidden
from goalvest_core.products import Product

from app.commands.bus import Command, CommandContext, CommandResult
from app.commands.loading import load_typed, save
from app.products.storage import write_stored
from app.queries.users import get_user
from app.reference.institutions import INSTITUTIONS


@dataclass(frozen=True)
class CreateProduct(Command):
    actor_id: UUID
    data: dict
    product_id: UUID | None = None
    correlation_id: str | None = None


@dataclass(frozen=True)
class UpdateProduct(Command):
    actor_id: UUID
    product_id: UUID
    data: dict
    correlation_id: str | None = None


@dataclass(frozen=True)
class DeactivateProduct(Command):
    actor_id: UUID
    product_id: UUID
    reason: str = ""
    correlation_id: str | None = None


@dataclass(frozen=True)
class UploadProductDocument(Command):
    actor_id: UUID
    product_id: UUID
    content: bytes
    original_name: str
    doc_type: str
    storage_dir: str
    correlation_id: str | None = None


def handle_create_product(command: CreateProduct, ctx: CommandContext) -> CommandResult:
    if command.product_id is not None:
        existing = ctx.repository.load(command.product_id, Product.aggregate_type)
        if existing:
            return CommandResult(id=command.product_id, version=existing[-1].version)
    institution = _own_institution(ctx, command.actor_id)
    product = Product(command.product_id)
    product.create(
        institution_id=institution,
        known_institutions=_known(),
        metadata=_meta(command, command.actor_id),
        **command.data,
    )
    save(ctx, product, 0)
    return CommandResult(id=product.aggregate_id, version=product.version)


def handle_update_product(command: UpdateProduct, ctx: CommandContext) -> CommandResult:
    product = _owned(ctx, command.product_id, command.actor_id)
    previous = product.version
    product.update(metadata=_meta(command, command.actor_id), **command.data)
    save(ctx, product, previous)
    return CommandResult(id=product.aggregate_id, version=product.version)


def handle_deactivate_product(command: DeactivateProduct, ctx: CommandContext) -> CommandResult:
    product = _owned(ctx, command.product_id, command.actor_id)
    previous = product.version
    product.deactivate(command.reason, _meta(command, command.actor_id))
    save(ctx, product, previous)
    return CommandResult(id=product.aggregate_id, version=product.version)


def handle_upload_document(command: UploadProductDocument, ctx: CommandContext) -> CommandResult:
    product = _owned(ctx, command.product_id, command.actor_id)
    previous = product.version
    product.upload_document(
        content=command.content,
        original_name=command.original_name,
        doc_type=command.doc_type,
        metadata=_meta(command, command.actor_id),
    )
    stored_name = product.uncommitted_events[-1].payload["stored_name"]
    write_stored(Path(command.storage_dir), stored_name, command.content)
    save(ctx, product, previous)
    return CommandResult(id=product.aggregate_id, version=product.version)


def _owned(ctx: CommandContext, product_id: UUID, actor_id: UUID) -> Product:
    institution = _own_institution(ctx, actor_id)
    product = load_typed(ctx, Product, product_id)
    if product.institution_id != institution:
        raise Forbidden("אפשר לנהל רק מוצרים של הגוף שלך")
    return product


def _own_institution(ctx: CommandContext, actor_id: UUID) -> UUID:
    user = get_user(ctx.repository.session, actor_id)
    if user is None or user["role"] != "AGENT" or not user["institutionId"]:
        raise Forbidden("אפשר לנהל רק מוצרים של הגוף שלך")
    return UUID(user["institutionId"])


def _known() -> set[str]:
    return {str(item.id) for item in INSTITUTIONS}


def _meta(command: Command, user_id: UUID) -> dict:
    correlation = getattr(command, "correlation_id", None)
    return {
        "user_id": str(user_id),
        "role": "AGENT",
        "correlation_id": correlation,
        "command_id": str(command.command_id),
    }
