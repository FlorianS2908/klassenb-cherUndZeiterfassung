from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class TargetDayResult:
    target_date: date | None
    can_auto_run: bool
    reason: str = ""


def previous_workday(today: date) -> TargetDayResult:
    weekday = today.weekday()
    if weekday == 5:
        return TargetDayResult(None, False, "Samstag: kein automatischer Lauf")
    if weekday == 6:
        return TargetDayResult(None, False, "Sonntag: kein automatischer Lauf")
    if weekday == 0:
        return TargetDayResult(today - timedelta(days=3), True)
    return TargetDayResult(today - timedelta(days=1), True)


def parse_date_list(value: str) -> set[date]:
    dates: set[date] = set()
    for item in [part.strip() for part in value.split(",") if part.strip()]:
        dates.add(date.fromisoformat(item))
    return dates
