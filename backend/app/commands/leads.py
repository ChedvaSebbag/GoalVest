"""פעולות סוכן על ליד: לקיחה, אישור, דחייה, הערכה מחדש והצעה."""

from dataclasses import dataclass
from uuid import UUID, uuid4

import sqlalchemy as sa
from goalvest_core import Forbidden, NotFound
from goalvest_core.requests import InvestmentRequest
from goalvest_core.requests.investment_request import OfferProduct
from sqlalchemy.orm import Session

from app.commands.bus import Command, CommandContext, CommandResult
from app.commands.loading import load_typed, save
from app.infrastructure.tables import rm_leads, rm_products
from app.queries.users import get_user


@dataclass(frozen=True)
class ClaimLead(Command):
    actor_id: UUID
    request_id: UUID
    correlation_id: str | None = None


@dataclass(frozen=True)
class ApproveAssessment(Command):
    actor_id: UUID
    request_id: UUID
    note: str = ""
    correlation_id: str | None = None


@dataclass(frozen=True)
class RejectAssessment(Command):
    actor_id: UUID
    request_id: UUID
    note: str = ""
    correlation_id: str | None = None


@dataclass(frozen=True)
class RequestReevaluation(Command):
    actor_id: UUID
    request_id: UUID
    reason: str = ""
    correlation_id: str | None = None


@dataclass(frozen=True)
class SendOffer(Command):
    actor_id: UUID
    request_id: UUID
    items: tuple[dict, ...]
    message: str
    correlation_id: str | None = None


def handle_claim(command: ClaimLead, ctx: CommandContext) -> CommandResult:
    request, institution_id = _owned_lead(ctx, command.actor_id, command.request_id)
    previous = request.version
    request.claim(
        agent_id=command.actor_id,
        institution_id=institution_id,
        metadata=_meta(command, "AGENT"),
    )
    save(ctx, request, previous)
    return CommandResult(id=request.aggregate_id, version=request.version)


def handle_approve(command: ApproveAssessment, ctx: CommandContext) -> CommandResult:
    request, _institution = _owned_lead(ctx, command.actor_id, command.request_id)
    previous = request.version
    request.approve_assessment(agent_id=command.actor_id, note=command.note, metadata=_meta(command, "AGENT"))
    save(ctx, request, previous)
    return CommandResult(id=request.aggregate_id, version=request.version)


def handle_reject(command: RejectAssessment, ctx: CommandContext) -> CommandResult:
    request, _institution = _owned_lead(ctx, command.actor_id, command.request_id)
    previous = request.version
    request.reject_assessment(agent_id=command.actor_id, note=command.note, metadata=_meta(command, "AGENT"))
    save(ctx, request, previous)
    return CommandResult(id=request.aggregate_id, version=request.version)


def handle_reevaluate(command: RequestReevaluation, ctx: CommandContext) -> CommandResult:
    request, _institution = _owned_lead(ctx, command.actor_id, command.request_id)
    previous = request.version
    request.request_reevaluation(
        agent_id=command.actor_id,
        reason=command.reason,
        metadata=_meta(command, "AGENT"),
    )
    save(ctx, request, previous)
    return CommandResult(id=request.aggregate_id, version=request.version)


def handle_send_offer(command: SendOffer, ctx: CommandContext) -> CommandResult:
    request, institution_id = _owned_lead(ctx, command.actor_id, command.request_id)
    offer_id = uuid4()
    items = [{"product_id": item["product_id"], "percent": item["percent"]} for item in command.items]
    products = _products(ctx.repository.session, [item["product_id"] for item in items])
    previous = request.version
    request.send_offer(
        agent_id=command.actor_id,
        institution_id=institution_id,
        offer_id=offer_id,
        items=items,
        message=command.message,
        products=products,
        metadata=_meta(command, "AGENT"),
    )
    save(ctx, request, previous)
    return CommandResult(id=offer_id, version=request.version)


def _owned_lead(ctx: CommandContext, actor_id: UUID, request_id: UUID) -> tuple[InvestmentRequest, UUID]:
    institution_id = _institution(ctx.repository.session, actor_id)
    lead = ctx.repository.session.execute(
        sa.select(rm_leads.c.request_id).where(
            rm_leads.c.request_id == request_id,
            rm_leads.c.institution_id == institution_id,
        )
    ).first()
    if lead is None:
        raise NotFound()
    return load_typed(ctx, InvestmentRequest, request_id), institution_id


def _institution(session: Session, actor_id: UUID) -> UUID:
    user = get_user(session, actor_id)
    if user is None or user["role"] != "AGENT" or not user["institutionId"]:
        raise Forbidden()
    return UUID(user["institutionId"])


def _products(session: Session, product_ids: list[UUID]) -> tuple[OfferProduct, ...]:
    if not product_ids:
        return ()
    rows = session.execute(
        sa.select(rm_products.c.product_id, rm_products.c.institution_id, rm_products.c.is_active).where(
            rm_products.c.product_id.in_(product_ids)
        )
    ).mappings()
    return tuple(
        OfferProduct(product_id=row["product_id"], institution_id=row["institution_id"], active=bool(row["is_active"]))
        for row in rows
    )


def _meta(command: Command, role: str) -> dict:
    return {
        "user_id": str(command.actor_id),
        "role": role,
        "correlation_id": command.correlation_id,
        "command_id": str(command.command_id),
    }
