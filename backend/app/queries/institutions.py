"""רשימת הגופים ל-Autocomplete. אין כאן קריאה ל-Aggregate."""

from app.reference.institutions import INSTITUTIONS


def list_institutions() -> list[dict[str, str]]:
    return [{"id": str(item.id), "name": item.name} for item in INSTITUTIONS]
