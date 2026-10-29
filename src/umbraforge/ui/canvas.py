"""The drawing surface.

A custom widget rather than a QGraphicsView: it keeps precise control over
normalized geometry, high-DPI preview rendering and the selection chrome. The
canvas renders a screen-resolution copy of the design and draws selection,
grid and guides on top, so exports never contain UI.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPoint, QPointF, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPen,
    QPolygonF,
    QTransform,
)
from PySide6.QtWidgets import QWidget

from .. import renderer, theme
from ..layers import Design, Layer

MARGIN = 46


class CanvasView(QWidget):
    selectionChanged = Signal(str)
    changed = Signal(str, str)
    editTextRequested = Signal(str)
    deleteRequested = Signal()
    duplicateRequested = Signal()
    contextMenuRequested = Signal(QPoint, str)
    zoomChanged = Signal(float)
    panChanged = Signal()

    def __init__(self, design_getter, parent: QWidget | None = None):
        super().__init__(parent)
        self._design = design_getter
        self._scale = 0.5
        self._fit_scale = 0.5
        self._offset = QPointF(0, 0)
        self._fit_mode = True
        self._dirty = True
        self._preview = None
        self._preview_size = QSize(0, 0)
        self._drag: dict | None = None
        self._guides: list[tuple[str, float]] = []
        self._grid = False
        self._space = False
        self._panning = False
        self._pan_origin = QPointF()
        self._pan_start = QPointF()
        self._dragging_live = False

        self.setMinimumSize(420, 380)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self._render_timer = QTimer(self)
        self._render_timer.setInterval(8)
        self._render_timer.setSingleShot(True)
        self._render_timer.timeout.connect(self.update)

    # ---------------------------------------------------------------- state
    def design(self) -> Design:
        return self._design()

    def set_grid(self, enabled: bool) -> None:
        self._grid = bool(enabled)
        self.update()

    def grid_enabled(self) -> bool:
        return self._grid

    def refresh(self, reset: bool = False) -> None:
        self._dirty = True
        if reset:
            self._fit_mode = True
            if self.width() > 10 and self.height() > 10:
                self.fit()
            else:
                self.update()
        else:
            self.update()

    def invalidate_preview(self) -> None:
        self._dirty = True
        self.update()

    def zoom(self) -> float:
        return self._scale

    def zoom_percent(self) -> int:
        return int(round(self._scale * 100))

    def fit(self) -> None:
        design = self.design()
        available_w = max(40, self.width() - MARGIN * 2)
        available_h = max(40, self.height() - MARGIN * 2)
        self._scale = max(0.02, min(12.0,
                                   min(available_w / design.width,
                                       available_h / design.height)))
        self._fit_scale = self._scale
        self._fit_mode = True
        self._center()
        self._dirty = True
        self.zoomChanged.emit(self._scale)
        self.update()

    def actual_size(self) -> None:
        self._zoom_about(QPointF(self.width() / 2, self.height() / 2), 1.0)

    def zoom_in(self) -> None:
        self._zoom_about(QPointF(self.width() / 2, self.height() / 2),
                         self._scale * 1.25)

    def zoom_out(self) -> None:
        self._zoom_about(QPointF(self.width() / 2, self.height() / 2),
                         self._scale / 1.25)

    def _center(self) -> None:
        design = self.design()
        width = design.width * self._scale
        height = design.height * self._scale
        self._offset = QPointF((self.width() - width) / 2,
                               (self.height() - height) / 2)

    def _zoom_about(self, anchor: QPointF, scale: float) -> None:
        design = self.design()
        scale = max(0.02, min(14.0, scale))
        before = (anchor - self._offset) / self._scale
        self._scale = scale
        self._offset = anchor - QPointF(before.x() * scale, before.y() * scale)
        self._fit_mode = abs(scale - self._fit_scale) < 0.0005
        self._dirty = True
        self.zoomChanged.emit(scale)
        self.update()

    def canvas_rect(self) -> QRectF:
        design = self.design()
        return QRectF(self._offset.x(), self._offset.y(),
                      design.width * self._scale, design.height * self._scale)

    def to_design(self, point: QPointF) -> QPointF:
        return QPointF((point.x() - self._offset.x()) / self._scale,
                       (point.y() - self._offset.y()) / self._scale)

    def to_screen(self, x: float, y: float) -> QPointF:
        return QPointF(self._offset.x() + x * self._scale,
                       self._offset.y() + y * self._scale)

    def _layer_screen_corners(self, layer: Layer) -> list[QPointF]:
        design = self.design()
        corners = renderer.layer_corners(layer, design.width, design.height)
        return [self.to_screen(point.x(), point.y()) for point in corners]

    # ---------------------------------------------------------------- paint
    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        background = QLinearGradient(0, 0, 0, self.height())
        background.setColorAt(0.0, QColor("#0a0a11"))
        background.setColorAt(1.0, QColor("#06060a"))
        painter.fillRect(self.rect(), background)

        rect = self.canvas_rect()
        for spread, alpha in ((14, 10), (8, 16), (3, 26)):
            shadow = rect.adjusted(-spread, -spread + 6, spread, spread + 8)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(0, 0, 0, alpha))
            painter.drawRoundedRect(shadow, 4, 4)

        painter.save()
        painter.setClipRect(rect)
        self._paint_checkerboard(painter, rect)
        if self._dirty or self._preview is None:
            self._render_preview(rect)
        if self._preview is not None:
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
            painter.drawImage(rect, self._preview)
        painter.restore()

        painter.setPen(QPen(QColor(theme.BORDER), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(rect)

        if self._grid:
            self._paint_grid(painter, rect)

        design = self.design()
        if not design.layers:
            painter.setPen(QColor(theme.TEXT_MUTED))
            font = QFont("Segoe UI", 11)
            painter.setFont(font)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter,
                             "Empty canvas\nPick a template or add a shape")

        self._paint_selection(painter)
        self._paint_guides(painter)

    def _paint_checkerboard(self, painter: QPainter, rect: QRectF) -> None:
        tile = 12.0
        painter.fillRect(rect, QColor(theme.CHECKER_A))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(theme.CHECKER_B))
        rows = int(math.ceil(rect.height() / tile))
        columns = int(math.ceil(rect.width() / tile))
        for row in range(rows):
            for column in range(columns):
                if (row + column) % 2:
                    continue
                painter.drawRect(QRectF(rect.x() + column * tile,
                                        rect.y() + row * tile, tile, tile))

    def _render_preview(self, rect: QRectF) -> None:
        design = self.design()
        dpr = self.devicePixelRatioF()
        target_w = rect.width() * dpr
        if self._drag is not None:
            target_w *= 0.8
        target_w = max(240.0, min(float(design.width), target_w * 1.15))
        target_h = target_w * design.height / design.width
        width, height = max(1, int(round(target_w))), max(1, int(round(target_h)))
        self._preview = renderer.render_design(design, width, height)
        self._preview_size = QSize(width, height)
        self._dirty = False

    def _paint_grid(self, painter: QPainter, rect: QRectF) -> None:
        painter.save()
        painter.setClipRect(rect)
        pen = QPen(QColor(255, 255, 255, 18), 1)
        painter.setPen(pen)
        for index in range(1, 10):
            x = rect.x() + rect.width() * index / 10.0
            y = rect.y() + rect.height() * index / 10.0
            painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))
            painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))
        painter.setPen(QPen(QColor(255, 122, 61, 48), 1, Qt.PenStyle.DashLine))
        painter.drawLine(QPointF(rect.center().x(), rect.top()),
                         QPointF(rect.center().x(), rect.bottom()))
        painter.drawLine(QPointF(rect.left(), rect.center().y()),
                         QPointF(rect.right(), rect.center().y()))
        painter.restore()

    def _paint_selection(self, painter: QPainter) -> None:
        layer = self.design().active
        if layer is None or not layer.visible:
            return
        corners = self._layer_screen_corners(layer)
        color = QColor(theme.ACCENT) if not layer.locked else QColor(theme.TEXT_DISABLED)
        pen = QPen(color, 1.4, Qt.PenStyle.DashLine)
        pen.setDashPattern([5, 4])
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPolygon(QPolygonF(corners))
        if layer.locked:
            return

        painter.setPen(QPen(QColor(theme.WINDOW), 1.4))
        painter.setBrush(QColor(theme.TEXT))
        for point in corners:
            painter.drawRect(QRectF(point.x() - 4.5, point.y() - 4.5, 9, 9))

        rotate_point = self._rotate_handle_position(corners)
        if rotate_point is not None:
            top_mid = QPointF((corners[0].x() + corners[1].x()) / 2,
                              (corners[0].y() + corners[1].y()) / 2)
            painter.setPen(QPen(QColor(theme.ACCENT), 1.2))
            painter.drawLine(top_mid, rotate_point)
            painter.setBrush(QColor(theme.ACCENT))
            painter.setPen(QPen(QColor(theme.WINDOW), 1.4))
            painter.drawEllipse(rotate_point, 5.5, 5.5)

    def _rotate_handle_position(self, corners: list[QPointF]) -> QPointF | None:
        if len(corners) != 4:
            return None
        center = QPointF(sum(p.x() for p in corners) / 4,
                         sum(p.y() for p in corners) / 4)
        top_mid = QPointF((corners[0].x() + corners[1].x()) / 2,
                          (corners[0].y() + corners[1].y()) / 2)
        dx, dy = top_mid.x() - center.x(), top_mid.y() - center.y()
        length = math.hypot(dx, dy) or 1.0
        return QPointF(top_mid.x() + dx / length * 26,
                       top_mid.y() + dy / length * 26)

    def _paint_guides(self, painter: QPainter) -> None:
        if not self._guides:
            return
        painter.save()
        pen = QPen(QColor(255, 122, 61, 190), 1, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        rect = self.canvas_rect()
        for orientation, position in self._guides:
            if orientation == "v":
                painter.drawLine(QPointF(position, rect.top() - 12),
                                 QPointF(position, rect.bottom() + 12))
            else:
                painter.drawLine(QPointF(rect.left() - 12, position),
                                 QPointF(rect.right() + 12, position))
        painter.restore()

    # ---------------------------------------------------------------- mouse
    def _handle_at(self, point: QPointF) -> tuple[str, int] | None:
        layer = self.design().active
        if layer is None or layer.locked or not layer.visible:
            return None
        corners = self._layer_screen_corners(layer)
        for index, corner in enumerate(corners):
            if math.hypot(point.x() - corner.x(), point.y() - corner.y()) <= 8.0:
                return ("corner", index)
        handle = self._rotate_handle_position(corners)
        if handle is not None and math.hypot(point.x() - handle.x(),
                                             point.y() - handle.y()) <= 9.0:
            return ("rotate", -1)
        return None

    def mousePressEvent(self, event) -> None:  # noqa: N802
        self.setFocus()
        pos = QPointF(event.position())
        if (event.button() == Qt.MouseButton.MiddleButton
                or (event.button() == Qt.MouseButton.LeftButton and self._space)):
            self._panning = True
            self._pan_origin = pos
            self._pan_start = QPointF(self._offset)
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return
        if event.button() != Qt.MouseButton.LeftButton:
            return

        layer = self.design().active
        handle = self._handle_at(pos)
        if layer is not None and handle is not None:
            if handle[0] == "rotate":
                design = self.design()
                center = self.to_screen(layer.cx * design.width,
                                        layer.cy * design.height)
                angle = math.degrees(math.atan2(pos.y() - center.y(),
                                                pos.x() - center.x()))
                self._drag = {"mode": "rotate", "layer": layer, "center": center,
                              "start_angle": angle, "start_rotation": layer.rotation,
                              "moved": False}
            else:
                self._drag = self._begin_scale(layer, pos, handle[1])
            return

        design = self.design()
        canvas_point = self.to_design(pos)
        hit = renderer.layer_at(design, canvas_point.x(), canvas_point.y(),
                                design.width, design.height)
        if hit is None:
            if design.selected:
                design.selected = None
                self.selectionChanged.emit("")
            self.update()
            return
        if design.selected != hit.id:
            design.selected = hit.id
            self.selectionChanged.emit(hit.id)
        if hit.locked:
            self.update()
            return
        self._drag = {"mode": "move", "layer": hit,
                      "start": canvas_point,
                      "start_x": hit.x, "start_y": hit.y,
                      "moved": False}
        self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def _begin_scale(self, layer: Layer, point: QPointF, handle: int) -> dict:
        design = self.design()
        center = QPointF(layer.cx * design.width, layer.cy * design.height)
        rect = QRectF(layer.x * design.width, layer.y * design.height,
                      layer.w * design.width, layer.h * design.height)
        radians = math.radians(layer.rotation)
        cos_a, sin_a = math.cos(radians), math.sin(radians)

        def to_local(world: QPointF) -> QPointF:
            dx, dy = world.x() - center.x(), world.y() - center.y()
            return QPointF(center.x() + dx * cos_a + dy * sin_a,
                           center.y() - dx * sin_a + dy * cos_a)

        corners = [rect.topLeft(), rect.topRight(), rect.bottomRight(),
                   rect.bottomLeft()]
        fixed_index = {0: 2, 1: 3, 2: 0, 3: 1}[handle]
        return {
            "mode": "scale", "layer": layer, "handle": handle,
            "center": center, "rect": rect, "rotation": layer.rotation,
            "cos": cos_a, "sin": sin_a,
            "fixed_local": corners[fixed_index],
            "fixed_world": corners[fixed_index],
            "start_local": to_local(self.to_design(point)),
            "to_local": to_local,
            "start_geom": (layer.x, layer.y, layer.w, layer.h),
            "moved": False,
        }

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        pos = QPointF(event.position())
        if self._panning:
            self._offset = self._pan_start + (pos - self._pan_origin)
            self._fit_mode = False
            self.update()
            self.panChanged.emit()
            return
        if self._drag is None:
            self._update_cursor(pos)
            return

        drag = self._drag
        layer: Layer = drag["layer"]
        design = self.design()
        if drag["mode"] == "move":
            point = self.to_design(pos)
            dx = (point.x() - drag["start"].x()) / design.width
            dy = (point.y() - drag["start"].y()) / design.height
            new_x = drag["start_x"] + dx
            new_y = drag["start_y"] + dy
            new_x, new_y = self._snap(layer, new_x, new_y)
            layer.x, layer.y = new_x, new_y
            drag["moved"] = True
        elif drag["mode"] == "rotate":
            center = drag["center"]
            angle = math.degrees(math.atan2(pos.y() - center.y(),
                                            pos.x() - center.x()))
            rotation = drag["start_rotation"] + (angle - drag["start_angle"])
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                rotation = round(rotation / 15.0) * 15.0
            layer.rotation = ((rotation + 180) % 360) - 180
            drag["moved"] = True
        elif drag["mode"] == "scale":
            self._update_scale(drag, pos, bool(
                event.modifiers() & Qt.KeyboardModifier.ShiftModifier))
            drag["moved"] = True
        self._dragging_live = True
        self._dirty = True
        self._render_timer.start()
        self.update()

    def _update_scale(self, drag: dict, screen_pos: QPointF, lock_ratio: bool) -> None:
        layer: Layer = drag["layer"]
        design = self.design()
        local = drag["to_local"](self.to_design(screen_pos))
        fixed: QPointF = drag["fixed_local"]
        handle = drag["handle"]
        rect: QRectF = drag["rect"]
        minimum = max(6.0, min(design.width, design.height) * 0.008)

        if handle in (1, 2):
            left, right = fixed.x(), local.x()
        else:
            left, right = local.x(), fixed.x()
        if handle in (2, 3):
            top, bottom = fixed.y(), local.y()
        else:
            top, bottom = local.y(), fixed.y()

        if right < left:
            left, right = right, left
        if bottom < top:
            top, bottom = bottom, top
        width = max(minimum, right - left)
        height = max(minimum, bottom - top)
        if lock_ratio:
            ratio = (rect.width() / rect.height()) if rect.height() else 1.0
            if width / height > ratio:
                width = height * ratio
            else:
                height = width / ratio
            width = max(minimum, width)
            height = max(minimum, height)

        # Re-anchor against the fixed corner after clamping.
        if handle in (1, 2):
            left = fixed.x()
            right = left + width
        else:
            right = fixed.x()
            left = right - width
        if handle in (2, 3):
            top = fixed.y()
            bottom = top + height
        else:
            bottom = fixed.y()
            top = bottom - height

        new_local_center = QPointF((left + right) / 2, (top + bottom) / 2)
        cos_a, sin_a = drag["cos"], drag["sin"]
        old_center: QPointF = drag["center"]
        dx = new_local_center.x() - old_center.x()
        dy = new_local_center.y() - old_center.y()
        center_world = QPointF(
            old_center.x() + dx * cos_a - dy * sin_a,
            old_center.y() + dx * sin_a + dy * cos_a)
        layer.w = width / design.width
        layer.h = height / design.height
        layer.x = (center_world.x() - width / 2) / design.width
        layer.y = (center_world.y() - height / 2) / design.height

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if self._panning:
            self._panning = False
            self._update_cursor(QPointF(event.position()))
            return
        if self._drag is None:
            return
        drag = self._drag
        self._drag = None
        self._dragging_live = False
        self._guides = []
        self._dirty = True
        self.update()
        if drag.get("moved"):
            label = {"move": "Move layer", "scale": "Resize layer",
                     "rotate": "Rotate layer"}.get(drag["mode"], "Transform")
            self.changed.emit(label, f"{drag['mode']}-{drag['layer'].id}")
        self._update_cursor(QPointF(event.position()))

    def _snap(self, layer: Layer, x: float, y: float) -> tuple[float, float]:
        design = self.design()
        threshold = 7.0 / max(0.01, self._scale)
        tol_x = threshold / design.width
        tol_y = threshold / design.height
        self._guides = []
        center_x = x + layer.w / 2
        center_y = y + layer.h / 2
        candidates_x = [0.5] + [item.cx for item in design.layers
                                if item.id != layer.id]
        candidates_y = [0.5] + [item.cy for item in design.layers
                                if item.id != layer.id]
        for candidate in candidates_x:
            if abs(center_x - candidate) <= tol_x:
                x = candidate - layer.w / 2
                self._guides.append(("v", candidate * design.width))
                break
        for candidate in candidates_y:
            if abs(center_y - candidate) <= tol_y:
                y = candidate - layer.h / 2
                self._guides.append(("h", candidate * design.height))
                break
        return x, y

    def _update_cursor(self, pos: QPointF) -> None:
        if self._space:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            return
        layer = self.design().active
        handle = self._handle_at(pos)
        if handle is not None:
            if handle[0] == "rotate":
                self.setCursor(Qt.CursorShape.CrossCursor)
            elif handle[1] in (1, 3):
                self.setCursor(Qt.CursorShape.SizeBDiagCursor)
            else:
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            return
        if layer is not None:
            point = self.to_design(pos)
            design = self.design()
            hit = renderer.layer_at(design, point.x(), point.y(),
                                    design.width, design.height)
            if hit is not None and not hit.locked:
                self.setCursor(Qt.CursorShape.OpenHandCursor)
                return
        self.setCursor(Qt.CursorShape.ArrowCursor)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        if event.button() != Qt.MouseButton.LeftButton:
            return
        design = self.design()
        point = self.to_design(QPointF(event.position()))
        hit = renderer.layer_at(design, point.x(), point.y(),
                                design.width, design.height)
        if hit is not None:
            design.selected = hit.id
            self.selectionChanged.emit(hit.id)
            if hit.kind == "text":
                self.editTextRequested.emit(hit.id)

    def wheelEvent(self, event) -> None:  # noqa: N802
        delta = event.angleDelta().y()
        if not delta:
            return
        factor = 1.0018 ** delta
        self._zoom_about(QPointF(event.position()), self._scale * factor)
        event.accept()

    # ------------------------------------------------------------- keyboard
    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Space:
            self._space = True
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            return
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.deleteRequested.emit()
            return
        if event.key() == Qt.Key.Key_Escape:
            self.design().selected = None
            self.selectionChanged.emit("")
            self.update()
            return
        if (event.modifiers() & Qt.KeyboardModifier.ControlModifier
                and event.key() == Qt.Key.Key_D):
            self.duplicateRequested.emit()
            return
        layer = self.design().active
        if layer is None or layer.locked:
            super().keyPressEvent(event)
            return
        step = (10.0 if event.modifiers() & Qt.KeyboardModifier.ShiftModifier
                else 1.0)
        dx = dy = 0.0
        if event.key() == Qt.Key.Key_Left:
            dx = -step
        elif event.key() == Qt.Key.Key_Right:
            dx = step
        elif event.key() == Qt.Key.Key_Up:
            dy = -step
        elif event.key() == Qt.Key.Key_Down:
            dy = step
        else:
            super().keyPressEvent(event)
            return
        layer.x += dx / self.design().width
        layer.y += dy / self.design().height
        self.changed.emit("Nudge layer", f"nudge-{layer.id}")
        self._dirty = True
        self.update()

    def keyReleaseEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Space:
            self._space = False
            self._update_cursor(QPointF(self.mapFromGlobal(
                self.cursor().pos())))
            return
        super().keyReleaseEvent(event)

    # ---------------------------------------------------------- context menu
    def contextMenuEvent(self, event) -> None:  # noqa: N802
        design = self.design()
        point = self.to_design(QPointF(event.pos()))
        hit = renderer.layer_at(design, point.x(), point.y(),
                                design.width, design.height)
        if hit is not None and design.selected != hit.id:
            design.selected = hit.id
            self.selectionChanged.emit(hit.id)
        self.contextMenuRequested.emit(event.globalPos(),
                                       hit.id if hit else "")
        event.accept()

    # --------------------------------------------------------------- resize
    def resizeEvent(self, event) -> None:  # noqa: N802
        if self._fit_mode:
            self.fit()
        else:
            self._dirty = True
        super().resizeEvent(event)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        if self._fit_mode:
            self.fit()
