from dataclasses import dataclass
from typing import Callable, Optional, List

from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QPainter, QPixmap, QPen, QFont
from PyQt6.QtWidgets import QWidget

from ..geometry import RectRel, rel_to_abs

@dataclass
class Zone:
    name: str
    rect_rel: RectRel
    on_click: Optional[Callable[[], None]] = None
    is_frame: bool = False  # nur anzeigen, nicht klickbar

class ScreenBase(QWidget):
    def __init__(self, bg_path: str, zones: List[Zone], fixed_w: int, fixed_h: int, parent=None):
        super().__init__(parent)
        self.setFixedSize(fixed_w, fixed_h)
        self._bg_path = bg_path
        self._bg = QPixmap(bg_path)
        self._zones = zones
        self._debug = False

        self.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def set_debug(self, enabled: bool):
        self._debug = enabled
        self.update()

    def is_debug(self) -> bool:
        return self._debug

    def paintEvent(self, event):
        p = QPainter(self)
        p.drawPixmap(0, 0, self._bg)

        if self._debug:
            pen = QPen(Qt.GlobalColor.green)
            pen.setWidth(2)
            p.setPen(pen)
            p.setFont(QFont("DejaVu Sans", 10))

            for z in self._zones:
                x, y, w, h = rel_to_abs(z.rect_rel, self.width(), self.height())
                p.drawRect(QRect(x, y, w, h))
                p.drawText(x + 4, y + 14, z.name)

    def _hit_zone(self, x: int, y: int) -> Optional[Zone]:
        px = int(x)
        py = int(y)
        for z in self._zones:
            if z.is_frame:
                continue
            rx, ry, rw, rh = rel_to_abs(z.rect_rel, self.width(), self.height())
            if QRect(rx, ry, rw, rh).contains(px, py):
                return z
        return None

    def mousePressEvent(self, event):
        if event.button() in (Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton):
            # PyQt6: position() -> QPointF
            px = int(event.position().x())
            py = int(event.position().y())
            z = self._hit_zone(px, py)
            if z and z.on_click:
                z.on_click()
                return
        super().mousePressEvent(event)
