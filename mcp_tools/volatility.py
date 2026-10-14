"""תנודתיות שנתית, Max Drawdown ושינוי יומי. Cache של 15 דקות. ראו docs/11 §11.2."""

import time
from decimal import ROUND_HALF_UP, Decimal
from statistics import stdev

_PERIODS = frozenset({"6mo", "1y", "3y", "5y"})
_TTL_SECONDS = 15 * 60
_CACHE: dict[tuple[str, str], tuple[float, dict]] = {}
_PERCENT = Decimal("0.01")
_TRADING_DAYS = Decimal(252)


def clear_volatility_cache() -> None:
    _CACHE.clear()


def get_stock_volatility(
    symbol: str,
    period: str = "1y",
    *,
    fetch=None,
    now=None,
) -> dict:
    """תנודתיות שנתית, Max Drawdown ושינוי יומי למנייה או מדד."""
    ticker = symbol.strip().upper()
    if not ticker:
        raise ValueError("חסר סימול")
    if period not in _PERIODS:
        raise ValueError("חלון הזמן אינו נתמך")
    clock = now or time.time
    current = float(clock())
    key = (ticker, period)
    cached = _CACHE.get(key)
    if cached is not None and current - cached[0] < _TTL_SECONDS:
        return cached[1]
    loader = fetch or fetch_yahoo
    closes, currency = loader(ticker, period)
    result = volatility_from_closes(ticker, closes, currency=currency, period=period)
    _CACHE[key] = (current, result)
    return result


def volatility_from_closes(
    symbol: str,
    closes: list[tuple[str, Decimal]],
    *,
    currency: str,
    period: str,
) -> dict:
    if len(closes) < 3:
        raise ValueError("אין מספיק ימי מסחר לחישוב תנודתיות")
    prices = [price for _, price in closes]
    returns = [(prices[index] / prices[index - 1]) - 1 for index in range(1, len(prices))]
    if any(prices[index - 1] <= 0 for index in range(1, len(prices))):
        raise ValueError("מחיר לא תקין בסדרה")
    annualized = _stdev(returns) * _TRADING_DAYS.sqrt()
    return {
        "symbol": symbol,
        "last_price": _number(prices[-1]),
        "currency": currency,
        "daily_change_pct": _number(_change(prices[-2], prices[-1])),
        "annualized_volatility": _number(annualized * 100),
        "max_drawdown": _number(_max_drawdown(prices) * 100),
        "period": period,
        "as_of": closes[-1][0],
    }


def fetch_yahoo(symbol: str, period: str) -> tuple[list[tuple[str, Decimal]], str]:
    import yfinance as yf

    frame = yf.Ticker(symbol).history(period=period, auto_adjust=True)
    if frame is None or frame.empty or "Close" not in frame:
        raise ValueError("אין נתוני מחיר לסימול")
    closes: list[tuple[str, Decimal]] = []
    for stamp, close in zip(frame.index, frame["Close"], strict=False):
        price = Decimal(str(close))
        if not price.is_finite():
            continue
        closes.append((stamp.date().isoformat(), price))
    currency = "ILS" if symbol.endswith(".TA") else "USD"
    return closes, currency


def _max_drawdown(prices: list[Decimal]) -> Decimal:
    peak = prices[0]
    worst = Decimal(0)
    for price in prices:
        peak = max(peak, price)
        if peak > 0:
            drop = (price - peak) / peak
            worst = min(worst, drop)
    return worst


def _change(previous: Decimal, current: Decimal) -> Decimal:
    return (current - previous) / previous * 100


def _stdev(values: list[Decimal]) -> Decimal:
    return Decimal(str(stdev(float(value) for value in values)))


def _number(value: Decimal) -> float:
    return float(value.quantize(_PERCENT, rounding=ROUND_HALF_UP))
