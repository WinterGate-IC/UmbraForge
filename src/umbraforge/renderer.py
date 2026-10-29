"""QPainter renderer: design in, pixels out.

Render at any size. The canvas always stores normalized geometry, so the same
design renders to a 96 px thumbnail or a full 4K export. Layer effects (glow
and drop shadow) are built offscreen and cached, which keeps dragging cheap.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from collections import OrderedDict

import numpy as np
from PIL import Image, ImageChops, ImageFilter
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetricsF,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QPolygonF,
    QRadialGradient,
    QTransform,
)

from . import geometry, imaging, layers

_COMPOSITION = {
    "normal": QPainter.CompositionMode.CompositionMode_SourceOver,
    "multiply": QPainter.CompositionMode.CompositionMode_Multiply,
    "screen": QPainter.CompositionMode.CompositionMode_Screen,
    "overlay": QPainter.CompositionMode.CompositionMode_Overlay,
    "darken": QPainter.CompositionMode.CompositionMode_Darken,
    "lighten": QPainter.CompositionMode.CompositionMode_Lighten,
    "color_dodge": QPainter.CompositionMode.CompositionMode_ColorDodge,
    "color_burn": QPainter.CompositionMode.CompositionMode_ColorBurn,
    "hard_light": QPainter.CompositionMode.CompositionMode_HardLight,
    "soft_light": QPainter.CompositionMode.CompositionMode_SoftLight,
    "difference": QPainter.CompositionMode.CompositionMode_Difference,
    "exclusion": QPainter.CompositionMode.CompositionMode_Exclusion,
}

_ASSET_CACHE: OrderedDict[str, QImage] = OrderedDict()
_ADJUST_CACHE: OrderedDict[tuple, QImage] = OrderedDict()
_LAYER_IMAGE_CACHE: OrderedDict[tuple, QImage] = OrderedDict()
_STYLED_CACHE: OrderedDict[str, QImage] = OrderedDict()
_MAX_ASSETS = 24
_MAX_ADJUSTED = 10
_MAX_LAYER_IMAGES = 32
_MAX_STYLED = 20


def clear_caches() -> None:
    _ASSET_CACHE.clear()
    _ADJUST_CACHE.clear()
    _LAYER_IMAGE_CACHE.clear()
    _STYLED_CACHE.clear()


def _remember(cache: OrderedDict, key, value, limit: int):
    cache[key] = value
    cache.move_to_end(key)
    while len(cache) > limit:
        cache.popitem(last=False)
    return value


def _color(value: str, alpha: int = 255) -> QColor:
    color = QColor(value or "#ffffff")
    if not color.isValid():
        color = QColor("#ffffff")
    color.setAlpha(alpha)
    return color


def _composition(name: str):
    return _COMPOSITION.get(name, QPainter.CompositionMode.CompositionMode_SourceOver)


# --------------------------------------------------------------------------
# assets and images
# --------------------------------------------------------------------------
def _asset_qimage(design: layers.Design, asset_id: str) -> QImage | None:
    if not asset_id:
        return None
    if asset_id in _ASSET_CACHE:
        _ASSET_CACHE.move_to_end(asset_id)
        return _ASSET_CACHE[asset_id]
    data = layers.asset_bytes(design.assets, asset_id)
    if not data:
        return None
    image = QImage.fromData(data)
    if image.isNull():
        return None
    image = image.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
    return _remember(_ASSET_CACHE, asset_id, image, _MAX_ASSETS)


def _adjusted_qimage(design: layers.Design, layer: "layers.ImageLayer") -> QImage | None:
    source = _asset_qimage(design, layer.asset_id)
    if source is None:
        return None
    key = (layer.asset_id, json.dumps(layer.adjustments, sort_keys=True))
    if key in _ADJUST_CACHE:
        _ADJUST_CACHE.move_to_end(key)
        return _ADJUST_CACHE[key]
    if imaging.is_identity(layer.adjustments):
        _remember(_ADJUST_CACHE, key, source, _MAX_ADJUSTED)
        return source
    pil = imaging.qimage_to_pil(source)
    adjusted = imaging.adjust(pil, layer.adjustments)
    result = imaging.pil_to_qimage(adjusted)
    return _remember(_ADJUST_CACHE, key, result, _MAX_ADJUSTED)


def _layer_image(design: layers.Design, layer: "layers.ImageLayer",
                 width: int, height: int) -> QImage | None:
    width, height = max(1, int(width)), max(1, int(height))
    key = (layer.asset_id, json.dumps(layer.adjustments, sort_keys=True),
           layer.fit, layer.mask, round(float(layer.mask_feather), 3),
           width, height)
    if key in _LAYER_IMAGE_CACHE:
        _LAYER_IMAGE_CACHE.move_to_end(key)
        return _LAYER_IMAGE_CACHE[key]
    adjusted = _adjusted_qimage(design, layer)
    if adjusted is None:
        return None
    pil = imaging.qimage_to_pil(adjusted)
    fitted = imaging.resize_cover(pil, width, height, layer.fit)
    if layer.mask and layer.mask != "none":
        mask = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
        mask.fill(Qt.GlobalColor.transparent)
        painter = QPainter(mask)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#ffffff"))
        painter.drawPath(geometry.scaled(geometry.shape_path(layer.mask),
                                         width, height))
        painter.end()
        mask_pil = imaging.qimage_to_pil(mask)
        alpha = mask_pil.getchannel("A")
        if layer.mask_feather > 0.002:
            alpha = alpha.filter(ImageFilter.GaussianBlur(
                layer.mask_feather * min(width, height)))
        fitted.putalpha(ImageChops.multiply(fitted.getchannel("A"), alpha))
    result = imaging.pil_to_qimage(fitted)
    return _remember(_LAYER_IMAGE_CACHE, key, result, _MAX_LAYER_IMAGES)


# --------------------------------------------------------------------------
# background
# --------------------------------------------------------------------------
def _gradient_brush(rect: QRectF, color: str, color2: str,
                    angle: float) -> QBrush:
    start_color = _color(color)
    end_color = _color(color2 or color)
    if not color2:
        return QBrush(start_color)
    radians = math.radians(float(angle))
    dx, dy = math.cos(radians), math.sin(radians)
    length = abs(rect.width() * dx) + abs(rect.height() * dy)
    center = rect.center()
    gradient = QLinearGradient(
        QPointF(center.x() - dx * length / 2, center.y() - dy * length / 2),
        QPointF(center.x() + dx * length / 2, center.y() + dy * length / 2),
    )
    gradient.setColorAt(0.0, start_color)
    gradient.setColorAt(1.0, end_color)
    return QBrush(gradient)


def _paint_background(painter: QPainter, design: layers.Design,
                      width: int, height: int) -> None:
    settings = layers.merge(layers.default_background(), design.background)
    kind = settings.get("kind", "linear")
    rect = QRectF(0, 0, width, height)
    if kind == "transparent":
        return
    painter.save()
    if kind == "solid":
        painter.fillRect(rect, _color(settings.get("color", "#0a0a10")))
    elif kind == "radial":
        center = QPointF(width * 0.5, height * 0.46)
        radius = max(width, height) * 0.78
        gradient = QRadialGradient(center, radius)
        gradient.setColorAt(0.0, _color(settings.get("color", "#1b1230")))
        gradient.setColorAt(0.55, _color(settings.get("color", "#1b1230")).darker(130))
        gradient.setColorAt(1.0, _color(settings.get("color2", "#07070b")))
        painter.fillRect(rect, QBrush(gradient))
    elif kind == "image":
        image = _asset_qimage(design, settings.get("asset_id", ""))
        if image is not None:
            fitted = imaging.resize_cover(
                imaging.qimage_to_pil(image), width, height, "cover")
            painter.setOpacity(float(settings.get("opacity", 1.0)))
            painter.drawImage(rect, imaging.pil_to_qimage(fitted))
    else:
        painter.fillRect(rect, _gradient_brush(
            rect, settings.get("color", "#0a0a10"),
            settings.get("color2", "#26123a"),
            float(settings.get("angle", 135.0))))

    pattern = settings.get("pattern", "none")
    if pattern and pattern != "none":
        _paint_pattern(painter, rect, pattern,
                       settings.get("pattern_color", "#ffffff"),
                       float(settings.get("pattern_opacity", 0.07)),
                       float(settings.get("pattern_scale", 0.35)))

    vignette = float(settings.get("vignette", 0.0))
    if vignette > 0.001:
        center = QPointF(width * 0.5, height * 0.5)
        radius = math.hypot(width, height) * 0.58
        gradient = QRadialGradient(center, radius)
        gradient.setColorAt(0.0, QColor(0, 0, 0, 0))
        gradient.setColorAt(0.55, QColor(0, 0, 0, int(40 * vignette)))
        gradient.setColorAt(1.0, QColor(0, 0, 0, int(210 * vignette)))
        painter.fillRect(rect, QBrush(gradient))
    painter.restore()


def _paint_pattern(painter: QPainter, rect: QRectF, pattern: str,
                   color_text: str, opacity: float, scale: float) -> None:
    width, height = rect.width(), rect.height()
    base = max(8.0, min(width, height) * max(0.02, scale) * 0.10)
    color = _color(color_text)
    painter.save()
    painter.setClipRect(rect)
    painter.setOpacity(max(0.0, min(1.0, opacity)))
    painter.setBrush(color)
    painter.setPen(Qt.PenStyle.NoPen)
    line_pen = QPen(color, max(1.0, min(width, height) * 0.0016))
    line_pen.setCapStyle(Qt.PenCapStyle.RoundCap)

    if pattern == "dots":
        radius = base * 0.14
        y = base * 0.5
        while y < height + base:
            x = base * 0.5
            while x < width + base:
                painter.drawEllipse(QPointF(x, y), radius, radius)
                x += base
            y += base
    elif pattern == "grid":
        painter.setPen(line_pen)
        x = 0.0
        while x <= width:
            painter.drawLine(QPointF(x, 0), QPointF(x, height))
            x += base
        y = 0.0
        while y <= height:
            painter.drawLine(QPointF(0, y), QPointF(width, y))
            y += base
    elif pattern == "diagonal":
        painter.setPen(line_pen)
        diagonal = math.hypot(width, height)
        painter.translate(rect.center())
        painter.rotate(-45)
        offset = -diagonal
        while offset <= diagonal:
            painter.drawLine(QPointF(offset, -diagonal),
                             QPointF(offset, diagonal))
            offset += base
    elif pattern == "rings":
        painter.setPen(line_pen)
        center = rect.center()
        radius = base
        while radius < math.hypot(width, height) * 0.6:
            painter.drawEllipse(center, radius, radius)
            radius += base
    elif pattern == "hexagons":
        painter.setPen(line_pen)
        size = base * 0.52
        step_x = size * 1.74
        step_y = size * 1.5
        row = 0
        y = -size
        while y < height + size:
            offset = (step_x / 2) if row % 2 else 0.0
            x = -size + offset
            while x < width + size:
                points = []
                for index in range(6):
                    angle = math.radians(60 * index)
                    points.append(QPointF(x + math.cos(angle) * size,
                                          y + math.sin(angle) * size))
                painter.drawPolygon(QPolygonF(points))
                x += step_x
            y += step_y
            row += 1
    elif pattern == "triangles":
        size = base * 0.75
        row = 0
        y = 0.0
        while y < height + size:
            x = 0.0
            while x < width + size:
                if (row + int(x / size)) % 2 == 0:
                    points = [QPointF(x, y + size), QPointF(x + size, y + size),
                              QPointF(x + size / 2, y)]
                else:
                    points = [QPointF(x, y), QPointF(x + size, y),
                              QPointF(x + size / 2, y + size)]
                painter.drawPolygon(QPolygonF(points))
                x += size
            y += size * 0.86
            row += 1
    elif pattern == "scanlines":
        painter.setPen(QPen(color, max(1.0, base * 0.07)))
        y = 0.0
        while y < height:
            painter.drawLine(QPointF(0, y), QPointF(width, y))
            y += max(3.0, base * 0.28)
    elif pattern == "stars":
        rng = random.Random(11)
        step = base * 2.6
        y = step * 0.4
        while y < height:
            x = step * 0.4
            while x < width:
                size = base * (0.10 + rng.random() * 0.16)
                cx = x + (rng.random() - 0.5) * step * 0.5
                cy = y + (rng.random() - 0.5) * step * 0.5
                sparkle = QPainterPath()
                sparkle.moveTo(cx, cy - size)
                sparkle.quadTo(cx + size * 0.18, cy - size * 0.18,
                               cx + size, cy)
                sparkle.quadTo(cx + size * 0.18, cy + size * 0.18,
                               cx, cy + size)
                sparkle.quadTo(cx - size * 0.18, cy + size * 0.18,
                               cx - size, cy)
                sparkle.quadTo(cx - size * 0.18, cy - size * 0.18,
                               cx, cy - size)
                painter.drawPath(sparkle)
                x += step
            y += step
    elif pattern == "waves":
        painter.setPen(line_pen)
        step = max(12.0, base * 0.9)
        y = 0.0
        while y < height:
            wave = QPainterPath()
            wave.moveTo(0, y)
            x = 0.0
            while x <= width:
                wave.lineTo(x, y + math.sin(x / step * math.pi) * step * 0.28)
                x += 4.0
            painter.drawPath(wave)
            y += step
    elif pattern == "rays":
        center = rect.center()
        rays = 28
        painter.setPen(QPen(color, max(1.0, base * 0.22)))
        radius = math.hypot(width, height)
        for index in range(rays):
            angle = index * math.tau / rays
            painter.drawLine(
                QPointF(center.x() + math.cos(angle) * base * 0.5,
                        center.y() + math.sin(angle) * base * 0.5),
                QPointF(center.x() + math.cos(angle) * radius,
                        center.y() + math.sin(angle) * radius))
    elif pattern == "noise":
        size = 128
        rng = np.random.default_rng(1337)
        noise = rng.integers(0, 256, (size, size), dtype=np.uint8)
        rgba = np.zeros((size, size, 4), dtype=np.uint8)
        rgba[..., 0] = color.red()
        rgba[..., 1] = color.green()
        rgba[..., 2] = color.blue()
        rgba[..., 3] = noise
        tile = QImage(rgba.tobytes(), size, size, size * 4,
                      QImage.Format.Format_RGBA8888).copy()
        painter.drawTiledPixmap(rect, QPixmap.fromImage(tile))
    painter.restore()


# --------------------------------------------------------------------------
# text
# --------------------------------------------------------------------------
def _font_for(layer: "layers.TextLayer", height: int) -> QFont:
    font = QFont(layer.font or "Bahnschrift")
    font.setPixelSize(max(1, int(round(layer.size * height))))
    try:
        font.setWeight(QFont.Weight(int(max(100, min(900, layer.weight)))))
    except ValueError:
        font.setBold(True)
    font.setItalic(bool(layer.italic))
    if abs(layer.letter_spacing) > 0.0005:
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing,
                              layer.letter_spacing * font.pixelSize())
    return font


def _wrap_lines(text: str, metrics: QFontMetricsF, max_width: float) -> list[str]:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        if not paragraph:
            lines.append("")
            continue
        words = paragraph.split(" ")
        current = ""
        for word in words:
            candidate = word if not current else f"{current} {word}"
            if not current or metrics.horizontalAdvance(candidate) <= max_width:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return lines


def _paint_text(painter: QPainter, layer: "layers.TextLayer",
                rect: QRectF, height: int) -> None:
    text = layer.text
    if layer.uppercase:
        text = text.upper()
    if not text:
        return
    font = _font_for(layer, height)
    metrics = QFontMetricsF(font)
    max_width = max(1.0, rect.width() - font.pixelSize() * 0.08)
    lines = _wrap_lines(text, metrics, max_width) if layer.wrap else text.split("\n")
    line_height = font.pixelSize() * max(0.7, layer.line_height)
    total = line_height * max(1, len(lines))
    if layer.valign == "top":
        top = rect.top()
    elif layer.valign == "bottom":
        top = rect.bottom() - total
    else:
        top = rect.center().y() - total / 2
    ascent = metrics.ascent()

    painter.save()
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
    fill = QBrush(_color(layer.color))
    pen = None
    if layer.stroke_color and layer.stroke_width > 0.0005:
        pen = QPen(_color(layer.stroke_color),
                   max(1.0, layer.stroke_width * font.pixelSize()))
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)

    for index, line in enumerate(lines):
        if not line:
            continue
        width = metrics.horizontalAdvance(line)
        if layer.align == "left":
            x = rect.left()
        elif layer.align == "right":
            x = rect.right() - width
        else:
            x = rect.center().x() - width / 2
        baseline = top + index * line_height + ascent
        if pen is not None:
            path = QPainterPath()
            path.addText(QPointF(x, baseline), font, line)
            painter.strokePath(path, pen)
            painter.fillPath(path, fill)
        else:
            painter.setFont(font)
            painter.setPen(QPen(_color(layer.color)))
            painter.drawText(QPointF(x, baseline), line)
    painter.restore()


# --------------------------------------------------------------------------
# layer content
# --------------------------------------------------------------------------
def _layer_transform(painter: QPainter, layer: layers.Layer,
                     width: int, height: int) -> QRectF:
    rect = QRectF(layer.x * width, layer.y * height,
                  layer.w * width, layer.h * height)
    painter.translate(rect.center())
    painter.rotate(layer.rotation)
    painter.scale(-1.0 if layer.flip_h else 1.0,
                  -1.0 if layer.flip_v else 1.0)
    painter.translate(-rect.center())
    return rect


def _paint_content(painter: QPainter, design: layers.Design,
                   layer: layers.Layer, width: int, height: int) -> None:
    if isinstance(layer, layers.ShapeLayer):
        rect = QRectF(layer.x * width, layer.y * height,
                      layer.w * width, layer.h * height)
        path = QTransform().translate(rect.x(), rect.y()).scale(
            max(0.001, rect.width()), max(0.001, rect.height())).map(
            geometry.shape_path(layer.shape))
        if layer.stroke and layer.stroke_width > 0.0005:
            pen = QPen(_color(layer.stroke),
                       max(1.0, layer.stroke_width * min(rect.width(), rect.height())))
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(_gradient_brush(rect, layer.fill, layer.fill2,
                                         layer.gradient_angle)
                         if layer.gradient else QBrush(_color(layer.fill)))
        painter.drawPath(path)
    elif isinstance(layer, layers.IconLayer):
        rect = QRectF(layer.x * width, layer.y * height,
                      layer.w * width, layer.h * height)
        path = QTransform().translate(rect.x(), rect.y()).scale(
            max(0.001, rect.width()), max(0.001, rect.height())).map(
            geometry.icon_path(layer.icon))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(_gradient_brush(rect, layer.color, layer.fill2,
                                         layer.gradient_angle)
                         if layer.gradient else QBrush(_color(layer.color)))
        painter.drawPath(path)
    elif isinstance(layer, layers.TextLayer):
        rect = QRectF(layer.x * width, layer.y * height,
                      layer.w * width, layer.h * height)
        _paint_text(painter, layer, rect, height)
    elif isinstance(layer, layers.ImageLayer):
        rect = QRectF(layer.x * width, layer.y * height,
                      layer.w * width, layer.h * height)
        image = _layer_image(design, layer, int(round(rect.width())),
                             int(round(rect.height())))
        if image is None:
            painter.save()
            painter.setPen(QPen(_color("#ff5c72"), max(1.0, min(width, height) * 0.004),
                                Qt.PenStyle.DashLine))
            painter.setBrush(QColor(255, 92, 114, 22))
            painter.drawRect(rect)
            painter.restore()
            return
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.drawImage(rect, image)


def _rotated_bounds(layer: layers.Layer, width: int, height: int) -> QRectF:
    rect = QRectF(layer.x * width, layer.y * height,
                  layer.w * width, layer.h * height)
    if abs(layer.rotation) < 0.001:
        return rect
    transform = QTransform()
    transform.translate(rect.center().x(), rect.center().y())
    transform.rotate(layer.rotation)
    transform.translate(-rect.center().x(), -rect.center().y())
    return transform.mapRect(rect)


def _effects_on(layer: layers.Layer) -> tuple[bool, bool]:
    shadow = layer.effects.get("shadow", {})
    glow = layer.effects.get("glow", {})
    return bool(shadow.get("enabled")), bool(glow.get("enabled"))


def _styled_layer(design: layers.Design, layer: layers.Layer,
                  width: int, height: int) -> tuple[QImage, QPointF]:
    """Render a layer plus its shadow and glow, with transparent padding."""
    shadow_on, glow_on = _effects_on(layer)
    shortest = min(width, height)
    shadow = layer.effects.get("shadow", {})
    glow = layer.effects.get("glow", {})
    blur = max(0.0, float(shadow.get("blur", 0.0))) * shortest
    glow_size = max(0.0, float(glow.get("size", 0.0))) * shortest
    dx = float(shadow.get("dx", 0.0)) * width
    dy = float(shadow.get("dy", 0.0)) * height
    margin = 2.0
    if shadow_on:
        margin = max(margin, blur * 2.4 + max(abs(dx), abs(dy)))
    if glow_on:
        margin = max(margin, glow_size * 2.6)
    margin = math.ceil(margin) + 2

    bounds = _rotated_bounds(layer, width, height)
    payload = layer.to_dict()
    for key in ("x", "y", "id", "name", "visible", "locked", "opacity", "blend"):
        payload.pop(key, None)
    fingerprint = json.dumps({
        "layer": payload, "width": width, "height": height,
    }, sort_keys=True)
    cache_key = hashlib.sha1(fingerprint.encode("utf-8")).hexdigest()
    origin = QPointF(bounds.x() - margin, bounds.y() - margin)
    if cache_key in _STYLED_CACHE:
        cached = _STYLED_CACHE[cache_key]
        _STYLED_CACHE.move_to_end(cache_key)
        return cached, origin

    temp = QImage(int(math.ceil(bounds.width())) + margin * 2,
                  int(math.ceil(bounds.height())) + margin * 2,
                  QImage.Format.Format_ARGB32_Premultiplied)
    temp.fill(Qt.GlobalColor.transparent)
    painter = QPainter(temp)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    painter.translate(margin - bounds.x(), margin - bounds.y())
    _layer_transform(painter, layer, width, height)
    _paint_content(painter, design, layer, width, height)
    painter.end()

    content = imaging.qimage_to_pil(temp)
    composed = content
    if glow_on:
        radius = max(1.0, glow_size * 1.15)
        alpha = content.getchannel("A").filter(ImageFilter.GaussianBlur(radius))
        glow_image = imaging.tint_mask(
            alpha, imaging.hex_to_rgb(glow.get("color", "#ff7a3d")),
            float(glow.get("opacity", 0.55)))
        composed = Image.alpha_composite(glow_image, composed)
    if shadow_on:
        radius = max(0.0, blur)
        alpha = content.getchannel("A")
        if radius >= 0.3:
            alpha = alpha.filter(ImageFilter.GaussianBlur(radius))
        shadow_image = imaging.tint_mask(
            alpha, imaging.hex_to_rgb(shadow.get("color", "#000000")),
            float(shadow.get("opacity", 0.55)))
        offset = Image.new("RGBA", composed.size, (0, 0, 0, 0))
        offset.paste(shadow_image, (int(round(dx)), int(round(dy))))
        composed = Image.alpha_composite(offset, composed)

    result = imaging.pil_to_qimage(composed)
    _remember(_STYLED_CACHE, cache_key, result, _MAX_STYLED)
    return result, origin


def _paint_layer(painter: QPainter, design: layers.Design,
                 layer: layers.Layer, width: int, height: int) -> None:
    if not layer.visible or layer.opacity <= 0.001:
        return
    shadow_on, glow_on = _effects_on(layer)
    needs_composite = (shadow_on or glow_on or layer.blend != "normal"
                       or layer.opacity < 0.999)
    if needs_composite:
        image, origin = _styled_layer(design, layer, width, height)
        painter.save()
        painter.setOpacity(max(0.0, min(1.0, layer.opacity)))
        painter.setCompositionMode(_composition(layer.blend))
        painter.drawImage(origin, image)
        painter.restore()
        return

    painter.save()
    _layer_transform(painter, layer, width, height)
    _paint_content(painter, design, layer, width, height)
    painter.restore()


# --------------------------------------------------------------------------
# public rendering
# --------------------------------------------------------------------------
def render_design(design: layers.Design, width: int | None = None,
                  height: int | None = None,
                  background: bool = True) -> QImage:
    out_width = max(1, int(width or design.width))
    out_height = max(1, int(height or design.height))
    image = QImage(out_width, out_height, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    if background:
        _paint_background(painter, design, out_width, out_height)
    for layer in design.layers:
        _paint_layer(painter, design, layer, out_width, out_height)
    painter.end()
    return image


def render_thumbnail(design: layers.Design, max_side: int = 300,
                     background: bool = True) -> QImage:
    max_side = max(32, int(max_side))
    if design.width >= design.height:
        width = max_side
        height = max(1, round(max_side * design.height / design.width))
    else:
        height = max_side
        width = max(1, round(max_side * design.width / design.height))
    return render_design(design, width, height, background=background)


def render_pixmap(design: layers.Design, width: int | None = None,
                  height: int | None = None, background: bool = True) -> QPixmap:
    return QPixmap.fromImage(render_design(design, width, height,
                                           background=background))


def save_image(design: layers.Design, path: str, width: int | None = None,
               height: int | None = None, quality: int = 92,
               background: bool = True) -> bool:
    image = render_design(design, width, height, background=background)
    suffix = str(path).lower().rsplit(".", 1)[-1]
    fmt = {"jpg": "JPEG", "jpeg": "JPEG", "png": "PNG", "webp": "WEBP",
           "bmp": "BMP", "tif": "TIFF", "tiff": "TIFF"}.get(suffix, "PNG")
    if fmt == "JPEG" and image.hasAlphaChannel() and not background:
        flattened = QImage(image.size(), QImage.Format.Format_RGB32)
        flattened.fill(Qt.GlobalColor.black)
        painter = QPainter(flattened)
        painter.drawImage(0, 0, image)
        painter.end()
        image = flattened
    if fmt in ("JPEG", "WEBP"):
        return image.save(path, fmt, int(max(10, min(100, quality))))
    return image.save(path, fmt)


def layer_at(design: layers.Design, x: float, y: float,
             width: int, height: int) -> layers.Layer | None:
    """Topmost layer under a canvas-pixel point."""
    for layer in reversed(design.layers):
        if not layer.visible:
            continue
        rect = QRectF(layer.x * width, layer.y * height,
                      layer.w * width, layer.h * height)
        center = rect.center()
        transform = QTransform()
        transform.translate(center.x(), center.y())
        transform.rotate(-layer.rotation)
        transform.translate(-center.x(), -center.y())
        local = transform.map(QPointF(x, y))
        if rect.contains(local):
            return layer
    return None


def layer_corners(layer: layers.Layer, width: int, height: int) -> list[QPointF]:
    rect = QRectF(layer.x * width, layer.y * height,
                  layer.w * width, layer.h * height)
    center = rect.center()
    transform = QTransform()
    transform.translate(center.x(), center.y())
    transform.rotate(layer.rotation)
    transform.translate(-center.x(), -center.y())
    points = [rect.topLeft(), rect.topRight(), rect.bottomRight(), rect.bottomLeft()]
    return [transform.map(point) for point in points]
