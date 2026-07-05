import tkinter as tk
from tkinter import ttk, messagebox
import threading

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from api_client import (
    get_dashboard_comercial_resumen_api,
    get_dashboard_comercial_filtros_api
)


class DashboardsComercialUI(ttk.Frame):

    def __init__(self, parent):
        super().__init__(parent)

        self.parent = parent

        self.pack(fill="both", expand=True)

        self._build_ui()

        self._cargar_filtros()


    # =========================================================
    # UI
    # =========================================================

    def _build_ui(self):

        container = ttk.Frame(self)
        container.pack(fill="both", expand=True, padx=20, pady=20)

        # HEADER

        header = ttk.Frame(container)
        header.pack(fill="x")

        ttk.Label(
            header,
            text="Dashboard - Comercial",
            font=("Segoe UI", 16, "bold")
        ).pack(side="left")

        ttk.Button(
            header,
            text="Home",
            command=self._go_home
        ).pack(side="right")

        ttk.Separator(container).pack(fill="x", pady=10)

        # =====================================================
        # FILTROS
        # =====================================================

        filtros = ttk.Frame(container)
        filtros.pack(fill="x", pady=10)

        ttk.Label(filtros, text="Año").grid(row=0, column=0, padx=5)

        self.combo_anio = ttk.Combobox(filtros, width=10, state="readonly")
        self.combo_anio.grid(row=0, column=1, padx=5)

        ttk.Label(filtros, text="País").grid(row=0, column=2, padx=5)

        self.combo_pais = ttk.Combobox(filtros, width=15, state="readonly")
        self.combo_pais.grid(row=0, column=3, padx=5)

        ttk.Label(filtros, text="Puerto").grid(row=0, column=4, padx=5)

        self.combo_puerto = ttk.Combobox(filtros, width=15, state="readonly")
        self.combo_puerto.grid(row=0, column=5, padx=5)

        ttk.Label(filtros, text="Cliente").grid(row=0, column=6, padx=5)

        self.combo_cliente = ttk.Combobox(filtros, width=18, state="readonly")
        self.combo_cliente.grid(row=0, column=7, padx=5)

        ttk.Label(filtros, text="Operación").grid(row=0, column=8, padx=5)

        self.combo_operacion = ttk.Combobox(filtros, width=18, state="readonly")
        self.combo_operacion.grid(row=0, column=9, padx=5)

        self.btn_buscar = ttk.Button(
            filtros,
            text="Buscar",
            command=self._buscar_dashboard
        )

        self.btn_buscar.grid(row=0, column=10, padx=10)

        self.loading = ttk.Label(filtros, text="")
        self.loading.grid(row=0, column=11, padx=10)

        # =====================================================
        # SCROLL AREA
        # =====================================================

        canvas = tk.Canvas(container)

        scrollbar = ttk.Scrollbar(
            container,
            orient="vertical",
            command=canvas.yview
        )

        self.graph_container = ttk.Frame(canvas)

        self.graph_container.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        canvas.create_window(
            (0,0),
            window=self.graph_container,
            anchor="nw"
        )

        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")


    # =========================================================
    # HOME
    # =========================================================

    def _go_home(self):

        for w in self.parent.winfo_children():
            w.destroy()

        from Modulos.Dashboards.dashboards_home_ui import DashboardsHomeUI

        DashboardsHomeUI(self.parent)


    # =========================================================
    # FILTROS
    # =========================================================

    def _cargar_filtros(self):

        try:

            data = get_dashboard_comercial_filtros_api()

            filtros = data

            self.combo_anio["values"] = [x["anio"] for x in filtros["anios"]]
            self.combo_pais["values"] = [x["pais"] for x in filtros["paises"]]
            self.combo_puerto["values"] = [x["puerto"] for x in filtros["puertos"]]
            self.combo_cliente["values"] = [x["cliente"] for x in filtros["clientes"]]
            self.combo_operacion["values"] = [x["operacion"] for x in filtros["operaciones"]]

        except Exception as e:

            messagebox.showerror(
                "Error",
                f"No se pudieron cargar filtros:\n{str(e)}"
            )


    # =========================================================
    # BUSCAR
    # =========================================================

    def _buscar_dashboard(self):

        self.btn_buscar.config(state="disabled")
        self.loading.config(text="Cargando...")

        thread = threading.Thread(
            target=self._consultar_api,
            daemon=True
        )

        thread.start()


    # =========================================================
    # CONSULTAR API
    # =========================================================

    def _consultar_api(self):

        try:

            data = get_dashboard_comercial_resumen_api(

                anio=self.combo_anio.get() or None,
                pais=self.combo_pais.get() or None,
                puerto=self.combo_puerto.get() or None,
                cliente=self.combo_cliente.get() or None,
                operacion=self.combo_operacion.get() or None
            )

            self.after(
                0,
                lambda: self._render_dashboard(data)
            )

        except Exception as e:

            self.after(
                0,
                lambda: messagebox.showerror(
                    "Error",
                    f"No se pudo cargar dashboard:\n{str(e)}"
                )
            )

        finally:

            self.after(0, self._finalizar)


    # =========================================================
    # FINALIZAR
    # =========================================================

    def _finalizar(self):

        self.btn_buscar.config(state="normal")
        self.loading.config(text="")


    # =========================================================
    # CLEAR
    # =========================================================

    def _clear(self):

        for child in self.graph_container.winfo_children():
            child.destroy()


    # =========================================================
    # RENDER DASHBOARD
    # =========================================================

    def _render_dashboard(self, data):

        self._clear()

        k = data["kpis"]

        # =====================================================
        # KPI CARDS
        # =====================================================

        kpi_frame = ttk.Frame(self.graph_container)
        kpi_frame.pack(fill="x", pady=10)

        self._kpi(kpi_frame, "Ticket Promedio", k["ticket_promedio"])
        self._kpi(kpi_frame, "Revenue", k["revenue_total"])
        self._kpi(kpi_frame, "Servicios", k["total_servicios"])
        self._kpi(kpi_frame, "Puertos", k["total_puertos"])
        self._kpi(kpi_frame, "Margen Neto %", k["margen_neto_pct"])

        # =====================================================
        # GRAFICOS
        # =====================================================

        self._bar_chart(
            "Revenue por Puerto",
            data["revenue_por_puerto"],
            "puerto",
            "total_revenue"
        )

        self._bar_chart(
            "Servicios por Puerto",
            data["servicios_por_puerto"],
            "puerto",
            "total_servicios"
        )

        self._bar_chart(
            "Servicios por Operación",
            data["servicios_por_operacion"],
            "operacion",
            "total_servicios",
            rotate=True
        )

        self._bar_chart(
            "Clientes por País",
            data["clientes_por_pais"],
            "pais",
            "total_clientes"
        )

        self._bar_chart(
            "Revenue por País",
            data["revenue_por_pais"],
            "pais",
            "total_revenue"
        )


    # =========================================================
    # KPI
    # =========================================================

    def _kpi(self, parent, title, value):

        frame = ttk.Frame(parent)
        frame.pack(side="left", padx=10)

        ttk.Label(frame, text=title).pack()

        ttk.Label(
            frame,
            text=f"{value:,.2f}",
            font=("Segoe UI", 14, "bold")
        ).pack()


    # =========================================================
    # BAR CHART
    # =========================================================

    def _bar_chart(self, title, dataset, label_key, value_key, rotate=False):

        frame = ttk.Frame(self.graph_container)
        frame.pack(fill="x", pady=10)

        labels = [x[label_key] for x in dataset]
        values = [x[value_key] for x in dataset]

        fig = Figure(figsize=(10,4), dpi=100)
        ax = fig.add_subplot(111)

        ax.bar(labels, values)

        ax.set_title(title)

        if rotate:
            ax.set_xticklabels(labels, rotation=45, ha="right")

        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)