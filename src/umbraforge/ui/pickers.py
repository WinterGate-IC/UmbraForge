"""Reusable picker dialogs for shapes, icons and emoji.

One dialog powers the Build rail's Browse buttons, the inspector and the
window's Insert menu, so search and category behaviour never drifts between
entry points.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .. import emojis, geometry
from .common import IconGrid, caption, hint, muted

_TITLES = {
    "shape": ("Pick a shape", "Browse every vector shape"),
    "icon": ("Pick an icon", "Browse every vector icon"),
    "emoji": ("Pick an emoji", "Search by name or keyword"),
}


class GlyphPickerDialog(QDialog):
    """A searchable, categorised grid of shapes, icons or emoji."""

    def __init__(self, kind: str, parent: QWidget | None = None,
                 current: str = ""):
        super().__init__(parent)
        self.kind = kind if kind in _TITLES else "shape"
        title, note = _TITLES[self.kind]
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(620, 540)
        self.selected = ""
        self._current = current
        self._grids: list[QWidget] = []
        self._empty: QWidget | None = None
        self._tail: QWidget | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)
        layout.addWidget(muted(note, True))

        row = QHBoxLayout()
        row.setSpacing(8)
        self.search = QLineEdit()
        self.search.setPlaceholderText(
            "Search emoji\u2026" if self.kind == "emoji"
            else f"Search {self.kind}s\u2026")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._refresh)
        row.addWidget(self.search, 1)
        self.category = QComboBox()
        self.category.addItem(self._all_label())
        for name in self._categories():
            self.category.addItem(name)
        self.category.currentTextChanged.connect(lambda _t: self._refresh())
        row.addWidget(self.category)
        layout.addLayout(row)

        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        body = QWidget()
        self.body_layout = QVBoxLayout(body)
        self.body_layout.setContentsMargins(2, 6, 4, 8)
        self.body_layout.setSpacing(8)
        self.body_layout.addStretch(1)
        area.setWidget(body)
        layout.addWidget(area, 1)

        footer = QHBoxLayout()
        footer.addStretch(1)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        footer.addWidget(cancel)
        layout.addLayout(footer)

        self._refresh()

    # ------------------------------------------------------------------ data
    def _all_label(self) -> str:
        return {"shape": "All shapes", "icon": "All icons",
                "emoji": "All emoji"}[self.kind]

    def _categories(self) -> list[str]:
        if self.kind == "shape":
            return geometry.shape_categories()
        if self.kind == "icon":
            return geometry.icon_categories()
        return emojis.categories()

    def _entries(self, needle: str) -> list[tuple[str, str]]:
        category = self.category.currentText()
        cat_filter = None if category in ("", self._all_label()) else category
        if self.kind == "shape":
            return geometry.shape_entries(cat_filter, needle)
        if self.kind == "icon":
            return geometry.icon_entries(cat_filter, needle)
        return [(item.char, item.name)
                for item in emojis.entries(cat_filter, needle)]

    # ---------------------------------------------------------------- widgets
    def _clear(self) -> None:
        for widget in self._grids:
            self.body_layout.removeWidget(widget)
            widget.setParent(None)
            widget.deleteLater()
        self._grids = []
        if self._empty is not None:
            self.body_layout.removeWidget(self._empty)
            self._empty.setParent(None)
            self._empty.deleteLater()
            self._empty = None
        if self._tail is not None:
            self.body_layout.removeWidget(self._tail)
            self._tail.setParent(None)
            self._tail.deleteLater()
            self._tail = None

    def _refresh(self) -> None:
        self._clear()
        needle = self.search.text().strip()
        entries = self._entries(needle)
        insert = self.body_layout.count() - 1
        if not entries:
            self._empty = hint("Nothing matches that filter. Try another word "
                               "or category.")
            self.body_layout.insertWidget(insert, self._empty)
            return
        label = caption(f"{len(entries)} "
                        f"result{'s' if len(entries) != 1 else ''}")
        self.body_layout.insertWidget(insert, label)
        self._grids.append(label)
        grid = IconGrid(entries, kind=self.kind, columns=8, icon_size=30)
        grid.chosen.connect(self._choose)
        self.body_layout.insertWidget(insert + 1, grid)
        self._grids.append(grid)
        self._tail = hint("Click a tile to use it. Search matches names and "
                          "keywords.")
        self.body_layout.insertWidget(insert + 2, self._tail)

    def _choose(self, key: str) -> None:
        if not key:
            return
        if self.kind == "emoji":
            emojis.remember(key)
        self.selected = key
        self.accept()


def pick_glyph(kind: str, parent: QWidget | None = None,
               current: str = "") -> str:
    """Show the picker and return the chosen key, or ``""`` if cancelled."""
    dialog = GlyphPickerDialog(kind, parent, current)
    try:
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return ""
        return dialog.selected
    finally:
        # The dialog owns hundreds of tile buttons; without this it would
        # linger (parented to the window) for the rest of the session.
        dialog.deleteLater()


__all__ = ["GlyphPickerDialog", "pick_glyph"]
