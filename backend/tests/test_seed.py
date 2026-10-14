"""Seed אידמפוטנטי: 25 מוצרים, 3 משקיעים, 3 סוכנים, ורק דרך פקודות."""

import sqlalchemy as sa
from app.auth.passwords import verify_password
from app.bootstrap import build_command_bus, build_dispatcher
from app.infrastructure.tables import event_store, rm_products, rm_users
from app.reference.institutions import INSTITUTIONS
from scripts.seed import PASSWORD, run_seed


def test_seed_is_idempotent_and_covers_channels(session):
    bus = build_command_bus(session, build_dispatcher())
    first = run_seed(session, bus)
    events_after_first = session.execute(sa.select(sa.func.count()).select_from(event_store)).scalar_one()
    second = run_seed(session, bus)
    events_after_second = session.execute(sa.select(sa.func.count()).select_from(event_store)).scalar_one()

    assert first == {"investors": 3, "agents": 3, "products": 25}
    assert second == first
    assert events_after_first == events_after_second
    assert session.execute(sa.select(sa.func.count()).select_from(rm_products)).scalar_one() == 25
    assert session.execute(sa.select(sa.func.count()).select_from(rm_users)).scalar_one() == 6

    rows = session.execute(sa.select(rm_products)).mappings().all()
    types = {row["type"] for row in rows}
    assert types == {"HISHTALMUT", "GEMEL_INVESTMENT", "SAVINGS_POLICY", "STOCK", "ETF"}
    symbols = {row["symbol"] for row in rows}
    assert {"SPY", "QQQ", "TEVA.TA"} <= symbols
    sp_tracks = [row["track"] for row in rows if "s&p" in row["track"].lower()]
    assert len(sp_tracks) >= 3
    known = {item.id for item in INSTITUTIONS}
    assert {row["institution_id"] for row in rows} <= known

    investor = session.execute(
        sa.select(rm_users.c.password_hash).where(rm_users.c.email == "demo.investor1@goalvest.test")
    ).scalar_one()
    agent = session.execute(
        sa.select(rm_users.c.role, rm_users.c.institution_id, rm_users.c.password_hash).where(
            rm_users.c.email == "demo.agent.migdal@goalvest.test"
        )
    ).one()
    assert verify_password(PASSWORD, investor)
    assert agent.role == "AGENT"
    assert agent.institution_id == INSTITUTIONS[0].id
    assert verify_password(PASSWORD, agent.password_hash)
