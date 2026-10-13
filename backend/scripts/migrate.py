"""מריץ את קובצי ה-SQL שב-db/migrations על מסד הנתונים שב-.env (Somee).

הרצה (מתוך תיקיית backend, עם .venv פעיל):
    python -m scripts.migrate

כל קובץ רץ פעם אחת בלבד – הרשימה נשמרת בטבלה SchemaMigrations.
"""
from pathlib import Path

from sqlalchemy import text

from app.config import Config
from app.infrastructure.db import get_engine

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "db" / "migrations"


def main() -> None:
    engine = get_engine(Config.DB_CONNECTION_STRING)
    with engine.begin() as conn:
        conn.execute(text(
            "IF OBJECT_ID('SchemaMigrations') IS NULL "
            "CREATE TABLE SchemaMigrations (name NVARCHAR(200) PRIMARY KEY, "
            "applied_at DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME())"
        ))
        applied = {row[0] for row in conn.execute(text("SELECT name FROM SchemaMigrations"))}

    files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    for f in files:
        if f.name in applied:
            print(f"✓ כבר הורץ: {f.name}")
            continue
        sql = f.read_text(encoding="utf-8")
        with engine.begin() as conn:      # כל קובץ בטרנזקציה נפרדת
            conn.exec_driver_sql(sql)
            conn.execute(text("INSERT INTO SchemaMigrations(name) VALUES (:n)"), {"n": f.name})
        print(f"✔ הורץ בהצלחה: {f.name}")

    print("סיום. טבלאות קיימות:")
    with engine.connect() as conn:
        for (name,) in conn.execute(text("SELECT name FROM sys.tables ORDER BY name")):
            print(f"  - {name}")


if __name__ == "__main__":
    main()
