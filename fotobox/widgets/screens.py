import os
import time
from typing import Optional

from PyQt6.QtCore import Qt, QTimer, QRect
from PyQt6.QtGui import QPixmap, QPainter, QFont, QImage
from PyQt6.QtWidgets import QWidget, QLabel

from .screen_base import ScreenBase, Zone
from ..geometry import rel_to_abs
from ..config import Zones
from .video_player import make_video_widget

class MainScreen(ScreenBase):
    def __init__(self, zones: Zones, fixed_w: int, fixed_h: int, assets_root: str, parent=None):
        self._zones_cfg = zones
        self._assets_root = assets_root
        self._last_image_path: Optional[str] = None
        super().__init__(
            bg_path=os.path.join(assets_root, "assets/main.png"),
            zones=[],
            fixed_w=fixed_w,
            fixed_h=fixed_h,
            parent=parent,
        )

    def bind(self, on_take_n, on_open_last):
        self._zones = [
            Zone("MAIN: take 1", self._zones_cfg.main_take_1, on_click=lambda: on_take_n(1)),
            Zone("MAIN: take 2", self._zones_cfg.main_take_2, on_click=lambda: on_take_n(2)),
            Zone("MAIN: take 4", self._zones_cfg.main_take_4, on_click=lambda: on_take_n(4)),
            Zone("MAIN: last frame", self._zones_cfg.main_last_image_frame, on_click=on_open_last, is_frame=True),
        ]

    def set_last_image(self, path: Optional[str]):
        self._last_image_path = path
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)

        # last image thumbnail in frame (wenn vorhanden)
        if self._last_image_path and os.path.exists(self._last_image_path):
            p = QPainter(self)
            x, y, w, h = rel_to_abs(self._zones_cfg.main_last_image_frame, self.width(), self.height())
            pm = QPixmap(self._last_image_path)
            if not pm.isNull():
                scaled = pm.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                px = x + (w - scaled.width()) // 2
                py = y + (h - scaled.height()) // 2
                p.drawPixmap(px, py, scaled)

class PreviewScreen(ScreenBase):
    def __init__(self, zones: Zones, fixed_w: int, fixed_h: int, assets_root: str, parent=None):
        self._zones_cfg = zones
        self._assets_root = assets_root
        self._countdown = 3
        self._tick = 0
        self._on_done = None  # callback
        self._qimg = None

        # WICHTIG: QWidget/ScreenBase zuerst initialisieren!
        super().__init__(
            bg_path=os.path.join(assets_root, "assets/preview.png"),
            zones=[
                Zone("PREVIEW: feed frame", zones.preview_feed_frame, on_click=None, is_frame=True),
            ],
            fixed_w=fixed_w,
            fixed_h=fixed_h,
            parent=parent,
        )

        # Danach dürfen QObjects mit parent=self erstellt werden
        self._countdown_timer = QTimer(self)
        self._countdown_timer.setInterval(1000)
        self._countdown_timer.timeout.connect(self._on_countdown_tick)

    def start(self, seconds: int = 3):
        self._countdown = seconds
        self._tick = 0
        self._countdown_timer.start()
        self.update()

    def stop(self):
        self._countdown_timer.stop()

    def set_on_done(self, cb):
        self._on_done = cb

    def _on_countdown_tick(self):
        self._countdown -= 1
        if self._countdown <= 0:
            self.stop()
            if self._on_done:
                self._on_done()
        self.update()

    def set_preview_jpeg(self, jpg_bytes: bytes):
      qimg = QImage.fromData(jpg_bytes, "JPG")
      if not qimg.isNull():
        self._qimg = qimg
        self.update()

    def paintEvent(self, event):
      super().paintEvent(event)

      p = QPainter(self)

      x, y, w, h = rel_to_abs(
        self._zones_cfg.preview_feed_frame,
        self.width(),
        self.height()
      )

      # ---- LIVE PREVIEW ----
      if self._qimg is not None:
        pix = QPixmap.fromImage(self._qimg)
        scaled = pix.scaled(
            w, h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        sx = x + (w - scaled.width()) // 2
        sy = y + (h - scaled.height()) // 2
        p.drawPixmap(sx, sy, scaled)
      else:
        # Fallback falls noch kein Frame da ist
        p.setPen(Qt.GlobalColor.white)
        p.drawRect(QRect(x, y, w, h))
        p.drawText(x + 20, y + 40, "LIVE...")

      # ---- COUNTDOWN ----
      if self._countdown > 0:
        p.setFont(QFont("DejaVu Sans", 96))
        p.setPen(Qt.GlobalColor.white)
        p.drawText(QRect(x, y, w, h),
                   Qt.AlignmentFlag.AlignCenter,
                   str(self._countdown))

      p.end()

class ProcessingScreen(ScreenBase):
    def __init__(self, fixed_w: int, fixed_h: int, assets_root: str, parent=None):
        super().__init__(
            bg_path=os.path.join(assets_root, "assets/processing.png"),
            zones=[],
            fixed_w=fixed_w,
            fixed_h=fixed_h,
            parent=parent,
        )

class FinalScreen(ScreenBase):
    def __init__(self, zones: Zones, fixed_w: int, fixed_h: int, assets_root: str, parent=None):
        self._zones_cfg = zones
        self._final_image_path: Optional[str] = None

        super().__init__(
            bg_path=os.path.join(assets_root, "assets/final.png"),
            zones=[],
            fixed_w=fixed_w,
            fixed_h=fixed_h,
            parent=parent,
        )

    def bind(self, on_print_copies):
        self._zones = [
            Zone("FINAL: image frame", self._zones_cfg.final_image_frame, on_click=None, is_frame=True),
            Zone("FINAL: print 0", self._zones_cfg.final_print_0, on_click=lambda: on_print_copies(0)),
            Zone("FINAL: print 1", self._zones_cfg.final_print_1, on_click=lambda: on_print_copies(1)),
            Zone("FINAL: print 2", self._zones_cfg.final_print_2, on_click=lambda: on_print_copies(2)),
            Zone("FINAL: print 3", self._zones_cfg.final_print_3, on_click=lambda: on_print_copies(3)),
        ]

    def set_final_image(self, path: Optional[str]):
        self._final_image_path = path
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._final_image_path and os.path.exists(self._final_image_path):
            p = QPainter(self)
            x, y, w, h = rel_to_abs(self._zones_cfg.final_image_frame, self.width(), self.height())
            pm = QPixmap(self._final_image_path)
            if not pm.isNull():
                scaled = pm.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                px = x + (w - scaled.width()) // 2
                py = y + (h - scaled.height()) // 2
                p.drawPixmap(px, py, scaled)

class EndScreen(ScreenBase):
    def __init__(self, fixed_w: int, fixed_h: int, assets_root: str, parent=None):
        super().__init__(
            bg_path=os.path.join(assets_root, "assets/end.png"),
            zones=[],
            fixed_w=fixed_w,
            fixed_h=fixed_h,
            parent=parent,
        )

class ScreensaverScreen(QWidget):
    def __init__(self, video_path: str, fixed_w: int, fixed_h: int, parent=None):
        super().__init__(parent)
        self.setFixedSize(fixed_w, fixed_h)
        w = make_video_widget(video_path)
        w.setParent(self)
        w.setGeometry(0, 0, fixed_w, fixed_h)
        self._inner = w
