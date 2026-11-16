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


def _outline(layer: Layer, color: str = "#000000",
             width: float = 0.006) -> Layer:
    layer.effects["outline"].update(enabled=True, color=color, width=width)
    return layer


def _mode(layer: Layer, name: str, **params) -> Layer:
    """Enable a named effect stage, e.g. ``_mode(layer, "comic", amount=0.8)``."""
    layer.effects[name].update(enabled=True, **params)
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


def meme_top_bottom() -> Design:
    design = _new("Top / Bottom Meme", "square", {
        "kind": "linear", "color": "#15131c", "color2": "#07070b",
        "angle": 120, "pattern": "noise", "pattern_color": "#ffffff",
        "pattern_opacity": 0.05, "pattern_scale": 0.5, "vignette": 0.42,
    })
    panel = _shape(design, "rounded", 0.06, 0.11, 0.88, 0.52,
                   "#2a2440", "Photo panel", gradient=True,
                   fill2="#120f1c", angle=115,
                   stroke="#4b4268", stroke_width=0.004)
    _mode(panel, "grain", amount=0.1)
    _icon(design, "eye", 0.42, 0.28, 0.16, "#7a6f9c", "Placeholder")
    top = _text(design, "TOP TEXT", 0.055, 0.12, 0.89, 0.13, 0.098,
                "#ffffff", "Top caption", weight=800, uppercase=True)
    _outline(top, "#000000", 0.008)
    _shadow(top, 0.006, 0.7, 0.003, 0.005)
    bottom = _text(design, "BOTTOM TEXT", 0.055, 0.665, 0.89, 0.15, 0.098,
                   "#ffffff", "Bottom caption", weight=800, uppercase=True)
    _outline(bottom, "#000000", 0.008)
    _shadow(bottom, 0.006, 0.7, 0.003, 0.005)
    _text(design, "EDIT ME", 0.06, 0.885, 0.88, 0.03, 0.014, "#6f6688",
          "Hint", weight=600, spacing=0.4)
    return design


def meme_drake() -> Design:
    design = _new("No / Yes Meme", "square", {
        "kind": "solid", "color": "#f0e6d2", "vignette": 0.12,
    })
    _shape(design, "rounded", 0.07, 0.09, 0.86, 0.35, "#28304a",
           "No panel", gradient=True, fill2="#131a2b", angle=100)
    _shape(design, "rounded", 0.07, 0.52, 0.86, 0.35, "#2f3f2a",
           "Yes panel", gradient=True, fill2="#142016", angle=100)
    _text(design, "NO", 0.12, 0.14, 0.36, 0.10, 0.075, "#ff7a6a",
          "No tag", weight=800, align="left", spacing=0.2)
    _text(design, "THAT", 0.12, 0.24, 0.70, 0.11, 0.085, "#f3f1f8",
          "No line", weight=800, align="left")
    _text(design, "YES", 0.12, 0.57, 0.36, 0.10, 0.075, "#9be89b",
          "Yes tag", weight=800, align="left", spacing=0.2)
    _text(design, "THIS", 0.12, 0.67, 0.70, 0.11, 0.085, "#f3f1f8",
          "Yes line", weight=800, align="left")
    _text(design, "PICK A SIDE", 0.10, 0.915, 0.80, 0.035, 0.018,
          "#5c5348", "Footer", weight=700, spacing=0.42)
    return design


def meme_brain() -> Design:
    design = _new("Expanding Brain", "square", {
        "kind": "linear", "color": "#0d0b12", "color2": "#040407",
        "angle": 160, "pattern": "stars", "pattern_color": "#c4b5fd",
        "pattern_opacity": 0.14, "pattern_scale": 0.4, "vignette": 0.45,
    })
    rows = [
        ("SMALL IDEA", "#4b4268", "#8b5cf6"),
        ("BIGGER IDEA", "#3b2f6b", "#a78bfa"),
        ("GALAXY IDEA", "#2a1f63", "#c4b5fd"),
        ("COSMIC IDEA", "#1d1450", "#f0eaff"),
    ]
    for index, (label, fill, glow) in enumerate(rows):
        top = 0.075 + index * 0.215
        height = 0.155
        tile = _shape(design, "rounded", 0.055, top, 0.55, height, fill,
                      f"Brain {index + 1}", gradient=True,
                      fill2="#0a0812", angle=110)
        if index == 3:
            _glow(tile, glow, 0.03, 0.5)
        _icon(design, "bolt", 0.075, top + 0.025, height * 0.62, glow,
              f"Spark {index + 1}")
        caption = _text(design, label, 0.075, top + 0.095, 0.50, 0.045,
                        0.023, "#e7e1f0", f"Label {index + 1}",
                        weight=700, align="left", spacing=0.14)
        if index == 3:
            _glow(caption, "#a78bfa", 0.012, 0.45)
    _text(design, "ASCEND", 0.64, 0.38, 0.30, 0.22, 0.05, "#ff8f5c",
          "Sideways", weight=800)
    return design


