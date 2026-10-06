"""
System dependency and dynamic library verification for Cianova Launcher.
"""
from src.gui import custom_dialogs as messagebox
from src import constants as c


def verify_dependencies(app):
    """Opens the modern dependencies verification and system diagnostics dialog."""
    try:
        from src.gui.dependencies_dialog import DependenciesDialog
        dlg = DependenciesDialog(app)
        dlg.exec()
    except Exception as e:
        messagebox.showerror(app, c.t("UI_ERROR_TITLE"), c.t("UI_DEPS_CHECK_ERROR", error=e))


def show_dep_results(app, missing=None, icmd=None):
    """Backwards compatibility: redirects to verify_dependencies."""
    verify_dependencies(app)

