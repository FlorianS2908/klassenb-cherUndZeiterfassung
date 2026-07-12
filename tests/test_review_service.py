from app.services.review_service import ReviewService


def test_review_confirmation():
    service = ReviewService()
    state = service.confirm({"checked": True})
    assert state.confirmed
    assert state.confirmed_at is not None
