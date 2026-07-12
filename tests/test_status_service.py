from app.models.schemas import StepState
from app.services.status_service import StatusService


def test_status_progress_updates():
    service = StatusService()
    service.set_step("setup", StepState.success, "ok")
    assert service.status.progress > 0
