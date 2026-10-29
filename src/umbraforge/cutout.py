"""Background removal.

Three roads to a cutout:

* ``auto``  - samples the border colour and flood-fills inward, so a subject
  that shares a colour with the background but is not connected to the edge
  survives.
* ``color`` - a chroma key with soft edges and optional despill.
* ``ai``    - optional ``rembg`` model, loaded only if the user installed it.

Everything is local. Nothing is uploaded.
"""

from __future__ import annotations

import importlib.util
from collections import deque
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageFilter

from .imaging import hex_to_rgb, smoothstep


@dataclass
class CutoutResult:
    image: Image.Image
    removed: float          # fraction of pixels made transparent
    mode: str
    note: str = ""


# --------------------------------------------------------------------------
# masks
# --------------------------------------------------------------------------
def border_color(image: Image.Image) -> tuple[int, int, int]:
    """A robust background colour: median of the outer two-pixel frame."""
    rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)
    height, width = rgb.shape[:2]
    if height < 3 or width < 3:
        return (0, 0, 0)
    frame = np.concatenate([
        rgb[0:2, :, :].reshape(-1, 3),
        rgb[-2:, :, :].reshape(-1, 3),
        rgb[:, 0:2, :].reshape(-1, 3),
        rgb[:, -2:, :].reshape(-1, 3),
    ])
    return tuple(int(v) for v in np.median(frame, axis=0))


def border_connected(candidate: np.ndarray) -> np.ndarray:
    """Flood fill from the image edge through ``candidate`` pixels.

    Scanline spans keep this quick in pure NumPy/Python - no SciPy or OpenCV,
    which keeps the install light.
    """
    height, width = candidate.shape
    visited = np.zeros((height, width), dtype=bool)
    if height == 0 or width == 0:
        return visited

    stack: deque[tuple[int, int]] = deque()
    for x in range(width):
        if candidate[0, x]:
            stack.append((0, x))
        if height > 1 and candidate[height - 1, x]:
            stack.append((height - 1, x))
    for y in range(height):
        if candidate[y, 0]:
            stack.append((y, 0))
        if width > 1 and candidate[y, width - 1]:
            stack.append((y, width - 1))

    while stack:
        y, x = stack.pop()
        if visited[y, x] or not candidate[y, x]:
            continue
        row = candidate[y]
        left = x
        while left > 0 and row[left - 1] and not visited[y, left - 1]:
            left -= 1
        right = x
        while right + 1 < width and row[right + 1] and not visited[y, right + 1]:
            right += 1
        visited[y, left:right + 1] = True

        for next_y in (y - 1, y + 1):
            if not (0 <= next_y < height):
                continue
            next_row = candidate[next_y]
            next_seen = visited[next_y]
            spans = next_row[left:right + 1] & ~next_seen[left:right + 1]
            if not spans.any():
                continue
            indexes = np.flatnonzero(spans)
            start = indexes[0]
            previous = start
            for index in indexes[1:]:
                if index != previous + 1:
                    stack.append((next_y, left + start))
                    start = index
                previous = index
            stack.append((next_y, left + start))
    return visited


def _distance(rgb: np.ndarray, color: tuple[int, int, int]) -> np.ndarray:
    delta = rgb.astype(np.int16) - np.array(color, dtype=np.int16)
    # Perceptual weighting keeps skin and warm backgrounds from clipping early.
    weights = np.array([0.30, 0.59, 0.11], dtype=np.float32)
    return np.sqrt((delta.astype(np.float32) ** 2 * weights).sum(axis=-1))


def auto_mask(image: Image.Image, tolerance: float = 32.0,
              sample: tuple[int, int, int] | None = None) -> tuple[np.ndarray, tuple[int, int, int]]:
    rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)
    color = sample or border_color(image)
    candidate = _distance(rgb, color) <= max(1.0, float(tolerance))
    return border_connected(candidate), color


def color_mask(image: Image.Image, key: tuple[int, int, int],
               tolerance: float = 32.0, softness: float = 24.0) -> np.ndarray:
    rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)
    distance = _distance(rgb, key)
    low = max(0.0, float(tolerance))
    high = low + max(1.0, float(softness))
    if softness <= 0.5:
        return distance <= low
    blend = smoothstep(low, high, distance)
    return blend > 0.02


def chroma_alpha(image: Image.Image, key: tuple[int, int, int],
                 tolerance: float = 32.0, softness: float = 24.0) -> np.ndarray:
    """Soft alpha for a chroma key (255 = keep)."""
    rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)
    distance = _distance(rgb, key)
    low = max(0.0, float(tolerance))
    high = low + max(1.0, float(softness))
    if softness <= 0.5:
        return np.where(distance <= low, 0.0, 1.0).astype(np.float32)
    return smoothstep(low, high, distance)


