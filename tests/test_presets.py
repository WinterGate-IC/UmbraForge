"""Canvas presets and their interaction with the document model."""

from __future__ import annotations

import pytest

from umbraforge import presets
from umbraforge.layers import Design, ShapeLayer

REQUIRED = ("profile", "square", "desktop", "mobile", "banner", "poster",
            "custom")


def test_presets_are_unique_and_complete():
    keys = [preset.key for preset in presets.PRESETS]
    assert len(keys) == len(set(keys))
    for key in REQUIRED:
        assert key in keys
    for preset in presets.PRESETS:
        assert preset.name and preset.category
        assert preset.width > 0 and preset.height > 0
        assert preset.width <= 8192 and preset.height <= 8192


def test_lookup_falls_back_to_the_default():
    assert presets.get("profile").key == "profile"
    assert presets.get("does-not-exist").key == presets.DEFAULT_PRESET


def test_ratio_labels_are_readable():
    assert presets.get("desktop").ratio_label == "16:9"
    assert presets.get("profile").ratio_label == "1:1"
    assert presets.get("mobile").ratio_label == "9:16"
    assert presets.get("poster").ratio_label == "2:3"
    assert presets.get("custom").ratio_label == "1:1"

    odd = presets.for_size(1000, 333)
    assert odd.key == "custom"
    assert odd.ratio_label == "3.00:1"


def test_shape_categories():
    assert presets.get("profile").shape == "square"
    assert presets.get("desktop").shape == "wide"
    assert presets.get("mobile").shape == "tall"


def test_for_size_and_key_for_size():
    assert presets.for_size(3840, 2160).key == "desktop"
    assert presets.for_size(1200, 1200).key == "profile"
    assert presets.for_size(777, 777).key == "custom"
    assert presets.key_for_size(1080, 1920) == "mobile"


@pytest.mark.parametrize("value,expected", [
    (0, 64),
    (-10, 64),
    (500, 500),
    (99999, 8192),
])
def test_clamp_size(value, expected):
    assert presets.clamp_size(value) == expected


def test_clamp_size_honours_bounds():
    assert presets.clamp_size(10, low=4, high=20) == 10
    assert presets.clamp_size(1, low=4, high=20) == 4
    assert presets.clamp_size(99, low=4, high=20) == 20


def test_design_preset_switch_keeps_normalized_geometry():
    design = Design()
    layer = design.add(ShapeLayer(x=0.1, y=0.2, w=0.3, h=0.4))
    design.set_preset("desktop")
    assert (design.width, design.height) == (3840, 2160)
    assert design.preset_key == "desktop"
    assert design.preset.ratio_label == "16:9"
    assert (layer.x, layer.y, layer.w, layer.h) == (0.1, 0.2, 0.3, 0.4)

    design.set_preset("mobile")
    assert (design.width, design.height) == (1080, 1920)
    assert (layer.x, layer.y, layer.w, layer.h) == (0.1, 0.2, 0.3, 0.4)


def test_design_custom_size_is_clamped():
    design = Design()
    design.set_size(1, 99999)
    assert (design.width, design.height) == (64, 8192)
    design.set_preset("custom", width=1234, height=567)
    assert (design.width, design.height) == (1234, 567)
    assert design.describe_size().startswith("1,234")


def test_design_preset_guess_for_custom_size():
    design = Design()
    design.set_size(1600, 1600)
    assert design.preset_key == "custom"
    design.set_size(1500, 500)
    assert design.preset_key == "banner"
