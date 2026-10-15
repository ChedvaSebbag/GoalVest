"""טבלאות EventStore ו-ProcessedCommands כהגדרת SQLAlchemy ניידת.

שמות הטבלאות והעמודות זהים ל-db/migrations/001_event_store.sql.
אילוץ ISJSON נשאר במיגרציית SQL Server; כאן הסוגים ניידים כדי ש-create_all ירוץ גם על SQLite.
"""

import sqlalchemy as sa

metadata = sa.MetaData()

event_store = sa.Table(
    "EventStore",
    metadata,
    sa.Column(
        "global_position",
        sa.BigInteger().with_variant(sa.Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    ),
    sa.Column("event_id", sa.Uuid, nullable=False, unique=True),
    sa.Column("aggregate_type", sa.Unicode(50), nullable=False),
    sa.Column("aggregate_id", sa.Uuid, nullable=False),
    sa.Column("version", sa.Integer, nullable=False),
    sa.Column("event_type", sa.Unicode(100), nullable=False),
    sa.Column("schema_version", sa.SmallInteger, nullable=False),
    sa.Column("payload", sa.UnicodeText, nullable=False),
    sa.Column("metadata", sa.UnicodeText, nullable=False),
    sa.Column("occurred_at", sa.DateTime(timezone=False), nullable=False),
    sa.UniqueConstraint("aggregate_type", "aggregate_id", "version", name="UQ_Aggregate_Version"),
)

sa.Index("IX_EventStore_Type", event_store.c.event_type, event_store.c.global_position)

consumer_checkpoints = sa.Table(
    "ConsumerCheckpoints",
    metadata,
    sa.Column("consumer_name", sa.Unicode(50), primary_key=True),
    sa.Column("last_position", sa.BigInteger().with_variant(sa.Integer, "sqlite"), nullable=False),
)

processed_commands = sa.Table(
    "ProcessedCommands",
    metadata,
    sa.Column("command_id", sa.Uuid, primary_key=True),
    sa.Column("result_json", sa.UnicodeText),
    sa.Column("processed_at", sa.DateTime(timezone=False), nullable=False),
)

rm_users = sa.Table(
    "rm_users",
    metadata,
    sa.Column("user_id", sa.Uuid, primary_key=True),
    sa.Column("email", sa.Unicode(320), nullable=False),
    sa.Column("full_name", sa.Unicode(200), nullable=False),
    sa.Column("phone", sa.Unicode(30), nullable=False),
    sa.Column("role", sa.Unicode(20), nullable=False),
    sa.Column("institution_id", sa.Uuid, nullable=True),
    sa.Column("status", sa.Unicode(20), nullable=False),
    sa.Column("password_hash", sa.Unicode(200), nullable=False),
    sa.UniqueConstraint("email", name="UQ_rm_users_email"),
)

revoked_tokens = sa.Table(
    "RevokedTokens",
    metadata,
    sa.Column("jti", sa.Uuid, primary_key=True),
    sa.Column("expires_at", sa.DateTime(timezone=False), nullable=False),
    sa.Column("revoked_at", sa.DateTime(timezone=False), nullable=False),
)

rm_investor_profiles = sa.Table(
    "rm_investor_profiles",
    metadata,
    sa.Column("user_id", sa.Uuid, primary_key=True),
    sa.Column("birth_year", sa.Integer),
    sa.Column("marital_status", sa.Unicode(30)),
    sa.Column("monthly_income_range", sa.Unicode(40)),
    sa.Column("has_emergency_fund", sa.Boolean),
    sa.Column("existing_products", sa.UnicodeText),
    sa.Column("risk_score", sa.SmallInteger),
    sa.Column("risk_label", sa.Unicode(40)),
    sa.Column("answers", sa.UnicodeText),
    sa.Column("assessed_at", sa.DateTime(timezone=False)),
)

rm_goals = sa.Table(
    "rm_goals",
    metadata,
    sa.Column("goal_id", sa.Uuid, primary_key=True),
    sa.Column("investor_id", sa.Uuid, nullable=False),
    sa.Column("type", sa.Unicode(30), nullable=False),
    sa.Column("title", sa.Unicode(200), nullable=False),
    sa.Column("initial_amount", sa.Numeric(18, 2), nullable=False),
    sa.Column("monthly_deposit", sa.Numeric(18, 2), nullable=False),
    sa.Column("target_amount", sa.Numeric(18, 2), nullable=False),
    sa.Column("target_date", sa.Date, nullable=False),
    sa.Column("flexibility", sa.Unicode(30), nullable=False),
    sa.Column("liquidity_need", sa.Unicode(30), nullable=False),
    sa.Column("excluded_channels", sa.UnicodeText, nullable=False),
    sa.Column("preferred_channels", sa.UnicodeText, nullable=False),
    sa.Column("preferred_institutions", sa.UnicodeText, nullable=False),
    sa.Column("active_request_id", sa.Uuid),
    sa.Column("status", sa.Unicode(20), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=False), nullable=False),
)

