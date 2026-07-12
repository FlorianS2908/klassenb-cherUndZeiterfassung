from datetime import date

from app.models.schemas import TimebutlerPayload
from app.services.validation import validate_timebutler_payload


def test_timebutler_payload_valid():
    payload = TimebutlerPayload(target_date=date(2026, 7, 10), project="FbW", category="Training/Coaching", start="08:30", end="16:30", pause="45m", remark="Training")
    assert validate_timebutler_payload(payload, "BW", "", "", "") == []


def test_end_must_be_after_start():
    payload = TimebutlerPayload(target_date=date(2026, 7, 10), project="FbW", category="Training/Coaching", start="16:30", end="08:30", pause="45m", remark="Training")
    assert "Endzeit muss nach Startzeit liegen." in validate_timebutler_payload(payload, "BW", "", "", "")
