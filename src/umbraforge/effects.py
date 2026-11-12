"""The effects library: non-destructive layer finishes.

Every effect is a plain dict inside ``Layer.effects`` so it serializes with the
project and old files keep loading. The renderer asks this module for the
composed result, which means the canvas, thumbnails and exports all share one
implementation.

Effects are grouped into three stages:

* **behind** - shadow, long shadow, outer glow, outline: pixels added around
  the layer;
* **content** - blur, pixelate, posterize, duotone, halftone, chroma split and
  friends: pixels changed inside the layer;
* **finish** - bloom, inner glow, scanlines, grain, vignette: pixels laid over
  the layer.

The presets are curated recipes over those primitives. They are what the
Build > Effects shelf shows, and what the inspector's style picker applies.
"""

from __future__ import annotations

import copy
import math
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageOps

from . import imaging

# --------------------------------------------------------------------------
# effect primitives and their defaults
# --------------------------------------------------------------------------
#: Every effect key the renderer understands. ``preset`` records which recipe
#: a layer came from so the UI can show it; it is not an effect itself.
EFFECT_DEFAULTS: dict[str, dict] = {
    "rays": {
        "enabled": False, "color": "#ffb347", "opacity": 0.35,
        "count": 12, "angle": 0.0, "length": 0.9,
    },
    "shadow": {
        "enabled": False, "color": "#000000", "opacity": 0.55,
        "blur": 0.018, "dx": 0.004, "dy": 0.006,
    },
    "long_shadow": {
        "enabled": False, "color": "#000000", "opacity": 0.5,
        "angle": 45.0, "distance": 0.18, "steps": 18,
    },
    "glow": {
        "enabled": False, "color": "#ff7a3d", "opacity": 0.55,
        "size": 0.022,
    },
    "bloom": {
        "enabled": False, "color": "#ffd9a8", "opacity": 0.5,
        "size": 0.03,
    },
    "outline": {
        "enabled": False, "color": "#08080c", "width": 0.012,
    },
    "inner_glow": {
        "enabled": False, "color": "#ffc07a", "opacity": 0.5,
        "size": 0.02,
    },
    "blur": {"enabled": False, "radius": 0.006},
    "motion_blur": {"enabled": False, "radius": 0.012, "angle": 0.0},
    "pixelate": {"enabled": False, "size": 0.012},
    "posterize": {"enabled": False, "levels": 4},
    "duotone": {"enabled": False, "color": "#ff9a5c", "color2": "#140b24"},
    "gradient_map": {
        "enabled": False, "color": "#f4fbff",
        "color2": "#160a20", "color3": "#7c3aed",
    },
    "hue_shift": {"enabled": False, "degrees": 0.0},
    "dither": {
        "enabled": False, "size": 0.004,
        "ink": "#0b0813", "paper": "#f6e7d6",
    },
    "halftone": {
        "enabled": False, "size": 0.014,
        "ink": "#0b0813", "paper": "#f6e7d6",
    },
    "emboss": {"enabled": False, "amount": 0.45},
    "edges": {
        "enabled": False, "color": "#2b2b33",
        "background": "#f7f3ea", "amount": 0.9,
    },
    "threshold": {"enabled": False, "level": 0.5},
    "invert": {"enabled": False},
    "saturate": {"enabled": False, "amount": 1.5},
    "contrast": {"enabled": False, "amount": 1.25},
    "chromatic": {"enabled": False, "offset": 0.004},
    "glitch": {"enabled": False, "amount": 0.12},
    "scanlines": {"enabled": False, "spacing": 0.004, "opacity": 0.28},
    "grain": {"enabled": False, "amount": 0.14},
    "vignette": {"enabled": False, "amount": 0.55},
}

#: Stable application order. Each stage reads top to bottom.
_CONTENT_ORDER = (
    "blur", "motion_blur", "pixelate", "edges", "posterize", "duotone",
    "threshold", "dither", "gradient_map", "invert", "saturate", "contrast",
    "emboss", "halftone", "hue_shift", "chromatic",
)


def default_stack() -> dict:
    stack = copy.deepcopy(EFFECT_DEFAULTS)
    stack["preset"] = ""
    return stack


def enabled(settings: dict | None, name: str) -> bool:
    entry = (settings or {}).get(name) or {}
    return bool(entry.get("enabled"))


def any_enabled(settings: dict | None) -> bool:
    return any(enabled(settings, key) for key in EFFECT_DEFAULTS)


def _number(entry: dict, key: str, default: float) -> float:
    try:
        return float(entry.get(key, default))
    except (TypeError, ValueError):
        return float(default)


# --------------------------------------------------------------------------
# presets
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Preset:
    key: str
    label: str
    category: str
    note: str
    stack: dict

    def apply(self) -> dict:
        stack = default_stack()
        stack["preset"] = self.key
        for name, params in self.stack.items():
            entry = stack.setdefault(name, {})
            entry.update(params)
            entry["enabled"] = True
        return stack


def _recipe(key: str, label: str, category: str, note: str,
            **effects) -> Preset:
    return Preset(key, label, category, note, effects)


