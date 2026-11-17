"""Emoji catalogue, search, picking and rendering."""

from __future__ import annotations

import collections

import numpy as np
import pytest
from PySide6.QtGui import QImage

from umbraforge import emojis, renderer
from umbraforge.layers import Design, EmojiLayer, Layer


def alpha_map(image: QImage) -> np.ndarray:
    converted = image.convertToFormat(QImage.Format.Format_RGBA8888)
    width, height = converted.width(), converted.height()
    stride = converted.bytesPerLine()
    data = bytes(converted.constBits())
    rows = np.frombuffer(data, dtype=np.uint8).reshape(height, stride)
    return rows[:, : width * 4].reshape(height, width, 4)[..., 3]


def test_catalogue_is_unique_and_categorised():
    assert len(emojis.EMOJIS) >= 400
    chars = [item.char for item in emojis.EMOJIS]
    assert len(chars) == len(set(chars))
    assert emojis.categories() == [
        "Smileys", "People", "Nature", "Food", "Activity", "Travel",
        "Objects", "Symbols", "Flags"]
    counts = collections.Counter(item.category for item in emojis.EMOJIS)
    assert all(counts[category] >= 5 for category in emojis.categories())
    assert emojis.get("\U0001F600").name == "Grinning face"


def test_search_matches_names_and_keywords():
    laugh = emojis.entries(needle="laugh")
    assert laugh
    assert any(item.char == "\U0001F602" for item in laugh)

    fire = emojis.entries(needle="FIRE")
    assert any(item.char == "\U0001F525" for item in fire)

    food = emojis.entries("Food", "pizza")
    assert [item.char for item in food] == ["\U0001F355"]
    assert emojis.entries("Food", "pizza") == emojis.entries(
        category="Food", needle="pizza")
    assert emojis.entries("Nature", "pizza") == []


def test_recents_are_ordered_deduplicated_and_bounded():
    emojis.clear_recent()
    emojis.remember("\U0001F600")
    emojis.remember("\U0001F525")
    emojis.remember("\U0001F600")
    recent = emojis.recent()
    assert [item.char for item in recent] == ["\U0001F600", "\U0001F525"]
    for index in range(40):
        emojis.remember(emojis.EMOJIS[index].char)
    assert len(emojis.recent()) <= 14
    emojis.clear_recent()
    assert emojis.recent() == []


@pytest.mark.skipif(not emojis.available(), reason="no colour emoji font")
def test_glyphs_render_as_square_pngs():
    for char in ("\U0001F600", "\U0001F984", "\U0001F1FA\U0001F1F8"):
        data = emojis.glyph_png(char, 64)
        assert data.startswith(b"\x89PNG")
    tinted = emojis.glyph_png("\U0001F600", 64, "#ff0000")
    assert tinted.startswith(b"\x89PNG")
    assert tinted != emojis.glyph_png("\U0001F600", 64)


def test_emoji_layer_round_trips():
    layer = EmojiLayer(name="Spark", char="\U0001F525", color="#ff0000",
                       x=0.2, y=0.3, w=0.25, h=0.25, opacity=0.75)
    data = layer.to_dict()
    assert data["kind"] == "emoji"
    assert data["char"] == "\U0001F525"

    restored = Layer.from_dict(data)
    assert isinstance(restored, EmojiLayer)
    assert restored.char == "\U0001F525"
    assert restored.color == "#ff0000"
    assert restored.opacity == pytest.approx(0.75)

    legacy = EmojiLayer.from_dict({"kind": "emoji", "id": "e1"})
    assert legacy.char == "\U0001F600"
    assert legacy.color == ""

    renamed = EmojiLayer(name="Hero", char="\U0001F525")
    assert renamed.describe() == "Hero \u00b7 Fire"
    assert EmojiLayer(char="\U0001F525").describe() == "Fire"


@pytest.mark.skipif(not emojis.available(), reason="no colour emoji font")
def test_renderer_paints_emoji_pixels(qapp):
    design = Design(name="Emoji")
    design.set_size(160, 160)
    design.background.update(kind="solid", color="#101018")
    design.add(EmojiLayer(char="\U0001F600", x=0.2, y=0.2, w=0.6, h=0.6))
    image = renderer.render_design(design, 160, 160)
    alpha = alpha_map(image)
    assert alpha.max() == 255
    # The backdrop is opaque; the glyph must introduce bright pixels too.
    rgb = image.convertToFormat(QImage.Format.Format_RGBA8888)
    data = np.frombuffer(bytes(rgb.constBits()), dtype=np.uint8)
    assert data.max() > 200


@pytest.mark.skipif(not emojis.available(), reason="no colour emoji font")
def test_export_accepts_path_objects(qapp, tmp_path):
    design = Design(name="Emoji")
    design.set_size(96, 96)
    design.background.update(kind="solid", color="#101018")
    design.add(EmojiLayer(char="\U0001F984", x=0.2, y=0.2, w=0.6, h=0.6))
    target = tmp_path / "emoji.png"
    assert renderer.save_image(design, target, 96) is True
    assert target.stat().st_size > 0
