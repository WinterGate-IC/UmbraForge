"""The document model: canvas, background, layers, assets and undo.

Everything here is plain Python - no Qt, no Pillow - so it can be tested
head-lessly and serialized without surprises. Geometry is normalized: x, y, w
and h are fractions of the canvas, which is what lets a composition move from
a profile picture to a 4K wallpaper without falling apart.
"""

from __future__ import annotations

import base64
import copy
import hashlib
import json
import os
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import ClassVar

from . import branding, fonts, presets, text_styles

FORMAT_VERSION = 1
MAX_LAYERS = 120
MAX_UNDO = 80

BLEND_MODES: tuple[tuple[str, str], ...] = (
    ("normal", "Normal"),
    ("multiply", "Multiply"),
    ("screen", "Screen"),
    ("overlay", "Overlay"),
    ("darken", "Darken"),
    ("lighten", "Lighten"),
    ("color_dodge", "Colour dodge"),
    ("color_burn", "Colour burn"),
    ("hard_light", "Hard light"),
    ("soft_light", "Soft light"),
    ("difference", "Difference"),
    ("exclusion", "Exclusion"),
)
BLEND_KEYS = {key for key, _ in BLEND_MODES}

PATTERNS: tuple[tuple[str, str], ...] = (
    ("none", "None"),
    ("dots", "Dots"),
    ("grid", "Grid"),
    ("diagonal", "Diagonal lines"),
    ("rings", "Rings"),
    ("hexagons", "Hexagons"),
    ("triangles", "Triangles"),
    ("scanlines", "Scanlines"),
    ("stars", "Stars"),
    ("waves", "Waves"),
    ("noise", "Grain"),
    ("rays", "Rays"),
)

ALIGNMENTS = ("left", "center", "right")
VALIGNMENTS = ("top", "middle", "bottom")

#: Curated families, exposed here so older callers keep working. The live,
#: installed-only list comes from :func:`umbraforge.fonts.available`.
TEXT_FONTS: tuple[str, ...] = fonts.TEXT_FONTS

#: Named type recipes. The browser, window and inspector all read this table.
TEXT_STYLES: tuple[tuple[str, str], ...] = text_styles.labels()


def new_id() -> str:
    return uuid.uuid4().hex[:10]


def default_effects() -> dict:
    return {
        "shadow": {
            "enabled": False, "color": "#000000", "opacity": 0.55,
            "blur": 0.018, "dx": 0.004, "dy": 0.006,
        },
        "glow": {
            "enabled": False, "color": "#ff7a3d", "opacity": 0.55,
            "size": 0.022,
        },
    }


#: Every non-destructive image adjustment understood by ``imaging.adjust``.
#: Values are deliberately plain floats so old .umbra files keep loading after
#: the stack grows: unknown keys are ignored and missing keys adopt these.
ADJUSTMENT_DEFAULTS: dict[str, float] = {
    # quick tone
    "brightness": 1.0, "contrast": 1.0, "saturation": 1.0,
    "warmth": 0.0, "hue": 0.0, "vignette": 0.0,
    # light
    "exposure": 0.0, "highlights": 0.0, "shadows": 0.0,
    "whites": 0.0, "blacks": 0.0, "gamma": 1.0, "fade": 0.0,
    # colour
    "temperature": 0.0, "tint": 0.0, "vibrance": 0.0,
    "sepia": 0.0, "monochrome": 0.0, "invert": 0.0, "posterize": 0.0,
    # detail and texture
    "sharpness": 0.0, "clarity": 0.0, "noise_reduction": 0.0,
    "blur": 0.0, "grain": 0.0,
}


def default_adjustments() -> dict:
    return dict(ADJUSTMENT_DEFAULTS)


def default_background() -> dict:
    return {
        "kind": "linear",
        "color": "#0a0a10",
        "color2": "#26123a",
        "angle": 135.0,
        "pattern": "none",
        "pattern_color": "#ffffff",
        "pattern_opacity": 0.07,
        "pattern_scale": 0.35,
        "asset_id": "",
        "opacity": 1.0,
        "vignette": 0.25,
    }


