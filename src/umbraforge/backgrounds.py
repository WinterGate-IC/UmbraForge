"""Curated background presets for fast starts.

These are just design.background values (merged against defaults), so they stay
editable in the Canvas tab and serialize cleanly into .umbra projects. Nothing
here is flattened or special-cased by the renderer beyond the existing kinds.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BackgroundPreset:
    key: str
    name: str
    note: str
    category: str
    background: dict


def _bg(kind: str, **kwargs) -> dict:
    base = {
        "kind": kind,
        "color": kwargs.pop("color", "#0a0a10"),
        "color2": kwargs.pop("color2", "#26123a"),
        "angle": kwargs.pop("angle", 135.0),
        "pattern": kwargs.pop("pattern", "none"),
        "pattern_color": kwargs.pop("pattern_color", "#ffffff"),
        "pattern_opacity": kwargs.pop("pattern_opacity", 0.07),
        "pattern_scale": kwargs.pop("pattern_scale", 0.35),
        "asset_id": kwargs.pop("asset_id", ""),
        "opacity": kwargs.pop("opacity", 1.0),
        "vignette": kwargs.pop("vignette", 0.25),
    }
    base.update(kwargs)
    return base


PRESETS: tuple[BackgroundPreset, ...] = (
    BackgroundPreset(
        "midnight_forge", "Midnight Forge", "Dark violet with a warm ember glow.",
        "Classic",
        _bg("linear", color="#241245", color2="#06060b", angle=135,
            pattern="rings", pattern_color="#ff8a4d",
            pattern_opacity=0.06, pattern_scale=0.55, vignette=0.30),
    ),
    BackgroundPreset(
        "ember_haze", "Ember Haze", "Fire-lit fade, great for badges and crests.",
        "Warm",
        _bg("linear", color="#2a130c", color2="#070609", angle=125,
            pattern="rings", pattern_color="#ff7a3d",
            pattern_opacity=0.07, pattern_scale=0.5, vignette=0.34),
    ),
    BackgroundPreset(
        "nocturne", "Nocturne", "Deep indigo radial with star speckles.",
        "Cool",
        _bg("radial", color="#3d236e", color2="#06050c",
            pattern="stars", pattern_color="#c4b5fd",
            pattern_opacity=0.22, pattern_scale=0.34, vignette=0.50),
    ),
    BackgroundPreset(
        "velvet_night", "Velvet Night", "Smooth, neutral dark for clean type.",
        "Minimal",
        _bg("linear", color="#191926", color2="#090910", angle=90, vignette=0.22),
    ),
    BackgroundPreset(
        "ocean_depth", "Ocean Depth", "Teal-tinted dark with a soft grid.",
        "Tech",
        _bg("linear", color="#0c3040", color2="#04070e", angle=160,
            pattern="grid", pattern_color="#63e6ff",
            pattern_opacity=0.10, pattern_scale=0.58, vignette=0.30),
    ),
    BackgroundPreset(
        "violet_mesh", "Violet Mesh", "Neon-friendly hex mesh for bold marks.",
        "Tech",
        _bg("linear", color="#291350", color2="#08060f", angle=160,
            pattern="hexagons", pattern_color="#a78bfa",
            pattern_opacity=0.14, pattern_scale=0.62, vignette=0.45),
    ),
    BackgroundPreset(
        "sunset_ridge", "Sunset Ridge", "Warm gradient with subtle grain.",
        "Warm",
        _bg("linear", color="#401d10", color2="#0a0710", angle=100,
            pattern="noise", pattern_color="#ffd9b0",
            pattern_opacity=0.05, pattern_scale=0.42, vignette=0.34),
    ),
    BackgroundPreset(
        "aurora", "Aurora", "Cool cyan haze with wave texture.",
        "Cool",
        _bg("linear", color="#0d3f4c", color2="#070510", angle=150,
            pattern="waves", pattern_color="#67e8f9",
            pattern_opacity=0.13, pattern_scale=0.66, vignette=0.42),
    ),
    BackgroundPreset(
        "scanline_dark", "Scanline Dark", "Retro display look without hiding art.",
        "Retro",
        _bg("solid", color="#0a0d16",
            pattern="scanlines", pattern_color="#63e6ff",
            pattern_opacity=0.10, pattern_scale=0.9, vignette=0.50),
    ),
    BackgroundPreset(
        "polished_slategrey", "Polished Slate", "Clean, professional for type-heavy pieces.",
        "Minimal",
        _bg("radial", color="#363642", color2="#0b0b12", vignette=0.20),
    ),
    BackgroundPreset(
        "poster_ink", "Poster Ink", "Moody vignetted ink for poster art.",
        "Classic",
        _bg("linear", color="#1e172b", color2="#06060a", angle=90, vignette=0.52),
    ),
    BackgroundPreset(
        "transparent", "Transparent", "No background drawn. Great for stickers, logos and overlays.",
        "Utility",
        _bg("transparent", vignette=0.0, pattern="none"),
    ),
)

PRESET_MAP = {item.key: item for item in PRESETS}


def keys() -> list[str]:
    return [item.key for item in PRESETS]


def categories() -> list[str]:
    seen: list[str] = []
    for item in PRESETS:
        if item.category not in seen:
            seen.append(item.category)
    return seen


def get(key: str) -> BackgroundPreset:
    return PRESET_MAP[key]
