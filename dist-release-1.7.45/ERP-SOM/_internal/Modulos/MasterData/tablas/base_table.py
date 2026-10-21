import tkinter as tk
from tkinter import ttk

COLOR_BG = "white"
COLOR_HEADER = "#003A75"
COLOR_TEXT = "white"


class BasePaginatedTable(tk.Frame):
    def __init__(self, parent, title="Tabla", on_back=None):
        super().__init__(parent, bg=COLOR_BG)

        self.parent = parent
        self.title_text = title
        self.on_back = on_back

        # Paginación
        self.page = 1
        self.page_size = 50
        self.total_items = 0

        # ===============================
        # Encabezado superior SAP
        # ===============================
        self.header = tk.Frame(self, bg=COLOR_HEADER)
        self.header.pack(fill="x")

        # Botón Volver
        self.btn_volver = tk.Button(
            self.header, text="⬅ Volver",
            bg="#555555", fg="white", bd=0,
            command=self._volver
        )
        self.btn_volver.pack(side="left", padx=6, pady=5)

        # Título
        self.lbl_title = tk.Label(
            self.header, text=f"{self.title_text}",
            bg=COLOR_HEADER, fg="white", font=("Segoe UI", 11, "bold")
        )
        self.lbl_title.pack(side="left", padx=10)

        # ===============================
        # Toolbar de acciones
        # ===============================
        self.toolbar = tk.Frame(self, bg="#E8E8E8")
        self.toolbar.pack(fill="x")

        self.btn_ver = tk.Button(self.toolbar, text="Ver", width=12)
        self.btn_ver.pack(side="left", padx=4, pady=4)

        self.btn_editar = tk.Button(self.toolbar, text="Editar", width=12)
        self.btn_editar.pack(side="left", padx=4)

        self.btn_eliminar = tk.Button(self.toolbar, text="Eliminar", width=12)
        self.btn_eliminar.pack(side="left", padx=4)

        # Exportar (menú desplegable)
        self.export_menu = tk.Menubutton(
            self.toolbar, text="Exportar ▼", bg="#005A9C", fg="white",
            width=14, relief="raised"
        )
        self.export_menu.menu = tk.Menu(self.export_menu, tearoff=0)
        self.export_menu["menu"] = self.export_menu.menu

        self.export_menu.menu.add_command(label="CSV")
        self.export_menu.menu.add_command(label="XML")
        self.export_menu.menu.add_command(label="PDF")
        self.export_menu.pack(side="left", padx=4)

        # ===============================
        # Área de tabla
        # ===============================
        self.table_frame = tk.Frame(self, bg=COLOR_BG)
        self.table_frame.pack(fill="both", expand=True)

        self.table = ttk.Treeview(
            self.table_frame,
            columns=[],
            show="headings",
            height=15
        )
        self.table.pack(side="left", fill="both", expand=True)

        # Scroll Y
        scroll_y = ttk.Scrollbar(self.table_frame, orient="vertical", command=self.table.yview)
        scroll_y.pack(side="right", fill="y")
        self.table.configure(yscrollcommand=scroll_y.set)

        # Scroll X
        scroll_x = ttk.Scrollbar(self, orient="horizontal", command=self.table.xview)
        scroll_x.pack(fill="x")
        self.table.configure(xscrollcommand=scroll_x.set)

        # ===============================
        # Navegación paginada
        # ===============================
        self.pagination_frame = tk.Frame(self, bg=COLOR_BG)
        self.pagination_frame.pack(fill="x", pady=5)

        self.lbl_page = tk.Label(self.pagination_frame, text="Página 1", bg=COLOR_BG)
        self.lbl_page.pack(side="left", padx=10)

        self.btn_prev = tk.Button(self.pagination_frame, text="Anterior", command=self.prev_page)
        self.btn_prev.pack(side="left")

        self.btn_next = tk.Button(self.pagination_frame, text="Siguiente", command=self.next_page)
        self.btn_next.pack(side="left")

    # ==================================================
    # Métodos de navegación
    # ==================================================
    def _volver(self):
        if self.on_back:
            self.on_back()
        self.destroy()

    def prev_page(self):
        if self.page > 1:
            self.page -= 1
            self.refresh()

    def next_page(self):
        if (self.page * self.page_size) < self.total_items:
            self.page += 1
            self.refresh()

    # ==================================================
    # Métodos Placeholder a implementar en tablas hijas
    # ==================================================
    def load_data(self):
        """Implementar en tabla hija"""
        pass

    def refresh(self):
        """Re-cargar datos del API"""
        self.load_data()