def merge(defaults: dict, values: dict | None) -> dict:
    out = copy.deepcopy(defaults)
    if not values:
        return out
    for key, value in values.items():
        if key in out and isinstance(out[key], dict) and isinstance(value, dict):
            out[key] = merge(out[key], value)
        elif key in out:
            out[key] = value
    return out


def _clamp(value, low, high, fallback):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return fallback
    if number != number:  # NaN
        return fallback
    return max(low, min(high, number))


@dataclass
class Layer:
    """Base layer. Subclasses add their own content fields."""

    kind: ClassVar[str] = "layer"
    id: str = field(default_factory=new_id)
    name: str = "Layer"
    visible: bool = True
    locked: bool = False
    opacity: float = 1.0
    blend: str = "normal"
    x: float = 0.10
    y: float = 0.10
    w: float = 0.80
    h: float = 0.80
    rotation: float = 0.0
    flip_h: bool = False
    flip_v: bool = False
    effects: dict = field(default_factory=default_effects)

    # ---- geometry -----------------------------------------------------
    @property
    def cx(self) -> float:
        return self.x + self.w / 2.0

    @property
    def cy(self) -> float:
        return self.y + self.h / 2.0

    def center(self) -> tuple[float, float]:
        return (self.cx, self.cy)

    def set_center(self, cx: float, cy: float) -> None:
        self.x = cx - self.w / 2.0
        self.y = cy - self.h / 2.0

    def normalized_rect(self) -> tuple[float, float, float, float]:
        return (self.x, self.y, self.w, self.h)

    def clamp_to_canvas(self, keep_visible: bool = True) -> None:
        self.w = _clamp(self.w, 0.001, 4.0, 0.5)
        self.h = _clamp(self.h, 0.001, 4.0, 0.5)
        if keep_visible:
            limit_x = 1.0 - min(self.w, 1.0) * 0.15
            limit_y = 1.0 - min(self.h, 1.0) * 0.15
            self.x = _clamp(self.x, -self.w + limit_x, limit_x, 0.0)
            self.y = _clamp(self.y, -self.h + limit_y, limit_y, 0.0)
        self.rotation = _clamp(self.rotation, -360.0, 360.0, 0.0)
        self.opacity = _clamp(self.opacity, 0.0, 1.0, 1.0)
        if self.blend not in BLEND_KEYS:
            self.blend = "normal"
        self.effects = merge(default_effects(), self.effects)

    # ---- serialization ------------------------------------------------
    def payload(self) -> dict:
        return {}

    def to_dict(self) -> dict:
        data = {
            "kind": self.kind,
            "id": self.id,
            "name": self.name,
            "visible": bool(self.visible),
            "locked": bool(self.locked),
            "opacity": float(self.opacity),
            "blend": self.blend,
            "x": float(self.x),
            "y": float(self.y),
            "w": float(self.w),
            "h": float(self.h),
            "rotation": float(self.rotation),
            "flip_h": bool(self.flip_h),
            "flip_v": bool(self.flip_v),
            "effects": copy.deepcopy(self.effects),
        }
        data.update(self.payload())
        return data

    def apply_common(self, data: dict) -> None:
        self.id = str(data.get("id") or new_id())
        self.name = str(data.get("name") or self.name)
        self.visible = bool(data.get("visible", True))
        self.locked = bool(data.get("locked", False))
        self.opacity = _clamp(data.get("opacity", 1.0), 0.0, 1.0, 1.0)
        blend = str(data.get("blend") or "normal")
        self.blend = blend if blend in BLEND_KEYS else "normal"
        self.x = _clamp(data.get("x", 0.1), -2.0, 2.0, 0.1)
        self.y = _clamp(data.get("y", 0.1), -2.0, 2.0, 0.1)
        self.w = _clamp(data.get("w", 0.8), 0.001, 4.0, 0.5)
        self.h = _clamp(data.get("h", 0.8), 0.001, 4.0, 0.5)
        self.rotation = _clamp(data.get("rotation", 0.0), -360.0, 360.0, 0.0)
        self.flip_h = bool(data.get("flip_h", False))
        self.flip_v = bool(data.get("flip_v", False))
        self.effects = merge(default_effects(), data.get("effects"))

    @classmethod
    def from_dict(cls, data: dict) -> "Layer":
        kind = str(data.get("kind") or "shape")
        target = LAYER_TYPES.get(kind, ShapeLayer)
        layer = target()
        layer.apply_common(data)
        layer.load_payload(data)
        layer.clamp_to_canvas(keep_visible=False)
        return layer

    def load_payload(self, data: dict) -> None:
        pass

    def clone(self) -> "Layer":
        data = self.to_dict()
        data["id"] = new_id()
        data["name"] = f"{self.name} copy"
        clone = Layer.from_dict(data)
        clone.x += 0.02
        clone.y += 0.02
        return clone

    def describe(self) -> str:
        return self.name


