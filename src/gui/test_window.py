from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTabWidget, QScrollArea, QFrame, QCheckBox,
                             QRadioButton, QProgressBar, QSlider, QComboBox, QButtonGroup, QLineEdit)
from PySide6.QtCore import Qt, QTimer
import threading
import time
from src import constants as c
from src.gui import custom_dialogs as messagebox
from src.gui.progress_dialog import ProgressDialog
from src.utils.image_manager import ImageManager
from src.core.update_checker import UpdateChecker

class TestWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__()
        self.setWindowTitle(f"{c.APP_NAME} - UI Test Mode (PySide6)")
        self.resize(1100, 900)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)

        self.tab_widget = QTabWidget()
        self.main_layout.addWidget(self.tab_widget)

        self.tab_widgets = QWidget()
        self.tab_dialogs = QWidget()
        self.tab_stress = QWidget()

        self.tab_widget.addTab(self.tab_widgets, "Standard Widgets")
        self.tab_widget.addTab(self.tab_dialogs, "Dialogs & Mockups")
        self.tab_widget.addTab(self.tab_stress, "Stress Test & Colors")

        self.setup_widgets_tab()
        self.setup_dialogs_tab()
        self.setup_stress_tab()

        self.setStyleSheet("background-color: #242424; color: white;")

    def create_section(self, layout, title):
        lbl = QLabel(title)
        lbl.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {c.COLOR_BLUE_BUTTON}; margin-top: 20px;")
        layout.addWidget(lbl)

    def setup_widgets_tab(self):
        layout = QVBoxLayout(self.tab_widgets)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        scroll_layout = QVBoxLayout(content)
        scroll_layout.setAlignment(Qt.AlignTop)
        scroll.setWidget(content)
        layout.addWidget(scroll)

        self.create_section(scroll_layout, "Standard Buttons")
        btn_frame = QHBoxLayout()
        for text, color in [("Normal Button", None), ("Success", c.COLOR_PRIMARY_GREEN),
                           ("Danger", c.COLOR_RED_BUTTON), ("Warning", c.COLOR_ORANGE_BUTTON)]:
            btn = QPushButton(text)
            if color: btn.setStyleSheet(f"background-color: {color}; color: white; border-radius: 6px;")
            btn_frame.addWidget(btn)
        scroll_layout.addLayout(btn_frame)

        self.create_section(scroll_layout, "Toggles & Selectors")
        toggle_layout = QHBoxLayout()
        toggle_layout.addWidget(QCheckBox("Checkbox"))
        toggle_layout.addWidget(QCheckBox("Switch (using CheckBox for now)"))
        scroll_layout.addLayout(toggle_layout)

        self.create_section(scroll_layout, "Inputs & Menus")
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLineEdit("Entry field"))
        cb = QComboBox()
        cb.addItems(["Choice 1", "Choice 2"])
        input_layout.addWidget(cb)
        scroll_layout.addLayout(input_layout)

        self.create_section(scroll_layout, "Sliders & Progress")
        s_layout = QHBoxLayout()
        slider = QSlider(Qt.Horizontal)
        s_layout.addWidget(slider)
        pb = QProgressBar()
        pb.setRange(0, 0)
        s_layout.addWidget(pb)
        scroll_layout.addLayout(s_layout)

    def setup_dialogs_tab(self):
        layout = QVBoxLayout(self.tab_dialogs)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        scroll_layout = QVBoxLayout(content)
        scroll_layout.setAlignment(Qt.AlignTop)
        scroll.setWidget(content)
        layout.addWidget(scroll)

        self.create_section(scroll_layout, "Custom Dialogs")
        diag_layout = QHBoxLayout()
        btn_info = QPushButton("Info")
        btn_info.clicked.connect(lambda: messagebox.showinfo(self, "Test", "This is an info dialog."))
        diag_layout.addWidget(btn_info)

        btn_err = QPushButton("Error")
        btn_err.clicked.connect(lambda: messagebox.showerror(self, "Test", "This is an error dialog."))
        diag_layout.addWidget(btn_err)
        scroll_layout.addLayout(diag_layout)

        self.create_section(scroll_layout, "Special Dialogs")
        btn_prog = QPushButton("Show Progress (5s)")
        btn_prog.clicked.connect(self.test_progress)
        scroll_layout.addWidget(btn_prog)

        btn_update = QPushButton("Check Update (test)")
        btn_update.clicked.connect(self.test_update_check)
        scroll_layout.addWidget(btn_update)

    def setup_stress_tab(self):
        layout = QVBoxLayout(self.tab_stress)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        scroll_layout = QVBoxLayout(content)
        scroll.setWidget(content)
        layout.addWidget(scroll)

        self.create_section(scroll_layout, "Color Palette")
        palette = QHBoxLayout()
        for name, color in [("BLUE", c.COLOR_BLUE_BUTTON), ("GREEN", c.COLOR_PRIMARY_GREEN)]:
            f = QFrame()
            f.setFixedSize(150, 50)
            f.setStyleSheet(f"background-color: {color}; border-radius: 8px;")
            l = QLabel(name, f)
            l.setAlignment(Qt.AlignCenter)
            palette.addWidget(f)
        scroll_layout.addLayout(palette)

    def test_progress(self):
        p = ProgressDialog(self, "Task", "Working...")
        p.show()
        def work():
            time.sleep(5)
            QTimer.singleShot(0, p.accept)
        threading.Thread(target=work).start()

    def test_update_check(self):
        """Test the remote update checker against the real URL."""
        local = c.VERSION_LAUNCHER
        checker = UpdateChecker(self)
        def on_result(available, remote_ver, error):
            if error:
                msg = f"Local version: {local}\n\n❌ {error}"
            elif available:
                msg = f"Local version: {local}\nRemote version: {remote_ver}\n\n✅ Update available!"
            else:
                msg = f"Local version: {local}\nRemote version: {remote_ver}\n\n✓ Already up to date."
            messagebox.showinfo(self, f"Update Check ({c.UPDATE_CHECK_URL})", msg)
        checker.check(on_result=on_result)
