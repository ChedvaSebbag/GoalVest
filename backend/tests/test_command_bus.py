"""idempotency של CommandBus מול ProcessedCommands."""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from app.commands.bus import Command, CommandBus, CommandContext, CommandResult
from app.infrastructure.event_store import EventStoreRepository
from app.infrastructure.serialization import dumps, to_naive_utc
from app.infrastructure.tables import processed_commands
from goalvest_core import Event


@dataclass(frozen=True)
class OpenWallet(Command):
    aggregate_id: UUID


def _handle(command: OpenWallet, ctx: CommandContext, calls: dict) -> CommandResult:
    calls["n"] += 1
    ctx.repository.append(
        command.aggregate_id,
        0,
        [
            Event(
                event_id=uuid4(),
                aggregate_id=command.aggregate_id,
                version=1,
                event_type="AccountOpened",
                aggregate_type="Wallet",
            )
        ],
    )
    return CommandResult(id=command.aggregate_id, version=1)


def test_same_command_id_runs_the_handler_once(session):
    calls = {"n": 0}
    bus = CommandBus(session)
    bus.register(OpenWallet, lambda command, ctx: _handle(command, ctx, calls))
    command = OpenWallet(command_id=uuid4(), aggregate_id=uuid4())

    first = bus.dispatch(command)
    second = bus.dispatch(command)

    assert first == CommandResult(id=command.aggregate_id, version=1)
    assert second == first
    assert isinstance(second.id, UUID)
    assert calls["n"] == 1
    assert session.scalar(sa.select(sa.func.count()).select_from(processed_commands)) == 1
    assert len(EventStoreRepository(session).load(command.aggregate_id)) == 1


def test_parallel_processed_command_returns_stored_result(session, monkeypatch):
    command = OpenWallet(command_id=uuid4(), aggregate_id=uuid4())
    winner = CommandResult(id=command.aggregate_id, version=4)
    session.execute(
        sa.insert(processed_commands).values(
            command_id=command.command_id,
            result_json=dumps({"id": str(winner.id), "version": winner.version}),
            processed_at=to_naive_utc(datetime.now(UTC)),
        )
    )
    session.commit()

    lookups = {"n": 0}
    original = CommandBus._stored_result

    def hide_the_winning_row_on_the_first_lookup(self, command_id):
        lookups["n"] += 1
        if lookups["n"] == 1:
            return None
        return original(self, command_id)

    monkeypatch.setattr(CommandBus, "_stored_result", hide_the_winning_row_on_the_first_lookup)

    calls = {"n": 0}
    bus = CommandBus(session)
    bus.register(OpenWallet, lambda cmd, ctx: _handle(cmd, ctx, calls))

    result = bus.dispatch(command)

    assert result == winner
    assert calls["n"] == 1
    assert session.scalar(sa.select(sa.func.count()).select_from(processed_commands)) == 1
    assert EventStoreRepository(session).load(command.aggregate_id) == []
