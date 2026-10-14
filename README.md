# GoalVest

פלטפורמה חכמה להשקעות מבוססות-מטרות – פרויקט סיום בקורס "הנדסת תוכנה בעידן AI", המרכז האקדמי לב.

**צוות:** חדוה סבג, איילת סורובסקי

## מסמכים
- אפיון מלא: [`docs/`](docs/00-README.md)
- הנחיות לסוכן הקוד: [`AGENTS.md`](AGENTS.md), [`CLAUDE.md`](CLAUDE.md)
- Rules: `.cursor/rules/`, `.claude/rules/`
- Skills: `.cursor/skills/`, `.claude/skills/`

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

**פעם ראשונה**
```bash
cp .env.example .env                       # ולמלא את DB_CONNECTION_STRING
docker compose up -d                       # ChromaDB
# Ollama מותקן ישירות על ה-Mac (https://ollama.com/download)
ollama pull qwen2.5:7b-instruct
ollama pull bge-m3

cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt            # כולל goalvest_core בעריכה חיה (-e ../core)
cd ../frontend && npm install              # אם נכשל: npx npm@11 install
```

**בכל פעם** (שני טרמינלים)
```bash
cd backend && source .venv/bin/activate && python wsgi.py     # http://localhost:5000
cd frontend && npm start                                       # http://localhost:4200
```

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
```
