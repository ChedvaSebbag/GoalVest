"""בדיקת קובץ מסמך לפי magic bytes. בלי כתיבה לדיסק."""

import hashlib
import io
import re
import zipfile
from pathlib import Path

from goalvest_core.errors import BusinessRuleViolation

MAX_DOCUMENT_BYTES = 10 * 1024 * 1024
_PDF = b"%PDF"
_ZIP = b"PK\x03\x04"


def inspect_document(content: bytes) -> tuple[str, str]:
    """מחזיר סיומת (pdf/docx) ו-sha256, או דוחה קובץ שאינו PDF/DOCX עד 10MB."""
    if not content or len(content) > MAX_DOCUMENT_BYTES:
        _reject("גודל הקובץ חייב להיות בין בייט אחד ל-10MB")
    digest = hashlib.sha256(content).hexdigest()
    if content.startswith(_PDF):
        return "pdf", digest
    if content.startswith(_ZIP) and _is_docx(content):
        return "docx", digest
    _reject("רק קובצי PDF או DOCX")
    raise AssertionError


def display_name(original: str, extension: str) -> str:
    base = Path(original or "document").name
    cleaned = re.sub(r"[^\w.\- \u0590-\u05FF]", "", base).strip(" .") or "document"
    stem = cleaned.rsplit(".", 1)[0] if "." in cleaned else cleaned
    return f"{stem[:180]}.{extension}"


def _is_docx(content: bytes) -> bool:
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            return "word/document.xml" in archive.namelist()
    except zipfile.BadZipFile:
        return False


def _reject(message: str) -> None:
    raise BusinessRuleViolation(message, code="INVALID_FILE", fields={"file": message})
