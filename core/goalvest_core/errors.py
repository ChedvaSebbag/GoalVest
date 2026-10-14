"""שגיאות דומיין. ראו docs/07 §7.2."""

from uuid import UUID


class BusinessRuleViolation(Exception):
    """הפרת חוק עסקי בתוך Aggregate. במקרה כזה לא נרשם אירוע."""

    def __init__(
        self,
        message: str = "",
        *,
        code: str = "BUSINESS_RULE",
        fields: dict[str, str] | None = None,
    ) -> None:
        self.code = code
        self.fields = dict(fields or {})
        super().__init__(message)


class EmailAlreadyExists(BusinessRuleViolation):
    """אימייל שכבר שמור ב-rm_users, כולל התנגשות מקבילית על האינדקס הייחודי."""

    def __init__(self) -> None:
        super().__init__("כתובת האימייל כבר רשומה", code="EMAIL_EXISTS")


class Forbidden(Exception):
    """המשתמש מחובר, אבל הפעולה אינה על המשאב של הגוף שלו."""

    def __init__(self, message: str = "אין הרשאה לפעולה הזו") -> None:
        self.code = "FORBIDDEN"
        super().__init__(message)


class NotFound(Exception):
    """משאב חסר, או שייך למשתמש אחר. התשובה לא חושפת אם הוא קיים."""

    def __init__(self, message: str = "הפריט לא נמצא") -> None:
        self.code = "NOT_FOUND"
        super().__init__(message)


class ConcurrencyError(Exception):
    """שני כותבים ניסו לתפוס את אותה גרסה (UQ_Aggregate_Version)."""

    def __init__(self, aggregate_id: UUID, expected_version: int) -> None:
        self.aggregate_id = aggregate_id
        self.expected_version = expected_version
        super().__init__(
            f"התנגשות גרסאות באגרגט {aggregate_id}: expected_version={expected_version}"
        )
