"""שגיאות דומיין. ראו docs/07 §7.2."""

from uuid import UUID


class BusinessRuleViolation(Exception):
    """הפרת חוק עסקי בתוך Aggregate. במקרה כזה לא נרשם אירוע."""


class ConcurrencyError(Exception):
    """שני כותבים ניסו לתפוס את אותה גרסה (UQ_Aggregate_Version)."""

    def __init__(self, aggregate_id: UUID, expected_version: int) -> None:
        self.aggregate_id = aggregate_id
        self.expected_version = expected_version
        super().__init__(
            f"התנגשות גרסאות באגרגט {aggregate_id}: expected_version={expected_version}"
        )
