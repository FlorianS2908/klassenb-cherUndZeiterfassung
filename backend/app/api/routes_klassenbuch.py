from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.browser.automation_klassenbuch import KlassenbuchLoadError, load_klassenbuecher_overview, prepare_klassenbuch, submit_klassenbuch
from app.models.schemas import SubmitRequest

router = APIRouter(prefix="/api/klassenbuch", tags=["klassenbuch"])


@router.get("/open")
async def open_books():
    try:
        result = await load_klassenbuecher_overview()
    except KlassenbuchLoadError as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "ok": False,
                "message": str(exc) or "Klassenbuecher konnten nicht geladen werden.",
                "exception_type": exc.diagnostics.get("exception_type", type(exc).__name__),
                "diagnostics": exc.diagnostics,
            },
        ) from exc
    except Exception as exc:
        message = str(exc).strip() or f"unbekannter Fehler ({type(exc).__name__})"
        raise HTTPException(
            status_code=500,
            detail={
                "ok": False,
                "message": f"Klassenbuecher konnten nicht geladen werden: {message}",
                "exception_type": type(exc).__name__,
                "diagnostics": {
                    "step": "route_open_books",
                    "current_url": "",
                    "page_title": "",
                    "screenshot_path": "",
                    "html_snapshot_path": "",
                },
            },
        ) from exc
    return result


@router.post("/prepare")
async def prepare(payload: dict):
    return await prepare_klassenbuch(payload)


@router.post("/submit")
async def submit(request: SubmitRequest):
    return await submit_klassenbuch(request.payload, request.review_confirmed, request.signature_confirmed)
