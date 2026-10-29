"""Vector geometry for shapes and icons.

Every builder returns a ``QPainterPath`` fitted to the unit square (0..1).
The renderer scales that path into a layer's rectangle, so the same art works
at thumbnail size and on a 4K canvas.

The library is deliberately broad. Hand-drawn marks sit beside procedural
families (polygons, stars, frames, seals, blobs) so the browser always has
something close to the idea in your head. User-imported SVG shapes and icons
join the same lookup, which is why ``shape_path`` and ``icon_path`` fall back
to :mod:`umbraforge.custom_art` before giving up.
"""

from __future__ import annotations

from math import cos, pi, sin

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QPainterPath, QPainterPathStroker, QTransform

from . import custom_art
from .icon_shelf import ICON_SVG

Point = tuple[float, float]


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------
def _poly(points: list[Point], close: bool = True) -> QPainterPath:
    path = QPainterPath()
    if not points:
        return path
    path.moveTo(*points[0])
    for point in points[1:]:
        path.lineTo(*point)
    if close:
        path.closeSubpath()
    return path


def _regular(sides: int, radius: float = 0.5, rotation: float = -90.0,
             cx: float = 0.5, cy: float = 0.5) -> QPainterPath:
    points = []
    for index in range(sides):
        angle = (rotation + index * 360.0 / sides) * pi / 180.0
        points.append((cx + cos(angle) * radius, cy + sin(angle) * radius))
    return _poly(points)


def _star(points: int, inner: float = 0.42, outer: float = 0.5,
          rotation: float = -90.0, cx: float = 0.5,
          cy: float = 0.5) -> QPainterPath:
    pts: list[Point] = []
    for index in range(points * 2):
        angle = (rotation + index * 180.0 / points) * pi / 180.0
        radius = outer if index % 2 == 0 else inner
        pts.append((cx + cos(angle) * radius, cy + sin(angle) * radius))
    return _poly(pts)


def _ellipse(cx: float, cy: float, rx: float, ry: float) -> QPainterPath:
    path = QPainterPath()
    path.addEllipse(QPointF(cx, cy), rx, ry)
    return path


def _rect(x: float, y: float, w: float, h: float,
          radius: float = 0.0) -> QPainterPath:
    path = QPainterPath()
    if radius > 0:
        path.addRoundedRect(QRectF(x, y, w, h), radius, radius)
    else:
        path.addRect(QRectF(x, y, w, h))
    return path


def _stroked(path: QPainterPath, width: float) -> QPainterPath:
    stroker = QPainterPathStroker()
    stroker.setWidth(width)
    stroker.setCapStyle(Qt.PenCapStyle.RoundCap)
    stroker.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    return stroker.createStroke(path)


def _line(points: list[Point], width: float, close: bool = False) -> QPainterPath:
    return _stroked(_poly(points, close), width)


def _arc_band(cx: float, cy: float, rx: float, ry: float, start: float,
              span: float, width: float) -> QPainterPath:
    path = QPainterPath()
    path.arcMoveTo(QRectF(cx - rx, cy - ry, rx * 2, ry * 2), start)
    path.arcTo(QRectF(cx - rx, cy - ry, rx * 2, ry * 2), start, span)
    return _stroked(path, width)


def _rotated(path: QPainterPath, angle: float, cx: float = 0.5,
             cy: float = 0.5) -> QPainterPath:
    return QTransform().translate(cx, cy).rotate(angle).translate(
        -cx, -cy).map(path)


def _scaled_to(path: QPainterPath, x: float, y: float, w: float,
               h: float) -> QPainterPath:
    bounds = path.boundingRect()
    if bounds.width() <= 1e-9 or bounds.height() <= 1e-9:
        return QPainterPath(path)
    transform = QTransform()
    transform.translate(x, y)
    transform.scale(w / bounds.width(), h / bounds.height())
    transform.translate(-bounds.x(), -bounds.y())
    return transform.map(path)


def _ring_path(outer: QPainterPath, inner: QPainterPath) -> QPainterPath:
    return outer.subtracted(inner)


def _svg(data: str, stroke: float = 0.0) -> QPainterPath:
    """Build a normalized icon/shape from compact SVG path data.

    Stroke widths are given in *unit* space (``0.08`` is 8% of the icon), so
    the same table works at every size. Normalize first, then stroke, which
    keeps thin line icons visually consistent with the handcrafted marks.
    """
    path = custom_art.parse_path_data(data)
    if path.isEmpty():
        return path
    path = custom_art.normalize(path, margin=0.05)
    if stroke > 0:
        path = _stroked(path, stroke)
    return path


def _blob(seed: int, points: int = 8, wobble: float = 0.14) -> QPainterPath:
    """A smooth organic blob with deterministic radii."""
    radii: list[float] = []
    value = seed * 2654435761 % 4294967296
    for _ in range(points):
        value = (value * 1103515245 + 12345) % 4294967296
        radii.append(1.0 + ((value / 4294967296.0) * 2.0 - 1.0) * wobble)
    path = QPainterPath()
    first = QPointF(0.5 + radii[0] * 0.40, 0.5)
    path.moveTo(first)
    for index in range(points):
        angle_a = index * 2 * pi / points
        angle_b = (index + 1) * 2 * pi / points
        mid = (angle_a + angle_b) / 2
        control = QPointF(0.5 + cos(mid) * radii[index] * 0.52,
                          0.5 + sin(mid) * radii[index] * 0.52)
        end = QPointF(0.5 + cos(angle_b) * radii[(index + 1) % points] * 0.40,
                      0.5 + sin(angle_b) * radii[(index + 1) % points] * 0.40)
        path.quadTo(control, end)
    path.closeSubpath()
    return path


# --------------------------------------------------------------------------
# basic and geometric shapes
# --------------------------------------------------------------------------
def _shape_circle() -> QPainterPath:
    return _ellipse(0.5, 0.5, 0.5, 0.5)


def _shape_ring() -> QPainterPath:
    return _ellipse(0.5, 0.5, 0.5, 0.5).subtracted(_ellipse(0.5, 0.5, 0.32, 0.32))


def _shape_rounded() -> QPainterPath:
    return _rect(0.0, 0.0, 1.0, 1.0, 0.22)


def _shape_capsule() -> QPainterPath:
    return _rect(0.0, 0.0, 1.0, 1.0, 0.5)


def _shape_square() -> QPainterPath:
    return _rect(0.0, 0.0, 1.0, 1.0)


def _shape_triangle() -> QPainterPath:
    return _poly([(0.5, 0.0), (1.0, 1.0), (0.0, 1.0)])


def _shape_diamond() -> QPainterPath:
    return _poly([(0.5, 0.0), (1.0, 0.5), (0.5, 1.0), (0.0, 0.5)])


def _shape_pentagon() -> QPainterPath:
    return _regular(5)


def _shape_hexagon() -> QPainterPath:
    return _regular(6)


def _shape_hex_flat() -> QPainterPath:
    return _regular(6, rotation=0.0)


def _shape_octagon() -> QPainterPath:
    return _regular(8, rotation=-67.5)


def _shape_star5() -> QPainterPath:
    return _star(5, inner=0.40)


def _shape_star6() -> QPainterPath:
    return _star(6, inner=0.52)


def _shape_star12() -> QPainterPath:
    return _star(12, inner=0.56)


def _shape_burst() -> QPainterPath:
    return _star(20, inner=0.58)


def _shape_shield() -> QPainterPath:
    path = QPainterPath()
    path.moveTo(0.5, 0.0)
    path.lineTo(1.0, 0.15)
    path.lineTo(1.0, 0.52)
    path.cubicTo(1.0, 0.76, 0.80, 0.91, 0.5, 1.0)
    path.cubicTo(0.20, 0.91, 0.0, 0.76, 0.0, 0.52)
    path.lineTo(0.0, 0.15)
    path.closeSubpath()
    return path


def _shape_chevron() -> QPainterPath:
    return _poly([(0.0, 0.10), (0.45, 0.10), (0.72, 0.5), (0.45, 0.90),
                  (0.0, 0.90), (0.28, 0.5)])


def _shape_arrow() -> QPainterPath:
    return _poly([(0.0, 0.30), (0.58, 0.30), (0.58, 0.08), (1.0, 0.50),
                  (0.58, 0.92), (0.58, 0.70), (0.0, 0.70)])


def _shape_cross() -> QPainterPath:
    return _poly([(0.33, 0.0), (0.67, 0.0), (0.67, 0.33), (1.0, 0.33),
                  (1.0, 0.67), (0.67, 0.67), (0.67, 1.0), (0.33, 1.0),
                  (0.33, 0.67), (0.0, 0.67), (0.0, 0.33), (0.33, 0.33)])


def _shape_half() -> QPainterPath:
    path = QPainterPath()
    path.moveTo(0.0, 1.0)
    path.arcTo(QRectF(0.0, 0.0, 1.0, 1.0), 180.0, -180.0)
    path.closeSubpath()
    return path


