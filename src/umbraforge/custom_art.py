"""User-imported vector shapes and icons.

UmbraForge ships with a large built-in set, but the studio should not decide
what your emblem looks like. This module lets people import an SVG and turn its
paths into first-class shape or icon layers. Records live outside projects in
``%APPDATA%/WinterGate/UmbraForge/art.json`` (override with
``UMBRAFORGE_ART_STORE``) so the same personal library is available in every
design.

Only vector data is stored - never the source file - so projects and the
library stay portable, and imported art remains sharp at any export size.
"""

from __future__ import annotations

import json
import math
import os
import re
import tempfile
import time
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QPainterPath, QTransform

STORE_ENV = "UMBRAFORGE_ART_STORE"
KINDS = ("shape", "icon")

_NUMBER = re.compile(r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?")
_COMMAND = re.compile(r"[MmLlHhVvCcSsQqTtAaZz]")
_PATH_CACHE: dict[tuple[str, str], tuple[float, QPainterPath]] = {}


# --------------------------------------------------------------------------
# persistence
# --------------------------------------------------------------------------
def store_path() -> Path:
    override = os.environ.get(STORE_ENV)
    if override:
        return Path(override)
    base = os.environ.get("APPDATA")
    root = Path(base) if base else Path.home() / ".config"
    return root / "WinterGate" / "UmbraForge" / "art.json"


def _blank() -> dict:
    return {"format": "umbraforge-art", "version": 1, "shapes": [], "icons": []}


def load() -> dict:
    path = store_path()
    if not path.exists():
        return _blank()
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return _blank()
    if not isinstance(data, dict):
        return _blank()
    out = _blank()
    for kind in KINDS:
        records = data.get(kind + "s") or []
        if isinstance(records, list):
            for record in records:
                if (isinstance(record, dict) and record.get("key")
                        and isinstance(record.get("path"), str)
                        and record["path"].strip()):
                    out[kind + "s"].append({
                        "key": str(record["key"]),
                        "name": str(record.get("name") or "Custom art"),
                        "note": str(record.get("note") or ""),
                        "path": record["path"],
                        "created": float(record.get("created") or 0.0),
                    })
    return out


def save(data: dict) -> Path:
    path = store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(prefix=".art-", suffix=".tmp",
                                    dir=str(path.parent))
    os.close(handle)
    temp = Path(name)
    try:
        temp.write_text(json.dumps(data, indent=1), encoding="utf-8")
        os.replace(temp, path)
    finally:
        if temp.exists():
            try:
                temp.unlink()
            except OSError:
                pass
    _PATH_CACHE.clear()
    return path


def _plural(kind: str) -> str:
    if kind not in KINDS:
        raise ValueError("Custom art kind must be shape or icon.")
    return kind + "s"


def entries(kind: str) -> list[dict]:
    return list(load().get(_plural(kind), []))


def get(kind: str, key: str) -> dict | None:
    for record in entries(kind):
        if record["key"] == key:
            return record
    return None


def label(kind: str, key: str) -> str | None:
    record = get(kind, key)
    return record["name"] if record else None


def _slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return slug[:28] or "art"


def add(kind: str, name: str, path_data: str, note: str = "") -> dict:
    """Add raw SVG path data and return the stored record."""
    data = load()
    key_base = f"user-{kind}-{_slug(name)}"
    keys = {record["key"] for record in data[_plural(kind)]}
    key = key_base
    index = 2
    while key in keys:
        key = f"{key_base}-{index}"
        index += 1
    record = {
        "key": key,
        "name": (name or "Custom art").strip()[:60],
        "note": (note or "").strip()[:160],
        "path": path_data.strip(),
        "created": time.time(),
    }
    # Validate before touching the store.
    path = parse_path_data(record["path"])
    if path.isEmpty():
        raise ValueError("That artwork has no drawable vector paths.")
    normalize(path)
    data[_plural(kind)].append(record)
    save(data)
    return record


def remove(kind: str, key: str) -> bool:
    data = load()
    records = data.get(_plural(kind), [])
    kept = [record for record in records if record["key"] != key]
    if len(kept) == len(records):
        return False
    data[_plural(kind)] = kept
    save(data)
    return True


def rename(kind: str, key: str, name: str) -> bool:
    data = load()
    for record in data.get(_plural(kind), []):
        if record["key"] == key:
            record["name"] = (name or record["name"]).strip()[:60]
            save(data)
            return True
    return False


# --------------------------------------------------------------------------
# SVG import
# --------------------------------------------------------------------------
def import_file(path: str | Path, kind: str, name: str = "",
                note: str = "") -> dict:
    source = Path(path)
    if source.suffix.lower() not in (".svg",):
        raise ValueError(
            "Import an SVG for vector shapes and icons. Photos can be added "
            "with Import image instead, where they become editable layers.")
    text = source.read_text(encoding="utf-8-sig", errors="replace")
    data = svg_to_path_data(text)
    return add(kind, name or source.stem.replace("-", " ").replace("_", " "),
               data, note or f"Imported from {source.name}")


def svg_to_path_data(text: str) -> str:
    """Extract usable geometry from a simple SVG document."""
    if "<svg" not in text[:4000].lower():
        raise ValueError("That file does not look like an SVG.")
    pieces: list[str] = []
    for match in re.finditer(r"<path\b([^>]*)>", text, re.IGNORECASE | re.DOTALL):
        attrs = match.group(1)
        d = re.search(r"\bd\s*=\s*(['\"])(.*?)\1", attrs, re.DOTALL)
        if d and d.group(2).strip():
            pieces.append(d.group(2).strip())
    for match in re.finditer(r"<(polygon|polyline)\b([^>]*)>", text,
                             re.IGNORECASE | re.DOTALL):
        attrs = match.group(2)
        points = re.search(r"\bpoints\s*=\s*(['\"])(.*?)\1", attrs, re.DOTALL)
        if not points:
            continue
        values = [float(value) for value in _NUMBER.findall(points.group(2))]
        pairs = list(zip(values[::2], values[1::2]))
        if not pairs:
            continue
        command = "M" if match.group(1).lower() == "polygon" else "M"
        d = command + " ".join(f"{x:g},{y:g}" for x, y in pairs)
        if match.group(1).lower() == "polygon":
            d += " Z"
        pieces.append(d)
    for match in re.finditer(r"<(circle|ellipse|rect)\b([^>]*)>", text,
                             re.IGNORECASE | re.DOTALL):
        kind = match.group(1).lower()
        attrs = match.group(2)

        def number(name: str, default: float = 0.0) -> float:
            found = re.search(rf"\b{name}\s*=\s*(['\"])(.*?)\1", attrs,
                              re.DOTALL)
            if not found:
                return default
            try:
                return float(_NUMBER.search(found.group(2)).group())
            except (AttributeError, ValueError):
                return default

        if kind == "circle":
            cx, cy, radius = number("cx"), number("cy"), number("r")
            if radius > 0:
                pieces.append(_ellipse_data(cx, cy, radius, radius))
        elif kind == "ellipse":
            cx, cy = number("cx"), number("cy")
            rx, ry = number("rx"), number("ry")
            if rx > 0 and ry > 0:
                pieces.append(_ellipse_data(cx, cy, rx, ry))
        else:
            x, y = number("x"), number("y")
            width, height = number("width"), number("height")
            radius = min(number("rx"), number("ry"), width / 2, height / 2)
            if width > 0 and height > 0:
                if radius > 0:
                    pieces.append(
                        f"M {x + radius:g} {y:g} H {x + width - radius:g} "
                        f"Q {x + width:g} {y:g} {x + width:g} {y + radius:g} "
                        f"V {y + height - radius:g} "
                        f"Q {x + width:g} {y + height:g} "
                        f"{x + width - radius:g} {y + height:g} "
                        f"H {x + radius:g} Q {x:g} {y + height:g} {x:g} "
                        f"{y + height - radius:g} V {y + radius:g} "
                        f"Q {x:g} {y:g} {x + radius:g} {y:g} Z")
                else:
                    pieces.append(
                        f"M {x:g} {y:g} H {x + width:g} V {y + height:g} "
                        f"H {x:g} Z")
    if not pieces:
        raise ValueError(
            "No vector paths were found. Try an SVG with paths, polygons, "
            "circles, ellipses or rectangles.")
    return " ".join(pieces)


def _ellipse_data(cx: float, cy: float, rx: float, ry: float) -> str:
    # Two half arcs make a full ellipse without depending on the SVG renderer.
    return (f"M {cx - rx:g} {cy:g} "
            f"A {rx:g} {ry:g} 0 0 1 {cx + rx:g} {cy:g} "
            f"A {rx:g} {ry:g} 0 0 1 {cx - rx:g} {cy:g} Z")


# --------------------------------------------------------------------------
# SVG path parsing
# --------------------------------------------------------------------------
def parse_path_data(data: str) -> QPainterPath:
    """Parse the practical subset of SVG path syntax into a QPainterPath."""
    path = QPainterPath()
    if not data:
        return path
    tokens = re.findall(
        r"[MmLlHhVvCcSsQqTtAaZz]|[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?",
        data)
    index = 0
    command = ""
    current = QPointF(0, 0)
    start = QPointF(0, 0)
    last_control: QPointF | None = None
    last_quad: QPointF | None = None
    previous = ""

    def number() -> float:
        nonlocal index
        if index >= len(tokens):
            raise ValueError("SVG path ended unexpectedly.")
        value = float(tokens[index])
        index += 1
        return value

    def is_command(token: str) -> bool:
        return bool(token) and token[0].isalpha()

    while index < len(tokens):
        token = tokens[index]
        if is_command(token):
            command = token
            index += 1
            if command in "Zz":
                path.closeSubpath()
                current = QPointF(start)
                previous = command
                continue
        elif not command:
            break
        relative = command.islower()
        upper = command.upper()
        if upper == "M":
            x, y = number(), number()
            point = QPointF(current.x() + x, current.y() + y) if relative else QPointF(x, y)
            path.moveTo(point)
            current = point
            start = QPointF(point)
            command = "l" if relative else "L"
            last_control = last_quad = None
        elif upper == "L":
            x, y = number(), number()
            point = QPointF(current.x() + x, current.y() + y) if relative else QPointF(x, y)
            path.lineTo(point)
            current = point
            last_control = last_quad = None
        elif upper == "H":
            x = number()
            point = QPointF(current.x() + x if relative else x, current.y())
            path.lineTo(point)
            current = point
            last_control = last_quad = None
        elif upper == "V":
            y = number()
            point = QPointF(current.x(), current.y() + y if relative else y)
            path.lineTo(point)
            current = point
            last_control = last_quad = None
        elif upper == "C":
            values = [number() for _ in range(6)]
            c1 = (QPointF(current.x() + values[0], current.y() + values[1])
                  if relative else QPointF(values[0], values[1]))
            c2 = (QPointF(current.x() + values[2], current.y() + values[3])
                  if relative else QPointF(values[2], values[3]))
            end = (QPointF(current.x() + values[4], current.y() + values[5])
                   if relative else QPointF(values[4], values[5]))
            path.cubicTo(c1, c2, end)
            current = end
            last_control = c2
            last_quad = None
        elif upper == "S":
            values = [number() for _ in range(4)]
            c1 = (QPointF(2 * current.x() - last_control.x(),
                          2 * current.y() - last_control.y())
                  if previous.upper() in ("C", "S") and last_control
                  else QPointF(current))
            c2 = (QPointF(current.x() + values[0], current.y() + values[1])
                  if relative else QPointF(values[0], values[1]))
            end = (QPointF(current.x() + values[2], current.y() + values[3])
                   if relative else QPointF(values[2], values[3]))
            path.cubicTo(c1, c2, end)
            current = end
            last_control = c2
            last_quad = None
        elif upper == "Q":
            values = [number() for _ in range(4)]
            control = (QPointF(current.x() + values[0], current.y() + values[1])
                       if relative else QPointF(values[0], values[1]))
            end = (QPointF(current.x() + values[2], current.y() + values[3])
                   if relative else QPointF(values[2], values[3]))
            path.quadTo(control, end)
            current = end
            last_quad = control
            last_control = None
        elif upper == "T":
            values = [number() for _ in range(2)]
            control = (QPointF(2 * current.x() - last_quad.x(),
                               2 * current.y() - last_quad.y())
                       if previous.upper() in ("Q", "T") and last_quad
                       else QPointF(current))
            end = (QPointF(current.x() + values[0], current.y() + values[1])
                   if relative else QPointF(values[0], values[1]))
            path.quadTo(control, end)
            current = end
            last_quad = control
            last_control = None
        elif upper == "A":
            values = [number() for _ in range(7)]
            rx, ry, rotation = abs(values[0]), abs(values[1]), values[2]
            large, sweep = bool(values[3]), bool(values[4])
            end = (QPointF(current.x() + values[5], current.y() + values[6])
                   if relative else QPointF(values[5], values[6]))
            _arc_to(path, current, end, rx, ry, rotation, large, sweep)
            current = end
            last_control = last_quad = None
        else:
            # Unknown command: consume nothing further and let the caller see
            # the artwork instead of hanging on malformed input.
            break
        previous = command
    return path


def _arc_to(path: QPainterPath, start: QPointF, end: QPointF, rx: float,
            ry: float, rotation: float, large: bool, sweep: bool) -> None:
    if rx <= 0 or ry <= 0 or start == end:
        path.lineTo(end)
        return
    # Endpoint-to-center conversion from the SVG implementation notes.
    phi = math.radians(rotation % 360.0)
    cos_phi, sin_phi = math.cos(phi), math.sin(phi)
    dx, dy = (start.x() - end.x()) / 2.0, (start.y() - end.y()) / 2.0
    x1 = cos_phi * dx + sin_phi * dy
    y1 = -sin_phi * dx + cos_phi * dy
    scale = (x1 * x1) / (rx * rx) + (y1 * y1) / (ry * ry)
    if scale > 1:
        factor = math.sqrt(scale)
        rx *= factor
        ry *= factor
    numerator = max(0.0, (rx * rx * ry * ry
                          - rx * rx * y1 * y1 - ry * ry * x1 * x1))
    denominator = rx * rx * y1 * y1 + ry * ry * x1 * x1
    coefficient = (math.sqrt(numerator / denominator)
                   if denominator > 1e-12 else 0.0)
    if large == sweep:
        coefficient = -coefficient
    cx1 = coefficient * rx * y1 / ry
    cy1 = -coefficient * ry * x1 / rx
    cx = cos_phi * cx1 - sin_phi * cy1 + (start.x() + end.x()) / 2.0
    cy = sin_phi * cx1 + cos_phi * cy1 + (start.y() + end.y()) / 2.0
    start_angle = _angle(1, 0,
                         (x1 - cx1) / rx, (y1 - cy1) / ry)
    end_angle = _angle((x1 - cx1) / rx, (y1 - cy1) / ry,
                       (-x1 - cx1) / rx, (-y1 - cy1) / ry)
    if not sweep and end_angle > 0:
        end_angle -= 2 * math.pi
    elif sweep and end_angle < 0:
        end_angle += 2 * math.pi
    rect = QRectF(cx - rx, cy - ry, rx * 2, ry * 2)
    # Qt measures arcs from 3 o'clock counter-clockwise in degrees. Rotating
    # the path around the ellipse centre handles SVG's rotated ellipses.
    transform = QTransform()
    transform.translate(cx, cy)
    transform.rotate(rotation)
    transform.translate(-cx, -cy)
    local = QPainterPath()
    local.arcMoveTo(rect, math.degrees(start_angle))
    local.arcTo(rect, math.degrees(start_angle),
                math.degrees(end_angle - start_angle))
    path.connectPath(transform.map(local))


def _angle(ux: float, uy: float, vx: float, vy: float) -> float:
    dot = ux * vx + uy * vy
    length = math.hypot(ux, uy) * math.hypot(vx, vy)
    if length <= 1e-12:
        return 0.0
    value = max(-1.0, min(1.0, dot / length))
    angle = math.acos(value)
    if ux * vy - uy * vx < 0:
        angle = -angle
    return angle


# --------------------------------------------------------------------------
# normalized paths
# --------------------------------------------------------------------------
def normalize(path: QPainterPath, margin: float = 0.02) -> QPainterPath:
    bounds = path.boundingRect()
    if bounds.width() <= 1e-9 or bounds.height() <= 1e-9:
        raise ValueError("That artwork is empty or has zero size.")
    usable = max(0.01, 1.0 - margin * 2)
    scale = min(usable / bounds.width(), usable / bounds.height())
    width = bounds.width() * scale
    height = bounds.height() * scale
    transform = QTransform()
    transform.translate((1.0 - width) / 2.0, (1.0 - height) / 2.0)
    transform.scale(scale, scale)
    transform.translate(-bounds.x(), -bounds.y())
    return transform.map(path)


def path(kind: str, key: str) -> QPainterPath | None:
    record = get(kind, key)
    if not record:
        return None
    stamp = record.get("created", 0.0)
    cached = _PATH_CACHE.get((kind, key))
    if cached and cached[0] == stamp:
        return QPainterPath(cached[1])
    try:
        built = normalize(parse_path_data(record["path"]))
    except (ValueError, ZeroDivisionError):
        return None
    _PATH_CACHE[(kind, key)] = (stamp, built)
    return QPainterPath(built)


def count() -> int:
    data = load()
    return len(data.get("shapes", [])) + len(data.get("icons", []))
