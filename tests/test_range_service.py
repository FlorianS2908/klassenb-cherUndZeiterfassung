import pytest

from app.services.range_service import parse_range_selection


def test_empty_is_full_range():
    result = parse_range_selection("", 3)
    assert result.selected == [1, 2, 3]


def test_single_value():
    assert parse_range_selection("2", 5).selected == [2]


def test_range():
    assert parse_range_selection("1-3", 5).selected == [1, 2, 3]


def test_combination_deduped_sorted():
    assert parse_range_selection("3, 1-2, 2", 5).selected == [1, 2, 3]


@pytest.mark.parametrize("value", ["0", "-1", "1-", "3-1", "9"])
def test_invalid_ranges(value):
    with pytest.raises(ValueError):
        parse_range_selection(value, 5)
