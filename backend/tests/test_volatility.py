"""תנודתיות על סדרת מחירים דמה, בלי yfinance."""

from decimal import Decimal

import pytest

from mcp_tools.volatility import clear_volatility_cache, get_stock_volatility, volatility_from_closes


def setup_function():
    clear_volatility_cache()


def test_volatility_drawdown_and_daily_change_from_dummy_prices():
    closes = [
        ("2026-01-01", Decimal(100)),
        ("2026-01-02", Decimal(110)),
        ("2026-01-03", Decimal(99)),
    ]
    result = volatility_from_closes("SPY", closes, currency="USD", period="1y")
    assert result["symbol"] == "SPY"
    assert result["last_price"] == 99
    assert result["currency"] == "USD"
    assert result["daily_change_pct"] == -10
    assert result["max_drawdown"] == -10
    assert result["annualized_volatility"] == pytest.approx(224.5, abs=0.02)
    assert result["period"] == "1y"
    assert result["as_of"] == "2026-01-03"


def test_cache_skips_fetch_for_fifteen_minutes():
    calls = []

    def fetch(symbol, period):
        calls.append((symbol, period))
        return (
            [
                ("2026-01-01", Decimal(10)),
                ("2026-01-02", Decimal(11)),
                ("2026-01-03", Decimal(12)),
            ],
            "USD",
        )

    clock = {"now": 1_000.0}
    first = get_stock_volatility("spy", "6mo", fetch=fetch, now=lambda: clock["now"])
    second = get_stock_volatility("SPY", "6mo", fetch=fetch, now=lambda: clock["now"] + (15 * 60) - 1)
    clock["now"] += 15 * 60
    third = get_stock_volatility("SPY", "6mo", fetch=fetch, now=lambda: clock["now"])
    assert first == second == third
    assert calls == [("SPY", "6mo"), ("SPY", "6mo")]
