"""Shared test setup.

Qt must be put on the offscreen platform before PySide6 is imported by any test
module. ``conftest.py`` is loaded first, so doing it here is enough.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.*=false")

import pytest


@pytest.fixture(scope="session")
def qapp():
    """One QApplication for the whole session (Qt allows no more than one)."""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication(["umbraforge-tests"])
    app.setApplicationName("UmbraForgeTests")
    app.setOrganizationName("WinterGate")
    yield app


@pytest.fixture()
def window(qapp, tmp_path):
    """A main window with settings redirected to a throwaway ini file."""
    from PySide6.QtCore import QSettings

    from umbraforge import theme
    from umbraforge.ui.main_window import MainWindow

    theme.apply(qapp)
    win = MainWindow()
    win.settings = QSettings(str(tmp_path / "settings.ini"),
                             QSettings.Format.IniFormat)
    yield win
    win._dirty = False
    win.close()
    win.deleteLater()
    qapp.processEvents()
