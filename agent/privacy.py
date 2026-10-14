"""שאילתות חיצוניות בלי פרטים מזהים או סכומים. ראו docs/09 §9.10."""

from decimal import Decimal


def market_queries(products: list[dict]) -> list[str]:
    queries = ["ריבית בנק ישראל", "מגמות מדדי מניות"]
    for product in products[:4]:
        institution = str(product.get("institution_name") or "").strip()
        track = str(product.get("track") or product.get("name") or "").strip()
        text = " ".join(part for part in (institution, track) if part)
        if text:
            queries.append(text)
    return queries


def sensitive_terms(snapshot: dict) -> list[str]:
    goal = snapshot.get("goal") or {}
    terms: list[str] = []
    for key in ("initial_amount", "monthly_deposit", "target_amount"):
        raw = goal.get(key)
        if raw is None:
            continue
        text = str(raw)
        terms.append(text)
        if isinstance(raw, Decimal):
            terms.append(format(raw.quantize(Decimal(1)), "f"))
    answers = (snapshot.get("risk") or {}).get("answers") or {}
    for key in ("email", "phone", "full_name"):
        if answers.get(key):
            terms.append(str(answers[key]))
    return [term for term in terms if term and term not in {"0", "0.00"}]


def assert_public(query: str, banned: list[str]) -> None:
    for term in banned:
        if term and term in query:
            raise ValueError("שאילתה חיצונית כוללת פרט אישי או סכום")
