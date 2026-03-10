# ============================================================
# COMERCIAL — POPUP PORTS COVERAGE ANALYTICS
# Archivo: Modulos/Comercial/popup/popup_ports_coverage.py
# ============================================================

import tkinter as tk
from tkinter import ttk, messagebox

from api_client import get_comercial_ports_coverage_api


class PopupPortsCoverage(tk.Toplevel):
    """
    POPUP ANALÍTICO
    Cobertura de operación por continente / país / puerto
    """

    PAGE_SIZE = 50

    def __init__(self, parent, year_from=None, year_to=None, cliente=None):
        super().__init__(parent)

        self.parent = parent
        self.year_from = year_from
        self.year_to = year_to
        self.cliente = cliente

        self.data_all = []
        self.page = 1

        self.min_ops_var = tk.IntVar(value=3)
        self.estado_var = tk.StringVar()
        self.continente_var = tk.StringVar()
        self.pais_var = tk.StringVar()
        self.puerto_var = tk.StringVar()


        self.kpi_total_puertos = tk.StringVar(value="0")
        self.kpi_con_operacion = tk.StringVar(value="0")
        self.kpi_sin_operacion = tk.StringVar(value="0")
        self.kpi_op_minima = tk.StringVar(value="0")
        self.kpi_op_activa = tk.StringVar(value="0")
        self.kpi_cobertura = tk.StringVar(value="0.00 %")

        self.title("Cobertura de Puertos — Comercial")
        self.geometry("1250x700")
        self.transient(parent)
        self.grab_set()
        self._is_maximized = False
        self._normal_geometry = self.geometry()


        self._build_ui()
        self._load_data()

    # =====================================================
    # UI
    # =====================================================
    def _build_ui(self):

        header = ttk.Frame(self)
        header.pack(fill="x", padx=10, pady=5)

        ttk.Label(
            header,
            text="Cobertura de Operación por Puerto",
            font=("Segoe UI", 14, "bold")
        ).pack(side="left")

        ttk.Button(
            header,
            text="🗖",
            width=3,
            command=self._toggle_maximize
        ).pack(side="right", padx=(0, 5))

        ttk.Button(header, text="Cerrar", command=self.destroy).pack(side="right")

        filters = ttk.LabelFrame(self, text="Parámetros")
        filters.pack(fill="x", padx=10, pady=5)

        ttk.Label(filters, text="Umbral operación mínima").grid(row=0, column=0, padx=5)
        ttk.Spinbox(
            filters,
            from_=1,
            to=20,
            width=6,
            textvariable=self.min_ops_var,
            command=self._reload
        ).grid(row=0, column=1)

        ttk.Label(filters, text="Estado").grid(row=0, column=2, padx=5)
        estado_cb = ttk.Combobox(
            filters,
            textvariable=self.estado_var,
            state="readonly",
            width=20
        )

        ttk.Label(filters, text="Continente").grid(row=1, column=0, padx=5)
        self.continente_cb = ttk.Combobox(
            filters,
            textvariable=self.continente_var,
            state="readonly",
            width=20
        )
        self.continente_cb.grid(row=1, column=1)

        ttk.Label(filters, text="País").grid(row=1, column=2, padx=5)
        self.pais_cb = ttk.Combobox(
            filters,
            textvariable=self.pais_var,
            state="readonly",
            width=20
        )
        self.pais_cb.grid(row=1, column=3)

        ttk.Label(filters, text="Puerto").grid(row=1, column=4, padx=5)
        self.puerto_cb = ttk.Combobox(
            filters,
            textvariable=self.puerto_var,
            state="readonly",
            width=25
        )
        self.puerto_cb.grid(row=1, column=5)

        estado_cb["values"] = ("", "SIN_OPERACION", "OPERACION_MINIMA", "OPERACION_ACTIVA")
        estado_cb.grid(row=0, column=3)
        estado_cb.bind("<<ComboboxSelected>>", lambda e: self._reload())

        self.continente_cb.bind("<<ComboboxSelected>>", lambda e: self._reset_and_render())
        self.pais_cb.bind("<<ComboboxSelected>>", lambda e: self._reset_and_render())
        self.puerto_cb.bind("<<ComboboxSelected>>", lambda e: self._reset_and_render())


        ttk.Button(filters, text="Actualizar", command=self._reload).grid(row=0, column=4, padx=10)

        kpis = ttk.Frame(self)
        kpis.pack(fill="x", padx=10, pady=5)

        self._kpi_card(kpis, "Puertos Totales", self.kpi_total_puertos, "#0d6efd", 0)
        self._kpi_card(kpis, "Con Operación", self.kpi_con_operacion, "#198754", 1)
        self._kpi_card(kpis, "Sin Operación", self.kpi_sin_operacion, "#dc3545", 2)
        self._kpi_card(kpis, "Op. Mínima", self.kpi_op_minima, "#ffc107", 3)
        self._kpi_card(kpis, "Op. Activa", self.kpi_op_activa, "#20c997", 4)
        self._kpi_card(kpis, "Cobertura %", self.kpi_cobertura, "#6f42c1", 5)

        table_frame = ttk.Frame(self)
        table_frame.pack(fill="both", expand=True, padx=10, pady=5)

        columns = (
            "continente", "pais", "puerto",
            "total_operaciones", "total_facturado", "estado_operativo"
        )

        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")

        for col in columns:
            self.tree.heading(col, text=col.replace("_", " ").title())
            self.tree.column(col, width=170, anchor="center")

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)

        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        pager = ttk.Frame(self)
        pager.pack(fill="x", padx=10, pady=5)

        ttk.Button(pager, text="⟵ Anterior", command=self._prev_page).pack(side="left")
        ttk.Button(pager, text="Siguiente ⟶", command=self._next_page).pack(side="left", padx=10)

    # =====================================================
    # DATA
    # =====================================================
    def _load_data(self):
        try:
            resp = get_comercial_ports_coverage_api(
                year_from=self.year_from,
                year_to=self.year_to,
                cliente=self.cliente,
                min_ops=self.min_ops_var.get()
            )

            self.data_all = resp.get("data", [])
            self.page = 1
            self._render_kpis(resp.get("kpis", {}))
            self._sync_location_filters()
            self._render_page()

        except NameError as e:
            messagebox.showerror(
                "Error de integración",
                "El API client usa una función '_get' que no está definida.\n"
                "Debe corregirse en api_client.py."
            )

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _reload(self):
        self._load_data()

    # =====================================================
    # KPIs
    # =====================================================
    def _render_kpis(self, k):
        self.kpi_total_puertos.set(k.get("total_puertos", 0))
        self.kpi_con_operacion.set(k.get("con_operacion", 0))
        self.kpi_sin_operacion.set(k.get("sin_operacion", 0))
        self.kpi_op_minima.set(k.get("operacion_minima", 0))
        self.kpi_op_activa.set(k.get("operacion_activa", 0))
        self.kpi_cobertura.set(f'{float(k.get("cobertura_pct", 0) or 0):.2f} %')

    # =====================================================
    # PAGINACIÓN
    # =====================================================
    def _render_page(self):
        self.tree.delete(*self.tree.get_children())

        rows = self.data_all

        if self.estado_var.get():
            rows = [r for r in rows if r.get("estado_operativo") == self.estado_var.get()]

        if self.continente_var.get():
            rows = [r for r in rows if r.get("continente") == self.continente_var.get()]

        if self.pais_var.get():
            rows = [r for r in rows if r.get("pais") == self.pais_var.get()]

        if self.puerto_var.get():
            rows = [r for r in rows if r.get("puerto") == self.puerto_var.get()]

        start = (self.page - 1) * self.PAGE_SIZE
        end = start + self.PAGE_SIZE

        for r in rows[start:end]:
            self.tree.insert(
                "",
                "end",
                values=(
                    r.get("continente", ""),
                    r.get("pais", ""),
                    r.get("puerto", ""),
                    r.get("total_operaciones", 0),
                    f'{float(r.get("total_facturado") or 0):,.2f}',
                    r.get("estado_operativo", "")
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
            font=("Segoe UI", 11, "bold")
        ).pack(padx=8, pady=(0, 6))

    def _sync_location_filters(self):
        self.continente_var.set("")
        self.pais_var.set("")
        self.puerto_var.set("")

        self.continente_cb["values"] = sorted({
            r.get("continente") for r in self.data_all if r.get("continente")
        })

        self.pais_cb["values"] = sorted({
            r.get("pais") for r in self.data_all if r.get("pais")
        })

        self.puerto_cb["values"] = sorted({
            r.get("puerto") for r in self.data_all if r.get("puerto")
        })


    def _toggle_maximize(self):
        if not self._is_maximized:
            self._normal_geometry = self.geometry()
            self.state("zoomed")
            self._is_maximized = True
        else:
            self.state("normal")
            self.geometry(self._normal_geometry)
            self._is_maximized = False


    def _reset_and_render(self):
        self.page = 1
        self._render_page()