def _shape_teardrop() -> QPainterPath:
    path = QPainterPath()
    path.moveTo(0.5, 0.0)
    path.cubicTo(0.84, 0.24, 1.0, 0.50, 1.0, 0.68)
    path.cubicTo(1.0, 0.87, 0.78, 1.0, 0.5, 1.0)
    path.cubicTo(0.22, 1.0, 0.0, 0.87, 0.0, 0.68)
    path.cubicTo(0.0, 0.50, 0.16, 0.24, 0.5, 0.0)
    path.closeSubpath()
    return path


def _shape_blob() -> QPainterPath:
    path = QPainterPath()
    path.moveTo(0.50, 0.02)
    path.cubicTo(0.77, 0.02, 0.98, 0.19, 0.98, 0.45)
    path.cubicTo(0.98, 0.70, 0.82, 0.96, 0.55, 0.98)
    path.cubicTo(0.31, 1.00, 0.02, 0.82, 0.02, 0.52)
    path.cubicTo(0.02, 0.23, 0.24, 0.02, 0.50, 0.02)
    path.closeSubpath()
    return path


def _shape_wave() -> QPainterPath:
    path = QPainterPath()
    path.moveTo(0.0, 0.22)
    path.cubicTo(0.20, 0.05, 0.30, 0.05, 0.50, 0.22)
    path.cubicTo(0.70, 0.39, 0.80, 0.39, 1.0, 0.22)
    path.lineTo(1.0, 0.78)
    path.cubicTo(0.80, 0.95, 0.70, 0.95, 0.50, 0.78)
    path.cubicTo(0.30, 0.61, 0.20, 0.61, 0.0, 0.78)
    path.closeSubpath()
    return path


def _shape_square_cut() -> QPainterPath:
    cut = 0.18
    return _poly([(cut, 0.0), (1.0 - cut, 0.0), (1.0, cut), (1.0, 1.0 - cut),
                  (1.0 - cut, 1.0), (cut, 1.0), (0.0, 1.0 - cut), (0.0, cut)])


def _shape_plus_round() -> QPainterPath:
    return _rect(0.32, 0.0, 0.36, 1.0, 0.10).united(
        _rect(0.0, 0.32, 1.0, 0.36, 0.10))


def _shape_minus_round() -> QPainterPath:
    return _rect(0.0, 0.32, 1.0, 0.36, 0.18)


def _shape_equals_round() -> QPainterPath:
    return _rect(0.0, 0.22, 1.0, 0.24, 0.12).united(
        _rect(0.0, 0.54, 1.0, 0.24, 0.12))


# --------------------------------------------------------------------------
# frames and panels
# --------------------------------------------------------------------------
def _frame(inset: float = 0.10, radius: float = 0.0,
           outer_radius: float = 0.0) -> QPainterPath:
    outer = _rect(0.0, 0.0, 1.0, 1.0, outer_radius)
    inner = _rect(inset, inset, 1.0 - inset * 2, 1.0 - inset * 2, radius)
    return outer.subtracted(inner)


def _shape_frame() -> QPainterPath:
    return _frame(0.10)


def _shape_frame_round() -> QPainterPath:
    return _frame(0.10, 0.10, 0.20)


def _shape_frame_thick() -> QPainterPath:
    return _frame(0.22, 0.22, 0.26)


def _shape_frame_corner() -> QPainterPath:
    arm, weight = 0.26, 0.055
    path = QPainterPath()
    for x in (0.0, 1.0 - arm):
        for y in (0.0, 1.0 - arm):
            path = path.united(
                _rect(x, y, arm, weight).united(
                    _rect(x if x == 0 else x + arm - weight,
                          y, weight, arm)))
    return path


def _shape_split_v() -> QPainterPath:
    return _rect(0.0, 0.0, 0.44, 1.0, 0.10).united(
        _rect(0.56, 0.0, 0.44, 1.0, 0.10))


def _shape_split_h() -> QPainterPath:
    return _rect(0.0, 0.0, 1.0, 0.44, 0.10).united(
        _rect(0.0, 0.56, 1.0, 0.44, 0.10))


def _shape_grid_2x2() -> QPainterPath:
    gap, size = 0.05, 0.45
    path = QPainterPath()
    for row in range(2):
        for col in range(2):
            path = path.united(_rect(col * (size + gap), row * (size + gap),
                                     size, size, 0.06))
    return path


def _shape_grid_3x3() -> QPainterPath:
    gap, size = 0.04, 0.3067
    path = QPainterPath()
    for row in range(3):
        for col in range(3):
            path = path.united(_rect(col * (size + gap), row * (size + gap),
                                     size, size, 0.035))
    return path


def _shape_rows_3() -> QPainterPath:
    path = QPainterPath()
    for index in range(3):
        path = path.united(_rect(0.0, index * 0.36, 1.0, 0.28, 0.07))
    return path


def _shape_cols_3() -> QPainterPath:
    path = QPainterPath()
    for index in range(3):
        path = path.united(_rect(index * 0.36, 0.0, 0.28, 1.0, 0.07))
    return path


def _shape_arch() -> QPainterPath:
    path = QPainterPath()
    path.moveTo(0.0, 1.0)
    path.lineTo(0.0, 0.5)
    path.arcTo(QRectF(0.0, 0.0, 1.0, 1.0), 180.0, -180.0)
    path.lineTo(1.0, 1.0)
    path.closeSubpath()
    return path


def _shape_arch_window() -> QPainterPath:
    outer = _shape_arch()
    inner = _shape_arch()
    inner = QTransform().translate(0.5, 0.52).scale(0.72, 0.72).translate(
        -0.5, -0.52).map(inner)
    return outer.subtracted(inner)


def _shape_window() -> QPainterPath:
    frame = _frame(0.09)
    bars = _rect(0.465, 0.09, 0.07, 0.82).united(
        _rect(0.09, 0.465, 0.82, 0.07))
    return frame.united(bars)


def _shape_window_round() -> QPainterPath:
    outer = _ellipse(0.5, 0.5, 0.5, 0.5)
    inner = _ellipse(0.5, 0.5, 0.40, 0.40)
    bars = _rect(0.465, 0.10, 0.07, 0.80).united(
        _rect(0.10, 0.465, 0.80, 0.07))
    return outer.subtracted(inner).united(bars)


def _shape_ticket() -> QPainterPath:
    body = _rect(0.0, 0.12, 1.0, 0.76, 0.06)
    notch = _ellipse(0.0, 0.5, 0.11, 0.14).united(
        _ellipse(1.0, 0.5, 0.11, 0.14))
    return body.subtracted(notch)


def _shape_panel_top() -> QPainterPath:
    return _rect(0.0, 0.0, 1.0, 0.28, 0.06).united(
        _rect(0.0, 0.28, 1.0, 0.72, 0.02))


def _shape_panel_bottom() -> QPainterPath:
    return _rect(0.0, 0.72, 1.0, 0.28, 0.06).united(
        _rect(0.0, 0.0, 1.0, 0.72, 0.02))


# --------------------------------------------------------------------------
# arrows
# --------------------------------------------------------------------------
def _arrow_shape(angle: float) -> QPainterPath:
    base = _poly([(0.0, 0.30), (0.58, 0.30), (0.58, 0.08), (1.0, 0.50),
                  (0.58, 0.92), (0.58, 0.70), (0.0, 0.70)])
    return _rotated(base, angle)


def _chevron_shape(angle: float) -> QPainterPath:
    return _rotated(_shape_chevron(), angle)


def _shape_arrow_left() -> QPainterPath:
    return _arrow_shape(180.0)


def _shape_arrow_right() -> QPainterPath:
    return _arrow_shape(0.0)


def _shape_arrow_up() -> QPainterPath:
    return _arrow_shape(-90.0)


def _shape_arrow_down() -> QPainterPath:
    return _arrow_shape(90.0)


def _shape_arrow_double() -> QPainterPath:
    right = _arrow_shape(0.0)
    left = _arrow_shape(180.0)
    return right.united(left)


def _shape_arrow_bend() -> QPainterPath:
    shaft = _line([(0.12, 0.82), (0.12, 0.34), (0.64, 0.34)], 0.20)
    head = _poly([(0.58, 0.16), (0.94, 0.34), (0.58, 0.52)])
    return shaft.united(head)


def _shape_arrow_curve() -> QPainterPath:
    curve = QPainterPath()
    curve.moveTo(0.10, 0.86)
    curve.cubicTo(0.10, 0.30, 0.44, 0.20, 0.72, 0.20)
    head = _poly([(0.68, 0.04), (0.98, 0.20), (0.68, 0.36)])
    return _stroked(curve, 0.18).united(head)


def _shape_chevron_left() -> QPainterPath:
    return _chevron_shape(180.0)


def _shape_chevron_right() -> QPainterPath:
    return _chevron_shape(0.0)


def _shape_chevron_up() -> QPainterPath:
    return _chevron_shape(-90.0)


def _shape_chevron_down() -> QPainterPath:
    return _chevron_shape(90.0)


def _shape_chevron_double() -> QPainterPath:
    return _shape_chevron().united(
        QTransform().translate(0.34, 0.0).map(_shape_chevron()))


