from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox,
    QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog, QMessageBox,
)
from PySide6.QtCore import Qt
from app.core.database import get_session
from app.repositories.campaign_repository import CampaignRepository
from app.repositories.tracking_repository import TrackingRepository
from app.models.campaign import Campaign


class ReportsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._load_campaigns()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        top = QHBoxLayout()
        top.addWidget(QLabel("Campaign:"))
        self.campaign_combo = QComboBox()
        self.campaign_combo.setMinimumWidth(250)
        top.addWidget(self.campaign_combo)
        self.btn_load = QPushButton("Load Stats")
        self.btn_export_excel = QPushButton("Export Excel")
        top.addWidget(self.btn_load)
        top.addStretch()
        top.addWidget(self.btn_export_excel)
        layout.addLayout(top)

        self.summary_label = QLabel("")
        layout.addWidget(self.summary_label)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Recipient", "Status", "Sent At", "Opened At", "Error"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        self.btn_load.clicked.connect(self._load_stats)
        self.btn_export_excel.clicked.connect(self._export_excel)

    def _load_campaigns(self):
        with get_session() as s:
            camps = s.query(Campaign).order_by(Campaign.created_at.desc()).all()
            data = [(c.id, c.name) for c in camps]
        self.campaign_combo.clear()
        for cid, name in data:
            self.campaign_combo.addItem(name, userData=cid)

    def _load_stats(self):
        cid = self.campaign_combo.currentData()
        if not cid:
            return
        with get_session() as s:
            camp = s.get(Campaign, cid)
            if not camp:
                return
            sends = camp.sends
            rows = []
            for send in sends:
                contact = s.get(send.__class__, send.contact_id)
                email = contact.email if contact else "?"
                rows.append((
                    email,
                    send.status,
                    str(send.sent_at or "")[:16],
                    str(send.opened_at or "")[:16],
                    send.error_message or "",
                ))
            summary = (
                f"Sent: {camp.sent_count}  Opens: {camp.open_count}  "
                f"Clicks: {camp.click_count}  Bounces: {camp.bounce_count}"
            )

        self.summary_label.setText(summary)
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, val in enumerate(row):
                self.table.setItem(i, j, QTableWidgetItem(val))

    def _export_excel(self):
        cid = self.campaign_combo.currentData()
        if not cid:
            return
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Report", "", "Excel (*.xlsx)")
        if not file_path:
            return
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Report"
        ws.append(["Recipient", "Status", "Sent At", "Opened At", "Error"])
        for row in range(self.table.rowCount()):
            ws.append([
                self.table.item(row, c).text() if self.table.item(row, c) else ""
                for c in range(self.table.columnCount())
            ])
        wb.save(file_path)
        QMessageBox.information(self, "Exported", f"Report saved to {file_path}")
