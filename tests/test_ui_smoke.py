"""Window-level smoke tests: the wiring between panels actually works."""

from __future__ import annotations

from PIL import Image
from PySide6.QtWidgets import QPushButton

from umbraforge import branding, presets
from umbraforge.layers import EmojiLayer, IconLayer, ShapeLayer, TextLayer


def test_window_starts_with_an_editable_template(window):
    assert window.design.layers
    assert branding.APP_NAME in window.windowTitle()
    assert window.canvas is not None
    assert window.layers_panel is not None
    assert window.inspector is not None
    assert window.status_hint.text()


def test_add_shape_icon_and_text(window):
    before = len(window.design.layers)

    window._add_shape("circle")
    added = window.design.active
    assert isinstance(added, ShapeLayer)
    assert added.shape == "circle"
    assert len(window.design.layers) == before + 1

    window._add_icon("skull")
    assert isinstance(window.design.active, IconLayer)
    assert len(window.design.layers) == before + 2

    window._add_emoji("\U0001F525")
    assert isinstance(window.design.active, EmojiLayer)
    assert window.design.active.char == "\U0001F525"
    assert len(window.design.layers) == before + 3

    window._add_text("display")
    assert isinstance(window.design.active, TextLayer)
    assert len(window.design.layers) == before + 4
    assert window.design.active.text
    # Adding text opens the words field, ready to replace the sample.
    assert window.inspector._text_editor is not None
    assert window.inspector._text_editor.toPlainText() == window.design.active.text


def test_rail_swaps_selected_shape_icon_and_emoji(window):
    window._add_shape("circle")
    shape = window.design.active
    assert shape.name.startswith("Circle")
    window._swap_shape("star5")
    assert shape.shape == "star5"
    assert shape.name.startswith("Five-point star")
    assert window.design.active is shape

    window._add_icon("star")
    icon = window.design.active
    window._swap_icon("skull")
    assert icon.icon == "skull"
    assert icon.name.startswith("Skull")

    window._add_emoji("\U0001F600")
    emoji = window.design.active
    window._swap_emoji("\U0001F984")
    assert emoji.char == "\U0001F984"
    assert emoji.name == "Unicorn"

    # Swapping only edits the selected layer; it never adds another.
    count = len(window.design.layers)
    window._swap_shape("hexagon")
    assert shape.shape == "star5"          # selection moved to the emoji layer
    assert len(window.design.layers) == count
    window._undo()
    assert window.design.layer(emoji.id).char == "\U0001F600"


def test_inspector_edits_an_emoji_layer(window, qapp):
    window._add_emoji("\U0001F525")
    layer = window.design.active
    inspector = window.inspector
    inspector.refresh()

    inspector._set_emoji_tint(layer, True)
    assert layer.color
    inspector._set_emoji_tint_colour(layer, "#00ff66")
    assert layer.color == "#00ff66"
    inspector._set_emoji_tint(layer, False)
    assert layer.color == ""

    inspector._use_recent_emoji(layer, "\U0001F984")
    assert layer.char == "\U0001F984"
    qapp.processEvents()
    assert inspector.kind_note.text() == "Unicorn"

    window._undo()
    assert window.design.layer(layer.id).char == "\U0001F525"


def test_text_is_discoverable_in_the_rail_and_menus(window):
    panel = window.library_panel
    labels = panel.section_labels()
    assert "Text" in labels
    assert "Type" not in labels

    text_tab = panel.pages.widget(labels.index("Text"))
    assert any(button.text() == "Add text"
               for button in text_tab.findChildren(QPushButton))
    # The rail, the top bar, the Edit menu and the empty-canvas menu all
    # offer the same action, so it does not hide behind a tab overflow.
    assert window.act_add_text.text() == "Add text"
    assert window.act_add_text.shortcut().toString() == "Ctrl+T"
    assert window.act_edit_text.text() == "Edit text"
    assert window.act_edit_text.shortcut().toString() == "F2"


