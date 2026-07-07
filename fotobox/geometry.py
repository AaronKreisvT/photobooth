from dataclasses import dataclass

BASE_W = 1024
BASE_H = 600

@dataclass(frozen=True)
class RectRel:
    """Rechteck in relativen Koordinaten [0..1]."""
    x: float
    y: float
    w: float
    h: float

def _norm_rect(x1: int, y1: int, x2: int, y2: int):
    left = min(x1, x2)
    right = max(x1, x2)
    top = min(y1, y2)
    bottom = max(y1, y2)
    return left, top, right - left, bottom - top

def abs_to_rel(x1: int, y1: int, x2: int, y2: int) -> RectRel:
    x, y, w, h = _norm_rect(x1, y1, x2, y2)
    return RectRel(x / BASE_W, y / BASE_H, w / BASE_W, h / BASE_H)

def rel_to_abs(r: RectRel, w: int, h: int):
    x = int(round(r.x * w))
    y = int(round(r.y * h))
    rw = int(round(r.w * w))
    rh = int(round(r.h * h))
    return x, y, rw, rh
