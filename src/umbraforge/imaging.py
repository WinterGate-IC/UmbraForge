"""Raster helpers shared by the renderer and the cutout tools.

Qt owns drawing; Pillow and NumPy own pixels. Keeping the conversion in one
place makes it obvious where colour management and alpha handling happen.
"""

from __future__ import annotations

import io
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps


def open_image(data: bytes | Path | str) -> Image.Image:
    """Load an image, honour EXIF rotation and return RGBA."""
    if isinstance(data, (str, Path)):
        image = Image.open(data)
    else:
        image = Image.open(io.BytesIO(data))
    image.load()
    try:
        image = ImageOps.exif_transpose(image)
    except Exception:
        pass
    return image.convert("RGBA")


def encode_png(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def hex_to_rgb(value: str, fallback: tuple[int, int, int] = (255, 122, 61)) -> tuple[int, int, int]:
    text = (value or "").strip().lstrip("#")
    if len(text) == 3:
        text = "".join(ch * 2 for ch in text)
    if len(text) != 6:
        return fallback
    try:
        return (int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16))
    except ValueError:
        return fallback


def rgba_to_hex(red: int, green: int, blue: int) -> str:
    return f"#{int(red):02x}{int(green):02x}{int(blue):02x}"


def _setting(settings: dict, key: str, default: float) -> float:
    """Read a numeric adjustment, keeping meaningful zeroes like saturation=0."""
    value = settings.get(key, default)
    try:
        return float(default if value is None else value)
    except (TypeError, ValueError):
        return float(default)


def _luma(rgb: "np.ndarray") -> "np.ndarray":
    return (rgb[..., 0] * 0.2126 + rgb[..., 1] * 0.7152
            + rgb[..., 2] * 0.0722)


def _hue_matrix(hue: float) -> "np.ndarray":
    angle = float(hue) * np.pi
    cos_a, sin_a = np.cos(angle), np.sin(angle)
    return np.array([
        [0.213 + cos_a * 0.787 - sin_a * 0.213,
         0.715 - cos_a * 0.715 - sin_a * 0.715,
         0.072 - cos_a * 0.072 + sin_a * 0.928],
        [0.213 - cos_a * 0.213 + sin_a * 0.143,
         0.715 + cos_a * 0.285 + sin_a * 0.140,
         0.072 - cos_a * 0.072 - sin_a * 0.283],
        [0.213 - cos_a * 0.213 - sin_a * 0.787,
         0.715 - cos_a * 0.715 + sin_a * 0.715,
         0.072 + cos_a * 0.928 + sin_a * 0.072],
    ], dtype=np.float32)


#: Defaults mirrored from ``layers.ADJUSTMENT_DEFAULTS``. Kept here as well so
#: the raster layer never needs to import the document model.
_ADJUSTMENT_DEFAULTS = {
    "brightness": 1.0, "contrast": 1.0, "saturation": 1.0,
    "warmth": 0.0, "hue": 0.0, "vignette": 0.0,
    "exposure": 0.0, "highlights": 0.0, "shadows": 0.0,
    "whites": 0.0, "blacks": 0.0, "gamma": 1.0, "fade": 0.0,
    "temperature": 0.0, "tint": 0.0, "vibrance": 0.0,
    "sepia": 0.0, "monochrome": 0.0, "invert": 0.0, "posterize": 0.0,
    "sharpness": 0.0, "clarity": 0.0, "noise_reduction": 0.0,
    "blur": 0.0, "grain": 0.0,
}


def is_identity(settings: dict | None) -> bool:
    """True when the stack would leave every pixel untouched."""
    if not settings:
        return True
    for key, default in _ADJUSTMENT_DEFAULTS.items():
        if abs(_setting(settings, key, default) - default) >= 0.001:
            return False
    return True


