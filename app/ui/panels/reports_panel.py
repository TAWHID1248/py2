from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox,
    QLabel, QTableWidget, QTableWidgetItem, QHeaderView,
    QFileDialog, QMessageBox, QFrame,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from app.core.database import get_session
from app.models.campaign import Campaign, CampaignSend
from app.models.contact import Contact


class ReportsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows: list[dict] = []
        self._build_ui()
        self._load_campaigns()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Top bar
        top = QHBoxLayout()
        top.addWidget(QLabel("Campaign:"))
        self.campaign_combo = QComboBox()
        self.campaign_combo.setMinimumWidth(260)
        top.addWidget(self.campaign_combo)
        self.btn_load = QPushButton("Load Stats")
        top.addWidget(self.btn_load)
        top.addStretch()
        self.btn_xlsx = QPushButton("Export Excel")
        self.btn_pdf  = QPushButton("Export PDF")
        top.addWidget(self.btn_xlsx)
        top.addWidget(self.btn_pdf)
        layout.addLayout(top)

        # Summary cards
        cards = QHBoxLayout()
        self._card_sent    = self._card("Sent",    "#89dceb")
        self._card_opens   = self._card("Opens",   "#a6e3a1")
        self._card_clicks  = self._card("Clicks",  "#f9e2af")
        self._card_bounces = self._card("Bounces", "#f38ba8")
        self._card_unsubs  = self._card("Unsubs",  "#cba6f7")
        self._card_rate    = self._card("Open %",  "#89b4fa")
        for c in [self._card_sent, self._card_opens, self._card_clicks,
                  self._card_bounces, self._card_unsubs, self._card_rate]:
            cards.addWidget(c)
        layout.addLayout(cards)

        # Detail table
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["Email", "Name", "Company", "Status", "Sent At", "Opened At", "Error"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

        self.btn_load.clicked.connect(self._load_stats)
        self.btn_xlsx.clicked.connect(self._export_excel)
        self.btn_pdf.clicked.connect(self._export_pdf)

    def _card(self, label: str, color: str) -> QFrame:
        f = QFrame()
        f.setFrameShape(QFrame.Shape.StyledPanel)
        from PySide6.QtWidgets import QVBoxLayout as VBL
        v = VBL(f)
        val = QLabel("—")
        val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = val.font(); font.setPointSize(20); font.setBold(True); val.setFont(font)
        val.setStyleSheet(f"color:{color};")
        lbl = QLabel(label)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(val); v.addWidget(lbl)
        f._value_label = val
        return f

    def _set_card(self, card, value):
        card._value_label.setText(str(value))

    def _load_campaigns(self):
        with get_session() as s:
            camps = s.query(Campaign).order_by(Campaign.created_at.desc()).all()
            data = [(c.id, c.name, c.status) for c in camps]
        self.campaign_combo.clear()
        for cid, name, status in data:
            self.campaign_combo.addItem(f"{name} [{status}]", userData=cid)

    def _load_stats(self):
        cid = self.campaign_combo.currentData()
        if not cid:
            return
        with get_session() as s:
            camp = s.get(Campaign, cid)
            if not camp:
                return
            sends = s.query(CampaignSend).filter_by(campaign_id=cid).all()
            rows = []
            for send in sends:
                contact = s.get(Contact, send.contact_id)
                rows.append({
                    "Email": contact.email if contact else "?",
                    "Name": f"{contact.first_name or ''} {contact.last_name or ''}".strip() if contact else "",
                    "Company": (contact.company or "") if contact else "",
                    "Status": send.status,
                    "Sent At": str(send.sent_at or "")[:16],
                    "Opened At": str(send.opened_at or "")[:16],
                    "Error": send.error_message or "",
                })
            sent    = camp.sent_count
            opens   = camp.open_count
            clicks  = camp.click_count
            bounces = camp.bounce_count
            unsubs  = camp.unsub_count
            rate    = f"{opens/sent*100:.1f}%" if sent else "—"

        self._set_card(self._card_sent,    sent)
        self._set_card(self._card_opens,   opens)
        self._set_card(self._card_clicks,  clicks)
        self._set_card(self._card_bounces, bounces)
        self._set_card(self._card_unsubs,  unsubs)
        self._set_card(self._card_rate,    rate)

        self._rows = rows
        self.table.setRowCount(len(rows))
        status_colors = {
            "sent": "#a6e3a1", "opened": "#89b4fa", "clicked": "#f9e2af",
            "failed": "#f38ba8", "bounced": "#f38ba8",
        }
        for i, row in enumerate(rows):
            vals = list(row.values())
            for j, v in enumerate(vals):
                item = QTableWidgetItem(v)
                if j == 3:  # Status column
                    item.setForeground(QColor(status_colors.get(v, "#cdd6f4")))
                self.table.setItem(i, j, item)

    def _export_excel(self):
        cid = self.campaign_combo.currentData()
        if not cid:
            QMessageBox.warning(self, "No Campaign", "Load a campaign first.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Excel Report", "", "Excel (*.xlsx)"
        )
        if not path:
            return
        try:
            from app.services.document.report_exporter import export_excel
            export_excel(cid, Path(path))
            QMessageBox.information(self, "Exported", f"Excel saved:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _export_pdf(self):
        cid = self.campaign_combo.currentData()
        if not cid:
            QMessageBox.warning(self, "No Campaign", "Load a campaign first.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export PDF Report", "", "PDF (*.pdf)"
        )
        if not path:
            return
        try:
            from app.services.document.report_exporter import export_pdf
            export_pdf(cid, Path(path))
            QMessageBox.information(self, "Exported", f"PDF saved:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))


# Path needed in export methods
from pathlib import Path
