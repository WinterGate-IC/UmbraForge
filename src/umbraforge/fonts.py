"""Font library: a curated shelf plus whatever the machine already has.

UmbraForge ships no font binaries. That keeps the download small and avoids
licence puzzles, but it means the useful answer to "which fonts can I pick?"
is "the ones installed here, ranked by what they are good at".

The curated shelf is deliberately broad: display faces, squarish industrial
grotesks, elegant serifs, handwriting, monospace and symbol-friendly families.
Names that are not installed are simply not offered. Live discovery means a
font the user installs today appears after a restart, with no update needed.
"""

from __future__ import annotations

from dataclasses import dataclass

#: The shelves used by the type browser and the inspector grouping.
CATEGORY_ORDER = (
    "Display", "Industrial", "Sans", "Serif", "Slab", "Mono",
    "Script", "Symbol", "System",
)

#: A curated shelf of widely available, characterful families. Each entry is
#: (family, category, note). Missing families are filtered out at runtime.
CURATED: tuple[tuple[str, str, str], ...] = (
    # Windows display / variable families -------------------------------
    ("Bahnschrift", "Industrial", "Squarish variable grotesk; the studio default."),
    ("Bahnschrift SemiBold", "Industrial", "Heavier optical cut of Bahnschrift."),
    ("Bahnschrift Light", "Industrial", "Fine, technical display weight."),
    ("Impact", "Display", "The loudest condensed face on Windows."),
    ("Arial Black", "Display", "Heavy geometric sans for posters."),
    ("Franklin Gothic Heavy", "Display", "Classic poster weight."),
    ("Haettenschweiler", "Display", "Ultra-condensed newsprint energy."),
    ("Showcard Gothic", "Display", "Friendly cartoon display lettering."),
    ("Broadway", "Display", "Art-deco marquee letters."),
    ("Algerian", "Display", "Ornate engraved capitals."),
    ("Old English Text MT", "Display", "Blackletter for heraldry and lore."),
    ("Copperplate Gothic Bold", "Display", "Engraved stationery caps."),
    ("Magneto", "Display", "Chrome-and-tailfin retro."),
    ("Stencil", "Display", "Cut-metal stencil lettering."),
    ("Rockwell Extra Bold", "Slab", "Poster slab with real weight."),
    ("Elephant", "Display", "Fat, warm display serif."),
    ("Bodoni MT Black", "Serif", "High-contrast fashion masthead."),
    ("Playbill", "Display", "Western playbill caps."),
    ("OCR A Extended", "Mono", "Cold machine-readable caps."),
    ("Terminal", "Mono", "Raw terminal lettering."),
    ("Fixedsys", "Mono", "Pixel-era system mono."),
    ("Consolas", "Mono", "Clean coding mono."),
    ("Cascadia Mono", "Mono", "Modern coding mono with character."),
    ("Cascadia Code", "Mono", "Ligature-friendly coding face."),
    ("Courier New", "Mono", "Typewriter classic."),
    ("Lucida Console", "Mono", "Wide, legible console face."),
    ("Lucida Sans Unicode", "Sans", "Broad Unicode workhorse."),
    ("Segoe UI", "Sans", "The Windows interface face."),
    ("Segoe UI Semibold", "Sans", "Stronger UI weight."),
    ("Segoe UI Light", "Sans", "Airy interface weight."),
    ("Segoe UI Black", "Display", "Heavy UI display weight."),
    ("Segoe UI Variable Display", "Sans", "Modern variable display cut."),
    ("Selawik", "Sans", "Open-source Segoe alternative."),
    ("Calibri", "Sans", "Soft humanist office face."),
    ("Candara", "Sans", "Calligraphic humanist sans."),
    ("Corbel", "Sans", "Friendly humanist sans."),
    ("Corbel Light", "Sans", "Light humanist cut."),
    ("Trebuchet MS", "Sans", "Loose, friendly web classic."),
    ("Verdana", "Sans", "Maximum small-size legibility."),
    ("Tahoma", "Sans", "Compact UI workhorse."),
    ("Arial", "Sans", "The universal fallback."),
    ("Arial Narrow", "Sans", "Condensed utility sans."),
    ("Century Gothic", "Sans", "Round geometric futurism."),
    ("Futura", "Sans", "Bauhaus geometry, if installed."),
    ("Avant Garde", "Sans", "Wide geometric display sans."),
    ("Gill Sans MT", "Sans", "Humanist English classic."),
    ("Lucida Sans", "Sans", "Warm humanist sans."),
    ("Microsoft Sans Serif", "Sans", "Plain, dependable sans."),
    ("MS Gothic", "Sans", "Japanese Gothic with a squared feel."),
    ("Yu Gothic", "Sans", "Modern Japanese sans."),
    ("Meiryo", "Sans", "Soft Japanese UI sans."),
    ("Malgun Gothic", "Sans", "Korean UI sans."),
    ("Microsoft YaHei", "Sans", "Chinese UI sans."),
    # Serifs ------------------------------------------------------------
    ("Georgia", "Serif", "Screen-first transitional serif."),
    ("Cambria", "Serif", "Sturdy reading serif."),
    ("Constantia", "Serif", "Warm book serif."),
    ("Palatino Linotype", "Serif", "Calligraphic old-style serif."),
    ("Book Antiqua", "Serif", "Humanist book face."),
    ("Times New Roman", "Serif", "The newspaper standard."),
    ("Garamond", "Serif", "French old-style elegance."),
    ("Baskerville", "Serif", "High-contrast transitional serif."),
    ("Perpetua", "Serif", "Sculptural classical serif."),
    ("Century", "Serif", "Round, readable serif."),
    ("Bookman Old Style", "Slab", "Friendly heavy serif."),
    ("Rockwell", "Slab", "Geometric slab serif."),
    ("Sitka Display", "Serif", "Literary display serif."),
    ("Sitka Text", "Serif", "Long-form literary serif."),
    ("Segoe UI Symbol", "Symbol", "Broad symbol coverage."),
    ("Segoe UI Emoji", "Symbol", "Colour emoji, flattened on export."),
    ("Wingdings", "Symbol", "Dingbat classics."),
    ("Webdings", "Symbol", "Pictogram dingbats."),
    # Script / handwriting ---------------------------------------------
    ("Segoe Script", "Script", "Casual brush script."),
    ("Segoe Print", "Script", "Hand-printed notebook voice."),
    ("Lucida Handwriting", "Script", "Friendly handwriting."),
    ("Bradley Hand ITC", "Script", "Marker-pen handwriting."),
    ("Brush Script MT", "Script", "Retro sign-painter script."),
    ("Ink Free", "Script", "Loose ink-pen display."),
    ("Comic Sans MS", "Script", "Informal comic lettering."),
    ("MV Boli", "Script", "Round handwritten sans."),
    ("Gabriola", "Script", "Flourished calligraphic serif."),
    # macOS / Linux names that may appear after installation ------------
    ("SF Pro Display", "Sans", "Apple's interface display face."),
    ("SF Mono", "Mono", "Apple's coding mono."),
    ("Helvetica Neue", "Sans", "The Swiss neutral."),
    ("Avenir Next", "Sans", "Humanist geometric sans."),
    ("Futura PT", "Sans", "Refined geometric display sans."),
    ("Optima", "Sans", "Flared humanist classic."),
    ("Didot", "Serif", "High-contrast fashion serif."),
    ("Bodoni 72", "Serif", "Sharp Italian modern serif."),
    ("Hoefler Text", "Serif", "Bookish old-style serif."),
    ("Charter", "Serif", "Durable text serif."),
    ("Menlo", "Mono", "Apple coding mono."),
    ("Monaco", "Mono", "Classic Mac coding mono."),
    ("DejaVu Sans", "Sans", "Open-source Unicode workhorse."),
    ("DejaVu Serif", "Serif", "Open-source reading serif."),
    ("DejaVu Sans Mono", "Mono", "Open-source coding mono."),
    ("Liberation Sans", "Sans", "Metric-compatible Arial replacement."),
    ("Liberation Serif", "Serif", "Metric-compatible Times replacement."),
    ("Liberation Mono", "Mono", "Metric-compatible Courier replacement."),
    ("Noto Sans", "Sans", "Broad-language open sans."),
    ("Noto Serif", "Serif", "Broad-language open serif."),
    ("Noto Sans Mono", "Mono", "Broad-language open mono."),
    ("Ubuntu", "Sans", "Ubuntu's humanist signature."),
    ("Ubuntu Mono", "Mono", "Ubuntu coding mono."),
    ("Cantarell", "Sans", "GNOME's interface sans."),
    ("Inter", "Sans", "Modern screen-first sans."),
    ("IBM Plex Sans", "Sans", "Engineered grotesk family."),
    ("IBM Plex Mono", "Mono", "Engineered coding mono."),
    ("JetBrains Mono", "Mono", "Developer favourite mono."),
    ("Fira Sans", "Sans", "Mozilla's humanist sans."),
    ("Fira Code", "Mono", "Ligature coding mono."),
    ("Source Sans 3", "Sans", "Adobe's open UI sans."),
    ("Source Serif 4", "Serif", "Adobe's open reading serif."),
    ("Space Grotesk", "Display", "Quirky contemporary display sans."),
    ("Space Mono", "Mono", "Retro-futurist mono."),
    ("Bebas Neue", "Display", "Tall all-caps poster sans."),
    ("Anton", "Display", "Heavy condensed poster sans."),
    ("Oswald", "Display", "Condensed web poster sans."),
    ("Archivo Black", "Display", "Wide, solid poster grotesk."),
    ("Playfair Display", "Serif", "High-contrast editorial display."),
    ("Cormorant Garamond", "Serif", "Delicate old-style display."),
    ("Cinzel", "Serif", "Roman inscriptional caps."),
    ("Abril Fatface", "Display", "Fat editorial display serif."),
    ("Lobster", "Script", "Bold retro script."),
    ("Pacifico", "Script", "Surf-sign script."),
    ("Caveat", "Script", "Loose marker handwriting."),
    ("Permanent Marker", "Script", "Heavy marker display."),
    ("Creepster", "Display", "Horror-poster lettering."),
    ("Nosifer", "Display", "Dripping horror display."),
    ("Rubik Glitch", "Display", "Digital glitch display."),
    ("Orbitron", "Display", "Sci-fi geometric display."),
    ("Audiowide", "Display", "Retro-tech display sans."),
    ("Press Start 2P", "Display", "8-bit arcade lettering."),
    ("VT323", "Mono", "Terminal-green pixel mono."),
    ("UnifrakturMaguntia", "Display", "Blackletter revival."),
    ("Cinzel Decorative", "Display", "Ornamented Roman caps."),
)

