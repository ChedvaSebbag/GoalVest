"""CommandBus – רישום handlers ו-idempotency מול ProcessedCommands. ראו docs/06 §6.4."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

import sqlalchemy as sa
from goalvest_core import EmailAlreadyExists
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.infrastructure.conflicts import is_email_unique_violation
from app.infrastructure.event_store import EventStoreRepository
from app.infrastructure.serialization import dumps, loads, to_naive_utc
from app.infrastructure.tables import processed_commands
from app.projections.dispatcher import ProjectionDispatcher


@dataclass(frozen=True)
class Command:
    command_id: UUID


@dataclass(frozen=True)
class CommandResult:
    id: UUID
    version: int


@dataclass(frozen=True)
class CommandContext:
    repository: EventStoreRepository


Handler = Callable[[Command, CommandContext], CommandResult]


class CommandBus:
    def __init__(self, session: Session, dispatcher: ProjectionDispatcher | None = None) -> None:
        self._session = session
        self._dispatcher = dispatcher if dispatcher is not None else ProjectionDispatcher()
        self._repository = EventStoreRepository(session, self._dispatcher)
        self._handlers: dict[type[Command], Handler] = {}

    def register(self, command_type: type[Command], handler: Handler) -> None:
        if command_type in self._handlers:
            raise ValueError(f"כבר רשום handler ל-{command_type.__name__}")
        self._handlers[command_type] = handler

    def dispatch(self, command: Command) -> CommandResult:
        stored = self._stored_result(command.command_id)
        if stored is not None:
            return stored
        handler = self._handlers.get(type(command))
        if handler is None:
            raise LookupError(f"אין handler לפקודה {type(command).__name__}")
        try:
            result = handler(command, CommandContext(repository=self._repository))
            if not isinstance(result, CommandResult):
                raise TypeError("handler מחזיר CommandResult בלבד: id ו-version")
            try:
                self._session.execute(
                    sa.insert(processed_commands).values(
                        command_id=command.command_id,
                        result_json=dumps({"id": str(result.id), "version": result.version}),
                        processed_at=to_naive_utc(datetime.now(UTC)),
                    )
                )
                self._session.commit()
            except IntegrityError:
                self._session.rollback()
                stored = self._stored_result(command.command_id)
                if stored is None:
                    raise
                return stored
        except IntegrityError as exc:
            self._session.rollback()
            if is_email_unique_violation(exc):
                raise EmailAlreadyExists() from exc
            raise
        except Exception:
            self._session.rollback()
            raise
        return result

    def _stored_result(self, command_id: UUID) -> CommandResult | None:
        row = (
            self._session.execute(
                sa.select(processed_commands.c.result_json).where(
                    processed_commands.c.command_id == command_id
                )
            )
            .mappings()
            .first()
        )
        if row is None:
            return None
        data = loads(row["result_json"])
        return CommandResult(id=UUID(data["id"]), version=data["version"])
