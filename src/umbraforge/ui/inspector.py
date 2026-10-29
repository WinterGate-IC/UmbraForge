"""Inspector: layer properties, effects, image tools and canvas settings."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .. import fonts, geometry, imaging, layers, presets, theme
from ..layers import (
    ALIGNMENTS,
    BLEND_MODES,
    PATTERNS,
    VALIGNMENTS,
    Design,
    IconLayer,
    ImageLayer,
    ShapeLayer,
    TextLayer,
    add_asset,
    asset_bytes,
    asset_name,
)
from .common import (
    Card,
    ColorButton,
    NumberField,
    PercentField,
    SliderField,
    caption,
    combo_box,
    hint,
    muted,
    rule,
)

PRESET_LABELS = [(preset.key, f"{preset.name}  \u00b7  {preset.width} \u00d7 {preset.height}")
                 for preset in presets.PRESETS]

WEIGHTS = [("300", "Light"), ("400", "Regular"), ("500", "Medium"),
           ("600", "Semibold"), ("700", "Bold"), ("800", "Extra bold"),
           ("900", "Black")]

BACKGROUND_KINDS = [
    ("linear", "Linear gradient"), ("radial", "Radial gradient"),
    ("solid", "Solid colour"), ("image", "Image"), ("transparent", "Transparent"),
]

MASK_OPTIONS = [("none", "No mask")] + [
    (key, f"Mask: {label}") for key, (label, _) in geometry.SHAPES.items()
]


def _clear(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()
            continue
        child = item.layout()
        if child is not None:
            _clear(child)
            child.deleteLater()


class Inspector(QWidget):
    changed = Signal(str, str)
    requestCutout = Signal(str)
    requestSave = Signal()

    def __init__(self, design_getter, parent: QWidget | None = None):
        super().__init__(parent)
        self._design = design_getter
        self._loading = False
        self._layer_scroll_value = 0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        layout.addWidget(self.tabs)

        self.layer_page = QWidget()
        layer_outer = QVBoxLayout(self.layer_page)
        layer_outer.setContentsMargins(0, 0, 0, 0)
        self.layer_scroll = QScrollArea()
        self.layer_scroll.setWidgetResizable(True)
        self.layer_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.layer_body = QWidget()
        self.layer_layout = QVBoxLayout(self.layer_body)
        self.layer_layout.setContentsMargins(12, 10, 12, 14)
        self.layer_layout.setSpacing(7)
        self.layer_scroll.setWidget(self.layer_body)
        layer_outer.addWidget(self.layer_scroll)
        self.tabs.addTab(self.layer_page, "Layer")

        self.canvas_page = QWidget()
        canvas_outer = QVBoxLayout(self.canvas_page)
        canvas_outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.canvas_body = QWidget()
        self.canvas_layout = QVBoxLayout(self.canvas_body)
        self.canvas_layout.setContentsMargins(12, 10, 12, 14)
        self.canvas_layout.setSpacing(7)
        scroll.setWidget(self.canvas_body)
        canvas_outer.addWidget(scroll)
        self.tabs.addTab(self.canvas_page, "Canvas")

        self._build_canvas_tab()
        self.refresh()

    # ------------------------------------------------------------- helpers
    def design(self) -> Design:
        return self._design()

    def _apply(self, label: str, key: str, action) -> None:
        if self._loading:
            return
        action()
        self.changed.emit(label, key)

    def _section(self, layout, title: str, note: str = "") -> None:
        row = QHBoxLayout()
        row.setContentsMargins(0, 6, 0, 0)
        row.addWidget(caption(title))
        if note:
            note_label = QLabel(note)
            note_label.setObjectName("hint")
            row.addStretch(1)
            row.addWidget(note_label)
        layout.addLayout(row)
        layout.addWidget(rule())

    def _labeled(self, layout, text: str, widget: QWidget) -> None:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        label = QLabel(text)
        label.setFixedWidth(64)
        label.setStyleSheet(f"color: {theme.TEXT_MUTED};")
        row.addWidget(label)
        row.addWidget(widget, 1)
        layout.addLayout(row)

    def _combo(self, items, current, receiver) -> QComboBox:
        box = combo_box(items, current)
        box.currentIndexChanged.connect(
            lambda _index, b=box: receiver(b.currentData()))
        return box

    def _check(self, text: str, checked: bool, receiver) -> QCheckBox:
        box = QCheckBox(text)
        box.setChecked(bool(checked))
        box.toggled.connect(receiver)
        return box

    # --------------------------------------------------------------- build
    def refresh(self) -> None:
        self._loading = True
        self._build_layer_tab()
        self._sync_canvas()
        self._loading = False

    def _build_layer_tab(self) -> None:
        self._layer_scroll_value = self.layer_scroll.verticalScrollBar().value()
        _clear(self.layer_layout)
        layer = self.design().active
        if layer is None:
            self._empty_layer_tab()
            return
        self._layer_header(layer)
        self._transform_section(layer)
        self._appearance_section(layer)
        self._effects_section(layer)
        if isinstance(layer, ShapeLayer):
            self._shape_section(layer)
        elif isinstance(layer, IconLayer):
            self._icon_section(layer)
        elif isinstance(layer, TextLayer):
            self._text_section(layer)
        elif isinstance(layer, ImageLayer):
            self._image_section(layer)
        self.layer_layout.addStretch(1)
        self.layer_scroll.verticalScrollBar().setValue(self._layer_scroll_value)

    def _empty_layer_tab(self) -> None:
        design = self.design()
        self.layer_layout.addSpacing(6)
        title = QLabel("Nothing selected")
        title.setObjectName("heading")
        self.layer_layout.addWidget(title)
        self.layer_layout.addWidget(muted(
            "Pick a layer on the canvas or in the Layers panel to edit it. "
            "Canvas size and the background live on the Canvas tab. Use "
            "Backgrounds in Build for a quick start.", True))
        self.layer_layout.addSpacing(10)
        self.layer_layout.addWidget(rule())
        self._section(self.layer_layout, "This design")
        rows = [
            ("Canvas", f"{design.width:,} \u00d7 {design.height:,} px"),
            ("Ratio", design.preset.ratio_label),
            ("Layers", str(len(design.layers))),
            ("Images", str(len(design.assets))),
        ]
        for key, value in rows:
            row = QHBoxLayout()
            left = QLabel(key)
            left.setObjectName("muted")
            right = QLabel(value)
            right.setAlignment(Qt.AlignmentFlag.AlignRight)
            row.addWidget(left)
            row.addWidget(right, 1)
            self.layer_layout.addLayout(row)
        self.layer_layout.addSpacing(8)
        bg_help = hint(
            "Start with Backgrounds in the Build rail, make it invisible as "
            "Transparent, or hide any layer in the Layers panel.")
        self.layer_layout.addWidget(bg_help)
        self.layer_layout.addSpacing(12)
        save = QPushButton("Save or export\u2026")
        save.setObjectName("primary")
        save.setToolTip("One place for PNG, icons, web kits and the editable "
                        "UmbraForge project")
        save.clicked.connect(self.requestSave.emit)
        self.layer_layout.addWidget(save)
        self.layer_layout.addStretch(1)

    def _layer_header(self, layer: layers.Layer) -> None:
        row = QHBoxLayout()
        kind = QLabel(layer.kind.upper())
        kind.setObjectName("tag")
        row.addWidget(kind)
        row.addStretch(1)
        self.kind_note = QLabel("")
        self.kind_note.setObjectName("hint")
        if isinstance(layer, TextLayer):
            self.kind_note.setText(f"{layer.size * 100:.1f}% type")
        elif isinstance(layer, ImageLayer):
            self.kind_note.setText(asset_name(self.design().assets, layer.asset_id))
        row.addWidget(self.kind_note)
        self.layer_layout.addLayout(row)

        name = QLineEdit(layer.name)
        name.setPlaceholderText("Layer name")
        name.editingFinished.connect(
            lambda: self._apply("Rename layer", f"rename-{layer.id}",
                                lambda: setattr(layer, "name", name.text().strip()
                                                or layer.name)))
        self.layer_layout.addWidget(name)

        lock = self._check("Lock this layer", layer.locked,
                           lambda checked: self._apply(
                               "Lock layer", f"lock-{layer.id}",
                               lambda: setattr(layer, "locked", checked)))
        self.layer_layout.addWidget(lock)

    def _transform_section(self, layer: layers.Layer) -> None:
        self._section(self.layer_layout, "Transform")
        design = self.design()
        for text, value, minimum, maximum, attribute in (
                ("X", layer.x * 100, -200.0, 300.0, "x"),
                ("Y", layer.y * 100, -200.0, 300.0, "y"),
                ("Width", layer.w * 100, 1.0, 400.0, "w"),
                ("Height", layer.h * 100, 1.0, 400.0, "h")):
            if attribute in ("x", "y"):
                minimum, maximum = -300.0, 400.0
            field = PercentField(text, value, minimum, maximum)
            field.valueChanged.connect(
                lambda v, a=attribute: self._apply(
                    "Transform layer", f"transform-{layer.id}",
                    lambda: setattr(layer, a, v / 100.0)))
            self.layer_layout.addWidget(field)

        rotation = SliderField("Rotation", -180, 180, layer.rotation,
                               decimals=0, suffix="\u00b0")
        rotation.valueChanged.connect(
            lambda v: self._apply("Rotate layer", f"rotate-{layer.id}",
                                  lambda: setattr(layer, "rotation", float(v))))
        self.layer_layout.addWidget(rotation)

        if isinstance(layer, TextLayer):
            spacing = SliderField("Tracking", -5, 100, layer.letter_spacing * 100,
                                  decimals=1)
            spacing.valueChanged.connect(
                lambda v: self._apply("Track type", f"track-{layer.id}",
                                      lambda: setattr(layer, "letter_spacing",
                                                      float(v) / 100.0)))
            self.layer_layout.addWidget(spacing)

        buttons = QHBoxLayout()
        buttons.setSpacing(4)
        center = QPushButton("Centre")
        center.setObjectName("chip")
        center.clicked.connect(lambda: self._apply(
            "Centre layer", f"centre-{layer.id}",
            lambda: layer.set_center(0.5, 0.5)))
        flip_h = QPushButton("Flip \u2194")
        flip_h.setObjectName("chip")
        flip_h.clicked.connect(lambda: self._apply(
            "Flip layer", f"flip-{layer.id}",
            lambda: setattr(layer, "flip_h", not layer.flip_h)))
        flip_v = QPushButton("Flip \u2195")
        flip_v.setObjectName("chip")
        flip_v.clicked.connect(lambda: self._apply(
            "Flip layer", f"flip-{layer.id}",
            lambda: setattr(layer, "flip_v", not layer.flip_v)))
        for button in (center, flip_h, flip_v):
            buttons.addWidget(button)
        buttons.addStretch(1)
        self.layer_layout.addLayout(buttons)

    def _appearance_section(self, layer: layers.Layer) -> None:
        self._section(self.layer_layout, "Appearance")
        opacity = SliderField("Opacity", 0, 100, layer.opacity * 100,
                              decimals=0, suffix="%")
        opacity.valueChanged.connect(
            lambda v: self._apply("Layer opacity", f"opacity-{layer.id}",
                                  lambda: setattr(layer, "opacity", float(v) / 100.0)))
        self.layer_layout.addWidget(opacity)
        blend = self._combo(list(BLEND_MODES), layer.blend,
                            lambda key: self._apply(
                                "Blend mode", f"blend-{layer.id}",
                                lambda: setattr(layer, "blend", key)))
        self._labeled(self.layer_layout, "Blend", blend)

    def _effects_section(self, layer: layers.Layer) -> None:
        self._section(self.layer_layout, "Effects")
        shadow = layer.effects.setdefault("shadow", {})
        glow = layer.effects.setdefault("glow", {})

        glow_on = self._check("Glow", bool(glow.get("enabled")),
                              lambda checked: self._apply(
                                  "Glow", f"glow-{layer.id}",
                                  lambda: glow.update(enabled=checked)))
        self.layer_layout.addWidget(glow_on)
        glow_box = QWidget()
        glow_layout = QVBoxLayout(glow_box)
        glow_layout.setContentsMargins(14, 0, 0, 0)
        glow_layout.setSpacing(4)
        glow_color = ColorButton(glow.get("color", "#ff7a3d"), "Glow colour")
        glow_color.colorChanged.connect(
            lambda value: self._apply("Glow colour", f"glow-colour-{layer.id}",
                                      lambda: glow.update(color=value)))
        glow_size = SliderField("Size", 0, 12, glow.get("size", 0.022) * 100,
                                decimals=1, suffix="%")
        glow_size.valueChanged.connect(
            lambda v: self._apply("Glow size", f"glow-size-{layer.id}",
                                  lambda: glow.update(size=float(v) / 100.0)))
        glow_opacity = SliderField("Strength", 0, 100,
                                   glow.get("opacity", 0.55) * 100,
                                   decimals=0, suffix="%")
        glow_opacity.valueChanged.connect(
            lambda v: self._apply("Glow strength", f"glow-strength-{layer.id}",
                                  lambda: glow.update(opacity=float(v) / 100.0)))
        glow_layout.addWidget(glow_color)
        glow_layout.addWidget(glow_size)
        glow_layout.addWidget(glow_opacity)
        glow_box.setEnabled(glow_on.isChecked())
        glow_on.toggled.connect(glow_box.setEnabled)
        self.layer_layout.addWidget(glow_box)

        shadow_on = self._check("Drop shadow", bool(shadow.get("enabled")),
                                lambda checked: self._apply(
                                    "Drop shadow", f"shadow-{layer.id}",
                                    lambda: shadow.update(enabled=checked)))
        self.layer_layout.addWidget(shadow_on)
        shadow_box = QWidget()
        shadow_layout = QVBoxLayout(shadow_box)
        shadow_layout.setContentsMargins(14, 0, 0, 0)
        shadow_layout.setSpacing(4)
        shadow_color = ColorButton(shadow.get("color", "#000000"), "Shadow colour")
        shadow_color.colorChanged.connect(
            lambda value: self._apply("Shadow colour", f"shadow-colour-{layer.id}",
                                      lambda: shadow.update(color=value)))
        blur = SliderField("Blur", 0, 12, shadow.get("blur", 0.018) * 100,
                           decimals=1, suffix="%")
        blur.valueChanged.connect(
            lambda v: self._apply("Shadow blur", f"shadow-blur-{layer.id}",
                                  lambda: shadow.update(blur=float(v) / 100.0)))
        shadow_opacity = SliderField("Strength", 0, 100,
                                     shadow.get("opacity", 0.55) * 100,
                                     decimals=0, suffix="%")
        shadow_opacity.valueChanged.connect(
            lambda v: self._apply("Shadow strength", f"shadow-strength-{layer.id}",
                                  lambda: shadow.update(opacity=float(v) / 100.0)))
        offset_row = QHBoxLayout()
        offset_x = NumberField("Offset X", shadow.get("dx", 0.004) * 100, -10, 10,
                               decimals=1, suffix=" %", step=0.2)
        offset_y = NumberField("Offset Y", shadow.get("dy", 0.006) * 100, -10, 10,
                               decimals=1, suffix=" %", step=0.2)
        offset_x.valueChanged.connect(
            lambda v: self._apply("Shadow offset", f"shadow-offset-{layer.id}",
                                  lambda: shadow.update(dx=float(v) / 100.0)))
        offset_y.valueChanged.connect(
            lambda v: self._apply("Shadow offset", f"shadow-offset-{layer.id}",
                                  lambda: shadow.update(dy=float(v) / 100.0)))
        offset_row.addWidget(offset_x, 1)
        offset_row.addWidget(offset_y, 1)
        shadow_layout.addWidget(shadow_color)
        shadow_layout.addWidget(blur)
        shadow_layout.addWidget(shadow_opacity)
        shadow_layout.addLayout(offset_row)
        shadow_box.setEnabled(shadow_on.isChecked())
        shadow_on.toggled.connect(shadow_box.setEnabled)
        self.layer_layout.addWidget(shadow_box)

    # ----------------------------------------------------------- shape/icon
    def _fill_controls(self, layer, layout, color_attr: str = "fill") -> None:
        self._labeled(layout, "Colour",
                      self._color_row(getattr(layer, color_attr, "#ffffff"),
                                      lambda value: self._apply(
                                          "Layer colour", f"colour-{layer.id}",
                                          lambda: setattr(layer, color_attr, value)),
                                      f"{layer.name} colour"))
        gradient = self._check("Gradient fill", bool(layer.gradient),
                               lambda checked: self._apply(
                                   "Gradient fill", f"gradient-{layer.id}",
                                   lambda: (setattr(layer, "gradient", checked),
                                            setattr(layer, "fill2",
                                                    layer.fill2 or "#8b5cf6"))))
        layout.addWidget(gradient)
        second = self._color_row(layer.fill2 or "#8b5cf6",
                                 lambda value: self._apply(
                                     "Gradient colour", f"gradient2-{layer.id}",
                                     lambda: setattr(layer, "fill2", value)),
                                 "Second colour")
        second.setEnabled(bool(layer.gradient))
        gradient.toggled.connect(second.setEnabled)
        self._labeled(layout, "Second", second)
        angle = SliderField("Angle", 0, 360, layer.gradient_angle, decimals=0,
                            suffix="\u00b0")
        angle.valueChanged.connect(
            lambda v: self._apply("Gradient angle", f"angle-{layer.id}",
                                  lambda: setattr(layer, "gradient_angle", float(v))))
        angle.setEnabled(bool(layer.gradient))
        gradient.toggled.connect(angle.setEnabled)
        layout.addWidget(angle)

    def _color_row(self, color: str, receiver, title: str) -> ColorButton:
        button = ColorButton(color, title)
        button.colorChanged.connect(receiver)
        return button

    def _shape_section(self, layer: ShapeLayer) -> None:
        self._section(self.layer_layout, "Shape")
        shape = self._combo(
            [(key, label) for key, (label, _) in geometry.SHAPES.items()],
            layer.shape,
            lambda key: self._apply("Change shape", f"shape-{layer.id}",
                                    lambda: setattr(layer, "shape", key)))
        self._labeled(self.layer_layout, "Form", shape)
        self._fill_controls(layer, self.layer_layout)
        outline_on = self._check("Outline", bool(layer.stroke),
                                 lambda checked: self._apply(
                                     "Outline", f"outline-{layer.id}",
                                     lambda: (setattr(layer, "stroke",
                                                      layer.stroke or "#f3f1f8"),
                                              setattr(layer, "stroke_width",
                                                      layer.stroke_width or 0.01))))
        self.layer_layout.addWidget(outline_on)
        outline_color = self._color_row(layer.stroke or "#f3f1f8",
                                        lambda value: self._apply(
                                            "Outline colour", f"outline-colour-{layer.id}",
                                            lambda: setattr(layer, "stroke", value)),
                                        "Outline colour")
        outline_color.setEnabled(bool(layer.stroke))
        outline_on.toggled.connect(outline_color.setEnabled)
        self._labeled(self.layer_layout, "Outline", outline_color)
        outline_width = SliderField("Weight", 0, 12, layer.stroke_width * 100,
                                    decimals=1, suffix="%")
        outline_width.valueChanged.connect(
            lambda v: self._apply("Outline width", f"outline-width-{layer.id}",
                                  lambda: setattr(layer, "stroke_width", float(v) / 100.0)))
        outline_width.setEnabled(bool(layer.stroke))
        outline_on.toggled.connect(outline_width.setEnabled)
        self.layer_layout.addWidget(outline_width)

    def _icon_section(self, layer: IconLayer) -> None:
        self._section(self.layer_layout, "Icon")
        icon = self._combo(
            [(key, label) for key, (label, _) in geometry.ICONS.items()],
            layer.icon,
            lambda key: self._apply("Change icon", f"icon-{layer.id}",
                                    lambda: setattr(layer, "icon", key)))
        self._labeled(self.layer_layout, "Glyph", icon)
        self._fill_controls(layer, self.layer_layout, "color")

    # ---------------------------------------------------------------- text
    def _text_section(self, layer: TextLayer) -> None:
        self._section(self.layer_layout, "Type")
        editor = QPlainTextEdit(layer.text)
        editor.setFixedHeight(66)
        editor.setPlaceholderText("Type something\u2026")
        editor.textChanged.connect(
            lambda: self._apply("Edit text", f"text-{layer.id}",
                                lambda: setattr(layer, "text", editor.toPlainText())))
        self.layer_layout.addWidget(editor)
        self._text_editor = editor

        families = [(name, name) for name in fonts.available()]
        if layer.font not in fonts.available():
            families.insert(0, (layer.font, layer.font))
        font = self._combo(families, layer.font,
                           lambda name: self._apply(
                               "Change font", f"font-{layer.id}",
                               lambda: setattr(layer, "font", name)))
        self._labeled(self.layer_layout, "Font", font)
        note = hint(fonts.note(layer.font))
        self.layer_layout.addWidget(note)

        size = SliderField("Size", 0.5, 40, layer.size * 100, decimals=1,
                           suffix="%")
        size.valueChanged.connect(
            lambda v: self._apply("Type size", f"size-{layer.id}",
                                  lambda: setattr(layer, "size", float(v) / 100.0)))
        self.layer_layout.addWidget(size)

        weight = self._combo(WEIGHTS, str(layer.weight),
                             lambda value: self._apply(
                                 "Type weight", f"weight-{layer.id}",
                                 lambda: setattr(layer, "weight", int(value))))
        self._labeled(self.layer_layout, "Weight", weight)

        color = self._color_row(layer.color,
                                lambda value: self._apply(
                                    "Type colour", f"text-colour-{layer.id}",
                                    lambda: setattr(layer, "color", value)),
                                "Text colour")
        self._labeled(self.layer_layout, "Colour", color)

        align = self._combo([(value, value.title()) for value in ALIGNMENTS],
                            layer.align,
                            lambda value: self._apply(
                                "Align text", f"align-{layer.id}",
                                lambda: setattr(layer, "align", value)))
        self._labeled(self.layer_layout, "Align", align)
        valign = self._combo([(value, value.title()) for value in VALIGNMENTS],
                             layer.valign,
                             lambda value: self._apply(
                                 "Align text", f"valign-{layer.id}",
                                 lambda: setattr(layer, "valign", value)))
        self._labeled(self.layer_layout, "Vertical", valign)

        line_height = SliderField("Line", 80, 220, layer.line_height * 100,
                                  decimals=0, suffix="%")
        line_height.valueChanged.connect(
            lambda v: self._apply("Line height", f"line-{layer.id}",
                                  lambda: setattr(layer, "line_height", float(v) / 100.0)))
        self.layer_layout.addWidget(line_height)

        checks = QHBoxLayout()
        checks.addWidget(self._check("Italic", layer.italic,
                                     lambda checked: self._apply(
                                         "Italic", f"italic-{layer.id}",
                                         lambda: setattr(layer, "italic", checked))))
        checks.addWidget(self._check("Caps", layer.uppercase,
                                     lambda checked: self._apply(
                                         "Uppercase", f"caps-{layer.id}",
                                         lambda: setattr(layer, "uppercase", checked))))
        checks.addWidget(self._check("Wrap", layer.wrap,
                                     lambda checked: self._apply(
                                         "Wrap text", f"wrap-{layer.id}",
                                         lambda: setattr(layer, "wrap", checked))))
        checks.addStretch(1)
        self.layer_layout.addLayout(checks)

        outline_on = self._check("Outline", bool(layer.stroke_color),
                                 lambda checked: self._apply(
                                     "Text outline", f"text-outline-{layer.id}",
                                     lambda: (setattr(layer, "stroke_color",
                                                      layer.stroke_color or "#08080c"),
                                              setattr(layer, "stroke_width",
                                                      layer.stroke_width or 0.02))))
        self.layer_layout.addWidget(outline_on)
        stroke_color = self._color_row(layer.stroke_color or "#08080c",
                                       lambda value: self._apply(
                                           "Outline colour", f"text-outline-colour-{layer.id}",
                                           lambda: setattr(layer, "stroke_color", value)),
                                       "Outline colour")
        stroke_color.setEnabled(bool(layer.stroke_color))
        outline_on.toggled.connect(stroke_color.setEnabled)
        self._labeled(self.layer_layout, "Outline", stroke_color)
        stroke_width = SliderField("Weight", 0, 10, layer.stroke_width * 100,
                                   decimals=1, suffix="%")
        stroke_width.valueChanged.connect(
            lambda v: self._apply("Outline width", f"text-outline-width-{layer.id}",
                                  lambda: setattr(layer, "stroke_width", float(v) / 100.0)))
        stroke_width.setEnabled(bool(layer.stroke_color))
        outline_on.toggled.connect(stroke_width.setEnabled)
        self.layer_layout.addWidget(stroke_width)

    def focus_text(self) -> None:
        editor = getattr(self, "_text_editor", None)
        if editor is not None:
            editor.setFocus()
            editor.selectAll()

    # --------------------------------------------------------------- image
    def _image_section(self, layer: ImageLayer) -> None:
        self._section(self.layer_layout, "Image")
        design = self.design()
        record = design.assets.get(layer.asset_id, {})
        name = QLabel(asset_name(design.assets, layer.asset_id))
        name.setWordWrap(True)
        self.layer_layout.addWidget(name)
        size = QLabel(f"{record.get('w', 0)} \u00d7 {record.get('h', 0)} px"
                      + ("  \u00b7  cut out" if layer.original_asset_id else ""))
        size.setObjectName("hint")
        self.layer_layout.addWidget(size)

        buttons = QHBoxLayout()
        replace = QPushButton("Replace\u2026")
        replace.clicked.connect(lambda: self._replace_image(layer))
        remove = QPushButton("Remove background\u2026")
        remove.setObjectName("primary")
        remove.clicked.connect(lambda: self.requestCutout.emit(layer.id))
        buttons.addWidget(replace)
        buttons.addWidget(remove, 1)
        self.layer_layout.addLayout(buttons)

        fit = self._combo([("cover", "Cover"), ("fill", "Stretch"),
                           ("contain", "Contain")], layer.fit,
                          lambda value: self._apply(
                              "Image fit", f"fit-{layer.id}",
                              lambda: setattr(layer, "fit", value)))
        self._labeled(self.layer_layout, "Fit", fit)
        mask = self._combo(MASK_OPTIONS, layer.mask,
                           lambda value: self._apply(
                               "Image mask", f"mask-{layer.id}",
                               lambda: setattr(layer, "mask", value)))
        self._labeled(self.layer_layout, "Mask", mask)
        feather = SliderField("Feather", 0, 15, layer.mask_feather * 100,
                              decimals=1, suffix="%")
        feather.valueChanged.connect(
            lambda v: self._apply("Mask feather", f"mask-feather-{layer.id}",
                                  lambda: setattr(layer, "mask_feather", float(v) / 100.0)))
        self.layer_layout.addWidget(feather)

        self._section(self.layer_layout, "Adjustments")
        settings = layer.adjustments
        entries = [
            ("Brightness", "brightness", 50, 160, 100, 1.0),
            ("Contrast", "contrast", 50, 160, 100, 1.0),
            ("Saturation", "saturation", 0, 200, 100, 1.0),
            ("Warmth", "warmth", -100, 100, 0, 100.0),
            ("Hue", "hue", -100, 100, 0, 100.0),
            ("Vignette", "vignette", 0, 100, 0, 100.0),
        ]
        for label, key, low, high, default, divisor in entries:
            value = float(settings.get(key, default / divisor)) * divisor
            field = SliderField(label, low, high, value, decimals=0, suffix="%")
            field.name.setFixedWidth(70)
            field.valueChanged.connect(
                lambda v, k=key, d=divisor: self._apply(
                    f"Image {label.lower()}", f"adjust-{k}-{layer.id}",
                    lambda: settings.__setitem__(k, float(v) / d)))
            self.layer_layout.addWidget(field)

        reset = QPushButton("Reset adjustments")
        reset.setObjectName("chip")
        reset.clicked.connect(lambda: self._apply(
            "Reset adjustments", f"adjust-reset-{layer.id}",
            lambda: layer.adjustments.update(layers.default_adjustments())))
        self.layer_layout.addWidget(reset)

    def _replace_image(self, layer: ImageLayer) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Replace image", str(Path.home()),
            "Images (*.png *.jpg *.jpeg *.webp *.bmp *.gif *.tif *.tiff)")
        if not path:
            return
        try:
            data = Path(path).read_bytes()
            image = imaging.open_image(data)
        except Exception as exc:
            QMessageBox.warning(self, "UmbraForge", f"Could not open that image:\n{exc}")
            return
        design = self.design()
        suffix = Path(path).suffix.lower().lstrip(".") or "png"
        mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg",
                "webp": "image/webp", "bmp": "image/bmp",
                "gif": "image/gif", "tif": "image/tiff",
                "tiff": "image/tiff"}.get(suffix, "image/png")
        asset_id = add_asset(design.assets, data, Path(path).name, mime,
                             image.width, image.height)
        self._apply("Replace image", f"replace-{layer.id}",
                    lambda: (setattr(layer, "asset_id", asset_id),
                             setattr(layer, "original_asset_id", "")))
        self.refresh()

    # -------------------------------------------------------------- canvas
    def _build_canvas_tab(self) -> None:
        layout = self.canvas_layout
        layout.addWidget(muted("The canvas decides the output size. Layers are "
                               "normalized, so switching size keeps the layout.", True))
        self._section(layout, "Size")
        self.preset_combo = QComboBox()
        for key, label in PRESET_LABELS:
            self.preset_combo.addItem(label, key)
        self.preset_combo.currentIndexChanged.connect(self._preset_selected)
        self._labeled(layout, "Preset", self.preset_combo)
        self.custom_w = NumberField("Width", 1200, 64, 8192, decimals=0,
                                    suffix=" px", step=10)
        self.custom_h = NumberField("Height", 1200, 64, 8192, decimals=0,
                                    suffix=" px", step=10)
        self.custom_w.valueChanged.connect(self._custom_size_changed)
        self.custom_h.valueChanged.connect(self._custom_size_changed)
        layout.addWidget(self.custom_w)
        layout.addWidget(self.custom_h)
        self.size_info = QLabel("")
        self.size_info.setObjectName("hint")
        layout.addWidget(self.size_info)

        self._section(layout, "Background")
        self.bg_help = hint(
            "Use Backgrounds in the Build rail for quick starts, or hide the "
            "background entirely here. Individual layers can also be hidden in "
            "the Layers panel.")
        layout.addWidget(self.bg_help)
        self.bg_kind = QComboBox()
        for key, label in BACKGROUND_KINDS:
            self.bg_kind.addItem(label, key)
        self.bg_kind.currentIndexChanged.connect(self._background_kind_changed)
        self._labeled(layout, "Style", self.bg_kind)

        self.bg_color = ColorButton("#0a0a10", "Background colour")
        self.bg_color.colorChanged.connect(
            lambda value: self._set_background("Background colour", "color", value))
        self._labeled(layout, "Colour", self.bg_color)
        self.bg_color2 = ColorButton("#26123a", "Second colour")
        self.bg_color2.colorChanged.connect(
            lambda value: self._set_background("Background colour", "color2", value))
        self._labeled(layout, "Second", self.bg_color2)

        self.bg_angle = SliderField("Angle", 0, 360, 135, decimals=0, suffix="\u00b0")
        self.bg_angle.valueChanged.connect(
            lambda value: self._set_background("Gradient angle", "angle", float(value)))
        layout.addWidget(self.bg_angle)

        self.bg_image_row = QWidget()
        image_row = QHBoxLayout(self.bg_image_row)
        image_row.setContentsMargins(0, 0, 0, 0)
        self.bg_image_name = QLabel("No image")
        self.bg_image_name.setObjectName("hint")
        choose = QPushButton("Choose\u2026")
        choose.clicked.connect(self._choose_background_image)
        image_row.addWidget(self.bg_image_name, 1)
        image_row.addWidget(choose)
        layout.addWidget(self.bg_image_row)

        self.bg_pattern = QComboBox()
        for key, label in PATTERNS:
            self.bg_pattern.addItem(label, key)
        self.bg_pattern.currentIndexChanged.connect(
            lambda _index: self._set_background("Pattern", "pattern",
                                                self.bg_pattern.currentData()))
        self._labeled(layout, "Pattern", self.bg_pattern)
        self.bg_pattern_color = ColorButton("#ffffff", "Pattern colour")
        self.bg_pattern_color.colorChanged.connect(
            lambda value: self._set_background("Pattern colour", "pattern_color", value))
        self._labeled(layout, "Ink", self.bg_pattern_color)
        self.bg_pattern_opacity = SliderField("Opacity", 0, 60, 7, decimals=0,
                                              suffix="%")
        self.bg_pattern_opacity.valueChanged.connect(
            lambda value: self._set_background("Pattern strength", "pattern_opacity",
                                               float(value) / 100.0))
        layout.addWidget(self.bg_pattern_opacity)
        self.bg_pattern_scale = SliderField("Scale", 5, 200, 35, decimals=0, suffix="%")
        self.bg_pattern_scale.valueChanged.connect(
            lambda value: self._set_background("Pattern scale", "pattern_scale",
                                               float(value) / 100.0))
        layout.addWidget(self.bg_pattern_scale)
        self.bg_vignette = SliderField("Vignette", 0, 100, 25, decimals=0, suffix="%")
        self.bg_vignette.valueChanged.connect(
            lambda value: self._set_background("Vignette", "vignette",
                                               float(value) / 100.0))
        layout.addWidget(self.bg_vignette)

        layout.addSpacing(10)
        warn = QLabel("Removing layers cannot be undone after you save, but "
                      "Undo still works while the design is open.")
        warn.setObjectName("hint")
        warn.setWordWrap(True)
        layout.addWidget(warn)
        clear = QPushButton("Remove all layers")
        clear.setObjectName("danger")
        clear.clicked.connect(self._clear_layers)
        layout.addWidget(clear)
        layout.addStretch(1)

    def _preset_selected(self, _index: int) -> None:
        if self._loading:
            return
        key = self.preset_combo.currentData()
        design = self.design()
        self._apply("Canvas size", "canvas-size", lambda: design.set_preset(key))
        self._sync_canvas()

    def _custom_size_changed(self, _value: float) -> None:
        if self._loading:
            return
        width = int(self.custom_w.value())
        height = int(self.custom_h.value())
        design = self.design()
        self._apply("Canvas size", "canvas-size",
                    lambda: design.set_size(width, height))
        self._sync_canvas()

    def _background_kind_changed(self, _index: int) -> None:
        if self._loading:
            return
        kind = self.bg_kind.currentData()
        self._set_background("Background style", "kind", kind)
        self._sync_canvas()

    def _set_background(self, label: str, key: str, value) -> None:
        if self._loading:
            return
        design = self.design()
        self._apply(label, f"bg-{key}",
                    lambda: design.background.__setitem__(key, value))

    def _choose_background_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Background image", str(Path.home()),
            "Images (*.png *.jpg *.jpeg *.webp *.bmp *.gif *.tif *.tiff)")
        if not path:
            return
        try:
            data = Path(path).read_bytes()
            image = imaging.open_image(data)
        except Exception as exc:
            QMessageBox.warning(self, "UmbraForge", f"Could not open that image:\n{exc}")
            return
        design = self.design()
        suffix = Path(path).suffix.lower().lstrip(".") or "png"
        mime = "image/jpeg" if suffix in ("jpg", "jpeg") else f"image/{suffix}"
        asset_id = add_asset(design.assets, data, Path(path).name, mime,
                             image.width, image.height)
        self._apply("Background image", "bg-image",
                    lambda: design.background.update(kind="image",
                                                     asset_id=asset_id))
        self._sync_canvas()

    def _clear_layers(self) -> None:
        design = self.design()
        if not design.layers:
            return
        answer = QMessageBox.question(
            self, "Remove all layers",
            f"Remove all {len(design.layers)} layers from this design? "
            "You can undo while the design is open.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._apply("Remove all layers", "clear-layers",
                    lambda: (design.layers.clear(), setattr(design, "selected", None)))

    def _sync_canvas(self) -> None:
        design = self.design()
        guard = self._loading
        self._loading = True
        key = design.preset_key
        index = self.preset_combo.findData(key)
        if index >= 0:
            self.preset_combo.setCurrentIndex(index)
        self.custom_w.set_value(design.width)
        self.custom_h.set_value(design.height)
        custom = key == "custom"
        self.custom_w.setEnabled(custom)
        self.custom_h.setEnabled(custom)
        self.size_info.setText(
            f"{design.width:,} \u00d7 {design.height:,} px  \u00b7  "
            f"{design.preset.ratio_label}  \u00b7  {len(design.layers)} layers")
        background = layers.merge(layers.default_background(), design.background)
        kind = background.get("kind", "linear")
        box_index = self.bg_kind.findData(kind)
        if box_index >= 0:
            self.bg_kind.setCurrentIndex(box_index)
        self.bg_color.set_color(background.get("color", "#0a0a10"))
        self.bg_color2.set_color(background.get("color2", "#26123a"))
        self.bg_angle.set_value(float(background.get("angle", 135)))
        pattern_index = self.bg_pattern.findData(background.get("pattern", "none"))
        if pattern_index >= 0:
            self.bg_pattern.setCurrentIndex(pattern_index)
        self.bg_pattern_color.set_color(background.get("pattern_color", "#ffffff"))
        self.bg_pattern_opacity.set_value(
            float(background.get("pattern_opacity", 0.07)) * 100)
        self.bg_pattern_scale.set_value(
            float(background.get("pattern_scale", 0.35)) * 100)
        self.bg_vignette.set_value(float(background.get("vignette", 0.25)) * 100)
        image_id = background.get("asset_id", "")
        self.bg_image_name.setText(
            asset_name(design.assets, image_id) if image_id else "No image")
        self._update_background_visibility(kind)
        self._loading = guard

    def _update_background_visibility(self, kind: str) -> None:
        self.bg_color.setEnabled(kind in ("linear", "radial", "solid"))
        self.bg_color2.setEnabled(kind in ("linear", "radial"))
        self.bg_angle.setEnabled(kind == "linear")
        self.bg_image_row.setVisible(kind == "image")
        self.bg_pattern.setEnabled(kind != "transparent")
        self.bg_pattern_color.setEnabled(kind != "transparent")
        self.bg_pattern_opacity.setEnabled(kind != "transparent")
        self.bg_pattern_scale.setEnabled(kind != "transparent")
        self.bg_vignette.setEnabled(kind != "transparent")