def test_all_build_sections_are_visible_and_reversible(window):
    panel = window.library_panel
    labels = panel.section_labels()
    assert labels == ["Start", "Templates", "Backgrounds", "Overlays",
                      "Shapes", "Icons", "Emoji", "Effects", "Text", "Fonts",
                      "Images"]
    for index, label in enumerate(labels):
        panel.show_section(index)
        assert panel.current_section() == index
        assert panel._section_buttons[index].isChecked()
    # Going right and back left is a click, not an overflow arrow.
    panel.show_section(labels.index("Text"))
    panel.show_section(labels.index("Start"))
    assert panel.current_section() == 0
    assert panel._section_buttons[0].isChecked()


def test_add_text_action_adds_a_focused_text_layer(window):
    count = len(window.design.layers)
    window.act_add_text.trigger()
    layer = window.design.active
    assert isinstance(layer, TextLayer)
    assert len(window.design.layers) == count + 1
    assert window.act_edit_text.isEnabled()
    assert window.inspector._text_editor is not None
    assert window.inspector._text_editor.toPlainText() == layer.text


def test_edit_text_action_tracks_the_selection(window):
    text_layer = next(layer for layer in window.design.layers
                      if isinstance(layer, TextLayer))
    window.design.selected = text_layer.id
    window._sync_selection()
    assert window.act_edit_text.isEnabled()

    window._add_shape("circle")
    window._sync_selection()
    assert not window.act_edit_text.isEnabled()


def test_build_rail_never_clips_its_contents(window):
    """Every Build section must fit the rail: no sideways scroll, no cut-off."""
    from PySide6.QtWidgets import QApplication, QScrollArea, QWidget

    window.resize(1080, 700)
    window.show()
    QApplication.processEvents()
    panel = window.library_panel
    for index, label in enumerate(panel.section_labels()):
        panel.show_section(index)
        QApplication.processEvents()
        page = panel.pages.widget(index)
        area = (page if isinstance(page, QScrollArea)
                else page.findChild(QScrollArea))
        assert area is not None, label
        assert area.horizontalScrollBar().maximum() == 0, label
        body = area.widget()
        assert body.width() <= area.viewport().width() + 1, label
        for child in body.findChildren(QWidget):
            if not child.isVisible():
                continue
            right = child.mapTo(body, child.rect().topLeft()).x() + child.width()
            assert right <= body.width() + 1, (
                f"{label}: {child.__class__.__name__} sticks out")


def test_lazily_built_sections_scroll_to_their_full_content(window):
    """Sections filled on first view must expose everything below the fold."""
    from PySide6.QtWidgets import QApplication, QScrollArea

    window.resize(1080, 700)
    window.show()
    panel = window.library_panel
    for label in ("Templates", "Backgrounds", "Overlays", "Emoji", "Effects"):
        index = panel.section_labels().index(label)
        panel.show_section(index)
        for _ in range(3):
            QApplication.processEvents()
        page = panel.pages.widget(index)
        area = (page if isinstance(page, QScrollArea)
                else page.findChild(QScrollArea))
        assert area is not None, label
        body = area.widget()
        content = body.layout().sizeHint().height()
        assert content > area.viewport().height(), label
        assert body.height() >= content, label
        assert area.verticalScrollBar().maximum() > 0, label


def test_icon_grids_reflow_to_the_rail_width(window):
    from PySide6.QtWidgets import QApplication, QWidget

    window.resize(1080, 700)
    window.show()
    panel = window.library_panel
    panel.show_section(panel.section_labels().index("Shapes"))
    QApplication.processEvents()
    grids = [widget for widget in panel.pages.widget(4).findChildren(QWidget)
             if widget.__class__.__name__ == "IconGrid"]
    assert grids
    for grid in grids:
        assert grid.columns() * grid.CELL + (grid.columns() - 1) * grid.GAP \
            <= grid.width()
        assert grid.columns() >= 4


