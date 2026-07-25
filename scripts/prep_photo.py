#!/usr/bin/env python3
"""Turn a source photo into a clean, background-free portrait for ASCII rendering.

Usage:
    python scripts/prep_photo.py [source-photo.jpg]

Writes data/portrait.png -- an RGBA image, subject isolated, auto-cropped,
contrast-normalised and ready for scripts/make_ascii_svg.py.

Background removal uses rembg when it is installed. If it is not available
(or NO_REMBG=1 is set) the script falls back to keeping the whole frame,
which still works but gives busier ASCII behind the subject.
"""

import os
import sys

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

SRC_DEFAULT = "source-photo.jpg"
OUT = os.path.join("data", "portrait.png")

# Working resolution. The ASCII pass downsamples heavily, so this only needs
# to be big enough to keep edges crisp.
WORK_SIZE = 900

# Alpha below this counts as background when auto-cropping.
ALPHA_FLOOR = 24

# Padding kept around the subject bounding box, as a fraction of its size.
CROP_PAD = 0.04


def load(path):
    if not os.path.exists(path):
        sys.exit(f"error: {path} not found. Put your photo there (or pass a path).")
    img = Image.open(path)
    img = ImageOps.exif_transpose(img)
    return img.convert("RGBA")


def cutout(img):
    """Remove the background, returning RGBA with a real alpha channel."""
    if os.environ.get("NO_REMBG") == "1":
        print("  background removal skipped (NO_REMBG=1)")
        return img
    try:
        from rembg import remove
    except ImportError:
        print("  rembg not installed -- keeping full frame")
        return img
    print("  removing background (first run downloads the u2net model)...")
    return remove(img).convert("RGBA")


def autocrop(img):
    """Crop to the subject's alpha bounding box, with a little breathing room."""
    alpha = np.array(img.split()[-1])
    ys, xs = np.where(alpha > ALPHA_FLOOR)
    if len(xs) == 0:
        return img
    x0, x1 = int(xs.min()), int(xs.max())
    y0, y1 = int(ys.min()), int(ys.max())
    pad_x = int((x1 - x0) * CROP_PAD)
    pad_y = int((y1 - y0) * CROP_PAD)
    box = (
        max(0, x0 - pad_x),
        max(0, y0 - pad_y),
        min(img.width, x1 + pad_x + 1),
        min(img.height, y1 + pad_y + 1),
    )
    return img.crop(box)


def normalise(img):
    """Stretch the subject's tonal range so the ASCII ramp uses every glyph."""
    rgb = img.convert("RGB")
    alpha = img.split()[-1]

    grey = np.array(rgb.convert("L"), dtype=np.float32)
    mask = np.array(alpha) > ALPHA_FLOOR
    if mask.sum() < 100:
        mask = np.ones_like(mask, dtype=bool)

    # Percentile stretch on subject pixels only -- background must not skew it.
    lo, hi = np.percentile(grey[mask], (2, 98))
    if hi - lo < 1:
        lo, hi = float(grey.min()), float(grey.max()) or 1.0
    grey = np.clip((grey - lo) / max(hi - lo, 1e-6), 0, 1) * 255.0

    out = Image.fromarray(grey.astype(np.uint8), mode="L").convert("RGBA")
    out.putalpha(alpha)

    # A touch of local contrast keeps facial features legible once the image
    # is squashed down to ~70 characters wide.
    out = out.filter(ImageFilter.UnsharpMask(radius=2, percent=90, threshold=3))
    return ImageEnhance.Contrast(out).enhance(1.12)


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else SRC_DEFAULT
    print(f"reading {src}")
    img = load(src)

    if max(img.size) > WORK_SIZE:
        img.thumbnail((WORK_SIZE, WORK_SIZE), Image.LANCZOS)

    img = cutout(img)
    img = autocrop(img)
    img = normalise(img)

    os.makedirs("data", exist_ok=True)
    img.save(OUT)
    print(f"wrote {OUT}  ({img.width}x{img.height})")


if __name__ == "__main__":
    main()