def _shape_chevron_triple() -> QPainterPath:
    path = _shape_chevron()
    for step in (0.18, 0.36):
        path = path.united(QTransform().translate(step, 0.0).map(
            _shape_chevron()))
    return path


def _shape_caret() -> QPainterPath:
    return _poly([(0.5, 0.82), (0.0, 0.22), (0.22, 0.06), (0.5, 0.52),
                  (0.78, 0.06), (1.0, 0.22)])


def _shape_pointer() -> QPainterPath:
    return _poly([(0.18, 0.02), (0.82, 0.50), (0.52, 0.55), (0.66, 0.94),
                  (0.48, 1.0), (0.34, 0.60), (0.14, 0.82)])


def _shape_cursor() -> QPainterPath:
    return _poly([(0.20, 0.04), (0.20, 0.86), (0.42, 0.66), (0.58, 0.98),
                  (0.72, 0.90), (0.56, 0.60), (0.84, 0.56)])


# --------------------------------------------------------------------------
# banners and badges
# --------------------------------------------------------------------------
def _shape_banner() -> QPainterPath:
    return _poly([(0.0, 0.10), (1.0, 0.10), (1.0, 0.78), (0.5, 0.96),
                  (0.0, 0.78)])


def _shape_banner_notch() -> QPainterPath:
    return _poly([(0.0, 0.10), (1.0, 0.10), (1.0, 0.90), (0.5, 0.72),
                  (0.0, 0.90)])


def _shape_banner_swallow() -> QPainterPath:
    return _poly([(0.0, 0.10), (1.0, 0.10), (1.0, 0.90), (0.5, 0.70),
                  (0.0, 0.90), (0.22, 0.50)])


def _shape_ribbon() -> QPainterPath:
    path = _rect(0.08, 0.22, 0.84, 0.50)
    left = _poly([(0.08, 0.30), (0.0, 0.30), (0.0, 0.68), (0.08, 0.68)])
    right = _poly([(0.92, 0.30), (1.0, 0.30), (1.0, 0.68), (0.92, 0.68)])
    return path.united(left).united(right)


def _shape_ribbon_fold() -> QPainterPath:
    band = _poly([(0.12, 0.20), (0.88, 0.20), (0.88, 0.70), (0.12, 0.70)])
    left = _poly([(0.12, 0.70), (0.12, 0.94), (0.34, 0.80), (0.12, 0.78)])
    right = _poly([(0.88, 0.70), (0.88, 0.94), (0.66, 0.80), (0.88, 0.78)])
    return band.united(left).united(right)


def _shape_pennant() -> QPainterPath:
    return _poly([(0.0, 0.10), (1.0, 0.10), (0.62, 0.94), (0.0, 0.94)])


def _shape_flag() -> QPainterPath:
    pole = _rect(0.06, 0.0, 0.075, 1.0, 0.03)
    cloth = _poly([(0.135, 0.03), (0.96, 0.03), (0.84, 0.30),
                   (0.96, 0.57), (0.135, 0.57)])
    return pole.united(cloth)


def _shape_tag() -> QPainterPath:
    body = _poly([(0.0, 0.18), (0.68, 0.18), (1.0, 0.50),
                  (0.68, 0.82), (0.0, 0.82)])
    return body.subtracted(_ellipse(0.18, 0.50, 0.055, 0.055))


def _shape_tag_round() -> QPainterPath:
    body = _rect(0.0, 0.22, 0.74, 0.56, 0.28)
    point = _poly([(0.58, 0.34), (1.0, 0.50), (0.58, 0.66)])
    return body.united(point).subtracted(_ellipse(0.20, 0.50, 0.05, 0.05))


def _shape_plaque() -> QPainterPath:
    return _rect(0.0, 0.16, 1.0, 0.68, 0.07)


def _shape_plaque_round() -> QPainterPath:
    return _rect(0.0, 0.18, 1.0, 0.64, 0.30)


def _shape_seal() -> QPainterPath:
    path = _ellipse(0.5, 0.5, 0.42, 0.42)
    bump = 0.058
    for index in range(24):
        angle = index * 2 * pi / 24
        path = path.united(_ellipse(0.5 + cos(angle) * 0.43,
                                    0.5 + sin(angle) * 0.43, bump, bump))
    return path


def _shape_seal_scallop() -> QPainterPath:
    path = _ellipse(0.5, 0.5, 0.40, 0.40)
    for index in range(12):
        angle = index * 2 * pi / 12
        path = path.united(_ellipse(0.5 + cos(angle) * 0.43,
                                    0.5 + sin(angle) * 0.43, 0.10, 0.10))
    return path


def _shape_seal_star() -> QPainterPath:
    return _star(16, inner=0.40, outer=0.50)


def _shape_award() -> QPainterPath:
    seal = _ellipse(0.5, 0.36, 0.30, 0.30)
    left = _poly([(0.30, 0.50), (0.22, 1.0), (0.42, 0.86), (0.30, 0.50)])
    right = _poly([(0.70, 0.50), (0.78, 1.0), (0.58, 0.86), (0.70, 0.50)])
    return seal.united(left).united(right)


def _shape_rosette() -> QPainterPath:
    path = _ellipse(0.5, 0.5, 0.18, 0.18)
    for index in range(8):
        angle = index * 45.0
        petal = _ellipse(0.5, 0.29, 0.11, 0.16)
        path = path.united(_rotated(petal, angle))
    return path


def _shape_crest() -> QPainterPath:
    outer = _shape_shield()
    inner = QTransform().translate(0.5, 0.48).scale(0.74, 0.74).translate(
        -0.5, -0.48).map(outer)
    return outer.subtracted(inner)


def _shape_hex_badge() -> QPainterPath:
    outer = _regular(6, radius=0.5)
    inner = _regular(6, radius=0.37)
    return outer.subtracted(inner)


# --------------------------------------------------------------------------
# organic shapes
# --------------------------------------------------------------------------
def _shape_drop() -> QPainterPath:
    path = QPainterPath()
    path.moveTo(0.5, 0.0)
    path.cubicTo(0.72, 0.28, 0.98, 0.48, 0.98, 0.68)
    path.cubicTo(0.98, 0.86, 0.76, 1.0, 0.5, 1.0)
    path.cubicTo(0.24, 1.0, 0.02, 0.86, 0.02, 0.68)
    path.cubicTo(0.02, 0.48, 0.28, 0.28, 0.5, 0.0)
    path.closeSubpath()
    return path


def _shape_droplet() -> QPainterPath:
    path = QPainterPath()
    path.moveTo(0.5, 0.02)
    path.cubicTo(0.64, 0.24, 0.84, 0.46, 0.84, 0.66)
    path.cubicTo(0.84, 0.86, 0.69, 0.99, 0.5, 0.99)
    path.cubicTo(0.31, 0.99, 0.16, 0.86, 0.16, 0.66)
    path.cubicTo(0.16, 0.46, 0.36, 0.24, 0.5, 0.02)
    path.closeSubpath()
    return path


def _shape_petal() -> QPainterPath:
    path = QPainterPath()
    path.moveTo(0.5, 0.5)
    path.cubicTo(0.62, 0.12, 0.92, 0.04, 0.98, 0.06)
    path.cubicTo(0.98, 0.34, 0.82, 0.58, 0.5, 0.5)
    path.closeSubpath()
    return path


def _shape_leaf() -> QPainterPath:
    path = QPainterPath()
    path.moveTo(0.06, 0.94)
    path.cubicTo(0.08, 0.40, 0.38, 0.06, 0.96, 0.04)
    path.cubicTo(0.94, 0.60, 0.64, 0.94, 0.06, 0.94)
    path.closeSubpath()
    return path


def _shape_leaf_double() -> QPainterPath:
    return _shape_leaf().united(
        QTransform().translate(1.0, 0.0).scale(-1.0, 1.0).map(
            _shape_leaf()))


def _shape_crescent() -> QPainterPath:
    return _ellipse(0.5, 0.5, 0.48, 0.48).subtracted(
        _ellipse(0.64, 0.42, 0.42, 0.42))


def _shape_moon() -> QPainterPath:
    return _rotated(_shape_crescent(), -28.0)


def _shape_quarter() -> QPainterPath:
    path = QPainterPath()
    path.moveTo(0.0, 1.0)
    path.lineTo(0.0, 0.0)
    path.arcTo(QRectF(0.0, 0.0, 1.0, 1.0), 90.0, -90.0)
    path.closeSubpath()
    return path


def _shape_pie() -> QPainterPath:
    path = QPainterPath()
    path.moveTo(0.5, 0.5)
    path.arcTo(QRectF(0.0, 0.0, 1.0, 1.0), 90.0, -270.0)
    path.closeSubpath()
    return path


def _shape_pie3() -> QPainterPath:
    path = QPainterPath()
    path.moveTo(0.5, 0.5)
    path.arcTo(QRectF(0.0, 0.0, 1.0, 1.0), 90.0, -120.0)
    path.closeSubpath()
    return path


