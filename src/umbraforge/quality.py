"""Device-aware quality governor for previews and exports.

UmbraForge is a local studio: there is no server to offload a 12,000-pixel
render to. That means the honest answer to "maximum quality" depends on the
machine in front of you. This module samples the machine with the standard
library (no psutil), turns the reading into a conservative pixel budget, and
provides quality presets, guarded rendering and atomic writes.

The philosophy mirrors VoiceForge's resource governor: measurements are
best-effort, every failure falls back to a safe value, and a failed render can
never leave a half-written image on disk.
"""

from __future__ import annotations

import ctypes
import io
import json
import math
import os
import platform
import shutil
import struct
import tempfile
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, Qt
from PySide6.QtGui import QImage, QPainter

MB = 1024 * 1024
MIN_SAFE_PIXELS = 2_000_000       # a comfortable 1414 x 1414 fallback
MAX_SAFE_PIXELS = 180_000_000     # 180 MP; beyond this even 32-bit routes hurt
MAX_SIDE = 16_384
PREVIEW_FLOOR = 1400
PREVIEW_CEILING = 3200

_PROFILE_CACHE: tuple[float, "DeviceProfile"] | None = None
_PROFILE_SECONDS = 6.0


@dataclass(frozen=True)
class DeviceProfile:
    cpu_count: int
    memory_total_mb: float
    memory_available_mb: float
    disk_free_mb: float
    system: str
    machine: str
    measured: bool = True

    @property
    def safe_pixels(self) -> int:
        """Conservative RGBA pixel budget for one composition."""
        if not self.measured or self.memory_available_mb <= 0:
            return 16_000_000
        # QImage RGBA uses 4 bytes per pixel. Keep the render to roughly a
        # third of available memory so Qt, Pillow and the OS still have room.
        budget = self.memory_available_mb * MB * 0.34
        pixels = int(budget / 4.0)
        return max(MIN_SAFE_PIXELS, min(MAX_SAFE_PIXELS, pixels))

    @property
    def max_side(self) -> int:
        return min(MAX_SIDE, int(math.sqrt(self.safe_pixels)) * 2)

    @property
    def label(self) -> str:
        if not self.measured:
            return "Conservative fallback"
        return f"{self.cpu_count} cores \u00b7 {self.memory_total_mb / 1024:.1f} GB RAM"

    def describe(self) -> str:
        parts = [f"{self.cpu_count} CPU cores",
                 f"{self.memory_total_mb / 1024:.1f} GB RAM",
                 f"{self.memory_available_mb / 1024:.1f} GB free"]
        if self.disk_free_mb > 0:
            parts.append(f"{self.disk_free_mb / 1024:.1f} GB disk")
        parts.append(self.system)
        return " \u00b7 ".join(parts)


