from app.browser.selectors_klassenbuch import KLASSENBUCH_SELECTORS
from pathlib import Path
import inspect
import asyncio

from app.browser import automation_klassenbuch
from app.browser.automation_klassenbuch import _canvas_has_ink, _draw_saved_signature_with_mouse, _extract_edit_action_index, _fill_signature, _interpolate_points, _normalize_table_key, _row_to_entry, _signature_points, _validate_signature_submit_allowed
from app.browser.base import first_locator
from app.browser.selectors_timebutler import TIMEBUTLER_SELECTORS
from app.config import get_settings
from app.services.klassenbuch_service import ensure_open_status
from app.services.status_service import status_service

ROOT = Path(__file__).resolve().parents[1]


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


def test_signature_canvas_prefers_real_signature_pad_canvas():
    assert KLASSENBUCH_SELECTORS["signature_canvas"][0] == "#signature-pad canvas"
    assert ".m-signature-pad canvas" in KLASSENBUCH_SELECTORS["signature_canvas"]
    assert "canvas[style*=\"touch-action\"]" in KLASSENBUCH_SELECTORS["signature_canvas"]


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


class CanvasMock:
    def __init__(self, has_ink=True):
        self.has_ink = has_ink

    async def evaluate(self, script):
        return self.has_ink


def test_canvas_has_ink_detects_empty_and_drawn_canvas():
    assert asyncio.run(_canvas_has_ink(CanvasMock(False))) is False
    assert asyncio.run(_canvas_has_ink(CanvasMock(True))) is True


class PageMouseMock:
    def __init__(self):
        self.moves = []

    async def move(self, x, y, steps=None):
        self.moves.append((x, y, steps))

    async def down(self):
        self.down_called = True

    async def up(self):
        self.up_called = True


class PageMock:
    def __init__(self):
        self.mouse = PageMouseMock()

    async def evaluate(self, script):
        return None


class CanvasBoxMock(CanvasMock):
    async def bounding_box(self):
        return {"x": 10, "y": 20, "width": 600, "height": 260}


def test_draw_signature_schaffer_uses_mouse_before_fallback(monkeypatch):
    calls = []
    page = PageMock()
    canvas = CanvasBoxMock(True)

    async def fake_safe_screenshot(page_arg, step):
        return step

    async def fake_direct(canvas_arg):
        calls.append("direct")
        return True

    monkeypatch.setattr(automation_klassenbuch, "_safe_screenshot", fake_safe_screenshot)
    monkeypatch.setattr(automation_klassenbuch, "_draw_signature_direct_canvas", fake_direct)

    asyncio.run(automation_klassenbuch.draw_signature_schaffer(page, canvas))

    assert page.mouse.moves
    assert "direct" not in calls


def test_draw_signature_schaffer_uses_direct_canvas_only_after_mouse_failure(monkeypatch):
    calls = []
    page = PageMock()
    canvas = CanvasBoxMock(False)

    async def fake_safe_screenshot(page_arg, step):
        return step

    async def fake_direct(canvas_arg):
        calls.append("direct")
        canvas_arg.has_ink = True
        return True

    monkeypatch.setattr(automation_klassenbuch, "_safe_screenshot", fake_safe_screenshot)
    monkeypatch.setattr(automation_klassenbuch, "_draw_signature_direct_canvas", fake_direct)

    asyncio.run(automation_klassenbuch.draw_signature_schaffer(page, canvas))

    assert page.mouse.moves
    assert calls == ["direct"]


def test_draw_saved_signature_with_mouse_uses_saved_strokes(monkeypatch):
    page = PageMock()
    canvas = CanvasBoxMock(True)
    profile = {"strokes": [[{"x": 0.1, "y": 0.5}, {"x": 0.5, "y": 0.6}, {"x": 0.9, "y": 0.5}]]}

    async def fake_safe_screenshot(page_arg, step):
        return step

    monkeypatch.setattr(automation_klassenbuch, "_safe_screenshot", fake_safe_screenshot)

    assert asyncio.run(_draw_saved_signature_with_mouse(page, canvas, profile)) is True
    assert len(page.mouse.moves) >= 3
    assert all(10 <= move[0] <= 610 for move in page.mouse.moves)


