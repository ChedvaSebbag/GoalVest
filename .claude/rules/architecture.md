
# Rule R1 – ארכיטקטורה: CQRS + Event Sourcing

חובה:
- כל שינוי מצב נשמר כאירוע דרך `EventStoreRepository.append()` בלבד.
- אסור UPDATE או DELETE על טבלת `EventStore`, בשום מקום בקוד.
- Controllers (Flask Blueprints) רק: ולידציית קלט, הרשאות, מיפוי ל-Command/Query, החזרת תשובה. אין לוגיקה עסקית.
- Command Handlers לא מחזירים נתוני תצוגה – רק `{id, version}`.
- Query Services קוראים רק מטבלאות `rm_*`, ולא טוענים Aggregates.
- חוקים עסקיים נמצאים במתודות של ה-Aggregate, לא ב-Handler ולא ב-Controller.
- Projectors הם פונקציות טהורות מול ה-Session, ללא קריאות רשת או מייל.
- תופעות לוואי (מייל, הטמעה, AI) רק ב-Worker או ב-Agent, אחרי שהאירוע נשמר.
- כסף: `Decimal` / `DECIMAL(18,2)`. אסור float לסכומים.
- כל אירוע חדש מתועד בקטלוג ב-`docs/07-data-model.md` באותו PR.
- באנגולר: קריאות כתיבה ב-`*-commands.service.ts`, קריאות קריאה ב-`*-queries.service.ts`.
