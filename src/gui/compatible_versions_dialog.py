import platform
import re
import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QFrame, QWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QIcon

from src import constants as c
from src.gui.custom_dialogs import _find_theme
from src.utils.image_manager import ImageManager
from src.utils.colors import hex_to_rgba, blend_colors, adjust_color
from src.core.hardware import _detect_cpu_flags, _detect_gl_version, _compute_compatibility


class CompatibleVersionsDialog(QDialog):
    """
    Modern informational dialog analyzing system hardware and detailing
    compatible Minecraft Bedrock versions, requirements, and technical notes.
    """
    def __init__(self, parent=None):
        parent_widget = parent if isinstance(parent, QWidget) else getattr(parent, "root", None)
        if not isinstance(parent_widget, QWidget):
            parent_widget = None
        super().__init__(parent_widget)
        self.app = parent
        self.setWindowTitle(c.t("UI_COMPAT_TITLE"))
        self.resize(720, 680)
        self.setMinimumSize(600, 520)

        mode, self.accent = _find_theme(parent)
        self.is_dark = mode == "Dark"

        self._setup_ui()
        self._apply_theme()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(22, 22, 22, 20)
        main_layout.setSpacing(16)

        # 1. Header with Icon and Titles
        header_layout = QHBoxLayout()
        header_layout.setSpacing(16)

        self.icon_label = QLabel()
        self.icon_label.setFixedSize(48, 48)
        self.icon_label.setAlignment(Qt.AlignCenter)
        pix = ImageManager.get_image("tools_versions.png", size=(48, 48))
        if pix and not pix.isNull():
            self.icon_label.setPixmap(pix)
        else:
            self.icon_label.setText("🛡️")
            self.icon_label.setStyleSheet("font-size: 28px;")
        header_layout.addWidget(self.icon_label)

        title_box = QVBoxLayout()
        title_box.setSpacing(3)
        self.lbl_title = QLabel(c.t("UI_COMPAT_TITLE"))
        self.lbl_title.setObjectName("DialogTitle")
        self.lbl_subtitle = QLabel(c.t("UI_COMPAT_SUBTITLE"))
        self.lbl_subtitle.setObjectName("DialogSubtitle")
        self.lbl_subtitle.setWordWrap(True)
        title_box.addWidget(self.lbl_title)
        title_box.addWidget(self.lbl_subtitle)
        header_layout.addLayout(title_box, 1)

        main_layout.addLayout(header_layout)

        # 2. System Hardware Diagnostics Card
        self.sys_card = QFrame()
        self.sys_card.setObjectName("SystemDiagCard")
        sys_l = QVBoxLayout(self.sys_card)
        sys_l.setContentsMargins(16, 14, 16, 14)
        sys_l.setSpacing(8)

        sys_header_row = QHBoxLayout()
        lbl_sys_title = QLabel(c.t("UI_COMPAT_HW_DIAG"))
        lbl_sys_title.setObjectName("DiagSectionHeader")
        sys_header_row.addWidget(lbl_sys_title)
        sys_header_row.addStretch(1)

        # Calculate compatible range
        arch, cpu_flags = _detect_cpu_flags()
        gl_ver = _detect_gl_version(self.app)
        compat_range = _compute_compatibility(arch, cpu_flags, gl_ver)

        self.chip_compat = QLabel(c.t("UI_COMPAT_RANGE_LABEL", range=compat_range))
        self.chip_compat.setObjectName("CompatStatusChip")
        sys_header_row.addWidget(self.chip_compat)
        sys_l.addLayout(sys_header_row)

        # CPU and GPU details
        arch_full = platform.machine()
        if arch == "x86_64":
            has_sse = all(f in cpu_flags for f in ["ssse3", "sse4_1", "sse4_2", "popcnt"])
            ext_text = c.t("UI_COMPAT_EXT_SSE_OK") if has_sse else c.t("UI_COMPAT_EXT_SSE_FAIL")
        elif arch in ("aarch64", "armv7l"):
            has_neon = "neon" in cpu_flags
            ext_text = c.t("UI_COMPAT_EXT_NEON_OK") if has_neon else c.t("UI_COMPAT_EXT_NEON_FAIL")
        else:
            ext_text = c.t("UI_COMPAT_EXT_LEGACY")

        clean_gl = re.sub(r"^OpenGL ES profile version string:\s*", "", str(gl_ver), flags=re.IGNORECASE).strip()
        details_text = (
            f"<b>{c.t('UI_COMPAT_CPU_ARCH')}</b> {arch_full} ({ext_text}) &nbsp;|&nbsp; "
            f"<b>{c.t('UI_COMPAT_GL_PROFILE')}</b> {clean_gl}"
        )
        lbl_details = QLabel(details_text)
        lbl_details.setObjectName("DiagDetailsLabel")
        lbl_details.setWordWrap(True)
        sys_l.addWidget(lbl_details)

        main_layout.addWidget(self.sys_card)

        # 3. Scrollable Area with Version Guides
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent; border: none;")

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        scroll_l = QVBoxLayout(scroll_content)
        scroll_l.setContentsMargins(0, 4, 8, 4)
        scroll_l.setSpacing(12)

        # Definition of Minecraft Bedrock version tiers
        version_tiers = [
            {
                "tier": c.t("UI_COMPAT_TIER1_TITLE"),
                "status": c.t("UI_COMPAT_TIER1_STATUS"),
                "status_color": "#10b981",  # Emerald
                "motor": "RenderDragon (OpenGL ES 3.0+ / Vulkan)",
                "arch": "64 bits (x86_64 / arm64-v8a)",
                "desc": c.t("UI_COMPAT_TIER1_DESC"),
            },
            {
                "tier": c.t("UI_COMPAT_TIER2_TITLE"),
                "status": c.t("UI_COMPAT_TIER2_STATUS"),
                "status_color": "#06b6d4",  # Cyan
                "motor": "RenderDragon v1",
                "arch": "64 bits",
                "desc": c.t("UI_COMPAT_TIER2_DESC"),
            },
            {
                "tier": c.t("UI_COMPAT_TIER3_TITLE"),
                "status": c.t("UI_COMPAT_TIER3_STATUS"),
                "status_color": "#3b82f6",  # Blue
                "motor": "OpenGL / RenderDragon",
                "arch": "32 bits & 64 bits",
                "desc": c.t("UI_COMPAT_TIER3_DESC"),
            },
            {
                "tier": c.t("UI_COMPAT_TIER4_TITLE"),
                "status": c.t("UI_COMPAT_TIER4_STATUS"),
                "status_color": "#8b5cf6",  # Purple
                "motor": "OpenGL ES 2.0+",
                "arch": "32 bits & 64 bits",
                "desc": c.t("UI_COMPAT_TIER4_DESC"),
            },
        ]

        for v in version_tiers:
            card = QFrame()
            card.setObjectName("VersionTierCard")
            cl = QVBoxLayout(card)
            cl.setContentsMargins(16, 14, 16, 14)
            cl.setSpacing(6)

            top_row = QHBoxLayout()
            lbl_tier_title = QLabel(v["tier"])
            lbl_tier_title.setObjectName("TierTitle")
            top_row.addWidget(lbl_tier_title, 1)

            badge = QLabel(v["status"])
            badge.setStyleSheet(f"""
                background-color: {hex_to_rgba(v['status_color'], 0.18)};
                color: {v['status_color']};
                border: 1px solid {hex_to_rgba(v['status_color'], 0.40)};
                border-radius: 6px;
                padding: 3px 10px;
                font-size: 11px;
                font-weight: 700;
            """)
            top_row.addWidget(badge, 0)
            cl.addLayout(top_row)

            # Metadata tags
            meta_lbl = QLabel(f"⚙ <b>{c.t('UI_COMPAT_MOTOR_LABEL')}:</b> {v['motor']} &nbsp;•&nbsp; 📦 <b>{c.t('UI_COMPAT_ARCH_LABEL')}:</b> {v['arch']}")
            meta_lbl.setObjectName("TierMeta")
            cl.addWidget(meta_lbl)

            desc_lbl = QLabel(v["desc"])
            desc_lbl.setObjectName("TierDesc")
            desc_lbl.setWordWrap(True)
            cl.addWidget(desc_lbl)

            scroll_l.addWidget(card)

        # Informational card regarding License and Version Acquisition
        info_card = QFrame()
        info_card.setObjectName("LicenseInfoCard")
        il = QVBoxLayout(info_card)
        il.setContentsMargins(16, 14, 16, 14)
        il.setSpacing(6)

        lbl_info_header = QLabel(f"ℹ {c.t('UI_COMPAT_LICENSE_TITLE').upper()}")
        lbl_info_header.setObjectName("DiagSectionHeader")
        il.addWidget(lbl_info_header)

        lbl_info_text = QLabel(c.t("UI_COMPAT_LICENSE_DESC"))
        lbl_info_text.setObjectName("TierDesc")
        lbl_info_text.setWordWrap(True)
        il.addWidget(lbl_info_text)

        scroll_l.addWidget(info_card)

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll, 1)

        # 4. Bottom Action Buttons
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(12)

        self.btn_hw_analysis = QPushButton(c.t("UI_COMPAT_BTN_ANALYZE_HW"))
        self.btn_hw_analysis.setObjectName("SecondaryDialogBtn")
        self.btn_hw_analysis.setCursor(Qt.PointingHandCursor)
        self.btn_hw_analysis.clicked.connect(self._on_hw_analysis_clicked)
        bottom_row.addWidget(self.btn_hw_analysis)

        bottom_row.addStretch(1)

        self.btn_close = QPushButton(c.t("UI_COMPAT_BTN_UNDERSTOOD"))
        self.btn_close.setObjectName("PrimaryDialogBtn")
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.clicked.connect(self.accept)
        bottom_row.addWidget(self.btn_close)

        main_layout.addLayout(bottom_row)

    def _on_hw_analysis_clicked(self):
        self.accept()
        if self.app and hasattr(self.app, "logic") and hasattr(self.app.logic, "check_requirements_dialog"):
            self.app.logic.check_requirements_dialog(self.app)

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
            QFrame#SystemDiagCard {{
                background-color: {card_bg};
                border: 1px solid {border_color};
                border-radius: 12px;
            }}
            QLabel#DiagSectionHeader {{
                font-size: 11px;
                font-weight: 800;
                letter-spacing: 0.6px;
                color: {accent};
            }}
            QLabel#CompatStatusChip {{
                background-color: {hex_to_rgba('#10b981', 0.16)};
                color: #10b981;
                border: 1px solid {hex_to_rgba('#10b981', 0.35)};
                border-radius: 6px;
                padding: 2px 10px;
                font-size: 11.5px;
                font-weight: 700;
            }}
            QLabel#DiagDetailsLabel {{
                font-size: 12px;
                color: {text_secondary};
            }}
            QFrame#VersionTierCard {{
                background-color: {card_bg};
                border: 1px solid {border_color};
                border-radius: 10px;
            }}
            QFrame#VersionTierCard:hover {{
                border: 1px solid {hex_to_rgba(accent, 0.40)};
                background-color: {"rgba(255, 255, 255, 0.065)" if self.is_dark else "rgba(0, 0, 0, 0.05)"};
            }}
            QFrame#LicenseInfoCard {{
                background-color: {"rgba(255, 255, 255, 0.03)" if self.is_dark else "rgba(0, 0, 0, 0.025)"};
                border: 1px dashed {border_color};
                border-radius: 10px;
            }}
            QLabel#TierTitle {{
                font-size: 14px;
                font-weight: 700;
                color: {text_primary};
            }}
            QLabel#TierMeta {{
                font-size: 11.5px;
                color: {text_secondary};
            }}
            QLabel#TierDesc {{
                font-size: 12px;
                line-height: 1.4;
                color: {'#cbd5e1' if self.is_dark else '#334155'};
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
