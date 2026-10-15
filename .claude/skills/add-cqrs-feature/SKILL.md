---
name: add-cqrs-feature
description: הוספת פיצ'ר מקצה לקצה ב-GoalVest לפי CQRS ו-Event Sourcing – מאירוע ועד מסך Angular ובדיקות. השתמש כשמבקשים לממש FR חדש או לשנות התנהגות עסקית.
---

# הוספת פיצ'ר CQRS ב-GoalVest

## קלט נדרש
מזהה דרישה (FR-xx). אם אין – בקש אותו או נסח דרישה ב-`docs/03` ואשר מול המשתמש לפני קוד.

## צעדים
1. **הבנה**: קרא את ה-FR ב-`docs/03`, את המסכים ב-`docs/05` ואת ה-API ב-`docs/08`. כתוב רשימת אירועים, פקודות ושאילתות שנדרשים.
2. **מסמכים קודם**: עדכן את קטלוג האירועים ב-`docs/07` ואת ה-Endpoints ב-`docs/08`.
3. **אירועים**: `core/goalvest_core/events/<aggregate>.py` – dataclass עם `event_type` ו-`schema_version`.
4. **Aggregate**: מתודה עסקית שמאמתת חוקים ומחזירה רשימת אירועים, ו-`apply_<Event>` לעדכון מצב.
5. **פקודה ו-Handler**: `backend/app/commands/<name>.py`, רישום ב-Command Bus, בדיקת בעלות/תפקיד.
6. **Projection**: Projector ב-`backend/app/projections/`, מיגרציה ב-`db/migrations/` אם צריך עמודה/טבלה.
7. **Query**: מתודה ב-Query Service + DTO.
8. **Controller**: Endpoint ב-Blueprint המתאים עם `@require_role`.
9. **Angular**: מתודה ב-`*-commands.service.ts` / `*-queries.service.ts`, רכיב Standalone, Route ו-Guard. עמידה ב-Rule R2.
10. **בדיקות**:
    - Aggregate: Given events → When command → Then events / שגיאה.
    - Projection: אירוע → מצב ב-`rm_*`.
    - API: הצלחה, 400, 403.
11. **סגירה**: הוסף TC ל-`docs/13`, הרץ `ruff`, `pytest`, `ng lint`, `ng test`. כתוב תיאור PR עם ה-FR והמסמכים שעודכנו.

## בדיקה עצמית לפני סיום
- [ ] אין UPDATE/DELETE על EventStore
- [ ] אין לוגיקה עסקית ב-Controller
- [ ] Query לא נוגע ב-Aggregates
- [ ] האירוע מתועד ב-docs/07
- [ ] יש בדיקות לשלושת הרבדים
