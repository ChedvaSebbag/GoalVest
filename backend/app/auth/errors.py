"""שגיאות שכבת האימות. מיפוי ל-HTTP נשאר ב-Controller."""


class Unauthorized(Exception):
    def __init__(self, message: str = "אימייל או סיסמה שגויים") -> None:
        super().__init__(message)


class UnknownInstitution(Exception):
    """institutionId של סוכן אינו מופיע בקטלוג."""