@dataclass
class ShapeLayer(Layer):
    kind: ClassVar[str] = "shape"
    name: str = "Shape"
    shape: str = "circle"
    fill: str = "#ff7a3d"
    fill2: str = ""
    gradient: bool = False
    gradient_angle: float = 90.0
    stroke: str = ""
    stroke_width: float = 0.0

    def payload(self) -> dict:
        return {
            "shape": self.shape, "fill": self.fill, "fill2": self.fill2,
            "gradient": bool(self.gradient),
            "gradient_angle": float(self.gradient_angle),
            "stroke": self.stroke, "stroke_width": float(self.stroke_width),
        }

    def load_payload(self, data: dict) -> None:
        self.shape = str(data.get("shape") or "circle")
        self.fill = str(data.get("fill") or "#ff7a3d")
        self.fill2 = str(data.get("fill2") or "")
        self.gradient = bool(data.get("gradient", False))
        self.gradient_angle = _clamp(data.get("gradient_angle", 90.0), 0.0, 360.0, 90.0)
        self.stroke = str(data.get("stroke") or "")
        self.stroke_width = _clamp(data.get("stroke_width", 0.0), 0.0, 0.5, 0.0)


@dataclass
class IconLayer(Layer):
    kind: ClassVar[str] = "icon"
    name: str = "Icon"
    icon: str = "star"
    color: str = "#f5f2ff"
    fill2: str = ""
    gradient: bool = False
    gradient_angle: float = 90.0

    def payload(self) -> dict:
        return {
            "icon": self.icon, "color": self.color, "fill2": self.fill2,
            "gradient": bool(self.gradient),
            "gradient_angle": float(self.gradient_angle),
        }

    def load_payload(self, data: dict) -> None:
        self.icon = str(data.get("icon") or "star")
        self.color = str(data.get("color") or "#f5f2ff")
        self.fill2 = str(data.get("fill2") or "")
        self.gradient = bool(data.get("gradient", False))
        self.gradient_angle = _clamp(data.get("gradient_angle", 90.0), 0.0, 360.0, 90.0)


@dataclass
class TextLayer(Layer):
    kind: ClassVar[str] = "text"
    name: str = "Text"
    text: str = "UMBRAFORGE"
    font: str = "Bahnschrift"
    size: float = 0.10           # fraction of canvas height
    weight: int = 700
    italic: bool = False
    color: str = "#f5f2ff"
    align: str = "center"
    valign: str = "middle"
    letter_spacing: float = 0.0  # em units
    line_height: float = 1.15
    wrap: bool = True
    uppercase: bool = False
    stroke_color: str = ""
    stroke_width: float = 0.0    # fraction of font size

    def payload(self) -> dict:
        return {
            "text": self.text, "font": self.font, "size": float(self.size),
            "weight": int(self.weight), "italic": bool(self.italic),
            "color": self.color, "align": self.align, "valign": self.valign,
            "letter_spacing": float(self.letter_spacing),
            "line_height": float(self.line_height), "wrap": bool(self.wrap),
            "uppercase": bool(self.uppercase),
            "stroke_color": self.stroke_color,
            "stroke_width": float(self.stroke_width),
        }

    def load_payload(self, data: dict) -> None:
        self.text = str(data.get("text") or "")
        self.font = str(data.get("font") or "Bahnschrift")
        self.size = _clamp(data.get("size", 0.10), 0.004, 0.6, 0.10)
        self.weight = int(_clamp(data.get("weight", 700), 100, 900, 700))
        self.italic = bool(data.get("italic", False))
        self.color = str(data.get("color") or "#f5f2ff")
        self.align = str(data.get("align") or "center")
        if self.align not in ALIGNMENTS:
            self.align = "center"
        self.valign = str(data.get("valign") or "middle")
        if self.valign not in VALIGNMENTS:
            self.valign = "middle"
        self.letter_spacing = _clamp(data.get("letter_spacing", 0.0), -0.05, 1.0, 0.0)
        self.line_height = _clamp(data.get("line_height", 1.15), 0.7, 2.5, 1.15)
        self.wrap = bool(data.get("wrap", True))
        self.uppercase = bool(data.get("uppercase", False))
        self.stroke_color = str(data.get("stroke_color") or "")
        self.stroke_width = _clamp(data.get("stroke_width", 0.0), 0.0, 0.2, 0.0)


