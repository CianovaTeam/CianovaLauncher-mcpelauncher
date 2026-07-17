import os
import subprocess
import shutil
from src import constants as c
from src.gui import custom_dialogs as messagebox
from src.utils.process_utils import host_command


def verify_dependencies(app):
    """Check for missing package dependencies and show results."""
    if app.running_in_flatpak:
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QLabel, QHBoxLayout
        d = QDialog(app)
        d.setWindowTitle(c.t("UI_FLATPAK_RUNTIME_INFO_TITLE"))
        d.resize(650, 500)
        l = QVBoxLayout(d)
        l.addWidget(QLabel("<b>Flatpak Runtimes Requeridos:</b>"))

        t_req = QTextEdit()
        t_req.setPlainText("\n".join(c.FLATPAK_REQUIRED_RUNTIMES))
        l.addWidget(t_req)

        l.addWidget(QLabel("<b>Detección Actual:</b>"))
        t_det = QTextEdit()
        t_det.setReadOnly(True)
        try:
            res = subprocess.check_output(
                host_command(["flatpak", "list", "--runtime"]), text=True
            )
            t_det.setPlainText(res)
        except Exception:
            t_det.setPlainText("Error al obtener lista de runtimes del host.")
        l.addWidget(t_det)

        btn_row = QHBoxLayout()
        b_save = QPushButton("Actualizar Lista")

        def update_list():
            new_list = t_req.toPlainText().strip().split('\n')
            c.FLATPAK_REQUIRED_RUNTIMES = [x.strip() for x in new_list if x.strip()]
            messagebox.showinfo(d, "Éxito", "Lista de runtimes actualizada (en memoria).")

        b_save.clicked.connect(update_list)
        btn_row.addWidget(b_save)

        b_close = QPushButton(c.t("UI_BUTTON_CLOSE"))
        b_close.clicked.connect(d.accept)
        btn_row.addWidget(b_close)
        l.addLayout(btn_row)

        d.exec()
        return

    manager_map = {
        "APT": (["dpkg", "-s"], "apt install -y"),
        "DNF": (["rpm", "-q"], "dnf install -y"),
        "PACMAN": (["pacman", "-Q"], "pacman -S --noconfirm --needed"),
    }
    detected = next((m for m in manager_map if shutil.which(m.lower())), None)
    if not detected:
        messagebox.showerror(app, c.t("UI_ERROR_TITLE"), c.t("UI_PKG_MANAGER_NOT_SUPPORTED"))
        return

    check_cmd, install_cmd = manager_map[detected]
    pkgs = sorted(list(set(c.DEPENDENCY_MAP[detected])))
    from src.gui.progress_dialog import ProgressDialog
    from src.core.worker import LogicWorker
    app._prog = ProgressDialog(app, c.t("UI_VERIFYING_TITLE"), c.t("UI_STARTING_MSG"))
    app._prog.show()

    def task():
        return [p for p in pkgs if subprocess.call(check_cmd + [p], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) != 0]

    app._worker = LogicWorker(task)
    app._worker.finished.connect(lambda missing: [app._prog.accept(), show_dep_results(app, missing, install_cmd)])
    app._worker.error.connect(lambda e: [app._prog.accept(), messagebox.showerror(app, c.t("UI_ERROR_TITLE"), e)])
    app._worker.start()


def show_dep_results(app, missing, icmd):
    """Display missing dependencies and offer to install them with elevated privileges."""
    if not missing:
        messagebox.showinfo(app, c.t("UI_RESULT_TITLE"), c.t("UI_DEPENDENCIES_OK"))
        return
    from PySide6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QLabel
    d = QDialog(app)
    d.setWindowTitle(c.t("UI_MISSING_DEPS_TITLE"))
    l = QVBoxLayout(d)
    l.addWidget(QLabel(c.t("UI_MISSING_DEPS_MSG")))
    t = QTextEdit()
    t.setPlainText("\n".join(missing))
    l.addWidget(t)

    def install():
        cmd = f"pkexec {icmd} {' '.join(missing)}"
        if messagebox.askyesno(d, c.t("UI_INFO_TITLE"), c.t("UI_INSTALL_PROMPT", full_cmd=cmd)):
            term = next((t for t in ["gnome-terminal", "konsole", "xfce4-terminal", "xterm"] if shutil.which(t)), None)
            if term:
                subprocess.Popen([term, "-e", f'bash -c "{cmd}; read -p OK"'])
            d.accept()

    b = QPushButton(c.t("UI_BUTTON_INSTALL_ROOT"))
    b.clicked.connect(install)
    l.addWidget(b)
    d.exec()
