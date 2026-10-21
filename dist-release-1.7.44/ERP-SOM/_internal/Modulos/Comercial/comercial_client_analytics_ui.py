import tkinter as tk
from tkinter import ttk, messagebox, filedialog, Menu
import math
import pandas as pd

from api_client import get_comercial_client_view_api
from Modulos.Comercial.date_utils import format_comercial_row_dates
from Modulos.Comercial.popup.popup_cliente_detalle import PopupClienteDetalle


class ComercialClientAnalyticsUI(ttk.Frame):
    """
    COMERCIAL — CLIENT ANALYTICS
    """

    PAGE_SIZE = 50

    def __init__(self, parent, usuario=None, rol=None, on_back=None):
        super().__init__(parent)

        self.parent = parent
        self.usuario = usuario
        self.rol = rol
        self.on_back = on_back

        self._data_all = []
        self._page = 1
        self._available_years = []

        self.pack(fill="both", expand=True)
        self._setup_style()
        self._build_ui()

    # =========================================================
    # STYLE
    # =========================================================
    def _setup_style(self):
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", font=("Segoe UI", 9), rowheight=24)
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))
        style.configure("TLabelFrame", font=("Segoe UI", 9, "bold"))

    # =========================================================
    # UI
    # =========================================================
    def _build_ui(self):

        # ---------------- HEADER ----------------
        header = ttk.Frame(self)
        header.pack(fill="x", padx=20, pady=(15, 10))

        ttk.Label(
            header,
            text="Comercial — Cliente Analytics",
            font=("Segoe UI", 15, "bold")
        ).pack(side="left")

        ttk.Button(
            header,
            text="⬅ Volver",
            command=self._go_back
        ).pack(side="right")

        # ---------------- KPI CARDS ----------------
        kpis = tk.Frame(self)
        kpis.pack(fill="x", padx=20, pady=(0, 12))

        self.kpi_clients = tk.StringVar(value="0")
        self.kpi_services = tk.StringVar(value="0")
        self.kpi_revenue = tk.StringVar(value="0.00")
        self.kpi_costs = tk.StringVar(value="0.00")
        self.kpi_ticket_avg = tk.StringVar(value="0.00")
        self.kpi_gross_margin = tk.StringVar(value="0.00")
        self.kpi_net_margin = tk.StringVar(value="0.00")
        self.kpi_profit_amt = tk.StringVar(value="0.00")
        self.kpi_profit_pct = tk.StringVar(value="0.00 %")

        self._kpi_card(kpis, "Clientes", self.kpi_clients, "#0B5ED7")
        self._kpi_card(kpis, "Servicios", self.kpi_services, "#0AA2C0")
        self._kpi_card(kpis, "Facturado", self.kpi_revenue, "#198754")
        self._kpi_card(kpis, "Costos", self.kpi_costs, "#DC3545")
        self._kpi_card(kpis, "Ticket Promedio", self.kpi_ticket_avg, "#0DCAF0")
        self._kpi_card(kpis, "Margen Bruto", self.kpi_gross_margin, "#6F42C1")
        self._kpi_card(kpis, "Margen Neto", self.kpi_net_margin, "#343A40")
        self._kpi_card(kpis, "Rentabilidad $", self.kpi_profit_amt, "#20C997")
        self._kpi_card(kpis, "Rentabilidad %", self.kpi_profit_pct, "#FD7E14")

        # ---------------- FILTROS ----------------
        filtros = ttk.LabelFrame(self, text="Filtros")
        filtros.pack(fill="x", padx=20, pady=(0, 10))

        self.f_year = tk.StringVar()
        self.f_cliente = tk.StringVar()
        self.f_servicio = tk.StringVar()

        # ---- Año ----
        ttk.Label(filtros, text="Año").grid(row=0, column=0, padx=6, pady=6, sticky="w")
        self.cb_year = ttk.Combobox(
            filtros,
            textvariable=self.f_year,
            width=10,
            state="readonly"
        )
        self.cb_year.grid(row=0, column=1, pady=6)

        # ---- Rango de Años (opcional) ----
        ttk.Label(filtros, text="Desde").grid(row=1, column=0, padx=6, pady=6, sticky="w")
        self.f_year_from = tk.StringVar()
        self.cb_year_from = ttk.Combobox(
            filtros,
            textvariable=self.f_year_from,
            width=10,
            state="readonly"
        )
        self.cb_year_from.grid(row=1, column=1, pady=6)

        ttk.Label(filtros, text="Hasta").grid(row=1, column=2, padx=6, pady=6, sticky="w")
        self.f_year_to = tk.StringVar()
        self.cb_year_to = ttk.Combobox(
            filtros,
            textvariable=self.f_year_to,
            width=10,
            state="readonly"
        )
        self.cb_year_to.grid(row=1, column=3, pady=6)


        # ---- Cliente ----
        ttk.Label(filtros, text="Cliente").grid(row=0, column=2, padx=6, pady=6, sticky="w")
        self.cb_cliente = ttk.Combobox(
            filtros,
            textvariable=self.f_cliente,
            width=25,
            state="readonly"
        )
        self.cb_cliente.grid(row=0, column=3, pady=6)

        # ---- Servicio ----
        ttk.Label(filtros, text="Servicio").grid(row=0, column=4, padx=6, pady=6, sticky="w")
        self.cb_servicio = ttk.Combobox(
            filtros,
            textvariable=self.f_servicio,
            width=25,
            state="readonly"
        )
        self.cb_servicio.grid(row=0, column=5, pady=6)

        # ---- Buscar ----
        ttk.Button(
            filtros,
            text="Buscar",
            command=self._search
        ).grid(row=0, column=6, padx=6)

        ttk.Button(
            filtros,
            text="Limpiar",
            command=self._clear_filters
        ).grid(row=0, column=7, padx=6)

        ttk.Button(
            filtros,
            text="Ver cliente seleccionado",
            command=self._view_selected_client
        ).grid(row=0, column=9, padx=6)



        # ---- Exportar (menú) ----
        btn_export = ttk.Menubutton(filtros, text="Exportar ▾")
        btn_export.grid(row=0, column=8, padx=6)

        export_menu = Menu(btn_export, tearoff=0)
        export_menu.add_command(label="Exportar Excel", command=self._export_excel)
        export_menu.add_command(label="Exportar PDF", command=self._export_pdf)
        btn_export["menu"] = export_menu

        # ---------------- TABLA ----------------
        frame_tabla = ttk.Frame(self)
        frame_tabla.pack(fill="both", expand=True, padx=20)

        self.columnas = [
            "cliente",
            "servicios",
            "buque_contenedor",
            "fecha_inicio",
            "fecha_fin",
            "factura",
            "valor_facturado",
            "costo_operativo",
            "costo_tarjetas",
            "honorarios",
            "iva",
            "comision_bancaria",
            "margen_bruto",
            "margen_neto"
        ]

        self.tabla = ttk.Treeview(frame_tabla, columns=self.columnas, show="headings")

        for col in self.columnas:
            self.tabla.heading(col, text=col.replace("_", " ").upper())
            self.tabla.column(col, width=140, anchor="w")

        self.tabla.pack(side="left", fill="both", expand=True)

        vsb = ttk.Scrollbar(frame_tabla, orient="vertical", command=self.tabla.yview)
        vsb.pack(side="right", fill="y")

        hsb = ttk.Scrollbar(self, orient="horizontal", command=self.tabla.xview)
        hsb.pack(fill="x", padx=20, pady=(0, 5))

        self.tabla.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        # ---------------- PAGINADOR ----------------
        pager = ttk.Frame(self)
        pager.pack(fill="x", padx=20, pady=(0, 10))

        self.lbl_page = ttk.Label(pager, text="Página 0 de 0")
        self.lbl_page.pack(side="left")

        ttk.Button(pager, text="◀ Anterior", command=self._prev_page).pack(side="right", padx=4)
        ttk.Button(pager, text="Siguiente ▶", command=self._next_page).pack(side="right")

    # =========================================================
    # KPI CARD
    # =========================================================
    def _kpi_card(self, parent, title, var, bg):
        box = tk.Frame(parent, bg=bg, padx=12, pady=10)
        box.pack(side="left", fill="x", expand=True, padx=4)

        tk.Label(box, text=title, bg=bg, fg="white", font=("Segoe UI", 9)).pack(anchor="w")
        tk.Label(box, textvariable=var, bg=bg, fg="white", font=("Segoe UI", 12, "bold")).pack(anchor="w")

    # =========================================================
    # DATA
    # =========================================================
    def _search(self):
        year = self.f_year.get()
        year = int(year) if year.isdigit() else None

        year_from = self.f_year_from.get()
        year_to = self.f_year_to.get()

        year_from = int(year_from) if year_from.isdigit() else None
        year_to = int(year_to) if year_to.isdigit() else None

        cliente_sel = self.f_cliente.get().strip() or None
        servicio_sel = self.f_servicio.get().strip() or None

        # -----------------------------------------
        # PRECEDENCIA DE FECHAS
        # -----------------------------------------
        if year_from or year_to:
            year_param = None
            year_from_param = year_from
            year_to_param = year_to
        else:
            year_param = year
            year_from_param = None
            year_to_param = None

        try:
            resp = get_comercial_client_view_api(
                year=year_param,
                year_from=year_from_param,
                year_to=year_to_param,
                cliente=cliente_sel,
                servicio=servicio_sel
            )
        except Exception as e:
            messagebox.showerror("Cliente Analytics", str(e))
            return

        # -------------------------------------------------
        # AÑOS DISPONIBLES
        # -------------------------------------------------
        self._available_years = resp.get("available_years", [])

        self.cb_year["values"] = self._available_years
        self.cb_year_from["values"] = self._available_years
        self.cb_year_to["values"] = self._available_years

        # -------------------------------------------------
        # KPIs (100% BACKEND)
        # -------------------------------------------------
        kpis = resp.get("kpis", {})

        self.kpi_clients.set(kpis.get("clientes", 0))
        self.kpi_services.set(kpis.get("servicios", 0))
        self.kpi_revenue.set(f"{kpis.get('facturado', 0):,.2f}")
        self.kpi_costs.set(f"{kpis.get('costos', 0):,.2f}")
        self.kpi_ticket_avg.set(f"{kpis.get('ticket_promedio', 0):,.2f}")
        self.kpi_gross_margin.set(f"{kpis.get('margen_bruto', 0):,.2f}")
        self.kpi_net_margin.set(f"{kpis.get('margen_neto', 0):,.2f}")
        self.kpi_profit_amt.set(f"{kpis.get('rentabilidad_monto', 0):,.2f}")
        self.kpi_profit_pct.set(f"{kpis.get('rentabilidad_pct', 0):.2f} %")

        # -------------------------------------------------
        # DATA (YA FILTRADA DESDE BACKEND)
        # -------------------------------------------------
        data = resp.get("data", [])

        # -------------------------------------------------
        # COMBOS DINÁMICOS
        # -------------------------------------------------
        self.cb_cliente["values"] = sorted({
            r.get("cliente") for r in data if r.get("cliente")
        })

        self.cb_servicio["values"] = sorted({
            r.get("servicios") for r in data if r.get("servicios")
        })

        self._data_all = data
        self._page = 1
        self._render_page()

    # =========================================================
    # TABLE / EXPORT / NAV
    # =========================================================
    def _render_page(self):
        for i in self.tabla.get_children():
            self.tabla.delete(i)

        total = len(self._data_all)
        if total == 0:
            self.lbl_page.config(text="Página 0 de 0")
            return

        total_pages = math.ceil(total / self.PAGE_SIZE)
        start = (self._page - 1) * self.PAGE_SIZE
        end = start + self.PAGE_SIZE

        for r in self._data_all[start:end]:
            r = format_comercial_row_dates(r, self.columnas)
            self.tabla.insert("", "end", values=[r.get(c, "") for c in self.columnas])

        self.lbl_page.config(text=f"Página {self._page} de {total_pages}")

    def _export_excel(self):
        if not self._data_all:
            return
        path = filedialog.asksaveasfilename(defaultextension=".xlsx")
        if not path:
            return
        export_rows = [format_comercial_row_dates(r, self.columnas) for r in self._data_all]
        pd.DataFrame(export_rows).to_excel(path, index=False)
        messagebox.showinfo("Export", "Excel generado correctamente")

    def _export_pdf(self):
        messagebox.showinfo("Pendiente", "Export PDF se integrará con el motor de reportes")

    def _next_page(self):
        if self._page * self.PAGE_SIZE < len(self._data_all):
            self._page += 1
            self._render_page()

    def _prev_page(self):
        if self._page > 1:
            self._page -= 1
            self._render_page()

    def _go_back(self):
        if self.on_back:
            self.on_back()


    def _clear_filters(self):
        # -------------------------------
        # LIMPIAR VARIABLES DE FILTRO
        # -------------------------------
        self.f_year.set("")
        self.f_cliente.set("")
        self.f_servicio.set("")
        self.f_year_from.set("")
        self.f_year_to.set("")

        # -------------------------------
        # LIMPIAR COMBOBOX
        # -------------------------------
        self.cb_cliente["values"] = []
        self.cb_servicio["values"] = []

        # -------------------------------
        # LIMPIAR DATA Y TABLA
        # -------------------------------
        self._data_all = []
        self._page = 1
        self._render_page()

        # -------------------------------
        # RESET KPIs
        # -------------------------------
        self.kpi_clients.set("0")
        self.kpi_services.set("0")
        self.kpi_revenue.set("0.00")
        self.kpi_costs.set("0.00")
        self.kpi_ticket_avg.set("0.00")
        self.kpi_gross_margin.set("0.00")
        self.kpi_net_margin.set("0.00")
        self.kpi_profit_amt.set("0.00")
        self.kpi_profit_pct.set("0.00 %")


    def _view_selected_client(self):
        selected = self.tabla.selection()

        if not selected:
            messagebox.showwarning(
                "Cliente",
                "Debe seleccionar un cliente en la tabla."
            )
            return

        item = self.tabla.item(selected[0])
        values = item.get("values", [])

        if not values:
            return

        # -----------------------------------------
        # El backend trabaja con nombrejuridico
        # -----------------------------------------
        nombre_juridico = values[0]

        PopupClienteDetalle(
            parent=self,
            nombre=nombre_juridico
        )


