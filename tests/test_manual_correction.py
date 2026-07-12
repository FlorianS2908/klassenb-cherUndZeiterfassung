from app.models.schemas import UeItem
from app.services.correction_service import validate_klassenbuch_correction


def test_manual_correction_requires_content():
    items = [UeItem(number=i, content="Inhalt") for i in range(1, 9)] + [UeItem(number=9, content="")]
    assert validate_klassenbuch_correction(items)