@dataclass
class ImageLayer(Layer):
    kind: ClassVar[str] = "image"
    name: str = "Image"
    asset_id: str = ""
    original_asset_id: str = ""
    fit: str = "fill"
    mask: str = "none"
    mask_feather: float = 0.0
    adjustments: dict = field(default_factory=default_adjustments)

    def payload(self) -> dict:
        return {
            "asset_id": self.asset_id,
            "original_asset_id": self.original_asset_id,
            "fit": self.fit, "mask": self.mask,
            "mask_feather": float(self.mask_feather),
            "adjustments": copy.deepcopy(self.adjustments),
        }

    def load_payload(self, data: dict) -> None:
        self.asset_id = str(data.get("asset_id") or "")
        self.original_asset_id = str(data.get("original_asset_id") or "")
        self.fit = str(data.get("fit") or "fill")
        if self.fit not in ("fill", "cover", "contain"):
            self.fit = "fill"
        self.mask = str(data.get("mask") or "none")
        self.mask_feather = _clamp(data.get("mask_feather", 0.0), 0.0, 0.4, 0.0)
        self.adjustments = merge(default_adjustments(), data.get("adjustments"))


LAYER_TYPES: dict[str, type[Layer]] = {
    "shape": ShapeLayer,
    "icon": IconLayer,
    "text": TextLayer,
    "image": ImageLayer,
}


# --------------------------------------------------------------------------
# images and assets
# --------------------------------------------------------------------------
def add_asset(assets: dict, data: bytes, name: str = "image",
              mime: str = "image/png", width: int = 0,
              height: int = 0) -> str:
    digest = hashlib.sha1(data).hexdigest()[:20]
    assets[digest] = {
        "name": name,
        "mime": mime,
        "data": base64.b64encode(data).decode("ascii"),
        "w": int(width),
        "h": int(height),
    }
    return digest


def asset_bytes(assets: dict, asset_id: str) -> bytes | None:
    record = assets.get(asset_id or "")
    if not record:
        return None
    try:
        return base64.b64decode(record.get("data", ""))
    except (ValueError, TypeError):
        return None


def asset_name(assets: dict, asset_id: str) -> str:
    record = assets.get(asset_id or "")
    return str(record.get("name") or "image") if record else "missing image"


def project_info(path: str | Path) -> dict:
    """Read only the useful header of a project for recents and hints.

    This still parses the JSON document (so a corrupt file fails early) but it
    does not decode embedded images, which keeps listing projects cheap.
    """
    target = Path(path)
    data = json.loads(target.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict) or data.get("format") != "umbraforge":
        raise ValueError("That file is not an UmbraForge design.")
    return {
        "name": str(data.get("name") or target.stem),
        "width": int(data.get("width") or 0),
        "height": int(data.get("height") or 0),
        "layers": len(data.get("layers") or []),
        "assets": len(data.get("assets") or {}),
        "saved_at": str(data.get("saved_at") or ""),
        "saved_with": str(data.get("saved_with") or ""),
        "version": int(data.get("version") or 1),
    }


