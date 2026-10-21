# ============================================================
# COMERCIAL — SERVICIOS ANALYTICS UI (BLINDADO)
# Archivo: Modulos/Comercial/comercial_servicios_analytics_ui.py
# ============================================================

import tkinter as tk
from tkinter import ttk, filedialog, Menu, messagebox
import math
import csv
import pandas as pd

from api_client import (
    get_comercial_servicios_by_servicio_api,
    get_comercial_servicios_kpis_api,
    get_comercial_servicios_no_ofrecidos_api,
    get_comercial_costos_surveyor_pareto_api
)

from Modulos.Comercial.popup.popup_servicios_no_ofrecidos import PopupServiciosNoOfrecidos
from Modulos.Comercial.popup.popup_costos_surveyor import PopupCostosSurveyor





class ComercialServiciosAnalyticsUI(ttk.Frame):

    PAGE_SIZE = 100

    def __init__(self, parent, usuario=None, rol=None, on_back=None):
        super().__init__(parent)

        self.parent = parent
        self.usuario = usuario
        self.rol = (rol or "").lower()
        self.on_back = on_back

        self._data_all = []
        self._page = 1
        self._total_pages = 1
        self._combos = {}

        # Colores KPI (necesario para tk.Label bg)
        self._kpi_colors = {}

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

        # KPI color frames
        kpi_colors = {
            "BLUE": "#1677FF",
            "CYAN": "#13C2C2",
            "GREEN": "#389E0D",
            "PURPLE": "#722ED1",
            "RED": "#CF1322",
            "GRAY": "#595959",
            "BLACK": "#262626",
            "ORANGE": "#FA8C16",
        }
        self._kpi_colors = dict(kpi_colors)

        for k, v in kpi_colors.items():
            style.configure(f"KPI.{k}.TFrame", background=v)

        # Nota: ya NO usamos ttk.Label para títulos/valores KPI,
        # porque ttk puede dibujar un fondo “gris”/resaltado en algunos temas.
        # Se dejan estilos por compatibilidad si los necesitas en el futuro.
        style.configure("KPI.Title.TLabel", foreground="white", font=("Segoe UI", 9, "bold"))
        style.configure("KPI.Value.TLabel", foreground="white", font=("Segoe UI", 12, "bold"))

    # =========================================================
    # UI
    # =========================================================
    def _build_ui(self):

        # ---------------- HEADER ----------------
        header = ttk.Frame(self)
        header.pack(fill="x", padx=10, pady=6)

        ttk.Label(
            header,
            text="Comercial — Servicios Analytics",
            font=("Segoe UI", 14, "bold")
        ).pack(side="left")

        ttk.Button(header, text="⟵ Volver", command=self._volver).pack(side="right")

        # ---------------- FILTROS ----------------
        filtros = ttk.LabelFrame(self, text="Filtros")
        filtros.pack(fill="x", padx=10, pady=6)

        # MODO AÑOS
        self.year_mode_var = tk.StringVar(value="RANGO")  # RANGO | EXACTO

        ttk.Label(filtros, text="Modo").grid(row=0, column=0, padx=4, sticky="w")

        mode_cb = ttk.Combobox(
            filtros,
            textvariable=self.year_mode_var,
            width=14,
            state="readonly",
            values=["RANGO", "EXACTO"]
        )
        mode_cb.grid(row=0, column=1, padx=4)
        mode_cb.bind("<<ComboboxSelected>>", lambda e: self._on_year_mode_change())

        self.year_from_var = tk.StringVar()
        self.year_to_var = tk.StringVar()
        self.continente_var = tk.StringVar()
        self.pais_var = tk.StringVar()
        self.puerto_var = tk.StringVar()
        self.servicio_var = tk.StringVar()
        self.quarter_var = tk.StringVar()

        # Ahora arrancamos columnas después de Modo (col 2 en adelante)
        campos = [
            ("Año desde", self.year_from_var, 8),
            ("Año hasta", self.year_to_var, 8),
            ("Continente", self.continente_var, 14),
            ("País", self.pais_var, 14),
            ("Puerto", self.puerto_var, 14),
            ("Servicio", self.servicio_var, 22),
        ]

        base_col = 2
        for i, (lbl, var, w) in enumerate(campos):
            ttk.Label(
                filtros,
                text=lbl
            ).grid(row=0, column=base_col + i * 2, padx=4, sticky="w")

            cb = ttk.Combobox(
                filtros,
                textvariable=var,
                width=w,
                state="readonly",
                postcommand=self._refresh_filters_on_dropdown
            )
            cb.grid(row=0, column=base_col + i * 2 + 1, padx=4)

            # 🔒 SI CAMBIA AÑO → RECALCULAR ESTADO DE QUARTER
            if lbl in ("Año desde", "Año hasta"):
                cb.bind("<<ComboboxSelected>>", lambda e: self._on_year_mode_change())

            self._combos[lbl] = cb

        # ---------------- QUARTER ----------------
        quarter_col = base_col + len(campos) * 2

        ttk.Label(
            filtros,
            text="Quarter"
        ).grid(row=0, column=quarter_col, padx=4, sticky="w")

        cb_quarter = ttk.Combobox(
            filtros,
            textvariable=self.quarter_var,
            width=8,
            state="disabled",
            values=["Q1", "Q2", "Q3", "Q4"]
        )
        cb_quarter.grid(row=0, column=quarter_col + 1, padx=4)
        self._combos["Quarter"] = cb_quarter

        # ---------------- BOTONES ----------------
        btn_col = quarter_col + 2

        ttk.Button(
            filtros,
            text="Buscar",
            command=self._buscar
        ).grid(row=0, column=btn_col, padx=6)

        ttk.Button(
            filtros,
            text="Limpiar",
            command=self._limpiar
        ).grid(row=0, column=btn_col + 1, padx=6)

        # EXPORTAR ▼
        btn_export = ttk.Button(filtros, text="Exportar ▼")
        btn_export.grid(row=0, column=btn_col + 2, padx=6)

        menu = Menu(btn_export, tearoff=0)
        menu.add_command(label="Exportar CSV", command=lambda: self._export("csv"))
        menu.add_command(label="Exportar Excel", command=lambda: self._export("xlsx"))
        btn_export.bind("<Button-1>", lambda e: menu.tk_popup(e.x_root, e.y_root))

        # Cargar filtros desde backend (SAFE) después de que la UI exista
        self.after(150, self._load_filters_backend)

        # Aplicar estado inicial del modo años
        self.after(200, self._on_year_mode_change)

        # ---------------- BOTÓN NO OFRECIDOS (ALINEADO IZQUIERDA) ----------------
        row_no = ttk.Frame(self)
        row_no.pack(fill="x", padx=10, pady=6)

        ttk.Button(
            row_no,
            text="Ver servicios NO ofrecidos",
            command=self._abrir_no_ofrecidos_popup
        ).pack(side="left", anchor="w")

        ttk.Button(
            row_no,
            text="Ver costos por Surveyor (Pareto 80/20)",
            command=self._abrir_costos_surveyor_popup
        ).pack(side="left", anchor="w", padx=(10, 0))


        # ---------------- KPIs ----------------
        self.kpis_frame = ttk.Frame(self)
        self.kpis_frame.pack(fill="x", padx=10, pady=6)

        for i in range(6):
            self.kpis_frame.grid_columnconfigure(i, weight=1)

        self._kpi_vars = {
            "servicios": tk.StringVar(value="0"),
            "facturado": tk.StringVar(value="0.00"),
            "costos": tk.StringVar(value="0.00"),
            "margen_bruto": tk.StringVar(value="0.00"),
            "margen_neto": tk.StringVar(value="0.00"),
            "rentabilidad": tk.StringVar(value="0.00 %"),
        }

        kpis = [
            ("Servicios", "servicios", "BLUE"),
            ("Facturado", "facturado", "PURPLE"),
            ("Costos", "costos", "RED"),
            ("Margen Bruto", "margen_bruto", "GRAY"),
            ("Margen Neto", "margen_neto", "BLACK"),
            ("Rentabilidad %", "rentabilidad", "ORANGE"),
        ]

        for i, (t, k, c) in enumerate(kpis):
            self._build_kpi(t, self._kpi_vars[k], c, i)

        # ---------------- TABLA ----------------
        frame_table = ttk.LabelFrame(self, text="Servicios Ofrecidos")
        frame_table.pack(fill="both", expand=True, padx=10, pady=6)

        cols = (
            "servicio",
            "cantidad_servicios",
            "revenue_neto_total",
            "costo_total",
            "margen_bruto",
            "margen_neto",
            "margen_neto_pct"
        )

        self.tree = ttk.Treeview(frame_table, columns=cols, show="headings")

        headers = {
            "servicio": "Servicio",
            "cantidad_servicios": "Cantidad",
            "revenue_neto_total": "Revenue Neto",
            "costo_total": "Costo",
            "margen_bruto": "Margen Bruto",
            "margen_neto": "Margen Neto",
            "margen_neto_pct": "%"
        }

        for c in cols:
            self.tree.heading(c, text=headers.get(c, c))
            self.tree.column(c, width=150, anchor="center")

        vsb = ttk.Scrollbar(frame_table, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        # ---------------- PAGINACIÓN ----------------
        pager = ttk.Frame(self)
        pager.pack(fill="x", padx=10, pady=6)

        self.lbl_page = ttk.Label(pager, text="Página 0 de 0")
        self.lbl_page.pack(side="left")

        ttk.Button(pager, text="◀", command=self._prev_page).pack(side="right")
        ttk.Button(pager, text="▶", command=self._next_page).pack(side="right")



    # =========================================================
    # YEAR MODE (EXACTO vs RANGO)
    # =========================================================
    def _on_year_mode_change(self):
        """
        EXACTO: deshabilita Año hasta y lo iguala a Año desde
        RANGO: habilita Año hasta
        """
        mode = (self.year_mode_var.get() or "").strip().upper()
        if mode not in ("EXACTO", "RANGO"):
            mode = "RANGO"
            self.year_mode_var.set("RANGO")

        cb_to = self._combos.get("Año hasta")

        if mode == "EXACTO":
            if cb_to:
                cb_to.configure(state="disabled")

            # Forzar igualdad si ya hay Año desde
            y_from = (self.year_from_var.get() or "").strip()
            if y_from:
                self.year_to_var.set(y_from)

        else:
            if cb_to:
                cb_to.configure(state="readonly")

        # ---------------- QUARTER CONTROL ----------------
        cb_q = self._combos.get("Quarter")
        if cb_q:
            self.quarter_var.set("")

            if self.year_from_var.get():
                cb_q.configure(state="readonly")
            else:
                cb_q.configure(state="disabled")


    # =========================================================
    # KPI UI (SIN RESALTADO)
    # =========================================================
    def _build_kpi(self, title, var, color, col):
        f = ttk.Frame(self.kpis_frame, style=f"KPI.{color}.TFrame", padding=6)
        f.grid(row=0, column=col, padx=4, sticky="nsew")

        bg = self._kpi_colors.get(color, "#262626")

        # tk.Label respeta bg/fg sin “halo” de tema ttk
        lbl_title = tk.Label(
            f,
            text=title,
            bg=bg,
            fg="white",
            font=("Segoe UI", 9, "bold")
        )
        lbl_title.pack(anchor="w")

        lbl_value = tk.Label(
            f,
            textvariable=var,
            bg=bg,
            fg="white",
            font=("Segoe UI", 12, "bold")
        )
        lbl_value.pack(anchor="w")

    def _render_kpis(self, kpis: dict):
        def _n(v):
            try:
                return float(v or 0)
            except Exception:
                return 0.0

        total_servicios = int(kpis.get("total_servicios", 0) or 0)

        revenue_neto_total = _n(kpis.get("revenue_neto_total"))
        costos_totales = _n(kpis.get("costos_totales"))
        margen_bruto_total = _n(kpis.get("margen_bruto_total"))
        margen_neto_total = _n(kpis.get("margen_neto_total"))
        margen_neto_pct = _n(kpis.get("margen_neto_pct"))

        self._kpi_vars["servicios"].set(f"{total_servicios:,}")
        self._kpi_vars["facturado"].set(f"{revenue_neto_total:,.2f}")
        self._kpi_vars["costos"].set(f"{costos_totales:,.2f}")
        self._kpi_vars["margen_bruto"].set(f"{margen_bruto_total:,.2f}")
        self._kpi_vars["margen_neto"].set(f"{margen_neto_total:,.2f}")
        self._kpi_vars["rentabilidad"].set(f"{margen_neto_pct:,.2f}%")

    # =========================================================
    # DATA
    # =========================================================
    def _build_filters_payload(self):
        def _to_int(s: str):
            s = (s or "").strip()
            if not s:
                return None
            try:
                return int(s)
            except Exception:
                return None

        mode = (self.year_mode_var.get() or "").strip().upper()
        if mode not in ("EXACTO", "RANGO"):
            mode = "RANGO"

        y_from = _to_int(self.year_from_var.get())
        y_to = _to_int(self.year_to_var.get())

        # EXACTO: y_to = y_from
        if mode == "EXACTO":
            if y_from is not None:
                y_to = y_from
                self.year_to_var.set(str(y_to))
            else:
                # si no hay año desde, no inventamos nada: backend usará default año en curso
                y_to = None
                self.year_to_var.set("")
        else:
            # RANGO: si viene uno solo → año exacto
            if y_from is not None and y_to is None:
                y_to = y_from
                self.year_to_var.set(str(y_to))

            if y_to is not None and y_from is None:
                y_from = y_to
                self.year_from_var.set(str(y_from))

            # Normalizar orden si están invertidos
            if y_from is not None and y_to is not None and y_from > y_to:
                y_from, y_to = y_to, y_from
                self.year_from_var.set(str(y_from))
                self.year_to_var.set(str(y_to))

        return {
            "year_from": y_from,
            "year_to": y_to,
            "quarter": (self.quarter_var.get() or "").strip() or None,
            "continente": (self.continente_var.get() or "").strip() or None,
            "pais": (self.pais_var.get() or "").strip() or None,
            "puerto": (self.puerto_var.get() or "").strip() or None,
        }

    def _buscar(self):
        try:
            self.tree.delete(*self.tree.get_children())

            filters = self._build_filters_payload()

            resp = get_comercial_servicios_by_servicio_api(**filters)

            # =====================================================
            # CRÍTICO: sincronizar UI con los años realmente aplicados por backend
            # (si backend está recibiendo None → él caerá a año en curso; aquí lo verás)
            # =====================================================
            backend_filters = resp.get("filters", {}) or {}
            bf_yf = backend_filters.get("year_from")
            bf_yt = backend_filters.get("year_to")
            if bf_yf is not None:
                self.year_from_var.set(str(bf_yf))
            if bf_yt is not None:
                self.year_to_var.set(str(bf_yt))
            bf_quarter = backend_filters.get("quarter")
            if bf_quarter:
                self.quarter_var.set(bf_quarter)


            self._data_all = resp.get("data", []) or []

            # Servicio (frontend) seguro
            if self.servicio_var.get():
                self._data_all = [
                    r for r in self._data_all
                    if (r.get("servicio") or "").strip() == (self.servicio_var.get() or "").strip()
                ]

            # KPIs (del backend) + render
            try:
                kpis = get_comercial_servicios_kpis_api(
                    year_from=filters.get("year_from"),
                    year_to=filters.get("year_to"),
                    quarter=filters.get("quarter"),
                    continente=filters.get("continente"),
                    pais=filters.get("pais"),
                    puerto=filters.get("puerto"),
                    operacion=self.servicio_var.get() or None
                ).get("kpis", {}) or {}
            except Exception:
                kpis = {}

            self._render_kpis(kpis)

            self._page = 1
            self._render_page()

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar información.\n{e}")

    # =========================================================
    # LOAD FILTERS (SAFE)
    # =========================================================
    def _refresh_filters_on_dropdown(self):
        self.after(10, self._load_filters_backend)

    def _load_filters_backend(self):
        try:
            resp = get_comercial_servicios_by_servicio_api()
            meta = resp.get("filters", {}) or {}

            years = meta.get("available_years", []) or []
            continentes = meta.get("continentes", []) or []
            paises = meta.get("paises", []) or []
            puertos = meta.get("puertos", []) or []
            servicios = meta.get("servicios", []) or []

            years = [str(y) for y in years if y is not None]

            self._combos["Año desde"]["values"] = years
            self._combos["Año hasta"]["values"] = years
            self._combos["Continente"]["values"] = [c for c in continentes if c]
            self._combos["País"]["values"] = [p for p in paises if p]
            self._combos["Puerto"]["values"] = [p for p in puertos if p]
            self._combos["Servicio"]["values"] = [s for s in servicios if s]

        except Exception:
            return

    # =========================================================
    # PAGINACIÓN
    # =========================================================
    def _render_page(self):

        # ---------------- LIMPIAR TABLA ----------------
        self.tree.delete(*self.tree.get_children())

        # ---------------- SIN DATA ----------------
        if not self._data_all:
            self._total_pages = 1
            self.lbl_page.config(text="Página 0 de 0")
            return

        # ---------------- TOTAL REGISTROS ----------------
        total = len(self._data_all)

        # ---------------- TOTAL PÁGINAS ----------------
        self._total_pages = max(
            1,
            math.ceil(total / self.PAGE_SIZE)
        )

        # ---------------- RANGO DE REGISTROS ----------------
        start = (self._page - 1) * self.PAGE_SIZE
        end = start + self.PAGE_SIZE

        # ---------------- INSERT FILAS ----------------
        for r in self._data_all[start:end]:

            try:
                servicio = (r.get("servicio") or "").strip()
            except Exception:
                servicio = ""

            try:
                cantidad_servicios = int(r.get("cantidad_servicios") or 0)
            except Exception:
                cantidad_servicios = 0

            try:
                revenue_neto_total = float(r.get("revenue_neto_total") or 0)
            except Exception:
                revenue_neto_total = 0.0

            try:
                costo_total = float(r.get("costo_total") or 0)
            except Exception:
                costo_total = 0.0

            try:
                margen_bruto = float(r.get("margen_bruto") or 0)
            except Exception:
                margen_bruto = 0.0

            try:
                margen_neto = float(r.get("margen_neto") or 0)
            except Exception:
                margen_neto = 0.0

            try:
                margen_neto_pct = float(r.get("margen_neto_pct") or 0)
            except Exception:
                margen_neto_pct = 0.0

            self.tree.insert(
                "",
                "end",
                values=(
                    servicio,
                    cantidad_servicios,
                    f"{revenue_neto_total:,.2f}",
                    f"{costo_total:,.2f}",
                    f"{margen_bruto:,.2f}",
                    f"{margen_neto:,.2f}",
                    f"{margen_neto_pct:,.2f}%"
                )
            )

        # ---------------- LABEL PÁGINA ----------------
        self.lbl_page.config(
            text=f"Página {self._page} de {self._total_pages}"
        )

    def _next_page(self):
        if self._page < self._total_pages:
            self._page += 1
            self._render_page()

    def _prev_page(self):
        if self._page > 1:
            self._page -= 1
            self._render_page()

    # =========================================================
    # ACTIONS
    # =========================================================
    def _limpiar(self):
        self.year_from_var.set("")
        self.year_to_var.set("")
        self.quarter_var.set("")
        self.continente_var.set("")
        self.pais_var.set("")
        self.puerto_var.set("")
        self.servicio_var.set("")
        self.year_mode_var.set("RANGO")
        self._on_year_mode_change()

        self._data_all = []
        self._page = 1
        self._total_pages = 1
        self.tree.delete(*self.tree.get_children())
        self.lbl_page.config(text="Página 0 de 0")

        self._kpi_vars["servicios"].set("0")
        self._kpi_vars["facturado"].set("0.00")
        self._kpi_vars["costos"].set("0.00")
        self._kpi_vars["margen_bruto"].set("0.00")
        self._kpi_vars["margen_neto"].set("0.00")
        self._kpi_vars["rentabilidad"].set("0.00 %")

    # =========================================================
    # POPUP — SERVICIOS NO OFRECIDOS
    # =========================================================
    def _abrir_no_ofrecidos_popup(self):
        try:
            filters = self._build_filters_payload()

            resp = get_comercial_servicios_no_ofrecidos_api(
                year_from=filters.get("year_from"),
                year_to=filters.get("year_to"),
                continente=filters.get("continente"),
                pais=filters.get("pais"),
                puerto=filters.get("puerto")
            ) or {}

            data = resp.get("data", []) or []
            total = resp.get("total_no_ofrecidos", len(data))

            parent = self.winfo_toplevel()

            try:
                PopupServiciosNoOfrecidos(
                    parent,
                    data=data,
                    total=total,
                    filters=resp.get("filters", {}),
                    usuario=self.usuario,
                    rol=self.rol
                )
            except TypeError:
                PopupServiciosNoOfrecidos(parent, data)

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir 'Servicios NO Ofrecidos'.\n{e}")

    # =========================================================
    # EXPORT
    # =========================================================
    def _export(self, fmt):
        if not self._data_all:
            messagebox.showinfo("Exportar", "No hay datos para exportar.")
            return

        try:
            if fmt == "csv":
                path = filedialog.asksaveasfilename(defaultextension=".csv")
                if not path:
                    return
                with open(path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=self._data_all[0].keys())
                    writer.writeheader()
                    writer.writerows(self._data_all)
                messagebox.showinfo("Exportar", "CSV exportado correctamente.")
                return

            if fmt == "xlsx":
                path = filedialog.asksaveasfilename(defaultextension=".xlsx")
                if not path:
                    return
                pd.DataFrame(self._data_all).to_excel(path, index=False)
                messagebox.showinfo("Exportar", "Excel exportado correctamente.")
                return

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo exportar.\n{e}")


    # =========================================================
    # POPUP — COSTOS POR SURVEYOR (PARETO 80/20)
    # =========================================================
    def _abrir_costos_surveyor_popup(self):
        try:
            filters = self._build_filters_payload()

            year = filters.get("year_from") or filters.get("year_to")
            operacion = self.servicio_var.get() or None

            resp = get_comercial_costos_surveyor_pareto_api(
                year=year,
                operacion=operacion
            ) or {}

            data = resp.get("data", []) or []

            parent = self.winfo_toplevel()

            PopupCostosSurveyor(
                parent,
                data=data,
                filters=resp.get("filters", {})
            )

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo abrir 'Costos por Surveyor'.\n{e}"
            )


    # =========================================================
    # NAV
    # =========================================================
    def _volver(self):
        if callable(self.on_back):
            self.on_back()

    # Alias por compatibilidad con tu botón header (si lo cambias)
    def _volver_(self):
        self._volver()
