import os
import customtkinter as ctk
from src.gui import custom_dialogs as messagebox
from src import constants as c
from src.core import addon_manager
from src.utils.image_manager import ImageManager
from PIL import Image
from src.utils import dialogs

class AddonManagerDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.app = parent

        self.title(c.UI_ADDON_MANAGER_TITLE)
        self.geometry("950x750")
        self.transient(parent)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header
        self.frame_top = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_top.grid(row=0, column=0, padx=20, pady=(15, 0), sticky="ew")

        # Row 1: Search and Main buttons
        self.row1 = ctk.CTkFrame(self.frame_top, fg_color="transparent")
        self.row1.pack(fill="x")

        self.entry_search = ctk.CTkEntry(
            self.row1,
            placeholder_text=c.UI_LABEL_SEARCH_PLACEHOLDER,
            width=300
        )
        self.entry_search.pack(side="left", padx=5)
        self.entry_search.bind("<KeyRelease>", self.on_search_delay)

        self.btn_reload = ctk.CTkButton(
            self.row1, text="↻", width=40, height=35,
            command=self.refresh_list, font=("Roboto", 20, "bold")
        )
        self.btn_reload.pack(side="left", padx=5)

        self.btn_import = ctk.CTkButton(
            self.row1,
            text=f"📥 {c.UI_BUTTON_IMPORT_FILE}",
            command=self.import_file,
            fg_color=c.COLOR_GREEN_BUTTON,
            hover_color=c.COLOR_GREEN_BUTTON_HOVER,
            height=35,
            font=c.FONT_BOLD
        )
        self.btn_import.pack(side="right", padx=5)

        # Row 2: Status Indicators
        self.row2 = ctk.CTkFrame(self.frame_top, fg_color="transparent")
        self.row2.pack(fill="x", pady=(5, 0))

        profile = self.app.config.get(c.CONFIG_KEY_CURRENT_PROFILE, c.UI_PROFILE_DEFAULT)
        install_mode = c.UI_INSTALL_MODES.get(self.app.config.get(c.CONFIG_KEY_INSTALL_MODE), "Unknown")

        self.lbl_profile_info = ctk.CTkLabel(
            self.row2,
            text=f"👤 {c.UI_LABEL_PROFILE} {profile}",
            font=c.FONT_SMALL,
            text_color=c.COLOR_PRIMARY_GREEN
        )
        self.lbl_profile_info.pack(side="left", padx=10)

        self.lbl_mode_info = ctk.CTkLabel(
            self.row2,
            text=f"📦 {c.UI_LABEL_INSTALLATION} {install_mode}",
            font=c.FONT_SMALL,
            text_color="gray"
        )
        self.lbl_mode_info.pack(side="left", padx=10)

        # Tabs (Worlds, RP, BP)
        self.tabview = ctk.CTkTabview(self, corner_radius=c.CORNER_RADIUS, command=self.on_tab_change)
        self.tabview.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")

        self.tab_worlds = self.tabview.add(c.UI_TAB_WORLDS)
        self.tab_rp = self.tabview.add(c.UI_TAB_RP)
        self.tab_bp = self.tabview.add(c.UI_TAB_BP)

        # Scroll frames
        self.scrolls = {
            c.UI_TAB_WORLDS: ctk.CTkScrollableFrame(self.tab_worlds, fg_color="transparent"),
            c.UI_TAB_RP: ctk.CTkScrollableFrame(self.tab_rp, fg_color="transparent"),
            c.UI_TAB_BP: ctk.CTkScrollableFrame(self.tab_bp, fg_color="transparent")
        }
        for s in self.scrolls.values(): s.pack(fill="both", expand=True)

        self.addons_data = []
        self._search_timer = None
        self._render_job = None
        self._last_rendered_search = {} # Cache search string per tab

        self.refresh_list()
        self.grab_set()

    def on_tab_change(self):
        self.render_filtered_list()

    def on_search_delay(self, event=None):
        if self._search_timer: self.after_cancel(self._search_timer)
        self._search_timer = self.after(300, self.render_filtered_list)

    def refresh_list(self):
        from src.gui.progress_dialog import ProgressDialog
        import threading

        progress = ProgressDialog(self, c.UI_ANALYZING_TITLE, c.UI_SCANNING_RESOURCES)

        def task():
            try:
                self.addons_data = addon_manager.scan_all_addons(self.app)
                self._last_rendered_search = {} # Invalidate cache
                self.after(0, lambda: [progress.close(), self.render_filtered_list()])
            except Exception as e:
                self.after(0, lambda: [progress.close(), messagebox.showerror(self, c.UI_ERROR_TITLE, str(e))])

        threading.Thread(target=task, daemon=True).start()

    def render_filtered_list(self):
        if self._render_job:
            self.after_cancel(self._render_job)

        search_query = self.entry_search.get().lower()
        current_tab = self.tabview.get()
        target_scroll = self.scrolls.get(current_tab)

        if not target_scroll: return

        # Check cache: if search hasn't changed and we have widgets, skip
        if self._last_rendered_search.get(current_tab) == search_query:
            if target_scroll.winfo_children():
                return

        # Map tab to folder
        folder_map = {
            c.UI_TAB_WORLDS: "minecraftWorlds",
            c.UI_TAB_BP: "behavior_packs",
            c.UI_TAB_RP: "resource_packs"
        }
        folder_filter = folder_map.get(current_tab, "")

        # Update cache
        self._last_rendered_search[current_tab] = search_query

        # Clear active scroll only
        for w in target_scroll.winfo_children(): w.destroy()

        # Filter logic
        filtered = [
            a for a in self.addons_data
            if (a["folder"] == folder_filter or (folder_filter == "resource_packs" and a["folder"] not in ["minecraftWorlds", "behavior_packs"]))
            and (not search_query or search_query in a["name"].lower() or search_query in a["description"].lower())
        ]
        filtered.sort(key=lambda x: x["name"].lower())

        def render_batch(items, index=0):
            if index >= len(items):
                self._render_job = None
                return
            batch_size = 6
            for i in range(index, min(index + batch_size, len(items))):
                self.create_item_ui(target_scroll, items[i])
            self._render_job = self.after(5, lambda: render_batch(items, index + batch_size))

        render_batch(filtered)

    def create_item_ui(self, scroll, addon):
        item_frame = ctk.CTkFrame(scroll, corner_radius=12)
        item_frame.pack(fill="x", pady=6, padx=10)

        # Icono más grande (90x90)
        icon_size = (90, 90)
        img = None
        if addon["icon_path"]:
            try:
                img = ctk.CTkImage(light_image=Image.open(addon["icon_path"]), size=icon_size)
            except: pass

        if not img:
            img = ImageManager.get_image("icon.png", size=icon_size)

        lbl_icon = ctk.CTkLabel(item_frame, text="", image=img)
        lbl_icon.pack(side="left", padx=15, pady=15)

        # Info
        info_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True, padx=5, pady=15)

        name_text = addon["name"]
        if addon["version"]: name_text += f" (v{addon['version']})"

        title_font = ctk.CTkFont(family="Roboto", size=20, weight="bold") if addon["folder"] == "minecraftWorlds" else c.FONT_BOLD
        lbl_name = ctk.CTkLabel(info_frame, text=name_text, font=title_font, anchor="w")
        lbl_name.pack(fill="x")

        # Tipo y estado
        if addon["folder"] != "minecraftWorlds":
            status_text = c.UI_STATUS_ACTIVE if addon["enabled"] else c.UI_STATUS_DISABLED
            type_str = f"[{addon['type_label']}] - {status_text}"
            lbl_type = ctk.CTkLabel(info_frame, text=type_str, font=c.FONT_SMALL, text_color="gray", anchor="w")
            lbl_type.pack(fill="x")

        if addon["description"]:
            lbl_desc = ctk.CTkLabel(info_frame, text=addon["description"], font=c.FONT_NORMAL, text_color="gray", anchor="w", wraplength=480, justify="left")
            lbl_desc.pack(fill="x", pady=(2, 0))

        # Acciones
        actions = ctk.CTkFrame(item_frame, fg_color="transparent")
        actions.pack(side="right", padx=20)

        if addon["folder"] != "minecraftWorlds":
            btn_text = c.UI_STATUS_ENABLED_BTN if addon["enabled"] else c.UI_STATUS_DISABLED_BTN
            btn_color = c.COLOR_GREEN_BUTTON if addon["enabled"] else c.COLOR_RED_BUTTON
            btn_hover = c.COLOR_GREEN_BUTTON_HOVER if addon["enabled"] else c.COLOR_RED_BUTTON_HOVER

            btn_toggle = ctk.CTkButton(
                actions, text=btn_text, width=130, height=40,
                fg_color=btn_color, hover_color=btn_hover,
                command=lambda a=addon: self.toggle(a),
                font=c.FONT_BOLD
            )
            btn_toggle.pack(side="left", padx=5)
        else:
            btn_exp = ctk.CTkButton(
                actions, text=c.UI_BUTTON_EXPORT, width=130, height=40,
                command=lambda a=addon: self.export_world(a),
                font=c.FONT_BOLD
            )
            btn_exp.pack(side="left", padx=5)

        btn_del = ctk.CTkButton(
            actions, text="🗑️", width=45, height=38,
            fg_color=c.COLOR_RED_BUTTON, hover_color=c.COLOR_RED_BUTTON_HOVER,
            command=lambda a=addon: self.delete(a)
        )
        btn_del.pack(side="left", padx=5)

    def toggle(self, addon):
        from src.gui.progress_dialog import ProgressDialog
        import threading

        progress = ProgressDialog(self, c.UI_INFO_TITLE, c.UI_TOGGLING_STATUS)

        def task():
            try:
                new_path = addon_manager.toggle_addon(self.app, addon)
                addon["enabled"] = not addon["enabled"]
                addon["path"] = new_path
                self._last_rendered_search = {} # Invalidate cache
                self.after(0, lambda: [progress.close(), self.render_filtered_list()])
            except Exception as e:
                self.after(0, lambda: [progress.close(), messagebox.showerror(self, c.UI_ERROR_TITLE, str(e))])

        threading.Thread(target=task, daemon=True).start()

    def delete(self, addon):
        if messagebox.askyesno(self, c.UI_CONFIRM_DELETE_TITLE, f"{c.UI_BUTTON_DELETE} {addon['name']}?"):
            from src.gui.progress_dialog import ProgressDialog
            import threading

            progress = ProgressDialog(self, c.UI_INFO_TITLE, c.UI_DELETING_RESOURCE)

            def task():
                try:
                    if addon_manager.delete_addon(addon["path"]):
                        if addon in self.addons_data: self.addons_data.remove(addon)
                        self._last_rendered_search = {} # Invalidate cache
                    self.after(0, lambda: [progress.close(), self.render_filtered_list()])
                except Exception as e:
                    self.after(0, lambda: [progress.close(), messagebox.showerror(self, c.UI_ERROR_TITLE, str(e))])

            threading.Thread(target=task, daemon=True).start()

    def export_world(self, addon):
        dest_dir = dialogs.ask_directory_native(self, title=c.UI_SELECT_DEST_FOLDER_TITLE)
        if dest_dir:
            success, msg = addon_manager.export_world(addon["path"], dest_dir)
            if success:
                messagebox.showinfo(self, c.UI_SUCCESS_TITLE, c.UI_WORLD_EXPORTED_SUCCESS.format(path=msg))
            else:
                messagebox.showerror(self, c.UI_ERROR_TITLE, msg)

    def import_file(self):
        file_path = dialogs.ask_open_filename_native(
            self,
            title=c.UI_OPEN_FILE_TITLE,
            filetypes=[(c.UI_MCPACK_FILES_TYPE, "*.mcpack *.mcaddon *.mcworld *.mcworldtemplate"), (c.UI_ALL_FILES_TYPE, "*.*")]
        )
        if not file_path: return
        self._install_task([file_path])

    def _install_task(self, file_paths):
        from src.gui.progress_dialog import ProgressDialog
        import threading

        progress = ProgressDialog(self, c.UI_INFO_TITLE, c.UI_INSTALLING_PACK)

        def task():
            try:
                for f in file_paths:
                    addon_manager.install_addon_file(self.app.active_path, f)
                self.after(0, lambda: [progress.close(), self.refresh_list()])
            except Exception as e:
                self.after(0, lambda: [progress.close(), messagebox.showerror(self, c.UI_ERROR_TITLE, str(e))])

        threading.Thread(target=task, daemon=True).start()