def meme_deep_fried() -> Design:
    design = _new("Deep Fried", "square", {
        "kind": "linear", "color": "#ff2d55", "color2": "#ffd60a",
        "angle": 45, "pattern": "scanlines", "pattern_color": "#00e5ff",
        "pattern_opacity": 0.1, "pattern_scale": 0.6, "vignette": 0.3,
    })
    headline = _text(design, "DEEP FRIED", 0.03, 0.10, 0.94, 0.30, 0.145,
                     "#ffffff", "Headline", weight=800, uppercase=True,
                     spacing=0.02)
    _outline(headline, "#000000", 0.014)
    _glow(headline, "#ff00c8", 0.04, 0.8)
    _mode(headline, "chromatic", offset=0.01)
    _text(design, "MAXIMUM\nSATURATION", 0.08, 0.44, 0.84, 0.24, 0.072,
          "#fff200", "Subhead", weight=800, uppercase=True, spacing=0.04)
    _icon(design, "bolt", 0.32, 0.70, 0.36, "#00e5ff", "Bolt",
          gradient=True, fill2="#ff00c8", angle=90)
    _text(design, "NO CHILL", 0.06, 0.86, 0.88, 0.06, 0.036, "#ffffff",
          "Footer", weight=800, uppercase=True, spacing=0.3)
    return design


def meme_galaxy() -> Design:
    design = _new("Galaxy Brain", "square", {
        "kind": "radial", "color": "#2a1466", "color2": "#03030a",
        "pattern": "stars", "pattern_color": "#e0d4ff",
        "pattern_opacity": 0.3, "pattern_scale": 0.5, "vignette": 0.55,
    })
    _icon(design, "orbit", 0.16, 0.14, 0.68, "#a78bfa", "Galaxy",
          gradient=True, fill2="#ff7a3d", angle=45)
    _glow(_icon(design, "star", 0.43, 0.34, 0.14, "#fff1c9", "Core"),
          "#ffd166", 0.05, 0.75)
    line = _text(design, "BEYOND", 0.08, 0.66, 0.84, 0.09, 0.085,
                 "#f3f1f8", "Wordmark", weight=800, spacing=0.18)
    _glow(line, "#8b5cf6", 0.025, 0.55)
    _text(design, "COMPREHENSION", 0.10, 0.755, 0.80, 0.05, 0.028,
          "#c4b5fd", "Kicker", weight=700, spacing=0.36)
    _text(design, "100% ENLIGHTENED", 0.14, 0.865, 0.72, 0.03, 0.014,
          "#8378a3", "Footer", weight=600, spacing=0.34)
    return design


def meme_this_is_fine() -> Design:
    design = _new("This Is Fine", "square", {
        "kind": "linear", "color": "#3a1408", "color2": "#0a0605",
        "angle": 110, "pattern": "rings", "pattern_color": "#ff7a3d",
        "pattern_opacity": 0.08, "pattern_scale": 0.7, "vignette": 0.55,
    })
    _shape(design, "rounded", 0.08, 0.10, 0.84, 0.55, "#1b100c",
           "Room", gradient=True, fill2="#0c0807", angle=100,
           stroke="#4a2418", stroke_width=0.004)
    _icon(design, "flame", 0.30, 0.17, 0.40, "#ff7a3d", "Fire",
          gradient=True, fill2="#ffd166", angle=90)
    _glow(_icon(design, "flame", 0.42, 0.29, 0.16, "#fff1c9", "Core"),
          "#ff5a1f", 0.05, 0.7)
    _text(design, "THIS IS FINE", 0.06, 0.69, 0.88, 0.10, 0.082,
          "#f3f1f8", "Caption", weight=800, uppercase=True)
    _text(design, "EVERYTHING IS FINE", 0.10, 0.815, 0.80, 0.04, 0.022,
          "#ff9a5c", "Subcaption", weight=700, spacing=0.36)
    return design


