"""מועמדים להערכה מתוך rm_products. אין טעינת Aggregate."""

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.infrastructure.tables import rm_products

_TYPES = {
    "capital_market": ("STOCK", "ETF"),
    "hishtalmut": ("HISHTALMUT",),
    "gemel_policy": ("GEMEL_INVESTMENT", "SAVINGS_POLICY"),
}
_EXCLUDED = {
    "CAPITAL_MARKET": "capital_market",
    "HISHTALMUT": "hishtalmut",
    "GEMEL_POLICY": "gemel_policy",
}
_BANDS = {1: (1, 3), 2: (1, 4), 3: (2, 5), 4: (3, 6), 5: (4, 7)}


def find_candidate_products(
    session: Session,
    *,
    risk_score: int,
    excluded_channels: list[str],
    liquidity_need: str,
    minimum: int = 10,
    limit: int = 15,
) -> list[dict]:
    """עד 15 מוצרים פעילים לפי סיכון ואפיק. אם בטווח הסיכון יש פחות מ-10, הטווח מורחב."""
    allowed = _allowed_types(excluded_channels)
    if not allowed:
        return []
    band = _BANDS.get(int(risk_score), (1, 7))
    ranked = _load(session, allowed, liquidity_need, band, limit)
    if len(ranked) < minimum:
        ranked = _load(session, allowed, liquidity_need, None, limit)
    return ranked


def _allowed_types(excluded_channels: list[str]) -> tuple[str, ...]:
    blocked = {_EXCLUDED[item] for item in excluded_channels if item in _EXCLUDED}
    chosen: list[str] = []
    for channel, types in _TYPES.items():
        if channel not in blocked:
            chosen.extend(types)
    return tuple(chosen)


def _load(
    session: Session,
    types: tuple[str, ...],
    liquidity_need: str,
    band: tuple[int, int] | None,
    limit: int,
) -> list[dict]:
    query = sa.select(rm_products).where(rm_products.c.is_active == sa.true(), rm_products.c.type.in_(types))
    if band is not None:
        query = query.where(rm_products.c.risk_level >= band[0], rm_products.c.risk_level <= band[1])
    if liquidity_need in {"PARTIAL", "HIGH"}:
        rank = sa.case((rm_products.c.liquidity == "HIGH", 0), else_=1)
    else:
        rank = sa.literal(0)
    rows = session.execute(
        query.order_by(rank, rm_products.c.risk_level, rm_products.c.name).limit(limit)
    ).mappings()
    return [_public(row) for row in rows]


def _public(row) -> dict:
    product_type = row["type"]
    channel = next(name for name, types in _TYPES.items() if product_type in types)
    return {
        "product_id": str(row["product_id"]),
        "name": row["name"],
        "type": product_type,
        "channel": channel,
        "institution_name": row["institution_name"],
        "track": row["track"],
        "symbol": row["symbol"],
        "risk_level": int(row["risk_level"]),
        "liquidity": row["liquidity"],
        "fee_assets": format(row["fee_assets"], "f"),
        "fee_deposit": format(row["fee_deposit"], "f"),
    }
