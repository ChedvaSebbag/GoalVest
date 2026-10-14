-- 005: הערכת AI – retry_at על הבקשה וטבלת rm_assessments (docs/07 §7.4)
-- הרצה: להדביק בחלון ה-SQL של Somee ולהריץ פעם אחת, אחרי 004.

ALTER TABLE rm_requests ADD retry_at DATETIME2(3) NULL;

CREATE TABLE rm_assessments (
    request_id   UNIQUEIDENTIFIER NOT NULL,
    attempt      INT              NOT NULL,
    assessment   NVARCHAR(MAX)    NOT NULL,
    created_at   DATETIME2(3)     NOT NULL,
    CONSTRAINT PK_rm_assessments PRIMARY KEY (request_id, attempt)
);
