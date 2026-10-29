"""Frozen entry point for UmbraForge Setup."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if (ROOT / "src").is_dir():
    sys.path.insert(0, str(ROOT / "src"))

from umbraforge import branding  # noqa: E402
from umbraforge.installer_ui import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
