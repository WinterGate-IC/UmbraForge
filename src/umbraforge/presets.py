"""Canvas presets.

Layers always live in normalized 0..1 space, so changing a preset only changes
the output pixel size - the composition keeps its proportions and reflows.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import gcd


@dataclass(frozen=True)
class CanvasPreset:
    key: str
    name: str
    width: int
    height: int
    category: str
    note: str = ""

    @property
    def ratio(self) -> float:
        return self.width / self.height

    @property
    def ratio_label(self) -> str:
        divisor = gcd(self.width, self.height) or 1
        w, h = self.width // divisor, self.height // divisor
        if w > 24 or h > 24:
            return f"{self.ratio:.2f}:1"
        return f"{w}:{h}"

    @property
    def shape(self) -> str:
        if abs(self.ratio - 1.0) < 0.02:
            return "square"
        return "wide" if self.ratio > 1 else "tall"

    def describe(self) -> str:
        return f"{self.width:,} \u00d7 {self.height:,} \u00b7 {self.ratio_label}"


PRESETS: tuple[CanvasPreset, ...] = (
    CanvasPreset("profile", "Profile picture", 1200, 1200, "Social",
                 "Square avatar that crops cleanly everywhere."),
    CanvasPreset("square", "Square post", 2048, 2048, "Social",
                 "High-resolution square art or album cover."),
    CanvasPreset("desktop", "Desktop 4K", 3840, 2160, "Wallpaper",
                 "3840 \u00d7 2160 wallpaper for a 4K desktop."),
    CanvasPreset("wide", "Wide 16:9", 1920, 1080, "Wallpaper",
                 "Standard widescreen wallpaper or video frame."),
    CanvasPreset("mobile", "Mobile wallpaper", 1080, 1920, "Wallpaper",
                 "Phone wallpaper, nine by sixteen."),
    CanvasPreset("banner", "Banner", 1500, 500, "Social",
                 "Profile banner for social and streaming pages."),
    CanvasPreset("poster", "Poster", 2400, 3600, "Print",
                 "Two by three poster at print resolution."),
    CanvasPreset("story", "Story / vertical", 1080, 1920, "Social",
                 "Vertical story or short-form cover."),
    CanvasPreset("card", "Card", 1600, 1000, "Social",
                 "Link preview card, eight by five."),
    CanvasPreset("custom", "Custom size", 1600, 1600, "Custom",
                 "Choose any size you need."),
)

PRESET_MAP = {preset.key: preset for preset in PRESETS}
DEFAULT_PRESET = "profile"


def get(key: str) -> CanvasPreset:
    return PRESET_MAP.get(key, PRESET_MAP[DEFAULT_PRESET])


def for_size(width: int, height: int) -> CanvasPreset:
    for preset in PRESETS:
        if preset.key != "custom" and preset.width == width and preset.height == height:
            return preset
    return CanvasPreset("custom", "Custom size", int(width), int(height), "Custom")


def key_for_size(width: int, height: int) -> str:
    return for_size(width, height).key


def clamp_size(value: int, low: int = 64, high: int = 8192) -> int:
    return max(low, min(high, int(value)))
