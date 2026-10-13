"""UserAccount – הרשמה, תפקיד וסיסמה. ראו docs/07 §7.1 ו-§7.3."""

from collections.abc import Callable
from uuid import UUID

from goalvest_core.aggregate import AggregateRoot
from goalvest_core.errors import BusinessRuleViolation
from goalvest_core.event import Event

ROLES = ("INVESTOR", "AGENT")


def normalize_email(email: str) -> str:
    """אותו אימייל בלי קשר לרווחים או לאותיות גדולות."""
    return email.strip().lower()


def password_is_valid(password: str) -> bool:
    """8 תווים לפחות, אות אחת ומספר אחד. ראו docs/12 §12.1."""
    return len(password) >= 8 and any(ch.isalpha() for ch in password) and any(ch.isdigit() for ch in password)


class UserAccount(AggregateRoot):
    aggregate_type = "UserAccount"

    def __init__(self, aggregate_id: UUID | None = None) -> None:
        super().__init__(aggregate_id)
        self.email = ""
        self.full_name = ""
        self.phone = ""
        self.role = ""
        self.password_hash = ""
        self.institution_id: str | None = None
        self.license_no: str | None = None

    def register(
        self,
        *,
        email: str,
        full_name: str,
        phone: str,
        password: str,
        role: str,
        hash_password: Callable[[str], str],
        institution_id: UUID | None = None,
        license_no: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        if self.version != 0:
            raise BusinessRuleViolation("המשתמש כבר רשום", code="ALREADY_REGISTERED")
        normalized = normalize_email(email)
        if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
            raise BusinessRuleViolation("כתובת האימייל אינה תקינה", code="INVALID_EMAIL")
        if not password_is_valid(password):
            raise BusinessRuleViolation(
                "הסיסמה חייבת להכיל לפחות 8 תווים, אות ומספר",
                code="WEAK_PASSWORD",
            )
        if role not in ROLES:
            raise BusinessRuleViolation("סוג המשתמש אינו נתמך", code="INVALID_ROLE")
        license = (license_no or "").strip() or None
        institution = str(institution_id) if institution_id is not None else None
        if role == "AGENT":
            if institution is None or license is None:
                raise BusinessRuleViolation(
                    "לסוכן חובה גוף פיננסי ומספר רישיון",
                    code="AGENT_FIELDS_REQUIRED",
                )
        elif institution is not None or license is not None:
            raise BusinessRuleViolation("משקיע אינו משויך לגוף פיננסי", code="INVESTOR_HAS_INSTITUTION")
        self._record(
            "UserRegistered",
            {
                "email": normalized,
                "full_name": full_name.strip(),
                "phone": phone.strip(),
                "role": role,
                "password_hash": hash_password(password),
                "institution_id": institution,
                "license_no": license,
            },
            metadata,
        )

    def _when(self, event: Event) -> None:
        if event.event_type != "UserRegistered":
            raise NotImplementedError(f"UserAccount אינו מטפל ב-{event.event_type}")
        payload = event.payload
        self.email = payload["email"]
        self.full_name = payload["full_name"]
        self.phone = payload["phone"]
        self.role = payload["role"]
        self.password_hash = payload["password_hash"]
        self.institution_id = payload.get("institution_id")
        self.license_no = payload.get("license_no")
