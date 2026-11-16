"""Canvas-wide overlays.

Unlike layer effects, an overlay sits above the whole composition: grain,
light leaks, halftone screens, CRT scanlines, frames and so on. They are stored
as ordinary ``design.overlays`` values (merged against defaults), render live in
the Canvas, stay editable in the Canvas tab and serialize into ``.umbra``
projects. A disabled stack is a pixel-identical no-op.
"""

from __future__ import annotations

import copy
import io
import math
import random
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageColor, ImageDraw, ImageFilter

# --------------------------------------------------------------------------
# primitives
# --------------------------------------------------------------------------
OVERLAY_DEFAULTS: dict[str, dict] = {
    "smoke": {"enabled": False, "opacity": 0.3, "color": "#8b5cf6",
              "scale": 0.6},
    "light_leak": {"enabled": False, "opacity": 0.45, "color": "#ff8a3d",
                   "angle": 35.0, "size": 0.55},
    "bokeh": {"enabled": False, "opacity": 0.45, "color": "#ffd9a8",
              "count": 20, "size": 0.11},
    "lens_flare": {"enabled": False, "opacity": 0.55, "color": "#ffd9a8",
                   "x": 0.72, "y": 0.24, "size": 0.3},
    "holo": {"enabled": False, "opacity": 0.32, "angle": 24.0},
    "rainbow": {"enabled": False, "opacity": 0.26, "angle": 28.0},
    "rain": {"enabled": False, "opacity": 0.35, "color": "#bfe9ff",
             "count": 130, "angle": 14.0, "size": 0.5},
    "snow": {"enabled": False, "opacity": 0.6, "color": "#ffffff",
             "count": 170, "size": 0.4},
    "embers": {"enabled": False, "opacity": 0.55, "color": "#ff8a3d",
               "count": 80, "size": 0.45},
    "sparkle": {"enabled": False, "opacity": 0.5, "color": "#fff1c9",
                "count": 70, "size": 0.4},
    "dust": {"enabled": False, "opacity": 0.35, "color": "#ffffff",
             "count": 150, "size": 0.3},
    "confetti": {"enabled": False, "opacity": 0.75, "count": 90,
                 "size": 0.5},
    "frost": {"enabled": False, "opacity": 0.4, "color": "#dff6ff",
              "scale": 0.6},
    "halftone": {"enabled": False, "opacity": 0.35, "color": "#0b0813",
                 "scale": 0.5, "angle": 12.0},
    "grid": {"enabled": False, "opacity": 0.18, "color": "#7ae7ff",
             "scale": 0.5},
    "pixel_grid": {"enabled": False, "opacity": 0.16, "color": "#000000",
                   "scale": 0.5},
    "scanlines": {"enabled": False, "opacity": 0.2, "color": "#000000",
                  "spacing": 0.006},
    "vhs": {"enabled": False, "opacity": 0.4, "color": "#63e6ff"},
    "frame": {"enabled": False, "opacity": 0.65, "color": "#ffffff",
              "width": 0.004, "inset": 0.035},
    "corner_marks": {"enabled": False, "opacity": 0.55, "color": "#ffffff",
                     "size": 0.05, "inset": 0.04},
    "paper": {"enabled": False, "opacity": 0.35, "color": "#f2e6d0",
              "scale": 0.5},
    "grain": {"enabled": False, "opacity": 0.18, "color": "#ffffff",
              "size": 0.5},
    "vignette": {"enabled": False, "opacity": 0.45, "color": "#000000"},
}

OVERLAY_LABELS: dict[str, str] = {
    "smoke": "Smoke",
    "light_leak": "Light leak",
    "bokeh": "Bokeh",
    "lens_flare": "Lens flare",
    "holo": "Holo sheen",
    "rainbow": "Prism wash",
    "rain": "Rain",
    "snow": "Snow",
    "embers": "Embers",
    "sparkle": "Sparkle",
    "dust": "Dust",
    "confetti": "Confetti",
    "frost": "Frost",
    "halftone": "Halftone",
    "grid": "Grid",
    "pixel_grid": "Pixel grid",
    "scanlines": "Scanlines",
    "vhs": "VHS bars",
    "frame": "Frame",
    "corner_marks": "Corner marks",
    "paper": "Paper",
    "grain": "Grain",
    "vignette": "Vignette",
}

#: Painter order. Later items sit on top.
_ORDER = (
    "smoke", "light_leak", "bokeh", "lens_flare", "holo", "rainbow",
    "rain", "snow", "embers", "sparkle", "dust", "confetti", "frost",
    "halftone", "grid", "pixel_grid", "scanlines", "vhs", "paper",
    "frame", "corner_marks", "grain", "vignette",
)


def default_stack() -> dict:
    stack = copy.deepcopy(OVERLAY_DEFAULTS)
    stack["preset"] = ""
    return stack


def enabled(settings: dict | None, name: str) -> bool:
    entry = (settings or {}).get(name) or {}
    return bool(entry.get("enabled"))


def any_enabled(settings: dict | None) -> bool:
    return any(enabled(settings, key) for key in OVERLAY_DEFAULTS)


def active_names(settings: dict | None) -> list[str]:
    return [OVERLAY_LABELS.get(key, key.title())
            for key in OVERLAY_DEFAULTS if enabled(settings, key)]


