import tkinter as tk
from tkinter import ttk, messagebox

from api_client import (
    get_clientes_api,
    get_surveyores_nombres_api,
    get_serviciosmd_api,
)

from Modulos.Servicios.popup_servicio import PopupServicio
from Modulos.Servicios.vista_servicios import VistaServicios


class ServiciosUI(tk.Frame):

    def __init__(self, parent):
        super().__init__(parent, bg="white")

        # ============================================================
        # CONTENEDOR PRINCIPAL (IGUAL A MASTER DATA)
        # ============================================================
        self.content = tk.Frame(self, bg="white")
        self.content.pack(fill="both", expand=True)

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

        # STATUS
        tk.Label(filtro, text="Status:", bg="white").grid(row=0, column=0, sticky="w")
        self.cmb_status = ttk.Combobox(
            filtro,
            width=15,
            state="readonly",
            values=["Todos", "Por confirmar", "Confirmado", "Cancelado", "Finalizado"]
        )
        self.cmb_status.current(0)
        self.cmb_status.grid(row=1, column=0, padx=5)

        # AÑO
        tk.Label(filtro, text="Año:", bg="white").grid(row=0, column=1, sticky="w")
        self.cmb_anio = ttk.Combobox(
            filtro,
            width=15,
            state="readonly",
            values=[str(a) for a in range(2020, 2031)]
        )
        self.cmb_anio.grid(row=1, column=1, padx=5)

        # CLIENTE
        tk.Label(filtro, text="Cliente:", bg="white").grid(row=0, column=2, sticky="w")
        self.cmb_cliente = ttk.Combobox(filtro, width=20, state="readonly")
        self.cmb_cliente.grid(row=1, column=2, padx=5)
        self.cmb_cliente.bind("<Button-1>", self.load_clientes)

        # OPERACIÓN
        tk.Label(filtro, text="Operación:", bg="white").grid(row=0, column=3, sticky="w")
        self.cmb_operacion = ttk.Combobox(filtro, width=20, state="readonly")
        self.cmb_operacion.grid(row=1, column=3, padx=5)
        self.cmb_operacion.bind("<Button-1>", self.load_operaciones)

        # SURVEYOR
        tk.Label(filtro, text="Surveyor:", bg="white").grid(row=0, column=4, sticky="w")
        self.cmb_surveyor = ttk.Combobox(filtro, width=20, state="readonly")
        self.cmb_surveyor.grid(row=1, column=4, padx=5)
        self.cmb_surveyor.bind("<Button-1>", self.load_surveyores)

        # BOTÓN BUSCAR
        ttk.Button(
            filtro,
            text="Buscar",
            command=self.on_search
        ).grid(row=1, column=5, padx=10)

        # BOTÓN + SERVICIO (MISMA POSICIÓN QUE MASTER DATA)
        acciones = tk.Frame(self.content, bg="white")
        acciones.pack(fill="x", padx=15, pady=10)

        ttk.Button(
            acciones,
            text="+ Servicio",
            width=20,
            command=self.add_servicio
        ).pack(side="left")

    # ============================================================
    # BUSCAR → MOSTRAR TABLA
    # ============================================================
    def on_search(self):
        filtros = {
            "status": self.cmb_status.get().strip(),
            "anio": self.cmb_anio.get().strip(),
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
    # POPUP NUEVO SERVICIO
    # ============================================================
    def add_servicio(self):
        PopupServicio(self, self.on_search)

    # ============================================================
    # CARGA SAP-LIKE (ON DEMAND)
    # ============================================================
    def load_clientes(self, *_):
        if not hasattr(self, "_clientes_loaded"):
            self.cmb_cliente.config(values=get_clientes_api())
            self._clientes_loaded = True

    def load_operaciones(self, *_):
        if not hasattr(self, "_operaciones_loaded"):
            self.cmb_operacion.config(values=get_serviciosmd_api())
            self._operaciones_loaded = True

    def load_surveyores(self, *_):
        if not hasattr(self, "_surveyores_loaded"):
            self.cmb_surveyor.config(values=get_surveyores_nombres_api())
            self._surveyores_loaded = True
