from __future__ import annotations

from app.config import get_settings
from app.models.schemas import ApiMessage


async def prepare_timebutler(payload: dict) -> ApiMessage:
    return ApiMessage(ok=True, message="Timebutler wurde im Dry-Run vorbereitet.", data={"payload": payload})


async def submit_timebutler(payload: dict, review_confirmed: bool) -> ApiMessage:
    settings = get_settings()
    if not settings.auto_submit or not review_confirmed:
        return ApiMessage(ok=False, message="Finales Speichern gesperrt: AUTO_SUBMIT und Review-Bestaetigung erforderlich.")
    return ApiMessage(ok=True, message="Timebutler wuerde produktiv gespeichert.", data={"payload": payload})
