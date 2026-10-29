"""Application bootstrap: one QApplication, one window, one theme.

``umbraforge`` (the console entry point) and ``python -m umbraforge`` both end
up here, so startup behaviour stays identical however the app is launched.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox

from . import branding, extensions, licensing, theme
from .layers import Design
from .ui.main_window import MainWindow

ORGANISATION = "WinterGate"
ORGANISATION_DOMAIN = "wintergate.org"


def create_app(argv: list[str] | None = None) -> QApplication:
    """Create (or reuse) the QApplication with the studio theme applied."""
    arguments = list(sys.argv if argv is None else argv)
    app = QApplication.instance()
    if app is None:
        app = QApplication(arguments)
    app.setApplicationName(branding.APP_NAME)
    app.setApplicationDisplayName(branding.APP_NAME)
    app.setApplicationVersion(branding.VERSION)
    app.setOrganizationName(ORGANISATION)
    app.setOrganizationDomain(ORGANISATION_DOMAIN)
    app.setWindowIcon(branding.qicon())
    theme.apply(app)
    return app


def open_target(target: str) -> tuple[Design | None, Path | None, str]:
    """Try to open a design passed on the command line."""
    path = Path(target).expanduser()
    try:
        return Design.open(path), path, ""
    except Exception as exc:  # noqa: BLE001 - shown to the user
        return None, None, f"Could not open {path.name}:\n{exc}"


def main(argv: list[str] | None = None) -> int:
    """Start the studio. ``argv`` excludes the program name."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    if any(item in ("-h", "--help") for item in arguments):
        print("UmbraForge - a layered image and emblem studio")
        print("Usage: umbraforge [design.umbra]")
        return 0
    if any(item in ("-V", "--version") for item in arguments):
        print(f"{branding.APP_NAME} {branding.VERSION}")
        return 0
    if "--machine-id" in arguments:
        print(licensing.machine_id())
        return 0
    if "--license" in arguments:
        print(json.dumps(licensing.describe_status(), indent=2))
        return 0
    if "--install-license" in arguments:
        index = arguments.index("--install-license")
        if index + 1 >= len(arguments):
            print("usage: umbraforge --install-license <token|file>", file=sys.stderr)
            return 2
        value = arguments[index + 1]
        source = Path(value)
        token = source.read_text(encoding="utf-8").strip() if source.is_file() else value
        try:
            written = licensing.install_license(token)
        except (OSError, licensing.LicenseError) as exc:
            print(f"could not install licence: {exc}", file=sys.stderr)
            return 1
        print(f"installed licence at {written}")
        return 0

    extensions.load()
    app = create_app([sys.argv[0] if sys.argv else "umbraforge", *arguments])

    target = next((item for item in arguments if not item.startswith("-")), None)
    design: Design | None = None
    path: Path | None = None
    error = ""
    if target:
        design, path, error = open_target(target)

    window = MainWindow(design=design, path=path)
    window.show()
    if error:
        QMessageBox.warning(window, "Open design", error)
    return app.exec()


if __name__ == "__main__":  # pragma: no cover - manual launch
    raise SystemExit(main())
