import os
import shutil
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
                               QPushButton, QComboBox, QLabel)
from PySide6.QtCore import QTimer
from src import constants as c
from src.utils.logger import logger
from src.utils.dialogs import ask_save_filename_native


class LogsTab(QWidget):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._live_timer = QTimer(self)
        self._live_timer.setInterval(2000)
        self._user_scrolled_away = False
        self._current_log_name = None
        self._log_dir = os.path.join(
            os.path.expanduser("~"), ".local/share/mcpelauncher/logs"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 10)

        header = QHBoxLayout()

        indicator = QLabel("●")
        indicator.setStyleSheet("font-size: 14px; color: #888;")
        indicator.setFixedWidth(16)
        self._indicator = indicator
        header.addWidget(indicator)

        self._title_label = QLabel(c.t("UI_LOG_VIEWER_LABEL"))
        self._title_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        header.addWidget(self._title_label)
        header.addStretch()

        self._combo = QComboBox()
        header.addWidget(self._combo)

        self._export_btn = QPushButton(c.t("UI_BUTTON_EXPORT_LOG"))
        self._export_btn.clicked.connect(self._export_log)
        header.addWidget(self._export_btn)

        layout.addLayout(header)

        self._text = QTextEdit()
        self._text.setReadOnly(True)
        layout.addWidget(self._text, 1)

        self._combo.currentIndexChanged.connect(self._on_log_change)
        self._text.verticalScrollBar().valueChanged.connect(self._on_scroll)

        self._live_timer.timeout.connect(self._refresh_live_log)

        self._refresh_log_list()

    def _refresh_log_list(self):
        self._combo.blockSignals(True)
        self._combo.clear()
        self._current_log_name = (
            os.path.basename(logger.log_file) if logger.log_file else None
        )
        log_files = []
        if os.path.isdir(self._log_dir):
            for f in os.listdir(self._log_dir):
                if f.startswith("cianovalauncher-") and f.endswith(".log"):
                    log_files.append(f)
            log_files.sort(reverse=True)
        for f in log_files:
            self._combo.addItem(f)
        self._combo.blockSignals(False)

        if log_files:
            idx = 0
            if self._current_log_name and self._current_log_name in log_files:
                idx = log_files.index(self._current_log_name)
            self._combo.setCurrentIndex(idx)
            self._load_log(self._combo.currentText())
            self._live_timer.start()

        self._update_indicator()

    def _load_log(self, fname):
        path = os.path.join(self._log_dir, fname)
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
                scroll_at_end = self._is_at_end()
                self._text.setPlainText(content)
                if not self._user_scrolled_away or scroll_at_end:
                    self._scroll_to_end()
        except Exception as e:
            self._text.setPlainText(f"Error reading log: {e}")

    def _on_log_change(self, idx):
        if idx >= 0 and idx < self._combo.count():
            self._user_scrolled_away = False
            self._load_log(self._combo.currentText())
            self._update_indicator()

    def _on_scroll(self, value):
        sb = self._text.verticalScrollBar()
        if sb.maximum() > 0:
            self._user_scrolled_away = value < sb.maximum()

    def _is_at_end(self):
        sb = self._text.verticalScrollBar()
        return sb.maximum() <= 0 or sb.value() >= sb.maximum()

    def _scroll_to_end(self):
        sb = self._text.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _refresh_live_log(self):
        if not self.isVisible():
            return
        sel = self._combo.currentText()
        if sel and sel == self._current_log_name:
            self._load_log(sel)

    def _update_indicator(self):
        sel = self._combo.currentText()
        is_live = sel and sel == self._current_log_name
        self._indicator.setStyleSheet(
            f"font-size: 14px; color: {'#4ade80' if is_live else '#888'};"
        )
        self._indicator.setToolTip(
            "Log activo — sesión actual" if is_live else "Log inactivo — sesión anterior"
        )

    def retranslate_ui(self):
        self._title_label.setText(c.t("UI_LOG_VIEWER_LABEL"))
        self._export_btn.setText(c.t("UI_BUTTON_EXPORT_LOG"))

    def _export_log(self):
        fname = self._combo.currentText()
        if not fname:
            return
        src = os.path.join(self._log_dir, fname)
        dst = ask_save_filename_native(
            self,
            title=c.t("UI_EXPORT_LOG_TITLE"),
            filetypes=[("Log Files", "*.log"), (c.t("UI_ALL_FILES_TYPE"), "*.*")],
            default_name=fname,
        )
        if dst:
            try:
                shutil.copy2(src, dst)
            except Exception as e:
                from src.gui import custom_dialogs as mbox
                mbox.showerror(self, c.t("UI_ERROR_TITLE"), f"Error exporting log: {e}")
