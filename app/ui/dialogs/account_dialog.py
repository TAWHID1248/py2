from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QSpinBox, QDoubleSpinBox,
    QCheckBox, QComboBox, QDialogButtonBox, QPushButton, QMessageBox,
    QVBoxLayout, QHBoxLayout, QLabel, QStackedWidget, QWidget, QFileDialog,
)
from PySide6.QtCore import Qt
from app.models.account import Account


class AccountDialog(QDialog):
    def __init__(self, account: Account | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Account" if not account else "Edit Account")
        self.setMinimumWidth(460)
        self._account = account
        self._oauth_json: str | None = None
        self._gmail_address: str = ""
        self._build_ui()
        if account:
            self._populate(account)

    def _build_ui(self):
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.name_edit = QLineEdit()
        self.email_edit = QLineEdit()
        self.type_combo = QComboBox()
        self.type_combo.addItems(["smtp", "gmail"])
        form.addRow("Display Name:", self.name_edit)
        form.addRow("Email Address:", self.email_edit)
        form.addRow("Account Type:", self.type_combo)
        layout.addLayout(form)

        # --- stacked pages: SMTP vs Gmail ---
        self._stack = QStackedWidget()

        # SMTP page
        smtp_page = QWidget()
        sf = QFormLayout(smtp_page)
        self.smtp_host = QLineEdit()
        self.smtp_port = QSpinBox()
        self.smtp_port.setRange(1, 65535)
        self.smtp_port.setValue(587)
        self.smtp_tls = QCheckBox("Use STARTTLS")
        self.smtp_tls.setChecked(True)
        self.smtp_user = QLineEdit()
        self.smtp_pass = QLineEdit()
        self.smtp_pass.setEchoMode(QLineEdit.EchoMode.Password)
        sf.addRow("SMTP Host:", self.smtp_host)
        sf.addRow("SMTP Port:", self.smtp_port)
        sf.addRow("", self.smtp_tls)
        sf.addRow("Username:", self.smtp_user)
        sf.addRow("Password:", self.smtp_pass)
        btn_test = QPushButton("Test SMTP Connection")
        btn_test.clicked.connect(self._test_smtp)
        sf.addRow("", btn_test)
        self._stack.addWidget(smtp_page)  # index 0

        # Gmail page
        gmail_page = QWidget()
        gf = QVBoxLayout(gmail_page)
        gf.addWidget(QLabel(
            "<b>Gmail OAuth2</b><br>"
            "Option A: select your client_secrets.json from Google Cloud Console.<br>"
            "Option B: enter Client ID + Secret manually."
        ))
        gf.addSpacing(6)

        row_a = QHBoxLayout()
        self.btn_secrets_file = QPushButton("Select client_secrets.json…")
        self.btn_secrets_file.clicked.connect(self._oauth_from_file)
        row_a.addWidget(self.btn_secrets_file)
        gf.addLayout(row_a)

        gf.addWidget(QLabel("— or —"))

        manual_form = QFormLayout()
        self.gmail_client_id = QLineEdit()
        self.gmail_client_id.setPlaceholderText("xxxxx.apps.googleusercontent.com")
        self.gmail_client_secret = QLineEdit()
        self.gmail_client_secret.setEchoMode(QLineEdit.EchoMode.Password)
        manual_form.addRow("Client ID:", self.gmail_client_id)
        manual_form.addRow("Client Secret:", self.gmail_client_secret)
        btn_manual = QPushButton("Authorize via Browser…")
        btn_manual.clicked.connect(self._oauth_from_manual)
        manual_form.addRow("", btn_manual)
        gf.addLayout(manual_form)

        self.gmail_status = QLabel("")
        self.gmail_status.setWordWrap(True)
        gf.addWidget(self.gmail_status)
        gf.addStretch()
        self._stack.addWidget(gmail_page)  # index 1

        layout.addWidget(self._stack)
        self.type_combo.currentIndexChanged.connect(self._stack.setCurrentIndex)

        # Shared limits
        limits_form = QFormLayout()
        self.daily_limit = QSpinBox()
        self.daily_limit.setRange(1, 100000)
        self.daily_limit.setValue(500)
        self.hourly_limit = QSpinBox()
        self.hourly_limit.setRange(1, 10000)
        self.hourly_limit.setValue(100)
        self.throttle = QDoubleSpinBox()
        self.throttle.setRange(0.0, 60.0)
        self.throttle.setSingleStep(0.5)
        self.throttle.setValue(1.0)
        self.is_active = QCheckBox("Active")
        self.is_active.setChecked(True)
        limits_form.addRow("Daily Limit:", self.daily_limit)
        limits_form.addRow("Hourly Limit:", self.hourly_limit)
        limits_form.addRow("Throttle Delay (s):", self.throttle)
        limits_form.addRow("", self.is_active)
        layout.addLayout(limits_form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _populate(self, acc: Account):
        self.name_edit.setText(acc.name)
        self.email_edit.setText(acc.email)
        idx = self.type_combo.findText(acc.account_type)
        if idx >= 0:
            self.type_combo.setCurrentIndex(idx)
        self.smtp_host.setText(acc.smtp_host or "")
        self.smtp_port.setValue(acc.smtp_port or 587)
        self.smtp_tls.setChecked(acc.smtp_use_tls)
        self.smtp_user.setText(acc.smtp_username or "")
        self.daily_limit.setValue(acc.daily_limit)
        self.hourly_limit.setValue(acc.hourly_limit)
        self.throttle.setValue(acc.throttle_delay)
        self.is_active.setChecked(acc.is_active)
        if acc.account_type == "gmail" and acc.oauth_token_enc:
            self.gmail_status.setText("Gmail: authorized (token stored)")

    def _oauth_from_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select client_secrets.json", "", "JSON (*.json)"
        )
        if not path:
            return
        self._run_oauth(lambda: self._auth_from_file(path))

    def _auth_from_file(self, path: str) -> str:
        from app.services.auth.google_auth_service import authorize_from_secrets_file
        return authorize_from_secrets_file(path)

    def _oauth_from_manual(self):
        cid = self.gmail_client_id.text().strip()
        cs = self.gmail_client_secret.text().strip()
        if not cid or not cs:
            QMessageBox.warning(self, "Missing", "Enter Client ID and Secret first.")
            return
        self._run_oauth(lambda: self._auth_from_manual(cid, cs))

    def _auth_from_manual(self, cid: str, cs: str) -> str:
        from app.services.auth.google_auth_service import authorize_from_client_id
        return authorize_from_client_id(cid, cs)

    def _run_oauth(self, auth_fn):
        self.gmail_status.setText("Opening browser for authorization…")
        try:
            creds_json = auth_fn()
            self._oauth_json = creds_json
            from app.services.auth.google_auth_service import get_gmail_address
            self._gmail_address = get_gmail_address(creds_json)
            if self._gmail_address and not self.email_edit.text():
                self.email_edit.setText(self._gmail_address)
            self.gmail_status.setText(f"Authorized: {self._gmail_address or 'OK'}")
        except Exception as exc:
            QMessageBox.critical(self, "OAuth Error", str(exc))
            self.gmail_status.setText(f"Authorization failed: {exc}")

    def _test_smtp(self):
        from app.services.email.smtp_service import test_smtp_connection
        acc = Account()
        acc.smtp_host = self.smtp_host.text().strip()
        acc.smtp_port = self.smtp_port.value()
        acc.smtp_use_tls = self.smtp_tls.isChecked()
        acc.smtp_username = self.smtp_user.text().strip()
        acc.email = self.email_edit.text().strip()
        ok, msg = test_smtp_connection(acc, self.smtp_pass.text())
        if ok:
            QMessageBox.information(self, "Test", msg)
        else:
            QMessageBox.critical(self, "Test Failed", msg)

    def _on_accept(self):
        if not self.email_edit.text().strip():
            QMessageBox.warning(self, "Required", "Email address is required.")
            return
        if self.type_combo.currentText() == "gmail" and not self._oauth_json:
            if self._account and self._account.oauth_token_enc:
                pass  # keep existing token
            else:
                QMessageBox.warning(self, "Required", "Authorize Gmail before saving.")
                return
        self.accept()

    def data(self) -> dict:
        d = {
            "name": self.name_edit.text().strip() or self.email_edit.text().strip(),
            "email": self.email_edit.text().strip(),
            "account_type": self.type_combo.currentText(),
            "smtp_host": self.smtp_host.text().strip(),
            "smtp_port": self.smtp_port.value(),
            "smtp_use_tls": self.smtp_tls.isChecked(),
            "smtp_username": self.smtp_user.text().strip(),
            "daily_limit": self.daily_limit.value(),
            "hourly_limit": self.hourly_limit.value(),
            "throttle_delay": self.throttle.value(),
            "is_active": self.is_active.isChecked(),
        }
        if self.smtp_pass.text():
            d["smtp_password"] = self.smtp_pass.text()
        if self._oauth_json:
            d["oauth_token"] = self._oauth_json
        return d
