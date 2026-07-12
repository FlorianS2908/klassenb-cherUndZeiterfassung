from app.services.screenshot_service import screenshot_name


def test_screenshot_name_contains_run_and_step():
    name = screenshot_name("RUN-1", "login")
    assert name.startswith("RUN-1_")
    assert name.endswith("_login.png")
