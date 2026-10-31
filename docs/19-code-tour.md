# 19 – סיור בקוד

מפת הקבצים המרכזיים לפי נושא. בראש כל אחד מהם יש הערת תיעוד שמסבירה את תפקידו.

## לפי נושא

| נושא | פותחים את | מה מראים |
|---|---|---|
| Event Sourcing | `backend/app/infrastructure/event_store.py` | `append()` – רק INSERT, Projections באותה טרנזקציה, 409 בהתנגשות |
| Aggregate | `core/goalvest_core/aggregate.py` | `from_events` / `_when` / `_record` |
| חוקים עסקיים ומכונת מצבים | `core/goalvest_core/requests/investment_request.py` | `RequestStatus`, `cancel()`, `send_offer()` |
| CQRS – כתיבה | `backend/app/commands/bus.py` + `commands/requests.py` | Bus, Idempotency, Handler שמחזיר `{id, version}` |
| CQRS – קריאה | `backend/app/queries/goals.py` | קורא רק `rm_*` |
| Projections | `backend/app/projections/dispatcher.py` | אירוע → עדכון טבלת קריאה |
| MVC / Controller | `backend/app/controllers/requests.py` | Blueprint: הרשאה, ולידציה, Command – בלי לוגיקה |
| הרשאות ו-JWT | `backend/app/auth/require_role.py`, `auth/jwt.py` | 401/403/404, Access 30 דק', Refresh 7 ימים |
| סוכן ה-AI | `agent/loop.py`, `agent/pipeline.py` | נעילה, Complete/Fail/Abort, 4 שלבי הערכה |
| RAG | `worker/rag.py`, `worker/indexer.py` | Embeddings, ChromaDB, Checkpoints |
| MCP | `mcp_tools/server.py` | 2 כלים ב-FastMCP + Tavily |
| Angular | `app.routes.ts`, `core/interceptors/auth.interceptor.ts`, `core/investor/*-commands/queries.service.ts` | Guards, Interceptor, CQRS בלקוח |

## הזרימה במשפט אחד

מסך Angular → `*-commands.service.ts` (POST + Idempotency-Key) → Controller → Command Bus → Handler → Aggregate (חוקים + אירוע) → `EventStore` (INSERT) + Projector (`rm_*`) → מסך קורא דרך `*-queries.service.ts` → Query Service → `rm_*`.
