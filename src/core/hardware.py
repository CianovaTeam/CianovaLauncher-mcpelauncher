import os
import re
import subprocess
import platform
from src import constants as c
from src.gui import custom_dialogs as messagebox


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
        gl_ver = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        if app.running_in_flatpak:
            try:
                cmd = ["flatpak-spawn", "--host", "sh", "-c", "glxinfo | grep 'OpenGL ES profile version'"]
                gl_ver = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL).strip()
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
    return c.UI_INCOMPATIBLE_TEXT


def get_compatibility_range(app):
    """Retorna el rango de compatibilidad de hardware para MC Bedrock."""
    arch, cpu_flags = _detect_cpu_flags()
    gl_ver = _detect_gl_version(app)
    return _compute_compatibility(arch, cpu_flags, gl_ver)


def check_requirements_dialog(app):
    """Analiza hardware y muestra resultado en diálogo."""
    from src.gui.progress_dialog import ProgressDialog
    from src.core.app_logic import LogicWorker
    app._prog = ProgressDialog(app, c.UI_ANALYZING_TITLE, c.UI_ANALYZING_HW_MSG)
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

        return (f"--- {c.UI_HW_CPU_INFO} ---\n" +
                f"{c.UI_HW_MODEL}: {cpu}\n" +
                c.UI_HW_ARCH.format(arch=arch) +
                c.UI_HW_CPU_EXT.format(status='✅' if has_sse else '⚠️') +
                f"\n--- {c.UI_HW_RAM_INFO} ---\n" +
                f"{c.UI_HW_RAM_TOTAL}: {ram}\n" +
                f"\n--- {c.UI_HW_GPU_INFO} ---\n" +
                c.UI_HW_OPENGL_ES.format(gl_ver=gl_ver) +
                f"\n----------------------------\n" +
                f"{c.UI_HARDWARE_ANALYSIS_RECOMMENDATION.format(compat_ver=compat_ver)}")

    app._worker = LogicWorker(task)
    app._worker.finished.connect(lambda res: [app._prog.accept(), show_hw_results(app, res)])
    app._worker.error.connect(lambda e: [app._prog.accept(), messagebox.showerror(app, c.UI_ERROR_TITLE, e)])
    app._worker.start()


def show_hw_results(app, txt):
    from PySide6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton
    d = QDialog(app)
    d.setWindowTitle(c.UI_HARDWARE_ANALYSIS_TITLE)
    l = QVBoxLayout(d)
    t = QTextEdit()
    t.setPlainText(txt)
    t.setReadOnly(True)
    l.addWidget(t)
    b = QPushButton(c.UI_BUTTON_CLOSE)
    b.clicked.connect(d.accept)
    l.addWidget(b)
    d.exec()
