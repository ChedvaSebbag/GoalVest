"""חיפוש Tavily לשרשרת. נשלחים רק מונחים ציבוריים."""

import requests

from agent.errors import InfrastructureError, as_infrastructure


def tavily_search(query: str, *, api_key: str, post=None) -> list[dict]:
    if not api_key:
        raise InfrastructureError("Tavily", "TAVILY_API_KEY חסר")
    sender = post or _post
    try:
        payload = sender(query, api_key)
    except InfrastructureError:
        raise
    except Exception as exc:
        infra = as_infrastructure(exc, "Tavily")
        raise infra or InfrastructureError("Tavily", str(exc)) from exc
    results = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(results, list):
        return []
    items = []
    for hit in results[:3]:
        if not isinstance(hit, dict):
            continue
        url = str(hit.get("url") or "")
        if not url.startswith(("http://", "https://")):
            continue
        items.append({
            "title": hit.get("title") or url,
            "url": url,
            "excerpt": (hit.get("content") or "")[:400],
        })
    return items


def _post(query: str, api_key: str) -> dict:
    response = requests.post(
        "https://api.tavily.com/search",
        json={"api_key": api_key, "query": query, "max_results": 3, "search_depth": "basic"},
        timeout=20,
    )
    if response.status_code >= 400:
        raise InfrastructureError("Tavily", f"HTTP {response.status_code}")
    return response.json()
