"""המרות משותפות ל-projectors."""

from datetime import date, datetime
from decimal import Decimal

from app.infrastructure.serialization import dumps


def as_money(value: object) -> Decimal:
    amount = value if isinstance(value, Decimal) else Decimal(str(value))
    return amount.quantize(Decimal("0.01"))


def as_date(value: object) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def as_json(value: object) -> str:
    return dumps(value)
