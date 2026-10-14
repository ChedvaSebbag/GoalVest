"""GoalVest domain core – Aggregates, Events ושגיאות דומיין (משותף ל-API, Agent ו-Worker)."""

from goalvest_core.aggregate import AggregateRoot
from goalvest_core.errors import BusinessRuleViolation, ConcurrencyError, EmailAlreadyExists, NotFound
from goalvest_core.event import Event

__all__ = [
    "AggregateRoot",
    "BusinessRuleViolation",
    "ConcurrencyError",
    "EmailAlreadyExists",
    "Event",
    "NotFound",
]
