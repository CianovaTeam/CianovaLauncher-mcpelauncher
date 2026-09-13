"""
Resource & Behavior Packs (RP/BP) Management Tab for Cianova Launcher.
Displays and manages Minecraft Bedrock resource packs and behavior packs,
including pack thumbnails, version metadata, enable/disable toggling,
native import/export (.mcpack/.mcaddon/.zip), folder browsing, and safe deletion.
"""

import os
import shutil
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QFrame, QScrollArea, QLineEdit,
                             QSizePolicy, QApplication, QCheckBox)
from PySide6.QtCore import Qt, QRect, QSize, QTimer, QThread, Signal
from PySide6.QtGui import (QPainter, QColor, QFont, QPen, QIcon, QPixmap,
                           QImage, QDesktopServices, QFontMetrics, QDragEnterEvent, QDropEvent)
from src import constants as c
from src.core.ui_utils import FlowLayout, clear_layout
from src.core import addon_manager
from src.utils.resource_path import resource_path
from src.utils.image_manager import ImageManager
from src.utils.colors import adjust_color, hex_to_rgba
from src.utils.logger import logger
from src.utils.dialogs import ask_open_filename_native, ask_save_filename_native
from src.gui import custom_dialogs as messagebox
from src.utils.process_utils import open_folder


class PackActionWorker(QThread):
    """Background worker for pack actions like toggle, delete, or install."""
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, action_func, *args):
        super().__init__()
        self.action_func = action_func
        self.args = args

    def run(self):
        try:
            res = self.action_func(*self.args)
            self.finished.emit(res)
        except Exception as e:
            self.error.emit(str(e))


