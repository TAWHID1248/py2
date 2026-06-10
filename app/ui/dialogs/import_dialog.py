from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QDialogButtonBox, QPushButton, QFileDialog,
)


class ImportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import Contacts")
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.file_edit = QLineEdit()
        self.file_edit.setReadOnly(True)
        btn_browse = QPushButton("Browse…")
        btn_browse.clicked.connect(self._browse)

        self.list_name_edit = QLineEdit()

        form.addRow("File:", self.file_edit)
        form.addRow("", btn_browse)
        form.addRow("List Name:", self.list_name_edit)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select File", "", "Excel/CSV (*.xlsx *.xls *.csv)"
        )
        if path:
            self.file_edit.setText(path)

    def file_path(self) -> str:
        return self.file_edit.text()

    def list_name(self) -> str:
        return self.list_name_edit.text().strip()
