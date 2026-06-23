import os
import re
import subprocess
import platform
import shutil
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QFrame
from src import constants as c
from src.gui import custom_dialogs as messagebox
from src.utils.logger import logger


def _detect_cpu_flags():
    """Retorna (arch, cpu_flags) desde /proc/cpuinfo."""
    arch = platform.machine()
    cpu_flags = []
    try:
        if os.path.exists("/proc/cpuinfo"):
            with open("/proc/cpuinfo") as f:
                content = f.read()
                m_flags = re.search(r"flags\s*:\s*(.*)", content)
                if m_flags:
                    cpu_flags = m_flags.group(1).split()
    except Exception:
        pass
    return arch, cpu_flags


def _detect_gl_version(app):
    """Retorna string de OpenGL ES profile version via glxinfo."""
    gl_ver = "Unknown"
    try:
        cmd = ["sh", "-c", "glxinfo | grep 'OpenGL ES profile version'"]
        gl_ver = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL, timeout=10).strip()
    except Exception:
        if app.running_in_flatpak:
            try:
                cmd = ["flatpak-spawn", "--host", "sh", "-c", "glxinfo | grep 'OpenGL ES profile version'"]
                gl_ver = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL, timeout=15).strip()
            except Exception:
                pass
    return gl_ver


def _compute_compatibility(arch, cpu_flags, gl_ver):
    """Retorna string de rango de compatibilidad."""
    has_sse = all(f in cpu_flags for f in ["ssse3", "sse4_1", "sse4_2", "popcnt"])
    if arch == "x86_64" and has_sse:
        if "3.1" in gl_ver or "3.2" in gl_ver:
            return "1.13.0 - 1.21.130+"
        if "3.0" in gl_ver:
            return "1.13.0 - 1.21.124"
        if "2.0" in gl_ver:
            return "1.13.0 - 1.20.20"
    return c.t("UI_INCOMPATIBLE_TEXT")


def get_compatibility_range(app):
    """Retorna el rango de compatibilidad de hardware para MC Bedrock."""
    arch, cpu_flags = _detect_cpu_flags()
    gl_ver = _detect_gl_version(app)
    return _compute_compatibility(arch, cpu_flags, gl_ver)


def check_requirements_dialog(app):
    """Analiza hardware y muestra resultado en diálogo."""
    from src.gui.progress_dialog import ProgressDialog
    from src.core.worker import LogicWorker
    app._prog = ProgressDialog(app, c.t("UI_ANALYZING_TITLE"), c.t("UI_ANALYZING_HW_MSG"))
    app._prog.show()

    def task():
        arch = platform.machine()
        cpu, ram = "Unknown", "Unknown"
        try:
            if os.path.exists("/proc/cpuinfo"):
                with open("/proc/cpuinfo") as f:
                    content = f.read()
                    m_model = re.search(r"model name\s*:\s*(.*)", content)
                    if m_model:
                        cpu = m_model.group(1).strip()
            if os.path.exists("/proc/meminfo"):
                with open("/proc/meminfo") as f:
                    m_mem = re.search(r"MemTotal:\s*(\d+)\s*kB", f.read())
                    if m_mem:
                        ram = f"{int(m_mem.group(1))/1024/1024:.2f} GB"
        except Exception:
            pass

        arch2, cpu_flags = _detect_cpu_flags()
        gl_ver = _detect_gl_version(app)
        compat_ver = _compute_compatibility(arch2, cpu_flags, gl_ver)
        has_sse = all(f in cpu_flags for f in ["ssse3", "sse4_1", "sse4_2", "popcnt"])

        return (f"--- {c.t("UI_HW_CPU_INFO")} ---\n" +
                f"{c.t("UI_HW_MODEL")}: {cpu}\n" +
                c.t("UI_HW_ARCH", arch=arch) +
                c.t("UI_HW_CPU_EXT", status='✅' if has_sse else '⚠️') +
                f"\n--- {c.t("UI_HW_RAM_INFO")} ---\n" +
                f"{c.t("UI_HW_RAM_TOTAL")}: {ram}\n" +
                f"\n--- {c.t("UI_HW_GPU_INFO")} ---\n" +
                c.t("UI_HW_OPENGL_ES", gl_ver=gl_ver) +
                f"\n----------------------------\n" +
                f"{c.t("UI_HARDWARE_ANALYSIS_RECOMMENDATION", compat_ver=compat_ver)}")

    app._worker = LogicWorker(task)
    app._worker.finished.connect(lambda res: [app._prog.accept(), show_hw_results(app, res)])
    app._worker.error.connect(lambda e: [app._prog.accept(), messagebox.showerror(app, c.t("UI_ERROR_TITLE"), e)])
    app._worker.start()


