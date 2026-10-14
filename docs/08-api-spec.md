# 08 – API

## 8.1 מוסכמות

- בסיס: `/api`. JSON בלבד. תאריכים ISO-8601 UTC. כסף כמספר עשרוני.
- כותרות: `Authorization: Bearer <access>`, `X-Correlation-Id`, ולפקודות `Idempotency-Key` (= `command_id`).
- **פקודות** (POST/PUT/DELETE) מחזירות `201`/`202` עם `{ id, version }` בלבד.
- **שאילתות** (GET) מחזירות DTO מוכן לתצוגה. רשימות: `?page=1&pageSize=20&sort=field,desc`.
- שגיאות בפורמט אחיד:

```json
{ "error": { "code": "VALIDATION_ERROR", "message": "סכום היעד חייב להיות חיובי", "fields": { "targetAmount": "חייב להיות גדול מ-0" } } }
```

| קוד HTTP | מתי |
|---|---|
| 400 | ולידציה |
| 401 | אין טוקן / טוקן פג |
| 403 | אין הרשאה לתפקיד או למשאב |
| 404 | לא נמצא |
| 409 | התנגשות גרסה, מעבר סטטוס לא חוקי, אימייל קיים |
| 422 | הפרת חוק עסקי (למשל בקשה שנייה לאותו יעד) |

## 8.2 אוטנטיקציה

