# fotobox/widgets/settings_dialog.py
from __future__ import annotations
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QSpinBox, QLineEdit, QComboBox,
    QDialogButtonBox, QLabel
)
from PyQt6.QtCore import Qt
from ..settings_store import Settings

class SettingsDialog(QDialog):
    def __init__(self, root_dir, parent=None, settings=None, template_names=None):
        super().__init__(parent)
        self.setWindowTitle("Fotobox Einstellungen")
        self.setModal(True)

        self.root_dir = root_dir

        self._settings = settings or Setting()
        self._template_names = template_names or []

        v = QVBoxLayout(self)
        info = QLabel("Änderungen werden gespeichert und sofort übernommen.")
        info.setWordWrap(True)
        v.addWidget(info)

        form = QFormLayout()
        v.addLayout(form)

        self.sb_idle = QSpinBox()
        self.sb_idle.setRange(10, 36000)
        self.sb_idle.setValue(settings.IDLE_SECONDS_TO_SCREENSAVER)
        form.addRow("Idle → Screensaver (s)", self.sb_idle)

        self.sb_final = QSpinBox()
        self.sb_final.setRange(5, 3600)
        self.sb_final.setValue(settings.FINAL_IDLE_TIMEOUT_SECONDS)
        form.addRow("Final Timeout (s)", self.sb_final)

        self.sb_countdown = QSpinBox()
        self.sb_countdown.setRange(1, 30)
        self.sb_countdown.setValue(settings.PREVIEW_COUNTDOWN_SECONDS)
        form.addRow("Preview Countdown (s)", self.sb_countdown)

        self.le_l1 = QLineEdit(settings.DEFAULT_TEXT_LINE1)
        form.addRow("Text Zeile 1", self.le_l1)

        self.le_l2 = QLineEdit(settings.DEFAULT_TEXT_LINE2)
        form.addRow("Text Zeile 2", self.le_l2)

        self.cb_template = QComboBox()

        if self._template_names:
          self.cb_template.addItems(self._template_names)

          if self._settings and self._settings.TEMPLATE_NAME in self._template_names:
            self.cb_template.setCurrentText(self._settings.TEMPLATE_NAME)
        else:
          self.cb_template.addItem("(keine gültigen Templates gefunden)")

        form.addRow("Template", self.cb_template)

        buttons = QDialogButtonBox(
          QDialogButtonBox.StandardButton.Save |
          QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        v.addWidget(buttons)

    def get_settings(self) -> Settings:
        s = Settings(
            IDLE_SECONDS_TO_SCREENSAVER=int(self.sb_idle.value()),
            FINAL_IDLE_TIMEOUT_SECONDS=int(self.sb_final.value()),
            PREVIEW_COUNTDOWN_SECONDS=int(self.sb_countdown.value()),
            DEFAULT_TEXT_LINE1=self.le_l1.text(),
            DEFAULT_TEXT_LINE2=self.le_l2.text(),
            TEMPLATE_NAME=self.cb_template.currentText() if self._template_names else self._settings.TEMPLATE_NAME,
        )
        return s
