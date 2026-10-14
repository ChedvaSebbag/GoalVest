# 09 – סוכן הערכת כדאיות השקעה (Investment Fit Agent)

## 9.1 תפקיד

ה-Process העצמאי קורא בקשות השקעה ממסד הנתונים, מעביר כל בקשה סדרת בדיקות, ומפיק הערכה מובנית: עד כמה כל אפיק מתאים למשקיע וליעד, איזה תמהיל מומלץ ואילו מוצרים. הסוכן לא מחליט במקום הסוכן האנושי. ההערכה היא כלי עזר שהסוכן מאשר או דוחה (FR-44).

## 9.2 טכנולוגיה

| רכיב | בחירה |
|---|---|
| מסגרת | `deepagents` (LangChain Deep Agents, מעל LangGraph) |
| LLM | Ollama ב-Docker, מודל עם תמיכה ב-Tool Calling ובעברית, למשל `qwen2.5:7b-instruct`. חלופה גדולה יותר אם החומרה מאפשרת: `qwen2.5:14b` |
| הטמעות | `bge-m3` דרך Ollama (רב-לשוני, מתאים לעברית) |
| Vector DB | ChromaDB (ראו 10-rag.md) |
| MCP | `langchain-mcp-adapters`: Tavily MCP + `goalvest-tools` |
| גישה ל-DB | `goalvest_core` (אותו Domain כמו ה-API) |

> הערה לחומרה: Ollama בתוך Docker על Mac לא משתמש ב-GPU של Apple, ולכן איטי יותר. על MacBook Air מומלץ מודל 7B ובדיקת זמנים מוקדמת. ראו 16-open-questions.md.

## 9.3 לולאת ה-Process

```python
# agent/main.py (שלד)
while True:
    for req in queries.pending_requests(limit=3):          # SUBMITTED / REEVALUATION_REQUESTED
        try:
            commands.start_assessment(req.id, expected_version=req.version)   # AssessmentStarted
        except ConcurrencyError:
            continue                                         # מישהו אחר כבר לקח
        result = run_assessment(req)                         # Deep Agent
        if result.ok:
            commands.complete_assessment(req.id, result.payload)   # AIAssessmentCompleted
        elif result.infrastructure:
            commands.abort_assessment(req.id, result.reason)       # AssessmentAborted
        else:
            commands.fail_assessment(req.id, result.error)         # AIAssessmentFailed
    sleep(20)
```

- רץ כ-`python -m agent` בקונטיינר או בטרמינל נפרד.
- Heartbeat ללוג כל דקה. Graceful shutdown על SIGTERM.
- בקשה שתקועה ב-`AI_PROCESSING` יותר מ-10 דקות נרשמת כ-`AIAssessmentFailed` וחוזרת לתור. הניסיון נספר.
- Ollama, Chroma או Tavily לא זמינים: נרשם `AssessmentAborted` (`attempt_not_counted: true`), הסטטוס חוזר ל-`SUBMITTED`, והסבב הבא מנסה שוב. אין עדכון ישיר של `rm_requests`.
- `AGENT_MODE=deep` (ברירת מחדל) מריץ את ה-Deep Agent, ואחרי שני כשלי פורמט עובר לשרשרת. `AGENT_MODE=chain` מדלג על ה-Deep Agent ומריץ רק את השרשרת.
- בדיקה והדגמה: `python -m agent --once --request <id> --verbose` מדפיס חוקים, מקורות RAG, מוצרים, תוצאות Tools, Tavily, זמן ריצה ותוצאה.

## 9.4 סדרת הבדיקות

| שלב | סוג | מה נבדק | כלי |
|---|---|---|---|
| 1 | דטרמיניסטי (קוד Python) | חוקי התאמה בסיסיים (ראו 9.5) והפקת דגלי סיכון | `suitability_rules.py` |
| 2 | RAG | תנאי נזילות ומיסוי לכל אפיק, תנאי פוליסות של מוצרים מועמדים, כללי מס רלוונטיים | Tool `search_knowledge_base` |
| 3 | נתוני מוצרים | שליפת 10–15 מוצרים מועמדים מתוך `rm_products` לפי סיכון ואפיק | Tool `find_candidate_products` |
| 4 | Tools מותאמים | תחזית צמיחה לכל אפיק, השפעת מס, השפעת דמי ניהול, תנודתיות למניות/מדדים | MCP `goalvest-tools` |
| 5 | חיפוש Web | תנאי שוק נוכחיים (ריבית בנק ישראל, מגמות מדדים), חדשות על הגופים המנהלים או המסלולים המועמדים | Tavily MCP |
| 6 | סינתזה | ציונים, תמהיל, מוצרים, נימוק ומקורות לפי סכמה | LLM + Pydantic |
| 7 | ולידציה | סכמת JSON, סכום תמהיל 100, מוצרים קיימים ופעילים, הבהרה משפטית, אין סתירה לחוקים משלב 1 | Python |

