"""Shared test setup.

Qt must be put on the offscreen platform before PySide6 is imported by any test
module. ``conftest.py`` is loaded first, so doing it here is enough.
"""

from __future__ import annotations

import atexit
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.*=false")

import pytest

#: Set in ``pytest_sessionfinish`` and consumed by ``pytest_unconfigure``.
_exit_status: int | None = None


def pytest_sessionfinish(session, exitstatus):
    global _exit_status
    _exit_status = int(exitstatus)


def pytest_unconfigure(config):
    """Leave without letting Qt tear down the offscreen platform plugin.

    PySide6 6.12 occasionally aborts while the interpreter finalises, *after*
    every test has passed. That makes an otherwise green CI run report a
    failure. Register an ``atexit`` handler (LIFO, so it runs before Qt's) that
    ends the process with the status pytest computed.
    """
    if _exit_status is None:
        return
    if not (sys.platform.startswith("win")
            and os.environ.get("QT_QPA_PLATFORM") == "offscreen"):
        return

    reporter = config.pluginmanager.getplugin("terminalreporter")
    writer = getattr(reporter, "_tw", None)

    def leave() -> None:
        for stream in (sys.stdout, sys.stderr, sys.__stdout__, sys.__stderr__):
            try:
                if stream is not None:
                    stream.flush()
            except Exception:
                pass
        try:
            if writer is not None:
                writer.flush()
        except Exception:
            pass
        os._exit(_exit_status)

    atexit.register(leave)


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
    # ``processEvents`` alone does not flush DeferredDelete, so closed windows
    # would keep their whole widget tree alive and make every later restyle
    # slower. Flush them explicitly.
    from PySide6.QtCore import QCoreApplication, QEvent

    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    qapp.processEvents()
