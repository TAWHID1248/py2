from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QFrame, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QSplitter,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from app.core.database import get_session
from app.models.campaign import Campaign
from app.models.contact import Contact
from app.models.account import Account
from app.core.event_bus import bus

try:
    from PySide6.QtCharts import QChart, QChartView, QBarSet, QBarSeries, QBarCategoryAxis, QValueAxis
    _HAS_CHARTS = True
except ImportError:
    _HAS_CHARTS = False


class _StatCard(QFrame):
    def __init__(self, title: str, color: str = "#89b4fa", parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumSize(160, 90)
        layout = QVBoxLayout(self)
        self.value_label = QLabel("0")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = self.value_label.font()
        font.setPointSize(26)
        font.setBold(True)
        self.value_label.setFont(font)
        self.value_label.setStyleSheet(f"color:{color};")
        self.title_label = QLabel(title)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.value_label)
        layout.addWidget(self.title_label)

    def set_value(self, v: int):
        self.value_label.setText(f"{v:,}")


class DashboardPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self.refresh()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)
        self._timer.start(15_000)
        bus.send_complete.connect(lambda _: self.refresh())
        bus.send_progress.connect(lambda *_: self._tick())

    def _build_ui(self):
        layout = QVBoxLayout(self)

        header_row = QHBoxLayout()
        title = QLabel("Dashboard")
        f = title.font(); f.setPointSize(15); f.setBold(True); title.setFont(f)
        header_row.addWidget(title)
        header_row.addStretch()
        btn = QPushButton("Refresh")
        btn.clicked.connect(self.refresh)
        header_row.addWidget(btn)
        layout.addLayout(header_row)

        # Stat cards
        grid = QGridLayout()
        grid.setSpacing(12)
        self.card_campaigns = _StatCard("Campaigns", "#89b4fa")
        self.card_contacts  = _StatCard("Contacts",  "#a6e3a1")
        self.card_accounts  = _StatCard("Accounts",  "#cba6f7")
        self.card_sent      = _StatCard("Emails Sent","#89dceb")
        self.card_opens     = _StatCard("Opens",     "#a6e3a1")
        self.card_clicks    = _StatCard("Clicks",    "#f9e2af")
        grid.addWidget(self.card_campaigns, 0, 0)
        grid.addWidget(self.card_contacts,  0, 1)
        grid.addWidget(self.card_accounts,  0, 2)
        grid.addWidget(self.card_sent,      1, 0)
        grid.addWidget(self.card_opens,     1, 1)
        grid.addWidget(self.card_clicks,    1, 2)
        layout.addLayout(grid)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Campaign stats table
        self.camp_table = QTableWidget(0, 6)
        self.camp_table.setHorizontalHeaderLabels(
            ["Campaign", "Status", "Sent", "Opens", "Clicks", "Open %"]
        )
        self.camp_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.camp_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.camp_table.setAlternatingRowColors(True)
        splitter.addWidget(self.camp_table)

        # Bar chart (requires QtCharts)
        if _HAS_CHARTS:
            self._chart_view = self._build_chart()
            splitter.addWidget(self._chart_view)
        else:
            splitter.addWidget(QLabel("Install PySide6-Charts for graphs"))

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)

    def _build_chart(self):
        self._bar_sent   = QBarSet("Sent");   self._bar_sent.setColor(QColor("#89dceb"))
        self._bar_opens  = QBarSet("Opens");  self._bar_opens.setColor(QColor("#a6e3a1"))
        self._bar_clicks = QBarSet("Clicks"); self._bar_clicks.setColor(QColor("#f9e2af"))

        self._series = QBarSeries()
        self._series.append(self._bar_sent)
        self._series.append(self._bar_opens)
        self._series.append(self._bar_clicks)

        chart = QChart()
        chart.addSeries(self._series)
        chart.setTitle("Campaign Performance")
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        chart.setBackgroundBrush(QColor("#181825"))
        chart.setTitleBrush(QColor("#cdd6f4"))

        self._axis_x = QBarCategoryAxis()
        self._axis_y = QValueAxis()
        chart.addAxis(self._axis_x, Qt.AlignmentFlag.AlignBottom)
        chart.addAxis(self._axis_y, Qt.AlignmentFlag.AlignLeft)
        self._series.attachAxis(self._axis_x)
        self._series.attachAxis(self._axis_y)

        legend = chart.legend()
        legend.setLabelColor(QColor("#cdd6f4"))

        view = QChartView(chart)
        view.setMinimumWidth(300)
        return view

    def refresh(self):
        with get_session() as s:
            campaigns = s.query(Campaign).order_by(Campaign.created_at.desc()).limit(10).all()
            n_contacts = s.query(Contact).count()
            n_accounts = s.query(Account).count()
            total_sent   = sum(c.sent_count   for c in campaigns)
            total_opens  = sum(c.open_count   for c in campaigns)
            total_clicks = sum(c.click_count  for c in campaigns)
            rows = [
                (c.name, c.status, c.sent_count, c.open_count, c.click_count)
                for c in campaigns
            ]

        self.card_campaigns.set_value(len(rows))
        self.card_contacts.set_value(n_contacts)
        self.card_accounts.set_value(n_accounts)
        self.card_sent.set_value(total_sent)
        self.card_opens.set_value(total_opens)
        self.card_clicks.set_value(total_clicks)

        # table
        self.camp_table.setRowCount(len(rows))
        for i, (name, status, sent, opens, clicks) in enumerate(rows):
            pct = f"{opens/sent*100:.1f}%" if sent > 0 else "—"
            for j, v in enumerate([name, status, str(sent), str(opens), str(clicks), pct]):
                item = QTableWidgetItem(v)
                if j == 1:
                    color = {
                        "running": "#a6e3a1", "completed": "#89b4fa",
                        "failed": "#f38ba8", "paused": "#f9e2af",
                    }.get(status, "#cdd6f4")
                    item.setForeground(QColor(color))
                self.camp_table.setItem(i, j, item)

        # chart
        if _HAS_CHARTS and len(rows) > 0:
            names = [r[0][:12] for r in rows]
            self._axis_x.clear()
            self._axis_x.append(names)
            self._bar_sent.remove(0, self._bar_sent.count())
            self._bar_opens.remove(0, self._bar_opens.count())
            self._bar_clicks.remove(0, self._bar_clicks.count())
            for _, _, sent, opens, clicks in rows:
                self._bar_sent.append(sent)
                self._bar_opens.append(opens)
                self._bar_clicks.append(clicks)
            mx = max((r[2] for r in rows), default=1)
            self._axis_y.setRange(0, max(mx, 1))

    def _tick(self):
        # lightweight update during active send — just refresh the table row
        self.refresh()