def _shape_pie6() -> QPainterPath:
    path = QPainterPath()
    path.moveTo(0.5, 0.5)
    path.arcTo(QRectF(0.0, 0.0, 1.0, 1.0), 90.0, -60.0)
    path.closeSubpath()
    return path


def _shape_heart() -> QPainterPath:
    path = QPainterPath()
    path.moveTo(0.5, 0.96)
    path.cubicTo(0.16, 0.72, 0.0, 0.50, 0.0, 0.32)
    path.cubicTo(0.0, 0.14, 0.14, 0.04, 0.30, 0.04)
    path.cubicTo(0.40, 0.04, 0.47, 0.09, 0.5, 0.18)
    path.cubicTo(0.53, 0.09, 0.60, 0.04, 0.70, 0.04)
    path.cubicTo(0.86, 0.04, 1.0, 0.14, 1.0, 0.32)
    path.cubicTo(1.0, 0.50, 0.84, 0.72, 0.5, 0.96)
    path.closeSubpath()
    return path


def _shape_club() -> QPainterPath:
    left = _ellipse(0.27, 0.34, 0.22, 0.22)
    right = _ellipse(0.73, 0.34, 0.22, 0.22)
    top = _ellipse(0.5, 0.62, 0.23, 0.23)
    stem = _poly([(0.42, 0.62), (0.58, 0.62), (0.64, 1.0),
                  (0.36, 1.0)])
    return left.united(right).united(top).united(stem)


def _shape_diamond_suit() -> QPainterPath:
    return _poly([(0.5, 0.02), (0.96, 0.5), (0.5, 0.98), (0.04, 0.5)])


def _shape_flame_form() -> QPainterPath:
    path = QPainterPath()
    path.moveTo(0.5, 0.01)
    path.cubicTo(0.62, 0.20, 0.84, 0.32, 0.88, 0.58)
    path.cubicTo(0.92, 0.82, 0.74, 1.0, 0.5, 1.0)
    path.cubicTo(0.24, 1.0, 0.06, 0.82, 0.08, 0.56)
    path.cubicTo(0.10, 0.36, 0.24, 0.24, 0.34, 0.10)
    path.cubicTo(0.36, 0.26, 0.40, 0.38, 0.48, 0.44)
    path.cubicTo(0.44, 0.28, 0.46, 0.12, 0.5, 0.01)
    path.closeSubpath()
    return path


def _shape_cloud() -> QPainterPath:
    base = _rect(0.16, 0.52, 0.68, 0.32, 0.16)
    return (base.united(_ellipse(0.32, 0.52, 0.22, 0.22))
            .united(_ellipse(0.54, 0.46, 0.26, 0.26))
            .united(_ellipse(0.72, 0.56, 0.18, 0.18)))


def _shape_splash() -> QPainterPath:
    return _star(14, inner=0.28, outer=0.5, rotation=-84.0)


def _shape_speech() -> QPainterPath:
    body = _rect(0.02, 0.06, 0.96, 0.66, 0.16)
    tail = _poly([(0.26, 0.66), (0.46, 0.66), (0.30, 0.98)])
    return body.united(tail)


def _shape_speech_round() -> QPainterPath:
    body = _ellipse(0.5, 0.42, 0.48, 0.34)
    tail = _poly([(0.28, 0.66), (0.48, 0.64), (0.32, 0.98)])
    return body.united(tail)


def _shape_thought() -> QPainterPath:
    body = _ellipse(0.54, 0.38, 0.38, 0.26)
    small = _ellipse(0.34, 0.40, 0.17, 0.15)
    bubble = _ellipse(0.20, 0.72, 0.09, 0.08)
    bubble2 = _ellipse(0.11, 0.88, 0.05, 0.05)
    return body.united(small).united(bubble).united(bubble2)


def _shape_speech_burst() -> QPainterPath:
    body = _star(14, inner=0.52, outer=0.5, rotation=-90.0)
    return body


def _shape_wave2() -> QPainterPath:
    path = QPainterPath()
    path.moveTo(0.0, 0.30)
    path.cubicTo(0.25, 0.06, 0.30, 0.06, 0.50, 0.30)
    path.cubicTo(0.70, 0.54, 0.75, 0.54, 1.0, 0.30)
    path.lineTo(1.0, 0.66)
    path.cubicTo(0.75, 0.90, 0.70, 0.90, 0.50, 0.66)
    path.cubicTo(0.30, 0.42, 0.25, 0.42, 0.0, 0.66)
    path.closeSubpath()
    return path


def _shape_wave3() -> QPainterPath:
    path = QPainterPath()
    path.moveTo(0.0, 0.14)
    path.cubicTo(0.14, 0.02, 0.22, 0.30, 0.36, 0.22)
    path.cubicTo(0.50, 0.14, 0.58, 0.42, 0.72, 0.34)
    path.cubicTo(0.86, 0.26, 0.92, 0.48, 1.0, 0.40)
    path.lineTo(1.0, 0.94)
    path.lineTo(0.0, 0.94)
    path.closeSubpath()
    return path


# --------------------------------------------------------------------------
# technical shapes
# --------------------------------------------------------------------------
def _shape_stripe_diag() -> QPainterPath:
    return _poly([(0.20, 0.0), (0.55, 0.0), (0.80, 1.0), (0.45, 1.0)])


def _shape_triangle_stack() -> QPainterPath:
    return _poly([(0.5, 0.02), (0.92, 0.34), (0.08, 0.34)]).united(
        _poly([(0.38, 0.38), (0.74, 0.68), (0.02, 0.68)])).united(
        _poly([(0.58, 0.72), (0.98, 1.0), (0.18, 1.0)]))


def _shape_chip() -> QPainterPath:
    body = _rect(0.20, 0.20, 0.60, 0.60, 0.08)
    for offset in (0.28, 0.44, 0.60):
        body = body.united(_rect(0.0, offset, 0.22, 0.08, 0.03))
        body = body.united(_rect(0.78, offset, 0.22, 0.08, 0.03))
        body = body.united(_rect(offset, 0.0, 0.08, 0.22, 0.03))
        body = body.united(_rect(offset, 0.78, 0.08, 0.22, 0.03))
    return body.subtracted(_rect(0.38, 0.38, 0.24, 0.24, 0.03))


def _shape_circuit() -> QPainterPath:
    path = _line([(0.10, 0.24), (0.46, 0.24), (0.46, 0.52),
                  (0.72, 0.52)], 0.08)
    path = path.united(_line([(0.24, 0.82), (0.24, 0.56),
                              (0.60, 0.56), (0.60, 0.76)], 0.08))
    for x, y in ((0.10, 0.24), (0.72, 0.52), (0.24, 0.82), (0.60, 0.76)):
        path = path.united(_ellipse(x, y, 0.075, 0.075))
    return path


def _shape_radar() -> QPainterPath:
    path = _stroked(_arc_band(0.5, 0.5, 0.44, 0.44, 0.0, 360.0, 0.045), 0.02)
    for radius in (0.30, 0.16):
        path = path.united(_stroked(
            _arc_band(0.5, 0.5, radius, radius, 0.0, 360.0, 0.035), 0.015))
    path = path.united(_rect(0.485, 0.06, 0.03, 0.88))
    path = path.united(_rect(0.06, 0.485, 0.88, 0.03))
    path = path.united(_poly([(0.5, 0.5), (0.92, 0.20), (0.86, 0.28)]))
    return path


def _shape_hex_cut() -> QPainterPath:
    return _regular(6, radius=0.5).subtracted(_regular(6, radius=0.34))


def _shape_octa_cut() -> QPainterPath:
    return _regular(8, radius=0.5, rotation=-67.5).subtracted(
        _regular(8, radius=0.34, rotation=-67.5))


def _shape_bolt_form() -> QPainterPath:
    return _poly([(0.62, 0.0), (0.16, 0.55), (0.45, 0.55), (0.34, 1.0),
                  (0.86, 0.40), (0.54, 0.40)])


def _shape_triquetra() -> QPainterPath:
    path = QPainterPath()
    for angle in (0.0, 120.0, 240.0):
        ring = _ellipse(0.5, 0.5, 0.32, 0.46)
        path = path.united(_rotated(ring, angle))
    return path.subtracted(_ellipse(0.5, 0.5, 0.34, 0.34)).united(
        _ellipse(0.5, 0.5, 0.06, 0.06))


def _shape_gear_form() -> QPainterPath:
    teeth = 12
    steps = teeth * 4
    points: list[Point] = []
    for index in range(steps):
        angle = -pi / 2 + index * 2 * pi / steps
        phase = index % 4
        radius = 0.50 if phase in (0, 1) else 0.36
        points.append((0.5 + cos(angle) * radius, 0.5 + sin(angle) * radius))
    return _poly(points).subtracted(_ellipse(0.5, 0.5, 0.17, 0.17))


def _shape_orbit_form() -> QPainterPath:
    ring_a = _ellipse(0.5, 0.5, 0.47, 0.22)
    ring_b = _rotated(ring_a, 62.0)
    return (_stroked(ring_a, 0.055).united(_stroked(ring_b, 0.055))
            .united(_ellipse(0.5, 0.5, 0.10, 0.10)))


