import tkinter as tk
from tkinter import ttk, messagebox

from api_client import (
    get_status_informes_api,
    get_status_informes_statuses_api
)


class StatusInformesTable(ttk.Frame):
    """
    MAIN SCREEN — STATUS INFORMES

    • No auto-load
    • Filtros dinámicos
    • Paginado 50
    • Scroll horizontal + vertical
    • Pending en rojo pastel
    """

    PAGE_SIZE = 50

    # =========================================================
    # INIT
    # =========================================================
    def __init__(self, parent):
        super().__init__(parent)

        self._data_all = []
        self._page = 1
        self._filters_loaded = False

        self._build_ui()

    # =========================================================
    # UI
    # =========================================================
    def _build_ui(self):

        self.pack(fill="both", expand=True)

        # ================= TOP =================
        top = ttk.Frame(self)
        top.pack(fill="x", padx=15, pady=10)

        ttk.Label(
            top,
            text="Status de Informes",
            font=("Segoe UI", 13, "bold")
        ).pack(side="left")

        ttk.Button(
            top,
            text="🔎 Buscar",
            command=self._on_search
        ).pack(side="right")

        self.lbl_info = ttk.Label(
            top,
            text="(Presiona Buscar para cargar datos)"
        )
        self.lbl_info.pack(side="right", padx=10)

        # ================= FILTERS =================
        filters = ttk.Frame(self)
        filters.pack(fill="x", padx=15, pady=(0, 10))

        self.filter_status = tk.StringVar()
        self.filter_continent = tk.StringVar()
        self.filter_country = tk.StringVar()
        self.filter_port = tk.StringVar()
        self.filter_year = tk.StringVar()
        self.filter_month = tk.StringVar()

        def _cb(label, var, width=14):
            ttk.Label(filters, text=label).pack(side="left", padx=(0, 5))
            cb = ttk.Combobox(filters, textvariable=var, width=width, state="readonly")
            cb.pack(side="left", padx=(0, 15))
            return cb

        self.cb_status = _cb("Status", self.filter_status)
        self.cb_continent = _cb("Continente", self.filter_continent)
        self.cb_country = _cb("País", self.filter_country)
        self.cb_port = _cb("Puerto", self.filter_port)
        self.cb_year = _cb("Año", self.filter_year, 8)
        self.cb_month = _cb("Mes", self.filter_month, 8)

        # ================= TABLE =================
        table_container = ttk.Frame(self)
        table_container.pack(fill="both", expand=True, padx=15)

        self._build_table(table_container)

        # ================= PAGINATION =================
        pagination = ttk.Frame(self)
        pagination.pack(fill="x", padx=15, pady=10)

        self.btn_prev = ttk.Button(
            pagination,
            text="← Prev",
            command=self._prev_page,
            state="disabled"
        )
        self.btn_prev.pack(side="left")

        self.lbl_page = ttk.Label(pagination, text="Page 0 / 0")
        self.lbl_page.pack(side="left", padx=10)

        self.btn_next = ttk.Button(
            pagination,
            text="Next →",
            command=self._next_page,
            state="disabled"
        )
        self.btn_next.pack(side="left")

    # =========================================================
    # TABLE
    # =========================================================
    def _build_table(self, parent):

        columns = (
            "num_informe",
            "buque",
            "cliente",
            "detalle",
            "continente",
            "pais",
            "puerto",
            "operacion",
            "fecha_inicio",
            "status"
        )

        self.tree = ttk.Treeview(
            parent,
            columns=columns,
            show="headings",
            height=18
        )

        headers = {
            "num_informe": "Num Informe",
            "buque": "Buque",
            "cliente": "Cliente",
            "detalle": "Detalle",
            "continente": "Continente",
            "pais": "País",
            "puerto": "Puerto",
            "operacion": "Operación",
            "fecha_inicio": "Fecha Inicio",
            "status": "Status"
        }

        widths = {
            "num_informe": 170,
            "buque": 180,
            "cliente": 180,
            "detalle": 200,
            "continente": 120,
            "pais": 120,
            "puerto": 120,
            "operacion": 200,
            "fecha_inicio": 120,
            "status": 120
        }

        for col in columns:
            self.tree.heading(col, text=headers[col])
            self.tree.column(col, width=widths[col], anchor="center")

        self.tree.pack(fill="both", expand=True, side="left")

        scroll_y = ttk.Scrollbar(parent, orient="vertical", command=self.tree.yview)
        scroll_y.pack(side="right", fill="y")

        scroll_x = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        scroll_x.pack(fill="x")

        self.tree.configure(
            yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set
        )

        # 🎨 Pending rojo pastel
        self.tree.tag_configure(
            "pending",
            background="#FFD6D6"
        )

    # =========================================================
    # SEARCH
    # =========================================================
    def _on_search(self):

        try:
            self.lbl_info.config(text="Buscando...")
            self.update_idletasks()

            # -------------------------------------------------
            # CARGAR FILTROS DINÁMICOS SOLO UNA VEZ
            # -------------------------------------------------
            if not self._filters_loaded:

                # 🔥 Traer TODOS los registros sin filtro de status
                full_resp = get_status_informes_api(status="")

                if full_resp.get("success"):
                    all_rows = full_resp.get("data", [])
                    self._load_dynamic_filters(all_rows)

                # Status desde endpoint dedicado
                statuses = get_status_informes_statuses_api()
                self.cb_status["values"] = [""] + sorted(statuses)

                self._filters_loaded = True

            # -------------------------------------------------
            # CONSULTA CON FILTROS ACTUALES
            # -------------------------------------------------
            resp = get_status_informes_api(
                status=self.filter_status.get() or None,
                continente=self.filter_continent.get() or None,
                pais=self.filter_country.get() or None,
                puerto=self.filter_port.get() or None,
                year=self.filter_year.get() or None,
                month=self.filter_month.get() or None
            )

            if not resp.get("success"):
                self._data_all = []
            else:
                self._data_all = resp.get("data", [])

            self._page = 1
            self._render_page()

        except Exception as e:
            messagebox.showerror("Error", str(e))

    # =========================================================
    # RENDER
    # =========================================================
    def _render_page(self):

        self.tree.delete(*self.tree.get_children())

        total = len(self._data_all)

        if total == 0:
            self.lbl_page.config(text="Page 0 / 0")
            self.btn_prev.config(state="disabled")
            self.btn_next.config(state="disabled")
            self.lbl_info.config(text="Sin resultados")
            return

        total_pages = (total + self.PAGE_SIZE - 1) // self.PAGE_SIZE

        start = (self._page - 1) * self.PAGE_SIZE
        end = start + self.PAGE_SIZE

        for r in self._data_all[start:end]:

            tags = ()
            if r.get("status_informe") == "Pending":
                tags = ("pending",)

            self.tree.insert(
                "",
                "end",
                values=(
                    r.get("num_informe"),
                    r.get("buque_contenedor"),
                    r.get("cliente"),
                    r.get("detalle"),
                    r.get("continente"),
                    r.get("pais"),
                    r.get("puerto"),
                    r.get("operacion"),
                    r.get("fecha_inicio"),
                    r.get("status_informe")
                ),
                tags=tags
            )

        self.lbl_page.config(
            text=f"Page {self._page} / {total_pages}"
        )

        self.lbl_info.config(
            text=f"Resultados: {total}"
        )

        self.btn_prev.config(
            state="normal" if self._page > 1 else "disabled"
        )

        self.btn_next.config(
            state="normal" if self._page < total_pages else "disabled"
        )

    # =========================================================
    # LOAD DYNAMIC FILTER VALUES FROM API DATA
    # =========================================================
    def _load_dynamic_filters(self, rows):

        continents = set()
        countries = set()
        ports = set()
        years = set()
        months = set()

        for r in rows:

            if r.get("continente"):
                continents.add(r["continente"])

            if r.get("pais"):
                countries.add(r["pais"])

            if r.get("puerto"):
                ports.add(r["puerto"])

            if r.get("fecha_inicio"):
                try:
                    year = str(r["fecha_inicio"])[:4]
                    month = str(r["fecha_inicio"])[5:7]

                    years.add(year)
                    months.add(month)

                except Exception:
                    pass

        self.cb_continent["values"] = [""] + sorted(continents)
        self.cb_country["values"] = [""] + sorted(countries)
        self.cb_port["values"] = [""] + sorted(ports)
        self.cb_year["values"] = [""] + sorted(years)
        self.cb_month["values"] = [""] + sorted(months)


    # =========================================================
    # NAV
    # =========================================================
    def _prev_page(self):
        if self._page > 1:
            self._page -= 1
            self._render_page()

    def _next_page(self):
        self._page += 1
        self._render_page()