# --------------------------------------------------------------------------
# propaganda
# --------------------------------------------------------------------------
def prop_rise() -> Design:
    design = _new("Rise", "poster", {
        "kind": "linear", "color": "#8c1c14", "color2": "#2a0906",
        "angle": 100, "pattern": "diagonal", "pattern_color": "#f5d6a8",
        "pattern_opacity": 0.05, "pattern_scale": 0.4, "vignette": 0.45,
    })
    _shape(design, "stripe_diag", -0.25, 0.42, 1.50, 0.18, "#f0dcc0",
           "Stripe", rotation=0)
    _shape(design, "star12", 0.30, 0.075, 0.40, 0.22, "#f5c451",
           "Star", gradient=True, fill2="#b8791f", angle=90)
    _text(design, "RISE", 0.07, 0.29, 0.86, 0.19, 0.14, "#f9f1e2",
          "Headline", weight=800, spacing=0.14)
    _text(design, "TOGETHER", 0.08, 0.49, 0.84, 0.09, 0.062, "#2a0906",
          "Banner text", weight=800, spacing=0.28)
    _text(design, "THE FORGE IS OURS", 0.10, 0.70, 0.80, 0.05, 0.026,
          "#f5d6a8", "Kicker", weight=700, spacing=0.34)
    _text(design, "ONE HAND  \u00b7  ONE HAMMER", 0.10, 0.885, 0.80, 0.035,
          0.016, "#d8a98a", "Footer", weight=600, spacing=0.3)
    return design


def prop_unite() -> Design:
    design = _new("Unite", "poster", {
        "kind": "solid", "color": "#101418",
        "pattern": "grid", "pattern_color": "#e8d6b0",
        "pattern_opacity": 0.04, "pattern_scale": 0.8, "vignette": 0.5,
    })
    gear = _icon(design, "gear", 0.13, 0.10, 0.38, "#d94a32", "Gear")
    _glow(gear, "#ff7a3d", 0.03, 0.45)
    _icon(design, "users", 0.51, 0.13, 0.34, "#e8d6b0", "People")
    _text(design, "UNITE", 0.05, 0.45, 0.90, 0.17, 0.145, "#f6ecd8",
          "Headline", weight=800, spacing=0.14)
    _shape(design, "square", 0.10, 0.645, 0.80, 0.004, "#d94a32", "Rule")
    _text(design, "FORGE A COMMON FUTURE", 0.08, 0.69, 0.84, 0.07, 0.034,
          "#d9b46a", "Kicker", weight=700, spacing=0.36)
    _text(design, "SOLIDARITY  /  STRENGTH  /  STEEL", 0.08, 0.87, 0.84,
          0.03, 0.014, "#7f8a90", "Footer", weight=600, spacing=0.28)
    return design


def prop_victory() -> Design:
    design = _new("Victory Standard", "poster", {
        "kind": "radial", "color": "#3a2a12", "color2": "#0b0806",
        "pattern": "rays", "pattern_color": "#d9b46a",
        "pattern_opacity": 0.06, "pattern_scale": 0.8, "vignette": 0.55,
    })
    _icon(design, "laurel", 0.19, 0.10, 0.62, "#d9b46a", "Laurel",
          gradient=True, fill2="#8a5a1f", angle=110)
    _shape(design, "seal_star", 0.35, 0.22, 0.30, 0.20, "#8c1c14",
           "Seal", gradient=True, fill2="#4a0d09", angle=100,
           stroke="#f5c451", stroke_width=0.006)
    _icon(design, "star", 0.455, 0.275, 0.09, "#f5c451", "Star")
    _text(design, "VICTORY", 0.05, 0.52, 0.90, 0.13, 0.112, "#f9f1e2",
          "Headline", weight=800, spacing=0.16)
    _shape(design, "ribbon", 0.18, 0.665, 0.64, 0.10, "#8c1c14", "Ribbon",
           gradient=True, fill2="#5c110c", angle=90)
    _text(design, "FORWARD", 0.18, 0.682, 0.64, 0.07, 0.040, "#f5c451",
          "Ribbon text", weight=800, spacing=0.4)
    _text(design, "MMXXVI", 0.20, 0.83, 0.60, 0.04, 0.020, "#b08a4a",
          "Year", weight=700, spacing=0.5)
    return design