def _number(entry: dict, key: str, default: float) -> float:
    try:
        return float(entry.get(key, default))
    except (TypeError, ValueError):
        return float(default)


def _opacity(entry: dict, default: float = 0.5) -> float:
    return max(0.0, min(1.0, _number(entry, "opacity", default)))


def _rgb(text: str) -> tuple[int, int, int]:
    try:
        return ImageColor.getrgb(text)[:3]
    except (ValueError, AttributeError):
        return (255, 255, 255)


def _empty(width: int, height: int) -> Image.Image:
    return Image.new("RGBA", (width, height), (0, 0, 0, 0))


def _work_size(width: int, height: int, cap: int = 1500) -> tuple[int, int]:
    scale = min(1.0, cap / max(1, width, height))
    return max(1, int(width * scale)), max(1, int(height * scale))


def _rgba_array(rgb: tuple[int, int, int],
                alpha: np.ndarray) -> Image.Image:
    height, width = alpha.shape
    array = np.empty((height, width, 4), dtype=np.uint8)
    array[..., 0] = rgb[0]
    array[..., 1] = rgb[1]
    array[..., 2] = rgb[2]
    array[..., 3] = np.clip(alpha, 0, 255).astype(np.uint8)
    return Image.fromarray(array, "RGBA")


# --------------------------------------------------------------------------
# generators
# --------------------------------------------------------------------------
def _smoke(width: int, height: int, entry: dict) -> Image.Image:
    scale = max(0.1, _number(entry, "scale", 0.6))
    small = (max(6, int(width * 0.12 / scale)),
             max(6, int(height * 0.12 / scale)))
    rng = np.random.default_rng(21)
    noise = rng.integers(0, 256, (small[1], small[0]), dtype=np.uint8)
    cloud = Image.fromarray(noise, "L").resize((width, height),
                                               Image.Resampling.BICUBIC)
    cloud = cloud.filter(ImageFilter.GaussianBlur(max(2.0, min(width, height)
                                                      * 0.02)))
    alpha = np.asarray(cloud, dtype=np.float32) / 255.0
    alpha = alpha ** 1.6 * _opacity(entry, 0.3) * 255
    return _rgba_array(_rgb(entry.get("color", "#8b5cf6")), alpha)


def _light_leak(width: int, height: int, entry: dict) -> Image.Image:
    opacity = _opacity(entry, 0.45)
    angle = math.radians(_number(entry, "angle", 35.0))
    size = max(0.1, _number(entry, "size", 0.55))
    yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)
    nx = (xx / max(1, width - 1)) * 2 - 1
    ny = (yy / max(1, height - 1)) * 2 - 1
    projection = nx * math.cos(angle) + ny * math.sin(angle)
    band = np.exp(-((projection - 0.35) / size) ** 2)
    far = np.exp(-((projection + 0.7) / (size * 0.5)) ** 2) * 0.45
    alpha = np.clip(band + far, 0, 1) * opacity * 255
    return _rgba_array(_rgb(entry.get("color", "#ff8a3d")), alpha)


def _bokeh(width: int, height: int, entry: dict) -> Image.Image:
    opacity = _opacity(entry, 0.45)
    count = max(1, int(_number(entry, "count", 20)))
    size = max(0.02, _number(entry, "size", 0.11))
    shortest = min(width, height)
    rng = random.Random(9)
    layer = _empty(width, height)
    draw = ImageDraw.Draw(layer)
    color = _rgb(entry.get("color", "#ffd9a8"))
    for _ in range(count):
        radius = shortest * size * (0.25 + rng.random() * 0.75)
        cx = rng.uniform(-0.05, 1.05) * width
        cy = rng.uniform(-0.05, 1.05) * height
        alpha = int(255 * opacity * (0.18 + rng.random() * 0.35))
        draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius),
                     fill=color + (alpha,))
    return layer.filter(ImageFilter.GaussianBlur(shortest * 0.012))


def _lens_flare(width: int, height: int, entry: dict) -> Image.Image:
    opacity = _opacity(entry, 0.55)
    shortest = min(width, height)
    cx = _number(entry, "x", 0.72) * width
    cy = _number(entry, "y", 0.24) * height
    size = max(0.05, _number(entry, "size", 0.3)) * shortest
    yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)
    dx = xx - cx
    dy = yy - cy
    core = np.exp(-(dx * dx + dy * dy) / (size * size))
    streak = np.exp(-(dy * dy) / (size * size * 0.02))
    streak *= np.exp(-(dx * dx) / (size * size * 9.0))
    halo = np.exp(-(dx * dx + dy * dy) / (size * size * 12.0)) * 0.4
    alpha = np.clip(core + streak * 0.8 + halo, 0, 1) * opacity * 255
    return _rgba_array(_rgb(entry.get("color", "#ffd9a8")), alpha)


