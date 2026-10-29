"""Run UmbraForge straight from a source checkout.

    python desktop.py
    python desktop.py path\\to\\design.umbra

No packaging or install step required; the ``src`` folder is put on the import
path for this process only.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if SRC.is_dir() and str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from umbraforge.app import main  # noqa: E402 - path set up above

if __name__ == "__main__":
    raise SystemExit(main())
