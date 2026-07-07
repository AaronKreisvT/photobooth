# fotobox/processing/template_compositor.py
from __future__ import annotations

import os
import math
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional

from PIL import Image, ImageDraw, ImageFont, ImageOps

Rect = Tuple[int, int, int, int]  # (left, top, right, bottom)

def rect_norm(p1: Tuple[int, int], p2: Tuple[int, int]) -> Rect:
    x1, y1 = p1
    x2, y2 = p2
    left, right = sorted([x1, x2])
    top, bottom = sorted([y1, y2])
    return (left, top, right, bottom)

def resize_cover(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Scale+crop to fill exactly target size."""
    iw, ih = img.size
    scale = max(target_w / iw, target_h / ih)
    nw, nh = int(math.ceil(iw * scale)), int(math.ceil(ih * scale))
    img2 = img.resize((nw, nh), Image.Resampling.LANCZOS)
    left = (nw - target_w) // 2
    top = (nh - target_h) // 2
    return img2.crop((left, top, left + target_w, top + target_h))

@dataclass(frozen=True)
class TextField:
    """
    pos: (x, y) in px, origin top-left (wie Pillow üblich).
    anchor:
      - "mm" = center-center (ideal für horizontal zentriert)
      - "lt" = left-top
    max_width: optional shrink-to-fit
    """
    pos: Tuple[int, int]
    font_px: int = 42
    color: Tuple[int, int, int] = (0, 0, 0) # schwarz default
    anchor: str = "lt"
    max_width: Optional[int] = None
    font_path: Optional[str] = None # custom font

@dataclass(frozen=True)
class TemplateSpec:
    bg_path: str
    slots: List[Rect]  # photo rects

    # slot_fg: overlay (Rahmen/Maske) über einem Slot.
    # Darf kleiner als der Slot sein und wird dann zentriert platziert.
    slot_fg_path: Optional[str] = None
    slot_fg_index: int = 0

    # text fields on final canvas
    text_fields: Dict[str, TextField] = None
    default_font_path: Optional[str] = None

def _try_load_font(px: int, font_path: Optional[str] = None, default_font_path: Optional[str] = None) -> ImageFont.FreeTypeFont:
    # 1) Explizit gesetzter Font im TextField
    if font_path and os.path.exists(font_path):
        try:
            return ImageFont.truetype(font_path, px)
        except Exception:
            pass

    # 2) Default-Font aus TemplateSpec
    if default_font_path and os.path.exists(default_font_path):
        try:
            return ImageFont.truetype(default_font_path, px)
        except Exception:
            pass

    # 3) System fallback
    for path in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    ]:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, px)
            except Exception:
                pass

    return ImageFont.load_default()

def _draw_text(draw: ImageDraw.ImageDraw, text: str, field: TextField, default_font_path: Optional[str]):
    if not text:
        return

    font_px = field.font_px
    font = _try_load_font(font_px, field.font_path, default_font_path)

    if field.max_width is not None:
        while font_px > 12:
            font = _try_load_font(font_px, field.font_path, default_font_path)
            bbox = draw.textbbox((0, 0), text, font=font, anchor="lt")
            w = bbox[2] - bbox[0]
            if w <= field.max_width:
                break
            font_px -= 2

    draw.text(field.pos, text, fill=field.color, font=font, anchor=field.anchor)

def compose_with_template(
    template: TemplateSpec,
    capture_paths: List[str],
    texts: Optional[Dict[str, str]] = None,
) -> Image.Image:
    """
    Compose: bg (1844x1240) -> photos in slots -> optional slot_fg centered on slot -> texts.
    Returns RGB image suitable for JPEG printing.
    """
    texts = texts or {}
    text_fields = template.text_fields or {}

    bg = Image.open(template.bg_path).convert("RGBA")
    canvas = bg.copy()

    if len(capture_paths) != len(template.slots):
        raise ValueError(f"Expected {len(template.slots)} captures, got {len(capture_paths)}")

    # 1) paste photos into slots
    for img_path, slot in zip(capture_paths, template.slots):
        l, t, r, b = slot
        w, h = (r - l), (b - t)

        img = Image.open(img_path)
        img = ImageOps.exif_transpose(img).convert("RGBA")  # Nikon orientation fix

        tile = resize_cover(img, w, h)
        canvas.alpha_composite(tile, (l, t))

    # 2) slot overlay (fg), centered within its slot (can be smaller than slot)
    if template.slot_fg_path:
        fg = Image.open(template.slot_fg_path).convert("RGBA")
        slot = template.slots[template.slot_fg_index]
        l, t, r, b = slot
        sw, sh = (r - l), (b - t)

        fw, fh = fg.size
        if fw > sw or fh > sh:
            raise ValueError(
                f"slot_fg larger than slot: fg={fg.size}, slot={(sw, sh)}. "
                f"Make fg <= slot or adjust slot."
            )

        # center in slot
        x = l + (sw - fw) // 2
        y = t + (sh - fh) // 2
        canvas.alpha_composite(fg, (x, y))

    # 3) texts on top
    draw = ImageDraw.Draw(canvas)
    for key, field in text_fields.items():
        _draw_text(draw, texts.get(key, ""), field, template.default_font_path)

    return canvas.convert("RGB")