def _palette_bands(width: int, height: int, entry: dict, cycles: float,
                   palette: list[str], opacity: float) -> Image.Image:
    angle = math.radians(_number(entry, "angle", 24.0))
    yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)
    nx = xx / max(1, width - 1)
    ny = yy / max(1, height - 1)
    t = (nx * math.cos(angle) + ny * math.sin(angle)) * cycles
    t = t - np.floor(t)
    stops = np.linspace(0.0, 1.0, len(palette))
    positions = np.concatenate((stops, [1.0 + 1e-6]))
    colors = [_rgb(value) for value in palette]
    colours = colors + [colors[-1]]
    alpha = np.full((height, width), opacity * 255.0, dtype=np.float32)
    channels = []
    for index in range(3):
        values = [colour[index] for colour in colours]
        channels.append(np.interp(t, positions, values))
    array = np.empty((height, width, 4), dtype=np.uint8)
    for index in range(3):
        array[..., index] = np.clip(channels[index], 0, 255).astype(np.uint8)
    array[..., 3] = np.clip(alpha, 0, 255).astype(np.uint8)
    return Image.fromarray(array, "RGBA").filter(
        ImageFilter.GaussianBlur(max(0.6, min(width, height) * 0.004)))


def _holo(width: int, height: int, entry: dict) -> Image.Image:
    return _palette_bands(
        width, height, entry, 2.2,
        ["#ff5cd6", "#ffd166", "#7ae7ff", "#a78bfa", "#ff8a3d",
         "#5cf2c7", "#ff5cd6"],
        _opacity(entry, 0.32))


def _rainbow(width: int, height: int, entry: dict) -> Image.Image:
    return _palette_bands(
        width, height, entry, 1.0,
        ["#ff3b30", "#ff9500", "#ffd60a", "#34c759", "#32ade6",
         "#5856d6", "#af52de", "#ff2d55", "#ff3b30"],
        _opacity(entry, 0.26))


def _rain(width: int, height: int, entry: dict) -> Image.Image:
    opacity = _opacity(entry, 0.35)
    count = max(1, int(_number(entry, "count", 130)))
    angle = math.radians(_number(entry, "angle", 14.0))
    shortest = min(width, height)
    length = shortest * 0.05 * max(0.2, _number(entry, "size", 0.5))
    rng = random.Random(12)
    layer = _empty(width, height)
    draw = ImageDraw.Draw(layer)
    color = _rgb(entry.get("color", "#bfe9ff"))
    for _ in range(count):
        x = rng.uniform(-0.1, 1.1) * width
        y = rng.uniform(-0.1, 1.1) * height
        dx = math.sin(angle) * length
        dy = math.cos(angle) * length
        draw.line((x, y, x + dx, y + dy),
                  fill=color + (int(255 * opacity * 0.7),),
                  width=max(1, int(shortest * 0.0015)))
    return layer


def _snow(width: int, height: int, entry: dict) -> Image.Image:
    opacity = _opacity(entry, 0.6)
    count = max(1, int(_number(entry, "count", 170)))
    size = max(0.1, _number(entry, "size", 0.4))
    shortest = min(width, height)
    rng = random.Random(13)
    layer = _empty(width, height)
    draw = ImageDraw.Draw(layer)
    color = _rgb(entry.get("color", "#ffffff"))
    for _ in range(count):
        radius = shortest * 0.0025 * size * (0.5 + rng.random() * 2.0)
        x = rng.uniform(0, width)
        y = rng.uniform(0, height)
        draw.ellipse((x - radius, y - radius, x + radius, y + radius),
                     fill=color + (int(255 * opacity * (0.4 + rng.random() * 0.6)),))
    return layer


def _embers(width: int, height: int, entry: dict) -> Image.Image:
    opacity = _opacity(entry, 0.55)
    count = max(1, int(_number(entry, "count", 80)))
    size = max(0.1, _number(entry, "size", 0.45))
    shortest = min(width, height)
    rng = random.Random(14)
    dots = _empty(width, height)
    draw = ImageDraw.Draw(dots)
    color = _rgb(entry.get("color", "#ff8a3d"))
    for _ in range(count):
        radius = shortest * 0.0022 * size * (0.6 + rng.random() * 2.4)
        x = rng.uniform(0, width)
        y = rng.uniform(0, height)
        draw.ellipse((x - radius, y - radius, x + radius, y + radius),
                     fill=color + (int(255 * opacity * (0.35 + rng.random() * 0.65)),))
    glow = dots.filter(ImageFilter.GaussianBlur(shortest * 0.012))
    return Image.alpha_composite(glow, dots)


def _sparkle(width: int, height: int, entry: dict) -> Image.Image:
    opacity = _opacity(entry, 0.5)
    count = max(1, int(_number(entry, "count", 70)))
    size = max(0.1, _number(entry, "size", 0.4))
    shortest = min(width, height)
    rng = random.Random(15)
    layer = _empty(width, height)
    draw = ImageDraw.Draw(layer)
    color = _rgb(entry.get("color", "#fff1c9"))
    for _ in range(count):
        radius = shortest * 0.006 * size * (0.4 + rng.random() * 1.6)
        x = rng.uniform(0, width)
        y = rng.uniform(0, height)
        alpha = int(255 * opacity * (0.4 + rng.random() * 0.6))
        draw.polygon([(x, y - radius), (x + radius * 0.18, y - radius * 0.18),
                      (x + radius, y), (x + radius * 0.18, y + radius * 0.18),
                      (x, y + radius), (x - radius * 0.18, y + radius * 0.18),
                      (x - radius, y), (x - radius * 0.18, y - radius * 0.18)],
                     fill=color + (alpha,))
    glow = layer.filter(ImageFilter.GaussianBlur(shortest * 0.008))
    return Image.alpha_composite(glow, layer)


