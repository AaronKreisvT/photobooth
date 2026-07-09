import os
import time
from dataclasses import dataclass
from typing import Optional, List

from datetime import datetime

from PyQt6.QtCore import Qt, QTimer, QObject, QEvent
from PyQt6.QtGui import QPixmap, QImage, QPainter, QFont, QCursor
from PyQt6.QtWidgets import QApplication, QStackedWidget, QWidget

from .config import (
    default_zones, WINDOW_W, WINDOW_H,
    GLOBAL_FONT_PATH,
)

from .templates import load_template_variant, background_path

from .processing.template_compositor import (
    TemplateSpec, TextField, rect_norm, compose_with_template,
)
from .state import AppState
from .idle import IdleWatcher
from .widgets.screens import MainScreen, PreviewScreen, ProcessingScreen, FinalScreen, EndScreen, ScreensaverScreen

from .naming import unique_filename
from .camera.gphoto_stream import GPhotoStream
from .printer.cups_printer import submit_print_job, record_print

from .settings_store import Settings, load_settings, save_settings, scan_templates
from .widgets.settings_dialog import SettingsDialog

@dataclass
class Session:
    requested_photos: int = 1
    captured_paths: List[str] = None
    final_path: Optional[str] = None
    print_copies: int = 0


class GlobalInputFilter(QObject):
    """Reset Idle on any input; also exit screensaver on any input.
    Returns True to consume the event if we were in screensaver (prevents click-through).
    """
    def __init__(self, on_any_input):
        super().__init__()
        self._cb = on_any_input

    def eventFilter(self, obj, event):
        et = event.type()
        if et in (
            QEvent.Type.MouseButtonPress,
            QEvent.Type.MouseMove,
            QEvent.Type.KeyPress,
            QEvent.Type.TouchBegin,
            QEvent.Type.TouchUpdate,
            QEvent.Type.TouchEnd,
        ):
            # cb returns True if event should be consumed
            consume = self._cb(event)
            if consume:
                return True
        return super().eventFilter(obj, event)


