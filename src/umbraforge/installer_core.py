"""UmbraForge installer engine (per-user, no admin).

The release ships a frozen ``UmbraForge.exe`` inside a package zip. This module
extracts that package into the chosen folder, strips the archive's top-level
``UmbraForge/`` directory, records the install and creates Desktop / Start Menu
shortcuts for the current user. It also still works from a source checkout so
``python -m umbraforge.installer_core`` remains useful during development.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
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
ROOT_DIRS = ("src", "assets")
IGNORE = shutil.ignore_patterns(
    ".venv", "__pycache__", "*.pyc", "*.pyo", ".cache", ".git", ".idea",
    "build", "dist", "releases", "tools", "tests", "*.log",
)

IS_WINDOWS = sys.platform.startswith("win")


def default_app_dir() -> Path:
    return Path.home() / "AppData" / "Local" / "Programs" / APP_NAME


def default_data_dir() -> Path:
    return branding.saves_dir()


def payload_archive() -> Path | None:
    """Locate ``payload.zip`` bundled beside a frozen setup executable."""
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


def _safe_members(archive: zipfile.ZipFile, destination: Path) -> list[tuple]:
    """Return (member, relative path) pairs with the archive wrapper removed."""
    names = [name.replace("\\", "/") for name in archive.namelist() if name]
    tops = {name.split("/", 1)[0] for name in names if name.strip("/")}
    prefix = ""
    if len(tops) == 1:
        candidate = next(iter(tops))
        if all(name == candidate or name.startswith(candidate + "/")
               for name in names):
            prefix = candidate + "/"

    members: list[tuple] = []
    for info in archive.infolist():
        name = info.filename.replace("\\", "/")
        if prefix:
            if name.rstrip("/") == prefix.rstrip("/"):
                continue
            if not name.startswith(prefix):
                continue
            name = name[len(prefix):]
        if not name or name.endswith("/"):
            continue
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts:
            continue
        target = destination / relative
        members.append((info, relative))
    return members


def _extract_payload(payload: Path, app_dir: Path) -> None:
    """Extract a package zip, flattening its single top-level folder."""
    with zipfile.ZipFile(payload) as archive:
        for info, relative in _safe_members(archive, app_dir):
            target = app_dir / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as source, open(target, "wb") as sink:
                shutil.copyfileobj(source, sink)


def _copy_source(app_dir: Path) -> None:
    root = source_root()
    for name in ROOT_FILES:
        source = root / name
        if source.is_file():
            shutil.copy2(source, app_dir / name)
    for name in ROOT_DIRS:
        source = root / name
        if source.is_dir():
            copytree(source, app_dir / name)


def launcher_path(app_dir: Path) -> Path | None:
    for name in (f"{APP_NAME}.exe", f"{APP_NAME}.pyw", "run.cmd"):
        candidate = app_dir / name
        if candidate.is_file():
            return candidate
    return None


def _shortcut_targets() -> list[Path]:
    profile = Path(os.environ.get("USERPROFILE", str(Path.home())))
    appdata = Path(os.environ.get("APPDATA", str(profile / "AppData" / "Roaming")))
    return [
        profile / "Desktop" / f"{APP_NAME}.lnk",
        appdata / "Microsoft" / "Windows" / "Start Menu" / "Programs"
        / f"{APP_NAME}.lnk",
    ]


def _create_shortcuts(app_dir: Path) -> list[str]:
    """Create per-user shortcuts. Returns the .lnk paths that were written."""
    if not IS_WINDOWS:
        return []
    launcher = launcher_path(app_dir)
    if launcher is None:
        return []

    icon = app_dir / "assets" / "umbraforge.ico"
    icon_value = str(icon) if icon.is_file() else str(launcher)
    targets = _shortcut_targets()
    for target in targets:
        target.parent.mkdir(parents=True, exist_ok=True)

    statements = ["$ws = New-Object -ComObject WScript.Shell"]
    for target in targets:
        statements.append(
            f"$s = $ws.CreateShortcut('{_ps_quote(target)}');"
            f"$s.TargetPath = '{_ps_quote(launcher)}';"
            f"$s.WorkingDirectory = '{_ps_quote(app_dir)}';"
            f"$s.IconLocation = '{_ps_quote(icon_value)}';"
            f"$s.Description = '{APP_NAME} studio';"
            "$s.Save()")
    script = "; ".join(statements)
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive",
             "-ExecutionPolicy", "Bypass", "-Command", script],
            check=True, capture_output=True, text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.SubprocessError):
        return []
    return [str(target) for target in targets if target.is_file()]


def _ps_quote(value) -> str:
    return str(value).replace("'", "''")


def _write_uninstaller(app_dir: Path, shortcuts: list[str]) -> Path:
    """Write a small per-user uninstaller that keeps saved projects."""
    shortcuts_block = "\r\n".join(
        f'del /f /q "{path}" >nul 2>nul' for path in shortcuts)
    content = (
        "@echo off\r\n"
        "rem Remove UmbraForge. Editable saves in Documents are kept.\r\n"
        "setlocal\r\n"
        "echo This removes the UmbraForge program folder:\r\n"
        f'echo   {app_dir}\r\n'
        "echo Your saved projects in Documents\\UmbraForge are kept.\r\n"
        "choice /c YN /m \"Remove UmbraForge\"\r\n"
        "if errorlevel 2 exit /b 1\r\n"
        f"{shortcuts_block}\r\n"
        "start \"\" /min cmd /c \"timeout /t 2 /nobreak >nul "
        f"& rmdir /s /q \\\"{app_dir}\\\"\"\r\n"
        "exit /b 0\r\n"
    )
    target = app_dir / "Uninstall UmbraForge.cmd"
    target.write_text(content, encoding="utf-8")
    return target


def install(app_dir: Path, payload: Path | None = None,
            create_shortcuts: bool = True, quiet: bool = False,
            data_dir: Path | None = None) -> dict:
    app_dir = Path(app_dir).expanduser().resolve()
    app_dir.mkdir(parents=True, exist_ok=True)

    if payload and payload.exists():
        _extract_payload(payload, app_dir)
    else:
        _copy_source(app_dir)

    libraries = Path(data_dir).expanduser().resolve() if data_dir else (
        default_data_dir())
    libraries.mkdir(parents=True, exist_ok=True)

    shortcuts: list[str] = []
    if create_shortcuts:
        shortcuts = _create_shortcuts(app_dir)
    uninstaller = _write_uninstaller(app_dir, shortcuts)

    config = {
        "app": APP_NAME,
        "version": VERSION,
        "installed_at": datetime.now(timezone.utc).isoformat(),
        "app_dir": str(app_dir),
        "data_dir": str(libraries),
        "launcher": str(launcher_path(app_dir) or ""),
        "shortcuts": shortcuts,
        "uninstaller": str(uninstaller),
        "bundled": bool(payload and payload.exists()),
    }
    (app_dir / CONFIG_NAME).write_text(
        json.dumps(config, indent=2), encoding="utf-8")
    if not quiet:
        print(f"installed {APP_NAME} {VERSION} to {app_dir}")
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

    app_dir = Path(args.app_dir).expanduser() if args.app_dir else default_app_dir()
    payload = payload_archive()
    install(app_dir, payload, create_shortcuts=not args.no_shortcuts,
            quiet=args.quiet or args.auto,
            data_dir=Path(args.data_dir) if args.data_dir else None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
