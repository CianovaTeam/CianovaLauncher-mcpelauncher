from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QTextEdit
from PySide6.QtCore import Qt
from src import constants as c

class CustomDialog(QDialog):
    """A themed dialog with icon, message, and customizable action buttons."""

    def __init__(self, parent, title, message, icon_type="info", options=["OK"]):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.result_value = None

        # Base size and layout
        self.setMinimumWidth(450)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(15, 15, 15, 15)
        self.layout.setSpacing(10)

        # Main frame to mimic CTk appearance
        self.main_frame = QFrame()
        self.main_frame.setObjectName("MainFrame")
        self.main_layout = QVBoxLayout(self.main_frame)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.layout.addWidget(self.main_frame)

        # Content layout (Icon + Text)
        self.content_layout = QHBoxLayout()
        self.content_layout.setSpacing(25)
        self.content_layout.setAlignment(Qt.AlignCenter)
        self.main_layout.addLayout(self.content_layout)

        # Icon mapping
        icon_map = {
            "info": ("#3498db", "ℹ️"),
            "warning": ("#f1c40f", "⚠️"),
            "error": ("#e74c3c", "❌"),
            "question": ("#2ecc71", "❓")
        }
        color, icon_char = icon_map.get(icon_type, icon_map["info"])

        # Icon Label — sin fondo, solo el emoji limpio
        self.icon_label = QLabel(icon_char)
        self.icon_label.setFixedSize(50, 50)
        self.icon_label.setStyleSheet("font-size: 36px;")
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.content_layout.addWidget(self.icon_label)

        # Message Container (to allow better centering)
        msg_container = QFrame()
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
            self.msg_widget.setStyleSheet("background: transparent; font-size: 13px; color: white;")
            self.msg_widget.setMinimumHeight(150)
        else:
            self.msg_widget = QLabel(message)
            self.msg_widget.setWordWrap(True)
            self.msg_widget.setStyleSheet("font-size: 14px; color: white; background: transparent;")
            self.msg_widget.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

        msg_layout.addWidget(self.msg_widget)
        self.content_layout.addWidget(msg_container, 1)

        # Buttons Frame
        self.btn_layout = QHBoxLayout()
        self.btn_layout.setSpacing(10)
        self.btn_layout.setAlignment(Qt.AlignCenter)
        self.main_layout.addLayout(self.btn_layout)

        for i, opt in enumerate(options):
            btn = QPushButton(opt)
            btn.setMinimumHeight(38)
            btn.setMinimumWidth(115)

            # Apply styles based on option text
            opt_low = opt.lower()
            is_positive = any(word in opt_low for word in ["sí", "yes", "ok", "confirm", "instalar", "play", "jugar"])
            is_negative = any(word in opt_low for word in ["no", "cancel", "borrar", "delete", "eliminar"])

            bg_color = c.COLOR_BLUE_BUTTON
            if is_positive:
                bg_color = c.COLOR_PRIMARY_GREEN
            elif is_negative:
                bg_color = c.COLOR_RED_BUTTON

            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {bg_color};
                    color: white;
                    border: none;
                    border-radius: 8px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {bg_color}bb;
                }}
            """)

            btn.clicked.connect(lambda checked=False, val=opt: self.close_with_result(val))
            self.btn_layout.addWidget(btn)

        # Styling the dialog itself (Dark mode by default)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: #242424;
            }}
            #MainFrame {{
                background-color: #242424;
            }}
            QLabel, QTextEdit {{
                color: white;
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
