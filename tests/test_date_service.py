from datetime import date

from app.services.date_service import previous_workday


def test_monday_targets_friday():
    result = previous_workday(date(2026, 7, 13))
    assert result.target_date == date(2026, 7, 10)
    assert result.can_auto_run


def test_tuesday_targets_monday():
    result = previous_workday(date(2026, 7, 14))
    assert result.target_date == date(2026, 7, 13)


def test_weekend_has_no_auto_run():
    assert not previous_workday(date(2026, 7, 11)).can_auto_run
    assert not previous_workday(date(2026, 7, 12)).can_auto_run
