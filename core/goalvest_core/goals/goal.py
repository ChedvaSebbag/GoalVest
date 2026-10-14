"""Goal – יעד השקעה והחוקים של FR-12. בקשה פעילה אחת נבדקת מול המזהה המוקרן."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from goalvest_core.aggregate import AggregateRoot
from goalvest_core.errors import BusinessRuleViolation
from goalvest_core.event import Event
from goalvest_core.goals.dates import is_far_enough

GOAL_TYPES = frozenset({"APARTMENT", "RETIREMENT", "CAR", "EDUCATION", "EMERGENCY", "GENERAL"})
FLEXIBILITY = frozenset({"FIXED", "MONTHS_6", "YEAR_1", "FLEXIBLE"})
LIQUIDITY = frozenset({"NONE", "PARTIAL", "HIGH"})
CHANNELS = frozenset({"CAPITAL_MARKET", "HISHTALMUT", "GEMEL_POLICY"})
MONEY = Decimal("0.01")


class Goal(AggregateRoot):
    aggregate_type = "Goal"

    def __init__(self, aggregate_id: UUID | None = None) -> None:
        super().__init__(aggregate_id)
        self.investor_id: UUID | None = None
        self.goal_type = ""
        self.title = ""
        self.initial_amount = Decimal(0)
        self.monthly_deposit = Decimal(0)
        self.target_amount = Decimal(0)
        self.target_date = date.min
        self.flexibility = ""
        self.liquidity_need = ""
        self.excluded_channels: list[str] = []
        self.preferred_channels: list[str] = []
        self.preferred_institutions: list[str] = []
        self.status = ""

    def create(self, *, investor_id: UUID, today: date, known_institutions: set[str], metadata: dict | None = None, **fields: object) -> None:
        if self.version != 0:
            raise BusinessRuleViolation("היעד כבר קיים", code="GOAL_EXISTS")
        payload = _goal_fields(fields, today, known_institutions)
        payload["investor_id"] = str(investor_id)
        self._record("GoalCreated", payload, metadata)

    def update(self, *, today: date, known_institutions: set[str], metadata: dict | None = None, **fields: object) -> None:
        self._ensure_active()
        incoming = _goal_fields(fields, today, known_institutions)
        changed = {key: value for key, value in incoming.items() if value != _current(self)[key]}
        if changed:
            self._record("GoalUpdated", changed, metadata)

    def archive(self, reason: str = "", metadata: dict | None = None) -> None:
        self._ensure_active()
        self._record("GoalArchived", {"reason": reason.strip()}, metadata)

    def ensure_no_active_request(self, active_request_id: UUID | None) -> None:
        if active_request_id is not None:
            raise BusinessRuleViolation("ליעד הזה כבר יש בקשה פעילה", code="ACTIVE_REQUEST_EXISTS")

    def _ensure_active(self) -> None:
        if self.status != "ACTIVE":
            raise BusinessRuleViolation("היעד בארכיון", code="GOAL_ARCHIVED")

    def _when(self, event: Event) -> None:
        payload = event.payload
        if event.event_type == "GoalCreated":
            self.investor_id = UUID(payload["investor_id"])
            self.status = "ACTIVE"
            _apply_fields(self, payload)
            return
        if event.event_type == "GoalUpdated":
            _apply_fields(self, payload)
            return
        if event.event_type == "GoalArchived":
            self.status = "ARCHIVED"
            return
        raise NotImplementedError(f"Goal אינו מטפל ב-{event.event_type}")


def _current(goal: Goal) -> dict:
    return {
        "type": goal.goal_type,
        "title": goal.title,
        "initial_amount": goal.initial_amount,
        "monthly_deposit": goal.monthly_deposit,
        "target_amount": goal.target_amount,
        "target_date": goal.target_date.isoformat(),
        "flexibility": goal.flexibility,
        "liquidity_need": goal.liquidity_need,
        "excluded_channels": list(goal.excluded_channels),
        "preferred_channels": list(goal.preferred_channels),
        "preferred_institutions": list(goal.preferred_institutions),
    }


def _apply_fields(goal: Goal, payload: dict) -> None:
    if "type" in payload:
        goal.goal_type = payload["type"]
    if "title" in payload:
        goal.title = payload["title"]
    if "initial_amount" in payload:
        goal.initial_amount = _money(payload["initial_amount"])
    if "monthly_deposit" in payload:
        goal.monthly_deposit = _money(payload["monthly_deposit"])
    if "target_amount" in payload:
        goal.target_amount = _money(payload["target_amount"])
    if "target_date" in payload:
        raw = payload["target_date"]
        goal.target_date = raw if isinstance(raw, date) else date.fromisoformat(raw)
    if "flexibility" in payload:
        goal.flexibility = payload["flexibility"]
    if "liquidity_need" in payload:
        goal.liquidity_need = payload["liquidity_need"]
    if "excluded_channels" in payload:
        goal.excluded_channels = list(payload["excluded_channels"])
    if "preferred_channels" in payload:
        goal.preferred_channels = list(payload["preferred_channels"])
    if "preferred_institutions" in payload:
        goal.preferred_institutions = list(payload["preferred_institutions"])


def _goal_fields(fields: dict, today: date, known_institutions: set[str]) -> dict:
    goal_type = _one(fields.get("goal_type"), GOAL_TYPES, "type", "יש לבחור סוג יעד", "INVALID_TYPE")
    title = fields.get("title")
    if not isinstance(title, str) or len(title.strip()) < 2:
        _invalid("יש להזין שם ליעד", "title", "INVALID_TITLE")
    initial = _non_negative(fields.get("initial_amount"), "initialAmount", "INVALID_INITIAL_AMOUNT")
    monthly = _non_negative(fields.get("monthly_deposit"), "monthlyDeposit", "INVALID_MONTHLY_DEPOSIT")
    if initial == 0 and monthly == 0:
        message = "יש להזין סכום התחלתי או הפקדה חודשית"
        raise BusinessRuleViolation(
            message,
            code="INVALID_AMOUNTS",
            fields={"initialAmount": message, "monthlyDeposit": message},
        )
    target = _positive(fields.get("target_amount"), "targetAmount", "INVALID_TARGET_AMOUNT")
    target_date = fields.get("target_date")
    if not isinstance(target_date, date) or not is_far_enough(target_date, today):
        _invalid("מועד היעד חייב להיות לפחות בעוד 6 חודשים", "targetDate", "INVALID_TARGET_DATE")
    flexibility = _one(fields.get("flexibility"), FLEXIBILITY, "flexibility", "יש לבחור גמישות", "INVALID_FLEXIBILITY")
    liquidity = _one(
        fields.get("liquidity_need"),
        LIQUIDITY,
        "liquidityNeed",
        "יש לבחור צורך בנזילות",
        "INVALID_LIQUIDITY",
    )
    excluded = _channels(fields.get("excluded_channels"), "excludedChannels")
    preferred = _channels(fields.get("preferred_channels"), "preferredChannels")
    if set(excluded) & set(preferred):
        _invalid("אי אפשר לסמן אפיק כמועדף וגם כלא רצוי", "preferredChannels", "INVALID_CHANNELS")
    institutions = _institutions(fields.get("preferred_institutions"), known_institutions)
    return {
        "type": goal_type,
        "title": title.strip(),
        "initial_amount": initial,
        "monthly_deposit": monthly,
        "target_amount": target,
        "target_date": target_date.isoformat(),
        "flexibility": flexibility,
        "liquidity_need": liquidity,
        "excluded_channels": excluded,
        "preferred_channels": preferred,
        "preferred_institutions": institutions,
    }


def _money(value: object) -> Decimal:
    amount = value if isinstance(value, Decimal) else Decimal(str(value))
    return amount.quantize(MONEY)


def _non_negative(value: object, field: str, code: str) -> Decimal:
    try:
        amount = _money(value)
    except Exception as exc:
        _invalid("הסכום אינו תקין", field, code)
        raise AssertionError from exc
    if amount < 0:
        _invalid("הסכום אינו יכול להיות שלילי", field, code)
    return amount


def _positive(value: object, field: str, code: str) -> Decimal:
    amount = _non_negative(value, field, code)
    if amount <= 0:
        _invalid("חייב להיות גדול מ-0", field, code)
    return amount


def _one(value: object, options: frozenset[str], field: str, message: str, code: str) -> str:
    if not isinstance(value, str) or value not in options:
        _invalid(message, field, code)
    return str(value)


def _channels(value: object, field: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or item not in CHANNELS for item in value):
        _invalid("אפיק לא מוכר", field, "INVALID_CHANNELS")
    if len(set(value)) != len(value):
        _invalid("אותו אפיק נבחר פעמיים", field, "INVALID_CHANNELS")
    return list(value)


def _institutions(value: object, known: set[str]) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        _invalid("יש לבחור גוף מהרשימה", "preferredInstitutions", "INVALID_INSTITUTION")
    if len(set(value)) != len(value) or any(item not in known for item in value):
        _invalid("יש לבחור גוף מהרשימה", "preferredInstitutions", "INVALID_INSTITUTION")
    return list(value)


def _invalid(message: str, field: str, code: str) -> None:
    raise BusinessRuleViolation(message, code=code, fields={field: message})
