"""The type shelf: named text styles with sensible starting values.

A style is not a font. It is a *recipe* - a suggested voice, size, weight,
tracking and case - that lands as ordinary editable text. Nothing here is
locked: every value can be changed in the Layer panel afterwards, which keeps
the studio beginner-friendly without capping what a power user can do.

The library browser, the Build rail and the inspector all read this one table,
so adding a style in a single place makes it appear everywhere.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TextStyle:
    key: str
    label: str
    hint: str
    sample: str
    text: str
    size: float = 0.05          # fraction of canvas height
    weight: int = 700
    spacing: float = 0.0        # em units
    line_height: float = 1.15
    uppercase: bool = False
    italic: bool = False
    align: str = "center"
    font: str = "Bahnschrift"
    color: str = "#f3f1f8"
    opacity: float = 1.0
    width: float = 0.72
    height: float = 0.13
    sample_px: int = 16

    def preset(self) -> dict:
        """A plain dictionary for the window's ``_add_text`` helper."""
        return {
            "name": self.label,
            "text": self.text,
            "size": self.size,
            "weight": self.weight,
            "spacing": self.spacing,
            "line_height": self.line_height,
            "uppercase": self.uppercase,
            "italic": self.italic,
            "align": self.align,
            "font": self.font,
            "color": self.color,
            "opacity": self.opacity,
            "width": self.width,
            "height": self.height,
        }