PRESETS: tuple[Preset, ...] = (
    # ---------------------------------------------------------------- light
    _recipe("glow_ember", "Ember glow", "Light",
            "Warm halo that lifts a mark off the canvas.",
            glow={"color": "#ff7a3d", "size": 0.028, "opacity": 0.75}),
    _recipe("glow_ice", "Ice halo", "Light",
            "Cool cyan glow for glassy, technical marks.",
            glow={"color": "#7ad9ff", "size": 0.026, "opacity": 0.7}),
    _recipe("glow_violet", "Violet aura", "Light",
            "Soft purple aura with a wide falloff.",
            glow={"color": "#a678ff", "size": 0.04, "opacity": 0.55}),
    _recipe("bloom_soft", "Soft bloom", "Light",
            "Gentle light bleed, like a bright lens.",
            bloom={"color": "#ffe9cf", "opacity": 0.4, "size": 0.022}),
    _recipe("bloom_dream", "Dream bloom", "Light",
            "Heavier bloom with a faint halo.",
            bloom={"color": "#ffd9f0", "opacity": 0.65, "size": 0.045},
            glow={"color": "#ff9ad5", "size": 0.02, "opacity": 0.4}),
    _recipe("neon_edge", "Neon edge", "Light",
            "Hot outline plus matching glow. Very arcade.",
            outline={"color": "#ff4fd8", "width": 0.006},
            glow={"color": "#ff4fd8", "size": 0.03, "opacity": 0.85}),
    _recipe("backlight", "Backlight", "Light",
            "Wide low glow that reads as a light source behind.",
            glow={"color": "#ffb46b", "size": 0.06, "opacity": 0.4}),
    _recipe("sun_flare", "Sun flare", "Light",
            "Warm bloom with a gold rim.",
            bloom={"color": "#ffcf7a", "opacity": 0.6, "size": 0.035},
            glow={"color": "#ffb347", "size": 0.018, "opacity": 0.55}),
    _recipe("inner_light", "Inner light", "Light",
            "Light seeps inside the layer edges.",
            inner_glow={"color": "#fff1c9", "opacity": 0.65, "size": 0.028}),
    _recipe("god_rays", "God rays", "Light",
            "Soft golden shafts fanning out behind the mark.",
            rays={"color": "#ffcf7a", "count": 14, "angle": -20.0,
                  "length": 0.9, "opacity": 0.3},
            bloom={"color": "#ffe2a8", "opacity": 0.35, "size": 0.028}),

    # --------------------------------------------------------------- shadow
    _recipe("shadow_soft", "Soft drop", "Shadow",
            "Everyday drop shadow with a gentle blur.",
            shadow={"blur": 0.03, "opacity": 0.5, "dy": 0.012}),
    _recipe("shadow_hard", "Hard drop", "Shadow",
            "Tight, crisp shadow for stickers and badges.",
            shadow={"blur": 0.002, "opacity": 0.65, "dx": 0.005, "dy": 0.012}),
    _recipe("shadow_lift", "Floating", "Shadow",
            "Large soft shadow that suggests height.",
            shadow={"blur": 0.05, "opacity": 0.42, "dy": 0.024}),
    _recipe("shadow_deep", "Deep cast", "Shadow",
            "Dark, heavy shadow for dramatic posters.",
            shadow={"blur": 0.02, "opacity": 0.8, "dx": 0.012, "dy": 0.02}),
    _recipe("long_shadow", "Long shadow", "Shadow",
            "Classic 45-degree cast shadow.",
            long_shadow={"angle": 45.0, "distance": 0.2, "opacity": 0.5}),
    _recipe("long_shadow_high", "High cast", "Shadow",
            "Long shadow thrown to the upper right.",
            long_shadow={"angle": -45.0, "distance": 0.18, "opacity": 0.45}),
    _recipe("retro_offset", "Retro offset", "Shadow",
            "Short, hard offset like a seventies print.",
            long_shadow={"angle": 45.0, "distance": 0.07, "steps": 6,
                         "opacity": 0.7}),
    _recipe("underline", "Underline", "Shadow",
            "Offset copy straight down, no blur.",
            shadow={"blur": 0.0, "opacity": 0.7, "dx": 0.0, "dy": 0.016}),

    # -------------------------------------------------------------- outline
    _recipe("outline_white", "White sticker", "Outline",
            "White border with a soft shadow. Instant sticker.",
            outline={"color": "#ffffff", "width": 0.014},
            shadow={"blur": 0.02, "opacity": 0.45, "dy": 0.012}),
    _recipe("outline_black", "Black ink", "Outline",
            "Heavy black keyline for bold marks.",
            outline={"color": "#08080c", "width": 0.012}),
    _recipe("outline_accent", "Accent edge", "Outline",
            "Thin ember keyline with a matching glow.",
            outline={"color": "#ff7a3d", "width": 0.008},
            glow={"color": "#ff7a3d", "size": 0.014, "opacity": 0.5}),
    _recipe("outline_thick", "Thick border", "Outline",
            "Wide border for small icons and thumbnails.",
            outline={"color": "#f3f1f8", "width": 0.024}),
    _recipe("outline_hairline", "Hairline", "Outline",
            "A single-pixel-feeling rim.",
            outline={"color": "#ffffff", "width": 0.004}),
    _recipe("sticker_bold", "Bold sticker", "Outline",
            "Fat white cut line, hard shadow.",
            outline={"color": "#ffffff", "width": 0.02},
            shadow={"blur": 0.004, "opacity": 0.6, "dx": 0.006, "dy": 0.01}),
    _recipe("chrome_edge", "Chrome edge", "Outline",
            "White rim plus embossed relief.",
            outline={"color": "#e8f4ff", "width": 0.006},
            emboss={"amount": 0.5}),

    # --------------------------------------------------------------- colour
    _recipe("duo_ember", "Ember duotone", "Colour",
            "Orange highlights on deep plum shadows.",
            duotone={"color": "#ff9a5c", "color2": "#160a20"}),
    _recipe("duo_ice", "Ice duotone", "Colour",
            "Cyan highlights on navy shadows.",
            duotone={"color": "#9be9ff", "color2": "#081426"}),
    _recipe("duo_forest", "Forest duotone", "Colour",
            "Mossy green over near-black.",
            duotone={"color": "#b6e08a", "color2": "#0a1408"}),
    _recipe("duo_rose", "Rose duotone", "Colour",
            "Dusty rose and oxblood.",
            duotone={"color": "#ffb3c7", "color2": "#2a0a16"}),
    _recipe("mono_punch", "Mono punch", "Colour",
            "Black and white with a hard contrast kick.",
            saturate={"amount": 0.0}, contrast={"amount": 1.45}),
    _recipe("sepia_print", "Sepia print", "Colour",
            "Old photograph sepia with a hint of grain.",
            duotone={"color": "#f0d6a8", "color2": "#2a1a10"},
            grain={"amount": 0.1}),
    _recipe("invert_pop", "Invert pop", "Colour",
            "Negative colours, full alpha.",
            invert={}, saturate={"amount": 1.2}),
    _recipe("poster_print", "Poster print", "Colour",
            "Flat four-tone screen print.",
            posterize={"levels": 4}, contrast={"amount": 1.2}),
    _recipe("threshold_ink", "Threshold ink", "Colour",
            "Pure two-tone black and white.",
            threshold={"level": 0.46}),
    _recipe("high_contrast", "High contrast", "Colour",
            "Punchy, glossy contrast boost.",
            contrast={"amount": 1.6}, saturate={"amount": 1.15}),
    _recipe("matte_fade", "Matte fade", "Colour",
            "Lifted blacks and softer colour.",
            contrast={"amount": 0.82}, saturate={"amount": 0.78},
            grain={"amount": 0.08}),
    _recipe("holo_chrome", "Holo chrome", "Colour",
            "Iridescent cyan-to-pink chrome with a light bleed.",
            gradient_map={"color": "#eafcff", "color3": "#6ee7ff",
                          "color2": "#3b0a5c"},
            bloom={"color": "#a78bfa", "opacity": 0.45, "size": 0.03},
            chromatic={"offset": 0.003}),
    _recipe("vaporwave", "Vaporwave", "Colour",
            "Pink highlights, teal shadows and a faint screen.",
            gradient_map={"color": "#ffd6f6", "color3": "#ff6ad5",
                          "color2": "#120a3a"},
            scanlines={"spacing": 0.004, "opacity": 0.2},
            chromatic={"offset": 0.004}),
    _recipe("thermal", "Thermal", "Colour",
            "Heat-camera palette: cold blue to white-hot.",
            gradient_map={"color": "#fff6d8", "color3": "#ff5a1f",
                          "color2": "#08207a"},
            contrast={"amount": 1.3}),
    _recipe("gold_leaf", "Gold leaf", "Colour",
            "Gilded highlights with a pressed-metal relief.",
            gradient_map={"color": "#fff3c4", "color3": "#f0b429",
                          "color2": "#3d2408"},
            emboss={"amount": 0.4}, grain={"amount": 0.08}),
    _recipe("blueprint", "Blueprint", "Colour",
            "Cyanotype lines on drafting blue.",
            gradient_map={"color": "#f2fbff", "color3": "#7ec8ff",
                          "color2": "#062a52"},
            scanlines={"spacing": 0.006, "opacity": 0.18}),
    _recipe("acid_shift", "Acid shift", "Colour",
            "Hue-rotated, over-saturated colour burn.",
            hue_shift={"degrees": 145.0}, saturate={"amount": 1.8},
            contrast={"amount": 1.15}),
    _recipe("hologram", "Hologram", "Colour",
            "Ghostly teal projection with a violet bloom.",
            gradient_map={"color": "#eafffb", "color3": "#5ff2d0",
                          "color2": "#0a2f3a"},
            bloom={"color": "#8b5cf6", "opacity": 0.35, "size": 0.025},
            chromatic={"offset": 0.005}),

    # -------------------------------------------------------------- texture
    _recipe("grain_film", "Film grain", "Texture",
            "Fine analogue grain.",
            grain={"amount": 0.14}),
    _recipe("grain_heavy", "Heavy grain", "Texture",
            "Coarse, pushed-film noise.",
            grain={"amount": 0.34}, contrast={"amount": 1.1}),
    _recipe("scan_crt", "CRT scanlines", "Texture",
            "Soft horizontal lines over the layer.",
            scanlines={"spacing": 0.004, "opacity": 0.3}),
    _recipe("scan_fine", "Fine scanlines", "Texture",
            "Very tight lines. Best on large layers.",
            scanlines={"spacing": 0.002, "opacity": 0.22}),
    _recipe("halftone_news", "Newsprint", "Texture",
            "Classic halftone dots in ink and paper.",
            halftone={"size": 0.014, "ink": "#141018", "paper": "#f4ead8"}),
    _recipe("halftone_poster", "Halftone poster", "Texture",
            "Big dots with flat colour.",
            halftone={"size": 0.026, "ink": "#1a0f22", "paper": "#ffd9b8"},
            posterize={"levels": 6}),
    _recipe("paper", "Paper", "Texture",
            "Warm paper tone with light grain.",
            duotone={"color": "#f4e6cf", "color2": "#6b5a44"},
            grain={"amount": 0.12}, contrast={"amount": 0.92}),
    _recipe("relief", "Relief", "Texture",
            "Embossed, carved look.",
            emboss={"amount": 0.6}),
    _recipe("stucco", "Stucco", "Texture",
            "Grain plus emboss for a rough surface.",
            grain={"amount": 0.22}, emboss={"amount": 0.35}),
    _recipe("dither_bit", "1-bit dither", "Texture",
            "Ordered black-and-white dithering.",
            dither={"size": 0.005, "ink": "#08080c", "paper": "#f6e7d6"}),
    _recipe("riso_dither", "Riso dither", "Texture",
            "Coarse two-ink dither with a printed feel.",
            dither={"size": 0.007, "ink": "#16324f", "paper": "#ffd9b0"},
            grain={"amount": 0.08}),
    _recipe("pencil", "Pencil sketch", "Texture",
            "Edge-detected line work on textured paper.",
            edges={"color": "#2b2b33", "background": "#f7f3ea", "amount": 1.0},
            grain={"amount": 0.12}),
    _recipe("watercolour", "Watercolour", "Texture",
            "Soft washes, pastel colour and paper grain.",
            blur={"radius": 0.005},
            gradient_map={"color": "#e0f2fe", "color3": "#fca5a5",
                          "color2": "#1e1b4b"},
            grain={"amount": 0.1}, contrast={"amount": 0.9}),

    # ----------------------------------------------------------- distortion
    _recipe("blur_soft", "Soft focus", "Distortion",
            "Slight defocus, edges stay soft.",
            blur={"radius": 0.004}),
    _recipe("blur_heavy", "Out of focus", "Distortion",
            "Heavy defocus for backgrounds.",
            blur={"radius": 0.014}),
    _recipe("motion_side", "Motion blur", "Distortion",
            "Sideways movement smear.",
            motion_blur={"radius": 0.014, "angle": 0.0}),
    _recipe("motion_diag", "Diagonal motion", "Distortion",
            "Fast diagonal pan.",
            motion_blur={"radius": 0.018, "angle": -35.0}),
    _recipe("pixelate_mid", "Pixelate", "Distortion",
            "Readable pixel chunks.",
            pixelate={"size": 0.012}),
    _recipe("pixelate_big", "Chunky pixels", "Distortion",
            "Big blocks, almost mosaic.",
            pixelate={"size": 0.03}),
    _recipe("chromatic_soft", "Chromatic split", "Distortion",
            "Subtle lens fringing.",
            chromatic={"offset": 0.003}),
    _recipe("chromatic_hard", "RGB split", "Distortion",
            "Loud channel separation.",
            chromatic={"offset": 0.012}),
    _recipe("glitch_light", "Glitch flicker", "Distortion",
            "A few displaced scanlines.",
            glitch={"amount": 0.08}),
    _recipe("glitch_heavy", "Heavy glitch", "Distortion",
            "Broken signal, strong slices.",
            glitch={"amount": 0.22}, chromatic={"offset": 0.008}),
    _recipe("glass", "Frosted glass", "Distortion",
            "Defocused body with a bright inner rim.",
            blur={"radius": 0.003},
            inner_glow={"color": "#dff6ff", "opacity": 0.5, "size": 0.02},
            bloom={"color": "#bfe9ff", "opacity": 0.3, "size": 0.02},
            chromatic={"offset": 0.003}),

    # ---------------------------------------------------------------- retro
    _recipe("crt", "CRT", "Retro",
            "Scanlines, bloom and a warm cast.",
            scanlines={"spacing": 0.004, "opacity": 0.32},
            bloom={"color": "#c8ffd9", "opacity": 0.35, "size": 0.02},
            chromatic={"offset": 0.002}),
    _recipe("vhs", "VHS", "Retro",
            "Tape wobble: grain, chroma and lines.",
            chromatic={"offset": 0.006}, scanlines={"spacing": 0.003,
                                                    "opacity": 0.3},
            grain={"amount": 0.18}, blur={"radius": 0.002}),
    _recipe("arcade", "Arcade", "Retro",
            "Posterised glow with a screen grid.",
            posterize={"levels": 5}, glow={"color": "#59f7ff", "size": 0.02,
                                           "opacity": 0.5},
            scanlines={"spacing": 0.005, "opacity": 0.25}),
    _recipe("risograph", "Risograph", "Retro",
            "Two-ink print with grain and a slight offset.",
            duotone={"color": "#ff7a3d", "color2": "#1b2a5c"},
            grain={"amount": 0.16},
            shadow={"blur": 0.0, "opacity": 0.5, "dx": 0.003, "dy": 0.004}),
    _recipe("photocopy", "Photocopy", "Retro",
            "Hard threshold with copier speckle.",
            threshold={"level": 0.42}, grain={"amount": 0.2}),
    _recipe("neon_night", "Neon night", "Retro",
            "Glowing rim with a chroma fringe.",
            glow={"color": "#ff4fd8", "size": 0.03, "opacity": 0.8},
            outline={"color": "#b9f6ff", "width": 0.006},
            chromatic={"offset": 0.004}),
    _recipe("gameboy", "Game Boy", "Retro",
            "Four-shade green dither, straight off the handheld.",
            dither={"size": 0.006, "ink": "#0f380f", "paper": "#9bbc0f"},
            gradient_map={"color": "#cadc9f", "color3": "#8bac0f",
                          "color2": "#0f380f"},
            scanlines={"spacing": 0.005, "opacity": 0.2}),
    _recipe("synthwave", "Synthwave", "Retro",
            "Hot pink rays, deep purple and a chrome sheen.",
            rays={"color": "#ff4fd8", "count": 16, "angle": 90.0,
                  "length": 1.0, "opacity": 0.28},
            gradient_map={"color": "#ffe4fb", "color3": "#ff4fd8",
                          "color2": "#12002e"},
            scanlines={"spacing": 0.004, "opacity": 0.22},
            chromatic={"offset": 0.004}),
    _recipe("terminal", "Terminal", "Retro",
            "Green-screen dither with scanlines.",
            dither={"size": 0.004, "ink": "#052e16", "paper": "#86efac"},
            gradient_map={"color": "#d9f99d", "color3": "#4ade80",
                          "color2": "#052e16"},
            scanlines={"spacing": 0.004, "opacity": 0.24}),
)