def test_effects_shelf_offers_the_whole_library(window):
    from PySide6.QtWidgets import QApplication, QWidget

    from umbraforge import effects

    panel = window.library_panel
    labels = panel.section_labels()
    assert "Effects" in labels
    panel.show_section(labels.index("Effects"))
    QApplication.processEvents()
    page = panel.pages.widget(labels.index("Effects"))
    cards = [widget for widget in page.findChildren(QWidget)
             if widget.__class__.__name__ == "Card"]
    assert len(cards) >= len(effects.PRESETS) >= 70
    assert len(effects.categories()) >= 5


def test_effects_apply_clear_and_undo(window):
    from umbraforge import effects

    layer = window.design.active
    window._apply_effect("outline_white")
    assert layer.effects["preset"] == "outline_white"
    assert layer.effects["outline"]["enabled"]

    window._clear_effects()
    assert not effects.any_enabled(layer.effects)

    window._apply_effect("glitch_heavy")
    assert effects.enabled(window.design.active.effects, "glitch")
    window._undo()
    assert not effects.any_enabled(window.design.active.effects)


def test_effect_presets_survive_a_project_round_trip(window):
    from umbraforge import effects
    from umbraforge.layers import Design

    window._apply_effect("neon_night")
    design = Design.from_dict(window.design.to_dict())
    stack = design.active.effects
    assert stack["preset"] == "neon_night"
    assert effects.describe(stack) == "Neon night"


def test_loading_a_stack_with_new_effects_keeps_old_files_valid():
    from umbraforge import effects
    from umbraforge.layers import ShapeLayer

    layer = ShapeLayer.from_dict({
        "kind": "shape", "id": "abc", "effects": {
            "shadow": {"enabled": True, "blur": 0.02},
            "glow": {"enabled": True, "color": "#00ffcc"},
        },
    })
    assert layer.effects["shadow"]["blur"] == 0.02
    assert layer.effects["glow"]["color"] == "#00ffcc"
    assert layer.effects["outline"]["enabled"] is False
    assert effects.any_enabled(layer.effects)


def test_layer_styles_copy_between_layers(window):
    from umbraforge import effects

    design = window.design
    source, target = design.layers[2], design.layers[3]
    design.selected = source.id
    window._apply_effect("synthwave")
    window._copy_style()
    assert window._style_clipboard["preset"] == "synthwave"

    design.selected = target.id
    window.inspector.refresh()
    assert not effects.any_enabled(target.effects)
    window._paste_style()
    assert target.effects["preset"] == "synthwave"
    assert effects.enabled(target.effects, "rays")

    window._undo()
    assert not effects.any_enabled(design.layer(target.id).effects)


def test_undo_and_redo_round_trip(window):
    before = len(window.design.layers)
    window._add_shape("star")
    assert len(window.design.layers) == before + 1

    window._undo()
    assert len(window.design.layers) == before
    assert window.history.can_redo

    window._redo()
    assert len(window.design.layers) == before + 1


def test_duplicate_delete_and_lock(window):
    window._add_shape("hexagon")
    layer = window.design.active
    count = len(window.design.layers)

    window._duplicate_layer()
    assert len(window.design.layers) == count + 1
    assert window.design.active.id != layer.id

    window._toggle_lock()
    assert window.design.active.locked
    window._toggle_lock()
    assert not window.design.active.locked

    window._delete_layer()
    assert len(window.design.layers) == count
    assert window.design.selected is not None


def test_flip_centre_and_reorder(window):
    window._add_shape("diamond")
    layer = window.design.active

    window._flip_h()
    assert layer.flip_h
    window._flip_v()
    assert layer.flip_v

    layer.x, layer.y = 0.05, 0.9
    window._centre_layer()
    assert abs((layer.x + layer.w / 2) - 0.5) < 1e-6
    assert abs((layer.y + layer.h / 2) - 0.5) < 1e-6

    window._reorder(1)
    window._vertical(True)
    assert window.design.layers[-1] is layer


