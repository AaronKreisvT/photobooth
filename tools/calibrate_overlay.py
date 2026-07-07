#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import time
import traceback
import argparse
from pathlib import Path

from PyQt6.QtCore import Qt, QPoint, QRect, QTimer
from PyQt6.QtGui import QPixmap, QPainter, QPen, QFont, QColor
from PyQt6.QtWidgets import QApplication, QWidget, QLabel

LOG_PATH_DEFAULT = "/tmp/fotobox_calibrate_debug.log"


def log(msg: str, logfile: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}\n"
    try:
        with open(logfile, "a", encoding="utf-8") as f:
            f.write(line)
            f.flush()
            os.fsync(f.fileno())
    except Exception:
        pass
    try:
        print(line, end="", flush=True)
    except Exception:
        pass


def snap_value(v: int, step: int) -> int:
    return int(round(v / step) * step) if step > 1 else v


def snap_point(p: QPoint, step: int) -> QPoint:
    return QPoint(snap_value(p.x(), step), snap_value(p.y(), step))


def clamp_rect_to(r: QRect, W: int, H: int) -> QRect:
    x = max(0, min(r.x(), W))
    y = max(0, min(r.y(), H))
    w = max(0, min(r.width(),  W - x))
    h = max(0, min(r.height(), H - y))
    return QRect(x, y, w, h)


def install_excepthook(logfile: str) -> None:
    def hook(exctype, value, tb):
        log("FATAL: Unhandled exception!", logfile)
        log("".join(traceback.format_exception(exctype, value, tb)), logfile)
        try:
            QApplication.quit()
        except Exception:
            pass
        sys.__excepthook__(exctype, value, tb)
    sys.excepthook = hook


