from __future__ import annotations

import re

from app.models.schemas import RangeResult


def parse_range_selection(selection: str, max_items: int) -> RangeResult:
    if max_items < 1:
        raise ValueError("Gesamtumfang muss mindestens 1 sein.")
    raw = (selection or "").strip()
    if not raw:
        selected = list(range(1, max_items + 1))
        return RangeResult(selection="", selected=selected, total_items=max_items, is_full_range=True, count=len(selected))
    if not re.fullmatch(r"\d+(-\d+)?(\s*,\s*\d+(-\d+)?)*", raw):
        raise ValueError("Ungueltige Bereichssyntax. Beispiel: 1-5, 8, 10-12")
    values: set[int] = set()
    for part in [p.strip() for p in raw.split(",")]:
        if "-" in part:
            start_s, end_s = part.split("-", 1)
            start, end = int(start_s), int(end_s)
            if start > end:
                raise ValueError("Bereichsanfang darf nicht groesser als Bereichsende sein.")
            values.update(range(start, end + 1))
        else:
            values.add(int(part))
    if any(value <= 0 for value in values):
        raise ValueError("0 und negative Werte sind ungueltig.")
    if any(value > max_items for value in values):
        raise ValueError("Bereich liegt ausserhalb des verfuegbaren Umfangs.")
    selected = sorted(values)
    return RangeResult(selection=raw, selected=selected, total_items=max_items, is_full_range=len(selected) == max_items, count=len(selected))
