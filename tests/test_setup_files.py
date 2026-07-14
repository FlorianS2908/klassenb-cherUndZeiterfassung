from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_env_example_has_no_real_credentials():
    content = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "your_password" in content
    assert "KLASSENBUCH_PASSWORD=<" not in content
    assert "OPENAI_API_KEY=sk-" not in content


def test_gitignore_contains_env():
    assert ".env" in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()


def test_single_start_file_exists_and_checks_runtime():
    content = (ROOT / "KlassenbuchTool_starten.bat").read_text(encoding="utf-8")
    assert ".venv" in content
    assert "backend\\requirements.txt" in content
    assert "playwright install" in content
    assert "node-v%NODE_VERSION%-win-x64" in content
    assert "frontend\\node_modules" in content
    assert "http://localhost:5173/setup" in content


def test_old_start_files_were_removed():
    removed = [
        "install.bat",
        "start_tool.bat",
        "setup_env.bat",
        "dry_run.bat",
        "update_dependencies.bat",
        "commit_and_push.bat",
        "start_test.cmd",
        "start_test_worker.cmd",
    ]
    assert not [name for name in removed if (ROOT / name).exists()]


def test_readme_mentions_only_single_start_file():
    content = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "KlassenbuchTool_starten.bat" in content
    for old_name in [
        "install.bat",
        "start_tool.bat",
        "setup_env.bat",
        "dry_run.bat",
        "update_dependencies.bat",
        "commit_and_push.bat",
        "start_test.cmd",
        "start_test_worker.cmd",
    ]:
        assert old_name not in content
