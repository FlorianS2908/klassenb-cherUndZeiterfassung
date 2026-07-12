from __future__ import annotations

from app.config import get_settings
from app.models.schemas import ApiMessage


async def prepare_klassenbuch(payload: dict) -> ApiMessage:
    return ApiMessage(ok=True, message="Klassenbuch wurde im Dry-Run vorbereitet.", data={"payload": payload})


async def submit_klassenbuch(payload: dict, review_confirmed: bool) -> ApiMessage:
    settings = get_settings()
    if not settings.auto_submit or not review_confirmed:
        return ApiMessage(ok=False, message="Finales Signieren gesperrt: AUTO_SUBMIT und Review-Bestaetigung erforderlich.")
    return ApiMessage(ok=True, message=f"Klassenbuch wuerde produktiv mit Signatur {settings.default_signature} signiert.", data={"payload": payload})
