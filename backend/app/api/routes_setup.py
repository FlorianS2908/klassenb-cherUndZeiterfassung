from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.browser.automation_klassenbuch import KlassenbuchLoadError, load_klassenbuecher_overview
from app.models.schemas import ApiMessage, SetupPayload
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
    return default_setup_values()


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
async def test_klassenbuch_login():
    try:
        result = await load_klassenbuecher_overview()
    except KlassenbuchLoadError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "ok": False,
                "message": "Login fehlgeschlagen. Bitte Benutzername und Passwort neu eingeben.",
                "diagnostics": exc.diagnostics,
            },
        ) from exc
    return ApiMessage(
        ok=True,
        message="Login erfolgreich. Klassenbuecher koennen geladen werden.",
        data={"count": result.get("count", 0), "diagnostics": result.get("diagnostics", {})},
    )


@router.post("/run")
def run_setup():
    return ApiMessage(ok=True, message="Bitte Setup in der Weboberflaeche unter /setup abschliessen.", data={"setup_url": "/setup"})