def _shape_atom_form() -> QPainterPath:
    path = QPainterPath()
    for angle in (0.0, 60.0, 120.0):
        path = path.united(_stroked(_rotated(
            _ellipse(0.5, 0.5, 0.48, 0.20), angle), 0.05))
    return path.united(_ellipse(0.5, 0.5, 0.095, 0.095))


def _shape_spiral_form() -> QPainterPath:
    points: list[Point] = []
    for index in range(150):
        angle = index * 0.22
        radius = 0.02 + index * 0.0031
        points.append((0.5 + cos(angle) * radius, 0.5 + sin(angle) * radius))
    return _stroked(_poly(points, close=False), 0.035)


def _shape_crosshair_form() -> QPainterPath:
    ring = _ellipse(0.5, 0.5, 0.34, 0.34).subtracted(
        _ellipse(0.5, 0.5, 0.25, 0.25))
    outer = _ellipse(0.5, 0.5, 0.48, 0.48).subtracted(
        _ellipse(0.5, 0.5, 0.43, 0.43))
    ticks = (_rect(0.465, 0.0, 0.07, 0.13).united(
        _rect(0.465, 0.87, 0.07, 0.13))
        .united(_rect(0.0, 0.465, 0.13, 0.07))
        .united(_rect(0.87, 0.465, 0.13, 0.07)))
    return ring.united(outer).united(ticks).united(
        _ellipse(0.5, 0.5, 0.055, 0.055))


def _shape_planet() -> QPainterPath:
    planet = _ellipse(0.5, 0.48, 0.32, 0.32)
    ring = _stroked(_ellipse(0.5, 0.50, 0.50, 0.15), 0.06)
    return planet.united(ring)


# --------------------------------------------------------------------------
# shape registry
# --------------------------------------------------------------------------
SHAPES: dict[str, tuple[str, object]] = {}
SHAPE_CATEGORY: dict[str, str] = {}


def _register_shape(key: str, label: str, builder, category: str) -> None:
    SHAPES[key] = (label, builder)
    SHAPE_CATEGORY[key] = category


for _key, _label, _builder, _category in (
    # basics ------------------------------------------------------------
    ("circle", "Circle", _shape_circle, "Basics"),
    ("ring", "Ring", _shape_ring, "Basics"),
    ("square", "Square", _shape_square, "Basics"),
    ("rounded", "Rounded square", _shape_rounded, "Basics"),
    ("capsule", "Capsule", _shape_capsule, "Basics"),
    ("triangle", "Triangle", _shape_triangle, "Basics"),
    ("diamond", "Diamond", _shape_diamond, "Basics"),
    ("half", "Half circle", _shape_half, "Basics"),
    ("teardrop", "Teardrop", _shape_teardrop, "Basics"),
    ("cross", "Cross", _shape_cross, "Basics"),
    ("plus_round", "Rounded plus", _shape_plus_round, "Basics"),
    ("minus_round", "Rounded minus", _shape_minus_round, "Basics"),
    ("equals_round", "Rounded equals", _shape_equals_round, "Basics"),
    ("square_cut", "Cut-corner square", _shape_square_cut, "Basics"),
    # polygons ----------------------------------------------------------
    ("pentagon", "Pentagon", _shape_pentagon, "Polygons"),
    ("hexagon", "Hexagon", _shape_hexagon, "Polygons"),
    ("hex_flat", "Flat hexagon", _shape_hex_flat, "Polygons"),
    ("octagon", "Octagon", _shape_octagon, "Polygons"),
    ("heptagon", "Heptagon", lambda: _regular(7), "Polygons"),
    ("nonagon", "Nonagon", lambda: _regular(9), "Polygons"),
    ("decagon", "Decagon", lambda: _regular(10), "Polygons"),
    ("hendecagon", "Eleven-sided", lambda: _regular(11), "Polygons"),
    ("dodecagon", "Twelve-sided", lambda: _regular(12), "Polygons"),
    ("tridecagon", "Thirteen-sided", lambda: _regular(13), "Polygons"),
    ("tetradecagon", "Fourteen-sided", lambda: _regular(14), "Polygons"),
    ("pentadecagon", "Fifteen-sided", lambda: _regular(15), "Polygons"),
    ("hexadecagon", "Sixteen-sided", lambda: _regular(16), "Polygons"),
    ("icosagon", "Twenty-sided", lambda: _regular(20), "Polygons"),
    # stars -------------------------------------------------------------
    ("star3", "Three-point star", lambda: _star(3, inner=0.32), "Stars"),
    ("star4", "Four-point star", lambda: _star(4, inner=0.28), "Stars"),
    ("star5", "Five-point star", _shape_star5, "Stars"),
    ("star6", "Six-point star", _shape_star6, "Stars"),
    ("star7", "Seven-point star", lambda: _star(7, inner=0.48), "Stars"),
    ("star8", "Eight-point star", lambda: _star(8, inner=0.52), "Stars"),
    ("star9", "Nine-point star", lambda: _star(9, inner=0.56), "Stars"),
    ("star10", "Ten-point star", lambda: _star(10, inner=0.58), "Stars"),
    ("star12", "Twelve-point star", _shape_star12, "Stars"),
    ("star16", "Sixteen-point star", lambda: _star(16, inner=0.54), "Stars"),
    ("star20", "Twenty-point star", lambda: _star(20, inner=0.52), "Stars"),
    ("sparkle4", "Four-point sparkle", lambda: _star(4, inner=0.16), "Stars"),
    ("sparkle8", "Eight-point sparkle", lambda: _star(8, inner=0.24), "Stars"),
    ("flare12", "Sun flare", lambda: _star(12, inner=0.34), "Stars"),
    ("burst", "Burst", _shape_burst, "Stars"),
    # frames and panels -------------------------------------------------
    ("frame", "Rectangular frame", _shape_frame, "Frames"),
    ("frame_round", "Rounded frame", _shape_frame_round, "Frames"),
    ("frame_thick", "Heavy frame", _shape_frame_thick, "Frames"),
    ("frame_corner", "Corner brackets", _shape_frame_corner, "Frames"),
    ("split_v", "Split vertical", _shape_split_v, "Frames"),
    ("split_h", "Split horizontal", _shape_split_h, "Frames"),
    ("grid_2x2", "Two by two grid", _shape_grid_2x2, "Frames"),
    ("grid_3x3", "Three by three grid", _shape_grid_3x3, "Frames"),
    ("rows_3", "Three rows", _shape_rows_3, "Frames"),
    ("cols_3", "Three columns", _shape_cols_3, "Frames"),
    ("arch", "Arch", _shape_arch, "Frames"),
    ("arch_window", "Arch window", _shape_arch_window, "Frames"),
    ("window", "Window frame", _shape_window, "Frames"),
    ("window_round", "Round window", _shape_window_round, "Frames"),
    ("ticket", "Ticket", _shape_ticket, "Frames"),
    ("panel_top", "Top panel", _shape_panel_top, "Frames"),
    ("panel_bottom", "Bottom panel", _shape_panel_bottom, "Frames"),
    # arrows ------------------------------------------------------------
    ("arrow", "Arrow right", _shape_arrow, "Arrows"),
    ("arrow_left", "Arrow left", _shape_arrow_left, "Arrows"),
    ("arrow_right", "Arrow right (plain)", _shape_arrow_right, "Arrows"),
    ("arrow_up", "Arrow up", _shape_arrow_up, "Arrows"),
    ("arrow_down", "Arrow down", _shape_arrow_down, "Arrows"),
    ("arrow_double", "Double arrow", _shape_arrow_double, "Arrows"),
    ("arrow_bend", "Bent arrow", _shape_arrow_bend, "Arrows"),
    ("arrow_curve", "Curved arrow", _shape_arrow_curve, "Arrows"),
    ("chevron", "Chevron right", _shape_chevron, "Arrows"),
    ("chevron_left", "Chevron left", _shape_chevron_left, "Arrows"),
    ("chevron_right", "Chevron right (outline)", _shape_chevron_right,
     "Arrows"),
    ("chevron_up", "Chevron up", _shape_chevron_up, "Arrows"),
    ("chevron_down", "Chevron down", _shape_chevron_down, "Arrows"),
    ("chevron_double", "Double chevron", _shape_chevron_double, "Arrows"),
    ("chevron_triple", "Triple chevron", _shape_chevron_triple, "Arrows"),
    ("caret", "Caret", _shape_caret, "Arrows"),
    ("pointer", "Pointer", _shape_pointer, "Arrows"),
    ("cursor", "Cursor", _shape_cursor, "Arrows"),
    # banners and badges ------------------------------------------------
    ("banner", "Banner", _shape_banner, "Banners"),
    ("banner_notch", "Notched banner", _shape_banner_notch, "Banners"),
    ("banner_swallow", "Swallowtail banner", _shape_banner_swallow, "Banners"),
    ("ribbon", "Ribbon", _shape_ribbon, "Banners"),
    ("ribbon_fold", "Folded ribbon", _shape_ribbon_fold, "Banners"),
    ("pennant", "Pennant", _shape_pennant, "Banners"),
    ("flag", "Flag", _shape_flag, "Banners"),
    ("tag", "Tag", _shape_tag, "Banners"),
    ("tag_round", "Round tag", _shape_tag_round, "Banners"),
    ("plaque", "Plaque", _shape_plaque, "Banners"),
    ("plaque_round", "Round plaque", _shape_plaque_round, "Banners"),
    ("shield", "Shield", _shape_shield, "Badges"),
    ("crest", "Crest outline", _shape_crest, "Badges"),
    ("hex_badge", "Hex badge ring", _shape_hex_badge, "Badges"),
    ("seal", "Scalloped seal", _shape_seal, "Badges"),
    ("seal_scallop", "Round seal", _shape_seal_scallop, "Badges"),
    ("seal_star", "Star seal", _shape_seal_star, "Badges"),
    ("award", "Award ribbon", _shape_award, "Badges"),
    ("rosette", "Rosette", _shape_rosette, "Badges"),
    # organic -----------------------------------------------------------
    ("blob", "Blob", _shape_blob, "Organic"),
    ("blob2", "Blob two", lambda: _blob(2), "Organic"),
    ("blob3", "Blob three", lambda: _blob(3), "Organic"),
    ("blob4", "Blob four", lambda: _blob(4), "Organic"),
    ("blob5", "Blob five", lambda: _blob(5), "Organic"),
    ("wave", "Wave", _shape_wave, "Organic"),
    ("wave2", "Wave two", _shape_wave2, "Organic"),
    ("wave3", "Wave three", _shape_wave3, "Organic"),
    ("drop", "Drop", _shape_drop, "Organic"),
    ("droplet", "Droplet", _shape_droplet, "Organic"),
    ("petal", "Petal", _shape_petal, "Organic"),
    ("leaf", "Leaf", _shape_leaf, "Organic"),
    ("leaf_double", "Double leaf", _shape_leaf_double, "Organic"),
    ("crescent", "Crescent", _shape_crescent, "Organic"),
    ("moon", "Moon", _shape_moon, "Organic"),
    ("quarter", "Quarter circle", _shape_quarter, "Organic"),
    ("pie", "Three-quarter pie", _shape_pie, "Organic"),
    ("pie3", "Third slice", _shape_pie3, "Organic"),
    ("pie6", "Sixth slice", _shape_pie6, "Organic"),
    ("heart", "Heart", _shape_heart, "Organic"),
    ("club", "Club", _shape_club, "Organic"),
    ("diamond_suit", "Diamond suit", _shape_diamond_suit, "Organic"),
    ("flame_form", "Flame", _shape_flame_form, "Organic"),
    ("cloud", "Cloud", _shape_cloud, "Organic"),
    ("splash", "Splash", _shape_splash, "Organic"),
    ("speech", "Speech bubble", _shape_speech, "Organic"),
    ("speech_round", "Round speech bubble", _shape_speech_round, "Organic"),
    ("thought", "Thought bubble", _shape_thought, "Organic"),
    ("speech_burst", "Burst bubble", _shape_speech_burst, "Organic"),
    # technical ---------------------------------------------------------
    ("stripe_diag", "Diagonal stripe", _shape_stripe_diag, "Tech"),
    ("triangle_stack", "Triangle stack", _shape_triangle_stack, "Tech"),
    ("chip", "Microchip", _shape_chip, "Tech"),
    ("circuit", "Circuit trace", _shape_circuit, "Tech"),
    ("radar", "Radar", _shape_radar, "Tech"),
    ("hex_cut", "Hex ring", _shape_hex_cut, "Tech"),
    ("octa_cut", "Octagon ring", _shape_octa_cut, "Tech"),
    ("bolt_form", "Bolt", _shape_bolt_form, "Tech"),
    ("triquetra", "Triquetra", _shape_triquetra, "Tech"),
    ("gear_form", "Gear", _shape_gear_form, "Tech"),
    ("orbit_form", "Orbit", _shape_orbit_form, "Tech"),
    ("atom_form", "Atom", _shape_atom_form, "Tech"),
    ("spiral_form", "Spiral", _shape_spiral_form, "Tech"),
    ("crosshair_form", "Crosshair", _shape_crosshair_form, "Tech"),
    ("planet", "Planet", _shape_planet, "Tech"),
):
    _register_shape(_key, _label, _builder, _category)


