"""חישוב מס צפוי לפי tax_rules.yaml. אין שיעורים קשיחים בקוד. ראו docs/11 §11.2."""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from functools import lru_cache
from pathlib import Path

import yaml

_RULES_PATH = Path(__file__).with_name("tax_rules.yaml")
_MONEY = Decimal("0.01")
_CHANNELS = frozenset({"capital_market", "hishtalmut", "gemel_lehashkaa", "savings_policy"})
_WITHDRAWALS = frozenset({"lump_sum", "annuity"})


@lru_cache(maxsize=1)
def load_tax_rules(path: str | None = None) -> dict:
    target = Path(path) if path else _RULES_PATH
    with target.open(encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle)
    if not isinstance(loaded, dict):
        raise TypeError("קובץ כללי המס אינו תקין")
    return loaded


def calculate_investment_tax(
    channel: str,
    total_deposits: float,
    final_value: float,
    years_held: float,
    age_at_withdrawal: int,
    withdrawal_type: str,
    inflation_rate: float | None = None,
) -> dict:
    """מחשב מס צפוי ותשואה נטו לפי אפיק ומועד משיכה. השיעורים נקראים מ-tax_rules.yaml."""
    rules = load_tax_rules()
    if channel not in _CHANNELS:
        raise ValueError("אפיק לא מוכר")
    if withdrawal_type not in _WITHDRAWALS:
        raise ValueError("סוג משיכה לא מוכר")
    if isinstance(age_at_withdrawal, bool) or not isinstance(age_at_withdrawal, int) or age_at_withdrawal < 0:
        raise ValueError("גיל המשיכה אינו תקין")
    deposits = _money(total_deposits)
    final = _money(final_value)
    years = _plain(years_held)
    if years < 0 or deposits < 0 or final < 0:
        raise ValueError("סכום או תקופה אינם תקינים")
    inflation = _plain(rules["inflation_default"]) if inflation_rate is None else _plain(inflation_rate)
    if inflation < 0:
        raise ValueError("שיעור האינפלציה אינו תקין")

    nominal_gain = final - deposits
    real_gain = final - (deposits * ((Decimal(1) + inflation) ** years))
    taxable = real_gain if real_gain > 0 else Decimal(0)
    rate = Decimal(0)
    reason: str | None = None
    notes = [str(item) for item in rules["notes"]]

    if channel == "capital_market":
        rate = _plain(rules["capital_market"]["real_gain_tax_rate"])
    elif channel == "hishtalmut":
        rate, taxable, reason, extra = _hishtalmut(rules["hishtalmut"], years, age_at_withdrawal, taxable)
        notes.extend(extra)
    elif channel == "gemel_lehashkaa":
        rate, taxable, reason, extra = _gemel(rules["gemel_lehashkaa"], age_at_withdrawal, withdrawal_type, taxable)
        notes.extend(extra)
    else:
        rate = _plain(rules["savings_policy"]["real_gain_tax_rate"])

    tax_amount = _money(taxable * rate)
    result = {
        "nominal_gain": _number(nominal_gain),
        "real_gain": _number(real_gain),
        "tax_rate_applied": float(rate),
        "tax_amount": _number(tax_amount),
        "net_value": _number(final - tax_amount),
        "notes": notes,
    }
    if reason:
        result["exemption_reason"] = reason
    return result


def _hishtalmut(rules: dict, years: Decimal, age: int, taxable: Decimal) -> tuple[Decimal, Decimal, str | None, list[str]]:
    lockup = _plain(rules["lockup_years"])
    reduced = rules["reduced_lockup"]
    if age >= int(reduced["from_age"]):
        lockup = _plain(reduced["years"])
    if years < lockup:
        return (
            _plain(rules["early_withdrawal_tax_rate"]),
            taxable,
            None,
            ["משיכה לפני תום תקופת הנעילה מחויבת על הרווח הריאלי לפי השיעור בקובץ."],
        )
    ceiling = rules["exemption_ceiling"]
    if ceiling is None or taxable <= _plain(ceiling):
        return Decimal(0), Decimal(0), "פטור אחרי תקופת הנעילה", []
    return (
        _plain(rules["post_lockup_tax_rate"]),
        taxable - _plain(ceiling),
        None,
        ["חלק מהרווח שמעל התקרה חייב במס לפי השיעור בקובץ."],
    )


def _gemel(rules: dict, age: int, withdrawal_type: str, taxable: Decimal) -> tuple[Decimal, Decimal, str | None, list[str]]:
    if withdrawal_type == "annuity" and age >= int(rules["annuity_age"]):
        return Decimal(0), Decimal(0), "קצבה מגיל הזכאות פטורה לפי הכללים המפושטים", []
    extra = []
    if withdrawal_type == "annuity":
        extra.append("קצבה לפני גיל הזכאות מחושבת כאן לפי שיעור המשיכה ההונית.")
    return _plain(rules["lump_sum_tax_rate"]), taxable, None, extra


def _plain(value: object) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float, str, Decimal)):
        raise TypeError("ערך מספרי לא תקין")
    try:
        return Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("ערך מספרי לא תקין") from exc


def _money(value: object) -> Decimal:
    return _plain(value).quantize(_MONEY, rounding=ROUND_HALF_UP)


def _number(value: Decimal) -> float:
    return float(value.quantize(_MONEY, rounding=ROUND_HALF_UP))
