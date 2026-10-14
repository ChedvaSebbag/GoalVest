"""חישובי תאריך ליעד. מועד היעד חייב להיות לפחות 6 חודשים קדימה (FR-12)."""

import calendar
from datetime import date


def add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def is_far_enough(target: date, today: date, months: int = 6) -> bool:
    return target >= add_months(today, months)
