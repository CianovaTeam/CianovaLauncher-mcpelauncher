import os
import sys
import shutil
import platform
import ctypes.util
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QFrame, QWidget,
    QTabWidget, QApplication
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QIcon

from src import constants as c
from src.gui import custom_dialogs as messagebox
from src.gui.custom_dialogs import _find_theme
from src.utils.image_manager import ImageManager
from src.utils.colors import hex_to_rgba, blend_colors, adjust_color
from src.utils.process_utils import is_running_in_flatpak


def check_dynamic_library(candidates):
    """Check if any candidate dynamic library is available in the system."""
    for cand in candidates:
        # Attempt via ctypes.util.find_library
        res = ctypes.util.find_library(cand)
        if res:
            return True, res
        # If .so format, test removing .so or searching prefix
        clean_name = cand.split(".so")[0]
        if clean_name.startswith("lib"):
            clean_name = clean_name[3:]
        res2 = ctypes.util.find_library(clean_name)
        if res2:
            return True, res2
    return False, None


class DependenciesDialog(QDialog):
    """
    Modern dialog for system dependencies and dynamic library verification
    tailored to Native or Flatpak environments, including package installation guides.
    """
    def __init__(self, parent=None):
        parent_widget = parent if isinstance(parent, QWidget) else getattr(parent, "root", None)
        if not isinstance(parent_widget, QWidget):
            parent_widget = None
        super().__init__(parent_widget)
        self.app = parent
        self.setWindowTitle(c.t("UI_DEPS_DIALOG_TITLE"))
        self.resize(760, 680)
        self.setMinimumSize(640, 540)

        mode, self.accent = _find_theme(parent)
        self.is_dark = mode == "Dark"
        self.in_flatpak = getattr(self.app, "running_in_flatpak", False) or is_running_in_flatpak()

        self._setup_ui()
        self._apply_theme()
        self._run_diagnostics()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(22, 20, 22, 20)
        main_layout.setSpacing(14)

        # 1. Header with Icon and Title
        header_layout = QHBoxLayout()
        header_layout.setSpacing(16)

        self.icon_label = QLabel()
        self.icon_label.setFixedSize(48, 48)
        self.icon_label.setAlignment(Qt.AlignCenter)
        pix = ImageManager.get_image("tools_dependencies.png", size=(48, 48))
        if pix and not pix.isNull():
            self.icon_label.setPixmap(pix)
        else:
            self.icon_label.setText("🔌")
            self.icon_label.setStyleSheet("font-size: 28px;")
        header_layout.addWidget(self.icon_label)

        title_box = QVBoxLayout()
        title_box.setSpacing(3)
        self.lbl_title = QLabel(c.t("UI_DEPS_DIALOG_TITLE"))
        self.lbl_title.setObjectName("DialogTitle")
        self.lbl_subtitle = QLabel(c.t("UI_DEPS_DIALOG_SUBTITLE"))
        self.lbl_subtitle.setObjectName("DialogSubtitle")
        self.lbl_subtitle.setWordWrap(True)
        title_box.addWidget(self.lbl_title)
        title_box.addWidget(self.lbl_subtitle)
        header_layout.addLayout(title_box, 1)

        main_layout.addLayout(header_layout)

        # 2. Environment Status Summary Card
        self.status_card = QFrame()
        self.status_card.setObjectName("StatusSummaryCard")
        sc_l = QVBoxLayout(self.status_card)
        sc_l.setContentsMargins(16, 12, 16, 12)
        sc_l.setSpacing(6)

        top_info_row = QHBoxLayout()
        env_label = c.t("UI_DEPS_ENV_FLATPAK") if self.in_flatpak else c.t("UI_DEPS_ENV_NATIVE", arch=platform.machine())
        self.lbl_env_chip = QLabel(f"📦 {env_label}")
        self.lbl_env_chip.setObjectName("EnvChip")
        top_info_row.addWidget(self.lbl_env_chip)
        top_info_row.addStretch(1)

        self.lbl_global_status = QLabel(c.t("UI_DEPS_STATUS_CHECKING"))
        self.lbl_global_status.setObjectName("GlobalStatusBadge")
        top_info_row.addWidget(self.lbl_global_status)
        sc_l.addLayout(top_info_row)

        self.lbl_summary_desc = QLabel(c.t("UI_DEPS_STATUS_CHECKING"))
        self.lbl_summary_desc.setObjectName("SummaryDescLabel")
        sc_l.addWidget(self.lbl_summary_desc)
        main_layout.addWidget(self.status_card)

        # 3. Tabs: Real-Time Diagnostics / Package Guide
        self.tabs = QTabWidget()
        self.tabs.setObjectName("DepsTabWidget")

        # Tab 1: Real-time diagnostics
        self.tab_diag = QWidget()
        diag_layout = QVBoxLayout(self.tab_diag)
        diag_layout.setContentsMargins(0, 10, 0, 0)

        self.scroll_diag = QScrollArea()
        self.scroll_diag.setWidgetResizable(True)
        self.scroll_diag.setFrameShape(QFrame.NoFrame)
        self.scroll_diag.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_diag.setStyleSheet("background: transparent; border: none;")

        self.diag_content = QWidget()
        self.diag_content.setStyleSheet("background: transparent;")
        self.diag_content_layout = QVBoxLayout(self.diag_content)
        self.diag_content_layout.setContentsMargins(0, 0, 8, 0)
        self.diag_content_layout.setSpacing(10)

        self.scroll_diag.setWidget(self.diag_content)
        diag_layout.addWidget(self.scroll_diag)
        self.tabs.addTab(self.tab_diag, c.t("UI_DEPS_TAB_DIAG"))

        # Tab 2: Package and Requirements Guide by Distribution
        self.tab_guide = QWidget()
        guide_layout = QVBoxLayout(self.tab_guide)
        guide_layout.setContentsMargins(0, 10, 0, 0)

        self.scroll_guide = QScrollArea()
        self.scroll_guide.setWidgetResizable(True)
        self.scroll_guide.setFrameShape(QFrame.NoFrame)
        self.scroll_guide.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_guide.setStyleSheet("background: transparent; border: none;")

        self.guide_content = QWidget()
        self.guide_content.setStyleSheet("background: transparent;")
        self.guide_content_layout = QVBoxLayout(self.guide_content)
        self.guide_content_layout.setContentsMargins(0, 0, 8, 0)
        self.guide_content_layout.setSpacing(12)

        self._build_distro_guide(self.guide_content_layout)

        self.scroll_guide.setWidget(self.guide_content)
        guide_layout.addWidget(self.scroll_guide)
        self.tabs.addTab(self.tab_guide, c.t("UI_DEPS_TAB_GUIDE"))

        main_layout.addWidget(self.tabs, 1)

        # 4. Bottom Action Buttons
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(12)

        self.btn_rescan = QPushButton(c.t("UI_DEPS_BTN_RESCAN"))
        self.btn_rescan.setObjectName("SecondaryDialogBtn")
        self.btn_rescan.setCursor(Qt.PointingHandCursor)
        self.btn_rescan.clicked.connect(self._run_diagnostics)
        bottom_row.addWidget(self.btn_rescan)

        bottom_row.addStretch(1)

        self.btn_close = QPushButton(c.t("UI_DEPS_BTN_CLOSE"))
        self.btn_close.setObjectName("PrimaryDialogBtn")
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.clicked.connect(self.accept)
        bottom_row.addWidget(self.btn_close)

        main_layout.addLayout(bottom_row)

    def _run_diagnostics(self):
        """Executes real system diagnostics for required dynamic libraries and tools."""
        # Clear previous content
        while self.diag_content_layout.count():
            item = self.diag_content_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        # Verification categories and items
        groups = [
            {
                "category": c.t("UI_DEPS_CAT_GRAPHICS"),
                "items": [
                    {
                        "name": "OpenGL / GLX (libGL)",
                        "desc": c.t("UI_DEPS_ITEM_OPENGL_DESC"),
                        "candidates": ["GL", "libGL.so.1"],
                        "required": True,
                    },
                    {
                        "name": "EGL Display Interface (libEGL)",
                        "desc": c.t("UI_DEPS_ITEM_EGL_DESC"),
                        "candidates": ["EGL", "libEGL.so.1"],
                        "required": True,
                    },
                    {
                        "name": "Vulkan ICD Loader (libvulkan)",
                        "desc": c.t("UI_DEPS_ITEM_VULKAN_DESC"),
                        "candidates": ["vulkan", "libvulkan.so.1"],
                        "required": False,
                    },
                ]
            },
            {
                "category": c.t("UI_DEPS_CAT_AUDIO"),
                "items": [
                    {
                        "name": "ALSA Audio (libasound)",
                        "desc": c.t("UI_DEPS_ITEM_ALSA_DESC"),
                        "candidates": ["asound", "libasound.so.2"],
                        "required": True,
                    },
                    {
                        "name": "PulseAudio / PipeWire (libpulse)",
                        "desc": c.t("UI_DEPS_ITEM_PULSE_DESC"),
                        "candidates": ["pulse", "libpulse.so.0"],
                        "required": True,
                    },
                ]
            },
            {
                "category": c.t("UI_DEPS_CAT_SECURITY"),
                "items": [
                    {
                        "name": "OpenSSL Crypto (libcrypto)",
                        "desc": c.t("UI_DEPS_ITEM_CRYPTO_DESC"),
                        "candidates": ["crypto", "libcrypto.so.3", "libcrypto.so.1.1"],
                        "required": True,
                    },
                    {
                        "name": "OpenSSL SSL (libssl)",
                        "desc": c.t("UI_DEPS_ITEM_SSL_DESC"),
                        "candidates": ["ssl", "libssl.so.3", "libssl.so.1.1"],
                        "required": True,
                    },
                ]
            },
            {
                "category": c.t("UI_DEPS_CAT_COMPRESSION"),
                "items": [
                    {
                        "name": "Zlib (libz)",
                        "desc": c.t("UI_DEPS_ITEM_ZLIB_DESC"),
                        "candidates": ["z", "libz.so.1"],
                        "required": True,
                    },
                    {
                        "name": "PNG Image Library (libpng16)",
                        "desc": c.t("UI_DEPS_ITEM_PNG_DESC"),
                        "candidates": ["png16", "libpng16.so.16"],
                        "required": True,
                    },
                    {
                        "name": "evdev / udev",
                        "desc": c.t("UI_DEPS_ITEM_EVDEV_DESC"),
                        "candidates": ["evdev", "libevdev.so.2", "udev", "libudev.so.1"],
                        "required": False,
                    },
                ]
            },
            {
                "category": c.t("UI_DEPS_CAT_TOOLS"),
                "items": [
                    {
                        "name": "unzip (CLI)",
                        "desc": c.t("UI_DEPS_ITEM_UNZIP_DESC"),
                        "is_cli": True,
                        "cli_bin": "unzip",
                        "required": True,
                    },
                    {
                        "name": "Zenity (CLI)",
                        "desc": c.t("UI_DEPS_ITEM_ZENITY_DESC"),
                        "is_cli": True,
                        "cli_bin": "zenity",
                        "required": False,
                    },
                    {
                        "name": "GameMode (gamemoderun)",
                        "desc": c.t("UI_DEPS_ITEM_GAMEMODE_DESC"),
                        "is_cli": True,
                        "cli_bin": "gamemoderun",
                        "required": False,
                    },
                ]
            }
        ]

        total_critical = 0
        missing_critical = 0

        for grp in groups:
            group_box = QFrame()
            group_box.setObjectName("CategoryGroupCard")
            g_layout = QVBoxLayout(group_box)
            g_layout.setContentsMargins(14, 12, 14, 12)
            g_layout.setSpacing(8)

            lbl_cat = QLabel(grp["category"])
            lbl_cat.setObjectName("CategoryHeader")
            g_layout.addWidget(lbl_cat)

            for item in grp["items"]:
                row = QHBoxLayout()
                row.setSpacing(12)

                is_cli = item.get("is_cli", False)
                if is_cli:
                    ok = bool(shutil.which(item["cli_bin"]))
                    detail = c.t("UI_DEPS_TOOL_FOUND", path=item['cli_bin']) if ok else c.t("UI_DEPS_TOOL_NOT_FOUND")
                else:
                    ok, soname = check_dynamic_library(item["candidates"])
                    detail = c.t("UI_DEPS_FOUND", name=soname) if ok else c.t("UI_DEPS_NOT_FOUND")

                is_req = item.get("required", True)
                if is_req:
                    total_critical += 1
                    if not ok:
                        missing_critical += 1

                # Status icon
                icon_lbl = QLabel("✅" if ok else ("⚠️" if not is_req else "❌"))
                icon_lbl.setFixedWidth(24)
                icon_lbl.setAlignment(Qt.AlignCenter)
                row.addWidget(icon_lbl)

                text_vbox = QVBoxLayout()
                text_vbox.setSpacing(2)

                title_row = QHBoxLayout()
                lbl_name = QLabel(item["name"])
                lbl_name.setObjectName("ItemName")
                title_row.addWidget(lbl_name)

                if not is_req:
                    chip_opt = QLabel(c.t("UI_DEPS_OPTIONAL"))
                    chip_opt.setObjectName("OptionalChip")
                    title_row.addWidget(chip_opt)

                title_row.addStretch(1)
                text_vbox.addLayout(title_row)

                lbl_desc = QLabel(f"{item['desc']} &nbsp;<span style='color: {'#10b981' if ok else '#f59e0b'};'>({detail})</span>")
                lbl_desc.setObjectName("ItemDesc")
                lbl_desc.setWordWrap(True)
                text_vbox.addWidget(lbl_desc)

                row.addLayout(text_vbox, 1)

                g_layout.addLayout(row)

            self.diag_content_layout.addWidget(group_box)

        # Update summary card
        if missing_critical == 0:
            self.lbl_global_status.setText(f"● {c.t('UI_DEPS_STATUS_ALL_OK')}")
            self.lbl_global_status.setStyleSheet(f"""
                background-color: {hex_to_rgba('#10b981', 0.16)};
                color: #10b981;
                border: 1px solid {hex_to_rgba('#10b981', 0.40)};
                border-radius: 6px;
                padding: 3px 10px;
                font-weight: 700;
                font-size: 11.5px;
            """)
            self.lbl_summary_desc.setText(c.t("UI_DEPS_SUMMARY_ALL_OK"))
        else:
            self.lbl_global_status.setText(f"● {missing_critical} {c.t('UI_DEPS_STATUS_MISSING')}")
            self.lbl_global_status.setStyleSheet(f"""
                background-color: {hex_to_rgba('#f59e0b', 0.16)};
                color: #f59e0b;
                border: 1px solid {hex_to_rgba('#f59e0b', 0.40)};
                border-radius: 6px;
                padding: 3px 10px;
                font-weight: 700;
                font-size: 11.5px;
            """)
            self.lbl_summary_desc.setText(c.t("UI_DEPS_SUMMARY_MISSING"))

    def _build_distro_guide(self, parent_layout):
        """Builds helper cards with package installation instructions by distribution."""
        distros = [
            {
                "name": "Ubuntu / Debian / Linux Mint",
                "manager": "APT",
                "packages": "libgl1 libegl1 libvulkan1 mesa-vulkan-drivers libasound2 libpulse0 libssl3 libpng16-16 zlib1g libevdev2 libudev1 zenity unzip",
                "cmd": "sudo apt update && sudo apt install -y libgl1 libegl1 libvulkan1 libasound2 libpulse0 libssl3 libpng16-16 zlib1g libevdev2 libudev1 zenity unzip gamemode",
                "notes": c.t("UI_DEPS_DISTRO_UBUNTU_NOTES")
            },
            {
                "name": "Arch Linux / Manjaro / EndeavourOS",
                "manager": "Pacman",
                "packages": "mesa vulkan-icd-loader alsa-lib libpulse openssl libpng zlib libevdev zenity unzip",
                "cmd": "sudo pacman -S --needed mesa vulkan-icd-loader alsa-lib libpulse openssl libpng zlib libevdev zenity unzip gamemode",
                "notes": c.t("UI_DEPS_DISTRO_ARCH_NOTES")
            },
            {
                "name": "Fedora / RHEL / Nobara",
                "manager": "DNF",
                "packages": "mesa-libGL mesa-libEGL vulkan-loader alsa-lib pulseaudio-libs openssl-libs libpng zlib libevdev zenity unzip",
                "cmd": "sudo dnf install -y mesa-libGL mesa-libEGL vulkan-loader alsa-lib pulseaudio-libs openssl-libs libpng zlib libevdev zenity unzip gamemode",
                "notes": c.t("UI_DEPS_DISTRO_FEDORA_NOTES")
            },
            {
                "name": c.t("UI_DEPS_DISTRO_FLATPAK_TITLE"),
                "manager": "Flatpak Runtimes",
                "packages": "org.freedesktop.Platform // org.gnome.Platform",
                "cmd": "flatpak update",
                "notes": c.t("UI_DEPS_DISTRO_FLATPAK_NOTES")
            }
        ]

        for d in distros:
            card = QFrame()
            card.setObjectName("CategoryGroupCard")
            cl = QVBoxLayout(card)
            cl.setContentsMargins(16, 14, 16, 14)
            cl.setSpacing(8)

            t_row = QHBoxLayout()
            lbl_title = QLabel(d["name"])
            lbl_title.setObjectName("TierTitle")
            t_row.addWidget(lbl_title, 1)

            mgr_badge = QLabel(d["manager"])
            mgr_badge.setObjectName("OptionalChip")
            t_row.addWidget(mgr_badge)
            cl.addLayout(t_row)

            lbl_notes = QLabel(f"• {d['notes']}")
            lbl_notes.setObjectName("ItemDesc")
            lbl_notes.setWordWrap(True)
            cl.addWidget(lbl_notes)

            # Copy command container
            cmd_frame = QFrame()
            cmd_frame.setObjectName("CmdBox")
            cml = QHBoxLayout(cmd_frame)
            cml.setContentsMargins(10, 6, 10, 6)
            cml.setSpacing(10)

            lbl_cmd = QLabel(f"<code>{d['cmd']}</code>")
            lbl_cmd.setObjectName("CmdLabel")
            lbl_cmd.setWordWrap(True)
            lbl_cmd.setTextInteractionFlags(Qt.TextSelectableByMouse)
            cml.addWidget(lbl_cmd, 1)

            btn_copy = QPushButton(c.t("UI_DEPS_BTN_COPY"))
            btn_copy.setObjectName("CopyBtn")
            btn_copy.setCursor(Qt.PointingHandCursor)
            btn_copy.clicked.connect(lambda _, cmd=d['cmd']: self._copy_to_clipboard(cmd))
            cml.addWidget(btn_copy, 0)

            cl.addWidget(cmd_frame)
            parent_layout.addWidget(card)

    def _copy_to_clipboard(self, text):
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        messagebox.showinfo(self, c.t("UI_DEPS_COPIED_TITLE"), c.t("UI_DEPS_COPIED_MSG"))

    def _apply_theme(self):
        bg = "#121317" if self.is_dark else "#f8fafc"
        card_bg = "rgba(255, 255, 255, 0.045)" if self.is_dark else "rgba(0, 0, 0, 0.035)"
        border_color = "rgba(255, 255, 255, 0.08)" if self.is_dark else "rgba(0, 0, 0, 0.08)"
        text_primary = "#ffffff" if self.is_dark else "#0f172a"
        text_secondary = "#94a3b8" if self.is_dark else "#475569"
        accent = self.accent

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg};
            }}
            QLabel#DialogTitle {{
                font-size: 18px;
                font-weight: 800;
                color: {text_primary};
            }}
            QLabel#DialogSubtitle {{
                font-size: 12.5px;
                color: {text_secondary};
            }}
            QFrame#StatusSummaryCard {{
                background-color: {card_bg};
                border: 1px solid {border_color};
                border-radius: 12px;
            }}
            QLabel#EnvChip {{
                font-size: 12px;
                font-weight: 700;
                color: {accent};
            }}
            QLabel#SummaryDescLabel {{
                font-size: 12px;
                color: {text_secondary};
            }}
            QTabWidget#DepsTabWidget::pane {{
                border: 1px solid {border_color};
                border-radius: 10px;
                background-color: transparent;
            }}
            QTabBar::tab {{
                background-color: {"rgba(255, 255, 255, 0.04)" if self.is_dark else "rgba(0, 0, 0, 0.03)"};
                color: {text_secondary};
                padding: 7px 16px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 4px;
                font-weight: 600;
                font-size: 12.5px;
            }}
            QTabBar::tab:selected {{
                background-color: {hex_to_rgba(accent, 0.20)};
                color: {text_primary};
                border-bottom: 2px solid {accent};
            }}
            QFrame#CategoryGroupCard {{
                background-color: {card_bg};
                border: 1px solid {border_color};
                border-radius: 10px;
            }}
            QLabel#CategoryHeader {{
                font-size: 11px;
                font-weight: 800;
                letter-spacing: 0.6px;
                color: {accent};
            }}
            QLabel#ItemName {{
                font-size: 13px;
                font-weight: 700;
                color: {text_primary};
            }}
            QLabel#TierTitle {{
                font-size: 13.5px;
                font-weight: 700;
                color: {text_primary};
            }}
            QLabel#ItemDesc {{
                font-size: 11.5px;
                color: {text_secondary};
            }}
            QLabel#OptionalChip {{
                background-color: {"rgba(255, 255, 255, 0.07)" if self.is_dark else "rgba(0, 0, 0, 0.05)"};
                color: {text_secondary};
                border-radius: 4px;
                padding: 1px 6px;
                font-size: 10px;
                font-weight: 600;
            }}
            QFrame#CmdBox {{
                background-color: {"rgba(0, 0, 0, 0.40)" if self.is_dark else "#f1f5f9"};
                border: 1px solid {border_color};
                border-radius: 8px;
            }}
            QLabel#CmdLabel {{
                color: {"#38bdf8" if self.is_dark else "#0284c7"};
                font-family: monospace, "Fira Code", "Courier New";
                font-size: 11px;
                background: transparent;
                border: none;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 6px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {"rgba(255, 255, 255, 0.18)" if self.is_dark else "rgba(0, 0, 0, 0.18)"};
                min-height: 24px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {accent};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
            QPushButton#CopyBtn {{
                background-color: {hex_to_rgba(accent, 0.20)};
                color: {text_primary};
                border: 1px solid {hex_to_rgba(accent, 0.40)};
                border-radius: 4px;
                padding: 3px 10px;
                font-size: 11px;
                font-weight: 700;
            }}
            QPushButton#CopyBtn:hover {{
                background-color: {accent};
                color: #ffffff;
            }}
            QPushButton#PrimaryDialogBtn {{
                background-color: {accent};
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 8px 22px;
                font-size: 13px;
                font-weight: 700;
            }}
            QPushButton#PrimaryDialogBtn:hover {{
                background-color: {adjust_color(accent, 20)};
            }}
            QPushButton#SecondaryDialogBtn {{
                background-color: {"rgba(255, 255, 255, 0.07)" if self.is_dark else "rgba(0, 0, 0, 0.05)"};
                color: {text_primary};
                border: 1px solid {border_color};
                border-radius: 8px;
                padding: 8px 18px;
                font-size: 12.5px;
                font-weight: 600;
            }}
            QPushButton#SecondaryDialogBtn:hover {{
                background-color: {"rgba(255, 255, 255, 0.12)" if self.is_dark else "rgba(0, 0, 0, 0.09)"};
                border: 1px solid {hex_to_rgba(accent, 0.40)};
            }}
        """)
