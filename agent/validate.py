"""בדיקה שהפלט לא סותר את שלב 1 ושהמוצרים והמקורות אמיתיים."""

from agent.schema import BANNED_PHRASES, CHANNELS, DISCLAIMER, ModelAssessment
from agent.scoring import overall_score
from agent.suitability import Suitability


def problems(output: ModelAssessment, suitability: Suitability, candidate_ids: set[str]) -> list[str]:
    errors: list[str] = []
    scores = output.channel_scores.model_dump()
    allocation = output.allocation.model_dump()
    for channel in CHANNELS:
        cap = suitability.score_caps.get(channel)
        if cap is not None and scores[channel] > cap:
            errors.append(f"ציון {channel} גבוה מהתקרה {cap}")
        share_cap = suitability.allocation_caps.get(channel)
        if share_cap is not None and allocation[channel] > share_cap:
            errors.append(f"אחוז {channel} גבוה מהתקרה {share_cap}")
    if sum(allocation.values()) != 100:
        errors.append("סכום התמהיל אינו 100")
    for product in output.recommended_products:
        if str(product.product_id) not in candidate_ids:
            errors.append("מוצר שאינו ברשימת המועמדים")
    if not any(source.type == "rag" for source in output.sources):
        errors.append("חסר מקור rag")
    if not any(source.type == "web" and source.url for source in output.sources):
        errors.append("חסר מקור web")
    for phrase in BANNED_PHRASES:
        if phrase in output.rationale:
            errors.append("הנימוק כולל ניסוח אסור")
    return errors


def finalize(output: ModelAssessment, suitability: Suitability, *, model: str, duration_ms: int) -> dict:
    flags = _merge_flags(output, suitability)
    scores = output.channel_scores.model_dump()
    allocation = output.allocation.model_dump()
    return {
        "overall_score": overall_score(scores, allocation, flags, suitability.penalty),
        "channel_scores": scores,
        "allocation": allocation,
        "recommended_products": [item.model_dump(mode="json") for item in output.recommended_products],
        "rationale": output.rationale,
        "risk_flags": flags,
        "sources": [item.model_dump(mode="json") for item in output.sources],
        "disclaimer": DISCLAIMER,
        "model": model,
        "duration_ms": duration_ms,
    }


def _merge_flags(output: ModelAssessment, suitability: Suitability) -> list[dict]:
    merged = [dict(flag) for flag in suitability.flags]
    known = {flag["code"] for flag in merged}
    for flag in output.risk_flags:
        if flag.code in known:
            continue
        merged.append({"code": flag.code, "severity": flag.severity, "text": flag.text})
        known.add(flag.code)
    return merged