PRESETS_BY_KEY = {preset.key: preset for preset in PRESETS}


def categories() -> list[str]:
    seen: list[str] = []
    for preset in PRESETS:
        if preset.category not in seen:
            seen.append(preset.category)
    return seen


def entries(category: str | None = None, needle: str = "") -> list[Preset]:
    needle = (needle or "").strip().casefold()
    found = []
    for preset in PRESETS:
        if category and preset.category != category:
            continue
        if needle and needle not in f"{preset.label} {preset.note} " \
                f"{preset.category}".casefold():
            continue
        found.append(preset)
    return found


def get(key: str) -> Preset | None:
    return PRESETS_BY_KEY.get(key)


def stack_for(key: str) -> dict:
    preset = PRESETS_BY_KEY.get(key)
    if preset is None:
        return default_stack()
    return preset.apply()


def active_names(settings: dict | None) -> list[str]:
    """Enabled primitives, in stack order, as display names."""
    return [name.replace("_", " ").title() for name in EFFECT_DEFAULTS
            if enabled(settings, name)]


def describe(settings: dict | None) -> str:
    """Human-readable summary used by the inspector."""
    settings = settings or {}
    key = str(settings.get("preset") or "")
    preset = PRESETS_BY_KEY.get(key)
    if preset is not None:
        return preset.label
    active = active_names(settings)
    return ", ".join(active) if active else "No effects"


