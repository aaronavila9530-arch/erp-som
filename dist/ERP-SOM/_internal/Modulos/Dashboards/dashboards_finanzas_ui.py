import tkinter as tk
from tkinter import ttk, messagebox
import threading

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from api_client import get_dashboard_finanzas_resumen_api


class DashboardsFinanzasUI(ttk.Frame):

    def __init__(self, parent):
        super().__init__(parent)

        self.parent = parent
        self.pack(fill="both", expand=True)

        self._build_ui()

    # =========================================================
    # UI
    # =========================================================

    def _build_ui(self):

        container = ttk.Frame(self)
        container.pack(fill="both", expand=True, padx=20, pady=20)

        # -----------------------------------------------------
        # HEADER
        # -----------------------------------------------------

        header = ttk.Frame(container)
        header.pack(fill="x")

        ttk.Label(
            header,
            text="Dashboard - Finanzas",
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

        filtros_frame = ttk.Frame(container)
        filtros_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(filtros_frame, text="Año").grid(row=0, column=0, padx=5)

        self.combo_anio = ttk.Combobox(
            filtros_frame,
            width=10,
            state="readonly"
        )

        self.combo_anio.grid(row=0, column=1, padx=5)

        ttk.Label(filtros_frame, text="Cliente").grid(row=0, column=2, padx=5)

        self.combo_cliente = ttk.Combobox(
            filtros_frame,
            width=25,
            state="readonly"
        )

        self.combo_cliente.grid(row=0, column=3, padx=5)

        self.btn_buscar = ttk.Button(
            filtros_frame,
            text="Buscar",
            command=self._crear_graficos
        )

        self.btn_buscar.grid(row=0, column=4, padx=10)

        self.loading_label = ttk.Label(
            filtros_frame,
            text=""
        )

        self.loading_label.grid(row=0, column=5, padx=10)

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
            (0, 0),
            window=self.graph_container,
            anchor="nw"
        )

        canvas.configure(
            yscrollcommand=scrollbar.set
        )

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
    # CLEAR
    # =========================================================

    def _clear_graphs(self):

        for child in self.graph_container.winfo_children():
            child.destroy()

    # =========================================================
    # BOTON BUSCAR
    # =========================================================

    def _crear_graficos(self):

        self._cargar_dashboard()

    # =========================================================
    # THREAD
    # =========================================================

    def _cargar_dashboard(self):

        self.btn_buscar.config(state="disabled")
        self.loading_label.config(text="Cargando...")

        thread = threading.Thread(
            target=self._consultar_api,
            daemon=True
        )

        thread.start()

    # =========================================================
    # CONSULTA API
    # =========================================================

    def _consultar_api(self):

        try:

            data = get_dashboard_finanzas_resumen_api(
                anio=self.combo_anio.get() or None,
                cliente=self.combo_cliente.get() or None
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
                    f"No se pudo cargar el dashboard:\n{str(e)}"
                )
            )

        finally:

            self.after(0, self._finalizar)

    # =========================================================
    # FINALIZAR
    # =========================================================

    def _finalizar(self):

        self.btn_buscar.config(state="normal")
        self.loading_label.config(text="")

    # =========================================================
    # RENDER
    # =========================================================

    def _render_dashboard(self, data):

        self._clear_graphs()

        kpis = data["kpis"]

        # =====================================================
        # KPI CARDS
        # =====================================================

        kpi_frame = ttk.Frame(self.graph_container)
        kpi_frame.pack(fill="x", pady=10)

        self._crear_kpi(kpi_frame, "Revenue", kpis["revenue_total"])
        self._crear_kpi(kpi_frame, "Accounts Receivable", kpis["ar_total"])
        self._crear_kpi(kpi_frame, "Payments", kpis["payments_total"])
        self._crear_kpi(kpi_frame, "Accounts Payable", kpis["ap_total"])

        # =====================================================
        # REVENUE MENSUAL
        # =====================================================

        self._crear_bar_chart(
            "Revenue Monthly",
            data["revenue_mensual"],
            "mes",
            "revenue"
        )

        # =====================================================
        # AGING AR
        # =====================================================

        self._crear_bar_chart(
            "Accounts Receivable Aging",
            data["aging_ar"],
            "bucket_aging",
            "total"
        )

        # =====================================================
        # TOP CLIENTES DEUDA
        # =====================================================

        self._crear_bar_chart(
            "Top Clientes con Deuda",
            data["top_clientes_deuda"],
            "nombre_cliente",
            "deuda",
            rotate_labels=True
        )

    # =========================================================
    # KPI CARD
    # =========================================================

    def _crear_kpi(self, parent, title, value):

        frame = ttk.Frame(parent)
        frame.pack(side="left", padx=10)

        ttk.Label(
            frame,
            text=title,
            font=("Segoe UI", 10)
        ).pack()

        ttk.Label(
            frame,
            text=f"{value:,.2f}",
            font=("Segoe UI", 14, "bold")
        ).pack()

    # =========================================================
    # GRAFICOS
    # =========================================================

    def _crear_bar_chart(self, title, dataset, label_key, value_key, rotate_labels=False):

        frame = ttk.Frame(self.graph_container)
        frame.pack(fill="x", pady=10)

        labels = [x[label_key] for x in dataset]
        values = [x[value_key] for x in dataset]

        fig = Figure(figsize=(10,4), dpi=100)
        ax = fig.add_subplot(111)

        ax.bar(labels, values)

        if rotate_labels:
            ax.set_xticklabels(labels, rotation=45, ha="right")

        ax.set_title(title)

        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)