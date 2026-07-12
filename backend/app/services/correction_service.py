from __future__ import annotations

from app.models.schemas import TimebutlerPayload, UeItem
from app.services.validation import validate_timebutler_payload, validate_ue_items


def validate_klassenbuch_correction(items: list[UeItem]) -> list[str]:
    return validate_ue_items(items)


def validate_timebutler_correction(payload: TimebutlerPayload, federal_state: str, blocked: str, vacation: str, sick: str) -> list[str]:
    return validate_timebutler_payload(payload, federal_state, blocked, vacation, sick)