SHAPE_ORDER = tuple(SHAPES)
SHAPE_CATEGORY_ORDER = (
    "Basics", "Polygons", "Stars", "Frames", "Arrows", "Banners",
    "Badges", "Organic", "Tech", "Forged",
)


# --------------------------------------------------------------------------
# handcrafted icons
# --------------------------------------------------------------------------
def _icon_skull() -> QPainterPath:
    cranium = _ellipse(0.5, 0.41, 0.34, 0.33)
    jaw = _rect(0.31, 0.58, 0.38, 0.32, 0.10)
    silhouette = cranium.united(jaw)
    holes = _ellipse(0.37, 0.40, 0.105, 0.12).united(
        _ellipse(0.63, 0.40, 0.105, 0.12))
    holes = holes.united(_poly([(0.5, 0.52), (0.44, 0.64), (0.56, 0.64)]))
    holes = holes.united(_rect(0.455, 0.72, 0.03, 0.14, 0.01))
    holes = holes.united(_rect(0.52, 0.72, 0.03, 0.14, 0.01))
    return silhouette.subtracted(holes)


def _icon_crown() -> QPainterPath:
    crown = _poly([(0.04, 0.26), (0.24, 0.44), (0.34, 0.14), (0.50, 0.38),
                   (0.66, 0.14), (0.76, 0.44), (0.96, 0.26), (0.88, 0.84),
                   (0.12, 0.84)])
    band = _rect(0.12, 0.84, 0.76, 0.10, 0.03)
    return crown.united(band)


def _icon_sword() -> QPainterPath:
    blade = _poly([(0.5, 0.0), (0.585, 0.16), (0.575, 0.62), (0.425, 0.62),
                   (0.415, 0.16)])
    guard = _rect(0.20, 0.61, 0.60, 0.085, 0.03)
    grip = _rect(0.455, 0.695, 0.09, 0.19, 0.02)
    pommel = _ellipse(0.5, 0.92, 0.075, 0.065)
    return blade.united(guard).united(grip).united(pommel)


def _icon_shield() -> QPainterPath:
    outer = _shape_shield()
    inner = QTransform().translate(0.5, 0.48).scale(0.78, 0.78).translate(
        -0.5, -0.48).map(outer)
    return outer.subtracted(inner)


def _icon_bolt() -> QPainterPath:
    return _poly([(0.62, 0.0), (0.16, 0.55), (0.45, 0.55), (0.34, 1.0),
                  (0.86, 0.40), (0.54, 0.40)])


def _icon_flame() -> QPainterPath:
    path = QPainterPath()
    path.moveTo(0.50, 0.01)
    path.cubicTo(0.62, 0.18, 0.80, 0.30, 0.84, 0.55)
    path.cubicTo(0.88, 0.79, 0.72, 0.98, 0.50, 0.98)
    path.cubicTo(0.28, 0.98, 0.12, 0.81, 0.12, 0.58)
    path.cubicTo(0.12, 0.42, 0.22, 0.31, 0.32, 0.19)
    path.cubicTo(0.34, 0.34, 0.38, 0.43, 0.45, 0.48)
    path.cubicTo(0.42, 0.31, 0.46, 0.14, 0.50, 0.01)
    path.closeSubpath()
    inner = QPainterPath()
    inner.moveTo(0.50, 0.40)
    inner.cubicTo(0.60, 0.50, 0.65, 0.60, 0.63, 0.71)
    inner.cubicTo(0.61, 0.84, 0.55, 0.90, 0.48, 0.90)
    inner.cubicTo(0.39, 0.90, 0.34, 0.81, 0.36, 0.70)
    inner.cubicTo(0.37, 0.60, 0.43, 0.53, 0.50, 0.40)
    inner.closeSubpath()
    return path.subtracted(inner)


def _icon_star() -> QPainterPath:
    return _star(5, inner=0.42)


def _icon_crescent() -> QPainterPath:
    outer = _ellipse(0.5, 0.5, 0.48, 0.48)
    cut = _ellipse(0.66, 0.40, 0.42, 0.42)
    return outer.subtracted(cut)


def _icon_sun() -> QPainterPath:
    path = _ellipse(0.5, 0.5, 0.23, 0.23)
    for index in range(8):
        angle = index * pi / 4
        dx, dy = cos(angle), sin(angle)
        ray = _line([(0.5 + dx * 0.32, 0.5 + dy * 0.32),
                     (0.5 + dx * 0.48, 0.5 + dy * 0.48)], 0.075)
        path = path.united(ray)
    return path