def despill(image: Image.Image, key: tuple[int, int, int],
            alpha: np.ndarray, strength: float = 0.65) -> Image.Image:
    """Pull the key colour out of the soft edge so fringes disappear."""
    rgb = np.asarray(image.convert("RGB"), dtype=np.float32)
    dominant = int(np.argmax(key))
    others = [index for index in range(3) if index != dominant]
    limit = np.maximum(rgb[..., others[0]], rgb[..., others[1]])
    excess = np.maximum(0.0, rgb[..., dominant] - limit)
    edge = np.clip(1.0 - alpha, 0.0, 1.0)
    rgb[..., dominant] -= excess * edge * float(strength)
    rgba = np.dstack([np.clip(rgb, 0, 255).astype(np.uint8),
                      np.asarray(image.convert("RGBA"))[..., 3]])
    return Image.fromarray(rgba, "RGBA")


# --------------------------------------------------------------------------
# alpha shaping
# --------------------------------------------------------------------------
def shape_alpha(alpha: np.ndarray, feather: float = 0.0,
                shrink: float = 0.0) -> Image.Image:
    mask = Image.fromarray(np.clip(alpha * 255.0, 0, 255).astype(np.uint8), "L")
    shrink = float(shrink)
    if shrink >= 1.0:
        size = int(min(15, round(shrink))) * 2 + 1
        mask = mask.filter(ImageFilter.MinFilter(size))
    elif shrink <= -1.0:
        size = int(min(15, round(abs(shrink)))) * 2 + 1
        mask = mask.filter(ImageFilter.MaxFilter(size))
    if feather >= 0.2:
        mask = mask.filter(ImageFilter.GaussianBlur(float(feather)))
    return mask


def _compose(image: Image.Image, mask: Image.Image,
             despill_key: tuple[int, int, int] | None = None) -> tuple[Image.Image, float]:
    rgba = image.convert("RGBA")
    alpha = np.asarray(mask, dtype=np.float32) / 255.0
    if despill_key is not None:
        rgba = despill(rgba, despill_key, alpha)
    array = np.asarray(rgba, dtype=np.uint8).copy()
    array[..., 3] = (array[..., 3].astype(np.float32) * alpha).astype(np.uint8)
    removed = 1.0 - float(array[..., 3].mean() / 255.0)
    return Image.fromarray(array, "RGBA"), removed


# --------------------------------------------------------------------------
# public API
# --------------------------------------------------------------------------
def remove_background(image: Image.Image, mode: str = "auto",
                      color: str | tuple[int, int, int] | None = None,
                      tolerance: float = 32.0, softness: float = 24.0,
                      feather: float = 1.5, shrink: float = 0.0
                      ) -> CutoutResult:
    """Remove a background with the offline engine.

    ``tolerance`` is a 0..255 colour distance. ``feather`` blurs the edge,
    ``shrink`` erodes the subject (negative values grow it).
    """
    image = image.convert("RGBA")
    if mode == "ai":
        return remove_background_ai(image)

    if mode == "color":
        key = hex_to_rgb(color, (0, 255, 0)) if isinstance(color, str) else (
            color or (0, 255, 0))
        alpha = chroma_alpha(image, key, tolerance, softness)
        mask = shape_alpha(alpha, feather=feather, shrink=shrink)
        result, removed = _compose(image, mask, despill_key=key)
        return CutoutResult(result, removed, "color",
                            f"Keyed {key[0]}, {key[1]}, {key[2]}")

    sample = color if isinstance(color, tuple) else (
        hex_to_rgb(color) if isinstance(color, str) else None)
    background, used = auto_mask(image, tolerance, sample)
    keep = (~background).astype(np.float32)
    mask = shape_alpha(keep, feather=feather, shrink=shrink)
    result, removed = _compose(image, mask)
    return CutoutResult(result, removed, "auto",
                        f"Sampled background {used[0]}, {used[1]}, {used[2]}")


def ai_available() -> bool:
    return importlib.util.find_spec("rembg") is not None


def ai_status() -> str:
    if ai_available():
        return "AI cutout is available (rembg detected)."
    return ("AI cutout needs the optional rembg package. Install it with: "
            "pip install rembg onnxruntime")


_SESSION = None


def remove_background_ai(image: Image.Image, model: str = "u2net") -> CutoutResult:
    global _SESSION
    if not ai_available():
        raise RuntimeError(ai_status())
    from rembg import new_session, remove  # type: ignore

    if _SESSION is None:
        _SESSION = new_session(model)
    cut = remove(image.convert("RGBA"), session=_SESSION)
    if not isinstance(cut, Image.Image):
        cut = Image.open(cut)
    cut = cut.convert("RGBA")
    alpha = np.asarray(cut.getchannel("A"), dtype=np.float32) / 255.0
    removed = 1.0 - float(alpha.mean())
    note = cut.getbbox()
    return CutoutResult(cut, removed, "ai",
                        "AI matte ready." if note else "AI found nothing to keep.")


def auto_trim(image: Image.Image, padding: int = 0) -> Image.Image:
    """Crop fully transparent borders (used after a cutout)."""
    rgba = image.convert("RGBA")
    box = rgba.getchannel("A").getbbox()
    if not box:
        return rgba
    left, top, right, bottom = box
    left = max(0, left - padding)
    top = max(0, top - padding)
    right = min(rgba.width, right + padding)
    bottom = min(rgba.height, bottom + padding)
    return rgba.crop((left, top, right, bottom))
