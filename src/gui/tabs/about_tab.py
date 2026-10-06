import os
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QFrame, QLabel,
    QScrollArea, QPushButton, QGridLayout, QSizePolicy,
    QDialog, QTextBrowser
)
from PySide6.QtGui import (
    QPixmap, QPainter, QColor, QFont, QPen, QLinearGradient,
    QPainterPath, QIcon, QDesktopServices
)
from PySide6.QtCore import Qt, QRectF, QSize, QUrl
from src.utils.resource_path import resource_path
from src.utils.image_manager import ImageManager
from src import constants as c


class AboutHeroCard(QFrame):
    """
    Right card for About tab displaying launcher branding, feature badges,
    credits, interest links, and the scenic wallpaper wall-about_us.png.
    Supports dynamic Light and Dark mode theme rendering.
    """
    def __init__(self, parent=None, app=None):
        super().__init__(parent)
        self.app = app
        self.setObjectName("AboutHeroCard")
        self.setMinimumWidth(260)
        self.setMaximumWidth(410)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self._bg_pixmap = None
        self._cached_target_h = None
        self._cached_scaled_bg = None

        wall_path = resource_path("wall-about_us.png")
        if not os.path.exists(wall_path):
            wall_path = resource_path("assets/media/wall-about_us.png")
        if os.path.exists(wall_path):
            self._bg_pixmap = QPixmap(wall_path)

        self._init_ui()
        self.update_theme_styles()

    def is_dark_mode(self):
        if self.app and hasattr(self.app, "is_dark_mode"):
            return self.app.is_dark_mode
        if self.app and hasattr(self.app, "config"):
            return self.app.config.get(c.CONFIG_KEY_APPEARANCE, "Dark") == "Dark"
        return True

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        is_dark = self.is_dark_mode()

        # 1. Rounded rectangle clipping
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 14, 14)
        painter.setClipPath(path)

        # 2. Base card fill
        base_color = QColor(18, 20, 25) if is_dark else QColor(255, 255, 255)
        painter.fillRect(self.rect(), base_color)

        # 3. Scenic wallpaper at bottom (Steve & campfire)
        if self._bg_pixmap and not self._bg_pixmap.isNull():
            target_h = int(self.height() * 0.68)
            if target_h > 0:
                if self._cached_scaled_bg is None or self._cached_target_h != target_h:
                    self._cached_scaled_bg = self._bg_pixmap.scaledToHeight(target_h, Qt.SmoothTransformation)
                    self._cached_target_h = target_h
                scaled = self._cached_scaled_bg
                img_x = int(155 - scaled.width() * 0.38)
                img_y = self.height() - scaled.height()
                painter.drawPixmap(img_x, img_y, scaled)

        # 4. Vertical gradient overlay for text legibility at the top
        grad = QLinearGradient(0, 0, 0, self.height())
        if is_dark:
            grad.setColorAt(0.0, QColor(14, 16, 20, 250))
            grad.setColorAt(0.46, QColor(14, 16, 20, 240))
            grad.setColorAt(0.66, QColor(14, 16, 20, 160))
            grad.setColorAt(0.80, QColor(14, 16, 20, 50))
            grad.setColorAt(1.0, QColor(14, 16, 20, 10))
        else:
            grad.setColorAt(0.0, QColor(255, 255, 255, 252))
            grad.setColorAt(0.46, QColor(255, 255, 255, 242))
            grad.setColorAt(0.66, QColor(255, 255, 255, 170))
            grad.setColorAt(0.80, QColor(255, 255, 255, 45))
            grad.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.fillRect(self.rect(), grad)

        # 5. Subtle card border
        painter.setClipping(False)
        border_pen = QPen(QColor(255, 255, 255, 22) if is_dark else QColor(0, 0, 0, 22), 1)
        painter.setPen(border_pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 14, 14)
        painter.end()

    def _init_ui(self):
        right_layout = QVBoxLayout(self)
        right_layout.setContentsMargins(20, 18, 20, 16)
        right_layout.setSpacing(10)

        # Branding header with launcher logo
        brand_row = QHBoxLayout()
        brand_row.setContentsMargins(0, 0, 0, 4)
        brand_row.setSpacing(12)

        lbl_launcher_logo = QLabel()
        launcher_pix = ImageManager.get_image("icon.png", (52, 52))
        if not launcher_pix or launcher_pix.isNull():
            icon_p = resource_path("assets/media/icon.png")
            if not os.path.exists(icon_p):
                icon_p = resource_path("icon.png")
            if os.path.exists(icon_p):
                launcher_pix = QPixmap(icon_p).scaled(52, 52, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        if launcher_pix and not launcher_pix.isNull():
            lbl_launcher_logo.setPixmap(launcher_pix)
        lbl_launcher_logo.setFixedSize(52, 52)
        lbl_launcher_logo.setStyleSheet("background: transparent; border: none;")
        brand_row.addWidget(lbl_launcher_logo)

        brand_txt = QVBoxLayout()
        brand_txt.setSpacing(2)

        row_title_ver = QHBoxLayout()
        row_title_ver.setSpacing(8)
        self.lbl_bname = QLabel("Cianova Launcher")
        self.lbl_bver = QLabel(f"v{c.VERSION_LAUNCHER}")
        row_title_ver.addWidget(self.lbl_bname)
        row_title_ver.addWidget(self.lbl_bver)
        row_title_ver.addStretch()
        brand_txt.addLayout(row_title_ver)

        self.lbl_bsub = QLabel(c.t("UI_HERO_SUB"))
        self.lbl_bmotto = QLabel(c.t("UI_HERO_MOTTO"))
        brand_txt.addWidget(self.lbl_bsub)
        brand_txt.addWidget(self.lbl_bmotto)
        brand_row.addLayout(brand_txt, 1)

        right_layout.addLayout(brand_row)

        # 2x2 Feature badges grid
        self.grid_badges = QGridLayout()
        self.grid_badges.setContentsMargins(0, 4, 0, 4)
        self.grid_badges.setSpacing(8)

        self.badge_widgets = []
        badge_specs = [
            ("</>", "UI_HERO_BADGE_OPEN_TITLE", "UI_HERO_BADGE_OPEN_SUB", 0, 0),
            ("👥", "UI_HERO_BADGE_COMM_TITLE", "UI_HERO_BADGE_COMM_SUB", 0, 1),
            ("❤️", "UI_HERO_BADGE_NONPROFIT_TITLE", "UI_HERO_BADGE_NONPROFIT_SUB", 1, 0),
            ("🐧", "UI_HERO_BADGE_LINUX_TITLE", "UI_HERO_BADGE_LINUX_SUB", 1, 1),
        ]
        for icon_str, title_key, sub_key, row, col in badge_specs:
            b = QFrame()
            bl = QHBoxLayout(b)
            bl.setContentsMargins(10, 8, 10, 8)
            bl.setSpacing(10)

            ic = QLabel(icon_str)
            bl.addWidget(ic, 0, Qt.AlignCenter)

            tx = QVBoxLayout()
            tx.setSpacing(1)
            t1 = QLabel(c.t(title_key))
            t2 = QLabel(c.t(sub_key))
            tx.addWidget(t1)
            tx.addWidget(t2)
            bl.addLayout(tx, 1)

            self.badge_widgets.append((b, ic, t1, t2, title_key, sub_key))
            self.grid_badges.addWidget(b, row, col)

        right_layout.addLayout(self.grid_badges)

        # Section: Developers
        self.dev_header = QLabel(c.t("UI_HERO_DEV_HEADER"))
        right_layout.addWidget(self.dev_header)

        dev_row = QHBoxLayout()
        dev_row.setContentsMargins(4, 0, 4, 0)
        dev_row.setSpacing(10)
        self.dev_labels = []
        for dev in ["@PlaGaDev", "@Leimsoto", "@darkanubis0100", "@ShaggyLinux"]:
            lbl_dev = QLabel(dev)
            self.dev_labels.append(lbl_dev)
            dev_row.addWidget(lbl_dev)
        dev_row.addStretch()
        right_layout.addLayout(dev_row)

        # Section: Links of Interest
        self.links_header = QLabel(c.t("UI_HERO_LINKS_HEADER"))
        right_layout.addWidget(self.links_header)

        links_list = [
            ("github_icon.svg", "UI_HERO_LINK_GITHUB", "https://github.com/CianovaTeam/CianovaLauncher-mcpelauncher"),
            ("discord_icon.svg", "UI_HERO_LINK_DISCORD", "https://discord.gg/las-tortuguitas-de-ezku-1214414622111567892"),
            ("globe_icon.svg", "UI_HERO_LINK_WEB", "https://cianovalauncher.org/")
        ]

        self.link_button_widgets = []
        for icon_name, text_key, url in links_list:
            btn = QPushButton()
            btn.setFixedHeight(36)
            btn.setCursor(Qt.PointingHandCursor)

            btn_layout = QHBoxLayout(btn)
            btn_layout.setContentsMargins(10, 0, 10, 0)
            btn_layout.setSpacing(10)

            lbl_icon = QLabel()
            pm = ImageManager.get_image(icon_name, (18, 18))
            if pm and not pm.isNull():
                lbl_icon.setPixmap(pm)
            lbl_icon.setFixedSize(18, 18)
            lbl_icon.setStyleSheet("background: transparent; border: none;")
            btn_layout.addWidget(lbl_icon)

            lbl_text = QLabel(c.t(text_key))
            btn_layout.addWidget(lbl_text, 1)

            lbl_ext = QLabel()
            ext_pm = ImageManager.get_image("external_link_icon.svg", (14, 14))
            if ext_pm and not ext_pm.isNull():
                lbl_ext.setPixmap(ext_pm)
            else:
                lbl_ext.setText("↗")
            lbl_ext.setFixedSize(14, 14)
            btn_layout.addWidget(lbl_ext)

            btn.clicked.connect(lambda _, u=url: QDesktopServices.openUrl(QUrl(u)))
            right_layout.addWidget(btn)
            self.link_button_widgets.append((btn, lbl_text, lbl_ext, text_key))

        right_layout.addStretch(1)

    def retranslate_ui(self):
        """Update localized texts when language changes."""
        self.lbl_bsub.setText(c.t("UI_HERO_SUB"))
        self.lbl_bmotto.setText(c.t("UI_HERO_MOTTO"))
        for b, ic, t1, t2, title_key, sub_key in self.badge_widgets:
            t1.setText(c.t(title_key))
            t2.setText(c.t(sub_key))
        self.dev_header.setText(c.t("UI_HERO_DEV_HEADER"))
        self.links_header.setText(c.t("UI_HERO_LINKS_HEADER"))
        for btn, lbl_text, lbl_ext, text_key in self.link_button_widgets:
            lbl_text.setText(c.t(text_key))


    def update_theme_styles(self):
        is_dark = self.is_dark_mode()

        # Branding
        title_color = "#ffffff" if is_dark else "#111827"
        ver_color = "#00d2d3" if is_dark else "#0284c7"
        sub_color = "#dedede" if is_dark else "#374151"
        motto_color = "#9e9e9e" if is_dark else "#6b7280"

        self.lbl_bname.setStyleSheet(f"font-size: 19px; font-weight: bold; color: {title_color}; background: transparent; border: none;")
        self.lbl_bver.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {ver_color}; background: transparent; border: none;")
        self.lbl_bsub.setStyleSheet(f"font-size: 12.5px; color: {sub_color}; background: transparent; border: none;")
        self.lbl_bmotto.setStyleSheet(f"font-size: 11px; color: {motto_color}; background: transparent; border: none;")

        # Badges 2x2
        badge_bg = "rgba(22, 24, 29, 0.75)" if is_dark else "rgba(255, 255, 255, 0.85)"
        badge_border = "rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.08)"
        badge_ic_color = "#00d2d3" if is_dark else "#0284c7"
        badge_title_color = "#ffffff" if is_dark else "#111827"
        badge_sub_color = "#8e9297" if is_dark else "#6b7280"

        for b, ic, t1, t2, *_ in self.badge_widgets:
            b.setStyleSheet(f"""
                QFrame {{
                    background-color: {badge_bg};
                    border: 1px solid {badge_border};
                    border-radius: 8px;
                }}
            """)
            ic.setStyleSheet(f"font-size: 16px; color: {badge_ic_color}; background: transparent; border: none;")
            t1.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {badge_title_color}; background: transparent; border: none;")
            t2.setStyleSheet(f"font-size: 10px; color: {badge_sub_color}; background: transparent; border: none;")

        # Developers
        dev_h_color = "#dedede" if is_dark else "#374151"
        dev_t_color = "#9e9e9e" if is_dark else "#6b7280"
        self.dev_header.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {dev_h_color}; background: transparent; border: none; margin-top: 4px;")
        for lbl_dev in self.dev_labels:
            lbl_dev.setStyleSheet(f"font-size: 11.5px; color: {dev_t_color}; background: transparent; border: none;")

        # Links
        links_h_color = "#dedede" if is_dark else "#374151"
        self.links_header.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {links_h_color}; background: transparent; border: none; margin-top: 4px;")

        btn_bg = "rgba(22, 24, 29, 0.75)" if is_dark else "rgba(255, 255, 255, 0.85)"
        btn_border = "rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.08)"
        btn_hover = "rgba(35, 38, 46, 0.85)" if is_dark else "rgba(243, 244, 246, 0.95)"
        btn_hover_border = "rgba(255, 255, 255, 0.16)" if is_dark else "rgba(0, 0, 0, 0.16)"
        btn_pressed = "rgba(18, 20, 24, 0.9)" if is_dark else "rgba(229, 231, 235, 0.95)"
        btn_txt_color = "#dedede" if is_dark else "#1f2937"
        ext_color = "#8e9297" if is_dark else "#6b7280"

        for btn, lbl_text, lbl_ext, *_ in self.link_button_widgets:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {btn_bg};
                    border: 1px solid {btn_border};
                    border-radius: 8px;
                    padding: 0 12px;
                    text-align: left;
                }}
                QPushButton:hover {{
                    background-color: {btn_hover};
                    border-color: {btn_hover_border};
                }}
                QPushButton:pressed {{
                    background-color: {btn_pressed};
                }}
            """)
            lbl_text.setStyleSheet(f"font-size: 12px; color: {btn_txt_color}; background: transparent; border: none;")
            lbl_ext.setStyleSheet(f"font-size: 11px; color: {ext_color}; background: transparent; border: none;")

class TermsDialog(QDialog):
    """
    Modal popup displaying the full Terms and Conditions dynamically
    loaded from Docs/LICENCE & TERMINOS y CONDICIONES.md.
    Supports dynamic Light and Dark theme styling.
    """
    def __init__(self, parent=None, app=None):
        super().__init__(parent)
        self.app = app
        self.setWindowTitle(c.t("UI_TERMS_DLG_TITLE"))
        self.resize(800, 640)
        self.setMinimumSize(620, 480)
        self._init_ui()
        self.apply_theme()

    def is_dark_mode(self):
        if self.app and hasattr(self.app, "is_dark_mode"):
            return self.app.is_dark_mode
        if self.app and hasattr(self.app, "config"):
            return self.app.config.get(c.CONFIG_KEY_APPEARANCE, "Dark") == "Dark"
        return True

    def _get_doc_path(self):
        candidates = [
            resource_path("Docs/LICENCE & TERMINOS y CONDICIONES.md"),
            resource_path("LICENCE & TERMINOS y CONDICIONES.md"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "Docs", "LICENCE & TERMINOS y CONDICIONES.md"),
        ]
        for p in candidates:
            if os.path.exists(p):
                return p
        return ""

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self.container = QFrame()
        self.container.setObjectName("TermsDialogContainer")
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(20, 18, 20, 18)
        container_layout.setSpacing(14)

        # Header with Icon, Title, and Close Button
        header = QHBoxLayout()
        header.setSpacing(12)

        self.lbl_icon = QLabel()
        book_pix = ImageManager.get_image("book_terms_icon.svg", (36, 36))
        if book_pix and not book_pix.isNull():
            self.lbl_icon.setPixmap(book_pix)
        else:
            self.lbl_icon.setText("⚖️")
            self.lbl_icon.setStyleSheet("font-size: 26px; background: transparent;")
        self.lbl_icon.setFixedSize(36, 36)
        self.lbl_icon.setStyleSheet("background: transparent; border: none;")
        header.addWidget(self.lbl_icon, 0, Qt.AlignVCenter)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        self.lbl_title = QLabel(c.t("UI_TERMS_DLG_HEADER_TITLE"))
        self.lbl_sub = QLabel(c.t("UI_TERMS_DLG_HEADER_SUB"))
        title_col.addWidget(self.lbl_title)
        title_col.addWidget(self.lbl_sub)
        header.addLayout(title_col, 1)

        self.btn_close = QPushButton("✕")
        self.btn_close.setFixedSize(32, 32)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.clicked.connect(self.accept)
        header.addWidget(self.btn_close, 0, Qt.AlignTop)

        container_layout.addLayout(header)

        # Markdown Text Browser
        self.text_browser = QTextBrowser()
        self.text_browser.setOpenExternalLinks(True)

        doc_path = self._get_doc_path()
        content = ""
        if doc_path and os.path.exists(doc_path):
            try:
                with open(doc_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception as e:
                content = f"# Error reading document\n\nCould not open file:\n`{e}`"
        else:
            content = "# File not found\n\nCould not locate `Docs/LICENCE & TERMINOS y CONDICIONES.md`."

        self.text_browser.setMarkdown(content)
        container_layout.addWidget(self.text_browser, 1)

        # Footer
        footer = QHBoxLayout()
        footer.setSpacing(10)

        self.lbl_status = QLabel(c.t("UI_TERMS_DLG_ORIGIN"))
        footer.addWidget(self.lbl_status, 1)

        self.btn_ok = QPushButton(c.t("UI_TERMS_DLG_BTN_OK"))
        self.btn_ok.setFixedSize(130, 36)
        self.btn_ok.setCursor(Qt.PointingHandCursor)
        self.btn_ok.clicked.connect(self.accept)
        footer.addWidget(self.btn_ok, 0)

        container_layout.addLayout(footer)
        layout.addWidget(self.container)

    def apply_theme(self):
        is_dark = self.is_dark_mode()
        accent = getattr(self.app, "current_accent_color", "#38b6ff") if self.app else "#38b6ff"

        if is_dark:
            self.setStyleSheet("background-color: #0e1014;")
            self.container.setStyleSheet("""
                QFrame#TermsDialogContainer {
                    background-color: rgba(22, 24, 29, 0.98);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 12px;
                }
            """)
            self.lbl_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff; background: transparent; border: none;")
            self.lbl_sub.setStyleSheet("font-size: 11.5px; color: #8e9297; background: transparent; border: none;")
            self.btn_close.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: #8e9297;
                    border: none;
                    font-size: 16px;
                    border-radius: 6px;
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 0.08);
                    color: #ffffff;
                }
            """)
            self.text_browser.setStyleSheet("""
                QTextBrowser {
                    background-color: #101216;
                    border: 1px solid rgba(255, 255, 255, 0.06);
                    border-radius: 8px;
                    padding: 14px 18px;
                    color: #dedede;
                    font-size: 13.5px;
                }
                QScrollBar:vertical { width: 6px; background: transparent; margin: 0; }
                QScrollBar::handle:vertical { background: rgba(255, 255, 255, 0.18); border-radius: 3px; min-height: 24px; }
                QScrollBar::handle:vertical:hover { background: rgba(255, 255, 255, 0.35); }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            """)
            self.lbl_status.setStyleSheet("font-size: 11px; color: #7f8c8d; background: transparent; border: none;")
            self.btn_ok.setStyleSheet(f"""
                QPushButton {{
                    background-color: {accent};
                    color: #ffffff;
                    font-weight: bold;
                    font-size: 13px;
                    border-radius: 8px;
                    border: none;
                }}
                QPushButton:hover {{
                    background-color: #2da1e7;
                }}
                QPushButton:pressed {{
                    background-color: #1a7ab5;
                }}
            """)
        else:
            self.setStyleSheet("background-color: #f0f2f5;")
            self.container.setStyleSheet("""
                QFrame#TermsDialogContainer {
                    background-color: rgba(255, 255, 255, 0.98);
                    border: 1px solid rgba(0, 0, 0, 0.08);
                    border-radius: 12px;
                }
            """)
            self.lbl_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #111827; background: transparent; border: none;")
            self.lbl_sub.setStyleSheet("font-size: 11.5px; color: #6b7280; background: transparent; border: none;")
            self.btn_close.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: #6b7280;
                    border: none;
                    font-size: 16px;
                    border-radius: 6px;
                }
                QPushButton:hover {
                    background: rgba(0, 0, 0, 0.06);
                    color: #111827;
                }
            """)
            self.text_browser.setStyleSheet("""
                QTextBrowser {
                    background-color: #f8fafc;
                    border: 1px solid rgba(0, 0, 0, 0.08);
                    border-radius: 8px;
                    padding: 14px 18px;
                    color: #1f2937;
                    font-size: 13.5px;
                }
                QScrollBar:vertical { width: 6px; background: transparent; margin: 0; }
                QScrollBar::handle:vertical { background: rgba(0, 0, 0, 0.15); border-radius: 3px; min-height: 24px; }
                QScrollBar::handle:vertical:hover { background: rgba(0, 0, 0, 0.30); }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            """)
            self.lbl_status.setStyleSheet("font-size: 11px; color: #6b7280; background: transparent; border: none;")
            self.btn_ok.setStyleSheet(f"""
                QPushButton {{
                    background-color: {accent if accent != '#38b6ff' else '#0284c7'};
                    color: #ffffff;
                    font-weight: bold;
                    font-size: 13px;
                    border-radius: 8px;
                    border: none;
                }}
                QPushButton:hover {{
                    background-color: #0369a1;
                }}
                QPushButton:pressed {{
                    background-color: #075985;
                }}
            """)


class AboutTab(QWidget):
    """
    Modern 'Acerca de' tab replicating the community mockup:
    - Left/Center: Terms and Conditions card with 4 numbered sections expanded comfortably,
      large legible typography, and bottom acceptance bar.
    - Right: Cianova Launcher hero card with branding, badges, developers, interest links,
      and wall-about_us.png wallpaper.
    Supports dynamic Light and Dark mode theme rendering.
    """
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.setObjectName("AboutTab")

        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(18, 12, 18, 16)
        self.main_layout.setSpacing(14)

        self._init_ui()
        self.update_theme_styles()

    def is_dark_mode(self):
        if self.app and hasattr(self.app, "is_dark_mode"):
            return self.app.is_dark_mode
        if self.app and hasattr(self.app, "config"):
            return self.app.config.get(c.CONFIG_KEY_APPEARANCE, "Dark") == "Dark"
        return True

    def _init_ui(self):
        # ─────────────────────────────────────────────────────────────
        # 1. CENTRAL CARD: Terms and Conditions
        # ─────────────────────────────────────────────────────────────
        self.card_left = QFrame()
        self.card_left.setObjectName("TermsCard")
        left_layout = QVBoxLayout(self.card_left)
        left_layout.setContentsMargins(24, 20, 24, 18)
        left_layout.setSpacing(16)

        # Header with book icon, title, subtitle, and responsive actions
        header_container = QVBoxLayout()
        header_container.setContentsMargins(0, 0, 0, 4)
        header_container.setSpacing(8)

        header_top_row = QHBoxLayout()
        header_top_row.setContentsMargins(0, 0, 0, 0)
        header_top_row.setSpacing(14)

        lbl_book = QLabel()
        book_pix = ImageManager.get_image("book_terms_icon.svg", (48, 48))
        if book_pix and not book_pix.isNull():
            lbl_book.setPixmap(book_pix)
        else:
            lbl_book.setText("📖")
            lbl_book.setStyleSheet("font-size: 30px; background: transparent;")
        lbl_book.setFixedSize(48, 48)
        lbl_book.setStyleSheet("background: transparent; border: none;")
        header_top_row.addWidget(lbl_book, 0, Qt.AlignVCenter)

        title_box = QVBoxLayout()
        title_box.setSpacing(3)
        self.lbl_title = QLabel(c.t("UI_TERMS_TITLE"))
        self.lbl_subtitle = QLabel(c.t("UI_TERMS_SUBTITLE"))
        self.lbl_subtitle.setWordWrap(True)
        title_box.addWidget(self.lbl_title)
        title_box.addWidget(self.lbl_subtitle)
        header_top_row.addLayout(title_box, 1)

        header_container.addLayout(header_top_row)

        # Actions row (Date + View Document)
        header_actions = QHBoxLayout()
        header_actions.setContentsMargins(62, 0, 0, 0)
        header_actions.setSpacing(10)

        self.date_box = QFrame()
        date_layout = QHBoxLayout(self.date_box)
        date_layout.setContentsMargins(10, 4, 12, 4)
        date_layout.setSpacing(6)

        lbl_cal = QLabel()
        cal_pix = ImageManager.get_image("calendar_icon.svg", (14, 14))
        if cal_pix and not cal_pix.isNull():
            lbl_cal.setPixmap(cal_pix)
        else:
            lbl_cal.setText("📅")
            lbl_cal.setStyleSheet("font-size: 11px; background: transparent;")
        lbl_cal.setFixedSize(14, 14)
        lbl_cal.setStyleSheet("background: transparent; border: none;")
        date_layout.addWidget(lbl_cal)

        self.lbl_date = QLabel(c.t("UI_TERMS_DATE"))
        date_layout.addWidget(self.lbl_date)
        header_actions.addWidget(self.date_box, 0, Qt.AlignLeft)

        # Button to open full terms dialog dynamically from markdown document
        self.btn_full_terms = QPushButton(c.t("UI_TERMS_VIEW_DOC"))
        self.btn_full_terms.setFixedHeight(28)
        self.btn_full_terms.setCursor(Qt.PointingHandCursor)
        self.btn_full_terms.clicked.connect(self.open_terms_dialog)
        header_actions.addWidget(self.btn_full_terms, 0, Qt.AlignLeft)
        header_actions.addStretch(1)

        header_container.addLayout(header_actions)
        left_layout.addLayout(header_container)

        # Scroll Area for the 4 sections
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.viewport().setStyleSheet("background: transparent;")
        self.scroll.viewport().setAutoFillBackground(False)

        scroll_widget = QWidget()
        scroll_widget.setStyleSheet("background: transparent;")
        sec_layout = QVBoxLayout(scroll_widget)
        sec_layout.setContentsMargins(0, 6, 8, 6)
        sec_layout.setSpacing(14)

        # Helper to create a section
        def create_section(num_str, title_text, desc_text=None, inner_widget=None):
            container = QWidget()
            container.setStyleSheet("background: transparent;")
            c_layout = QHBoxLayout(container)
            c_layout.setContentsMargins(0, 0, 0, 0)
            c_layout.setSpacing(16)
            c_layout.setAlignment(Qt.AlignTop)

            badge = QLabel(num_str)
            badge.setFixedSize(36, 36)
            badge.setAlignment(Qt.AlignCenter)
            c_layout.addWidget(badge, 0, Qt.AlignTop)

            body_box = QVBoxLayout()
            body_box.setSpacing(6)
            lbl_stitle = QLabel(title_text)
            body_box.addWidget(lbl_stitle)

            lbl_desc = None
            if desc_text:
                lbl_desc = QLabel(desc_text)
                lbl_desc.setWordWrap(True)
                body_box.addWidget(lbl_desc)

            if inner_widget:
                body_box.addWidget(inner_widget)

            c_layout.addLayout(body_box, 1)
            return container, badge, lbl_stitle, lbl_desc

        # Section 1: Nature of the Project
        self.box1 = QFrame()
        b1_layout = QVBoxLayout(self.box1)
        b1_layout.setContentsMargins(14, 12, 14, 12)
        b1_layout.setSpacing(6)
        self.l1_note = QLabel(c.t("UI_TERMS_SEC1_NOTE1"))
        self.l1_note.setWordWrap(True)
        self.l2_note = QLabel(c.t("UI_TERMS_SEC1_NOTE2"))
        self.l2_note.setWordWrap(True)
        b1_layout.addWidget(self.l1_note)
        b1_layout.addWidget(self.l2_note)

        sec1_w, self.b1_badge, self.b1_title, self.b1_desc = create_section(
            "1", c.t("UI_TERMS_SEC1_TITLE"),
            c.t("UI_TERMS_SEC1_DESC"),
            self.box1
        )
        sec_layout.addWidget(sec1_w)
        sec_layout.addStretch(1)

        # Section 2: Attribution and Dependencies
        box2 = QWidget()
        box2.setStyleSheet("background: transparent;")
        b2_layout = QVBoxLayout(box2)
        b2_layout.setContentsMargins(0, 3, 0, 0)
        b2_layout.setSpacing(5)
        self.b2_labels = []
        for key in ["UI_TERMS_SEC2_ITEM1", "UI_TERMS_SEC2_ITEM2", "UI_TERMS_SEC2_ITEM3"]:
            lbl = QLabel(c.t(key))
            lbl.setWordWrap(True)
            self.b2_labels.append(lbl)
            b2_layout.addWidget(lbl)

        self.lbl_b2_note = QLabel(c.t("UI_TERMS_SEC2_NOTE"))
        self.lbl_b2_note.setWordWrap(True)
        b2_layout.addWidget(self.lbl_b2_note)

        sec2_w, self.b2_badge, self.b2_title, self.b2_desc = create_section(
            "2", c.t("UI_TERMS_SEC2_TITLE"),
            c.t("UI_TERMS_SEC2_DESC"),
            box2
        )
        sec_layout.addWidget(sec2_w)
        sec_layout.addStretch(1)

        # Section 3: Non-Profit Use
        sec3_w, self.b3_badge, self.b3_title, self.b3_desc = create_section(
            "3", c.t("UI_TERMS_SEC3_TITLE"),
            c.t("UI_TERMS_SEC3_DESC")
        )
        sec_layout.addWidget(sec3_w)
        sec_layout.addStretch(1)

        # Section 4: Disclaimer of Warranty
        self.box4 = QFrame()
        b4_layout = QHBoxLayout(self.box4)
        b4_layout.setContentsMargins(16, 14, 16, 14)
        b4_layout.setSpacing(16)

        lbl_warn = QLabel("⚠️")
        lbl_warn.setStyleSheet("font-size: 28px; background: transparent; border: none;")
        b4_layout.addWidget(lbl_warn, 0, Qt.AlignVCenter)

        col1 = QVBoxLayout()
        col1.setSpacing(5)
        self.b4_labels = []
        for i in range(1, 4):
            l = QLabel(c.t(f"UI_TERMS_SEC4_ITEM{i}"))
            l.setWordWrap(True)
            self.b4_labels.append(l)
            col1.addWidget(l)

        col2 = QVBoxLayout()
        col2.setSpacing(5)
        for i in range(4, 7):
            l = QLabel(c.t(f"UI_TERMS_SEC4_ITEM{i}"))
            l.setWordWrap(True)
            self.b4_labels.append(l)
            col2.addWidget(l)

        b4_layout.addLayout(col1, 1)
        b4_layout.addLayout(col2, 1)

        sec4_w, self.b4_badge, self.b4_title, self.b4_desc = create_section(
            "4", c.t("UI_TERMS_SEC4_TITLE"),
            c.t("UI_TERMS_SEC4_DESC"),
            self.box4
        )
        sec_layout.addWidget(sec4_w)

        self.scroll.setWidget(scroll_widget)
        left_layout.addWidget(self.scroll, 1)

        # Bottom acceptance bar
        self.bar_accept = QFrame()
        self.bar_accept.setFixedHeight(48)
        bar_layout = QHBoxLayout(self.bar_accept)
        bar_layout.setContentsMargins(14, 0, 14, 0)
        bar_layout.setSpacing(10)

        self.lbl_chk = QLabel("✔")
        self.lbl_chk.setFixedSize(20, 20)
        self.lbl_chk.setAlignment(Qt.AlignCenter)
        bar_layout.addWidget(self.lbl_chk)

        self.lbl_accept_text = QLabel(c.t("UI_TERMS_ACCEPT_MSG"))
        bar_layout.addWidget(self.lbl_accept_text, 1)

        self.lbl_made_with = QLabel(c.t("UI_TERMS_MADE_WITH"))
        bar_layout.addWidget(self.lbl_made_with, 0, Qt.AlignRight)

        left_layout.addWidget(self.bar_accept, 0)
        self.main_layout.addWidget(self.card_left, 1)

        # ─────────────────────────────────────────────────────────────
        # 2. RIGHT CARD: AboutHeroCard with wall-about_us.png wallpaper
        # ─────────────────────────────────────────────────────────────
        self.card_right = AboutHeroCard(app=self.app)
        self.main_layout.addWidget(self.card_right, 0)

    def update_theme_styles(self):
        """Update colors, backgrounds, borders and text styles for Light and Dark themes."""
        is_dark = self.is_dark_mode()

        # 1. TermsCard container
        card_bg = "rgba(22, 24, 29, 0.95)" if is_dark else "rgba(255, 255, 255, 0.95)"
        card_border = "rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.08)"
        self.card_left.setStyleSheet(f"""
            QFrame#TermsCard {{
                background-color: {card_bg};
                border: 1px solid {card_border};
                border-radius: 14px;
            }}
        """)

        # 2. Header
        title_color = "#ffffff" if is_dark else "#111827"
        subtitle_color = "#9e9e9e" if is_dark else "#6b7280"
        self.lbl_title.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {title_color}; background: transparent; border: none;")
        self.lbl_subtitle.setStyleSheet(f"font-size: 13.5px; color: {subtitle_color}; background: transparent; border: none;")

        # Date Badge
        date_bg = "rgba(255, 255, 255, 0.04)" if is_dark else "rgba(0, 0, 0, 0.04)"
        date_border = "rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.08)"
        date_color = "#dedede" if is_dark else "#374151"

        self.date_box.setStyleSheet(f"background: {date_bg}; border: 1px solid {date_border}; border-radius: 8px;")
        self.lbl_date.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {date_color}; background: transparent; border: none;")

        # Full Document Button
        if is_dark:
            self.btn_full_terms.setStyleSheet("""
                QPushButton {
                    background-color: rgba(56, 182, 255, 0.12);
                    border: 1px solid rgba(56, 182, 255, 0.35);
                    color: #38b6ff;
                    font-size: 11.5px;
                    font-weight: bold;
                    border-radius: 8px;
                    padding: 0 12px;
                }
                QPushButton:hover {
                    background-color: rgba(56, 182, 255, 0.25);
                    color: #ffffff;
                }
                QPushButton:pressed {
                    background-color: rgba(56, 182, 255, 0.06);
                }
            """)
        else:
            self.btn_full_terms.setStyleSheet("""
                QPushButton {
                    background-color: rgba(2, 132, 199, 0.08);
                    border: 1px solid rgba(2, 132, 199, 0.30);
                    color: #0284c7;
                    font-size: 11.5px;
                    font-weight: bold;
                    border-radius: 8px;
                    padding: 0 12px;
                }
                QPushButton:hover {
                    background-color: rgba(2, 132, 199, 0.16);
                    color: #0369a1;
                }
                QPushButton:pressed {
                    background-color: rgba(2, 132, 199, 0.05);
                }
            """)

        # Scrollbar
        handle_color = "rgba(255, 255, 255, 0.15)" if is_dark else "rgba(0, 0, 0, 0.15)"
        handle_hover = "rgba(255, 255, 255, 0.30)" if is_dark else "rgba(0, 0, 0, 0.30)"
        self.scroll.setStyleSheet(f"""
            QScrollArea {{ background: transparent; border: none; }}
            QScrollBar:vertical {{ width: 6px; background: transparent; margin: 0; }}
            QScrollBar::handle:vertical {{ background: {handle_color}; border-radius: 3px; min-height: 24px; }}
            QScrollBar::handle:vertical:hover {{ background: {handle_hover}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """)

        # 3. Section 1 (Green)
        sec_desc_color = "#b8bcc2" if is_dark else "#374151"
        b1_border = "#2ed573" if is_dark else "#16a34a"
        b1_bg = "rgba(46, 213, 115, 0.18)" if is_dark else "rgba(22, 163, 74, 0.12)"
        b1_txt = "#2ed573" if is_dark else "#15803d"

        self.b1_badge.setStyleSheet(f"""
            background-color: {b1_bg};
            border: 1.5px solid {b1_border};
            color: {b1_txt};
            font-size: 16px;
            font-weight: bold;
            border-radius: 8px;
        """)
        self.b1_title.setStyleSheet(f"font-size: 16.5px; font-weight: bold; color: {b1_txt}; background: transparent; border: none;")
        self.b1_desc.setStyleSheet(f"font-size: 13.5px; color: {sec_desc_color}; background: transparent; border: none; line-height: 1.5;")

        box_bg = "rgba(0, 0, 0, 0.35)" if is_dark else "rgba(0, 0, 0, 0.03)"
        box_border = "rgba(255, 255, 255, 0.05)" if is_dark else "rgba(0, 0, 0, 0.06)"
        self.box1.setStyleSheet(f"background-color: {box_bg}; border: 1px solid {box_border}; border-radius: 10px;")
        l1_color = "#dedede" if is_dark else "#1f2937"
        l2_color = "#9e9e9e" if is_dark else "#6b7280"
        self.l1_note.setStyleSheet(f"font-size: 13px; color: {l1_color}; background: transparent; border: none;")
        self.l2_note.setStyleSheet(f"font-size: 13px; color: {l2_color}; background: transparent; border: none;")

        # 4. Section 2 (Blue)
        b2_border = "#38b6ff" if is_dark else "#0284c7"
        b2_bg = "rgba(56, 182, 255, 0.18)" if is_dark else "rgba(2, 132, 199, 0.12)"
        b2_txt = "#38b6ff" if is_dark else "#0369a1"

        self.b2_badge.setStyleSheet(f"""
            background-color: {b2_bg};
            border: 1.5px solid {b2_border};
            color: {b2_txt};
            font-size: 16px;
            font-weight: bold;
            border-radius: 8px;
        """)
        self.b2_title.setStyleSheet(f"font-size: 16.5px; font-weight: bold; color: {b2_txt}; background: transparent; border: none;")
        self.b2_desc.setStyleSheet(f"font-size: 13.5px; color: {sec_desc_color}; background: transparent; border: none; line-height: 1.5;")
        for lbl in self.b2_labels:
            lbl.setStyleSheet(f"font-size: 13px; color: {sec_desc_color}; background: transparent; border: none;")
        b2_note_color = "#7f8c8d" if is_dark else "#6b7280"
        self.lbl_b2_note.setStyleSheet(f"font-size: 12px; color: {b2_note_color}; font-style: italic; background: transparent; border: none; margin-top: 4px;")

        # 5. Section 3 (Purple)
        b3_border = "#a855f7" if is_dark else "#9333ea"
        b3_bg = "rgba(168, 85, 247, 0.22)" if is_dark else "rgba(147, 51, 234, 0.12)"
        b3_txt = "#d8b4fe" if is_dark else "#7e22ce"

        self.b3_badge.setStyleSheet(f"""
            background-color: {b3_bg};
            border: 1.5px solid {b3_border};
            color: {b3_txt};
            font-size: 16px;
            font-weight: bold;
            border-radius: 8px;
        """)
        self.b3_title.setStyleSheet(f"font-size: 16.5px; font-weight: bold; color: {b3_txt}; background: transparent; border: none;")
        self.b3_desc.setStyleSheet(f"font-size: 13.5px; color: {sec_desc_color}; background: transparent; border: none; line-height: 1.5;")

        # 6. Section 4 (Orange)
        b4_border = "#f97316" if is_dark else "#ea580c"
        b4_bg = "rgba(249, 115, 22, 0.18)" if is_dark else "rgba(234, 88, 12, 0.12)"
        b4_txt = "#fb923c" if is_dark else "#c2410c"

        self.b4_badge.setStyleSheet(f"""
            background-color: {b4_bg};
            border: 1.5px solid {b4_border};
            color: {b4_txt};
            font-size: 16px;
            font-weight: bold;
            border-radius: 8px;
        """)
        self.b4_title.setStyleSheet(f"font-size: 16.5px; font-weight: bold; color: {b4_txt}; background: transparent; border: none;")
        self.b4_desc.setStyleSheet(f"font-size: 13.5px; color: {sec_desc_color}; background: transparent; border: none; line-height: 1.5;")

        self.box4.setStyleSheet(f"background-color: {box_bg}; border: 1px solid {box_border}; border-radius: 10px;")
        b4_item_color = "#9e9e9e" if is_dark else "#4b5563"
        for l in self.b4_labels:
            l.setStyleSheet(f"font-size: 12.5px; color: {b4_item_color}; background: transparent; border: none;")

        # 7. Bottom Acceptance Bar
        bar_bg = "rgba(46, 213, 115, 0.08)" if is_dark else "rgba(22, 163, 74, 0.08)"
        bar_border = "rgba(46, 213, 115, 0.3)" if is_dark else "rgba(22, 163, 74, 0.25)"
        self.bar_accept.setStyleSheet(f"""
            background-color: {bar_bg};
            border: 1px solid {bar_border};
            border-radius: 8px;
        """)
        chk_bg = "#2ed573" if is_dark else "#16a34a"
        chk_fg = "#0e1014" if is_dark else "#ffffff"
        self.lbl_chk.setStyleSheet(f"background-color: {chk_bg}; color: {chk_fg}; font-weight: bold; border-radius: 10px; font-size: 12px;")

        accept_text_color = "#dedede" if is_dark else "#1f2937"
        self.lbl_accept_text.setStyleSheet(f"font-size: 11.5px; color: {accept_text_color}; background: transparent; border: none;")

        made_with_color = "#2ed573" if is_dark else "#15803d"
        self.lbl_made_with.setStyleSheet(f"font-size: 11.5px; color: {made_with_color}; font-weight: bold; background: transparent; border: none;")

        # 8. Update right hero card styles
        if hasattr(self, "card_right") and hasattr(self.card_right, "update_theme_styles"):
            self.card_right.update_theme_styles()

    def open_terms_dialog(self):
        """Open modal dialog displaying Docs/LICENCE & TERMINOS y CONDICIONES.md."""
        dlg = TermsDialog(parent=self.window(), app=self.app)
        dlg.exec()

    def retranslate_ui(self):
        """Update all text labels in AboutTab when language changes."""
        self.lbl_title.setText(c.t("UI_TERMS_TITLE"))
        self.lbl_subtitle.setText(c.t("UI_TERMS_SUBTITLE"))
        self.lbl_date.setText(c.t("UI_TERMS_DATE"))
        self.btn_full_terms.setText(c.t("UI_TERMS_VIEW_DOC"))

        # Section 1
        self.b1_title.setText(c.t("UI_TERMS_SEC1_TITLE"))
        self.b1_desc.setText(c.t("UI_TERMS_SEC1_DESC"))
        self.l1_note.setText(c.t("UI_TERMS_SEC1_NOTE1"))
        self.l2_note.setText(c.t("UI_TERMS_SEC1_NOTE2"))

        # Section 2
        self.b2_title.setText(c.t("UI_TERMS_SEC2_TITLE"))
        self.b2_desc.setText(c.t("UI_TERMS_SEC2_DESC"))
        sec2_keys = ["UI_TERMS_SEC2_ITEM1", "UI_TERMS_SEC2_ITEM2", "UI_TERMS_SEC2_ITEM3"]
        for lbl, key in zip(self.b2_labels, sec2_keys):
            lbl.setText(c.t(key))
        self.lbl_b2_note.setText(c.t("UI_TERMS_SEC2_NOTE"))

        # Section 3
        self.b3_title.setText(c.t("UI_TERMS_SEC3_TITLE"))
        self.b3_desc.setText(c.t("UI_TERMS_SEC3_DESC"))

        # Section 4
        self.b4_title.setText(c.t("UI_TERMS_SEC4_TITLE"))
        self.b4_desc.setText(c.t("UI_TERMS_SEC4_DESC"))
        for i, lbl in enumerate(self.b4_labels, start=1):
            lbl.setText(c.t(f"UI_TERMS_SEC4_ITEM{i}"))

        # Bottom bar
        self.lbl_accept_text.setText(c.t("UI_TERMS_ACCEPT_MSG"))
        self.lbl_made_with.setText(c.t("UI_TERMS_MADE_WITH"))

        if hasattr(self, "card_right") and hasattr(self.card_right, "retranslate_ui"):
            self.card_right.retranslate_ui()

