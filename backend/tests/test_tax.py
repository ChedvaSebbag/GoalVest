"""חישוב מס על נתוני דמה. השיעורים נקראים מהקובץ, בלי רשת."""

from decimal import Decimal

from mcp_tools.tax import calculate_investment_tax, load_tax_rules


def test_capital_market_taxes_real_gain_and_explains_the_simplification():
    result = calculate_investment_tax("capital_market", 1000, 1300, 2, 40, "lump_sum", inflation_rate=0)
    assert result["nominal_gain"] == 300
    assert result["real_gain"] == 300
    assert result["tax_rate_applied"] == 0.25
    assert result["tax_amount"] == 75
    assert result["net_value"] == 1225
    assert any("יסף" in note for note in result["notes"])
    assert "exemption_reason" not in result


def test_omitted_inflation_uses_the_yaml_default():
    default = float(Decimal(load_tax_rules()["inflation_default"]))
    omitted = calculate_investment_tax("capital_market", 1000, 2000, 1, 40, "lump_sum")
    explicit = calculate_investment_tax("capital_market", 1000, 2000, 1, 40, "lump_sum", inflation_rate=default)
    zero = calculate_investment_tax("capital_market", 1000, 2000, 1, 40, "lump_sum", inflation_rate=0)
    assert omitted == explicit
    assert omitted["tax_amount"] < zero["tax_amount"]


def test_hishtalmut_is_exempt_after_lockup_and_taxed_before_it():
    lockup = int(Decimal(load_tax_rules()["hishtalmut"]["lockup_years"]))
    exempt = calculate_investment_tax("hishtalmut", 1000, 1500, lockup, 40, "lump_sum", inflation_rate=0)
    early = calculate_investment_tax("hishtalmut", 1000, 1500, 1, 40, "lump_sum", inflation_rate=0)
    assert exempt["tax_amount"] == 0
    assert exempt["exemption_reason"]
    assert early["tax_amount"] == 125
    assert "exemption_reason" not in early


def test_hishtalmut_uses_the_shorter_lockup_from_the_configured_age():
    reduced = load_tax_rules()["hishtalmut"]["reduced_lockup"]
    years = int(Decimal(reduced["years"]))
    result = calculate_investment_tax("hishtalmut", 100, 180, years, int(reduced["from_age"]), "lump_sum", 0)
    assert result["tax_amount"] == 0


def test_gemel_annuity_from_configured_age_is_exempt_and_lump_sum_is_taxed():
    age = int(load_tax_rules()["gemel_lehashkaa"]["annuity_age"])
    exempt = calculate_investment_tax("gemel_lehashkaa", 1000, 1500, 10, age, "annuity", inflation_rate=0)
    taxed = calculate_investment_tax("gemel_lehashkaa", 1000, 1500, 10, age + 5, "lump_sum", inflation_rate=0)
    assert exempt["tax_amount"] == 0
    assert "קצבה" in exempt["exemption_reason"]
    assert taxed["tax_amount"] == 125
    assert "exemption_reason" not in taxed


def test_savings_policy_taxes_the_real_gain():
    result = calculate_investment_tax("savings_policy", 1000, 1500, 1, 50, "lump_sum", inflation_rate=0)
    assert result["tax_amount"] == 125
    assert result["net_value"] == 1375


def test_inflation_can_wipe_the_taxable_real_gain():
    result = calculate_investment_tax("capital_market", 1000, 1100, 1, 40, "lump_sum", inflation_rate=0.1)
    assert result["nominal_gain"] == 100
    assert result["real_gain"] == 0
    assert result["tax_amount"] == 0
