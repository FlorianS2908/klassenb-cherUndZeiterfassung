from app.services.validation import final_action_allowed


def test_no_submit_when_auto_submit_false():
    allowed, _ = final_action_allowed(False, True, [])
    assert not allowed


def test_no_submit_without_review():
    allowed, _ = final_action_allowed(True, False, [])
    assert not allowed


def test_submit_allowed_only_with_all_gates():
    allowed, _ = final_action_allowed(True, True, [])
    assert allowed
