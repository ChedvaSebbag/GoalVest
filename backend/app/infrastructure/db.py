"""חיבור SQLAlchemy ל-MS SQL Server ב-Somee.com."""
from functools import lru_cache

from sqlalchemy import Engine, create_engine


@lru_cache(maxsize=4)
def get_engine(connection_string: str) -> Engine:
    if not connection_string:
        raise RuntimeError("פרטי מסד הנתונים (DB_SERVER, DB_USER, DB_PASSWORD) לא הוגדרו בקובץ .env")
    return create_engine(connection_string, pool_pre_ping=True, pool_recycle=1800)
