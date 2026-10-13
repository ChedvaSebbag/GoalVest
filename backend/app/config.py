"""הגדרות מתוך משתני סביבה (.env בשורש ה-Repo). אין סודות בקוד."""
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine import URL

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def _build_db_url() -> str:
    """בונה מחרוזת חיבור מ-4 שדות נפרדים ב-.env (מטפל אוטומטית בתווים מיוחדים בסיסמה).
    אם הוגדר DB_CONNECTION_STRING מלא – הוא קודם."""
    if os.getenv("DB_CONNECTION_STRING"):
        return os.environ["DB_CONNECTION_STRING"]
    server = os.getenv("DB_SERVER", "")
    if not server:
        return ""
    url = URL.create(
        "mssql+pyodbc",
        username=os.getenv("DB_USER", ""),
        password=os.getenv("DB_PASSWORD", ""),
        host=server,
        database=os.getenv("DB_NAME", ""),
        query={"driver": "ODBC Driver 18 for SQL Server", "TrustServerCertificate": "yes"},
    )
    return url.render_as_string(hide_password=False)


class Config:
    DB_CONNECTION_STRING = _build_db_url()
    FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:4200")
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_CHAT_MODEL = os.getenv("OLLAMA_CHAT_MODEL", "qwen2.5:7b-instruct")
    OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "bge-m3")
    CHROMA_URL = f"http://{os.getenv('CHROMA_HOST', 'localhost')}:{os.getenv('CHROMA_PORT', '8000')}"
    HEALTH_TIMEOUT_SECONDS = float(os.getenv("HEALTH_TIMEOUT_SECONDS", "3"))