#: PNG bytes keyed by preset, so the shelf redraws without re-rendering.
_PREVIEW_CACHE: dict[tuple[str, int, int], bytes] = {}


def preview_png(key: str, width: int = 156, height: int = 100) -> bytes:
    """A small rendered sample of a recipe, for the Build > Effects shelf."""
    cache_key = (key, width, height)
    cached = _PREVIEW_CACHE.get(cache_key)
    if cached is not None:
        return cached

    base = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(base)
    pad_x = round(width * 0.2)
    pad_y = round(height * 0.24)
    draw.rounded_rectangle(
        (pad_x, pad_y, width - pad_x, height - pad_y),
        radius=min(width, height) * 0.16,
        fill=(255, 122, 61, 255))
    draw.ellipse(
        (width * 0.34, height * 0.33, width * 0.66, height * 0.67),
        fill=(245, 242, 255, 255))
    sample = apply_stack(base, stack_for(key), width, height)
    data = imaging.encode_png(sample)
    _PREVIEW_CACHE[cache_key] = data
    return data


# --------------------------------------------------------------------------
# geometry: how much padding an effect stack needs
# --------------------------------------------------------------------------
def margin(settings: dict | None, width: int, height: int) -> float:
    settings = settings or {}
    shortest = max(1.0, float(min(width, height)))
    margin = 2.0
    if enabled(settings, "shadow"):
        entry = settings["shadow"]
        blur = max(0.0, _number(entry, "blur", 0.018)) * shortest
        margin = max(margin, blur * 2.4 + max(
            abs(_number(entry, "dx", 0.0)) * width,
            abs(_number(entry, "dy", 0.0)) * height))
    if enabled(settings, "rays"):
        margin = max(margin, _number(settings["rays"], "length", 0.9)
                     * shortest * 0.35)
    if enabled(settings, "long_shadow"):
        entry = settings["long_shadow"]
        margin = max(margin, _number(entry, "distance", 0.18) * shortest * 1.15)
    if enabled(settings, "glow"):
        margin = max(margin,
                     _number(settings["glow"], "size", 0.022) * shortest * 2.6)
    if enabled(settings, "outline"):
        margin = max(margin,
                     _number(settings["outline"], "width", 0.012) * shortest * 1.8)
    if enabled(settings, "blur"):
        margin = max(margin,
                     _number(settings["blur"], "radius", 0.006) * shortest * 2.4)
    if enabled(settings, "motion_blur"):
        margin = max(margin, _number(settings["motion_blur"], "radius",
                                     0.012) * shortest * 1.4)
    if enabled(settings, "chromatic"):
        margin = max(margin, _number(settings["chromatic"], "offset",
                                     0.004) * shortest * 2.0 + 2.0)
    if enabled(settings, "glitch"):
        margin = max(margin, shortest * 0.02 + 2.0)
    return math.ceil(margin) + 2