def _icon_eye() -> QPainterPath:
    lens = QPainterPath()
    lens.moveTo(0.02, 0.5)
    lens.cubicTo(0.16, 0.24, 0.34, 0.12, 0.50, 0.12)
    lens.cubicTo(0.66, 0.12, 0.84, 0.24, 0.98, 0.50)
    lens.cubicTo(0.84, 0.76, 0.66, 0.88, 0.50, 0.88)
    lens.cubicTo(0.34, 0.88, 0.16, 0.76, 0.02, 0.50)
    lens.closeSubpath()
    iris = _ellipse(0.5, 0.5, 0.24, 0.24)
    pupil = _ellipse(0.5, 0.5, 0.11, 0.11)
    return lens.subtracted(iris.subtracted(pupil))


def _icon_wing() -> QPainterPath:
    path = QPainterPath()
    path.moveTo(0.04, 0.26)
    path.cubicTo(0.28, 0.06, 0.64, 0.04, 0.96, 0.18)
    path.cubicTo(0.80, 0.30, 0.74, 0.48, 0.62, 0.56)
    path.cubicTo(0.70, 0.60, 0.78, 0.62, 0.88, 0.62)
    path.cubicTo(0.68, 0.74, 0.56, 0.82, 0.40, 0.79)
    path.cubicTo(0.45, 0.86, 0.50, 0.90, 0.58, 0.93)
    path.cubicTo(0.30, 0.96, 0.12, 0.82, 0.08, 0.62)
    path.cubicTo(0.06, 0.48, 0.06, 0.36, 0.04, 0.26)
    path.closeSubpath()
    return path


def _icon_anchor() -> QPainterPath:
    ring = _ellipse(0.5, 0.12, 0.13, 0.13).subtracted(
        _ellipse(0.5, 0.12, 0.065, 0.065))
    shaft = _rect(0.455, 0.22, 0.09, 0.62, 0.02)
    cross = _rect(0.25, 0.34, 0.50, 0.085, 0.03)
    arms = _arc_band(0.5, 0.50, 0.36, 0.36, 200.0, 140.0, 0.10)
    left = _poly([(0.10, 0.66), (0.22, 0.60), (0.22, 0.78)])
    right = _poly([(0.90, 0.66), (0.78, 0.60), (0.78, 0.78)])
    return ring.united(shaft).united(cross).united(arms).united(left).united(right)


def _icon_crosshair() -> QPainterPath:
    ring = _ellipse(0.5, 0.5, 0.34, 0.34).subtracted(
        _ellipse(0.5, 0.5, 0.255, 0.255))
    outer_ring = _ellipse(0.5, 0.5, 0.47, 0.47).subtracted(
        _ellipse(0.5, 0.5, 0.42, 0.42))
    ticks = (_rect(0.465, 0.0, 0.07, 0.13).united(_rect(0.465, 0.87, 0.07, 0.13))
             .united(_rect(0.0, 0.465, 0.13, 0.07))
             .united(_rect(0.87, 0.465, 0.13, 0.07)))
    return ring.united(outer_ring).united(ticks).united(
        _ellipse(0.5, 0.5, 0.055, 0.055))


def _icon_gear() -> QPainterPath:
    teeth = 10
    steps = teeth * 4
    points: list[Point] = []
    for index in range(steps):
        angle = -pi / 2 + index * 2 * pi / steps
        phase = index % 4
        radius = 0.48 if phase in (0, 1) else 0.355
        points.append((0.5 + cos(angle) * radius, 0.5 + sin(angle) * radius))
    body = _poly(points)
    return body.subtracted(_ellipse(0.5, 0.5, 0.165, 0.165))


def _icon_diamond() -> QPainterPath:
    gem = _poly([(0.50, 0.02), (0.86, 0.30), (0.50, 0.98), (0.14, 0.30)])
    table = _poly([(0.14, 0.30), (0.28, 0.34), (0.72, 0.34), (0.86, 0.30),
                   (0.78, 0.20), (0.50, 0.14), (0.22, 0.20)])
    facet_left = _poly([(0.28, 0.34), (0.30, 0.345), (0.485, 0.955),
                        (0.475, 0.955)])
    facet_right = _poly([(0.72, 0.34), (0.70, 0.345), (0.515, 0.955),
                         (0.525, 0.955)])
    veins = _poly([(0.50, 0.14), (0.505, 0.14), (0.505, 0.96), (0.495, 0.96)])
    return gem.subtracted(table).subtracted(facet_left).subtracted(
        facet_right).subtracted(veins)


def _icon_spade() -> QPainterPath:
    head = QPainterPath()
    head.moveTo(0.50, 0.02)
    head.cubicTo(0.68, 0.24, 0.94, 0.38, 0.94, 0.60)
    head.cubicTo(0.94, 0.76, 0.80, 0.86, 0.66, 0.84)
    head.cubicTo(0.58, 0.83, 0.52, 0.78, 0.50, 0.72)
    head.cubicTo(0.48, 0.78, 0.42, 0.83, 0.34, 0.84)
    head.cubicTo(0.20, 0.86, 0.06, 0.76, 0.06, 0.60)
    head.cubicTo(0.06, 0.38, 0.32, 0.24, 0.50, 0.02)
    head.closeSubpath()
    stem = _poly([(0.42, 0.72), (0.58, 0.72), (0.56, 0.84), (0.66, 0.90),
                  (0.34, 0.90), (0.44, 0.84)])
    return head.united(stem)


def _icon_rune() -> QPainterPath:
    return (_line([(0.22, 0.92), (0.22, 0.08)], 0.12)
            .united(_line([(0.22, 0.10), (0.80, 0.38)], 0.12))
            .united(_line([(0.22, 0.52), (0.68, 0.52)], 0.11))
            .united(_line([(0.68, 0.52), (0.78, 0.88)], 0.11)))


def _icon_orbit() -> QPainterPath:
    ring_a = _ellipse(0.5, 0.5, 0.47, 0.22)
    ring_b = _rotated(ring_a, 62.0)
    core = _ellipse(0.5, 0.5, 0.10, 0.10)
    return _stroked(ring_a, 0.055).united(_stroked(ring_b, 0.055)).united(core)


def _icon_laurel() -> QPainterPath:
    path = QPainterPath()
    path = path.united(_arc_band(0.5, 0.52, 0.39, 0.39, 110.0, 130.0, 0.055))
    path = path.united(_arc_band(0.5, 0.52, 0.39, 0.39, -60.0, 130.0, 0.055))
    for side in (-1, 1):
        for index in range(5):
            angle = (-80 + index * 26) * pi / 180.0
            cx = 0.5 + side * cos(angle) * 0.36
            cy = 0.52 + sin(angle) * 0.36
            leaf = QTransform().translate(cx, cy).rotate(
                (angle * 180 / pi) + (90 if side > 0 else -90)
            ).translate(-cx, -cy).map(_ellipse(cx, cy, 0.035, 0.085))
            path = path.united(leaf)
    return path


def _icon_heart() -> QPainterPath:
    return _shape_heart()


def _icon_club() -> QPainterPath:
    return _shape_club()


def _icon_skull_cross() -> QPainterPath:
    skull = _icon_skull()
    skull = QTransform().translate(0.5, 0.42).scale(0.82, 0.82).translate(
        -0.5, -0.42).map(skull)
    bones = (_line([(0.12, 0.86), (0.88, 0.94)], 0.10)
             .united(_line([(0.12, 0.94), (0.88, 0.86)], 0.10)))
    return skull.united(bones)


def _icon_target() -> QPainterPath:
    return (_ellipse(0.5, 0.5, 0.48, 0.48)
            .subtracted(_ellipse(0.5, 0.5, 0.38, 0.38))
            .united(_ellipse(0.5, 0.5, 0.27, 0.27)
                    .subtracted(_ellipse(0.5, 0.5, 0.17, 0.17)))
            .united(_ellipse(0.5, 0.5, 0.07, 0.07)))


def _icon_pentagram() -> QPainterPath:
    points: list[Point] = []
    for index in range(5):
        angle = (-90 + index * 144) * pi / 180.0
        points.append((0.5 + cos(angle) * 0.46, 0.5 + sin(angle) * 0.46))
    return _stroked(_poly(points), 0.055).united(
        _stroked(_ellipse(0.5, 0.5, 0.49, 0.49), 0.04))


def _icon_hexagram() -> QPainterPath:
    up = _regular(3, radius=0.48)
    down = _rotated(up, 180.0)
    return _stroked(up, 0.055).united(_stroked(down, 0.055))


def _icon_ankh() -> QPainterPath:
    loop = _ellipse(0.5, 0.21, 0.15, 0.19).subtracted(
        _ellipse(0.5, 0.21, 0.085, 0.12))
    return loop.united(_rect(0.455, 0.38, 0.09, 0.60, 0.02)).united(
        _rect(0.22, 0.44, 0.56, 0.09, 0.03))


def _icon_yin_yang() -> QPainterPath:
    outer = _ellipse(0.5, 0.5, 0.48, 0.48)
    right = _ellipse(0.5, 0.5, 0.24, 0.48)
    return outer.subtracted(right).united(
        _ellipse(0.5, 0.26, 0.24, 0.24)).united(
        _ellipse(0.5, 0.74, 0.24, 0.24).subtracted(
            _ellipse(0.5, 0.74, 0.115, 0.115)))


