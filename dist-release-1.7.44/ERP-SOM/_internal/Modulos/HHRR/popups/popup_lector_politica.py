import tkinter as tk
from tkinter import ttk


class PopupLectorPolitica(tk.Toplevel):
    """
    Popup lector de política interna (solo lectura)

    • Scroll vertical
    • Texto completo
    • Footer legal fijo
    • Sin edición
    """

    def __init__(
        self,
        parent,
        titulo: str,
        categoria: str,
        articulo_ref: str,
        contenido: str
    ):
        super().__init__(parent)

        self.title("Política Interna de la Empresa")
        self.geometry("800x600")
        self.resizable(True, True)

        self._construir_ui(
            titulo,
            categoria,
            articulo_ref,
            contenido
        )

        self.transient(parent)
        self.grab_set()
        self.focus_force()

    # =========================================================
    # UI
    # =========================================================
    def _construir_ui(
        self,
        titulo,
        categoria,
        articulo_ref,
        contenido
    ):

        # ---------------------------
        # Header
        # ---------------------------
        frame_header = ttk.Frame(self)
        frame_header.pack(fill="x", padx=10, pady=10)

        ttk.Label(
            frame_header,
            text=titulo,
            font=("Segoe UI", 12, "bold")
        ).pack(anchor="w")

        ttk.Label(
            frame_header,
            text=f"Categoría: {categoria} | Referencia: {articulo_ref}",
            font=("Segoe UI", 9),
            foreground="#555555"
        ).pack(anchor="w", pady=(2, 0))

        ttk.Separator(self).pack(fill="x", padx=10, pady=5)

        # ---------------------------
        # Contenido (scroll)
        # ---------------------------
        frame_contenido = ttk.Frame(self)
        frame_contenido.pack(fill="both", expand=True, padx=10, pady=5)

        self.text = tk.Text(
            frame_contenido,
            wrap="word",
            font=("Segoe UI", 10),
            state="normal"
        )
        self.text.pack(side="left", fill="both", expand=True)

        scroll_y = ttk.Scrollbar(
            frame_contenido,
            orient="vertical",
            command=self.text.yview
        )
        scroll_y.pack(side="right", fill="y")

        self.text.configure(yscrollcommand=scroll_y.set)

        self.text.insert("1.0", contenido)
        self.text.configure(state="disabled")

        # ---------------------------
        # Footer legal
        # ---------------------------
        ttk.Separator(self).pack(fill="x", padx=10, pady=5)

        frame_footer = ttk.Frame(self)
        frame_footer.pack(fill="x", padx=10, pady=10)

        footer_text = (
            "Esta política interna se basa en el Reglamento Interno de Trabajo de MSL, "
            "aprobado conforme a la legislación laboral costarricense vigente. "
            "En caso de duda o conflicto, prevalece el documento oficial del Reglamento."
        )

        ttk.Label(
            frame_footer,
            text=footer_text,
            font=("Segoe UI", 8),
            foreground="#666666",
            wraplength=760,
            justify="center"
        ).pack()

        ttk.Button(
            frame_footer,
            text="Cerrar",
            command=self.destroy
        ).pack(pady=8)
