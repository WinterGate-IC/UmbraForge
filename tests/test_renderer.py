"""Rendering, effects, hit testing and file export."""

from __future__ import annotations

import numpy as np
import pytest
from PySide6.QtGui import QImage

from umbraforge import imaging, renderer
from umbraforge.layers import (
    BLEND_MODES,
    PATTERNS,
    Design,
    IconLayer,
    ImageLayer,
    ShapeLayer,
    TextLayer,
    add_asset,
)


def alpha_map(image: QImage) -> np.ndarray:
    converted = image.convertToFormat(QImage.Format.Format_RGBA8888)
    width, height = converted.width(), converted.height()
    stride = converted.bytesPerLine()
    data = bytes(converted.constBits())
    rows = np.frombuffer(data, dtype=np.uint8).reshape(height, stride)
    return rows[:, : width * 4].reshape(height, width, 4)[..., 3]


def simple_design(width: int = 400, height: int = 300) -> Design:
    design = Design(name="Render test")
    design.set_size(width, height)
    design.background.update(kind="solid", color="#202030")
    design.add(ShapeLayer(name="Block", shape="square", x=0.2, y=0.2,
                          w=0.4, h=0.4, fill="#ff7a3d", gradient=False))
    return design


def test_render_design_uses_requested_size_and_background(qapp):
    image = renderer.render_design(simple_design(), 320, 240)
    assert not image.isNull()
    assert (image.width(), image.height()) == (320, 240)
    assert image.pixelColor(0, 0).alpha() == 255
    assert alpha_map(image).min() == 255


