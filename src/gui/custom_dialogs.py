import customtkinter as ctk
from src import constants as c
from src.utils.image_manager import ImageManager

class CustomDialog(ctk.CTkToplevel):
    def __init__(self, parent, title, message, icon_type="info", options=["OK"]):
        super().__init__(parent)
        self.parent = parent
        self.title(title)
        self.result = None

        # Determine if we need a scrollbar (long message)
        is_long = len(message) > 250 or message.count('\n') > 4

        # Dynamic height calculation
        width = 500
        if is_long:
            estimated_lines = (len(message) // 45) + message.count('\n') + 1
            text_height = max(100, min(250, estimated_lines * 24))
            height = 140 + text_height
        else:
            # For short messages, calculate height based on wrapped lines
            estimated_lines = (len(message) // 40) + message.count('\n') + 1
            height = 160 + (estimated_lines * 22)
            height = min(height, 350) # Cap it

        try:
            parent.update_idletasks()
            x = parent.winfo_x() + (parent.winfo_width() // 2) - (width // 2)
            y = parent.winfo_y() + (parent.winfo_height() // 2) - (height // 2)
            self.geometry(f"{width}x{int(height)}+{x}+{y}")
        except:
            self.geometry(f"{width}x{int(height)}")

        self.resizable(False, False)
        self.transient(parent)

        self.wait_visibility()
        self.grab_set()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Main frame
        self.frame = ctk.CTkFrame(self, corner_radius=c.CORNER_RADIUS)
        self.frame.grid(row=0, column=0, sticky="nsew", padx=15, pady=15)

        self.frame.grid_rowconfigure(0, weight=1)
        self.frame.grid_columnconfigure(0, weight=1)

        # Content Subframe
        self.content_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        self.content_frame.grid(row=0, column=0, padx=25, pady=(20, 10), sticky="nsew")
        self.content_frame.grid_columnconfigure(1, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=1) # Crucial for vertical centering

        # Icon mapping
        icon_map = {
            "info": ("#3498db", "ℹ️"),
            "warning": ("#f1c40f", "⚠️"),
            "error": ("#e74c3c", "❌"),
            "question": ("#2ecc71", "❓")
        }
        color, icon_char = icon_map.get(icon_type, icon_map["info"])

        # Icon label - Centered vertically (removed sticky="n")
        self.lbl_icon = ctk.CTkLabel(self.content_frame, text=icon_char, font=("Roboto", 55), text_color=color)
        self.lbl_icon.grid(row=0, column=0, padx=(0, 25))

        if is_long:
            # Long text: Use Textbox with scrollbar
            self.txt_msg = ctk.CTkTextbox(
                self.content_frame,
                font=c.FONT_NORMAL,
                fg_color="transparent",
                wrap="word",
                activate_scrollbars=True,
                height=text_height
            )
            self.txt_msg.grid(row=0, column=1, sticky="nsew")
            self.txt_msg.insert("0.0", message)
            self.txt_msg.configure(state="disabled")
        else:
            # Short text: Use Label for better vertical centering and no unnecessary space
            self.lbl_msg = ctk.CTkLabel(
                self.content_frame,
                text=message,
                font=c.FONT_NORMAL,
                wraplength=320,
                justify="left",
                anchor="w"
            )
            self.lbl_msg.grid(row=0, column=1, sticky="ew")

        # Buttons frame - Centered horizontally
        self.btn_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        self.btn_frame.grid(row=1, column=0, pady=(0, 20), padx=20, sticky="s")

        self.btn_inner = ctk.CTkFrame(self.btn_frame, fg_color="transparent")
        self.btn_inner.pack()

        for i, opt in enumerate(options):
            btn_color = c.COLOR_BLUE_BUTTON
            opt_low = opt.lower()
            is_positive = any(word in opt_low for word in ["sí", "yes", "ok", "confirm", "instalar", "play", "jugar"])
            is_negative = any(word in opt_low for word in ["no", "cancel", "borrar", "delete", "eliminar"])

            if is_positive:
                btn_color = c.COLOR_PRIMARY_GREEN
            elif is_negative:
                btn_color = c.COLOR_RED_BUTTON

            btn = ctk.CTkButton(
                self.btn_inner,
                text=opt,
                width=115,
                height=38,
                fg_color=btn_color,
                command=lambda val=opt: self.close(val),
                font=c.FONT_BOLD
            )
            btn.pack(side="left", padx=10)

            if i == 0:
                self.bind("<Return>", lambda e: self.close(options[0]))

        self.bind("<Escape>", lambda e: self.close(None))

    def close(self, value):
        self.result = value
        self.destroy()

# Helper functions to mimic messagebox
def showinfo(parent, title, message):
    dialog = CustomDialog(parent, title, message, icon_type="info", options=["OK"])
    parent.wait_window(dialog)

def showwarning(parent, title, message):
    dialog = CustomDialog(parent, title, message, icon_type="warning", options=["OK"])
    parent.wait_window(dialog)

def showerror(parent, title, message):
    dialog = CustomDialog(parent, title, message, icon_type="error", options=["OK"])
    parent.wait_window(dialog)

def askyesno(parent, title, message):
    options = [getattr(c, "UI_YES", "Sí"), getattr(c, "UI_NO", "No")]
    dialog = CustomDialog(parent, title, message, icon_type="question", options=options)
    parent.wait_window(dialog)
    return dialog.result == options[0]

def askokcancel(parent, title, message):
    options = ["OK", getattr(c, "UI_CANCEL", "Cancelar")]
    dialog = CustomDialog(parent, title, message, icon_type="question", options=options)
    parent.wait_window(dialog)
    return dialog.result == options[0]
