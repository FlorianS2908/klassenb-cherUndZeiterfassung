from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.diagnostic_export_service import export_klassenbuch_diagnostic  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Exportiert einen sanitisieren Klassenbuch-Diagnosebericht.")
    parser.add_argument("--run-id", default=None, help="Optionaler Diagnose-Run, sonst wird der neueste Lauf exportiert.")
    args = parser.parse_args()
    try:
        result = export_klassenbuch_diagnostic(args.run_id)
    except FileNotFoundError as exc:
        print(str(exc))
        return 1
    print(f"Exportiert nach {result['export_folder']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
