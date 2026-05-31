from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QFrame, QCheckBox,
                             QComboBox, QWidget, QStackedWidget, QScrollArea,
                             QSizePolicy)
from PySide6.QtCore import Qt, Signal
import os
import shutil
import threading
from src.gui import custom_dialogs as messagebox
from src.utils.dialogs import ask_directory_native
from src.gui.progress_dialog import ProgressDialog
from src import constants as c


class _ClickableFrame(QFrame):
    clicked = Signal()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class MigrationWizard(QDialog):
    """Multi-step wizard for migrating Minecraft data between installations."""

    def __init__(self, parent):
        super().__init__(parent)
        self.parent_app = parent
        self.setWindowTitle(c.t("UI_MIGRATION_MANAGER_TITLE"))
        self.resize(650, 720)
        self.setMinimumSize(600, 600)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setModal(True)

        self.current_step = 0
        self.total_steps = 5

        self.source_path = ""
        self.source_mode = "local"
        self.flatpak_id = c.DEFAULT_FLATPAK_ID
        self.source_valid = False
        self.dst_profile = "Default"
        self.content_mode = "all"
        self.migrate_versions = False
        self.migrate_worlds = False
        self.migrate_resources = False
        self.method = ""

        self.accent = c.THEME_COLOR_MAP.get(
            self.parent_app.config.get(c.CONFIG_KEY_COLOR_THEME, "blue"), "#1f6aa5"
        )

        self.setup_ui()

    # ───────────────────────── UI Build ─────────────────────────

    def setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        header = QFrame()
        header.setFixedHeight(80)
        header.setObjectName("HeaderFrame")
        hl = QHBoxLayout(header)

        self.lbl_title = QLabel(c.t("UI_MIGRATION_TITLE"))
        self.lbl_title.setStyleSheet("font-size: 20px; font-weight: bold; color: white;")
        hl.addWidget(self.lbl_title)
        hl.addStretch()
        self.lbl_step = QLabel("")
        self.lbl_step.setStyleSheet("color: #aaaaaa; font-weight: bold; font-size: 13px;")
        hl.addWidget(self.lbl_step)
        self.main_layout.addWidget(header)

        self.stack = QStackedWidget()
        self.main_layout.addWidget(self.stack, 1)

        self.create_source_step()
        self.create_profile_step()
        self.create_content_step()
        self.create_method_step()
        self.create_summary_step()

        footer = QFrame()
        footer.setFixedHeight(75)
        footer.setObjectName("FooterFrame")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(25, 0, 25, 0)

        self.btn_back = QPushButton(c.t("UI_BUTTON_BACK"))
        self.btn_back.setFixedSize(140, 42)
        self.btn_back.setObjectName("NavButton")
        self.btn_back.setEnabled(False)
        self.btn_back.clicked.connect(self.prev_step)
        fl.addWidget(self.btn_back)
        fl.addStretch()

        self.btn_next = QPushButton(c.t("UI_BUTTON_NEXT"))
        self.btn_next.setFixedSize(140, 42)
        self.btn_next.setObjectName("NavButton")
        self.btn_next.clicked.connect(self.next_step)
        fl.addWidget(self.btn_next)

        self.main_layout.addWidget(footer)

        self._on_source_selected("local")
        self.apply_styles()
        self.update_buttons()

    def _scrolled_page(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")
        page = QWidget()
        l = QVBoxLayout(page)
        l.setContentsMargins(40, 30, 40, 30)
        l.setSpacing(12)
        scroll.setWidget(page)
        return scroll, l

    def _tl(self, text, style="", word_wrap=False):
        lbl = QLabel(text)
        lbl.setAttribute(Qt.WA_TransparentForMouseEvents)
        if style:
            lbl.setStyleSheet(style)
        if word_wrap:
            lbl.setWordWrap(True)
        return lbl

    def _create_card(self, icon, title, description="", card_id="", max_height=110):
        card = _ClickableFrame()
        card.setObjectName(f"Card_{card_id}")
        card.setCursor(Qt.PointingHandCursor)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        card.setMaximumHeight(max_height)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(15, 8, 15, 8)
        layout.setSpacing(3)

        if icon:
            layout.addWidget(self._tl(icon, "font-size: 22px; border: none;"))
        layout.addWidget(self._tl(title, "font-size: 14px; font-weight: bold; color: white; border: none;"))
        if description:
            layout.addWidget(self._tl(description, "color: #aaaaaa; font-size: 10px; border: none;", word_wrap=True))

        self._style_card(card, card_id, False)
        return card

    def _create_hcard(self, icon, title, description, card_id=""):
        card = _ClickableFrame()
        card.setObjectName(f"CardH_{card_id}")
        card.setCursor(Qt.PointingHandCursor)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        card.setMinimumHeight(80)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(15, 14, 15, 14)
        layout.setSpacing(15)

        icon_lbl = self._tl(icon, "font-size: 34px; border: none;")
        icon_lbl.setFixedWidth(45)
        icon_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_lbl)

        text_col = QVBoxLayout()
        text_col.setSpacing(4)
        text_col.addWidget(self._tl(title, "font-size: 15px; font-weight: bold; color: white; border: none;"))
        if description:
            text_col.addWidget(self._tl(description, "color: #aaaaaa; font-size: 11px; border: none;", word_wrap=True))
        layout.addLayout(text_col)
        layout.addStretch()

        self._style_hcard(card, card_id, False)
        return card

    def _style_card(self, card, card_id, checked):
        if checked:
            card.setStyleSheet(f"""
                QFrame#Card_{card_id} {{
                    background-color: #2a3a4a;
                    border-radius: {c.CORNER_RADIUS}px;
                    border: 2px solid {self.accent};
                    padding: 8px;
                }}
                QFrame#Card_{card_id}:hover {{
                    border: 2px solid {self.accent};
                    background-color: #2a3a4a;
                }}
            """)
        else:
            card.setStyleSheet(f"""
                QFrame#Card_{card_id} {{
                    background-color: #333333;
                    border-radius: {c.CORNER_RADIUS}px;
                    border: 2px solid #555555;
                    padding: 8px;
                }}
                QFrame#Card_{card_id}:hover {{
                    border: 2px solid #888888;
                    background-color: #3a3a3a;
                }}
            """)

    def _style_hcard(self, card, card_id, checked):
        if checked:
            card.setStyleSheet(f"""
                QFrame#CardH_{card_id} {{
                    background-color: #2a3a4a;
                    border-radius: {c.CORNER_RADIUS}px;
                    border: 2px solid {self.accent};
                    padding: 8px;
                }}
                QFrame#CardH_{card_id}:hover {{
                    border: 2px solid {self.accent};
                    background-color: #2a3a4a;
                }}
            """)
        else:
            card.setStyleSheet(f"""
                QFrame#CardH_{card_id} {{
                    background-color: #333333;
                    border-radius: {c.CORNER_RADIUS}px;
                    border: 2px solid #555555;
                    padding: 8px;
                }}
                QFrame#CardH_{card_id}:hover {{
                    border: 2px solid #888888;
                    background-color: #3a3a3a;
                }}
            """)

    # ─────────────── Step 0 — Source Selection ───────────────

    def create_source_step(self):
        scroll, l = self._scrolled_page()

        title = QLabel(c.t("UI_WIZARD_STEP_SOURCE_TITLE"))
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        l.addWidget(title)

        self.source_cards = {}
        sources = [
            ("local", "💻", c.t("UI_SOURCE_MODES_DISPLAY")[0], c.t("UI_WIZARD_SOURCE_LOCAL_DESC")),
            ("flatpak", "📦", c.t("UI_SOURCE_MODES_DISPLAY")[1], c.t("UI_WIZARD_SOURCE_FLATPAK_DESC")),
            ("custom", "📂", c.t("UI_SOURCE_MODES_DISPLAY")[2], c.t("UI_WIZARD_SOURCE_CUSTOM_DESC")),
        ]

        for mode_id, icon, title_text, desc in sources:
            card = self._create_card(icon, title_text, desc, card_id=f"src_{mode_id}")
            card.clicked.connect(lambda m=mode_id: self._on_source_selected(m))
            self.source_cards[mode_id] = card
            l.addWidget(card)

        self.frame_flatpak = QFrame()
        fid_l = QHBoxLayout(self.frame_flatpak)
        fid_l.setContentsMargins(0, 0, 0, 0)
        lbl_appid = QLabel(c.t("UI_LABEL_APP_ID"))
        lbl_appid.setStyleSheet("color: white; font-weight: bold;")
        fid_l.addWidget(lbl_appid)
        self.entry_flatpak_id = QLineEdit()
        self.entry_flatpak_id.setText(c.DEFAULT_FLATPAK_ID)
        self.entry_flatpak_id.setStyleSheet(f"background-color: #1e1e1e; color: white; border: 2px solid {self.accent}; border-radius: 6px; padding: 8px; font-size: 13px;")
        self.entry_flatpak_id.textChanged.connect(self._on_flatpak_id_changed)
        fid_l.addWidget(self.entry_flatpak_id)
        self.frame_flatpak.hide()
        l.addWidget(self.frame_flatpak)

        self.entry_src = QLineEdit()
        self.entry_src.setPlaceholderText(c.t("UI_PLACEHOLDER_SOURCE_PATH"))
        self.entry_src.setReadOnly(True)
        self.entry_src.setStyleSheet("background-color: #2a2a2a; color: #cccccc; border: 1px solid #555555; border-radius: 6px; padding: 8px; font-size: 13px;")
        l.addWidget(self.entry_src)

        self.btn_browse_src = QPushButton(c.t("UI_BUTTON_BROWSE_FOLDER"))
        self.btn_browse_src.setObjectName("BrowseButton")
        self.btn_browse_src.setStyleSheet(f"background-color: #3a3a3a; color: {self.accent}; border: 1px solid {self.accent}; border-radius: 8px; padding: 8px 18px; font-size: 13px; font-weight: bold;")
        self.btn_browse_src.clicked.connect(self._browse_source)
        self.btn_browse_src.hide()
        l.addWidget(self.btn_browse_src, 0, Qt.AlignRight)

        self.lbl_src_validation = QLabel("")
        self.lbl_src_validation.setStyleSheet("font-size: 11px; font-weight: bold; padding: 2px 0;")
        l.addWidget(self.lbl_src_validation)

        l.addStretch()
        self.stack.addWidget(scroll)

    def _on_source_selected(self, mode_id):
        self.source_mode = mode_id
        for mid, card in self.source_cards.items():
            self._style_card(card, f"src_{mid}", mid == mode_id)

        self.frame_flatpak.setVisible(mode_id == "flatpak")
        self.btn_browse_src.setVisible(mode_id == "custom")

        if mode_id == "local":
            path = os.path.join(os.path.expanduser("~"), c.LOCAL_SHARE_DIR)
            self.entry_src.setText(path)
            self.entry_src.setReadOnly(True)
            self.entry_src.setStyleSheet("background-color: #2a2a2a; color: #cccccc; border: 1px solid #555555; border-radius: 6px; padding: 8px; font-size: 13px;")
            self._validate_source(path)
        elif mode_id == "flatpak":
            app_id = self.entry_flatpak_id.text().strip() or c.DEFAULT_FLATPAK_ID
            path = os.path.join(os.path.expanduser("~"), f"{c.FLATPAK_DATA_DIR}/{app_id}/{c.MCPELAUNCHER_DATA_SUBDIR}")
            self.entry_src.setText(path)
            self.entry_src.setReadOnly(True)
            self.entry_src.setStyleSheet("background-color: #2a2a2a; color: #cccccc; border: 1px solid #555555; border-radius: 6px; padding: 8px; font-size: 13px;")
            self._validate_source(path)
        else:
            self.entry_src.setText("")
            self.entry_src.setReadOnly(False)
            self.entry_src.setStyleSheet(f"background-color: #1e1e1e; color: white; border: 2px solid {self.accent}; border-radius: 6px; padding: 8px; font-size: 13px;")
            self.entry_src.setPlaceholderText(c.t("UI_WIZARD_SOURCE_CUSTOM_PLACEHOLDER"))
            self.lbl_src_validation.setText("")
            self.source_valid = False
            self.update_buttons()

    def _on_flatpak_id_changed(self, text):
        if self.source_mode == "flatpak":
            app_id = text.strip() or c.DEFAULT_FLATPAK_ID
            path = os.path.join(os.path.expanduser("~"), f"{c.FLATPAK_DATA_DIR}/{app_id}/{c.MCPELAUNCHER_DATA_SUBDIR}")
            self.entry_src.setText(path)
            self._validate_source(path)

    def _validate_source(self, path):
        if not path:
            self.lbl_src_validation.setText("")
            self.source_valid = False
        elif os.path.exists(path):
            if "mcpelauncher" in path or os.path.exists(os.path.join(path, c.VERSIONS_DIR)):
                self.lbl_src_validation.setText(f"✅ {c.t('UI_VALID_FOLDER_DETECTED')}")
                self.lbl_src_validation.setStyleSheet("color: #4CAF50; font-size: 11px; font-weight: bold; padding: 2px 0;")
                self.source_valid = True
            else:
                self.lbl_src_validation.setText(f"⚠️ {c.t('UI_INVALID_FOLDER_WARNING')}")
                self.lbl_src_validation.setStyleSheet("color: orange; font-size: 11px; font-weight: bold; padding: 2px 0;")
                self.source_valid = False
        else:
            self.lbl_src_validation.setText(f"❌ {c.t('UI_FOLDER_NOT_EXISTS')}")
            self.lbl_src_validation.setStyleSheet("color: #f44336; font-size: 11px; font-weight: bold; padding: 2px 0;")
            self.source_valid = False
        self.update_buttons()

    def _browse_source(self):
        d = ask_directory_native(self, title=c.t("UI_SELECT_SOURCE_FOLDER"))
        if d:
            self.entry_src.setText(d)
            self._validate_source(d)

    # ─────────────── Step 1 — Profile ───────────────

    def create_profile_step(self):
        scroll, l = self._scrolled_page()

        title = QLabel(c.t("UI_WIZARD_STEP_PROFILE_TITLE"))
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        l.addWidget(title)

        l.addStretch(1)

        profile_card = QFrame()
        profile_card.setObjectName("ProfileCard")
        profile_card.setStyleSheet(f"""
            QFrame#ProfileCard {{
                background-color: #333333;
                border-radius: {c.CORNER_RADIUS}px;
                border: 1px solid #555555;
                padding: 20px;
            }}
        """)
        pc_layout = QVBoxLayout(profile_card)
        pc_layout.setSpacing(14)

        row = QHBoxLayout()
        row.setSpacing(14)
        icon_lbl = QLabel("👤")
        icon_lbl.setStyleSheet("font-size: 32px; border: none;")
        row.addWidget(icon_lbl)
        text_col = QVBoxLayout()
        text_col.setSpacing(6)
        lbl_prof = QLabel(c.t("UI_LABEL_PROFILE"))
        lbl_prof.setStyleSheet("color: #aaaaaa; font-size: 12px; border: none;")
        text_col.addWidget(lbl_prof)
        self.combo_profile = QComboBox()
        self.combo_profile.setMinimumHeight(38)
        self.combo_profile.setStyleSheet(f"background-color: #1e1e1e; color: white; border: 2px solid {self.accent}; border-radius: 6px; padding: 4px 10px; font-size: 14px;")
        profiles = self.parent_app.logic.get_profiles(self.parent_app)
        self.combo_profile.addItems(profiles)
        current = self.parent_app.config.get(c.CONFIG_KEY_CURRENT_PROFILE, profiles[0] if profiles else "Default")
        if current in profiles:
            self.combo_profile.setCurrentText(current)
        self.combo_profile.currentTextChanged.connect(self._on_profile_changed)
        text_col.addWidget(self.combo_profile)
        row.addLayout(text_col)
        row.addStretch()
        pc_layout.addLayout(row)

        path_frame = QFrame()
        path_frame.setObjectName("PathFrame")
        path_frame.setStyleSheet("""
            QFrame#PathFrame {
                background-color: #2a2a2a;
                border-radius: 6px;
                border: 1px solid #444444;
                padding: 10px;
            }
        """)
        pf_l = QHBoxLayout(path_frame)
        pf_l.setContentsMargins(12, 10, 12, 10)
        self.lbl_profile_path = QLabel("")
        self.lbl_profile_path.setStyleSheet(f"color: {self.accent}; font-size: 12px; border: none;")
        self.lbl_profile_path.setWordWrap(True)
        pf_l.addWidget(self.lbl_profile_path)
        pc_layout.addWidget(path_frame)

        l.addWidget(profile_card)

        if len(profiles) <= 1:
            info_lbl = QLabel(c.t("UI_WIZARD_PROFILE_DEFAULT_ONLY"))
            info_lbl.setStyleSheet("color: #aaaaaa; font-size: 12px; font-style: italic; padding: 8px 0;")
            l.addWidget(info_lbl)

        l.addStretch(2)
        self.stack.addWidget(scroll)

        self._on_profile_changed(self.combo_profile.currentText())

    def _on_profile_changed(self, profile):
        self.dst_profile = profile
        path = os.path.join(self.parent_app.active_path, c.PROFILES_DIR, profile)
        dest_label = c.t("UI_WIZARD_SUMMARY_LABEL_DEST")
        self.lbl_profile_path.setText(f"📍 {dest_label}: {path}")

    # ─────────────── Step 2 — Content ───────────────

    def create_content_step(self):
        scroll, l = self._scrolled_page()

        title = QLabel(c.t("UI_WIZARD_STEP_CONTENT_TITLE"))
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        l.addWidget(title)

        l.addStretch(1)

        self.content_all_card = self._create_hcard(
            "📦", c.t("UI_MIGRATE_ALL"),
            c.t("UI_WIZARD_CONTENT_ALL_DESC"),
            card_id="content_all"
        )
        self.content_all_card.clicked.connect(lambda: self._on_content_mode("all"))
        l.addWidget(self.content_all_card)

        self.content_custom_card = self._create_hcard(
            "⚙️", c.t("UI_WIZARD_CONTENT_CUSTOM"),
            c.t("UI_WIZARD_CONTENT_CUSTOM_DESC"),
            card_id="content_custom"
        )
        self.content_custom_card.clicked.connect(lambda: self._on_content_mode("custom"))
        l.addWidget(self.content_custom_card)

        l.addSpacing(8)

        self.frame_custom = QFrame()
        self.frame_custom.setObjectName("CustomContentFrame")
        self.frame_custom.setStyleSheet(f"""
            QFrame#CustomContentFrame {{
                background-color: #2a2a2a;
                border-radius: {c.CORNER_RADIUS}px;
                border: 1px solid {self.accent};
                padding: 16px;
            }}
        """)
        cl = QVBoxLayout(self.frame_custom)
        cl.setSpacing(10)

        self.cb_versions = QCheckBox(c.t("UI_MIGRATE_VERSIONS"))
        self.cb_versions.stateChanged.connect(self._on_content_change)
        cl.addWidget(self.cb_versions)

        self.cb_worlds = QCheckBox(c.t("UI_MIGRATE_WORLDS"))
        self.cb_worlds.stateChanged.connect(self._on_content_change)
        cl.addWidget(self.cb_worlds)

        self.cb_resources = QCheckBox(c.t("UI_MIGRATE_RESOURCES"))
        self.cb_resources.stateChanged.connect(self._on_content_change)
        cl.addWidget(self.cb_resources)

        self.frame_custom.hide()
        l.addWidget(self.frame_custom)

        l.addStretch(2)
        self.stack.addWidget(scroll)

    def _on_content_mode(self, mode):
        self.content_mode = mode
        self._style_hcard(self.content_all_card, "content_all", mode == "all")
        self._style_hcard(self.content_custom_card, "content_custom", mode == "custom")
        self.frame_custom.setVisible(mode == "custom")
        self.update_buttons()

    def _on_content_change(self):
        self.update_buttons()

    # ─────────────── Step 3 — Method ───────────────

    def create_method_step(self):
        scroll, l = self._scrolled_page()

        title = QLabel(c.t("UI_WIZARD_STEP_METHOD_TITLE"))
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        l.addWidget(title)

        sub = QLabel(c.t("UI_WIZARD_METHOD_SUB"))
        sub.setStyleSheet("color: #aaaaaa; font-size: 12px; border: none;")
        sub.setWordWrap(True)
        l.addWidget(sub)

        self.method_cards = {}
        methods = [
            ("copy", "📋", c.t("UI_WIZARD_METHOD_COPY_TITLE"), c.t("UI_WIZARD_METHOD_COPY_DESC")),
            ("move", "✂️", c.t("UI_WIZARD_METHOD_MOVE_TITLE"), c.t("UI_WIZARD_METHOD_MOVE_DESC")),
            ("link", "🔗", c.t("UI_WIZARD_METHOD_LINK_TITLE"), c.t("UI_WIZARD_METHOD_LINK_DESC")),
        ]

        for method_id, icon, title_text, desc in methods:
            card = self._create_card(icon, title_text, desc, card_id=f"mtd_{method_id}")
            card.clicked.connect(lambda m=method_id: self._on_method_selected(m))
            self.method_cards[method_id] = card
            l.addWidget(card)

        l.addStretch()
        self.stack.addWidget(scroll)

    def _on_method_selected(self, method_id):
        self.method = method_id
        for mid, card in self.method_cards.items():
            self._style_card(card, f"mtd_{mid}", mid == method_id)
        self.update_buttons()

    # ─────────────── Step 4 — Summary ───────────────

    def create_summary_step(self):
        scroll, l = self._scrolled_page()

        title = QLabel(c.t("UI_WIZARD_STEP_SUMMARY_TITLE"))
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        l.addWidget(title)

        l.addStretch(1)

        self.summary_frame = QFrame()
        self.summary_frame.setObjectName("SummaryFrame")
        self.summary_frame.setStyleSheet(f"""
            QFrame#SummaryFrame {{
                background-color: #333333;
                border-radius: {c.CORNER_RADIUS}px;
                border: 1px solid #555555;
                padding: 20px;
            }}
        """)
        sl = QVBoxLayout(self.summary_frame)
        sl.setSpacing(10)

        self.summary_labels = {}
        for key in ["source", "dest", "profile", "items", "method"]:
            row = QHBoxLayout()
            lbl_key = c.t(f"UI_WIZARD_SUMMARY_LABEL_{key.upper()}")
            row.addWidget(self._tl(f"<b>{lbl_key}:</b>", "color: #aaaaaa; font-size: 13px;"))
            val = self._tl("", "color: white; font-size: 13px;")
            row.addWidget(val)
            row.addStretch()
            sl.addLayout(row)
            self.summary_labels[key] = val

        l.addWidget(self.summary_frame)
        l.addStretch(1)
        self.stack.addWidget(scroll)

    def _update_summary(self):
        method_names = {
            "copy": c.t("UI_WIZARD_METHOD_COPY_TITLE"),
            "move": c.t("UI_WIZARD_METHOD_MOVE_TITLE"),
            "link": c.t("UI_WIZARD_METHOD_LINK_TITLE"),
        }
        if self.content_mode == "all":
            items_text = c.t("UI_MIGRATE_ALL")
        else:
            parts = []
            if self.migrate_versions:
                parts.append(c.t("UI_MIGRATE_VERSIONS_SIMPLE"))
            if self.migrate_worlds:
                parts.append(c.t("UI_MIGRATE_WORLDS_SIMPLE"))
            if self.migrate_resources:
                parts.append(c.t("UI_MIGRATE_RESOURCES_SIMPLE"))
            items_text = ", ".join(parts) if parts else "—"

        self.summary_labels["source"].setText(self.source_path)
        dst = os.path.join(self.parent_app.active_path, c.PROFILES_DIR, self.dst_profile)
        self.summary_labels["dest"].setText(dst)
        self.summary_labels["profile"].setText(self.dst_profile)
        self.summary_labels["items"].setText(items_text)
        self.summary_labels["method"].setText(method_names.get(self.method, self.method))

    # ─────────────── Navigation ───────────────

    def next_step(self):
        if self.current_step == self.total_steps - 1:
            self.start_migration()
            return

        if self.current_step == 0 and not self.source_valid:
            return
        if self.current_step == 2:
            if self.content_mode == "custom":
                has = self.cb_versions.isChecked() or self.cb_worlds.isChecked() or self.cb_resources.isChecked()
                if not has:
                    return
        if self.current_step == 3 and not self.method:
            return

        if self.current_step == 0:
            self.source_path = self.entry_src.text().strip()
        elif self.current_step == 2:
            self.migrate_versions = self.cb_versions.isChecked()
            self.migrate_worlds = self.cb_worlds.isChecked()
            self.migrate_resources = self.cb_resources.isChecked()

        self.current_step += 1
        self.stack.setCurrentIndex(self.current_step)

        if self.current_step == self.total_steps - 1:
            self._update_summary()

        self.update_buttons()

    def prev_step(self):
        if self.current_step > 0:
            self.current_step -= 1
            self.stack.setCurrentIndex(self.current_step)
            self.update_buttons()

    def update_buttons(self):
        self.btn_back.setEnabled(self.current_step > 0)

        if self.current_step == self.total_steps - 1:
            self.btn_next.setText(c.t("UI_BUTTON_MIGRATE"))
        else:
            self.btn_next.setText(c.t("UI_BUTTON_NEXT"))

        self.lbl_step.setText(c.t("UI_SETUP_STEP", current=self.current_step + 1, total=self.total_steps))
        self._validate_nav()

    def _validate_nav(self):
        if self.current_step == 0:
            self.btn_next.setEnabled(self.source_valid)
        elif self.current_step == 2:
            if self.content_mode == "custom":
                has = self.cb_versions.isChecked() or self.cb_worlds.isChecked() or self.cb_resources.isChecked()
                self.btn_next.setEnabled(has)
            else:
                self.btn_next.setEnabled(True)
        elif self.current_step == 3:
            self.btn_next.setEnabled(bool(self.method))
        else:
            self.btn_next.setEnabled(True)

    # ─────────────── Migration Execution ───────────────

    def start_migration(self):
        src = self.source_path
        profile = self.dst_profile
        dst = os.path.join(self.parent_app.active_path, c.PROFILES_DIR, profile)
        method = self.method
        migrate_all = (self.content_mode == "all")
        migrate_versions = self.migrate_versions
        migrate_worlds = self.migrate_worlds
        migrate_resources = self.migrate_resources

        if not os.path.exists(src):
            messagebox.showerror(self, c.t("UI_ERROR_TITLE"), c.t("UI_FOLDER_NOT_EXISTS"))
            return
        if src == dst:
            messagebox.showerror(self, c.t("UI_ERROR_TITLE"), c.t("UI_ERROR_SAME_FOLDER"))
            return
        if not migrate_all and not any([migrate_versions, migrate_worlds, migrate_resources]):
            messagebox.showwarning(self, c.t("UI_INFO_TITLE"), c.t("UI_ERROR_NOTHING_SELECTED"))
            return

        items = []
        if migrate_all:
            items.append("TODO")
        else:
            if migrate_versions:
                items.append(c.t("UI_MIGRATE_VERSIONS_SIMPLE"))
            if migrate_worlds:
                items.append(c.t("UI_MIGRATE_WORLDS_SIMPLE"))
            if migrate_resources:
                items.append(c.t("UI_MIGRATE_RESOURCES_SIMPLE"))

        if not messagebox.askyesno(self, c.t("UI_CONFIRM_TITLE"), c.t("UI_MIGRATION_CONFIRM_MSG", src=src, dst=dst, method=method.upper(), items=", ".join(items))):
            return

        self.progress_dialog = ProgressDialog(self, c.t("UI_MIGRATING_TITLE"), c.t("UI_MIGRATING_MSG"))
        self.progress_dialog.show()

        thread = threading.Thread(
            target=self._run_migration,
            args=(src, dst, method, migrate_all, migrate_versions, migrate_worlds, migrate_resources)
        )
        thread.start()

    def _run_migration(self, src, dst_profile_path, method, migrate_all, migrate_versions, migrate_worlds, migrate_resources):
        try:
            migrated_count = 0
            base_dst = self.parent_app.active_path

            def process_item(s_item, d_item):
                if os.path.exists(d_item):
                    return False
                if method == "copy":
                    if os.path.isdir(s_item):
                        shutil.copytree(s_item, d_item)
                    else:
                        shutil.copy2(s_item, d_item)
                elif method == "move":
                    shutil.move(s_item, d_item)
                elif method == "link":
                    os.symlink(s_item, d_item)
                return True

            if migrate_all:
                if process_item(src, base_dst):
                    migrated_count = 1
            else:
                if migrate_versions:
                    src_dir = os.path.join(src, c.VERSIONS_DIR)
                    dst_dir = os.path.join(base_dst, c.VERSIONS_DIR)
                    if os.path.exists(src_dir):
                        os.makedirs(dst_dir, exist_ok=True)
                        for item in os.listdir(src_dir):
                            if process_item(os.path.join(src_dir, item), os.path.join(dst_dir, item)):
                                migrated_count += 1
                if migrate_worlds:
                    src_dir = os.path.join(src, c.WORLDS_DIR)
                    dst_dir = os.path.join(dst_profile_path, c.WORLDS_DIR)
                    if os.path.exists(src_dir):
                        os.makedirs(dst_dir, exist_ok=True)
                        for item in os.listdir(src_dir):
                            if process_item(os.path.join(src_dir, item), os.path.join(dst_dir, item)):
                                migrated_count += 1
                if migrate_resources:
                    src_dir = os.path.join(src, "games/com.mojang/resource_packs")
                    dst_dir = os.path.join(dst_profile_path, "games/com.mojang/resource_packs")
                    if os.path.exists(src_dir):
                        os.makedirs(dst_dir, exist_ok=True)
                        for item in os.listdir(src_dir):
                            if process_item(os.path.join(src_dir, item), os.path.join(dst_dir, item)):
                                migrated_count += 1

            from PySide6.QtCore import QTimer
            QTimer.singleShot(0, lambda: self._on_migration_finished(migrated_count))
        except Exception as e:
            from PySide6.QtCore import QTimer
            QTimer.singleShot(0, lambda: self._on_migration_error(str(e)))

    def _on_migration_finished(self, count):
        self.progress_dialog.accept()
        messagebox.showinfo(self, c.t("UI_SUCCESS_TITLE"), c.t("UI_MIGRATION_SUCCESS_MSG", count=count))
        self.parent_app.logic.refresh_version_list(self.parent_app)
        self.accept()

    def _on_migration_error(self, err):
        self.progress_dialog.accept()
        messagebox.showerror(self, c.t("UI_ERROR_TITLE"), f"Error: {err}")

    # ─────────────── Styling ───────────────

    def apply_styles(self):
        accent = c.THEME_COLOR_MAP.get(self.parent_app.config.get(c.CONFIG_KEY_COLOR_THEME, "blue"), "#1f6aa5")
        self.setStyleSheet(self.styleSheet() + f"""
            QDialog {{ background-color: #242424; }}
            #HeaderFrame {{ background-color: #333333; border-bottom: 1px solid #444444; }}
            #FooterFrame {{ background-color: #2b2b2b; border-top: 1px solid #444444; }}
            QLabel {{ color: #DCE4EE; }}
            QPushButton {{ 
                background-color: {accent}; color: white; border: none;
                border-radius: 8px; font-weight: bold; padding: 8px;
                font-size: 13px;
            }}
            QPushButton:hover {{ background-color: {accent}dd; }}
            QPushButton:disabled {{ background-color: #444444; color: #666666; }}
            QPushButton#BrowseButton {{ 
                background-color: #3a3a3a; border: 1px solid {accent}; color: {accent};
                padding: 8px 18px; font-size: 13px; border-radius: 8px;
            }}
            QPushButton#BrowseButton:hover {{ background-color: #4a4a4a; border: 1px solid white; }}
            QLineEdit {{ 
                background-color: #1e1e1e; color: white; border: 1px solid #666666; 
                border-radius: 6px; padding: 8px; min-height: 20px;
            }}
            QLineEdit:focus {{ border: 1px solid {accent}; }}
            QLineEdit:read-only {{ background-color: #2a2a2a; color: #cccccc; border: 1px solid #444444; }}
            QComboBox {{ 
                background-color: #1e1e1e; color: white; border: 1px solid #666666; 
                border-radius: 6px; padding: 6px 10px; min-height: 28px;
                font-size: 13px;
            }}
            QComboBox:hover {{ border: 1px solid #aaaaaa; }}
            QComboBox::drop-down {{ 
                border: none; width: 32px; 
                subcontrol-origin: padding;
                subcontrol-position: top right;
            }}
            QComboBox::down-arrow {{
                width: 10px; height: 10px;
            }}
            QComboBox QAbstractItemView {{
                background-color: #2a2a2a; color: white; 
                selection-background-color: {accent}; border: 1px solid #555555;
                border-radius: 4px; padding: 4px;
                outline: none;
            }}
            QCheckBox {{ color: #DCE4EE; spacing: 8px; font-size: 13px; }}
            QCheckBox::indicator {{ width: 18px; height: 18px; }}
            QScrollArea {{ background: transparent; border: none; }}
        """)
