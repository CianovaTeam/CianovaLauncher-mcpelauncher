import customtkinter as ctk
import sys
from src.gui.main_window import CianovaLauncherApp

if __name__ == "__main__":
    # Configuración de Tema por defecto
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    import os
    from src import constants as c

    launcher_path = os.path.abspath(sys.argv[0])
    force_flatpak_ui = "--force-flatpak-ui" in sys.argv
    app = CianovaLauncherApp(launcher_path=launcher_path, force_flatpak_ui=force_flatpak_ui)

    # Lógica de configuración inicial inteligente (solo en el primer arranque)
    if not app.config_manager.get(c.CONFIG_KEY_INITIAL_SETUP_COMPLETE, False):
        if app.running_in_flatpak:
            own_path_versions = os.path.join(app.our_data_path, c.VERSIONS_DIR)
            shared_path_versions = os.path.join(os.path.expanduser("~"), c.LOCAL_SHARE_DIR, c.VERSIONS_DIR)

            # Prioridad 1: Usar "Local (Propio)" si ya tiene datos.
            if os.path.exists(own_path_versions):
                app.config_manager.set(c.CONFIG_KEY_INSTALL_MODE, c.UI_MODE_VALUES_FLATPAK[0]) # Local (Propio)
            # Prioridad 2: Usar "Local (Compartido)" si tiene datos y el propio no.
            elif os.path.exists(shared_path_versions):
                app.config_manager.set(c.CONFIG_KEY_INSTALL_MODE, c.UI_MODE_VALUES_FLATPAK[1]) # Local (Compartido)
            # Por defecto: "Local (Propio)" si no se encuentra nada.
            else:
                app.config_manager.set(c.CONFIG_KEY_INSTALL_MODE, c.UI_MODE_VALUES_FLATPAK[0])

        # Marcar la configuración inicial como completada para no volver a ejecutarla.
        app.config_manager.set(c.CONFIG_KEY_INITIAL_SETUP_COMPLETE, True)

        # Recargar la configuración en la app para que la UI refleje el cambio
        app.logic.detect_installation(app)

    app.mainloop()
