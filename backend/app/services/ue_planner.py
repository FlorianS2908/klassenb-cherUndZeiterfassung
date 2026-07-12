from __future__ import annotations

from app.models.schemas import UeItem

DEFAULT_FORMATS = ["Aufgaben-/Uebungsbesprechung", "betreute Einzelarbeit"]


def extract_topics_from_text(text: str) -> list[str]:
    candidates = []
    for line in text.splitlines():
        clean = " ".join(line.strip("-#* \t").split())
        if len(clean) >= 8:
            candidates.append(clean[:120])
    if not candidates and text.strip():
        chunks = [text.strip()[idx : idx + 120] for idx in range(0, min(len(text.strip()), 720), 120)]
        candidates.extend(chunks)
    return candidates[:18] or ["Unterrichtsinhalte aus dem ausgewaehlten Material"]


def plan_nine_ue(text: str) -> tuple[list[str], float, list[UeItem]]:
    topics = extract_topics_from_text(text)
    items: list[UeItem] = []
    for index in range(9):
        topic = topics[index % len(topics)]
        items.append(UeItem(number=index + 1, content=f"{topic}", formats=DEFAULT_FORMATS.copy()))
    confidence = 0.78 if len(text.strip()) > 300 else 0.55
    return topics[:9], confidence, items
