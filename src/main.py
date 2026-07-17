import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from src.gui.main_window import CianovaLauncherApp
from src.gui.test_window import TestWindow
from src.gui.setup_wizard import SetupWizard
from src import constants as c
from src.core import language_manager
from src.utils.logger import logger
from src.utils.process_utils import is_running_in_flatpak, get_flatpak_app_id

if __name__ == "__main__":
    # --- Pre-App Init (Scaling) ---
    # We need to read scaling before QApplication starts
    ui_scale = "1.0"
    try:
        import json
        # Determine config path (simplified version of CianovaLauncherApp logic)
        home = os.path.expanduser("~")
        if is_running_in_flatpak():
            fid = get_flatpak_app_id() or c.DEFAULT_FLATPAK_ID
            c_path = os.path.join(home, c.FLATPAK_DATA_DIR, fid, "data", c.CONFIG_FILE_NAME)
        else:
            c_path = os.path.join(home, c.LOCAL_SHARE_DIR, c.CONFIG_FILE_NAME)
        
        if os.path.exists(c_path):
            with open(c_path, "r") as f:
                conf = json.load(f)
                ui_scale = str(conf.get("ui_scale", "1.0"))
    except: pass

    if ui_scale != "1.0":
        os.environ["QT_SCALE_FACTOR"] = ui_scale
        os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "0" # Disable auto when manual is set

    app = QApplication(sys.argv)

    # Parse arguments
    launcher_path = os.path.abspath(sys.argv[0])
    force_flatpak_ui = "--force-flatpak-ui" in sys.argv
    force_nvidia_ui = "--force-nvidia-ui" in sys.argv
    test_mode = "--test-mode" in sys.argv

    # Initialize Logger
    # Determine log dir based on environment
    if is_running_in_flatpak():
        fid = get_flatpak_app_id() or c.DEFAULT_FLATPAK_ID
        log_dir = os.path.join(os.path.expanduser("~"), c.FLATPAK_DATA_DIR, fid, c.MCPELAUNCHER_DATA_SUBDIR, "logs")
    else:
        log_dir = os.path.join(os.path.expanduser("~"), c.LOCAL_SHARE_DIR, "logs")
    
    logger.init(log_dir)
    logger.info(f"Launcher started (Path: {launcher_path})")

    if test_mode:
        window = TestWindow()
        window.show()
        sys.exit(app.exec())

    # Create app instance (this loads config)
    window = CianovaLauncherApp(launcher_path=launcher_path, force_flatpak_ui=force_flatpak_ui, force_nvidia_ui=force_nvidia_ui)

    # --- Factory Reset Argument ---
    if "--factory-reset" in sys.argv:
        from src.gui import custom_dialogs as messagebox
        if messagebox.askyesno(window, "Factory Reset", "¿Deseas borrar toda la configuración y restaurar los valores de fábrica?"):
            config_path = window.config_manager.config_file
            try:
                if os.path.exists(config_path):
                    os.remove(config_path)
                    logger.info(f"Config deleted successfully: {config_path}")
                sys.exit(0)
            except Exception as e:
                logger.error(f"Error during factory reset: {e}")
                sys.exit(1)
        else:
            sys.exit(0)

    # Initial setup logic (for old migration)
    if not window.config_manager.get(c.CONFIG_KEY_INITIAL_SETUP_COMPLETE, False):
        logger.info("First run detected, running initial migration check...")
        if window.running_in_flatpak:
            own_path_versions = os.path.join(window.our_data_path, c.VERSIONS_DIR)
            shared_path_versions = os.path.join(os.path.expanduser("~"), c.LOCAL_SHARE_DIR, c.VERSIONS_DIR)

            if os.path.exists(own_path_versions):
                window.config_manager.set(c.CONFIG_KEY_INSTALL_MODE, c.MODE_INSTALL_OWN)
            elif os.path.exists(shared_path_versions):
                window.config_manager.set(c.CONFIG_KEY_INSTALL_MODE, c.MODE_INSTALL_SHARED)
            else:
                window.config_manager.set(c.CONFIG_KEY_INSTALL_MODE, c.MODE_INSTALL_OWN)

        window.config_manager.set(c.CONFIG_KEY_INITIAL_SETUP_COMPLETE, True)
        window.logic.detect_installation(window)

    # New Setup Wizard v3.0
    force_wizard = "--first-wizard" in sys.argv
    if not window.config.get(c.CONFIG_KEY_ACCEPTED_TERMS, False) or force_wizard:
        logger.info("Triggering Setup Wizard (Accepted terms: {} | Forced: {})".format(
            window.config.get(c.CONFIG_KEY_ACCEPTED_TERMS), force_wizard
        ))
        wizard = SetupWizard(window)
        if wizard.exec() != SetupWizard.Accepted:
            logger.warning("Setup Wizard closed without completion. Exiting.")
            sys.exit(0) 
        else:
            logger.info("Setup Wizard completed successfully.")
            QTimer.singleShot(2000, window.check_drm_alert)
    else:
        # Version Check Logic only if terms already accepted
        QTimer.singleShot(1000, window.check_version_update)
        QTimer.singleShot(3000, window.check_drm_alert)

    window.show()
    sys.exit(app.exec())