def adjustment_groups() -> list[tuple[str, list[tuple]]]:
    """UI metadata: (tab, key, label, minimum, maximum, default, decimals, suffix)."""
    return [
        ("Light", [
            ("exposure", "Exposure", -3.0, 3.0, 0.0, 2, " EV"),
            ("brightness", "Brightness", 0.2, 2.0, 1.0, 2, "\u00d7"),
            ("contrast", "Contrast", 0.2, 2.0, 1.0, 2, "\u00d7"),
            ("highlights", "Highlights", -1.0, 1.0, 0.0, 2, ""),
            ("shadows", "Shadows", -1.0, 1.0, 0.0, 2, ""),
            ("whites", "Whites", -1.0, 1.0, 0.0, 2, ""),
            ("blacks", "Blacks", -1.0, 1.0, 0.0, 2, ""),
            ("gamma", "Gamma", 0.2, 3.0, 1.0, 2, ""),
            ("fade", "Fade / matte", 0.0, 1.0, 0.0, 2, ""),
        ]),
        ("Colour", [
            ("temperature", "Temperature", -1.0, 1.0, 0.0, 2, ""),
            ("tint", "Tint", -1.0, 1.0, 0.0, 2, ""),
            ("vibrance", "Vibrance", -1.0, 1.0, 0.0, 2, ""),
            ("saturation", "Saturation", 0.0, 2.0, 1.0, 2, "\u00d7"),
            ("hue", "Hue rotate", -1.0, 1.0, 0.0, 2, ""),
            ("warmth", "Warmth (legacy)", -1.0, 1.0, 0.0, 2, ""),
            ("sepia", "Sepia", 0.0, 1.0, 0.0, 2, ""),
            ("monochrome", "Monochrome", 0.0, 1.0, 0.0, 2, ""),
            ("invert", "Invert", 0.0, 1.0, 0.0, 1, ""),
            ("posterize", "Posterize levels", 0.0, 32.0, 0.0, 0, ""),
        ]),
        ("Detail", [
            ("sharpness", "Sharpness", 0.0, 3.0, 0.0, 2, ""),
            ("clarity", "Clarity", 0.0, 3.0, 0.0, 2, ""),
            ("noise_reduction", "Noise reduction", 0.0, 1.0, 0.0, 2, ""),
            ("blur", "Lens blur", 0.0, 1.0, 0.0, 2, ""),
            ("grain", "Film grain", 0.0, 1.0, 0.0, 2, ""),
        ]),
        ("Finish", [
            ("vignette", "Vignette", -1.0, 1.0, 0.0, 2, ""),
        ]),
    ]


def _detail_pass(rgb: "np.ndarray", settings: dict) -> "np.ndarray":
    """Pillow-powered blur/sharpen passes, kept off the hot array path."""
    noise = max(0.0, min(1.0, _setting(settings, "noise_reduction", 0.0)))
    blur = max(0.0, min(1.0, _setting(settings, "blur", 0.0)))
    clarity = max(0.0, min(3.0, _setting(settings, "clarity", 0.0)))
    sharp = max(0.0, min(3.0, _setting(settings, "sharpness", 0.0)))
    if noise < 0.001 and blur < 0.001 and clarity < 0.001 and sharp < 0.001:
        return rgb
    from PIL import ImageFilter

    height, width = rgb.shape[:2]
    shortest = max(1.0, min(width, height))
    base = Image.fromarray((np.clip(rgb, 0.0, 1.0) * 255.0 + 0.5)
                           .astype(np.uint8), "RGB")
    if noise >= 0.001:
        radius = 0.6 + noise * shortest * 0.012
        smoothed = base.filter(ImageFilter.GaussianBlur(radius))
        base = Image.blend(base, smoothed, min(0.92, noise))
    if blur >= 0.001:
        base = base.filter(ImageFilter.GaussianBlur(
            0.4 + blur * shortest * 0.02))
    if clarity >= 0.001:
        base = base.filter(ImageFilter.UnsharpMask(
            radius=max(1.0, shortest * 0.006),
            percent=int(clarity * 95), threshold=3))
    if sharp >= 0.001:
        base = base.filter(ImageFilter.UnsharpMask(
            radius=1.1, percent=int(sharp * 130), threshold=2))
    return np.asarray(base, dtype=np.float32) / 255.0