def prop_forward() -> Design:
    design = _new("Forward", "banner", {
        "kind": "linear", "color": "#0c2a3a", "color2": "#061018",
        "angle": 15, "pattern": "diagonal",
        "pattern_color": "#63e6ff", "pattern_opacity": 0.05,
        "pattern_scale": 0.5, "vignette": 0.4,
    })
    _text(design, "FORWARD", 0.05, 0.20, 0.60, 0.28, 0.215, "#f3f1f8",
          "Headline", weight=800, align="left", spacing=0.03)
    _shape(design, "arrow_right", 0.62, 0.20, 0.28, 0.20, "#63e6ff",
           "Arrow", gradient=True, fill2="#ff7a3d", angle=90)
    _text(design, "NEVER BACK", 0.06, 0.52, 0.56, 0.10, 0.045, "#ff8f5c",
          "Kicker", weight=700, align="left", spacing=0.3)
    _shape(design, "square", 0.06, 0.665, 0.34, 0.004, "#2b6f7d", "Rule")
    _text(design, "BUILD THE NEXT THING", 0.06, 0.70, 0.52, 0.05, 0.022,
          "#8ba3aa", "Note", weight=500, align="left", spacing=0.18)
    _text(design, "UMBRAFORGE", 0.62, 0.71, 0.32, 0.05, 0.024, "#7f9aa3",
          "Credit", weight=700, align="right", spacing=0.3)
    return design


def prop_warning() -> Design:
    design = _new("Attention", "poster", {
        "kind": "linear", "color": "#1c1a12", "color2": "#070604",
        "angle": 90, "pattern": "noise", "pattern_color": "#f5d166",
        "pattern_opacity": 0.06, "pattern_scale": 0.5, "vignette": 0.5,
    })
    _shape(design, "triangle", 0.16, 0.07, 0.68, 0.42, "#d9b42a",
           "Warning", gradient=True, fill2="#8a6f10", angle=100,
           stroke="#f5e6a8", stroke_width=0.006)
    _icon(design, "bolt", 0.435, 0.20, 0.13, "#1c1a12", "Bolt")
    _text(design, "ATTENTION", 0.05, 0.53, 0.90, 0.11, 0.092, "#f5e6a8",
          "Headline", weight=800, spacing=0.14)
    _shape(design, "square", 0.10, 0.655, 0.80, 0.005, "#d9b42a", "Rule")
    _text(design, "READ BEFORE YOU MARCH", 0.08, 0.70, 0.84, 0.06, 0.030,
          "#d9b42a", "Kicker", weight=700, spacing=0.32)
    _text(design, "NOTICE  /  PUBLIC  /  001", 0.08, 0.88, 0.84, 0.03,
          0.014, "#8a8060", "Footer", weight=600, spacing=0.3)
    return design


def prop_voice() -> Design:
    design = _new("Our Voice", "square", {
        "kind": "radial", "color": "#4a1010", "color2": "#08060a",
        "pattern": "rays", "pattern_color": "#ff8a3d",
        "pattern_opacity": 0.08, "pattern_scale": 0.8, "vignette": 0.55,
    })
    _icon(design, "signal", 0.24, 0.10, 0.52, "#ff8a3d", "Broadcast",
          gradient=True, fill2="#ffd166", angle=100)
    _glow(_icon(design, "signal", 0.36, 0.22, 0.28, "#fff1c9", "Core"),
          "#ff5a1f", 0.045, 0.6)
    _text(design, "OUR", 0.06, 0.56, 0.88, 0.09, 0.078, "#f3f1f8",
          "Word one", weight=800, spacing=0.24)
    _text(design, "VOICE", 0.06, 0.64, 0.88, 0.11, 0.098, "#ffd166",
          "Word two", weight=800, spacing=0.16)
    _shape(design, "square", 0.18, 0.79, 0.64, 0.004, "#7a2410", "Rule")
    _text(design, "LOUDER THAN FEAR", 0.12, 0.82, 0.76, 0.035, 0.018,
          "#d8a98a", "Footer", weight=700, spacing=0.34)
    return design


def prop_standard_bearer() -> Design:
    design = _new("Standard Bearer", "profile", {
        "kind": "linear", "color": "#17120a", "color2": "#060504",
        "angle": 120, "pattern": "rings", "pattern_color": "#d9b46a",
        "pattern_opacity": 0.06, "pattern_scale": 0.6, "vignette": 0.5,
    })
    _shape(design, "crest", 0.16, 0.10, 0.68, 0.62, "#241a0c",
           "Crest", gradient=True, fill2="#0c0906", angle=100,
           stroke="#d9b46a", stroke_width=0.008)
    _icon(design, "flag", 0.36, 0.19, 0.24, "#d9b46a", "Flag",
          gradient=True, fill2="#8a5a1f", angle=90)
    _glow(_icon(design, "star", 0.465, 0.44, 0.07, "#ffd166", "Star"),
          "#d9b46a", 0.02, 0.5)
    _text(design, "BEAR THE MARK", 0.06, 0.76, 0.88, 0.06, 0.038,
          "#f3f1f8", "Wordmark", weight=800, spacing=0.24)
    _text(design, "STEADY  \u00b7  PROUD  \u00b7  TRUE", 0.10, 0.845, 0.80,
          0.035, 0.016, "#b08a4a", "Footer", weight=600, spacing=0.34)
    return design


