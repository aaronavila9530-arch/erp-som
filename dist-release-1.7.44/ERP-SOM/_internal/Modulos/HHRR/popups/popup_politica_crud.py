import tkinter as tk
from tkinter import ttk, messagebox

from api_client import (
    crear_politica_hr,
    actualizar_politica_hr
)


class PopupPoliticaCRUD(tk.Toplevel):
    """
    Popup CRUD de Políticas HHRR
    - Crear y Editar
    - TODAS las operaciones son vía API
    """

    def __init__(self, parent, modo="crear", data=None, on_success=None):
        super().__init__(parent)

        self.modo = modo
        self.data = data or {}
        self.on_success = on_success

        self.title(
            "Agregar Política" if modo == "crear"
            else "Editar Política"
        )
        self.geometry("720x600")
        self.resizable(True, True)

        self._construir_ui()

        if self.modo == "editar":
            self._cargar_data()

        self.transient(parent)
        self.grab_set()
        self.focus_force()

    # =========================================================
    # UI
    # =========================================================
    def _construir_ui(self):

        frame = ttk.Frame(self)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Categoría
        ttk.Label(frame, text="Categoría").pack(anchor="w")
        self.var_categoria = tk.StringVar()
        ttk.Entry(frame, textvariable=self.var_categoria).pack(fill="x")

        # Título
        ttk.Label(frame, text="Título").pack(anchor="w", pady=(10, 0))
        self.var_titulo = tk.StringVar()
        ttk.Entry(frame, textvariable=self.var_titulo).pack(fill="x")

        # Artículo
        ttk.Label(frame, text="Referencia Artículo").pack(anchor="w", pady=(10, 0))
        self.var_articulo = tk.StringVar()
        ttk.Entry(frame, textvariable=self.var_articulo).pack(fill="x")

        # Contenido
        ttk.Label(frame, text="Contenido").pack(anchor="w", pady=(10, 0))
        self.txt_contenido = tk.Text(frame, wrap="word", height=15)
        self.txt_contenido.pack(fill="both", expand=True)

        # Botones
        frame_btn = ttk.Frame(frame)
        frame_btn.pack(fill="x", pady=10)

        ttk.Button(
            frame_btn,
            text="Guardar",
            command=self._guardar
        ).pack(side="right", padx=5)

        ttk.Button(
            frame_btn,
            text="Cancelar",
            command=self.destroy
        ).pack(side="right")

    # =========================================================
    # DATA
    # =========================================================
    def _cargar_data(self):
        self.var_categoria.set(self.data.get("categoria", ""))
        self.var_titulo.set(self.data.get("titulo", ""))
        self.var_articulo.set(self.data.get("articulo_ref", ""))
        self.txt_contenido.insert("1.0", self.data.get("contenido", ""))

    # =========================================================
    # GUARDAR (API)
    # =========================================================
    def _guardar(self):

        payload = {
            "categoria": self.var_categoria.get().strip(),
            "titulo": self.var_titulo.get().strip(),
            "articulo_ref": self.var_articulo.get().strip(),
            "contenido": self.txt_contenido.get("1.0", "end").strip()
        }

        if not payload["categoria"] or not payload["titulo"] or not payload["contenido"]:
            messagebox.showerror(
                "Error",
                "Categoría, título y contenido son obligatorios."
            )
            return

        try:
            if self.modo == "crear":
                crear_politica_hr(payload)
            else:
                actualizar_politica_hr(self.data["id"], payload)

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No fue posible guardar la política.\n\n{e}"
            )
            return

        if self.on_success:
            self.on_success()

        self.destroy()
