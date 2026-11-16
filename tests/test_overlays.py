"""Canvas overlays: catalogue integrity, raster behaviour and persistence."""

from __future__ import annotations

from PIL import Image, ImageDraw

from umbraforge import layers, overlays, renderer


def sample() -> Image.Image:
    image = Image.new("RGBA", (140, 140), (32, 20, 58, 255))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((24, 30, 116, 110), radius=16,
                           fill=(255, 122, 61, 255))
    draw.ellipse((50, 46, 90, 86), fill=(245, 242, 255, 255))
    return image


def test_the_catalogue_is_large_unique_and_grouped():
    assert len(overlays.PRESETS) >= 40
    keys = [preset.key for preset in overlays.PRESETS]
    assert len(keys) == len(set(keys))
    assert len(overlays.OVERLAY_DEFAULTS) >= 20
    categories = overlays.categories()
    assert len(categories) >= 8
    assert len(categories) == len(set(categories))
    for preset in overlays.PRESETS:
        assert preset.label and preset.note and preset.category
        assert overlays.get(preset.key) is preset
        stack = preset.apply()
        assert stack["preset"] == preset.key
        assert overlays.any_enabled(stack)


def test_presets_filter_and_describe():
    assert overlays.describe({}) == "No overlay"
    preset = overlays.PRESETS[0]
    assert overlays.describe(preset.apply()) == preset.label
    film = overlays.entries("Film")
    assert film and all(item.category == "Film" for item in film)
    assert overlays.entries(None, "grain")


def test_the_default_stack_is_a_pixel_identical_no_op():
    base = sample()
    out = overlays.apply_stack(base, overlays.default_stack(), 140, 140)
    assert out is base
    assert out.tobytes() == base.tobytes()


def test_every_preset_changes_pixels_and_keeps_size():
    base = sample()
    for preset in overlays.PRESETS:
        out = overlays.apply_stack(base, preset.apply(), 140, 140)
        assert out.size == base.size, preset.key
        assert out.mode == "RGBA"
        assert out.tobytes() != base.tobytes(), preset.key


def test_an_unknown_overlay_name_is_ignored():
    base = sample()
    stack = overlays.default_stack()
    stack["not_a_real_overlay"] = {"enabled": True, "opacity": 1.0}
    out = overlays.apply_stack(base, stack, 140, 140)
    assert out.tobytes() == base.tobytes()


def test_every_preview_renders_and_is_cached():
    for preset in overlays.PRESETS:
        data = overlays.preview_png(preset.key)
        assert data.startswith(b"\x89PNG"), preset.key
        assert data == overlays.preview_png(preset.key)


def test_overlays_survive_a_design_round_trip():
    design = layers.Design(name="Overlay test", width=400, height=400)
    design.overlays = overlays.stack_for("vhs_tape")
    clone = layers.Design.from_dict(design.to_dict())
    assert clone.overlays == design.overlays
    assert clone.overlays["preset"] == "vhs_tape"
    assert overlays.enabled(clone.overlays, "scanlines")


def test_old_projects_without_overlays_stay_a_no_op():
    design = layers.Design(name="Legacy", width=400, height=400)
    data = design.to_dict()
    data.pop("overlays", None)
    restored = layers.Design.from_dict(data)
    assert not overlays.any_enabled(restored.overlays)
    assert restored.overlays["preset"] == ""


def test_renderer_composites_the_overlay_stack(qapp):
    design = layers.Design(name="Render", width=400, height=400)
    plain = renderer.render_design(design, 400, 400)
    design.overlays = overlays.stack_for("comic_dots")
    decorated = renderer.render_design(design, 400, 400)
    assert plain.size() == decorated.size()
    plain = plain.convertToFormat(plain.Format.Format_RGBA8888)
    decorated = decorated.convertToFormat(decorated.Format.Format_RGBA8888)
    assert plain.bits().tobytes() != decorated.bits().tobytes()


def test_overlay_shelf_applies_clears_and_undoes(window):
    from PySide6.QtWidgets import QApplication, QWidget

    panel = window.library_panel
    labels = panel.section_labels()
    assert "Overlays" in labels
    panel.show_section(labels.index("Overlays"))
    QApplication.processEvents()
    page = panel.pages.widget(labels.index("Overlays"))
    cards = [widget for widget in page.findChildren(QWidget)
             if widget.__class__.__name__ == "Card"]
    assert len(cards) >= len(overlays.PRESETS) >= 40

    window._apply_overlay("vhs_tape")
    assert window.design.overlays["preset"] == "vhs_tape"
    assert overlays.any_enabled(window.design.overlays)
    assert "VHS tape" in panel._overlay_active.text()

    window._clear_overlays()
    assert not overlays.any_enabled(window.design.overlays)

    window._apply_overlay("comic_dots")
    assert overlays.enabled(window.design.overlays, "halftone")
    window._undo()
    assert not overlays.any_enabled(window.design.overlays)


def test_inspector_can_pick_and_clear_an_overlay(window):
    window.inspector.overlay_combo.setCurrentIndex(
        window.inspector.overlay_combo.findData("halftone_press"))
    assert window.design.overlays["preset"] == "halftone_press"
    assert overlays.enabled(window.design.overlays, "halftone")

    window.inspector.overlay_combo.setCurrentIndex(0)
    assert not overlays.any_enabled(window.design.overlays)
    assert "exactly as saved" in window.inspector.overlay_info.text()