# --------------------------------------------------------------------------
# social + utility
# --------------------------------------------------------------------------
def sale_burst() -> Design:
    design = _new("Sale Burst", "square", {
        "kind": "radial", "color": "#ff5c39", "color2": "#7a1408",
        "pattern": "dots", "pattern_color": "#ffd166",
        "pattern_opacity": 0.08, "pattern_scale": 0.4, "vignette": 0.35,
    })
    _shape(design, "burst", 0.05, 0.06, 0.90, 0.62, "#ffd166", "Burst",
           gradient=True, fill2="#ff8a3d", angle=90)
    _text(design, "50%", 0.16, 0.16, 0.68, 0.22, 0.175, "#7a1408",
          "Number", weight=800, spacing=-0.01)
    _text(design, "OFF", 0.22, 0.36, 0.56, 0.10, 0.072, "#7a1408",
          "Off", weight=800, spacing=0.2)
    _text(design, "EVERYTHING", 0.08, 0.68, 0.84, 0.08, 0.056, "#fff4e0",
          "Headline", weight=800, spacing=0.12)
    _text(design, "THIS WEEK ONLY", 0.14, 0.80, 0.72, 0.04, 0.021,
          "#ffd166", "Kicker", weight=700, spacing=0.34)
    return design


def quote_card() -> Design:
    design = _new("Quote Card", "square", {
        "kind": "linear", "color": "#14121c", "color2": "#08070c",
        "angle": 125, "pattern": "noise", "pattern_color": "#ffffff",
        "pattern_opacity": 0.04, "pattern_scale": 0.4, "vignette": 0.4,
    })
    _text(design, "\u201c", 0.07, 0.03, 0.30, 0.22, 0.22, "#ff7a3d",
          "Mark", weight=800, align="left")
    _text(design, "Make the dark\nwork for you.", 0.10, 0.24, 0.80, 0.32,
          0.078, "#f3f1f8", "Quote", weight=700, align="left",
          spacing=0.01)
    _shape(design, "square", 0.10, 0.62, 0.14, 0.004, "#ff7a3d", "Rule")
    _text(design, "UMBRAFORGE STUDIO", 0.10, 0.66, 0.60, 0.05, 0.024,
          "#a397bd", "Credit", weight=700, align="left", spacing=0.3)
    return design


def launch_day() -> Design:
    design = _new("Launch Day", "story", {
        "kind": "radial", "color": "#1a1040", "color2": "#05030c",
        "pattern": "stars", "pattern_color": "#c4b5fd",
        "pattern_opacity": 0.18, "pattern_scale": 0.4, "vignette": 0.55,
    })
    rocket = _icon(design, "rocket", 0.27, 0.14, 0.46, "#a78bfa",
                   "Rocket", gradient=True, fill2="#ff7a3d", angle=105)
    _glow(rocket, "#8b5cf6", 0.05, 0.65)
    _text(design, "LAUNCH", 0.08, 0.55, 0.84, 0.12, 0.105, "#f3f1f8",
          "Headline", weight=800, spacing=0.16)
    _text(design, "DAY", 0.08, 0.655, 0.84, 0.09, 0.078, "#ff8f5c",
          "Second", weight=800, spacing=0.34)
    _text(design, "T-MINUS  ZERO", 0.14, 0.79, 0.72, 0.04, 0.020,
          "#a397bd", "Footer", weight=700, spacing=0.4)
    return design


def event_series() -> Design:
    design = _new("Event Series", "poster", {
        "kind": "linear", "color": "#0a1a24", "color2": "#04060a",
        "angle": 95, "pattern": "grid", "pattern_color": "#63e6ff",
        "pattern_opacity": 0.06, "pattern_scale": 0.6, "vignette": 0.45,
    })
    _shape(design, "square", 0.10, 0.10, 0.80, 0.004, "#63e6ff", "Top rule")
    _text(design, "SERIES", 0.10, 0.14, 0.80, 0.05, 0.028, "#63e6ff",
          "Kicker", weight=700, align="left", spacing=0.42)
    _text(design, "NIGHT\nSESSIONS", 0.10, 0.22, 0.78, 0.24, 0.10,
          "#f3f1f8", "Headline", weight=800, align="left")
    _text(design, "01", 0.10, 0.50, 0.36, 0.10, 0.075, "#ff7a3d",
          "Number", weight=800, align="left")
    _shape(design, "square", 0.10, 0.63, 0.80, 0.004, "#244552", "Rule")
    _text(design, "FRI 21:00  \u00b7  THE FORGE", 0.10, 0.67, 0.80, 0.05,
          0.024, "#a9c6d8", "Details", weight=600, align="left",
          spacing=0.2)
    _text(design, "FREE ENTRY  /  LIMITED SEATS", 0.10, 0.86, 0.80, 0.03,
          0.014, "#5f7a88", "Footer", weight=600, align="left",
          spacing=0.24)
    return design


