import tkinter as tk
from tkinter import ttk, messagebox
import threading

from api_client import get_dashboard_servicios_api
from Modulos.Dashboards.chart_helpers import render_bar_chart, render_pie_chart


class DashboardsServiciosUI(ttk.Frame):

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
            text="Dashboard - Servicios",
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
        self.combo_anio = ttk.Combobox(filtros_frame, width=10, state="readonly")
        self.combo_anio.grid(row=0, column=1, padx=5)

        ttk.Label(filtros_frame, text="País").grid(row=0, column=2, padx=5)
        self.combo_pais = ttk.Combobox(filtros_frame, width=20, state="readonly")
        self.combo_pais.grid(row=0, column=3, padx=5)

        ttk.Label(filtros_frame, text="Puerto").grid(row=0, column=4, padx=5)
        self.combo_puerto = ttk.Combobox(filtros_frame, width=20, state="readonly")
        self.combo_puerto.grid(row=0, column=5, padx=5)

        ttk.Label(filtros_frame, text="Cliente").grid(row=0, column=6, padx=5)
        self.combo_cliente = ttk.Combobox(filtros_frame, width=25, state="readonly")
        self.combo_cliente.grid(row=0, column=7, padx=5)

        self.btn_crear = ttk.Button(
            filtros_frame,
            text="Actualizar Dashboard",
            command=self._crear_graficos
        )
        self.btn_crear.grid(row=0, column=8, padx=10)

        self.loading_label = ttk.Label(filtros_frame, text="")
        self.loading_label.grid(row=0, column=9, padx=10)

        # =====================================================
        # SCROLL AREA PARA GRAFICOS
        # =====================================================

        canvas = tk.Canvas(container)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)

        self.graph_container = ttk.Frame(canvas)

        self.graph_container.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.graph_container, anchor="nw")

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
    # CLEAR
    # =========================================================

    def _clear_graphs(self):

        for child in self.graph_container.winfo_children():
            child.destroy()

    # =========================================================
    # BOTON
    # =========================================================

    def _crear_graficos(self):
        self._cargar_dashboard()

    # =========================================================
    # THREAD
    # =========================================================

    def _cargar_dashboard(self):

        self.btn_crear.config(state="disabled")
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

            data = get_dashboard_servicios_api(
                anio=self.combo_anio.get() or None,
                pais=self.combo_pais.get() or None,
                puerto=self.combo_puerto.get() or None,
                cliente=self.combo_cliente.get() or None
            )

            self.after(0, lambda: self._render_dashboard(data))

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

        self.btn_crear.config(state="normal")
        self.loading_label.config(text="")

    # =========================================================
    # RENDER
    # =========================================================

    def _render_dashboard(self, data):

        self._clear_graphs()

        filtros = data["filtros"]

        self.combo_anio["values"] = [x["anio"] for x in filtros["anios"]]
        self.combo_pais["values"] = [x["pais"] for x in filtros["paises"]]
        self.combo_puerto["values"] = [x["puerto"] for x in filtros["puertos"]]
        self.combo_cliente["values"] = [x["cliente"] for x in filtros["clientes"]]

        # =====================================================
        # SERVICIOS POR PAIS
        # =====================================================

        self._crear_bar_chart(
            "Revenue mensual (agosto en adelante)",
            data.get("revenue_mensual", []),
            "mes",
            "revenue"
        )

        self._crear_bar_chart(
            "Servicios por País",
            data["servicios_por_pais"],
            "pais",
            "total"
        )

        # =====================================================
        # SERVICIOS POR OPERACION (TOP 10)
        # =====================================================

        dataset = sorted(
            data["servicios_por_operacion"],
            key=lambda x: x["total"],
            reverse=True
        )[:10]

        self._crear_bar_chart(
            "Servicios por Operación (Top 10)",
            dataset,
            "operacion",
            "total",
            rotate_labels=True
        )

        # =====================================================
        # FACTURACION POR PAIS
        # =====================================================

        self._crear_bar_chart(
            "Facturación por País",
            data["facturacion_por_pais"],
            "pais",
            "total_facturado"
        )

        # =====================================================
        # FACTURACION POR TIPO
        # =====================================================

        render_pie_chart(
            self.graph_container,
            "Facturación por Tipo",
            data["facturacion_por_tipo"],
            "tipo",
            "total_facturado"
        )

    # =========================================================
    # UTILIDAD GRAFICOS
    # =========================================================

    def _crear_bar_chart(self, title, dataset, label_key, value_key, rotate_labels=False):

        render_bar_chart(self.graph_container, title, dataset, label_key, value_key, rotate_labels)
