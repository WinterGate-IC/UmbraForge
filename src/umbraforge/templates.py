"""Template gallery.

Each template is a complete, editable design: background, shapes, icons and
type in normalized coordinates. Nothing is flattened, so picking one is only
a starting point - every part can be moved, recoloured or deleted.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from . import presets
from .layers import (
    Design,
    IconLayer,
    Layer,
    ShapeLayer,
    TextLayer,
    default_background,
    merge,
)


@dataclass(frozen=True)
class Template:
    key: str
    name: str
    note: str
    category: str
    build: Callable[[], Design]


def _new(name: str, preset: str, background: dict) -> Design:
    canvas = presets.get(preset)
    design = Design(name=name, width=canvas.width, height=canvas.height)
    design.background = merge(default_background(), background)
    return design


def _square_height(design: Design, width: float) -> float:
    return width * design.width / design.height


def _shape(design: Design, shape: str, x: float, y: float, w: float,
           h: float, fill: str, name: str | None = None, *,
           gradient: bool = False, fill2: str = "", angle: float = 90.0,
           stroke: str = "", stroke_width: float = 0.0,
           rotation: float = 0.0) -> ShapeLayer:
    layer = ShapeLayer(name=name or shape.title(), shape=shape, x=x, y=y,
                       w=w, h=h, fill=fill, gradient=gradient, fill2=fill2,
                       gradient_angle=angle, stroke=stroke,
                       stroke_width=stroke_width, rotation=rotation)
    design.add(layer)
    return layer


def _icon(design: Design, icon: str, x: float, y: float, size: float,
          color: str, name: str | None = None, *,
          gradient: bool = False, fill2: str = "", angle: float = 90.0,
          rotation: float = 0.0) -> IconLayer:
    layer = IconLayer(name=name or icon.title(), icon=icon, x=x, y=y,
                      w=size, h=_square_height(design, size), color=color,
                      gradient=gradient, fill2=fill2, gradient_angle=angle,
                      rotation=rotation)
    design.add(layer)
    return layer


def _text(design: Design, text: str, x: float, y: float, w: float, h: float,
          size: float, color: str, name: str | None = None, *,
          font: str = "Bahnschrift", weight: int = 700, align: str = "center",
          valign: str = "middle", spacing: float = 0.0,
          uppercase: bool = False) -> TextLayer:
    layer = TextLayer(name=name or "Type", text=text, x=x, y=y, w=w, h=h,
                      size=size, color=color, font=font, weight=weight,
                      align=align, valign=valign, letter_spacing=spacing,
                      uppercase=uppercase)
    design.add(layer)
    return layer


def _glow(layer: Layer, color: str, size: float = 0.02,
          opacity: float = 0.6) -> Layer:
    layer.effects["glow"].update(enabled=True, color=color, size=size,
                                 opacity=opacity)
    return layer


def _shadow(layer: Layer, blur: float = 0.02, opacity: float = 0.6,
            dx: float = 0.004, dy: float = 0.008) -> Layer:
    layer.effects["shadow"].update(enabled=True, color="#000000", blur=blur,
                                   opacity=opacity, dx=dx, dy=dy)
    return layer


# --------------------------------------------------------------------------
# templates
# --------------------------------------------------------------------------
def ember_sigil() -> Design:
    design = _new("Ember Sigil", "profile", {
        "kind": "linear", "color": "#160b08", "color2": "#050508",
        "angle": 125, "pattern": "rings", "pattern_color": "#ff7a3d",
        "pattern_opacity": 0.045, "pattern_scale": 0.55, "vignette": 0.45,
    })
    ring = _shape(design, "ring", 0.14, 0.14, 0.72, 0.72, "#ff7a3d",
                  "Sigil ring", gradient=True, fill2="#7a2410", angle=120)
    _glow(ring, "#ff5a1f", 0.03, 0.55)
    _shape(design, "circle", 0.205, 0.205, 0.59, 0.59, "#0c0a0e",
           "Sigil void", gradient=True, fill2="#171018", angle=90)
    spark = _icon(design, "flame", 0.405, 0.34, 0.19, "#ffb066",
                  "Ember", gradient=True, fill2="#ff5a1f", angle=90)
    _glow(spark, "#ff7a3d", 0.045, 0.65)
    _text(design, "UMBRA", 0.10, 0.655, 0.80, 0.075, 0.068, "#f3f1f8",
          "Wordmark", weight=800, spacing=0.18)
    _text(design, "FORGE", 0.10, 0.735, 0.80, 0.045, 0.026, "#ff7a3d",
          "Rule", weight=600, spacing=0.62)
    return design


def night_crown() -> Design:
    design = _new("Night Crown", "profile", {
        "kind": "radial", "color": "#2a1648", "color2": "#05050a",
        "pattern": "stars", "pattern_color": "#c4b5fd",
        "pattern_opacity": 0.16, "pattern_scale": 0.35, "vignette": 0.55,
    })
    _shape(design, "ring", 0.115, 0.115, 0.77, 0.77, "#211632",
           "Halo", gradient=True, fill2="#0b0812", angle=90)
    crown = _icon(design, "crown", 0.265, 0.19, 0.47, "#c4b5fd",
                  "Crown", gradient=True, fill2="#7c3aed", angle=110)
    _glow(crown, "#8b5cf6", 0.045, 0.6)
    _text(design, "NOCTURNE", 0.07, 0.60, 0.86, 0.085, 0.072, "#f3f1f8",
          "Wordmark", weight=700, spacing=0.16)
    _shape(design, "square", 0.34, 0.705, 0.32, 0.0035, "#8b5cf6",
           "Rule")
    _text(design, "NIGHT COURT", 0.15, 0.735, 0.70, 0.04, 0.024, "#a397bd",
          "Subtitle", weight=600, spacing=0.42)
    return design


def void_orbit() -> Design:
    design = _new("Void Orbit", "desktop", {
        "kind": "linear", "color": "#05050b", "color2": "#1a0f2e",
        "angle": 100, "pattern": "stars", "pattern_color": "#cfc6ff",
        "pattern_opacity": 0.28, "pattern_scale": 0.55, "vignette": 0.5,
    })
    _text(design, "BEYOND", 0.055, 0.30, 0.52, 0.20, 0.185, "#f3f1f8",
          "Headline", weight=800, align="left", spacing=-0.01)
    _text(design, "THE VEIL", 0.06, 0.505, 0.42, 0.07, 0.042, "#ff7a3d",
          "Kicker", weight=700, align="left", spacing=0.34)
    _shape(design, "square", 0.06, 0.625, 0.18, 0.0035, "#ff7a3d", "Rule")
    _text(design, "AN ORIGINAL STUDY IN DARKNESS", 0.06, 0.655, 0.46, 0.05,
          0.019, "#8f8aa3", "Note", weight=500, align="left", spacing=0.18)
    orbit = _icon(design, "orbit", 0.615, 0.18, 0.38, "#8b5cf6",
                  "Orbit", gradient=True, fill2="#ff7a3d", angle=35)
    _glow(orbit, "#7c3aed", 0.045, 0.6)
    _icon(design, "star", 0.86, 0.19, 0.026, "#ffb066", "North star")
    _text(design, "UMBRAFORGE  \u00b7  001", 0.62, 0.805, 0.32, 0.04,
          0.017, "#7e7891", "Credit", weight=600, align="right", spacing=0.24)
    return design


def dusk_ridge() -> Design:
    design = _new("Dusk Ridge", "mobile", {
        "kind": "linear", "color": "#08080e", "color2": "#42160e",
        "angle": 90, "pattern": "noise", "pattern_color": "#ffd9b0",
        "pattern_opacity": 0.05, "pattern_scale": 0.4, "vignette": 0.5,
    })
    sun = _shape(design, "circle", 0.19, 0.285, 0.62, 0.349, "#ff7a3d",
                 "Setting sun", gradient=True, fill2="#ffcf8f", angle=90)
    _glow(sun, "#ff5a1f", 0.05, 0.65)
    _shape(design, "triangle", -0.18, 0.675, 1.10, 0.28, "#0b0b12",
           "Ridge back", rotation=0)
    _shape(design, "triangle", -0.10, 0.725, 0.82, 0.24, "#08080d",
           "Ridge mid")
    _shape(design, "triangle", 0.34, 0.795, 0.78, 0.18, "#050509",
           "Ridge front")
    _text(design, "DUSK", 0.10, 0.605, 0.80, 0.085, 0.072, "#f3f1f8",
          "Wordmark", weight=800, spacing=0.28)
    _text(design, "RIDGE", 0.10, 0.675, 0.80, 0.04, 0.023, "#ffb066",
          "Kicker", weight=600, spacing=0.7)
    _text(design, "A WINTERGATE STUDY", 0.16, 0.875, 0.68, 0.035, 0.016,
          "#8c8499", "Footer", weight=500, spacing=0.3)
    return design


def signal_lost() -> Design:
    design = _new("Signal Lost", "profile", {
        "kind": "solid", "color": "#06060a", "pattern": "scanlines",
        "pattern_color": "#63e6ff", "pattern_opacity": 0.07,
        "pattern_scale": 0.9, "vignette": 0.6,
    })
    _shape(design, "square", 0.17, 0.32, 0.66, 0.0025, "#26313a", "Rule")
    aim = _icon(design, "crosshair", 0.265, 0.17, 0.47, "#63e6ff",
                "Crosshair", gradient=True, fill2="#2b6f7d", angle=120)
    _glow(aim, "#22d3ee", 0.035, 0.55)
    _text(design, "SIGNAL", 0.08, 0.61, 0.84, 0.085, 0.072, "#f3f1f8",
          "Wordmark", weight=800, spacing=0.12)
    _text(design, "LOST", 0.08, 0.685, 0.84, 0.062, 0.052, "#63e6ff",
          "Kicker", weight=700, spacing=0.42)
    _text(design, "NO CARRIER  /  NO HORIZON", 0.12, 0.79, 0.76, 0.035,
          0.016, "#5f6f78", "Footer", weight=600, spacing=0.3)
    return design


def chrome_standard() -> Design:
    design = _new("Chrome Standard", "banner", {
        "kind": "linear", "color": "#0b0b12", "color2": "#171425",
        "angle": 20, "pattern": "grid", "pattern_color": "#a6a1b8",
        "pattern_opacity": 0.055, "pattern_scale": 0.7, "vignette": 0.4,
    })
    shield = _icon(design, "shield", 0.055, 0.20, 0.175, "#ff7a3d",
                   "Crest", gradient=True, fill2="#8b5cf6", angle=100)
    _glow(shield, "#ff7a3d", 0.02, 0.45)
    _text(design, "WINTERGATE", 0.285, 0.265, 0.65, 0.17, 0.205, "#f3f1f8",
          "Wordmark", weight=800, align="left", spacing=0.045)
    _text(design, "INTELLIGENCE COLLECTIVE", 0.29, 0.455, 0.60, 0.075,
          0.042, "#ff8f5c", "Descriptor", weight=600, align="left",
          spacing=0.32)
    _shape(design, "square", 0.29, 0.60, 0.30, 0.004, "#34304a", "Rule")
    _text(design, "EST. 2026", 0.64, 0.585, 0.20, 0.07, 0.036, "#7f7895",
          "Year", weight=600, align="left", spacing=0.3)
    return design


def static_skull() -> Design:
    design = _new("Static Skull", "square", {
        "kind": "linear", "color": "#0d0d12", "color2": "#050508",
        "angle": 100, "pattern": "noise", "pattern_color": "#f3f1f8",
        "pattern_opacity": 0.07, "pattern_scale": 0.5, "vignette": 0.55,
    })
    _shape(design, "circle", 0.145, 0.115, 0.71, 0.71, "#131318",
           "Disc", gradient=True, fill2="#0a0a0e", angle=120)
    skull = _icon(design, "skull", 0.265, 0.175, 0.47, "#f3f1f8",
                  "Skull", gradient=True, fill2="#9a93ad", angle=100)
    _glow(skull, "#ff7a3d", 0.03, 0.4)
    _text(design, "NO", 0.18, 0.585, 0.64, 0.10, 0.105, "#f3f1f8",
          "Line one", weight=800, spacing=0.3)
    _text(design, "SIGNAL", 0.18, 0.665, 0.64, 0.085, 0.078, "#ff7a3d",
          "Line two", weight=800, spacing=0.18)
    _shape(design, "square", 0.22, 0.795, 0.56, 0.003, "#3a3548", "Rule")
    _text(design, "DEAD AIR / OPEN FREQUENCY", 0.20, 0.825, 0.60, 0.035,
          0.017, "#7b748e", "Footer", weight=600, spacing=0.24)
    return design


def forge_mark() -> Design:
    design = _new("Forge Mark", "square", {
        "kind": "radial", "color": "#35190b", "color2": "#07070b",
        "pattern": "dots", "pattern_color": "#ffb066",
        "pattern_opacity": 0.10, "pattern_scale": 0.5, "vignette": 0.5,
    })
    tile = _shape(design, "rounded", 0.20, 0.17, 0.60, 0.60, "#12121b",
                  "Plate", gradient=True, fill2="#0a0a10", angle=120,
                  stroke="#5a3220", stroke_width=0.006)
    _shadow(tile, 0.02, 0.5, 0.004, 0.01)
    _text(design, "UF", 0.20, 0.30, 0.60, 0.28, 0.225, "#ff7a3d",
          "Monogram", weight=800, spacing=-0.02)
    _icon(design, "bolt", 0.585, 0.505, 0.062, "#ffd3a8", "Spark")
    _text(design, "UMBRAFORGE", 0.15, 0.815, 0.70, 0.05, 0.032,
          "#e7e1f0", "Wordmark", weight=700, spacing=0.36)
    _text(design, "DESIGN STUDIO", 0.20, 0.865, 0.60, 0.035, 0.016,
          "#8a7f96", "Footer", weight=600, spacing=0.4)
    return design


def laurel_standard() -> Design:
    design = _new("Laurel Standard", "profile", {
        "kind": "linear", "color": "#121018", "color2": "#241a0c",
        "angle": 135, "pattern": "grid", "pattern_color": "#d9b46a",
        "pattern_opacity": 0.045, "pattern_scale": 0.8, "vignette": 0.5,
    })
    wreath = _icon(design, "laurel", 0.235, 0.145, 0.53, "#d9b46a",
                   "Laurel", gradient=True, fill2="#8a5a1f", angle=110)
    _glow(wreath, "#d9b46a", 0.025, 0.4)
    _shape(design, "shield", 0.365, 0.265, 0.27, 0.27, "#0d0c12",
           "Escutcheon", stroke="#d9b46a", stroke_width=0.012)
    _icon(design, "star", 0.455, 0.345, 0.09, "#ff7a3d", "Star")
    _text(design, "STANDARD", 0.06, 0.685, 0.88, 0.075, 0.064, "#f3f1f8",
          "Wordmark", weight=700, spacing=0.24)
    _text(design, "MMXXVI", 0.20, 0.765, 0.60, 0.04, 0.022, "#d9b46a",
          "Year", weight=600, spacing=0.55)
    return design


def aurora_field() -> Design:
    design = _new("Aurora Field", "desktop", {
        "kind": "radial", "color": "#0a2b31", "color2": "#04040a",
        "pattern": "waves", "pattern_color": "#67e8f9",
        "pattern_opacity": 0.08, "pattern_scale": 0.7, "vignette": 0.55,
    })
    _icon(design, "orbit", 0.585, 0.115, 0.39, "#67e8f9", "Aurora",
          gradient=True, fill2="#8b5cf6", angle=40)
    _glow(_icon(design, "orbit", 0.615, 0.20, 0.26, "#c4b5fd", "Inner orbit"),
          "#8b5cf6", 0.035, 0.5)
    _text(design, "NORTHERN", 0.055, 0.325, 0.55, 0.13, 0.115, "#f3f1f8",
          "Headline", weight=800, align="left", spacing=0.02)
    _text(design, "LIGHTS", 0.055, 0.44, 0.55, 0.13, 0.115, "#67e8f9",
          "Second line", weight=800, align="left", spacing=0.06)
    _shape(design, "square", 0.06, 0.615, 0.24, 0.003, "#2e7f8a", "Rule")
    _text(design, "THE SKY REMEMBERS EVERY SIGNAL", 0.06, 0.65, 0.48, 0.04,
          0.019, "#8ba3aa", "Note", weight=500, align="left", spacing=0.16)
    return design


def long_night() -> Design:
    design = _new("The Long Night", "poster", {
        "kind": "linear", "color": "#0a0a10", "color2": "#1c1026",
        "angle": 90, "pattern": "stars", "pattern_color": "#d8ccff",
        "pattern_opacity": 0.14, "pattern_scale": 0.4, "vignette": 0.5,
    })
    moon = _shape(design, "circle", 0.14, 0.36, 0.72, 0.48, "#c4b5fd",
                  "Moon", gradient=True, fill2="#3b2a5e", angle=100)
    _glow(moon, "#8b5cf6", 0.03, 0.35)
    _shape(design, "square", 0.10, 0.315, 0.80, 0.0025, "#5f5a74", "Rule")
    _text(design, "THE LONG", 0.10, 0.115, 0.80, 0.09, 0.052, "#f3f1f8",
          "Title one", weight=800, spacing=0.08)
    _text(design, "NIGHT", 0.10, 0.185, 0.80, 0.10, 0.075, "#ff7a3d",
          "Title two", weight=800, spacing=0.24)
    _text(design, "A STUDY IN DARKNESS AND DISTANCE", 0.15, 0.875, 0.70,
          0.03, 0.015, "#8a829d", "Footer", weight=600, spacing=0.3)
    _text(design, "01", 0.78, 0.115, 0.14, 0.03, 0.014, "#ff7a3d",
          "Number", weight=700, align="right", spacing=0.2)
    return design


def violet_mesh() -> Design:
    design = _new("Violet Mesh", "story", {
        "kind": "linear", "color": "#0c0714", "color2": "#25103f",
        "angle": 160, "pattern": "hexagons", "pattern_color": "#a78bfa",
        "pattern_opacity": 0.09, "pattern_scale": 0.65, "vignette": 0.55,
    })
    _icon(design, "bolt", 0.30, 0.24, 0.40, "#a78bfa", "Bolt",
          gradient=True, fill2="#ff7a3d", angle=120)
    _glow(_icon(design, "bolt", 0.35, 0.30, 0.30, "#f0eaff", "Core"),
          "#8b5cf6", 0.05, 0.6)
    _text(design, "HIGH", 0.10, 0.63, 0.80, 0.075, 0.072, "#f3f1f8",
          "Word one", weight=800, spacing=0.22)
    _text(design, "VOLTAGE", 0.10, 0.70, 0.80, 0.075, 0.062, "#ff8f5c",
          "Word two", weight=700, spacing=0.3)
    _text(design, "UMBRAFORGE  \u00b7  STORY", 0.14, 0.89, 0.72, 0.03,
          0.015, "#8b819c", "Footer", weight=600, spacing=0.34)
    return design


TEMPLATES: tuple[Template, ...] = (
    Template("ember_sigil", "Ember Sigil", "A forge-lit sigil for a profile.",
             "Featured", ember_sigil),
    Template("night_crown", "Night Crown", "Violet heraldry with a soft halo.",
             "Featured", night_crown),
    Template("void_orbit", "Void Orbit", "A wide wallpaper with orbital rings.",
             "Wallpaper", void_orbit),
    Template("aurora_field", "Aurora Field", "Teal and violet wide horizon.",
             "Wallpaper", aurora_field),
    Template("dusk_ridge", "Dusk Ridge", "A sunset ridge for a phone.",
             "Mobile", dusk_ridge),
    Template("violet_mesh", "Violet Mesh", "Neon bolt with a hex mesh.",
             "Mobile", violet_mesh),
    Template("signal_lost", "Signal Lost", "Cold cyan targeting art.",
             "Profile", signal_lost),
    Template("static_skull", "Static Skull", "Grainy, loud and monochrome.",
             "Square", static_skull),
    Template("forge_mark", "Forge Mark", "A clean monogram plate.",
             "Square", forge_mark),
    Template("laurel_standard", "Laurel Standard", "Gold laurel and star.",
             "Profile", laurel_standard),
    Template("chrome_standard", "Chrome Standard", "A wide WinterGate banner.",
             "Banner", chrome_standard),
    Template("long_night", "The Long Night", "A minimal two-colour poster.",
             "Poster", long_night),
)

TEMPLATE_MAP = {item.key: item for item in TEMPLATES}


def get(key: str) -> Template:
    return TEMPLATE_MAP[key]


def categories() -> list[str]:
    seen: list[str] = []
    for template in TEMPLATES:
        if template.category not in seen:
            seen.append(template.category)
    return seen


def build(key: str) -> Design:
    return TEMPLATE_MAP[key].build()
