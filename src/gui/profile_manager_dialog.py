import customtkinter as ctk
from src import constants as c
from src.gui import custom_dialogs as messagebox

class ProfileManagerDialog(ctk.CTkToplevel):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.title(c.UI_PROFILES_MANAGER_TITLE)
        self.geometry("500x500")
        self.transient(parent)
        self.resizable(False, False)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header
        self.frame_top = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_top.grid(row=0, column=0, padx=20, pady=15, sticky="ew")

        self.btn_add = ctk.CTkButton(
            self.frame_top,
            text=f"➕ {c.UI_BUTTON_ADD_PROFILE}",
            command=self.add_profile,
            fg_color=c.COLOR_GREEN_BUTTON,
            hover_color=c.COLOR_GREEN_BUTTON_HOVER,
            height=35,
            font=c.FONT_BOLD
        )
        self.btn_add.pack(fill="x")

        # Lista
        self.scroll_list = ctk.CTkScrollableFrame(self, corner_radius=c.CORNER_RADIUS, fg_color=("gray90", "gray15"))
        self.scroll_list.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")

        self.refresh_list()
        self.grab_set()

    def refresh_list(self):
        for widget in self.scroll_list.winfo_children():
            widget.destroy()

        profiles = self.app.logic.get_profiles(self.app)
        current = self.app.config.get(c.CONFIG_KEY_CURRENT_PROFILE)

        # Asegurar orden y listar correctamente
        for p in sorted(profiles):
            self.create_item(p, p == current)

    def create_item(self, name, is_current):
        frame = ctk.CTkFrame(self.scroll_list, corner_radius=10, fg_color=("gray85", "gray25") if not is_current else (c.COLOR_PRIMARY_GREEN, c.COLOR_SELECTED_GREEN))
        frame.pack(fill="x", pady=4, padx=5)

        status_dot = "●" if is_current else "○"
        lbl_name = ctk.CTkLabel(frame, text=f"{status_dot} {name}", font=c.FONT_BOLD, text_color="white" if is_current else None)
        lbl_name.pack(side="left", padx=15, pady=12)

        actions = ctk.CTkFrame(frame, fg_color="transparent")
        actions.pack(side="right", padx=10)

        if name != c.UI_PROFILE_DEFAULT:
            btn_rename = ctk.CTkButton(
                actions, text="✏️", width=35, height=30,
                fg_color=("gray75", "gray40"), hover_color="gray50",
                command=lambda n=name: self.rename_profile(n)
            )
            btn_rename.pack(side="left", padx=2)

            if not is_current:
                btn_del = ctk.CTkButton(
                    actions, text="🗑️", width=35, height=30,
                    fg_color=c.COLOR_RED_BUTTON, hover_color=c.COLOR_RED_BUTTON_HOVER,
                    command=lambda n=name: self.delete_profile(n)
                )
                btn_del.pack(side="left", padx=2)
        else:
             # Indicador de que default no se borra
             lbl_def = ctk.CTkLabel(actions, text="[System]", font=c.FONT_SMALL, text_color="gray")
             lbl_def.pack(side="right", padx=5)

    def _sync_ui(self):
        if hasattr(self.app.settings_tab, "refresh_profile_list"):
            self.app.settings_tab.refresh_profile_list()
        if hasattr(self.app.play_tab, "update_profile_indicator"):
            self.app.play_tab.update_profile_indicator()

    def add_profile(self):
        if self.app.logic.create_profile_dialog(self.app):
            self.refresh_list()
            self._sync_ui()

    def rename_profile(self, old_name):
        dialog = ctk.CTkInputDialog(text=c.UI_PROFILE_NAME_REQUIRED, title=c.UI_BUTTON_RENAME_PROFILE)
        new_name = dialog.get_input()
        if new_name and self.app.logic.rename_profile(self.app, old_name, new_name):
            self.refresh_list()
            self._sync_ui()

    def delete_profile(self, name):
        if self.app.logic.delete_profile(self.app, name):
            self.refresh_list()
            self._sync_ui()
