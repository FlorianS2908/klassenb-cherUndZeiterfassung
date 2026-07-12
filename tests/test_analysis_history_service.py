from pathlib import Path

from app.config import get_settings
from app.services import analysis_history_service


def test_analysis_history_saves_multiple_runs(monkeypatch):
    folder = Path(__file__).resolve().parents[1] / "analysis_history_test"
    folder.mkdir(exist_ok=True)
    for path in folder.glob("*.json"):
        path.unlink()
    settings = get_settings()
    monkeypatch.setattr(settings, "analysis_history_folder", str(folder))
    first = analysis_history_service.save_history({"filename": "kurs.pptx", "selection": "5-10"})
    second = analysis_history_service.save_history({"filename": "kurs.pptx", "selection": "11-18"})
    items = analysis_history_service.list_history()
    assert first["id"] != second["id"]
    assert len(items) == 2
    assert analysis_history_service.reopen_history(first["id"])["selection"] == "5-10"
    for path in folder.glob("*.json"):
        path.unlink()