def adjust(image: Image.Image, settings: dict) -> Image.Image:
    """Apply the non-destructive image adjustment stack.

    The order is deliberate: exposure and tone first, colour next, then local
    detail, then finish. Alpha is never adjusted, so cutouts stay crisp.
    """
    source = image.convert("RGBA")
    if is_identity(settings):
        return source

    array = np.asarray(source, dtype=np.float32) / 255.0
    rgb = array[..., :3].copy()

    exposure = _setting(settings, "exposure", 0.0)
    brightness = _setting(settings, "brightness", 1.0)
    contrast = _setting(settings, "contrast", 1.0)
    saturation = _setting(settings, "saturation", 1.0)
    warmth = _setting(settings, "warmth", 0.0)
    hue = _setting(settings, "hue", 0.0)
    vignette = _setting(settings, "vignette", 0.0)
    highlights = _setting(settings, "highlights", 0.0)
    shadows = _setting(settings, "shadows", 0.0)
    whites = _setting(settings, "whites", 0.0)
    blacks = _setting(settings, "blacks", 0.0)
    gamma = _setting(settings, "gamma", 1.0)
    fade = _setting(settings, "fade", 0.0)
    temperature = _setting(settings, "temperature", 0.0)
    tint = _setting(settings, "tint", 0.0)
    vibrance = _setting(settings, "vibrance", 0.0)
    sepia = _setting(settings, "sepia", 0.0)
    monochrome = _setting(settings, "monochrome", 0.0)
    invert = _setting(settings, "invert", 0.0)
    posterize = _setting(settings, "posterize", 0.0)
    grain = _setting(settings, "grain", 0.0)

    if abs(exposure) > 0.0001:
        rgb *= float(2.0 ** exposure)
    if abs(temperature) > 0.0001 or abs(tint) > 0.0001:
        rgb[..., 0] += temperature * 0.12
        rgb[..., 2] -= temperature * 0.12
        rgb[..., 1] += tint * 0.09
    if abs(brightness - 1.0) > 0.0001:
        rgb *= brightness
    if abs(contrast - 1.0) > 0.0001:
        rgb = (rgb - 0.5) * contrast + 0.5
    if abs(highlights) > 0.0001 or abs(shadows) > 0.0001:
        light = np.clip(_luma(rgb), 0.0, 1.0)[..., None]
        shadow_mask = (1.0 - light) ** 2
        highlight_mask = light ** 2
        rgb += shadows * 0.45 * shadow_mask
        rgb += highlights * 0.45 * highlight_mask
    if abs(whites) > 0.0001 or abs(blacks) > 0.0001:
        light = np.clip(_luma(rgb), 0.0, 1.0)[..., None]
        rgb += whites * 0.35 * (light ** 3)
        rgb -= blacks * 0.35 * ((1.0 - light) ** 3)
    if abs(gamma - 1.0) > 0.0001 and gamma > 0.01:
        rgb = np.power(np.clip(rgb, 0.0, None), 1.0 / gamma)
    if fade > 0.0001:
        rgb = rgb * (1.0 - fade * 0.35) + fade * 0.14
        rgb = (rgb - 0.5) * (1.0 - fade * 0.22) + 0.5

    if abs(saturation - 1.0) > 0.0001:
        light = _luma(rgb)[..., None]
        rgb = light + (rgb - light) * saturation

    if abs(vibrance) > 0.0001:
        light = _luma(rgb)[..., None]
        high = np.max(rgb, axis=2)[..., None]
        low = np.min(rgb, axis=2)[..., None]
        already = np.clip(high - low, 0.0, 1.0)
        amount = vibrance * 0.9 * (1.0 - already)
        rgb = light + (rgb - light) * (1.0 + amount)

    if abs(hue) > 0.0001:
        rgb = rgb @ _hue_matrix(hue).T

    if abs(warmth) > 0.0001:
        rgb[..., 0] += warmth * 0.10
        rgb[..., 1] += warmth * 0.02
        rgb[..., 2] -= warmth * 0.10

    if sepia > 0.0001:
        mix = np.array([[0.393, 0.769, 0.189],
                        [0.349, 0.686, 0.168],
                        [0.272, 0.534, 0.131]], dtype=np.float32)
        rgb = rgb * (1.0 - sepia) + (rgb @ mix.T) * sepia
    if monochrome > 0.0001:
        light = _luma(rgb)[..., None]
        rgb = rgb * (1.0 - monochrome) + light * monochrome
    if invert > 0.0001:
        rgb = rgb * (1.0 - invert) + (1.0 - rgb) * invert
    if posterize >= 2.0:
        levels = max(2, int(round(posterize)))
        rgb = np.round(np.clip(rgb, 0.0, 1.0) * (levels - 1)) / (levels - 1)

    rgb = _detail_pass(rgb, settings)

    if abs(vignette) > 0.0001:
        height, width = rgb.shape[:2]
        ys = np.linspace(-1.0, 1.0, height, dtype=np.float32)[:, None]
        xs = np.linspace(-1.0, 1.0, width, dtype=np.float32)[None, :]
        distance = np.sqrt(xs * xs + ys * ys) / np.sqrt(2.0)
        falloff = np.clip((distance - 0.32) / 0.68, 0.0, 1.0) ** 2
        if vignette > 0:
            rgb *= (1.0 - falloff[..., None] * vignette)
        else:
            rgb += falloff[..., None] * (-vignette) * 0.22

    if grain > 0.0001:
        rng = np.random.default_rng(20260214)
        noise = rng.normal(0.0, 0.10 * grain, rgb.shape[:2]).astype(np.float32)
        rgb += noise[..., None]

    array[..., :3] = np.clip(rgb, 0.0, 1.0)
    out = (array * 255.0 + 0.5).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def resize_cover(image: Image.Image, width: int, height: int,
                 mode: str = "cover") -> Image.Image:
    """Resize for a layer box, preserving the source aspect where asked."""
    width, height = max(1, int(width)), max(1, int(height))
    if mode == "fill":
        return image.resize((width, height), Image.Resampling.LANCZOS)
    source_w, source_h = image.size
    if not source_w or not source_h:
        return image.resize((width, height), Image.Resampling.LANCZOS)
    scale = (max(width / source_w, height / source_h) if mode == "cover"
             else min(width / source_w, height / source_h))
    target = (max(1, round(source_w * scale)), max(1, round(source_h * scale)))
    resized = image.resize(target, Image.Resampling.LANCZOS)
    if mode == "contain":
        canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        canvas.paste(resized, ((width - target[0]) // 2,
                               (height - target[1]) // 2))
        return canvas
    left = (target[0] - width) // 2
    top = (target[1] - height) // 2
    return resized.crop((left, top, left + width, top + height))


def blur_alpha(image: Image.Image, radius: float) -> Image.Image:
    if radius <= 0.05:
        return image
    from PIL import ImageFilter

    alpha = image.getchannel("A").filter(ImageFilter.GaussianBlur(radius))
    output = image.copy()
    output.putalpha(alpha)
    return output


def tint_mask(mask: Image.Image, color: tuple[int, int, int],
              opacity: float = 1.0) -> Image.Image:
    rgba = Image.new("RGBA", mask.size, (*color, 0))
    if mask.mode == "L":
        alpha = mask
    elif "A" in mask.getbands():
        alpha = mask.getchannel("A")
    else:
        alpha = mask.convert("L")
    if opacity < 0.999:
        alpha = alpha.point(lambda value: int(value * opacity))
    rgba.putalpha(alpha)
    return rgba


# --------------------------------------------------------------------------
# Qt bridges (imported lazily so tests can exercise the raster side alone)
# --------------------------------------------------------------------------
def pil_to_qimage(image: Image.Image):
    from PySide6.QtGui import QImage

    rgba = image.convert("RGBA")
    width, height = rgba.size
    data = rgba.tobytes("raw", "RGBA")
    qimage = QImage(data, width, height, width * 4, QImage.Format.Format_RGBA8888)
    return qimage.copy()


def qimage_to_pil(image) -> Image.Image:
    from PySide6.QtGui import QImage

    converted = image.convertToFormat(QImage.Format.Format_RGBA8888)
    width, height = converted.width(), converted.height()
    stride = converted.bytesPerLine()
    data = bytes(converted.constBits())
    if stride != width * 4:
        rows = [data[y * stride:y * stride + width * 4] for y in range(height)]
        data = b"".join(rows)
    return Image.frombytes("RGBA", (width, height), data)


def smoothstep(low: float, high: float, values: "np.ndarray") -> "np.ndarray":
    span = max(1e-6, high - low)
    scaled = np.clip((values - low) / span, 0.0, 1.0)
    return scaled * scaled * (3.0 - 2.0 * scaled)
