"""התראות במערכת. ראו docs/08 §8.6."""

from uuid import UUID

from flask import Blueprint, current_app, jsonify, request
from goalvest_core import NotFound

from app.auth.require_role import require_role
from app.bootstrap import build_command_bus
from app.commands.notifications import MarkNotificationRead
from app.controllers.errors import error_response
from app.controllers.http import actor_id, command_id, correlation_id, missing_command_id
from app.infrastructure.db import get_db
from app.queries.notifications import list_notifications, unread_count

notifications_bp = Blueprint("notifications", __name__)


@notifications_bp.get("/notifications")
@require_role("INVESTOR", "AGENT")
def read_notifications():
    unread_only = (request.args.get("unreadOnly") or "").strip().lower() in {"1", "true", "yes"}
    return jsonify(list_notifications(get_db(), actor_id(), unread_only=unread_only))


@notifications_bp.get("/notifications/unread-count")
@require_role("INVESTOR", "AGENT")
def read_unread_count():
    return jsonify(unread_count(get_db(), actor_id()))


@notifications_bp.post("/notifications/<uuid:notification_id>/read")
@require_role("INVESTOR", "AGENT")
def mark_read(notification_id: UUID):
    key = command_id()
    if key is None:
        return missing_command_id()
    try:
        result = build_command_bus(get_db(), current_app.extensions["projections"]).dispatch(
            MarkNotificationRead(
                command_id=key,
                actor_id=actor_id(),
                notification_id=notification_id,
                correlation_id=correlation_id(),
            )
        )
    except NotFound as exc:
        return error_response(404, exc.code, str(exc))
    return jsonify({"id": str(result.id), "version": result.version}), 201
