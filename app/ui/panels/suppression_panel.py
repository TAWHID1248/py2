"""Suppression / unsubscribe list management panel."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QMessageBox, QFileDialog,
)
from PySide6.QtCore import Qt
from app.core.database import get_session
from app.repositories.contact_repository import ContactRepository


class SuppressionPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        top = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search email…")
        self.search_edit.textChanged.connect(self._filter)
        self.btn_add = QPushButton("Add Email")
        self.btn_remove = QPushButton("Remove")
        self.btn_import = QPushButton("Import List…")
        self.btn_export = QPushButton("Export…")
        top.addWidget(self.search_edit, 2)
        top.addWidget(self.btn_add)
        top.addWidget(self.btn_remove)
        top.addStretch()
        top.addWidget(self.btn_import)
        top.addWidget(self.btn_export)
        layout.addLayout(top)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Email", "Reason", "Added"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        self.count_label = QLabel("")
        layout.addWidget(self.count_label)

        self.btn_add.clicked.connect(self._add)
        self.btn_remove.clicked.connect(self._remove)
        self.btn_import.clicked.connect(self._import)
        self.btn_export.clicked.connect(self._export)

        self._all_rows: list[tuple] = []

    def refresh(self):
        with get_session() as s:
            rows = ContactRepository(s).all_suppressed()
            self._all_rows = [(r.email, r.reason or "", str(r.added_at)[:16]) for r in rows]
        self._render(self._all_rows)

    def _render(self, rows: list[tuple]):
        self.table.setRowCount(len(rows))
        for i, (email, reason, added) in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(email))
            self.table.setItem(i, 1, QTableWidgetItem(reason))
            self.table.setItem(i, 2, QTableWidgetItem(added))
        self.count_label.setText(f"{len(rows)} suppressed addresses")

    def _filter(self, text: str):
        text = text.lower()
        filtered = [r for r in self._all_rows if text in r[0].lower()]
        self._render(filtered)

    def _add(self):
        from PySide6.QtWidgets import QInputDialog
        email, ok = QInputDialog.getText(self, "Add to Suppression List", "Email address:")
        if ok and email.strip():
            with get_session() as s:
                ContactRepository(s).suppress(email.strip(), reason="manual")
            self.refresh()

    def _remove(self):
        row = self.table.currentRow()
        if row < 0:
            return
        email = self.table.item(row, 0).text()
        if QMessageBox.question(self, "Remove", f"Remove {email} from suppression list?") \
                == QMessageBox.StandardButton.Yes:
            with get_session() as s:
                from app.models.contact import SuppressionList
                rec = s.query(SuppressionList).filter_by(email=email).first()
                if rec:
                    s.delete(rec)
                # Also un-suppress the contact record
                contact = ContactRepository(s).get_by_email(email)
                if contact:
                    contact.is_suppressed = False
            self.refresh()

    def _import(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Suppression List", "", "CSV/Text (*.csv *.txt)"
        )
        if not path:
            return
        count = 0
        with open(path, encoding="utf-8-sig") as f:
            for line in f:
                email = line.strip().split(",")[0].strip()
                if email and "@" in email:
                    with get_session() as s:
                        ContactRepository(s).suppress(email, reason="imported")
                    count += 1
        QMessageBox.information(self, "Import", f"Added {count} addresses.")
        self.refresh()

    def _export(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Suppression List", "suppression.csv", "CSV (*.csv)"
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write("email,reason,added_at\n")
            for email, reason, added in self._all_rows:
                f.write(f"{email},{reason},{added}\n")
        QMessageBox.information(self, "Export", f"Exported {len(self._all_rows)} addresses.")
