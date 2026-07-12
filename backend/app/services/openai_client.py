from __future__ import annotations

from app.services.ue_planner import plan_nine_ue


async def analyze_topics(text: str) -> tuple[list[str], float, list]:
    # Optional OpenAI integration hook. The local deterministic planner keeps Dry-Run usable without an API key.
    return plan_nine_ue(text)
