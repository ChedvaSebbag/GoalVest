"""חוקי התאמה דטרמיניסטיים. ספים מ-rules.yaml, נעילה וגיל קצבה מ-tax_rules.yaml."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

import yaml

_RULES_PATH = Path(__file__).with_name("rules.yaml")
_EXCLUDED = {
    "CAPITAL_MARKET": "capital_market",
    "HISHTALMUT": "hishtalmut",
    "GEMEL_POLICY": "gemel_policy",
}
_NAMES = {
    "capital_market": "שוק ההון",
    "hishtalmut": "קרן השתלמות",
    "gemel_policy": "גמל ופוליסה",
}


@dataclass(frozen=True)
class Suitability:
    flags: tuple[dict, ...]
    score_caps: dict[str, int]
    allocation_caps: dict[str, int]
    prefer: tuple[str, ...]
    bonus_channel: str | None
    risk_score: int
    penalty: int


def load_rules(path: Path | None = None) -> dict:
    target = path or _RULES_PATH
    with target.open(encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle)
    if not isinstance(loaded, dict):
        raise TypeError("קובץ החוקים אינו תקין")
    return loaded


def evaluate(snapshot: dict, *, today: date, rules: dict, tax_rules: dict) -> Suitability:
    goal = snapshot["goal"]
    risk = snapshot["risk"]
    answers = risk.get("answers") or {}
    target = _date(goal["target_date"])
    horizon_days = (target - today).days
    score_caps: dict[str, int] = {}
    allocation_caps: dict[str, int] = {}
    flags: list[dict] = []
    prefer: list[str] = []
    bonus_channel = None

    excluded = [_EXCLUDED[item] for item in goal.get("excluded_channels") or [] if item in _EXCLUDED]
    for channel in excluded:
        score_caps[channel] = 0
        allocation_caps[channel] = 0
        flags.append(_flag(
            "EXCLUDED_CHANNEL",
            "medium",
            f"{_NAMES[channel]}: {rules['excluded_text']}",
        ))

    products = answers.get("existing_products") or []
    lockup_years = _whole(tax_rules["hishtalmut"]["lockup_years"])
    if horizon_days < lockup_years * 365 and "HISHTALMUT" not in products and "hishtalmut" not in excluded:
        score_caps["hishtalmut"] = min(score_caps.get("hishtalmut", 100), int(rules["hishtalmut_score_cap"]))
        flags.append(_flag("LOCKUP_EXCEEDS_HORIZON", "high", rules["lockup_text"]))

    if answers.get("emergency_fund") == "NONE" and goal.get("type") != "EMERGENCY":
        flags.append(_flag("NO_EMERGENCY_FUND", "medium", rules["emergency_text"]))

    label = str(risk.get("label") or "")
    if label in set(rules["growth_labels"]) and horizon_days < int(rules["growth_horizon_years"]) * 365:
        allocation_caps["capital_market"] = min(
            allocation_caps.get("capital_market", 100),
            int(rules["equity_allocation_cap"]),
        )
        flags.append(_flag("RISK_HORIZON_MISMATCH", "medium", rules["growth_text"]))

    if label in set(rules["conservative_labels"]) and horizon_days > int(rules["long_horizon_years"]) * 365:
        flags.append(_flag("LOW_RISK_LONG_HORIZON", "info", rules["inflation_text"]))

    if goal.get("liquidity_need") in {"PARTIAL", "HIGH"}:
        prefer.extend(["capital_market", "gemel_policy"])
        flags.append(_flag("LIQUIDITY_NEED", "info", rules["liquidity_text"]))

    annuity_age = _whole(tax_rules["gemel_lehashkaa"]["annuity_age"])
    birth_year = answers.get("birth_year")
    retirement = goal.get("type") == "RETIREMENT" and isinstance(birth_year, int) and not isinstance(birth_year, bool)
    if retirement and target.year - birth_year >= annuity_age and "gemel_policy" not in excluded:
        bonus_channel = "gemel_policy"
        flags.append(_flag("RETIREMENT_AGE_BENEFIT", "info", rules["retirement_text"]))

    return Suitability(
        flags=tuple(flags),
        score_caps=score_caps,
        allocation_caps=allocation_caps,
        prefer=tuple(dict.fromkeys(prefer)),
        bonus_channel=bonus_channel,
        risk_score=int(risk.get("score") or 3),
        penalty=int(rules["severe_penalty"]),
    )


def _flag(code: str, severity: str, text: str) -> dict:
    return {"code": code, "severity": severity, "text": text}


def _date(value: object) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _whole(value: object) -> int:
    return int(Decimal(str(value)))
