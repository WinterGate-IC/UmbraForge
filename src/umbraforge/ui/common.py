"""Small shared widgets: colour swatches, slider rows and icon tiles."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QIcon,
    QPainter,
    QPainterPath,
    QPixmap,
    QTransform,
)
from PySide6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSlider,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .. import geometry, theme


def caption(text: str) -> QLabel:
    label = QLabel(text.upper())
    label.setObjectName("sectionLabel")
    return label


def hint(text: str, wrap: bool = True) -> QLabel:
    label = QLabel(text)
    label.setObjectName("hint")
    label.setWordWrap(wrap)
    return label


def muted(text: str, wrap: bool = False) -> QLabel:
    label = QLabel(text)
    label.setObjectName("muted")
    label.setWordWrap(wrap)
    return label


def rule() -> QFrame:
    line = QFrame()
    line.setObjectName("rule")
    line.setFixedHeight(1)
    line.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    return line


class ElidedLabel(QLabel):
    """A one-line label that shortens itself instead of widening the rail.

    The Build rail is only a few hundred pixels wide, but project paths,
    template notes and image names can be far longer. A plain ``QLabel``
    reports its full width as a *minimum*, which forced the whole panel
    wider than its viewport so the right-hand side was clipped away. This
    label reports a zero minimum, paints an ellipsis and keeps the full
    value in its tooltip.
    """

    def __init__(self, text: str = "",
                 mode: Qt.TextElideMode = Qt.TextElideMode.ElideRight,
                 parent: QWidget | None = None):
        super().__init__(parent)
        self._full_text = ""
        self._mode = mode
        self.setSizePolicy(QSizePolicy.Policy.Ignored,
                           QSizePolicy.Policy.Preferred)
        self.setMinimumWidth(0)
        self.setText(text)

    def setText(self, text: str) -> None:  # noqa: N802 (Qt naming)
        self._full_text = text or ""
        super().setText(self._full_text)
        self.setToolTip(self._full_text)
        self._elide()

    def text(self) -> str:  # noqa: N802 (Qt naming)
        return self._full_text

    def sizeHint(self) -> QSize:  # noqa: N802 (Qt naming)
        hint = super().sizeHint()
        return QSize(min(hint.width(), 120), hint.height())

    def minimumSizeHint(self) -> QSize:  # noqa: N802 (Qt naming)
        return QSize(0, super().minimumSizeHint().height())

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        super().resizeEvent(event)
        self._elide()

    def _elide(self) -> None:
        available = self.width() - 2
        if available <= 8:
            return
        metrics = QFontMetrics(self.font())
        shown = metrics.elidedText(self._full_text, self._mode, available)
        if shown != super().text():
            super().setText(shown)


class ColorButton(QPushButton):
    colorChanged = Signal(str)

    def __init__(self, color: str = "#ffffff", title: str = "Colour",
                 parent: QWidget | None = None):
        super().__init__(parent)
        self._color = color or "#ffffff"
        self._title = title
        self.setFixedHeight(26)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(self._choose)
        self.set_color(self._color)

    def color(self) -> str:
        return self._color

    def set_color(self, color: str, emit: bool = False) -> None:
        value = color or "#000000"
        if not QColor(value).isValid():
            value = "#000000"
        self._color = value
        readable = QColor(value).lightness() > 150
        self.setText(value.upper())
        self.setStyleSheet(
            f"QPushButton {{ background: {value}; color: "
            f"{'#101017' if readable else '#f3f1f8'}; border: 1px solid "
            f"{theme.BORDER_HOVER}; border-radius: 6px; font-size: 10px; "
            f"font-weight: 700; padding: 2px 8px; text-align: left; }}"
            f"QPushButton:hover {{ border-color: {theme.ACCENT}; }}")
        if emit:
            self.colorChanged.emit(value)

    def _choose(self) -> None:
        start = QColor(self._color)
        chosen = QColorDialog.getColor(
            start, self, self._title,
            QColorDialog.ColorDialogOption.DontUseNativeDialog)
        if chosen.isValid():
            self.set_color(chosen.name(), emit=True)


class SliderField(QWidget):
    valueChanged = Signal(float)

    def __init__(self, label: str, minimum: float, maximum: float,
                 value: float, *, decimals: int = 0, suffix: str = "",
                 step: float | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self._minimum = float(minimum)
        self._maximum = float(maximum)
        self._decimals = int(decimals)
        self._guard = False

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 1, 0, 1)
        row.setSpacing(8)
        self.name = QLabel(label)
        self.name.setFixedWidth(64)
        self.name.setStyleSheet(f"color: {theme.TEXT_MUTED};")
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 1000)
        self.spin = QDoubleSpinBox()
        self.spin.setDecimals(self._decimals)
        self.spin.setSingleStep(step if step is not None else (
            10 ** -self._decimals if self._decimals else 1))
        self.spin.setRange(minimum, maximum)
        self.spin.setSuffix(suffix)
        self.spin.setFixedWidth(72)
        self.spin.setAlignment(Qt.AlignmentFlag.AlignRight)
        row.addWidget(self.name)
        row.addWidget(self.slider, 1)
        row.addWidget(self.spin)

        self.slider.valueChanged.connect(self._slider_moved)
        self.spin.valueChanged.connect(self._spin_changed)
        self.set_value(value)

    def value(self) -> float:
        return float(self.spin.value())

    def set_value(self, value: float) -> None:
        self._guard = True
        self.spin.setValue(float(value))
        span = self._maximum - self._minimum
        position = 0.0 if span <= 0 else (float(value) - self._minimum) / span
        self.slider.setValue(int(round(max(0.0, min(1.0, position)) * 1000)))
        self._guard = False

    def _slider_moved(self, position: int) -> None:
        if self._guard:
            return
        value = self._minimum + (position / 1000.0) * (self._maximum - self._minimum)
        self._guard = True
        self.spin.setValue(value)
        self._guard = False
        self.valueChanged.emit(float(self.spin.value()))

    def _spin_changed(self, value: float) -> None:
        if self._guard:
            return
        span = self._maximum - self._minimum
        position = 0.0 if span <= 0 else (value - self._minimum) / span
        self._guard = True
        self.slider.setValue(int(round(max(0.0, min(1.0, position)) * 1000)))
        self._guard = False
        self.valueChanged.emit(float(value))


class NumberField(QWidget):
    valueChanged = Signal(float)

    def __init__(self, label: str, value: float, minimum: float,
                 maximum: float, *, decimals: int = 1, suffix: str = "",
                 step: float = 1.0, parent: QWidget | None = None):
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 1, 0, 1)
        row.setSpacing(8)
        self.name = QLabel(label)
        self.name.setFixedWidth(64)
        self.name.setStyleSheet(f"color: {theme.TEXT_MUTED};")
        self.spin = QDoubleSpinBox()
        self.spin.setDecimals(decimals)
        self.spin.setRange(minimum, maximum)
        self.spin.setSingleStep(step)
        self.spin.setSuffix(suffix)
        self.spin.setValue(value)
        self.spin.setAlignment(Qt.AlignmentFlag.AlignRight)
        row.addWidget(self.name)
        row.addStretch(1)
        row.addWidget(self.spin)
        self.spin.valueChanged.connect(lambda v: self.valueChanged.emit(float(v)))

    def value(self) -> float:
        return float(self.spin.value())

    def set_value(self, value: float) -> None:
        self.spin.blockSignals(True)
        self.spin.setValue(float(value))
        self.spin.blockSignals(False)


class PercentField(NumberField):
    def __init__(self, label: str, value: float, minimum: float = -200.0,
                 maximum: float = 300.0, parent: QWidget | None = None):
        super().__init__(label, value, minimum, maximum, decimals=1,
                         suffix=" %", step=1.0, parent=parent)


def combo_box(items: list[tuple[str, str]], current: str = "",
              parent: QWidget | None = None) -> QComboBox:
    box = QComboBox(parent)
    for key, label in items:
        box.addItem(label, key)
    index = box.findData(current)
    if index >= 0:
        box.setCurrentIndex(index)
    return box


def draw_shape_icon(kind: str, size: int = 28, color: str = theme.TEXT_MUTED) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(color))
    margin = size * 0.14
    inner = size - margin * 2
    path = QTransform().translate(margin, margin).scale(inner, inner).map(
        geometry.shape_path(kind))
    painter.drawPath(path)
    painter.end()
    return QIcon(pixmap)


def draw_layer_icon(kind: str, size: int = 26, color: str = theme.TEXT_MUTED) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(color))
    margin = size * 0.18
    inner = size - margin * 2
    if kind == "shape":
        painter.drawEllipse(QRectF(margin, margin, inner, inner))
    elif kind == "icon":
        path = QTransform().translate(margin, margin).scale(inner, inner).map(
            geometry.icon_path("star"))
        painter.drawPath(path)
    elif kind == "text":
        font = QFont("Bahnschrift", int(size * 0.72))
        font.setWeight(QFont.Weight.Black)
        painter.setFont(font)
        painter.setPen(QColor(color))
        painter.drawText(QRectF(0, -size * 0.08, size, size),
                         Qt.AlignmentFlag.AlignCenter, "T")
    else:
        frame = QRectF(margin, margin + size * 0.06, inner, inner * 0.86)
        painter.setPen(QColor(color))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(frame, 3, 3)
        painter.setBrush(QColor(color))
        painter.drawEllipse(QPointF(margin + inner * 0.28,
                                    margin + size * 0.06 + inner * 0.26),
                            size * 0.07, size * 0.07)
        path = QPainterPath()
        path.moveTo(frame.left() + inner * 0.10, frame.bottom() - inner * 0.12)
        path.lineTo(frame.left() + inner * 0.42, frame.top() + inner * 0.38)
        path.lineTo(frame.left() + inner * 0.62, frame.bottom() - inner * 0.24)
        path.lineTo(frame.right() - inner * 0.10, frame.top() + inner * 0.52)
        path.lineTo(frame.right() - inner * 0.10, frame.bottom() - inner * 0.12)
        path.closeSubpath()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(path)
    painter.end()
    return QIcon(pixmap)


class IconGrid(QWidget):
    """A grid of square icon buttons that reflows to fit the rail."""

    chosen = Signal(str)

    CELL = 42
    GAP = 6

    def __init__(self, entries: list[tuple[str, str]], kind: str = "shape",
                 columns: int = 6, icon_size: int = 28,
                 parent: QWidget | None = None):
        super().__init__(parent)
        from PySide6.QtWidgets import QGridLayout

        self._preferred_columns = max(1, int(columns))
        self._columns = self._preferred_columns
        self._buttons: list[QToolButton] = []
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(self.GAP)
        for index, (key, label) in enumerate(entries):
            button = QToolButton()
            button.setFixedSize(self.CELL, self.CELL)
            button.setToolTip(label)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setIcon(draw_shape_icon(key, icon_size) if kind == "shape"
                           else _icon_icon(key, icon_size))
            button.setIconSize(QSize(icon_size, icon_size))
            button.setStyleSheet(
                f"QToolButton {{ background: {theme.PANEL_ALT}; border: 1px "
                f"solid {theme.BORDER}; border-radius: 8px; }}"
                f"QToolButton:hover {{ border-color: {theme.ACCENT}; "
                f"background: {theme.RAISED}; }}")
            button.clicked.connect(lambda _=False, k=key: self.chosen.emit(k))
            self._grid.addWidget(button, index // self._columns,
                                 index % self._columns)
            self._buttons.append(button)
        self._grid.setColumnStretch(self._columns, 1)
        # The layout width must never dictate the rail width: report no
        # minimum so the scroll body can stay inside its viewport, then
        # pick however many columns actually fit.
        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Fixed)

    def sizeHint(self) -> QSize:  # noqa: N802 (Qt naming)
        return QSize(0, super().sizeHint().height())

    def minimumSizeHint(self) -> QSize:  # noqa: N802 (Qt naming)
        return QSize(0, super().minimumSizeHint().height())

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        super().resizeEvent(event)
        self._reflow()

    def columns(self) -> int:
        return self._columns

    def _reflow(self) -> None:
        if not self._buttons:
            return
        width = max(self.CELL, self.width())
        fitted = (width + self.GAP) // (self.CELL + self.GAP)
        columns = max(1, min(int(fitted), len(self._buttons)))
        if columns == self._columns:
            return
        self._columns = columns
        for index, button in enumerate(self._buttons):
            self._grid.addWidget(button, index // columns, index % columns)
        for column in range(self._preferred_columns + 1):
            self._grid.setColumnStretch(column, 0)
        self._grid.setColumnStretch(columns, 1)
        self.updateGeometry()


def _icon_icon(kind: str, size: int = 28,
               color: str = theme.TEXT_MUTED) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(color))
    margin = size * 0.13
    inner = size - margin * 2
    path = QTransform().translate(margin, margin).scale(inner, inner).map(
        geometry.icon_path(kind))
    painter.drawPath(path)
    painter.end()
    return QIcon(pixmap)


def preview_pixmap(data: bytes, width: int = 64, height: int = 44) -> QPixmap:
    from PySide6.QtGui import QImage

    image = QImage.fromData(data)
    if image.isNull():
        return QPixmap()
    scaled = image.scaled(width, height, Qt.AspectRatioMode.KeepAspectRatio,
                          Qt.TransformationMode.SmoothTransformation)
    return QPixmap.fromImage(scaled)


class Card(QFrame):
    clicked = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)
