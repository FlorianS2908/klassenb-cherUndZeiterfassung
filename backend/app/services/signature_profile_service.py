from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from app.config import resolve_project_path

SIGNATURE_PROFILE_PATH = "runtime/secrets/signature.profile.json"


def _profile_path() -> Path:
    return resolve_project_path(SIGNATURE_PROFILE_PATH)


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _normalize_point(point: dict[str, Any], fallback_t: int) -> dict[str, float | int]:
    x = max(0.0, min(1.0, float(point.get("x", 0))))
    y = max(0.0, min(1.0, float(point.get("y", 0))))
    t = int(point.get("t", fallback_t) or fallback_t)
    return {"x": x, "y": y, "t": t}


def _normalize_strokes(strokes: Any) -> list[list[dict[str, float | int]]]:
    if not isinstance(strokes, list):
        raise ValueError("Signatur-Strokes fehlen.")
    normalized: list[list[dict[str, float | int]]] = []
    point_counter = 0
    for stroke in strokes:
        if not isinstance(stroke, list):
            continue
        normalized_stroke = []
        for point in stroke:
            if isinstance(point, dict):
                normalized_stroke.append(_normalize_point(point, point_counter))
                point_counter += 1
        if normalized_stroke:
            normalized.append(normalized_stroke)
    if sum(len(stroke) for stroke in normalized) < 20:
        raise ValueError("Signatur muss mindestens 20 Punkte enthalten.")
    return normalized


def _sanitize_profile(profile: dict[str, Any]) -> dict[str, Any]:
    strokes = profile.get("strokes") or []
    return {
        "exists": True,
        "source": profile.get("source", "local_signature_pad"),
        "stroke_count": len(strokes),
        "point_count": sum(len(stroke) for stroke in strokes if isinstance(stroke, list)),
        "has_preview": bool(profile.get("preview_png_data_url")),
        "path": SIGNATURE_PROFILE_PATH,
        "format": "strokes + png/svg",
    }


def read_signature_profile() -> dict[str, Any] | None:
    path = _profile_path()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError("Lokales Signaturprofil konnte nicht gelesen werden.") from exc
    if not isinstance(data, dict):
        raise ValueError("Lokales Signaturprofil ist ungueltig.")
    return data


def write_signature_profile(profile: dict[str, Any]) -> dict[str, Any]:
    strokes = _normalize_strokes(profile.get("strokes"))
    canvas = profile.get("canvas") if isinstance(profile.get("canvas"), dict) else {}
    existing = read_signature_profile()
    now = _now()
    safe_profile = {
        "version": 1,
        "owner": "local_user",
        "source": "local_signature_pad",
        "created_at": (existing or {}).get("created_at") or now,
        "updated_at": now,
        "canvas": {
            "width": int(canvas.get("width") or 700),
            "height": int(canvas.get("height") or 260),
        },
        "strokes": strokes,
        "preview_png_data_url": str(profile.get("preview_png_data_url") or ""),
    }
    path = _profile_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(safe_profile, ensure_ascii=False, indent=2), encoding="utf-8")
    return _sanitize_profile(safe_profile)


def delete_signature_profile() -> None:
    path = _profile_path()
    if path.exists():
        path.unlink()


def get_signature_profile_status() -> dict[str, Any]:
    profile = read_signature_profile()
    if not profile:
        return {
            "exists": False,
            "source": "missing",
            "stroke_count": 0,
            "point_count": 0,
            "has_preview": False,
            "path": SIGNATURE_PROFILE_PATH,
            "format": "strokes + png/svg",
        }
    return _sanitize_profile(profile)
