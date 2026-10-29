"""Layer stack panel.

Top of the list is the top of the stack. Checkboxes toggle visibility, the
footer reorders, duplicates, locks or removes the selected layer.
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .. import theme
from ..layers import Design, Layer
from .common import caption, draw_layer_icon

KIND_LABEL = {"shape": "Shape", "icon": "Icon", "text": "Text", "image": "Image"}


class LayersPanel(QWidget):
    selectionChanged = Signal(str)
    changed = Signal(str, str)

    def __init__(self, design_getter, parent: QWidget | None = None):
        super().__init__(parent)
        self._design = design_getter
        self._guard = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        header = QHBoxLayout()
        header.setSpacing(8)
        header.addWidget(caption("Layers"))
        self.count = QLabel("0")
        self.count.setObjectName("pill")
        header.addWidget(self.count)
        header.addStretch(1)
        layout.addLayout(header)

        self.list = QListWidget()
        self.list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list.setIconSize(QSize(24, 24))
        self.list.setSpacing(1)
        self.list.currentItemChanged.connect(self._on_current)
        self.list.itemChanged.connect(self._on_item_changed)
        self.list.itemDoubleClicked.connect(self._on_double_click)
        self.list.customContextMenuRequested.connect(self._context_menu)
        layout.addWidget(self.list, 1)

        self.empty = QLabel("No layers yet.\nAdd a shape, icon or text\nfrom the Build panel.")
        self.empty.setObjectName("hint")
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty.setVisible(False)
        layout.addWidget(self.empty)

        footer = QHBoxLayout()
        footer.setSpacing(2)
        self.up_btn = self._tool("Up", "Move layer forward", "\u2191")
        self.down_btn = self._tool("Down", "Move layer back", "\u2193")
        self.copy_btn = self._tool("Copy", "Duplicate layer  (Ctrl+D)", "\u29c9")
        self.lock_btn = self._tool("Lock", "Lock or unlock this layer", "\u25a3")
        self.delete_btn = self._tool("Delete", "Delete layer  (Del)", "\u2715")
        self.up_btn.clicked.connect(lambda: self._move(1))
        self.down_btn.clicked.connect(lambda: self._move(-1))
        self.copy_btn.clicked.connect(self.duplicate)
        self.lock_btn.clicked.connect(self.toggle_lock)
        self.delete_btn.clicked.connect(self.delete)
        for button in (self.up_btn, self.down_btn, self.copy_btn,
                       self.lock_btn, self.delete_btn):
            footer.addWidget(button)
        footer.addStretch(1)
        layout.addLayout(footer)

        self.refresh()

    def _tool(self, name: str, tip: str, text: str) -> QToolButton:
        button = QToolButton()
        button.setText(text)
        button.setToolTip(tip)
        button.setFixedSize(28, 26)
        button.setObjectName("ghost")
        return button

    # ---------------------------------------------------------------- data
    def design(self) -> Design:
        return self._design()

    def refresh(self) -> None:
        design = self.design()
        self._guard = True
        self.list.clear()
        for layer in design.top_first():
            item = QListWidgetItem(self._icon(layer), layer.name)
            item.setData(Qt.ItemDataRole.UserRole, layer.id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if layer.visible
                               else Qt.CheckState.Unchecked)
            item.setSizeHint(QSize(0, 33))
            item.setToolTip(self._tooltip(layer))
            if layer.locked:
                item.setForeground(QColor(theme.TEXT_MUTED))
            elif not layer.visible:
                item.setForeground(QColor(theme.TEXT_DISABLED))
            self.list.addItem(item)
        active = design.selected
        for row in range(self.list.count()):
            item = self.list.item(row)
            if item.data(Qt.ItemDataRole.UserRole) == active:
                self.list.setCurrentRow(row)
                break
        self._guard = False
        self.count.setText(str(len(design.layers)))
        self.empty.setVisible(not design.layers)
        self._sync_buttons()

    def sync_selection(self) -> None:
        active = self.design().selected
        self._guard = True
        for row in range(self.list.count()):
            item = self.list.item(row)
            if item.data(Qt.ItemDataRole.UserRole) == active:
                self.list.setCurrentRow(row)
                break
        else:
            self.list.setCurrentRow(-1)
        self._guard = False
        self._sync_buttons()

    def _sync_buttons(self) -> None:
        design = self.design()
        layer = design.active
        has = layer is not None
        index = design.layers.index(layer) if layer else -1
        self.up_btn.setEnabled(has and index < len(design.layers) - 1)
        self.down_btn.setEnabled(has and index > 0)
        self.copy_btn.setEnabled(has and len(design.layers) < 120)
        self.delete_btn.setEnabled(has)
        self.lock_btn.setEnabled(has)
        self.lock_btn.setToolTip("Unlock this layer" if layer and layer.locked
                                 else "Lock this layer")

    def _icon(self, layer: Layer) -> QIcon:
        color = theme.TEXT if layer.visible else theme.TEXT_DISABLED
        icon = draw_layer_icon(layer.kind, 26, color)
        if layer.locked:
            pixmap = icon.pixmap(26, 26)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(theme.ACCENT))
            painter.drawEllipse(17, 16, 9, 9)
            painter.setBrush(QColor(theme.WINDOW))
            painter.drawRect(19, 20, 5, 4)
            painter.drawArc(19, 16, 5, 6, 0, 180 * 16)
            painter.end()
            return QIcon(pixmap)
        return icon

    @staticmethod
    def _tooltip(layer: Layer) -> str:
        kind = KIND_LABEL.get(layer.kind, layer.kind.title())
        state = []
        if not layer.visible:
            state.append("hidden")
        if layer.locked:
            state.append("locked")
        suffix = f" \u00b7 {', '.join(state)}" if state else ""
        return (f"{layer.name}\n{kind} \u00b7 "
                f"{layer.w * 100:.0f}% \u00d7 {layer.h * 100:.0f}% "
                f"\u00b7 {layer.opacity * 100:.0f}% opacity{suffix}")

    # -------------------------------------------------------------- signals
    def _on_current(self, current, _previous) -> None:
        if self._guard or current is None:
            return
        layer_id = current.data(Qt.ItemDataRole.UserRole)
        if layer_id and layer_id != self.design().selected:
            self.selectionChanged.emit(layer_id)

    def _on_item_changed(self, item: QListWidgetItem) -> None:
        if self._guard:
            return
        layer = self.design().layer(item.data(Qt.ItemDataRole.UserRole))
        if layer is None:
            return
        checked = item.checkState() == Qt.CheckState.Checked
        if layer.visible != checked:
            layer.visible = checked
            self._guard = True
            item.setForeground(QColor(theme.TEXT if checked else theme.TEXT_DISABLED))
            item.setIcon(self._icon(layer))
            self._guard = False
            self.changed.emit("Show/hide layer", f"visible-{layer.id}")

    def _on_double_click(self, item: QListWidgetItem) -> None:
        self.rename()

    def _context_menu(self, point) -> None:
        item = self.list.itemAt(point)
        if item is None:
            return
        layer_id = item.data(Qt.ItemDataRole.UserRole)
        self.design().selected = layer_id
        self.refresh()
        self.selectionChanged.emit(layer_id)
        menu = QMenu(self)
        menu.addAction("Rename\u2026", self.rename)
        menu.addAction("Duplicate", self.duplicate)
        menu.addSeparator()
        menu.addAction("Bring forward", lambda: self._move(1))
        menu.addAction("Send backward", lambda: self._move(-1))
        menu.addAction("Bring to front", lambda: self._to_end(True))
        menu.addAction("Send to back", lambda: self._to_end(False))
        menu.addSeparator()
        menu.addAction("Unlock layer" if self.design().active and self.design().active.locked
                       else "Lock layer", self.toggle_lock)
        menu.addAction("Delete", self.delete)
        menu.exec(self.list.viewport().mapToGlobal(point))

    # ------------------------------------------------------------- actions
    def rename(self) -> None:
        layer = self.design().active
        if layer is None:
            return
        name, ok = QInputDialog.getText(self, "Rename layer", "Layer name:",
                                        text=layer.name)
        if not ok or not name.strip():
            return
        layer.name = name.strip()
        self.refresh()
        self.changed.emit("Rename layer", f"rename-{layer.id}")

    def _move(self, delta: int) -> None:
        layer = self.design().active
        if layer is None:
            return
        if self.design().move(layer.id, delta):
            self.refresh()
            self.changed.emit("Reorder layers", "reorder")

    def _to_end(self, front: bool) -> None:
        layer = self.design().active
        if layer is None:
            return
        changed = (self.design().to_front(layer.id) if front
                   else self.design().to_back(layer.id))
        if changed:
            self.refresh()
            self.changed.emit("Reorder layers", "reorder")

    def duplicate(self) -> None:
        layer = self.design().duplicate()
        if layer is None:
            return
        self.refresh()
        self.selectionChanged.emit(layer.id)
        self.changed.emit("Duplicate layer", "duplicate")

    def delete(self) -> None:
        design = self.design()
        layer = design.active
        if layer is None:
            return
        design.remove(layer.id)
        self.refresh()
        self.selectionChanged.emit(design.selected or "")
        self.changed.emit("Delete layer", "delete")

    def toggle_lock(self) -> None:
        layer = self.design().active
        if layer is None:
            return
        layer.locked = not layer.locked
        self.refresh()
        self.changed.emit("Lock layer", f"lock-{layer.id}")
