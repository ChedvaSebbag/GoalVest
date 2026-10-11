"""בדיקות תקינות לרכיבי התשתית. כל בדיקה מחזירה dict עם status ו-detail ולא זורקת חריגה."""
import requests
from sqlalchemy import text

from .db import get_engine


def _ok(detail: str) -> dict:
    return {"status": "ok", "detail": detail}


def _error(detail: str) -> dict:
    return {"status": "error", "detail": detail}


def check_database(connection_string: str) -> dict:
    try:
        with get_engine(connection_string).connect() as conn:
            version = conn.execute(text("SELECT @@VERSION")).scalar() or ""
        return _ok(version.splitlines()[0][:80])
    except Exception as exc:  # noqa: BLE001 – health check must never crash
        return _error(f"{type(exc).__name__}: {str(exc)[:160]}")


def check_ollama(base_url: str, required_models: list[str], timeout: float) -> dict:
    try:
        resp = requests.get(f"{base_url}/api/tags", timeout=timeout)
        resp.raise_for_status()
        installed = {m["name"] for m in resp.json().get("models", [])}
        missing = [m for m in required_models if not any(i == m or i.startswith(m + ":") for i in installed)]
        if missing:
            return _error(f"Ollama רץ, חסרים מודלים: {', '.join(missing)} (הריצי ollama pull)")
        return _ok(f"מודלים: {', '.join(sorted(installed))}")
    except Exception as exc:  # noqa: BLE001
        return _error(f"אין חיבור ל-Ollama ב-{base_url}: {type(exc).__name__}")


def check_chroma(chroma_url: str, timeout: float) -> dict:
    for path in ("/api/v2/heartbeat", "/api/v1/heartbeat"):
        try:
            resp = requests.get(f"{chroma_url}{path}", timeout=timeout)
            if resp.ok:
                return _ok(f"ChromaDB מגיב ({path})")
        except Exception:  # noqa: BLE001, S112 – ננסה את הנתיב הבא
            continue
    return _error(f"אין חיבור ל-ChromaDB ב-{chroma_url}")
