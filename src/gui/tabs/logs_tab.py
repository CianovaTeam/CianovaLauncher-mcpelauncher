import os
import re
import shutil
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
                               QPushButton, QComboBox, QLabel, QFrame)
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
        self._log_dir = logger.default_log_dir()
        self._offsets = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 10)

        header = QHBoxLayout()

        self._indicator = QLabel("●")
        self._indicator.setStyleSheet("font-size: 16px; color: #888;")
        self._indicator.setFixedWidth(20)
        header.addWidget(self._indicator)

        self._hint_label = QLabel("")
        self._hint_label.setStyleSheet("font-size: 12px; font-weight: bold; color: #888;")
        header.addWidget(self._hint_label)

        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("color: rgba(128,128,128,0.4);")
        header.addWidget(sep)

        self._title_label = QLabel(c.t("UI_LOG_VIEWER_LABEL"))
        self._title_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        header.addWidget(self._title_label)
        header.addStretch()

        self._combo = QComboBox()
        self._combo.setMinimumWidth(250)
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

    # ── Helpers ─────────────────────────────────────────────────

    @staticmethod
    def _parse_log_name(fname):
        """Return 'DD/MM/AAAA - HH:MM:SS' from a log filename, or None."""
        m = re.match(
            r"cianovalauncher-(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})\.log", fname
        )
        if not m:
            return None
        y, mo, d, h, mi, s = m.groups()
        return f"{d}/{mo}/{y} - {h}:{mi}:{s}"

    # ── List building ───────────────────────────────────────────

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
            self._offsets.setdefault(f, 0)
            ts = self._parse_log_name(f)
            label = f"● {ts}" if ts else f
            self._combo.addItem(label, f)
        self._combo.blockSignals(False)

        if log_files:
            idx = 0
            if self._current_log_name and self._current_log_name in log_files:
                idx = log_files.index(self._current_log_name)
            self._combo.setCurrentIndex(idx)
            self._load_log(self._combo.currentData())
            self._live_timer.start()

        self._update_indicator()

    # ── Loading ─────────────────────────────────────────────────

    def _load_log(self, fname):
        if not fname:
            return
        if fname == self._current_log_name:
            chunk = self._read_new_chunk(fname)
            if chunk:
                self._append_text(chunk)
            return
        path = os.path.join(self._log_dir, fname)
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            self._offsets[fname] = os.path.getsize(path) if os.path.exists(path) else 0
            scroll_at_end = self._is_at_end()
            self._text.setPlainText(content)
            if not self._user_scrolled_away or scroll_at_end:
                self._scroll_to_end()
        except Exception as e:
            self._text.setPlainText(f"Error reading log: {e}")

    def _read_new_chunk(self, fname):
        """Read only the newly appended bytes since the last poll."""
        path = os.path.join(self._log_dir, fname)
        if not os.path.exists(path):
            return ""
        start = self._offsets.get(fname, 0)
        try:
            size = os.path.getsize(path)
            if size < start:
                start = 0
            if size == start:
                return ""
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                f.seek(start)
                chunk = f.read()
            self._offsets[fname] = size
            return chunk
        except OSError:
            return ""

    def _append_text(self, chunk):
        """Append text without resetting the viewport (no flicker)."""
        was_at_end = self._is_at_end() and not self._user_scrolled_away
        cursor = self._text.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(chunk)
        if was_at_end:
            self._scroll_to_end()

    def _on_log_change(self, idx):
        if idx >= 0 and idx < self._combo.count():
            fname = self._combo.itemData(idx)
            self._user_scrolled_away = False
            self._offsets[fname] = 0
            self._load_log(fname)
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
        sel = self._combo.currentData()
        if sel and sel == self._current_log_name:
            self._load_log(sel)

    # ── Indicator ───────────────────────────────────────────────

    def _update_indicator(self):
        fname = self._combo.currentData()
        is_live = bool(fname) and fname == self._current_log_name
        if is_live:
            self._indicator.setStyleSheet("font-size: 16px; color: #4ade80;")
            self._hint_label.setText(f"● {c.t('UI_LOG_LIVE_SESSION')}")
        else:
            self._indicator.setStyleSheet("font-size: 16px; color: #888;")
            ts = self._parse_log_name(fname) if fname else None
            if ts:
                self._hint_label.setText(f"● {c.t('UI_LOG_PREV_SESSION')} {ts}")
            else:
                self._hint_label.setText(f"● {c.t('UI_LOG_PREV_SESSION')}")
        self._indicator.setToolTip(self._hint_label.text())

    def retranslate_ui(self):
        self._title_label.setText(c.t("UI_LOG_VIEWER_LABEL"))
        self._export_btn.setText(c.t("UI_BUTTON_EXPORT_LOG"))
        self._update_indicator()

    def _export_log(self):
        fname = self._combo.currentData()
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
