#!/usr/bin/env python3
"""Composite the appreciation certificate at print resolution."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
OUT = ROOT / "output"
OUT.mkdir(exist_ok=True)

SCALE = 3
SRC_W, SRC_H = 1600, 1066
W, H = SRC_W * SCALE, SRC_H * SCALE

OVAL_CX, OVAL_CY = 229, 448
OVAL_RX, OVAL_RY = 140, 196

# Source-pixel regions (ink to remove).
SCHOOLS_BOX = (420, 352, 1540, 448)
NAME_BOX = (478, 500, 1560, 708)

PARCHMENT = (252, 246, 232)


def inpaint_ink(base: Image.Image, box_src: tuple[int, int, int, int]) -> None:
    """Replace non-parchment ink in a box with nearby parchment color."""
    x0, y0, x1, y1 = [v * SCALE for v in box_src]
    x0 = max(0, x0)
    y0 = max(0, y0)
    x1 = min(W, x1)
    y1 = min(H, y1)
    crop = base.crop((x0, y0, x1, y1))
    arr = np.array(crop).astype(np.float32)
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    luma = 0.299 * r + 0.587 * g + 0.114 * b
    # Parchment is very light; ink/gold/calligraphy is darker or more saturated.
    sat = np.maximum(np.maximum(r, g), b) - np.minimum(np.minimum(r, g), b)
    gold = (r > g) & (g > b - 8) & (sat > 18) & (luma < 248)
    ink = (luma < 232) | ((sat > 22) & (luma < 246)) | gold
    # Dilate ink mask so serifs and anti-alias disappear.
    mask = Image.fromarray((ink * 255).astype(np.uint8), "L")
    mask = mask.filter(ImageFilter.MaxFilter(7))
    mask = mask.filter(ImageFilter.GaussianBlur(SCALE * 0.7))
    m = np.array(mask).astype(np.float32) / 255.0
    # Sample parchment from the lightest pixels in the crop.
    light = luma > 235
    if light.any():
        parch = np.array(
            [r[light].mean(), g[light].mean(), b[light].mean()],
            dtype=np.float32,
        )
    else:
        parch = np.array(PARCHMENT, dtype=np.float32)
    rng = np.random.default_rng(7)
    fill = np.clip(parch + rng.normal(0, 1.4, arr.shape), 0, 255)
    out = arr * (1 - m[..., None]) + fill * m[..., None]
    base.paste(Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)), (x0, y0))


def paste_oval_portrait(base: Image.Image, portrait: Image.Image) -> None:
    cx, cy = OVAL_CX * SCALE, OVAL_CY * SCALE
    rx, ry = OVAL_RX * SCALE, OVAL_RY * SCALE
    target_w, target_h = rx * 2, ry * 2
    src = portrait.convert("RGB")
    aspect = target_w / target_h
    sw, sh = src.size
    if sw / sh > aspect:
        nw = int(sh * aspect)
        src = src.crop(((sw - nw) // 2, 0, (sw + nw) // 2, sh))
    else:
        nh = int(sw / aspect)
        top = max(0, int((sh - nh) * 0.02))
        src = src.crop((0, top, sw, min(sh, top + nh)))
    src = src.resize((target_w, target_h), Image.Resampling.LANCZOS)

    mask = Image.new("L", (target_w, target_h), 0)
    ImageDraw.Draw(mask).ellipse((1, 1, target_w - 2, target_h - 2), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(1.2))
    x = cx - target_w // 2
    y = cy - target_h // 2
    base.paste(src, (x, y), mask)


def make_name_rgba(path: Path) -> Image.Image:
    im = Image.open(path).convert("RGBA")
    arr = np.array(im)
    rgb = arr[:, :, :3].astype(np.float32)
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    mx = rgb.max(axis=2)
    mn = rgb.min(axis=2)
    sat = mx - mn
    luma = 0.299 * r + 0.587 * g + 0.114 * b
    navy = (b > r + 8) & (luma < 170)
    gold = (r > 150) & (g > 110) & (r - b > 35)
    ink = navy | gold
    ys, xs = np.where(ink)
    pad = 18
    box = (
        max(0, int(xs.min()) - pad),
        max(0, int(ys.min()) - pad),
        min(im.size[0], int(xs.max()) + pad),
        min(im.size[1], int(ys.max()) + pad),
    )
    is_bg = (luma > 218) & (sat < 42)
    alpha = np.where(is_bg, 0, 255).astype(np.uint8)
    a = Image.fromarray(alpha, "L").filter(ImageFilter.GaussianBlur(0.55))
    arr[:, :, 3] = np.array(a)
    return Image.fromarray(arr, "RGBA").crop(box)


def paste_name(base: Image.Image, name_img: Image.Image) -> None:
    # Fit the shorter name into the original name band (~y 505–700).
    target_h = int(228 * SCALE)
    ratio = target_h / name_img.size[1]
    target_w = int(name_img.size[0] * ratio)
    name_img = name_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
    cx = int(990 * SCALE)
    x = cx - target_w // 2
    y = int(488 * SCALE)
    base.paste(name_img, (x, y), name_img.split()[-1])


def draw_schools(base: Image.Image) -> None:
    font = ImageFont.truetype(str(ROOT / "fonts" / "Amiri-Regular.ttf"), int(36 * SCALE))
    draw = ImageDraw.Draw(base)
    cx = int(980 * SCALE)
    color = (22, 20, 24)
    lines = [
        (int(370 * SCALE), "يسعدنا نحن أساتذة م.م أولاد عثمان، م.م تسركات، م.م أفلاندرا،"),
        (int(418 * SCALE), "والمدرسة الجماعاتية تنسيفت"),
    ]
    for y, text in lines:
        draw.text(
            (cx, y),
            text,
            font=font,
            fill=color,
            anchor="mm",
            language="ar",
            direction="rtl",
        )


def to_a4(im: Image.Image) -> Image.Image:
    a4 = Image.new("RGB", (3508, 2480), PARCHMENT)
    scale = max(3508 / im.size[0], 2480 / im.size[1])
    nw, nh = int(im.size[0] * scale), int(im.size[1] * scale)
    fitted = im.resize((nw, nh), Image.Resampling.LANCZOS)
    a4.paste(fitted, ((3508 - nw) // 2, (2480 - nh) // 2))
    return a4


def main() -> None:
    base = Image.open(ASSETS / "original-certificate.jpg").convert("RGB")
    base = base.resize((W, H), Image.Resampling.LANCZOS)
    inpaint_ink(base, SCHOOLS_BOX)
    inpaint_ink(base, NAME_BOX)
    paste_oval_portrait(base, Image.open(ASSETS / "inspector-portrait.jpg"))
    paste_name(base, make_name_rgba(ASSETS / "name-mourad-wide.jpg"))
    draw_schools(base)

    hi = OUT / "shahada-mourad-boustawi.png"
    a4_path = OUT / "shahada-mourad-boustawi-a4.png"
    pdf_path = OUT / "shahada-mourad-boustawi-a4.pdf"
    base.save(hi, "PNG")
    a4 = to_a4(base)
    a4.save(a4_path, "PNG")
    a4.convert("RGB").save(pdf_path, "PDF", resolution=300.0)
    base.resize((1600, 1066), Image.Resampling.LANCZOS).save(
        OUT / "preview.jpg", quality=93
    )
    print("wrote", hi, base.size)
    print("wrote", a4_path, pdf_path)


if __name__ == "__main__":
    main()
