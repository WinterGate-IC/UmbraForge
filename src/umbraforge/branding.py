"""UmbraForge brand constants and a self-contained app mark.

The mark is drawn with QPainter so the app needs no bundled image to look
finished. ``icon_pixmap`` is also used by the About dialog and the launcher.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "UmbraForge"
VERSION = "0.1.1"
COMPANY = "WinterGate Intelligence Collective"
COMPANY_SHORT = "WIC"
OWNER = "AnonCatalyst"
WEBSITE = "https://wintergate.org"
TAGLINE = "Make the dark yours."
DESCRIPTION = (
    "A layered image and emblem studio for profile pictures, wallpapers, "
    "posters and everything between."
)
COPYRIGHT = f"\u00a9 2026 {COMPANY}. UmbraForge is a {COMPANY_SHORT} tool by {OWNER}."

ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
ASSETS = ROOT / "assets"


def icon_pixmap(size: int = 256):
    """The UmbraForge mark: a forge-lit monolith on a dark rounded tile."""
    from PySide6.QtCore import QPointF, QRectF, Qt
    from PySide6.QtGui import (
        QColor,
        QIcon,
        QLinearGradient,
        QPainter,
        QPainterPath,
        QPen,
        QPixmap,
        QRadialGradient,
    )

    size = max(16, int(size))
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    rect = QRectF(0, 0, size, size)
    tile = QPainterPath()
    tile.addRoundedRect(rect.adjusted(size * 0.03, size * 0.03,
                                      -size * 0.03, -size * 0.03),
                        size * 0.22, size * 0.22)

    base = QLinearGradient(0, 0, size, size)
    base.setColorAt(0.0, QColor("#191926"))
    base.setColorAt(0.55, QColor("#0d0d14"))
    base.setColorAt(1.0, QColor("#08080c"))
    p.fillPath(tile, base)

    glow = QRadialGradient(QPointF(size * 0.52, size * 0.62), size * 0.62)
    glow.setColorAt(0.0, QColor(255, 122, 61, 92))
    glow.setColorAt(0.55, QColor(139, 92, 246, 34))
    glow.setColorAt(1.0, QColor(0, 0, 0, 0))
    p.fillPath(tile, glow)

    p.setPen(QPen(QColor(255, 255, 255, 26), max(1.0, size * 0.006)))
    p.drawPath(tile)

    # The monolith: an angular U with a notch, cut by a forge spark.
    u = QPainterPath()
    x0, x1 = size * 0.30, size * 0.70
    y0, y1 = size * 0.24, size * 0.74
    u.moveTo(x0, y0)
    u.lineTo(x0 + size * 0.11, y0)
    u.lineTo(x0 + size * 0.11, y1 - size * 0.11)
    u.lineTo(x1 - size * 0.11, y1 - size * 0.11)
    u.lineTo(x1 - size * 0.11, y0)
    u.lineTo(x1, y0)
    u.lineTo(x1, y1)
    u.lineTo(x0, y1)
    u.closeSubpath()

    ember = QLinearGradient(0, y0, 0, y1)
    ember.setColorAt(0.0, QColor("#ffb066"))
    ember.setColorAt(0.5, QColor("#ff7a3d"))
    ember.setColorAt(1.0, QColor("#c4431b"))
    p.fillPath(u, ember)

    spark = QPainterPath()
    spark.moveTo(size * 0.585, size * 0.12)
    spark.lineTo(size * 0.505, size * 0.33)
    spark.lineTo(size * 0.575, size * 0.33)
    spark.lineTo(size * 0.515, size * 0.52)
    spark.lineTo(size * 0.655, size * 0.28)
    spark.lineTo(size * 0.585, size * 0.28)
    spark.closeSubpath()
    p.fillPath(spark, QColor("#f5f2ff"))

    p.end()
    return pix


def qicon() -> "QIcon":
    from PySide6.QtGui import QIcon

    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256, 512):
        icon.addPixmap(icon_pixmap(size))
    return icon


def ensure_assets() -> Path:
    """Write the mark to assets/ so the repo and docs have a real icon."""
    ASSETS.mkdir(parents=True, exist_ok=True)
    target = ASSETS / "umbraforge-256.png"
    if not target.exists():
        icon_pixmap(256).save(str(target), "PNG")
    return target


def saves_dir() -> Path:
    """The default folder for editable saves, shown in the Saves menu."""
    override = os.environ.get("UMBRAFORGE_SAVES")
    if override:
        return Path(override).expanduser()
    documents = Path.home() / "Documents"
    base = documents if documents.is_dir() else Path.home()
    return base / APP_NAME