class Overlay(QWidget):
    """
    Läuft stabil in deinem Kiosk-X (wie deine alte Debug-Version),
    plus:
      - POINT: Klick -> px + rel ausgeben
      - RECT: Taste R, 2 Klicks -> Rect ausgeben
      - Snap/Grid toggles
      - Quit ohne Tastatur: Rechtsklick oder 5s Hold links
    """
    def __init__(self, logfile: str, grid_step=50, show_grid=True, snap=True):
        super().__init__()
        self.logfile = logfile

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)

        self.grid_step = grid_step
        self.show_grid = show_grid
        self.snap = snap

        self.raw_pos = QPoint(0, 0)
        self.target_pos = QPoint(0, 0)
        self.last_click: QPoint | None = None

        # Rect mode
        self.rect_mode = False
        self.rect_start: QPoint | None = None
        self.rect_current: QPoint | None = None
        self.last_rect: QRect | None = None

        # Hold-to-quit
        self._hold_start: float | None = None

        # Heartbeat
        self._heartbeat_count = 0

        self.font = QFont()
        self.font.setPointSize(12)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(1000)

        log("Overlay init OK", self.logfile)

    def _tick(self) -> None:
        self._heartbeat_count += 1

        # Hold-to-quit
        if self._hold_start is not None and (time.time() - self._hold_start) >= 5.0:
            log("HOLD 5s -> quit", self.logfile)
            QApplication.quit()
            return

        self.update()

    def _target(self, p: QPoint) -> QPoint:
        return snap_point(p, self.grid_step) if self.snap else p

    def _print_point(self, p: QPoint) -> None:
        W, H = self.width(), self.height()
        xr = p.x() / W if W else 0.0
        yr = p.y() / H if H else 0.0
        print(f"POINT px=({p.x()},{p.y()}) rel=({xr:.6f},{yr:.6f}) tuple_rel=({xr:.6f}, {yr:.6f})")
        sys.stdout.flush()

    def _print_rect(self, r: QRect) -> None:
        W, H = self.width(), self.height()
        xr = r.x() / W if W else 0.0
        yr = r.y() / H if H else 0.0
        wr = r.width() / W if W else 0.0
        hr = r.height() / H if H else 0.0
        print(
            f"RECT px=(x={r.x()}, y={r.y()}, w={r.width()}, h={r.height()}) "
            f"rel=(x={xr:.6f}, y={yr:.6f}, w={wr:.6f}, h={hr:.6f}) "
            f"tuple_rel=({xr:.6f}, {yr:.6f}, {wr:.6f}, {hr:.6f})"
        )
        sys.stdout.flush()

    def mouseMoveEvent(self, e) -> None:
        raw = e.position().toPoint()
        self.raw_pos = raw
        self.target_pos = self._target(raw)

        if self.rect_mode and self.rect_start is not None:
            self.rect_current = self.target_pos

        self.update()

    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.RightButton:
            log("RIGHT click -> quit", self.logfile)
            QApplication.quit()
            return

        if e.button() != Qt.MouseButton.LeftButton:
            return

        self._hold_start = time.time()
        self.last_click = self.target_pos

        if not self.rect_mode:
            self._print_point(self.target_pos)
            return

        # Rect mode: 2 clicks
        if self.rect_start is None:
            self.rect_start = self.target_pos
            self.rect_current = self.target_pos
        else:
            end = self.target_pos
            x1, y1 = self.rect_start.x(), self.rect_start.y()
            x2, y2 = end.x(), end.y()
            x = min(x1, x2)
            y = min(y1, y2)
            w = abs(x2 - x1)
            h = abs(y2 - y1)
            r = clamp_rect_to(QRect(x, y, w, h), self.width(), self.height())
            self.last_rect = r
            self.rect_start = None
            self.rect_current = None
            self._print_rect(r)

    def mouseReleaseEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            self._hold_start = None

    def keyPressEvent(self, e) -> None:
        k = e.key()
        if k in (Qt.Key.Key_Q, Qt.Key.Key_Escape):
            QApplication.quit()
            return
        if k == Qt.Key.Key_G:
            self.show_grid = not self.show_grid
        elif k == Qt.Key.Key_S:
            self.snap = not self.snap
        elif k in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
            self.grid_step = min(300, self.grid_step + 10)
        elif k == Qt.Key.Key_Minus:
            self.grid_step = max(10, self.grid_step - 10)
        elif k == Qt.Key.Key_R:
            self.rect_mode = not self.rect_mode
            self.rect_start = None
            self.rect_current = None
        self.update()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        W, H = self.width(), self.height()
        mx, my = self.target_pos.x(), self.target_pos.y()

        # Grid
        if self.show_grid and self.grid_step > 5:
            p.setPen(QPen(QColor(255, 255, 255, 40), 1))
            for x in range(0, W + 1, self.grid_step):
                p.drawLine(x, 0, x, H)
            for y in range(0, H + 1, self.grid_step):
                p.drawLine(0, y, W, y)

        # Crosshair
        p.setPen(QPen(QColor(255, 255, 255, 230), 2))
        p.drawLine(mx - 12, my, mx + 12, my)
        p.drawLine(mx, my - 12, mx, my + 12)

        # Rect preview
        if self.rect_mode and self.rect_start is not None and self.rect_current is not None:
            x1, y1 = self.rect_start.x(), self.rect_start.y()
            x2, y2 = self.rect_current.x(), self.rect_current.y()
            x = min(x1, x2)
            y = min(y1, y2)
            w = abs(x2 - x1)
            h = abs(y2 - y1)
            rr = clamp_rect_to(QRect(x, y, w, h), W, H)
            p.setPen(QPen(QColor(0, 255, 160, 180), 3))
            p.setBrush(QColor(0, 255, 160, 40))
            p.drawRect(rr)

        # HUD
        hud = QRect(10, 10, 820, 240)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 170))
        p.drawRoundedRect(hud, 12, 12)

        rx, ry = self.raw_pos.x(), self.raw_pos.y()
        rrx = rx / W if W else 0.0
        rry = ry / H if H else 0.0
        txr = mx / W if W else 0.0
        tyr = my / H if H else 0.0

        p.setPen(QColor(255, 255, 255, 245))
        p.setFont(self.font)

        lines = [
            f"RAW:    {rx:4d},{ry:4d}  rel=({rrx:.4f},{rry:.4f})",
            f"TARGET: {mx:4d},{my:4d}  rel=({txr:.4f},{tyr:.4f})",
            f"Grid: {'ON' if self.show_grid else 'OFF'}  step={self.grid_step}px | Snap: {'ON' if self.snap else 'OFF'}",
            f"RectMode: {'ON' if self.rect_mode else 'OFF'} (R) | Heartbeat: {self._heartbeat_count}",
            "Click: POINT | RectMode: 2 clicks => RECT",
            "Quit: Right click / hold left 5s / Q",
        ]
        p.drawText(hud.adjusted(12, 12, -12, -12), Qt.TextFlag.TextWordWrap, "\n".join(lines))


