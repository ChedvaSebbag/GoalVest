-- 003: פרופיל משקיע, יעדים, בקשות וציר זמן (docs/07 §7.4)
-- וגם הרחבת UQ_Aggregate_Version כך ש-UserAccount ו-InvestorProfile חולקים user_id.
-- הרצה: להדביק בחלון ה-SQL של Somee ולהריץ פעם אחת, אחרי 002.

ALTER TABLE EventStore DROP CONSTRAINT UQ_Aggregate_Version;
ALTER TABLE EventStore ADD CONSTRAINT UQ_Aggregate_Version
    UNIQUE (aggregate_type, aggregate_id, version);

CREATE TABLE rm_investor_profiles (
    user_id               UNIQUEIDENTIFIER NOT NULL PRIMARY KEY,
    birth_year            INT              NULL,
    marital_status        NVARCHAR(30)     NULL,
    monthly_income_range  NVARCHAR(40)     NULL,
    has_emergency_fund    BIT              NULL,
    existing_products     NVARCHAR(MAX)    NULL,
    risk_score            SMALLINT         NULL,
    risk_label            NVARCHAR(40)     NULL,
    answers               NVARCHAR(MAX)    NULL,
    assessed_at           DATETIME2(3)     NULL
);

CREATE TABLE rm_goals (
    goal_id                  UNIQUEIDENTIFIER NOT NULL PRIMARY KEY,
    investor_id              UNIQUEIDENTIFIER NOT NULL,
    type                     NVARCHAR(30)     NOT NULL,
    title                    NVARCHAR(200)    NOT NULL,
    initial_amount           DECIMAL(18, 2)   NOT NULL,
    monthly_deposit          DECIMAL(18, 2)   NOT NULL,
    target_amount            DECIMAL(18, 2)   NOT NULL,
    target_date              DATE             NOT NULL,
    flexibility              NVARCHAR(30)     NOT NULL,
    liquidity_need           NVARCHAR(30)     NOT NULL,
    excluded_channels        NVARCHAR(MAX)    NOT NULL,
    preferred_channels       NVARCHAR(MAX)    NOT NULL,
    preferred_institutions   NVARCHAR(MAX)    NOT NULL,
    active_request_id        UNIQUEIDENTIFIER NULL,
    status                   NVARCHAR(20)     NOT NULL,
    updated_at               DATETIME2(3)     NOT NULL
);
CREATE INDEX IX_rm_goals_investor ON rm_goals(investor_id);

CREATE TABLE rm_requests (
    request_id              UNIQUEIDENTIFIER NOT NULL PRIMARY KEY,
    goal_id                 UNIQUEIDENTIFIER NOT NULL,
    investor_id             UNIQUEIDENTIFIER NOT NULL,
    status                  NVARCHAR(30)     NOT NULL,
    consent_share_contact   BIT              NOT NULL,
    snapshot                NVARCHAR(MAX)    NOT NULL,
    overall_score           INT              NULL,
    claimed_by              UNIQUEIDENTIFIER NULL,
    institution_id          UNIQUEIDENTIFIER NULL,
    assessment_review       NVARCHAR(20)     NULL,
    created_at              DATETIME2(3)     NOT NULL,
    updated_at              DATETIME2(3)     NOT NULL
);
CREATE INDEX IX_rm_requests_goal ON rm_requests(goal_id);

CREATE TABLE rm_request_timeline (
    request_id       UNIQUEIDENTIFIER NOT NULL,
    global_position  BIGINT           NOT NULL,
    event_type       NVARCHAR(100)    NOT NULL,
    actor            NVARCHAR(100)    NOT NULL,
    display_text     NVARCHAR(300)    NOT NULL,
    occurred_at      DATETIME2(3)     NOT NULL,
    CONSTRAINT PK_rm_request_timeline PRIMARY KEY (request_id, global_position)
);