# --------------------------------------------------------------------------
# design document
# --------------------------------------------------------------------------
@dataclass
class Design:
    name: str = "Untitled"
    width: int = 1200
    height: int = 1200
    background: dict = field(default_factory=default_background)
    layers: list[Layer] = field(default_factory=list)
    assets: dict = field(default_factory=dict)
    selected: str | None = None

    # ---- presets ------------------------------------------------------
    @property
    def preset_key(self) -> str:
        return presets.key_for_size(self.width, self.height)

    @property
    def preset(self) -> presets.CanvasPreset:
        return presets.for_size(self.width, self.height)

    def set_preset(self, key: str, width: int | None = None,
                   height: int | None = None) -> None:
        preset = presets.get(key)
        if preset.key == "custom":
            self.width = presets.clamp_size(width or self.width)
            self.height = presets.clamp_size(height or self.height)
        else:
            self.width, self.height = preset.width, preset.height

    def set_size(self, width: int, height: int) -> None:
        self.width = presets.clamp_size(width)
        self.height = presets.clamp_size(height)

    # ---- layers -------------------------------------------------------
    def layer(self, layer_id: str | None) -> Layer | None:
        if not layer_id:
            return None
        for layer in self.layers:
            if layer.id == layer_id:
                return layer
        return None

    @property
    def active(self) -> Layer | None:
        return self.layer(self.selected)

    def top_first(self) -> list[Layer]:
        return list(reversed(self.layers))

    def add(self, layer: Layer, select: bool = True) -> Layer:
        if len(self.layers) >= MAX_LAYERS:
            raise ValueError(f"This design already has {MAX_LAYERS} layers.")
        self.layers.append(layer)
        if select:
            self.selected = layer.id
        return layer

    def insert(self, index: int, layer: Layer, select: bool = True) -> Layer:
        if len(self.layers) >= MAX_LAYERS:
            raise ValueError(f"This design already has {MAX_LAYERS} layers.")
        index = max(0, min(len(self.layers), index))
        self.layers.insert(index, layer)
        if select:
            self.selected = layer.id
        return layer

    def remove(self, layer_id: str) -> Layer | None:
        layer = self.layer(layer_id)
        if layer is None:
            return None
        index = self.layers.index(layer)
        self.layers.pop(index)
        if self.selected == layer_id:
            self.selected = (self.layers[min(index, len(self.layers) - 1)].id
                             if self.layers else None)
        return layer

    def duplicate(self, layer_id: str | None = None) -> Layer | None:
        source = self.layer(layer_id or self.selected)
        if source is None:
            return None
        clone = source.clone()
        index = self.layers.index(source)
        self.insert(index + 1, clone)
        return clone

    def move(self, layer_id: str, delta: int) -> bool:
        layer = self.layer(layer_id)
        if layer is None:
            return False
        index = self.layers.index(layer)
        target = max(0, min(len(self.layers) - 1, index + delta))
        if target == index:
            return False
        self.layers.pop(index)
        self.layers.insert(target, layer)
        return True

    def to_front(self, layer_id: str) -> bool:
        layer = self.layer(layer_id)
        if layer is None or self.layers[-1] is layer:
            return False
        self.layers.remove(layer)
        self.layers.append(layer)
        return True

    def to_back(self, layer_id: str) -> bool:
        layer = self.layer(layer_id)
        if layer is None or self.layers[0] is layer:
            return False
        self.layers.remove(layer)
        self.layers.insert(0, layer)
        return True

    def center_layer(self, layer_id: str) -> None:
        layer = self.layer(layer_id)
        if layer is not None:
            layer.set_center(0.5, 0.5)

    def unique_name(self, base: str) -> str:
        existing = {layer.name for layer in self.layers}
        if base not in existing:
            return base
        index = 2
        while f"{base} {index}" in existing:
            index += 1
        return f"{base} {index}"

    # ---- document -----------------------------------------------------
    def to_dict(self, include_selection: bool = True) -> dict:
        return {
            "format": "umbraforge",
            "version": FORMAT_VERSION,
            "name": self.name,
            "width": int(self.width),
            "height": int(self.height),
            "background": copy.deepcopy(self.background),
            "layers": [layer.to_dict() for layer in self.layers],
            "assets": copy.deepcopy(self.assets),
            "selected": self.selected if include_selection else None,
        }

    def load_dict(self, data: dict) -> None:
        self.name = str(data.get("name") or "Untitled")
        self.set_size(int(data.get("width") or 1200), int(data.get("height") or 1200))
        self.background = merge(default_background(), data.get("background"))
        self.assets = dict(data.get("assets") or {})
        layers: list[Layer] = []
        for raw in data.get("layers") or []:
            if not isinstance(raw, dict):
                continue
            try:
                layers.append(Layer.from_dict(raw))
            except Exception:
                continue
        self.layers = layers[:MAX_LAYERS]
        selected = data.get("selected")
        self.selected = selected if self.layer(selected) else (
            self.layers[-1].id if self.layers else None
        )

    @classmethod
    def from_dict(cls, data: dict) -> "Design":
        design = cls()
        design.load_dict(data)
        return design

    def clone(self) -> "Design":
        return Design.from_dict(self.to_dict())

    def import_layers(self, source: "Design") -> int:
        """Merge another project's layers and images into this design.

        Coordinates are already normalized, so a project made at any canvas
        size drops in without needing a resize. Embedded images are re-keyed
        into this design's asset table and duplicated content is deduplicated
        by the asset hash. Returns the number of layers imported.
        """
        mapping: dict[str, str] = {}
        for source_id, record in source.assets.items():
            data = asset_bytes(source.assets, source_id)
            if not data:
                continue
            mapping[source_id] = add_asset(
                self.assets, data,
                str(record.get("name") or "image"),
                str(record.get("mime") or "image/png"),
                int(record.get("w") or 0), int(record.get("h") or 0))
        imported = 0
        for layer in source.layers:
            raw = layer.to_dict()
            raw["id"] = new_id()
            raw["name"] = self.unique_name(layer.name)
            if isinstance(layer, ImageLayer):
                target_asset = mapping.get(layer.asset_id)
                if not target_asset:
                    continue
                raw["asset_id"] = target_asset
                original = mapping.get(layer.original_asset_id or "")
                raw["original_asset_id"] = original or target_asset
            try:
                clone = Layer.from_dict(raw)
                self.add(clone, select=False)
            except ValueError:
                break
            imported += 1
        if imported:
            self.selected = self.layers[-1].id
        return imported

    def save(self, path: str | Path, *, preview: bytes | None = None) -> Path:
        """Write the project atomically, with a small identity header.

        The header tells UmbraForge what wrote the file and when, without
        pretending it is a standard image. It also makes the format easy to
        inspect or repair with any text editor. A previously saved project is
        only replaced once the new bytes are safely on disk.
        """
        target = Path(path)
        if target.suffix.lower() != ".umbra":
            target = target.with_suffix(".umbra")
        target.parent.mkdir(parents=True, exist_ok=True)
        data = self.to_dict()
        data["saved_with"] = f"{branding.APP_NAME} {branding.VERSION}"
        data["saved_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        if preview:
            data["preview"] = base64.b64encode(preview).decode("ascii")
        handle, temp_name = tempfile.mkstemp(
            prefix=f".{target.stem}-", suffix=".umbra.tmp", dir=str(target.parent))
        temp = Path(temp_name)
        try:
            with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
                json.dump(data, stream, indent=1)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp, target)
        finally:
            if temp.exists():
                try:
                    temp.unlink()
                except OSError:
                    pass
        return target

    @classmethod
    def open(cls, path: str | Path) -> "Design":
        data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
        if not isinstance(data, dict) or data.get("format") != "umbraforge":
            raise ValueError("That file is not an UmbraForge design.")
        version = int(data.get("version") or 1)
        if version > FORMAT_VERSION:
            raise ValueError(
                "This design was made with a newer UmbraForge version.")
        return cls.from_dict(data)

    # ---- convenience --------------------------------------------------
    def layer_count(self) -> int:
        return len(self.layers)

    def describe_size(self) -> str:
        return f"{self.width:,} \u00d7 {self.height:,} \u00b7 {self.preset.ratio_label}"


