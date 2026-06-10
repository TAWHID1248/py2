from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QListWidget, QListWidgetItem, QSplitter, QLineEdit,
    QLabel, QTextEdit, QMessageBox, QInputDialog,
)
from PySide6.QtCore import Qt
from app.core.database import get_session
from app.repositories.campaign_repository import CampaignRepository
from app.models.template import Template
from sqlalchemy.orm import Session


class TemplatesPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        btn_bar = QHBoxLayout()
        self.btn_new = QPushButton("New Template")
        self.btn_save = QPushButton("Save")
        self.btn_delete = QPushButton("Delete")
        btn_bar.addWidget(self.btn_new)
        btn_bar.addWidget(self.btn_save)
        btn_bar.addWidget(self.btn_delete)
        btn_bar.addStretch()
        layout.addLayout(btn_bar)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.list_widget = QListWidget()
        self.list_widget.setMaximumWidth(250)
        splitter.addWidget(self.list_widget)

        right = QWidget()
        right_layout = QVBoxLayout(right)

        right_layout.addWidget(QLabel("Template Name:"))
        self.name_edit = QLineEdit()
        right_layout.addWidget(self.name_edit)

        right_layout.addWidget(QLabel("Subject:"))
        self.subject_edit = QLineEdit()
        right_layout.addWidget(self.subject_edit)

        right_layout.addWidget(QLabel("HTML Body:"))
        self.html_edit = QTextEdit()
        self.html_edit.setPlaceholderText(
            "HTML content. Use {first_name}, {company}, {custom1}, etc.\n"
            "Spintax: {Hello|Hi|Hey} {first_name}!"
        )
        right_layout.addWidget(self.html_edit, 3)

        right_layout.addWidget(QLabel("Plain Text Fallback:"))
        self.text_edit = QTextEdit()
        self.text_edit.setMaximumHeight(120)
        right_layout.addWidget(self.text_edit)

        splitter.addWidget(right)
        splitter.setStretchFactor(1, 3)
        layout.addWidget(splitter)

        self.list_widget.currentItemChanged.connect(self._on_select)
        self.btn_new.clicked.connect(self._new)
        self.btn_save.clicked.connect(self._save)
        self.btn_delete.clicked.connect(self._delete)

    def refresh(self):
        with get_session() as s:
            templates = s.query(Template).order_by(Template.name).all()
            data = [(t.id, t.name) for t in templates]
        self.list_widget.clear()
        for tid, tname in data:
            item = QListWidgetItem(tname)
            item.setData(Qt.ItemDataRole.UserRole, tid)
            self.list_widget.addItem(item)

    def _on_select(self, item: QListWidgetItem):
        if not item:
            return
        tid = item.data(Qt.ItemDataRole.UserRole)
        with get_session() as s:
            t = s.get(Template, tid)
            if t:
                self.name_edit.setText(t.name)
                self.subject_edit.setText(t.subject)
                self.html_edit.setPlainText(t.html_body or "")
                self.text_edit.setPlainText(t.text_body or "")
                self._current_id = tid

    def _new(self):
        name, ok = QInputDialog.getText(self, "New Template", "Template name:")
        if not ok or not name.strip():
            return
        with get_session() as s:
            t = Template(name=name.strip(), subject="")
            s.add(t)
            s.flush()
            tid = t.id
        self.refresh()
        for i in range(self.list_widget.count()):
            if self.list_widget.item(i).data(Qt.ItemDataRole.UserRole) == tid:
                self.list_widget.setCurrentRow(i)
                break

    def _save(self):
        item = self.list_widget.currentItem()
        if not item:
            return
        tid = item.data(Qt.ItemDataRole.UserRole)
        with get_session() as s:
            t = s.get(Template, tid)
            if t:
                t.name = self.name_edit.text().strip()
                t.subject = self.subject_edit.text().strip()
                t.html_body = self.html_edit.toPlainText()
                t.text_body = self.text_edit.toPlainText()
                item.setText(t.name)
        QMessageBox.information(self, "Saved", "Template saved.")

    def _delete(self):
        item = self.list_widget.currentItem()
        if not item:
            return
        if QMessageBox.question(self, "Delete", "Delete this template?") == QMessageBox.StandardButton.Yes:
            tid = item.data(Qt.ItemDataRole.UserRole)
            with get_session() as s:
                t = s.get(Template, tid)
                if t:
                    s.delete(t)
            self.refresh()
