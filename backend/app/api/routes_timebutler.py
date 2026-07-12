from __future__ import annotations

from datetime import date

from fastapi import APIRouter

from app.browser.automation_timebutler import prepare_timebutler, submit_timebutler
from app.models.schemas import SubmitRequest, TimebutlerPayload
from app.services.date_service import previous_workday
from app.services.timebutler_service import default_payload, duplicate_check_stub

router = APIRouter(prefix="/api/timebutler", tags=["timebutler"])


@router.get("/defaults")
def defaults():
    target = previous_workday(date.today()).target_date or date.today()
    return default_payload(target)


@router.post("/prepare")
async def prepare(payload: TimebutlerPayload):
    if duplicate_check_stub(payload):
        return {"ok": False, "message": "Doppelter Zeiteintrag erkannt."}
    return await prepare_timebutler(payload.model_dump(mode="json"))


@router.post("/submit")
async def submit(request: SubmitRequest):
    return await submit_timebutler(request.payload, request.review_confirmed)
