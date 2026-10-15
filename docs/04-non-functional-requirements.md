# 04 – דרישות לא-פונקציונליות

## 4.1 מיפוי מלא לדרישות המרצה

| # | דרישת המרצה | מימוש ב-GoalVest | איפה מתועד |
|---|---|---|---|
| 1 | פיתוח מבוסס סדרת מסמכי MD | תיקיית `docs/` (הסט הזה), `.claude/rules`, `.claude/skills`, `CLAUDE.md` בשורש | 00-README.md |
| 2 | Skill אחד לפחות מ-Skills.sh | `angular-developer` מתוך `angular/skills` (הותקן עם `npx skills add`). נמצא ב-`.claude/skills`, ב-`.cursor/skills` וב-`.agents/skills`, ונעול ב-`skills-lock.json` | 11-mcp-tools-skills-rules.md |
| 3 | הגדרת Skill אחד ו-Rule אחד לפחות | Skill: `add-cqrs-feature`. Rules: R1 ארכיטקטורה, R2 UI עברי, R3 ציות פיננסי | 11, `.claude/` |
| 4 | שרת אפליקציה Flask | Flask 3 עם Blueprints, flask-jwt-extended, SQLAlchemy | 06-architecture.md |
| 5 | מסד נתונים בענן | MS SQL Server ב-Somee.com | 07-data-model.md |
| 6 | הטמעה במסד וקטורי וחיפוש סמנטי | ChromaDB, מודל הטמעה `bge-m3` דרך Ollama. מוטמעים מסמכי פוליסות, כללי מס, דוחות שוק, תיאורי מוצרים ופרופילי בקשות | 10-rag.md |
| 7 | MVC/CQRS | Controllers (Blueprints) → Command Bus / Query Service. מודל פקודות נפרד ממודל שאילתות | 06-architecture.md |
| 8 | Event Sourcing בענן | טבלת `EventStore` ב-Somee כמקור אמת, Projections לטבלאות קריאה | 07-data-model.md |
| 9 | שירותים חיצוניים דרך MCP | Tavily MCP (חיפוש Web), Gmail MCP (התראות ושחזור סיסמה) | 11 |
| 10 | שני Tools לפחות ב-MCP | שרת MCP עצמאי `goalvest-tools` עם 4 Tools: מחשבון מס, תנודתיות מנייה, תחזית צמיחה, השוואת דמי ניהול | 11 |
| 11 | סוכן ב-Deep Agent עם RAG ו-Tavily | `deepagents` של LangChain, מודל Ollama, Tools: RAG, Tavily MCP, Tools מותאמים | 09-ai-agent.md |
| 12 | ניהול קוד ב-GitHub | Repo אחד (monorepo), ענפים לפי פיצ'ר, Pull Requests, GitHub Actions לבדיקות | 14-repo-and-deployment.md |
| הערה 4 | תצוגה מקצועית, UI/UX | Angular Material + ערכת עיצוב, RTL, נגישות, מצבי ריק/טעינה/שגיאה | 05-screens-and-ux.md |
| הערה 5 | הכרת הקוד ובפרט מימוש התבניות | מסמך זה מפרט כל תבנית עם דוגמת קוד וזרימה. כל אחת מבנות הצוות מציגה את כל התבניות | 06, 15 |

## 4.2 ביצועים

| מזהה | דרישה |
|---|---|
| NFR-01 | שאילתות (Read) יחזירו תשובה תוך 500ms ב-95% מהמקרים, מתוך Read Models בלבד |
| NFR-02 | פקודות (Write) יסתיימו תוך 1 שנייה, כולל כתיבת האירוע ועדכון ה-Projection |
| NFR-03 | הערכת AI תסתיים תוך 3 דקות (Ollama, מודל 7B, מחשב פיתוח) |
| NFR-04 | טעינת מסך ראשונית באנגולר עד 3 שניות. Lazy Loading לכל מודול תפקיד |
| NFR-05 | נתוני שוק מ-yfinance נשמרים ב-Cache ל-15 דקות כדי לא לחרוג ממגבלות |

## 4.3 אמינות ועקביות

| מזהה | דרישה |
|---|---|
| NFR-10 | אירועים הם Append-Only. אין UPDATE או DELETE על טבלת `EventStore` (נאכף גם בהרשאות משתמש DB אם Somee מאפשר, וגם בקוד) |
| NFR-11 | בקרת מקביליות אופטימית: אינדקס ייחודי על (`aggregate_id`, `version`) |
| NFR-12 | כתיבת אירוע ועדכון Projection באותה טרנזקציה (עקביות מיידית ב-MVP) |
| NFR-13 | פקודת `rebuild-projections` מוחקת את טבלאות הקריאה ובונה אותן מחדש מכל האירועים |
| NFR-14 | פקודות idempotent: כל פקודה נושאת `command_id`. פקודה שכבר עובדה לא תיצור אירוע נוסף |
| NFR-15 | כשל של סוכן ה-AI או של Ollama לא משפיע על זמינות שרת Flask |

## 4.4 אבטחה ופרטיות

ראו 12-security-and-compliance.md. עיקרים: bcrypt לסיסמאות, JWT עם תפוגה, הרשאות לפי תפקיד בשרת (לא רק בלקוח), סודות ב-`.env` בלבד, HTTPS בפריסה, אין מידע אישי מזהה בפרומפטים שנשלחים ל-Tavily.

## 4.5 שימושיות ונגישות

| מזהה | דרישה |
|---|---|
| NFR-30 | ממשק בעברית מלאה, `dir="rtl"`, מספרים וסימולים באנגלית בתוך `<bdi>` |
| NFR-31 | רספונסיבי: 360px (מובייל), 768px (טאבלט), 1280px+ (דסקטופ) |
| NFR-32 | ניגודיות AA לפי WCAG 2.1, ניווט מקלדת מלא, aria-label לכל כפתור אייקון |
| NFR-33 | לכל רשימה/טבלה: מצב טעינה (Skeleton), מצב ריק עם קריאה לפעולה, מצב שגיאה עם "נסה שוב" |
| NFR-34 | פורמט כספי: `₪ 1,234,567`, אחוזים עם ספרה אחת אחרי הנקודה, תאריכים `dd/MM/yyyy` |
| NFR-35 | הבהרה משפטית ("המידע אינו מהווה ייעוץ השקעות...") בכל מסך שמציג הערכה או המלצה |

## 4.6 תחזוקתיות ואיכות קוד

| מזהה | דרישה |
|---|---|
| NFR-40 | Python: Type hints, ruff, pytest עם כיסוי ≥ 70% לשכבת Domain ו-Command Handlers |
| NFR-41 | Angular: strict mode, ESLint, Standalone Components, Signals לניהול מצב מקומי ו-RxJS לזרמי נתונים |
| NFR-42 | כל פיצ'ר מתחיל בעדכון מסמך MD רלוונטי, ורק אחר כך קוד (SDAD) |
| NFR-43 | לוגים מובנים (JSON) עם `correlation_id` שעובר מהבקשה ב-Angular דרך Flask ועד אירועי ה-Event Store והסוכן |
