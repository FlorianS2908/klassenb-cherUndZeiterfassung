from app.browser.selectors_klassenbuch import KLASSENBUCH_SELECTORS
from app.browser.selectors_timebutler import TIMEBUTLER_SELECTORS
from app.services.klassenbuch_service import ensure_open_status


def test_important_klassenbuch_selectors_have_fallbacks():
    for key in ["username", "password", "login_button", "edit_button", "save_button", "signature"]:
        assert len(KLASSENBUCH_SELECTORS[key]) >= 3


def test_important_timebutler_selectors_have_fallbacks():
    for key in ["username", "password", "login_button", "project", "category", "save_button"]:
        assert len(TIMEBUTLER_SELECTORS[key]) >= 3


def test_klassenbuch_requires_open_status():
    assert ensure_open_status({"status": "Offen"})
    assert not ensure_open_status({"status": "Signiert"})
