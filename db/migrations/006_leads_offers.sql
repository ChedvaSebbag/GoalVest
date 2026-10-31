-- 006: לידים, מדדי סוכן, הצעות והתראות (docs/07 §7.4)
-- הרצה: python -m scripts.migrate מתוך backend, אחרי 005.

ALTER TABLE rm_requests ADD assessment_note NVARCHAR(500) NULL;

CREATE TABLE rm_leads (
    request_id             UNIQUEIDENTIFIER NOT NULL,
    institution_id         UNIQUEIDENTIFIER NOT NULL,
    investor_id            UNIQUEIDENTIFIER NOT NULL,
    investor_display_name  NVARCHAR(200)    NOT NULL,
    goal_type              NVARCHAR(30)     NOT NULL,
    goal_title             NVARCHAR(200)    NOT NULL,
    amount                 DECIMAL(18, 2)   NOT NULL,
    horizon_years          INT              NOT NULL,
    risk_label             NVARCHAR(40)     NOT NULL,
    ai_score               INT              NULL,
    status                 NVARCHAR(30)     NOT NULL,
    is_new                 BIT              NOT NULL,
    created_at             DATETIME2(3)     NOT NULL,
    updated_at             DATETIME2(3)     NOT NULL,
    CONSTRAINT PK_rm_leads PRIMARY KEY (request_id, institution_id)
);

CREATE INDEX IX_rm_leads_institution ON rm_leads (institution_id, status);

CREATE TABLE rm_agent_kpis (
    institution_id    UNIQUEIDENTIFIER NOT NULL PRIMARY KEY,
    evaluated_count   INT              NOT NULL,
    in_review_count   INT              NOT NULL,
    offer_sent_count  INT              NOT NULL,
    offers_sent       INT              NOT NULL,
    offers_accepted   INT              NOT NULL,
    avg_ai_score      DECIMAL(6, 1)    NULL,
    updated_at        DATETIME2(3)     NOT NULL
);

CREATE TABLE rm_agent_product_interest (
    product_id         UNIQUEIDENTIFIER NOT NULL PRIMARY KEY,
    institution_id     UNIQUEIDENTIFIER NOT NULL,
    recommended_count  INT              NOT NULL,
    offers_count       INT              NOT NULL,
    accepted_count     INT              NOT NULL
);

CREATE INDEX IX_rm_agent_product_interest_institution
    ON rm_agent_product_interest (institution_id);

CREATE TABLE rm_offers (
    offer_id        UNIQUEIDENTIFIER NOT NULL PRIMARY KEY,
    request_id      UNIQUEIDENTIFIER NOT NULL,
    investor_id     UNIQUEIDENTIFIER NOT NULL,
    agent_id        UNIQUEIDENTIFIER NOT NULL,
    institution_id  UNIQUEIDENTIFIER NOT NULL,
    items_json      NVARCHAR(MAX)    NOT NULL,
    message         NVARCHAR(MAX)    NOT NULL,
    status          NVARCHAR(20)     NOT NULL,
    created_at      DATETIME2(3)     NOT NULL,
    updated_at      DATETIME2(3)     NOT NULL
);

CREATE INDEX IX_rm_offers_investor ON rm_offers (investor_id, status);
CREATE INDEX IX_rm_offers_institution ON rm_offers (institution_id);

CREATE TABLE rm_notifications (
    notification_id  UNIQUEIDENTIFIER NOT NULL PRIMARY KEY,
    user_id          UNIQUEIDENTIFIER NOT NULL,
    title            NVARCHAR(200)    NOT NULL,
    body             NVARCHAR(1000)   NOT NULL,
    link             NVARCHAR(300)    NOT NULL,
    is_read          BIT              NOT NULL,
    created_at       DATETIME2(3)     NOT NULL
);

CREATE INDEX IX_rm_notifications_user ON rm_notifications (user_id, is_read);
