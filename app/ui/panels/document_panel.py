"""Document Generation panel — PDF template editor, Word template manager, image tools."""
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QPushButton, QLabel,
    QTextEdit, QLineEdit, QFileDialog, QMessageBox, QComboBox,
    QGroupBox, QFormLayout, QSpinBox, QCheckBox, QSplitter,
)
from PySide6.QtCore import Qt
from app.core.config import settings


class _PDFTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(
            "Design a reusable PDF template. Use {first_name}, {last_name}, {company}, "
            "{email}, {custom1}…{custom5} merge fields."
        ))

        top = QHBoxLayout()
        self.btn_preview = QPushButton("Preview PDF")
        self.btn_save    = QPushButton("Save Template")
        self.btn_load    = QPushButton("Load Template")
        self.btn_test    = QPushButton("Generate Test PDF")
        for b in [self.btn_preview, self.btn_save, self.btn_load, self.btn_test]:
            top.addWidget(b)
        top.addStretch()
        layout.addLayout(top)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.html_editor = QTextEdit()
        self.html_editor.setPlaceholderText(
            "<!DOCTYPE html>\n<html><body>\n"
            "<h1>Hello, {first_name}!</h1>\n"
            "<p>Company: {company}</p>\n"
            "</body></html>"
        )
        splitter.addWidget(self.html_editor)

        # Preview pane
        try:
            from PySide6.QtWebEngineWidgets import QWebEngineView
            self._preview = QWebEngineView()
            splitter.addWidget(self._preview)
            self.btn_preview.clicked.connect(self._render_preview)
        except ImportError:
            self._preview = QTextEdit()
            self._preview.setReadOnly(True)
            splitter.addWidget(self._preview)
            self.btn_preview.setEnabled(False)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)

        self.btn_save.clicked.connect(self._save)
        self.btn_load.clicked.connect(self._load)
        self.btn_test.clicked.connect(self._test_pdf)

        self._tmpl_dir = settings.templates_dir / "pdf"
        self._tmpl_dir.mkdir(parents=True, exist_ok=True)

    def get_html(self) -> str:
        return self.html_editor.toPlainText()

    def _render_preview(self):
        try:
            self._preview.setHtml(self.html_editor.toPlainText())
        except Exception:
            pass

    def _save(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save PDF Template", str(self._tmpl_dir), "HTML (*.html)"
        )
        if path:
            Path(path).write_text(self.html_editor.toPlainText(), encoding="utf-8")
            QMessageBox.information(self, "Saved", f"Saved: {path}")

    def _load(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Load PDF Template", str(self._tmpl_dir), "HTML (*.html)"
        )
        if path:
            self.html_editor.setPlainText(Path(path).read_text(encoding="utf-8"))

    def _test_pdf(self):
        from app.services.document.pdf_service import html_to_pdf
        from app.models.contact import Contact

        # use a dummy contact for preview
        dummy = Contact()
        dummy.id = 0
        dummy.email = "test@example.com"
        dummy.first_name = "Jane"
        dummy.last_name = "Doe"
        dummy.company = "ACME Corp"

        from app.services.content.personalization import render
        html = render(self.html_editor.toPlainText(), dummy)

        out = settings.attachments_dir / "test_preview.pdf"
        try:
            html_to_pdf(html, out)
            QMessageBox.information(self, "Generated", f"PDF saved to:\n{out}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))


class _WordTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Select a .docx Word template file. Use {first_name}, {company}, etc. "
            "as merge fields inside your Word document."
        ))

        form = QFormLayout()
        path_row = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setReadOnly(True)
        btn_browse = QPushButton("Browse…")
        btn_browse.clicked.connect(self._browse)
        path_row.addWidget(self.path_edit)
        path_row.addWidget(btn_browse)
        form.addRow("Template File:", path_row)
        layout.addLayout(form)

        btn_bar = QHBoxLayout()
        self.btn_test = QPushButton("Generate Test Document")
        self.btn_test.clicked.connect(self._test_word)
        btn_bar.addWidget(self.btn_test)
        btn_bar.addStretch()
        layout.addLayout(btn_bar)

        layout.addStretch()

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Word Template", str(settings.templates_dir), "Word (*.docx)"
        )
        if path:
            self.path_edit.setText(path)

    def template_path(self) -> str:
        return self.path_edit.text()

    def _test_word(self):
        tmpl = self.path_edit.text()
        if not tmpl:
            QMessageBox.warning(self, "Missing", "Select a template file first.")
            return
        from app.models.contact import Contact
        from app.services.document.word_service import fill_template

        dummy = Contact()
        dummy.id = 0
        dummy.email = "test@example.com"
        dummy.first_name = "Jane"
        dummy.last_name = "Doe"
        dummy.company = "ACME Corp"

        out = settings.attachments_dir / "test_word.docx"
        try:
            fill_template(Path(tmpl), dummy, out)
            QMessageBox.information(self, "Generated", f"Word doc saved to:\n{out}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))


class _ImageTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Image manipulation tools — Pillow + Wand"))

        grp_resize = QGroupBox("Resize Image")
        rf = QFormLayout(grp_resize)
        self.img_src = QLineEdit()
        self.img_src.setReadOnly(True)
        btn_src = QPushButton("Browse…")
        btn_src.clicked.connect(lambda: self._browse_img(self.img_src))
        row = QHBoxLayout()
        row.addWidget(self.img_src)
        row.addWidget(btn_src)
        rf.addRow("Source:", row)
        self.resize_w = QSpinBox(); self.resize_w.setRange(1, 9999); self.resize_w.setValue(800)
        self.resize_h = QSpinBox(); self.resize_h.setRange(1, 9999); self.resize_h.setValue(600)
        rf.addRow("Width:", self.resize_w)
        rf.addRow("Height:", self.resize_h)
        btn_resize = QPushButton("Resize")
        btn_resize.clicked.connect(self._do_resize)
        rf.addRow("", btn_resize)
        layout.addWidget(grp_resize)

        grp_fx = QGroupBox("Apply Effect (requires ImageMagick)")
        ff = QFormLayout(grp_fx)
        self.fx_src = QLineEdit(); self.fx_src.setReadOnly(True)
        btn_fx_src = QPushButton("Browse…")
        btn_fx_src.clicked.connect(lambda: self._browse_img(self.fx_src))
        row2 = QHBoxLayout(); row2.addWidget(self.fx_src); row2.addWidget(btn_fx_src)
        ff.addRow("Source:", row2)
        self.effect_combo = QComboBox()
        self.effect_combo.addItems(["blur", "sharpen", "grayscale", "sepia", "emboss"])
        ff.addRow("Effect:", self.effect_combo)
        btn_fx = QPushButton("Apply")
        btn_fx.clicked.connect(self._do_effect)
        ff.addRow("", btn_fx)
        layout.addWidget(grp_fx)
        layout.addStretch()

    def _browse_img(self, target: QLineEdit):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Image", "", "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if path:
            target.setText(path)

    def _do_resize(self):
        src = self.img_src.text()
        if not src:
            QMessageBox.warning(self, "Missing", "Select a source image.")
            return
        from app.services.document.image_service import resize
        src_p = Path(src)
        out = src_p.parent / f"{src_p.stem}_resized{src_p.suffix}"
        try:
            resize(src_p, self.resize_w.value(), self.resize_h.value(), out)
            QMessageBox.information(self, "Done", f"Saved: {out}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _do_effect(self):
        src = self.fx_src.text()
        if not src:
            QMessageBox.warning(self, "Missing", "Select a source image.")
            return
        from app.services.document.image_service import apply_effect
        src_p = Path(src)
        fx = self.effect_combo.currentText()
        out = src_p.parent / f"{src_p.stem}_{fx}{src_p.suffix}"
        try:
            apply_effect(src_p, fx, out)
            QMessageBox.information(self, "Done", f"Saved: {out}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))


class DocumentPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        tabs = QTabWidget()
        self.pdf_tab   = _PDFTab()
        self.word_tab  = _WordTab()
        self.image_tab = _ImageTab()
        tabs.addTab(self.pdf_tab,   "PDF Templates")
        tabs.addTab(self.word_tab,  "Word Templates")
        tabs.addTab(self.image_tab, "Image Tools")
        layout.addWidget(tabs)
