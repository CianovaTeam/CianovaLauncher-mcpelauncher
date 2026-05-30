from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QFrame, QStackedWidget, QComboBox, 
                             QCheckBox, QTextEdit, QRadioButton, QGridLayout, QWidget, QScrollArea)
from PySide6.QtCore import Qt, QTimer
from src import constants as c
from src.core import language_manager
from src.utils.image_manager import ImageManager
from src.utils.logger import logger
import os

class SetupWizard(QDialog):
    """Multi-step wizard for first-run setup including language, legal, and appearance."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(c.t("UI_SETUP_WIZARD_TITLE"))
        self.resize(750, 650)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setModal(True)
        
        self.app = parent
        self.current_step = 0
        self.total_steps = 7 # Lang, Legal, Migration, Style, Install, Changelog, Summary
        
        self.setup_ui()

    def setup_ui(self):
        """Build the full wizard UI with header, stacked pages, and footer buttons."""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Header Area
        self.header_frame = QFrame()
        self.header_frame.setFixedHeight(80)
        self.header_frame.setObjectName("HeaderFrame")
        h_layout = QHBoxLayout(self.header_frame)
        
        self.lbl_title = QLabel(c.t("UI_SETUP_WELCOME_TITLE"))
        self.lbl_title.setStyleSheet("font-size: 20px; font-weight: bold; color: white;")
        h_layout.addWidget(self.lbl_title)
        
        h_layout.addStretch()
        
        self.lbl_step = QLabel(c.t("UI_SETUP_STEP", current=1, total=self.total_steps))
        self.lbl_step.setStyleSheet("color: #aaaaaa; font-weight: bold;")
        h_layout.addWidget(self.lbl_step)
        
        self.main_layout.addWidget(self.header_frame)

        # Content Area (Stacked Widget)
        self.stack = QStackedWidget()
        self.main_layout.addWidget(self.stack, 1)

        self.create_lang_step()          # 0
        self.create_legal_step()         # 1
        self.create_migration_step()     # 2
        self.create_style_step()         # 3
        self.create_install_step()       # 4
        self.create_changelog_step()     # 5
        self.create_summary_step()       # 6

        # Footer Area (Buttons)
        self.footer_frame = QFrame()
        self.footer_frame.setFixedHeight(75)
        self.footer_frame.setObjectName("FooterFrame")
        f_layout = QHBoxLayout(self.footer_frame)
        f_layout.setContentsMargins(25, 0, 25, 0)

        # Using standard button sizes and padding
        self.btn_back = QPushButton(c.t("UI_BUTTON_BACK"))
        self.btn_back.setMinimumSize(130, 40)
        self.btn_back.setEnabled(False)
        self.btn_back.clicked.connect(self.prev_step)
        f_layout.addWidget(self.btn_back)

        f_layout.addStretch()

        self.btn_next = QPushButton(c.t("UI_BUTTON_NEXT"))
        self.btn_next.setMinimumSize(130, 40)
        self.btn_next.setObjectName("ActionButton")
        self.btn_next.clicked.connect(self.next_step)
        f_layout.addWidget(self.btn_next)

        self.main_layout.addWidget(self.footer_frame)
        
        self.apply_styles()

    def create_lang_step(self):
        """Create the language selection wizard page."""
        page = QWidget()
        l = QVBoxLayout(page)
        l.setContentsMargins(50, 50, 50, 50)
        l.setSpacing(25)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(ImageManager.get_image("icon.png", size=(90, 90)))
        icon_lbl.setAlignment(Qt.AlignCenter)
        l.addWidget(icon_lbl)

        self.lbl_lang_title = QLabel(c.t("UI_SETUP_LANG_TITLE"))
        self.lbl_lang_title.setStyleSheet("font-size: 20px; font-weight: bold; color: white;")
        self.lbl_lang_title.setAlignment(Qt.AlignCenter)
        l.addWidget(self.lbl_lang_title)

        self.lbl_lang_sub = QLabel(c.t("UI_SETUP_WELCOME_SUB"))
        self.lbl_lang_sub.setWordWrap(True)
        self.lbl_lang_sub.setAlignment(Qt.AlignCenter)
        l.addWidget(self.lbl_lang_sub)

        l.addStretch()

        self.combo_lang = QComboBox()
        langs = language_manager.get_available_languages()
        self.combo_lang.addItems(list(langs.values()))
        self.combo_lang.setFixedHeight(35)
        
        curr_lang = self.app.config.get(c.CONFIG_KEY_LANGUAGE, "en")
        self.combo_lang.setCurrentText(langs.get(curr_lang, "English"))
        self.combo_lang.currentTextChanged.connect(self.on_lang_change)
        
        l.addWidget(self.combo_lang)
        l.addStretch()
        
        self.stack.addWidget(page)

    def create_legal_step(self):
        """Create the legal terms acceptance wizard page."""
        page = QWidget()
        l = QVBoxLayout(page)
        l.setContentsMargins(40, 30, 40, 30)
        l.setSpacing(15)
        
        self.lbl_legal_title = QLabel(c.t("UI_SETUP_LEGAL_TITLE"))
        self.lbl_legal_title.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        l.addWidget(self.lbl_legal_title)

        self.txt_legal = QTextEdit()
        self.txt_legal.setPlainText(c.t("LEGAL_TEXT"))
        self.txt_legal.setReadOnly(True)
        self.txt_legal.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4; font-size: 11px;")
        l.addWidget(self.txt_legal, 1)

        self.cb_accept = QCheckBox(c.t("UI_SETUP_LEGAL_CHECK"))
        self.cb_accept.stateChanged.connect(self.validate_next)
        l.addWidget(self.cb_accept)
        
        self.stack.addWidget(page)

    def create_migration_step(self):
        """Create the migration tool wizard page."""
        page = QWidget()
        l = QVBoxLayout(page)
        l.setContentsMargins(40, 50, 40, 50)
        l.setSpacing(25)
        
        self.lbl_mig_title = QLabel(c.t("UI_SETUP_MIGRATION_TITLE"))
        self.lbl_mig_title.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        self.lbl_mig_title.setAlignment(Qt.AlignCenter)
        l.addWidget(self.lbl_mig_title)

        self.lbl_mig_sub = QLabel(c.t("UI_SETUP_MIGRATION_SUB"))
        self.lbl_mig_sub.setWordWrap(True)
        self.lbl_mig_sub.setAlignment(Qt.AlignCenter)
        l.addWidget(self.lbl_mig_sub)

        l.addStretch()
        
        btn_open_mig = QPushButton(f"🚀 {c.t("UI_BUTTON_OPEN_MIGRATION")}")
        btn_open_mig.setFixedHeight(60)
        btn_open_mig.setStyleSheet("font-size: 15px; font-weight: bold;")
        btn_open_mig.clicked.connect(lambda: self.app.open_migration_tool())
        l.addWidget(btn_open_mig)
        
        l.addStretch()
        self.stack.addWidget(page)

    def create_style_step(self):
        """Create the appearance and theme customization wizard page."""
        page = QWidget()
        l = QVBoxLayout(page)
        l.setContentsMargins(40, 30, 40, 30)
        l.setSpacing(15)
        
        self.lbl_style_title = QLabel(c.t("UI_SETUP_APPEARANCE_TITLE"))
        self.lbl_style_title.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        l.addWidget(self.lbl_style_title)

        # Mode Toggle
        mode_layout = QHBoxLayout()
        self.lbl_app_mode = QLabel(c.t("UI_LABEL_APPEARANCE_MODE"))
        mode_layout.addWidget(self.lbl_app_mode)
        self.combo_mode = QComboBox()
        self.combo_mode.addItems(list(c.t("UI_APPEARANCE_MODES").values()))
        self.combo_mode.setCurrentText(c.t("UI_APPEARANCE_MODES").get(self.app.config.get(c.CONFIG_KEY_APPEARANCE, "Dark")))
        self.combo_mode.currentTextChanged.connect(self.on_appearance_change)
        mode_layout.addWidget(self.combo_mode)
        l.addLayout(mode_layout)

        l.addWidget(QLabel(c.t("UI_SETUP_RESTART_NOTE")), 0, Qt.AlignLeft)
        l.addSpacing(5)

        self.lbl_app_color = QLabel(c.t("UI_LABEL_COLOR_THEME"))
        l.addWidget(self.lbl_app_color)
        
        # Theme Gallery
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll_content = QWidget()
        grid = QGridLayout(scroll_content)
        grid.setSpacing(12)
        
        self.theme_btns = []
        themes = c.t("UI_COLOR_THEMES")
        for i, theme in enumerate(themes):
            btn = QPushButton()
            btn.setCheckable(True)
            btn.setFixedSize(45, 45)
            color = c.THEME_COLOR_MAP.get(theme, "#1f6aa5")
            btn.setStyleSheet(f"background-color: {color}; border-radius: 22px; border: 2px solid #555;")
            btn.setToolTip(c.t("UI_THEME_NAMES").get(theme, theme.capitalize()))
            
            if self.app.config.get(c.CONFIG_KEY_COLOR_THEME) == theme:
                btn.setChecked(True)
                btn.setStyleSheet(f"background-color: {color}; border-radius: 22px; border: 3px solid white;")
            
            btn.clicked.connect(lambda checked, t=theme: self.on_theme_selected(t))
            grid.addWidget(btn, i // 6, i % 6)
            self.theme_btns.append((btn, theme))
            
        scroll.setWidget(scroll_content)
        l.addWidget(scroll)

        # Version List Style
        l.addWidget(QLabel(c.t("UI_LABEL_VERSION_LIST_STYLE")))
        self.combo_list_style = QComboBox()
        self.combo_list_style.addItems(list(c.t("UI_LIST_STYLES").values()))
        curr_style = self.app.config.get(c.CONFIG_KEY_VERSION_LIST_STYLE, c.STYLE_LIST)
        self.combo_list_style.setCurrentText(c.t("UI_LIST_STYLES").get(curr_style, c.STYLE_LIST))
        l.addWidget(self.combo_list_style)
        
        l.addStretch()
        self.stack.addWidget(page)

    def create_install_step(self):
        """Create the initial APK installation wizard page."""
        page = QWidget()
        l = QVBoxLayout(page)
        l.setContentsMargins(50, 50, 50, 50)
        l.setSpacing(30)

        self.lbl_inst_title = QLabel(c.t("UI_SETUP_INSTALL_TITLE"))
        self.lbl_inst_title.setStyleSheet("font-size: 24px; font-weight: bold; color: white;")
        self.lbl_inst_title.setAlignment(Qt.AlignCenter)
        l.addWidget(self.lbl_inst_title)

        self.lbl_inst_sub = QLabel(c.t("UI_SETUP_INSTALL_SUB"))
        self.lbl_inst_sub.setWordWrap(True)
        self.lbl_inst_sub.setAlignment(Qt.AlignCenter)
        l.addWidget(self.lbl_inst_sub)

        l.addStretch()

        self.btn_install_wiz = QPushButton(f"📥 {c.t("UI_BUTTON_INSTALL_APK")}")
        self.btn_install_wiz.setFixedHeight(65)
        accent = c.THEME_COLOR_MAP.get(self.app.config.get(c.CONFIG_KEY_COLOR_THEME, "blue"), "#1f6aa5")
        self.btn_install_wiz.setStyleSheet(f"background-color: {accent}; color: white; font-size: 18px; font-weight: bold; border-radius: 12px;")
        self.btn_install_wiz.clicked.connect(lambda: self.app.install_apk_dialog())
        l.addWidget(self.btn_install_wiz)

        l.addStretch()
        self.stack.addWidget(page)

    def create_changelog_step(self):
        """Create the changelog display wizard page."""
        page = QWidget()
        l = QVBoxLayout(page)
        l.setContentsMargins(40, 30, 40, 30)
        l.setSpacing(15)

        self.lbl_ch_title = QLabel(c.t("UI_SETUP_CHANGELOG_TITLE"))
        self.lbl_ch_title.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        l.addWidget(self.lbl_ch_title)

        from PySide6.QtWidgets import QTextBrowser
        self.txt_changelog = QTextBrowser()
        self.txt_changelog.setReadOnly(True)
        self.txt_changelog.setFrameShape(QFrame.NoFrame)
        from src.utils.resource_path import resource_path
        try:
            path = resource_path("Docs/Changelog.md")
            if not os.path.exists(path):
                path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "Docs/Changelog.md")
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except: content = "Error loading changelog."

        self.txt_changelog.setMarkdown(content)
        self.txt_changelog.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4; padding: 5px;")
        l.addWidget(self.txt_changelog, 1)

        self.stack.addWidget(page)

    def create_summary_step(self):
        """Create the final summary wizard page with finish instructions."""
        page = QWidget()
        l = QVBoxLayout(page)
        l.setContentsMargins(50, 40, 50, 40)
        l.setSpacing(15)

        self.lbl_sum_title = QLabel(c.t("UI_SETUP_FINISH_TITLE"))
        self.lbl_sum_title.setStyleSheet("font-size: 22px; font-weight: bold; color: white;")
        self.lbl_sum_title.setAlignment(Qt.AlignCenter)
        l.addWidget(self.lbl_sum_title)

        self.lbl_sum_sub = QLabel()
        self.lbl_sum_sub.setWordWrap(True)
        self.lbl_sum_sub.setAlignment(Qt.AlignCenter)
        # Use HTML to guarantee line breaks across all Qt versions
        html_text = c.t("UI_SETUP_FINISH_SUB").replace("\n", "<br>")
        self.lbl_sum_sub.setText(html_text)
        self.lbl_sum_sub.setStyleSheet("color: #DCE4EE; font-size: 13px; line-height: 150%;")
        l.addWidget(self.lbl_sum_sub)

        l.addStretch()
        icon_lbl = QLabel()
        icon_lbl.setPixmap(ImageManager.get_image("icon.png", size=(80, 80)))
        icon_lbl.setAlignment(Qt.AlignCenter)
        l.addWidget(icon_lbl)
        l.addStretch()
        
        self.stack.addWidget(page)

    def on_lang_change(self, display_name):
        """Handle language selection change and refresh all UI strings."""
        langs = language_manager.get_available_languages()
        lang_code = next((k for k, v in langs.items() if v == display_name), "en")
        self.app.config[c.CONFIG_KEY_LANGUAGE] = lang_code
        self.app.config_manager.save_config()
        
        language_manager.load_language(lang_code)
        self.refresh_all_strings()

    def on_appearance_change(self, display_name):
        """Handle appearance mode change and apply the new theme."""
        mode_key = next((k for k, v in c.t("UI_APPEARANCE_MODES").items() if v == display_name), "Dark")
        self.app.config[c.CONFIG_KEY_APPEARANCE] = mode_key
        self.app.config_manager.save_config()
        self.app.apply_theme_settings()

    def on_theme_selected(self, theme_key):
        """Handle color theme selection and update the UI accent colors."""
        self.app.config[c.CONFIG_KEY_COLOR_THEME] = theme_key
        self.app.config_manager.save_config()
        self.app.apply_theme_settings()
        
        for btn, key in self.theme_btns:
            color = c.THEME_COLOR_MAP.get(key, "#1f6aa5")
            if key == theme_key:
                btn.setStyleSheet(f"background-color: {color}; border-radius: 22px; border: 3px solid white;")
            else:
                btn.setStyleSheet(f"background-color: {color}; border-radius: 22px; border: 2px solid #555;")

    def refresh_all_strings(self):
        """Reload all UI text labels to reflect the currently selected language."""
        self.setWindowTitle(c.t("UI_SETUP_WIZARD_TITLE"))
        self.lbl_step.setText(c.t("UI_SETUP_STEP", current=self.current_step + 1, total=self.total_steps))
        self.btn_back.setText(c.t("UI_BUTTON_BACK"))
        self.btn_next.setText(c.t("UI_BUTTON_FINISH") if self.current_step == self.total_steps - 1 else c.t("UI_BUTTON_NEXT"))
        if self.current_step == 4: self.btn_next.setText(c.t("UI_BUTTON_SKIP"))

        # Labels
        self.lbl_lang_title.setText(c.t("UI_SETUP_LANG_TITLE"))
        self.lbl_lang_sub.setText(c.t("UI_SETUP_WELCOME_SUB"))
        self.lbl_legal_title.setText(c.t("UI_SETUP_LEGAL_TITLE"))
        self.cb_accept.setText(c.t("UI_SETUP_LEGAL_CHECK"))
        self.lbl_mig_title.setText(c.t("UI_SETUP_MIGRATION_TITLE"))
        self.lbl_mig_sub.setText(c.t("UI_SETUP_MIGRATION_SUB"))
        self.lbl_style_title.setText(c.t("UI_SETUP_APPEARANCE_TITLE"))
        self.lbl_inst_title.setText(c.t("UI_SETUP_INSTALL_TITLE"))
        self.lbl_inst_sub.setText(c.t("UI_SETUP_INSTALL_SUB"))
        self.lbl_ch_title.setText(c.t("UI_SETUP_CHANGELOG_TITLE"))
        self.lbl_sum_title.setText(c.t("UI_SETUP_FINISH_TITLE"))
        self.lbl_sum_sub.setText(c.t("UI_SETUP_FINISH_SUB").replace("\n", "<br>"))

        # Update install button text and style (in case theme changed)

        self.btn_install_wiz.setText(f"📥 {c.t("UI_BUTTON_INSTALL_APK")}")
        accent = c.THEME_COLOR_MAP.get(self.app.config.get(c.CONFIG_KEY_COLOR_THEME, "blue"), "#1f6aa5")
        self.btn_install_wiz.setStyleSheet(f"background-color: {accent}; color: white; font-size: 18px; font-weight: bold; border-radius: 12px;")

        self.lbl_title.setText(c.t("UI_SETUP_WIZARD_TITLE") if self.current_step > 0 else c.t("UI_SETUP_WELCOME_TITLE"))

    def next_step(self):
        """Advance to the next wizard step or save and close on the final step."""
        if self.current_step < self.total_steps - 1:
            self.current_step += 1
            self.stack.setCurrentIndex(self.current_step)
            self.update_buttons()
        else:
            self.save_final_config()
            self.accept()

    def prev_step(self):
        """Go back to the previous wizard step."""
        if self.current_step > 0:
            self.current_step -= 1
            self.stack.setCurrentIndex(self.current_step)
            self.update_buttons()

    def update_buttons(self):
        """Update the back/next button text and enabled state for the current step."""
        self.btn_back.setEnabled(self.current_step > 0)
        
        # Logic for Skip button in step 4
        if self.current_step == 4:
            self.btn_next.setText(c.t("UI_BUTTON_SKIP"))
        elif self.current_step == self.total_steps - 1:
            self.btn_next.setText(c.t("UI_BUTTON_FINISH"))
        else:
            self.btn_next.setText(c.t("UI_BUTTON_NEXT"))

        self.lbl_title.setText(c.t("UI_SETUP_WIZARD_TITLE") if self.current_step > 0 else c.t("UI_SETUP_WELCOME_TITLE"))
        self.lbl_step.setText(c.t("UI_SETUP_STEP", current=self.current_step + 1, total=self.total_steps))
        self.validate_next()

    def validate_next(self):
        """Enable or disable the next button based on the current step's validation rules."""
        if self.current_step == 1: # Legal step
            self.btn_next.setEnabled(self.cb_accept.isChecked())
        else:
            self.btn_next.setEnabled(True)

    def save_final_config(self):
        """Persist the final configuration values to the config file."""
        style_disp = self.combo_list_style.currentText()
        style_key = next((k for k, v in c.t("UI_LIST_STYLES").items() if v == style_disp), c.STYLE_LIST)
        self.app.config[c.CONFIG_KEY_VERSION_LIST_STYLE] = style_key
        self.app.config[c.CONFIG_KEY_ACCEPTED_TERMS] = True
        self.app.config[c.CONFIG_KEY_VERSION] = c.VERSION_LAUNCHER
        self.app.config_manager.save_config()

    def apply_styles(self):
        """Apply theme-aware stylesheets to all wizard components."""
        accent = c.THEME_COLOR_MAP.get(self.app.config.get(c.CONFIG_KEY_COLOR_THEME, "blue"), "#1f6aa5")
        self.setStyleSheet(self.styleSheet() + f"""
            QDialog {{ background-color: #242424; }}
            #HeaderFrame {{ background-color: #333333; border-bottom: 1px solid #444444; }}
            #FooterFrame {{ background-color: #2b2b2b; border-top: 1px solid #444444; }}
            QLabel {{ color: #DCE4EE; }}
            QPushButton {{ 
                background-color: {accent}; 
                color: white; 
                border: none;
                border-radius: 8px; 
                font-weight: bold; 
                padding: 8px;
            }}
            QPushButton:hover {{
                background-color: {accent}dd;
            }}
            QPushButton:disabled {{
                background-color: #444444;
                color: #888888;
            }}
            QPushButton#FlatButton {{ 
                background-color: transparent; border: none; color: gray; text-decoration: underline; 
            }}
            QPushButton#FlatButton:hover {{ color: white; }}
        """)
