from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_git_security_script_exists():
    assert (ROOT / "scripts" / "check_before_commit.py").exists()


def test_commit_and_push_batch_removed():
    assert not (ROOT / "commit_and_push.bat").exists()


def test_gitignore_contains_analysis_history():
    assert "analysis_history/" in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()


def test_gitignore_contains_api_key_patterns():
    lines = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "api_key*.txt" in lines
    assert "*.secret" in lines


def test_gitignore_contains_local_credential_patterns():
    lines = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "runtime/*" in lines
    assert "runtime/secrets/klassenbuch.credentials.json" in lines
    assert "*.credentials.json" in lines
    assert "*.secret.json" in lines
    assert "!runtime/secrets/klassenbuch.credentials.example.json" in lines


def test_example_credentials_file_contains_no_real_secret():
    content = (ROOT / "runtime" / "secrets" / "klassenbuch.credentials.example.json").read_text(encoding="utf-8")
    assert "name@example.com" in content
    assert "NICHT_ECHT" in content
    assert "Florian.Schaffer" not in content
    assert "florian.schaffer" not in content.lower()
