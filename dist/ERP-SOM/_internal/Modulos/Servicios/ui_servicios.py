import tkinter as tk
from tkinter import ttk
from datetime import date

from api_client import (
    get_clientes_api,
    get_serviciosmd_api,
    get_filtros_servicios_api,
)

from Modulos.Servicios.popup_servicio import PopupServicio
from Modulos.Servicios.vista_servicios import VistaServicios


class ServiciosUI(tk.Frame):

    def __init__(self, parent):
        super().__init__(parent, bg="white")

        # ============================================================
        # CONTENEDOR PRINCIPAL
        # ============================================================
        self.content = tk.Frame(self, bg="white")
        self.content.pack(fill="both", expand=True)

        # Cache de filtros (se llena SOLO cuando se necesite)
        self._filtros_servicios = None

        self._build_filtros()

    # ============================================================
    # FILTROS
    # ============================================================
    def _build_filtros(self):
        for w in self.content.winfo_children():
            w.destroy()

        lbl_buscar = tk.Label(
            self.content,
            text="Buscar",
            bg="white",
            fg="black",
            font=("Segoe UI", 10, "bold")
        )
        lbl_buscar.pack(anchor="w", padx=15, pady=(10, 0))

        filtro = tk.Frame(self.content, bg="white")
        filtro.pack(fill="x", padx=15, pady=5)

        # ----------------------------
        # STATUS (desde BD - LAZY)
        # ----------------------------
        tk.Label(filtro, text="Status:", bg="white").grid(row=0, column=0, sticky="w")
        self.cmb_status = ttk.Combobox(
            filtro,
            width=15,
            state="readonly",
            postcommand=self.load_status
        )
        self.cmb_status.grid(row=1, column=0, padx=5)

        # ----------------------------
        # AÑO (desde num_informe - LAZY)
        # ----------------------------
        tk.Label(filtro, text="Año:", bg="white").grid(row=0, column=1, sticky="w")
        self.cmb_anio = ttk.Combobox(
            filtro,
            width=15,
            state="readonly",
            postcommand=self.load_anios
        )
        self.cmb_anio.grid(row=1, column=1, padx=5)

        # ----------------------------
        # CLIENTE (catálogo existente - LAZY)
        # ----------------------------
        tk.Label(filtro, text="Cliente:", bg="white").grid(row=0, column=2, sticky="w")
        self.cmb_cliente = ttk.Combobox(
            filtro,
            width=20,
            state="readonly",
            postcommand=self.load_clientes
        )
        self.cmb_cliente.grid(row=1, column=2, padx=5)

        # ----------------------------
        # OPERACIÓN (catálogo existente - LAZY)
        # ----------------------------
        tk.Label(filtro, text="Operación:", bg="white").grid(row=0, column=3, sticky="w")
        self.cmb_operacion = ttk.Combobox(
            filtro,
            width=20,
            state="readonly",
            postcommand=self.load_operaciones
        )
        self.cmb_operacion.grid(row=1, column=3, padx=5)

        # ----------------------------
        # SURVEYOR (desde servicios - LAZY)
        # ----------------------------
        tk.Label(filtro, text="Surveyor:", bg="white").grid(row=0, column=4, sticky="w")
        self.cmb_surveyor = ttk.Combobox(
            filtro,
            width=20,
            state="readonly",
            postcommand=self.load_surveyores
        )
        self.cmb_surveyor.grid(row=1, column=4, padx=5)

        ttk.Button(
            filtro,
            text="Buscar",
            command=self.on_search
        ).grid(row=1, column=5, padx=10)

        acciones = tk.Frame(self.content, bg="white")
        acciones.pack(fill="x", padx=15, pady=10)

        ttk.Button(
            acciones,
            text="+ Servicio",
            width=20,
            command=self.add_servicio
        ).pack(side="left")

    # ============================================================
    # BUSCAR → API
    # ============================================================
    def on_search(self):

        status = self.cmb_status.get().strip() or None

        year_raw = self.cmb_anio.get().strip()
        year = int(year_raw) if year_raw.isdigit() else None

        filtros = {
            "status": status,
            "year": year,
            "cliente": self.cmb_cliente.get().strip(),
            "operacion": self.cmb_operacion.get().strip(),
            "surveyor": self.cmb_surveyor.get().strip(),
        }

        for w in self.content.winfo_children():
            w.destroy()

        VistaServicios(
            self.content,
            filtros,
            on_back=self._build_filtros
        ).pack(fill="both", expand=True)

    # ============================================================
    # NUEVO SERVICIO
    # ============================================================
    def add_servicio(self):
        PopupServicio(self, self.on_search)

    # ============================================================
    # FILTROS DESDE SERVICIOS (LAZY + CACHE)
    # ============================================================
    def _load_filtros_servicios(self):
        if self._filtros_servicios is None:
            self._filtros_servicios = get_filtros_servicios_api()
        return self._filtros_servicios

    def load_status(self):
        if not hasattr(self, "_status_loaded"):
            filtros = self._load_filtros_servicios()
            self.cmb_status.config(values=filtros.get("status", []))
            self._status_loaded = True

    def load_anios(self):
        if not hasattr(self, "_anios_loaded"):
            filtros = self._load_filtros_servicios()
            anios = [str(y) for y in filtros.get("year", [])]
            self.cmb_anio.config(values=anios)
            self._anios_loaded = True

    def load_surveyores(self):
        if not hasattr(self, "_surveyores_loaded"):
            filtros = self._load_filtros_servicios()
            self.cmb_surveyor.config(values=filtros.get("surveyor", []))
            self._surveyores_loaded = True

    # ============================================================
    # CATÁLOGOS EXISTENTES (LAZY)
    # ============================================================
    def load_clientes(self):
        if not hasattr(self, "_clientes_loaded"):
            self.cmb_cliente.config(values=get_clientes_api())
            self._clientes_loaded = True

    def load_operaciones(self):
        if not hasattr(self, "_operaciones_loaded"):
            self.cmb_operacion.config(values=get_serviciosmd_api())
            self._operaciones_loaded = True