def show_hw_results(app, txt):
    """Display hardware analysis results in a read-only dialog with log viewer."""
    from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTextEdit,
                                   QPushButton, QComboBox, QFileDialog, QLabel)
    d = QDialog(app)
    d.setWindowTitle(c.t("UI_HARDWARE_ANALYSIS_TITLE"))
    d.resize(520, 500)
    l = QVBoxLayout(d)

    # ── Hardware analysis ──
    t = QTextEdit()
    t.setPlainText(txt)
    t.setReadOnly(True)
    l.addWidget(t)

    # ── Log viewer ──
    log_frame = QFrame()
    log_frame.setObjectName("GroupFrame")
    log_layout = QVBoxLayout(log_frame)

    log_header = QHBoxLayout()
    log_label = QLabel(c.t("UI_LOG_VIEWER_LABEL"))
    log_label.setStyleSheet("font-weight: bold;")
    log_header.addWidget(log_label)
    log_header.addStretch()

    log_combo = QComboBox()
    if app.running_in_flatpak:
        log_dir = os.path.join(app.our_data_path, "logs")
    else:
        log_dir = os.path.join(app.compiled_path, "logs")
    current_log = os.path.basename(logger.log_file) if logger.log_file else None
    log_files = []
    if os.path.isdir(log_dir):
        for f in os.listdir(log_dir):
            if f.startswith("cianovalauncher-") and f.endswith(".log"):
                log_files.append(f)
        log_files.sort(reverse=True)
    if current_log:
        log_combo.addItem("🔴 En vivo — log actual", current_log)
    for f in log_files:
        if f == current_log:
            continue
        log_combo.addItem(f)
    log_header.addWidget(log_combo)

    export_btn = QPushButton(c.t("UI_BUTTON_EXPORT_LOG"))
    log_header.addWidget(export_btn)
    log_layout.addLayout(log_header)

    log_view = QTextEdit()
    log_view.setReadOnly(True)
    log_view.setMaximumHeight(180)
    log_layout.addWidget(log_view)

    l.addWidget(log_frame)

    _timer = None
    _showing_current = False

    def load_log(fname):
        nonlocal _showing_current
        _showing_current = False
        if _timer:
            _timer.stop()
        path = os.path.join(log_dir, fname)
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                log_view.setPlainText(f.read())
            log_view.verticalScrollBar().setValue(log_view.verticalScrollBar().maximum())
        except Exception as e:
            log_view.setPlainText(f"Error reading log: {e}")

    def load_current_log():
        nonlocal _showing_current
        _showing_current = True
        if not current_log:
            return
        path = os.path.join(log_dir, current_log)
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                log_view.setPlainText(f.read())
            log_view.verticalScrollBar().setValue(log_view.verticalScrollBar().maximum())
        except Exception:
            pass

    def refresh_current():
        if not _showing_current or not current_log:
            return
        path = os.path.join(log_dir, current_log)
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                log_view.setPlainText(f.read())
            log_view.verticalScrollBar().setValue(log_view.verticalScrollBar().maximum())
        except Exception:
            pass

    def on_log_change(idx):
        if idx < 0 or idx >= log_combo.count():
            return
        if current_log and idx == 0:
            load_current_log()
            if _timer:
                _timer.start(2000)
        else:
            load_log(log_combo.currentText())

    def export_log():
        fname = log_combo.currentData() or log_combo.currentText()
        if not fname:
            return
        src = os.path.join(log_dir, fname)
        dst, _ = QFileDialog.getSaveFileName(d, c.t("UI_EXPORT_LOG_TITLE"), fname,
                                              "Log Files (*.log);;All Files (*)")
        if dst:
            try:
                shutil.copy2(src, dst)
            except Exception as e:
                from src.gui import custom_dialogs as mbox
                mbox.showerror(d, c.t("UI_ERROR_TITLE"), f"Error exporting log: {e}")

    log_combo.currentIndexChanged.connect(on_log_change)
    export_btn.clicked.connect(export_log)

    _timer = QTimer(d)
    _timer.timeout.connect(refresh_current)

    if current_log:
        load_current_log()
        _timer.start(2000)
    elif log_files:
        load_log(log_files[0])

    # ── Close button ──
    b = QPushButton(c.t("UI_BUTTON_CLOSE"))
    b.clicked.connect(d.accept)
    l.addWidget(b)
    d.exec()
