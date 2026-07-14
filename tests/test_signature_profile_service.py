from pathlib import Path
from uuid import uuid4
import shutil

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import routes_signature
from app.services import signature_profile_service

ROOT = Path(__file__).resolve().parents[1]


def _profile_payload():
    points = [{"x": index / 25, "y": 0.45 + (index % 3) * 0.02, "t": index * 10} for index in range(25)]
    points[0] = {"x": -1, "y": 2, "t": 0}
    return {
        "canvas": {"width": 700, "height": 260},
        "strokes": [points],
        "preview_png_data_url": "data:image/png;base64,dummy",
    }


def _workspace_tmp() -> Path:
    path = ROOT / ".tools" / "test_env" / uuid4().hex
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_signature_profile_is_saved_locally_and_normalized(monkeypatch):
    workspace = _workspace_tmp()
    monkeypatch.setattr(signature_profile_service, "resolve_project_path", lambda value: workspace / value)
    try:
        status = signature_profile_service.write_signature_profile(_profile_payload())
        profile = signature_profile_service.read_signature_profile()

        assert status["exists"] is True
        assert status["stroke_count"] == 1
        assert status["point_count"] == 25
        assert profile is not None
        assert profile["strokes"][0][0]["x"] == 0
        assert profile["strokes"][0][0]["y"] == 1
        assert (workspace / "runtime/secrets/signature.profile.json").exists()
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_signature_api_status_does_not_return_raw_signature(monkeypatch):
    workspace = _workspace_tmp()
    monkeypatch.setattr(signature_profile_service, "resolve_project_path", lambda value: workspace / value)
    app = FastAPI()
    app.include_router(routes_signature.router)
    client = TestClient(app)
    try:
        save_response = client.post("/api/signature/save", json=_profile_payload())
        status_response = client.get("/api/signature/status")

        assert save_response.status_code == 200
        assert status_response.status_code == 200
        data = status_response.json()["data"]
        assert "strokes" not in data
        assert "preview_png_data_url" not in data
        assert "dummy" not in str(status_response.json())
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_gitignore_protects_signature_profile():
    content = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "runtime/secrets/signature.profile.json" in content
    assert "*.signature.json" in content