def _icon_peace() -> QPainterPath:
    ring = _stroked(_ellipse(0.5, 0.5, 0.46, 0.46), 0.055)
    spokes = (_line([(0.5, 0.04), (0.5, 0.96)], 0.055)
              .united(_line([(0.5, 0.5), (0.20, 0.82)], 0.055))
              .united(_line([(0.5, 0.5), (0.80, 0.82)], 0.055)))
    return ring.united(spokes)


def _icon_infinity() -> QPainterPath:
    left = _stroked(_ellipse(0.31, 0.5, 0.25, 0.25), 0.09)
    right = _stroked(_ellipse(0.69, 0.5, 0.25, 0.25), 0.09)
    return left.united(right)


def _icon_ouroboros() -> QPainterPath:
    ring = _ellipse(0.5, 0.5, 0.42, 0.42).subtracted(
        _ellipse(0.5, 0.5, 0.30, 0.30))
    head = _poly([(0.78, 0.18), (0.96, 0.26), (0.84, 0.40)])
    eye = _ellipse(0.84, 0.28, 0.028, 0.028)
    return ring.united(head).subtracted(eye)


def _icon_atom() -> QPainterPath:
    path = QPainterPath()
    for angle in (0.0, 60.0, 120.0):
        path = path.united(_stroked(_rotated(
            _ellipse(0.5, 0.5, 0.48, 0.20), angle), 0.045))
    return path.united(_ellipse(0.5, 0.5, 0.075, 0.075))


def _icon_compass() -> QPainterPath:
    ring = _ellipse(0.5, 0.5, 0.47, 0.47).subtracted(
        _ellipse(0.5, 0.5, 0.40, 0.40))
    needle = _poly([(0.5, 0.14), (0.62, 0.52), (0.5, 0.86), (0.38, 0.52)])
    return ring.united(needle)


def _icon_snowflake() -> QPainterPath:
    path = QPainterPath()
    for angle in (0.0, 60.0, 120.0):
        arm = _line([(0.5, 0.04), (0.5, 0.96)], 0.055)
        arm = arm.united(_line([(0.5, 0.22), (0.34, 0.10)], 0.045))
        arm = arm.united(_line([(0.5, 0.22), (0.66, 0.10)], 0.045))
        arm = arm.united(_line([(0.5, 0.78), (0.34, 0.90)], 0.045))
        arm = arm.united(_line([(0.5, 0.78), (0.66, 0.90)], 0.045))
        path = path.united(_rotated(arm, angle))
    return path


# --------------------------------------------------------------------------
# icon registry
# --------------------------------------------------------------------------
ICONS: dict[str, tuple[str, object]] = {}
ICON_CATEGORY: dict[str, str] = {}


def _register_icon(key: str, label: str, builder, category: str) -> None:
    ICONS[key] = (label, builder)
    ICON_CATEGORY[key] = category


for _key, _label, _builder, _category in (
    ("skull", "Skull", _icon_skull, "Symbols"),
    ("skull_cross", "Skull and crossbones", _icon_skull_cross, "Symbols"),
    ("crown", "Crown", _icon_crown, "Symbols"),
    ("sword", "Sword", _icon_sword, "Combat"),
    ("shield", "Shield ring", _icon_shield, "Combat"),
    ("bolt", "Lightning", _icon_bolt, "Weather"),
    ("flame", "Flame", _icon_flame, "Symbols"),
    ("star", "Star", _icon_star, "Symbols"),
    ("crescent", "Crescent", _icon_crescent, "Symbols"),
    ("sun", "Sun ring", _icon_sun, "Weather"),
    ("eye", "Eye", _icon_eye, "Symbols"),
    ("wing", "Wing", _icon_wing, "Symbols"),
    ("anchor", "Anchor", _icon_anchor, "Symbols"),
    ("crosshair", "Crosshair", _icon_crosshair, "Combat"),
    ("gear", "Gear", _icon_gear, "Tech"),
    ("diamond", "Diamond", _icon_diamond, "Symbols"),
    ("spade", "Spade", _icon_spade, "Symbols"),
    ("rune", "Rune", _icon_rune, "Arcane"),
    ("orbit", "Orbit", _icon_orbit, "Tech"),
    ("laurel", "Laurel", _icon_laurel, "Symbols"),
    ("heart", "Heart", _icon_heart, "Symbols"),
    ("club", "Club", _icon_club, "Symbols"),
    ("target", "Target", _icon_target, "Combat"),
    ("pentagram", "Pentagram", _icon_pentagram, "Arcane"),
    ("hexagram", "Hexagram", _icon_hexagram, "Arcane"),
    ("ankh", "Ankh", _icon_ankh, "Symbols"),
    ("yin_yang", "Yin yang", _icon_yin_yang, "Symbols"),
    ("peace", "Peace", _icon_peace, "Symbols"),
    ("infinity", "Infinity", _icon_infinity, "Symbols"),
    ("ouroboros", "Ouroboros", _icon_ouroboros, "Arcane"),
    ("atom", "Atom", _icon_atom, "Tech"),
    ("compass", "Compass", _icon_compass, "Symbols"),
    ("snowflake", "Snowflake", _icon_snowflake, "Weather"),
):
    _register_icon(_key, _label, _builder, _category)


for _key, _label, _data, _stroke, _category in ICON_SVG:
    _register_icon(_key, _label,
                   lambda d=_data, s=_stroke: _svg(d, s), _category)

ICON_ORDER = tuple(ICONS)
ICON_CATEGORY_ORDER = (
    "UI", "Tech", "Weather", "Nature", "Combat", "Arcane", "Symbols",
    "Music", "Commerce", "Communication", "People", "Forged",
)


# --------------------------------------------------------------------------
# lookup, search and custom art
# --------------------------------------------------------------------------
_CACHE: dict[tuple[str, str], QPainterPath] = {}


def _built(kind: str, key: str):
    table = SHAPES if kind == "shape" else ICONS
    entry = table.get(key)
    if entry is None:
        return None
    _label, builder = entry
    try:
        return builder() if callable(builder) else builder
    except Exception:
        return None


def _lookup(kind: str, key: str, fallback: str) -> QPainterPath:
    cache_key = (kind, key)
    cached = _CACHE.get(cache_key)
    if cached is not None:
        return cached
    path = custom_art.path(kind, key)
    if path is None:
        path = _built(kind, key)
    if path is None or path.isEmpty():
        return _lookup(kind, fallback, fallback)
    _CACHE[cache_key] = path
    return path


def shape_path(key: str) -> QPainterPath:
    return _lookup("shape", str(key or ""), "circle")


def icon_path(key: str) -> QPainterPath:
    return _lookup("icon", str(key or ""), "star")


def shape_label(key: str) -> str:
    entry = SHAPES.get(key)
    if entry:
        return entry[0]
    return custom_art.label("shape", key) or "Custom"


def icon_label(key: str) -> str:
    entry = ICONS.get(key)
    if entry:
        return entry[0]
    return custom_art.label("icon", key) or "Icon"


def scaled(path: QPainterPath, width: float, height: float) -> QPainterPath:
    """Stretch a unit-square path into a pixel rectangle."""
    return QTransform().scale(width, height).map(path)


def _entries(table: dict[str, tuple[str, object]],
             categories: dict[str, str], kind: str,
             category: str | None = None,
             search: str = "") -> list[tuple[str, str]]:
    needle = (search or "").strip().casefold()
    only_custom = category == "Forged"
    show_custom = not category or category in ("All", "Forged")
    rows: list[tuple[str, str]] = []
    if not only_custom:
        for key, (label, _builder) in table.items():
            if category and category not in ("All", ""):
                if categories.get(key) != category:
                    continue
            if needle and (needle not in label.casefold()
                           and needle not in key.casefold()):
                continue
            rows.append((key, label))
    if show_custom:
        for record in custom_art.entries(kind):
            label = record.get("name") or (
                "Custom shape" if kind == "shape" else "Custom icon")
            if needle and (needle not in label.casefold()
                           and needle not in record["key"].casefold()):
                continue
            rows.append((record["key"], label))
    return rows


def shape_entries(category: str | None = None,
                  search: str = "") -> list[tuple[str, str]]:
    return _entries(SHAPES, SHAPE_CATEGORY, "shape", category, search)


def icon_entries(category: str | None = None,
                 search: str = "") -> list[tuple[str, str]]:
    return _entries(ICONS, ICON_CATEGORY, "icon", category, search)


def _present_categories(order: tuple[str, ...],
                        categories: dict[str, str], kind: str) -> list[str]:
    present = set(categories.values())
    rows = [name for name in order if name in present]
    if custom_art.entries(kind):
        rows.append("Forged")
    return rows


def shape_categories() -> list[str]:
    return _present_categories(SHAPE_CATEGORY_ORDER, SHAPE_CATEGORY, "shape")


def icon_categories() -> list[str]:
    return _present_categories(ICON_CATEGORY_ORDER, ICON_CATEGORY, "icon")


def all_shape_count() -> int:
    return len(SHAPES) + len(custom_art.entries("shape"))


def all_icon_count() -> int:
    return len(ICONS) + len(custom_art.entries("icon"))