def test_render_design_can_be_transparent(qapp):
    image = renderer.render_design(simple_design(), 200, 150, background=False)
    alpha = alpha_map(image)
    assert alpha[0, 0] == 0
    assert alpha[150 // 2, 200 // 2] > 0
    assert alpha.max() > 0


def test_render_defaults_to_design_size(qapp):
    design = simple_design(130, 90)
    image = renderer.render_design(design)
    assert (image.width(), image.height()) == (130, 90)


def test_every_background_pattern_renders(qapp):
    design = simple_design(96, 96)
    for key, _label in PATTERNS:
        design.background.update(kind="solid", color="#111122", pattern=key,
                                 pattern_scale=0.5)
        image = renderer.render_design(design, 96, 96)
        assert image.width() == 96
    design.background.update(kind="transparent", pattern="none")
    image = renderer.render_design(design, 64, 64)
    assert alpha_map(image)[0, 0] == 0


def test_every_blend_mode_renders(qapp):
    design = simple_design(80, 80)
    layer = design.layers[0]
    layer.opacity = 0.7
    for key, _label in BLEND_MODES:
        layer.blend = key
        image = renderer.render_design(design, 80, 80)
        assert not image.isNull()
    layer.blend = "not-real"
    assert renderer.render_design(design, 40, 40).width() == 40


def test_text_renders_with_effects_and_stroke(qapp):
    design = Design(name="Type", width=300, height=200)
    design.background.update(kind="transparent")
    layer = TextLayer(name="Title", text="UMBRA\nFORGE", size=0.12,
                      weight=800, uppercase=True, letter_spacing=0.1,
                      stroke_color="#000000", stroke_width=0.02,
                      x=0.05, y=0.1, w=0.9, h=0.8)
    layer.effects["glow"]["enabled"] = True
    layer.effects["glow"]["size"] = 0.03
    layer.effects["shadow"]["enabled"] = True
    design.add(layer)
    image = renderer.render_design(design, 300, 200)
    assert alpha_map(image).max() > 0


def test_wrapped_text_and_alignment_variants_render(qapp):
    design = Design(name="Wrap", width=240, height=240)
    design.background.update(kind="transparent")
    text = ("A long caption that should wrap across several lines inside its "
            "layer box without disappearing.")
    for align, valign in (("left", "top"), ("center", "middle"),
                          ("right", "bottom")):
        layer = TextLayer(name=f"{align}-{valign}", text=text, size=0.05,
                          align=align, valign=valign, wrap=True,
                          x=0.1, y=0.1, w=0.8, h=0.8)
        design.layers = [layer]
        assert alpha_map(renderer.render_design(design, 240, 240)).max() > 0
    unwrapped = TextLayer(name="No wrap", text="ONE\nTWO", wrap=False)
    design.layers = [unwrapped]
    assert renderer.render_design(design, 120, 120).width() == 120


def test_image_layer_renders_with_mask_and_adjustments(qapp):
    from PIL import Image

    source = Image.new("RGBA", (48, 32), (40, 200, 90, 255))
    for x in range(48):
        for y in range(32):
            source.putpixel((x, y), (x * 5 % 255, y * 7 % 255, 120, 255))
    design = Design(name="Photo", width=200, height=200)
    design.background.update(kind="transparent")
    asset = add_asset(design.assets, imaging.encode_png(source), "photo.png",
                      "image/png", 48, 32)
    layer = ImageLayer(name="Photo", asset_id=asset, x=0.2, y=0.2,
                       w=0.6, h=0.6, fit="cover", mask="circle",
                       mask_feather=0.02)
    layer.adjustments.update(brightness=1.2, saturation=0.7)
    layer.effects["shadow"]["enabled"] = True
    design.add(layer)
    image = renderer.render_design(design, 200, 200)
    alpha = alpha_map(image)
    assert alpha[100, 100] > 0
    assert alpha[2, 2] == 0


def test_missing_image_asset_is_skipped(qapp):
    design = Design(width=80, height=80)
    design.add(ImageLayer(name="Ghost", asset_id="missing", w=0.5, h=0.5))
    image = renderer.render_design(design, 80, 80)
    assert not image.isNull()


def test_render_thumbnail_fits_the_long_edge(qapp):
    design = Design(width=3840, height=2160)
    image = renderer.render_thumbnail(design, 200)
    assert max(image.width(), image.height()) <= 200
    assert image.width() == 200
    assert abs(image.width() / image.height() - 16 / 9) < 0.02

    small = renderer.render_thumbnail(design, 8)
    assert small.width() >= 32


def test_render_pixmap(qapp):
    pixmap = renderer.render_pixmap(simple_design(64, 64), 32, 32)
    assert not pixmap.isNull()
    assert (pixmap.width(), pixmap.height()) == (32, 32)


@pytest.mark.parametrize("suffix", ["png", "jpg", "webp"])
def test_save_image(tmp_path, qapp, suffix):
    design = simple_design(240, 160)
    path = tmp_path / f"out.{suffix}"
    assert renderer.save_image(design, str(path), 120, 80, 88, True) is True
    assert path.exists() and path.stat().st_size > 100
    loaded = imaging.open_image(path)
    assert loaded.size == (120, 80)


def test_save_transparent_png_keeps_alpha(tmp_path, qapp):
    design = Design(width=100, height=100)
    design.background.update(kind="transparent")
    design.add(ShapeLayer(name="Dot", shape="circle", x=0.25, y=0.25,
                          w=0.5, h=0.5, fill="#ff0000", gradient=False))
    path = tmp_path / "alpha.png"
    assert renderer.save_image(design, str(path), 100, 100, background=False)
    loaded = imaging.open_image(path)
    assert loaded.getpixel((2, 2))[3] == 0
    assert loaded.getpixel((50, 50))[3] > 0


def test_save_image_with_unknown_suffix_writes_png(tmp_path, qapp):
    path = tmp_path / "out.weird"
    assert renderer.save_image(simple_design(40, 40), str(path), 40, 40)
    assert imaging.open_image(path).size == (40, 40)


def test_layer_at_returns_the_topmost_visible_layer(qapp):
    design = Design(width=1000, height=1000)
    lower = design.add(ShapeLayer(name="Lower", x=0.1, y=0.1, w=0.6, h=0.6))
    upper = design.add(ShapeLayer(name="Upper", x=0.2, y=0.2, w=0.2, h=0.2))
    assert renderer.layer_at(design, 250, 250, 1000, 1000) is upper
    assert renderer.layer_at(design, 150, 150, 1000, 1000) is lower
    assert renderer.layer_at(design, 950, 950, 1000, 1000) is None

    upper.visible = False
    assert renderer.layer_at(design, 250, 250, 1000, 1000) is lower


def test_layer_at_respects_rotation(qapp):
    design = Design(width=400, height=400)
    layer = design.add(ShapeLayer(name="Spin", x=0.2, y=0.4, w=0.6, h=0.1,
                                  rotation=90))
    # The long axis is vertical after rotating, so a point above the centre
    # is inside while the same offset horizontally is outside.
    assert renderer.layer_at(design, 200, 80, 400, 400) is layer
    assert renderer.layer_at(design, 100, 200, 400, 400) is None


def test_layer_corners_are_four_rotated_points(qapp):
    layer = ShapeLayer(x=0.2, y=0.2, w=0.4, h=0.2)
    corners = renderer.layer_corners(layer, 1000, 1000)
    assert len(corners) == 4
    assert corners[0].x() == pytest.approx(200)
    assert corners[0].y() == pytest.approx(200)

    layer.rotation = 30
    rotated = renderer.layer_corners(layer, 1000, 1000)
    assert rotated[0].y() != pytest.approx(200)


def test_clear_caches_does_not_break_rendering(qapp):
    design = simple_design(120, 120)
    first = renderer.render_design(design, 60, 60)
    renderer.clear_caches()
    second = renderer.render_design(design, 60, 60)
    assert first.size() == second.size()


def test_icon_layer_renders(qapp):
    design = Design(width=120, height=120)
    design.background.update(kind="transparent")
    design.add(IconLayer(name="Skull", icon="skull", x=0.2, y=0.2, w=0.6,
                         h=0.6, color="#ffffff"))
    assert alpha_map(renderer.render_design(design, 120, 120)).max() > 0