class PackCardWidget(QFrame):
    """Card displaying a single Resource Pack or Behavior Pack."""

    def __init__(self, pack_info: dict, app=None, parent_tab=None):
        super().__init__()
        self.pack_info = pack_info
        self.app = app
        self.parent_tab = parent_tab
        self.setObjectName("PackCard")
        self.setFixedSize(280, 240)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(12, 12, 12, 12)
        self._layout.setSpacing(6)

        # 1. Top Row: Thumbnail + Badges
        row_top = QHBoxLayout()
        row_top.setSpacing(10)

        self.lbl_thumb = QLabel()
        self.lbl_thumb.setFixedSize(64, 64)
        self.lbl_thumb.setAlignment(Qt.AlignCenter)
        self.lbl_thumb.setStyleSheet("background-color: #0d0e11; border-radius: 8px;")
        row_top.addWidget(self.lbl_thumb, 0, Qt.AlignTop)

        col_head = QVBoxLayout()
        col_head.setContentsMargins(0, 0, 0, 0)
        col_head.setSpacing(4)

        # Type Badge (RP / BP)
        self.lbl_type_badge = QLabel()
        self.lbl_type_badge.setStyleSheet("""
            font-size: 10px;
            font-weight: bold;
            padding: 2px 6px;
            border-radius: 4px;
        """)
        col_head.addWidget(self.lbl_type_badge, 0, Qt.AlignLeft)

        # Name
        self.lbl_name = QLabel()
        self.lbl_name.setStyleSheet("font-size: 13px; font-weight: bold;")
        col_head.addWidget(self.lbl_name)

        # Version
        self.lbl_version = QLabel()
        self.lbl_version.setStyleSheet("font-size: 10px; color: #9aa0a6;")
        col_head.addWidget(self.lbl_version)

        row_top.addLayout(col_head, 1)
        self._layout.addLayout(row_top)

        # 2. Description
        self.lbl_desc = QLabel()
        self.lbl_desc.setWordWrap(True)
        self.lbl_desc.setStyleSheet("font-size: 11px; color: #a0a6b0;")
        self.lbl_desc.setFixedHeight(48)
        self.lbl_desc.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self._layout.addWidget(self.lbl_desc)

        # 3. Status Toggle Row (Enabled Checkbox / Switch)
        row_toggle = QHBoxLayout()
        self.cb_enabled = QCheckBox("Habilitado en el juego")
        self.cb_enabled.setCursor(Qt.PointingHandCursor)
        self.cb_enabled.setChecked(self.pack_info.get("enabled", True))
        self.cb_enabled.clicked.connect(self._on_toggle_clicked)
        row_toggle.addWidget(self.cb_enabled)
        row_toggle.addStretch(1)
        self._layout.addLayout(row_toggle)

        # 4. Action Buttons (Folder, Export, Delete)
        row_actions = QHBoxLayout()
        row_actions.setContentsMargins(0, 2, 0, 0)
        row_actions.setSpacing(6)

        self.btn_open_folder = QPushButton()
        self.btn_open_folder.setToolTip(c.t("UI_PACKS_TOOLTIP_FOLDER"))
        self.btn_open_folder.setCursor(Qt.PointingHandCursor)
        self.btn_open_folder.setFixedSize(28, 24)
        self.btn_open_folder.clicked.connect(self._open_folder)

        self.btn_export = QPushButton()
        self.btn_export.setToolTip(c.t("UI_PACKS_TOOLTIP_EXPORT") if c.t("UI_PACKS_TOOLTIP_EXPORT") else "Exportar pack...")
        self.btn_export.setCursor(Qt.PointingHandCursor)
        self.btn_export.setFixedSize(28, 24)
        self.btn_export.clicked.connect(self._export_pack)

        self.btn_delete = QPushButton()
        self.btn_delete.setToolTip(c.t("UI_PACKS_TOOLTIP_DELETE"))
        self.btn_delete.setCursor(Qt.PointingHandCursor)
        self.btn_delete.setFixedSize(28, 24)
        self.btn_delete.clicked.connect(self._delete_pack)

        row_actions.addWidget(self.btn_open_folder)
        row_actions.addWidget(self.btn_export)
        row_actions.addStretch(1)
        row_actions.addWidget(self.btn_delete)

        self._layout.addLayout(row_actions)

        self._load_data()
        self.update_theme_styles()

    def _load_data(self):
        clean_name = addon_manager.strip_mc_codes(self.pack_info.get("name", "Pack sin nombre"))
        fm = self.lbl_name.fontMetrics()
        self.lbl_name.setText(fm.elidedText(clean_name, Qt.ElideRight, 180))
        self.lbl_name.setToolTip(clean_name)

        clean_desc = addon_manager.strip_mc_codes(self.pack_info.get("desc", ""))
        self.lbl_desc.setText(clean_desc or "Sin descripción proporcionada.")
        self.lbl_desc.setToolTip(clean_desc)

        ver = self.pack_info.get("version", "")
        self.lbl_version.setText(f"Versión: {ver}" if ver else "Versión desconocida")

        ptype = self.pack_info.get("type", "rp")
        if ptype == "rp":
            self.lbl_type_badge.setText("Resource Pack (RP)")
            self.lbl_type_badge.setStyleSheet("""
                background: rgba(16, 185, 129, 0.20);
                color: #10b981;
                font-size: 10px;
                font-weight: bold;
                padding: 2px 6px;
                border-radius: 4px;
                border: 1px solid rgba(16, 185, 129, 0.40);
            """)
        else:
            self.lbl_type_badge.setText("Behavior Pack (BP)")
            self.lbl_type_badge.setStyleSheet("""
                background: rgba(245, 158, 11, 0.20);
                color: #f59e0b;
                font-size: 10px;
                font-weight: bold;
                padding: 2px 6px;
                border-radius: 4px;
                border: 1px solid rgba(245, 158, 11, 0.40);
            """)

        # Thumbnail
        icon_path = self.pack_info.get("icon")
        if icon_path and os.path.exists(icon_path):
            pix = QPixmap(icon_path)
            if not pix.isNull():
                self.lbl_thumb.setPixmap(pix.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                self._draw_default_icon()
        else:
            self._draw_default_icon()

    def _draw_default_icon(self):
        pix = ImageManager.get_icon("pack_pixel.svg").pixmap(40, 40)
        self.lbl_thumb.setPixmap(pix)

    def _on_toggle_clicked(self):
        want_enabled = self.cb_enabled.isChecked()
        self.cb_enabled.setEnabled(False)

        def worker_task():
            return addon_manager.toggle_addon(self.app, self.pack_info)

        self._worker = PackActionWorker(worker_task)
        def on_done(success):
            self.cb_enabled.setEnabled(True)
            if self.parent_tab:
                self.parent_tab.load_packs()
        def on_err(err):
            self.cb_enabled.setEnabled(True)
            self.cb_enabled.setChecked(not want_enabled)
            messagebox.showerror(self.parent_tab or self, "Error", f"No se pudo alternar el estado del pack:\n{err}")

        self._worker.finished.connect(on_done)
        self._worker.error.connect(on_err)
        self._worker.start()

    def _open_folder(self):
        path = self.pack_info.get("path")
        if path and os.path.isdir(path):
            open_folder(path)

    def _export_pack(self):
        path = self.pack_info.get("path")
        if not path or not os.path.isdir(path):
            return

        name = addon_manager.strip_mc_codes(self.pack_info.get("name", "Pack"))
        safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).strip() or "Pack"
        default_export = os.path.expanduser(f"~/Descargas/{safe_name}.mcpack")

        dest = ask_save_filename_native(
            self.parent_tab or self,
            title="Exportar Pack (.mcpack)",
            filetypes=[("Paquete de Minecraft", "*.mcpack"), ("Archivo ZIP", "*.zip")],
            default_name=default_export
        )
        if not dest:
            return

        try:
            addon_manager.export_addon(self.app, self.pack_info, dest)
            icon_check = ImageManager.get_tinted_icon(resource_path("check_circle_icon.svg"), "#10b981", 14)
            if icon_check:
                self.btn_export.setIcon(icon_check)
            QTimer.singleShot(1500, self.update_theme_styles)
        except Exception as e:
            logger.error(f"Error exporting pack to {dest}: {e}")
            messagebox.showerror(self.parent_tab or self, c.t("UI_PACKS_EXPORT_ERROR"), f"No se pudo exportar el pack:\n{e}")

    def _delete_pack(self):
        name = addon_manager.strip_mc_codes(self.pack_info.get("name", "este pack"))
        if messagebox.askyesno(
            self.parent_tab or self,
            c.t("UI_PACKS_TOOLTIP_DELETE"),
            c.t("UI_PACKS_DELETE_CONFIRM", name=name)
        ):
            try:
                addon_manager.delete_addon(self.app, self.pack_info)
                if self.parent_tab:
                    self.parent_tab.load_packs()
            except Exception as e:
                logger.error(f"Error deleting pack {self.pack_info.get('path')}: {e}")
                messagebox.showerror(self.parent_tab or self, "Error", f"No se pudo eliminar el pack:\n{e}")

    def update_theme_styles(self):
        accent = getattr(self.app, "current_accent_color", "#1f6aa5") if self.app else "#1f6aa5"
        is_dark = getattr(self.app, "is_dark_mode", True) if self.app else True

        self.setStyleSheet(f"""
            QFrame#PackCard {{
                background-color: {"rgba(255, 255, 255, 0.05)" if is_dark else "rgba(0, 0, 0, 0.04)"};
                border: 1px solid {"rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.08)"};
                border-radius: 12px;
            }}
            QFrame#PackCard:hover {{
                background-color: {"rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.06)"};
                border: 1px solid {hex_to_rgba(accent, 0.7)};
            }}
        """)

        self.lbl_name.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {'#ffffff' if is_dark else '#18191c'}; background: transparent; border: none;")
        self.lbl_desc.setStyleSheet(f"font-size: 11px; color: {'#a0a6b0' if is_dark else '#4b5563'}; background: transparent; border: none;")
        self.lbl_version.setStyleSheet(f"font-size: 10px; color: {'#9aa0a6' if is_dark else '#6b7280'}; background: transparent; border: none;")
        self.cb_enabled.setStyleSheet(f"font-size: 11px; color: {'#e2e8f0' if is_dark else '#1e293b'}; background: transparent;")

        icon_color = "#ffffff" if is_dark else "#18191c"
        icon_folder = ImageManager.get_tinted_icon(resource_path("folder_browse_icon.svg"), icon_color, 14)
        icon_export = ImageManager.get_tinted_icon(resource_path("export_download_icon.svg"), icon_color, 14)
        icon_trash = ImageManager.get_tinted_icon(resource_path("trash_delete_icon.svg"), "#ef4444", 14)

        if icon_folder:
            self.btn_open_folder.setIcon(icon_folder)
        if icon_export:
            self.btn_export.setIcon(icon_export)
        if icon_trash:
            self.btn_delete.setIcon(icon_trash)

        btn_card_style = f"""
            QPushButton {{
                background: {"rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.05)"};
                border: 1px solid {"rgba(255, 255, 255, 0.10)" if is_dark else "rgba(0, 0, 0, 0.08)"};
                border-radius: 5px;
            }}
            QPushButton:hover {{
                background: {hex_to_rgba(accent, 0.35)};
                border: 1px solid {accent};
            }}
            QToolTip {{
                background-color: {"#181a1f" if is_dark else "#ffffff"};
                color: {"#ffffff" if is_dark else "#18191c"};
                border: 1px solid {"rgba(255, 255, 255, 0.18)" if is_dark else "rgba(0, 0, 0, 0.16)"};
                border-radius: 6px;
                padding: 5px 9px;
                font-size: 11px;
                font-weight: 500;
            }}
        """
        self.btn_open_folder.setStyleSheet(btn_card_style)
        self.btn_export.setStyleSheet(btn_card_style)
        self.btn_delete.setStyleSheet(f"""
            QPushButton {{
                background: {"rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.05)"};
                border: 1px solid {"rgba(255, 255, 255, 0.10)" if is_dark else "rgba(0, 0, 0, 0.08)"};
                border-radius: 5px;
            }}
            QPushButton:hover {{
                background: rgba(239, 68, 68, 0.35);
                border: 1px solid #ef4444;
            }}
            QToolTip {{
                background-color: {"#181a1f" if is_dark else "#ffffff"};
                color: {"#ffffff" if is_dark else "#18191c"};
                border: 1px solid {"rgba(255, 255, 255, 0.18)" if is_dark else "rgba(0, 0, 0, 0.16)"};
                border-radius: 6px;
                padding: 5px 9px;
                font-size: 11px;
                font-weight: 500;
            }}
        """)

    def retranslate_ui(self):
        if hasattr(self, "btn_open_folder"):
            self.btn_open_folder.setToolTip(c.t("UI_PACKS_TOOLTIP_FOLDER"))
        if hasattr(self, "btn_export"):
            self.btn_export.setToolTip(c.t("UI_PACKS_TOOLTIP_EXPORT") if c.t("UI_PACKS_TOOLTIP_EXPORT") else "Exportar pack...")
        if hasattr(self, "btn_delete"):
            self.btn_delete.setToolTip(c.t("UI_PACKS_TOOLTIP_DELETE"))


