"""Build the official UmbraForge release.

The build intermediates stay under ``build/``. One file is published:

    releases/UmbraForge-<timestamp>.zip

It contains exactly four items, matching the VoiceForge release pattern:

    UmbraForge-<version>-windows-x64.zip   portable package
    UmbraForge-Setup-<version>.exe         offline per-user installer
    README.md
    LICENSE

The package contains a frozen ``UmbraForge.exe`` so the target machine needs no
Python and no pip. The setup executable embeds the package zip as its payload.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from umbraforge import branding

VERSION = branding.VERSION
PLATFORM_TAG = "windows-x64"
PACKAGE_NAME = f"{branding.APP_NAME}-{VERSION}-{PLATFORM_TAG}.zip"
SETUP_NAME = f"{branding.APP_NAME}-Setup-{VERSION}.exe"
STAGE_FOLDER = branding.APP_NAME

BUILD = ROOT / "build"
RELEASES = ROOT / "releases"
STAGE_ROOT = BUILD / "stage"
PACKAGE_DIR = BUILD / "package"
SETUP_DIR = BUILD / "setup"
APP_DIR = BUILD / "app-dist"
APP_WORK = BUILD / "app-work"
APP_SPEC = BUILD / "app-spec"

PACKAGE_FILES = (
    "README.md",
    "LICENSE",
    "THIRD_PARTY_NOTICES.md",
    "Register UmbraForge Files.cmd",
    "register_file_types.ps1",
)
PACKAGE_DIRS = ("licenses",)

IS_WINDOWS = sys.platform.startswith("win")


def log(msg: str):
    print(f"[build] {msg}", flush=True)


def clean(path: Path):
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)


def build_app() -> Path:
    """Freeze the studio into a single windowed executable."""
    clean(APP_DIR)
    clean(APP_WORK)
    clean(APP_SPEC)
    APP_SPEC.mkdir(parents=True, exist_ok=True)
    python = Path(sys.executable)
    cmd = [
        str(python), "-m", "PyInstaller",
        "--noconfirm", "--clean", "--onefile", "--windowed",
        "--name", branding.APP_NAME,
        "--icon", str(ROOT / "assets" / "umbraforge.ico"),
        "--paths", str(ROOT / "src"),
        "--add-data", f"{ROOT / 'assets'};assets",
        "--distpath", str(APP_DIR),
        "--workpath", str(APP_WORK),
        "--specpath", str(APP_SPEC),
        str(ROOT / "desktop.py"),
    ]
    log("freezing the studio with PyInstaller...")
    subprocess.run(cmd, cwd=str(ROOT), check=True)
    produced = APP_DIR / f"{branding.APP_NAME}.exe"
    if not produced.exists():
        raise SystemExit(f"missing {produced}")
    log(f"app: {produced} ({produced.stat().st_size / 1024 / 1024:.1f} MB)")
    return produced


def stage_program(destination: Path, executable: Path):
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copy2(executable, destination / executable.name)
    for name in PACKAGE_FILES:
        source = ROOT / name
        if source.is_file():
            shutil.copy2(source, destination / name)
    for name in PACKAGE_DIRS:
        source = ROOT / name
        if source.is_dir():
            shutil.copytree(source, destination / name, dirs_exist_ok=True)
    assets = ROOT / "assets"
    if assets.is_dir():
        shutil.copytree(assets, destination / "assets", dirs_exist_ok=True)
    log(f"staged {destination}")


def make_package_zip(stage: Path, target: Path):
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        target.unlink()
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED,
                         compresslevel=6, allowZip64=True) as zf:
        for path in sorted(stage.rglob("*")):
            if path.is_file():
                zf.write(path, (Path(STAGE_FOLDER)
                                / path.relative_to(stage)).as_posix())
    log(f"package: {target} ({target.stat().st_size / 1024 / 1024:.1f} MB)")
    return target


def build_setup(payload: Path) -> Path:
    setup_work = BUILD / "setup-work"
    setup_dist = SETUP_DIR
    setup_spec = BUILD / "setup-spec"
    clean(setup_work)
    clean(setup_dist)
    clean(setup_spec)
    setup_spec.mkdir(parents=True, exist_ok=True)
    python = Path(sys.executable)
    cmd = [
        str(python), "-m", "PyInstaller",
        "--noconfirm", "--clean", "--onefile", "--windowed",
        "--name", SETUP_NAME.removesuffix(".exe"),
        "--icon", str(ROOT / "assets" / "umbraforge.ico"),
        "--add-data", f"{payload}{os.pathsep}.",
        "--paths", str(ROOT / "src"),
        "--distpath", str(setup_dist),
        "--workpath", str(setup_work),
        "--specpath", str(setup_spec),
        str(ROOT / "setup_entry.py"),
    ]
    log("building the setup executable...")
    subprocess.run(cmd, cwd=str(ROOT), check=True)
    produced = setup_dist / SETUP_NAME
    if not produced.exists():
        raise SystemExit(f"missing {produced}")
    log(f"setup: {produced} ({produced.stat().st_size / 1024 / 1024:.1f} MB)")
    return produced


def prune_releases(keep: Path | None = None) -> None:
    """Remove loose copies and older bundles so one official release remains."""
    RELEASES.mkdir(parents=True, exist_ok=True)
    stamp = re.compile(r"^UmbraForge-\d{8}-\d{6}\.zip$")
    for path in RELEASES.iterdir():
        if not path.is_file():
            continue
        if keep is not None and path.resolve() == keep.resolve():
            continue
        if path.name in (PACKAGE_NAME, SETUP_NAME) or stamp.match(path.name):
            path.unlink()
            log(f"removed superseded {path.name}")


def make_release(package: Path, setup_exe: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = RELEASES / f"{branding.APP_NAME}-{stamp}.zip"
    prune_releases(keep=target)
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED,
                         compresslevel=6, allowZip64=True) as zf:
        zf.write(package, package.name)
        zf.write(setup_exe, setup_exe.name)
        for name in ("README.md", "LICENSE", "THIRD_PARTY_NOTICES.md"):
            source = ROOT / name
            if source.exists():
                zf.write(source, name)
        licenses = ROOT / "licenses"
        if licenses.is_dir():
            for path in sorted(licenses.rglob("*")):
                if path.is_file():
                    zf.write(path, (Path("licenses")
                                    / path.relative_to(licenses)).as_posix())
    log(f"official release: {target} "
        f"({target.stat().st_size / 1024 / 1024:.1f} MB)")
    return target


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-setup", action="store_true",
                        help="build only the portable package zip")
    parser.add_argument("--skip-app", action="store_true",
                        help="reuse build/app-dist/UmbraForge.exe")
    parser.add_argument("--no-clean", action="store_true")
    args = parser.parse_args(argv)

    BUILD.mkdir(parents=True, exist_ok=True)
    if not args.no_clean:
        for folder in (STAGE_ROOT, PACKAGE_DIR):
            clean(folder)

    if args.skip_app:
        executable = APP_DIR / f"{branding.APP_NAME}.exe"
        if not executable.exists():
            raise SystemExit(f"no frozen app at {executable}")
    else:
        executable = build_app()

    stage = STAGE_ROOT / STAGE_FOLDER
    stage_program(stage, executable)

    PACKAGE_DIR.mkdir(parents=True, exist_ok=True)
    package = make_package_zip(stage, PACKAGE_DIR / PACKAGE_NAME)

    if args.skip_setup:
        return 0

    payload = BUILD / "payload.zip"
    if payload.exists():
        payload.unlink()
    shutil.copy2(package, payload)
    setup_exe = build_setup(payload)
    make_release(package, setup_exe)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
