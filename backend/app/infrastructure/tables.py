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
    sa.UniqueConstraint("aggregate_id", "version", name="UQ_Aggregate_Version"),
)

sa.Index("IX_EventStore_Type", event_store.c.event_type, event_store.c.global_position)

processed_commands = sa.Table(
    "ProcessedCommands",
    metadata,
    sa.Column("command_id", sa.Uuid, primary_key=True),
    sa.Column("result_json", sa.UnicodeText),
    sa.Column("processed_at", sa.DateTime(timezone=False), nullable=False),
)
