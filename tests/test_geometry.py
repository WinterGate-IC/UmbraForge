"""Vector shapes and icons."""

from __future__ import annotations

import pytest

from umbraforge import geometry


@pytest.mark.parametrize("key", list(geometry.SHAPES))
def test_every_shape_builds_a_path(qapp, key):
    path = geometry.shape_path(key)
    assert not path.isEmpty()
    bounds = path.boundingRect()
    assert bounds.width() > 0.3
    assert bounds.height() > 0.3
    assert -0.2 <= bounds.left() <= 1.2
    assert -0.2 <= bounds.top() <= 1.2
    assert -0.2 <= bounds.right() <= 1.2
    assert -0.2 <= bounds.bottom() <= 1.2


@pytest.mark.parametrize("key", list(geometry.ICONS))
def test_every_icon_builds_a_path(qapp, key):
    path = geometry.icon_path(key)
    assert not path.isEmpty()
    bounds = path.boundingRect()
    assert bounds.width() > 0.15
    assert bounds.height() > 0.15
    assert -0.2 <= bounds.left() <= 1.2
    assert -0.2 <= bounds.top() <= 1.2


def test_lookup_tables_are_complete():
    assert len(geometry.SHAPES) >= 20
    assert len(geometry.ICONS) >= 18
    for key, (label, builder) in geometry.SHAPES.items():
        assert label and callable(builder)
        assert geometry.shape_label(key) == label
    for key, (label, builder) in geometry.ICONS.items():
        assert label and callable(builder)
        assert geometry.icon_label(key) == label


def test_unknown_keys_fall_back(qapp):
    fallback_shape = geometry.shape_path("no-such-shape")
    assert fallback_shape == geometry.shape_path("circle")
    fallback_icon = geometry.icon_path("no-such-icon")
    assert fallback_icon == geometry.icon_path("star")
    assert geometry.shape_label("no-such-shape") == "Custom"
    assert geometry.icon_label("no-such-icon") == "Icon"


def test_paths_are_cached(qapp):
    geometry.shape_path("shield")
    geometry.icon_path("skull")
    count = len(geometry._CACHE)
    geometry.shape_path("shield")
    geometry.icon_path("skull")
    assert len(geometry._CACHE) == count


@pytest.mark.parametrize("key", ["circle", "shield", "star12", "wave"])
def test_scaled_paths_fit_the_box(qapp, key):
    path = geometry.shape_path(key)
    mapped = geometry.scaled(path, 240, 120)
    bounds = mapped.boundingRect()
    assert bounds.left() >= -240 * 0.2
    assert bounds.top() >= -120 * 0.2
    assert bounds.right() <= 240 * 1.2
    assert bounds.bottom() <= 120 * 1.2
    # Non-square boxes must actually stretch the shape.
    assert bounds.width() > 50
    assert bounds.height() > 40
