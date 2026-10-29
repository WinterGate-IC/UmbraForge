"""The Build rail: templates, shapes, icons, type and imported images."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .. import backgrounds, branding, cutout, fonts, geometry, renderer, templates, text_styles, theme
from ..layers import Design, asset_name, asset_bytes
from .common import Card, IconGrid, caption, hint, muted, preview_pixmap, rule


class TemplateCard(Card):
    def __init__(self, template, parent: QWidget | None = None):
        super().__init__(parent)
        self.template = template
        self.setFixedHeight(210)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 8)
        layout.setSpacing(4)
        self.image = QLabel("Rendering\u2026")
        self.image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image.setFixedHeight(154)
        self.image.setStyleSheet(
            f"background: {theme.FIELD}; border-radius: 7px; color: {theme.TEXT_DISABLED};")
        self.title = QLabel(template.name)
        self.title.setObjectName("heading")
        self.note = QLabel(template.note)
        self.note.setObjectName("dim")
        self.note.setWordWrap(True)
        self.note.setFixedHeight(30)
        for widget in (self.image, self.title, self.note):
            widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            layout.addWidget(widget)
        self.setToolTip(f"{template.name}\n{template.note}")

    def set_thumbnail(self, pixmap: QPixmap) -> None:
        if pixmap.isNull():
            self.image.setText("No preview")
            return
        scaled = pixmap.scaled(268, 154, Qt.AspectRatioMode.KeepAspectRatio,
                               Qt.TransformationMode.SmoothTransformation)
        self.image.setText("")
        self.image.setPixmap(scaled)


class BackgroundCard(Card):
    def __init__(self, preset, parent: QWidget | None = None):
        super().__init__(parent)
        self.preset = preset
        self.setFixedHeight(96)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 10, 6)
        layout.setSpacing(10)
        self.swatch = QLabel("Rendering\u2026")
        self.swatch.setFixedSize(72, 70)
        self.swatch.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.swatch.setStyleSheet(
            f"background: {theme.FIELD}; border-radius: 8px;"
            f" color: {theme.TEXT_DISABLED}; font-size: 10px;")
        layout.addWidget(self.swatch)
        text_box = QVBoxLayout()
        text_box.setSpacing(1)
        self.title = QLabel(preset.name)
        self.title.setObjectName("heading")
        self.note = QLabel(preset.note)
        self.note.setObjectName("dim")
        self.note.setWordWrap(True)
        text_box.addWidget(self.title)
        text_box.addWidget(self.note)
        layout.addLayout(text_box, 1)
        self.setToolTip(f"{preset.name}\n{preset.note}")

    def set_thumbnail(self, pixmap: QPixmap) -> None:
        if pixmap.isNull():
            self.swatch.setText("No preview")
            return
        scaled = pixmap.scaled(
            self.swatch.size(),
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation)
        self.swatch.setText("")
        self.swatch.setPixmap(scaled)


class LibraryPanel(QWidget):
    applyTemplate = Signal(str)
    applyBackground = Signal(str)
    newBlank = Signal()
    openProject = Signal()
    recentProject = Signal(str)
    addShape = Signal(str)
    addIcon = Signal(str)
    addText = Signal(str)
    addAsset = Signal(str)
    importImage = Signal()
    fontChosen = Signal(str)

    def __init__(self, design_getter, parent: QWidget | None = None):
        super().__init__(parent)
        self._design = design_getter
        self._template_cards: list[TemplateCard] = []
        self._bg_cards: list[BackgroundCard] = []
        self._template_built = False
        self._bg_built = False
        self._asset_widgets: list[QWidget] = []
        self._recent_paths: list[Path] = []
        self._recent_widgets: list[QWidget] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 8)
        layout.setSpacing(8)
        header = QHBoxLayout()
        header.addWidget(caption("Build"))
        header.addStretch(1)
        version = QLabel("v0.1")
        version.setObjectName("pill")
        header.addWidget(version)
        layout.addLayout(header)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.addTab(self._start_tab(), "Start")
        self.tabs.addTab(self._background_tab(), "Backgrounds")
        self.tabs.addTab(self._shape_tab(), "Shapes")
        self.tabs.addTab(self._icon_tab(), "Icons")
        self.tabs.addTab(self._type_tab(), "Type")
        self.tabs.addTab(self._font_tab(), "Fonts")
        self.tabs.addTab(self._image_tab(), "Images")
        layout.addWidget(self.tabs, 1)

        self._template_timer = QTimer(self)
        self._template_timer.setSingleShot(True)
        self._template_timer.setInterval(60)
        self._template_timer.timeout.connect(self._build_templates)
        self._template_timer.start()
        self._bg_timer = QTimer(self)
        self._bg_timer.setSingleShot(True)
        self._bg_timer.setInterval(40)
        self._bg_timer.timeout.connect(self._build_backgrounds)
        self._bg_timer.start()
        self._bg_thumb_queue: list[BackgroundCard] = []
        self._bg_thumb_timer = QTimer(self)
        self._bg_thumb_timer.setSingleShot(True)
        self._bg_thumb_timer.setInterval(16)
        self._bg_thumb_timer.timeout.connect(self._render_next_bg_thumb)
        self.refresh_assets()

    # ---------------------------------------------------------------- tabs
    def _scroll(self) -> tuple[QScrollArea, QWidget, QVBoxLayout]:
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(2, 8, 4, 10)
        layout.setSpacing(9)
        area.setWidget(body)
        return area, body, layout

    def _start_tab(self) -> QWidget:
        area, _body, layout = self._scroll()
        layout.addWidget(muted("Start from a design, then make it yours.", True))
        start_row = QHBoxLayout()
        blank = QPushButton("Blank canvas")
        blank.setObjectName("primary")
        blank.setToolTip("Start with an empty canvas using the current size")
        blank.clicked.connect(self.newBlank.emit)
        open_project = QPushButton("Open project\u2026")
        open_project.setToolTip(
            "Open an .umbra project and keep editing every layer and image")
        open_project.clicked.connect(self.openProject.emit)
        start_row.addWidget(blank, 1)
        start_row.addWidget(open_project, 1)
        layout.addLayout(start_row)

        self._resume_target: Path | None = None
        self._resume_button = QPushButton("Continue where you left off")
        self._resume_button.setObjectName("primary")
        self._resume_button.setToolTip(
            "Open your most recent editable project and keep editing")
        self._resume_button.clicked.connect(self._resume_last)
        self._resume_button.setVisible(False)
        layout.addWidget(self._resume_button)
        layout.addSpacing(4)

        layout.addWidget(caption("Backgrounds"))
        layout.addWidget(muted(
            "Pick a ready-made background to build on. You can still make it "
            "completely invisible later from the Canvas tab.", True))
        quick_bg = QPushButton("Browse backgrounds\u2026")
        quick_bg.clicked.connect(lambda: self.tabs.setCurrentIndex(1))
        layout.addWidget(quick_bg)
        layout.addSpacing(4)

        layout.addWidget(caption("Continue editing"))
        self._recent_empty = QLabel(
            "No recent projects yet. Save a design as an UmbraForge project "
            "(.umbra) and it will appear here, ready to reopen.")
        self._recent_empty.setObjectName("hint")
        self._recent_empty.setWordWrap(True)
        layout.addWidget(self._recent_empty)
        self._recent_box = QVBoxLayout()
        self._recent_box.setSpacing(6)
        layout.addLayout(self._recent_box)
        layout.addSpacing(2)
        layout.addWidget(hint(
            "An .umbra file is UmbraForge's editable project - like a .psd. "
            "PNG, JPEG and the other image formats are final flat images."))
        layout.addSpacing(4)

        layout.addWidget(caption("Templates"))
        self._template_layout = layout
        layout.addStretch(1)
        return area

    def _background_tab(self) -> QWidget:
        area, _body, layout = self._scroll()
        layout.addWidget(muted(
            "Drop in a base background, then add text, shapes or images on top. "
            "Nothing is forced - backgrounds are optional.", True))
        layout.addWidget(hint("Use Canvas > Background to go fully invisible or "
                              "hide individual layers in the Layers panel."))
        layout.addSpacing(4)
        self._background_layout = layout
        layout.addStretch(1)
        return area

    def _build_backgrounds(self) -> None:
        if self._bg_built or not hasattr(self, "_background_layout"):
            return
        self._bg_built = True
        for category in backgrounds.categories():
            self._background_layout.insertWidget(
                self._background_layout.count() - 1, caption(category))
            for preset in backgrounds.PRESETS:
                if preset.category != category:
                    continue
                card = BackgroundCard(preset)
                card.clicked.connect(
                    lambda _checked=False, key=preset.key:
                    self.applyBackground.emit(key))
                self._background_layout.insertWidget(
                    self._background_layout.count() - 1, card)
                self._bg_cards.append(card)
        self._background_layout.insertWidget(
            self._background_layout.count() - 1, hint(
                "Backgrounds are editable after applying. Tweak colours, patterns "
                "or switch to Transparent in the Canvas tab."))
        self._bg_thumb_queue = list(self._bg_cards)
        if self._bg_thumb_queue:
            self._bg_thumb_timer.start(16)

    def _render_next_bg_thumb(self) -> None:
        if not self._bg_thumb_queue:
            return
        card = self._bg_thumb_queue.pop(0)
        self._render_background_thumb(card)
        if self._bg_thumb_queue:
            self._bg_thumb_timer.start(16)

    def _render_background_thumb(self, card: BackgroundCard) -> None:
        try:
            design = Design(name=card.preset.name, width=720, height=700)
            design.background = dict(card.preset.background)
            image = renderer.render_thumbnail(design, 240)
            card.set_thumbnail(QPixmap.fromImage(image))
        except Exception:
            card.swatch.setText("No preview")

    def _resume_last(self) -> None:
        if self._resume_target is not None:
            self.recentProject.emit(str(self._resume_target))

    def set_recent_projects(self, paths) -> None:
        """Show the projects the window has opened or saved recently."""
        seen: list[Path] = []
        for item in paths:
            path = Path(item)
            if path.exists() and path not in seen:
                seen.append(path)
        self._recent_paths = seen[:5]
        if hasattr(self, "_resume_button"):
            self._resume_target = self._recent_paths[0] if self._recent_paths else None
            self._resume_button.setVisible(bool(self._recent_paths))
            if self._recent_paths:
                self._resume_button.setText(
                    f"Continue \u201c{self._recent_paths[0].stem}\u201d")
                self._resume_button.setToolTip(
                    f"{self._recent_paths[0]}\nOpen this editable project and "
                    "pick up where you left off.")
        if not hasattr(self, "_recent_box"):
            return
        for widget in self._recent_widgets:
            widget.setParent(None)
            widget.deleteLater()
        self._recent_widgets = []
        self._recent_empty.setVisible(not self._recent_paths)
        for path in self._recent_paths:
            card = Card()
            card.setFixedHeight(54)
            card.setToolTip(f"Open {path}\nEvery layer stays editable.")
            card.clicked.connect(
                lambda _checked=False, target=path:
                self.recentProject.emit(str(target)))
            row = QHBoxLayout(card)
            row.setContentsMargins(8, 5, 9, 5)
            mark = QLabel()
            mark.setPixmap(branding.icon_pixmap(30))
            mark.setFixedSize(32, 32)
            row.addWidget(mark)
            text_box = QVBoxLayout()
            text_box.setSpacing(1)
            title = QLabel(path.stem or path.name)
            title.setObjectName("heading")
            detail = QLabel(f"Project  \u00b7  {path.parent}")
            detail.setObjectName("hint")
            detail.setToolTip(str(path))
            text_box.addWidget(title)
            text_box.addWidget(detail)
            row.addLayout(text_box, 1)
            arrow = QLabel("\u203a")
            arrow.setStyleSheet(f"color: {theme.ACCENT}; font-size: 19px;")
            row.addWidget(arrow)
            for child in card.findChildren(QLabel):
                child.setAttribute(
                    Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            self._recent_box.addWidget(card)
            self._recent_widgets.append(card)

    def _shape_tab(self) -> QWidget:
        area, _body, layout = self._scroll()
        layout.addWidget(muted("Click a shape to add it at the centre of the canvas.", True))
        self._shape_filter = QLineEdit()
        self._shape_filter.setPlaceholderText("Search shapes\u2026")
        self._shape_filter.setClearButtonEnabled(True)
        self._shape_filter.textChanged.connect(self._refresh_shape_list)
        layout.addWidget(self._shape_filter)
        self._shape_category = QComboBox()
        self._shape_category.addItem("All shapes")
        for cat in geometry.shape_categories():
            self._shape_category.addItem(cat)
        self._shape_category.currentTextChanged.connect(
            lambda _t: self._refresh_shape_list())
        layout.addWidget(self._shape_category)
        self._shape_grids: list[tuple[QLabel, IconGrid]] = []
        self._shape_layout = layout
        self._refresh_shape_list()
        layout.addStretch(1)
        return area

    def _refresh_shape_list(self) -> None:
        if not hasattr(self, "_shape_layout") or not hasattr(self, "_shape_grids"):
            return
        layout = self._shape_layout
        for label, grid in self._shape_grids:
            label.setParent(None)
            grid.setParent(None)
            label.deleteLater()
            grid.deleteLater()
        self._shape_grids = []
        needle = self._shape_filter.text().strip() if hasattr(self, "_shape_filter") else ""
        category = (self._shape_category.currentText()
                    if hasattr(self, "_shape_category") else "All shapes")
        cat_filter = None if category in ("", "All shapes") else category
        entries = geometry.shape_entries(cat_filter, needle)
        if not entries:
            layout.insertWidget(layout.count() - 1, hint("No shapes match that filter."))
            return
        if category in ("", "All shapes") and not needle:
            for cat in geometry.shape_categories():
                cat_entries = geometry.shape_entries(cat)
                if not cat_entries:
                    continue
                layout.insertWidget(layout.count() - 1, caption(cat))
                grid = IconGrid(cat_entries, kind="shape", columns=6, icon_size=26)
                grid.chosen.connect(self.addShape.emit)
                layout.insertWidget(layout.count() - 1, grid)
                label_w = layout.itemAt(layout.count()-2).widget()
                if isinstance(label_w, QLabel):
                    self._shape_grids.append((label_w, grid))
                else:
                    self._shape_grids.append((None, grid))
            hint_w = hint("Shapes are vector paths: no pixelation when you export.")
            layout.insertWidget(layout.count() - 1, hint_w)
        else:
            grid = IconGrid(entries, kind="shape", columns=6, icon_size=26)
            grid.chosen.connect(self.addShape.emit)
            layout.insertWidget(layout.count() - 1, grid)
            self._shape_grids.append((None, grid))
            hint_w = hint("Shapes are vector paths: no pixelation when you export.")
            layout.insertWidget(layout.count() - 1, hint_w)

    def _icon_tab(self) -> QWidget:
        area, _body, layout = self._scroll()
        layout.addWidget(muted("Emblems, marks and symbols. All drawn as vectors.", True))
        self._icon_filter = QLineEdit()
        self._icon_filter.setPlaceholderText("Search icons\u2026")
        self._icon_filter.setClearButtonEnabled(True)
        self._icon_filter.textChanged.connect(self._refresh_icon_list)
        layout.addWidget(self._icon_filter)
        self._icon_category = QComboBox()
        self._icon_category.addItem("All icons")
        for cat in geometry.icon_categories():
            self._icon_category.addItem(cat)
        self._icon_category.currentTextChanged.connect(
            lambda _t: self._refresh_icon_list())
        layout.addWidget(self._icon_category)
        self._icon_grids: list[tuple[QLabel | None, IconGrid]] = []
        self._icon_layout = layout
        self._refresh_icon_list()
        layout.addStretch(1)
        return area

    def _refresh_icon_list(self) -> None:
        if not hasattr(self, "_icon_layout") or not hasattr(self, "_icon_grids"):
            return
        layout = self._icon_layout
        for label, grid in self._icon_grids:
            if label is not None:
                label.setParent(None)
                label.deleteLater()
            grid.setParent(None)
            grid.deleteLater()
        self._icon_grids = []
        needle = self._icon_filter.text().strip() if hasattr(self, "_icon_filter") else ""
        category = (self._icon_category.currentText()
                    if hasattr(self, "_icon_category") else "All icons")
        cat_filter = None if category in ("", "All icons") else category
        entries = geometry.icon_entries(cat_filter, needle)
        if not entries:
            layout.insertWidget(layout.count() - 1, hint("No icons match that filter."))
            return
        if category in ("", "All icons") and not needle:
            for cat in geometry.icon_categories():
                cat_entries = geometry.icon_entries(cat)
                if not cat_entries:
                    continue
                cat_label = caption(cat)
                layout.insertWidget(layout.count() - 1, cat_label)
                grid = IconGrid(cat_entries, kind="icon", columns=6, icon_size=26)
                grid.chosen.connect(self.addIcon.emit)
                layout.insertWidget(layout.count() - 1, grid)
                self._icon_grids.append((cat_label, grid))
            hint_w = hint("Tip: put an icon inside a ring or shield for a crest.")
            layout.insertWidget(layout.count() - 1, hint_w)
        else:
            grid = IconGrid(entries, kind="icon", columns=6, icon_size=26)
            grid.chosen.connect(self.addIcon.emit)
            layout.insertWidget(layout.count() - 1, grid)
            self._icon_grids.append((None, grid))
            hint_w = hint("Tip: put an icon inside a ring or shield for a crest.")
            layout.insertWidget(layout.count() - 1, hint_w)

    def _type_tab(self) -> QWidget:
        area, _body, layout = self._scroll()
        layout.addWidget(muted("Click a type style, then edit the words in the "
                               "Layer panel. Every style is a starting point, "
                               "not a lock.", True))
        for style in text_styles.STYLES:
            card = Card()
            card.setFixedHeight(58)
            card.clicked.connect(lambda k=style.key: self.addText.emit(k))
            row = QHBoxLayout(card)
            row.setContentsMargins(12, 6, 12, 6)
            sample = QLabel(style.sample)
            font = QFont(style.font)
            font.setPixelSize(style.sample_px)
            font.setWeight(QFont.Weight.Bold if style.weight >= 700
                           else QFont.Weight.Medium)
            font.setItalic(style.italic)
            font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing,
                                  style.spacing * style.sample_px)
            sample.setFont(font)
            sample.setStyleSheet(f"color: {theme.TEXT};")
            sample.setToolTip(f"Starts in {style.font}")
            row.addWidget(sample, 1)
            side = QVBoxLayout()
            side.setSpacing(0)
            name = QLabel(style.label)
            name.setObjectName("dim")
            note = QLabel(style.hint)
            note.setObjectName("hint")
            side.addWidget(name)
            side.addWidget(note)
            row.addLayout(side)
            layout.addWidget(card)
        layout.addStretch(1)
        return area

    def _font_tab(self) -> QWidget:
        area, _body, layout = self._scroll()
        layout.addWidget(muted("Preview the fonts installed on this machine. "
                               "Click one to apply it to the selected text "
                               "layer.", True))
        self._font_search = QLineEdit()
        self._font_search.setPlaceholderText("Search fonts\u2026")
        self._font_search.setClearButtonEnabled(True)
        self._font_search.textChanged.connect(self._refresh_font_list)
        layout.addWidget(self._font_search)
        self._font_category = QComboBox()
        self._font_category.addItem("All fonts")
        self._font_category.addItems(fonts.categories())
        self._font_category.currentTextChanged.connect(
            lambda _text: self._refresh_font_list())
        layout.addWidget(self._font_category)
        self._font_list = QListWidget()
        self._font_list.setUniformItemSizes(True)
        self._font_list.setMinimumHeight(360)
        self._font_list.setStyleSheet(
            f"QListWidget {{ background: {theme.FIELD}; border-radius: 6px; }}"
            "QListWidget::item { padding: 3px 6px; }")
        self._font_list.itemClicked.connect(self._pick_font)
        layout.addWidget(self._font_list, 1)
        self._font_count = QLabel("")
        self._font_count.setObjectName("hint")
        layout.addWidget(self._font_count)
        self._refresh_font_list()
        return area

    def _refresh_font_list(self) -> None:
        if not hasattr(self, "_font_list"):
            return
        self._font_list.clear()
        needle = self._font_search.text().strip().casefold()
        category = self._font_category.currentText()
        count = 0
        for family in fonts.available():
            note = fonts.note(family)
            if category not in ("", "All fonts"):
                if fonts.shelf(family) != category:
                    continue
            if needle and (needle not in family.casefold()
                           and needle not in note.casefold()):
                continue
            item = QListWidgetItem(family)
            item.setData(Qt.ItemDataRole.UserRole, family)
            item.setToolTip(note)
            font = QFont(family)
            font.setPixelSize(15)
            item.setFont(font)
            self._font_list.addItem(item)
            count += 1
        self._font_count.setText(
            f"{count} font{'s' if count != 1 else ''} on this device")

    def _pick_font(self, item: QListWidgetItem) -> None:
        family = item.data(Qt.ItemDataRole.UserRole)
        if family:
            self.fontChosen.emit(str(family))

    def _image_tab(self) -> QWidget:
        area, _body, layout = self._scroll()
        import_btn = QPushButton("Import an image\u2026")
        import_btn.setObjectName("primary")
        import_btn.clicked.connect(self.importImage.emit)
        layout.addWidget(import_btn)
        self.ai_label = QLabel(cutout.ai_status())
        self.ai_label.setObjectName("hint")
        self.ai_label.setWordWrap(True)
        layout.addWidget(self.ai_label)
        layout.addWidget(rule())
        layout.addWidget(caption("In this design"))
        self.assets_box = QVBoxLayout()
        self.assets_box.setSpacing(6)
        layout.addLayout(self.assets_box)
        self.assets_empty = QLabel("No images yet. Imports are embedded in the "
                                   "design file, so it stays portable.")
        self.assets_empty.setObjectName("hint")
        self.assets_empty.setWordWrap(True)
        layout.addWidget(self.assets_empty)
        layout.addStretch(1)
        return area

    # ------------------------------------------------------------ templates
    def _build_templates(self) -> None:
        if self._template_built:
            return
        self._template_built = True
        for template in templates.TEMPLATES:
            card = TemplateCard(template)
            card.clicked.connect(lambda t=template.key: self.applyTemplate.emit(t))
            self._template_layout.insertWidget(self._template_layout.count() - 1,
                                               card)
            self._template_cards.append(card)
        self._thumb_queue = list(self._template_cards)
        self._thumb_timer = QTimer(self)
        self._thumb_timer.setSingleShot(True)
        self._thumb_timer.setInterval(18)
        self._thumb_timer.timeout.connect(self._render_next_thumb)
        if self._thumb_queue:
            self._thumb_timer.start(20)

    def _render_next_thumb(self) -> None:
        if not self._thumb_queue:
            return
        card = self._thumb_queue.pop(0)
        self._render_template_thumb(card)
        if self._thumb_queue:
            self._thumb_timer.start(18)

    def _render_template_thumb(self, card: TemplateCard) -> None:
        try:
            design = card.template.build()
            image = renderer.render_thumbnail(design, 300)
            card.set_thumbnail(QPixmap.fromImage(image))
        except Exception:
            card.image.setText("Preview unavailable")

    # --------------------------------------------------------------- assets
    def refresh_assets(self) -> None:
        design = self.design()
        for widget in self._asset_widgets:
            widget.setParent(None)
            widget.deleteLater()
        self._asset_widgets = []
        records = list(design.assets.items())
        self.assets_empty.setVisible(not records)
        for asset_id, record in records:
            data = asset_bytes(design.assets, asset_id)
            if not data:
                continue
            row = Card()
            row.setFixedHeight(52)
            row.clicked.connect(lambda aid=asset_id: self.addAsset.emit(aid))
            layout = QHBoxLayout(row)
            layout.setContentsMargins(6, 5, 8, 5)
            thumb = QLabel()
            thumb.setFixedSize(58, 40)
            thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
            thumb.setStyleSheet(f"background: {theme.FIELD}; border-radius: 5px;")
            pixmap = preview_pixmap(data, 54, 38)
            if not pixmap.isNull():
                thumb.setPixmap(pixmap)
            layout.addWidget(thumb)
            text_box = QVBoxLayout()
            text_box.setSpacing(1)
            name = QLabel(str(record.get("name") or "image"))
            name.setStyleSheet("font-size: 11px;")
            name.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
            size_info = QLabel(f"{record.get('w', 0)} \u00d7 {record.get('h', 0)}")
            size_info.setObjectName("hint")
            text_box.addWidget(name)
            text_box.addWidget(size_info)
            layout.addLayout(text_box, 1)
            add = QLabel("+")
            add.setStyleSheet(f"color: {theme.ACCENT}; font-size: 18px; font-weight: 700;")
            layout.addWidget(add)
            for child in row.findChildren(QLabel):
                child.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            self.assets_box.addWidget(row)
            self._asset_widgets.append(row)

    def design(self) -> Design:
        return self._design()

    def refresh(self) -> None:
        self.refresh_assets()
        self.ai_label.setText(cutout.ai_status())
