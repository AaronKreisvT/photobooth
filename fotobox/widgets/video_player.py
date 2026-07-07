from PyQt6.QtCore import QUrl
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout

def make_video_widget(video_path: str) -> QWidget:
    try:
        from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
        from PyQt6.QtMultimediaWidgets import QVideoWidget

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        vw = QVideoWidget()
        layout.addWidget(vw)

        player = QMediaPlayer(container)
        audio = QAudioOutput(container)
        audio.setVolume(0.0)
        player.setAudioOutput(audio)
        player.setVideoOutput(vw)
        player.setSource(QUrl.fromLocalFile(video_path))

        # ✅ Loop ohne Neustart-Flackern
        if hasattr(player, "setLoops"):
            try:
                player.setLoops(QMediaPlayer.Loops.Infinite)  # PyQt6/Qt6
            except Exception:
                player.setLoops(-1)  # fallback: -1 = infinite (bei manchen Builds)

        player.play()

        container._player = player  # keep ref
        return container

    except Exception:
        fallback = QLabel("Screensaver (Video nicht verfügbar)")
        fallback.setStyleSheet("color: white; background: black; font-size: 28px;")
        fallback.setAlignment(fallback.alignment() | fallback.alignment().AlignCenter)
        return fallback
