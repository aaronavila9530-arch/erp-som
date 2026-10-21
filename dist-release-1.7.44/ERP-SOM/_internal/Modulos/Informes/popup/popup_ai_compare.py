import tkinter as tk
from tkinter import ttk


class PopupAICompare(tk.Toplevel):

    """
    ERP-SOM
    PORTIA Text Comparison Popup

    Compara:
    - Texto original
    - Texto propuesto por PORTIA

    Soporta:
    - str
    - list[str]

    on_accept(): callback ejecutado si el usuario acepta.
    """

    # =========================================================
    # INIT
    # =========================================================
    def __init__(self, parent, original_text, ai_text, on_accept=None, on_retry=None):

        super().__init__(parent)

        self.title("Propuesta PORTIA")
        self.geometry("1000x650")
        self.minsize(850, 520)

        self.transient(parent)
        self.grab_set()

        self.on_accept = on_accept
        self.on_retry = on_retry

        # =====================================================
        # MAIN CONTAINER
        # =====================================================
        container = ttk.Frame(self, padding=12)
        container.pack(fill="both", expand=True)

        cols = ttk.Frame(container)
        cols.pack(fill="both", expand=True)

        cols.columnconfigure(0, weight=1)
        cols.columnconfigure(1, weight=1)

        # =====================================================
        # ORIGINAL PANEL
        # =====================================================
        left = ttk.LabelFrame(cols, text="Original Text")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        left.columnconfigure(0, weight=1)
        left.rowconfigure(0, weight=1)

        self.txt_original = tk.Text(
            left,
            wrap="word",
            padx=10,
            pady=10
        )

        self._insert_text(self.txt_original, original_text)
        self.txt_original.config(state="disabled")
        self.txt_original.grid(row=0, column=0, sticky="nsew")

        sb_left = ttk.Scrollbar(left, command=self.txt_original.yview)
        sb_left.grid(row=0, column=1, sticky="ns")

        self.txt_original.configure(
            yscrollcommand=sb_left.set
        )

        # =====================================================
        # AI PANEL
        # =====================================================
        right = ttk.LabelFrame(cols, text="Propuesta PORTIA")
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)

        self.txt_ai = tk.Text(
            right,
            wrap="word",
            padx=10,
            pady=10
        )

        self._insert_text(self.txt_ai, ai_text)
        self.txt_ai.grid(row=0, column=0, sticky="nsew")

        sb_right = ttk.Scrollbar(right, command=self.txt_ai.yview)
        sb_right.grid(row=0, column=1, sticky="ns")

        self.txt_ai.configure(
            yscrollcommand=sb_right.set
        )

        # =====================================================
        # ACTION BUTTONS
        # =====================================================
        actions = ttk.Frame(container)
        actions.pack(fill="x", pady=12)

        ttk.Button(
            actions,
            text="🔁 New Proposal",
            command=self._retry
        ).pack(side="left")

        ttk.Button(
            actions,
            text="❌ Cancel",
            command=self.destroy
        ).pack(side="right", padx=5)

        ttk.Button(
            actions,
            text="✅ Usar texto PORTIA",
            command=self._accept
        ).pack(side="right")

        # =====================================================
        # CENTER WINDOW
        # =====================================================
        self._center_window()

    # =========================================================
    # INSERT TEXT (STR OR LIST)
    # =========================================================
    def _insert_text(self, widget, text_data):

        try:

            if not text_data:
                widget.insert("1.0", "")
                return

            if isinstance(text_data, list):

                formatted = "\n\n".join(
                    f"{i+1}. {str(t).strip()}"
                    for i, t in enumerate(text_data)
                )

            else:

                formatted = str(text_data).strip()

            widget.insert("1.0", formatted)

        except Exception:

            widget.insert("1.0", "")

    # =========================================================
    # ACCEPT PORTIA TEXT
    # =========================================================
    def _accept(self):

        try:

            if callable(self.on_accept):
                self.on_accept()

        except Exception:
            pass

        self.destroy()

    # =========================================================
    # RETRY
    # =========================================================
    def _retry(self):

        try:

            if callable(self.on_retry):
                self.on_retry()

        except Exception:
            pass

        self.destroy()

    # =========================================================
    # CENTER WINDOW
    # =========================================================
    def _center_window(self):

        self.update_idletasks()

        width = self.winfo_width()
        height = self.winfo_height()

        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)

        self.geometry(f"{width}x{height}+{x}+{y}")