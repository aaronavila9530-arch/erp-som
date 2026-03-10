import tkinter as tk
from tkinter import ttk


class Badge(ttk.Label):
    """
    Badge visual para alertas.
    Se actualiza SOLO cuando se llama set_valor().
    """

    def __init__(self, parent, texto="", bg="#d32f2f", fg="white"):
        super().__init__(parent, text=texto, anchor="center")

        self._bg = bg
        self._fg = fg

        self._configurar()

    def _configurar(self):
        self.configure(
            background=self._bg,
            foreground=self._fg,
            padding=(6, 2),
            font=("Segoe UI", 9, "bold")
        )

    def set_valor(self, valor: int):
        """
        Muestra u oculta el badge.
        """
        if valor and valor > 0:
            self.configure(text=str(valor))
            self.place(relx=1.0, rely=0.0, anchor="ne")
        else:
            self.place_forget()