def _dust(width: int, height: int, entry: dict) -> Image.Image:
    opacity = _opacity(entry, 0.35)
    count = max(1, int(_number(entry, "count", 150)))
    size = max(0.1, _number(entry, "size", 0.3))
    shortest = min(width, height)
    rng = random.Random(16)
    layer = _empty(width, height)
    draw = ImageDraw.Draw(layer)
    color = _rgb(entry.get("color", "#ffffff"))
    for _ in range(count):
        radius = max(0.5, shortest * 0.0016 * size * (0.4 + rng.random() * 1.8))
        x = rng.uniform(0, width)
        y = rng.uniform(0, height)
        draw.ellipse((x - radius, y - radius, x + radius, y + radius),
                     fill=color + (int(255 * opacity * (0.2 + rng.random() * 0.6)),))
    return layer


def _confetti(width: int, height: int, entry: dict) -> Image.Image:
    opacity = _opacity(entry, 0.75)
    count = max(1, int(_number(entry, "count", 90)))
    size = max(0.1, _number(entry, "size", 0.5))
    shortest = min(width, height)
    rng = random.Random(17)
    layer = _empty(width, height)
    draw = ImageDraw.Draw(layer)
    palette = ["#ff5c39", "#ffd166", "#4ade80", "#63b3ff", "#ff5cd6",
               "#a78bfa", "#5cf2c7"]
    for _ in range(count):
        w = shortest * 0.012 * size * (0.6 + rng.random())
        h = w * (0.4 + rng.random() * 0.9)
        x = rng.uniform(0, width)
        y = rng.uniform(0, height)
        angle = rng.uniform(0, math.tau)
        points = []
        for dx, dy in ((-w / 2, -h / 2), (w / 2, -h / 2),
                       (w / 2, h / 2), (-w / 2, h / 2)):
            points.append((x + dx * math.cos(angle) - dy * math.sin(angle),
                           y + dx * math.sin(angle) + dy * math.cos(angle)))
        colour = _rgb(rng.choice(palette))
        draw.polygon(points, fill=colour + (int(255 * opacity),))
    return layer


def _frost(width: int, height: int, entry: dict) -> Image.Image:
    opacity = _opacity(entry, 0.4)
    scale = max(0.1, _number(entry, "scale", 0.6))
    shortest = min(width, height)
    rng = random.Random(18)
    layer = _empty(width, height)
    draw = ImageDraw.Draw(layer)
    color = _rgb(entry.get("color", "#dff6ff"))
    for _ in range(int(26 * scale) + 8):
        x = rng.choice([0, width, rng.uniform(0, width)])
        y = rng.choice([0, height, rng.uniform(0, height)])
        angle = rng.uniform(0, math.tau)
        for _ in range(rng.randint(3, 8)):
            length = shortest * 0.02 * (0.4 + rng.random())
            nx = x + math.cos(angle) * length
            ny = y + math.sin(angle) * length
            draw.line((x, y, nx, ny),
                      fill=color + (int(255 * opacity * 0.6),),
                      width=max(1, int(shortest * 0.0012)))
            x, y = nx, ny
            angle += rng.uniform(-0.8, 0.8)
    return layer.filter(ImageFilter.GaussianBlur(0.6))


def _halftone(width: int, height: int, entry: dict) -> Image.Image:
    opacity = _opacity(entry, 0.35)
    scale = max(0.1, _number(entry, "scale", 0.5))
    spacing = max(4.0, min(width, height) * 0.012 * scale)
    layer = _empty(width, height)
    draw = ImageDraw.Draw(layer)
    color = _rgb(entry.get("color", "#0b0813"))
    y = 0.0
    row = 0
    while y < height + spacing:
        x = spacing * 0.5 if row % 2 else 0.0
        while x < width + spacing:
            t = 0.25 + 0.75 * (y / max(1, height))
            radius = spacing * 0.34 * t
            draw.ellipse((x - radius, y - radius, x + radius, y + radius),
                         fill=color + (int(255 * opacity),))
            x += spacing
        y += spacing * 0.87
        row += 1
    return layer


def _grid(width: int, height: int, entry: dict) -> Image.Image:
    opacity = _opacity(entry, 0.18)
    scale = max(0.1, _number(entry, "scale", 0.5))
    spacing = max(8.0, min(width, height) * 0.05 * (scale / 0.5))
    layer = _empty(width, height)
    draw = ImageDraw.Draw(layer)
    color = _rgb(entry.get("color", "#7ae7ff"))
    width_px = max(1, int(min(width, height) * 0.0012))
    y = 0.0
    while y <= height:
        draw.line((0, y, width, y), fill=color + (int(255 * opacity),),
                  width=width_px)
        y += spacing
    x = 0.0
    while x <= width:
        draw.line((x, 0, x, height), fill=color + (int(255 * opacity),),
                  width=width_px)
        x += spacing
    return layer


