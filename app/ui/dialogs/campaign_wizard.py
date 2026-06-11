from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QCheckBox, QDoubleSpinBox, QSpinBox, QDialogButtonBox, QLabel,
    QDateTimeEdit, QTabWidget, QWidget, QPushButton, QFileDialog,
    QTextEdit, QHBoxLayout, QGroupBox,
)
from PySide6.QtCore import QDateTime
from app.core.database import get_session
from app.models.template import Template
from app.models.account import Account
from app.models.contact import ContactList


class CampaignWizard(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Campaign")
        self.setMinimumSize(520, 620)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        tabs = QTabWidget()

        # ── Tab 1: Basic ───────────────────────────────────────────────────────
        basic = QWidget()
        bf = QFormLayout(basic)

        self.name_edit      = QLineEdit()
        self.template_combo = QComboBox()
        self.account_combo  = QComboBox()
        self.list_combo     = QComboBox()
        self.from_name_edit = QLineEdit()
        self.from_name_edit.setPlaceholderText("Leave blank for Faker random name")
        self.reply_to_edit  = QLineEdit()

        bf.addRow("Campaign Name:", self.name_edit)
        bf.addRow("Template:", self.template_combo)
        bf.addRow("Send Account:", self.account_combo)
        bf.addRow("Contact List:", self.list_combo)
        bf.addRow("From Name:", self.from_name_edit)
        bf.addRow("Reply-To:", self.reply_to_edit)
        tabs.addTab(basic, "Basic")

        # ── Tab 2: Send Settings ───────────────────────────────────────────────
        send_tab = QWidget()
        sf = QFormLayout(send_tab)

        self.throttle     = QDoubleSpinBox()
        self.throttle.setRange(0.0, 60.0); self.throttle.setValue(1.0)
        self.thread_count = QSpinBox()
        self.thread_count.setRange(1, 20); self.thread_count.setValue(4)
        self.use_spintax  = QCheckBox("Spintax {opt1|opt2|opt3} spinning")
        self.use_synonyms = QCheckBox("WordNet synonym substitution (slower)")
        self.inject_unsub = QCheckBox("Inject unsubscribe link")
        self.inject_unsub.setChecked(True)
        self.use_rotation = QCheckBox("Multi-account rotation (round-robin all active accounts)")
        self.schedule_check = QCheckBox("Schedule for later")
        self.schedule_dt  = QDateTimeEdit(QDateTime.currentDateTime().addSecs(3600))
        self.schedule_dt.setEnabled(False)
        self.schedule_dt.setCalendarPopup(True)

        sf.addRow("Throttle Delay (s):", self.throttle)
        sf.addRow("Send Threads:", self.thread_count)
        sf.addRow("", self.use_spintax)
        sf.addRow("", self.use_synonyms)
        sf.addRow("", self.inject_unsub)
        sf.addRow("", self.use_rotation)
        sf.addRow("", self.schedule_check)
        sf.addRow("Schedule At:", self.schedule_dt)
        self.schedule_check.toggled.connect(self.schedule_dt.setEnabled)
        tabs.addTab(send_tab, "Send Settings")

        # ── Tab 3: Attachments (Phase 3) ───────────────────────────────────────
        att_tab = QWidget()
        av = QVBoxLayout(att_tab)

        grp_pdf = QGroupBox("PDF Attachment")
        pf = QVBoxLayout(grp_pdf)
        self.attach_pdf = QCheckBox("Attach personalized PDF to each email")
        pf.addWidget(self.attach_pdf)
        pf.addWidget(QLabel("PDF HTML Template (merge fields supported):"))
        self.pdf_html = QTextEdit()
        self.pdf_html.setPlaceholderText(
            "<!DOCTYPE html><html><body>\n"
            "<h1>Hello, {first_name}!</h1>\n"
            "<p>Company: {company}</p>\n"
            "</body></html>"
        )
        self.pdf_html.setMaximumHeight(160)
        pf.addWidget(self.pdf_html)
        av.addWidget(grp_pdf)

        grp_word = QGroupBox("Word Document Attachment")
        wf = QVBoxLayout(grp_word)
        self.attach_word = QCheckBox("Attach personalized Word document")
        wf.addWidget(self.attach_word)
        word_row = QHBoxLayout()
        self.word_path = QLineEdit(); self.word_path.setReadOnly(True)
        self.word_path.setPlaceholderText("Select .docx template…")
        btn_word = QPushButton("Browse…")
        btn_word.clicked.connect(self._browse_word)
        word_row.addWidget(self.word_path)
        word_row.addWidget(btn_word)
        wf.addLayout(word_row)
        av.addWidget(grp_word)

        name_form = QFormLayout()
        self.att_name_pattern = QLineEdit()
        self.att_name_pattern.setPlaceholderText(
            "e.g. Invoice_{first_name}_{last_name}.pdf"
        )
        name_form.addRow("Attachment filename pattern:", self.att_name_pattern)
        av.addLayout(name_form)
        av.addStretch()
        tabs.addTab(att_tab, "Attachments")

        layout.addWidget(tabs)
        self._populate_combos()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _populate_combos(self):
        with get_session() as s:
            templates = [(t.id, t.name) for t in s.query(Template).order_by(Template.name).all()]
            accounts  = [(a.id, a.name, a.email) for a in s.query(Account).filter_by(is_active=True).order_by(Account.name).all()]
            lists     = [(cl.id, cl.name, cl.record_count) for cl in s.query(ContactList).order_by(ContactList.name).all()]

        for tid, tname in templates:
            self.template_combo.addItem(tname, userData=tid)
        for aid, aname, aemail in accounts:
            self.account_combo.addItem(f"{aname} <{aemail}>", userData=aid)
        for clid, clname, clcount in lists:
            self.list_combo.addItem(f"{clname} ({clcount})", userData=clid)

    def _browse_word(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Word Template", "", "Word (*.docx)"
        )
        if path:
            self.word_path.setText(path)

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
            "use_account_rotation": self.use_rotation.isChecked(),
            "attach_pdf": self.attach_pdf.isChecked(),
            "pdf_template_html": self.pdf_html.toPlainText() or None,
            "attach_word": self.attach_word.isChecked(),
            "word_template_path": self.word_path.text() or None,
            "attachment_name_pattern": self.att_name_pattern.text().strip() or None,
            "status": "draft",
        }
        if self.schedule_check.isChecked():
            d["scheduled_at"] = self.schedule_dt.dateTime().toPython()
            d["status"] = "scheduled"
        return d
