from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QFrame, QScrollArea, QWidget, QFileDialog)
from PySide6.QtCore import Qt
from src.gui import custom_dialogs as messagebox
import os
import shutil
import tempfile
import zipfile
import json
import uuid
from src.utils.dialogs import ask_open_filenames_native
from src import constants as c

class SkinPackTool(QDialog):
    """Dialog for creating a Minecraft skin pack (.mcpack) from PNG images."""
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle(c.t("UI_SKIN_PACK_CREATOR_TITLE"))
        self.resize(700, 550)

        self.skins = []
        self.setup_ui()

    def setup_ui(self):
        """Build the dialog with pack name entry, skin list, and add/export buttons."""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(10)

        # Header
        header = QFrame()
        header.setStyleSheet(f"background-color: #333333; border-radius: {c.CORNER_RADIUS}px;")
        h_layout = QHBoxLayout(header)
        h_layout.addWidget(QLabel(c.t("UI_PACK_NAME_LABEL")))
        self.entry_pack_name = QLineEdit()
        self.entry_pack_name.setMinimumWidth(200)
        h_layout.addWidget(self.entry_pack_name)
        self.main_layout.addWidget(header)

        # Scroll Area
        lbl_skins = QLabel(c.t("UI_SKINS_ADDED_LABEL"))
        lbl_skins.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.main_layout.addWidget(lbl_skins)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setStyleSheet("background: transparent;")

        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setAlignment(Qt.AlignTop)
        self.scroll_area.setWidget(self.scroll_content)
        self.main_layout.addWidget(self.scroll_area, 1)

        # Botones
        btn_frame = QFrame()
        btn_frame.setStyleSheet(f"background-color: #333333; border-radius: {c.CORNER_RADIUS}px;")
        b_layout = QHBoxLayout(btn_frame)

        btn_add = QPushButton(c.t("UI_BUTTON_ADD_SKINS_PNG"))
        btn_add.clicked.connect(self.add_skins_multi)
        b_layout.addWidget(btn_add)

        b_layout.addStretch()

        btn_export = QPushButton(c.t("UI_BUTTON_EXPORT_MCPACK"))
        btn_export.setStyleSheet("background-color: green; color: white; font-weight: bold;")
        btn_export.clicked.connect(self.export_pack)
        b_layout.addWidget(btn_export)

        self.main_layout.addWidget(btn_frame)
        self.setStyleSheet("background-color: #2b2b2b; color: white;")

    def add_skins_multi(self):
        """Open a file picker to select multiple PNG files and add them to the skin list."""
        paths = ask_open_filenames_native(self, filetypes=[("PNG Files", "*.png")])
        if paths:
            for path in paths:
                name = os.path.splitext(os.path.basename(path))[0]
                self.skins.append({"name": name, "path": path})
            self.refresh_list()

    def refresh_list(self):
        """Rebuild the skin list UI showing editable names and delete buttons."""
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i, skin in enumerate(self.skins):
            f = QFrame()
            f.setStyleSheet("background-color: #3a3a3a; border-radius: 8px;")
            l = QHBoxLayout(f)

            e = QLineEdit(skin["name"])
            e.setMinimumWidth(150)
            e.textChanged.connect(lambda text, idx=i: self.update_skin_name(idx, text))
            l.addWidget(e)

            l.addWidget(QLabel(os.path.basename(skin["path"])), 1)

            btn_del = QPushButton("X")
            btn_del.setFixedWidth(30)
            btn_del.setStyleSheet("background-color: red; color: white;")
            btn_del.clicked.connect(lambda checked=False, idx=i: self.remove_skin(idx))
            l.addWidget(btn_del)

            self.scroll_layout.addWidget(f)

    def update_skin_name(self, idx, text):
        """Update the internal skin name when the user edits the text field."""
        self.skins[idx]["name"] = text

    def remove_skin(self, idx):
        """Remove a skin from the list by its index."""
        del self.skins[idx]
        self.refresh_list()

    def export_pack(self):
        """Generate a .mcpack file with manifest, skins.json, and textures."""
        pack_name = self.entry_pack_name.text().strip()
        if not pack_name or not self.skins:
            messagebox.showwarning(self, c.t("UI_ERROR_TITLE"), c.t("UI_ERROR_MISSING_NAME_OR_SKINS"))
            return

        save_path, _ = QFileDialog.getSaveFileName(self, filter=f"{c.t("UI_MCPACK_FILES_TYPE")} (*.mcpack)")
        if not save_path: return

        temp_dir = tempfile.mkdtemp(prefix="skin_pack_")
        try:
            skins_json = {"skins": [], "serialize_name": pack_name, "localization_name": pack_name}
            for skin in self.skins:
                safe_name = "".join(x for x in skin["name"] if x.isalnum())
                filename = f"{safe_name}.png"
                shutil.copy(skin["path"], os.path.join(temp_dir, filename))
                skins_json["skins"].append({
                    "localization_name": skin["name"],
                    "geometry": "geometry.humanoid.custom",
                    "texture": filename,
                    "type": "free"
                })

            manifest = {
                "format_version": 1,
                "header": {"name": pack_name, "uuid": str(uuid.uuid4()), "version": [1, 0, 0]},
                "modules": [{"type": "skin_pack", "uuid": str(uuid.uuid4()), "version": [1, 0, 0]}]
            }

            with open(os.path.join(temp_dir, "manifest.json"), "w") as f: json.dump(manifest, f, indent=4)
            with open(os.path.join(temp_dir, "skins.json"), "w") as f: json.dump(skins_json, f, indent=4)

            texts_dir = os.path.join(temp_dir, "texts")
            os.makedirs(texts_dir)
            with open(os.path.join(texts_dir, "en_US.lang"), "w") as f:
                f.write(f"skinpack.{pack_name}={pack_name}\n")
                for skin in self.skins: f.write(f"skin.{pack_name}.{skin['name']}={skin['name']}\n")

            with zipfile.ZipFile(save_path, "w") as zipf:
                for root, _, files in os.walk(temp_dir):
                    for file in files:
                        zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), temp_dir))

            messagebox.showinfo(self, c.t("UI_SUCCESS_TITLE"), c.t("UI_PACK_SAVED_SUCCESS", save_path=save_path))
        except Exception as e: messagebox.showerror(self, c.t("UI_ERROR_TITLE"), str(e))
        finally:
            if os.path.exists(temp_dir): shutil.rmtree(temp_dir)
