import customtkinter as ctk
from src.gui import custom_dialogs as messagebox
import os
import shutil
import threading
from src.utils.dialogs import ask_directory_native
from src.gui.progress_dialog import ProgressDialog
from src import constants as c

class MigrationDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title(c.UI_MIGRATION_MANAGER_TITLE)
        self.geometry("600x600")  # Reducido de 700 para pantallas pequeñas
        self.resizable(False, False)

        self.transient(parent)

        # ScrollableFrame principal para pantallas pequeñas
        self.main_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.main_scroll.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(
            self.main_scroll,
            text=c.UI_MIGRATION_TITLE,
            font=c.FONT_TITLE,
        ).pack(pady=c.SECTION_PADDING)

        # --- Frame Origen ---
        self.frame_src = ctk.CTkFrame(self.main_scroll, corner_radius=c.CORNER_RADIUS)
        self.frame_src.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            self.frame_src,
            text=c.UI_SOURCE_LABEL,
            font=c.FONT_SUBTITLE,
        ).pack(anchor="w", padx=c.SECTION_PADDING, pady=c.ELEMENT_SPACING)

        self.src_mode = ctk.StringVar(value=c.UI_SOURCE_MODES_DISPLAY[0])
        self.combo_src = ctk.CTkComboBox(
            self.frame_src,
            variable=self.src_mode,
            values=c.UI_SOURCE_MODES_DISPLAY,
            command=self.update_src_path_ui,
            width=300,
            font=c.FONT_NORMAL,
        )
        self.combo_src.pack(fill="x", padx=10, pady=5)

        # Frame para ID de Flatpak (solo visible en modo Flatpak)
        self.frame_flatpak_id = ctk.CTkFrame(self.frame_src, fg_color="transparent")
        ctk.CTkLabel(self.frame_flatpak_id, text=c.UI_LABEL_APP_ID, font=c.FONT_NORMAL).pack(side="left", padx=5)
        self.entry_flatpak_src_id = ctk.CTkEntry(self.frame_flatpak_id, width=250, font=c.FONT_NORMAL)
        self.entry_flatpak_src_id.pack(side="left", padx=5)
        self.entry_flatpak_src_id.insert(0, c.DEFAULT_FLATPAK_ID)

        self.entry_src = ctk.CTkEntry(
            self.frame_src, placeholder_text=c.UI_PLACEHOLDER_SOURCE_PATH, font=c.FONT_NORMAL
        )
        self.entry_src.pack(fill="x", padx=10, pady=5)

        self.btn_browse_src = ctk.CTkButton(
            self.frame_src, text=c.UI_BUTTON_BROWSE_FOLDER, width=120, command=self.browse_src, font=c.FONT_NORMAL
        )
        self.btn_browse_src.pack(anchor="e", padx=10, pady=5)

        # Label de validación
        self.lbl_src_validation = ctk.CTkLabel(
            self.frame_src, text="", text_color="gray", font=ctk.CTkFont(size=10)
        )
        self.lbl_src_validation.pack(anchor="w", padx=10, pady=2)

        # --- Frame Destino ---
        self.frame_dst = ctk.CTkFrame(self.main_scroll, corner_radius=c.CORNER_RADIUS)
        self.frame_dst.pack(fill="x", padx=10, pady=20)

        ctk.CTkLabel(
            self.frame_dst,
            text=c.UI_DESTINATION_LABEL,
            font=c.FONT_SUBTITLE,
        ).pack(anchor="w", padx=c.SECTION_PADDING, pady=c.ELEMENT_SPACING)

        f_dst_selector = ctk.CTkFrame(self.frame_dst, fg_color="transparent")
        f_dst_selector.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(f_dst_selector, text=f"👤 {c.UI_LABEL_PROFILE}", font=c.FONT_BOLD).pack(side="left", padx=5)

        self.dst_profile_var = ctk.StringVar(value=self.parent.config.get(c.CONFIG_KEY_CURRENT_PROFILE, c.UI_PROFILE_DEFAULT))
        self.combo_dst_profile = ctk.CTkComboBox(
            f_dst_selector,
            values=self.parent.logic.get_profiles(self.parent),
            variable=self.dst_profile_var,
            command=self.update_dst_path_info,
            width=200
        )
        self.combo_dst_profile.pack(side="left", padx=5)

        self.lbl_dst = ctk.CTkLabel(
            self.frame_dst,
            text="",
            text_color="#3498db",
            font=c.FONT_SMALL,
            wraplength=550
        )
        self.lbl_dst.pack(anchor="w", padx=10, pady=5)
        self.update_dst_path_info()

        # --- Opciones de Migración ---
        self.frame_opts = ctk.CTkFrame(self.main_scroll, corner_radius=c.CORNER_RADIUS)
        self.frame_opts.pack(fill="x", padx=10, pady=15)

        ctk.CTkLabel(
            self.frame_opts,
            text=c.UI_WHAT_TO_MIGRATE,
            font=c.FONT_SUBTITLE,
        ).pack(anchor="w", padx=c.SECTION_PADDING, pady=c.ELEMENT_SPACING)

        # Checkboxes para opciones de migración
        self.check_versions = ctk.BooleanVar(value=True)
        self.check_worlds = ctk.BooleanVar(value=False)
        self.check_resources = ctk.BooleanVar(value=False)
        self.check_all = ctk.BooleanVar(value=False)

        self.cb_versions = ctk.CTkCheckBox(
            self.frame_opts,
            text=c.UI_MIGRATE_VERSIONS,
            variable=self.check_versions,
            command=self.on_migration_option_change,
            font=c.FONT_NORMAL,
        )
        self.cb_versions.pack(anchor="w", padx=20, pady=3)

        self.cb_worlds = ctk.CTkCheckBox(
            self.frame_opts,
            text=c.UI_MIGRATE_WORLDS,
            variable=self.check_worlds,
            command=self.on_migration_option_change,
            font=c.FONT_NORMAL,
        )
        self.cb_worlds.pack(anchor="w", padx=20, pady=3)

        self.cb_resources = ctk.CTkCheckBox(
            self.frame_opts,
            text=c.UI_MIGRATE_RESOURCES,
            variable=self.check_resources,
            command=self.on_migration_option_change,
            font=c.FONT_NORMAL,
        )
        self.cb_resources.pack(anchor="w", padx=20, pady=3)

        # Separador
        ctk.CTkLabel(self.frame_opts, text="─" * 50, text_color="gray").pack(pady=5)

        self.cb_all = ctk.CTkCheckBox(
            self.frame_opts,
            text=c.UI_MIGRATE_ALL,
            variable=self.check_all,
            command=self.on_all_migration_toggle,
            font=c.FONT_BOLD,
        )
        self.cb_all.pack(anchor="w", padx=20, pady=3)

        # --- Método de Migración ---
        self.frame_method = ctk.CTkFrame(self.main_scroll, corner_radius=c.CORNER_RADIUS)
        self.frame_method.pack(fill="x", padx=10, pady=15)

        ctk.CTkLabel(
            self.frame_method,
            text=c.UI_MIGRATION_METHOD,
            font=c.FONT_SUBTITLE,
        ).pack(anchor="w", padx=10, pady=5)

        self.method = ctk.StringVar(value="copy")
        ctk.CTkRadioButton(
            self.frame_method,
            text=c.UI_METHOD_COPY,
            variable=self.method,
            value="copy",
            font=c.FONT_NORMAL,
        ).pack(anchor="w", padx=20, pady=2)
        ctk.CTkRadioButton(
            self.frame_method,
            text=c.UI_METHOD_MOVE,
            variable=self.method,
            value="move",
            font=c.FONT_NORMAL,
        ).pack(anchor="w", padx=20, pady=2)
        ctk.CTkRadioButton(
            self.frame_method,
            text=c.UI_METHOD_LINK,
            variable=self.method,
            value="link",
            font=c.FONT_NORMAL,
        ).pack(anchor="w", padx=20, pady=2)

        # --- Acción ---
        self.btn_migrate = ctk.CTkButton(
            self,
            text=c.UI_BUTTON_START_MIGRATION,
            height=40,
            font=c.FONT_BOLD,
            command=self.start_migration,
        )
        self.btn_migrate.pack(pady=(10, 15), padx=30, fill="x", side="bottom")

        self.update_src_path_ui(c.UI_SOURCE_MODES_DISPLAY[0])
        self.update_idletasks()
        self.grab_set()

    def on_all_migration_toggle(self):
        """Cuando se selecciona Migrar TODO, deshabilitar otras opciones"""
        if self.check_all.get():
            self.cb_versions.configure(state="disabled")
            self.cb_worlds.configure(state="disabled")
            self.cb_resources.configure(state="disabled")
            self.check_versions.set(False)
            self.check_worlds.set(False)
            self.check_resources.set(False)
        else:
            self.cb_versions.configure(state="normal")
            self.cb_worlds.configure(state="normal")
            self.cb_resources.configure(state="normal")

    def on_migration_option_change(self):
        """Si se selecciona alguna opción específica, desmarcar TODO"""
        if (
            self.check_versions.get()
            or self.check_worlds.get()
            or self.check_resources.get()
        ):
            self.check_all.set(False)
            self.cb_versions.configure(state="normal")
            self.cb_worlds.configure(state="normal")
            self.cb_resources.configure(state="normal")

    def update_src_path_ui(self, choice):
        if choice == c.UI_SOURCE_MODES_DISPLAY[0]: # Local (.local)
            path = os.path.join(os.path.expanduser("~"), c.LOCAL_SHARE_DIR)
            self.entry_src.delete(0, "end")
            self.entry_src.insert(0, path)
            self.entry_src.configure(state="disabled", fg_color="gray30")
            self.frame_flatpak_id.pack_forget()
            self.validate_source_path(path)

        elif choice == c.UI_SOURCE_MODES_DISPLAY[1]: # Flatpak (por ID)
            self.entry_src.configure(state="disabled", fg_color="gray30")
            self.frame_flatpak_id.pack(fill="x", padx=10, pady=5)
            # Actualizar ruta basada en ID
            app_id = self.entry_flatpak_src_id.get().strip()
            if not app_id:
                app_id = c.DEFAULT_FLATPAK_ID
            path = os.path.join(
                os.path.expanduser("~"),
                f"{c.FLATPAK_DATA_DIR}/{app_id}/{c.MCPELAUNCHER_DATA_SUBDIR}",
            )
            self.entry_src.delete(0, "end")
            self.entry_src.insert(0, path)
            self.validate_source_path(path)

        else:  # Personalizado
            self.entry_src.delete(0, "end")
            self.entry_src.configure(state="normal", fg_color=["#F9F9FA", "#343638"])
            self.frame_flatpak_id.pack_forget()
            self.lbl_src_validation.configure(text="")

    def validate_source_path(self, path):
        """Validar que la carpeta contenga 'mcpelauncher'"""
        if not path:
            self.lbl_src_validation.configure(text="", text_color="gray")
            return False

        if os.path.exists(path):
            # Validar que contenga estructura de mcpelauncher
            if "mcpelauncher" in path or os.path.exists(os.path.join(path, c.VERSIONS_DIR)):
                self.lbl_src_validation.configure(
                    text=c.UI_VALID_FOLDER_DETECTED, text_color="green"
                )
                return True
            else:
                self.lbl_src_validation.configure(
                    text=c.UI_INVALID_FOLDER_WARNING,
                    text_color="orange",
                )
                return False
        else:
            self.lbl_src_validation.configure(
                text=c.UI_FOLDER_NOT_EXISTS, text_color="red"
            )
            return False

    def browse_src(self):
        d = ask_directory_native(self, title=c.UI_SELECT_SOURCE_FOLDER)
        if d:
            self.entry_src.configure(state="normal", fg_color=["#F9F9FA", "#343638"])
            self.entry_src.delete(0, "end")
            self.entry_src.insert(0, d)
            self.combo_src.set(c.UI_SOURCE_MODES_DISPLAY[2]) # Personalizado
            self.validate_source_path(d)

    def update_dst_path_info(self, *args):
        profile = self.dst_profile_var.get()
        # Ruta base + profiles/perfil
        path = os.path.join(self.parent.active_path, c.PROFILES_DIR, profile)
        # Pero si el perfil es el actual, podemos usar active_path directamente para mundos/recursos
        # No obstante, para el migrador es mejor ser explícito con el perfil destino seleccionado.
        self.lbl_dst.configure(text=f"Ruta: {path}")

    def start_migration(self):
        src = self.entry_src.get().strip()

        # Determinar destino basado en el perfil seleccionado en el diálogo
        profile = self.dst_profile_var.get()
        dst = os.path.join(self.parent.active_path, c.PROFILES_DIR, profile)

        method = self.method.get()
        migrate_all = self.check_all.get()
        migrate_versions = self.check_versions.get()
        migrate_worlds = self.check_worlds.get()
        migrate_resources = self.check_resources.get()

        if not os.path.exists(src):
            messagebox.showerror(self, c.UI_ERROR_TITLE, c.UI_FOLDER_NOT_EXISTS)
            return
        if src == dst:
            messagebox.showerror(self, c.UI_ERROR_TITLE, c.UI_ERROR_SAME_FOLDER)
            return
        if not any([migrate_all, migrate_versions, migrate_worlds, migrate_resources]):
            messagebox.showwarning(self, c.UI_INFO_TITLE, c.UI_ERROR_NOTHING_SELECTED)
            return

        items_to_migrate = []
        if migrate_all:
            items_to_migrate.append("TODO")
        else:
            if migrate_versions: items_to_migrate.append(c.UI_MIGRATE_VERSIONS_SIMPLE)
            if migrate_worlds: items_to_migrate.append(c.UI_MIGRATE_WORLDS_SIMPLE)
            if migrate_resources: items_to_migrate.append(c.UI_MIGRATE_RESOURCES_SIMPLE)

        msg = c.UI_MIGRATION_CONFIRM_MSG.format(
            src=src, dst=dst, method=method.upper(), items=', '.join(items_to_migrate)
        )
        if not messagebox.askyesno(self, c.UI_CONFIRM_TITLE, msg):
            return

        self.progress_dialog = ProgressDialog(self, c.UI_MIGRATING_TITLE, c.UI_MIGRATING_MSG)

        thread = threading.Thread(target=self._run_migration, args=(
            src, dst, method, migrate_all, migrate_versions, migrate_worlds, migrate_resources
        ))
        thread.start()

    def _run_migration(self, src, dst_profile_path, method, migrate_all, migrate_versions, migrate_worlds, migrate_resources):
        try:
            migrated_count = 0
            base_dst = self.parent.active_path

            def process_item(s_item, d_item):
                if os.path.exists(d_item): return False
                if method == "copy": shutil.copytree(s_item, d_item)
                elif method == "move": shutil.move(s_item, d_item)
                elif method == "link": os.symlink(s_item, d_item)
                return True

            if migrate_all:
                # Migrar todo a la base (incluye todas las carpetas)
                if process_item(src, base_dst): migrated_count = 1
            else:
                if migrate_versions:
                    # Versiones siempre van a la raíz del active_path (compartidas)
                    src_dir, dst_dir = os.path.join(src, c.VERSIONS_DIR), os.path.join(base_dst, c.VERSIONS_DIR)
                    if os.path.exists(src_dir):
                        os.makedirs(dst_dir, exist_ok=True)
                        for item in os.listdir(src_dir):
                            if process_item(os.path.join(src_dir, item), os.path.join(dst_dir, item)): migrated_count += 1

                if migrate_worlds:
                    # Mundos van al perfil seleccionado
                    src_dir = os.path.join(src, c.WORLDS_DIR)
                    dst_dir = os.path.join(dst_profile_path, c.WORLDS_DIR)
                    if os.path.exists(src_dir):
                        os.makedirs(dst_dir, exist_ok=True)
                        for item in os.listdir(src_dir):
                            if process_item(os.path.join(src_dir, item), os.path.join(dst_dir, item)): migrated_count += 1

                if migrate_resources:
                    # Recursos van al perfil seleccionado
                    src_dir = os.path.join(src, "games/com.mojang/resource_packs")
                    dst_dir = os.path.join(dst_profile_path, "games/com.mojang/resource_packs")
                    if os.path.exists(src_dir):
                        os.makedirs(dst_dir, exist_ok=True)
                        for item in os.listdir(src_dir):
                            if process_item(os.path.join(src_dir, item), os.path.join(dst_dir, item)): migrated_count += 1

            def on_complete():
                self.progress_dialog.close()
                messagebox.showinfo(self, c.UI_SUCCESS_TITLE, c.UI_MIGRATION_SUCCESS_MSG.format(count=migrated_count))
                self.parent.logic.refresh_version_list(self.parent)
                self.destroy()
            self.parent.after(0, on_complete)

        except Exception as e:
            def on_error():
                self.progress_dialog.close()
                messagebox.showerror(self, c.UI_ERROR_TITLE, f"Error: {e}")
            self.parent.after(0, on_error)
