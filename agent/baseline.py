"""הערכה דטרמיניסטית מהראיות, כשהסינתזה של המודל לא בפורמט תקין."""

from uuid import UUID

from agent.schema import (
    Allocation,
    ChannelScores,
    ModelAssessment,
    RecommendedProduct,
    RiskFlag,
    Source,
)
from agent.scoring import allocate, allocation_weights, propose_scores
from agent.suitability import Suitability


def build_baseline(
    suitability: Suitability,
    products: list[dict],
    rag: list[dict],
    web: list[dict],
    bonus: int,
) -> ModelAssessment:
    scores = propose_scores(suitability.risk_score, suitability.score_caps, suitability.bonus_channel, bonus)
    weights = allocation_weights(scores, suitability.prefer)
    caps = {**{channel: 100 for channel in scores}, **suitability.allocation_caps}
    for channel, cap in suitability.score_caps.items():
        if cap == 0:
            caps[channel] = 0
    split = allocate(weights, caps)
    chosen = _products(products, scores)
    sources = _sources(rag, web)
    flags = [RiskFlag.model_validate(flag) for flag in suitability.flags]
    return ModelAssessment(
        channel_scores=ChannelScores.model_validate(scores),
        allocation=Allocation.model_validate(split),
        recommended_products=chosen,
        rationale=_rationale(suitability, split),
        risk_flags=flags,
        sources=sources,
    )


def _products(products: list[dict], scores: dict[str, int]) -> list[RecommendedProduct]:
    ranked = [item for item in products if scores.get(item["channel"], 0) > 0]
    ranked.sort(key=lambda item: scores[item["channel"]], reverse=True)
    chosen: list[RecommendedProduct] = []
    seen: set[str] = set()
    for item in ranked:
        channel = item["channel"]
        if channel in seen:
            continue
        seen.add(channel)
        track = item.get("track") or item.get("name")
        institution = item.get("institution_name") or ""
        reason = f"מתאים יותר למסלול {track} של {institution}. כדאי לשקול אותו לפי רמת הסיכון של המסלול."
        chosen.append(RecommendedProduct(
            product_id=UUID(str(item["product_id"])),
            fit_score=scores[channel],
            reason=reason[:300],
        ))
        if len(chosen) == 3:
            break
    if not chosen:
        raise ValueError("אין מוצר מועמד שעומד בחוקים")
    return chosen


def _sources(rag: list[dict], web: list[dict]) -> list[Source]:
    sources: list[Source] = []
    for hit in rag:
        title = hit.get("title") or "מסמך מהמאגר"
        excerpt = (hit.get("excerpt") or "")[:400] or None
        document_id = _uuid(hit.get("document_id"))
        sources.append(Source(type="rag", title=str(title)[:200], document_id=document_id, excerpt=excerpt))
        break
    for hit in web:
        url = str(hit.get("url") or "")
        if not url.startswith(("http://", "https://")):
            continue
        excerpt = (hit.get("excerpt") or "")[:400] or None
        sources.append(Source(type="web", title=str(hit.get("title") or url)[:200], url=url, excerpt=excerpt))
        break
    if len(sources) < 2:
        raise ValueError("חסר מקור מהמאגר או מהרשת")
    return sources


def _rationale(suitability: Suitability, split: dict[str, int]) -> str:
    mix = (
        f"שוק ההון {split['capital_market']} אחוז, "
        f"קרן השתלמות {split['hishtalmut']} אחוז, "
        f"וגמל או פוליסה {split['gemel_policy']} אחוז"
    )
    parts = [
        "ההערכה נשענת על טווח היעד, על פרופיל הסיכון ועל מקורות מהמאגר ומהרשת.",
        f"כדאי לשקול תמהיל שבו {mix}.",
        "הניסוח מתאר התאמה אפשרית בלבד, ואפשר לבחון אותו מול סוכן מורשה.",
    ]
    parts.extend(flag["text"] for flag in suitability.flags)
    text = " ".join(parts)
    filler = " כדאי לשקול את ההתאמה לפי המקורות שנאספו, בלי לראות בכך הוראה לפעולה."
    while len(text) < 200:
        text += filler
    return text[:3000]


def _uuid(value: object) -> UUID | None:
    if not value:
        return None
    try:
        return UUID(str(value))
    except ValueError:
        return None
