"""שרת MCP goalvest-tools בתעבורת stdio. ראו docs/11 §11.2."""

from mcp.server.fastmcp import FastMCP

from mcp_tools.tax import calculate_investment_tax as compute_tax
from mcp_tools.volatility import get_stock_volatility as compute_volatility

mcp = FastMCP("goalvest-tools")


@mcp.tool()
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
    return compute_tax(
        channel,
        total_deposits,
        final_value,
        years_held,
        age_at_withdrawal,
        withdrawal_type,
        inflation_rate,
    )


@mcp.tool()
def get_stock_volatility(symbol: str, period: str = "1y") -> dict:
    """תנודתיות שנתית, Max Drawdown ושינוי יומי למנייה או מדד."""
    return compute_volatility(symbol, period)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
