"""שמירת קובץ מסמך בשם UUID, מחוץ לתיקיית הקוד."""

import re
from pathlib import Path

from goalvest_core import BusinessRuleViolation

_STORED = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\.(pdf|docx)$")


def write_stored(directory: Path, stored_name: str, content: bytes) -> None:
    target = _resolve(directory, stored_name)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)


def resolve_stored(directory: Path, stored_name: str) -> Path:
    return _resolve(directory, stored_name)


def _resolve(directory: Path, stored_name: str) -> Path:
    if not _STORED.match(stored_name):
        _reject()
    root = directory.resolve()
    target = (root / stored_name).resolve()
    if target.parent != root:
        _reject()
    return target


def _reject() -> None:
    raise BusinessRuleViolation("שם הקובץ אינו תקין", code="INVALID_FILE", fields={"file": "שם הקובץ אינו תקין"})
