import customtkinter as ctk
import sys
import os
from src.gui.main_window import CianovaLauncherApp
from src.gui.test_window import TestWindow
from src import constants as c
from src.core import language_manager

if __name__ == "__main__":
    # 1. Configuración básica de UI
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    # 2. Parseo de argumentos
    launcher_path = os.path.abspath(sys.argv[0])
    force_flatpak_ui = "--force-flatpak-ui" in sys.argv
    force_nvidia_ui = "--force-nvidia-ui" in sys.argv
    test_mode = "--test-mode" in sys.argv

    if test_mode:
        app = TestWindow()
        app.mainloop()
        sys.exit(0)

    # 3. Lanzamiento normal
    app = CianovaLauncherApp(launcher_path=launcher_path, force_flatpak_ui=force_flatpak_ui, force_nvidia_ui=force_nvidia_ui)

    # Lógica de configuración inicial inteligente (solo en el primer arranque)
    if not app.config_manager.get(c.CONFIG_KEY_INITIAL_SETUP_COMPLETE, False):
        if app.running_in_flatpak:
            own_path_versions = os.path.join(app.our_data_path, c.VERSIONS_DIR)
            shared_path_versions = os.path.join(os.path.expanduser("~"), c.LOCAL_SHARE_DIR, c.VERSIONS_DIR)

            # Prioridad 1: Usar "local_own" si ya tiene datos.
            if os.path.exists(own_path_versions):
                app.config_manager.set(c.CONFIG_KEY_INSTALL_MODE, c.MODE_INSTALL_OWN)
            # Prioridad 2: Usar "local_shared" si tiene datos y el propio no.
            elif os.path.exists(shared_path_versions):
                app.config_manager.set(c.CONFIG_KEY_INSTALL_MODE, c.MODE_INSTALL_SHARED)
            # Por defecto: "local_own" si no se encuentra nada.
            else:
                app.config_manager.set(c.CONFIG_KEY_INSTALL_MODE, c.MODE_INSTALL_OWN)

        # Marcar la configuración inicial como completada para no volver a ejecutarla.
        app.config_manager.set(c.CONFIG_KEY_INITIAL_SETUP_COMPLETE, True)

        # Recargar la configuración en la app para que la UI refleje el cambio
        app.logic.detect_installation(app)

    app.mainloop()
