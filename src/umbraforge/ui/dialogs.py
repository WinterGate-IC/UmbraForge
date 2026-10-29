"""Dialogs: new design, export, background removal, guide and about.

Each dialog owns a small piece of the studio workflow and stays usable on its
own, so the main window only has to say "show this" and handle the result.
"""

from __future__ import annotations

import re
from pathlib import Path

from PySide6.QtCore import QSettings, Qt, QThread, QTimer, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QFont, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from PIL import Image as PILImage

from .. import branding, cutout, imaging, presets, quality, renderer, templates, theme
from ..layers import Design

IMAGE_FILTER = "Images (*.png *.jpg *.jpeg *.webp *.bmp *.gif *.tif *.tiff)"


def safe_stem(name: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9._ -]+", "", name or "").strip(" .")
    return stem or "umbraforge"


# --------------------------------------------------------------------------
# shared widgets
# --------------------------------------------------------------------------
class PreviewPane(QWidget):
    """A checkerboard-backed preview that fits its image without cropping."""

    def __init__(self, title: str, parent: QWidget | None = None):
        super().__init__(parent)
        self._title = title
        self._pixmap: QPixmap | None = None
        self._message = "No preview"
        self.setMinimumSize(250, 250)
        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Expanding)

    def set_image(self, image) -> None:
        if image is None:
            self._pixmap = None
            self._message = "No preview"
        else:
            self._pixmap = QPixmap.fromImage(imaging.pil_to_qimage(image))
            self._message = ""
        self.update()

    def set_message(self, text: str) -> None:
        self._message = text
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        inner = self.rect().adjusted(1, 1, -1, -1)
        painter.fillRect(inner, QColor(theme.CHECKER_A))
        tile = 11
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(theme.CHECKER_B))
        for row in range(inner.top(), inner.bottom() + 1, tile):
            for column in range(inner.left(), inner.right() + 1, tile):
                if ((column - inner.left()) // tile
                        + (row - inner.top()) // tile) % 2 == 0:
                    painter.drawRect(column, row, min(tile, inner.right() - column),
                                     min(tile, inner.bottom() - row))
        if self._pixmap is not None and not self._pixmap.isNull():
            area = inner.adjusted(10, 10, -10, -10)
            scaled = self._pixmap.scaled(
                area.size(), Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation)
            painter.drawPixmap(
                area.left() + (area.width() - scaled.width()) // 2,
                area.top() + (area.height() - scaled.height()) // 2, scaled)
        else:
            painter.setPen(QColor(theme.TEXT_DISABLED))
            painter.drawText(inner, Qt.AlignmentFlag.AlignCenter, self._message)
        painter.setPen(QColor(theme.BORDER))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(inner)

    def title(self) -> str:
        return self._title


class PresetTile(QPushButton):
    def __init__(self, preset: presets.CanvasPreset, parent: QWidget | None = None):
        super().__init__(parent)
        self.preset = preset
        self.setObjectName("chip")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setText(f"{preset.name}\n{preset.width} \u00d7 {preset.height}")
        self.setToolTip(preset.note or preset.describe())
        self.setFixedHeight(52)
        font = QFont(theme.FONT_FAMILY)
        font.setPixelSize(11)
        self.setFont(font)


# --------------------------------------------------------------------------
# new design
# --------------------------------------------------------------------------
class NewDesignDialog(QDialog):
    """Pick a canvas preset, a name, and either a blank sheet or a template."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("New design")
        self.setMinimumSize(760, 560)
        self._selected = presets.DEFAULT_PRESET
        self._tiles: list[PresetTile] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(22, 20, 22, 18)
        outer.setSpacing(14)

        title = QLabel("Start something new")
        title.setObjectName("title")
        outer.addWidget(title)
        subtitle = QLabel("Every part stays editable. Layers use normalized "
                         "coordinates, so you can change the canvas size later.")
        subtitle.setObjectName("muted")
        subtitle.setWordWrap(True)
        outer.addWidget(subtitle)

        body = QHBoxLayout()
        body.setSpacing(18)
        outer.addLayout(body, 1)

        # presets -----------------------------------------------------------
        left = QVBoxLayout()
        left.setSpacing(8)
        left.addWidget(self._caption("Canvas"))
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        grid_body = QWidget()
        grid = QGridLayout(grid_body)
        grid.setContentsMargins(0, 0, 6, 0)
        grid.setSpacing(6)
        for index, preset in enumerate(presets.PRESETS):
            tile = PresetTile(preset)
            tile.clicked.connect(lambda _checked=False, key=preset.key:
                                 self._choose(key))
            grid.addWidget(tile, index // 2, index % 2)
            self._tiles.append(tile)
        grid.setRowStretch(grid.rowCount(), 1)
        area.setWidget(grid_body)
        left.addWidget(area, 1)
        body.addLayout(left, 3)

        # details -----------------------------------------------------------
        right = QVBoxLayout()
        right.setSpacing(8)
        right.addWidget(self._caption("Details"))

        row = QHBoxLayout()
        name_label = QLabel("Name")
        name_label.setFixedWidth(48)
        name_label.setObjectName("muted")
        self.name_edit = QLineEdit("Untitled")
        self.name_edit.setPlaceholderText("Design name")
        row.addWidget(name_label)
        row.addWidget(self.name_edit, 1)
        right.addLayout(row)

        row = QHBoxLayout()
        start_label = QLabel("Start")
        start_label.setFixedWidth(48)
        start_label.setObjectName("muted")
        self.start_combo = QComboBox()
        self.start_combo.addItem("Blank canvas", "")
        for template in templates.TEMPLATES:
            self.start_combo.addItem(f"{template.name}  \u00b7  {template.category}",
                                     template.key)
        self.start_combo.currentIndexChanged.connect(self._update_summary)
        row.addWidget(start_label)
        row.addWidget(self.start_combo, 1)
        right.addLayout(row)

        self.custom_box = QFrame()
        self.custom_box.setObjectName("card")
        custom = QVBoxLayout(self.custom_box)
        custom.setContentsMargins(10, 9, 10, 9)
        custom.setSpacing(6)
        custom.addWidget(self._caption("Custom size"))
        size_row = QHBoxLayout()
        self.width_spin = QSpinBox()
        self.width_spin.setRange(64, 8192)
        self.width_spin.setValue(1600)
        self.width_spin.setSuffix(" px")
        self.width_spin.setSingleStep(10)
        self.height_spin = QSpinBox()
        self.height_spin.setRange(64, 8192)
        self.height_spin.setValue(1600)
        self.height_spin.setSuffix(" px")
        self.height_spin.setSingleStep(10)
        times = QLabel("\u00d7")
        times.setObjectName("muted")
        size_row.addWidget(self.width_spin, 1)
        size_row.addWidget(times)
        size_row.addWidget(self.height_spin, 1)
        custom.addLayout(size_row)
        self.width_spin.valueChanged.connect(self._custom_changed)
        self.height_spin.valueChanged.connect(self._custom_changed)
        right.addWidget(self.custom_box)

        self.summary = QLabel("")
        self.summary.setObjectName("hint")
        self.summary.setWordWrap(True)
        right.addWidget(self.summary)

        tip = QLabel("Tip: start from a template when you want a finished look, "
                     "or a blank canvas when the idea is already in your head.")
        tip.setObjectName("hint")
        tip.setWordWrap(True)
        right.addWidget(tip)
        right.addStretch(1)

        self.preview = PreviewPane("Template preview")
        self.preview.setMinimumSize(280, 210)
        right.addWidget(self.preview, 1)
        body.addLayout(right, 2)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        create = QPushButton("Create design")
        create.setObjectName("primary")
        buttons.addButton(create, QDialogButtonBox.ButtonRole.AcceptRole)
        create.clicked.connect(self.accept)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

        self._choose(presets.DEFAULT_PRESET)
        self._update_summary()

    @staticmethod
    def _caption(text: str) -> QLabel:
        label = QLabel(text.upper())
        label.setObjectName("sectionLabel")
        return label

    def _choose(self, key: str) -> None:
        self._selected = key
        for tile in self._tiles:
            tile.setChecked(tile.preset.key == key)
        custom = key == "custom"
        self.custom_box.setVisible(custom)
        preset = presets.get(key)
        if not custom:
            self.width_spin.blockSignals(True)
            self.height_spin.blockSignals(True)
            self.width_spin.setValue(preset.width)
            self.height_spin.setValue(preset.height)
            self.width_spin.blockSignals(False)
            self.height_spin.blockSignals(False)
        self._update_summary()

    def _custom_changed(self, _value: int) -> None:
        if self._selected != "custom":
            return
        self._update_summary()

    def _update_summary(self, _index: int | None = None) -> None:
        key = self.start_combo.currentData()
        if key:
            template = templates.get(key)
            self.summary.setText(
                f"{template.name}: {template.note}\n"
                f"Opens at {template.build().width} \u00d7 "
                f"{template.build().height} px, then you can resize it.")
            try:
                image = renderer.render_thumbnail(template.build(), 360)
                self.preview.set_image(imaging.qimage_to_pil(image))
            except Exception:
                self.preview.set_message("Preview unavailable")
        else:
            if self._selected == "custom":
                width = self.width_spin.value()
                height = self.height_spin.value()
                ratio = width / max(1, height)
                self.summary.setText(
                    f"{width:,} \u00d7 {height:,} px \u00b7 {ratio:.3f}:1\n"
                    "A blank sheet with a dark gradient background.")
            else:
                preset = presets.get(self._selected)
                self.summary.setText(
                    f"{preset.name}: {preset.note}\n{preset.describe()} "
                    "A blank sheet with a dark gradient background.")
            self.preview.set_message("Blank canvas")

    def build_design(self) -> Design:
        key = self.start_combo.currentData()
        if key:
            design = templates.build(key)
            name = self.name_edit.text().strip()
            if name and name != "Untitled":
                design.name = name
            return design
        design = Design(name=self.name_edit.text().strip() or "Untitled")
        if self._selected == "custom":
            design.set_size(self.width_spin.value(), self.height_spin.value())
        else:
            design.set_preset(self._selected)
        return design


# --------------------------------------------------------------------------
# save and export (one flow)
# --------------------------------------------------------------------------
#: One list drives the format menu, the file filters and the save dispatch.
#: ``key, label, suffix, hint`` - the order is what people see first.
FORMATS: tuple[tuple[str, str, str, str], ...] = (
    ("png", "PNG image", "png",
     "Lossless and transparent. The best default for almost everything."),
    ("umbra", "UmbraForge project (editable)", "umbra",
     "UmbraForge's own project file - like a .psd, not a standard image "
     "format. Keeps every layer editable so you can come back later."),
    ("jpg", "JPEG image", "jpg",
     "Small photos, no transparency. Good for sharing and the web."),
    ("webp", "WebP image", "webp",
     "Modern web format with transparency and small files."),
    ("ico", "Windows icon (.ico)", "ico",
     "Square multi-resolution icon: 16, 24, 32, 48, 64, 128 and 256 px."),
    ("icns", "macOS icon (.icns)", "icns",
     "Square Apple icon bundle from 16 up to 1024 px."),
    ("webicon", "Web icon kit (.zip)", "zip",
     "favicon.ico, PNG favicons, Apple/PWA icons, manifest and "
     "browserconfig - ready to upload."),
    ("bmp", "BMP image", "bmp",
     "Uncompressed bitmap for legacy tools. Large files."),
    ("tif", "TIFF image", "tif",
     "Archive and print hand-off. Lossless, very large."),
)
FORMAT_BY_KEY = {row[0]: row for row in FORMATS}
RASTER_FORMATS = ("png", "jpg", "webp", "bmp", "tif")
ICON_FORMATS = ("ico", "icns")
LOSSY_FORMATS = ("jpg", "webp")
SUFFIX_ALIASES = {"jpg": ("jpg", "jpeg"), "tif": ("tif", "tiff")}


def _format_label(key: str) -> str:
    return FORMAT_BY_KEY.get(key, FORMAT_BY_KEY["png"])[1]


def _format_suffix(key: str) -> str:
    return FORMAT_BY_KEY.get(key, FORMAT_BY_KEY["png"])[2]


class SaveDialog(QDialog):
    """Save the editable project or export a finished image - one place.

    Exporting and saving are the same idea: commit what is on the canvas to a
    file. The only difference is whether the result stays editable, so this
    dialog leads with the format rather than making people choose a menu.
    """

    def __init__(self, design: Design, parent: QWidget | None = None,
                 *, preferred_format: str | None = None,
                 preferred_path: str | Path | None = None):
        super().__init__(parent)
        self.design = design
        self.saved_path: Path | None = None
        self.saved_project_path: Path | None = None
        self.exported_path: Path | None = None   # backwards-compatible alias
        self.saved_format: str = ""
        self.setWindowTitle("Save")
        self.setMinimumWidth(590)
        self._settings = QSettings("WinterGate", "UmbraForge")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(22, 20, 22, 18)
        outer.setSpacing(12)

        title = QLabel("Save")
        title.setObjectName("title")
        outer.addWidget(title)
        subtitle = QLabel("Saving and exporting are the same action. Pick a "
                          "format once and you are done. Flat images are final; "
                          "the UmbraForge project is the one you can reopen and "
                          "keep editing. Guides and selection never appear.")
        subtitle.setObjectName("muted")
        subtitle.setWordWrap(True)
        outer.addWidget(subtitle)

        section = QLabel("FILE")
        section.setObjectName("sectionLabel")
        outer.addWidget(section)
        path_row = QHBoxLayout()
        default_dir = (self._settings.value("last_save_dir")
                       or self._settings.value("last_export_dir")
                       or str(branding.saves_dir()))
        if preferred_path:
            initial = Path(preferred_path)
        else:
            initial = Path(default_dir) / f"{safe_stem(design.name)}.png"
        self.path_edit = QLineEdit(str(initial))
        browse = QPushButton("Browse\u2026")
        browse.clicked.connect(self._browse)
        path_row.addWidget(self.path_edit, 1)
        path_row.addWidget(browse)
        outer.addLayout(path_row)

        format_row = QHBoxLayout()
        format_row.addWidget(QLabel("Format"))
        self.format_combo = QComboBox()
        for key, label, _suffix, _hint in FORMATS:
            self.format_combo.addItem(label, key)
            self.format_combo.setItemData(self.format_combo.count() - 1,
                                          _hint, Qt.ItemDataRole.ToolTipRole)
        self.format_combo.currentIndexChanged.connect(self._format_changed)
        format_row.addWidget(self.format_combo, 1)
        outer.addLayout(format_row)
        self.format_hint = QLabel("")
        self.format_hint.setObjectName("hint")
        self.format_hint.setWordWrap(True)
        outer.addWidget(self.format_hint)

        self.bg_check = QCheckBox("Include background")
        self.bg_check.setChecked(
            str(design.background.get("kind", "solid")) != "transparent")
        self.bg_check.setToolTip(
            "Turn this off for a transparent PNG, WebP or icon. "
            "JPEG always needs a background.")
        self.bg_check.toggled.connect(self._update_summary)
        outer.addWidget(self.bg_check)

        self.project_copy = QCheckBox(
            "Also save an editable .umbra project beside the image")
        self.project_copy.setChecked(True)
        self.project_copy.setToolTip(
            "Recommended. The image is the finished picture; the .umbra file is "
            "the one you can reopen from the Saves menu and keep editing.")
        self.project_copy.toggled.connect(self._update_summary)
        outer.addWidget(self.project_copy)

        section = QLabel("SIZE")
        section.setObjectName("sectionLabel")
        outer.addWidget(section)
        self.size_note = QLabel("")
        self.size_note.setObjectName("hint")
        self.size_note.setWordWrap(True)
        outer.addWidget(self.size_note)

        self.size_row = QWidget()
        size_row = QHBoxLayout(self.size_row)
        size_row.setContentsMargins(0, 0, 0, 0)
        size_row.addWidget(QLabel("Quality"))
        self.scale_combo = QComboBox()
        for tier in quality.tiers_for(design):
            self.scale_combo.addItem(tier.name, tier.scale)
            self.scale_combo.setItemData(self.scale_combo.count() - 1,
                                          tier.note, Qt.ItemDataRole.ToolTipRole)
        self._select_recommended()
        self.scale_combo.currentIndexChanged.connect(self._scale_changed)
        size_row.addWidget(self.scale_combo, 1)
        outer.addWidget(self.size_row)

        self.custom_row = QWidget()
        custom = QHBoxLayout(self.custom_row)
        custom.setContentsMargins(0, 0, 0, 0)
        self.width_spin = QSpinBox()
        self.width_spin.setRange(16, 12000)
        self.width_spin.setValue(design.width)
        self.width_spin.setSuffix(" px")
        self.height_spin = QSpinBox()
        self.height_spin.setRange(16, 12000)
        self.height_spin.setValue(design.height)
        self.height_spin.setSuffix(" px")
        self.lock_check = QCheckBox("Lock ratio")
        self.lock_check.setChecked(True)
        self.width_spin.valueChanged.connect(self._width_changed)
        self.height_spin.valueChanged.connect(self._height_changed)
        custom.addWidget(QLabel("Width"))
        custom.addWidget(self.width_spin, 1)
        custom.addWidget(QLabel("Height"))
        custom.addWidget(self.height_spin, 1)
        custom.addWidget(self.lock_check)
        self.custom_row.setVisible(False)
        outer.addWidget(self.custom_row)

        self.quality_row = QWidget()
        quality_row = QHBoxLayout(self.quality_row)
        quality_row.setContentsMargins(0, 0, 0, 0)
        quality_row.addWidget(QLabel("Compression"))
        self.quality = QSlider(Qt.Orientation.Horizontal)
        self.quality.setRange(30, 100)
        self.quality.setValue(92)
        self.quality.setToolTip("Higher keeps more detail and makes a larger "
                                "file. Only used by JPEG and WebP.")
        self.quality_label = QLabel("92")
        self.quality_label.setFixedWidth(28)
        self.quality.valueChanged.connect(
            lambda value: self.quality_label.setText(str(value)))
        quality_row.addWidget(self.quality, 1)
        quality_row.addWidget(self.quality_label)
        outer.addWidget(self.quality_row)

        self.summary = QLabel("")
        self.summary.setObjectName("hint")
        self.summary.setWordWrap(True)
        outer.addWidget(self.summary)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self.save_button = QPushButton("Save PNG")
        self.save_button.setObjectName("primary")
        self.save_button.setDefault(True)
        buttons.addButton(self.save_button,
                          QDialogButtonBox.ButtonRole.AcceptRole)
        self.save_button.clicked.connect(self._save)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

        self._select_format(preferred_format or "png")
        self._format_changed()

    # ------------------------------------------------------------- helpers
    def _format(self) -> str:
        data = self.format_combo.currentData()
        return str(data or "png")

    def _select_format(self, key: str) -> None:
        index = self.format_combo.findData(key)
        if index >= 0:
            self.format_combo.setCurrentIndex(index)

    def _select_recommended(self) -> None:
        for index in range(self.scale_combo.count()):
            tier = quality.tiers_for(self.design)[index]
            if tier.key == "device":
                self.scale_combo.setCurrentIndex(index)
                return

    def _browse(self) -> None:
        fmt = self._format()
        suffix = _format_suffix(fmt)
        label = _format_label(fmt)
        path, _ = QFileDialog.getSaveFileName(
            self, "Save", self.path_edit.text(),
            f"{label} (*.{suffix});;All files (*.*)")
        if path:
            self.path_edit.setText(path)

    def _format_changed(self, _index: int | None = None) -> None:
        fmt = self._format()
        suffix = _format_suffix(fmt)
        current = self.path_edit.text().strip()
        if current:
            stem = Path(current).with_suffix("")
            self.path_edit.setText(str(stem) + f".{suffix}")
        spec = FORMAT_BY_KEY[fmt]
        self.format_hint.setText(spec[3])

        raster = fmt in RASTER_FORMATS
        is_umbra = fmt == "umbra"
        self.size_row.setEnabled(raster)
        self.scale_combo.setEnabled(raster)
        self.custom_row.setEnabled(raster)
        self.quality_row.setEnabled(fmt in LOSSY_FORMATS)
        self.bg_check.setEnabled(not is_umbra)
        self.project_copy.setVisible(not is_umbra)
        self.project_copy.setEnabled(not is_umbra)
        if fmt == "jpg":
            self.bg_check.setChecked(True)
            self.bg_check.setEnabled(False)
            self.bg_check.setToolTip("JPEG has no transparency")
        elif is_umbra:
            self.bg_check.setToolTip(
                "Transparency is stored inside the design, not chosen here.")
        elif fmt in ICON_FORMATS or fmt == "webicon":
            self.bg_check.setEnabled(True)
            self.bg_check.setToolTip(
                "Leave this off for a clean transparent icon.")
        else:
            self.bg_check.setToolTip(
                "Turn this off for a transparent PNG or WebP.")
        if is_umbra:
            self.size_note.setText(
                "Editable project - canvas size, layers, images and every "
                "setting come back exactly as they are now.")
        elif fmt in ICON_FORMATS:
            self.size_note.setText(
                f"Icons are rendered square from a "
                f"{quality.icon_base():,} px master and fitted without "
                "stretching. Non-square art is centred.")
        elif fmt == "webicon":
            self.size_note.setText(
                f"Renders a {quality.icon_base():,} px square master and "
                "writes every standard favicon and PWA size into one ZIP.")
        else:
            self.size_note.setText("")
        self._scale_changed()
        label = {"umbra": "Save editable project", "ico": "Save icon",
                 "icns": "Save icon", "webicon": "Save icon kit"}.get(
            fmt, f"Save {_format_suffix(fmt).upper()}")
        self.save_button.setText(label)
        self._update_summary()

    def _scale_changed(self, _index: int | None = None) -> None:
        scale = self.scale_combo.currentData()
        custom = not scale
        self.custom_row.setVisible(custom and self.scale_combo.isEnabled())
        if not custom:
            self.width_spin.blockSignals(True)
            self.height_spin.blockSignals(True)
            self.width_spin.setValue(max(16, round(self.design.width * scale)))
            self.height_spin.setValue(max(16, round(self.design.height * scale)))
            self.width_spin.blockSignals(False)
            self.height_spin.blockSignals(False)
        self._update_summary()

    def _width_changed(self, value: int) -> None:
        if self.lock_check.isChecked():
            ratio = self.design.height / max(1, self.design.width)
            self.height_spin.blockSignals(True)
            self.height_spin.setValue(max(16, round(value * ratio)))
            self.height_spin.blockSignals(False)
        self._update_summary()

    def _height_changed(self, value: int) -> None:
        if self.lock_check.isChecked():
            ratio = self.design.width / max(1, self.design.height)
            self.width_spin.blockSignals(True)
            self.width_spin.setValue(max(16, round(value * ratio)))
            self.width_spin.blockSignals(False)
        self._update_summary()

    def _size(self) -> tuple[int, int]:
        return max(16, self.width_spin.value()), max(16, self.height_spin.value())

    def _update_summary(self, _value=None) -> None:
        fmt = self._format()
        background = self.bg_check.isChecked()
        bg = "with background" if background else "transparent"
        if fmt == "umbra":
            self.summary.setText(
                f"Editable .umbra project \u00b7 {len(self.design.layers)} "
                f"layers \u00b7 {len(self.design.assets)} embedded image"
                f"{'s' if len(self.design.assets) != 1 else ''}")
            return
        if fmt in ICON_FORMATS:
            frames = (quality.ICNS_SIZES if fmt == "icns" else quality.ICO_SIZES)
            sizes = f"{frames[0]}\u2013{frames[-1]} px"
            self.summary.setText(
                f"Square {fmt.upper()} \u00b7 {sizes} \u00b7 {bg}")
            return
        if fmt == "webicon":
            self.summary.setText(
                "Web icon kit \u00b7 favicon.ico \u00b7 PNG 16/32/48/180/192/"
                f"512 \u00b7 manifest + browserconfig \u00b7 {bg}")
            return
        width, height = self._size()
        plan = quality.plan_export(self.design, width, height)
        bits = [quality.describe_plan(plan), _format_label(fmt), bg,
                f"{width / max(1, height):.3f}:1"]
        if not self.project_copy.isHidden() and self.project_copy.isChecked():
            bits.append("plus editable .umbra copy")
        text = " \u00b7 ".join(bits)
        if plan.warning:
            text += f"\n{plan.warning}"
        self.summary.setText(text)

    # ---------------------------------------------------------------- save
    def _save(self) -> None:
        fmt = self._format()
        spec = FORMAT_BY_KEY[fmt]
        suffix = spec[2]
        text = self.path_edit.text().strip()
        if not text:
            QMessageBox.warning(self, "Save", "Choose where to save the file.")
            return
        path = Path(text)
        allowed = SUFFIX_ALIASES.get(fmt, (suffix,))
        if path.suffix.lower().lstrip(".") not in allowed:
            path = path.with_suffix(f".{suffix}")
            self.path_edit.setText(str(path))
        if path.exists():
            answer = QMessageBox.question(
                self, "Replace file",
                f"{path.name} already exists. Replace it?",
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel)
            if answer != QMessageBox.StandardButton.Yes:
                return
        if not path.parent.exists():
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                QMessageBox.warning(self, "Save",
                                    f"Could not create that folder:\n{exc}")
                return

        background = self.bg_check.isChecked()
        width, height = self._size()
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        error = ""
        try:
            if fmt == "umbra":
                saved = self.design.save(path)
            elif fmt in ICON_FORMATS:
                saved, _plan = quality.save_icon_export(
                    self.design, path, fmt, background=background)
            elif fmt == "webicon":
                saved, _plan = quality.save_web_icon_kit(
                    self.design, path, background=background)
            else:
                saved, _plan = quality.save_export(
                    self.design, path, width, height,
                    quality=self.quality.value(), background=background)
        except Exception as exc:  # pragma: no cover - defensive
            error = str(exc)
            saved = path
        finally:
            QApplication.restoreOverrideCursor()
        if error:
            QMessageBox.critical(self, "Save", f"Could not save the file:\n"
                                               f"{error}")
            return

        # Flat images are final. By default we also write the paired project so
        # the Saves menu can always return to this exact design.
        project_path: Path | None = None
        project_error = ""
        if fmt == "umbra":
            project_path = Path(saved)
        elif self.project_copy.isChecked():
            candidate = Path(saved).with_suffix(".umbra")
            try:
                project_path = self.design.save(candidate)
            except Exception as exc:  # pragma: no cover - defensive
                project_error = str(exc)
        if project_error:
            QMessageBox.warning(
                self, "Editable copy",
                "The image was saved, but the editable project copy could "
                f"not be written:\n{project_error}")

        self.saved_path = Path(saved)
        self.saved_project_path = project_path
        self.exported_path = self.saved_path
        self.saved_format = fmt
        self.path_edit.setText(str(self.saved_path))
        self._settings.setValue("last_save_dir", str(self.saved_path.parent))
        self._settings.setValue("last_export_dir", str(self.saved_path.parent))
        if project_path is not None:
            self._settings.setValue("last_project_dir",
                                    str(project_path.parent))

        size_bytes = (self.saved_path.stat().st_size
                      if self.saved_path.exists() else 0)
        if size_bytes >= 1024 * 1024:
            size_text = f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            size_text = f"{size_bytes / 1024:.0f} KB"
        if fmt == "umbra":
            heading = "Project saved."
            detail = (f"{self.saved_path.name}\n{len(self.design.layers)} "
                      f"layers \u00b7 reopen this file to keep editing \u00b7 "
                      f"{size_text}")
        elif fmt == "webicon":
            heading = "Web icon kit saved."
            detail = (f"{self.saved_path.name}\n"
                      f"{len(quality.WEB_KIT_FILES)} files \u00b7 {size_text}")
        elif fmt in ICON_FORMATS:
            heading = "Icon saved."
            detail = (f"{self.saved_path.name}\n{fmt.upper()} \u00b7 "
                      f"{size_text}")
        else:
            heading = "Image saved."
            detail = (f"{self.saved_path.name}\n{width:,} \u00d7 "
                      f"{height:,} px \u00b7 {_format_label(fmt)} \u00b7 "
                      f"{size_text}")
        if project_path is not None and fmt != "umbra":
            detail += (f"\nEditable project: {project_path.name}\n"
                       "Reopen it from Saves to keep editing.")
        box = QMessageBox(self)
        box.setWindowTitle("Saved")
        box.setText(heading)
        box.setInformativeText(detail)
        open_button = box.addButton("Open folder",
                                    QMessageBox.ButtonRole.ActionRole)
        box.addButton(QMessageBox.StandardButton.Close)
        box.exec()
        if box.clickedButton() is open_button:
            QDesktopServices.openUrl(
                QUrl.fromLocalFile(str(self.saved_path.parent)))
        self.accept()


#: Kept so older code and tests can keep constructing the export dialog.
ExportDialog = SaveDialog


# --------------------------------------------------------------------------
# background removal
# --------------------------------------------------------------------------
class _CutoutWorker(QThread):
    finished_ok = Signal(object)
    failed = Signal(str)

    def __init__(self, image, options: dict, token: int):
        super().__init__()
        self._image = image
        self._options = options
        self._token = token

    def run(self) -> None:  # pragma: no cover - thread timing
        try:
            result = cutout.remove_background(self._image, **self._options)
        except Exception as exc:
            self.failed.emit(str(exc))
        else:
            self.finished_ok.emit((self._token, result))


class CutoutDialog(QDialog):
    """Preview and tune a background removal before writing it to the design."""

    PREVIEW_MAX = 560

    def __init__(self, image, name: str = "image",
                 parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Remove background")
        self.setMinimumSize(960, 640)
        self._source = image.convert("RGBA")
        self._name = name
        self._result = None
        self._result_image = None
        self._mode_used = "auto"
        self._token = 0
        self._workers: list[_CutoutWorker] = []
        self._closing = False
        self._accepting = False
        self._busy = False

        preview_scale = min(1.0, self.PREVIEW_MAX / max(self._source.size))
        self._preview_source = (
            self._source if preview_scale >= 0.999 else
            self._source.resize((max(1, round(self._source.width * preview_scale)),
                                 max(1, round(self._source.height * preview_scale))),
                                PILImage.Resampling.LANCZOS))

        outer = QVBoxLayout(self)
        outer.setContentsMargins(22, 20, 22, 18)
        outer.setSpacing(12)
        title = QLabel("Remove background")
        title.setObjectName("title")
        outer.addWidget(title)
        subtitle = QLabel("Auto samples the border and only removes connected "
                          "pixels. Chroma key removes one colour anywhere. AI is "
                          "optional and runs locally if rembg is installed.")
        subtitle.setObjectName("muted")
        subtitle.setWordWrap(True)
        outer.addWidget(subtitle)

        body = QHBoxLayout()
        body.setSpacing(16)
        outer.addLayout(body, 1)

        previews = QHBoxLayout()
        previews.setSpacing(10)
        left = QVBoxLayout()
        left.addWidget(self._caption("Before"))
        self.before = PreviewPane("Original")
        left.addWidget(self.before, 1)
        previews.addLayout(left, 1)
        right = QVBoxLayout()
        right.addWidget(self._caption("After"))
        self.after = PreviewPane("Cutout")
        right.addWidget(self.after, 1)
        previews.addLayout(right, 1)
        body.addLayout(previews, 3)
        self.before.set_image(self._source)

        # controls ----------------------------------------------------------
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFixedWidth(300)
        panel = QWidget()
        controls = QVBoxLayout(panel)
        controls.setContentsMargins(4, 0, 8, 4)
        controls.setSpacing(8)

        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Auto (border sample)", "auto")
        self.mode_combo.addItem("Chroma key (one colour)", "color")
        self.mode_combo.addItem("AI cutout (optional)", "ai")
        self.mode_combo.currentIndexChanged.connect(self._mode_changed)
        self._labeled(controls, "Method", self.mode_combo)

        self.color_row = QWidget()
        color_layout = QHBoxLayout(self.color_row)
        color_layout.setContentsMargins(0, 0, 0, 0)
        self.color_edit = QLineEdit("#00ff00")
        self.color_edit.setMaxLength(7)
        pick = QPushButton("Pick")
        pick.setFixedWidth(48)
        pick.clicked.connect(self._pick_color)
        sample = QPushButton("Sample")
        sample.setFixedWidth(58)
        sample.setToolTip("Use the image's border colour")
        sample.clicked.connect(self._sample_color)
        color_layout.addWidget(self.color_edit, 1)
        color_layout.addWidget(pick)
        color_layout.addWidget(sample)
        self._labeled(controls, "Key colour", self.color_row)

        self.tolerance = self._slider(controls, "Tolerance", 1, 120, 32)
        self.softness = self._slider(controls, "Softness", 0, 80, 24)
        self.feather = self._slider(controls, "Feather", 0, 25, 1.5, decimals=1)
        self.shrink = self._slider(controls, "Shrink", -8, 8, 0)

        self.trim_check = QCheckBox("Trim transparent edges")
        self.trim_check.setChecked(True)
        controls.addWidget(self.trim_check)

        self.ai_hint = QLabel(cutout.ai_status())
        self.ai_hint.setObjectName("hint")
        self.ai_hint.setWordWrap(True)
        controls.addWidget(self.ai_hint)
        self.ai_hint.setVisible(self.mode_combo.currentData() == "ai")

        self.status = QLabel("")
        self.status.setObjectName("hint")
        self.status.setWordWrap(True)
        controls.addWidget(self.status)
        controls.addStretch(1)

        reset = QPushButton("Reset settings")
        reset.setObjectName("chip")
        reset.clicked.connect(self._reset)
        controls.addWidget(reset)
        scroll.setWidget(panel)
        body.addWidget(scroll, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self.apply_button = QPushButton("Use cutout")
        self.apply_button.setObjectName("primary")
        buttons.addButton(self.apply_button, QDialogButtonBox.ButtonRole.AcceptRole)
        self.apply_button.clicked.connect(self._accept)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(160)
        self._debounce.timeout.connect(self._refresh_preview)

        self._update_mode_visibility()
        self.before.set_image(self._source)
        self._refresh_preview()

    # ------------------------------------------------------------- helpers
    @staticmethod
    def _caption(text: str) -> QLabel:
        label = QLabel(text.upper())
        label.setObjectName("sectionLabel")
        return label

    def _labeled(self, layout, text: str, widget: QWidget) -> None:
        label = QLabel(text)
        label.setObjectName("muted")
        layout.addWidget(label)
        layout.addWidget(widget)

    def _slider(self, layout, label: str, low: int, high: int, value,
                decimals: int = 0) -> QSlider:
        row = QHBoxLayout()
        name = QLabel(label)
        name.setObjectName("muted")
        readout = QLabel("")
        readout.setFixedWidth(44)
        readout.setAlignment(Qt.AlignmentFlag.AlignRight)
        slider = QSlider(Qt.Orientation.Horizontal)
        factor = 10 ** decimals
        slider.setRange(int(low * factor), int(high * factor))
        slider.setValue(int(value * factor))
        slider.valueChanged.connect(
            lambda raw, r=readout, f=factor: (
                r.setText(f"{raw / f:g}"), self._debounce.start()))
        readout.setText(f"{value:g}")
        row.addWidget(name)
        row.addWidget(slider, 1)
        row.addWidget(readout)
        layout.addLayout(row)
        slider._factor = factor  # type: ignore[attr-defined]
        return slider

    def _value(self, slider: QSlider) -> float:
        return slider.value() / getattr(slider, "_factor", 1)

    def _mode(self) -> str:
        return self.mode_combo.currentData()

    def _mode_changed(self, _index: int) -> None:
        self._update_mode_visibility()
        self._refresh_preview()

    def _update_mode_visibility(self) -> None:
        mode = self._mode()
        self.color_row.setEnabled(mode == "color")
        self.ai_hint.setVisible(mode == "ai")
        self.softness.setEnabled(mode == "color")

    def _pick_color(self) -> None:
        from PySide6.QtWidgets import QColorDialog

        chosen = QColorDialog.getColor(
            QColor(self.color_edit.text() or "#00ff00"), self,
            "Key colour", QColorDialog.ColorDialogOption.DontUseNativeDialog)
        if chosen.isValid():
            self.color_edit.setText(chosen.name())
            self._debounce.start()

    def _sample_color(self) -> None:
        color = cutout.border_color(self._source)
        self.color_edit.setText("#{:02x}{:02x}{:02x}".format(*color))
        self._debounce.start()

    def _reset(self) -> None:
        for slider, value in ((self.tolerance, 32), (self.softness, 24),
                              (self.feather, 1.5), (self.shrink, 0)):
            slider.setValue(int(value * getattr(slider, "_factor", 1)))
        self.trim_check.setChecked(True)
        self.color_edit.setText("#00ff00")
        self.mode_combo.setCurrentIndex(0)

    # ------------------------------------------------------------- preview
    def _options(self) -> dict:
        mode = self._mode()
        options = {
            "mode": mode,
            "tolerance": self._value(self.tolerance),
            "softness": self._value(self.softness),
            "feather": self._value(self.feather),
            "shrink": self._value(self.shrink),
        }
        if mode == "color":
            options["color"] = self.color_edit.text().strip() or "#00ff00"
        return options

    def _refresh_preview(self) -> None:
        if self._closing:
            return
        if self._mode() == "ai" and not cutout.ai_available():
            self.after.set_message("AI cutout needs rembg")
            self.status.setText(cutout.ai_status())
            self.apply_button.setEnabled(False)
            return
        self.apply_button.setEnabled(True)
        self._token += 1
        token = self._token
        if self._mode() == "ai":
            self._run_worker(self._preview_source, self._options(), token)
            return
        self._compute(self._preview_source, token)

    def _compute(self, source, token: int) -> None:
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            result = cutout.remove_background(source, **self._options())
        except Exception as exc:
            QApplication.restoreOverrideCursor()
            self.status.setText(str(exc))
            return
        QApplication.restoreOverrideCursor()
        if token != self._token and source is self._preview_source:
            return
        self._show(result, preview=True)

    def _run_worker(self, source, options: dict, token: int) -> None:
        self._set_busy(True)
        self.status.setText("Working locally\u2026" if options.get("mode") == "ai"
                            else "Working\u2026")
        worker = _CutoutWorker(source, options, token)
        worker.finished_ok.connect(self._worker_done)
        worker.failed.connect(self._worker_failed)
        worker.finished.connect(lambda w=worker: self._forget_worker(w))
        self._workers.append(worker)
        worker.start()

    def _forget_worker(self, worker) -> None:
        if worker in self._workers:
            self._workers.remove(worker)
        worker.deleteLater()

    def _worker_done(self, payload) -> None:
        token, result = payload
        if self._closing:
            return
        self._set_busy(False)
        if self._accepting:
            self._finish_accept(result)
            return
        if token != self._token:
            return
        self._show(result, preview=True)

    def _worker_failed(self, message: str) -> None:
        self._set_busy(False)
        if self._closing:
            return
        self.status.setText(message)
        if self._accepting:
            self._accepting = False
            QMessageBox.warning(self, "Remove background", message)

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.apply_button.setEnabled(not busy)
        self.apply_button.setText("Working\u2026" if busy else "Use cutout")
        if busy:
            self.after.set_message("Rendering cutout\u2026")

    def _show(self, result, preview: bool) -> None:
        self._result = result
        self._mode_used = result.mode
        if preview:
            self._preview_result = result
        self.after.set_image(result.image)
        percent = max(0.0, min(100.0, result.removed * 100.0))
        self.status.setText(
            f"{percent:.0f}% of the image became transparent. {result.note}")

    # -------------------------------------------------------------- accept
    def _accept(self) -> None:
        if self._busy:
            return
        options = self._options()
        if options["mode"] == "ai" and not cutout.ai_available():
            QMessageBox.information(self, "AI cutout", cutout.ai_status())
            return
        if options["mode"] == "ai":
            self._accepting = True
            self._token += 1
            self._run_worker(self._source, options, self._token)
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            result = cutout.remove_background(self._source, **options)
        except Exception as exc:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Remove background", str(exc))
            return
        QApplication.restoreOverrideCursor()
        self._finish_accept(result)

    def _finish_accept(self, result) -> None:
        image = result.image
        if self.trim_check.isChecked():
            image = cutout.auto_trim(image)
        self._result_image = image
        self._mode_used = result.mode
        self.accept()

    def result_image(self):
        return self._result_image

    def result_mode(self) -> str:
        return self._mode_used

    def closeEvent(self, event) -> None:  # noqa: N802
        self._closing = True
        for worker in list(self._workers):
            worker.finished.disconnect()
            worker.finished_ok.disconnect()
            worker.failed.disconnect()
            worker.wait(50)
        self._workers = []
        super().closeEvent(event)


# --------------------------------------------------------------------------
# guide and about
# --------------------------------------------------------------------------
GUIDE_HTML = """
<style>
h2 {{ color: #f3f1f8; font-size: 16px; margin: 16px 0 6px 0; }}
p, li {{ color: #b9b4c8; font-size: 12px; line-height: 1.55; }}
b {{ color: #f3f1f8; }}
code {{ color: #ffb066; }}
</style>
<h2>Make something</h2>
<p>Pick a <b>template</b> on the Start tab, or press <b>New design</b> to choose a
canvas. Everything a template contains is a normal layer: nothing is flattened.</p>
<p>Add shapes, icons and type from the <b>Build</b> rail. They are vector paths, so
they stay sharp at any export size. Import a photo in the Images tab and it is
embedded in the design file.</p>

<h2>Move things</h2>
<ul>
<li>Drag a layer to move it. Corners resize; the round handle above the box rotates.</li>
<li>Hold <b>Shift</b> while resizing to keep proportions, or while rotating to snap to 15&deg;.</li>
<li>Arrow keys nudge by one pixel; <b>Shift</b> + arrow nudges by ten.</li>
<li>Scroll to zoom, middle-drag or <b>Space</b> + drag to pan, <b>Ctrl+0</b> to fit.</li>
<li>Layers snap to the centre and to other layers, with guides showing why.</li>
</ul>

<h2>Background removal</h2>
<p><b>Auto</b> samples the border colour, then removes only pixels connected to
the edge. A subject that shares a colour with the background survives. Adjust
Tolerance for how close a pixel must be, Feather for a soft edge, and Shrink to
pull the matte in.</p>
<p><b>Chroma key</b> removes one colour anywhere in the image. Use the Sample
button to grab the corner colour, then lower Tolerance if too much disappears.</p>
<p><b>AI cutout</b> is optional and fully local. Install it with
<code>pip install rembg onnxruntime</code> and restart. Nothing is uploaded.</p>

<h2>Canvas and saving</h2>
<p>Canvas presets cover profile pictures, square posts, desktop and mobile
wallpapers, banners, posters and custom sizes. Layers are stored as fractions of
the canvas, so switching presets reflows the composition instead of cropping it.
Use the Canvas tab to change size, gradient, pattern and vignette.</p>
<p><b>Save</b> and <b>export</b> are the same action, so there is one Save button.
It opens a single dialog with PNG first, plus JPEG, WebP, BMP, TIFF, Windows
<code>.ico</code>, macOS <code>.icns</code>, a ready-to-upload web icon kit, and
the editable <code>.umbra</code> project. Choose a size or the recommended
device-aware quality, then save. Untick <b>Include background</b> for a
transparent image or icon.</p>

<h2>Files and undo</h2>
<p><code>.umbra</code> is UmbraForge's own project file - like a <code>.psd</code>
or <code>.kra</code>, not a standard image format. It keeps every layer, image
and setting editable. Reopen it from <b>Open project</b>, the Start tab's
<b>Continue editing</b> list, or by dropping it on the window. Use
<b>Import project layers</b> to merge another project's layers into the current
one. PNG and the other image formats are flat and final. Undo and redo cover
every edit; dragging a slider is one undo step, not fifty. Closing with unsaved
work asks first.</p>

<h2>Shortcuts</h2>
<ul>
<li><b>Ctrl+N</b> new &nbsp; <b>Ctrl+O</b> open &nbsp; <b>Ctrl+S</b> save &nbsp; <b>Ctrl+Shift+S</b> save as</li>
<li><b>Ctrl+Z</b> undo &nbsp; <b>Ctrl+Shift+Z</b> redo</li>
<li><b>Ctrl+D</b> duplicate layer &nbsp; <b>Del</b> delete layer &nbsp; <b>Ctrl+L</b> lock</li>
<li><b>Ctrl+I</b> import image &nbsp; <b>Ctrl+G</b> grid &nbsp; <b>F1</b> guide</li>
</ul>
"""


class GuideDialog(QDialog):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("UmbraForge quick guide")
        self.resize(660, 660)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 16)
        layout.setSpacing(10)
        title = QLabel("Quick guide")
        title.setObjectName("title")
        layout.addWidget(title)
        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setHtml(GUIDE_HTML)
        browser.setStyleSheet(
            f"QTextBrowser {{ background: {theme.PANEL}; border: 1px solid "
            f"{theme.BORDER}; border-radius: 10px; padding: 10px; }}")
        layout.addWidget(browser, 1)
        footer = QHBoxLayout()
        link = QLabel(f"<a style='color:{theme.ACCENT}' href='{branding.WEBSITE}'>"
                      f"{branding.WEBSITE}</a>")
        link.setOpenExternalLinks(True)
        link.setObjectName("hint")
        footer.addWidget(link)
        footer.addStretch(1)
        close = QPushButton("Close")
        close.setObjectName("primary")
        close.clicked.connect(self.accept)
        footer.addWidget(close)
        layout.addLayout(footer)


class AboutDialog(QDialog):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(f"About {branding.APP_NAME}")
        self.setMinimumWidth(480)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(10)

        head = QHBoxLayout()
        mark = QLabel()
        mark.setPixmap(branding.icon_pixmap(72))
        mark.setFixedSize(72, 72)
        head.addWidget(mark)
        text = QVBoxLayout()
        text.setSpacing(2)
        name = QLabel(branding.APP_NAME)
        name.setObjectName("title")
        version = QLabel(f"Version {branding.VERSION}")
        version.setObjectName("pill")
        version_row = QHBoxLayout()
        version_row.addWidget(version)
        version_row.addStretch(1)
        tagline = QLabel(branding.TAGLINE)
        tagline.setObjectName("muted")
        text.addWidget(name)
        text.addLayout(version_row)
        text.addWidget(tagline)
        head.addLayout(text, 1)
        layout.addLayout(head)

        description = QLabel(branding.DESCRIPTION)
        description.setWordWrap(True)
        layout.addWidget(description)

        features = QLabel(
            "Layered emblems, shapes and icons\n"
            "Profile, wallpaper, banner and poster presets\n"
            "Offline background removal with an optional AI matte\n"
            "Portable .umbra projects with embedded images\n"
            "PNG, JPEG and WebP export at any size")
        features.setObjectName("muted")
        layout.addWidget(features)

        rule = QFrame()
        rule.setObjectName("rule")
        rule.setFixedHeight(1)
        layout.addWidget(rule)

        company = QLabel(f"{branding.COMPANY}\nby {branding.OWNER}")
        company.setObjectName("muted")
        layout.addWidget(company)
        site = QLabel(f"<a style='color:{theme.ACCENT}' href='{branding.WEBSITE}'>"
                      f"{branding.WEBSITE}</a>")
        site.setOpenExternalLinks(True)
        layout.addWidget(site)
        copyright_label = QLabel(branding.COPYRIGHT)
        copyright_label.setObjectName("hint")
        copyright_label.setWordWrap(True)
        layout.addWidget(copyright_label)

        layout.addSpacing(4)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
