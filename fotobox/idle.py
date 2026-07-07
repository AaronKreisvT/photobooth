from PyQt6.QtCore import QObject, QTimer, pyqtSignal

class IdleWatcher(QObject):
    idle_timeout = pyqtSignal()

    def __init__(self, seconds: int, parent=None):
        super().__init__(parent)
        self._seconds = seconds
        self._timer = QTimer(self)
        self._timer.setInterval(seconds * 1000)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.idle_timeout.emit)

    def start(self):
        self._timer.start()

    def reset(self):
        self._timer.start()

    def stop(self):
        self._timer.stop()

    def set_seconds(self, seconds: int):
      self._seconds = int(seconds)
      self._timer.setInterval(self._seconds * 1000)
      if self._timer.isActive():
        self._timer.start()