TEXT_FONTS: tuple[str, ...] = tuple(name for name, _category, _note in CURATED)

_AVAILABLE_CACHE: list[str] | None = None
_INSTALLED_CACHE: set[str] | None = None


@dataclass(frozen=True)
class FontChoice:
    name: str
    category: str
    note: str
    installed: bool = True

    @property
    def label(self) -> str:
        return self.name


def installed_families(refresh: bool = False) -> set[str]:
    """Every family Qt can see, cached. Returns empty when Qt is unavailable."""
    global _INSTALLED_CACHE
    if _INSTALLED_CACHE is not None and not refresh:
        return _INSTALLED_CACHE
    try:
        from PySide6.QtGui import QFontDatabase

        families = {str(name) for name in QFontDatabase.families()}
    except Exception:
        families = set()
    _INSTALLED_CACHE = families
    return families


def _casefold_map(names) -> dict[str, str]:
    return {str(name).casefold(): str(name) for name in names}


def resolve(name: str, fallbacks: tuple[str, ...] = ()) -> str:
    """Return an installed spelling of *name*, or the best fallback."""
    if not name:
        return fallback_family()
    installed = installed_families()
    if not installed:
        return name
    by_fold = _casefold_map(installed)
    match = by_fold.get(name.casefold())
    if match:
        return match
    for candidate in fallbacks:
        match = by_fold.get(candidate.casefold())
        if match:
            return match
    return fallback_family()


