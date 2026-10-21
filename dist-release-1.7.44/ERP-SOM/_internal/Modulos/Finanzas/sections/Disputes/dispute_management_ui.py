import tkinter as tk
from tkinter import ttk, messagebox
import requests

from api_client import BASE_URL, get_clientes_finanzas_api
from Modulos.Finanzas.date_utils import to_long_english_date
from Modulos.Finanzas.sections.Disputes.kpi_disputes import DisputesKPIs


class DisputeManagementUI(tk.Frame):

    def __init__(self, parent):
        super().__init__(parent)

        self.page = 1
        self.page_size = 50
        self.data_loaded = False
        self.clientes_map = {}

        self._build_filters()
        self._build_kpis()
        self._build_actions()
        self._build_table()
        self._load_clientes()

    # =====================================================
    # FILTROS
    # =====================================================
    def _build_filters(self):

        frm = tk.Frame(self)
        frm.pack(fill="x", padx=10, pady=5)

        tk.Label(frm, text="Cliente").pack(side="left")

        self.cliente = ttk.Combobox(frm, width=40, state="readonly")
        self.cliente.pack(side="left", padx=5)

        ttk.Button(frm, text="Buscar", command=self._buscar).pack(
            side="left", padx=10
        )

    def _load_clientes(self):

        clientes = get_clientes_finanzas_api()
        self.clientes_map = {c["codigo"]: c["nombre"] for c in clientes}

        self.cliente["values"] = [
            f"{codigo} - {nombre}"
            for codigo, nombre in self.clientes_map.items()
        ]

    # =====================================================
    # KPIs
    # =====================================================
    def _build_kpis(self):

        self.kpis = DisputesKPIs(self)
        self.kpis.pack(fill="x", padx=5, pady=5)

    # =====================================================
    # BOTONES DE ACCIÓN
    # =====================================================
    def _build_actions(self):

        frm = tk.Frame(self)
        frm.pack(fill="x", padx=10, pady=(0, 5))

        ttk.Button(
            frm,
            text="🛠 Gestionar Disputa",
            command=self._open_popup_button
        ).pack(side="left")

    # =====================================================
    # TABLA
    # =====================================================
    def _build_table(self):

        columns = (
            "dispute_case",
            "numero_documento",
            "codigo_cliente",
            "nombre_cliente",
            "fecha_factura",
            "fecha_vencimiento",
            "monto",
            "status",
            "motivo",
            "comentario",
            "buque",
            "operacion",
            "periodo",
            "descripcion",
            "created_at"
        )

        container = tk.Frame(self)
        container.pack(fill="both", expand=True, padx=10, pady=5)

        self.tree = ttk.Treeview(
            container,
            columns=columns,
            show="headings",
            height=18
        )

        headers = {
            "dispute_case": "Dispute",
            "numero_documento": "Documento",
            "codigo_cliente": "Código Cliente",
            "nombre_cliente": "Cliente",
            "fecha_factura": "Fecha Factura",
            "fecha_vencimiento": "Vencimiento",
            "monto": "Monto Factura",
            "status": "Status",
            "motivo": "Motivo",
            "comentario": "Comentario",
            "buque": "Buque / Contenedor",
            "operacion": "Operación",
            "periodo": "Periodo",
            "descripcion": "Descripción Servicio",
            "created_at": "Creado"
        }

        for col, txt in headers.items():
            self.tree.heading(col, text=txt)
            self.tree.column(col, width=160, anchor="w")

        vsb = ttk.Scrollbar(container, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(container, orient="horizontal", command=self.tree.xview)

        self.tree.configure(
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set
        )

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.tree.bind("<Double-1>", self._open_popup_event)

    # =====================================================
    # BUSCAR → /dispute-management
    # =====================================================
    def _buscar(self):

        params = {
            "page": self.page,
            "page_size": self.page_size
        }

        if self.cliente.get():
            params["cliente"] = self.cliente.get().split(" - ")[0]

        try:
            r = requests.get(
                f"{BASE_URL}/dispute-management",
                params=params,
                timeout=20
            )
            r.raise_for_status()
            data = r.json().get("data", [])
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo cargar la gestión de disputas:\n{e}"
            )
            return

        self.tree.delete(*self.tree.get_children())

        for row in data:
            self.tree.insert(
                "",
                "end",
                iid=f"D-{row['dispute_id']}",
                values=(
                    row["dispute_case"],
                    row["numero_documento"],
                    row["codigo_cliente"],
                    row["nombre_cliente"],
                    to_long_english_date(row["fecha_factura"]),
                    to_long_english_date(row["fecha_vencimiento"]),
                    f"{row['monto']:,.2f}",
                    row["status"],                         # ✅ status REAL
                    row.get("motivo", ""),                 # ✅ MOTIVO
                    row.get("comentario", ""),             # ✅ COMENTARIO
                    row.get("buque_contenedor", ""),       # ✅ BUQUE
                    row.get("operacion", ""),              # ✅ OPERACIÓN
                    row.get("periodo_operacion", ""),      # ✅ PERIODO
                    row.get("descripcion_servicio", ""),   # ✅ DESCRIPCIÓN
                    to_long_english_date(row["created_at"])
                )
            )

        self.data_loaded = True
        self.kpis.load_kpis()

    # =====================================================
    # POPUP (BOTÓN)
    # =====================================================
    def _open_popup_button(self):

        selected = self.tree.focus()
        if not selected:
            messagebox.showwarning(
                "Dispute",
                "Seleccione una disputa primero"
            )
            return

        self._open_popup(selected)

    # =====================================================
    # POPUP (DOBLE CLICK)
    # =====================================================
    def _open_popup_event(self, event):

        selected = self.tree.focus()
        if selected:
            self._open_popup(selected)

    def _open_popup(self, iid):

        dispute_id = int(iid.replace("D-", ""))

        from Modulos.Finanzas.sections.Disputes.popups.popup_dispute_management import (
            PopupDisputeManagement
        )

        PopupDisputeManagement(
            self,
            dispute_id=dispute_id,
            on_success=self._buscar
        )
