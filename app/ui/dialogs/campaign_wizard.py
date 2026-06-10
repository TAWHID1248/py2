from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QCheckBox, QDoubleSpinBox, QSpinBox, QDialogButtonBox, QLabel,
    QDateTimeEdit,
)
from PySide6.QtCore import QDateTime, Qt
from app.core.database import get_session
from app.models.template import Template
from app.models.account import Account
from app.models.contact import ContactList


class CampaignWizard(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Campaign")
        self.setMinimumWidth(460)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_edit = QLineEdit()
        self.template_combo = QComboBox()
        self.account_combo = QComboBox()
        self.list_combo = QComboBox()
        self.from_name_edit = QLineEdit()
        self.reply_to_edit = QLineEdit()
        self.throttle = QDoubleSpinBox()
        self.throttle.setRange(0.0, 60.0)
        self.throttle.setValue(1.0)
        self.thread_count = QSpinBox()
        self.thread_count.setRange(1, 20)
        self.thread_count.setValue(4)
        self.use_spintax = QCheckBox("Spintax spinning")
        self.use_synonyms = QCheckBox("WordNet synonyms (slower)")
        self.inject_unsub = QCheckBox("Inject unsubscribe link")
        self.inject_unsub.setChecked(True)
        self.schedule_check = QCheckBox("Schedule for later")
        self.schedule_dt = QDateTimeEdit(QDateTime.currentDateTime().addSecs(3600))
        self.schedule_dt.setEnabled(False)
        self.schedule_dt.setCalendarPopup(True)

        form.addRow("Campaign Name:", self.name_edit)
        form.addRow("Template:", self.template_combo)
        form.addRow("Send Account:", self.account_combo)
        form.addRow("Contact List:", self.list_combo)
        form.addRow("From Name:", self.from_name_edit)
        form.addRow("Reply-To:", self.reply_to_edit)
        form.addRow("Throttle Delay (s):", self.throttle)
        form.addRow("Send Threads:", self.thread_count)
        form.addRow("", self.use_spintax)
        form.addRow("", self.use_synonyms)
        form.addRow("", self.inject_unsub)
        form.addRow("", self.schedule_check)
        form.addRow("Schedule Time:", self.schedule_dt)
        layout.addLayout(form)

        self.schedule_check.toggled.connect(self.schedule_dt.setEnabled)

        self._populate_combos()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _populate_combos(self):
        with get_session() as s:
            templates = s.query(Template).order_by(Template.name).all()
            accounts = s.query(Account).filter_by(is_active=True).order_by(Account.name).all()
            lists = s.query(ContactList).order_by(ContactList.name).all()

        for t in templates:
            self.template_combo.addItem(t.name, userData=t.id)
        for a in accounts:
            self.account_combo.addItem(f"{a.name} <{a.email}>", userData=a.id)
        for cl in lists:
            self.list_combo.addItem(f"{cl.name} ({cl.record_count})", userData=cl.id)

    def data(self) -> dict:
        d = {
            "name": self.name_edit.text().strip() or "Untitled Campaign",
            "template_id": self.template_combo.currentData(),
            "account_id": self.account_combo.currentData(),
            "list_id": self.list_combo.currentData(),
            "from_name": self.from_name_edit.text().strip(),
            "reply_to": self.reply_to_edit.text().strip() or None,
            "throttle_delay": self.throttle.value(),
            "thread_count": self.thread_count.value(),
            "use_spintax": self.use_spintax.isChecked(),
            "use_synonyms": self.use_synonyms.isChecked(),
            "inject_unsubscribe": self.inject_unsub.isChecked(),
            "status": "draft",
        }
        if self.schedule_check.isChecked():
            dt = self.schedule_dt.dateTime().toPython()
            d["scheduled_at"] = dt
            d["status"] = "scheduled"
        return d