sa.Index("IX_rm_goals_investor", rm_goals.c.investor_id)

rm_requests = sa.Table(
    "rm_requests",
    metadata,
    sa.Column("request_id", sa.Uuid, primary_key=True),
    sa.Column("goal_id", sa.Uuid, nullable=False),
    sa.Column("investor_id", sa.Uuid, nullable=False),
    sa.Column("status", sa.Unicode(30), nullable=False),
    sa.Column("consent_share_contact", sa.Boolean, nullable=False),
    sa.Column("snapshot", sa.UnicodeText, nullable=False),
    sa.Column("overall_score", sa.Integer),
    sa.Column("claimed_by", sa.Uuid),
    sa.Column("institution_id", sa.Uuid),
    sa.Column("assessment_review", sa.Unicode(20)),
    sa.Column("assessment_note", sa.Unicode(500)),
    sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=False), nullable=False),
    sa.Column("retry_at", sa.DateTime(timezone=False)),
)

sa.Index("IX_rm_requests_goal", rm_requests.c.goal_id)

rm_leads = sa.Table(
    "rm_leads",
    metadata,
    sa.Column("request_id", sa.Uuid, primary_key=True),
    sa.Column("institution_id", sa.Uuid, primary_key=True),
    sa.Column("investor_id", sa.Uuid, nullable=False),
    sa.Column("investor_display_name", sa.Unicode(200), nullable=False),
    sa.Column("goal_type", sa.Unicode(30), nullable=False),
    sa.Column("goal_title", sa.Unicode(200), nullable=False),
    sa.Column("amount", sa.Numeric(18, 2), nullable=False),
    sa.Column("horizon_years", sa.Integer, nullable=False),
    sa.Column("risk_label", sa.Unicode(40), nullable=False),
    sa.Column("ai_score", sa.Integer),
    sa.Column("status", sa.Unicode(30), nullable=False),
    sa.Column("is_new", sa.Boolean, nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=False), nullable=False),
)

sa.Index("IX_rm_leads_institution", rm_leads.c.institution_id, rm_leads.c.status)

rm_agent_kpis = sa.Table(
    "rm_agent_kpis",
    metadata,
    sa.Column("institution_id", sa.Uuid, primary_key=True),
    sa.Column("evaluated_count", sa.Integer, nullable=False),
    sa.Column("in_review_count", sa.Integer, nullable=False),
    sa.Column("offer_sent_count", sa.Integer, nullable=False),
    sa.Column("offers_sent", sa.Integer, nullable=False),
    sa.Column("offers_accepted", sa.Integer, nullable=False),
    sa.Column("avg_ai_score", sa.Numeric(6, 1)),
    sa.Column("updated_at", sa.DateTime(timezone=False), nullable=False),
)

rm_agent_product_interest = sa.Table(
    "rm_agent_product_interest",
    metadata,
    sa.Column("product_id", sa.Uuid, primary_key=True),
    sa.Column("institution_id", sa.Uuid, nullable=False),
    sa.Column("recommended_count", sa.Integer, nullable=False),
    sa.Column("offers_count", sa.Integer, nullable=False),
    sa.Column("accepted_count", sa.Integer, nullable=False),
)

sa.Index("IX_rm_agent_product_interest_institution", rm_agent_product_interest.c.institution_id)

rm_offers = sa.Table(
    "rm_offers",
    metadata,
    sa.Column("offer_id", sa.Uuid, primary_key=True),
    sa.Column("request_id", sa.Uuid, nullable=False),
    sa.Column("investor_id", sa.Uuid, nullable=False),
    sa.Column("agent_id", sa.Uuid, nullable=False),
    sa.Column("institution_id", sa.Uuid, nullable=False),
    sa.Column("items_json", sa.UnicodeText, nullable=False),
    sa.Column("message", sa.UnicodeText, nullable=False),
    sa.Column("status", sa.Unicode(20), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=False), nullable=False),
)

