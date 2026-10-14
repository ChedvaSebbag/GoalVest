# 14 – Repo, סביבות והרצה

## 14.1 מבנה ה-Repo (GitHub, monorepo)

```
goalvest/
├── CLAUDE.md                 # הקשר לסוכן הקוד: הפניה ל-docs, Rules ו-Skills
├── README.md                 # הסבר, הרצה, צילומי מסך, קרדיטים ל-Skills
├── docs/                     # מסמכי האפיון (הסט הזה)
├── .claude/
│   ├── rules/                # architecture.md, ui-hebrew.md, financial-compliance.md
│   └── skills/               # add-cqrs-feature/ + Skill מ-skills.sh
├── frontend/                 # Angular
├── backend/                  # Flask API
├── core/                     # goalvest_core – Domain משותף
├── agent/                    # Investment Fit Agent
├── worker/                   # Indexer, Notifier, Price Alerts
├── mcp_tools/                # goalvest-tools MCP server
├── seed/                     # CSV של מוצרים, מסמכים ל-RAG, משתמשי דמו
├── db/migrations/            # סקריפטי SQL ל-Somee
├── docker-compose.yml        # ollama, chromadb (+ אופציונלי api, agent, worker)
├── .env.example
└── .github/workflows/ci.yml  # lint + tests
```

## 14.2 Git

- ענף `main` מוגן. כל פיצ'ר בענף `feature/FR-xx-short-name`.
- Pull Request עם תבנית: איזה FR, אילו מסמכים עודכנו, צילום מסך, בדיקות.
- Code Review הדדי בין בנות הצוות לפני Merge.
- Commits בפורמט Conventional Commits (`feat:`, `fix:`, `docs:`).
- GitHub Issues לכל FR, ו-GitHub Projects כלוח עבודה.

## 14.3 סביבות

| רכיב | פיתוח | הדגמה / הגשה |
|---|---|---|
| Angular | `ng serve` (4200) | `ng build` + הגשה מ-Flask או מ-Netlify/Vercel |
| Flask | `flask run` (5000) | אותו מחשב, או Render/Railway |
| DB | Somee.com (מסד פיתוח) | Somee.com (מסד הדגמה נפרד) |
| Ollama, ChromaDB | Docker Compose מקומי | Docker Compose מקומי |
| Agent, Worker | טרמינל נפרד לכל אחד | Docker Compose |

## 14.4 משתני סביבה (`.env.example`)

```
DB_CONNECTION_STRING=mssql+pyodbc://user:pass@xxx.mssql.somee.com/goalvest?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes
JWT_SECRET=change-me
FRONTEND_ORIGIN=http://localhost:4200
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_CHAT_MODEL=qwen2.5:7b-instruct
OLLAMA_EMBED_MODEL=bge-m3
CHROMA_HOST=localhost
CHROMA_PORT=8000
TAVILY_API_KEY=
GMAIL_MCP_CREDENTIALS_PATH=./secrets/gmail.json
# DOCUMENT_STORAGE_DIR=~/goalvest-documents   ברירת מחדל אם לא הוגדר: תיקייה מחוץ לקוד
AGENT_POLL_SECONDS=20
AGENT_MODE=deep
PRICE_ALERT_DEFAULT_PCT=5
```

## 14.5 הרצה מקומית

```bash
docker compose up -d ollama chromadb
docker exec ollama ollama pull qwen2.5:7b-instruct && docker exec ollama ollama pull bge-m3
cd backend && pip install -e ../core -r requirements.txt && python -m scripts.migrate && python -m scripts.seed && flask run
cd agent && python -m agent
cd worker && python -m worker
cd frontend && npm i && ng serve
```

## 14.6 CI (GitHub Actions)

- `backend`: ruff + pytest (בלי בדיקות `@slow` של LLM).
- `frontend`: eslint + בדיקות יחידה + build.
- `docs`: בדיקת קישורים שבורים במסמכי MD (markdown-link-check).

## 14.7 הערות ל-Somee.com

- בחשבון חינמי יש מגבלת גודל למסד, ועלולות להיות הגבלות על חיבורים חיצוניים או הצגת פרסומות בתוכניות אירוח. יש לבדוק בשבוע הראשון שחיבור pyodbc מבחוץ עובד, ולשמור חלופה (Azure SQL חינמי) במקרה הצורך.
- חיבור דרך `ODBC Driver 18 for SQL Server`. על Mac: `brew install msodbcsql18`.
