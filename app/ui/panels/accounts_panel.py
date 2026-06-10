from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
)
from PySide6.QtCore import Qt
from app.core.database import get_session
from app.repositories.account_repository import AccountRepository
from app.ui.dialogs.account_dialog import AccountDialog


class AccountsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        btn_bar = QHBoxLayout()
        self.btn_add = QPushButton("Add Account")
        self.btn_edit = QPushButton("Edit")
        self.btn_delete = QPushButton("Delete")
        self.btn_refresh = QPushButton("Refresh")
        btn_bar.addWidget(self.btn_add)
        btn_bar.addWidget(self.btn_edit)
        btn_bar.addWidget(self.btn_delete)
        btn_bar.addStretch()
        btn_bar.addWidget(self.btn_refresh)
        layout.addLayout(btn_bar)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Name", "Email", "Type", "SMTP Host", "Active"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        self.btn_add.clicked.connect(self._add)
        self.btn_edit.clicked.connect(self._edit)
        self.btn_delete.clicked.connect(self._delete)
        self.btn_refresh.clicked.connect(self.refresh)

    def refresh(self):
        with get_session() as s:
            accounts = AccountRepository(s).all()
            self.table.setRowCount(len(accounts))
            for i, acc in enumerate(accounts):
                self.table.setItem(i, 0, QTableWidgetItem(acc.name))
                self.table.setItem(i, 1, QTableWidgetItem(acc.email))
                self.table.setItem(i, 2, QTableWidgetItem(acc.account_type.upper()))
                self.table.setItem(i, 3, QTableWidgetItem(acc.smtp_host or ""))
                self.table.setItem(i, 4, QTableWidgetItem("Yes" if acc.is_active else "No"))
                self.table.item(i, 0).setData(Qt.ItemDataRole.UserRole, acc.id)

    def _selected_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _add(self):
        dlg = AccountDialog(parent=self)
        if dlg.exec():
            with get_session() as s:
                AccountRepository(s).create(dlg.data())
            self.refresh()

    def _edit(self):
        acc_id = self._selected_id()
        if not acc_id:
            return
        with get_session() as s:
            acc = AccountRepository(s).get(acc_id)
            if not acc:
                return
            dlg = AccountDialog(account=acc, parent=self)
        if dlg.exec():
            with get_session() as s:
                AccountRepository(s).update(acc_id, dlg.data())
            self.refresh()

    def _delete(self):
        acc_id = self._selected_id()
        if not acc_id:
            return
        if QMessageBox.question(self, "Delete", "Delete this account?") == QMessageBox.StandardButton.Yes:
            with get_session() as s:
                AccountRepository(s).delete(acc_id)
            self.refresh()
