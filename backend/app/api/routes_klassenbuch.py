from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.browser.automation_klassenbuch import KlassenbuchLoadError, load_klassenbuecher_overview, prepare_klassenbuch, submit_klassenbuch
from app.browser.playwright_health import check_playwright_health
from app.models.schemas import SubmitRequest
from app.services.diagnostics_service import write_route_error_diagnostic

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
        diagnostics = write_route_error_diagnostic("klassenbuch", "load_open_klassenbuecher", "route_open_books", exc)
        raise HTTPException(
            status_code=500,
            detail={
                "ok": False,
                "message": diagnostics["error_message"],
                "exception_type": type(exc).__name__,
                "diagnostics": diagnostics,
            },
        ) from exc
    return result


@router.get("/browser-health")
async def browser_health():
    result = await check_playwright_health()
    if not result.get("ok"):
        exc = RuntimeError(result.get("message") or "Browser-Health fehlgeschlagen.")
        diagnostics = write_route_error_diagnostic("klassenbuch", "browser_health", str(result.get("step") or "browser_health"), exc, {"browser_health": result})
        result["diagnostics"] = diagnostics
    return result


@router.post("/prepare")
async def prepare(payload: dict):
    return await prepare_klassenbuch(payload)


@router.post("/submit")
async def submit(request: SubmitRequest):
    return await submit_klassenbuch(request.payload, request.review_confirmed, request.signature_confirmed)
