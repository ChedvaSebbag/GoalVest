# 07 – מודל נתונים ו-Event Sourcing

## 7.1 Aggregates

| Aggregate | מזהה | אחריות וחוקים מרכזיים |
|---|---|---|
| `UserAccount` | user_id | הרשמה, תפקיד, סיסמה, אישור סוכן. אימייל ייחודי (נאכף גם ב-`rm_users`) |
| `InvestorProfile` | user_id | פרטים אישיים ופרופיל סיכון. אי אפשר להגיש בקשה בלי פרופיל סיכון |
| `Goal` | goal_id | יעד ובקשת ההשקעה הפעילה שלו. בקשה פעילה אחת לכל יעד |
| `InvestmentRequest` | request_id | מכונת המצבים (03 §3.9), הערכת AI, Claim, אישור/דחייה, הצעות |
| `Product` | product_id | מוצר של גוף פיננסי, מסמכים ומצב הטמעה |
| `Institution` | institution_id | גוף פיננסי (seed / Admin) |
| `Portfolio` | user_id | אחזקות מניות וספי התראה |

## 7.2 טבלת Event Store (SQL Server)

```sql
CREATE TABLE EventStore (
    global_position  BIGINT IDENTITY(1,1) PRIMARY KEY,
    event_id         UNIQUEIDENTIFIER NOT NULL UNIQUE,
    aggregate_type   NVARCHAR(50)  NOT NULL,
    aggregate_id     UNIQUEIDENTIFIER NOT NULL,
    version          INT           NOT NULL,
    event_type       NVARCHAR(100) NOT NULL,
    schema_version   SMALLINT      NOT NULL DEFAULT 1,
    payload          NVARCHAR(MAX) NOT NULL,   -- JSON
    metadata         NVARCHAR(MAX) NOT NULL,   -- JSON: user_id, role, correlation_id, command_id
    occurred_at      DATETIME2(3)  NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_Aggregate_Version UNIQUE (aggregate_type, aggregate_id, version),
    CONSTRAINT CK_Payload_Json CHECK (ISJSON(payload) = 1)
);
CREATE INDEX IX_EventStore_Type ON EventStore(event_type, global_position);

CREATE TABLE ProcessedCommands (
    command_id   UNIQUEIDENTIFIER PRIMARY KEY,
    result_json  NVARCHAR(MAX),
    processed_at DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME()
);

CREATE TABLE ConsumerCheckpoints (       -- למעקב של ה-Worker וה-Agent
    consumer_name    NVARCHAR(50) PRIMARY KEY,
    last_position    BIGINT NOT NULL
);
```

- הוספת אירוע: `INSERT` עם `version = expected_version + 1`. הפרת `UQ_Aggregate_Version` → `ConcurrencyError` → HTTP 409.
- האילוץ כולל `aggregate_type`, כדי ש-`UserAccount` ו-`InvestorProfile` יחלקו את אותו `user_id` ועדיין לכל אחד תהיה גרסה 1. מיגרציה 003 מעדכנת מסד שנוצר עם האילוץ הישן.
- הקוד לעולם לא מריץ `UPDATE`/`DELETE` על `EventStore`. בדיקת יחידה סורקת את הקוד ומוודאת זאת.
- שינוי מבנה אירוע: מעלים `schema_version` ומוסיפים Upcaster בקוד הטעינה.

## 7.3 קטלוג אירועים

