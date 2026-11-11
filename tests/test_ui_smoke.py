"""Window-level smoke tests: the wiring between panels actually works."""

from __future__ import annotations

from PIL import Image
from PySide6.QtWidgets import QPushButton

from umbraforge import branding, presets
from umbraforge.layers import IconLayer, ShapeLayer, TextLayer


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

    window._add_text("display")
    assert isinstance(window.design.active, TextLayer)
    assert len(window.design.layers) == before + 3
    assert window.design.active.text
    # Adding text opens the words field, ready to replace the sample.
    assert window.inspector._text_editor is not None
    assert window.inspector._text_editor.toPlainText() == window.design.active.text


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
    assert labels == ["Start", "Backgrounds", "Shapes", "Icons", "Text",
                      "Fonts", "Images"]
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


def test_icon_grids_reflow_to_the_rail_width(window):
    from PySide6.QtWidgets import QApplication, QWidget

    window.resize(1080, 700)
    window.show()
    panel = window.library_panel
    panel.show_section(panel.section_labels().index("Shapes"))
    QApplication.processEvents()
    grids = [widget for widget in panel.pages.widget(2).findChildren(QWidget)
             if widget.__class__.__name__ == "IconGrid"]
    assert grids
    for grid in grids:
        assert grid.columns() * grid.CELL + (grid.columns() - 1) * grid.GAP \
            <= grid.width()
        assert grid.columns() >= 4


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