## 9.5 חוקי התאמה דטרמיניסטיים (שלב 1)

| קוד | תנאי | תוצאה |
|---|---|---|
| `LOCKUP_EXCEEDS_HORIZON` | טווח היעד קצר מתקופת הנעילה של קרן השתלמות (6 שנים) ואין למשקיע קרן ותיקה | תקרת ציון 40 לאפיק השתלמות, דגל חמור |
| `NO_EMERGENCY_FUND` | אין קרן חירום ויעד שאינו "קרן חירום" | המלצה להפריד 3–6 חודשי הוצאות בנזיל, דגל בינוני |
| `RISK_HORIZON_MISMATCH` | פרופיל "צמיחה" עם טווח קצר מ-3 שנים | תקרת אחוז מניות בתמהיל 40%, דגל |
| `LOW_RISK_LONG_HORIZON` | פרופיל סולידי עם טווח מעל 15 שנה | דגל מידע: סיכון אינפלציה |
| `LIQUIDITY_NEED` | המשקיע ציין צורך בנזילות לפני היעד | העדפה לשוק ההון ולגמל/פוליסה נזילים |
| `EXCLUDED_CHANNEL` | אפיק שהמשקיע סימן כלא רצוי | ציון 0 ואחוז 0 |
| `RETIREMENT_AGE_BENEFIT` | יעד פרישה וגיל פרישה ≥ 60 במועד היעד | בונוס לגמל להשקעה (קצבה פטורה ממס) |

החוקים בקובץ `agent/rules.yaml` כך שאפשר לשנות ספים בלי קוד. המודל מקבל את התוצאות כקלט ואסור לו לסתור אותן (נבדק בשלב 7).

## 9.6 מבנה ה-Deep Agent

```python
agent = create_deep_agent(
    model=ChatOllama(model="qwen2.5:7b-instruct", temperature=0.1),
    tools=[get_request_details, find_candidate_products, search_knowledge_base,
           *mcp_tools],            # tavily_search, calculate_investment_tax,
                                   # get_stock_volatility, project_goal_growth, compare_fees
    system_prompt=SYSTEM_PROMPT,
    subagents=[
        {"name": "market-researcher",
         "description": "חוקר תנאי שוק וחדשות על גופים ומסלולים באינטרנט",
         "system_prompt": MARKET_PROMPT, "tools": ["tavily_search", "get_stock_volatility"]},
        {"name": "policy-analyst",
         "description": "מנתח תנאי פוליסות ומיסוי מתוך מאגר המסמכים",
         "system_prompt": POLICY_PROMPT,
         "tools": ["search_knowledge_base", "calculate_investment_tax"]},
    ],
)
```

- הסוכן הראשי מתכנן (`write_todos`), מאציל ל-2 תת-סוכנים, ואז מסנתז.
- מספר צעדים מקסימלי: 25. Timeout לבקשה: 4 דקות.
- הפלט הסופי מנותח ל-`AssessmentOutput` (Pydantic). כשל → ניסיון תיקון אחד עם הודעת השגיאה.
- גיבוי (החלטה ממומשת): אחרי שני כשלי פורמט של ה-Deep Agent, או כש-`AGENT_MODE=chain`, שלבים 2–5 רצים כשרשרת קבועה. ה-LLM משמש לסינתזה בלבד. אם גם הסינתזה לא בפורמט תקין, נשמרת הערכה דטרמיניסטית שנבנתה מהראיות שנאספו (חוקים, מועמדים ומקורות אמיתיים), כל עוד יש מוצר, מקור RAG ומקור Web. בלי הראיות האלה נרשם `AIAssessmentFailed`.
- בשרשרת, מס ותנודתיות נקראים ממימוש `mcp_tools` בתוך התהליך, ו-Tavily נקרא ב-API של החיפוש. ה-Deep Agent מגיע לאותם כלים דרך MCP (`goalvest-tools` ב-stdio ו-`npx -y tavily-mcp`).

## 9.7 System Prompt (תמצית)