class CalibrateWindow(QWidget):
    def __init__(self, image_path: Path, logfile: str, grid: int, no_grid: bool, no_snap: bool):
        super().__init__()
        self.logfile = logfile
        log("Window: init start", self.logfile)

        self.setWindowTitle("Fotobox Calibrate")
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.setMouseTracking(True)

        self._pix = QPixmap(str(image_path))
        log(f"Window: QPixmap isNull={self._pix.isNull()} size=({self._pix.width()}x{self._pix.height()})", self.logfile)
        if self._pix.isNull():
            raise RuntimeError(f"QPixmap konnte das Bild nicht laden: {image_path}")

        self.bg = QLabel(self)
        self.bg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.bg.setStyleSheet("background: black;")

        self.overlay = Overlay(logfile=self.logfile, grid_step=grid, show_grid=not no_grid, snap=not no_snap)
        self.overlay.setParent(self)

        # --- EXACT working fullscreen strategy ---
        screen = QApplication.primaryScreen()
        if screen is None:
            geo = QRect(0, 0, 1024, 600)
            log("Window: primaryScreen None -> fallback 1024x600", self.logfile)
        else:
            geo = screen.geometry()
            log(f"Window: primaryScreen geometry = {geo.width()}x{geo.height()} @ {geo.x()},{geo.y()}", self.logfile)

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setGeometry(geo)
        self.show()

        QTimer.singleShot(0, self._apply_background)
        QTimer.singleShot(150, self._apply_background)
        QTimer.singleShot(400, self._apply_background)

        self._hb = QTimer(self)
        self._hb.timeout.connect(lambda: log(f"Window: alive size={self.width()}x{self.height()}", self.logfile))
        self._hb.start(2000)

        log("Window: init end", self.logfile)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        log("Window: showEvent()", self.logfile)
        self._apply_background()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        log(f"Window: resizeEvent {self.width()}x{self.height()}", self.logfile)
        self._apply_background()

    def _apply_background(self) -> None:
        r = self.rect()
        self.bg.setGeometry(r)
        self.overlay.setGeometry(r)

        if r.width() <= 0 or r.height() <= 0:
            log(f"apply_background: invalid {r.width()}x{r.height()}", self.logfile)
            return

        scaled = self._pix.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.bg.setPixmap(scaled)
        self.bg.lower()
        self.overlay.raise_()
        self.overlay.setFocus()
        log(f"apply_background: ok window={self.width()}x{self.height()} scaled={scaled.width()}x{scaled.height()}", self.logfile)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("image", help="PNG (z.B. assets/final.png)")
    ap.add_argument("--grid", type=int, default=50)
    ap.add_argument("--no-grid", action="store_true")
    ap.add_argument("--no-snap", action="store_true")
    ap.add_argument("--log", default=LOG_PATH_DEFAULT)
    args = ap.parse_args()

    os.environ["PYTHONUNBUFFERED"] = "1"

    img = Path(args.image).expanduser().resolve()
    logfile = str(Path(args.log).expanduser().resolve())
    Path(logfile).parent.mkdir(parents=True, exist_ok=True)
    Path(logfile).write_text("", encoding="utf-8")

    install_excepthook(logfile)

    log(f"START python={sys.executable}", logfile)
    log(f"START cwd={os.getcwd()}", logfile)
    log(f"START DISPLAY={os.environ.get('DISPLAY')}", logfile)
    log(f"START image={img}", logfile)

    if not img.exists():
        raise SystemExit(f"Datei nicht gefunden: {img}")

    app = QApplication(sys.argv)
    log("QApplication constructed", logfile)

    _w = CalibrateWindow(img, logfile, args.grid, args.no_grid, args.no_snap)
    log("Window constructed", logfile)

    rc = app.exec()
    log(f"EXIT app.exec() -> {rc}", logfile)
    sys.exit(rc)


if __name__ == "__main__":
    main()
