from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QTextEdit, QSplitter, QMessageBox, QLabel,
)
from PySide6.QtCore import Qt
from app.core.database import get_session
from app.repositories.campaign_repository import CampaignRepository
from app.core.event_bus import bus
from app.ui.dialogs.campaign_wizard import CampaignWizard
from app.ui.workers.send_worker import SendWorker


class CampaignsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._workers: dict[int, SendWorker] = {}
        self._build_ui()
        self.refresh()
        bus.log_line.connect(self._append_log)
        bus.send_progress.connect(self._on_progress)
        bus.send_complete.connect(lambda cid: self.refresh())

    def _build_ui(self):
        layout = QVBoxLayout(self)

        btn_bar = QHBoxLayout()
        self.btn_new = QPushButton("New Campaign")
        self.btn_start = QPushButton("Start")
        self.btn_pause = QPushButton("Pause")
        self.btn_stop = QPushButton("Stop")
        self.btn_delete = QPushButton("Delete")
        self.btn_refresh = QPushButton("Refresh")
        for b in [self.btn_new, self.btn_start, self.btn_pause, self.btn_stop,
                  self.btn_delete, self.btn_refresh]:
            btn_bar.addWidget(b)
        btn_bar.addStretch()
        layout.addLayout(btn_bar)

        splitter = QSplitter(Qt.Orientation.Vertical)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["Name", "Status", "Sent", "Opens", "Clicks", "Bounces", "Created"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        splitter.addWidget(self.table)

        log_widget = QWidget()
        log_layout = QVBoxLayout(log_widget)
        log_layout.addWidget(QLabel("Send Log:"))
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(200)
        log_layout.addWidget(self.log_view)
        splitter.addWidget(log_widget)
        splitter.setStretchFactor(0, 3)

        layout.addWidget(splitter)

        self.btn_new.clicked.connect(self._new_campaign)
        self.btn_start.clicked.connect(self._start)
        self.btn_pause.clicked.connect(self._pause)
        self.btn_stop.clicked.connect(self._stop)
        self.btn_delete.clicked.connect(self._delete)
        self.btn_refresh.clicked.connect(self.refresh)

    def refresh(self):
        with get_session() as s:
            camps = CampaignRepository(s).all()
            rows = [
                (c.id, c.name, c.status, c.sent_count, c.open_count,
                 c.click_count, c.bounce_count, str(c.created_at)[:16])
                for c in camps
            ]
        self.table.setRowCount(len(rows))
        for i, (cid, name, status, sent, opens, clicks, bounces, created) in enumerate(rows):
            vals = [name, status, str(sent), str(opens), str(clicks), str(bounces), created]
            for j, v in enumerate(vals):
                self.table.setItem(i, j, QTableWidgetItem(v))
            self.table.item(i, 0).setData(Qt.ItemDataRole.UserRole, cid)

    def _selected_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _new_campaign(self):
        dlg = CampaignWizard(parent=self)
        if dlg.exec():
            with get_session() as s:
                CampaignRepository(s).create(dlg.data())
            self.refresh()

    def _start(self):
        cid = self._selected_id()
        if not cid:
            return
        if cid in self._workers:
            QMessageBox.information(self, "Running", "Campaign already running.")
            return
        worker = SendWorker(cid, parent=self)
        self._workers[cid] = worker
        worker.start()

    def _pause(self):
        cid = self._selected_id()
        if cid and cid in self._workers:
            self._workers[cid].pause()

    def _stop(self):
        cid = self._selected_id()
        if cid and cid in self._workers:
            self._workers.pop(cid).stop()
            self.refresh()

    def _delete(self):
        cid = self._selected_id()
        if not cid:
            return
        if QMessageBox.question(self, "Delete", "Delete this campaign?") == QMessageBox.StandardButton.Yes:
            with get_session() as s:
                CampaignRepository(s).delete(cid)
            self.refresh()

    def _append_log(self, line: str):
        self.log_view.append(line)
        self.log_view.verticalScrollBar().setValue(
            self.log_view.verticalScrollBar().maximum()
        )

    def _on_progress(self, campaign_id: int, sent: int, email: str):
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.data(Qt.ItemDataRole.UserRole) == campaign_id:
                self.table.setItem(row, 2, QTableWidgetItem(str(sent)))
                break
