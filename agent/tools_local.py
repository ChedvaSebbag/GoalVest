"""מס, דמי ניהול, תחזית ותנודתיות לשרשרת. הכסף ב-Decimal עד גבול ה-tool הקיים."""

from datetime import date
from decimal import Decimal

_MONEY = Decimal("0.01")


def run_market_tools(snapshot: dict, products: list[dict], *, today: date | None = None, volatility=None) -> dict:
    goal = snapshot.get("goal") or {}
    answers = (snapshot.get("risk") or {}).get("answers") or {}
    deposits = _money(goal.get("initial_amount"))
    target = _date(goal.get("target_date"), today or date.today())
    years = max(Decimal((target - (today or date.today())).days) / Decimal("365.25"), Decimal(1))
    birth = answers.get("birth_year")
    age = target.year - int(birth) if isinstance(birth, int) and not isinstance(birth, bool) else 67
    withdrawal = "annuity" if goal.get("type") == "RETIREMENT" and age >= 60 else "lump_sum"
    return {
        "tax": _tax(deposits, years, age, withdrawal),
        "volatility": _volatility(products, volatility),
        "fees": _fees(products, deposits, years),
        "growth": _growth(deposits, _money(goal.get("monthly_deposit")), years),
    }


def _tax(deposits: Decimal, years: Decimal, age: int, withdrawal: str) -> list[dict]:
    from mcp_tools.tax import calculate_investment_tax

    final = deposits * (Decimal(1) + Decimal("0.04")) ** years
    items = []
    for channel, tool_channel in (
        ("capital_market", "capital_market"),
        ("hishtalmut", "hishtalmut"),
        ("gemel_policy", "gemel_lehashkaa"),
    ):
        try:
            result = calculate_investment_tax(
                tool_channel,
                float(deposits),
                float(final),
                float(years),
                age,
                withdrawal,
            )
            items.append({"channel": channel, "result": result})
        except (TypeError, ValueError) as exc:
            items.append({"channel": channel, "error": str(exc)})
    return items


def _volatility(products: list[dict], volatility) -> list[dict]:
    loader = volatility
    if loader is None:
        from mcp_tools.volatility import get_stock_volatility

        loader = get_stock_volatility
    found = []
    for product in products:
        symbol = product.get("symbol")
        if not symbol:
            continue
        try:
            found.append(loader(symbol))
        except Exception as exc:  # noqa: BLE001 – כשל yfinance נשאר בתוצאת הכלי
            found.append({"symbol": symbol, "error": str(exc)})
        if len(found) == 2:
            break
    return found


def _fees(products: list[dict], deposits: Decimal, years: Decimal) -> list[dict]:
    rows = []
    for product in products[:4]:
        rate = Decimal(str(product.get("fee_assets") or "0")) / Decimal(100)
        paid = (deposits * rate * years).quantize(_MONEY)
        rows.append({"product_id": product["product_id"], "fee_assets": str(paid)})
    return rows


def _growth(initial: Decimal, monthly: Decimal, years: Decimal) -> list[dict]:
    rows = []
    for name, rate in (("שמרני", Decimal("0.02")), ("צפוי", Decimal("0.05")), ("אופטימי", Decimal("0.08"))):
        factor = (Decimal(1) + rate) ** years
        value = (initial * factor) + (monthly * Decimal(12) * years)
        rows.append({"scenario": name, "value": str(value.quantize(_MONEY))})
    return rows


def _money(value: object) -> Decimal:
    if value is None:
        return Decimal(0)
    return Decimal(str(value))


def _date(value: object, today: date) -> date:
    if isinstance(value, date):
        return value
    if not value:
        return today
    return date.fromisoformat(str(value)[:10])
