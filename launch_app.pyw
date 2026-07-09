"""Launch the Bambu dashboard without opening a console window"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
APP_FILE = PROJECT_DIR / "app.py"
VENV_PYTHONW = PROJECT_DIR / ".venv" / "Scripts" / "pythonw.exe"
VENV_PYTHON = PROJECT_DIR / ".venv" / "Scripts" / "python.exe"


def pick_python() -> Path:
    """Prefer the project virtual environment so installed packages are found"""
    if VENV_PYTHONW.exists():
        return VENV_PYTHONW
    if VENV_PYTHON.exists():
        return VENV_PYTHON
    return Path(sys.executable)


def main() -> int:
    if not APP_FILE.exists():
        return 1

    subprocess.Popen(
        [str(pick_python()), str(APP_FILE)],
        cwd=str(PROJECT_DIR),
        close_fds=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
