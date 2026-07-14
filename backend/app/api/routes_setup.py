from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.browser.automation_klassenbuch import KlassenbuchLoadError, test_klassenbuch_login as run_klassenbuch_login_test
from app.models.schemas import ApiMessage, SetupPayload
from app.services.credentials_service import get_klassenbuch_credential_status, write_klassenbuch_local_credentials
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
    credentials = None
    username = (payload.get("username") or payload.get("klassenbuch_username") or "").strip()
    password = payload.get("password") or payload.get("klassenbuch_password") or ""
    if username and password:
        credentials = (username, password)
    try:
        result = await run_klassenbuch_login_test(credentials)
    except KlassenbuchLoadError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "ok": False,
                "message": "Login fehlgeschlagen. Die lokal gespeicherten Zugangsdaten wurden abgelehnt.",
                "diagnostics": exc.diagnostics,
            },
        ) from exc
    return ApiMessage(
        ok=True,
        message="Login erfolgreich. Klassenbuecher koennen geladen werden.",
        data={"diagnostics": result.get("diagnostics", {})},
    )


@router.post("/save-local-klassenbuch-credentials")
def save_local_klassenbuch_credentials(payload: dict[str, str]):
    try:
        status = write_klassenbuch_local_credentials(payload.get("username", ""), payload.get("password", ""))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    from app.config import get_settings

    get_settings.cache_clear()
    return ApiMessage(ok=True, message="Klassenbuch-Zugangsdaten wurden lokal gespeichert.", data=status)


@router.post("/run")
def run_setup():
    return ApiMessage(ok=True, message="Bitte Setup in der Weboberflaeche unter /setup abschliessen.", data={"setup_url": "/setup"})