| אירוע | Aggregate | שדות עיקריים ב-payload | מי יוצר |
|---|---|---|---|
| `UserRegistered` | UserAccount | email, full_name, phone, role, password_hash, institution_id?, license_no? | API |
| `AgentApproved` | UserAccount | approved_by | Admin |
| `PasswordResetRequested` | UserAccount | token_hash, expires_at | API |
| `PasswordChanged` | UserAccount | password_hash | API |
| `InvestorProfileCreated` | InvestorProfile | birth_year, marital_status, monthly_income_range, has_emergency_fund, existing_products[] | API |
| `RiskProfileAssessed` | InvestorProfile | answers{}, score (1–5), label | API |
| `GoalCreated` | Goal | investor_id, type, title, initial_amount, monthly_deposit, target_amount, target_date, flexibility, liquidity_need, excluded_channels[], preferred_channels[], preferred_institutions[] | API |
| `GoalUpdated` | Goal | שדות שהשתנו בלבד | API |
| `GoalArchived` | Goal | reason | API |
| `InvestmentRequestSubmitted` | InvestmentRequest | goal_id, investor_id, snapshot של יעד ופרופיל סיכון, consent_share_contact | API |
| `AssessmentStarted` | InvestmentRequest | attempt, agent_run_id, model | Agent |
| `AIAssessmentCompleted` | InvestmentRequest | overall_score, channel_scores{}, allocation{}, recommended_products[], rationale, risk_flags[], sources[], duration_ms, model | Agent |
| `AIAssessmentFailed` | InvestmentRequest | attempt, error_code, message, retry_at? | Agent |
| `LeadClaimed` | InvestmentRequest | agent_id, institution_id | API |
| `AssessmentApproved` | InvestmentRequest | agent_id, note? | API |
| `AssessmentRejected` | InvestmentRequest | agent_id, note | API |
| `ReevaluationRequested` | InvestmentRequest | agent_id, reason | API |
| `OfferSent` | InvestmentRequest | offer_id, agent_id, items[{product_id, percent}], message | API |
| `OfferAccepted` / `OfferDeclined` | InvestmentRequest | offer_id, reason? | API |
| `RequestCancelled` | InvestmentRequest | by, reason | API |
| `ProductCreated` | Product | type, name, institution_id, track, symbol?, fee_deposit, fee_assets, return_1y/3y/5y, std_dev, risk_level (1–7), liquidity, liquidity_terms, tax_notes, min_deposit, description | API / Seed |
| `ProductUpdated` | Product | רק השדות שהשתנו מתוך הרשימה של `ProductCreated` (בלי `institution_id`) | API |
| `ProductDeactivated` | Product | reason | API |
| `ProductDocumentUploaded` | Product | document_id, file_name, stored_name, doc_type, storage_path (שם יחסי `{uuid}.pdf\|docx`), sha256, size_bytes | API |
| `ProductDocumentIndexed` | Product | document_id, chunks_count, embedding_model | Worker |
| `ProductDocumentIndexFailed` | Product | document_id, error | Worker |
| `HoldingAdded` / `HoldingRemoved` | Portfolio | symbol, quantity, buy_price, buy_date | API |
| `AlertThresholdChanged` | Portfolio | percent | API |
| `PriceAlertTriggered` | Portfolio | symbol, change_pct, price, trading_date | Worker |
| `NotificationSent` | (לפי הקשר) | channel (email / in_app), template, recipient_user_id, related_event_id | Worker |

סטטוסי `InvestmentRequest` שקיימים בקוד גם לפני אירועי הסוכן: `SUBMITTED`, `AI_PROCESSING`, `AI_EVALUATED`, `IN_REVIEW`, `CANCELLED`. ביטול מותר מ-`SUBMITTED`, `AI_EVALUATED` ו-`IN_REVIEW` (03 §3.9). עריכה או ארכוב כשהבקשה ב-`AI_PROCESSING` נדחים בקוד `REQUEST_IN_PROCESSING`. אירועי `AssessmentStarted`, `AIAssessmentCompleted` ו-`LeadClaimed` עדיין לא נכתבים כאן; הסוכן יחבר אותם לסטטוסים הקיימים.

דוגמת payload:

```json
{
  "event_type": "AIAssessmentCompleted",
  "payload": {
    "overall_score": 78,
    "channel_scores": { "capital_market": 55, "hishtalmut": 30, "gemel_policy": 85 },
    "allocation": { "capital_market": 20, "hishtalmut": 0, "gemel_policy": 80 },
    "recommended_products": [
      { "product_id": "…", "fit_score": 88, "reason": "מסלול מחקה S&P500, דמי ניהול 0.6% מצבירה" }
    ],
    "rationale": "…",
    "risk_flags": [ { "code": "LOCKUP_EXCEEDS_HORIZON", "severity": "high", "text": "…" } ],
    "sources": [
      { "type": "rag", "document_id": "…", "title": "תנאי פוליסה X", "excerpt": "…" },
      { "type": "web", "url": "https://…", "title": "…", "retrieved_at": "2026-10-08T09:12:00Z" }
    ],
    "model": "qwen2.5:7b",
    "duration_ms": 104233
  }
}
```

## 7.4 Read Models (טבלאות שאילתה)

