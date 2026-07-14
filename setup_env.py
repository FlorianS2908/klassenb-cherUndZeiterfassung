from __future__ import annotations


def main() -> int:
    print("Das Setup laeuft jetzt in der Weboberflaeche.")
    print("Bitte nutze http://localhost:5173/setup.")
    print("start_tool.bat startet Backend und Frontend und oeffnet das Setup automatisch, wenn .env fehlt.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
