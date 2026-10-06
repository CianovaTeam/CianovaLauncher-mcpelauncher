import os
import shutil
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QFrame, QLineEdit,
    QSlider, QWidget
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen
from src import constants as c
from src.gui import custom_dialogs as messagebox
from src.utils.dialogs import ask_open_filename_native
from src.utils.image_manager import ImageManager
from src.utils.colors import hex_to_rgba, adjust_color, blend_colors


class SleekVersionEditDialog(QDialog):
    """
    Modern, theme-integrated dialog for editing and customizing a specific installed version:
    rename, custom icon with live zoom & XY offset preview, and desktop shortcuts.
    """
    def __init__(self, app, target_version=None, parent=None):
        super().__init__(parent or (app if isinstance(app, QWidget) else None))
        self.app = app
        self.target_version = target_version or ""
        self.setObjectName("SleekVersionEditDialog")
        self.setWindowTitle(f"{c.t('UI_VM_TITLE')} - {self.target_version}")
        self.setFixedSize(540, 620)
        self.setModal(True)
        self._loading = True

        self._setup_ui()
        self._load_version_data()
        self._loading = False
        self._apply_theme_styles()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(14)

        # 1. Header
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(10)

        self.lbl_title = QLabel(c.t("UI_VM_TITLE"))
        self.lbl_title.setStyleSheet("font-size: 17px; font-weight: bold;")
        header_row.addWidget(self.lbl_title, 1)

        main_layout.addLayout(header_row)

        # Scroll Area for Content
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setStyleSheet("background: transparent; border: none;")

        self.container = QWidget()
        self.container.setStyleSheet("background: transparent;")
        self.c_layout = QVBoxLayout(self.container)
        self.c_layout.setContentsMargins(0, 0, 0, 0)
        self.c_layout.setSpacing(12)

        # 2. Card: Rename Version
        self.card_rename = QFrame()
        self.card_rename.setObjectName("EditCard")
        rn_layout = QVBoxLayout(self.card_rename)
        rn_layout.setContentsMargins(16, 12, 16, 12)
        rn_layout.setSpacing(8)

        self.lbl_rn_title = QLabel(c.t("UI_VM_VERSION_NAME"))
        rn_layout.addWidget(self.lbl_rn_title)

        row_rn_inputs = QHBoxLayout()
        row_rn_inputs.setSpacing(10)

        self.entry_rename = QLineEdit()
        self.entry_rename.setFixedHeight(38)
        row_rn_inputs.addWidget(self.entry_rename, 1)

        self.btn_rename = QPushButton(c.t("UI_VM_BTN_RENAME"))
        self.btn_rename.setFixedHeight(38)
        self.btn_rename.setFixedWidth(100)
        self.btn_rename.setCursor(Qt.PointingHandCursor)
        self.btn_rename.clicked.connect(self.rename_version)
        row_rn_inputs.addWidget(self.btn_rename)

        rn_layout.addLayout(row_rn_inputs)
        self.c_layout.addWidget(self.card_rename)

        # 3. Card: Custom Icon
        self.card_icon = QFrame()
        self.card_icon.setObjectName("EditCard")
        ic_layout = QVBoxLayout(self.card_icon)
        ic_layout.setContentsMargins(16, 12, 16, 12)
        ic_layout.setSpacing(10)

        self.lbl_ic_title = QLabel(c.t("UI_VM_CUSTOM_ICON"))
        ic_layout.addWidget(self.lbl_ic_title)

        # Buttons row
        row_ic_btns = QHBoxLayout()
        row_ic_btns.setSpacing(10)

        self.btn_change_icon = QPushButton(c.t("UI_VM_BTN_CHOOSE_IMG"))
        self.btn_change_icon.setFixedHeight(32)
        self.btn_change_icon.setCursor(Qt.PointingHandCursor)
        self.btn_change_icon.clicked.connect(self.change_icon)
        row_ic_btns.addWidget(self.btn_change_icon)

        self.btn_reset_icon = QPushButton(c.t("UI_VM_BTN_RESET"))
        self.btn_reset_icon.setFixedHeight(32)
        self.btn_reset_icon.setCursor(Qt.PointingHandCursor)
        self.btn_reset_icon.clicked.connect(self.reset_icon)
        row_ic_btns.addWidget(self.btn_reset_icon)

        ic_layout.addLayout(row_ic_btns)

        # Live Preview & Sliders Row
        row_preview_and_sliders = QHBoxLayout()
        row_preview_and_sliders.setSpacing(14)

        # 110x110 Preview Box
        self.box_preview = QFrame()
        self.box_preview.setObjectName("PreviewBox")
        self.box_preview.setFixedSize(110, 110)

        self.lbl_preview = QLabel(self.box_preview)
        self.lbl_preview.setStyleSheet("background: transparent; border: none;")
        row_preview_and_sliders.addWidget(self.box_preview, 0, Qt.AlignCenter)

        # Sliders Column
        col_sliders = QVBoxLayout()
        col_sliders.setSpacing(6)

        # Zoom Slider
        row_zoom = QHBoxLayout()
        self.lbl_z = QLabel(c.t("UI_VM_ZOOM"))
        self.lbl_z.setFixedWidth(50)
        row_zoom.addWidget(self.lbl_z)
        self.slider_zoom = QSlider(Qt.Horizontal)
        self.slider_zoom.setRange(10, 300)
        self.slider_zoom.setValue(100)
        self.slider_zoom.valueChanged.connect(self.update_personalization)
        self.slider_zoom.sliderReleased.connect(self.on_personalization_released)
        row_zoom.addWidget(self.slider_zoom, 1)
        self.lbl_zoom_val = QLabel("100%")
        self.lbl_zoom_val.setFixedWidth(40)
        row_zoom.addWidget(self.lbl_zoom_val)
        col_sliders.addLayout(row_zoom)

        # Pos X Slider
        row_x = QHBoxLayout()
        self.lbl_x = QLabel(c.t("UI_VM_POS_X"))
        self.lbl_x.setFixedWidth(50)
        row_x.addWidget(self.lbl_x)
        self.slider_x = QSlider(Qt.Horizontal)
        self.slider_x.setRange(-100, 100)
        self.slider_x.setValue(0)
        self.slider_x.valueChanged.connect(self.update_personalization)
        self.slider_x.sliderReleased.connect(self.on_personalization_released)
        row_x.addWidget(self.slider_x, 1)
        self.lbl_x_val = QLabel("0")
        self.lbl_x_val.setFixedWidth(40)
        row_x.addWidget(self.lbl_x_val)
        col_sliders.addLayout(row_x)

        # Pos Y Slider
        row_y = QHBoxLayout()
        self.lbl_y = QLabel(c.t("UI_VM_POS_Y"))
        self.lbl_y.setFixedWidth(50)
        row_y.addWidget(self.lbl_y)
        self.slider_y = QSlider(Qt.Horizontal)
        self.slider_y.setRange(-100, 100)
        self.slider_y.setValue(0)
        self.slider_y.valueChanged.connect(self.update_personalization)
        self.slider_y.sliderReleased.connect(self.on_personalization_released)
        row_y.addWidget(self.slider_y, 1)
        self.lbl_y_val = QLabel("0")
        self.lbl_y_val.setFixedWidth(40)
        row_y.addWidget(self.lbl_y_val)
        col_sliders.addLayout(row_y)

        row_preview_and_sliders.addLayout(col_sliders, 1)
        ic_layout.addLayout(row_preview_and_sliders)

        self.c_layout.addWidget(self.card_icon)

        # 4. Card: Shortcuts
        self.card_shortcuts = QFrame()
        self.card_shortcuts.setObjectName("EditCard")
        sc_layout = QVBoxLayout(self.card_shortcuts)
        sc_layout.setContentsMargins(16, 12, 16, 12)
        sc_layout.setSpacing(8)

        self.lbl_sc_title = QLabel(c.t("UI_VM_SHORTCUTS"))
        sc_layout.addWidget(self.lbl_sc_title)

        row_sc_btns = QHBoxLayout()
        row_sc_btns.setSpacing(10)

        self.btn_create_shortcut = QPushButton(c.t("UI_VM_BTN_CREATE_SC"))
        self.btn_create_shortcut.setFixedHeight(34)
        self.btn_create_shortcut.setCursor(Qt.PointingHandCursor)
        self.btn_create_shortcut.clicked.connect(self.create_shortcut)
        row_sc_btns.addWidget(self.btn_create_shortcut, 1)

        self.btn_remove_shortcut = QPushButton(c.t("UI_VM_BTN_REMOVE_SC"))
        self.btn_remove_shortcut.setFixedHeight(34)
        self.btn_remove_shortcut.setCursor(Qt.PointingHandCursor)
        self.btn_remove_shortcut.clicked.connect(self.remove_shortcut)
        row_sc_btns.addWidget(self.btn_remove_shortcut, 1)

        sc_layout.addLayout(row_sc_btns)
        self.c_layout.addWidget(self.card_shortcuts)

        self.scroll_area.setWidget(self.container)
        main_layout.addWidget(self.scroll_area, 1)

        # Bottom row: Close and Save buttons
        row_bottom = QHBoxLayout()
        row_bottom.setSpacing(10)
        row_bottom.addStretch(1)

        self.btn_close = QPushButton(c.t("UI_DEPS_BTN_CLOSE"))
        self.btn_close.setFixedHeight(36)
        self.btn_close.setFixedWidth(100)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.clicked.connect(self.reject)
        row_bottom.addWidget(self.btn_close)

        self.btn_save = QPushButton(c.t("UI_BUTTON_SAVE"))
        self.btn_save.setFixedHeight(36)
        self.btn_save.setFixedWidth(110)
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.clicked.connect(self.save_and_close)
        row_bottom.addWidget(self.btn_save)

        main_layout.addLayout(row_bottom)

    def _load_version_data(self):
        v = self.target_version
        if not v:
            vers = self.app.logic.get_installed_versions(self.app)
            v = vers[0] if vers else ""
            self.target_version = v

        self.lbl_title.setText(f"{c.t('UI_VM_TITLE')} ({v})")
        self.entry_rename.setText(v)

        zooms = self.app.config_manager.get(c.CONFIG_KEY_VERSION_ICON_ZOOM, {}) or {}
        zoom = zooms.get(v, 100)
        self.slider_zoom.setValue(zoom)
        self.lbl_zoom_val.setText(f"{zoom}%")

        xs = self.app.config_manager.get(c.CONFIG_KEY_VERSION_ICON_X, {}) or {}
        x = xs.get(v, 0)
        self.slider_x.setValue(x)
        self.lbl_x_val.setText(str(x))

        ys = self.app.config_manager.get(c.CONFIG_KEY_VERSION_ICON_Y, {}) or {}
        y = ys.get(v, 0)
        self.slider_y.setValue(y)
        self.lbl_y_val.setText(str(y))

        self.update_preview()

    def _apply_theme_styles(self):
        accent = getattr(self.app, "current_accent_color", "#1f6aa5") if self.app else "#1f6aa5"
        is_dark = getattr(self.app, "is_dark_mode", True) if self.app else True

        self.setStyleSheet(f"""
            QDialog#SleekVersionEditDialog {{
                background-color: {"#121316" if is_dark else "#f0f2f5"};
            }}
            QFrame#EditCard {{
                background-color: {"rgba(255, 255, 255, 0.055)" if is_dark else "rgba(0, 0, 0, 0.04)"};
                border: 1px solid {hex_to_rgba(accent, 0.40) if is_dark else hex_to_rgba(accent, 0.30)};
                border-radius: 12px;
            }}
            QFrame#PreviewBox {{
                background-color: {"rgba(0, 0, 0, 0.35)" if is_dark else "rgba(0, 0, 0, 0.06)"};
                border: 1.5px solid {hex_to_rgba(accent, 0.45)};
                border-radius: 10px;
            }}
            QLineEdit {{
                background-color: {"rgba(255, 255, 255, 0.08)" if is_dark else "#ffffff"};
                color: {'#ffffff' if is_dark else '#111214'};
                border: 1.5px solid {hex_to_rgba(accent, 0.50) if is_dark else hex_to_rgba(accent, 0.60)};
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border: 2px solid {accent};
            }}
            QSlider::groove:horizontal {{
                height: 4px;
                background: {"rgba(255, 255, 255, 0.15)" if is_dark else "rgba(0, 0, 0, 0.15)"};
                border-radius: 2px;
            }}
            QSlider::sub-page:horizontal {{
                background: {accent};
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: {accent};
                border: 2px solid white;
                width: 14px;
                height: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }}
        """)

        self.lbl_title.setStyleSheet(f"font-size: 17px; font-weight: bold; color: {'#ffffff' if is_dark else '#111214'}; background: transparent; border: none;")

        btn_primary_css = f"""
            QPushButton {{
                background: {accent};
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {adjust_color(accent, 20)};
            }}
        """
        btn_secondary_css = f"""
            QPushButton {{
                background: {"rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.06)"};
                color: {'#ffffff' if is_dark else '#18191c'};
                border: 1px solid {'rgba(255, 255, 255, 0.18)' if is_dark else 'rgba(0, 0, 0, 0.22)'};
                border-radius: 8px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: {"rgba(255, 255, 255, 0.15)" if is_dark else "rgba(0, 0, 0, 0.12)"};
            }}
        """

        self.btn_rename.setStyleSheet(btn_primary_css)
        self.btn_change_icon.setStyleSheet(btn_secondary_css)
        self.btn_reset_icon.setStyleSheet(btn_secondary_css)
        self.btn_create_shortcut.setStyleSheet(btn_primary_css)
        self.btn_remove_shortcut.setStyleSheet(btn_secondary_css)
        self.btn_close.setStyleSheet(btn_secondary_css)
        self.btn_save.setStyleSheet(btn_primary_css)

        label_title_css = f"font-size: 13px; font-weight: bold; color: {'#ffffff' if is_dark else '#111214'}; background: transparent; border: none;"
        if hasattr(self, "lbl_rn_title"): self.lbl_rn_title.setStyleSheet(label_title_css)
        if hasattr(self, "lbl_ic_title"): self.lbl_ic_title.setStyleSheet(label_title_css)
        if hasattr(self, "lbl_sc_title"): self.lbl_sc_title.setStyleSheet(label_title_css)

        slider_lbl_css = f"font-size: 11px; color: {'#8ea3b0' if is_dark else '#2c2f36'}; background: transparent; border: none;"
        for lbl in [getattr(self, "lbl_z", None), getattr(self, "lbl_x", None), getattr(self, "lbl_y", None),
                    getattr(self, "lbl_zoom_val", None), getattr(self, "lbl_x_val", None), getattr(self, "lbl_y_val", None)]:
            if lbl: lbl.setStyleSheet(slider_lbl_css)

        self.entry_rename.setStyleSheet(f"""
            QLineEdit {{
                background-color: {"rgba(255, 255, 255, 0.08)" if is_dark else "#ffffff"};
                color: {'#ffffff' if is_dark else '#111214'};
                border: 1.5px solid {hex_to_rgba(accent, 0.50) if is_dark else hex_to_rgba(accent, 0.60)};
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 13px;
                font-weight: 500;
            }}
            QLineEdit:focus {{
                border: 2px solid {accent};
            }}
        """)

    def save_and_close(self):
        """Save rename, icon zoom & offsets, refresh launcher, and close dialog."""
        new_name = self.entry_rename.text().strip()
        if new_name and new_name != self.target_version:
            if self.app.logic.rename_version(self.app, self.target_version, new_name):
                self.target_version = new_name

        if self.target_version:
            self.app.config_manager.set(c.CONFIG_KEY_VERSION_ICON_ZOOM, self.app.config_manager.get(c.CONFIG_KEY_VERSION_ICON_ZOOM, {}))
            self.app.config_manager.set(c.CONFIG_KEY_VERSION_ICON_X, self.app.config_manager.get(c.CONFIG_KEY_VERSION_ICON_X, {}))
            self.app.config_manager.set(c.CONFIG_KEY_VERSION_ICON_Y, self.app.config_manager.get(c.CONFIG_KEY_VERSION_ICON_Y, {}))

        if hasattr(self.app, "logic") and hasattr(self.app.logic, "refresh_version_list"):
            self.app.logic.refresh_version_list(self.app)

        self.accept()

    def update_personalization(self):
        """Update icon labels and preview live while dragging."""
        if getattr(self, "_loading", False):
            return
        version = self.target_version
        if not version: return

        zoom = self.slider_zoom.value()
        x = self.slider_x.value()
        y = self.slider_y.value()

        self.lbl_zoom_val.setText(f"{zoom}%")
        self.lbl_x_val.setText(str(x))
        self.lbl_y_val.setText(str(y))

        zooms = self.app.config_manager.get(c.CONFIG_KEY_VERSION_ICON_ZOOM, {}) or {}
        zooms[version] = zoom
        self.app.config_manager.set(c.CONFIG_KEY_VERSION_ICON_ZOOM, zooms)

        xs = self.app.config_manager.get(c.CONFIG_KEY_VERSION_ICON_X, {}) or {}
        xs[version] = x
        self.app.config_manager.set(c.CONFIG_KEY_VERSION_ICON_X, xs)

        ys = self.app.config_manager.get(c.CONFIG_KEY_VERSION_ICON_Y, {}) or {}
        ys[version] = y
        self.app.config_manager.set(c.CONFIG_KEY_VERSION_ICON_Y, ys)

        self.update_preview()

    def on_personalization_released(self):
        """Save icon personalization on slider release."""
        self.update_personalization()
        if hasattr(self.app, "logic") and hasattr(self.app.logic, "refresh_version_list"):
            self.app.logic.refresh_version_list(self.app)

    def update_preview(self):
        """Refresh the icon preview with current zoom and position settings."""
        version = self.target_version
        if not version: return

        vdir = os.path.join(self.app.active_path, c.VERSIONS_DIR, version)
        pix = None
        for ext in [".svg", ".png", ".jpg", ".jpeg", ".webp"]:
            icon_p = os.path.join(vdir, "icon" + ext)
            if os.path.exists(icon_p):
                pix = ImageManager.get_image(icon_p, size=(64, 64))
                break

        if not pix or pix.isNull():
            pix = (
                ImageManager.get_image("assets/minecraft_logo.svg", size=(64, 64))
                or ImageManager.get_image("minecraft_logo.svg", size=(64, 64))
                or ImageManager.get_image("minecraft_logo.png", size=(64, 64))
                or ImageManager.get_icon("icon.png").pixmap(64, 64)
            )

        zoom = self.slider_zoom.value() / 100.0
        x = self.slider_x.value()
        y = self.slider_y.value()

        sw = max(10, int(64 * zoom))
        sh = max(10, int(64 * zoom))
        scaled_pix = pix.scaled(sw, sh, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.lbl_preview.setPixmap(scaled_pix)
        self.lbl_preview.setFixedSize(scaled_pix.size())
        # Center in 110x110 box with offsets
        self.lbl_preview.move(int((110 - scaled_pix.width()) // 2 + x), int((110 - scaled_pix.height()) // 2 + y))

    def rename_version(self):
        """Rename the version folder and update target."""
        old = self.target_version
        new = self.entry_rename.text().strip()
        if not new or old == new: return

        if self.app.logic.rename_version(self.app, old, new):
            self.target_version = new
            self.lbl_title.setText(f"{c.t('UI_VM_TITLE')} ({new})")
            self.setWindowTitle(f"{c.t('UI_VM_TITLE')} - {new}")
            messagebox.showinfo(self, c.t("UI_SUCCESS_TITLE"), c.t("UI_SAVE_SUCCESS_MSG"))

    def reset_icon(self):
        """Remove custom icon file and reset sliders in live."""
        version = self.target_version
        if not version: return
        vdir = os.path.join(self.app.active_path, c.VERSIONS_DIR, version)
        try:
            for f in os.listdir(vdir):
                if f.startswith("icon."):
                    os.remove(os.path.join(vdir, f))

            ImageManager.invalidate()

            self._loading = True
            self.slider_zoom.setValue(100)
            self.slider_x.setValue(0)
            self.slider_y.setValue(0)
            self.lbl_zoom_val.setText("100%")
            self.lbl_x_val.setText("0")
            self.lbl_y_val.setText("0")
            self._loading = False

            for key in [c.CONFIG_KEY_VERSION_ICON_ZOOM, c.CONFIG_KEY_VERSION_ICON_X, c.CONFIG_KEY_VERSION_ICON_Y]:
                d = self.app.config_manager.get(key, {}) or {}
                if version in d:
                    d.pop(version, None)
                    self.app.config_manager.set(key, d)

            self.update_preview()
            if hasattr(self.app.logic, "refresh_version_list"):
                self.app.logic.refresh_version_list(self.app)
            messagebox.showinfo(self, c.t("UI_SUCCESS_TITLE"), c.t("UI_VM_ICON_RESET_SUCCESS"))
        except Exception as e:
            messagebox.showerror(self, c.t("UI_ERROR_TITLE"), str(e))

    def change_icon(self):
        """Pick a new image file and set it as custom icon."""
        version = self.target_version
        if not version: return

        p = ask_open_filename_native(self, title=c.t("UI_BUTTON_CHANGE_ICON"))
        if p:
            vdir = os.path.join(self.app.active_path, c.VERSIONS_DIR, version)
            ext = os.path.splitext(p)[1].lower()
            target = os.path.join(vdir, "icon" + ext)
            try:
                for f in os.listdir(vdir):
                    if f.startswith("icon."): os.remove(os.path.join(vdir, f))
                shutil.copy(p, target)
                ImageManager.invalidate()
                self.update_preview()
                self.app.logic.refresh_version_list(self.app)
                messagebox.showinfo(self, c.t("UI_SUCCESS_TITLE"), c.t("UI_SAVE_SUCCESS_MSG"))
            except Exception as e:
                messagebox.showerror(self, c.t("UI_ERROR_TITLE"), str(e))

    def create_shortcut(self):
        """Create a desktop shortcut for the version."""
        if not self.target_version: return
        self.app.logic.create_version_shortcut(self.app, self.target_version)

    def remove_shortcut(self):
        """Remove desktop shortcut for the version."""
        if not self.target_version: return
        self.app.logic.remove_version_shortcut(self.app, self.target_version)


class SleekVersionContextMenu(QWidget):
    """Sleek popup menu for a specific version item with Editar, Mover a Respaldo, and Eliminar."""
    def __init__(self, app, version_name, parent=None):
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.app = app
        self.version_name = version_name
        self.setMinimumWidth(180)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        accent = getattr(self.app, "current_accent_color", "#1f6aa5") if self.app else "#1f6aa5"
        is_dark = getattr(self.app, "is_dark_mode", True) if self.app else True

        # Option: Editar
        self.btn_edit = QPushButton(c.t("UI_VM_MENU_EDIT"))
        self.btn_edit.setFixedHeight(34)
        self.btn_edit.setCursor(Qt.PointingHandCursor)
        edit_icon = ImageManager.get_icon("edit_pencil_icon.svg")
        if not edit_icon.isNull():
            self.btn_edit.setIcon(edit_icon)
        self.btn_edit.clicked.connect(self._on_edit)
        layout.addWidget(self.btn_edit)

        # Option: Mover a Respaldo
        self.btn_backup = QPushButton(c.t("UI_VM_MENU_BACKUP"))
        self.btn_backup.setFixedHeight(34)
        self.btn_backup.setCursor(Qt.PointingHandCursor)
        backup_icon = ImageManager.get_icon("backup_box_icon.svg")
        if not backup_icon.isNull():
            self.btn_backup.setIcon(backup_icon)
        self.btn_backup.clicked.connect(self._on_backup)
        layout.addWidget(self.btn_backup)

        # Option: Eliminar
        self.btn_delete = QPushButton(c.t("UI_VM_MENU_DELETE"))
        self.btn_delete.setFixedHeight(34)
        self.btn_delete.setCursor(Qt.PointingHandCursor)
        trash_icon = ImageManager.get_icon("trash_delete_icon.svg")
        if not trash_icon.isNull():
            self.btn_delete.setIcon(trash_icon)
        self.btn_delete.clicked.connect(self._on_delete)
        layout.addWidget(self.btn_delete)

        # Styling
        text_color = "#ffffff" if is_dark else "#111214"
        hover_bg = blend_colors("#282828", accent, 0.25) if is_dark else blend_colors("#dfe3e8", accent, 0.20)
        self.btn_edit.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {text_color}; border: none; border-radius: 6px;
                text-align: left; padding-left: 10px; font-size: 12px; font-weight: 500;
            }}
            QPushButton:hover {{ background: {hover_bg}; }}
        """)
        self.btn_backup.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {text_color}; border: none; border-radius: 6px;
                text-align: left; padding-left: 10px; font-size: 12px; font-weight: 500;
            }}
            QPushButton:hover {{ background: {hover_bg}; }}
        """)
        self.btn_delete.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: #ef4444; border: none; border-radius: 6px;
                text-align: left; padding-left: 10px; font-size: 12px; font-weight: 500;
            }}
            QPushButton:hover {{ background: rgba(239, 68, 68, 0.18); color: #ff6b6b; }}
        """)

    def _on_edit(self):
        self.close()
        dialog = SleekVersionEditDialog(self.app, target_version=self.version_name)
        dialog.exec()

    def _on_backup(self):
        self.close()
        try:
            backup_dir = os.path.join(self.app.home, c.BACKUP_DIR)
            os.makedirs(backup_dir, exist_ok=True)
            vdir = os.path.join(self.app.active_path, c.VERSIONS_DIR, self.version_name)
            shutil.move(vdir, backup_dir)
            if hasattr(self.app.logic, "refresh_version_list"):
                self.app.logic.refresh_version_list(self.app)
            messagebox.showinfo(self.parent(), c.t("UI_SUCCESS_TITLE"), c.t("UI_VERSION_MOVED_MSG"))
        except Exception as e:
            messagebox.showerror(self.parent(), c.t("UI_ERROR_TITLE"), str(e))

    def _on_delete(self):
        self.close()
        if messagebox.askyesno(self.parent(), c.t("UI_CONFIRM_DELETE_TITLE"), c.t("UI_CONFIRM_PERMANENT_DELETE", version=self.version_name)):
            try:
                vdir = os.path.join(self.app.active_path, c.VERSIONS_DIR, self.version_name)
                shutil.rmtree(vdir)
                if hasattr(self.app.logic, "refresh_version_list"):
                    self.app.logic.refresh_version_list(self.app)
                messagebox.showinfo(self.parent(), c.t("UI_SUCCESS_TITLE"), c.t("UI_VERSION_DELETED_MSG"))
            except Exception as e:
                messagebox.showerror(self.parent(), c.t("UI_ERROR_TITLE"), str(e))

    def show_at(self, pos):
        self.adjustSize()
        self.move(pos)
        self.show()

    def paintEvent(self, event):
        from src.utils.colors import blend_colors
        from PySide6.QtGui import QPainter, QColor, QPen
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        accent = getattr(self.app, "current_accent_color", "#1f6aa5") if self.app else "#1f6aa5"
        is_dark = getattr(self.app, "is_dark_mode", True) if self.app else True
        bg_color = QColor("#16171a" if is_dark else "#ffffff")
        border_color = QColor(hex_to_rgba(accent, 0.45))
        painter.setBrush(bg_color)
        painter.setPen(QPen(border_color, 1.2))
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 10, 10)
        painter.end()


# Backwards compatibility alias
VersionManagerDialog = SleekVersionEditDialog
