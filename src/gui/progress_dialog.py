import customtkinter as ctk

class ProgressDialog(ctk.CTkToplevel):
    def __init__(self, parent, title, message):
        super().__init__(parent)
        self.title(title)
        self.geometry("400x150")
        self.resizable(False, False)
        self.attributes("-topmost", True)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        from src import constants as c
        self.label = ctk.CTkLabel(self, text=message, font=c.FONT_NORMAL)
        self.label.pack(pady=(20, 10))

        self.progressbar = ctk.CTkProgressBar(self, mode="indeterminate")
        self.progressbar.pack(pady=10, padx=20, fill="x")
        self.progressbar.start()

        # Centrar ventana
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")

    def close(self):
        self.destroy()
