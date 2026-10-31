"""חיבור SQLAlchemy ל-MS SQL Server ב-Somee.com."""
from functools import lru_cache

from flask import current_app, g
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session


def engine_for(app) -> Engine:
    override = app.config.get("DB_ENGINE")
    if override is not None:
        return override
    return get_engine(app.config["DB_CONNECTION_STRING"])


def get_db() -> Session:
    db = g.get("db")
    if db is None:
        db = Session(engine_for(current_app))
        g.db = db
    return db


def close_db(_exc: BaseException | None = None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


@lru_cache(maxsize=4)
def get_engine(connection_string: str) -> Engine:
    if not connection_string:
        raise RuntimeError("פרטי מסד הנתונים (DB_SERVER, DB_USER, DB_PASSWORD) לא הוגדרו בקובץ .env")
    # Somee סוגר חיבורים שלא בשימוש. מחדשים חיבור אחרי 4 דקות כדי לא לקבל "TCP Provider 0x20"
    return create_engine(connection_string, pool_pre_ping=True, pool_recycle=240)
