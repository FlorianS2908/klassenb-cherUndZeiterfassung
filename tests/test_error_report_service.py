from app.services.error_report_service import sanitize


def test_error_report_sanitizes_secrets():
    clean = sanitize({"password": "secret", "nested": {"api_key": "sk-test"}})
    assert clean["password"] == "<redacted>"
    assert clean["nested"]["api_key"] == "<redacted>"
