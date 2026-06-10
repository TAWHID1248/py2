from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QSpinBox, QDoubleSpinBox,
    QLineEdit, QDialogButtonBox, QLabel,
)
from app.core.config import settings


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(380)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.tracking_host = QLineEdit(settings.tracking_host)
        self.tracking_port = QSpinBox()
        self.tracking_port.setRange(1024, 65535)
        self.tracking_port.setValue(settings.tracking_port)
        self.thread_count = QSpinBox()
        self.thread_count.setRange(1, 20)
        self.thread_count.setValue(settings.send_thread_count)
        self.throttle = QDoubleSpinBox()
        self.throttle.setRange(0.0, 60.0)
        self.throttle.setSingleStep(0.5)
        self.throttle.setValue(settings.default_throttle_delay)

        form.addRow("Tracking Host:", self.tracking_host)
        form.addRow("Tracking Port:", self.tracking_port)
        form.addRow("Default Threads:", self.thread_count)
        form.addRow("Default Throttle (s):", self.throttle)
        form.addRow(QLabel("Changes apply on next app restart."))
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def apply(self):
        settings.tracking_host = self.tracking_host.text().strip()
        settings.tracking_port = self.tracking_port.value()
        settings.send_thread_count = self.thread_count.value()
        settings.default_throttle_delay = self.throttle.value()
