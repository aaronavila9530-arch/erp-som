import tkinter as tk
from tkinter import ttk, messagebox
import math

from api_client import get_comercial_board_api
from Modulos.Comercial.comercial_client_analytics_ui import ComercialClientAnalyticsUI
from Modulos.Comercial.comercial_ports_analytics_ui import ComercialPortsAnalyticsUI
from Modulos.Comercial.comercial_servicios_analytics_ui import ComercialServiciosAnalyticsUI
from Modulos.Comercial.comercial_precios_ui import ComercialPreciosUI
from Modulos.Comercial.comercial_cotizaciones_ui import ComercialCotizacionesUI
from Modulos.Comercial.date_utils import format_comercial_row_dates, parse_comercial_date


class ComercialHomeUI(ttk.Frame):
    """
    HOME COMERCIAL — PIZARRA OPERATIVA
    """

    PAGE_SIZE = 50

    def __init__(self, parent, usuario=None, rol=None, callbacks=None):
        super().__init__(parent)

        self.parent = parent
        self.usuario = usuario
        self.rol = (rol or "").lower()
        self.callbacks = callbacks or {}
        self._ensure_internal_callbacks()

        self._data_all = []
        self._page = 1
        self._years_loaded = False

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

        header = ttk.Frame(self)
        header.pack(fill="x", padx=20, pady=(15, 10))

        ttk.Label(
            header,
            text="Comercial — Pizarra Operativa",
            font=("Segoe UI", 15, "bold")
        ).pack(side="left")

        # ---------------------------------------------------------
        # RBAC LOCAL — NAV COMERCIAL
        # Surveyors SOLO pueden ver el Home y usar filtros/búsqueda
        # ---------------------------------------------------------

        usuario = (self.usuario or "").lower()

        if usuario not in ("surveyor01", "surveyor02", "surveyor03"):

            nav = ttk.Frame(header)
            nav.pack(side="right")

            ttk.Button(
                nav,
                text="Clientes",
                command=self._open("open_clients")
            ).pack(side="left", padx=4)

            ttk.Button(
                nav,
                text="Puertos",
                command=self._open("open_ports")
            ).pack(side="left", padx=4)

            ttk.Button(
                nav,
                text="Servicios",
                command=self._open("open_services")
            ).pack(side="left", padx=4)

            ttk.Button(
                nav,
                text="Cotizaciones",
                command=self._open("open_quotations")
            ).pack(side="left", padx=4)

            ttk.Button(
                nav,
                text="Precios",
                command=self._open("open_pricing")
            ).pack(side="left", padx=4)

        filtros = ttk.LabelFrame(self, text="Filtros")
        filtros.pack(fill="x", padx=20, pady=(0, 10))

        self.f_cliente = tk.StringVar()
        self.f_pais = tk.StringVar()
        self.f_puerto = tk.StringVar()
        self.f_surveyor = tk.StringVar()
        self.f_year = tk.StringVar()

        self.f_estado_confirmado = tk.BooleanVar(value=True)
        self.f_estado_por_confirmar = tk.BooleanVar(value=True)
        self.f_estado_finalizado = tk.BooleanVar(value=False)
        self.f_estado_cancelado = tk.BooleanVar(value=False)

        ttk.Label(filtros, text="Cliente").grid(row=0, column=0, padx=6, pady=6, sticky="w")
        self.cb_cliente = ttk.Combobox(filtros, textvariable=self.f_cliente, width=24)
        self.cb_cliente.grid(row=0, column=1, pady=6)

        ttk.Label(filtros, text="País").grid(row=0, column=2, padx=6, pady=6, sticky="w")
        self.cb_pais = ttk.Combobox(filtros, textvariable=self.f_pais, width=18)
        self.cb_pais.grid(row=0, column=3, pady=6)

        ttk.Label(filtros, text="Puerto").grid(row=0, column=4, padx=6, pady=6, sticky="w")
        self.cb_puerto = ttk.Combobox(filtros, textvariable=self.f_puerto, width=18)
        self.cb_puerto.grid(row=0, column=5, pady=6)

        ttk.Label(filtros, text="Surveyor").grid(row=0, column=6, padx=6, pady=6, sticky="w")
        self.cb_surveyor = ttk.Combobox(filtros, textvariable=self.f_surveyor, width=18)
        self.cb_surveyor.grid(row=0, column=7, pady=6)

        ttk.Label(filtros, text="Año").grid(row=0, column=8, padx=6, pady=6, sticky="w")
        self.cb_year = ttk.Combobox(filtros, textvariable=self.f_year, width=10, state="readonly")
        self.cb_year.grid(row=0, column=9, pady=6)
        self.cb_year.bind("<Button-1>", self._load_years_from_api)

        ttk.Checkbutton(filtros, text="Confirmado", variable=self.f_estado_confirmado).grid(row=1, column=0, padx=6, sticky="w")
        ttk.Checkbutton(filtros, text="En Operación", variable=self.f_estado_por_confirmar).grid(row=1, column=1, sticky="w")
        ttk.Checkbutton(filtros, text="Finalizado", variable=self.f_estado_finalizado).grid(row=1, column=2, sticky="w")
        ttk.Checkbutton(filtros, text="Cancelado", variable=self.f_estado_cancelado).grid(row=1, column=3, sticky="w")

        ttk.Button(filtros, text="Buscar", command=self._search).grid(row=1, column=8, padx=6)
        ttk.Button(filtros, text="Limpiar", command=self._clear).grid(row=1, column=9, padx=6)

        # =====================================================
        # TABLA (ALTURA REAL + SCROLL VISIBLE)
        # =====================================================
        frame_tabla = ttk.Frame(self)
        frame_tabla.pack(fill="both", expand=True, padx=20)

        self.columnas = [
            "consec", "tipo", "estado", "num_informe", "buque_contenedor",
            "cliente", "operacion", "detalle", "surveyor",
            "continente", "pais", "puerto",
            "fecha_inicio", "hora_inicio",
            "fecha_fin", "hora_fin",
            "demoras", "duracion"
        ]

        self.tabla = ttk.Treeview(
            frame_tabla,
            columns=self.columnas,
            show="headings"
        )

        for col in self.columnas:
            self.tabla.heading(col, text=col.replace("_", " ").upper())
            self.tabla.column(col, width=140, anchor="w")

        self.tabla.pack(side="left", fill="both", expand=True)

        vsb = ttk.Scrollbar(frame_tabla, orient="vertical", command=self.tabla.yview)
        vsb.pack(side="right", fill="y")

        hsb = ttk.Scrollbar(self, orient="horizontal", command=self.tabla.xview)
        hsb.pack(fill="x", padx=20, pady=(0, 5))

        self.tabla.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        pager = ttk.Frame(self)
        pager.pack(fill="x", padx=20, pady=(0, 10))

        self.lbl_page = ttk.Label(pager, text="Página 0 de 0")
        self.lbl_page.pack(side="left")

        ttk.Button(pager, text="◀ Anterior", command=self._prev_page).pack(side="right", padx=4)
        ttk.Button(pager, text="Siguiente ▶", command=self._next_page).pack(side="right")

    # =========================================================
    # HELPERS
    # =========================================================
    def _format_duration(self, minutes):
        try:
            m = int(minutes)
        except Exception:
            return ""
        d, rem = divmod(m, 1440)
        h, m = divmod(rem, 60)
        return f"{d}D {h}H {m}M"

    # =========================================================
    # AÑOS DESDE DB (REAL, TODOS)
    # =========================================================
    def _load_years_from_api(self, event=None):

        if self._years_loaded:
            return

        try:

            data = []

            # ---------------------------------------------
            # CARGAR TODOS LOS ESTADOS
            # ---------------------------------------------
            for estados in (["FINALIZADO"], ["Confirmado"], ["En Operación"]):
                try:
                    resp = get_comercial_board_api(estados=estados) or []
                    data.extend(resp)
                except Exception:
                    continue

            # ---------------------------------------------
            # EXTRAER AÑOS (BLINDADO)
            # ---------------------------------------------
            years = set()

            for r in data:

                if not isinstance(r, dict):
                    continue

                fecha = r.get("fecha_inicio")

                if not fecha:
                    continue

                parsed = parse_comercial_date(fecha)
                if parsed:
                    years.add(parsed.year)

            # ---------------------------------------------
            # ORDENAR DESCENDENTE (AÑO MÁS RECIENTE PRIMERO)
            # ---------------------------------------------
            years = sorted(years, reverse=True)

            self.cb_year["values"] = years
            self._years_loaded = True

        except Exception:
            return

    # =========================================================
    # DATA
    # =========================================================
    def _build_filters(self):

        estados = []
        if self.f_estado_confirmado.get():
            estados.append("Confirmado")
        if self.f_estado_por_confirmar.get():
            estados.append("En Operación")
        if self.f_estado_finalizado.get():
            estados.append("FINALIZADO")
        if self.f_estado_cancelado.get():
            estados.append("Cancelado")

        year = self.f_year.get().strip()
        year = int(year) if year.isdigit() else None

        return {
            "cliente": self.f_cliente.get().strip() or None,
            "pais": self.f_pais.get().strip() or None,
            "puerto": self.f_puerto.get().strip() or None,
            "surveyor": self.f_surveyor.get().strip() or None,
            "estados": estados or None,
            "year": year
        }

    def _search(self):

        filtros = self._build_filters()

        try:
            self._data_all = get_comercial_board_api(**filtros) or []
        except Exception as e:
            messagebox.showerror("Comercial", str(e))
            return

        # -----------------------------------------------------
        # ORDENAR POR CONSEC (MAYOR → MENOR)
        # -----------------------------------------------------
        try:
            self._data_all.sort(
                key=lambda r: int((r or {}).get("consec") or 0),
                reverse=True
            )
        except Exception:
            pass

        self._refresh_comboboxes()
        self._page = 1
        self._render_page()

    def _refresh_comboboxes(self):

        def uniq(col):
            return sorted({r.get(col) for r in self._data_all if isinstance(r, dict) and r.get(col)})

        self.cb_cliente["values"] = uniq("cliente")
        self.cb_pais["values"] = uniq("pais")
        self.cb_puerto["values"] = uniq("puerto")
        self.cb_surveyor["values"] = uniq("surveyor")

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
            r["duracion"] = self._format_duration(r.get("duracion"))
            self.tabla.insert("", "end", values=[r.get(c, "") for c in self.columnas])

        self.lbl_page.config(text=f"Página {self._page} de {total_pages}")

    def _next_page(self):
        if self._page * self.PAGE_SIZE < len(self._data_all):
            self._page += 1
            self._render_page()

    def _prev_page(self):
        if self._page > 1:
            self._page -= 1
            self._render_page()

    def _clear(self):

        self.f_cliente.set("")
        self.f_pais.set("")
        self.f_puerto.set("")
        self.f_surveyor.set("")
        self.f_year.set("")

        self.f_estado_confirmado.set(True)
        self.f_estado_por_confirmar.set(True)
        self.f_estado_finalizado.set(False)
        self.f_estado_cancelado.set(False)

        self._data_all = []
        self._page = 1
        self._years_loaded = False

        for i in self.tabla.get_children():
            self.tabla.delete(i)

        self.lbl_page.config(text="Página 0 de 0")


    def _ensure_internal_callbacks(self):
        """
        Define callbacks internos si no vienen desde el contenedor.
        Evita que los botones no hagan nada.
        """
        if "open_clients" not in self.callbacks:
            self.callbacks["open_clients"] = self._open_clients_view

        if "open_ports" not in self.callbacks:
            self.callbacks["open_ports"] = self._open_ports_view

        if "open_services" not in self.callbacks:
            self.callbacks["open_services"] = self._open_services_view

        # ✅ PRECIOS
        if "open_pricing" not in self.callbacks:
            self.callbacks["open_pricing"] = self._open_pricing_view

        # ✅ COTIZACIONES (ESTE ES EL NUEVO)
        if "open_quotations" not in self.callbacks:
            self.callbacks["open_quotations"] = self._open_quotations_view


    def _open_clients_view(self):
        """
        Abre la vista de Analytics por Cliente.
        Reemplaza este frame por el nuevo UI.
        """

        # destruir contenido actual
        for w in self.parent.winfo_children():
            w.destroy()

        ComercialClientAnalyticsUI(
            self.parent,
            usuario=self.usuario,
            rol=self.rol,
            on_back=self._back_to_home
        ).pack(fill="both", expand=True)

    def _open_ports_view(self):
        """
        Abre la vista de Analytics por Puertos.
        """

        # destruir contenido actual
        for w in self.parent.winfo_children():
            w.destroy()

        ComercialPortsAnalyticsUI(
            self.parent,
            usuario=self.usuario,
            rol=self.rol,
            on_back=self._back_to_home
        ).pack(fill="both", expand=True)




    def _back_to_home(self):
        """
        Regresa al Home Comercial.
        """

        for w in self.parent.winfo_children():
            w.destroy()

        self.__class__(
            self.parent,
            usuario=self.usuario,
            rol=self.rol
        ).pack(fill="both", expand=True)

    def _open_services_view(self):
        """
        Abre la vista de Analytics por Servicios.
        """

        # destruir contenido actual
        for w in self.parent.winfo_children():
            w.destroy()

        ComercialServiciosAnalyticsUI(
            self.parent,
            usuario=self.usuario,
            rol=self.rol,
            on_back=self._back_to_home
        ).pack(fill="both", expand=True)


    def _open_pricing_view(self):
        """
        Abre la vista de Precios (Servicios / Cliente / Ubicación).
        """

        # destruir contenido actual
        for w in self.parent.winfo_children():
            w.destroy()

        ComercialPreciosUI(
            self.parent,
            usuario=self.usuario,
            rol=self.rol,
            on_back=self._back_to_home
        ).pack(fill="both", expand=True)

    def _open_quotations_view(self):
        """
        Abre la vista de Cotizaciones Comerciales.
        """

        # destruir contenido actual
        for w in self.parent.winfo_children():
            w.destroy()

        ComercialCotizacionesUI(
            self.parent,
            usuario=self.usuario,
            rol=self.rol,
            on_back=self._back_to_home
        ).pack(fill="both", expand=True)



    # =========================================================
    # NAV
    # =========================================================
    def _open(self, key):
        def _cb():
            fn = self.callbacks.get(key)
            if fn:
                fn()
        return _cb
