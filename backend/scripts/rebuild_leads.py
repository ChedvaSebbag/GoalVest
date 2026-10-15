"""בונה לידים ומדדי סוכן מההערכות שכבר נשמרו. לא נוגע ב-Event Store.

הרצה (מתוך backend):
    python -m scripts.rebuild_leads
"""

from sqlalchemy.orm import Session

from app.config import Config
from app.infrastructure.db import get_engine
from app.projections.leads import rebuild_agent_views


def main() -> None:
    engine = get_engine(Config.DB_CONNECTION_STRING)
    with Session(engine) as session:
        count = rebuild_agent_views(session)
        session.commit()
    print(f"נבנו {count} שורות ליד")


if __name__ == "__main__":
    main()