def test_preset_switch_reflows_canvas(window):
    window.inspector.preset_combo.setCurrentIndex(
        window.inspector.preset_combo.findData("desktop"))
    assert (window.design.width, window.design.height) == (3840, 2160)
    assert window.design.preset_key == presets.key_for_size(3840, 2160)

    window.inspector.preset_combo.setCurrentIndex(
        window.inspector.preset_combo.findData("mobile"))
    assert (window.design.width, window.design.height) == (1080, 1920)


def test_applying_a_template_replaces_the_design(window):
    window._apply_template("laurel_standard")
    assert window.design.name == "Laurel Standard"
    assert window.design.preset_key == "profile"
    assert any(isinstance(layer, ShapeLayer) for layer in window.design.layers)


def test_dialogs_construct_offscreen(window):
    from umbraforge.ui import dialogs

    new = dialogs.NewDesignDialog(window)
    try:
        design = new.build_design()
        assert design.name
        assert design.width >= 64
    finally:
        new.deleteLater()

    save = dialogs.SaveDialog(window.design, window)
    try:
        assert save._size()[0] >= 1
        assert save._format() == "png"
        assert save.format_combo.count() >= 9
        assert dialogs.ExportDialog is dialogs.SaveDialog
    finally:
        save.deleteLater()

    source = Image.new("RGBA", (24, 24), (0, 255, 0, 255))
    cutout = dialogs.CutoutDialog(source, "swatch", window)
    try:
        assert cutout.mode_combo.count() == 3
        assert cutout.result_image() is None
    finally:
        cutout.close()
        cutout.deleteLater()

    guide = dialogs.GuideDialog(window)
    about = dialogs.AboutDialog(window)
    assert "shortcut" in guide.windowTitle().lower() or guide.windowTitle()
    assert branding.APP_NAME in about.windowTitle()
    guide.deleteLater()
    about.deleteLater()


# --------------------------------------------------------------------------
# undo grouping for discrete actions
# --------------------------------------------------------------------------
def _blank(window):
    window.design.layers.clear()
    window.design.selected = None
    window.history.reset()


def test_two_quick_deletes_are_two_undo_steps(window):
    design = window.design
    _blank(window)
    window._add_shape("circle")
    window._add_shape("hexagon")
    first, second = design.layers

    design.selected = first.id
    window._delete_layer()
    design.selected = second.id
    window._delete_layer()

    assert window.history.cursor == 4
    assert window.history.labels()[-2:] == ["Delete layer", "Delete layer"]

    window._undo()
    assert len(design.layers) == 1
    window._undo()
    assert len(design.layers) == 2


def test_two_quick_duplicates_are_two_undo_steps(window):
    design = window.design
    _blank(window)
    window._add_shape("circle")
    window._duplicate_layer()
    window._duplicate_layer()

    assert len(design.layers) == 3
    assert window.history.cursor == 3
    assert window.history.labels()[-2:] == ["Duplicate layer", "Duplicate layer"]

    window._undo()
    assert len(design.layers) == 2
    window._undo()
    assert len(design.layers) == 1


def test_two_quick_reorders_are_two_undo_steps(window):
    design = window.design
    _blank(window)
    window._add_shape("circle")
    window._add_shape("hexagon")
    window._add_shape("star5")
    bottom = design.layers[0]
    design.selected = bottom.id

    window._reorder(1)
    window._reorder(1)
    assert window.history.cursor == 5
    assert design.layers.index(design.layer(bottom.id)) == 2

    window._undo()
    assert design.layers.index(design.layer(bottom.id)) == 1
    window._undo()
    assert design.layers.index(design.layer(bottom.id)) == 0


def test_layer_panel_delete_and_duplicate_keep_their_own_steps(window, qapp):
    design = window.design
    panel = window.layers_panel
    _blank(window)
    window._add_shape("circle")
    panel.refresh()
    qapp.processEvents()

    panel.duplicate()
    panel.duplicate()
    assert window.history.cursor == 3
    assert window.history.labels()[-2:] == ["Duplicate layer", "Duplicate layer"]

    panel.delete()
    panel.delete()
    assert window.history.cursor == 5
    assert window.history.labels()[-2:] == ["Delete layer", "Delete layer"]

    window._undo()
    assert len(design.layers) == 2
    window._undo()
    assert len(design.layers) == 3


