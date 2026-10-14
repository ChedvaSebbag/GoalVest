"""פיצול טקסט ל-chunks של 800 תווים עם חפיפה של 120. ראו docs/10 §10.2."""

import re

_SIZE = 800
_OVERLAP = 120
_SEPARATORS = ("\n# ", "\n## ", "\n\n", "\n", ". ", " ")


def clean_text(text: str) -> str:
    cleaned = text.replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n")
    cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def split_text(text: str, size: int = _SIZE, overlap: int = _OVERLAP) -> list[str]:
    cleaned = clean_text(text)
    if not cleaned:
        return []
    if overlap < 0 or overlap >= size:
        raise ValueError("חפיפה לא תקינה")
    chunks: list[str] = []
    start = 0
    length = len(cleaned)
    while start < length:
        end = min(start + size, length)
        if end < length:
            end = _prefer_break(cleaned, start, end)
        piece = cleaned[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= length:
            break
        next_start = max(start + 1, end - overlap)
        start = next_start
    return chunks


def _prefer_break(text: str, start: int, end: int) -> int:
    window = text[start:end]
    minimum = max(1, len(window) // 4)
    for separator in _SEPARATORS:
        position = window.rfind(separator)
        if position >= minimum:
            return start + position
    return end
