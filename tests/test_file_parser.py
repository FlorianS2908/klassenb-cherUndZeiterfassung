from app.services.file_parser import count_items, detect_file_type, extract_text


def test_txt_parser_extracts_selected_lines():
    from pathlib import Path

    path = Path(__file__).resolve().parent / "fixtures" / "sample.txt"
    assert detect_file_type(path) == ("Text", "Zeilen")
    assert count_items(path) == 3
    assert extract_text(path, [2]) == "b"
