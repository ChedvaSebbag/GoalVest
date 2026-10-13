"""קטלוג גופים פיננסיים להרשמת סוכן. מקור יחיד לשרת ול-Autocomplete."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class Institution:
    id: UUID
    name: str


INSTITUTIONS: tuple[Institution, ...] = (
    Institution(UUID("c0ffee00-0000-4000-8000-000000000001"), "מגדל"),
    Institution(UUID("c0ffee00-0000-4000-8000-000000000002"), "הראל"),
    Institution(UUID("c0ffee00-0000-4000-8000-000000000003"), "כלל"),
    Institution(UUID("c0ffee00-0000-4000-8000-000000000004"), "מנורה מבטחים"),
    Institution(UUID("c0ffee00-0000-4000-8000-000000000005"), "הפניקס"),
    Institution(UUID("c0ffee00-0000-4000-8000-000000000006"), "אלטשולר שחם"),
)


def find_institution(institution_id: UUID) -> Institution | None:
    for item in INSTITUTIONS:
        if item.id == institution_id:
            return item
    return None
