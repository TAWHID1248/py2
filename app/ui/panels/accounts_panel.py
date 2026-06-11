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
        prev_row = self.table.currentRow()
        with get_session() as s:
            accounts = AccountRepository(s).all()
            rows = [
                (acc.id, acc.name, acc.email, acc.account_type.upper(),
                 acc.smtp_host or "", "Yes" if acc.is_active else "No")
                for acc in accounts
            ]
        self.table.setRowCount(len(rows))
        for i, (acc_id, name, email, atype, host, active) in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(name))
            self.table.setItem(i, 1, QTableWidgetItem(email))
            self.table.setItem(i, 2, QTableWidgetItem(atype))
            self.table.setItem(i, 3, QTableWidgetItem(host))
            self.table.setItem(i, 4, QTableWidgetItem(active))
            self.table.item(i, 0).setData(Qt.ItemDataRole.UserRole, acc_id)
        if rows:
            self.table.selectRow(max(0, min(prev_row, len(rows) - 1)))

    def _selected_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0 and self.table.rowCount() == 1:
            self.table.selectRow(0)
            row = 0
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _require_selection(self) -> int | None:
        acc_id = self._selected_id()
        if not acc_id:
            QMessageBox.warning(self, "No Selection", "Please select an account from the list first.")
        return acc_id

    def _add(self):
        dlg = AccountDialog(parent=self)
        if dlg.exec():
            with get_session() as s:
                AccountRepository(s).create(dlg.data())
            self.refresh()

    def _edit(self):
        acc_id = self._require_selection()
        if not acc_id:
            return
        # Extract all needed data inside the session so the dialog gets plain values
        with get_session() as s:
            acc = AccountRepository(s).get(acc_id)
            if not acc:
                return
            # Read all attributes while session is open to avoid DetachedInstanceError
            acc_data = {
                "name": acc.name,
                "email": acc.email,
                "account_type": acc.account_type,
                "smtp_host": acc.smtp_host,
                "smtp_port": acc.smtp_port,
                "smtp_use_tls": acc.smtp_use_tls,
                "smtp_username": acc.smtp_username,
                "daily_limit": acc.daily_limit,
                "hourly_limit": acc.hourly_limit,
                "throttle_delay": acc.throttle_delay,
                "is_active": acc.is_active,
                "has_oauth": bool(acc.oauth_token_enc),
            }
        dlg = AccountDialog(account_data=acc_data, parent=self)
        if dlg.exec():
            with get_session() as s:
                AccountRepository(s).update(acc_id, dlg.data())
            self.refresh()

    def _delete(self):
        acc_id = self._require_selection()
        if not acc_id:
            return
        if QMessageBox.question(self, "Delete", "Delete this account?") == QMessageBox.StandardButton.Yes:
            with get_session() as s:
                AccountRepository(s).delete(acc_id)
            self.refresh()
