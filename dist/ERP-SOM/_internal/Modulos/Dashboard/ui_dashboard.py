import tkinter as tk
from tkinter import ttk

COLOR_MENU = "#003A75"
COLOR_BG = "white"


class DashboardUI(tk.Frame):

    def __init__(self, parent, go_back_callback):
        super().__init__(parent, bg=COLOR_BG)

        self.go_back_callback = go_back_callback

        self._build_header()
        self._build_filters()
        self._build_content()


    # Encabezado del módulo
    def _build_header(self):
        title = tk.Label(
            self,
            text="Dashboard — ERP-SOM",
            bg=COLOR_BG,
            fg=COLOR_MENU,
            font=("Segoe UI", 18, "bold")
        )
        title.pack(anchor="w", pady=15, padx=20)


    # Área de filtros (vacía por ahora)
    def _build_filters(self):
        frm = tk.Frame(self, bg=COLOR_BG)
        frm.pack(fill="x", padx=20)

        tk.Label(frm, text="Filtros:", bg=COLOR_BG, fg=COLOR_MENU,
                 font=("Segoe UI", 11, "bold")).grid(row=0, column=0, pady=5)

        ttk.Button(
            frm,
            text="Buscar",
            command=self._buscar_placeholder
        ).grid(row=0, column=1, padx=10)

        ttk.Button(
            frm,
            text="Limpiar",
            command=self._limpiar_placeholder
        ).grid(row=0, column=2)


    # Área de tabla (aún sin data)
    def _build_content(self):
        frm = tk.Frame(self, bg=COLOR_BG)
        frm.pack(fill="both", expand=True, padx=20, pady=10)

        tk.Label(
            frm,
            text="(Aquí se mostrarán indicadores y tableros en futuras versiones)",
            bg=COLOR_BG,
            fg="gray",
            font=("Segoe UI", 11)
        ).pack(pady=20)


    # Placeholder para funciones de filtros
    def _buscar_placeholder(self):
        print("🔎 Buscar — pendiente de integración API")

    def _limpiar_placeholder(self):
        print("🧹 Limpiar — pendiente de integración API")
