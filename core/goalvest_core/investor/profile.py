"""InvestorProfile – פרטים אישיים ופרופיל סיכון. המזהה הוא user_id. ראו docs/07 §7.1."""

from datetime import date
from uuid import UUID

from goalvest_core.aggregate import AggregateRoot
from goalvest_core.errors import BusinessRuleViolation
from goalvest_core.event import Event
from goalvest_core.investor.scoring import evaluate, profile_payload


class InvestorProfile(AggregateRoot):
    aggregate_type = "InvestorProfile"

    def __init__(self, aggregate_id: UUID | None = None) -> None:
        super().__init__(aggregate_id)
        self.birth_year: int | None = None
        self.marital_status = ""
        self.monthly_income_range = ""
        self.has_emergency_fund = False
        self.existing_products: list[str] = []
        self.risk_score: int | None = None
        self.risk_label = ""
        self.answers: dict = {}

    def create_profile(self, *, today: date, metadata: dict | None = None, **fields: object) -> None:
        if self.version != 0:
            raise BusinessRuleViolation("הפרופיל כבר קיים", code="PROFILE_EXISTS")
        self._record("InvestorProfileCreated", profile_payload(today=today, **fields), metadata)

    def record_assessment(self, raw: dict, *, today: date, metadata: dict | None = None) -> None:
        result = evaluate(raw, today)
        if self.version == 0:
            self._record("InvestorProfileCreated", result.profile_payload(), metadata)
        self._record("RiskProfileAssessed", result.assessed_payload(), metadata)

    def _when(self, event: Event) -> None:
        if event.event_type == "InvestorProfileCreated":
            payload = event.payload
            self.birth_year = payload["birth_year"]
            self.marital_status = payload["marital_status"]
            self.monthly_income_range = payload["monthly_income_range"]
            self.has_emergency_fund = bool(payload["has_emergency_fund"])
            self.existing_products = list(payload["existing_products"])
            return
        if event.event_type == "RiskProfileAssessed":
            payload = event.payload
            self.risk_score = int(payload["score"])
            self.risk_label = payload["label"]
            self.answers = dict(payload["answers"])
            answers = self.answers
            self.birth_year = answers["birth_year"]
            self.marital_status = answers["marital_status"]
            self.monthly_income_range = answers["monthly_income_range"]
            self.has_emergency_fund = answers["emergency_fund"] != "NONE"
            self.existing_products = list(answers["existing_products"])
            return
        raise NotImplementedError(f"InvestorProfile אינו מטפל ב-{event.event_type}")