| טבלה | עמודות עיקריות | משמשת את |
|---|---|---|
| `rm_users` | user_id, email (unique, אחרי `strip().lower()`), full_name, phone, role, institution_id, status, password_hash | התחברות, הרשאות |
| `rm_investor_profiles` | user_id, risk_score, risk_label, birth_year, … | שאלון, דשבורד |
| `rm_goals` | goal_id, investor_id, type, title, amounts, target_date, active_request_id, status | S7, S8 |
| `rm_requests` | request_id, goal_id, investor_id, status, overall_score, claimed_by, institution_id, assessment_review (approved/rejected/null), created_at, updated_at | תור הסוכן, S8 |
| `rm_assessments` | request_id, attempt, json מלא של ההערכה, created_at | S8, S15 |
| `rm_leads` | request_id, institution_id (שורה לכל גוף רלוונטי), investor_display_name, goal_type, amount, horizon_years, risk_label, ai_score, status, is_new | S14 טבלת לידים |
| `rm_agent_kpis` | institution_id, count_by_status (עמודה לכל סטטוס), offers_sent, offers_accepted, avg_ai_score | S14 KPI |
| `rm_agent_product_interest` | product_id, institution_id, recommended_count, offers_count, accepted_count | S14 גרף "מתעניינים לפי מוצר" (FR-42) |
| `rm_products` | product_id, type, name, institution_id, institution_name, track, symbol, fee_deposit, fee_assets, return_1y/3y/5y, std_dev, risk_level, liquidity, liquidity_terms, tax_notes, min_deposit, description, is_active, search_text, updated_at | S9, S10, S16 |
| `rm_product_documents` | document_id, product_id, file_name, stored_name, doc_type, storage_path, sha256, size_bytes, index_status, chunks_count, uploaded_at | S10, S17 |
| `rm_offers` | offer_id, request_id, investor_id, agent_id, items_json, message, status | S12 |
| `rm_holdings` | user_id, symbol, quantity, buy_price | S13 |
| `rm_notifications` | notification_id, user_id, title, body, link, is_read, created_at | S18 |
| `rm_request_timeline` | request_id, global_position, event_type, actor, display_text, occurred_at | S8, S15 |

`license_no` נשמר ב-payload של `UserRegistered` ואינו עמודה ב-`rm_users`.

`storage_path` של מסמך הוא שם קובץ יחסי (`{document_id}.pdf` או `.docx`) תחת `DOCUMENT_STORAGE_DIR`, מחוץ לתיקיית הקוד. `index_status` נפתח ב-`PENDING_INDEX`. אירועי `ProductDocumentIndexed` ו-`ProductDocumentIndexFailed` נשארים ל-Worker ואינם נכתבים בהעלאה.

סוגי מוצר (`type`): `HISHTALMUT`, `GEMEL_INVESTMENT`, `SAVINGS_POLICY`, `STOCK`, `ETF`. סינון "סוג אפיק" משתמש בשלושת האפיקים `CAPITAL_MARKET` (מניה ותעודת סל), `HISHTALMUT`, `GEMEL_POLICY` (גמל להשקעה ופוליסת חיסכון). נזילות: `NONE`, `PARTIAL`, `HIGH`. סוגי מסמך: `POLICY_TERMS`, `QUARTERLY_REPORT`, `TAX_RULES`, `MARKET_REPORT`.

### טבלת תפעול (אינה Read Model)

| טבלה | עמודות | תפקיד |
|---|---|---|
| `RevokedTokens` | jti, expires_at, revoked_at | פסילת Refresh Token ב-logout וב-rotation. לפי docs/12 §12.1. לא נגזרת מאירוע, ואין עליה `UPDATE`/`DELETE` של `EventStore` |

**דוגמת Projector:**

```python
@projector("AIAssessmentCompleted")
def on_assessment_completed(e: Event, s: Session):
    s.execute(update(RmRequest).where(RmRequest.request_id == e.aggregate_id)
              .values(status="AI_EVALUATED", overall_score=e.payload["overall_score"]))
    for inst_id in institutions_of(e.payload["recommended_products"], s):
        upsert_lead(s, e.aggregate_id, inst_id, ai_score=e.payload["overall_score"])
    for p in e.payload["recommended_products"]:
        increment(s, RmAgentProductInterest, p["product_id"], "recommended_count")
```

## 7.5 נתוני Seed

| נתון | מקור | כמות מוערכת |
|---|---|---|
| גופים פיננסיים | רשימה ידנית של גופים מוסדיים (שמות בדויים או אמיתיים – ראו 16) | 6–8 |
| קרנות השתלמות וקופות גמל להשקעה | נתוני תשואות ודמי ניהול מגמל-נט (משרד האוצר), הורדה ידנית ל-CSV וייבוא בסקריפט | 30–50 מסלולים |
| פוליסות חיסכון | נתוני ביטוח-נט / אתרי החברות, הזנה ידנית | 10–15 |
| מניות ותעודות סל | רשימת סימולים (S&P500, ת"א 35, תעודות סל מחקות) – נתונים חיים מ-yfinance | 30–50 |
| מסמכים ל-RAG | תנאי פוליסות לדוגמה, סיכום כללי מס לאפיקים, מדריכים לצרכן, דוחות שוק | 15–30 מסמכים |
| משתמשי דמו | 3 משקיעים, 3 סוכנים מגופים שונים, Admin | 7 |

כל ה-Seed נכנס דרך פקודות (ולא INSERT ישיר), כך שגם הוא נשמר כאירועים.
