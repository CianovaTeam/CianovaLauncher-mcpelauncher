import os
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QTextEdit
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from src import constants as c
from src.utils.colors import blend_colors, hex_to_rgba
from src.utils.resource_path import resource_path

_CHICKEN_PIXMAP_CACHE = None

def get_chicken_icon_pixmap(target_height=60):
    """Load, crop out transparent borders, and cache the Minecraft chicken asset."""
    global _CHICKEN_PIXMAP_CACHE
    if _CHICKEN_PIXMAP_CACHE is not None and not _CHICKEN_PIXMAP_CACHE.isNull():
        return _CHICKEN_PIXMAP_CACHE

    path = resource_path("chicken_forward.png")
    if not os.path.exists(path):
        path = resource_path("assets/media/chicken_forward.png")

    if os.path.exists(path):
        orig = QPixmap(path)
        if not orig.isNull():
            # Non-transparent bounding box for chicken: (237, 37, 325, 377)
            cropped = orig.copy(237, 37, 325, 377)
            scaled = cropped.scaledToHeight(target_height, Qt.SmoothTransformation)
            _CHICKEN_PIXMAP_CACHE = scaled
            return scaled
    return None


def _find_theme(parent):
    """Walk up the parent chain looking for a config to read appearance/theme."""
    obj = parent
    while obj is not None:
        cfg = getattr(obj, "config", None)
        if cfg is None:
            cfg = getattr(obj, "config_manager", None)
        if cfg is not None:
            mode = cfg.get(c.CONFIG_KEY_APPEARANCE, "Dark")
            theme_color = cfg.get(c.CONFIG_KEY_COLOR_THEME, "blue")
            return mode, c.THEME_COLOR_MAP.get(theme_color, "#1f6aa5")
        parent_func = getattr(obj, "parent", None)
        obj = parent_func() if callable(parent_func) else None
    return "Dark", c.THEME_COLOR_MAP.get("blue", "#1f6aa5")