def poll_card() -> Design:
    design = _new("Poll Card", "square", {
        "kind": "linear", "color": "#121018", "color2": "#08070c",
        "angle": 120, "pattern": "grid", "pattern_color": "#8b5cf6",
        "pattern_opacity": 0.04, "pattern_scale": 0.7, "vignette": 0.3,
    })
    _text(design, "WHICH ONE?", 0.08, 0.10, 0.84, 0.09, 0.058, "#f3f1f8",
          "Question", weight=800, spacing=0.1)
    _shape(design, "rounded", 0.08, 0.27, 0.84, 0.22, "#221a36",
           "Option A", gradient=True, fill2="#151022", angle=90,
           stroke="#8b5cf6", stroke_width=0.004)
    _text(design, "OPTION A", 0.12, 0.31, 0.60, 0.08, 0.042, "#c4b5fd",
          "A label", weight=800, align="left", spacing=0.16)
    _shape(design, "rounded", 0.08, 0.55, 0.84, 0.22, "#2a1a14",
           "Option B", gradient=True, fill2="#160e0c", angle=90,
           stroke="#ff7a3d", stroke_width=0.004)
    _text(design, "OPTION B", 0.12, 0.59, 0.60, 0.08, 0.042, "#ffb066",
          "B label", weight=800, align="left", spacing=0.16)
    _text(design, "VOTE IN THE COMMENTS", 0.10, 0.86, 0.80, 0.035, 0.016,
          "#7e7891", "Footer", weight=600, spacing=0.34)
    return design


def countdown() -> Design:
    design = _new("Countdown", "story", {
        "kind": "linear", "color": "#1e0e36", "color2": "#050409",
        "angle": 100, "pattern": "rings", "pattern_color": "#ff7a3d",
        "pattern_opacity": 0.07, "pattern_scale": 0.7, "vignette": 0.5,
    })
    _text(design, "03", 0.10, 0.20, 0.80, 0.34, 0.30, "#f3f1f8",
          "Number", weight=800, spacing=-0.02)
    _text(design, "DAYS", 0.16, 0.55, 0.68, 0.08, 0.052, "#ff7a3d",
          "Unit", weight=800, spacing=0.5)
    _shape(design, "square", 0.22, 0.67, 0.56, 0.004, "#4b3a68", "Rule")
    _text(design, "UNTIL THE DROP", 0.14, 0.71, 0.72, 0.05, 0.026,
          "#c4b5fd", "Kicker", weight=700, spacing=0.34)
    _text(design, "SET A REMINDER", 0.18, 0.87, 0.64, 0.03, 0.015,
          "#8378a3", "Footer", weight=600, spacing=0.3)
    return design


