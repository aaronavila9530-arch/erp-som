import tkinter as tk
from tkinter import ttk, messagebox
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
        for flag in ("_status_loaded", "_anios_loaded", "_surveyores_loaded", "_clientes_loaded", "_operaciones_loaded"):
            if hasattr(self, flag):
                delattr(self, flag)
        self._filtros_servicios = None
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
        self._load_combo("_status_loaded", self.cmb_status,
                         lambda: self._load_filtros_servicios().get("status", []))

    def load_anios(self):
        self._load_combo("_anios_loaded", self.cmb_anio,
                         lambda: [str(y) for y in self._load_filtros_servicios().get("year", [])])

    def load_surveyores(self):
        self._load_combo("_surveyores_loaded", self.cmb_surveyor,
                         lambda: self._load_filtros_servicios().get("surveyor", []))

    # ============================================================
    # CATÁLOGOS EXISTENTES (LAZY)
    # ============================================================
    def load_clientes(self):
        def names():
            raw = get_clientes_api()
            rows = raw.get("data", []) if isinstance(raw, dict) else raw or []
            values = []
            for row in rows:
                name = (row.get("nombrecomercial") or row.get("nombrejuridico")
                        or row.get("NombreComercial") or row.get("NombreJuridico")
                        or row.get("codigo") or row.get("Codigo") or ""
                        ) if isinstance(row, dict) else str(row)
                if name:
                    values.append(name)
            return values
        self._load_combo("_clientes_loaded", self.cmb_cliente, names)

    def load_operaciones(self):
        self._load_combo("_operaciones_loaded", self.cmb_operacion, get_serviciosmd_api)

    def _load_combo(self, flag, combo, loader):
        if hasattr(self, flag):
            return
        try:
            combo.config(values=loader())
        except Exception as exc:
            messagebox.showerror("Servicios", f"No se pudo cargar el filtro.\n{exc}", parent=self)
            return
        setattr(self, flag, True)
