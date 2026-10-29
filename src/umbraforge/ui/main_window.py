"""The studio window: rails, canvas, panels, menus and all the wiring."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QSettings, Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QDesktopServices, QKeySequence
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSplitter,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .. import (
    backgrounds,
    branding,
    extensions,
    fonts,
    geometry,
    imaging,
    licensing,
    renderer,
    templates,
    text_styles,
    theme,
)
from ..layers import (
    Design,
    History,
    IconLayer,
    ImageLayer,
    ShapeLayer,
    TextLayer,
    add_asset,
    asset_bytes,
    asset_name,
)
from .canvas import CanvasView
from .common import hint
from .dialogs import (
    AboutDialog,
    CutoutDialog,
    GuideDialog,
    IMAGE_FILTER,
    NewDesignDialog,
    SaveDialog,
)
from .inspector import Inspector
from .layers import LayersPanel
from .library import LibraryPanel

SHAPE_COLOURS = ("#ff7a3d", "#8b5cf6", "#63e6ff", "#d9b46a", "#f3f1f8", "#ff5c72")
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif",
                  ".tiff")

#: Type recipes live in :mod:`umbraforge.text_styles` so the shelf, browser and
#: window cannot drift apart. Kept as a dictionary for older call sites.
TEXT_PRESETS: dict[str, dict] = text_styles.presets()


def mime_for(path: str | Path) -> str:
    suffix = Path(path).suffix.lower().lstrip(".")
    return {"jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp",
            "bmp": "image/bmp", "gif": "image/gif", "tif": "image/tiff",
            "tiff": "image/tiff"}.get(suffix, "image/png")


class MainWindow(QMainWindow):
    def __init__(self, design: Design | None = None,
                 path: str | Path | None = None,
                 parent: QWidget | None = None):
        super().__init__(parent)
        self.settings = QSettings("WinterGate", "UmbraForge")
        self.design = design or templates.build("ember_sigil")
        self.path = Path(path) if path else None
        self.history = History(self.design)
        self._dirty = False
        self._restoring = False
        self.setAcceptDrops(True)

        self.setWindowTitle(branding.APP_NAME)
        self.setWindowIcon(branding.qicon())
        self.resize(1500, 940)
        self.setMinimumSize(1080, 700)

        self._build_actions()
        self._build_menus()
        self._build_ui()
        self._flash_timer = QTimer(self)
        self._flash_timer.setSingleShot(True)
        self._flash_timer.setInterval(6000)
        self._flash_timer.timeout.connect(self._reset_status)
        self._restore_geometry()
        self._set_design(self.design, self.path, reset_history=True)

    # ------------------------------------------------------------------ ui
    def _build_actions(self) -> None:
        self.act_new = self._action("New design\u2026", self._new, ["Ctrl+N"])
        self.act_open = self._action("Open project\u2026", self._open, ["Ctrl+O"])
        self.act_save = self._action("Save\u2026", self._save, ["Ctrl+S"])
        self.act_save_as = self._action("Save as\u2026", self._save_as,
                                        ["Ctrl+Shift+S"])
        self.act_save_project = self._action(
            "Save editable copy\u2026", self._save_project_copy, ["Ctrl+Alt+S"])
        self.act_import = self._action("Import image\u2026", self._import_image,
                                       ["Ctrl+I"])
        self.act_import_project = self._action(
            "Import project layers\u2026", self._import_project,
            ["Ctrl+Shift+I"])
        self.act_exit = self._action("Exit", self.close, ["Alt+F4"])

        self.act_undo = self._action("Undo", self._undo, ["Ctrl+Z"])
        self.act_redo = self._action("Redo", self._redo,
                                     ["Ctrl+Shift+Z", "Ctrl+Y"])
        self.act_duplicate = self._action("Duplicate layer", self._duplicate_layer,
                                          ["Ctrl+D"])
        self.act_delete = self._action("Delete layer", self._delete_layer,
                                       ["Delete"])
        self.act_lock = self._action("Lock layer", self._toggle_lock, ["Ctrl+L"])

        self.act_forward = self._action("Bring forward", lambda: self._reorder(1),
                                        ["Ctrl+]"])
        self.act_backward = self._action("Send backward", lambda: self._reorder(-1),
                                         ["Ctrl+["])
        self.act_front = self._action("Bring to front",
                                      lambda: self._vertical(True),
                                      ["Ctrl+Shift+]"])
        self.act_back = self._action("Send to back", lambda: self._vertical(False),
                                     ["Ctrl+Shift+["])
        self.act_centre = self._action("Centre on canvas", self._centre_layer,
                                       ["Ctrl+Shift+C"])
        self.act_flip_h = self._action("Flip horizontally", self._flip_h)
        self.act_flip_v = self._action("Flip vertically", self._flip_v)
        self.act_clear = self._action("Remove all layers", self._clear_layers)

        self.act_zoom_in = self._action("Zoom in", self._zoom_in,
                                        ["Ctrl++", "Ctrl+="])
        self.act_zoom_out = self._action("Zoom out", self._zoom_out, ["Ctrl+-"])
        self.act_fit = self._action("Fit to window", self._fit, ["Ctrl+0"])
        self.act_actual = self._action("Actual pixels", self._actual, ["Ctrl+1"])
        self.act_grid = self._action("Show grid", self._toggle_grid, ["Ctrl+G"],
                                     checkable=True)

        self.act_guide = self._action("Quick guide", self._guide, ["F1"])
        self.act_about = self._action(f"About {branding.APP_NAME}", self._about)

    def _action(self, text: str, slot, shortcuts=None, *, checkable=False):
        action = QAction(text, self)
        if shortcuts:
            action.setShortcuts([QKeySequence(item) for item in shortcuts])
        action.setCheckable(checkable)
        if callable(slot):
            if checkable:
                action.toggled.connect(lambda checked: slot())
            else:
                action.triggered.connect(lambda _checked=False: slot())
        return action

    def _build_menus(self) -> None:
        bar = self.menuBar()
        file_menu = bar.addMenu("&File")
        file_menu.addAction(self.act_new)
        file_menu.addAction(self.act_open)
        self.recent_menu = file_menu.addMenu("Open recent")
        self._rebuild_recent_menu()
        file_menu.addSeparator()
        file_menu.addAction(self.act_save)
        file_menu.addAction(self.act_save_as)
        file_menu.addAction(self.act_save_project)
        file_menu.addSeparator()
        file_menu.addAction(self.act_import)
        file_menu.addAction(self.act_import_project)
        file_menu.addSeparator()
        file_menu.addAction(self.act_exit)

        self.saves_menu = bar.addMenu("&Saves")
        self._rebuild_saves_menu()

        edit_menu = bar.addMenu("&Edit")
        edit_menu.addAction(self.act_undo)
        edit_menu.addAction(self.act_redo)
        edit_menu.addSeparator()
        edit_menu.addAction(self.act_duplicate)
        edit_menu.addAction(self.act_delete)
        edit_menu.addAction(self.act_lock)

        layer_menu = bar.addMenu("&Layer")
        layer_menu.addAction(self.act_forward)
        layer_menu.addAction(self.act_backward)
        layer_menu.addAction(self.act_front)
        layer_menu.addAction(self.act_back)
        layer_menu.addSeparator()
        layer_menu.addAction(self.act_centre)
        layer_menu.addAction(self.act_flip_h)
        layer_menu.addAction(self.act_flip_v)
        layer_menu.addSeparator()
        layer_menu.addAction(self.act_clear)

        view_menu = bar.addMenu("&View")
        view_menu.addAction(self.act_zoom_in)
        view_menu.addAction(self.act_zoom_out)
        view_menu.addAction(self.act_fit)
        view_menu.addAction(self.act_actual)
        view_menu.addSeparator()
        view_menu.addAction(self.act_grid)

        help_menu = bar.addMenu("&Help")
        help_menu.addAction(self.act_guide)
        help_menu.addAction(self.act_about)

        self.addons_menu = bar.addMenu("&Add-ons")
        self._rebuild_addons_menu()

    def _rebuild_addons_menu(self) -> None:
        """Show contributions from licensed add-ons, plus licence status."""
        menu = self.addons_menu
        menu.clear()
        entries = extensions.registry.menu_entries("Add-ons")
        for entry in entries:
            action = menu.addAction(entry.label)
            if entry.tooltip:
                action.setStatusTip(entry.tooltip)
            enabled = extensions.registry.allows(entry.feature)
            action.setEnabled(enabled)
            if not enabled:
                action.setToolTip(
                    "This action needs a WinterGate licence that includes "
                    f"{entry.feature!r}. See Add-ons > Licence status."
                )
            action.triggered.connect(
                lambda _checked=False, callback=entry.callback: callback()
            )
        if entries:
            menu.addSeparator()
        status = menu.addAction("Licence status...")
        status.triggered.connect(self._show_license_status)

    def _show_license_status(self) -> None:
        status = licensing.describe_status()
        if not status["licensed"]:
            text = (
                "UmbraForge open-source edition.\n\n"
                "Every feature in this build is available without a licence. "
                "Optional add-ons stay disabled until a valid licence is installed.\n\n"
                f"Machine id: {status['machine']}\n"
                "Install a licence with:\n"
                "  umbraforge --install-license <file>\n\n"
                "Licences: https://wintergate.org"
            )
        else:
            expiry = "never (perpetual)" if status["perpetual"] else status["expires"]
            text = (
                f"Edition: {status['edition']}\n"
                f"Licensed to: {status['licensee']} <{status['email']}>\n"
                f"Licence id: {status['id']}\n"
                f"Expires: {expiry}\n"
                f"Features: {', '.join(status['features'])}\n"
                f"Machine bound: {'yes' if status['machine_bound'] else 'no'}\n"
                f"Licence file: {status['license_path']}"
            )
        QMessageBox.information(self, "Licence status", text)

    def _build_ui(self) -> None:
        central = QWidget()
        central.setObjectName("page")
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._top_bar())

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(1)

        left = QWidget()
        left.setObjectName("leftRail")
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        self.library_panel = LibraryPanel(lambda: self.design)
        left_layout.addWidget(self.library_panel)
        left.setMinimumWidth(300)
        left.setMaximumWidth(400)
        splitter.addWidget(left)

        centre = QWidget()
        centre.setObjectName("page")
        centre_layout = QVBoxLayout(centre)
        centre_layout.setContentsMargins(0, 0, 0, 0)
        centre_layout.setSpacing(0)
        centre_layout.addWidget(self._canvas_bar())
        self.canvas = CanvasView(lambda: self.design)
        centre_layout.addWidget(self.canvas, 1)
        footer = QWidget()
        footer.setObjectName("statusBar")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(12, 5, 12, 5)
        footer_layout.addWidget(hint(
            "Drag to move \u00b7 corners resize \u00b7 the round handle rotates \u00b7 "
            "scroll to zoom \u00b7 Space-drag to pan"))
        centre_layout.addWidget(footer)
        splitter.addWidget(centre)

        right = QWidget()
        right.setObjectName("rightRail")
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        right_split = QSplitter(Qt.Orientation.Vertical)
        right_split.setChildrenCollapsible(False)
        right_split.setHandleWidth(1)
        self.layers_panel = LayersPanel(lambda: self.design)
        self.inspector = Inspector(lambda: self.design)
        right_split.addWidget(self.layers_panel)
        right_split.addWidget(self.inspector)
        right_split.setSizes([250, 610])
        right_layout.addWidget(right_split)
        right.setMinimumWidth(320)
        right.setMaximumWidth(430)
        splitter.addWidget(right)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        splitter.setSizes([318, 800, 360])
        outer.addWidget(splitter, 1)
        self.setCentralWidget(central)

        status = self.statusBar()
        self.status_hint = QLabel("Ready")
        self.status_hint.setObjectName("muted")
        status.addWidget(self.status_hint, 1)
        self.status_layers = QLabel("")
        self.status_size = QLabel("")
        self.status_zoom = QLabel("")
        for widget in (self.status_layers, self.status_size, self.status_zoom):
            widget.setObjectName("muted")
            status.addPermanentWidget(widget)

        self._wire()
        self.library_panel.set_recent_projects(self._recent_paths())

    def _top_bar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("topBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(9)

        mark = QLabel()
        mark.setPixmap(branding.icon_pixmap(28))
        mark.setFixedSize(28, 28)
        layout.addWidget(mark)
        brand = QLabel(branding.APP_NAME.upper())
        brand.setObjectName("brand")
        layout.addWidget(brand)

        separator = QFrame()
        separator.setFixedWidth(1)
        separator.setFixedHeight(24)
        separator.setStyleSheet(f"background: {theme.BORDER};")
        layout.addWidget(separator)

        self.name_edit = QLineEdit(self.design.name)
        self.name_edit.setToolTip("Design name")
        self.name_edit.setMaxLength(80)
        self.name_edit.setFixedWidth(230)
        self.name_edit.setStyleSheet(
            f"QLineEdit {{ background: transparent; border: 1px solid transparent;"
            f" border-radius: 6px; padding: 4px 7px; font-size: 13px;"
            f" font-weight: 600; }}"
            f"QLineEdit:hover {{ background: {theme.PANEL_ALT}; }}"
            f"QLineEdit:focus {{ background: {theme.FIELD}; border-color: "
            f"{theme.ACCENT}; }}")
        self.name_edit.editingFinished.connect(self._rename_design)
        layout.addWidget(self.name_edit)

        pill = QLabel(f"v{branding.VERSION}")
        pill.setObjectName("pill")
        layout.addWidget(pill)
        layout.addStretch(1)

        undo = self._tool_button("\u21b6", "Undo  (Ctrl+Z)", self.act_undo)
        redo = self._tool_button("\u21b7", "Redo  (Ctrl+Shift+Z)", self.act_redo)
        layout.addWidget(undo)
        layout.addWidget(redo)

        layout.addWidget(self._bar_button("New", self.act_new, "ghost"))
        layout.addWidget(self._bar_button("Open", self.act_open, "ghost"))
        layout.addWidget(self._bar_button("Import", self.act_import, "ghost"))
        save = self._bar_button("Save", self.act_save, "primary")
        save.setMinimumWidth(92)
        save.setToolTip("Save an image or the editable project - one flow, "
                        "any format")
        layout.addWidget(save)
        return bar

    @staticmethod
    def _tool_button(text: str, tooltip: str, action) -> QToolButton:
        button = QToolButton()
        button.setText(text)
        button.setToolTip(tooltip)
        button.setFixedSize(30, 28)
        button.setStyleSheet(
            f"QToolButton {{ font-size: 16px; color: {theme.TEXT_MUTED};"
            f" background: transparent; border: 1px solid transparent;"
            f" border-radius: 6px; }}"
            f"QToolButton:hover {{ background: {theme.RAISED}; color: "
            f"{theme.TEXT}; }}"
            f"QToolButton:disabled {{ color: {theme.TEXT_DISABLED}; }}")
        button.clicked.connect(action.trigger)
        return button

    @staticmethod
    def _bar_button(text: str, action, object_name: str = "") -> QPushButton:
        button = QPushButton(text)
        if object_name:
            button.setObjectName(object_name)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.clicked.connect(action.trigger)
        return button

    def _canvas_bar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("canvasBar")
        bar.setStyleSheet(
            f"QWidget#canvasBar {{ background: {theme.PANEL};"
            f" border-bottom: 1px solid {theme.BORDER}; }}")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(4)

        for text, tip, slot in (
                ("\u2212", "Zoom out  (Ctrl+-)", self._zoom_out),
                ("+", "Zoom in  (Ctrl++)", self._zoom_in)):
            button = QToolButton()
            button.setText(text)
            button.setToolTip(tip)
            button.setFixedSize(26, 24)
            button.setObjectName("ghost")
            button.clicked.connect(slot)
            layout.addWidget(button)

        self.zoom_label = QLabel("100%")
        self.zoom_label.setFixedWidth(46)
        self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.zoom_label.setObjectName("muted")
        layout.addWidget(self.zoom_label)

        fit = QToolButton()
        fit.setText("Fit")
        fit.setToolTip("Fit to window  (Ctrl+0)")
        fit.setFixedHeight(24)
        fit.setObjectName("ghost")
        fit.clicked.connect(self._fit)
        layout.addWidget(fit)

        actual = QToolButton()
        actual.setText("1:1")
        actual.setToolTip("Actual pixels  (Ctrl+1)")
        actual.setFixedHeight(24)
        actual.setObjectName("ghost")
        actual.clicked.connect(self._actual)
        layout.addWidget(actual)

        divider = QFrame()
        divider.setFixedWidth(1)
        divider.setFixedHeight(18)
        divider.setStyleSheet(f"background: {theme.BORDER};")
        layout.addWidget(divider)

        self.grid_button = QToolButton()
        self.grid_button.setText("Grid")
        self.grid_button.setToolTip("Show grid  (Ctrl+G)")
        self.grid_button.setCheckable(True)
        self.grid_button.setFixedHeight(24)
        self.grid_button.setObjectName("ghost")
        self.grid_button.toggled.connect(self.canvas_set_grid)
        layout.addWidget(self.grid_button)

        layout.addStretch(1)
        self.canvas_size_label = QLabel("")
        self.canvas_size_label.setObjectName("hint")
        layout.addWidget(self.canvas_size_label)
        return bar

    def canvas_set_grid(self, checked: bool) -> None:
        if self.act_grid.isChecked() != checked:
            self.act_grid.setChecked(checked)
        if hasattr(self, "canvas"):
            self.canvas.set_grid(checked)

    def _wire(self) -> None:
        self.canvas.selectionChanged.connect(self._on_canvas_selection)
        self.canvas.changed.connect(self._on_canvas_changed)
        self.canvas.editTextRequested.connect(self._edit_text)
        self.canvas.deleteRequested.connect(self._delete_layer)
        self.canvas.duplicateRequested.connect(self._duplicate_layer)
        self.canvas.contextMenuRequested.connect(self._canvas_menu)
        self.canvas.zoomChanged.connect(self._on_zoom)
        self.layers_panel.selectionChanged.connect(self._on_layers_selection)
        self.layers_panel.changed.connect(self._on_layers_changed)
        self.inspector.changed.connect(self._on_inspector_changed)
        self.inspector.requestCutout.connect(self._remove_background)
        self.inspector.requestSave.connect(self._save)
        self.library_panel.applyTemplate.connect(self._apply_template)
        self.library_panel.applyBackground.connect(self._apply_background)
        self.library_panel.newBlank.connect(self._new_blank)
        self.library_panel.openProject.connect(self._open)
        self.library_panel.recentProject.connect(self._open_path)
        self.library_panel.addShape.connect(self._add_shape)
        self.library_panel.addIcon.connect(self._add_icon)
        self.library_panel.addText.connect(self._add_text)
        self.library_panel.addAsset.connect(self._add_asset)
        self.library_panel.importImage.connect(self._import_image)
        self.library_panel.fontChosen.connect(self._set_selected_font)
        self.act_grid.toggled.connect(self.canvas_set_grid)

    # ------------------------------------------------------------- documents
    def _set_design(self, design: Design, path=None,
                    reset_history: bool = True) -> None:
        self.design = design
        self.path = Path(path) if path else None
        if reset_history:
            self.history = History(design)
        self._dirty = False
        renderer.clear_caches()
        self._restoring = True
        try:
            self.name_edit.setText(design.name)
            self.canvas.refresh(reset=True)
            self.layers_panel.refresh()
            self.inspector.refresh()
            self.library_panel.refresh()
        finally:
            self._restoring = False
        self._update_actions()
        self._update_stats()
        self._update_title()

    def _new(self) -> None:
        if not self._maybe_save():
            return
        dialog = NewDesignDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._set_design(dialog.build_design(), None)
            self._flash("New design ready.")

    def _new_blank(self) -> None:
        if not self._maybe_save():
            return
        design = Design(name="Untitled")
        design.set_size(self.design.width, self.design.height)
        self._set_design(design, None)
        self._flash("Blank canvas at the same size.")

    def _open(self) -> None:
        start = self.settings.value("last_project_dir", str(Path.home()))
        path, _ = QFileDialog.getOpenFileName(
            self, "Open UmbraForge project", start,
            "UmbraForge project (*.umbra);;All files (*)")
        if path:
            self._open_path(path)

    def _open_path(self, path: str | Path) -> bool:
        """Open a project file, keeping the previous design safe on cancel."""
        target = Path(path).expanduser()
        if not target.exists():
            QMessageBox.warning(self, "Open project",
                                f"That project is no longer there:\n{target}")
            self._forget_project(target)
            return False
        if not self._maybe_save():
            return False
        try:
            design = Design.open(target)
        except Exception as exc:
            QMessageBox.critical(self, "Open project",
                                 f"Could not open that project:\n{exc}")
            return False
        self.settings.setValue("last_project_dir", str(target.parent))
        self._remember_project(target)
        self._set_design(design, target)
        self._flash(f"Opened {target.name} - every layer is still editable.")
        return True

    def _import_project(self) -> None:
        """Merge another project's layers into the design being edited."""
        start = self.settings.value("last_project_dir", str(Path.home()))
        path, _ = QFileDialog.getOpenFileName(
            self, "Import layers from an UmbraForge project", start,
            "UmbraForge project (*.umbra);;All files (*)")
        if not path:
            return
        target = Path(path)
        try:
            source = Design.open(target)
        except Exception as exc:
            QMessageBox.critical(self, "Import project layers",
                                 f"Could not open that project:\n{exc}")
            return
        try:
            count = self.design.import_layers(source)
        except Exception as exc:  # pragma: no cover - defensive
            QMessageBox.critical(self, "Import project layers",
                                 f"Could not import those layers:\n{exc}")
            return
        if count <= 0:
            QMessageBox.information(
                self, "Import project layers",
                "That project has no layers UmbraForge could add here.")
            return
        self._record("Import project layers", "import-project")
        self._refresh_all()
        self._flash(f"Imported {count} layers from {target.name}. "
                    "The background stayed as it was.")

    # -------------------------------------------------------- recent files
    def _recent_paths(self) -> list[Path]:
        raw = self.settings.value("recent_projects", [])
        if isinstance(raw, (str, Path)):
            raw = [raw]
        paths: list[Path] = []
        for item in raw or []:
            try:
                path = Path(str(item)).expanduser()
            except (TypeError, ValueError):
                continue
            if path not in paths:
                paths.append(path)
        return paths

    def _remember_project(self, path: str | Path) -> None:
        target = Path(path).expanduser()
        try:
            target = target.resolve()
        except OSError:
            pass
        existing = []
        for item in self._recent_paths():
            try:
                same = item.resolve() == target
            except OSError:
                same = item == target
            if not same:
                existing.append(item)
        paths = [target, *existing][:8]
        self.settings.setValue("recent_projects", [str(item) for item in paths])
        self._rebuild_recent_menu()
        self._rebuild_saves_menu()
        if hasattr(self, "library_panel"):
            self.library_panel.set_recent_projects(paths)

    def _forget_project(self, path: str | Path) -> None:
        target = Path(path).expanduser()
        remaining = [item for item in self._recent_paths() if item != target]
        self.settings.setValue("recent_projects", [str(item) for item in remaining])
        self._rebuild_recent_menu()
        self._rebuild_saves_menu()
        if hasattr(self, "library_panel"):
            self.library_panel.set_recent_projects(remaining)

    def _clear_recent_projects(self) -> None:
        self.settings.remove("recent_projects")
        self._rebuild_recent_menu()
        self._rebuild_saves_menu()
        if hasattr(self, "library_panel"):
            self.library_panel.set_recent_projects([])

    def _rebuild_recent_menu(self) -> None:
        if not hasattr(self, "recent_menu"):
            return
        self.recent_menu.clear()
        paths = [path for path in self._recent_paths() if path.exists()]
        if not paths:
            empty = self.recent_menu.addAction("No recent projects yet")
            empty.setEnabled(False)
            return
        for path in paths:
            action = self.recent_menu.addAction(path.stem)
            action.setToolTip(str(path))
            action.triggered.connect(
                lambda _checked=False, target=path: self._open_path(target))
        self.recent_menu.addSeparator()
        self.recent_menu.addAction("Clear recent projects",
                                   self._clear_recent_projects)

    # ------------------------------------------------------------------ saves
    def _rebuild_saves_menu(self) -> None:
        """The Saves menu: return to any editable project in one click."""
        if not hasattr(self, "saves_menu"):
            return
        self.saves_menu.clear()
        paths = [path for path in self._recent_paths() if path.exists()]

        resume = self.saves_menu.addAction("Continue where you left off")
        resume.setEnabled(bool(paths))
        if paths:
            resume.setToolTip(str(paths[0]))
            resume.triggered.connect(lambda _checked=False: self._continue_last())
        self.saves_menu.addSeparator()

        if paths:
            for path in paths[:8]:
                try:
                    stamp = datetime.fromtimestamp(
                        path.stat().st_mtime).strftime("%d %b %H:%M")
                except OSError:
                    stamp = ""
                label = path.stem + (f"   {stamp}" if stamp else "")
                action = self.saves_menu.addAction(label)
                action.setToolTip(
                    f"{path}\nOpen the editable project and keep editing.")
                action.triggered.connect(
                    lambda _checked=False, target=path: self._open_path(target))
        else:
            empty = self.saves_menu.addAction(
                "No saves yet - save an .umbra to come back to")
            empty.setEnabled(False)

        self.saves_menu.addSeparator()
        self.saves_menu.addAction(self.act_save_project)
        self.saves_menu.addAction("Open project\u2026", self._open)
        self.saves_menu.addAction("Open saves folder", self._open_saves_folder)
        if paths:
            self.saves_menu.addAction("Clear saved projects",
                                       self._clear_recent_projects)

    def _continue_last(self) -> None:
        paths = [path for path in self._recent_paths() if path.exists()]
        if paths:
            self._open_path(paths[0])

    def _open_saves_folder(self) -> None:
        folder = branding.saves_dir()
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            QMessageBox.warning(self, "Saves",
                                f"Could not open the saves folder:\n{exc}")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def _save(self, *, project_only: bool = False) -> bool:
        """Save the canvas: project or flat image, chosen in one dialog.

        Saving and exporting are deliberately the same flow. The dialog leads
        with PNG and offers every other format underneath it, so there is only
        ever one place to look.
        """
        preferred_path = (self.path if self.path is not None
                          and self.path.suffix.lower() == ".umbra" else None)
        preferred_format = ("umbra" if project_only or preferred_path is not None
                            else None)
        dialog = SaveDialog(
            self.design, self,
            preferred_format=preferred_format,
            preferred_path=preferred_path)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return False
        saved = dialog.saved_path
        if saved is None:
            return False
        project = dialog.saved_project_path
        if project is not None:
            self.path = Path(project)
            self._dirty = False
            self.settings.setValue("last_project_dir", str(self.path.parent))
            self._remember_project(self.path)
            if dialog.saved_format == "umbra":
                self._flash(f"Project saved as {saved.name} - reopen it from "
                            "Saves to keep editing.")
            else:
                self._flash(f"Saved {saved.name} and {self.path.name}. "
                            "Reopen the project from Saves to keep editing.")
        else:
            # A flat export does not make the editable design saved. Keep the
            # dirty flag so closing still offers to keep a project copy.
            self._flash(f"Exported {saved.name}. No editable copy was saved.")
        self._update_title()
        self._update_actions()
        self.settings.setValue("last_save_dir", str(saved.parent))
        return True

    def _save_as(self) -> bool:
        # Both paths open the same dialog on purpose: there is one save flow.
        return self._save()

    def _save_project_copy(self) -> bool:
        """Save the editable project even when the last save was an image."""
        return self._save(project_only=True)

    def _maybe_save(self) -> bool:
        if not self._dirty:
            return True
        answer = QMessageBox.question(
            self, "Unsaved changes",
            f"Save changes to \u201c{self.design.name}\u201d before continuing?",
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save)
        if answer == QMessageBox.StandardButton.Save:
            return self._save()
        return answer == QMessageBox.StandardButton.Discard

    def _rename_design(self) -> None:
        name = self.name_edit.text().strip() or "Untitled"
        if name == self.design.name:
            return
        self.design.name = name
        self.name_edit.setText(name)
        self._record("Rename design", "design-name")
        self._update_title()

    # --------------------------------------------------------------- editing
    def _record(self, label: str, key: str | None = None) -> None:
        if self._restoring:
            return
        self.history.push(label, key)
        self._dirty = True
        self._update_actions()
        self._update_title()

    def _undo(self) -> None:
        if not self.history.undo():
            return
        self._dirty = True
        self._after_history("Undo")

    def _redo(self) -> None:
        if not self.history.redo():
            return
        self._dirty = True
        self._after_history("Redo")

    def _after_history(self, label: str) -> None:
        self._restoring = True
        try:
            self.name_edit.setText(self.design.name)
            self.canvas.refresh()
            self.layers_panel.refresh()
            self.inspector.refresh()
            self.library_panel.refresh_assets()
        finally:
            self._restoring = False
        self._update_stats()
        self._update_title()
        self._update_actions()
        self._flash(f"{label}.")

    # ------------------------------------------------------------ selection
    def _on_canvas_selection(self, layer_id: str) -> None:
        self.design.selected = layer_id or None
        self._sync_selection(switch_tab=bool(layer_id))

    def _on_layers_selection(self, layer_id: str) -> None:
        self.design.selected = layer_id or None
        self._sync_selection(switch_tab=True)

    def _sync_selection(self, switch_tab: bool = False) -> None:
        self.canvas.update()
        self.layers_panel.sync_selection()
        self.inspector.refresh()
        if switch_tab:
            self.inspector.tabs.setCurrentIndex(0)
        self._update_stats()
        self._update_actions()

    def _on_canvas_changed(self, label: str, key: str) -> None:
        self._record(label, key)
        self.inspector.refresh()
        self._update_stats()

    def _on_layers_changed(self, label: str, key: str) -> None:
        self._record(label, key)
        self.inspector.refresh()
        self.canvas.refresh()
        self._update_stats()

    def _on_inspector_changed(self, label: str, key: str) -> None:
        self._record(label, key)
        self.canvas.refresh(reset=key == "canvas-size")
        if key.startswith(("rename-", "lock-", "visible-")):
            self.layers_panel.refresh()
        if key.startswith(("replace-", "bg-image", "canvas-size", "clear-layers")):
            self.library_panel.refresh_assets()
        self._update_stats()

    # ------------------------------------------------------------ layer ops
    def _duplicate_layer(self) -> None:
        layer = self.design.duplicate()
        if layer is None:
            self._flash("Select a layer to duplicate.")
            return
        self._record("Duplicate layer", "duplicate-layer")
        self.canvas.refresh()
        self.layers_panel.refresh()
        self.inspector.refresh()
        self._update_stats()
        self._update_actions()

    def _delete_layer(self) -> None:
        design = self.design
        layer = design.active
        if layer is None:
            self._flash("Select a layer to delete.")
            return
        design.remove(layer.id)
        self._record("Delete layer", "delete-layer")
        self.canvas.refresh()
        self.layers_panel.refresh()
        self.inspector.refresh()
        self._update_stats()
        self._update_actions()

    def _toggle_lock(self) -> None:
        layer = self.design.active
        if layer is None:
            return
        layer.locked = not layer.locked
        self._record("Lock layer", f"lock-{layer.id}")
        self.layers_panel.refresh()
        self.canvas.update()
        self.inspector.refresh()
        self._update_actions()

    def _reorder(self, delta: int) -> None:
        layer = self.design.active
        if layer and self.design.move(layer.id, delta):
            self._record("Reorder layers", "reorder")
            self.layers_panel.refresh()
            self.canvas.refresh()
            self._update_actions()

    def _vertical(self, front: bool) -> None:
        layer = self.design.active
        if layer is None:
            return
        changed = (self.design.to_front(layer.id) if front
                   else self.design.to_back(layer.id))
        if changed:
            self._record("Reorder layers", "reorder")
            self.layers_panel.refresh()
            self.canvas.refresh()
            self._update_actions()

    def _centre_layer(self) -> None:
        layer = self.design.active
        if layer is None:
            return
        layer.set_center(0.5, 0.5)
        self._record("Centre layer", f"centre-{layer.id}")
        self.canvas.refresh()
        self.inspector.refresh()
        self._update_stats()

    def _flip_h(self) -> None:
        layer = self.design.active
        if layer is None:
            return
        layer.flip_h = not layer.flip_h
        self._record("Flip layer", f"flip-{layer.id}")
        self.canvas.refresh()
        self.inspector.refresh()

    def _flip_v(self) -> None:
        layer = self.design.active
        if layer is None:
            return
        layer.flip_v = not layer.flip_v
        self._record("Flip layer", f"flip-{layer.id}")
        self.canvas.refresh()
        self.inspector.refresh()

    def _clear_layers(self) -> None:
        design = self.design
        if not design.layers:
            return
        answer = QMessageBox.question(
            self, "Remove all layers",
            f"Remove all {len(design.layers)} layers from this design?\n"
            "Undo still works while the design is open.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            return
        design.layers.clear()
        design.selected = None
        self._record("Remove all layers", "clear-layers")
        self._refresh_all()

    def _edit_text(self, layer_id: str) -> None:
        layer = self.design.layer(layer_id)
        if not isinstance(layer, TextLayer):
            return
        self.design.selected = layer.id
        self._sync_selection(switch_tab=True)
        self.inspector.focus_text()

    # ---------------------------------------------------------------- adding
    def _next_colour(self) -> str:
        index = sum(1 for layer in self.design.layers
                    if isinstance(layer, (ShapeLayer, IconLayer)))
        return SHAPE_COLOURS[index % len(SHAPE_COLOURS)]

    def _square_size(self, size: float = 0.30) -> tuple[float, float]:
        design = self.design
        width = min(size, 0.85)
        height = width * design.width / max(1, design.height)
        if height > 0.85:
            scale = 0.85 / height
            width *= scale
            height *= scale
        return width, height

    def _add_shape(self, key: str) -> None:
        design = self.design
        width, height = self._square_size(0.30)
        layer = ShapeLayer(
            name=design.unique_name(geometry.shape_label(key)), shape=key,
            x=0.5 - width / 2, y=0.5 - height / 2, w=width, h=height,
            fill=self._next_colour(), gradient=True, fill2="#2a1430",
            gradient_angle=120.0)
        design.add(layer)
        self._record("Add shape", f"add-shape-{layer.id}")
        self._refresh_all()
        self._flash(f"Added {layer.name}.")

    def _add_icon(self, key: str) -> None:
        design = self.design
        width, height = self._square_size(0.26)
        layer = IconLayer(
            name=design.unique_name(geometry.icon_label(key)), icon=key,
            x=0.5 - width / 2, y=0.5 - height / 2, w=width, h=height,
            color="#f3f1f8")
        design.add(layer)
        self._record("Add icon", f"add-icon-{layer.id}")
        self._refresh_all()
        self._flash(f"Added {layer.name}.")

    def _add_text(self, style: str) -> None:
        spec = TEXT_PRESETS.get(style, TEXT_PRESETS["heading"])
        design = self.design
        width = float(spec.get("width", 0.72))
        height = float(spec.get("height", 0.13))
        # Resolve against the fonts really installed here, so a missing
        # display face falls back to something usable instead of a blank box.
        family = fonts.resolve(str(spec.get("font", "Bahnschrift")),
                               ("Bahnschrift", "Segoe UI", "Arial"))
        layer = TextLayer(
            name=design.unique_name(spec["name"]), text=spec["text"],
            font=family, size=spec["size"], weight=spec["weight"],
            italic=bool(spec.get("italic", False)),
            letter_spacing=spec["spacing"],
            line_height=float(spec.get("line_height", 1.15)),
            align=str(spec.get("align", "center")),
            uppercase=spec["uppercase"],
            x=0.5 - width / 2, y=0.5 - height / 2, w=width, h=height,
            color=str(spec.get("color", "#f3f1f8")),
            opacity=float(spec.get("opacity", 1.0)),
            stroke_color="#08080c" if style == "display" else "",
            stroke_width=0.015 if style == "display" else 0.0)
        design.add(layer)
        self._record("Add text", f"add-text-{layer.id}")
        self._refresh_all()
        self._flash("Text added. Edit it in the inspector.")

    def _set_selected_font(self, family: str) -> None:
        layer = self.design.active
        if not isinstance(layer, TextLayer):
            self._flash("Select a text layer first, then click a font.")
            return
        resolved = fonts.resolve(family)
        if layer.font == resolved:
            return
        layer.font = resolved
        self._record("Change font", f"font-{layer.id}-{resolved}")
        self._refresh_all()
        self._flash(f"Font set to {resolved}.")

    def _add_asset(self, asset_id: str) -> None:
        design = self.design
        record = design.assets.get(asset_id)
        if not record:
            return
        source_w = int(record.get("w") or 0)
        source_h = int(record.get("h") or 0)
        if source_w <= 0 or source_h <= 0:
            data = asset_bytes(design.assets, asset_id)
            try:
                image = imaging.open_image(data)
                source_w, source_h = image.size
            except Exception:
                source_w = source_h = 1
        width = 0.52
        height = width * (design.width / max(1, design.height)) * (source_h / max(1, source_w))
        if height > 0.86:
            scale = 0.86 / height
            width *= scale
            height *= scale
        layer = ImageLayer(
            name=design.unique_name(Path(asset_name(design.assets, asset_id)).stem
                                    or "Image"),
            asset_id=asset_id, x=0.5 - width / 2, y=0.5 - height / 2,
            w=width, h=height, fit="cover")
        design.add(layer)
        self._record("Add image", f"add-image-{layer.id}")
        self._refresh_all()
        self._flash("Image layer added.")

    def _import_image(self) -> None:
        start = self.settings.value("last_image_dir", str(Path.home()))
        path, _ = QFileDialog.getOpenFileName(
            self, "Import image", start, IMAGE_FILTER + ";;All files (*)")
        if path:
            self._import_image_path(path)

    def _import_image_path(self, path: str | Path) -> bool:
        target = Path(path)
        try:
            data = target.read_bytes()
            image = imaging.open_image(data)
        except Exception as exc:
            QMessageBox.warning(self, "Import image",
                                f"Could not open {target.name}:\n{exc}")
            return False
        self.settings.setValue("last_image_dir", str(target.parent))
        design = self.design
        asset_id = add_asset(design.assets, data, target.name,
                             mime_for(target), image.width, image.height)
        self._add_asset(asset_id)
        return True

    def _remove_background(self, layer_id: str) -> None:
        layer = self.design.layer(layer_id)
        if not isinstance(layer, ImageLayer):
            return
        design = self.design
        data = asset_bytes(design.assets, layer.asset_id)
        if not data:
            QMessageBox.warning(self, "Remove background",
                                "That image is missing from the design.")
            return
        try:
            image = imaging.open_image(data)
        except Exception as exc:
            QMessageBox.warning(self, "Remove background",
                                f"Could not read that image:\n{exc}")
            return
        dialog = CutoutDialog(image, asset_name(design.assets, layer.asset_id), self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        result = dialog.result_image()
        if result is None:
            return
        encoded = imaging.encode_png(result)
        stem = Path(asset_name(design.assets, layer.asset_id)).stem
        asset_id = add_asset(design.assets, encoded, f"{stem}-cutout.png",
                             "image/png", result.width, result.height)
        layer.original_asset_id = layer.original_asset_id or layer.asset_id
        layer.asset_id = asset_id
        layer.mask = "none"
        layer.mask_feather = 0.0
        self._record("Remove background", f"cutout-{layer.id}")
        self._refresh_all()
        self._flash("Background removed and embedded as a new asset.")

    def _refresh_all(self) -> None:
        self.canvas.refresh()
        self.layers_panel.refresh()
        self.inspector.refresh()
        self.library_panel.refresh()
        self._update_stats()
        self._update_title()
        self._update_actions()

    def _apply_template(self, key: str) -> None:
        if not self._maybe_save():
            return
        try:
            design = templates.build(key)
        except Exception as exc:  # pragma: no cover - defensive
            QMessageBox.critical(self, "Template", f"Could not build it:\n{exc}")
            return
        self._set_design(design, None)
        self._flash(f"Started from {design.name}. Every layer is editable.")

    def _apply_background(self, key: str) -> None:
        try:
            preset = backgrounds.get(key)
        except Exception as exc:  # pragma: no cover - defensive
            QMessageBox.critical(self, "Background", f"Could not apply it:\n{exc}")
            return
        import copy

        self.design.background = copy.deepcopy(preset.background)
        renderer.clear_caches()
        self._record("Apply background", f"bg-preset-{key}")
        self.canvas.refresh(reset=True)
        self.inspector.refresh()
        self.library_panel.refresh()
        self._update_stats()
        self._flash(f"Background set to {preset.name}. Tweak it in Canvas.")

    # ---------------------------------------------------------------- canvas
    def _zoom_in(self) -> None:
        self.canvas.zoom_in()

    def _zoom_out(self) -> None:
        self.canvas.zoom_out()

    def _fit(self) -> None:
        self.canvas.fit()

    def _actual(self) -> None:
        self.canvas.actual_size()

    def _toggle_grid(self) -> None:
        self.canvas.set_grid(self.act_grid.isChecked())
        if self.grid_button.isChecked() != self.act_grid.isChecked():
            self.grid_button.blockSignals(True)
            self.grid_button.setChecked(self.act_grid.isChecked())
            self.grid_button.blockSignals(False)

    def _on_zoom(self, scale: float) -> None:
        self.zoom_label.setText(f"{int(round(scale * 100))}%")
        self.status_zoom.setText(f"{int(round(scale * 100))}%")

    def _canvas_menu(self, position, layer_id: str) -> None:
        design = self.design
        layer = design.layer(layer_id)
        menu = QMenu(self)
        if layer is not None:
            if design.selected != layer.id:
                design.selected = layer.id
                self._sync_selection()
            menu.addAction("Duplicate", self._duplicate_layer)
            menu.addAction("Delete", self._delete_layer)
            menu.addSeparator()
            menu.addAction("Bring forward", lambda: self._reorder(1))
            menu.addAction("Send backward", lambda: self._reorder(-1))
            menu.addAction("Bring to front", lambda: self._vertical(True))
            menu.addAction("Send to back", lambda: self._vertical(False))
            menu.addSeparator()
            menu.addAction("Centre on canvas", self._centre_layer)
            menu.addAction("Flip horizontally", self._flip_h)
            menu.addAction("Flip vertically", self._flip_v)
            menu.addSeparator()
            menu.addAction("Unlock layer" if layer.locked else "Lock layer",
                           self._toggle_lock)
            if isinstance(layer, TextLayer):
                menu.addAction("Edit text", lambda: self._edit_text(layer.id))
            if isinstance(layer, ImageLayer):
                menu.addAction("Remove background\u2026",
                               lambda: self._remove_background(layer.id))
        else:
            menu.addAction("New design\u2026", self._new)
            menu.addAction("Import image\u2026", self._import_image)
            menu.addAction("Fit to window", self._fit)
        menu.exec(position)

    # ------------------------------------------------------------------ help
    def _guide(self) -> None:
        GuideDialog(self).exec()

    def _about(self) -> None:
        AboutDialog(self).exec()

    # ---------------------------------------------------------------- status
    def _flash(self, message: str) -> None:
        self.status_hint.setText(message)
        self._flash_timer.start()

    def _reset_status(self) -> None:
        layer = self.design.active
        self.status_hint.setText(f"Selected: {layer.name}" if layer else "Ready")

    def _update_actions(self) -> None:
        self.act_undo.setEnabled(self.history.can_undo)
        self.act_redo.setEnabled(self.history.can_redo)
        layer = self.design.active
        index = self.design.layers.index(layer) if layer else -1
        has = layer is not None
        self.act_duplicate.setEnabled(has)
        self.act_delete.setEnabled(has)
        self.act_lock.setEnabled(has)
        self.act_lock.setText("Unlock layer" if has and layer.locked else "Lock layer")
        self.act_forward.setEnabled(has and index < len(self.design.layers) - 1)
        self.act_backward.setEnabled(has and index > 0)
        self.act_front.setEnabled(has and index < len(self.design.layers) - 1)
        self.act_back.setEnabled(has and index > 0)
        self.act_centre.setEnabled(has)
        self.act_flip_h.setEnabled(has)
        self.act_flip_v.setEnabled(has)
        self.act_clear.setEnabled(bool(self.design.layers))
        self.act_save.setEnabled(True)
        self.act_save_as.setEnabled(True)

    def _update_stats(self) -> None:
        design = self.design
        self.zoom_label.setText(f"{self.canvas.zoom_percent()}%")
        self.canvas_size_label.setText(
            f"{design.width:,} \u00d7 {design.height:,}  \u00b7  "
            f"{design.preset.ratio_label}")
        self.status_size.setText(
            f"{design.width:,} \u00d7 {design.height:,} px")
        self.status_layers.setText(f"{len(design.layers)} layers")
        self.status_zoom.setText(f"{self.canvas.zoom_percent()}%")
        layer = design.active
        if layer is not None:
            self.status_hint.setText(f"Selected: {layer.name}")
        elif not self.status_hint.text() or self.status_hint.text().startswith(
                "Selected:"):
            self.status_hint.setText("Ready")

    def _update_title(self) -> None:
        marker = " *" if self._dirty else ""
        project = f"  \u00b7  {self.path.name}" if self.path else ""
        self.setWindowTitle(
            f"{self.design.name}{marker}{project} \u2014 {branding.APP_NAME}")

    # ------------------------------------------------------------- lifecycle
    @staticmethod
    def _dropped_files(mime) -> tuple[list[Path], list[Path]]:
        projects: list[Path] = []
        images: list[Path] = []
        if not mime.hasUrls():
            return projects, images
        for url in mime.urls():
            if not url.isLocalFile():
                continue
            path = Path(url.toLocalFile())
            if not path.is_file():
                continue
            suffix = path.suffix.lower()
            if suffix == ".umbra":
                projects.append(path)
            elif suffix in IMAGE_SUFFIXES:
                images.append(path)
        return projects, images

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        projects, images = self._dropped_files(event.mimeData())
        if projects or images:
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:  # noqa: N802
        projects, images = self._dropped_files(event.mimeData())
        if not projects and not images:
            event.ignore()
            return
        event.acceptProposedAction()
        if projects:
            self._open_path(projects[0])
            return
        imported = sum(1 for path in images if self._import_image_path(path))
        if imported:
            self._flash(f"Imported {imported} image"
                        f"{'s' if imported != 1 else ''} by drag and drop.")

    def _restore_geometry(self) -> None:
        geometry_data = self.settings.value("window_geometry")
        if geometry_data:
            self.restoreGeometry(geometry_data)

    def closeEvent(self, event) -> None:  # noqa: N802
        if not self._maybe_save():
            event.ignore()
            return
        self.settings.setValue("window_geometry", self.saveGeometry())
        event.accept()
