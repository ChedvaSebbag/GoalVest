"""חישוב ציון סיכון 1–5. הציון נקבע כאן, לא בדפדפן. ראו FR-10."""

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import NoReturn

from goalvest_core.errors import BusinessRuleViolation

LABELS = {
    1: "סולידי",
    2: "סולידי-מאוזן",
    3: "מאוזן",
    4: "מאוזן-צמיחה",
    5: "צמיחה",
}

HORIZON_POINTS = {
    "UNDER_3": 1,
    "Y3_TO_5": 2,
    "Y6_TO_10": 3,
    "Y11_TO_20": 4,
    "OVER_20": 5,
}
DROP_POINTS = {
    "SELL_ALL": 1,
    "SELL_SOME": 2,
    "WAIT": 3,
    "HOLD": 4,
    "BUY_MORE": 5,
}
EXPERIENCE_POINTS = {
    "NONE": 1,
    "DEPOSITS": 2,
    "FUNDS": 3,
    "OCCASIONAL_STOCKS": 4,
    "ACTIVE": 5,
}
STABILITY_POINTS = {
    "UNSTABLE": 1,
    "VARIABLE": 2,
    "MOSTLY_STABLE": 3,
    "SALARIED": 4,
    "SURPLUS": 5,
}
EMERGENCY = {
    "NONE": (1, False),
    "PARTIAL": (3, True),
    "YES": (5, True),
}
MARITAL = frozenset({"SINGLE", "MARRIED", "DIVORCED", "WIDOWED"})
INCOME_RANGES = frozenset({
    "UP_TO_10K",
    "FROM_10K_TO_20K",
    "FROM_20K_TO_35K",
    "FROM_35K_TO_50K",
    "OVER_50K",
})
PRODUCTS = frozenset({"HISHTALMUT", "GEMEL", "POLICY", "PENSION", "NONE"})


@dataclass(frozen=True)
class Assessment:
    score: int
    label: str
    birth_year: int
    marital_status: str
    monthly_income_range: str
    has_emergency_fund: bool
    existing_products: tuple[str, ...]
    answers: dict

    def profile_payload(self) -> dict:
        return {
            "birth_year": self.birth_year,
            "marital_status": self.marital_status,
            "monthly_income_range": self.monthly_income_range,
            "has_emergency_fund": self.has_emergency_fund,
            "existing_products": list(self.existing_products),
        }

    def assessed_payload(self) -> dict:
        return {"answers": self.answers, "score": self.score, "label": self.label}


def profile_payload(
    *,
    birth_year: object,
    marital_status: object,
    monthly_income_range: object,
    has_emergency_fund: object,
    existing_products: object,
    today: date,
) -> dict:
    if not isinstance(has_emergency_fund, bool):
        _invalid("hasEmergencyFund", "יש לציין אם קיימת קרן חירום")
    return {
        "birth_year": _birth_year(birth_year, today),
        "marital_status": _one_of(marital_status, MARITAL, "maritalStatus", "יש לבחור מצב משפחתי"),
        "monthly_income_range": _one_of(
            monthly_income_range,
            INCOME_RANGES,
            "monthlyIncomeRange",
            "יש לבחור טווח הכנסה",
        ),
        "has_emergency_fund": has_emergency_fund,
        "existing_products": list(_products(existing_products)),
    }


def evaluate(raw: dict, today: date) -> Assessment:
    birth_year = _birth_year(raw.get("birth_year"), today)
    horizon = _choice(raw.get("horizon"), HORIZON_POINTS, "horizon", "יש לבחור טווח השקעה")
    drop = _choice(raw.get("drop_reaction"), DROP_POINTS, "dropReaction", "יש לבחור תגובה לירידה")
    experience = _choice(raw.get("experience"), EXPERIENCE_POINTS, "experience", "יש לבחור ניסיון")
    stability = _choice(
        raw.get("income_stability"),
        STABILITY_POINTS,
        "incomeStability",
        "יש לבחור יציבות הכנסה",
    )
    emergency_points, has_fund = _emergency(raw.get("emergency_fund"))
    marital = _one_of(raw.get("marital_status"), MARITAL, "maritalStatus", "יש לבחור מצב משפחתי")
    income = _one_of(
        raw.get("monthly_income_range"),
        INCOME_RANGES,
        "monthlyIncomeRange",
        "יש לבחור טווח הכנסה",
    )
    products = _products(raw.get("existing_products"))
    points = (
        _age_points(today.year - birth_year),
        horizon,
        drop,
        experience,
        stability,
        emergency_points,
    )
    average = (Decimal(sum(points)) / Decimal(len(points))).quantize(Decimal(1), rounding=ROUND_HALF_UP)
    score = int(average)
    answers = {
        "birth_year": birth_year,
        "horizon": raw["horizon"],
        "drop_reaction": raw["drop_reaction"],
        "experience": raw["experience"],
        "income_stability": raw["income_stability"],
        "emergency_fund": raw["emergency_fund"],
        "marital_status": marital,
        "monthly_income_range": income,
        "existing_products": list(products),
    }
    return Assessment(
        score=score,
        label=LABELS[score],
        birth_year=birth_year,
        marital_status=marital,
        monthly_income_range=income,
        has_emergency_fund=has_fund,
        existing_products=products,
        answers=answers,
    )


def _age_points(age: int) -> int:
    if age <= 30:
        return 5
    if age <= 40:
        return 4
    if age <= 50:
        return 3
    if age <= 60:
        return 2
    return 1


def _birth_year(value: object, today: date) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        _invalid("birthYear", "יש להזין שנת לידה")
    year = int(value)
    if year < today.year - 100 or year > today.year - 18:
        _invalid("birthYear", "שנת הלידה אינה בטווח 18 עד 100")
    return year


def _choice(value: object, options: dict[str, int], field: str, message: str) -> int:
    if not isinstance(value, str) or value not in options:
        _invalid(field, message)
    return options[str(value)]


def _one_of(value: object, options: frozenset[str], field: str, message: str) -> str:
    if not isinstance(value, str) or value not in options:
        _invalid(field, message)
    return str(value)


def _emergency(value: object) -> tuple[int, bool]:
    if not isinstance(value, str) or value not in EMERGENCY:
        _invalid("emergencyFund", "יש לבחור אם קיימת קרן חירום")
    return EMERGENCY[value]


def _products(value: object) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        _invalid("existingProducts", "יש לבחור מוצרים קיימים, או שאין")
    if any(not isinstance(item, str) or item not in PRODUCTS for item in value):
        _invalid("existingProducts", "מוצר לא מוכר")
    if len(set(value)) != len(value):
        _invalid("existingProducts", "אותו מוצר נבחר פעמיים")
    if "NONE" in value and len(value) > 1:
        _invalid("existingProducts", "אי אפשר לבחור 'אין' יחד עם מוצר")
    return tuple(value)


def _invalid(field: str, message: str) -> NoReturn:
    raise BusinessRuleViolation(message, code="INVALID_ANSWERS", fields={field: message})
