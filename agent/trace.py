"""הדפסת שלבי ההערכה להדגמה."""

import json


def print_step(step: str, data: object) -> None:
    titles = {
        "rules": "שלב 1 – חוקי התאמה",
        "rag": "שלב 2 – מקורות RAG",
        "products": "שלב 3 – מוצרים מועמדים",
        "tools": "שלב 4 – תוצאות כלים",
        "web": "שלב 5 – Tavily",
        "result": "תוצאה",
    }
    print(f"\n{titles.get(step, step)}")
    print(_render(data))


def print_summary(status: str, duration_ms: int) -> None:
    print(f"\nסטטוס: {status}")
    print(f"זמן ריצה: {duration_ms} ms")


def _render(data: object) -> str:
    if isinstance(data, (dict, list)):
        return json.dumps(data, ensure_ascii=False, indent=2, default=str)
    return str(data)