class FotoboxApp(QStackedWidget):
    def __init__(self, root_dir: str):
        super().__init__()
        self.setFixedSize(WINDOW_W, WINDOW_H)

        self.root_dir = root_dir
        self.assets_root = root_dir
        self.photos_dir = os.path.join(root_dir, "photos")
        self.photos_tmp_dir = os.path.join(root_dir, "photos-tmp")
        os.makedirs(self.photos_dir, exist_ok=True)
        os.makedirs(self.photos_tmp_dir, exist_ok=True)

        self.z = default_zones()

        defaults = Settings(
          IDLE_SECONDS_TO_SCREENSAVER=180,
          FINAL_IDLE_TIMEOUT_SECONDS=45,
          PREVIEW_COUNTDOWN_SECONDS=5,
          DEFAULT_TEXT_LINE1="",
          DEFAULT_TEXT_LINE2="",
          TEMPLATE_NAME="partyballoons",
        )
        self.settings = load_settings(self.root_dir, defaults)
        self.template_names = scan_templates(self.root_dir)

        if self.template_names and self.settings.TEMPLATE_NAME not in self.template_names:
          self.settings.TEMPLATE_NAME = self.template_names[0]

        # Screens
        self.screen_main = MainScreen(self.z, WINDOW_W, WINDOW_H, self.assets_root)
        self.screen_preview = PreviewScreen(self.z, WINDOW_W, WINDOW_H, self.assets_root)
        self.screen_processing = ProcessingScreen(WINDOW_W, WINDOW_H, self.assets_root)
        self.screen_final = FinalScreen(self.z, WINDOW_W, WINDOW_H, self.assets_root)
        self.screen_end = EndScreen(WINDOW_W, WINDOW_H, self.assets_root)

        self.cam = GPhotoStream(self)

        # Preview frames in den PreviewScreen
        self.cam.preview_frame.connect(self.screen_preview.set_preview_jpeg)
        self.cam.preview_error.connect(lambda m: print("[PREVIEW]", m))

        # Capture callbacks
        self.cam.capture_done.connect(self._on_capture_done)
        self.cam.capture_error.connect(self._on_capture_error)

        # wenn du schon countdown->done callback hast:
        self.screen_preview.set_on_done(self._take_picture_now)

        idle_video = os.path.join(self.assets_root, "assets/idle.mp4")
        self.screen_screensaver = ScreensaverScreen(idle_video, WINDOW_W, WINDOW_H)

        # Stack order
        self.addWidget(self.screen_main)        # idx 0
        self.addWidget(self.screen_preview)     # idx 1
        self.addWidget(self.screen_processing)  # idx 2
        self.addWidget(self.screen_final)       # idx 3
        self.addWidget(self.screen_end)         # idx 4
        self.addWidget(self.screen_screensaver) # idx 5

        self.state = AppState.MAIN
        self.debug_overlay = False

        # Session
        self.session = Session(requested_photos=1, captured_paths=[], final_path=None, print_copies=0)
        self.last_image_path: Optional[str] = None

        # Bind actions
        self.screen_main.bind(self._start_capture_flow, self._open_last_from_main)
        self.screen_final.bind(self._on_print_choice)

        # Idle watcher (nur relevant in MAIN)
        self.idle = IdleWatcher(self.settings.IDLE_SECONDS_TO_SCREENSAVER, self)
        self.idle.idle_timeout.connect(self._enter_screensaver)
        self.idle.start()

        self._apply_debug_overlay()

        # Final idle timeout
        self._final_idle_timer = QTimer(self)
        self._final_idle_timer.setSingleShot(True)
        self._final_idle_timer.timeout.connect(self._on_final_idle_timeout)

        # End "printing" timer stub
        self._end_timer = QTimer(self)
        self._end_timer.setSingleShot(True)
        self._end_timer.timeout.connect(self._back_to_main)

        # Timeout while waiting between multiple captures
        self._between_shots_timer = QTimer(self)
        self._between_shots_timer.setSingleShot(True)
        self._between_shots_timer.timeout.connect(self._abort_capture_session)

        # Show main
        self._go(AppState.MAIN)

    def _take_picture_now(self):
      self.cam.stop_preview()
      self.screen_preview.stop()  # stop countdown timers etc.
      self._go(AppState.PROCESSING)

      ts = time.strftime("%Y%m%d-%H%M%S")
      self._current_capture_path = os.path.join(self.photos_tmp_dir, f"capture_{ts}.jpg")
      self._capture_retry_count = 0

      # Small delay to let PTP settle after stopping movie stream
      QTimer.singleShot(300, lambda: self.cam.capture_image(self._current_capture_path, keep_on_camera=True))

    def _on_capture_done(self, path: str):
      self.session.captured_paths.append(path)

      # noch mehr Bilder erforderlich?
      if len(self.session.captured_paths) < self.session.requested_photos:
        self._go(AppState.PREVIEW)
        # Countdown erneut starten (wie auch immer deine PreviewScreen API ist)
        self.screen_preview.wait_for_next(self._continue_after_between_shots)
        self._between_shots_timer.start(120_000)
        return
      # alle Bilder da -> weiterverarbeiten
      self._finish_processing()

    def _continue_after_between_shots(self):
      self._between_shots_timer.stop()

      if self.state != AppState.PREVIEW:
        return

      self.screen_preview.start(seconds=self.settings.PREVIEW_COUNTDOWN_SECONDS)


    def _abort_capture_session(self):
      print("[CAPTURE] Session aborted: no input between shots.")

      self.screen_preview.stop()

      for p in self.session.captured_paths:
        try:
          if p and os.path.exists(p):
            os.remove(p)
        except Exception as e:
          print(f"[CAPTURE] Could not delete temp capture {p}: {e}")

      self.session = Session(
        requested_photos=1,
        captured_paths=[],
        final_path=None,
        print_copies=0,
      )

      self._back_to_main()

    def _on_capture_error(self, msg: str):
      print("[CAPTURE] Capture failed:\n", msg)

      # Retry once if device busy / I/O in progress
      busy = ("PTP Device Busy" in msg) or ("I/O in progress" in msg) or ("-110" in msg) or ("exit=9" in msg)

      if busy and getattr(self, "_capture_retry_count", 0) < 1:
        self._capture_retry_count += 1
        # ensure preview stays stopped
        self.cam.stop_preview()
        # retry after short wait
        QTimer.singleShot(800, lambda: self.cam.capture_image(self._current_capture_path, keep_on_camera=True))
        return

      # If you're remote-testing with lens cap: optionally fallback to a dummy file (see below),
      # otherwise abort session cleanly:
      self._back_to_main()

    # ---------- state switching ----------
    def _go(self, s: AppState):
      # If we are leaving PREVIEW, stop its timers (countdown, etc.)
      if getattr(self, "state", None) == AppState.PREVIEW and s != AppState.PREVIEW:
        self.screen_preview.stop()

      # Stop/start camera preview depending on target state
      if s != AppState.PREVIEW:
        if hasattr(self, "cam") and self.cam is not None:
            self.cam.stop_preview()

      self.state = s

      if s == AppState.MAIN:
        self.setCurrentWidget(self.screen_main)
        self.idle.reset()
        self._final_idle_timer.stop()

      elif s == AppState.PREVIEW:
        self.setCurrentWidget(self.screen_preview)
        self.cam.start_preview()

      elif s == AppState.PROCESSING:
        self.setCurrentWidget(self.screen_processing)

      elif s == AppState.FINAL:
        self.setCurrentWidget(self.screen_final)
        self._final_idle_timer.start(self.settings.FINAL_IDLE_TIMEOUT_SECONDS * 1000)

      elif s == AppState.END:
        self.setCurrentWidget(self.screen_end)

      elif s == AppState.SCREENSAVER:
        self.setCurrentWidget(self.screen_screensaver)

      self._apply_debug_overlay()

    def _apply_debug_overlay(self):
        for w in [self.screen_main, self.screen_preview, self.screen_processing, self.screen_final, self.screen_end]:
            w.set_debug(self.debug_overlay)

    # ---------- debug toggle ----------
    def toggle_debug(self):
        self.debug_overlay = not self.debug_overlay
        self._apply_debug_overlay()

    def _apply_settings(self):
      self.idle.set_seconds(self.settings.IDLE_SECONDS_TO_SCREENSAVER)
      if self.state == AppState.FINAL:
        self._final_idle_timer.start(self.settings.FINAL_IDLE_TIMEOUT_SECONDS * 1000)

    def _open_settings(self):
      self.template_names = scan_templates(self.root_dir)
      dlg = SettingsDialog(root_dir=self.root_dir, parent=self, settings=self.settings, template_names=self.template_names)
      if dlg.exec() == dlg.DialogCode.Accepted:
        self.settings = dlg.get_settings()
        save_settings(self.root_dir, self.settings)
        self._apply_settings()

    # ---------- global input handler ----------
    def on_any_input(self, event=None) -> bool:
      # Exit screensaver on any input, but CONSUME that first event
      if self.state == AppState.SCREENSAVER:
        self._go(AppState.MAIN)
        self.idle.reset()
        return True  # <- verhindert click-through auf MAIN

      # Reset final idle timer on any interaction in FINAL
      if self.state == AppState.FINAL:
        self._final_idle_timer.start(self.settings.FINAL_IDLE_TIMEOUT_SECONDS * 1000)

      # Normal: reset idle if we're in MAIN
      if self.state == AppState.MAIN:
        self.idle.reset()

      return False

    # ---------- main flow ----------
    def _start_capture_flow(self, n: int):
        self._between_shots_timer.stop()
        self.session = Session(requested_photos=n, captured_paths=[], final_path=None, print_copies=0)
        self._begin_next_preview()

    def _open_last_from_main(self):
        # Für später: könnte "final" öffnen oder galerie.
        # Aktuell: wenn last existiert -> direkt final mit last anzeigen.
        if self.last_image_path and os.path.exists(self.last_image_path):
            self.session.final_path = self.last_image_path
            self.screen_final.set_final_image(self.session.final_path)
            self._go(AppState.FINAL)

    def _begin_next_preview(self):
        self._go(AppState.PREVIEW)
        self.screen_preview.start(seconds=self.settings.PREVIEW_COUNTDOWN_SECONDS)

    def _finish_processing(self):
      n = len(self.session.captured_paths)
      if n not in (1, 2, 4):
        raise ValueError(f"Unsupported capture count: {n}")

      template_name = self.settings.TEMPLATE_NAME
      variant = load_template_variant(self.root_dir, template_name, n)

      bg_path = background_path(self.root_dir, template_name, n)

      # ---- slots: JSON -> Rect (left, top, right, bottom)
      slots = variant["slots_px"]
      slots_rects = [rect_norm(tuple(a), tuple(b)) for a, b in slots]

      # ---- text fields: JSON -> TextField dataclass
      raw_tfs = variant.get("text_fields_px", {})
      text_fields = {
        name: TextField(
            pos=tuple(tf["pos"]),
            font_px=int(tf.get("font_px", 42)),
            anchor=tf.get("anchor", "lt"),
            max_width=tf.get("max_width", None),
            color=tuple(tf.get("color", (0, 0, 0))),
            font_path=tf.get("font_path", None),
        )
        for name, tf in raw_tfs.items()
      }

      spec = TemplateSpec(
        bg_path=bg_path,
        slots=slots_rects,              # <-- wichtig: slots, nicht slots_px
        slot_fg_path=None,
        slot_fg_index=0,                # <-- int, nicht None
        text_fields=text_fields,        # <-- Dict[str, TextField]
        default_font_path=GLOBAL_FONT_PATH,
      )

      final_img = compose_with_template(
        spec,
        self.session.captured_paths,
        texts={
            "line1": self.settings.DEFAULT_TEXT_LINE1,
            "line2": self.settings.DEFAULT_TEXT_LINE2,
        },
      )

      final_path = unique_filename(self.photos_dir, "jpg")
      final_img.save(final_path, "JPEG", quality=95, subsampling=0, dpi=(300, 300))

      # cleanup tmp captures
      for p in self.session.captured_paths:
        try:
            if p and os.path.exists(p):
                os.remove(p)
        except Exception:
            pass

      self.session.final_path = final_path
      self.screen_final.set_final_image(final_path)
      self.last_image_path = final_path
      self.screen_main.set_last_image(self.last_image_path)

      self._go(AppState.FINAL)

    def _on_print_choice(self, copies: int):
      self.session.print_copies = copies

      # 0 copies -> directly back
      if copies <= 0:
        self._back_to_main()
        return

      # show END while submitting job (not while physically printing)
      self._go(AppState.END)

      # submit to CUPS queue
      img = self.session.final_path
      result = submit_print_job(img, copies=copies)

      if result.ok:
        # record locally
        record_print(self.root_dir, copies=copies, job_id=result.job_id, image_path=img)
        # return to main after max 10s (we don't need to block)
        QTimer.singleShot(10_000, self._back_to_main)
      else:
        print("[PRINT ERROR]", result.error)
        # fallback: don't get stuck
        QTimer.singleShot(1500, self._back_to_main)

    def _back_to_main(self):
        self._between_shots_timer.stop()
        self._go(AppState.MAIN)

    # ---------- screensaver ----------
    def _enter_screensaver(self):
        # nur wenn wir wirklich in MAIN sind
        if self.state == AppState.MAIN:
            self._go(AppState.SCREENSAVER)

    def _on_final_idle_timeout(self):
        # Sicherheitsrücksprung, falls jemand weggeht
        if self.state == AppState.FINAL:
            self._back_to_main()

    # ---------- stubs ----------
    def _stub_capture_image(self) -> str:
        ts = time.strftime("%Y%m%d-%H%M%S")
        out = os.path.join(self.photos_tmp_dir, f"capture_{ts}.png")

        img = QImage(800, 480, QImage.Format.Format_RGB32)
        img.fill(0x202020)

        p = QPainter(img)
        p.setPen(Qt.GlobalColor.white)
        p.setFont(QFont("DejaVu Sans", 32))
        p.drawText(img.rect(), Qt.AlignmentFlag.AlignCenter, f"CAPTURE\n{ts}")
        p.end()

        img.save(out)
        return out

    def _stub_make_final(self, captured_paths: List[str]) -> str:
        ts = time.strftime("%Y%m%d-%H%M%S")
        out = os.path.join(self.photos_dir, f"final_{ts}.png")

        # simple: use last capture (copy) + watermark text
        if captured_paths:
            pm = QPixmap(captured_paths[-1])
        else:
            pm = QPixmap(800, 480)

        img = pm.toImage()
        p = QPainter(img)
        p.setPen(Qt.GlobalColor.white)
        p.setFont(QFont("DejaVu Sans", 18))
        p.drawText(20, 30, f"FINAL (stub)  shots={len(captured_paths)}")
        p.end()
        img.save(out)
        return out


def run():
    app = QApplication([])

    # Cursor verstecken
    app.setOverrideCursor(QCursor(Qt.CursorShape.BlankCursor))

    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    w = FotoboxApp(root_dir)

    # Fullscreen kiosk style:
    w.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
    w.showFullScreen()

    # global input filter
    def any_input(event):
      return w.on_any_input(event)

    f = GlobalInputFilter(any_input)
    app.installEventFilter(f)
    w._global_filter = f

    class KeyFilter(QObject):
      def __init__(self, w: FotoboxApp):
        super().__init__()
        self.w = w

      def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_F1:
                self.w.toggle_debug()
                return True
            if event.key() == Qt.Key.Key_F2:
                self.w._open_settings()
                return True
            if event.key() == Qt.Key.Key_F5:
                self.w._start_capture_flow(1)
                return True
            if event.key() == Qt.Key.Key_F6:
                self.w._start_capture_flow(2)
                return True
            if event.key() == Qt.Key.Key_F7:
                self.w._start_capture_flow(4)
                return True
        return False

    key_filter = KeyFilter(w)
    app.installEventFilter(key_filter)
    w._key_filter = key_filter

    app.exec()
