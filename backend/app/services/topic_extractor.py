from __future__ import annotations

from app.services.ue_planner import extract_topics_from_text


def extract_topics(text: str) -> list[str]:
    return extract_topics_from_text(text)
