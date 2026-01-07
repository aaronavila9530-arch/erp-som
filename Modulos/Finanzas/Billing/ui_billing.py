import tkinter as tk
from tkinter import ttk
from datetime import datetime
import requests

from api_client import BASE_URL
from Modulos.Finanzas.Billing.tabla_billing import TablaBilling


class BillingUI(tk.Frame):

    def __init__(self, parent):
        super().__init__(parent)
        self.pack(fill="both", expand=True)

        self.tabla = None
        self._build_filtros()

    # ======================================================
    # FILTROS
    # ======================================================
    def _build_filtros(self):

        filtros = tk.Frame(self)
        filtros.pack(fill="x", padx=10, pady=10)

        self.cliente = tk.StringVar(value="ALL")
        self.fecha_desde = tk.StringVar()
        self.fecha_hasta = tk.StringVar()
        self.tipo_factura = tk.StringVar()
        self.tipo_documento = tk.StringVar()

        # ===================== ROW 0 =====================
        tk.Label(filtros, text="Cliente").grid(row=0, column=0, padx=5, sticky="w")

        self.combo_cliente = ttk.Combobox(
            filtros,
            textvariable=self.cliente,
            state="readonly",
            width=30
        )
        self.combo_cliente.grid(row=0, column=1, padx=5, sticky="w")

        tk.Label(filtros, text="Desde").grid(row=0, column=2, padx=5, sticky="w")
        ttk.Entry(filtros, textvariable=self.fecha_desde, width=12)\
            .grid(row=0, column=3, padx=5, sticky="w")

        tk.Label(filtros, text="Hasta").grid(row=0, column=4, padx=5, sticky="w")
        ttk.Entry(filtros, textvariable=self.fecha_hasta, width=12)\
            .grid(row=0, column=5, padx=5, sticky="w")

        # ===================== ROW 1 =====================
        tk.Label(filtros, text="Tipo Factura").grid(row=1, column=0, padx=5, sticky="w")

        ttk.Combobox(
            filtros,
            textvariable=self.tipo_factura,
            values=["", "MANUAL", "ELECTRONICA"],
            state="readonly",
            width=18
        ).grid(row=1, column=1, padx=5, sticky="w")

        tk.Label(filtros, text="Documento").grid(row=1, column=2, padx=5, sticky="w")

        ttk.Combobox(
            filtros,
            textvariable=self.tipo_documento,
            values=["", "FACTURA", "NOTA_CREDITO"],
            state="readonly",
            width=18
        ).grid(row=1, column=3, padx=5, sticky="w")

        ttk.Button(
            filtros,
            text="🔍 Buscar",
            command=self._buscar
        ).grid(row=1, column=5, padx=10, sticky="e")

        self._cargar_clientes()

    # ======================================================
    # CLIENTES
    # ======================================================
    def _cargar_clientes(self):

        try:
            r = requests.get(
                f"{BASE_URL}/clientes",
                params={"page": 1, "page_size": 500},
                timeout=15
            )
            r.raise_for_status()

            data = r.json().get("data", [])
            clientes = ["ALL"] + sorted(
                c["nombrecomercial"]
                for c in data
                if c.get("nombrecomercial")
            )

            self.combo_cliente["values"] = clientes
            self.combo_cliente.current(0)

        except Exception:
            self.combo_cliente["values"] = ["ALL"]
            self.combo_cliente.current(0)

    # ======================================================
    # BUSCAR
    # ======================================================
    def _buscar(self):

        def to_iso(fecha_str):
            if not fecha_str:
                return None
            try:
                return datetime.strptime(
                    fecha_str.strip(),
                    "%d/%m/%Y"
                ).date().isoformat()
            except ValueError:
                return None

        filtros_raw = {
            "cliente": self.cliente.get(),  # ALL o nombre
            "fecha_desde": to_iso(self.fecha_desde.get()),
            "fecha_hasta": to_iso(self.fecha_hasta.get()),
            "tipo_factura": self.tipo_factura.get(),
            "tipo_documento": self.tipo_documento.get(),
        }

        # ✅ LIMPIAR: no mandar None / ""
        filtros = {
            k: v for k, v in filtros_raw.items()
            if v not in (None, "")
        }

        # (Opcional) si el backend ya trata ALL como vacío
        if filtros.get("cliente", "").upper() == "ALL":
            filtros.pop("cliente", None)

        if self.tabla:
            self.tabla.destroy()

        self.tabla = TablaBilling(self, filtros)
        self.tabla.pack(fill="both", expand=True)
