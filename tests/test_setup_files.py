from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_env_example_has_no_real_credentials():
    content = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "your_password" in content
    assert "KLASSENBUCH_PASSWORD=<" not in content
    assert "OPENAI_API_KEY=sk-" not in content


def test_gitignore_contains_env():
    assert ".env" in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()


def test_start_tool_checks_venv():
    content = (ROOT / "start_tool.bat").read_text(encoding="utf-8")
    assert ".venv" in content


def test_dry_run_forces_dry_run():
    content = (ROOT / "dry_run.bat").read_text(encoding="utf-8")
    assert "FORCE_DRY_RUN=true" in content
