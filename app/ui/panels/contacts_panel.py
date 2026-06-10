from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QProgressBar, QFileDialog, QInputDialog, QMessageBox, QTabWidget,
)
from PySide6.QtCore import Qt
from app.core.database import get_session
from app.repositories.contact_repository import ContactRepository
from app.ui.workers.import_worker import ImportWorker
from app.ui.panels.suppression_panel import SuppressionPanel


class _ListsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: ImportWorker | None = None
        self._build_ui()
        self._load_lists()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        top = QHBoxLayout()
        top.addWidget(QLabel("List:"))
        self.list_combo = QComboBox()
        self.list_combo.setMinimumWidth(220)
        top.addWidget(self.list_combo)
        self.btn_new_list = QPushButton("New List")
        self.btn_del_list = QPushButton("Delete List")
        self.btn_import   = QPushButton("Import CSV/Excel…")
        self.btn_export   = QPushButton("Export…")
        top.addWidget(self.btn_new_list)
        top.addWidget(self.btn_del_list)
        top.addStretch()
        top.addWidget(self.btn_import)
        top.addWidget(self.btn_export)
        layout.addLayout(top)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["Email", "First Name", "Last Name", "Company", "Phone", "Suppressed"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        self.list_combo.currentIndexChanged.connect(self._load_contacts)
        self.btn_new_list.clicked.connect(self._new_list)
        self.btn_del_list.clicked.connect(self._delete_list)
        self.btn_import.clicked.connect(self._import)
        self.btn_export.clicked.connect(self._export)

    def _load_lists(self):
        with get_session() as s:
            lists = ContactRepository(s).all_lists()
        self.list_combo.blockSignals(True)
        self.list_combo.clear()
        for cl in lists:
            self.list_combo.addItem(f"{cl.name} ({cl.record_count})", userData=cl.id)
        self.list_combo.blockSignals(False)
        self._load_contacts()

    def _load_contacts(self):
        list_id = self.list_combo.currentData()
        if list_id is None:
            self.table.setRowCount(0)
            return
        with get_session() as s:
            contacts = ContactRepository(s).contacts_in_list(list_id)
        self.table.setRowCount(len(contacts))
        for i, c in enumerate(contacts):
            self.table.setItem(i, 0, QTableWidgetItem(c.email))
            self.table.setItem(i, 1, QTableWidgetItem(c.first_name or ""))
            self.table.setItem(i, 2, QTableWidgetItem(c.last_name or ""))
            self.table.setItem(i, 3, QTableWidgetItem(c.company or ""))
            self.table.setItem(i, 4, QTableWidgetItem(c.phone or ""))
            self.table.setItem(i, 5, QTableWidgetItem("Yes" if c.is_suppressed else ""))
        self.status_label.setText(f"{len(contacts)} contacts")

    def _new_list(self):
        name, ok = QInputDialog.getText(self, "New List", "List name:")
        if ok and name.strip():
            with get_session() as s:
                ContactRepository(s).create_list(name.strip())
            self._load_lists()

    def _delete_list(self):
        list_id = self.list_combo.currentData()
        if not list_id:
            return
        if QMessageBox.question(self, "Delete List", "Delete this list?") \
                == QMessageBox.StandardButton.Yes:
            with get_session() as s:
                ContactRepository(s).delete_list(list_id)
            self._load_lists()

    def _import(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Contacts", "", "Excel/CSV (*.xlsx *.xls *.csv)"
        )
        if not file_path:
            return

        list_id = self.list_combo.currentData()
        if list_id is not None:
            list_name = self.list_combo.currentText().split(" (")[0]
        else:
            list_name, ok = QInputDialog.getText(self, "List Name", "Enter list name:")
            if not ok or not list_name.strip():
                return
            list_name = list_name.strip()

        self.progress.setVisible(True)
        self.progress.setValue(0)
        self._worker = ImportWorker(file_path, list_name, parent=self)
        self._worker.progress.connect(lambda c, t: self.progress.setValue(int(c / t * 100)))
        self._worker.finished.connect(self._on_import_done)
        self._worker.error.connect(lambda e: QMessageBox.critical(self, "Import Error", e))
        self._worker.start()

    def _on_import_done(self, count: int, list_name: str):
        self.progress.setVisible(False)
        self.status_label.setText(f"Imported {count} contacts into '{list_name}'")
        self._load_lists()

    def _export(self):
        list_id = self.list_combo.currentData()
        if not list_id:
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Contacts", "", "Excel (*.xlsx);;CSV (*.csv)"
        )
        if not file_path:
            return
        with get_session() as s:
            contacts = ContactRepository(s).contacts_in_list(list_id)
        if file_path.endswith(".csv"):
            import csv
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["email", "first_name", "last_name", "company", "phone"])
                for c in contacts:
                    writer.writerow([c.email, c.first_name, c.last_name, c.company, c.phone])
        else:
            import openpyxl
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.append(["email", "first_name", "last_name", "company", "phone"])
            for c in contacts:
                ws.append([c.email, c.first_name, c.last_name, c.company, c.phone])
            wb.save(file_path)
        QMessageBox.information(self, "Export", f"Exported {len(contacts)} contacts.")


class ContactsPanel(QWidget):
    """Contacts panel with Lists and Suppression sub-tabs."""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        tabs = QTabWidget()
        self._lists_tab = _ListsTab()
        self._supp_tab = SuppressionPanel()
        tabs.addTab(self._lists_tab, "Contact Lists")
        tabs.addTab(self._supp_tab, "Suppression List")
        layout.addWidget(tabs)

    # proxy method used by MainWindow quick-import
    def _import(self):
        self._lists_tab._import()
