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
docker compose up -d                       # Ollama + ChromaDB
docker exec ollama ollama pull qwen2.5:7b-instruct
docker exec ollama ollama pull bge-m3

cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cd ../frontend && npm install              # אם נכשל: npx npm@11 install
```

**בכל פעם** (שני טרמינלים)
```bash
cd backend && source .venv/bin/activate && python wsgi.py     # http://localhost:5000
cd frontend && npm start                                       # http://localhost:4200
```

**בדיקות**
```bash
cd backend && pytest
cd frontend && npx ng test --watch=false
```
