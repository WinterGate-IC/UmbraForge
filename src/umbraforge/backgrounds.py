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
        "poster_ink", "Poster Ink", "Moody vignetted ink for poster art.",
        "Classic",
        _bg("linear", color="#1e172b", color2="#06060a", angle=90, vignette=0.52),
    ),
    BackgroundPreset(
        "ink_wash", "Ink Wash", "Blue-black parchment with a faint wash.",
        "Classic",
        _bg("linear", color="#1a2233", color2="#05060a", angle=110,
            pattern="noise", pattern_color="#9fb4d6",
            pattern_opacity=0.06, pattern_scale=0.5, vignette=0.44),
    ),
    BackgroundPreset(
        "gilded_dusk", "Gilded Dusk", "Old-gold radial for crests and seals.",
        "Classic",
        _bg("radial", color="#5a4318", color2="#08070a",
            pattern="rings", pattern_color="#e9c46a",
            pattern_opacity=0.10, pattern_scale=0.62, vignette=0.48),
    ),

    # ------------------------------------------------------------------ warm
    BackgroundPreset(
        "ember_haze", "Ember Haze", "Fire-lit fade, great for badges and crests.",
        "Warm",
        _bg("linear", color="#2a130c", color2="#070609", angle=125,
            pattern="rings", pattern_color="#ff7a3d",
            pattern_opacity=0.07, pattern_scale=0.5, vignette=0.34),
    ),
    BackgroundPreset(
        "sunset_ridge", "Sunset Ridge", "Warm gradient with subtle grain.",
        "Warm",
        _bg("linear", color="#401d10", color2="#0a0710", angle=100,
            pattern="noise", pattern_color="#ffd9b0",
            pattern_opacity=0.05, pattern_scale=0.42, vignette=0.34),
    ),
    BackgroundPreset(
        "lantern_night", "Lantern Night", "Deep amber glow over charcoal.",
        "Warm",
        _bg("radial", color="#6a2f10", color2="#07070b",
            pattern="dots", pattern_color="#ffcf8f",
            pattern_opacity=0.10, pattern_scale=0.55, vignette=0.46),
    ),
    BackgroundPreset(
        "desert_dusk", "Desert Dusk", "Dusty rose and burnt orange bands.",
        "Warm",
        _bg("linear", color="#5a2a22", color2="#140b14", angle=115,
            pattern="waves", pattern_color="#ffb066",
            pattern_opacity=0.06, pattern_scale=0.7, vignette=0.36),
    ),

    # ------------------------------------------------------------------ cool
    BackgroundPreset(
        "nocturne", "Nocturne", "Deep indigo radial with star speckles.",
        "Cool",
        _bg("radial", color="#3d236e", color2="#06050c",
            pattern="stars", pattern_color="#c4b5fd",
            pattern_opacity=0.22, pattern_scale=0.34, vignette=0.50),
    ),
    BackgroundPreset(
        "aurora", "Aurora", "Cool cyan haze with wave texture.",
        "Cool",
        _bg("linear", color="#0d3f4c", color2="#070510", angle=150,
            pattern="waves", pattern_color="#67e8f9",
            pattern_opacity=0.13, pattern_scale=0.66, vignette=0.42),
    ),
    BackgroundPreset(
        "glacier", "Glacier", "Pale ice light with a frozen grid.",
        "Cool",
        _bg("radial", color="#2e5a6b", color2="#05070d",
            pattern="grid", pattern_color="#d9f6ff",
            pattern_opacity=0.07, pattern_scale=0.75, vignette=0.40),
    ),
    BackgroundPreset(
        "deep_sea", "Deep Sea", "Navy depths with drifting motes.",
        "Cool",
        _bg("linear", color="#062033", color2="#02040a", angle=170,
            pattern="dots", pattern_color="#63e6ff",
            pattern_opacity=0.08, pattern_scale=0.42, vignette=0.52),
    ),

    # --------------------------------------------------------------- minimal
    BackgroundPreset(
        "velvet_night", "Velvet Night", "Smooth, neutral dark for clean type.",
        "Minimal",
        _bg("linear", color="#191926", color2="#090910", angle=90, vignette=0.22),
    ),
    BackgroundPreset(
        "polished_slategrey", "Polished Slate", "Clean, professional for type-heavy pieces.",
        "Minimal",
        _bg("radial", color="#363642", color2="#0b0b12", vignette=0.20),
    ),
    BackgroundPreset(
        "paper_grey", "Paper Grey", "Warm neutral sheet with a paper tooth.",
        "Minimal",
        _bg("solid", color="#2a2825",
            pattern="noise", pattern_color="#e8e2d4",
            pattern_opacity=0.06, pattern_scale=0.35, vignette=0.18),
    ),
    BackgroundPreset(
        "graphite", "Graphite", "Soft graphite radial, no pattern noise.",
        "Minimal",
        _bg("radial", color="#3b3b41", color2="#0a0a0e", vignette=0.28),
    ),
    BackgroundPreset(
        "linen", "Linen", "Woven dark cloth with a diagonal weave.",
        "Minimal",
        _bg("solid", color="#22202a",
            pattern="diagonal", pattern_color="#b7aed0",
            pattern_opacity=0.05, pattern_scale=0.3, vignette=0.24),
    ),

    # ------------------------------------------------------------------ tech
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
        "circuit", "Circuit", "Muted board green with fine traces.",
        "Tech",
        _bg("linear", color="#0d2b22", color2="#04070a", angle=140,
            pattern="grid", pattern_color="#7ef0b0",
            pattern_opacity=0.09, pattern_scale=0.35, vignette=0.34),
    ),
    BackgroundPreset(
        "mainframe", "Mainframe", "Terminal black with a phosphor grid.",
        "Tech",
        _bg("solid", color="#04100b",
            pattern="grid", pattern_color="#4ade80",
            pattern_opacity=0.10, pattern_scale=0.5, vignette=0.50),
    ),
    BackgroundPreset(
        "blueprint", "Blueprint", "Engineer's blue with a drafting grid.",
        "Tech",
        _bg("linear", color="#123a6b", color2="#071a36", angle=160,
            pattern="grid", pattern_color="#bfe3ff",
            pattern_opacity=0.12, pattern_scale=0.4, vignette=0.30),
    ),

    # ----------------------------------------------------------------- retro
    BackgroundPreset(
        "scanline_dark", "Scanline Dark", "Retro display look without hiding art.",
        "Retro",
        _bg("solid", color="#0a0d16",
            pattern="scanlines", pattern_color="#63e6ff",
            pattern_opacity=0.10, pattern_scale=0.9, vignette=0.50),
    ),
    BackgroundPreset(
        "vhs_night", "VHS Night", "Tape-era magenta with soft tracking bars.",
        "Retro",
        _bg("linear", color="#3d0b33", color2="#06050c", angle=105,
            pattern="scanlines", pattern_color="#ff9ad5",
            pattern_opacity=0.07, pattern_scale=0.7, vignette=0.44),
    ),
    BackgroundPreset(
        "arcade_carpet", "Arcade Carpet", "Loud triangles on midnight purple.",
        "Retro",
        _bg("linear", color="#1c0f2e", color2="#07040c", angle=120,
            pattern="triangles", pattern_color="#7c3aed",
            pattern_opacity=0.14, pattern_scale=0.5, vignette=0.48),
    ),
    BackgroundPreset(
        "sepia_film", "Sepia Film", "Warm brown stock with silver grain.",
        "Retro",
        _bg("radial", color="#4a3a24", color2="#0c0a08",
            pattern="noise", pattern_color="#f0dcb8",
            pattern_opacity=0.08, pattern_scale=0.4, vignette=0.52),
    ),

    # ---------------------------------------------------------------- nature
    BackgroundPreset(
        "forest_floor", "Forest Floor", "Mossy green with dappled texture.",
        "Nature",
        _bg("radial", color="#173d27", color2="#040806",
            pattern="noise", pattern_color="#9fe6b0",
            pattern_opacity=0.07, pattern_scale=0.45, vignette=0.48),
    ),
    BackgroundPreset(
        "moss_light", "Moss Light", "Soft green light through a canopy.",
        "Nature",
        _bg("linear", color="#1d4a33", color2="#070b09", angle=95,
            pattern="dots", pattern_color="#d6f5bd",
            pattern_opacity=0.09, pattern_scale=0.5, vignette=0.40),
    ),
    BackgroundPreset(
        "sand_dune", "Sand Dune", "Warm sand with wind-carved bands.",
        "Nature",
        _bg("linear", color="#5c4526", color2="#100b09", angle=100,
            pattern="waves", pattern_color="#ffdf9e",
            pattern_opacity=0.08, pattern_scale=0.8, vignette=0.34),
    ),
    BackgroundPreset(
        "storm_sky", "Storm Sky", "Cold slate clouds and distant rain.",
        "Nature",
        _bg("linear", color="#27303b", color2="#07090d", angle=120,
            pattern="diagonal", pattern_color="#a9c6d8",
            pattern_opacity=0.06, pattern_scale=0.35, vignette=0.42),
    ),

    # ----------------------------------------------------------------- print
    BackgroundPreset(
        "risograph", "Risograph", "Warm paper with a riso ink dot screen.",
        "Print",
        _bg("solid", color="#e8ddc8",
            pattern="dots", pattern_color="#ff5c39",
            pattern_opacity=0.12, pattern_scale=0.22, vignette=0.14),
    ),
    BackgroundPreset(
        "newsprint", "Newsprint", "Cool stock with a fine editorial screen.",
        "Print",
        _bg("solid", color="#d8d4c8",
            pattern="dots", pattern_color="#2a2a2e",
            pattern_opacity=0.10, pattern_scale=0.18, vignette=0.12),
    ),
    BackgroundPreset(
        "comic_ink", "Comic Ink", "Bright newsprint with a bold half-tone.",
        "Print",
        _bg("solid", color="#f2d98a",
            pattern="dots", pattern_color="#1a1420",
            pattern_opacity=0.14, pattern_scale=0.26, vignette=0.16),
    ),

    # ------------------------------------------------------------------ neon
    BackgroundPreset(
        "synth_sunset", "Synth Sunset", "Magenta horizon with a retro grid.",
        "Neon",
        _bg("linear", color="#6a1460", color2="#0b0518", angle=100,
            pattern="grid", pattern_color="#ff5cd6",
            pattern_opacity=0.12, pattern_scale=0.5, vignette=0.42),
    ),
    BackgroundPreset(
        "cyber_lime", "Cyber Lime", "Acid green on near-black circuitry.",
        "Neon",
        _bg("linear", color="#184017", color2="#04060a", angle=150,
            pattern="hexagons", pattern_color="#b6ff4d",
            pattern_opacity=0.12, pattern_scale=0.55, vignette=0.46),
    ),
    BackgroundPreset(
        "electric_blue", "Electric Blue", "Cold electric rays behind the art.",
        "Neon",
        _bg("radial", color="#133a7a", color2="#04060d",
            pattern="rays", pattern_color="#63b3ff",
            pattern_opacity=0.10, pattern_scale=0.7, vignette=0.44),
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
