import customtkinter as ctk
from src import constants as c

class ToolsTab(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.pack(fill="both", expand=True)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Cabecera para el indicador de modo
        self.frame_tools_header = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_tools_header.grid(row=0, column=0, pady=(5, 0), padx=10, sticky="ew")

        self.lbl_tools_status = ctk.CTkLabel(
            self.frame_tools_header,
            text="",
            font=c.FONT_MODO,
        )
        self.lbl_tools_status.pack(side="left")

        # Usar ScrollableFrame
        self.scroll_tools = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_tools.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        self.refresh_tools_ui()

    def get_tools_data(self):
        # Definir las herramientas agrupadas
        groups = [
            {
                "title": c.UI_SECTION_MANAGEMENT,
                "icon": "⚙️",
                "tools": [
                    {"text": c.UI_BUTTON_INSTALL_APK, "icon": "📥", "cmd": self.app.install_apk_dialog, "color": None},
                    {"text": c.UI_BUTTON_MOVE_DELETE_VERSION, "icon": "🗑️", "cmd": lambda: self.app.logic.delete_version_dialog(self.app), "color": c.COLOR_RED_BUTTON},
                    {"text": c.UI_BUTTON_MIGRATE_DATA, "icon": "🚀", "cmd": self.app.open_migration_tool, "color": None},
                ]
            },
            {
                "title": c.UI_SECTION_CUSTOMIZATION,
                "icon": "🎨",
                "tools": [
                    {"text": c.UI_BUTTON_SKIN_PACK_CREATOR, "icon": "👕", "cmd": self.app.open_skin_tool, "color": None},
                    {"text": c.UI_BUTTON_GAME_CONFIG, "icon": "🛠️", "cmd": self.app.open_game_config_tool, "color": None},
                    {"text": c.UI_BUTTON_FIX_SHADERS, "icon": "✨", "cmd": lambda: self.app.logic.disable_shaders(self.app), "color": c.COLOR_YELLOW_BUTTON, "show_status": True},
                ]
            },
            {
                "title": c.UI_SECTION_FILES,
                "icon": "📂",
                "tools": [
                    {"text": c.UI_BUTTON_OPEN_DATA_FOLDER, "icon": "📁", "cmd": lambda: self.app.logic.open_data_folder(self.app), "color": None},
                    {"text": c.UI_BUTTON_EXPORT_WORLDS, "icon": "🌍", "cmd": lambda: self.app.logic.export_worlds_dialog(self.app), "color": None},
                    {"text": c.UI_BUTTON_OPEN_SCREENSHOTS, "icon": "📸", "cmd": lambda: self.app.logic.export_screenshots_dialog(self.app), "color": None},
                ]
            },
            {
                "title": c.UI_SECTION_SYSTEM,
                "icon": "💻",
                "tools": [
                    {
                        "text": c.UI_BUTTON_VERIFY_DEPS_FLATPAK if self.app.running_in_flatpak else c.UI_BUTTON_VERIFY_DEPS_LOCAL,
                        "icon": "📦", "cmd": lambda: self.app.logic.verify_dependencies(self.app), "color": None
                    },
                    {"text": c.UI_BUTTON_VERIFY_HW, "icon": "🔍", "cmd": lambda: self.app.logic.check_requirements_dialog(self.app), "color": None},
                    {"text": c.UI_BUTTON_MANAGE_SHORTCUT, "icon": "🔗", "cmd": self.app.manage_desktop_shortcut, "color": None},
                ]
            }
        ]
        return groups

    def refresh_tools_ui(self):
        # Limpiar scroll
        for child in self.scroll_tools.winfo_children():
            child.destroy()

        layout = self.app.config.get(c.CONFIG_KEY_TOOLS_LAYOUT, c.STYLE_COLUMNS)
        groups = self.get_tools_data()

        if layout == c.STYLE_LIST:
            self._render_list(groups)
        elif layout == c.STYLE_COLUMNS:
            self._render_columns(groups)
        else: # STYLE_GRID
            self._render_grid(groups)

        # Footer Créditos
        footer_row = 100 # Un número grande para que siempre esté al final
        if layout == c.STYLE_LIST:
            ctk.CTkLabel(
                self.scroll_tools, text=c.CREDITOS, text_color="gray", font=c.FONT_SMALL
            ).grid(row=footer_row, column=0, pady=20)
        elif layout == c.STYLE_COLUMNS:
            ctk.CTkLabel(
                self.scroll_tools, text=c.CREDITOS, text_color="gray", font=c.FONT_SMALL
            ).grid(row=footer_row, column=0, columnspan=2, pady=20)
        else: # GRID
            ctk.CTkLabel(
                self.scroll_tools, text=c.CREDITOS, text_color="gray", font=c.FONT_SMALL
            ).grid(row=footer_row, column=0, columnspan=3, pady=20)

    def _create_tool_button(self, parent, tool):
        if tool.get("hide_if_flatpak") and self.app.running_in_flatpak:
            return None

        btn_text = f"{tool['icon']} {tool['text']}"
        btn = ctk.CTkButton(
            parent,
            text=btn_text,
            height=c.BTN_HEIGHT + 4,
            corner_radius=8,
            command=tool["cmd"],
            font=c.FONT_NORMAL,
        )
        if tool.get("color"):
            btn.configure(fg_color=tool["color"])
            # Si el color es una constante con HOVER, intentar usarla
            hover_key = tool["color"] + "_HOVER"
            if hasattr(c, hover_key):
                btn.configure(hover_color=getattr(c, hover_key))

        btn.pack(pady=c.ELEMENT_SPACING, padx=15, fill="x")

        if tool.get("show_status"):
            self.lbl_shader_status = ctk.CTkLabel(
                parent, text=c.UI_LABEL_SHADERS_STATUS, font=c.FONT_SMALL
            )
            self.lbl_shader_status.pack(pady=(0, 5))
            # Actualizar estado inmediatamente
            self.app.logic.update_shader_status_label(self.app)

        return btn

    def _render_list(self, groups):
        self.scroll_tools.grid_columnconfigure(0, weight=1)
        self.scroll_tools.grid_columnconfigure(1, weight=0)

        for i, group in enumerate(groups):
            frame = ctk.CTkFrame(self.scroll_tools, corner_radius=c.CORNER_RADIUS)
            frame.grid(row=i, column=0, padx=20, pady=10, sticky="ew")

            ctk.CTkLabel(
                frame, text=f"{group['icon']} {group['title']}", font=c.FONT_SUBTITLE
            ).pack(pady=(10, 5))

            for tool in group["tools"]:
                self._create_tool_button(frame, tool)

    def _render_columns(self, groups):
        self.scroll_tools.grid_columnconfigure(0, weight=1)
        self.scroll_tools.grid_columnconfigure(1, weight=1)

        for i, group in enumerate(groups):
            col = i % 2
            frame = ctk.CTkFrame(self.scroll_tools, corner_radius=c.CORNER_RADIUS)
            frame.grid(row=i // 2, column=col, padx=10, pady=10, sticky="new")

            ctk.CTkLabel(
                frame, text=f"{group['icon']} {group['title']}", font=c.FONT_SUBTITLE
            ).pack(pady=(10, 5))

            for tool in group["tools"]:
                self._create_tool_button(frame, tool)

    def _render_grid(self, groups):
        # Renderizar cada herramienta como una tarjeta individual en un grid
        self.scroll_tools.grid_columnconfigure((0, 1, 2), weight=1)

        all_tools = []
        for group in groups:
            for tool in group["tools"]:
                if tool.get("hide_if_flatpak") and self.app.running_in_flatpak:
                    continue
                all_tools.append(tool)

        for i, tool in enumerate(all_tools):
            row = i // 3
            col = i % 3

            card = ctk.CTkFrame(self.scroll_tools, corner_radius=c.CORNER_RADIUS, width=180, height=140)
            card.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
            card.grid_propagate(False)

            # Icono grande
            lbl_icon = ctk.CTkLabel(card, text=tool["icon"], font=("Roboto", 40))
            lbl_icon.pack(pady=(15, 5))

            # Texto descriptivo (Label para que pueda hacer wrap)
            lbl_text = ctk.CTkLabel(card, text=tool["text"], font=c.FONT_SMALL, wraplength=160)
            lbl_text.pack(padx=10, pady=0)

            # Toda la tarjeta es clicable
            for w in [card, lbl_icon, lbl_text]:
                w.bind("<Button-1>", lambda e, cmd=tool["cmd"]: cmd())

            # Indicador de estado si es necesario
            if tool.get("show_status"):
                self.lbl_shader_status = ctk.CTkLabel(
                    card, text="...", font=("Roboto", 9)
                )
                self.lbl_shader_status.pack(side="bottom")
                self.app.logic.update_shader_status_label(self.app)