def _pixel_grid(width: int, height: int, entry: dict) -> Image.Image:
    opacity = _opacity(entry, 0.16)
    scale = max(0.1, _number(entry, "scale", 0.5))
    spacing = max(4.0, min(width, height) * 0.012 * (scale / 0.5))
    layer = _empty(width, height)
    draw = ImageDraw.Draw(layer)
    color = _rgb(entry.get("color", "#000000"))
    width_px = max(1, int(spacing * 0.16))
    y = 0.0
    while y <= height:
        draw.line((0, y, width, y), fill=color + (int(255 * opacity),),
                  width=width_px)
        y += spacing
    x = 0.0
    while x <= width:
        draw.line((x, 0, x, height), fill=color + (int(255 * opacity),),
                  width=width_px)
        x += spacing
    return layer


def _scanlines(width: int, height: int, entry: dict) -> Image.Image:
    opacity = _opacity(entry, 0.2)
    spacing = max(3.0, min(width, height) * _number(entry, "spacing", 0.006))
    layer = _empty(width, height)
    draw = ImageDraw.Draw(layer)
    color = _rgb(entry.get("color", "#000000"))
    y = 0.0
    while y < height:
        draw.line((0, y, width, y),
                  fill=color + (int(255 * opacity),),
                  width=max(1, int(spacing * 0.4)))
        y += spacing
    return layer


def _vhs(width: int, height: int, entry: dict) -> Image.Image:
    opacity = _opacity(entry, 0.4)
    rng = random.Random(19)
    layer = _empty(width, height)
    draw = ImageDraw.Draw(layer)
    for _ in range(9):
        top = rng.uniform(0, height)
        band = rng.uniform(0.004, 0.02) * height
        alpha = int(255 * opacity * rng.uniform(0.2, 0.55))
        draw.rectangle((0, top, width, top + band),
                       fill=_rgb("#ffffff") + (alpha,))
    for _ in range(3):
        top = rng.uniform(0, height)
        band = rng.uniform(0.006, 0.03) * height
        colour = _rgb(rng.choice(["#63e6ff", "#ff5cd6", "#ffd166"]))
        draw.rectangle((0, top, width, top + band),
                       fill=colour + (int(255 * opacity * 0.5),))
    return layer.filter(ImageFilter.GaussianBlur(0.5))


