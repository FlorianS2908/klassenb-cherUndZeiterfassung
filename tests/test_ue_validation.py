from app.models.schemas import UeItem
from app.services.ue_planner import plan_nine_ue
from app.services.validation import validate_ue_items


def test_planner_creates_exactly_nine_ue():
    _, confidence, items = plan_nine_ue("Datenbanken\nSQL\nNormalisierung\nJoins")
    assert len(items) == 9
    assert confidence >= 0


def test_max_two_formats():
    items = [UeItem(number=i, content="Inhalt", formats=["A", "B"]) for i in range(1, 10)]
    assert validate_ue_items(items)


def test_required_learning_format_present_by_default():
    _, _, items = plan_nine_ue("Datenbanken\nSQL\nNormalisierung\nJoins")
    assert all("Aufgaben-/Uebungsbesprechung" in item.formats for item in items)
    assert validate_ue_items(items) == []
