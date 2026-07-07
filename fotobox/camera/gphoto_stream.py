from __future__ import annotations

import os
from typing import Optional

from PyQt6.QtCore import QObject, QProcess, QByteArray, pyqtSignal, QTimer


class GPhotoStream(QObject):
    """
    Preview via one persistent MJPEG stream:
      gphoto2 --capture-movie --stdout
    Capture via:
      gphoto2 --capture-image-and-download --filename <path> --keep
    """

    preview_frame = pyqtSignal(bytes)   # JPEG bytes
    preview_error = pyqtSignal(str)

    capture_done = pyqtSignal(str)      # filepath
    capture_error = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._stream_proc: Optional[QProcess] = None
        self._buf = bytearray()
        self._streaming = False
        self._stopping = False
        self._capture_proc: Optional[QProcess] = None

    # ---------- PREVIEW STREAM ----------
    def start_preview(self):
      if self._streaming:
        return

      self._stopping = False
      self._streaming = True
      self._buf.clear()

      proc = QProcess(self)
      self._stream_proc = proc

      proc.setProgram("gphoto2")
      proc.setArguments(["--quiet", "--capture-movie", "--stdout"])
      proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)

      proc.readyReadStandardOutput.connect(self._on_stream_data)

      def finished(exit_code, exit_status):
        self._streaming = False
        self._buf.clear()

        if self._stopping:
            proc.deleteLater()
            if self._stream_proc is proc:
                self._stream_proc = None
            return

        if exit_code != 0:
            self.preview_error.emit(f"Preview stream stopped (exit={exit_code})")

        proc.deleteLater()
        if self._stream_proc is proc:
            self._stream_proc = None

      proc.finished.connect(finished)
      proc.start()

    def stop_preview(self):
      self._stopping = True
      self._streaming = False
      self._buf.clear()
      if self._stream_proc and self._stream_proc.state() != QProcess.ProcessState.NotRunning:
        self._stream_proc.kill()
      self._stream_proc = None

    def _on_stream_data(self):
        proc = self._stream_proc
        if not proc:
            return

        chunk: QByteArray = proc.readAllStandardOutput()
        if not chunk:
            return
        self._buf.extend(bytes(chunk))

        # Extract MJPEG frames by JPEG SOI/EOI markers
        while True:
            soi = self._buf.find(b"\xff\xd8")
            if soi < 0:
                # keep buffer from growing forever
                if len(self._buf) > 2_000_000:
                    del self._buf[:-1024]
                return

            eoi = self._buf.find(b"\xff\xd9", soi + 2)
            if eoi < 0:
                # not complete yet; discard leading junk
                if soi > 0:
                    del self._buf[:soi]
                return

            frame = bytes(self._buf[soi:eoi + 2])
            del self._buf[:eoi + 2]
            self.preview_frame.emit(frame)

    # ---------- CAPTURE ----------
    def capture_image(self, out_path: str, keep_on_camera: bool = True):
      os.makedirs(os.path.dirname(out_path), exist_ok=True)

      if self._capture_proc and self._capture_proc.state() != QProcess.ProcessState.NotRunning:
        self.capture_error.emit("Capture already running")
        return

      proc = QProcess(self)
      self._capture_proc = proc

      args = ["--capture-image-and-download", "--filename", out_path]
      args.append("--keep" if keep_on_camera else "--no-keep")

      proc.setProgram("gphoto2")
      proc.setArguments(args)
      proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)

      # Timeout that cannot crash: timer is parented to proc -> dies with proc
      timeout_timer = QTimer(proc)
      timeout_timer.setSingleShot(True)

      def on_timeout():
        if proc.state() != QProcess.ProcessState.NotRunning:
            print("[CAPTURE] Timeout -> killing gphoto2")
            proc.kill()

      timeout_timer.timeout.connect(on_timeout)

      def finished(exit_code, exit_status):
        try:
            timeout_timer.stop()

            out = bytes(proc.readAllStandardOutput())
            msg = out.decode("utf-8", errors="replace")

            ok_file = os.path.exists(out_path) and os.path.getsize(out_path) > 0
            has_error_text = ("ERROR:" in msg) or ("*** Error ***" in msg) or ("Out of Focus" in msg)

            # Some cameras return exit_code=0 even on error -> trust file+text
            if ok_file and not has_error_text:
                self.capture_done.emit(out_path)
            else:
                # Clean up partial file if any
                if ok_file:
                    try:
                        os.remove(out_path)
                    except Exception:
                        pass
                self.capture_error.emit(msg.strip() or f"Capture failed (exit={exit_code})")
        finally:
            proc.deleteLater()
            if self._capture_proc is proc:
                self._capture_proc = None

      proc.finished.connect(finished)
      proc.start()
      timeout_timer.start(12000)

