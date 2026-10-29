"""Raster helpers: colour maths, adjustments, resizing and Qt bridges."""

from __future__ import annotations

import io

import numpy as np
import pytest
from PIL import Image

from umbraforge import imaging


# --------------------------------------------------------------------------
# colour
# --------------------------------------------------------------------------
def test_hex_to_rgb():
    assert imaging.hex_to_rgb("#ff7a3d") == (255, 122, 61)
    assert imaging.hex_to_rgb("ff7a3d") == (255, 122, 61)
    assert imaging.hex_to_rgb("#f80") == (255, 136, 0)
    assert imaging.hex_to_rgb("not-a-colour") == (255, 122, 61)
    assert imaging.hex_to_rgb("", (1, 2, 3)) == (1, 2, 3)
    assert imaging.hex_to_rgb("#zzzzzz", (9, 9, 9)) == (9, 9, 9)


def test_rgba_to_hex():
    assert imaging.rgba_to_hex(255, 0, 16) == "#ff0010"
    assert imaging.rgba_to_hex(0, 0, 0) == "#000000"


# --------------------------------------------------------------------------
# load and encode
# --------------------------------------------------------------------------
def test_open_image_converts_to_rgba(tmp_path):
    source = Image.new("RGB", (12, 9), (10, 20, 30))
    buffer = io.BytesIO()
    source.save(buffer, format="JPEG")
    image = imaging.open_image(buffer.getvalue())
    assert image.mode == "RGBA"
    assert image.size == (12, 9)

    path = tmp_path / "sample.png"
    source.save(path)
    assert imaging.open_image(path).mode == "RGBA"
    assert imaging.open_image(str(path)).size == (12, 9)


def test_encode_png_roundtrip():
    source = Image.new("RGBA", (5, 4), (1, 2, 3, 128))
    data = imaging.encode_png(source)
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    loaded = imaging.open_image(data)
    assert loaded.size == (5, 4)
    assert loaded.getpixel((0, 0)) == (1, 2, 3, 128)


# --------------------------------------------------------------------------
# adjustments
# --------------------------------------------------------------------------
def test_adjust_identity_keeps_pixels():
    source = Image.new("RGBA", (4, 4), (10, 20, 30, 255))
    out = imaging.adjust(source, {})
    assert out.size == source.size
    assert out.getpixel((0, 0)) == (10, 20, 30, 255)


def test_adjust_brightness():
    source = Image.new("RGBA", (2, 2), (100, 100, 100, 255))
    out = imaging.adjust(source, {"brightness": 0.5})
    assert out.getpixel((0, 0))[:3] == (50, 50, 50)


def test_adjust_vignette_darkens_corners_more_than_centre():
    source = Image.new("RGBA", (64, 64), (255, 255, 255, 255))
    out = imaging.adjust(source, {"vignette": 1.0})
    corner = out.getpixel((0, 0))[0]
    centre = out.getpixel((32, 32))[0]
    assert centre == 255
    assert corner < 80


def test_adjust_saturation_and_warmth_change_colour():
    source = Image.new("RGBA", (2, 2), (200, 100, 50, 255))
    grey = imaging.adjust(source, {"saturation": 0.0})
    r, g, b = grey.getpixel((0, 0))[:3]
    assert abs(r - g) < 3 and abs(g - b) < 3
    warm = imaging.adjust(source, {"warmth": 1.0})
    assert warm.getpixel((0, 0))[0] >= source.getpixel((0, 0))[0]


# --------------------------------------------------------------------------
# resizing
# --------------------------------------------------------------------------
def test_resize_fill_exact():
    source = Image.new("RGBA", (100, 50), (255, 0, 0, 255))
    out = imaging.resize_cover(source, 40, 20, "fill")
    assert out.size == (40, 20)


def test_resize_cover_crops_and_contain_pads():
    source = Image.new("RGBA", (100, 50), (255, 0, 0, 255))
    covered = imaging.resize_cover(source, 40, 40, "cover")
    assert covered.size == (40, 40)
    assert covered.getpixel((0, 0))[3] == 255

    contained = imaging.resize_cover(source, 40, 40, "contain")
    assert contained.size == (40, 40)
    assert contained.getpixel((20, 5))[3] == 0
    assert contained.getpixel((20, 20))[3] == 255


def test_resize_handles_zero_source_size():
    source = Image.new("RGBA", (10, 10), (1, 2, 3, 4))
    out = imaging.resize_cover(source, 8, 8, "cover")
    assert out.size == (8, 8)


# --------------------------------------------------------------------------
# masks and bridges
# --------------------------------------------------------------------------
def test_blur_alpha_skips_tiny_radii_and_smears_edges():
    source = Image.new("RGBA", (32, 32), (255, 255, 255, 255))
    assert imaging.blur_alpha(source, 0.0) is source

    source.putpixel((16, 16), (255, 255, 255, 0))
    blurred = imaging.blur_alpha(source, 3.0)
    assert blurred.getpixel((16, 16))[3] > 0
    assert blurred.getpixel((1, 1))[3] == 255


def test_tint_mask_sets_colour_and_opacity():
    mask = Image.new("L", (4, 4), 255)
    tinted = imaging.tint_mask(mask, (255, 0, 0), 0.5)
    assert tinted.mode == "RGBA"
    red, green, blue, alpha = tinted.getpixel((0, 0))
    assert (red, green, blue) == (255, 0, 0)
    assert alpha == pytest.approx(127, abs=2)


def test_pil_qimage_roundtrip(qapp):
    source = Image.new("RGBA", (9, 7))
    for y in range(7):
        for x in range(9):
            source.putpixel((x, y), (x * 20, y * 30, (x + y) * 10, 255 - x))
    qimage = imaging.pil_to_qimage(source)
    assert (qimage.width(), qimage.height()) == (9, 7)
    restored = imaging.qimage_to_pil(qimage)
    assert restored.size == source.size
    assert restored.tobytes() == source.tobytes()


def test_smoothstep_is_clamped_and_monotonic():
    values = np.array([-1.0, 0.0, 0.5, 1.0, 2.0], dtype=np.float32)
    out = imaging.smoothstep(0.0, 1.0, values)
    assert out[0] == 0.0
    assert out[1] == 0.0
    assert out[2] == pytest.approx(0.5)
    assert out[3] == 1.0
    assert out[4] == 1.0
    assert list(out) == sorted(out)
