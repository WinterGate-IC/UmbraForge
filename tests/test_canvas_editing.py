"""Canvas-tab editing: background presets, colour flip and overlay mixing."""

from __future__ import annotations

from umbraforge import backgrounds, layers, overlays


def test_background_preset_combo_applies_a_preset(window):
    inspector = window.inspector
    preset = backgrounds.PRESETS[0]
    index = inspector.bg_preset.findData(preset.key)
    assert index > 0
    inspector.bg_preset.setCurrentIndex(index)
    assert window.design.background == preset.background
    assert inspector.bg_preset.currentData() == preset.key


def test_background_colour_swap_and_randomise(window, monkeypatch):
    design = window.design
    design.background.update(kind="linear", color="#111111",
                             color2="#222222")
    window.inspector.refresh()
    window.inspector._swap_background_colours()
    assert design.background["color"] == "#222222"
    assert design.background["color2"] == "#111111"

    preset = backgrounds.PRESETS[-1]
    monkeypatch.setattr("umbraforge.ui.inspector.random.choice",
                        lambda _items: preset)
    window.inspector._randomise_background()
    assert design.background == preset.background


def test_overlay_mixer_enables_and_tunes_one_component(window):
    inspector = window.inspector
    design = window.design
    index = inspector.overlay_part.findData("grain")
    assert index > 0
    inspector.overlay_part.setCurrentIndex(index)

    inspector._set_overlay_value("grain", "enabled", True)
    inspector._set_overlay_value("grain", "opacity", 0.42)
    inspector._set_overlay_value("grain", "color", "#abcdef")
    inspector._set_overlay_value("grain", "size", 0.66)

    entry = design.overlays["grain"]
    assert entry["enabled"] is True
    assert entry["opacity"] == 0.42
    assert entry["color"] == "#abcdef"
    assert entry["size"] == 0.66
    assert design.overlays["preset"] == "custom"
    assert overlays.any_enabled(design.overlays)
    # Only the chosen component changed.
    assert not design.overlays["rain"]["enabled"]
    assert inspector.overlay_combo.currentData() == "custom"
    assert "Grain" in inspector.overlay_info.text()

    inspector._set_overlay_value("grain", "enabled", False)
    assert not overlays.any_enabled(design.overlays)
    assert design.overlays["preset"] == ""
    assert inspector.overlay_combo.currentData() == ""


def test_overlay_mixer_builds_controls_for_every_primitive(window):
    from PySide6.QtWidgets import QCheckBox

    inspector = window.inspector
    for name in overlays.OVERLAY_DEFAULTS:
        index = inspector.overlay_part.findData(name)
        assert index > 0, name
        inspector.overlay_part.setCurrentIndex(index)
        assert inspector.overlay_mix_layout.count() > 0
        checks = inspector.overlay_mix.findChildren(QCheckBox)
        assert checks
        pretty = overlays.OVERLAY_LABELS[name]
        assert checks[0].text() == f"Enable {pretty}"


def test_old_files_without_emoji_or_mixer_still_load():
    data = {
        "name": "Legacy",
        "width": 800,
        "height": 600,
        "layers": [{"kind": "shape", "id": "s1", "shape": "circle"}],
        "background": {"kind": "solid", "color": "#000000"},
        "overlays": {"preset": "silent"},
    }
    design = layers.Design.from_dict(data)
    assert design.layers[0].shape == "circle"
    assert design.background["color"] == "#000000"
    assert design.overlays["preset"] == "silent"

def test_two_quick_canvas_presets_are_two_undo_steps(window):
    from umbraforge import presets

    inspector = window.inspector
    design = window.design
    window.history.reset()
    before = (design.width, design.height)
    first, second = presets.PRESETS[1], presets.PRESETS[2]

    inspector.preset_combo.setCurrentIndex(
        inspector.preset_combo.findData(first.key))
    inspector.preset_combo.setCurrentIndex(
        inspector.preset_combo.findData(second.key))
    assert (design.width, design.height) == (second.width, second.height)
    assert window.history.cursor == 2

    window._undo()
    assert (design.width, design.height) == (first.width, first.height)
    window._undo()
    assert (design.width, design.height) == before
