import customtkinter as ctk
import time
import threading
from src import constants as c
from src.gui import custom_dialogs as messagebox
from src.gui.progress_dialog import ProgressDialog
from src.utils.image_manager import ImageManager

class TestWindow(ctk.CTk):
    def __init__(self, parent=None):
        super().__init__()
        self.title(f"{c.APP_NAME} - UI Test Mode")
        self.geometry("1100x950")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.tabview = ctk.CTkTabview(self, corner_radius=c.CORNER_RADIUS)
        self.tabview.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)

        self.tab_widgets = self.tabview.add("Standard Widgets")
        self.tab_dialogs = self.tabview.add("Dialogs & Mockups")
        self.tab_stress = self.tabview.add("Stress Test & Colors")

        self.setup_widgets_tab()
        self.setup_dialogs_tab()
        self.setup_stress_tab()

    def create_section(self, parent, title):
        ctk.CTkLabel(parent, text=title, font=c.FONT_SUBTITLE, text_color=c.COLOR_BLUE_BUTTON).pack(anchor="w", pady=(20, 10), padx=10)

    def setup_widgets_tab(self):
        scroll = ctk.CTkScrollableFrame(self.tab_widgets, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        self.create_section(scroll, "Standard Buttons")
        btn_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10)
        ctk.CTkButton(btn_frame, text="Normal Button").pack(side="left", padx=5, pady=5)
        ctk.CTkButton(btn_frame, text="Success (Green)", fg_color=c.COLOR_PRIMARY_GREEN).pack(side="left", padx=5, pady=5)
        ctk.CTkButton(btn_frame, text="Danger (Red)", fg_color=c.COLOR_RED_BUTTON).pack(side="left", padx=5, pady=5)
        ctk.CTkButton(btn_frame, text="Warning (Orange)", fg_color=c.COLOR_ORANGE_BUTTON).pack(side="left", padx=5, pady=5)

        self.create_section(scroll, "Toggles & Selectors")
        toggle_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        toggle_frame.pack(fill="x", padx=10)
        ctk.CTkCheckBox(toggle_frame, text="Checkbox", font=c.FONT_NORMAL).pack(side="left", padx=20)
        ctk.CTkSwitch(toggle_frame, text="Switch", font=c.FONT_NORMAL).pack(side="left", padx=20)

        radio_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        radio_frame.pack(fill="x", padx=10, pady=10)
        r_var = ctk.StringVar(value="1")
        ctk.CTkRadioButton(radio_frame, text="Option 1", variable=r_var, value="1", font=c.FONT_NORMAL).pack(side="left", padx=10)
        ctk.CTkRadioButton(radio_frame, text="Option 2", variable=r_var, value="2", font=c.FONT_NORMAL).pack(side="left", padx=10)

        seg_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        seg_frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkSegmentedButton(seg_frame, values=["Value A", "Value B", "Value C"]).pack(side="left", padx=10)

        self.create_section(scroll, "Inputs & Menus")
        input_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        input_frame.pack(fill="x", padx=10)
        ctk.CTkEntry(input_frame, placeholder_text="Entry field", width=200).pack(side="left", padx=5)
        ctk.CTkComboBox(input_frame, values=["Choice 1", "Choice 2", "Choice 3"]).pack(side="left", padx=5)
        ctk.CTkOptionMenu(input_frame, values=["Option X", "Option Y"]).pack(side="left", padx=5)

        self.create_section(scroll, "Sliders & Progress")
        s_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        s_frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkSlider(s_frame).pack(fill="x", expand=True, side="left", padx=5)
        ctk.CTkProgressBar(s_frame, mode="indeterminate").pack(fill="x", expand=True, side="left", padx=5)

    def setup_dialogs_tab(self):
        scroll = ctk.CTkScrollableFrame(self.tab_dialogs, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        self.create_section(scroll, "Custom Dialogs (Perfect Centering)")
        diag_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        diag_frame.pack(fill="x", padx=10)
        ctk.CTkButton(diag_frame, text="Info Dialog", command=self.test_info).pack(side="left", padx=5, pady=5)
        ctk.CTkButton(diag_frame, text="Warning Dialog", command=self.test_warning).pack(side="left", padx=5, pady=5)
        ctk.CTkButton(diag_frame, text="Error Dialog", command=self.test_error).pack(side="left", padx=5, pady=5)
        ctk.CTkButton(diag_frame, text="Confirmation (Yes/No)", command=self.test_ask).pack(side="left", padx=5, pady=5)
        ctk.CTkButton(diag_frame, text="Long Text Info", command=self.test_long_info).pack(side="left", padx=5, pady=5)

        self.create_section(scroll, "Special Dialogs")
        special_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        special_frame.pack(fill="x", padx=10)
        ctk.CTkButton(special_frame, text="Show Progress Dialog (5s)", command=self.test_progress).pack(side="left", padx=5, pady=5)

        self.create_section(scroll, "Launcher Mockups")

        # Profile Selector
        prof_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        prof_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(prof_frame, text="👤 Perfil:", font=c.FONT_NORMAL).pack(side="left", padx=5)
        ctk.CTkOptionMenu(prof_frame, values=["default", "test-profile-1", "survival"]).pack(side="left", padx=5)
        ctk.CTkButton(prof_frame, text="+", width=30).pack(side="left", padx=5)

        # Version Card
        v_card = ctk.CTkFrame(scroll, corner_radius=c.CORNER_RADIUS, fg_color=("gray85", "gray25"))
        v_card.pack(fill="x", pady=5, padx=10)
        img = ImageManager.get_image("icon.png", size=(32, 32))
        ctk.CTkLabel(v_card, text="", image=img).pack(side="left", padx=10, pady=10)
        ctk.CTkLabel(v_card, text="Minecraft v1.21.0 (Mock)", font=c.FONT_BOLD).pack(side="left", padx=10)
        ctk.CTkButton(v_card, text="Play", width=60, height=25).pack(side="right", padx=10)

        # Addon Card
        a_card = ctk.CTkFrame(scroll, corner_radius=12)
        a_card.pack(fill="x", pady=5, padx=10)
        ctk.CTkLabel(a_card, text="", image=ImageManager.get_image("icon.png", size=(64, 64))).pack(side="left", padx=15, pady=15)
        a_info = ctk.CTkFrame(a_card, fg_color="transparent")
        a_info.pack(side="left", fill="both", expand=True, padx=5, pady=15)
        ctk.CTkLabel(a_info, text="Faithful 32x", font=c.FONT_BOLD, anchor="w").pack(fill="x")
        ctk.CTkLabel(a_info, text="[Resources] - Active", font=c.FONT_SMALL, text_color="gray", anchor="w").pack(fill="x")
        ctk.CTkLabel(a_info, text="High definition resource pack for Minecraft PE.", font=c.FONT_NORMAL, text_color="gray", anchor="w").pack(fill="x")
        a_btns = ctk.CTkFrame(a_card, fg_color="transparent")
        a_btns.pack(side="right", padx=15)
        ctk.CTkButton(a_btns, text="Enabled", fg_color=c.COLOR_PRIMARY_GREEN, width=100).pack(side="left", padx=2)
        ctk.CTkButton(a_btns, text="🗑️", fg_color=c.COLOR_RED_BUTTON, width=35).pack(side="left", padx=2)

    def setup_stress_tab(self):
        scroll = ctk.CTkScrollableFrame(self.tab_stress, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        self.create_section(scroll, "Color Theme Palette")
        palette = ctk.CTkFrame(scroll, fg_color="transparent")
        palette.pack(fill="x", padx=10)
        colors = [
            ("COLOR_BLUE_BUTTON", c.COLOR_BLUE_BUTTON),
            ("COLOR_PRIMARY_GREEN", c.COLOR_PRIMARY_GREEN),
            ("COLOR_RED_BUTTON", c.COLOR_RED_BUTTON),
            ("COLOR_ORANGE_BUTTON", c.COLOR_ORANGE_BUTTON),
        ]
        for name, color in colors:
            f = ctk.CTkFrame(palette, fg_color=color, width=150, height=50)
            f.pack(side="left", padx=5)
            ctk.CTkLabel(f, text=name, text_color="white", font=c.FONT_SMALL).place(relx=0.5, rely=0.5, anchor="center")

        self.create_section(scroll, "Dynamic Layout Stress (50 items)")
        stress_frame = ctk.CTkFrame(scroll, fg_color=("gray95", "gray15"))
        stress_frame.pack(fill="both", expand=True, padx=10, pady=10)
        for i in range(50):
            l = ctk.CTkLabel(stress_frame, text=f"Dynamic Item #{i+1}", font=c.FONT_NORMAL)
            l.pack(pady=2)

    def test_info(self):
        messagebox.showinfo(self, "Test Info", "This is a custom themed information dialog with perfect horizontal and vertical centering.")

    def test_warning(self):
        messagebox.showwarning(self, "Test Warning", "This is a custom themed warning dialog.")

    def test_error(self):
        messagebox.showerror(self, "Test Error", "This is a custom themed error dialog.")

    def test_ask(self):
        res = messagebox.askyesno(self, "Test Confirmation", "¿Deseas confirmar esta acción de prueba?")
        print(f"User selected: {res}")

    def test_long_info(self):
        long_text = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. " * 3
        messagebox.showinfo(self, "Long Text Test", long_text)

    def test_progress(self):
        p = ProgressDialog(self, "Task in progress", "Simulating a long task...")
        def work():
            time.sleep(5)
            self.after(0, p.close)
        threading.Thread(target=work).start()
