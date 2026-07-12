from datetime import date

from app.services.holiday_service import blocked_reason


def test_blocked_dates():
    assert blocked_reason(date(2026, 7, 10), "BW", "2026-07-10", "", "") == "Zieltag ist gesperrt"


def test_vacation_dates():
    assert blocked_reason(date(2026, 7, 10), "BW", "", "2026-07-10", "") == "Zieltag ist Urlaubstag"


def test_sick_dates():
    assert blocked_reason(date(2026, 7, 10), "BW", "", "", "2026-07-10") == "Zieltag ist Krankheitstag"
