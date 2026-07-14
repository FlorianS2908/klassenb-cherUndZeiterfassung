from __future__ import annotations

from datetime import date

from fastapi import APIRouter

from app.config import get_settings
from app.services.date_service import previous_workday
from app.services.holiday_service import blocked_reason
from app.services.status_service import status_service

router = APIRouter(prefix="/api/status", tags=["status"])


@router.get("")
def get_status():
    settings = get_settings()
    target = previous_workday(date.today())
    reason = target.reason
    blocked = False
    if target.target_date:
        reason = blocked_reason(target.target_date, settings.federal_state, settings.blocked_dates, settings.vacation_dates, settings.sick_dates)
        blocked = bool(reason)
    status_service.status.target_date = target.target_date
    status_service.status.auto_submit = settings.auto_submit and not settings.dry_run_forced
    status_service.status.mode = "dry-run" if settings.dry_run_forced or not settings.auto_submit else "productive"
    status_service.status.browser_headless = settings.browser_headless
    status_service.status.browser_mode = "unsichtbar/headless" if settings.browser_headless else "sichtbar/debug"
    status_service.status.blocked = blocked or not target.can_auto_run
    status_service.status.blocked_reason = reason
    return status_service.status
