# ============================================================
# COMERCIAL — PORTS ANALYTICS UI
# Archivo: Modulos/Comercial/comercial_ports_analytics_ui.py
# ============================================================

import tkinter as tk
from tkinter import ttk, messagebox
from Modulos.Comercial.popup.popup_ports_coverage import PopupPortsCoverage

from api_client import (
    get_comercial_ports_analytics_api,
    get_comercial_ports_kpis_api,
    get_comercial_ports_filters_api
)


class ComercialPortsAnalyticsUI(ttk.Frame):
    """
    ANALYTICS — PUERTOS
    Vista analítica estratégica por puerto / continente / cliente
    """

    PAGE_SIZE = 50

    def __init__(self, parent, usuario=None, rol=None, on_back=None):
        super().__init__(parent)

        self.parent = parent
        self.usuario = usuario
        self.rol = (rol or "").lower()
        self.on_back = on_back

        # =====================================================
        # STATE
        # =====================================================
        self.data_all = []
        self.page = 1

        # =====================================================
        # FILTER VARS
        # =====================================================
        self.year_from_var = tk.StringVar()
        self.year_to_var = tk.StringVar()
        self.year_exact_var = tk.StringVar()

        self.continente_var = tk.StringVar()
        self.pais_var = tk.StringVar()
        self.cliente_var = tk.StringVar()

        # =====================================================
        # KPI VARS (BACKEND ONLY)
        # =====================================================
        self.kpi_clientes_var = tk.StringVar(value="0")
        self.kpi_paises_var = tk.StringVar(value="0")
        self.kpi_puertos_var = tk.StringVar(value="0")
        self.kpi_facturacion_var = tk.StringVar(value="0.00")
        self.kpi_costos_var = tk.StringVar(value="0.00")
        self.kpi_margen_bruto_var = tk.StringVar(value="0.00")
        self.kpi_margen_neto_var = tk.StringVar(value="0.00")
        self.kpi_rentabilidad_var = tk.StringVar(value="0.00")
        self.kpi_rentabilidad_pct_var = tk.StringVar(value="0.00 %")

        self.pack(fill="both", expand=True)

        self._build_ui()
        self._load_filters_from_backend()

    # =====================================================
    # UI
    # =====================================================
    def _build_ui(self):

        # ================= HEADER =================
        header = ttk.Frame(self)
        header.pack(fill="x", padx=10, pady=5)

        ttk.Label(
            header,
            text="Comercial — Puertos Analytics",
            font=("Segoe UI", 14, "bold")
        ).pack(side="left")

        ttk.Button(
            header,
            text="⟵ Volver",
            command=self._go_back
        ).pack(side="right")

        # ================= FILTROS =================
        filters = ttk.LabelFrame(self, text="Filtros")
        filters.pack(fill="x", padx=10, pady=5)

        ttk.Label(filters, text="Año desde").grid(row=0, column=0, padx=5)
        self.year_from_cb = ttk.Combobox(filters, textvariable=self.year_from_var, width=8, state="readonly")
        self.year_from_cb.grid(row=0, column=1)

        ttk.Label(filters, text="Año hasta").grid(row=0, column=2, padx=5)
        self.year_to_cb = ttk.Combobox(filters, textvariable=self.year_to_var, width=8, state="readonly")
        self.year_to_cb.grid(row=0, column=3)

        ttk.Label(filters, text="Año exacto").grid(row=0, column=4, padx=5)
        self.year_exact_cb = ttk.Combobox(filters, textvariable=self.year_exact_var, width=8, state="readonly")
        self.year_exact_cb.grid(row=0, column=5)

        ttk.Label(filters, text="Continente").grid(row=1, column=0, padx=5)
        self.continente_cb = ttk.Combobox(filters, textvariable=self.continente_var, width=15, state="readonly")
        self.continente_cb.grid(row=1, column=1)

        ttk.Label(filters, text="País").grid(row=1, column=2, padx=5)
        self.pais_cb = ttk.Combobox(filters, textvariable=self.pais_var, width=15, state="readonly")
        self.pais_cb.grid(row=1, column=3)

        ttk.Label(filters, text="Cliente").grid(row=1, column=4, padx=5)
        self.cliente_cb = ttk.Combobox(filters, textvariable=self.cliente_var, width=25, state="readonly")
        self.cliente_cb.grid(row=1, column=5)

        ttk.Button(filters, text="Buscar", command=self._buscar).grid(row=0, column=6, rowspan=2, padx=10)
        ttk.Button(filters, text="Limpiar", command=self._limpiar).grid(row=0, column=7, rowspan=2)
        ttk.Button(filters, text="📊 Cobertura de Puertos", command=self._open_ports_coverage_popup).grid(row=0, column=8, rowspan=2)

        # ================= KPIs =================
        kpis = ttk.Frame(self)
        kpis.pack(fill="x", padx=10, pady=5)

        self._kpi_card(kpis, "Clientes", self.kpi_clientes_var, "#0d6efd", 0)
        self._kpi_card(kpis, "Países", self.kpi_paises_var, "#0dcaf0", 1)
        self._kpi_card(kpis, "Puertos", self.kpi_puertos_var, "#198754", 2)
        self._kpi_card(kpis, "Facturado", self.kpi_facturacion_var, "#6610f2", 3)
        self._kpi_card(kpis, "Costos", self.kpi_costos_var, "#dc3545", 4)
        self._kpi_card(kpis, "Margen Bruto", self.kpi_margen_bruto_var, "#6c757d", 5)
        self._kpi_card(kpis, "Margen Neto", self.kpi_margen_neto_var, "#212529", 6)
        self._kpi_card(kpis, "Rentabilidad %", self.kpi_rentabilidad_pct_var, "#fd7e14", 7)

        # ================= TABLA =================
        table_frame = ttk.Frame(self)
        table_frame.pack(fill="both", expand=True, padx=10, pady=5)

        columns = (
            "continente", "pais", "puerto",
            "total_operaciones", "frecuencia",
            "facturacion_neta", "ticket_promedio",
            "margen_bruto", "margen_neto", "pareto_80"
        )

        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")

        for col in columns:
            self.tree.heading(col, text=col.replace("_", " ").title())
            self.tree.column(col, width=140, anchor="center")

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)

        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        # ================= PAGINACIÓN =================
        pager = ttk.Frame(self)
        pager.pack(fill="x", padx=10, pady=5)

        ttk.Button(pager, text="⟵ Anterior", command=self._prev_page).pack(side="left")
        ttk.Button(pager, text="Siguiente ⟶", command=self._next_page).pack(side="left", padx=10)

    # =====================================================
    # LOAD FILTERS FROM BACKEND
    # =====================================================
    def _load_filters_from_backend(self):
        try:
            data = get_comercial_ports_filters_api()

            years = data.get("years", [])
            clientes = data.get("clientes", [])

            self.year_from_cb["values"] = years
            self.year_to_cb["values"] = years
            self.year_exact_cb["values"] = years
            self.cliente_cb["values"] = clientes

        except Exception as e:
            messagebox.showerror("Error", str(e))

    # =====================================================
    # KPI CARD
    # =====================================================
    def _kpi_card(self, parent, title, var, color, col):
        frame = tk.Frame(parent, bg=color)
        frame.grid(row=0, column=col, padx=4, pady=4, sticky="nsew")

        tk.Label(frame, text=title, bg=color, fg="white").pack(padx=8, pady=(6, 0))
        tk.Label(
            frame,
            textvariable=var,
            bg=color,
            fg="white",
            font=("Segoe UI", 12, "bold")
        ).pack(padx=8, pady=(0, 6))

    # =====================================================
    # BUSCAR
    # =====================================================
    def _buscar(self):

        year_from = self.year_from_var.get()
        year_to = self.year_to_var.get()

        if self.year_exact_var.get():
            year_from = year_to = self.year_exact_var.get()

        filtros = dict(
            year_from=year_from or None,
            year_to=year_to or None,
            continente=self.continente_var.get() or None,
            pais=self.pais_var.get() or None,
            clientes=[self.cliente_var.get()] if self.cliente_var.get() else None
        )

        try:
            resp = get_comercial_ports_analytics_api(**filtros)
            rows = resp.get("data", [])

            rows_sorted = sorted(
                rows,
                key=lambda r: (
                    not bool(r.get("is_pareto_80")),
                    -(r.get("facturacion_neta") or 0)
                )
            )

            self.data_all = rows_sorted
            self.page = 1

            self._sync_comboboxes()
            self._render_page()

            kpis = get_comercial_ports_kpis_api(**filtros)
            self._render_kpis(kpis)

        except Exception as e:
            messagebox.showerror("Error", str(e))
    # =====================================================
    # KPIs (BACKEND)
    # =====================================================
    def _render_kpis(self, k):
        self.kpi_clientes_var.set(k["clientes"])
        self.kpi_paises_var.set(k["paises"])
        self.kpi_puertos_var.set(k["puertos"])
        self.kpi_facturacion_var.set(f'{k["facturacion"]:,.2f}')
        self.kpi_costos_var.set(f'{k["costos"]:,.2f}')
        self.kpi_margen_bruto_var.set(f'{k["margen_bruto"]:,.2f}')
        self.kpi_margen_neto_var.set(f'{k["margen_neto"]:,.2f}')
        self.kpi_rentabilidad_var.set(f'{k["rentabilidad"]:,.2f}')
        self.kpi_rentabilidad_pct_var.set(f'{k["rentabilidad_pct"]:.2f} %')

    # =====================================================
    # COMBOS DINÁMICOS (DERIVADOS DE DATA)
    # =====================================================
    def _sync_comboboxes(self):
        self.continente_cb["values"] = sorted({r["continente"] for r in self.data_all if r.get("continente")})
        self.pais_cb["values"] = sorted({r["pais"] for r in self.data_all if r.get("pais")})

    # =====================================================
    # PAGINACIÓN
    # =====================================================
    def _render_page(self):
        self.tree.delete(*self.tree.get_children())

        start = (self.page - 1) * self.PAGE_SIZE
        end = start + self.PAGE_SIZE

        for r in self.data_all[start:end]:
            self.tree.insert(
                "",
                "end",
                values=(
                    r.get("continente"),
                    r.get("pais"),
                    r.get("puerto"),
                    r.get("total_operaciones") or 0,
                    r.get("frecuencia") or 0,
                    f'{float(r.get("facturacion_neta") or 0):,.2f}',
                    f'{float(r.get("ticket_promedio") or 0):,.2f}',
                    f'{float(r.get("margen_bruto") or 0):,.2f}',
                    f'{float(r.get("margen_neto") or 0):,.2f}',
                    "✔" if r.get("is_pareto_80") else ""
                )
            )

    def _next_page(self):
        if self.page * self.PAGE_SIZE < len(self.data_all):
            self.page += 1
            self._render_page()

    def _prev_page(self):
        if self.page > 1:
            self.page -= 1
            self._render_page()

    # =====================================================
    # LIMPIAR
    # =====================================================
    def _limpiar(self):
        self.year_from_var.set("")
        self.year_to_var.set("")
        self.year_exact_var.set("")
        self.continente_var.set("")
        self.pais_var.set("")
        self.cliente_var.set("")

        self.page = 1
        self.data_all = []

        self.tree.delete(*self.tree.get_children())


    # =====================================================
    # POPUP — PORTS COVERAGE
    # =====================================================
    def _open_ports_coverage_popup(self):

        year_from = self.year_from_var.get() or None
        year_to = self.year_to_var.get() or None
        cliente = self.cliente_var.get() or None

        PopupPortsCoverage(
            self,
            year_from=year_from,
            year_to=year_to,
            cliente=cliente
        )


    # =====================================================
    # BACK
    # =====================================================
    def _go_back(self):
        if callable(self.on_back):
            self.on_back()
