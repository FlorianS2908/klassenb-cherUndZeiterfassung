from __future__ import annotations

import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> int:
    env = os.environ.copy()
    backend = subprocess.Popen([sys.executable, "-m", "app.main"], cwd=ROOT / "backend", env=env)
    frontend = subprocess.Popen(["npm", "run", "dev", "--", "--host", "127.0.0.1"], cwd=ROOT / "frontend", env=env, shell=True)
    time.sleep(5)
    webbrowser.open("http://localhost:5173")
    try:
        backend.wait()
        frontend.wait()
    except KeyboardInterrupt:
        backend.terminate()
        frontend.terminate()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