| Method | Path | תיאור | תפקיד |
|---|---|---|---|
| POST | `/api/auth/register` | הרשמה (FR-01) | ציבורי |
| POST | `/api/auth/login` | מחזיר `accessToken` (30 דק'), `refreshToken` (7 ימים), `user {id, role, fullName}` | ציבורי |
| POST | `/api/auth/refresh` | טוקן חדש | ציבורי + refresh |
| POST | `/api/auth/logout` | פסילת refresh | מחובר |
| POST | `/api/auth/forgot-password` | תמיד 202 (לא חושף אם האימייל קיים) | ציבורי |
| POST | `/api/auth/reset-password` | `{ token, newPassword }` | ציבורי |
| GET | `/api/auth/me` | פרטי המשתמש המחובר | מחובר |
| GET | `/api/institutions` | רשימת גופים פיננסיים ל-Autocomplete בהרשמת סוכן (Query, קטלוג קבוע בשרת) | ציבורי |

הרשמה (`POST /api/auth/register`) מקבלת `Idempotency-Key` ומחזירה `201` עם `{ id, version }` בלבד. האימייל נשמר אחרי `strip().lower()`. אימייל קיים, גם בהתנגשות מקבילית על האינדקס הייחודי, מחזיר `409` עם `EMAIL_EXISTS`. סוכן חייב `institutionId` מתוך `GET /api/institutions` ו-`licenseNo`, אחרת `400`.

התחברות מחזירה `accessToken` (30 דקות), `refreshToken` (7 ימים) ו-`user {id, role, fullName}`. ה-claims בטוקן: `sub`, `role`, `institution_id`. סיסמה שגויה או אימייל לא קיים מחזירים אותו `401` ("אימייל או סיסמה שגויים"). 5 ניסיונות כושלים לאימייל ב-15 דקות מחזירים `429`.

## 8.3 משקיע

| Method | Path | סוג | תיאור |
|---|---|---|---|
| PUT | `/api/investor/profile` | Command | יצירה/עדכון פרופיל |
| POST | `/api/investor/risk-assessment` | Command | `{ answers }` → מחשב ציון ושומר `RiskProfileAssessed` |
| GET | `/api/investor/profile` | Query | פרופיל + פרופיל סיכון |
| POST | `/api/investor/goals` | Command | יצירת יעד |
| PUT | `/api/investor/goals/{id}` | Command | עדכון יעד |
| DELETE | `/api/investor/goals/{id}` | Command | ארכוב |
| GET | `/api/investor/goals` | Query | רשימת יעדים לדשבורד |
| GET | `/api/investor/goals/{id}` | Query | יעד + בקשה פעילה + הערכה (לפי הרשאה) |
| POST | `/api/investor/goals/projection` | Query (חישוב) | תחזית 3 תרחישים, דרך Tool `project_goal_growth` (FR-13) |
| POST | `/api/requests` | Command | `{ goalId, consentShareContact }` → הגשת בקשה |
| POST | `/api/requests/{id}/cancel` | Command | ביטול |
| GET | `/api/requests/{id}/timeline` | Query | ציר זמן מאירועים (FR-65) |

כל הנתיבים בטבלה למעט `POST /api/investor/goals/projection` (FR-13, לא בשלב הזה) דורשים `INVESTOR`. משקיע שניגש ליעד או לבקשה של משקיע אחר מקבל 404.

| קוד | מתי |
|---|---|
| 400 `VALIDATION_ERROR` | סכום, תאריך (פחות מ-6 חודשים, כולל עבר), שדה חסר. `targetDate` בתאריך לא חוקי |
| 403 `FORBIDDEN` | תפקיד שאינו `INVESTOR` |
| 404 `NOT_FOUND` | אין יעד/בקשה, או שהם של משקיע אחר |
| 409 `PROFILE_EXISTS` | `PUT /profile` אחרי שכבר נוצר פרופיל |
| 422 `RISK_PROFILE_REQUIRED` | הגשת בקשה בלי ציון סיכון |
| 422 `ACTIVE_REQUEST_EXISTS` | בקשה פעילה שנייה לאותו יעד |
| 422 `REQUEST_IN_PROCESSING` | עריכה, ארכוב או ביטול כשהבקשה ב-`AI_PROCESSING` |
| 422 `CONSENT_REQUIRED` | הגשה בלי אישור שיתוף פרטים |

`PUT /api/investor/goals/{id}` עם `consentShareContact: true` ושינוי בשדות, כשיש בקשה פעילה שאינה בעיבוד: `GoalUpdated`, `RequestCancelled` על הישנה, ו-`InvestmentRequestSubmitted` חדשה. ארכוב סוגר בקשה פעילה ולא פותח חדשה.
| GET | `/api/investor/dashboard` | Query | KPI, יעדים, תמהיל, מסלולים מומלצים |
| GET | `/api/investor/offers` | Query | הצעות שהתקבלו |
| POST | `/api/investor/offers/{offerId}/accept` | Command | קבלה |
| POST | `/api/investor/offers/{offerId}/decline` | Command | דחייה `{ reason? }` |
| GET | `/api/investor/portfolio` | Query | אחזקות + שווי נוכחי |
| POST | `/api/investor/portfolio/holdings` | Command | הוספת אחזקה |
| DELETE | `/api/investor/portfolio/holdings/{symbol}` | Command | הסרה |
| PUT | `/api/investor/portfolio/alert-threshold` | Command | `{ percent }` |

## 8.4 מוצרים

| Method | Path | סוג | תיאור | תפקיד |
|---|---|---|---|---|
| GET | `/api/products` | Query | חיפוש וסינון: `q, type[], riskMin, riskMax, maxFee, minReturn3y, liquidity, institutionId, page, sort` | מחובר |
| GET | `/api/products/semantic-search?q=` | Query | חיפוש סמנטי ב-ChromaDB (FR-22) | מחובר |
| GET | `/api/products/{id}` | Query | פרטים מלאים + מסמכים + התאמה למשתמש | מחובר |
| GET | `/api/products/compare?ids=` | Query | 2–4 מוצרים | מחובר |
| GET | `/api/products/{id}/market` | Query | מחיר ותנודתיות (מניות/סל) | מחובר |
| POST | `/api/agent/products` | Command | יצירת מוצר | AGENT |
| PUT | `/api/agent/products/{id}` | Command | עדכון | AGENT (אותו גוף) |
| POST | `/api/agent/products/{id}/deactivate` | Command | השבתה | AGENT |
| POST | `/api/agent/products/{id}/documents` | Command | `multipart/form-data`: file, docType | AGENT |
| GET | `/api/agent/products/{id}/documents` | Query | סטטוס הטמעה | AGENT |
| GET | `/api/documents/{docId}/download` | Query | הורדת קובץ | מחובר |

## 8.5 סוכן – לידים ודשבורד

| Method | Path | סוג | תיאור |
|---|---|---|---|
| GET | `/api/agent/dashboard` | Query | KPI לפי סטטוס, המרה, ציון ממוצע (FR-41) |
| GET | `/api/agent/dashboard/product-interest` | Query | מתעניינים לפי מוצר (FR-42) |
| GET | `/api/agent/leads` | Query | `status, minScore, goalType, page, sort, since` |
| GET | `/api/agent/leads/{requestId}` | Query | פרטי ליד + הערכה מלאה + ציר זמן |
| POST | `/api/agent/leads/{requestId}/claim` | Command | לקיחת ליד |
| POST | `/api/agent/leads/{requestId}/assessment/approve` | Command | `{ note? }` |
| POST | `/api/agent/leads/{requestId}/assessment/reject` | Command | `{ note }` חובה |
| POST | `/api/agent/leads/{requestId}/reevaluate` | Command | `{ reason }` |
| POST | `/api/agent/leads/{requestId}/offers` | Command | `{ items:[{productId, percent}], message }` – סכום אחוזים 100 |

## 8.6 התראות ומערכת

| Method | Path | סוג | תיאור |
|---|---|---|---|
| GET | `/api/notifications?unreadOnly=` | Query | רשימת התראות |
| GET | `/api/notifications/unread-count` | Query | מונה לפעמון (Polling) |
| POST | `/api/notifications/{id}/read` | Command | סימון כנקרא |
| GET | `/api/health` | – | בריאות: DB, ChromaDB, Ollama |
| POST | `/api/admin/agents/{userId}/approve` | Command | ADMIN |
| POST | `/api/admin/projections/rebuild` | Command | ADMIN |

## 8.7 דוגמה: שליחת הצעה

```http
POST /api/agent/leads/7d1e…/offers
Authorization: Bearer eyJ…
Idempotency-Key: 4a0c…
Content-Type: application/json

{
  "items": [
    { "productId": "c21…", "percent": 70 },
    { "productId": "9fa…", "percent": 30 }
  ],
  "message": "שלום נועה, בהמשך להערכה, מציעה תמהיל סולידי-מאוזן…"
}
```

```http
201 Created
{ "id": "offer-5e2…", "version": 9 }
```

חוקים שנבדקים ב-Aggregate: הליד בסטטוס `IN_REVIEW` ומשויך לסוכן הזה, כל המוצרים פעילים ושייכים לגוף של הסוכן, סכום האחוזים 100, 1–3 מוצרים.