def test_fill_signature_uses_direct_fallback_only_when_saved_mouse_fails(monkeypatch):
    calls = []
    canvas = CanvasBoxMock(False)

    async def fake_locator_or_none(page, selectors):
        return canvas

    async def fake_profile():
        return {"strokes": [[{"x": 0.2, "y": 0.5}, {"x": 0.8, "y": 0.5}]]}

    async def fake_mouse(page, canvas_arg, profile):
        calls.append("mouse")
        return False

    async def fake_direct(page, canvas_arg, profile):
        calls.append("direct")
        canvas_arg.has_ink = True
        return True

    async def fake_safe_screenshot(page, step):
        return step

    monkeypatch.setattr(automation_klassenbuch, "_locator_or_none", fake_locator_or_none)
    monkeypatch.setattr(automation_klassenbuch, "_load_saved_signature_profile", fake_profile)
    monkeypatch.setattr(automation_klassenbuch, "_draw_saved_signature_with_mouse", fake_mouse)
    monkeypatch.setattr(automation_klassenbuch, "_draw_saved_signature_direct_canvas", fake_direct)
    monkeypatch.setattr(automation_klassenbuch, "_safe_screenshot", fake_safe_screenshot)

    result = asyncio.run(_fill_signature(PageMock(), allow_overwrite=True))

    assert calls == ["mouse", "direct"]
    assert result["canvas_has_ink"] is True


def test_fill_signature_aborts_without_canvas_or_signature_field(monkeypatch):
    async def fake_locator_or_none(page, selectors):
        return None

    async def fake_safe_screenshot(page, step):
        return step

    monkeypatch.setattr(automation_klassenbuch, "_locator_or_none", fake_locator_or_none)
    monkeypatch.setattr(automation_klassenbuch, "_safe_screenshot", fake_safe_screenshot)

    try:
        asyncio.run(_fill_signature(PageMock(), allow_overwrite=False))
    except RuntimeError as exc:
        assert "Signaturfeld nicht gefunden" in str(exc)
    else:
        raise AssertionError("_fill_signature should fail without canvas or field")


def test_prepare_signature_klassenbuch_does_not_finalize_signature():
    source = inspect.getsource(automation_klassenbuch.prepare_signature_klassenbuch)
    assert "_finalize_signature" not in source
    assert "signatur_ready_for_submit" in source
    assert "Signatur wurde vorbereitet" in source


def test_signature_diagnostics_include_canvas_context():
    source = inspect.getsource(automation_klassenbuch.prepare_signature_klassenbuch)
    helper_source = inspect.getsource(automation_klassenbuch._canvas_debug_info)
    assert "bounding_box" in helper_source
    assert "canvas_has_ink" in helper_source
    assert "canvas_width" in helper_source
    assert "html_snapshot" in source


def test_signature_diagnostics_do_not_store_passwords():
    source = inspect.getsource(automation_klassenbuch.prepare_signature_klassenbuch)
    assert "password" not in source.lower()
    assert "secret" not in source.lower()


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


def test_browser_code_does_not_call_locator_first_as_function():
    for path in [ROOT / "backend" / "app" / "browser" / "base.py", ROOT / "backend" / "app" / "browser" / "automation_klassenbuch.py"]:
        assert ".first()" not in path.read_text(encoding="utf-8")


def test_first_locator_uses_nth_zero():
    class LocatorMock:
        def __init__(self):
            self.index = None

        def nth(self, index):
            self.index = index
            return self

    class ScopeMock:
        def __init__(self):
            self.locator_value = LocatorMock()

        def locator(self, selector):
            return self.locator_value

    scope = ScopeMock()
    result = first_locator(scope, "body")
    assert result.index == 0


def test_login_uses_credentials_service_instead_of_settings_password():
    source = inspect.getsource(automation_klassenbuch._login)
    overview_source = inspect.getsource(automation_klassenbuch.load_klassenbuecher_overview)

    assert "get_klassenbuch_credentials()" in source
    assert "settings.klassenbuch_password" not in source
    assert "await _login(page, diag)" in overview_source


def test_save_html_snapshot_masks_password_values(monkeypatch):
    class PageMock:
        async def content(self):
            return '<input type="password" value="secret-one"><div>secret-one</div>'

    snapshot_dir = ROOT / ".tools" / "test_env" / "html_snapshot_masks_password"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    settings = get_settings().model_copy(update={"screenshot_folder": str(snapshot_dir), "klassenbuch_password": "secret-one"})
    monkeypatch.setattr(automation_klassenbuch, "get_settings", lambda: settings)
    monkeypatch.setattr(automation_klassenbuch, "get_klassenbuch_credentials", lambda: ("trainer@example.com", "secret-one"))

    path = asyncio.run(automation_klassenbuch.save_html_snapshot(PageMock(), "login"))
    content = Path(path).read_text(encoding="utf-8")

    assert "secret-one" not in content
    assert "***" in content
