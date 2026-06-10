"""HTML composer — QWebEngineView + TinyMCE, with plain-text fallback."""
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTextEdit, QSplitter, QMessageBox,
)
from PySide6.QtCore import Qt, QUrl

_EDITOR_HTML = Path(__file__).parent.parent / "resources" / "editor" / "index.html"
_TINYMCE_JS = _EDITOR_HTML.parent / "tinymce" / "tinymce.min.js"

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
    _HAS_WE = True
except ImportError:
    _HAS_WE = False


class ComposerPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._web: "QWebEngineView | None" = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        toolbar = QHBoxLayout()
        self.btn_get = QPushButton("Get HTML")
        self.btn_clear = QPushButton("Clear")
        self.btn_preview = QPushButton("Preview")
        toolbar.addWidget(self.btn_get)
        toolbar.addWidget(self.btn_clear)
        toolbar.addWidget(self.btn_preview)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        if _HAS_WE and _TINYMCE_JS.exists():
            self._web = QWebEngineView()
            self._web.load(QUrl.fromLocalFile(str(_EDITOR_HTML)))
            layout.addWidget(self._web)
            self.btn_get.clicked.connect(self._get_html_web)
            self.btn_clear.clicked.connect(lambda: self.set_html(""))
            self.btn_preview.clicked.connect(self._preview_web)
        else:
            # Plain-text fallback — fully functional for templates
            if _HAS_WE and not _TINYMCE_JS.exists():
                notice = QLabel(
                    "TinyMCE not found. Download the self-hosted TinyMCE package and extract "
                    "it as <b>tinymce/</b> inside app/ui/resources/editor/. "
                    "Using plain-text editor until then."
                )
                notice.setWordWrap(True)
                notice.setStyleSheet("color:#f38ba8; padding:6px;")
                layout.addWidget(notice)

            self._editor = QTextEdit()
            self._editor.setPlaceholderText(
                "Write your HTML here.\n\n"
                "Merge fields: {first_name} {last_name} {company} {email} {custom1}…{custom5}\n"
                "Spintax:      {Hello|Hi|Hey} {first_name}!\n"
                "Plain HTML is fine — paste from any email builder."
            )
            layout.addWidget(self._editor)

            self.btn_get.clicked.connect(
                lambda: QMessageBox.information(self, "HTML", self._editor.toPlainText())
            )
            self.btn_clear.clicked.connect(self._editor.clear)
            self.btn_preview.clicked.connect(self._preview_plain)

    def get_html(self) -> str:
        if self._web:
            result = []
            self._web.page().runJavaScript(
                "typeof tinymce !== 'undefined' ? tinymce.activeEditor.getContent() : document.body.innerHTML;",
                lambda v: result.append(v or ""),
            )
            # runJavaScript is async — for synchronous callers use plain editor
            return result[0] if result else ""
        return self._editor.toPlainText() if hasattr(self, "_editor") else ""

    def set_html(self, html: str):
        if self._web:
            escaped = html.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")
            self._web.page().runJavaScript(
                f"if(typeof tinymce!=='undefined') tinymce.activeEditor.setContent(`{escaped}`);"
            )
        elif hasattr(self, "_editor"):
            self._editor.setPlainText(html)

    def _get_html_web(self):
        self._web.page().runJavaScript(
            "tinymce.activeEditor.getContent();",
            lambda v: QMessageBox.information(self, "HTML", v or "(empty)"),
        )

    def _preview_web(self):
        self._web.page().runJavaScript(
            "tinymce.activeEditor.getContent();",
            self._open_preview,
        )

    def _preview_plain(self):
        self._open_preview(self._editor.toPlainText())

    def _open_preview(self, html: str):
        from PySide6.QtWidgets import QDialog
        dlg = QDialog(self)
        dlg.setWindowTitle("Preview")
        dlg.resize(700, 500)
        v = QVBoxLayout(dlg)
        if _HAS_WE:
            w = QWebEngineView()
            w.setHtml(html)
            v.addWidget(w)
        else:
            te = QTextEdit()
            te.setReadOnly(True)
            te.setHtml(html)
            v.addWidget(te)
        dlg.exec()
