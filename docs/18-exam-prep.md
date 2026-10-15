# 18 – הכנה להצגה: שאלות ותשובות

המרצה דורש שכל אחת מאיתנו תכיר את כל הקוד. כאן מרוכזות השאלות הסבירות, עם התשובה והקובץ שאפשר לפתוח כדי להראות אותה.

## Event Sourcing

**מה זה Event Sourcing, ולמה בחרנו בו?**
במקום לשמור רק את המצב הנוכחי, שומרים כל שינוי כאירוע שאי אפשר לשנות (למשל `InvestmentRequestSubmitted` או `OfferAccepted`). המצב הוא תוצאה של הרצת האירועים לפי הסדר. יתרונות: היסטוריה מלאה (Audit), ציר זמן במסך בלי קוד נוסף, ואפשרות לבנות מחדש טבלאות קריאה.
קבצים: `db/migrations/001_event_store.sql`, `backend/app/infrastructure/event_store.py`.

**איך נראית טבלת ה-EventStore?**
לכל שורה יש `global_position` (מספר רץ, מפתח ראשי), `event_id`, `aggregate_type`, `aggregate_id`, `version`, `event_type`, `payload` (JSON שנבדק עם `ISJSON`), `metadata` ו-`occurred_at`. יש אילוץ `UQ_Aggregate_Version` על הצירוף (aggregate_id, version).

**מה זה Optimistic Concurrency, ואיך מימשתן?**
ה-Handler טוען Aggregate בגרסה N ושומר אירועים בגרסה N+1. אם מישהו אחר כתב בינתיים, נוצרת התנגשות על `UQ_Aggregate_Version` ומקבלים שגיאת 409. כך שני סוכנים לא יכולים לקחת את אותו ליד.

**מה זה Aggregate? תני דוגמה.**
אובייקט דומיין ששומר על החוקים העסקיים. למשל `InvestmentRequest` ב-`core/goalvest_core/requests/investment_request.py`: הוא בודק שאי אפשר לבטל בקשה בעיבוד, ושאפשר לשלוח הצעה רק אחרי לקיחת ליד. מתודה עסקית לא משנה שדות ישירות. היא רושמת אירוע, ו-`_when(event)` מחיל אותו.

**מה זה Rehydration?**
טעינת Aggregate על ידי הרצת כל האירועים שלו מההתחלה (`from_events`). אין Snapshots, כי לכל Aggregate יש מעט אירועים.

**מה זה Projection?**
פונקציה שמקבלת אירוע ומעדכנת טבלת קריאה (`rm_*`). אצלנו היא רצה סינכרונית באותה טרנזקציה עם כתיבת האירוע (ADR-1), ולכן המשתמש רואה את השינוי מיד. אפשר לבנות את כל הטבלאות מחדש מהאירועים, למשל עם `scripts/rebuild_leads.py`.

**מה זה `ProcessedCommands`?**
Idempotency: כל פקודה נשלחת עם `Idempotency-Key`. אם אותה פקודה מגיעה פעמיים (לחיצה כפולה או רשת), היא לא מבוצעת שוב.

**מה זה `ConsumerCheckpoints`?**
ה-Worker וה-Agent קוראים את זרם האירועים מנקודה מסוימת (`global_position`). ה-Checkpoint שומר עד איפה כל צרכן הגיע.

## CQRS ו-MVC

**מה זה CQRS?**
הפרדה בין צד הכתיבה (Commands) לצד הקריאה (Queries). Command עובר דרך `CommandBus` אל Handler, שטוען Aggregate ושומר אירועים, ומחזיר רק `{id, version}`. Query קורא רק מטבלאות `rm_*` ולא נוגע ב-Aggregates.
קבצים: `backend/app/commands/`, `backend/app/queries/`.

**איפה רואים את ה-CQRS באנגולר?**
לכל אזור יש שני Services: `*-commands.service.ts` (POST/PUT) ו-`*-queries.service.ts` (GET), למשל `core/investor/`.

**איפה ה-MVC?**
Model: ה-Aggregates וה-Read Models. View: אפליקציית Angular. Controller: ה-Flask Blueprints ב-`backend/app/controllers/`. ה-Controller רק מאמת קלט והרשאות וממפה ל-Command או ל-Query.

**למה טבלאות קריאה נפרדות?**
כל טבלה בנויה לפי מסך. למשל `rm_agent_product_interest` מחזיקה מונים מוכנים לגרף בדשבורד הסוכן, בלי JOIN ובלי חישובים בזמן הקריאה.

## סוכן ה-AI

**מה הסוכן עושה?**
Process עצמאי (`python -m agent`) שמחפש כל 20 שניות בקשות בסטטוס `SUBMITTED`. הוא כותב `AssessmentStarted`, מריץ את ההערכה וכותב `AIAssessmentCompleted`.

**איך הוא בנוי?**
Deep Agent (`deepagents`) עם `ChatOllama` (qwen2.5:7b-instruct), ושני Subagents:
- `market-researcher`: Tavily ותנודתיות
- `policy-analyst`: מסמכי הפוליסות

קודם רצים חוקים דטרמיניסטיים מ-`agent/rules.yaml`, למשל לסנן אפיק שהמשקיע לא רוצה. הפלט עובר ולידציה של Pydantic (`ModelAssessment` ב-`agent/schema.py`, ובדיקות נוספות ב-`agent/validate.py`). אם המודל מחזיר JSON לא תקין, מנסים שוב.
קבצים: `agent/deep_runner.py`, `agent/pipeline.py`, `agent/suitability.py`.