def fallback_family() -> str:
    installed = installed_families()
    if not installed:
        return "Bahnschrift"
    by_fold = _casefold_map(installed)
    for candidate in ("Bahnschrift", "Segoe UI", "Arial", "DejaVu Sans",
                      "Noto Sans", "Liberation Sans", "Helvetica"):
        match = by_fold.get(candidate.casefold())
        if match:
            return match
    return sorted(installed, key=str.casefold)[0]


def available(refresh: bool = False) -> list[str]:
    """Curated families this machine actually has, plus any extras we know."""
    global _AVAILABLE_CACHE
    if _AVAILABLE_CACHE is not None and not refresh:
        return list(_AVAILABLE_CACHE)
    installed = installed_families()
    if not installed:
        # Qt is not up yet (model tests): offer the shelf as a promise.
        _AVAILABLE_CACHE = [name for name in TEXT_FONTS]
        return list(_AVAILABLE_CACHE)
    by_fold = _casefold_map(installed)
    names: list[str] = []
    seen: set[str] = set()
    for family, _category, _note in CURATED:
        match = by_fold.get(family.casefold())
        if match and match.casefold() not in seen:
            seen.add(match.casefold())
            names.append(match)
    # A few dependable extras that are not on the curated shelf but are
    # installed and genuinely useful. This makes the "All installed" group
    # feel alive without turning the menu into an alphabetical dump.
    for family in sorted(installed, key=str.casefold):
        fold = family.casefold()
        if fold in seen or fold.startswith(("@", ".")):
            continue
        if any(token in fold for token in (
                "symbol", "emoji", "icon", "awesome", "material",
                "bootstrap", "fontawesome", "webdings", "wingdings")):
            continue
        seen.add(fold)
        names.append(family)
    _AVAILABLE_CACHE = names
    return list(names)