def _paper(width: int, height: int, entry: dict) -> Image.Image:
    opacity = _opacity(entry, 0.35)
    scale = max(0.1, _number(entry, "scale", 0.5))
    cell = max(24, int(60 * scale))
    rng = np.random.default_rng(22)
    tile = rng.integers(0, 256, (cell, cell), dtype=np.uint8)
    array = np.tile(tile, (height // cell + 1, width // cell + 1))[:height, :width]
    alpha = (array.astype(np.float32) / 255.0) * opacity * 255 * 0.5
    rgb = _rgb(entry.get("color", "#f2e6d0"))
    return _rgba_array(rgb, alpha)


def _frame(width: int, height: int, entry: dict) -> Image.Image:
    opacity = _opacity(entry, 0.65)
    inset = _number(entry, "inset", 0.035) * min(width, height)
    width_px = max(1.0, _number(entry, "width", 0.004) * min(width, height))
    layer = _empty(width, height)
    draw = ImageDraw.Draw(layer)
    color = _rgb(entry.get("color", "#ffffff"))
    draw.rectangle((inset, inset, width - inset, height - inset),
                   outline=color + (int(255 * opacity),), width=int(width_px))
    return layer


def _corner_marks(width: int, height: int, entry: dict) -> Image.Image:
    opacity = _opacity(entry, 0.55)
    inset = _number(entry, "inset", 0.04) * min(width, height)
    arm = _number(entry, "size", 0.05) * min(width, height)
    width_px = max(1, int(min(width, height) * 0.002))
    layer = _empty(width, height)
    draw = ImageDraw.Draw(layer)
    color = _rgb(entry.get("color", "#ffffff"))
    stroke = color + (int(255 * opacity),)
    corners = [
        (inset, inset, 1, 1),
        (width - inset, inset, -1, 1),
        (inset, height - inset, 1, -1),
        (width - inset, height - inset, -1, -1),
    ]
    for x, y, dx, dy in corners:
        draw.line((x, y, x + dx * arm, y), fill=stroke, width=width_px)
        draw.line((x, y, x, y + dy * arm), fill=stroke, width=width_px)
    return layer


def _grain(width: int, height: int, entry: dict) -> Image.Image:
    opacity = _opacity(entry, 0.18)
    size = max(0.1, _number(entry, "size", 0.5))
    cell = max(16, int(30 + size * 150))
    rng = np.random.default_rng(23)
    tile = rng.integers(0, 256, (cell, cell), dtype=np.uint8)
    array = np.tile(tile, (height // cell + 1, width // cell + 1))[:height, :width]
    alpha = (array.astype(np.float32) / 255.0) * opacity * 255 * 0.55
    return _rgba_array(_rgb(entry.get("color", "#ffffff")), alpha)


def _vignette(width: int, height: int, entry: dict) -> Image.Image:
    opacity = _opacity(entry, 0.45)
    yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)
    nx = (xx - width * 0.5) / max(1.0, width * 0.5)
    ny = (yy - height * 0.5) / max(1.0, height * 0.5)
    distance = np.sqrt(nx * nx + ny * ny) / math.sqrt(2)
    alpha = np.clip((distance - 0.28) / 0.72, 0, 1) ** 1.5 * opacity * 255
    return _rgba_array(_rgb(entry.get("color", "#000000")), alpha)


_GENERATORS = {
    "smoke": _smoke,
    "light_leak": _light_leak,
    "bokeh": _bokeh,
    "lens_flare": _lens_flare,
    "holo": _holo,
    "rainbow": _rainbow,
    "rain": _rain,
    "snow": _snow,
    "embers": _embers,
    "sparkle": _sparkle,
    "dust": _dust,
    "confetti": _confetti,
    "frost": _frost,
    "halftone": _halftone,
    "grid": _grid,
    "pixel_grid": _pixel_grid,
    "scanlines": _scanlines,
    "vhs": _vhs,
    "paper": _paper,
    "frame": _frame,
    "corner_marks": _corner_marks,
    "grain": _grain,
    "vignette": _vignette,
}


def apply_stack(image: Image.Image, settings: dict | None,
                width: int | None = None,
                height: int | None = None) -> Image.Image:
    """Return ``image`` with the enabled overlays composited on top."""
    if not any_enabled(settings):
        return image
    base = image.convert("RGBA")
    out_width = int(width or base.width)
    out_height = int(height or base.height)
    if base.size != (out_width, out_height):
        base = base.resize((out_width, out_height), Image.Resampling.LANCZOS)
    work_width, work_height = _work_size(out_width, out_height)
    for name in _ORDER:
        if not enabled(settings, name):
            continue
        generator = _GENERATORS.get(name)
        if generator is None:
            continue
        entry = settings.get(name) or {}
        layer = generator(work_width, work_height, entry)
        if layer.size != (out_width, out_height):
            layer = layer.resize((out_width, out_height),
                                 Image.Resampling.LANCZOS)
        base = Image.alpha_composite(base, layer)
    return base


# --------------------------------------------------------------------------
# presets
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class OverlayPreset:
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
            **overlays) -> OverlayPreset:
    return OverlayPreset(key, label, category, note, overlays)


PRESETS: tuple[OverlayPreset, ...] = (
    # ------------------------------------------------------------ atmosphere
    _recipe("grain_fine", "Fine grain", "Atmosphere",
            "Light 35mm tooth over everything.",
            grain={"opacity": 0.10, "size": 0.35}),
    _recipe("grain_heavy", "Heavy film", "Atmosphere",
            "Coarse silver grain with a soft vignette.",
            grain={"opacity": 0.26, "size": 0.7},
            vignette={"opacity": 0.35}),
    _recipe("grain_cinema", "Cinema stock", "Atmosphere",
            "Warm grain, gentle corners, anamorphic feel.",
            grain={"opacity": 0.16, "size": 0.5, "color": "#ffe6c7"},
            vignette={"opacity": 0.45}),
    _recipe("dust_motes", "Dust motes", "Atmosphere",
            "Floating specks catching the light.",
            dust={"opacity": 0.35, "count": 190, "size": 0.35}),
    _recipe("smoke_violet", "Violet smoke", "Atmosphere",
            "Slow purple haze across the frame.",
            smoke={"opacity": 0.35, "color": "#8b5cf6", "scale": 0.7}),
    _recipe("smoke_ember", "Ember smoke", "Atmosphere",
            "Warm smoke with a low ember tint.",
            smoke={"opacity": 0.32, "color": "#ff7a3d", "scale": 0.6},
            grain={"opacity": 0.10}),

    # ----------------------------------------------------------------- light
    _recipe("warm_leak", "Warm leak", "Light",
            "A soft orange leak from the top corner.",
            light_leak={"opacity": 0.5, "color": "#ff8a3d", "angle": 35}),
    _recipe("golden_hour", "Golden hour", "Light",
            "Wide gold wash with a little bokeh.",
            light_leak={"opacity": 0.42, "color": "#ffd166",
                        "angle": 60, "size": 0.7},
            bokeh={"opacity": 0.35, "count": 14, "size": 0.09}),
    _recipe("flare_soft", "Soft flare", "Light",
            "A gentle lens bloom in the upper right.",
            lens_flare={"opacity": 0.45, "size": 0.26, "x": 0.76, "y": 0.2}),
    _recipe("flare_hard", "Hard flare", "Light",
            "Bright anamorphic streak with a hot core.",
            lens_flare={"opacity": 0.7, "size": 0.34, "x": 0.7, "y": 0.28},
            grain={"opacity": 0.08}),
    _recipe("prism_wash", "Prism wash", "Light",
            "A rainbow prism spread across the art.",
            rainbow={"opacity": 0.28, "angle": 24}),
    _recipe("holo_wash", "Holo wash", "Light",
            "Iridescent bands like foil packaging.",
            holo={"opacity": 0.34, "angle": 18}),
    _recipe("bokeh_lights", "Bokeh lights", "Light",
            "Out-of-focus warm lights behind glass.",
            bokeh={"opacity": 0.55, "count": 26, "size": 0.13},
            vignette={"opacity": 0.3}),

    # ------------------------------------------------------------------ film
    _recipe("vhs_tape", "VHS tape", "Film",
            "Tracking bars and a cold CRT wash.",
            vhs={"opacity": 0.45, "color": "#63e6ff"},
            scanlines={"opacity": 0.16, "spacing": 0.005},
            grain={"opacity": 0.12}),
    _recipe("tracking_error", "Tracking error", "Film",
            "Heavier tape damage with chroma bars.",
            vhs={"opacity": 0.7},
            scanlines={"opacity": 0.22},
            grain={"opacity": 0.18, "size": 0.6}),
    _recipe("old_projector", "Old projector", "Film",
            "Dust, grain, corners and a warm frame.",
            grain={"opacity": 0.2, "size": 0.6, "color": "#ffe6c7"},
            dust={"opacity": 0.3, "count": 120, "size": 0.5},
            vignette={"opacity": 0.55}),
    _recipe("polaroid", "Polaroid", "Film",
            "Instant-print border with a light leak.",
            frame={"opacity": 0.8, "width": 0.014, "inset": 0.05,
                   "color": "#f6f1e4"},
            light_leak={"opacity": 0.3, "color": "#ffb066", "angle": 20}),
    _recipe("slide_mount", "Slide mount", "Film",
            "Registration marks and a thin mount frame.",
            frame={"opacity": 0.5, "width": 0.003, "inset": 0.03},
            corner_marks={"opacity": 0.45, "size": 0.045}),

    # ----------------------------------------------------------------- print
    _recipe("halftone_press", "Halftone press", "Print",
            "A fine newsprint dot screen over the art.",
            halftone={"opacity": 0.32, "scale": 0.45}),
    _recipe("riso_mist", "Riso mist", "Print",
            "Coarse warm dots with paper tooth.",
            halftone={"opacity": 0.28, "scale": 0.7, "color": "#ff5c39"},
            paper={"opacity": 0.25, "color": "#f2e6d0"}),
    _recipe("newsprint_overlay", "Newsprint", "Print",
            "Cool grey screen and a soft fold.",
            halftone={"opacity": 0.26, "scale": 0.4, "color": "#2a2a2e"},
            grain={"opacity": 0.1},
            vignette={"opacity": 0.2}),
    _recipe("comic_dots", "Comic dots", "Print",
            "Bold dots and black corner marks.",
            halftone={"opacity": 0.4, "scale": 0.8, "color": "#141018"},
            corner_marks={"opacity": 0.5, "size": 0.04}),

    # ----------------------------------------------------------------- retro
    _recipe("crt_scan", "CRT scanlines", "Retro",
            "Thin black lines and a phosphor vignette.",
            scanlines={"opacity": 0.22, "spacing": 0.005},
            vignette={"opacity": 0.4}),
    _recipe("arcade_glow", "Arcade glow", "Retro",
            "Scanlines, grid and a magenta bloom.",
            scanlines={"opacity": 0.16},
            grid={"opacity": 0.14, "color": "#ff5cd6", "scale": 0.6},
            holo={"opacity": 0.18}),
    _recipe("retro_tv", "Retro TV", "Retro",
            "Warm glass, curved vignette and static.",
            grain={"opacity": 0.14, "color": "#ffe6c7"},
            scanlines={"opacity": 0.12},
            vignette={"opacity": 0.5}),
    _recipe("y2k_chrome", "Y2K chrome", "Retro",
            "Foil sheen with a soft light leak.",
            holo={"opacity": 0.32, "angle": 40},
            light_leak={"opacity": 0.3, "color": "#ffd166", "angle": 70}),

    # ------------------------------------------------------------------ tech
    _recipe("blueprint_grid", "Blueprint grid", "Tech",
            "A drafting grid over a cool wash.",
            grid={"opacity": 0.2, "color": "#bfe3ff", "scale": 0.45},
            corner_marks={"opacity": 0.4}),
    _recipe("hud_grid", "HUD grid", "Tech",
            "Fine target grid with corner brackets.",
            grid={"opacity": 0.16, "color": "#7ae7ff", "scale": 0.35},
            corner_marks={"opacity": 0.6, "size": 0.06}),
    _recipe("pixel_screen", "Pixel screen", "Tech",
            "An LCD pixel grid over the whole canvas.",
            pixel_grid={"opacity": 0.18, "scale": 0.4}),
    _recipe("hologram_lines", "Hologram lines", "Tech",
            "Scanlines and an iridescent foil wash.",
            scanlines={"opacity": 0.14, "color": "#7ae7ff"},
            holo={"opacity": 0.22, "angle": 65}),

    # --------------------------------------------------------------- weather
    _recipe("rain_glass", "Rain on glass", "Weather",
            "Cool streaks with a heavy vignette.",
            rain={"opacity": 0.4, "count": 170, "angle": 8},
            vignette={"opacity": 0.4}),
    _recipe("snowfall", "Snowfall", "Weather",
            "Soft flakes drifting over the art.",
            snow={"opacity": 0.65, "count": 210}),
    _recipe("frost_edges", "Frost", "Weather",
            "Ice crystals creeping in from the edges.",
            frost={"opacity": 0.45, "scale": 0.8},
            snow={"opacity": 0.25, "count": 60}),
    _recipe("storm_dust", "Storm dust", "Weather",
            "Grit and a cold blue haze.",
            dust={"opacity": 0.3, "count": 220, "size": 0.5},
            smoke={"opacity": 0.2, "color": "#a9c6d8"},
            vignette={"opacity": 0.35}),
    _recipe("ember_drift", "Ember drift", "Weather",
            "Warm sparks rising through the frame.",
            embers={"opacity": 0.55, "count": 90},
            smoke={"opacity": 0.18, "color": "#ff7a3d"}),

    # ----------------------------------------------------------- celebration
    _recipe("confetti_pop", "Confetti pop", "Celebration",
            "A burst of colour for launches and wins.",
            confetti={"opacity": 0.8, "count": 120}),
    _recipe("sparkle_dust", "Sparkle dust", "Celebration",
            "Tiny four-point stars across the canvas.",
            sparkle={"opacity": 0.55, "count": 90}),
    _recipe("party_dots", "Party dots", "Celebration",
            "Bold dots with confetti and sparkle.",
            halftone={"opacity": 0.18, "scale": 0.9, "color": "#ff5cd6"},
            confetti={"opacity": 0.45, "count": 60}),
    _recipe("spotlight", "Spotlight", "Celebration",
            "A warm flare and lifted centre.",
            lens_flare={"opacity": 0.35, "x": 0.5, "y": 0.42, "size": 0.4},
            bokeh={"opacity": 0.25, "count": 12, "size": 0.08}),

    # --------------------------------------------------------------- utility
    _recipe("clean_vignette", "Vignette", "Utility",
            "A gentle darkening at the edges.",
            vignette={"opacity": 0.45}),
    _recipe("thin_frame", "Thin frame", "Utility",
            "A crisp hairline border around the canvas.",
            frame={"opacity": 0.55, "width": 0.003, "inset": 0.03}),
    _recipe("print_marks", "Registration marks", "Utility",
            "Corner marks for a print-proof look.",
            corner_marks={"opacity": 0.55, "size": 0.05}),
    _recipe("paper_tooth", "Paper tooth", "Utility",
            "Warm fibre texture with a soft edge.",
            paper={"opacity": 0.3, "color": "#f2e6d0"},
            grain={"opacity": 0.08},
            vignette={"opacity": 0.2}),
)

PRESETS_BY_KEY = {preset.key: preset for preset in PRESETS}


def categories() -> list[str]:
    seen: list[str] = []
    for preset in PRESETS:
        if preset.category not in seen:
            seen.append(preset.category)
    return seen


def entries(category: str | None = None, needle: str = "") -> list[OverlayPreset]:
    needle = (needle or "").strip().lower()
    found = []
    for preset in PRESETS:
        if category and preset.category != category:
            continue
        if needle and needle not in (
                f"{preset.label} {preset.category} {preset.note}".lower()):
            continue
        found.append(preset)
    return found


def get(key: str) -> OverlayPreset | None:
    return PRESETS_BY_KEY.get(key)


def stack_for(key: str) -> dict:
    preset = PRESETS_BY_KEY.get(key)
    return preset.apply() if preset else default_stack()


def describe(settings: dict | None) -> str:
    stack = settings or {}
    preset = PRESETS_BY_KEY.get(str(stack.get("preset") or ""))
    if preset is not None:
        return preset.label
    names = active_names(stack)
    return ", ".join(names) if names else "No overlay"


# --------------------------------------------------------------------------
# previews
# --------------------------------------------------------------------------
_PREVIEW_CACHE: dict[tuple[str, int, int], bytes] = {}


def _sample_poster(width: int, height: int) -> Image.Image:
    yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)
    nx = xx / max(1, width - 1)
    ny = yy / max(1, height - 1)
    blend = np.clip(nx * 0.65 + ny * 0.35, 0, 1)
    array = np.empty((height, width, 3), dtype=np.uint8)
    start = np.array([34, 20, 62], dtype=np.float32)
    end = np.array([198, 92, 52], dtype=np.float32)
    for index in range(3):
        array[..., index] = (start[index] * (1 - blend)
                             + end[index] * blend).astype(np.uint8)
    image = Image.fromarray(array, "RGB").convert("RGBA")
    draw = ImageDraw.Draw(image)
    shortest = min(width, height)
    cx, cy = width * 0.52, height * 0.46
    radius = shortest * 0.30
    draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius),
                 outline=(255, 220, 180, 235), width=max(2, int(shortest * 0.02)))
    draw.ellipse((cx - radius * 0.42, cy - radius * 0.42,
                  cx + radius * 0.42, cy + radius * 0.42),
                 fill=(255, 154, 92, 235))
    draw.polygon([(cx, cy - radius * 1.5), (cx + radius * 0.16, cy - radius * 0.35),
                  (cx + radius * 1.35, cy - radius * 0.35),
                  (cx + radius * 0.24, cy + radius * 0.12),
                  (cx + radius * 0.52, cy + radius * 1.2),
                  (cx, cy + radius * 0.38),
                  (cx - radius * 0.52, cy + radius * 1.2),
                  (cx - radius * 0.24, cy + radius * 0.12),
                  (cx - radius * 1.35, cy - radius * 0.35),
                  (cx - radius * 0.16, cy - radius * 0.35)],
                 fill=(255, 241, 201, 255))
    return image


def preview_png(key: str, width: int = 156, height: int = 100) -> bytes:
    cached = _PREVIEW_CACHE.get((key, width, height))
    if cached is not None:
        return cached
    sample = _sample_poster(width * 2, height * 2)
    result = apply_stack(sample, stack_for(key), width * 2, height * 2)
    result = result.resize((width, height), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    result.save(buffer, format="PNG", optimize=True)
    data = buffer.getvalue()
    _PREVIEW_CACHE[(key, width, height)] = data
    return data
