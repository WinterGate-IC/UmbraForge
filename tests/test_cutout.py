"""Background removal maths (offline engines only)."""

from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from umbraforge import cutout


def green_scene(size: int = 40) -> Image.Image:
    """A red square floating on a green background."""
    image = Image.new("RGBA", (size, size), (0, 255, 0, 255))
    low, high = size // 3, size - size // 3
    for y in range(low, high):
        for x in range(low, high):
            image.putpixel((x, y), (220, 30, 40, 255))
    return image


def test_border_color_samples_the_frame():
    image = green_scene()
    assert cutout.border_color(image) == (0, 255, 0)

    tiny = Image.new("RGB", (2, 2), (1, 2, 3))
    assert cutout.border_color(tiny) == (0, 0, 0)


def test_border_connected_keeps_the_edge_and_spares_the_middle():
    candidate = np.zeros((5, 5), dtype=bool)
    candidate[0, :] = True
    candidate[-1, :] = True
    candidate[:, 0] = True
    candidate[:, -1] = True
    candidate[2, 2] = True  # an island, not connected to the border
    visited = cutout.border_connected(candidate)
    assert visited[0, 0]
    assert visited[4, 4]
    assert not visited[2, 2]
    assert visited.sum() == 16


def test_border_connected_handles_empty_arrays():
    empty = np.zeros((0, 0), dtype=bool)
    assert cutout.border_connected(empty).shape == (0, 0)


def test_auto_mode_removes_connected_background_only():
    result = cutout.remove_background(green_scene(), mode="auto")
    assert result.mode == "auto"
    assert result.image.mode == "RGBA"
    assert result.image.getpixel((0, 0))[3] == 0
    assert result.image.getpixel((20, 20))[3] == 255
    assert 0.0 < result.removed < 1.0
    assert "Sampled background" in result.note


def test_auto_mode_keeps_background_coloured_subject():
    image = green_scene()
    # A green gem in the middle of the red subject: same colour as the
    # background, but not reachable from the border.
    for y in range(18, 23):
        for x in range(18, 23):
            image.putpixel((x, y), (0, 255, 0, 255))
    result = cutout.remove_background(image, mode="auto")
    assert result.image.getpixel((20, 20))[3] == 255


def test_auto_mode_accepts_an_explicit_sample_colour():
    image = Image.new("RGBA", (20, 20), (10, 20, 200, 255))
    result = cutout.remove_background(image, mode="auto", color=(10, 20, 200))
    assert result.image.getpixel((0, 0))[3] == 0


def test_color_mode_keys_one_colour():
    image = green_scene()
    result = cutout.remove_background(image, mode="color", color="#00ff00",
                                      tolerance=40, softness=10)
    assert result.mode == "color"
    assert result.image.getpixel((0, 0))[3] == 0
    assert result.image.getpixel((20, 20))[3] == 255
    assert "Keyed" in result.note


def test_color_mode_accepts_rgb_tuple_and_unknown_mode_falls_back():
    image = green_scene()
    result = cutout.remove_background(image, mode="color",
                                      color=(0, 255, 0), softness=0)
    assert result.image.getpixel((0, 0))[3] == 0

    fallback = cutout.remove_background(green_scene(), mode="not-a-mode")
    assert fallback.mode == "auto"


def test_chroma_alpha_is_soft_and_inverted():
    image = Image.new("RGB", (3, 1))
    image.putpixel((0, 0), (0, 255, 0))
    image.putpixel((1, 0), (255, 255, 255))
    image.putpixel((2, 0), (0, 0, 0))
    alpha = cutout.chroma_alpha(image, (0, 255, 0), tolerance=10, softness=0)
    assert alpha[0, 0] == 0.0
    assert alpha[0, 1] == 1.0
    assert alpha[0, 2] == 1.0


def test_despill_reduces_a_green_fringe():
    image = Image.new("RGBA", (1, 1), (100, 200, 100, 255))
    alpha = np.zeros((1, 1), dtype=np.float32)
    out = cutout.despill(image, (0, 255, 0), alpha)
    red, green, blue, _ = out.getpixel((0, 0))
    assert green < 200
    assert red <= 100 and blue <= 100


def test_shape_alpha_feathers_and_shrinks():
    alpha = np.zeros((40, 40), dtype=np.float32)
    alpha[10:30, 10:30] = 1.0
    base = cutout.shape_alpha(alpha, feather=0, shrink=0)
    shrunk = cutout.shape_alpha(alpha, feather=0, shrink=2)
    grown = cutout.shape_alpha(alpha, feather=0, shrink=-2)
    base_count = np.count_nonzero(np.asarray(base) > 128)
    shrunk_count = np.count_nonzero(np.asarray(shrunk) > 128)
    grown_count = np.count_nonzero(np.asarray(grown) > 128)
    assert shrunk_count < base_count < grown_count

    soft = cutout.shape_alpha(alpha, feather=3.0, shrink=0)
    assert np.asarray(soft).min() < 255
    assert np.asarray(soft).max() == 255


def test_auto_trim_crops_transparent_borders():
    image = Image.new("RGBA", (30, 30), (0, 0, 0, 0))
    for y in range(10, 20):
        for x in range(10, 20):
            image.putpixel((x, y), (255, 0, 0, 255))
    assert cutout.auto_trim(image).size == (10, 10)
    assert cutout.auto_trim(image, padding=2).size == (14, 14)
    empty = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
    assert cutout.auto_trim(empty).size == (8, 8)


def test_ai_status_is_honest():
    assert isinstance(cutout.ai_available(), bool)
    status = cutout.ai_status()
    assert status
    if not cutout.ai_available():
        assert "rembg" in status.lower()


@pytest.mark.skipif(cutout.ai_available(), reason="rembg is installed")
def test_ai_engine_reports_missing_dependency():
    with pytest.raises(RuntimeError, match="rembg"):
        cutout.remove_background_ai(Image.new("RGBA", (4, 4)))
