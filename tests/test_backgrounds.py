"""Background presets and the thumbnails the Build rail shows for them."""

from __future__ import annotations

import numpy as np
import pytest

from umbraforge import backgrounds, layers, renderer
from umbraforge.ui.library import BackgroundCard


def test_presets_are_unique_and_labelled():
    keys = [preset.key for preset in backgrounds.PRESETS]
    assert len(keys) == len(set(keys))
    assert len(keys) == len(backgrounds.PRESET_MAP)
    assert "transparent" in keys
    for preset in backgrounds.PRESETS:
        assert preset.name and preset.note and preset.category
        assert preset.background["kind"] in (
            "linear", "radial", "solid", "image", "transparent")


def test_categories_are_stable():
    expected = ["Classic", "Warm", "Cool", "Minimal", "Tech", "Retro",
                "Utility"]
    assert backgrounds.categories() == expected


def _mean(image) -> float:
    image = image.convertToFormat(image.Format.Format_RGBA8888)
    array = np.frombuffer(image.bits(), dtype=np.uint8).reshape(
        (image.height(), image.width(), 4))
    return float(array[..., :3].mean())


@pytest.mark.parametrize("preset", backgrounds.PRESETS,
                         ids=[preset.key for preset in backgrounds.PRESETS])
def test_every_preset_renders(qapp, preset):
    design = layers.Design(name=preset.name, width=320, height=320)
    design.background = layers.merge(layers.default_background(),
                                     preset.background)
    image = renderer.render_thumbnail(design, 160)
    assert not image.isNull()
    assert image.width() > 0 and image.height() > 0
    if preset.key == "transparent":
        image = image.convertToFormat(image.Format.Format_RGBA8888)
        array = np.frombuffer(image.bits(), dtype=np.uint8).reshape(
            (image.height(), image.width(), 4))
        assert int(array[..., 3].max()) == 0
    else:
        # A preset that looks like an empty black card is a bug: every visible
        # preset must put some actual colour on the canvas.
        assert _mean(image) >= 8.0


def test_rail_cards_get_a_thumbnail(window):
    panel = window.library_panel
    panel._build_backgrounds()
    while panel._bg_thumb_queue:
        panel._render_next_bg_thumb()

    assert panel._bg_cards
    for card in panel._bg_cards:
        assert isinstance(card, BackgroundCard)
        pixmap = card.swatch.pixmap()
        assert pixmap is not None and not pixmap.isNull(), card.preset.key
        assert pixmap.width() == 72 and pixmap.height() == 70


def test_transparent_preset_is_actually_transparent(qapp):
    preset = backgrounds.get("transparent")
    design = layers.Design(name="Overlay", width=512, height=512)
    design.background = layers.merge(layers.default_background(),
                                     preset.background)
    image = renderer.render_design(design, 512, 512)
    image = image.convertToFormat(image.Format.Format_RGBA8888)
    array = np.frombuffer(image.bits(), dtype=np.uint8).reshape(
        (512, 512, 4))
    assert int(array[..., 3].max()) == 0
