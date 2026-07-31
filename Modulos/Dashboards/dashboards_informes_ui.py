import tkinter as tk
from tkinter import ttk, messagebox
import threading
from datetime import datetime

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from api_client import (
    get_dashboard_informes_filtros_api,
    get_dashboard_informes_resumen_api
)


class DashboardsInformesUI(ttk.Frame):

    def __init__(self, parent):
        super().__init__(parent)

        self.parent = parent
        self.pack(fill="both", expand=True)

        self._build_ui()
        self._cargar_filtros()

        self.after(300, self._crear_graficos)

    # =========================================================
    # UI
    # =========================================================

    def _build_ui(self):

        container = ttk.Frame(self)
        container.pack(fill="both", expand=True, padx=20, pady=20)

        header = ttk.Frame(container)
        header.pack(fill="x")

        ttk.Label(
            header,
            text="Dashboard - Informes",
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
        filtros.pack(fill="x", pady=(0, 10))

        ttk.Label(filtros, text="Año").grid(row=0, column=0, padx=5, pady=3)

        self.combo_anio = ttk.Combobox(
            filtros,
            width=10,
            state="readonly"
        )
        self.combo_anio.grid(row=0, column=1, padx=5, pady=3)

        ttk.Label(filtros, text="País").grid(row=0, column=2, padx=5, pady=3)

        self.combo_pais = ttk.Combobox(
            filtros,
            width=15,
            state="readonly"
        )
        self.combo_pais.grid(row=0, column=3, padx=5, pady=3)

        ttk.Label(filtros, text="Puerto").grid(row=0, column=4, padx=5, pady=3)

        self.combo_puerto = ttk.Combobox(
            filtros,
            width=15,
            state="readonly"
        )
        self.combo_puerto.grid(row=0, column=5, padx=5, pady=3)

        ttk.Label(filtros, text="Cliente").grid(row=1, column=0, padx=5, pady=3)

        self.combo_cliente = ttk.Combobox(
            filtros,
            width=20,
            state="readonly"
        )
        self.combo_cliente.grid(row=1, column=1, padx=5, pady=3)

        ttk.Label(filtros, text="Operación").grid(row=1, column=2, padx=5, pady=3)

        self.combo_operacion = ttk.Combobox(
            filtros,
            width=20,
            state="readonly"
        )
        self.combo_operacion.grid(row=1, column=3, padx=5, pady=3)

        ttk.Label(filtros, text="Tipo Informe").grid(row=1, column=4, padx=5, pady=3)

        self.combo_tipo = ttk.Combobox(
            filtros,
            width=20,
            state="readonly"
        )
        self.combo_tipo.grid(row=1, column=5, padx=5, pady=3)

        self.btn_buscar = ttk.Button(
            filtros,
            text="Buscar",
            command=self._crear_graficos
        )
        self.btn_buscar.grid(row=0, column=6, rowspan=2, padx=10, pady=3)

        self.loading_label = ttk.Label(
            filtros,
            text=""
        )
        self.loading_label.grid(row=0, column=7, padx=10, pady=3)

        filtros.grid_columnconfigure(7, weight=1)

        # =====================================================
        # SCROLL AREA
        # =====================================================

        self.canvas = tk.Canvas(container, highlightthickness=0)

        scrollbar = ttk.Scrollbar(
            container,
            orient="vertical",
            command=self.canvas.yview
        )

        self.graph_container = ttk.Frame(self.canvas)

        self.graph_container.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        self.canvas.create_window(
            (0, 0),
            window=self.graph_container,
            anchor="nw"
        )

        self.canvas.configure(
            yscrollcommand=scrollbar.set
        )

        self.canvas.pack(side="left", fill="both", expand=True)
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
    # HELPERS
    # =========================================================

    def _safe_list(self, value):

        if isinstance(value, list):
            return value

        return []

    def _safe_number(self, value):

        try:
            if value is None:
                return 0.0
            return float(value)
        except Exception:
            return 0.0

    def _safe_text(self, value):

        if value is None:
            return ""

        return str(value).strip()

    def _set_combo_values(self, combo, values):

        clean_values = []

        for item in self._safe_list(values):

            if item is None:
                continue

            text = str(item).strip()

            if not text:
                continue

            clean_values.append(text)

        combo["values"] = clean_values

    # =========================================================
    # FILTROS API
    # =========================================================

    def _cargar_filtros(self):

        try:

            data = get_dashboard_informes_filtros_api()

            if not isinstance(data, dict):
                raise Exception(f"Respuesta inesperada del API: {data}")

            self._set_combo_values(self.combo_anio, data.get("anios"))
            self._set_combo_values(self.combo_pais, data.get("paises"))
            self._set_combo_values(self.combo_puerto, data.get("puertos"))
            self._set_combo_values(self.combo_cliente, data.get("clientes"))
            self._set_combo_values(self.combo_operacion, data.get("operaciones"))
            self._set_combo_values(self.combo_tipo, data.get("tipos_informe"))

            current_year = str(datetime.now().year)

            if current_year in self.combo_anio["values"]:
                self.combo_anio.set(current_year)
            elif self.combo_anio["values"]:
                self.combo_anio.current(0)

        except Exception as e:

            messagebox.showerror(
                "Error",
                f"No se pudieron cargar filtros:\n{str(e)}"
            )

    # =========================================================
    # CLEAR
    # =========================================================

    def _clear_graphs(self):

        for child in self.graph_container.winfo_children():
            child.destroy()

    # =========================================================
    # BUSCAR
    # =========================================================

    def _crear_graficos(self):

        if str(self.btn_buscar.cget("state")) == "disabled":
            return

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

            anio_value = self._safe_text(self.combo_anio.get()) or None

            data = get_dashboard_informes_resumen_api(
                anio=anio_value,
                pais=self._safe_text(self.combo_pais.get()) or None,
                puerto=self._safe_text(self.combo_puerto.get()) or None,
                cliente=self._safe_text(self.combo_cliente.get()) or None,
                operacion=self._safe_text(self.combo_operacion.get()) or None,
                tipo_informe=self._safe_text(self.combo_tipo.get()) or None
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

        if not isinstance(data, dict):

            messagebox.showwarning(
                "Dashboard",
                f"Respuesta inesperada:\n{data}"
            )

            return

        if "detail" in data:

            messagebox.showwarning(
                "Dashboard",
                f"El backend devolvió un error:\n{data['detail']}"
            )

            return

        kpis = data.get("kpis") or {}

        frame = ttk.Frame(self.graph_container)
        frame.pack(fill="x", pady=10)

        self._crear_kpi(
            frame,
            "Tiempo Promedio (hrs)",
            kpis.get("tiempo_promedio_horas")
        )
        self._crear_kpi(
            frame,
            "Total Informes",
            kpis.get("total_informes")
        )
        self._crear_kpi(
            frame,
            "Clientes",
            kpis.get("clientes_con_informes")
        )
        self._crear_kpi(
            frame,
            "Puertos",
            kpis.get("puertos_con_informes")
        )

        self._crear_bar_chart(
            "Informes por Tipo",
            data.get("informes_por_tipo"),
            "tipo",
            "total"
        )

        self._crear_bar_chart(
            "Informes por País",
            data.get("informes_por_pais"),
            "pais",
            "total"
        )

        self._crear_bar_chart(
            "Informes por Puerto",
            data.get("informes_por_puerto"),
            "puerto",
            "total"
        )

        self._crear_bar_chart(
            "Informes por Cliente",
            data.get("informes_por_cliente"),
            "cliente",
            "total",
            rotate_labels=True
        )

        self._crear_bar_chart(
            "Tiempo Promedio por Operación",
            data.get("tiempo_por_operacion"),
            "operacion",
            "horas_promedio",
            rotate_labels=True
        )

        self.canvas.yview_moveto(0)

    # =========================================================
    # KPI
    # =========================================================

    def _crear_kpi(self, parent, title, value):

        frame = ttk.Frame(parent)
        frame.pack(side="left", padx=10)

        ttk.Label(
            frame,
            text=title
        ).pack()

        ttk.Label(
            frame,
            text=f"{self._safe_number(value):,.2f}",
            font=("Segoe UI", 14, "bold")
        ).pack()

    # =========================================================
    # CHART
    # =========================================================

    def _crear_bar_chart(self, title, dataset, label_key, value_key, rotate_labels=False):

        dataset = self._safe_list(dataset)

        frame = ttk.Frame(self.graph_container)
        frame.pack(fill="x", pady=15)

        labels = []
        values = []

        for row in dataset:

            if not isinstance(row, dict):
                continue

            label = row.get(label_key, "N/A")

            if label is None or str(label).strip() == "":
                label = "N/A"

            label = str(label).strip()

            # -------------------------------------------------
            # ACORTAR LABELS MUY LARGOS
            # -------------------------------------------------

            if len(label) > 20:
                label = label[:20] + "..."

            labels.append(label)

            value = self._safe_number(row.get(value_key))

            # -------------------------------------------------
            # CONVERTIR HORAS A DIAS PARA EL DASHBOARD
            # -------------------------------------------------

            if "tiempo" in title.lower():

                # backend devuelve horas → convertir a días
                value = value / 24

            values.append(value)

        if not labels:

            ttk.Label(
                frame,
                text=f"{title}: sin datos"
            ).pack()

            return

        # -------------------------------------------------
        # LIMITAR A TOP 10 PARA QUE NO SE SATURÉ EL GRÁFICO
        # -------------------------------------------------

        combined = list(zip(labels, values))
        combined.sort(key=lambda x: x[1], reverse=True)
        combined = combined[:10]

        labels = [c[0] for c in combined]
        values = [c[1] for c in combined]

        # -------------------------------------------------
        # SI HAY MUCHOS ELEMENTOS → USAR HORIZONTAL
        # -------------------------------------------------

        horizontal = len(labels) > 6

        fig = Figure(figsize=(10, 5), dpi=100)
        ax = fig.add_subplot(111)

        pos = list(range(len(labels)))

        if horizontal:

            ax.barh(pos, values)
            ax.set_yticks(pos)
            ax.set_yticklabels(labels)

        else:

            ax.bar(pos, values)
            ax.set_xticks(pos)
            ax.set_xticklabels(labels, rotation=45, ha="right")

        ax.set_title(title)

        if "tiempo" in title.lower():
            ax.set_xlabel("Tiempo promedio (días)")

        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