def test_two_quick_canvas_drags_are_two_undo_steps(window, qapp):
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtTest import QTest

    design = window.design
    _blank(window)
    window.resize(1180, 820)
    window.show()
    qapp.processEvents()
    window._add_shape("circle")
    layer = design.active
    canvas = window.canvas
    canvas.fit()
    qapp.processEvents()

    start_x = layer.x

    def drag(dx: int) -> None:
        current = design.layer(layer.id)
        centre = canvas.to_screen(design.width * (current.x + current.w / 2),
                                  design.height * (current.y + current.h / 2)
                                  ).toPoint()
        end = QPoint(centre.x() + dx, centre.y())
        QTest.mousePress(canvas, Qt.MouseButton.LeftButton,
                         Qt.KeyboardModifier.NoModifier, centre)
        QTest.mouseMove(canvas, end)
        QTest.mouseRelease(canvas, Qt.MouseButton.LeftButton,
                           Qt.KeyboardModifier.NoModifier, end)
        qapp.processEvents()

    drag(60)
    moved_once = design.layer(layer.id).x
    drag(60)
    moved_twice = design.layer(layer.id).x

    assert moved_once != start_x
    assert moved_twice != moved_once
    assert window.history.labels()[-2:] == ["Move layer", "Move layer"]
    assert window.history.cursor == 3

    window._undo()
    assert abs(design.layer(layer.id).x - moved_once) < 1e-6
    window._undo()
    assert abs(design.layer(layer.id).x - start_x) < 1e-6


def test_two_quick_nudges_are_two_undo_steps(window, qapp):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    design = window.design
    _blank(window)
    window._add_shape("circle")
    layer = design.active
    start_x = layer.x
    canvas = window.canvas
    canvas.setFocus()
    qapp.processEvents()

    QTest.keyClick(canvas, Qt.Key.Key_Right)
    qapp.processEvents()
    once = design.layer(layer.id).x
    QTest.keyClick(canvas, Qt.Key.Key_Right)
    qapp.processEvents()
    twice = design.layer(layer.id).x

    assert once > start_x
    assert twice > once
    assert window.history.labels()[-2:] == ["Nudge layer", "Nudge layer"]

    window._undo()
    assert abs(design.layer(layer.id).x - once) < 1e-6
    window._undo()
    assert abs(design.layer(layer.id).x - start_x) < 1e-6


# --------------------------------------------------------------------------
# picker and recent-emoji housekeeping
# --------------------------------------------------------------------------
def test_glyph_picker_clears_each_widget_once(qapp):
    from umbraforge.ui.pickers import GlyphPickerDialog

    dialog = GlyphPickerDialog("shape")
    try:
        assert dialog._tail is not None
        assert dialog._tail not in dialog._grids
        assert dialog.body_layout.count() == 4
        dialog._refresh()
        dialog._refresh()
        assert dialog.body_layout.count() == 4
        dialog._clear()
        assert dialog.body_layout.count() == 1
    finally:
        dialog.close()
        dialog.deleteLater()
        qapp.processEvents()


def test_pick_glyph_disposes_the_dialog(monkeypatch):
    from PySide6.QtWidgets import QDialog

    from umbraforge.ui import pickers

    seen: list[object] = []
    disposed: list[object] = []

    def fake_exec(self):
        seen.append(self)
        return QDialog.DialogCode.Rejected

    monkeypatch.setattr(pickers.GlyphPickerDialog, "exec", fake_exec)
    monkeypatch.setattr(pickers.GlyphPickerDialog, "deleteLater",
                        lambda self: disposed.append(self))

    assert pickers.pick_glyph("shape") == ""
    assert len(seen) == 1
    assert disposed == seen


