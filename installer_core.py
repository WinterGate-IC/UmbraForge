"""UmbraForge installer engine (per-user, no admin)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path

from umbraforge import branding

APP_NAME = branding.APP_NAME
VERSION = branding.VERSION
CONFIG_NAME = "install.json"
PAYLOAD_NAME = "payload.zip"
RUNTIME_DIR = "runtime"

ROOT_FILES = (
    "desktop.py", "UmbraForge.pyw", "run.cmd",
    "README.md", "LICENSE", "pyproject.toml",
    "requirements.txt", "requirements-ai.txt",
    "Register UmbraForge Files.cmd", "register_file_types.ps1",
)
ROOT_DIRS = ("src",)
IGNORE = shutil.ignore_patterns(
    ".venv", "__pycache__", "*.pyc", "*.pyo", ".cache", ".git", ".idea",
    "build", "dist", "releases", "tools", "tests", "*.log",
)

IS_WINDOWS = sys.platform.startswith("win")


def payload_archive() -> Path | None:
    if not getattr(sys, "frozen", False):
        return None
    bundled = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    for candidate in (bundled / PAYLOAD_NAME,
                      Path(sys.executable).parent / PAYLOAD_NAME):
        if candidate.is_file():
            return candidate
    return None


def source_root() -> Path:
    here = Path(__file__).resolve()
    if here.parent.name == "src":
        return here.parents[1]
    if here.parent.name == "umbraforge":
        return here.parents[2]
    return here.parent


def copytree(src: Path, dst: Path) -> None:
    shutil.copytree(src, dst, ignore=IGNORE, dirs_exist_ok=True)


def install(app_dir: Path, payload: Path | None = None,
            create_shortcuts: bool = True, quiet: bool = False) -> dict:
    app_dir = Path(app_dir).expanduser().resolve()
    app_dir.mkdir(parents=True, exist_ok=True)

    if payload and payload.exists():
        with zipfile.ZipFile(payload) as zf:
            zf.extractall(app_dir)
    else:
        root = source_root()
        for name in ROOT_FILES:
            s = root / name
            if s.is_file():
                shutil.copy2(s, app_dir / name)
        for name in ROOT_DIRS:
            s = root / name
            if s.is_dir():
                copytree(s, app_dir / name)

    config = {
        "app": APP_NAME,
        "version": VERSION,
        "installed_at": datetime.utcnow().isoformat() + "Z",
        "app_dir": str(app_dir),
        "bundled": payload is not None and payload.exists(),
    }
    (app_dir / CONFIG_NAME).write_text(json.dumps(config, indent=2), encoding="utf-8")
    return config


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--auto", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--no-shortcuts", action="store_true")
    parser.add_argument("--app-dir")
    parser.add_argument("--data-dir")
    args = parser.parse_args(argv)

    app_dir = Path(args.app_dir).expanduser() if args.app_dir else (
        Path.home() / "AppData" / "Local" / "Programs" / APP_NAME)
    payload = payload_archive()
    install(app_dir, payload, create_shortcuts=not args.no_shortcuts,
            quiet=args.quiet or args.auto)
    if not args.quiet:
        print("installed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
