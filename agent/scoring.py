"""ציון כללי ותמהיל. החישוב בקוד, לא במודל. ראו docs/09 §9.9."""

from decimal import ROUND_HALF_UP, Decimal

from agent.schema import CHANNELS

_BASE = {
    1: (25, 45, 70),
    2: (35, 50, 65),
    3: (50, 55, 60),
    4: (65, 60, 55),
    5: (80, 70, 45),
}


def propose_scores(risk_score: int, caps: dict[str, int], bonus_channel: str | None, bonus: int) -> dict[str, int]:
    triple = _BASE.get(risk_score, _BASE[3])
    scores = dict(zip(CHANNELS, triple, strict=True))
    if bonus_channel and caps.get(bonus_channel, 100) > 0:
        scores[bonus_channel] = min(100, scores[bonus_channel] + bonus)
    for channel, cap in caps.items():
        scores[channel] = min(scores[channel], cap)
    return scores


def allocation_weights(scores: dict[str, int], prefer: tuple[str, ...]) -> dict[str, int]:
    weights = {}
    for channel in CHANNELS:
        if scores.get(channel, 0) == 0:
            weights[channel] = 0
        elif channel in prefer:
            weights[channel] = scores[channel] + 15
        else:
            weights[channel] = scores[channel]
    return weights


def allocate(weights: dict[str, int], caps: dict[str, int]) -> dict[str, int]:
    capped = {channel: min(caps.get(channel, 100), 100) for channel in CHANNELS}
    usable = {channel: 0 if capped[channel] == 0 else max(weights.get(channel, 0), 0) for channel in CHANNELS}
    total = sum(usable.values())
    if total == 0:
        return _single_channel(capped)
    raw = {channel: (usable[channel] * 100) // total for channel in CHANNELS}
    _give_remainder(raw, capped, usable)
    _clamp(raw, capped)
    _give_remainder(raw, capped, usable)
    return raw


def overall_score(scores: dict[str, int], allocation: dict[str, int], flags: list[dict], penalty: int) -> int:
    weighted = sum(Decimal(scores[channel]) * Decimal(allocation[channel]) for channel in CHANNELS)
    average = weighted / Decimal(100)
    severe = sum(1 for flag in flags if flag.get("severity") == "high")
    value = average - (Decimal(penalty) * severe)
    rounded = int(value.quantize(Decimal(1), rounding=ROUND_HALF_UP))
    return max(0, min(100, rounded))


def _single_channel(capped: dict[str, int]) -> dict[str, int]:
    result = {channel: 0 for channel in CHANNELS}
    for channel in CHANNELS:
        if capped[channel] >= 100:
            result[channel] = 100
            return result
    for channel in CHANNELS:
        if capped[channel] > 0:
            result[channel] = capped[channel]
    return result


def _give_remainder(raw: dict[str, int], capped: dict[str, int], usable: dict[str, int]) -> None:
    order = sorted(CHANNELS, key=lambda channel: usable[channel], reverse=True)
    drift = 100 - sum(raw.values())
    for channel in order:
        if drift <= 0:
            return
        room = capped[channel] - raw[channel]
        if room <= 0:
            continue
        step = min(room, drift)
        raw[channel] += step
        drift -= step


def _clamp(raw: dict[str, int], capped: dict[str, int]) -> None:
    excess = 0
    for channel in CHANNELS:
        if raw[channel] > capped[channel]:
            excess += raw[channel] - capped[channel]
            raw[channel] = capped[channel]
    if excess == 0:
        return
    receivers = [channel for channel in CHANNELS if raw[channel] < capped[channel]]
    if not receivers:
        return
    share, remainder = divmod(excess, len(receivers))
    for index, channel in enumerate(receivers):
        room = capped[channel] - raw[channel]
        raw[channel] += min(room, share + (1 if index < remainder else 0))
