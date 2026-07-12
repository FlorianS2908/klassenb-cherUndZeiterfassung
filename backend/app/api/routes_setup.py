from __future__ import annotations

import subprocess
import sys

from fastapi import APIRouter

from app.config import ENV_PATH, ROOT_DIR, ensure_runtime_ready
from app.models.schemas import ApiMessage

router = APIRouter(prefix="/api/setup", tags=["setup"])


@router.post("/check")
def check_setup():
    ok, messages = ensure_runtime_ready(False)
    return ApiMessage(ok=ok, message="Setup vollstaendig." if ok else "Setup unvollstaendig.", data={"messages": messages, "env_exists": ENV_PATH.exists()})


@router.post("/run")
def run_setup():
    subprocess.Popen([sys.executable, str(ROOT_DIR / "setup_env.py")], cwd=ROOT_DIR)
    return ApiMessage(ok=True, message="Setup-Assistent wurde in einem lokalen Prozess gestartet.")