```
אתה אנליסט התאמת השקעות במערכת GoalVest. תפקידך להעריך עד כמה כל אפיק
(שוק ההון, קרן השתלמות, קופת גמל להשקעה/פוליסת חיסכון) מתאים ליעד ולפרופיל של המשקיע.
- הסתמך רק על: נתוני הבקשה, תוצאות חוקי ההתאמה, מסמכים מהמאגר, תוצאות כלים ותוצאות חיפוש.
- כל טענה עובדתית על מס, נזילות או דמי ניהול חייבת מקור (rag או web).
- אל תסתור את חוקי ההתאמה שקיבלת.
- המלץ רק על מוצרים מתוך רשימת המועמדים.
- כתוב בעברית פשוטה, בלי ז'רגון. אל תשתמש בלשון ציווי ("קנה"), אלא "מתאים יותר", "כדאי לשקול".
- סיים תמיד בהבהרה: "ההערכה נוצרה אוטומטית ואינה מהווה ייעוץ השקעות."
- החזר JSON בלבד לפי הסכמה.
```

## 9.8 סכמת פלט

```python
class ChannelScores(BaseModel):
    capital_market: conint(ge=0, le=100)
    hishtalmut: conint(ge=0, le=100)
    gemel_policy: conint(ge=0, le=100)

class RecommendedProduct(BaseModel):
    product_id: UUID
    fit_score: conint(ge=0, le=100)
    reason: constr(max_length=300)

class Source(BaseModel):
    type: Literal["rag", "web", "tool"]
    title: str
    document_id: UUID | None = None
    url: HttpUrl | None = None
    excerpt: constr(max_length=400) | None = None

class AssessmentOutput(BaseModel):
    overall_score: conint(ge=0, le=100)
    channel_scores: ChannelScores
    allocation: dict[Literal["capital_market", "hishtalmut", "gemel_policy"], conint(ge=0, le=100)]
    recommended_products: conlist(RecommendedProduct, min_length=1, max_length=5)
    rationale: constr(min_length=200, max_length=3000)
    risk_flags: list[RiskFlag]
    sources: conlist(Source, min_length=2)
    disclaimer: str
    # ולידציה נוספת: sum(allocation) == 100, לפחות מקור rag אחד ומקור web אחד
```

## 9.9 איך נקבע הציון הכללי

`overall_score` = ממוצע משוקלל של ציוני האפיקים לפי התמהיל המומלץ, פחות קנס על דגלי סיכון חמורים (‏10 נקודות לכל דגל חמור). החישוב נעשה בקוד ולא על ידי המודל, כדי שיהיה עקבי ושקוף. המודל מחזיר ציוני אפיקים ותמהיל בלבד.

## 9.10 פרטיות מול שירותים חיצוניים

- לשאילתות Tavily נשלחים רק מונחים כלליים (שם מסלול, שם גוף, "ריבית בנק ישראל"), לעולם לא שם, אימייל, טלפון או סכום אישי.
- הנתונים האישיים נשארים בין ה-DB, Ollama המקומי ו-ChromaDB המקומי.

## 9.11 הערכת איכות הסוכן

| מדד | איך נמדד |
|---|---|
| תקינות פלט | % ריצות שעוברות ולידציה בניסיון ראשון. יעד ≥ 85% |
| עמידה בחוקים | 0 הפרות של חוקי שלב 1 ב-20 תרחישי בדיקה (13-testing-plan.md) |
| עיגון במקורות | כל הערכה עם ≥ 1 מקור RAG ו-≥ 1 מקור Web |
| שיעור אישור סוכנים | `AssessmentApproved / (Approved + Rejected)` מוצג ב-KPI. מדד איכות אמיתי לאורך זמן |
| זמן ריצה | p95 ≤ 3 דקות |

## 9.12 ה-Worker (Process נוסף, לא ה-AI)

| משימה | הפעלה | מה עושה |
|---|---|---|
| Indexer | אירועי `ProductDocumentUploaded` | חילוץ טקסט, פיצול, הטמעה ב-ChromaDB, `ProductDocumentIndexed` |
| Notifier | אירועים: `AIAssessmentCompleted`, `OfferSent`, `OfferAccepted`, `PriceAlertTriggered`, `PasswordResetRequested` | יצירת התראה במערכת ושליחת מייל דרך Gmail MCP, ואז `NotificationSent` |
| Price Alerts | כל 30 דקות בשעות מסחר (ת"א וארה"ב) | בדיקת שינוי יומי של כל אחזקה מול סף המשתמש. מייל אחד לכל מנייה ליום |
