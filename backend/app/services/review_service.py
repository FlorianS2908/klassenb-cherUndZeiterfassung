from __future__ import annotations

from datetime import datetime

from app.models.schemas import ReviewState


class ReviewService:
    def __init__(self) -> None:
        self.state = ReviewState()

    def confirm(self, data: dict) -> ReviewState:
        self.state = ReviewState(confirmed=True, confirmed_at=datetime.now(), data=data)
        return self.state

    def reset(self) -> None:
        self.state = ReviewState()


review_service = ReviewService()
