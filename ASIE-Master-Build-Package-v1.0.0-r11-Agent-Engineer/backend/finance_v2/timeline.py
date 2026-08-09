from __future__ import annotations

import re


_PERIOD = re.compile(r"^(?P<year>[0-9]{4})-(?P<month>0[1-9]|1[0-2])$")


def period_index(period: str) -> int:
    match = _PERIOD.fullmatch(period)
    if not match:
        raise ValueError(f"Invalid monthly period: {period!r}")
    year = int(match.group("year"))
    month = int(match.group("month"))
    return year * 12 + month - 1


def period_from_index(index: int) -> str:
    if isinstance(index, bool) or not isinstance(index, int) or index < 12:
        raise ValueError(f"Invalid monthly period index: {index!r}")
    year, month_zero = divmod(index, 12)
    return f"{year:04d}-{month_zero + 1:02d}"


def add_months(period: str, months: int) -> str:
    if isinstance(months, bool) or not isinstance(months, int):
        raise TypeError("months must be an integer")
    target = period_index(period) + months
    if target < 12:
        raise ValueError("monthly period precedes year 0001")
    return period_from_index(target)


def monthly_periods(start_period: str, count: int) -> tuple[str, ...]:
    if isinstance(count, bool) or not isinstance(count, int) or not 12 <= count <= 240:
        raise ValueError("monthly period count must be an integer from 12 to 240")
    start = period_index(start_period)
    return tuple(period_from_index(start + offset) for offset in range(count))
