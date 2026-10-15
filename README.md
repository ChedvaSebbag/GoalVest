# GoalVest

פלטפורמה חכמה להשקעות מבוססות-מטרות – פרויקט סיום בקורס "הנדסת תוכנה בעידן AI", המרכז האקדמי לב.

**צוות:** חדוה סבג, איילת סורובסקי

## מסמכים
- אפיון מלא: [`docs/`](docs/00-README.md)
- הנחיות לסוכן הקוד: [`AGENTS.md`](AGENTS.md), [`CLAUDE.md`](CLAUDE.md)
- Rules: `.cursor/rules/`, `.claude/rules/`
- Skills: `.cursor/skills/`, `.claude/skills/`. כולל `angular-developer` שהותקן מ-skills.sh (`npx skills add https://github.com/angular/skills`)

## טכנולוגיות
Angular · Flask · MS SQL Server (Somee.com) · Event Sourcing + CQRS · ChromaDB · Ollama · LangChain Deep Agents · MCP

## מבנה
```
frontend/   Angular (RTL, Angular Material)
backend/    Flask API – controllers / commands / queries / projections
core/       goalvest_core – Domain משותף
agent/      Investment Fit Agent (Deep Agent)
worker/     Indexer, Notifier, Price Alerts
mcp_tools/  goalvest-tools MCP server
db/         מיגרציות SQL ל-Somee
```

## הרצה מקומית

**דרישות מוקדמות (פעם אחת):** Docker Desktop, Ollama (https://ollama.com/download), Python 3.12, Node 20+, ODBC Driver 18 for SQL Server.
```bash
cp .env.example .env              # למלא DB_SERVER, DB_NAME, DB_USER, DB_PASSWORD, JWT_SECRET, TAVILY_API_KEY
ollama pull qwen2.5:7b-instruct
ollama pull bge-m3
cd backend && python3.12 -m venv .venv && cd ..
```

**הרצה בפקודה אחת** (משורש ה-Repo)
```bash
bash dev.sh --setup    # בפעם הראשונה ואחרי משיכת קוד חדש: pip install, מיגרציות, npm install
bash dev.sh            # בכל פעם: ChromaDB, API, סוכן AI, Indexer ו-Angular
```
הסקריפט מעלה את כל הרכיבים, מחכה שיהיו בריאים ופותח את הדפדפן ב-http://localhost:4200. הלוגים נכתבים ל-`logs/*.log`. Ctrl+C עוצר הכול.

**נתוני הדגמה** (פעם אחת, אחרי `--setup`)
```bash
cd backend && source .venv/bin/activate
python -m scripts.seed            # 25 מוצרים, 3 משקיעים, 3 סוכנים
python -m scripts.rebuild_leads   # בונה מחדש את טבלאות הלידים מהאירועים
```
| חשבון | אימייל | סיסמה |
|---|---|---|
| משקיעה | `demo.investor1@goalvest.test` | `Demo1234` |
| סוכן הראל | `demo.agent.harel@goalvest.test` | `Demo1234` |
| סוכן כלל | `demo.agent.clal@goalvest.test` | `Demo1234` |
| סוכן מגדל | `demo.agent.migdal@goalvest.test` | `Demo1234` |

בסביבת פיתוח מסך ההתחברות מציג כפתורים שממלאים את החשבונות האלה.

## איך משתמשים במערכת

- **בכניסה הראשונה** מופיע סיור היכרות קצר. אפשר להציג אותו שוב מדף **עזרה** (קישור בסרגל העליון).
- **בראש כל דשבורד** יש כרטיס "הצעד הבא" שאומר מה המצב ומה כדאי לעשות עכשיו.
- **בדף יעד ובדף ליד** מוצג מסלול הבקשה: הגשה ← הערכת AI ← בדיקת סוכן ← הצעה ← סיום, עם הסבר מי צריך לפעול.
- **סימן ?** ליד מונחים מקצועיים (דמי ניהול, סטיית תקן, ציון התאמה) מציג הסבר קצר.
- **דף העזרה** (`/help`) כולל מדריך למשקיע ולסוכן, הסבר לכל סטטוס, מילון מונחים ושאלות נפוצות.

תהליך מלא בקצרה:
1. **משקיע** נרשם, ממלא שאלון סיכון ומגדיר יעד (סכום, מועד והעדפות).
2. **סוכן ה-AI** מעריך את היעד תוך דקה עד שלוש: ציון, תמהיל, מסלולים, דגלי סיכון ומקורות.
3. **סוכן אנושי** מהגוף המתאים לוקח את הליד, מאשר את ההערכה ושולח הצעה.
4. **המשקיע** מקבל התראה ומאשר או דוחה.

תסריט הדגמה: [`docs/17-demo-script.md`](docs/17-demo-script.md). שאלות הכנה: [`docs/18-exam-prep.md`](docs/18-exam-prep.md).

**בדיקות**
```bash
cd backend && source .venv/bin/activate && pytest   # SQLite בזיכרון, בלי Somee
cd frontend && npx ng test --watch=false
```

**MCP ו-RAG** (משורש ה-Repo, עם סביבת ה-backend)
```bash
source backend/.venv/bin/activate
npx @modelcontextprotocol/inspector python -m mcp_tools.server
python -m worker.indexer          # לולאה כל 15 שניות
python -m worker.indexer --once   # הרצה אחת
python -m worker.index_knowledge  # seed/knowledge אל knowledge_base
python -m agent                   # לולאת הערכה כל 20 שניות. AGENT_MODE=deep או chain
python -m agent --once --request <id> --verbose
```