def choices() -> list[FontChoice]:
    """Grouped, de-duplicated font choices for menus and browsers."""
    rows: list[FontChoice] = []
    seen: set[str] = set()
    installed = installed_families()
    by_fold = _casefold_map(installed)
    for family, category, note in CURATED:
        actual = by_fold.get(family.casefold(), family)
        fold = actual.casefold()
        if fold in seen:
            continue
        seen.add(fold)
        rows.append(FontChoice(actual, category, note,
                              installed=bool(not installed or actual in installed)))
    if installed:
        for family in sorted(installed, key=str.casefold):
            fold = family.casefold()
            if fold in seen or fold.startswith(("@", ".")):
                continue
            if any(token in fold for token in (
                    "symbol", "emoji", "icon", "awesome", "material",
                    "bootstrap", "webdings", "wingdings")):
                continue
            seen.add(fold)
            rows.append(FontChoice(family, "System",
                                   "Installed on this device."))
    return rows


def choices_in(category: str | None = None, search: str = "") -> list[FontChoice]:
    needle = (search or "").strip().casefold()
    rows = choices()
    if category and category not in ("All", ""):
        rows = [row for row in rows if row.category == category]
    if needle:
        rows = [row for row in rows
                if needle in row.name.casefold() or needle in row.note.casefold()]
    return rows


def categories() -> list[str]:
    present = {row.category for row in choices()}
    return [name for name in CATEGORY_ORDER if name in present]


def shelf(family: str) -> str:
    for name, category, _note in CURATED:
        if name.casefold() == (family or "").casefold():
            return category
    return "System"


def note(family: str) -> str:
    for name, _category, text in CURATED:
        if name.casefold() == (family or "").casefold():
            return text
    return "Installed on this device."


def refresh() -> None:
    """Forget cached font lists so a newly installed family shows up."""
    global _AVAILABLE_CACHE, _INSTALLED_CACHE
    _AVAILABLE_CACHE = None
    _INSTALLED_CACHE = None