**מה קורה כשמשהו נכשל?**
אם התשתית לא זמינה (Ollama, Chroma או Tavily), נכתב `AssessmentAborted` והבקשה חוזרת ל-`SUBMITTED` בלי שזה ייספר כניסיון. אם התוכן לא תקין, נכתב `AIAssessmentFailed`, ואחרי שלושה כישלונות הבקשה עוברת ל-`FAILED`. המשקיע יכול לשמור את היעד שוב ולהגיש מחדש.

**`AGENT_MODE=deep|chain`?**
`deep` הוא ה-Deep Agent המלא. `chain` הוא שרשרת פשוטה ומהירה יותר, כגיבוי כשהמודל המקומי איטי.

**איך שומרים על פרטיות?**
`agent/privacy.py`: לשירותים חיצוניים (Tavily) לא נשלחים שם, אימייל, טלפון או סכומים (Rule R3).

## RAG

**מה זה RAG?**
Retrieval-Augmented Generation: לפני שהמודל כותב תשובה, מחפשים קטעים רלוונטיים ממסמכים ומוסיפים אותם להקשר. כך ההערכה מצטטת את מסמכי הפוליסה האמיתיים ולא ממציאה.

**איך מסמך נכנס למאגר?**
סוכן מעלה PDF או DOCX, ונכתב אירוע `ProductDocumentUploaded`. ה-Worker (`worker/indexer.py`) מחלץ טקסט ומפצל ל-chunks של 800 תווים עם חפיפה של 120. כל chunk מקבל embedding עם `bge-m3` דרך Ollama, ונשמר ב-ChromaDB ב-collection `policy_documents`. מסמכי ידע כלליים (`seed/knowledge`) נשמרים ב-`knowledge_base`.

**למה חפיפה?**
כדי שמשפט שנחתך בין שני chunks יופיע בשלמותו לפחות באחד מהם.

**למה ChromaDB מקומי ולא בענן?**
פשוט ולא דורש חשבון. ה-DB הראשי (Somee) בענן כנדרש (ADR-4).

## MCP

**מה זה MCP?**
Model Context Protocol: פרוטוקול סטנדרטי שדרכו סוכן AI מגלה כלים וקורא להם. השרת מפרסם כלים עם סכמה, והלקוח (הסוכן) קורא להם.

**אילו שרתי MCP יש?**
- חיצוני: Tavily (`npx -y tavily-mcp`) לחיפוש ברשת.
- שלנו: `goalvest-tools` (`mcp_tools/server.py`, FastMCP, תעבורת stdio) עם שני כלים:
  - `calculate_investment_tax`: לפי `tax_rules.yaml`, בלי מספרים קשיחים בקוד
  - `get_stock_volatility`: לפי yfinance

**איך מדגימים?**
`npx @modelcontextprotocol/inspector python -m mcp_tools.server` (משורש ה-Repo, עם ה-venv של backend).

**איך הסוכן מתחבר לשרתי ה-MCP?**
`langchain-mcp-adapters` הופך כל כלי MCP לכלי LangChain שה-Deep Agent יכול לקרוא לו.

## SDAD, Rules ו-Skills

**מה זה SDAD?**
Specification-Driven Application Development. קודם כותבים מסמכי אפיון (`docs/00`–`18`), ואחר כך סוכן הקוד מפתח פיצ'ר שלם לפי המסמכים. כל שינוי מתחיל בעדכון המסמך. דוגמה: מעבר `FAILED → CANCELLED` נוסף קודם ל-`docs/03` §3.9 ורק אחר כך לקוד.

**אילו Rules יש?**
- R1 ארכיטקטורה: אסור UPDATE על EventStore, ו-Controller בלי לוגיקה
- R2 ממשק עברי: RTL, `<bdi>` ומצבי טעינה, ריק ושגיאה
- R3 ציות פיננסי: הבהרה, לשון זהירה ומקורות

הן נמצאות ב-`.cursor/rules/*.mdc` וב-`.claude/rules/*.md`.

**אילו Skills יש?**
- `add-cqrs-feature`: כתבנו בעצמנו. מסביר לסוכן הקוד איך להוסיף פיצ'ר מקצה לקצה (אירוע ← פקודה ← Projection ← Query ← API ← מסך ← בדיקות).
- `angular-developer`: הותקן מ-skills.sh (`npx skills add https://github.com/angular/skills`). הקבצים ב-`.claude/skills/`, `.cursor/skills/` ו-`.agents/skills/`, והגרסה נעולה ב-`skills-lock.json`.

## שאלות כלליות

**למה Polling ולא WebSocket?**
פשוט יותר ב-Flask, ועדכון כל 15 שניות מספיק (ADR-3).

**למה כסף כ-DECIMAL?**
Float לא מדויק בחישובים כספיים, למשל 0.1+0.2. אצלנו `Decimal` בפייתון ו-`DECIMAL(18,2)` ב-DB (ADR-6).

**איך מאבטחים?**
- JWT: Access ל-30 דקות ו-Refresh ל-7 ימים
- סיסמאות ב-bcrypt
- Rate limiting בהתחברות (5 ניסיונות לכל 15 דקות)
- הרשאות לפי תפקיד בכל Controller, וסוכן רואה רק לידים של הגוף שלו
- סודות רק ב-`.env`, שלא נכנס ל-git

**איך בדקתן?**
pytest עם SQLite בזיכרון (118 בדיקות), כולל בדיקת קומפילציה לדיאלקט MSSQL, ובדיקות Vitest לאנגולר.
