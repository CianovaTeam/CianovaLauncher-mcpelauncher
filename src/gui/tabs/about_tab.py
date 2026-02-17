import customtkinter as ctk

from src import constants as c


class AboutTab(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app

        self.pack(fill="both", expand=True)

        self.grid_columnconfigure(0, weight=1)

        # Licencia y Términos
        frame_legal = ctk.CTkScrollableFrame(
            self, label_text=c.UI_TITLE_LEGAL, corner_radius=12
        )
        frame_legal.pack(fill="both", expand=True, padx=20, pady=10)

        lbl_legal = ctk.CTkLabel(
            frame_legal,
            text=c.LEGAL_TEXT,
            justify="left",
            wraplength=500,
            font=ctk.CTkFont(size=11),
        )
        lbl_legal.pack(padx=10, pady=10, anchor="w")

        # Créditos
        ctk.CTkLabel(self, text=c.CREDITOS, font=ctk.CTkFont(size=12)).pack(
            pady=10
        )
        ctk.CTkLabel(
            self, text=f"{c.UI_VERSION_TEXT}{c.VERSION_LAUNCHER}", text_color="gray"
        ).pack()
