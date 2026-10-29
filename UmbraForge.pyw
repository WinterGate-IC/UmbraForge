"""Double-click launcher for Windows (no console window).

Same as ``desktop.py``, but kept as ``.pyw`` so Explorer uses ``pythonw.exe``.
If Explorer starts this with a Python that does not have the project's
dependencies, it re-launches itself with the local ``.venv`` interpreter.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"


def _prefer_virtualenv() -> None:
    """Restart under the project venv when double-clicked with another Python."""
    if os.environ.get("UMBRAFORGE_LAUNCHED") == "1":
        return
    candidates = (
        ROOT / ".venv" / "Scripts" / "pythonw.exe",
        ROOT / ".venv" / "Scripts" / "python.exe",
    )
    target = next((path for path in candidates if path.exists()), None)
    if target is None:
        return
    try:
        if Path(sys.executable).resolve() == target.resolve():
            return
    except OSError:
        pass

    import subprocess

    environment = os.environ.copy()
    environment["UMBRAFORGE_LAUNCHED"] = "1"
    subprocess.Popen(
        [str(target), str(Path(__file__).resolve()), *sys.argv[1:]],
        cwd=str(ROOT),
        env=environment,
        close_fds=True,
    )
    raise SystemExit(0)


_prefer_virtualenv()

if SRC.is_dir() and str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from umbraforge.app import main  # noqa: E402 - path set up above

if __name__ == "__main__":
    raise SystemExit(main())