def asset_image_size(data: bytes) -> tuple[int, int]:
    """Read image dimensions without importing Qt or Pillow."""
    if data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) >= 24:
        return (int.from_bytes(data[16:20], "big"),
                int.from_bytes(data[20:24], "big"))
    if data[:2] == b"\xff\xd8":
        index = 2
        while index + 9 < len(data):
            if data[index] != 0xFF:
                index += 1
                continue
            marker = data[index + 1]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                          0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                height = int.from_bytes(data[index + 5:index + 7], "big")
                width = int.from_bytes(data[index + 7:index + 9], "big")
                return (width, height)
            length = int.from_bytes(data[index + 2:index + 4], "big")
            index += 2 + max(2, length)
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP" and len(data) >= 30:
        chunk = data[12:16]
        if chunk == b"VP8X":
            width = int.from_bytes(data[24:27], "little") + 1
            height = int.from_bytes(data[27:30], "little") + 1
            return (width, height)
        if chunk == b"VP8 ":
            width = int.from_bytes(data[26:28], "little") & 0x3FFF
            height = int.from_bytes(data[28:30], "little") & 0x3FFF
            return (width, height)
    return (0, 0)


# --------------------------------------------------------------------------
# undo
# --------------------------------------------------------------------------
class History:
    """Snapshot undo with light coalescing for slider drags."""

    def __init__(self, design: Design, limit: int = MAX_UNDO):
        self.design = design
        self.limit = limit
        self._entries: list[dict] = []
        self._labels: list[str] = []
        self._cursor = -1
        self._last_key = ""
        self._last_at = 0.0
        self.reset()

    # -- state ----------------------------------------------------------
    def reset(self) -> None:
        self._entries = [self.design.to_dict()]
        self._labels = ["Opened"]
        self._cursor = 0
        self._last_key = ""
        self._last_at = 0.0

    @property
    def can_undo(self) -> bool:
        return self._cursor > 0

    @property
    def can_redo(self) -> bool:
        return self._cursor < len(self._entries) - 1

    @property
    def cursor(self) -> int:
        return self._cursor

    def labels(self) -> list[str]:
        return list(self._labels)

    def undo_label(self) -> str:
        return self._labels[self._cursor] if self._cursor >= 0 else ""

    def redo_label(self) -> str:
        if self._cursor + 1 < len(self._labels):
            return self._labels[self._cursor + 1]
        return ""

    # -- recording ------------------------------------------------------
    def push(self, label: str, key: str | None = None,
             coalesce_seconds: float = 1.1) -> bool:
        """Record the current design. Returns True if a snapshot was added.

        Repeated pushes with the same ``key`` inside the coalesce window are
        folded together so dragging one slider is one undo step.
        """
        now = time.monotonic()
        key = key or label
        if (self._cursor >= 0 and key == self._last_key
                and now - self._last_at < coalesce_seconds):
            # Refresh the newest snapshot in place with the latest values.
            self._entries[self._cursor] = self.design.to_dict()
            self._last_at = now
            return False
        snapshot = self.design.to_dict()
        if self._cursor >= 0 and snapshot == self._entries[self._cursor]:
            return False
        del self._entries[self._cursor + 1:]
        del self._labels[self._cursor + 1:]
        self._entries.append(snapshot)
        self._labels.append(label)
        self._cursor = len(self._entries) - 1
        while len(self._entries) > self.limit:
            self._entries.pop(0)
            self._labels.pop(0)
            self._cursor -= 1
        self._last_key = key
        self._last_at = now
        return True

    # -- travel ---------------------------------------------------------
    def undo(self) -> bool:
        if not self.can_undo:
            return False
        self._cursor -= 1
        self._restore()
        self._last_key = ""
        return True

    def redo(self) -> bool:
        if not self.can_redo:
            return False
        self._cursor += 1
        self._restore()
        self._last_key = ""
        return True

    def _restore(self) -> None:
        self.design.load_dict(copy.deepcopy(self._entries[self._cursor]))
