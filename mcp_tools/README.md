# goalvest-tools (MCP Server)

שרת FastMCP בתעבורת stdio, לפי `docs/11` §11.2. שני Tools:

- `calculate_investment_tax` — מס צפוי לפי `tax_rules.yaml` (הערכה מפושטת).
- `get_stock_volatility` — תנודתיות שנתית, max drawdown ושינוי יומי דרך yfinance, עם cache של 15 דקות.

## הרצה ב-MCP Inspector

משורש ה-Repo, אחרי `source backend/.venv/bin/activate`:

```bash
npx @modelcontextprotocol/inspector python -m mcp_tools.server
```
