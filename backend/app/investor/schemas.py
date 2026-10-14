"""סכמות קלט של פרופיל, שאלון ויעד. החוקים העסקיים נשארים ב-Aggregate."""

from datetime import date
from decimal import Decimal, InvalidOperation
from uuid import UUID

from goalvest_core.goals import CHANNELS, FLEXIBILITY, GOAL_TYPES, LIQUIDITY
from goalvest_core.goals.dates import is_far_enough
from pydantic import BaseModel, ConfigDict, Field, field_validator


def _money(value: object) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float, str, Decimal)):
        raise ValueError("הסכום אינו תקין")  # noqa: TRY004 — ולידציית קלט, לא TypeError של פייתון
    try:
        amount = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("הסכום אינו תקין") from exc
    return amount.quantize(Decimal("0.01"))


class ProfileBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    birth_year: int = Field(alias="birthYear")
    marital_status: str = Field(alias="maritalStatus")
    monthly_income_range: str = Field(alias="monthlyIncomeRange")
    has_emergency_fund: bool = Field(alias="hasEmergencyFund")
    existing_products: list[str] = Field(alias="existingProducts")


class RiskAnswerBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    birth_year: int = Field(alias="birthYear")
    horizon: str
    drop_reaction: str = Field(alias="dropReaction")
    experience: str
    income_stability: str = Field(alias="incomeStability")
    emergency_fund: str = Field(alias="emergencyFund")
    marital_status: str = Field(alias="maritalStatus")
    monthly_income_range: str = Field(alias="monthlyIncomeRange")
    existing_products: list[str] = Field(alias="existingProducts")

    def as_dict(self) -> dict:
        return {
            "birth_year": self.birth_year,
            "horizon": self.horizon,
            "drop_reaction": self.drop_reaction,
            "experience": self.experience,
            "income_stability": self.income_stability,
            "emergency_fund": self.emergency_fund,
            "marital_status": self.marital_status,
            "monthly_income_range": self.monthly_income_range,
            "existing_products": list(self.existing_products),
        }


class RiskBody(BaseModel):
    answers: RiskAnswerBody


class GoalBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    goal_type: str = Field(alias="type")
    title: str
    initial_amount: Decimal = Field(alias="initialAmount")
    monthly_deposit: Decimal = Field(alias="monthlyDeposit")
    target_amount: Decimal = Field(alias="targetAmount")
    target_date: date = Field(alias="targetDate")
    flexibility: str
    liquidity_need: str = Field(alias="liquidityNeed")
    excluded_channels: list[str] = Field(alias="excludedChannels")
    preferred_channels: list[str] = Field(alias="preferredChannels")
    preferred_institutions: list[UUID] = Field(alias="preferredInstitutions")

    @field_validator("initial_amount", "monthly_deposit", "target_amount", mode="before")
    @classmethod
    def money(cls, value: object) -> Decimal:
        return _money(value)

    @field_validator("title")
    @classmethod
    def title_present(cls, value: str) -> str:
        if len(value.strip()) < 2:
            raise ValueError("יש להזין שם ליעד")
        return value.strip()

    @field_validator("goal_type")
    @classmethod
    def known_type(cls, value: str) -> str:
        if value not in GOAL_TYPES:
            raise ValueError("יש לבחור סוג יעד")
        return value

    @field_validator("flexibility")
    @classmethod
    def known_flexibility(cls, value: str) -> str:
        if value not in FLEXIBILITY:
            raise ValueError("יש לבחור גמישות")
        return value

    @field_validator("liquidity_need")
    @classmethod
    def known_liquidity(cls, value: str) -> str:
        if value not in LIQUIDITY:
            raise ValueError("יש לבחור צורך בנזילות")
        return value

    @field_validator("excluded_channels", "preferred_channels")
    @classmethod
    def known_channels(cls, value: list[str]) -> list[str]:
        if any(item not in CHANNELS for item in value):
            raise ValueError("אפיק לא מוכר")
        return value

    @field_validator("target_amount")
    @classmethod
    def target_positive(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("חייב להיות גדול מ-0")
        return value

    @field_validator("initial_amount", "monthly_deposit")
    @classmethod
    def not_negative(cls, value: Decimal) -> Decimal:
        if value < 0:
            raise ValueError("הסכום אינו יכול להיות שלילי")
        return value

    @field_validator("target_date")
    @classmethod
    def far_enough(cls, value: date) -> date:
        if not is_far_enough(value, date.today()):
            raise ValueError("מועד היעד חייב להיות לפחות בעוד 6 חודשים")
        return value


class GoalUpdateBody(GoalBody):
    consent_share_contact: bool = Field(default=False, alias="consentShareContact")


class SubmitBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    goal_id: UUID = Field(alias="goalId")
    consent_share_contact: bool = Field(alias="consentShareContact")


class CancelBody(BaseModel):
    reason: str = ""

    @field_validator("reason")
    @classmethod
    def short_reason(cls, value: str) -> str:
        if len(value.strip()) > 500:
            raise ValueError("עד 500 תווים")
        return value.strip()
