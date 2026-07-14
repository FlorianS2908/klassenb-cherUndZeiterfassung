from __future__ import annotations

from fastapi import APIRouter, HTTPException

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
    return ApiMessage(ok=True, message="Setup wurde gespeichert.", data=data)


@router.post("/run")
def run_setup():
    return ApiMessage(ok=True, message="Bitte Setup in der Weboberflaeche unter /setup abschliessen.", data={"setup_url": "/setup"})