sa.Index("IX_rm_offers_investor", rm_offers.c.investor_id, rm_offers.c.status)
sa.Index("IX_rm_offers_institution", rm_offers.c.institution_id)

rm_notifications = sa.Table(
    "rm_notifications",
    metadata,
    sa.Column("notification_id", sa.Uuid, primary_key=True),
    sa.Column("user_id", sa.Uuid, nullable=False),
    sa.Column("title", sa.Unicode(200), nullable=False),
    sa.Column("body", sa.Unicode(1000), nullable=False),
    sa.Column("link", sa.Unicode(300), nullable=False),
    sa.Column("is_read", sa.Boolean, nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
)

sa.Index("IX_rm_notifications_user", rm_notifications.c.user_id, rm_notifications.c.is_read)

rm_assessments = sa.Table(
    "rm_assessments",
    metadata,
    sa.Column("request_id", sa.Uuid, primary_key=True),
    sa.Column("attempt", sa.Integer, primary_key=True),
    sa.Column("assessment", sa.UnicodeText, nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
)

rm_products = sa.Table(
    "rm_products",
    metadata,
    sa.Column("product_id", sa.Uuid, primary_key=True),
    sa.Column("type", sa.Unicode(30), nullable=False),
    sa.Column("name", sa.Unicode(120), nullable=False),
    sa.Column("institution_id", sa.Uuid, nullable=False),
    sa.Column("institution_name", sa.Unicode(200), nullable=False),
    sa.Column("track", sa.Unicode(120), nullable=False),
    sa.Column("symbol", sa.Unicode(20)),
    sa.Column("fee_deposit", sa.Numeric(18, 2), nullable=False),
    sa.Column("fee_assets", sa.Numeric(18, 2), nullable=False),
    sa.Column("return_1y", sa.Numeric(18, 2), nullable=False),
    sa.Column("return_3y", sa.Numeric(18, 2), nullable=False),
    sa.Column("return_5y", sa.Numeric(18, 2), nullable=False),
    sa.Column("std_dev", sa.Numeric(18, 2), nullable=False),
    sa.Column("risk_level", sa.SmallInteger, nullable=False),
    sa.Column("liquidity", sa.Unicode(30), nullable=False),
    sa.Column("liquidity_terms", sa.Unicode(500), nullable=False),
    sa.Column("tax_notes", sa.Unicode(500), nullable=False),
    sa.Column("min_deposit", sa.Numeric(18, 2), nullable=False),
    sa.Column("description", sa.UnicodeText, nullable=False),
    sa.Column("is_active", sa.Boolean, nullable=False),
    sa.Column("search_text", sa.UnicodeText, nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=False), nullable=False),
)

sa.Index("IX_rm_products_institution", rm_products.c.institution_id)

rm_product_documents = sa.Table(
    "rm_product_documents",
    metadata,
    sa.Column("document_id", sa.Uuid, primary_key=True),
    sa.Column("product_id", sa.Uuid, nullable=False),
    sa.Column("file_name", sa.Unicode(200), nullable=False),
    sa.Column("stored_name", sa.Unicode(80), nullable=False),
    sa.Column("doc_type", sa.Unicode(40), nullable=False),
    sa.Column("storage_path", sa.Unicode(80), nullable=False),
    sa.Column("sha256", sa.Unicode(64), nullable=False),
    sa.Column("size_bytes", sa.Integer, nullable=False),
    sa.Column("index_status", sa.Unicode(20), nullable=False),
    sa.Column("chunks_count", sa.Integer),
    sa.Column("uploaded_at", sa.DateTime(timezone=False), nullable=False),
)

sa.Index("IX_rm_product_documents_product", rm_product_documents.c.product_id)

rm_request_timeline = sa.Table(
    "rm_request_timeline",
    metadata,
    sa.Column("request_id", sa.Uuid, primary_key=True),
    sa.Column("global_position", sa.BigInteger, primary_key=True),
    sa.Column("event_type", sa.Unicode(100), nullable=False),
    sa.Column("actor", sa.Unicode(100), nullable=False),
    sa.Column("display_text", sa.Unicode(300), nullable=False),
    sa.Column("occurred_at", sa.DateTime(timezone=False), nullable=False),
)
