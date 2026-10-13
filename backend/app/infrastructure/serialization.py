"""קידוד JSON ל-payload, ל-metadata ולתוצאת פקודה.

Decimal נשמר כמחרוזת, UUID כמחרוזת, datetime כ-ISO-8601, והטעינה משחזרת את הטיפוס.
"""

import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

_MARKER = "$gv"


class DomainEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:
        if isinstance(o, Decimal):
            return {_MARKER: "decimal", "v": str(o)}
        if isinstance(o, UUID):
            return {_MARKER: "uuid", "v": str(o)}
        if isinstance(o, datetime):
            return {_MARKER: "datetime", "v": o.isoformat()}
        raise TypeError(f"לא ניתן לקודד {type(o).__name__} ל-JSON")


def dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, cls=DomainEncoder)


def loads(value: str) -> Any:
    return json.loads(value, object_hook=_restore)


def _restore(obj: dict) -> Any:
    marker = obj.get(_MARKER)
    raw = obj.get("v")
    if marker == "decimal" and isinstance(raw, str) and len(obj) == 2:
        return Decimal(raw)
    if marker == "uuid" and isinstance(raw, str) and len(obj) == 2:
        return UUID(raw)
    if marker == "datetime" and isinstance(raw, str) and len(obj) == 2:
        parsed = datetime.fromisoformat(raw)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed
    return obj


def to_naive_utc(value: datetime) -> datetime:
    """DateTime(timezone=False) שומר את הרגע בלי offset. הערך עצמו הוא UTC."""
    aware = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    return aware.astimezone(UTC).replace(tzinfo=None)


def to_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
