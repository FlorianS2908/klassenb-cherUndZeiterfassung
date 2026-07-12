from __future__ import annotations

from fastapi import APIRouter

from app.browser.automation_klassenbuch import prepare_klassenbuch, submit_klassenbuch
from app.models.schemas import SubmitRequest
from app.services.klassenbuch_service import open_klassenbuecher_stub

router = APIRouter(prefix="/api/klassenbuch", tags=["klassenbuch"])


@router.get("/open")
def open_books():
    return {"items": open_klassenbuecher_stub()}


@router.post("/prepare")
async def prepare(payload: dict):
    return await prepare_klassenbuch(payload)


@router.post("/submit")
async def submit(request: SubmitRequest):
    return await submit_klassenbuch(request.payload, request.review_confirmed)
