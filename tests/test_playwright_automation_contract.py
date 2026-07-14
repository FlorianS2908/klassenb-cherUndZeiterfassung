from app.browser.selectors_klassenbuch import KLASSENBUCH_SELECTORS
from app.browser.automation_klassenbuch import _extract_edit_action_index, _interpolate_points, _normalize_table_key, _row_to_entry, _signature_points, _validate_signature_submit_allowed
from app.browser.selectors_timebutler import TIMEBUTLER_SELECTORS
from app.config import get_settings
from app.services.klassenbuch_service import ensure_open_status
from app.services.status_service import status_service


def test_important_klassenbuch_selectors_have_fallbacks():
    for key in [
        "username",
        "password",
        "login_button",
        "edit_button",
        "save_button",
        "teaching_format_fields",
        "teaching_format_modal",
        "teaching_format_apply",
        "wizard_markers",
        "signature_canvas",
        "signature",
        "sign_button",
        "signature_page_markers",
    ]:
        assert len(KLASSENBUCH_SELECTORS[key]) >= 3
    for key in ["offene", "ueberfaellige", "freigegebene", "korrektur"]:
        assert len(KLASSENBUCH_SELECTORS["overview_tabs"][key]) >= 3


def test_important_timebutler_selectors_have_fallbacks():
    for key in ["username", "password", "login_button", "project", "category", "save_button"]:
        assert len(TIMEBUTLER_SELECTORS[key]) >= 3


def test_klassenbuch_requires_open_status():
    assert ensure_open_status({"status": "Offen"})
    assert not ensure_open_status({"status": "Signiert"})


def test_signature_submit_requires_all_safety_gates(monkeypatch):
    settings = get_settings().model_copy(update={"auto_submit": True})
    monkeypatch.setattr("app.browser.automation_klassenbuch.get_settings", lambda: settings)
    status_service.status.blocked = False
    payload = {"klassenbuch": {"status": "Offen"}, "ue_items": [{"content": str(index)} for index in range(9)]}

    assert _validate_signature_submit_allowed(payload, review_confirmed=True, signature_confirmed=True) is None
    assert "Review" in _validate_signature_submit_allowed(payload, review_confirmed=False, signature_confirmed=True)
    assert "Signatur" in _validate_signature_submit_allowed(payload, review_confirmed=True, signature_confirmed=False)
    assert "9 UE" in _validate_signature_submit_allowed({**payload, "ue_items": []}, review_confirmed=True, signature_confirmed=True)


def test_schaffer_signature_points_stay_inside_canvas():
    points = _signature_points()
    assert len(points) >= 30
    assert all(0 <= x <= 1 and 0 <= y <= 1 for x, y in points)


def test_schaffer_signature_interpolation_adds_smooth_mouse_points():
    points = _signature_points()
    interpolated = _interpolate_points(points)
    assert interpolated[0] == points[0]
    assert interpolated[-1] == points[-1]
    assert len(interpolated) > len(points)


def test_klassenbuch_table_headers_are_normalized():
    assert _normalize_table_key("Einsatzzeit Von") == "einsatzzeit_von"
    assert _normalize_table_key("Einsatzzeit Bis") == "einsatzzeit_bis"
    assert _normalize_table_key("Nummer") == "nummer"
    assert _normalize_table_key("Bearbeiten") == "bearbeiten"


def test_klassenbuch_number_can_be_alphanumeric_in_fallback_parser():
    entry = _row_to_entry("EACGBAC\nLF-ZQ8a HTML & CSS\nOffen", 0)
    assert entry["number"] == "EACGBAC"


def test_edit_action_index_is_extracted_from_overview_onclick():
    onclick = "classbookApp.overview.forwardToWizardWithPreselection(12);"
    assert _extract_edit_action_index(onclick) == "12"