# --------------------------------------------------------------------------
# raster helpers
# --------------------------------------------------------------------------
def _alpha(image: Image.Image) -> Image.Image:
    return image.getchannel("A")


def _tint(alpha: Image.Image, color: str, opacity: float) -> Image.Image:
    return imaging.tint_mask(alpha, imaging.hex_to_rgb(color), opacity)


def _attach(alpha_source: Image.Image, rgb: Image.Image) -> Image.Image:
    out = rgb.convert("RGBA")
    out.putalpha(_alpha(alpha_source))
    return out


def _offset_paste(image: Image.Image, dx: float, dy: float) -> Image.Image:
    shifted = Image.new("RGBA", image.size, (0, 0, 0, 0))
    shifted.paste(image, (int(round(dx)), int(round(dy))))
    return shifted


def _grow(alpha: Image.Image, radius: float) -> Image.Image:
    """Approximate a circular dilation of the alpha channel."""
    if radius < 0.75:
        return alpha
    blurred = alpha.filter(ImageFilter.GaussianBlur(radius * 0.62))
    grown = blurred.point(lambda value: 255 if value >= 28 else 0)
    if radius >= 1.5:
        grown = grown.filter(ImageFilter.GaussianBlur(0.6))
    return grown


def _luma_array(rgb: np.ndarray) -> np.ndarray:
    return (rgb[..., 0] * 0.2126 + rgb[..., 1] * 0.7152 + rgb[..., 2] * 0.0722)


def _blur_content(content: Image.Image, radius: float) -> Image.Image:
    if radius < 0.2:
        return content
    return content.filter(ImageFilter.GaussianBlur(radius))


def _motion(content: Image.Image, radius: float, angle: float) -> Image.Image:
    steps = 9
    if radius < 0.5:
        return content
    radians = math.radians(angle)
    step_x = math.cos(radians) * radius / steps
    step_y = math.sin(radians) * radius / steps
    acc = content.copy()
    for index in range(1, steps + 1):
        shifted = _offset_paste(content, step_x * index, step_y * index)
        acc = Image.blend(acc, shifted, 1.0 / (index + 1))
    return acc


