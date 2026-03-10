import tkinter as tk
from tkinter import ttk, messagebox


class PopupNoticias(tk.Toplevel):
    """
    Popup para publicar noticias HHRR.

    • Envía las noticias al backend vía callback
    • Al cerrarse, el HOME se refresca inmediatamente
    """

    def __init__(self, parent, on_save):
        super().__init__(parent)

        self.on_save = on_save

        self.title("Publicar noticias")
        self.geometry("520x420")
        self.resizable(False, False)

        self.vars = [tk.StringVar() for _ in range(5)]

        # =====================================================
        # UI
        # =====================================================
        container = ttk.Frame(self)
        container.pack(fill="both", expand=True, padx=15, pady=15)

        ttk.Label(
            container,
            text="Publicación de noticias HHRR",
            font=("Segoe UI", 12, "bold")
        ).pack(anchor="w", pady=(0, 10))

        for i in range(5):
            ttk.Label(
                container,
                text=f"Noticia {i + 1}"
            ).pack(anchor="w")

            ttk.Entry(
                container,
                textvariable=self.vars[i],
                width=70
            ).pack(anchor="w", pady=(0, 8))

        footer = ttk.Frame(container)
        footer.pack(fill="x", pady=(10, 0))

        ttk.Button(
            footer,
            text="Cancelar",
            command=self.destroy
        ).pack(side="right", padx=5)

        ttk.Button(
            footer,
            text="Publicar",
            command=self._guardar
        ).pack(side="right", padx=5)

        # Modal
        self.transient(parent)
        self.grab_set()
        self.focus_force()

    # =====================================================
    # ACTIONS
    # =====================================================
    def _guardar(self):
        payload = {
            f"noticia_{i + 1}": self.vars[i].get().strip() or None
            for i in range(5)
        }

        if not any(payload.values()):
            messagebox.showwarning(
                "Validación",
                "Debe ingresar al menos una noticia."
            )
            return

        try:
            # 🔥 Ejecuta el callback (API + refresh HOME)
            self.on_save(payload)

        except Exception as e:
            messagebox.showerror(
                "Error",
                str(e)
            )
            return

        # ✅ Cierre limpio (HOME ya refrescado)
        self.destroy()
