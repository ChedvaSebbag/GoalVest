"""Controller: GET /api/health – בודק את כל רכיבי התשתית (docs/08 §8.6)."""
from flask import Blueprint, current_app, jsonify

from ..infrastructure.health_checks import check_chroma, check_database, check_ollama

health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def health():
    cfg = current_app.config
    timeout = cfg["HEALTH_TIMEOUT_SECONDS"]
    checks = {
        "database": check_database(cfg["DB_CONNECTION_STRING"]),
        "ollama": check_ollama(cfg["OLLAMA_BASE_URL"], [cfg["OLLAMA_CHAT_MODEL"], cfg["OLLAMA_EMBED_MODEL"]], timeout),
        "chroma": check_chroma(cfg["CHROMA_URL"], timeout),
    }
    healthy = all(c["status"] == "ok" for c in checks.values())
    return jsonify({"status": "ok" if healthy else "error", "checks": checks}), 200 if healthy else 503