def _pixelate(content: Image.Image, size: float) -> Image.Image:
    width, height = content.size
    factor = max(2, int(round(size)))
    small = content.resize((max(1, width // factor), max(1, height // factor)),
                           Image.Resampling.BILINEAR)
    return small.resize((width, height), Image.Resampling.NEAREST)


def _duotone(content: Image.Image, color: str, color2: str) -> Image.Image:
    array = np.asarray(content.convert("RGB"), dtype=np.float32) / 255.0
    light = _luma_array(array)[..., None]
    dark = np.array(imaging.hex_to_rgb(color2), dtype=np.float32) / 255.0
    bright = np.array(imaging.hex_to_rgb(color), dtype=np.float32) / 255.0
    mixed = dark + (bright - dark) * light
    return _attach(content, Image.fromarray(
        (np.clip(mixed, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8), "RGB"))


def _threshold(content: Image.Image, level: float) -> Image.Image:
    array = np.asarray(content.convert("L"), dtype=np.float32) / 255.0
    cut = np.where(array >= level, 255, 0).astype(np.uint8)
    return _attach(content, Image.fromarray(cut, "L").convert("RGB"))


def _halftone(content: Image.Image, cell: float, ink: str,
              paper: str) -> Image.Image:
    width, height = content.size
    cell = max(3.0, float(cell))
    rgb = np.asarray(content.convert("RGB"), dtype=np.float32) / 255.0
    light = _luma_array(rgb)
    ink_rgb = np.array(imaging.hex_to_rgb(ink), dtype=np.float32) / 255.0
    paper_rgb = np.array(imaging.hex_to_rgb(paper), dtype=np.float32) / 255.0
    # Work in horizontal bands so a 4K export does not need a full-canvas
    # meshgrid per channel.
    band_rows = max(1, min(height, 1_000_000 // max(1, width)))
    xs = np.arange(width, dtype=np.float32)[None, :]
    fx = (xs % cell) / cell - 0.5
    out = np.empty((height, width, 3), dtype=np.float32)
    for top in range(0, height, band_rows):
        bottom = min(height, top + band_rows)
        ys = np.arange(top, bottom, dtype=np.float32)[:, None]
        fy = (ys % cell) / cell - 0.5
        distance = np.sqrt(fx * fx + fy * fy) / 0.7071
        radius = (1.0 - light[top:bottom]) * 0.86
        dots = distance <= radius
        out[top:bottom] = np.where(dots[..., None], ink_rgb, paper_rgb)
    return _attach(content, Image.fromarray(
        (np.clip(out, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8), "RGB"))


def _hue_shift(content: Image.Image, degrees: float) -> Image.Image:
    shift = int(round(degrees / 360.0 * 256.0)) % 256
    if shift == 0:
        return content
    hue, saturation, value = content.convert("RGB").convert("HSV").split()
    hue = hue.point(lambda level: (level + shift) % 256)
    return _attach(content, Image.merge(
        "HSV", (hue, saturation, value)).convert("RGB"))


def _gradient_map(content: Image.Image, shadow: str, mid: str,
                  light: str) -> Image.Image:
    array = np.asarray(content.convert("RGB"), dtype=np.float32) / 255.0
    luma = _luma_array(array)[..., None]
    dark = np.array(imaging.hex_to_rgb(shadow), dtype=np.float32) / 255.0
    middle = np.array(imaging.hex_to_rgb(mid), dtype=np.float32) / 255.0
    bright = np.array(imaging.hex_to_rgb(light), dtype=np.float32) / 255.0
    low = np.clip(luma * 2.0, 0.0, 1.0)
    high = np.clip((luma - 0.5) * 2.0, 0.0, 1.0)
    mixed = np.where(luma < 0.5,
                     dark + (middle - dark) * low,
                     middle + (bright - middle) * high)
    return _attach(content, Image.fromarray(
        (np.clip(mixed, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8), "RGB"))


#: Ordered 4x4 Bayer matrix, centred so a mid-grey gives even coverage.
_BAYER4 = (np.array([
    [0, 8, 2, 10],
    [12, 4, 14, 6],
    [3, 11, 1, 9],
    [15, 7, 13, 5],
], dtype=np.float32) + 0.5) / 16.0


def _dither(content: Image.Image, size: float, ink: str,
            paper: str) -> Image.Image:
    width, height = content.size
    block = max(1, int(round(size)))
    small_width = max(1, width // block)
    small_height = max(1, height // block)
    light = np.asarray(
        content.convert("L").resize((small_width, small_height),
                                    Image.Resampling.BILINEAR),
        dtype=np.float32) / 255.0
    ys = np.arange(small_height, dtype=np.int32)[:, None]
    xs = np.arange(small_width, dtype=np.int32)[None, :]
    dots = light > _BAYER4[ys % 4, xs % 4]
    ink_rgb = np.array(imaging.hex_to_rgb(ink), dtype=np.float32) / 255.0
    paper_rgb = np.array(imaging.hex_to_rgb(paper), dtype=np.float32) / 255.0
    mixed = np.where(dots[..., None], ink_rgb, paper_rgb)
    image = Image.fromarray(
        (mixed * 255.0 + 0.5).astype(np.uint8), "RGB")
    if (small_width, small_height) != (width, height):
        image = image.resize((width, height), Image.Resampling.NEAREST)
    return _attach(content, image)


def _edges(content: Image.Image, color: str, background: str,
           amount: float) -> Image.Image:
    strokes = content.convert("L").filter(ImageFilter.FIND_EDGES)
    strokes = strokes.point(lambda value: 255 - value)
    paper = ImageOps.colorize(strokes, black=color, white=background)
    return _attach(content, Image.blend(
        content.convert("RGB"), paper,
        max(0.0, min(1.0, amount))))


def _rays(size: tuple[int, int], color: str, count: float, angle: float,
          length: float, opacity: float) -> Image.Image:
    width, height = size
    if width < 8 or height < 8:
        return Image.new("RGBA", size, (0, 0, 0, 0))
    count = max(2, min(64, int(round(count))))
    ys = np.linspace(-1.0, 1.0, height, dtype=np.float32)[:, None]
    xs = np.linspace(-1.0, 1.0, width, dtype=np.float32)[None, :]
    theta = np.arctan2(ys, xs) - math.radians(angle)
    wave = 0.5 + 0.5 * np.cos(theta * count)
    radius = np.sqrt(xs * xs + ys * ys) / max(0.15, length)
    falloff = np.clip(1.0 - radius, 0.0, 1.0)
    mask = np.clip(wave ** 6 * falloff * opacity, 0.0, 1.0)
    array = np.zeros((height, width, 4), dtype=np.uint8)
    array[..., 0], array[..., 1], array[..., 2] = imaging.hex_to_rgb(color)
    array[..., 3] = (mask * 255.0 + 0.5).astype(np.uint8)
    return Image.fromarray(array, "RGBA")


def _chromatic(content: Image.Image, offset: float) -> Image.Image:
    shift = int(round(offset))
    if shift < 1:
        return content
    red, green, blue, alpha = content.split()
    red = _offset_channel(red, shift)
    blue = _offset_channel(blue, -shift)
    merged = Image.merge("RGBA", (red, green, blue, alpha))
    return merged


def _offset_channel(channel: Image.Image, dx: int) -> Image.Image:
    out = Image.new("L", channel.size, 0)
    out.paste(channel, (dx, 0))
    return out


def _glitch(content: Image.Image, amount: float) -> Image.Image:
    width, height = content.size
    if width < 4 or height < 4:
        return content
    rng = np.random.default_rng(20261112)
    out = content.copy()
    slices = max(3, int(round(amount * 40)))
    for _ in range(slices):
        band = max(1, int(height * (0.01 + rng.random() * 0.05)))
        top = int(rng.integers(0, max(1, height - band)))
        shift = int((rng.random() - 0.5) * 2 * amount * width * 0.25)
        piece = out.crop((0, top, width, top + band))
        band_image = Image.new("RGBA", (width, band), (0, 0, 0, 0))
        band_image.paste(piece, (shift, 0))
        out.paste(band_image, (0, top))
    if amount > 0.15:
        out = _chromatic(out, max(1.0, amount * width * 0.05))
    return out


def _scanlines(content: Image.Image, spacing: float, opacity: float) -> Image.Image:
    width, height = content.size
    step = max(2.0, spacing)
    array = np.asarray(content.convert("RGB"), dtype=np.float32)
    ys = np.arange(height, dtype=np.float32)[:, None, None]
    line = (np.mod(ys, step) < max(1.0, step * 0.4)).astype(np.float32)
    array *= (1.0 - line * opacity)
    return _attach(content, Image.fromarray(
        np.clip(array, 0, 255).astype(np.uint8), "RGB"))


def _grain(content: Image.Image, amount: float) -> Image.Image:
    array = np.asarray(content.convert("RGB"), dtype=np.float32)
    rng = np.random.default_rng(1337)
    noise = rng.normal(0.0, 255.0 * amount * 0.35,
                       array.shape[:2]).astype(np.float32)
    array = array + noise[..., None]
    return _attach(content, Image.fromarray(
        np.clip(array, 0, 255).astype(np.uint8), "RGB"))


def _vignette(content: Image.Image, amount: float) -> Image.Image:
    width, height = content.size
    array = np.asarray(content.convert("RGB"), dtype=np.float32)
    ys = np.linspace(-1.0, 1.0, height, dtype=np.float32)[:, None]
    xs = np.linspace(-1.0, 1.0, width, dtype=np.float32)[None, :]
    distance = np.sqrt(xs * xs + ys * ys) / math.sqrt(2.0)
    falloff = np.clip((distance - 0.35) / 0.65, 0.0, 1.0) ** 1.6
    array *= (1.0 - falloff[..., None] * amount)
    return _attach(content, Image.fromarray(
        np.clip(array, 0, 255).astype(np.uint8), "RGB"))


def _bloom(content: Image.Image, color: str, opacity: float,
           radius: float) -> Image.Image:
    rgb = content.convert("RGB")
    blurred = rgb.filter(ImageFilter.GaussianBlur(max(0.6, radius)))
    tinted = Image.blend(blurred, Image.new("RGB", rgb.size,
                                            imaging.hex_to_rgb(color)), 0.35)
    screened = ImageChops.screen(rgb, tinted)
    return _attach(content, Image.blend(rgb, screened, max(0.0, min(1.0, opacity))))


def _inner_glow(content: Image.Image, color: str, opacity: float,
                radius: float) -> Image.Image:
    alpha = _alpha(content)
    inverted = ImageOps.invert(alpha)
    blurred = inverted.filter(ImageFilter.GaussianBlur(max(0.6, radius)))
    inside = ImageChops.multiply(blurred, alpha)
    glow = _tint(inside, color, opacity)
    return Image.alpha_composite(content, glow)


# --------------------------------------------------------------------------
# the stack
# --------------------------------------------------------------------------
def apply_stack(image: Image.Image, settings: dict | None,
                width: int, height: int) -> Image.Image:
    """Return ``image`` with the enabled effects baked in."""
    settings = settings or {}
    content = image.convert("RGBA")
    shortest = max(1.0, float(min(width, height)))
    size = content.size
    base_alpha = _alpha(content)
    behind = Image.new("RGBA", size, (0, 0, 0, 0))

    if enabled(settings, "rays"):
        entry = settings["rays"]
        behind = Image.alpha_composite(behind, _rays(
            size, entry.get("color", "#ffb347"),
            _number(entry, "count", 12), _number(entry, "angle", 0.0),
            _number(entry, "length", 0.9),
            max(0.0, min(1.0, _number(entry, "opacity", 0.35)))))

    if enabled(settings, "long_shadow"):
        entry = settings["long_shadow"]
        distance = max(0.0, _number(entry, "distance", 0.18)) * shortest
        steps = max(2, min(40, int(_number(entry, "steps", 18))))
        angle = math.radians(_number(entry, "angle", 45.0))
        tinted = _tint(base_alpha, entry.get("color", "#000000"),
                       _number(entry, "opacity", 0.5))
        step_x = math.cos(angle) * distance / steps
        step_y = math.sin(angle) * distance / steps
        for index in range(steps, 0, -1):
            behind = Image.alpha_composite(
                behind, _offset_paste(tinted, step_x * index, step_y * index))

    if enabled(settings, "shadow"):
        entry = settings["shadow"]
        blur = max(0.0, _number(entry, "blur", 0.018)) * shortest
        alpha = base_alpha.filter(ImageFilter.GaussianBlur(blur)) \
            if blur >= 0.3 else base_alpha
        shadow = _tint(alpha, entry.get("color", "#000000"),
                       _number(entry, "opacity", 0.55))
        behind = Image.alpha_composite(
            behind, _offset_paste(shadow,
                                  _number(entry, "dx", 0.0) * width,
                                  _number(entry, "dy", 0.0) * height))

    if enabled(settings, "glow"):
        entry = settings["glow"]
        radius = max(1.0, _number(entry, "size", 0.022) * shortest * 1.15)
        alpha = base_alpha.filter(ImageFilter.GaussianBlur(radius))
        behind = Image.alpha_composite(
            behind, _tint(alpha, entry.get("color", "#ff7a3d"),
                          _number(entry, "opacity", 0.55)))

    if enabled(settings, "outline"):
        entry = settings["outline"]
        width_px = _number(entry, "width", 0.012) * shortest
        grown = _grow(base_alpha, width_px)
        ring = ImageChops.subtract(grown, base_alpha)
        behind = Image.alpha_composite(
            behind, _tint(ring, entry.get("color", "#08080c"), 1.0))

    for name in _CONTENT_ORDER:
        if not enabled(settings, name):
            continue
        entry = settings[name]
        if name == "blur":
            content = _blur_content(content,
                                    _number(entry, "radius", 0.006) * shortest)
        elif name == "motion_blur":
            content = _motion(content,
                              _number(entry, "radius", 0.012) * shortest,
                              _number(entry, "angle", 0.0))
        elif name == "pixelate":
            content = _pixelate(content,
                                max(2.0, _number(entry, "size", 0.012) * shortest))
        elif name == "edges":
            content = _edges(content,
                             entry.get("color", "#2b2b33"),
                             entry.get("background", "#f7f3ea"),
                             _number(entry, "amount", 0.9))
        elif name == "posterize":
            levels = max(2, min(32, int(_number(entry, "levels", 4))))
            bits = max(1, min(8, int(round(math.log2(levels)))))
            content = _attach(content, ImageOps.posterize(
                content.convert("RGB"), bits))
        elif name == "duotone":
            content = _duotone(content, entry.get("color", "#ff9a5c"),
                               entry.get("color2", "#140b24"))
        elif name == "gradient_map":
            content = _gradient_map(content,
                                    entry.get("color2", "#160a20"),
                                    entry.get("color3", "#7c3aed"),
                                    entry.get("color", "#f4fbff"))
        elif name == "threshold":
            content = _threshold(content, _number(entry, "level", 0.5))
        elif name == "dither":
            content = _dither(content,
                              max(1.0, _number(entry, "size", 0.004)
                                  * shortest),
                              entry.get("ink", "#0b0813"),
                              entry.get("paper", "#f6e7d6"))
        elif name == "invert":
            content = _attach(content, ImageOps.invert(content.convert("RGB")))
        elif name == "saturate":
            content = _attach(content, ImageEnhance.Color(
                content.convert("RGB")).enhance(
                    max(0.0, _number(entry, "amount", 1.5))))
        elif name == "contrast":
            content = _attach(content, ImageEnhance.Contrast(
                content.convert("RGB")).enhance(
                    max(0.0, _number(entry, "amount", 1.25))))
        elif name == "emboss":
            amount = max(0.0, min(1.0, _number(entry, "amount", 0.45)))
            rgb = content.convert("RGB")
            raised = rgb.filter(ImageFilter.EMBOSS)
            content = _attach(content, Image.blend(rgb, raised, amount))
        elif name == "halftone":
            content = _halftone(content,
                                _number(entry, "size", 0.014) * shortest,
                                entry.get("ink", "#0b0813"),
                                entry.get("paper", "#f6e7d6"))
        elif name == "hue_shift":
            content = _hue_shift(content, _number(entry, "degrees", 0.0))
        elif name == "chromatic":
            content = _chromatic(content,
                                 _number(entry, "offset", 0.004) * shortest)

    merged = Image.alpha_composite(behind, content)

    if enabled(settings, "inner_glow"):
        entry = settings["inner_glow"]
        merged = _inner_glow(merged, entry.get("color", "#ffc07a"),
                             _number(entry, "opacity", 0.5),
                             _number(entry, "size", 0.02) * shortest)

    if enabled(settings, "bloom"):
        entry = settings["bloom"]
        merged = _bloom(merged, entry.get("color", "#ffd9a8"),
                        _number(entry, "opacity", 0.5),
                        _number(entry, "size", 0.03) * shortest)

    if enabled(settings, "glitch"):
        merged = _glitch(merged, _number(settings["glitch"], "amount", 0.12))

    if enabled(settings, "scanlines"):
        entry = settings["scanlines"]
        merged = _scanlines(merged,
                            max(2.0, _number(entry, "spacing", 0.004) * shortest),
                            max(0.0, min(1.0, _number(entry, "opacity", 0.28))))

    if enabled(settings, "grain"):
        merged = _grain(merged, max(0.0, _number(settings["grain"], "amount", 0.14)))

    if enabled(settings, "vignette"):
        merged = _vignette(merged,
                           max(0.0, _number(settings["vignette"], "amount", 0.55)))

    return merged