def test_emoji_recent_strip_updates_without_rebuilding_every_tile(window,
                                                                  monkeypatch,
                                                                  qapp):
    from umbraforge import emojis

    panel = window.library_panel
    index = panel.section_labels().index("Emoji")
    panel.show_section(index)
    qapp.processEvents()

    emojis.clear_recent()
    emojis.remember("\U0001F984")
    monkeypatch.setattr(
        panel, "_refresh_emoji_list",
        lambda: (_ for _ in ()).throw(AssertionError("full emoji rebuild")))
    panel.refresh()
    qapp.processEvents()

    grids = [widget for widget in panel._emoji_recent
             if widget.__class__.__name__ == "IconGrid"]
    assert grids
    assert any(button.toolTip() == "Unicorn" for button in grids[0]._buttons)
    emojis.clear_recent()

def test_two_quick_flips_are_two_undo_steps(window):
    design = window.design
    _blank(window)
    window._add_shape("circle")
    layer = design.active

    window._flip_h()
    once = design.layer(layer.id).flip_h
    window._flip_h()
    twice = design.layer(layer.id).flip_h

    assert once != twice
    assert window.history.labels()[-2:] == ["Flip layer", "Flip layer"]
    assert window.history.cursor == 3

    window._undo()
    assert design.layer(layer.id).flip_h == once
    window._undo()
    assert design.layer(layer.id).flip_h == (not once)


def test_two_quick_lock_toggles_are_two_undo_steps(window):
    design = window.design
    _blank(window)
    window._add_shape("circle")
    layer = design.active

    window._toggle_lock()
    assert design.layer(layer.id).locked is True
    window._toggle_lock()
    assert design.layer(layer.id).locked is False
    assert window.history.labels()[-2:] == ["Lock layer", "Lock layer"]
    assert window.history.cursor == 3

    window._undo()
    assert design.layer(layer.id).locked is True
    window._undo()
    assert design.layer(layer.id).locked is False


def test_undo_and_redo_names_show_the_last_action(window):
    _blank(window)
    window._add_shape("circle")

    assert window.act_undo.text() == "Undo Add shape"
    assert window.undo_button.toolTip() == "Undo Add shape  (Ctrl+Z)"
    window._undo()
    assert window.act_redo.text() == "Redo Add shape"
    assert window.redo_button.toolTip() == "Redo Add shape  (Ctrl+Shift+Z)"
    window._redo()
    assert window.act_undo.text() == "Undo Add shape"


def test_rename_with_whitespace_keeps_the_name_visible(window):
    window.design.name = "Untitled"
    window.name_edit.setText("   ")
    window._rename_design()

    assert window.design.name == "Untitled"
    assert window.name_edit.text() == "Untitled"


def test_maybe_save_warns_when_only_an_image_was_exported(window, monkeypatch):
    from umbraforge.ui import main_window

    window._dirty = True
    prompts: list[str] = []

    def question(_parent, title, _text, *args, **kwargs):
        prompts.append(title)
        if len(prompts) == 1:
            return main_window.QMessageBox.StandardButton.Save
        return main_window.QMessageBox.StandardButton.Cancel

    monkeypatch.setattr(main_window.QMessageBox, "question", question)
    monkeypatch.setattr(window, "_save", lambda: True)

    assert window._maybe_save() is False
    assert prompts == ["Unsaved changes", "Editable design not saved"]
    assert window._dirty is True


def test_new_design_dialog_is_released_after_use(window, monkeypatch):
    from umbraforge.ui import dialogs, main_window

    released = []
    original = dialogs.NewDesignDialog.deleteLater

    def record(self):
        released.append(self)
        original(self)

    monkeypatch.setattr(dialogs.NewDesignDialog, "exec",
                        lambda self: main_window.QDialog.DialogCode.Rejected)
    monkeypatch.setattr(dialogs.NewDesignDialog, "deleteLater", record)
    window._dirty = False

    window._new()

    assert len(released) == 1