class PacksTab(QWidget):
    """Packs Management View (Resource Packs & Behavior Packs) for Cianova Launcher."""

    def __init__(self, parent=None, app=None):
        super().__init__(parent)
        self.app = app
        self.setAcceptDrops(True)

        self._all_packs = []
        self._current_filter = "all"  # 'all', 'rp', 'bp'
        self._packs_scan_worker = None
        self._packs_scan_pending = False

        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(28, 24, 28, 20)
        self._main_layout.setSpacing(14)

        # 1. Header (Brand Badge & Titles)
        header_widget = QWidget()
        row_brand = QHBoxLayout(header_widget)
        row_brand.setContentsMargins(0, 0, 0, 0)
        row_brand.setSpacing(14)

        self.badge_pack = QLabel()
        self.badge_pack.setFixedSize(44, 44)
        self.badge_pack.setAlignment(Qt.AlignCenter)
        row_brand.addWidget(self.badge_pack, 0, Qt.AlignVCenter)

        col_brand_text = QVBoxLayout()
        col_brand_text.setContentsMargins(0, 0, 0, 0)
        col_brand_text.setSpacing(2)

        self.lbl_brand_title = QLabel(c.t("UI_PACKS_HEADER_TITLE"))
        self.lbl_brand_sub = QLabel(c.t("UI_PACKS_HEADER_SUB"))
        col_brand_text.addWidget(self.lbl_brand_title)
        col_brand_text.addWidget(self.lbl_brand_sub)
        row_brand.addLayout(col_brand_text, 1)

        header_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self._main_layout.addWidget(header_widget, 0)

        # 2. Row 1: Search + Segmented Filter Chips
        filter_widget = QWidget()
        self.row_filters = QHBoxLayout(filter_widget)
        self.row_filters.setContentsMargins(0, 0, 0, 0)
        self.row_filters.setSpacing(8)

        self.entry_search = QLineEdit()
        self.entry_search.setPlaceholderText(c.t("UI_PACKS_SEARCH_PLACEHOLDER"))
        self.entry_search.setFixedWidth(220)
        self.entry_search.setFixedHeight(32)
        self.entry_search.textChanged.connect(self.render_cards)
        self.row_filters.addWidget(self.entry_search)

        self.btn_filter_all = QPushButton(c.t("UI_PACKS_FILTER_ALL"))
        self.btn_filter_rp = QPushButton(c.t("UI_PACKS_FILTER_RP"))
        self.btn_filter_bp = QPushButton(c.t("UI_PACKS_FILTER_BP"))

        for btn in (self.btn_filter_all, self.btn_filter_rp, self.btn_filter_bp):
            btn.setFixedHeight(32)
            btn.setCursor(Qt.PointingHandCursor)

        self.btn_filter_all.clicked.connect(lambda: self._set_filter("all"))
        self.btn_filter_rp.clicked.connect(lambda: self._set_filter("rp"))
        self.btn_filter_bp.clicked.connect(lambda: self._set_filter("bp"))

        self.row_filters.addWidget(self.btn_filter_all)
        self.row_filters.addWidget(self.btn_filter_rp)
        self.row_filters.addWidget(self.btn_filter_bp)
        self.row_filters.addStretch(1)

        filter_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self._main_layout.addWidget(filter_widget, 0)

        # 3. Row 2: Stats + Action Buttons
        toolbar_widget = QWidget()
        self.row_toolbar = QHBoxLayout(toolbar_widget)
        self.row_toolbar.setContentsMargins(0, 0, 0, 0)
        self._total_cnt = 0
        self.lbl_stats = QLabel(c.t("UI_PACKS_STATS_LABEL", count=0, plural="s"))
        self.lbl_stats.setStyleSheet("font-size: 13px; font-weight: bold; color: #9aa0a6;")
        self.row_toolbar.addWidget(self.lbl_stats)
        self.row_toolbar.addStretch(1)

        self.btn_import = QPushButton(c.t("UI_PACKS_BTN_IMPORT"))
        self.btn_import.setCursor(Qt.PointingHandCursor)
        self.btn_import.setFixedHeight(32)
        self.btn_import.clicked.connect(self._import_pack)
        self.row_toolbar.addWidget(self.btn_import)

        self.btn_open_folder = QPushButton(c.t("UI_PACKS_BTN_OPEN_FOLDER"))
        self.btn_open_folder.setCursor(Qt.PointingHandCursor)
        self.btn_open_folder.setFixedHeight(32)
        self.btn_open_folder.clicked.connect(self._open_packs_folder)
        self.row_toolbar.addWidget(self.btn_open_folder)

        self.btn_refresh = QPushButton("↻")
        self.btn_refresh.setToolTip(c.t("UI_MODS_BTN_REFRESH"))
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_refresh.setFixedSize(32, 32)
        self.btn_refresh.clicked.connect(self.load_packs)
        self.row_toolbar.addWidget(self.btn_refresh)

        toolbar_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self._main_layout.addWidget(toolbar_widget, 0)

        # 4. Empty State Card
        self.card_empty = QFrame()
        self.card_empty.setObjectName("EmptyPacksCard")
        empty_layout = QVBoxLayout(self.card_empty)
        empty_layout.setContentsMargins(24, 32, 24, 32)
        empty_layout.setSpacing(10)
        empty_layout.setAlignment(Qt.AlignCenter)

        self.lbl_empty_title = QLabel(c.t("UI_PACKS_EMPTY_TITLE"))
        self.lbl_empty_title.setAlignment(Qt.AlignCenter)
        self.lbl_empty_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #ffffff;")
        empty_layout.addWidget(self.lbl_empty_title)

        self.lbl_empty_desc = QLabel(c.t("UI_PACKS_EMPTY_SUB"))
        self.lbl_empty_desc.setAlignment(Qt.AlignCenter)
        self.lbl_empty_desc.setWordWrap(True)
        self.lbl_empty_desc.setStyleSheet("font-size: 12px; color: #a0a6b0; max-width: 500px;")
        empty_layout.addWidget(self.lbl_empty_desc)

        row_empty_btns = QHBoxLayout()
        row_empty_btns.setSpacing(10)

        self.btn_empty_import = QPushButton(c.t("UI_PACKS_BTN_IMPORT"))
        self.btn_empty_import.setCursor(Qt.PointingHandCursor)
        self.btn_empty_import.setFixedHeight(36)
        self.btn_empty_import.clicked.connect(self._import_pack)

        self.btn_empty_open = QPushButton(c.t("UI_PACKS_BTN_OPEN_PACKS_FOLDER"))
        self.btn_empty_open.setCursor(Qt.PointingHandCursor)
        self.btn_empty_open.setFixedHeight(36)
        self.btn_empty_open.clicked.connect(self._open_packs_folder)

        row_empty_btns.addWidget(self.btn_empty_import)
        row_empty_btns.addWidget(self.btn_empty_open)
        empty_layout.addLayout(row_empty_btns)

        self._main_layout.addWidget(self.card_empty)

        # 5. Scroll Area with FlowLayout Grid
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("background: transparent; border: none;")

        self.grid_container = QWidget()
        self.grid_layout = FlowLayout(self.grid_container, margin=0, h_spacing=14, v_spacing=14)
        self.scroll_area.setWidget(self.grid_container)

        self._main_layout.addWidget(self.scroll_area, 1)

        self.update_theme_styles()

    def _set_filter(self, filter_mode: str):
        self._current_filter = filter_mode
        self._update_filter_button_styles()
        self.render_cards()

    def _update_filter_button_styles(self):
        accent = getattr(self.app, "current_accent_color", "#1f6aa5") if self.app else "#1f6aa5"
        is_dark = getattr(self.app, "is_dark_mode", True) if self.app else True

        for mode, btn in (("all", self.btn_filter_all), ("rp", self.btn_filter_rp), ("bp", self.btn_filter_bp)):
            is_active = (self._current_filter == mode)
            if is_active:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {accent};
                        color: #ffffff;
                        border: none;
                        border-radius: 8px;
                        padding: 0 14px;
                        font-size: 11px;
                        font-weight: bold;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {"rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.06)"};
                        color: {'#ffffff' if is_dark else '#18191c'};
                        border: 1px solid {"rgba(255, 255, 255, 0.12)" if is_dark else "rgba(0, 0, 0, 0.10)"};
                        border-radius: 8px;
                        padding: 0 14px;
                        font-size: 11px;
                        font-weight: 500;
                    }}
                    QPushButton:hover {{
                        background: {hex_to_rgba(accent, 0.30)};
                        border: 1px solid {accent};
                    }}
                """)

    def _open_packs_folder(self):
        com_mojang = addon_manager.get_com_mojang_path(getattr(self.app, "active_path", None))
        if com_mojang and os.path.exists(com_mojang):
            rp_path = os.path.join(com_mojang, "resource_packs")
            os.makedirs(rp_path, exist_ok=True)
            open_folder(rp_path)

    def _import_pack(self):
        file_path = ask_open_filename_native(
            self,
            title="Importar Pack de Recursos o Comportamientos",
            filetypes=[("Packs de Minecraft", "*.mcpack *.mcaddon *.zip"), ("Todos los archivos", "*.*")],
            initial_dir=os.path.expanduser("~/Descargas")
        )
        if not file_path or not os.path.isfile(file_path):
            return

        self._install_file(file_path)

    def _install_file(self, file_path: str):
        def worker():
            return addon_manager.install_addon_file(self.app, file_path)

        self._import_worker = PackActionWorker(worker)
        def on_done(res):
            bname = os.path.basename(file_path)
            messagebox.showinfo(self, c.t("UI_PACK_INSTALLED"), c.t("UI_PACKS_IMPORT_SUCCESS", bname=bname))
            self.load_packs()
        def on_err(err):
            logger.error(f"Error installing pack {file_path}: {err}")
            messagebox.showerror(self, c.t("UI_PACKS_IMPORT_ERROR"), f"No se pudo instalar el pack:\n{err}")

        self._import_worker.finished.connect(on_done)
        self._import_worker.error.connect(on_err)
        self._import_worker.start()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                ext = os.path.splitext(url.toLocalFile())[1].lower()
                if ext in (".mcpack", ".mcaddon", ".zip"):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                fp = url.toLocalFile()
                ext = os.path.splitext(fp)[1].lower()
                if ext in (".mcpack", ".mcaddon", ".zip"):
                    self._install_file(fp)
            event.acceptProposedAction()

    def load_packs(self):
        """Scan packs in the background so opening the tab remains instant."""
        if self._packs_scan_worker and self._packs_scan_worker.isRunning():
            self._packs_scan_pending = True
            return

        self._packs_scan_worker = PackActionWorker(addon_manager.scan_all_addons, self.app)
        self._packs_scan_worker.finished.connect(self._on_packs_loaded)
        self._packs_scan_worker.error.connect(self._on_packs_load_error)
        self._packs_scan_worker.start()

    def _on_packs_loaded(self, raw_addons):
        # Filter only rp and bp (exclude worlds).
        self._all_packs = [item for item in raw_addons if item.get("type") in ("rp", "bp")]
        self._packs_scan_worker = None
        self.render_cards()
        if self._packs_scan_pending:
            self._packs_scan_pending = False
            self.load_packs()

    def _on_packs_load_error(self, error):
        logger.error("Error scanning packs: %s", error)
        self._all_packs = []
        self._packs_scan_worker = None
        self.render_cards()
        if self._packs_scan_pending:
            self._packs_scan_pending = False
            self.load_packs()

    def render_cards(self):
        clear_layout(self.grid_layout)

        query = self.entry_search.text().strip().lower()
        filtered = []

        for p in self._all_packs:
            ptype = p.get("type")
            if self._current_filter == "rp" and ptype != "rp":
                continue
            if self._current_filter == "bp" and ptype != "bp":
                continue

            name = addon_manager.strip_mc_codes(p.get("name", "")).lower()
            desc = addon_manager.strip_mc_codes(p.get("desc", "")).lower()
            if query and query not in name and query not in desc:
                continue
            filtered.append(p)

        total_cnt = len(self._all_packs)
        active_cnt = sum(1 for p in self._all_packs if p.get("enabled", True))
        self._total_cnt = total_cnt
        self._active_cnt = active_cnt
        self.lbl_stats.setText(c.t("UI_PACKS_STATS_LABEL", count=total_cnt, plural="s" if total_cnt != 1 else ""))

        if not filtered:
            self.card_empty.show()
            self.scroll_area.hide()
        else:
            self.card_empty.hide()
            self.scroll_area.show()
            for p in filtered:
                card = PackCardWidget(p, app=self.app, parent_tab=self)
                self.grid_layout.addWidget(card)

    def showEvent(self, event):
        super().showEvent(event)
        self.load_packs()

    def update_theme_styles(self):
        accent = getattr(self.app, "current_accent_color", "#1f6aa5") if self.app else "#1f6aa5"
        is_dark = getattr(self.app, "is_dark_mode", True) if self.app else True

        # Titles
        self.lbl_brand_title.setStyleSheet(
            f"font-size: 16px; font-weight: 900; letter-spacing: 0.6px; color: {'#ffffff' if is_dark else '#111214'}; background: transparent; border: none;"
        )
        self.lbl_brand_sub.setStyleSheet(
            f"font-size: 13px; font-weight: {'normal' if is_dark else '500'}; color: {'#9aa0a6' if is_dark else '#2c2f36'}; background: transparent; border: none;"
        )

        # Brand Badge Icon
        self.badge_pack.setStyleSheet(f"""
            background-color: {"rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.06)"};
            border: 1px solid {"rgba(255, 255, 255, 0.12)" if is_dark else "rgba(0, 0, 0, 0.08)"};
            border-radius: 12px;
        """)
        icon_path = resource_path("pack_pixel.svg")
        if os.path.exists(icon_path):
            if is_dark:
                icon = ImageManager.get_icon("pack_pixel.svg")
                pix = QPixmap(24, 24)
                pix.fill(Qt.transparent)
                p = QPainter(pix)
                p.setRenderHint(QPainter.Antialiasing)
                p.setRenderHint(QPainter.SmoothPixmapTransform)
                icon.paint(p, QRect(0, 0, 24, 24))
                p.end()
                self.badge_pack.setPixmap(pix)
            else:
                try:
                    with open(icon_path, "r", encoding="utf-8") as f:
                        svg_content = f.read()
                    svg_light = svg_content.replace('fill="#ffffff"', 'fill="#18191c"').replace('fill="#1e1e24"', 'fill="#f3f4f6"')
                    from PySide6.QtSvg import QSvgRenderer
                    renderer = QSvgRenderer(svg_light.encode("utf-8"))
                    pix = QPixmap(24, 24)
                    pix.fill(Qt.transparent)
                    p = QPainter(pix)
                    renderer.render(p)
                    p.end()
                    self.badge_pack.setPixmap(pix)
                except Exception:
                    self.badge_pack.setPixmap(ImageManager.get_icon("pack_pixel.svg").pixmap(24, 24))

        # Search Input Style
        self.entry_search.setStyleSheet(f"""
            QLineEdit {{
                background-color: {"rgba(255, 255, 255, 0.06)" if is_dark else "rgba(0, 0, 0, 0.04)"};
                color: {'#ffffff' if is_dark else '#18191c'};
                border: 1px solid {"rgba(255, 255, 255, 0.12)" if is_dark else "rgba(0, 0, 0, 0.10)"};
                border-radius: 8px;
                padding: 0 10px;
                font-size: 12px;
            }}
            QLineEdit:focus {{
                border: 1px solid {accent};
            }}
        """)

        # Buttons
        self._update_filter_button_styles()

        self.btn_import.setStyleSheet(f"""
            QPushButton {{
                background-color: {accent};
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 0 14px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {adjust_color(accent, 1.15)};
            }}
        """)

        btn_top_style = f"""
            QPushButton {{
                background: {"rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.06)"};
                color: {'#ffffff' if is_dark else '#18191c'};
                border: 1px solid {"rgba(255, 255, 255, 0.12)" if is_dark else "rgba(0, 0, 0, 0.10)"};
                border-radius: 8px;
                padding: 0 14px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {hex_to_rgba(accent, 0.30)};
                border: 1px solid {accent};
            }}
        """
        self.btn_open_folder.setStyleSheet(btn_top_style)
        self.btn_refresh.setStyleSheet(btn_top_style)

        # Empty State Card
        self.card_empty.setStyleSheet(f"""
            QFrame#EmptyPacksCard {{
                background-color: {"rgba(255, 255, 255, 0.04)" if is_dark else "rgba(0, 0, 0, 0.03)"};
                border: 1.5px dashed {"rgba(255, 255, 255, 0.12)" if is_dark else "rgba(0, 0, 0, 0.10)"};
                border-radius: 14px;
            }}
        """)
        self.lbl_empty_title.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {'#ffffff' if is_dark else '#18191c'}; background: transparent;")
        self.lbl_empty_desc.setStyleSheet(f"font-size: 12px; color: {'#a0a6b0' if is_dark else '#4b5563'}; background: transparent;")

        self.btn_empty_import.setStyleSheet(f"""
            QPushButton {{
                background-color: {accent};
                color: #ffffff;
                border: none;
                border-radius: 8px;
                font-size: 12px;
                font-weight: bold;
                padding: 0 16px;
            }}
            QPushButton:hover {{
                background-color: {adjust_color(accent, 1.15)};
            }}
        """)
        self.btn_empty_open.setStyleSheet(f"""
            QPushButton {{
                background: {"rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.06)"};
                color: {'#ffffff' if is_dark else '#18191c'};
                border: 1px solid {"rgba(255, 255, 255, 0.12)" if is_dark else "rgba(0, 0, 0, 0.10)"};
                border-radius: 8px;
                font-size: 12px;
                font-weight: bold;
                padding: 0 16px;
            }}
            QPushButton:hover {{
                background: {hex_to_rgba(accent, 0.30)};
                border: 1px solid {accent};
            }}
        """)

        # Update cards
        if hasattr(self, "grid_layout"):
            for i in range(self.grid_layout.count()):
                item = self.grid_layout.itemAt(i)
                if item and item.widget() and hasattr(item.widget(), "update_theme_styles"):
                    item.widget().update_theme_styles()

    def retranslate_ui(self):
        if hasattr(self, "lbl_brand_title"):
            self.lbl_brand_title.setText(c.t("UI_PACKS_HEADER_TITLE"))
        if hasattr(self, "lbl_brand_sub"):
            self.lbl_brand_sub.setText(c.t("UI_PACKS_HEADER_SUB"))
        if hasattr(self, "entry_search"):
            self.entry_search.setPlaceholderText(c.t("UI_PACKS_SEARCH_PLACEHOLDER"))
        if hasattr(self, "btn_filter_all"):
            self.btn_filter_all.setText(c.t("UI_PACKS_FILTER_ALL"))
        if hasattr(self, "btn_filter_rp"):
            self.btn_filter_rp.setText(c.t("UI_PACKS_FILTER_RP"))
        if hasattr(self, "btn_filter_bp"):
            self.btn_filter_bp.setText(c.t("UI_PACKS_FILTER_BP"))
        if hasattr(self, "btn_import"):
            self.btn_import.setText(c.t("UI_PACKS_BTN_IMPORT"))
        if hasattr(self, "btn_open_folder"):
            self.btn_open_folder.setText(c.t("UI_PACKS_BTN_OPEN_FOLDER"))
        if hasattr(self, "btn_refresh"):
            self.btn_refresh.setToolTip(c.t("UI_MODS_BTN_REFRESH"))
        if hasattr(self, "lbl_empty_title"):
            self.lbl_empty_title.setText(c.t("UI_PACKS_EMPTY_TITLE"))
        if hasattr(self, "lbl_empty_desc"):
            self.lbl_empty_desc.setText(c.t("UI_PACKS_EMPTY_SUB"))
        if hasattr(self, "btn_empty_import"):
            self.btn_empty_import.setText(c.t("UI_PACKS_BTN_IMPORT"))
        if hasattr(self, "btn_empty_open"):
            self.btn_empty_open.setText(c.t("UI_PACKS_BTN_OPEN_PACKS_FOLDER"))
        total = getattr(self, "_total_cnt", 0)
        if hasattr(self, "lbl_stats"):
            self.lbl_stats.setText(c.t("UI_PACKS_STATS_LABEL", count=total, plural="s" if total != 1 else ""))
        if hasattr(self, "grid_layout"):
            for i in range(self.grid_layout.count()):
                item = self.grid_layout.itemAt(i)
                if item and item.widget() and hasattr(item.widget(), "retranslate_ui"):
                    item.widget().retranslate_ui()