class CustomDialog(QDialog):
    """A themed dialog with icon, message, and customizable action buttons."""

    def __init__(self, parent, title, message, icon_type="info", options=["OK"]):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.result_value = None

        mode, self.accent = _find_theme(parent)
        light = mode != "Dark"
        if not light:
            self.dialog_bg = blend_colors("#0e0e0e", self.accent, 0.035)
            self.card_bg = blend_colors("#171717", self.accent, 0.065)
            self.text_color = "#dedede"
            self.muted_color = "#9e9e9e"
            self.border_color = hex_to_rgba(blend_colors("#303030", self.accent, 0.12), 0.6)
        else:
            self.dialog_bg = blend_colors("#f5f6f8", self.accent, 0.02)
            self.card_bg = blend_colors("#ffffff", self.accent, 0.04)
            self.text_color = "#212121"
            self.muted_color = "#5f6368"
            self.border_color = "rgba(0, 0, 0, 0.12)"

        # Base size and layout
        self.setMinimumWidth(460)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(16, 16, 16, 16)
        self.layout.setSpacing(12)

        # Main frame to mimic clean modern card appearance
        self.main_frame = QFrame()
        self.main_frame.setObjectName("MainFrame")
        self.main_layout = QVBoxLayout(self.main_frame)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(16)
        self.layout.addWidget(self.main_frame)

        # Content layout (Icon + Text)
        self.content_layout = QHBoxLayout()
        self.content_layout.setSpacing(20)
        self.content_layout.setAlignment(Qt.AlignCenter)
        self.main_layout.addLayout(self.content_layout)

        # Check if chicken icon asset should be used (info, warning, question, confirm)
        use_chicken = icon_type in ("info", "warning", "question", "ask", "confirm", "chicken")
        chicken_pix = get_chicken_icon_pixmap(60) if use_chicken else None

        self.icon_label = QLabel()
        self.icon_label.setStyleSheet("background: transparent; border: none;")
        self.icon_label.setAlignment(Qt.AlignCenter)

        if chicken_pix and not chicken_pix.isNull():
            self.icon_label.setPixmap(chicken_pix)
            self.icon_label.setFixedSize(chicken_pix.size())
        else:
            icon_map = {
                "info": ("#3498db", "ℹ️"),
                "warning": ("#f1c40f", "⚠️"),
                "error": ("#e74c3c", "❌"),
                "question": ("#2ecc71", "❓")
            }
            color, icon_char = icon_map.get(icon_type, icon_map["info"])
            self.icon_label.setText(icon_char)
            self.icon_label.setFixedSize(48, 48)
            self.icon_label.setStyleSheet("font-size: 34px; background: transparent; border: none;")

        self.content_layout.addWidget(self.icon_label)

        # Message Container (to allow better centering)
        msg_container = QFrame()
        msg_container.setStyleSheet("background: transparent; border: none;")
        msg_layout = QVBoxLayout(msg_container)
        msg_layout.setContentsMargins(0, 0, 0, 0)
        msg_layout.setAlignment(Qt.AlignVCenter)

        # Message (Label or TextEdit if long)
        is_long = len(message) > 250 or message.count('\n') > 4
        if is_long:
            self.msg_widget = QTextEdit()
            self.msg_widget.setPlainText(message)
            self.msg_widget.setReadOnly(True)
            self.msg_widget.setFrameStyle(QFrame.NoFrame)
            self.msg_widget.setStyleSheet(f"background: transparent; font-size: 13px; color: {self.text_color}; border: none;")
            self.msg_widget.setMinimumHeight(150)
        else:
            self.msg_widget = QLabel(message)
            self.msg_widget.setWordWrap(True)
            self.msg_widget.setStyleSheet(f"font-size: 13px; color: {self.text_color}; background: transparent; border: none;")
            self.msg_widget.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

        msg_layout.addWidget(self.msg_widget)
        self.content_layout.addWidget(msg_container, 1)

        # Buttons Frame
        self.btn_layout = QHBoxLayout()
        self.btn_layout.setSpacing(12)
        self.btn_layout.setAlignment(Qt.AlignCenter)
        self.main_layout.addLayout(self.btn_layout)

        for i, opt in enumerate(options):
            btn = QPushButton(opt)
            btn.setMinimumHeight(38)
            btn.setMinimumWidth(110)

            # Apply styles based on option text
            opt_low = opt.lower()
            is_positive = any(word in opt_low for word in ["sí", "yes", "ok", "confirm", "instalar", "play", "jugar"])
            is_negative = any(word in opt_low for word in ["no", "cancel", "borrar", "delete", "eliminar"])

            bg_color = self.accent
            if is_positive:
                bg_color = c.COLOR_PRIMARY_GREEN
            elif is_negative:
                bg_color = c.COLOR_RED_BUTTON

            r = int(bg_color[1:3], 16)
            g = int(bg_color[3:5], 16)
            b = int(bg_color[5:7], 16)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {bg_color};
                    color: white;
                    border: none;
                    border-radius: 6px;
                    font-weight: bold;
                    font-size: 13px;
                    padding: 8px 16px;
                }}
                QPushButton:hover {{
                    background-color: rgba({r}, {g}, {b}, 0.82);
                }}
            """)

            btn.clicked.connect(lambda checked=False, val=opt: self.close_with_result(val))
            self.btn_layout.addWidget(btn)

        # Styling the dialog itself (theme-aware)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {self.dialog_bg};
            }}
            #MainFrame {{
                background-color: {self.card_bg};
                border-radius: 10px;
                border: 1px solid {self.border_color};
            }}
            QLabel, QTextEdit {{
                color: {self.text_color};
                background-color: transparent;
            }}
        """)

    def close_with_result(self, value):
        """Close the dialog and store the selected button value as the result."""
        self.result_value = value
        self.accept()

# Helper functions to mimic messagebox
def showinfo(parent, title, message):
    """Display an informational message dialog."""
    dialog = CustomDialog(parent, title, message, icon_type="info", options=["OK"])
    dialog.exec()

def showwarning(parent, title, message):
    """Display a warning message dialog."""
    dialog = CustomDialog(parent, title, message, icon_type="warning", options=["OK"])
    dialog.exec()

def showerror(parent, title, message):
    """Display an error message dialog."""
    dialog = CustomDialog(parent, title, message, icon_type="error", options=["OK"])
    dialog.exec()

def askyesno(parent, title, message):
    """Display a yes/no question dialog and return the user's choice."""
    options = [c.t("UI_YES"), c.t("UI_NO")]
    dialog = CustomDialog(parent, title, message, icon_type="question", options=options)
    result = dialog.exec()
    return dialog.result_value == options[0]

def askokcancel(parent, title, message):
    """Display an OK/Cancel question dialog and return the user's choice."""
    options = ["OK", c.t("UI_CANCEL")]
    dialog = CustomDialog(parent, title, message, icon_type="question", options=options)
    result = dialog.exec()
    return dialog.result_value == options[0]
