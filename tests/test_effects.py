"""The effects library: catalogue integrity and raster behaviour."""

from __future__ import annotations

from PIL import Image, ImageDraw

from umbraforge import effects
from umbraforge.layers import ShapeLayer


def sample() -> Image.Image:
    image = Image.new("RGBA", (120, 120), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((25, 35, 95, 85), radius=14, fill=(255, 122, 61, 255))
    draw.ellipse((45, 45, 75, 75), fill=(245, 242, 255, 255))
    return image


def test_the_catalogue_is_large_unique_and_grouped():
    assert len(effects.PRESETS) >= 70
    keys = [preset.key for preset in effects.PRESETS]
    assert len(keys) == len(set(keys))
    assert len(effects.categories()) >= 5
    for preset in effects.PRESETS:
        assert preset.label and preset.note
        assert effects.get(preset.key) is preset
        stack = preset.apply()
        assert stack["preset"] == preset.key
        assert effects.any_enabled(stack)


def test_presets_filter_and_describe():
    assert effects.describe({}) == "No effects"
    preset = effects.PRESETS[0]
    assert effects.describe(preset.apply()) == preset.label
    retro = effects.entries("Retro")
    assert retro and all(item.category == "Retro" for item in retro)
    assert effects.entries(None, "glow")


def test_every_preset_renders_and_keeps_the_canvas_size():
    base = sample()
    for preset in effects.PRESETS:
        out = effects.apply_stack(base, preset.apply(), 900, 900)
        assert out.size == base.size, preset.key
        assert out.mode == "RGBA"
        assert out.getbbox() is not None, preset.key


def test_the_default_stack_is_a_no_op():
    base = sample()
    out = effects.apply_stack(base, effects.default_stack(), 900, 900)
    assert out.tobytes() == base.tobytes()


def test_effects_actually_change_pixels():
    base = sample()
    for key in ("glow_ember", "outline_white", "pixelate_mid", "duo_ember",
                "threshold_ink", "motion_diag", "halftone_news",
                "god_rays", "holo_chrome", "synthwave", "pencil"):
        out = effects.apply_stack(base, effects.stack_for(key), 900, 900)
        assert out.tobytes() != base.tobytes(), key


def test_the_new_primitives_render():
    base = sample()
    for name, params in (
        ("rays", {"count": 10, "opacity": 0.4}),
        ("gradient_map", {"color": "#ffffff", "color3": "#ff00ff",
                          "color2": "#000080"}),
        ("hue_shift", {"degrees": 120.0}),
        ("dither", {"size": 4.0}),
        ("edges", {}),
        ("zoom_blur", {"amount": 0.18}),
        ("tilt_shift", {"focus": 0.3}),
        ("swirl", {"angle": 2.0}),
        ("wave", {"amplitude": 0.03}),
        ("bulge", {"strength": 0.5}),
        ("kaleidoscope", {"sectors": 6}),
        ("sharpen", {"amount": 0.7}),
        ("charcoal", {"amount": 0.8}),
        ("comic", {"amount": 0.8}),
        ("solarize", {"level": 0.6}),
    ):
        stack = effects.default_stack()
        stack[name].update(params)
        stack[name]["enabled"] = True
        out = effects.apply_stack(base, stack, 900, 900)
        assert out.size == base.size
        assert out.tobytes() != base.tobytes(), name


def test_the_sketch_category_and_new_recipes_are_present():
    assert "Sketch" in effects.categories()
    keys = {preset.key for preset in effects.PRESETS}
    for key in ("zoom_punch", "tilt_miniature", "swirl_vortex",
                "wave_liquid", "bulge_lens", "kaleido_six",
                "charcoal_draw", "comic_ink", "solar_neon", "crisp_hard"):
        assert key in keys


def test_previews_render_for_every_recipe():
    for preset in effects.PRESETS:
        data = effects.preview_png(preset.key)
        assert data.startswith(b"\x89PNG"), preset.key
        assert data == effects.preview_png(preset.key)


def test_margin_grows_for_effects_that_spill_outside_the_layer():
    plain = effects.margin(effects.default_stack(), 900, 900)
    for key in ("glow_ember", "long_shadow", "outline_thick", "blur_heavy",
                "god_rays"):
        assert effects.margin(effects.stack_for(key), 900, 900) > plain, key


def test_outline_keeps_the_original_alpha_inside_the_shape():
    base = sample()
    out = effects.apply_stack(base, effects.stack_for("outline_white"), 900, 900)
    inside = (60, 60)
    assert out.getpixel(inside)[3] == 255
    assert out.getpixel((40, 40))[3] == 255  # border grew into the gap
    assert out.getpixel((1, 1))[3] == 0


def test_a_saved_stack_merges_against_new_defaults():
    layer = ShapeLayer.from_dict({
        "kind": "shape", "id": "abc",
        "effects": {"glow": {"enabled": True, "color": "#00ffcc"}},
    })
    assert layer.effects["glow"]["color"] == "#00ffcc"
    assert layer.effects["glow"]["enabled"] is True
    assert layer.effects["outline"]["enabled"] is False
    assert layer.effects["preset"] == ""
    assert effects.any_enabled(layer.effects)


def test_preset_keys_survive_serialization():
    layer = ShapeLayer()
    layer.effects = effects.stack_for("risograph")
    restored = ShapeLayer.from_dict(layer.to_dict())
    assert restored.effects["preset"] == "risograph"
    assert effects.enabled(restored.effects, "duotone")
    assert effects.enabled(restored.effects, "shadow")
