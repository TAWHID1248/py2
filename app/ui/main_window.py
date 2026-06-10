from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QStatusBar, QMessageBox,
)
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt
from app.ui.panels.dashboard_panel import DashboardPanel
from app.ui.panels.accounts_panel import AccountsPanel
from app.ui.panels.contacts_panel import ContactsPanel
from app.ui.panels.templates_panel import TemplatesPanel
from app.ui.panels.composer_panel import ComposerPanel
from app.ui.panels.campaigns_panel import CampaignsPanel
from app.ui.panels.reports_panel import ReportsPanel
from app.core.event_bus import bus


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BM2Ultra — Email Marketing Platform")
        self.setMinimumSize(1150, 720)
        self._build_menu()
        self._build_tabs()
        self._build_status_bar()
        bus.log_line.connect(self._status_message)
        bus.send_progress.connect(self._on_send_progress)

    def _build_menu(self):
        mb = self.menuBar()

        file_menu = mb.addMenu("File")
        act_settings = QAction("Settings…", self)
        act_settings.triggered.connect(self._open_settings)
        act_exit = QAction("Exit", self)
        act_exit.triggered.connect(self.close)
        file_menu.addAction(act_settings)
        file_menu.addSeparator()
        file_menu.addAction(act_exit)

        tools_menu = mb.addMenu("Tools")
        act_import = QAction("Import Contacts…", self)
        act_import.triggered.connect(self._quick_import)
        act_nltk = QAction("Download NLTK WordNet…", self)
        act_nltk.triggered.connect(self._download_nltk)
        tools_menu.addAction(act_import)
        tools_menu.addAction(act_nltk)

        help_menu = mb.addMenu("Help")
        act_about = QAction("About BM2Ultra", self)
        act_about.triggered.connect(self._about)
        help_menu.addAction(act_about)

    def _build_tabs(self):
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.West)

        self.dashboard  = DashboardPanel()
        self.accounts   = AccountsPanel()
        self.contacts   = ContactsPanel()
        self.templates  = TemplatesPanel()
        self.composer   = ComposerPanel()
        self.campaigns  = CampaignsPanel()
        self.reports    = ReportsPanel()

        self.tabs.addTab(self.dashboard,  "Dashboard")
        self.tabs.addTab(self.accounts,   "Accounts")
        self.tabs.addTab(self.contacts,   "Contacts")
        self.tabs.addTab(self.templates,  "Templates")
        self.tabs.addTab(self.composer,   "Composer")
        self.tabs.addTab(self.campaigns,  "Campaigns")
        self.tabs.addTab(self.reports,    "Reports")

        self.setCentralWidget(self.tabs)

    def _build_status_bar(self):
        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status.showMessage("Ready — BM2Ultra Phase 2")

    def _status_message(self, msg: str):
        self._status.showMessage(msg, 6000)

    def _on_send_progress(self, campaign_id: int, sent: int, email: str):
        self._status.showMessage(f"Sending campaign {campaign_id}: {sent} sent — last: {email}", 4000)

    def _open_settings(self):
        from app.ui.dialogs.settings_dialog import SettingsDialog
        dlg = SettingsDialog(parent=self)
        if dlg.exec():
            dlg.apply()

    def _quick_import(self):
        self.tabs.setCurrentWidget(self.contacts)
        self.contacts._import()

    def _download_nltk(self):
        from app.services.content.spinner_service import download_nltk_data
        download_nltk_data()
        QMessageBox.information(
            self, "NLTK", "WordNet download started in background.\nCheck logs for status."
        )

    def _about(self):
        QMessageBox.about(
            self,
            "About BM2Ultra",
            "<b>BM2Ultra v1.0 — Phase 2</b><br>"
            "Bulk Email Marketing Platform<br><br>"
            "Python · PySide6 · SQLAlchemy · FastAPI<br>"
            "Gmail OAuth2 · Spintax · WordNet · APScheduler",
        )
