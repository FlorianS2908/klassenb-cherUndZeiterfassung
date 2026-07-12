from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_IGNORES = {
    ".env",
    "uploads/",
    "screenshots/",
    "logs/",
    "error_reports/",
    "analysis_history/",
    "node_modules/",
    ".venv/",
    "dist/",
    "__pycache__/",
}
BLOCKED_PREFIXES = (
    "uploads/",
    "screenshots/",
    "logs/",
    "error_reports/",
    "analysis_history/",
    "node_modules/",
    ".venv/",
    "dist/",
)
SECRET_PATTERNS = [
    re.compile(r"(?m)^[ \t]*KLASSENBUCH_PASSWORD[ \t]*=[ \t]*.+"),
    re.compile(r"(?m)^[ \t]*TIMEBUTLER_PASSWORD[ \t]*=[ \t]*.+"),
    re.compile(r"(?m)^[ \t]*OPENAI_API_KEY[ \t]*=[ \t]*sk-"),
    re.compile(r"github_pat_[A-Za-z0-9_]+"),
    re.compile(r"ghp_[A-Za-z0-9_]+"),
    re.compile(r"\bPasswort\b\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(r"\bpassword\b\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(r"\bapi_key\b\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(r"\btoken\b\s*[:=]\s*\S+", re.IGNORECASE),
]
ALLOW_SECRET_WORD_FILES = {
    "README.md",
    ".env.example",
    "setup_env.py",
    "scripts/check_before_commit.py",
    "tests/test_git_security_check.py",
    "tests/test_setup_files.py",
}


def run_git(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True, check=False)


def fail(message: str) -> int:
    print(f"FEHLER: {message}")
    return 1


def staged_files() -> list[str]:
    result = run_git(["diff", "--cached", "--name-only"])
    if result.returncode != 0:
        return []
    return [line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()]


def tracked_files() -> list[str]:
    result = run_git(["ls-files"])
    if result.returncode != 0:
        return []
    return [line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()]


def file_text(path: str) -> str:
    try:
        return (ROOT / path).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def main() -> int:
    gitignore = ROOT / ".gitignore"
    if not gitignore.exists():
        return fail(".gitignore fehlt.")
    ignore_lines = set(gitignore.read_text(encoding="utf-8", errors="ignore").splitlines())
    missing = sorted(REQUIRED_IGNORES - ignore_lines)
    if missing:
        return fail(".gitignore enthaelt nicht alle Pflichtmuster: " + ", ".join(missing))

    all_index_files = set(staged_files()) | set(tracked_files())
    blocked = [path for path in all_index_files if path == ".env" or path.startswith(BLOCKED_PREFIXES)]
    if blocked:
        return fail("Sensible oder generierte Dateien sind im Git-Index: " + ", ".join(sorted(blocked)))

    candidates = sorted(set(staged_files()) or set(tracked_files()))
    for path in candidates:
        if path == ".env" or path.startswith(BLOCKED_PREFIXES) or Path(path).name.endswith((".png", ".jpg", ".jpeg", ".zip")):
            return fail(f"Sensible/generierte Datei darf nicht committed werden: {path}")
        if path in ALLOW_SECRET_WORD_FILES:
            continue
        text = file_text(path)
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                return fail(f"Moegliches Secret in {path}: Muster {pattern.pattern}")

    print("Git-Sicherheitspruefung erfolgreich.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
