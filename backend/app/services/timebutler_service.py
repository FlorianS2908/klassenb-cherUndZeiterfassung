from __future__ import annotations

from datetime import date

from app.config import get_settings
from app.models.schemas import TimebutlerPayload


def default_payload(target_date: date) -> TimebutlerPayload:
    settings = get_settings()
    return TimebutlerPayload(
        target_date=target_date,
        project=settings.timebutler_project,
        category=settings.timebutler_category,
        start=settings.timebutler_start,
        end=settings.timebutler_end,
        pause=settings.timebutler_pause,
        remark=settings.timebutler_remark,
    )


def duplicate_check_stub(_: TimebutlerPayload) -> bool:
    # The authoritative duplicate check happens in the Playwright flow after login,
    # because Timebutler's current entries are only visible in the web UI.
    return False
