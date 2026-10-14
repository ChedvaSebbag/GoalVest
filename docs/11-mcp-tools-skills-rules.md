# 11 – MCP, Tools, Skills ו-Rules

## 11.1 שירותים חיצוניים דרך MCP (דרישה 9)

| שירות | שימוש | צרכן | הגדרה |
|---|---|---|---|
| **Tavily MCP** (`tavily-mcp`) | חיפוש Web: תנאי שוק, ריבית, חדשות על גופים ומסלולים | Investment Fit Agent (תת-סוכן market-researcher) | `TAVILY_API_KEY` ב-`.env`. רמת חינם מספיקה לפרויקט |
| **Gmail MCP** | שליחת מיילים: "ההערכה מוכנה", "התקבלה הצעה", התראת מחיר, שחזור סיסמה | Worker (Notifier) | חשבון Gmail ייעודי לפרויקט, OAuth. שרת Gmail MCP קהילתי (לבחירה ובדיקה, ראו 16) |

```json
// mcp.config.json (משמש את הסוכן וה-Worker דרך langchain-mcp-adapters)
{
  "tavily":   { "transport": "stdio", "command": "npx", "args": ["-y", "tavily-mcp"], "env": { "TAVILY_API_KEY": "${TAVILY_API_KEY}" } },
  "gmail":    { "transport": "stdio", "command": "npx", "args": ["-y", "<gmail-mcp-package>"] },
  "goalvest": { "transport": "stdio", "command": "python", "args": ["-m", "mcp_tools.server"] }
}
```

## 11.2 Tools מותאמים – שרת `goalvest-tools` (דרישה 10)

שרת MCP שפותח בצוות ב-Python עם FastMCP, תעבורת stdio. נדרשים שניים, מתוכננים ארבעה (שניים Must, שניים Should).

### Tool 1 (Must): `calculate_investment_tax`

מחשב מס צפוי ותשואה נטו לפי אפיק ומועד משיכה.

| קלט | סוג | תיאור |
|---|---|---|
| channel | `capital_market` / `hishtalmut` / `gemel_lehashkaa` / `savings_policy` | אפיק |
| total_deposits | number | סך הפקדות |
| final_value | number | שווי צפוי במשיכה |
| years_held | number | שנים |
| age_at_withdrawal | int | גיל במשיכה |
| withdrawal_type | `lump_sum` / `annuity` | משיכה הונית או קצבה |
| inflation_rate | number (ברירת מחדל 2.5%) | לחישוב רווח ריאלי |

**פלט**: `{ nominal_gain, real_gain, tax_rate_applied, tax_amount, net_value, exemption_reason?, notes[] }`

**לוגיקה (מפושטת, הפרמטרים ב-`tax_rules.yaml`):**
- שוק ההון: מס רווחי הון על הרווח הריאלי.
- קרן השתלמות: פטור אחרי תקופת הנעילה (עד תקרה). משיכה מוקדמת – חיוב לפי הכללים בקובץ.
- גמל להשקעה: משיכה הונית לפני גיל 60 – מס על הרווח הריאלי. קצבה מגיל 60 – פטור.
- פוליסת חיסכון: מס על הרווח הריאלי במשיכה.
- התוצאה כוללת תמיד `notes` שמבהירות שמדובר בהערכה מפושטת (בלי מס יסף, קיזוז הפסדים או מקרים מיוחדים).

> את שיעורי המס והתקרות יש לאמת מול רשות המסים / משרד האוצר ולעדכן ב-`tax_rules.yaml` לפני ההגשה.

### Tool 2 (Must): `get_stock_volatility`

| קלט | סוג | תיאור |
|---|---|---|
| symbol | string | למשל `SPY`, `TEVA.TA`, `^TA35.TA` |
| period | `6mo` / `1y` / `3y` / `5y` | חלון |

**פלט**: `{ symbol, last_price, currency, daily_change_pct, annualized_volatility, max_drawdown, beta_vs_benchmark?, period, as_of }`
**מימוש**: yfinance → תשואות יומיות → סטיית תקן × √252, Max Drawdown מהמחירים. Cache של 15 דקות.

### Tool 3 (Should): `project_goal_growth`

| קלט | תיאור |
|---|---|
| initial_amount, monthly_deposit, years | נתוני היעד |
| scenarios | ברירת מחדל: שמרני 2%, צפוי 5%, אופטימי 8% שנתי (לפי פרופיל הסיכון) |
| annual_fee_assets, deposit_fee | דמי ניהול |
| target_amount | יעד להשוואה |

