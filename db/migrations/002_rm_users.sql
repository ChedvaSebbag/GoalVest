-- 002: rm_users ו-RevokedTokens (docs/07 §7.4, docs/12 §12.1)
-- הרצה: להדביק בחלון ה-SQL של Somee ולהריץ פעם אחת, אחרי 001.

CREATE TABLE rm_users (
    user_id         UNIQUEIDENTIFIER NOT NULL PRIMARY KEY,
    email           NVARCHAR(320)    NOT NULL,
    full_name       NVARCHAR(200)    NOT NULL,
    phone           NVARCHAR(30)     NOT NULL,
    role            NVARCHAR(20)     NOT NULL,
    institution_id  UNIQUEIDENTIFIER NULL,
    status          NVARCHAR(20)     NOT NULL,
    password_hash   NVARCHAR(200)    NOT NULL,
    CONSTRAINT UQ_rm_users_email UNIQUE (email)
);

-- טבלת תפעול לפסילת Refresh Token. אינה Read Model ואינה נגזרת מאירוע.
CREATE TABLE RevokedTokens (
    jti         UNIQUEIDENTIFIER NOT NULL PRIMARY KEY,
    expires_at  DATETIME2(3)     NOT NULL,
    revoked_at  DATETIME2(3)     NOT NULL DEFAULT SYSUTCDATETIME()
);
