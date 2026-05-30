import os
import shutil
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QComboBox, QScrollArea, QFrame,
                             QLineEdit, QSlider, QWidget)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QIcon
from src import constants as c
from src.gui import custom_dialogs as messagebox
from src.utils.dialogs import ask_open_filename_native
from src.utils.image_manager import ImageManager

class VersionManagerDialog(QDialog):
    """Dialog for managing installed versions: rename, change icon, delete, and create shortcuts."""
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.setObjectName("VersionManagerDialog")
        self.setWindowTitle(c.t("UI_MANAGE_VERSION_TITLE"))
        self.setMinimumSize(520, 500)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Main container with proper styling - removed extra frame wrapper
        self.container = QFrame()
        self.container.setObjectName("GroupFrame")
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(15, 15, 15, 15)
        self.container_layout.setAlignment(Qt.AlignTop)
        self.container_layout.setSpacing(10)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setStyleSheet("background: transparent; border: none;")
        self.scroll_area.setWidget(self.container)
        self.main_layout.addWidget(self.scroll_area)

        # Selector de Versión
        selector_layout = QHBoxLayout()
        selector_layout.addWidget(QLabel(c.t("UI_LABEL_INSTALLED_VERSIONS") + ":"))
        self.combo_versions = QComboBox()
        self.refresh_versions()
        self.combo_versions.currentTextChanged.connect(self.on_version_selected)
        selector_layout.addWidget(self.combo_versions, 1)
        self.container_layout.addLayout(selector_layout)

        # Actions Area - with proper separation between elements
        self.info_frame = QFrame()
        self.info_frame.setObjectName("ToolCard")
        self.info_layout = QVBoxLayout(self.info_frame)
        self.info_layout.setSpacing(12)  # Add spacing between elements
        self.info_layout.setContentsMargins(15, 15, 15, 15)
        self.container_layout.addWidget(self.info_frame)

        self.lbl_prompt = QLabel("")
        self.lbl_prompt.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.lbl_prompt.setAlignment(Qt.AlignCenter)
        self.info_layout.addWidget(self.lbl_prompt)

        # Separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet(f"background-color: {'#444444' if self.app.config.get(c.CONFIG_KEY_APPEARANCE, 'Dark') == 'Dark' else '#cccccc'};")
        separator.setFixedHeight(1)
        self.info_layout.addWidget(separator)

        # Renombrar
        rename_row = QHBoxLayout()
        rename_row.addWidget(QLabel(c.t("UI_BUTTON_RENAME") + ":"))
        self.entry_rename = QLineEdit()
        self.entry_rename.setStyleSheet("background-color: #333; color: white; border: 1px solid #555; border-radius: 6px; padding: 4px 8px;")
        rename_row.addWidget(self.entry_rename)
        self.btn_rename = QPushButton(c.t("UI_BUTTON_RENAME"))
        self.btn_rename.setFixedWidth(100)
        self.btn_rename.setStyleSheet("background-color: #1f6aa5; color: white; border: none; border-radius: 8px; font-weight: bold;")
        self.btn_rename.clicked.connect(self.rename_version)
        rename_row.addWidget(self.btn_rename)
        self.info_layout.addLayout(rename_row)

        # Icono Personalizado - simplified layout
        icon_row = QHBoxLayout()
        icon_row.setContentsMargins(0, 5, 0, 5)
        icon_row.addWidget(QLabel(c.t("UI_BUTTON_CHANGE_ICON") + ":"))
        self.btn_change_icon = QPushButton("...")
        self.btn_change_icon.setFixedWidth(40)
        self.btn_change_icon.clicked.connect(self.change_icon)
        icon_row.addWidget(self.btn_change_icon)

        self.btn_reset_icon = QPushButton("🔄")
        self.btn_reset_icon.setFixedWidth(40)
        self.btn_reset_icon.setToolTip(c.t("UI_BUTTON_RESET_ICON"))
        self.btn_reset_icon.clicked.connect(self.reset_icon)
        icon_row.addWidget(self.btn_reset_icon)

        icon_row.addSpacing(10)
        icon_row.addWidget(QLabel(c.t("UI_LABEL_ICON_ZOOM")))
        self.slider_zoom = QSlider(Qt.Horizontal)
        self.slider_zoom.setRange(10, 500)
        self.slider_zoom.setValue(100)
        self.slider_zoom.valueChanged.connect(self.update_personalization)
        self.slider_zoom.sliderReleased.connect(self.on_personalization_released)
        icon_row.addWidget(self.slider_zoom, 1)
        self.lbl_zoom_val = QLabel("100%")
        icon_row.addWidget(self.lbl_zoom_val)
        self.info_layout.addLayout(icon_row)

        # Icon Position - simplified layout
        pos_row = QHBoxLayout()
        pos_row.setContentsMargins(0, 5, 0, 5)
        pos_row.addWidget(QLabel(c.t("UI_LABEL_POS_X")))
        self.slider_x = QSlider(Qt.Horizontal)
        self.slider_x.setRange(-200, 200)
        self.slider_x.setValue(0)
        self.slider_x.valueChanged.connect(self.update_personalization)
        self.slider_x.sliderReleased.connect(self.on_personalization_released)
        pos_row.addWidget(self.slider_x)
        self.lbl_x_val = QLabel("0")
        pos_row.addWidget(self.lbl_x_val)

        pos_row.addSpacing(15)
        pos_row.addWidget(QLabel(c.t("UI_LABEL_POS_Y")))
        self.slider_y = QSlider(Qt.Horizontal)
        self.slider_y.setRange(-200, 200)
        self.slider_y.setValue(0)
        self.slider_y.valueChanged.connect(self.update_personalization)
        self.slider_y.sliderReleased.connect(self.on_personalization_released)
        pos_row.addWidget(self.slider_y)
        self.lbl_y_val = QLabel("0")
        pos_row.addWidget(self.lbl_y_val)
        self.info_layout.addLayout(pos_row)

        # Preview Area
        preview_frame = QFrame()
        preview_frame.setFixedSize(120, 120)
        preview_frame.setStyleSheet("background: #333; border-radius: 10px; border: 1px solid #555;")
        preview_layout = QVBoxLayout(preview_frame)
        preview_layout.setAlignment(Qt.AlignCenter)
        self.lbl_preview = QLabel()
        self.lbl_preview.setScaledContents(True)
        preview_layout.addWidget(self.lbl_preview)

        preview_container = QHBoxLayout()
        preview_container.addStretch()
        preview_container.addWidget(preview_frame)
        preview_container.addStretch()
        self.info_layout.addLayout(preview_container)

        # Acciones de Archivo - centered and smaller buttons
        file_actions = QHBoxLayout()
        file_actions.setContentsMargins(0, 10, 0, 5)
        file_actions.setAlignment(Qt.AlignCenter | Qt.AlignHCenter)
        
        self.btn_move = QPushButton(c.t("UI_MOVE_TO_BACKUP"))
        self.btn_move.setFixedWidth(120)
        self.btn_move.setFixedHeight(36)
        self.btn_move.setStyleSheet(f"background-color: {c.COLOR_YELLOW_BUTTON}; color: white; border-radius: 8px; font-weight: bold; border: 1px solid {c.COLOR_YELLOW_BUTTON};")
        self.btn_move.clicked.connect(self.move_to_backup)
        file_actions.addWidget(self.btn_move)

        self.btn_delete = QPushButton(c.t("UI_DELETE_PERMANENTLY"))
        self.btn_delete.setFixedWidth(100)
        self.btn_delete.setFixedHeight(36)
        self.btn_delete.setStyleSheet(f"background-color: {c.COLOR_RED_BUTTON}; color: white; border-radius: 8px; font-weight: bold; border: 1px solid {c.COLOR_RED_BUTTON};")
        self.btn_delete.clicked.connect(self.delete_permanently)
        file_actions.addWidget(self.btn_delete)
        
        self.container_layout.addLayout(file_actions)

        # Shortcut Section
        lbl_shortcut = QLabel(c.t("UI_SECTION_VERSION_SHORTCUTS"))
        lbl_shortcut.setStyleSheet("font-weight: bold; margin-top: 10px;")
        self.container_layout.addWidget(lbl_shortcut)

        self.btn_create_shortcut = QPushButton(c.t("UI_BUTTON_CREATE_MAIN"))
        self.btn_create_shortcut.setStyleSheet(f"background-color: {c.COLOR_GREEN_BUTTON}; color: white; border: 1px solid {c.COLOR_GREEN_BUTTON};")
        self.btn_create_shortcut.setFixedHeight(38)
        self.btn_create_shortcut.clicked.connect(self.create_shortcut)
        self.container_layout.addWidget(self.btn_create_shortcut)

        self.container_layout.addStretch()

        self.btn_close = QPushButton(c.t("UI_BUTTON_CLOSE"))
        self.btn_close.setObjectName("ActionButton") # Consistent styling
        self.btn_close.setFixedHeight(40)
        self.btn_close.clicked.connect(self.accept)
        self.container_layout.addWidget(self.btn_close)

        # Initial call after all widgets are set up
        QTimer.singleShot(100, lambda: self.on_version_selected(self.combo_versions.currentText()))

    def refresh_versions(self):
        """Reload the installed versions list into the selector combo."""
        curr = self.combo_versions.currentText()
        self.combo_versions.clear()
        vers = self.app.logic.get_installed_versions(self.app)
        self.combo_versions.addItems(vers)
        if curr in vers: self.combo_versions.setCurrentText(curr)

    def on_version_selected(self, version):
        """Populate the UI fields when a version is selected in the combo box."""
        if not version:
            self.info_frame.setEnabled(False)
            self.btn_create_shortcut.setEnabled(False)
            return
        self.info_frame.setEnabled(True)
        self.btn_create_shortcut.setEnabled(True)
        self.lbl_prompt.setText(c.t("UI_MANAGE_VERSION_PROMPT", version=version))
        self.entry_rename.setText(version)

        zooms = self.app.config.get(c.CONFIG_KEY_VERSION_ICON_ZOOM, {})
        zoom = zooms.get(version, 100)
        self.slider_zoom.setValue(zoom)
        self.lbl_zoom_val.setText(f"{zoom}%")

        xs = self.app.config.get(c.CONFIG_KEY_VERSION_ICON_X, {})
        x = xs.get(version, 0)
        self.slider_x.setValue(x)
        self.lbl_x_val.setText(str(x))

        ys = self.app.config.get(c.CONFIG_KEY_VERSION_ICON_Y, {})
        y = ys.get(version, 0)
        self.slider_y.setValue(y)
        self.lbl_y_val.setText(str(y))

        self.update_preview()

    def update_personalization(self):
        """Update icon labels and preview live while dragging."""
        version = self.combo_versions.currentText()
        if not version: return

        zoom = self.slider_zoom.value()
        x = self.slider_x.value()
        y = self.slider_y.value()

        self.lbl_zoom_val.setText(f"{zoom}%")
        self.lbl_x_val.setText(str(x))
        self.lbl_y_val.setText(str(y))

        zooms = self.app.config.get(c.CONFIG_KEY_VERSION_ICON_ZOOM, {})
        zooms[version] = zoom
        self.app.config[c.CONFIG_KEY_VERSION_ICON_ZOOM] = zooms

        xs = self.app.config.get(c.CONFIG_KEY_VERSION_ICON_X, {})
        xs[version] = x
        self.app.config[c.CONFIG_KEY_VERSION_ICON_X] = xs

        ys = self.app.config.get(c.CONFIG_KEY_VERSION_ICON_Y, {})
        ys[version] = y
        self.app.config[c.CONFIG_KEY_VERSION_ICON_Y] = ys

        self.update_preview()

    def on_personalization_released(self):
        """Save icon personalization on slider release."""
        version = self.combo_versions.currentText()
        if not version: return
        self.app.config_manager.set(c.CONFIG_KEY_VERSION_ICON_ZOOM, self.app.config.get(c.CONFIG_KEY_VERSION_ICON_ZOOM, {}))
        self.app.config_manager.set(c.CONFIG_KEY_VERSION_ICON_X, self.app.config.get(c.CONFIG_KEY_VERSION_ICON_X, {}))
        self.app.config_manager.set(c.CONFIG_KEY_VERSION_ICON_Y, self.app.config.get(c.CONFIG_KEY_VERSION_ICON_Y, {}))

    def update_preview(self):
        """Refresh the icon preview with current zoom and position settings."""
        version = self.combo_versions.currentText()
        if not version: return

        vdir = os.path.join(self.app.active_path, c.VERSIONS_DIR, version)
        pix = None
        for ext in [".png", ".jpg", ".jpeg", ".webp"]:
            icon_p = os.path.join(vdir, "icon" + ext)
            if os.path.exists(icon_p):
                pix = QPixmap(icon_p)
                break

        if not pix or pix.isNull():
            pix = ImageManager.get_icon("icon.png").pixmap(64, 64)

        zoom = self.slider_zoom.value() / 100.0
        x = self.slider_x.value()
        y = self.slider_y.value()

        sw, sh = 64 * zoom, 64 * zoom
        self.lbl_preview.setPixmap(pix)
        self.lbl_preview.setFixedSize(sw, sh)
        # Center it in the 120x120 frame + offset
        self.lbl_preview.move(int(60 - sw/2 + x), int(60 - sh/2 + y))

    def rename_version(self):
        """Rename the selected version folder and refresh the list."""
        old = self.combo_versions.currentText()
        new = self.entry_rename.text().strip()
        if not new or old == new: return

        if self.app.logic.rename_version(self.app, old, new):
            self.refresh_versions()
            self.combo_versions.setCurrentText(new)
            messagebox.showinfo(self, c.t("UI_SUCCESS_TITLE"), c.t("UI_SAVE_SUCCESS_MSG"))

    def reset_icon(self):
        """Remove the custom icon file for the selected version."""
        version = self.combo_versions.currentText()
        if not version: return
        vdir = os.path.join(self.app.active_path, c.VERSIONS_DIR, version)
        try:
            for f in os.listdir(vdir):
                if f.startswith("icon."): os.remove(os.path.join(vdir, f))
            self.update_preview()
            self.app.logic.refresh_version_list(self.app)
        except Exception as e:
            messagebox.showerror(self, c.t("UI_ERROR_TITLE"), str(e))

    def change_icon(self):
        """Pick a new image file and set it as the version's custom icon."""
        version = self.combo_versions.currentText()
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
                self.update_preview()
                self.app.logic.refresh_version_list(self.app)
                messagebox.showinfo(self, c.t("UI_SUCCESS_TITLE"), c.t("UI_SAVE_SUCCESS_MSG"))
            except Exception as e:
                messagebox.showerror(self, c.t("UI_ERROR_TITLE"), str(e))

    def move_to_backup(self):
        """Move the selected version folder to the backup directory."""
        version = self.combo_versions.currentText()
        if not version: return
        try:
            backup_dir = os.path.join(self.app.home, c.BACKUP_DIR)
            os.makedirs(backup_dir, exist_ok=True)
            shutil.move(os.path.join(self.app.active_path, c.VERSIONS_DIR, version), backup_dir)
            self.refresh_versions()
            self.app.logic.refresh_version_list(self.app)
            messagebox.showinfo(self, c.t("UI_SUCCESS_TITLE"), c.t("UI_VERSION_MOVED_MSG"))
        except Exception as e: messagebox.showerror(self, c.t("UI_ERROR_TITLE"), str(e))

    def delete_permanently(self):
        """Permanently delete the selected version after confirmation."""
        version = self.combo_versions.currentText()
        if not version: return
        if messagebox.askyesno(self, c.t("UI_CONFIRM_DELETE_TITLE"), c.t("UI_CONFIRM_PERMANENT_DELETE", version=version)):
            try:
                shutil.rmtree(os.path.join(self.app.active_path, c.VERSIONS_DIR, version))
                self.refresh_versions()
                self.app.logic.refresh_version_list(self.app)
                messagebox.showinfo(self, c.t("UI_SUCCESS_TITLE"), c.t("UI_VERSION_DELETED_MSG"))
            except Exception as e: messagebox.showerror(self, c.t("UI_ERROR_TITLE"), str(e))

    def create_shortcut(self):
        """Create a desktop shortcut for the selected version."""
        version = self.combo_versions.currentText()
        if not version: return
        self.app.logic.create_version_shortcut(self.app, version)