#: Ordered roughly from biggest voice to smallest annotation. The order is
#: what the Type browser shows, so the first few entries should feel like the
#: obvious choices for a poster or emblem.
STYLES: tuple[TextStyle, ...] = (
    TextStyle(
        "display", "Display", "Large, tight display type", "FORGE",
        "YOUR TITLE", size=0.105, weight=800, spacing=0.015,
        uppercase=True, sample_px=26, width=0.74, height=0.18),
    TextStyle(
        "poster", "Poster shout", "Huge condensed caps for posters",
        "JOIN THE FORGE", "JOIN THE FORGE", size=0.145, weight=900,
        spacing=-0.01, uppercase=True, font="Impact",
        sample_px=26, width=0.82, height=0.24),
    TextStyle(
        "headline", "Serif headline", "Editorial serif title",
        "The Long Night", "The Long Night", size=0.095, weight=700,
        spacing=-0.005, font="Georgia", line_height=1.05,
        sample_px=24, width=0.76, height=0.20),
    TextStyle(
        "heading", "Heading", "Section or name heading", "Heading",
        "Heading", size=0.062, weight=700, font="Bahnschrift",
        sample_px=19, width=0.70, height=0.14),
    TextStyle(
        "subheading", "Subheading", "A second-level heading",
        "Subheading", "Subheading", size=0.044, weight=600,
        font="Segoe UI Semibold", sample_px=17, width=0.66, height=0.12),
    TextStyle(
        "subtitle", "Subtitle", "Quiet supporting line", "A quieter line",
        "A quieter supporting line", size=0.032, weight=400,
        font="Segoe UI Light", color="#c9c4d6", sample_px=15, width=0.68,
        height=0.11),
    TextStyle(
        "body", "Body copy", "Wrapped body text", "Body copy",
        "Body copy goes here. Select this text and type your own words. "
        "It wraps inside the layer box.",
        size=0.030, weight=400, font="Segoe UI", align="left",
        line_height=1.35, sample_px=13, width=0.66, height=0.24),
    TextStyle(
        "caption", "Caption", "Small supporting line", "A short caption",
        "A short caption", size=0.022, weight=400, spacing=0.01,
        italic=True, font="Georgia", color="#bdb8cb", sample_px=11,
        width=0.62, height=0.09),
    TextStyle(
        "quote", "Quote", "Italic serif pull quote",
        "\u201cThe night remembers.\u201d",
        "\u201cThe night remembers.\u201d", size=0.052, weight=400,
        italic=True, font="Georgia", line_height=1.25, sample_px=18,
        width=0.68, height=0.20),
    TextStyle(
        "monogram", "Monogram", "Initials in a strong face", "UF",
        "UF", size=0.160, weight=800, spacing=-0.01, uppercase=True,
        font="Bahnschrift", sample_px=30, width=0.32, height=0.22),
    TextStyle(
        "label", "Spaced label", "Wide-tracked label", "L A B E L",
        "LABEL", size=0.030, weight=700, spacing=0.30, uppercase=True,
        font="Segoe UI Semibold", sample_px=12, width=0.54, height=0.08),
    TextStyle(
        "tagline", "Tagline", "Established-line tracking", "EST. MMXXVI",
        "EST. MMXXVI", size=0.022, weight=500, spacing=0.24,
        uppercase=True, font="Trebuchet MS", color="#d9b46a",
        sample_px=12, width=0.56, height=0.07),
    TextStyle(
        "badge", "Badge", "Compact stamp or seal word", "VERIFIED",
        "VERIFIED", size=0.026, weight=800, spacing=0.12, uppercase=True,
        font="Bahnschrift", color="#08080c", sample_px=13, width=0.34,
        height=0.07),
    TextStyle(
        "numeral", "Numeral", "Big figure or count", "01",
        "01", size=0.170, weight=900, spacing=-0.02, font="Impact",
        sample_px=30, width=0.30, height=0.24),
    TextStyle(
        "micro", "Micro type", "Tiny legal or technical line",
        "MICRO TYPE", "MICRO TYPE", size=0.014, weight=500, spacing=0.30,
        uppercase=True, font="Segoe UI", color="#9d97ab", sample_px=9,
        width=0.50, height=0.05),
    TextStyle(
        "terminal", "Terminal", "Console line with a prompt",
        "> SYSTEM ONLINE", "> SYSTEM ONLINE", size=0.026, weight=500,
        font="Consolas", color="#63e6ff", align="left", sample_px=13,
        width=0.58, height=0.08),
    TextStyle(
        "code", "Code", "Monospaced code sample", "forge.build()",
        "forge.build()", size=0.024, weight=400, font="Cascadia Mono",
        color="#8b5cf6", align="left", sample_px=12, width=0.56,
        height=0.08),
    TextStyle(
        "script", "Script", "Handwritten signature line",
        "Forge your own", "Forge your own", size=0.070, weight=500,
        italic=True, font="Segoe Script", sample_px=22, width=0.66,
        height=0.16),
    TextStyle(
        "arcane", "Blackletter", "Old-world heraldic caps", "ARCANUM",
        "ARCANUM", size=0.085, weight=700, uppercase=True,
        font="Old English Text MT", sample_px=22, width=0.64, height=0.16),
    TextStyle(
        "stencil", "Stencil", "Cut-metal marking", "DIVISION 09",
        "DIVISION 09", size=0.070, weight=700, spacing=0.05,
        uppercase=True, font="Stencil", sample_px=20, width=0.64,
        height=0.13),
    TextStyle(
        "condensed", "Condensed", "Narrow industrial caps",
        "MAXIMUM OUTPUT", "MAXIMUM OUTPUT", size=0.080, weight=700,
        spacing=0.0, uppercase=True, font="Arial Narrow", sample_px=21,
        width=0.60, height=0.15),
    TextStyle(
        "spaced", "Wide caps", "Letter-spaced wordmark",
        "W I N T E R G A T E", "WINTERGATE", size=0.042, weight=300,
        spacing=0.45, uppercase=True, font="Bahnschrift Light",
        sample_px=16, width=0.78, height=0.09),
    TextStyle(
        "price", "Price", "Shop or ticket figure", "$42.00",
        "$42.00", size=0.075, weight=800, font="Georgia", sample_px=20,
        width=0.40, height=0.13),
    TextStyle(
        "cta", "Call to action", "Button-style imperative",
        "GET STARTED", "GET STARTED", size=0.038, weight=800,
        spacing=0.08, uppercase=True, font="Arial Black", color="#ff7a3d",
        sample_px=15, width=0.50, height=0.09),
    TextStyle(
        "annotation", "Annotation", "Technical figure note",
        "fig. 1 \u2014 detail", "fig. 1 \u2014 detail", size=0.019,
        weight=400, italic=True, font="Consolas", color="#a7a1b5",
        align="left", sample_px=11, width=0.50, height=0.06),
    TextStyle(
        "date", "Date", "Day, month, year line", "26.10.2026",
        "26.10.2026", size=0.024, weight=500, spacing=0.12,
        font="Segoe UI", color="#c9c4d6", sample_px=12, width=0.40,
        height=0.06),
    TextStyle(
        "watermark", "Watermark", "Faint oversized background word",
        "UMBRAFORGE", "UMBRAFORGE", size=0.155, weight=900,
        spacing=0.12, uppercase=True, font="Impact", opacity=0.16,
        sample_px=24, width=0.92, height=0.22),
    TextStyle(
        "editorial", "Editorial", "Warm literary display serif",
        "The Forge", "The Forge", size=0.078, weight=700,
        font="Cambria", line_height=1.1, sample_px=21, width=0.72,
        height=0.16),
)

_BY_KEY = {style.key: style for style in STYLES}


def get(key: str) -> TextStyle:
    """Return a style, falling back to the display style."""
    return _BY_KEY.get(key, _BY_KEY["display"])


def keys() -> tuple[str, ...]:
    return tuple(style.key for style in STYLES)


def labels() -> tuple[tuple[str, str], ...]:
    """``(key, label)`` pairs for compact pickers."""
    return tuple((style.key, style.label) for style in STYLES)


def presets() -> dict[str, dict]:
    """A backwards-compatible dictionary used by the main window."""
    return {style.key: style.preset() for style in STYLES}


def count() -> int:
    return len(STYLES)