**פלט**: סדרה שנתית לכל תרחיש, שווי סופי, `probability_hint` (מגיע / קרוב / רחוק). משמש גם את אשף היעד (FR-13) וגם את הסוכן.

### Tool 4 (Should): `compare_fees`

מקבל 2–4 מזהי מוצרים, סכום וטווח, ומחזיר כמה ₪ ישולמו בדמי ניהול לאורך התקופה בכל מוצר. ממחיש למשקיע את ההבדל בין 0.5% ל-1.0%.

### שלד

```python
# mcp_tools/server.py
from mcp.server.fastmcp import FastMCP
mcp = FastMCP("goalvest-tools")

@mcp.tool()
def get_stock_volatility(symbol: str, period: str = "1y") -> dict:
    """תנודתיות שנתית, Max Drawdown ושינוי יומי למנייה או מדד."""
    ...

if __name__ == "__main__":
    mcp.run()          # stdio
```

**מימוש**: `mcp_tools/server.py` (FastMCP, stdio). שיעורי המס ב-`mcp_tools/tax_rules.yaml` בלבד. `get_stock_volatility` קורא ל-yfinance ושומר cache של 15 דקות. חיבור ל-MCP Inspector משורש ה-Repo, אחרי הפעלת סביבת ה-backend:

```bash
npx @modelcontextprotocol/inspector python -m mcp_tools.server
```

## 11.3 Skill מ-Skills.sh (דרישה 2)

| Skill | שימוש | התקנה |
|---|---|---|
| `analogjs/angular-skills` | הנחיות לסוכן הקוד לכתיבת Angular מודרני: Standalone, Signals, Control Flow, בדיקות | `npx skills add analogjs/angular-skills` (לאמת את שם ה-Skill המדויק בעמוד ב-skills.sh) |
| חלופה / תוספת | Skill לעיצוב Frontend מקצועי מ-skills.sh | לפי בחירה |

מתועד ב-README של ה-Repo: למה נבחר, איך הותקן, ודוגמה לפיצ'ר שנבנה בעזרתו.

## 11.4 Skill שפיתחנו (דרישה 3)

**`add-cqrs-feature`** – מנחה את סוכן הקוד להוסיף פיצ'ר מקצה לקצה בדיוק לפי הארכיטקטורה שלנו. נמצא ב-`.claude/skills/add-cqrs-feature/SKILL.md`. הצעדים:

1. קריאת דרישת ה-FR הרלוונטית ב-`docs/03`.
2. הגדרת אירוע/ים חדשים ב-`core/goalvest_core/events/` + עדכון קטלוג האירועים ב-`docs/07`.
3. פקודה + Handler + מתודה ב-Aggregate עם חוקי ולידציה.
4. Projector ועדכון Read Model (+ מיגרציה).
5. Query Service ו-DTO.
6. Controller (Blueprint) ועדכון `docs/08`.
7. Angular: `*-commands.service.ts`, `*-queries.service.ts`, רכיב, Route.
8. בדיקות: יחידה ל-Aggregate (Given events → When command → Then events), אינטגרציה ל-API, ובדיקת Projection.
9. עדכון `docs/13` עם מקרה הבדיקה.

Skill נוסף אפשרי (Could): `financial-sentiment` – הנחיות לתת-סוכן market-researcher לסיווג סנטימנט של כתבות (חיובי/ניטרלי/שלילי) עם ציטוט.

## 11.5 Rules (דרישה 3)

| Rule | קובץ | עיקר |
|---|---|---|
| R1 – ארכיטקטורה | `.claude/rules/architecture.md` | אין כתיבה ל-DB מחוץ ל-`EventStoreRepository`, אין UPDATE/DELETE על EventStore, Controllers בלי לוגיקה עסקית, Queries רק מ-`rm_*`, כל שינוי מצב = אירוע |
| R2 – ממשק עברי | `.claude/rules/ui-hebrew.md` | RTL, טקסטים בעברית, פורמט כסף/תאריך, מצבי טעינה/ריק/שגיאה, נגישות |
| R3 – ציות פיננסי | `.claude/rules/financial-compliance.md` | הבהרה משפטית, לשון זהירה, אין PII לשירותים חיצוניים, כל עובדה על מס עם מקור, אין שיעורי מס קשיחים בקוד |

התוכן המלא של הקבצים נמצא בתיקיית `.claude/` של ה-Repo.
