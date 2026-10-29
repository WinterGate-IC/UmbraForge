"""No-console entry point for UmbraForge Setup."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INSTALLER = ROOT / "installer.py"


def alert(message: str) -> None:
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, message, "UmbraForge Setup", 0x10)
    except Exception:
        print(message, file=sys.stderr)


def interpreter() -> Path | None:
    for relative in (Path(".venv/Scripts/pythonw.exe"),
                     Path(".venv/Scripts/python.exe"),
                     Path(".venv/bin/python")):
        candidate = ROOT / relative
        if candidate.exists():
            return candidate
    return None


def main() -> int:
    if not INSTALLER.exists():
        alert(f"installer.py is missing from:\n{ROOT}")
        return 1
    python = interpreter() or Path(sys.executable)
    try:
        subprocess.Popen([str(python), str(INSTALLER), *sys.argv[1:]],
                         cwd=str(ROOT), close_fds=True)
    except Exception as exc:
        alert(f"Could not start UmbraForge Setup:\n{exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
