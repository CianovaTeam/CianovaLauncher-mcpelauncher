import sys
import os
from PySide6.QtWidgets import QApplication
from src.gui.main_window import CianovaLauncherApp
from src.gui.test_window import TestWindow
from src import constants as c
from src.core import language_manager

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Parse arguments
    launcher_path = os.path.abspath(sys.argv[0])
    force_flatpak_ui = "--force-flatpak-ui" in sys.argv
    force_nvidia_ui = "--force-nvidia-ui" in sys.argv
    test_mode = "--test-mode" in sys.argv

    if test_mode:
        window = TestWindow()
        window.show()
        sys.exit(app.exec())

    # normal launch
    window = CianovaLauncherApp(launcher_path=launcher_path, force_flatpak_ui=force_flatpak_ui, force_nvidia_ui=force_nvidia_ui)

    # Initial setup logic
    if not window.config_manager.get(c.CONFIG_KEY_INITIAL_SETUP_COMPLETE, False):
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

    window.show()
    sys.exit(app.exec())