def team_intro() -> Design:
    design = _new("Team Intro", "square", {
        "kind": "linear", "color": "#0e1218", "color2": "#06080b",
        "angle": 130, "pattern": "grid", "pattern_color": "#63e6ff",
        "pattern_opacity": 0.04, "pattern_scale": 0.7, "vignette": 0.4,
    })
    _text(design, "THE CREW", 0.08, 0.09, 0.84, 0.08, 0.052, "#f3f1f8",
          "Title", weight=800, spacing=0.14)
    names = ["NOVA", "ASH", "WREN", "KAI"]
    for index, name in enumerate(names):
        x = 0.09 + (index % 2) * 0.44
        y = 0.23 + (index // 2) * 0.29
        _shape(design, "circle", x, y, 0.26, 0.14, "#1c2430",
               f"Plate {index + 1}", gradient=True, fill2="#10151c",
               angle=90, stroke="#2f3b4a", stroke_width=0.004)
        _icon(design, "user", x + 0.085, y + 0.028, 0.09,
              ["#63e6ff", "#ff8f5c", "#a78bfa", "#5cf2c7"][index],
              f"Avatar {index + 1}")
        _text(design, name, x + 0.02, y + 0.17, 0.22, 0.04, 0.022,
              "#d8e2ea", f"Name {index + 1}", weight=700, spacing=0.2)
    _text(design, "BUILT IN THE DARK", 0.10, 0.89, 0.80, 0.03, 0.014,
          "#6d7d8a", "Footer", weight=600, spacing=0.32)
    return design


def link_bio() -> Design:
    design = _new("Link In Bio", "story", {
        "kind": "radial", "color": "#2a1648", "color2": "#07050c",
        "pattern": "stars", "pattern_color": "#c4b5fd",
        "pattern_opacity": 0.16, "pattern_scale": 0.4, "vignette": 0.5,
    })
    _shape(design, "circle", 0.35, 0.08, 0.30, 0.17, "#211632",
           "Avatar", gradient=True, fill2="#0d0916", angle=100,
           stroke="#8b5cf6", stroke_width=0.006)
    _text(design, "U", 0.35, 0.10, 0.30, 0.13, 0.09, "#c4b5fd",
          "Mark", weight=800)
    _text(design, "@UMBRAFORGE", 0.12, 0.29, 0.76, 0.06, 0.036, "#f3f1f8",
          "Handle", weight=800, spacing=0.14)
    _text(design, "dark design tools", 0.14, 0.35, 0.72, 0.04, 0.021,
          "#9a8fb8", "Bio", weight=500, spacing=0.08)
    links = [("PORTFOLIO", "#ff7a3d"), ("NEW DROP", "#8b5cf6"),
             ("NEWSLETTER", "#22d3ee")]
    for index, (label, color) in enumerate(links):
        top = 0.44 + index * 0.13
        _shape(design, "rounded", 0.12, top, 0.76, 0.095, "#171022",
               f"Link {index + 1}", gradient=True, fill2="#0d0914",
               angle=90, stroke=color, stroke_width=0.004)
        _text(design, label, 0.15, top + 0.025, 0.60, 0.045, 0.024,
              color, f"Link text {index + 1}", weight=700, align="left",
              spacing=0.24)
        _icon(design, "forward", 0.77, top + 0.026, 0.045, color,
              f"Arrow {index + 1}")
    _text(design, "UMBRAFORGE.STUDIO", 0.18, 0.88, 0.64, 0.03, 0.014,
          "#8378a3", "Footer", weight=600, spacing=0.3)
    return design


def milestone() -> Design:
    design = _new("Milestone", "square", {
        "kind": "radial", "color": "#3a2a12", "color2": "#08060a",
        "pattern": "rays", "pattern_color": "#d9b46a",
        "pattern_opacity": 0.07, "pattern_scale": 0.8, "vignette": 0.5,
    })
    _shape(design, "star12", 0.14, 0.10, 0.72, 0.50, "#d9b46a",
           "Star", gradient=True, fill2="#8a5a1f", angle=100)
    _glow(_shape(design, "star12", 0.20, 0.155, 0.60, 0.39, "#2a1e0c",
                 "Star inner", gradient=True, fill2="#140f08", angle=100),
          "#d9b46a", 0.02, 0.4)
    _text(design, "10K", 0.20, 0.24, 0.60, 0.16, 0.13, "#ffd166",
          "Number", weight=800, spacing=-0.01)
    _text(design, "THANK YOU", 0.08, 0.67, 0.84, 0.09, 0.062, "#f3f1f8",
          "Headline", weight=800, spacing=0.16)
    _text(design, "FOR EVERY SIGNAL", 0.14, 0.78, 0.72, 0.04, 0.021,
          "#b08a4a", "Kicker", weight=700, spacing=0.36)
    return design


def product_drop() -> Design:
    design = _new("Product Drop", "square", {
        "kind": "linear", "color": "#101c16", "color2": "#050806",
        "angle": 110, "pattern": "hexagons", "pattern_color": "#7ef0b0",
        "pattern_opacity": 0.06, "pattern_scale": 0.7, "vignette": 0.45,
    })
    _shape(design, "capsule", 0.27, 0.13, 0.46, 0.34, "#7ef0b0",
           "Product", gradient=True, fill2="#1f7a4a", angle=110)
    _glow(_icon(design, "bolt", 0.425, 0.22, 0.15, "#04110b", "Mark"),
          "#4ade80", 0.03, 0.5)
    _text(design, "THE DROP", 0.06, 0.54, 0.88, 0.10, 0.082, "#f3f1f8",
          "Headline", weight=800, spacing=0.14)
    _shape(design, "square", 0.12, 0.67, 0.76, 0.004, "#2f6b4a", "Rule")
    _text(design, "LIMITED RUN  \u00b7  NO RESTOCK", 0.10, 0.71, 0.80,
          0.04, 0.020, "#9fe6b0", "Kicker", weight=700, spacing=0.3)
    _text(design, "AVAILABLE FRIDAY", 0.16, 0.86, 0.68, 0.03, 0.015,
          "#6d8b78", "Footer", weight=600, spacing=0.34)
    return design


def minimal_caption() -> Design:
    design = _new("Minimal Caption", "story", {
        "kind": "linear", "color": "#14121a", "color2": "#050508",
        "angle": 160, "pattern": "noise", "pattern_color": "#ffffff",
        "pattern_opacity": 0.03, "pattern_scale": 0.4, "vignette": 0.45,
    })
    _shape(design, "circle", 0.16, 0.16, 0.68, 0.68, "#1e1a28", "Field")
    _icon(design, "eye", 0.36, 0.31, 0.28, "#4b4268", "Mark")
    _text(design, "say less.", 0.10, 0.62, 0.80, 0.14, 0.095, "#f3f1f8",
          "Headline", weight=700, align="left", spacing=0.01)
    _text(design, "UMBRAFORGE", 0.10, 0.82, 0.60, 0.04, 0.019, "#7e7891",
          "Credit", weight=700, align="left", spacing=0.36)
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
    Template("laurel_standard", "Laurel Standard", "Gold laurel and star.",
             "Profile", laurel_standard),
    Template("prop_standard_bearer", "Standard Bearer",
             "A crest and flag for a profile.", "Profile",
             prop_standard_bearer),
    Template("static_skull", "Static Skull", "Grainy, loud and monochrome.",
             "Square", static_skull),
    Template("forge_mark", "Forge Mark", "A clean monogram plate.",
             "Square", forge_mark),
    Template("sale_burst", "Sale Burst", "A starburst for a loud discount.",
             "Social", sale_burst),
    Template("quote_card", "Quote Card", "Minimal type with a big quote mark.",
             "Social", quote_card),
    Template("poll_card", "Poll Card", "Two options, ready for a vote.",
             "Social", poll_card),
    Template("team_intro", "Team Intro", "Four crew cards on a dark grid.",
             "Social", team_intro),
    Template("milestone", "Milestone", "A gold star for a follower milestone.",
             "Social", milestone),
    Template("product_drop", "Product Drop", "A capsule launch card.",
             "Social", product_drop),
    Template("chrome_standard", "Chrome Standard", "A wide WinterGate banner.",
             "Banner", chrome_standard),
    Template("prop_forward", "Forward", "A wide directional banner.",
             "Banner", prop_forward),
    Template("long_night", "The Long Night", "A minimal two-colour poster.",
             "Poster", long_night),
    Template("prop_rise", "Rise", "Constructivist diagonals and a gold star.",
             "Propaganda", prop_rise),
    Template("prop_unite", "Unite", "Gear and people in a bold poster.",
             "Propaganda", prop_unite),
    Template("prop_victory", "Victory Standard",
             "Laurel, seal and ribbon in gold and red.", "Propaganda",
             prop_victory),
    Template("prop_warning", "Attention", "A warning triangle public notice.",
             "Propaganda", prop_warning),
    Template("prop_voice", "Our Voice", "A broadcast signal in hot orange.",
             "Propaganda", prop_voice),
    Template("event_series", "Event Series", "A numbered night-session poster.",
             "Event", event_series),
    Template("countdown", "Countdown", "Three days and counting.",
             "Event", countdown),
    Template("launch_day", "Launch Day", "A vertical launch announcement.",
             "Event", launch_day),
    Template("link_bio", "Link In Bio", "Three link buttons for a story.",
             "Event", link_bio),
    Template("meme_top_bottom", "Top / Bottom Meme",
             "Classic caption bars over a photo panel.", "Meme",
             meme_top_bottom),
    Template("meme_drake", "No / Yes Meme", "The two-panel choice format.",
             "Meme", meme_drake),
    Template("meme_brain", "Expanding Brain", "Four rows of escalating ideas.",
             "Meme", meme_brain),
    Template("meme_deep_fried", "Deep Fried", "Maximum saturation and glow.",
             "Meme", meme_deep_fried),
    Template("meme_galaxy", "Galaxy Brain", "Cosmic orbit and glowing type.",
             "Meme", meme_galaxy),
    Template("meme_this_is_fine", "This Is Fine",
             "A calm caption over a burning room.", "Meme",
             meme_this_is_fine),
    Template("minimal_caption", "Minimal Caption",
             "A quiet vertical type card.", "Mobile", minimal_caption),
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