def _windows_memory() -> tuple[float, float]:
    class MemoryStatus(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    status = MemoryStatus()
    status.dwLength = ctypes.sizeof(MemoryStatus)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        raise OSError("GlobalMemoryStatusEx failed")
    return (status.ullTotalPhys / MB, status.ullAvailPhys / MB)


def _unix_memory() -> tuple[float, float]:
    total = available = 0.0
    try:
        total = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / MB
    except (ValueError, OSError, AttributeError):
        pass
    try:
        available = (os.sysconf("SC_PAGE_SIZE")
                     * os.sysconf("SC_AVPHYS_PAGES") / MB)
    except (ValueError, OSError, AttributeError):
        pass
    return total, available


def sample_device(refresh: bool = False) -> DeviceProfile:
    """Read the machine, cached briefly so sliders do not resample constantly."""
    global _PROFILE_CACHE
    now = time.monotonic()
    if (not refresh and _PROFILE_CACHE is not None
            and now - _PROFILE_CACHE[0] < _PROFILE_SECONDS):
        return _PROFILE_CACHE[1]
    total = available = 0.0
    measured = True
    try:
        if os.name == "nt":
            total, available = _windows_memory()
        else:
            total, available = _unix_memory()
    except Exception:
        measured = False
    try:
        disk = shutil.disk_usage(str(Path.home())).free / MB
    except OSError:
        disk = 0.0
    try:
        cpus = os.cpu_count() or 1
    except Exception:
        cpus = 1
    if total <= 0:
        measured = False
    profile = DeviceProfile(
        cpu_count=max(1, int(cpus)),
        memory_total_mb=max(0.0, float(total)),
        memory_available_mb=max(0.0, float(available)),
        disk_free_mb=max(0.0, float(disk)),
        system=platform.system() or "Unknown",
        machine=platform.machine() or "unknown",
        measured=measured,
    )
    _PROFILE_CACHE = (now, profile)
    return profile


@dataclass(frozen=True)
class QualityTier:
    key: str
    name: str
    scale: float
    note: str
    recommended: bool = False


def _safe_scale(design, profile: DeviceProfile) -> float:
    base = max(1, int(design.width) * int(design.height))
    scale = math.sqrt(profile.safe_pixels / base)
    # Cap the recommendation at 4x: beyond that the file size grows faster
    # than the visible gain for normal artwork.
    return max(0.25, min(4.0, scale))


def tiers_for(design, profile: DeviceProfile | None = None) -> list[QualityTier]:
    profile = profile or sample_device()
    best = _safe_scale(design, profile)
    high = 2.0 if design.width * design.height * 4 <= profile.safe_pixels else 1.0
    return [
        QualityTier("draft", "Draft", 0.5,
                    "Fast preview export at half the canvas size."),
        QualityTier("canvas", "Canvas size", 1.0,
                    "Exactly the canvas resolution."),
        QualityTier("high", "High (2\u00d7)" if high > 1 else "High (1\u00d7)",
                    high,
                    "Extra pixels for print, cropping or a Retina display.",
                    recommended=high > 1 and abs(high - best) < 0.05),
        QualityTier("device", "Best for this device", round(best, 3),
                    "The largest crisp size this machine can render safely.",
                    recommended=True),
        QualityTier("custom", "Custom\u2026", 0.0, "Type an exact pixel size."),
    ]


def recommended_tier(design, profile: DeviceProfile | None = None) -> QualityTier:
    for tier in tiers_for(design, profile):
        if tier.key == "device":
            return tier
    return tiers_for(design, profile)[1]


def preview_max_side(profile: DeviceProfile | None = None) -> int:
    profile = profile or sample_device()
    # Preview is deliberately modest: every repaint is interactive.
    side = int(math.sqrt(profile.safe_pixels) * 0.10)
    return max(PREVIEW_FLOOR, min(PREVIEW_CEILING, side))


def clamp_size(width: int, height: int, profile: DeviceProfile | None = None,
               allow_unsafe: bool = False) -> tuple[int, int]:
    """Fit a requested size into the device budget, preserving aspect ratio."""
    profile = profile or sample_device()
    width = max(1, min(MAX_SIDE, int(width)))
    height = max(1, min(MAX_SIDE, int(height)))
    limit = profile.safe_pixels if not allow_unsafe else MAX_SAFE_PIXELS
    if width * height <= limit:
        return width, height
    scale = math.sqrt(limit / max(1, width * height))
    return max(1, int(width * scale)), max(1, int(height * scale))


@dataclass(frozen=True)
class ExportPlan:
    width: int
    height: int
    requested_width: int
    requested_height: int
    pixels: int
    estimated_mb: float
    safe: bool
    supersample: int
    warning: str
    profile: DeviceProfile


def plan_export(design, width: int, height: int,
                profile: DeviceProfile | None = None) -> ExportPlan:
    profile = profile or sample_device()
    requested = (max(1, int(width)), max(1, int(height)))
    safe_width, safe_height = clamp_size(*requested, profile=profile)
    pixels = safe_width * safe_height
    safe = pixels <= profile.safe_pixels
    # Supersampling: when the final image is small enough, render twice as
    # large and downsample. This is the cheapest way to get very clean edges.
    supersample = 1
    if safe and pixels * 4 <= profile.safe_pixels and safe_width * 2 <= MAX_SIDE:
        supersample = 2
    warning = ""
    if (safe_width, safe_height) != requested:
        warning = (
            f"Reduced from {requested[0]:,} \u00d7 {requested[1]:,} to stay "
            f"inside this device's safe memory budget.")
    estimated_mb = (pixels * 4.0 * (supersample ** 2)) / MB
    return ExportPlan(
        width=safe_width, height=safe_height,
        requested_width=requested[0], requested_height=requested[1],
        pixels=pixels, estimated_mb=estimated_mb, safe=safe,
        supersample=supersample, warning=warning, profile=profile)


def _flatten(image: QImage) -> QImage:
    flat = QImage(image.size(), QImage.Format.Format_RGB32)
    flat.fill(Qt.GlobalColor.black)
    painter = QPainter(flat)
    painter.drawImage(0, 0, image)
    painter.end()
    return flat


def render_export(design, width: int, height: int, background: bool = True,
                  profile: DeviceProfile | None = None):
    """Render with a guard, optional 2x supersampling and no half states."""
    from . import renderer

    plan = plan_export(design, width, height, profile=profile)
    render_width = plan.width * plan.supersample
    render_height = plan.height * plan.supersample
    image = renderer.render_design(design, render_width, render_height,
                                   background=background)
    if image.isNull():
        raise RuntimeError("Qt could not create that image.")
    if plan.supersample > 1:
        image = image.scaled(plan.width, plan.height,
                             Qt.AspectRatioMode.IgnoreAspectRatio,
                             Qt.TransformationMode.SmoothTransformation)
    return image, plan


def _atomic_target(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(
        prefix=f".{path.stem}-", suffix=f".tmp{path.suffix}", dir=str(path.parent))
    os.close(handle)
    return Path(name)


def save_export(design, path: str | Path, width: int, height: int,
                quality: int = 92, background: bool = True,
                profile: DeviceProfile | None = None) -> tuple[Path, ExportPlan]:
    """Save atomically. The destination only appears after a full write."""
    target = Path(path)
    fmt = {"jpg": "JPEG", "jpeg": "JPEG", "png": "PNG", "webp": "WEBP",
           "bmp": "BMP", "tif": "TIFF", "tiff": "TIFF"}.get(
        target.suffix.lower().lstrip("."), "PNG")
    if fmt == "JPEG":
        background = True
    image, plan = render_export(design, width, height, background=background,
                                profile=profile)
    if fmt == "JPEG":
        image = _flatten(image)
    temp = _atomic_target(target)
    try:
        if fmt in ("JPEG", "WEBP"):
            ok = image.save(str(temp), fmt, int(max(10, min(100, quality))))
        else:
            ok = image.save(str(temp), fmt)
        if not ok or not temp.exists() or temp.stat().st_size == 0:
            raise OSError("Qt could not encode the image.")
        os.replace(temp, target)
    finally:
        if temp.exists():
            try:
                temp.unlink()
            except OSError:
                pass
    return target, plan


def format_megapixels(width: int, height: int) -> str:
    return f"{width * height / 1_000_000:.1f} MP"


def describe_plan(plan: ExportPlan) -> str:
    bits = [f"{plan.width:,} \u00d7 {plan.height:,} px",
            format_megapixels(plan.width, plan.height),
            f"~{plan.estimated_mb:.0f} MB render"]
    if plan.supersample > 1:
        bits.append(f"{plan.supersample}\u00d7 supersampled")
    return " \u00b7 ".join(bits)


# --------------------------------------------------------------------------
# icon and web-icon exports
# --------------------------------------------------------------------------
#: Standard Windows/ICO frames. 256 is the practical ceiling for .ico.
ICO_SIZES: tuple[int, ...] = (16, 24, 32, 48, 64, 128, 256)
#: Frame sizes macOS reads from an .icns bundle.
ICNS_SIZES: tuple[int, ...] = (16, 32, 64, 128, 256, 512, 1024)
#: Everything a modern site asks for, plus a maskable-friendly 512.
WEB_KIT_SIZES: tuple[int, ...] = (16, 32, 48, 150, 180, 192, 512)
ICON_BASE = 1024
WEB_KIT_FILES: tuple[str, ...] = (
    "favicon.ico", "favicon-16x16.png", "favicon-32x32.png",
    "favicon-48x48.png", "apple-touch-icon.png", "mstile-150x150.png",
    "android-chrome-192x192.png", "android-chrome-512x512.png",
    "site.webmanifest", "browserconfig.xml", "README.txt",
)


def _png_bytes(image: QImage) -> bytes:
    buffer = QBuffer()
    buffer.open(QBuffer.OpenModeFlag.ReadWrite)
    if not image.save(buffer, "PNG"):
        raise OSError("Qt could not encode the icon frame.")
    data = bytes(buffer.data())
    buffer.close()
    return data


def _pil_image(image: QImage):
    from PIL import Image as PILImage

    return PILImage.open(io.BytesIO(_png_bytes(image))).convert("RGBA")


def _fitted_size(design, size: int) -> tuple[int, int]:
    """Aspect-preserving inside box, never larger than *size*."""
    size = max(1, int(size))
    width = max(1, int(design.width))
    height = max(1, int(design.height))
    if width >= height:
        return size, max(1, round(size * height / width))
    return max(1, round(size * width / height)), size


def render_icon_master(design, size: int = ICON_BASE, background: bool = True,
                       profile: DeviceProfile | None = None):
    """Render the design as a square icon without distorting it.

    Non-square art is centred on a transparent square. That is what desktop
    shells and favicon pickers expect, and it keeps circles circular.
    """
    size = max(16, min(4096, int(size)))
    fit_width, fit_height = _fitted_size(design, size)
    image, plan = render_export(design, fit_width, fit_height,
                                background=background, profile=profile)
    if image.width() == size and image.height() == size:
        return image, plan
    square = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    square.fill(Qt.GlobalColor.transparent)
    painter = QPainter(square)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.drawImage((size - image.width()) // 2,
                      (size - image.height()) // 2, image)
    painter.end()
    return square, plan


def _icon_base(profile: DeviceProfile | None) -> int:
    """Choose a master size this machine can render comfortably."""
    profile = profile or sample_device()
    limit = int(math.sqrt(profile.safe_pixels))
    return max(256, min(ICON_BASE, limit))


def icon_base(profile: DeviceProfile | None = None) -> int:
    """Public wrapper for the icon master size shown in the save dialog."""
    return _icon_base(profile)


def save_icon_export(design, path: str | Path, kind: str = "ico",
                     size: int | None = None, background: bool = True,
                     profile: DeviceProfile | None = None
                     ) -> tuple[Path, ExportPlan]:
    """Write a multi-resolution .ico or .icns atomically."""
    target = Path(path)
    kind = "icns" if str(kind).lower() == "icns" else "ico"
    master_size = int(size or _icon_base(profile))
    image, plan = render_icon_master(design, master_size,
                                     background=background, profile=profile)
    pil = _pil_image(image)
    temp = _atomic_target(target)
    try:
        if kind == "icns":
            pil.save(str(temp), format="ICNS")
        else:
            pil.save(str(temp), format="ICO",
                     sizes=[(side, side) for side in ICO_SIZES])
        if not temp.exists() or temp.stat().st_size == 0:
            raise OSError("The icon encoder produced no data.")
        os.replace(temp, target)
    finally:
        if temp.exists():
            try:
                temp.unlink()
            except OSError:
                pass
    return target, plan


def _manifest(name: str, background_colour: str) -> str:
    short = (name or "UmbraForge").strip() or "UmbraForge"
    short = short if len(short) <= 12 else short[:12].rstrip()
    payload = {
        "name": name or "UmbraForge",
        "short_name": short,
        "icons": [
            {"src": "android-chrome-192x192.png", "sizes": "192x192",
             "type": "image/png"},
            {"src": "android-chrome-512x512.png", "sizes": "512x512",
             "type": "image/png"},
        ],
        "theme_color": background_colour,
        "background_color": background_colour,
        "display": "standalone",
    }
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def save_web_icon_kit(design, path: str | Path, background: bool = True,
                      profile: DeviceProfile | None = None,
                      theme_colour: str = "#08080c"
                      ) -> tuple[Path, ExportPlan]:
    """Write a ready-to-drop web icon folder as a single ZIP.

    The archive contains the favicon set, Apple touch icon, Android/PWA icons,
    a Windows tile, ``site.webmanifest``, ``browserconfig.xml`` and a short
    note explaining where each file goes.
    """
    target = Path(path)
    master_size = int(_icon_base(profile))
    image, plan = render_icon_master(design, master_size,
                                     background=background, profile=profile)
    pil = _pil_image(image)
    frames: dict[int, bytes] = {}
    for side in WEB_KIT_SIZES:
        resized = pil if side == pil.width else pil.resize(
            (side, side), _resampling())
        buffer = io.BytesIO()
        resized.save(buffer, format="PNG", optimize=True)
        frames[side] = buffer.getvalue()

    temp = _atomic_target(target)
    try:
        with zipfile.ZipFile(temp, "w", zipfile.ZIP_DEFLATED) as bundle:
            bundle.writestr("favicon-16x16.png", frames[16])
            bundle.writestr("favicon-32x32.png", frames[32])
            bundle.writestr("favicon-48x48.png", frames[48])
            bundle.writestr("apple-touch-icon.png", frames[180])
            bundle.writestr("mstile-150x150.png", frames[150])
            bundle.writestr("android-chrome-192x192.png", frames[192])
            bundle.writestr("android-chrome-512x512.png", frames[512])
            ico_bytes = io.BytesIO()
            pil.save(ico_bytes, format="ICO",
                     sizes=[(side, side) for side in ICO_SIZES[:4]])
            bundle.writestr("favicon.ico", ico_bytes.getvalue())
            bundle.writestr("site.webmanifest",
                            _manifest(design.name, theme_colour))
            bundle.writestr(
                "browserconfig.xml",
                "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n"
                "<browserconfig><msapplication><tile>"
                "<square150x150logo src=\"mstile-150x150.png\"/>"
                f"<TileColor>{theme_colour}</TileColor>"
                "</tile></msapplication></browserconfig>\n")
            bundle.writestr(
                "README.txt",
                "UmbraForge web icon kit\n"
                "=======================\n\n"
                "1. Upload every file in this folder to your site root.\n"
                "2. Add these lines inside <head>:\n\n"
                "   <link rel=\"icon\" href=\"/favicon.ico\" sizes=\"any\">\n"
                "   <link rel=\"icon\" type=\"image/png\" href=\"/favicon-32x32.png\" sizes=\"32x32\">\n"
                "   <link rel=\"icon\" type=\"image/png\" href=\"/favicon-16x16.png\" sizes=\"16x16\">\n"
                "   <link rel=\"apple-touch-icon\" href=\"/apple-touch-icon.png\">\n"
                "   <link rel=\"manifest\" href=\"/site.webmanifest\">\n\n"
                "3. Keep the file names exactly as they are - the manifest and\n"
                "   browserconfig files point at them.\n")
        if not temp.exists() or temp.stat().st_size == 0:
            raise OSError("The icon kit produced no data.")
        os.replace(temp, target)
    finally:
        if temp.exists():
            try:
                temp.unlink()
            except OSError:
                pass
    return target, plan


def _resampling():
    from PIL import Image as PILImage

    return getattr(PILImage, "Resampling", PILImage).LANCZOS
