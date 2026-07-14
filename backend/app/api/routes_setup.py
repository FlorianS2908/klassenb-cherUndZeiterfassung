from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.browser.klassenbuch_login_test import test_klassenbuch_login_only
from app.config import get_settings
from app.models.schemas import ApiMessage, SetupPayload
from app.services.credentials_service import get_klassenbuch_credential_status, write_klassenbuch_local_credentials
from app.services.local_credentials_file import delete_klassenbuch_credentials_file
from app.services.setup_service import check_setup as check_setup_state
from app.services.setup_service import default_setup_values, save_setup, validate_openai_key_file

router = APIRouter(prefix="/api/setup", tags=["setup"])


@router.post("/check")
def check_setup():
    state = check_setup_state()
    return ApiMessage(
        ok=not state.setup_required,
        message="Setup vollstaendig." if not state.setup_required else "Setup unvollstaendig.",
        data=state.model_dump(),
    )


@router.get("/defaults")
def setup_defaults():
    defaults = default_setup_values()
    status = get_klassenbuch_credential_status()
    return defaults.model_copy(
        update={
            "klassenbuch_password_present": status["password_present"],
            "klassenbuch_password_source": status["source"],
            "klassenbuch_credentials_file_exists": status["credentials_file_exists"],
            "klassenbuch_credentials_file_path": status["credentials_file_path"],
        }
    )


@router.post("/validate-openai-key-file")
def validate_key_file(payload: dict[str, str]):
    result = validate_openai_key_file(payload.get("openai_api_key_file") or payload.get("path", ""))
    return ApiMessage(ok=result.exists and result.readable and result.non_empty, message=result.message, data=result.model_dump())


@router.post("/save")
def save_setup_payload(payload: SetupPayload):
    try:
        data = save_setup(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    warnings = data.get("warnings") if isinstance(data, dict) else []
    message = "Setup wurde gespeichert."
    if warnings:
        message = f"{message} {warnings[0]}"
    return ApiMessage(ok=True, message=message, data=data)


@router.post("/test-klassenbuch-login")
async def test_klassenbuch_login(payload: dict[str, str] | None = None):
    payload = payload or {}
    username = (payload.get("username") or payload.get("klassenbuch_username") or "").strip()
    password = payload.get("password") or payload.get("klassenbuch_password") or ""
    url = payload.get("url") or None
    try:
        result = await test_klassenbuch_login_only(username or None, password or None, url)
    except RuntimeError as exc:
        return ApiMessage(ok=False, message=str(exc), data={"problem_category": "credentials_missing", "credential_source_used": "missing"})
    except Exception:
        return ApiMessage(ok=False, message="Login fehlgeschlagen.", data={"problem_category": "login"})
    return ApiMessage(ok=bool(result.get("ok")), message=str(result.get("message", "")), data=result)


@router.get("/local-klassenbuch-credentials/status")
def local_klassenbuch_credentials_status():
    return ApiMessage(ok=True, message="Status der lokalen Klassenbuch-Zugangsdaten.", data=get_klassenbuch_credential_status())


@router.post("/save-local-klassenbuch-credentials")
def save_local_klassenbuch_credentials(payload: dict[str, str]):
    try:
        status = write_klassenbuch_local_credentials(payload.get("username", ""), payload.get("password", ""))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    get_settings.cache_clear()
    return ApiMessage(ok=True, message="Klassenbuch-Zugangsdaten wurden lokal gespeichert.", data=status)


@router.post("/delete-local-klassenbuch-credentials")
def delete_local_klassenbuch_credentials():
    delete_klassenbuch_credentials_file()
    get_settings.cache_clear()
    return ApiMessage(ok=True, message="Lokale Klassenbuch-Zugangsdaten wurden geloescht.", data=get_klassenbuch_credential_status())


@router.post("/run")
def run_setup():
    return ApiMessage(ok=True, message="Bitte Setup in der Weboberflaeche unter /setup abschliessen.", data={"setup_url": "/setup"})
