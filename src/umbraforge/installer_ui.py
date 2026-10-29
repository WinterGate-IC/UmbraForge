"""Simple UmbraForge Setup UI (mirrors VoiceForge pattern)."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QDialog, QHBoxLayout, QLabel, QMessageBox,
    QPushButton, QVBoxLayout, QFileDialog,
)

from . import branding
from . import installer_core


class SetupDialog(QDialog):
    def __init__(self, argv=None):
        super().__init__()
        self.setWindowTitle(f"{branding.APP_NAME} Setup")
        self.setFixedSize(480, 260)
        self.setWindowIcon(branding.qicon())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 16)
        layout.setSpacing(10)

        title = QLabel(f"Install {branding.APP_NAME}")
        title.setStyleSheet("font-size: 16px; font-weight: 700;")
        layout.addWidget(title)

        self.path_label = QLabel(str(installer_core.default_app_dir()))
        self.path_label.setWordWrap(True)
        layout.addWidget(self.path_label)

        self.data_label = QLabel(
            f"Saves: {installer_core.default_data_dir()}")
        self.data_label.setObjectName("muted")
        self.data_label.setWordWrap(True)
        layout.addWidget(self.data_label)

        browse = QPushButton("Choose folder...")
        browse.clicked.connect(self._browse)
        layout.addWidget(browse)

        layout.addStretch(1)
        row = QHBoxLayout()
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        install_btn = QPushButton("Install")
        install_btn.setDefault(True)
        install_btn.clicked.connect(self._install)
        row.addStretch(1)
        row.addWidget(cancel)
        row.addWidget(install_btn)
        layout.addLayout(row)

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, "Install location", self.path_label.text())
        if d:
            self.path_label.setText(d)

    def _install(self):
        try:
            installer_core.install(Path(self.path_label.text()),
                                   installer_core.payload_archive(),
                                   create_shortcuts=True, quiet=False)
            QMessageBox.information(self, "Setup", f"{branding.APP_NAME} installed.")
            self.accept()
        except Exception as exc:
            QMessageBox.critical(self, "Setup", str(exc))


def main(argv=None):
    if argv and ("--auto" in argv or "--quiet" in argv):
        return installer_core.main(argv)
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName(branding.APP_NAME)
    app.setWindowIcon(branding.qicon())
    d = SetupDialog(argv)
    return 0 if d.exec() == QDialog.DialogCode.Accepted else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
