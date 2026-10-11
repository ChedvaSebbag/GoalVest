-- 001: Event Store (docs/07-data-model.md §7.2)
-- הרצה: להדביק בחלון ה-SQL של Somee (או ב-Azure Data Studio) ולהריץ פעם אחת.

CREATE TABLE EventStore (
    global_position  BIGINT IDENTITY(1,1) PRIMARY KEY,
    event_id         UNIQUEIDENTIFIER NOT NULL UNIQUE,
    aggregate_type   NVARCHAR(50)  NOT NULL,
    aggregate_id     UNIQUEIDENTIFIER NOT NULL,
    version          INT           NOT NULL,
    event_type       NVARCHAR(100) NOT NULL,
    schema_version   SMALLINT      NOT NULL DEFAULT 1,
    payload          NVARCHAR(MAX) NOT NULL,
    metadata         NVARCHAR(MAX) NOT NULL,
    occurred_at      DATETIME2(3)  NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_Aggregate_Version UNIQUE (aggregate_id, version),
    CONSTRAINT CK_Payload_Json CHECK (ISJSON(payload) = 1)
);
CREATE INDEX IX_EventStore_Type ON EventStore(event_type, global_position);

CREATE TABLE ProcessedCommands (
    command_id   UNIQUEIDENTIFIER PRIMARY KEY,
    result_json  NVARCHAR(MAX),
    processed_at DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME()
);

CREATE TABLE ConsumerCheckpoints (
    consumer_name  NVARCHAR(50) PRIMARY KEY,
    last_position  BIGINT NOT NULL
);
