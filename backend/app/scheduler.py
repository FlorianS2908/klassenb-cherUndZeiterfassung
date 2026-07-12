from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import get_settings
from app.services.notification_service import notify


def create_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone="Europe/Berlin")

    def weekday_tick() -> None:
        settings = get_settings()
        if settings.auto_dry_run_on_start:
            notify("Klassenbuch-Tool", "Automatischer Dry-Run kann gestartet werden.", settings.desktop_notifications)
        else:
            notify("Klassenbuch-Tool", "Zieltag vorbereitet. Bitte Oberflaeche pruefen.", settings.desktop_notifications)

    scheduler.add_job(weekday_tick, CronTrigger(day_of_week="mon-fri", hour=8, minute=20, timezone="Europe/Berlin"), id="weekday_0820", replace_existing=True)
    return scheduler
