from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.browser.automation_klassenbuch import KlassenbuchLoadError, fill_classbook_and_open_signature, load_klassenbuecher_overview, prepare_klassenbuch, prepare_signature_klassenbuch, submit_klassenbuch
from app.browser.klassenbuch_login_test import test_klassenbuch_login_only
from app.browser.playwright_health import check_playwright_health
from app.config import get_settings
from app.models.schemas import SubmitRequest
from app.services.credentials_service import get_klassenbuch_credential_status, write_klassenbuch_local_credentials
from app.services.diagnostics_service import write_route_error_diagnostic
from app.services.local_credentials_file import delete_klassenbuch_credentials_file

router = APIRouter(prefix="/api/klassenbuch", tags=["klassenbuch"])


@router.get("/credentials/status")
async def credentials_status():
    return {"ok": True, "data": get_klassenbuch_credential_status()}


@router.post("/credentials/save")
async def save_credentials(payload: dict[str, str]):
    try:
        status = write_klassenbuch_local_credentials(payload.get("username", ""), payload.get("password", ""))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    get_settings.cache_clear()
    return {"ok": True, "message": "Klassenbuch-Zugangsdaten wurden lokal gespeichert.", "data": status}


@router.post("/credentials/delete")
async def delete_credentials():
    delete_klassenbuch_credentials_file()
    get_settings.cache_clear()
    return {"ok": True, "message": "Lokale Klassenbuch-Zugangsdaten wurden geloescht.", "data": get_klassenbuch_credential_status()}


@router.post("/login-test")
async def login_test(payload: dict[str, str] | None = None):
    payload = payload or {}
    try:
        result = await test_klassenbuch_login_only(
            (payload.get("username") or "").strip() or None,
            payload.get("password") or None,
            payload.get("url") or None,
        )
    except RuntimeError as exc:
        return {"ok": False, "message": str(exc), "data": {"problem_category": "credentials_missing", "credential_source_used": "missing"}}
    except Exception:
        return {"ok": False, "message": "Login fehlgeschlagen.", "data": {"problem_category": "login"}}
    return {"ok": bool(result.get("ok")), "message": str(result.get("message", "")), "data": result}


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


@router.post("/prepare-signature")
async def prepare_signature(request: SubmitRequest):
    return await prepare_signature_klassenbuch(request.payload, request.review_confirmed)


@router.post("/fill-and-open-signature")
async def fill_and_open_signature(request: SubmitRequest):
    return await fill_classbook_and_open_signature(request.payload, request.review_confirmed)


@router.post("/submit")
async def submit(request: SubmitRequest):
    return await submit_klassenbuch(request.payload, request.review_confirmed, request.signature_confirmed)
