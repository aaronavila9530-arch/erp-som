import tkinter as tk
from tkinter import ttk, messagebox

from Modulos.Finanzas.sections.BankReconciliation.popups.popup_view_applied import PopupViewApplied
from Modulos.Finanzas.sections.BankReconciliation.popups.popup_registrar_pago_manual import (
    PopupRegistrarPagoManual
)
from api_client import (
    get_bank_reconciliation_api,
    get_clientes_finanzas_api
)


class BankReconciliationUI(tk.Frame):

    def __init__(self, parent):
        super().__init__(parent)

        # ============================
        # Estado interno
        # ============================
        self.page = 1
        self.page_size = 50
        self.total_pages = 1

        self.table = None
        self.frm_table = None
        self.current_data = {}

        # 👉 mapa texto combobox → codigo_cliente
        self.clientes_map = {}

        self._build_filters()
        self._build_actions()
        self._build_pagination()

        self._load_clientes()

    # =========================================================
    # FILTROS
    # =========================================================
    def _build_filters(self):

        frm_filters = ttk.LabelFrame(self, text="Filtros")
        frm_filters.pack(fill="x", padx=10, pady=5)

        frm_filters.columnconfigure(1, weight=1)
        frm_filters.columnconfigure(3, weight=1)

        ttk.Label(frm_filters, text="Cliente").grid(
            row=0, column=0, padx=5, pady=5, sticky="w"
        )
        self.cmb_cliente = ttk.Combobox(frm_filters, width=35, state="readonly")
        self.cmb_cliente.grid(
            row=0, column=1, padx=5, pady=5, sticky="ew"
        )

        ttk.Label(frm_filters, text="Referencia Bancaria / Comprobante").grid(
            row=0, column=2, padx=5, pady=5, sticky="w"
        )
        self.txt_referencia = ttk.Entry(frm_filters)
        self.txt_referencia.grid(
            row=0, column=3, padx=5, pady=5, sticky="ew"
        )

        self.var_ver_todos = tk.BooleanVar()
        ttk.Checkbutton(
            frm_filters,
            text="Ver todos",
            variable=self.var_ver_todos
        ).grid(row=0, column=4, padx=10, pady=5)

    def _load_clientes(self):
        """
        Carga clientes desde clientes (codigo + nombre)
        """
        try:
            clientes = get_clientes_finanzas_api()
            valores = []

            for c in clientes:
                texto = f"{c['codigo']} - {c['nombre']}"
                valores.append(texto)
                self.clientes_map[texto] = c["codigo"]

            self.cmb_cliente["values"] = valores

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudieron cargar los clientes:\n{e}"
            )

    # =========================================================
    # BOTONES
    # =========================================================
    def _build_actions(self):

        frm_actions = ttk.Frame(self)
        frm_actions.pack(fill="x", padx=10, pady=5)

        ttk.Button(
            frm_actions,
            text="🔍 Buscar",
            command=self._on_search
        ).pack(side="left", padx=5)

        ttk.Button(
            frm_actions,
            text="📄 Ver Detalle del Pago",
            command=self._on_view_applied
        ).pack(side="left", padx=5)

        ttk.Button(
            frm_actions,
            text="➕ Registrar Pago Manual",
            command=self._on_registrar_pago_manual
        ).pack(side="left", padx=15)

        ttk.Button(
            frm_actions,
            text="🔄 Limpiar",
            command=self._on_clear
        ).pack(side="left")

    # =========================================================
    # TABLA
    # =========================================================
    def _build_table(self):

        self.frm_table = ttk.Frame(self)
        self.frm_table.pack(fill="both", expand=True, padx=10, pady=5)

        columns = (
            "banco", "fecha_pago", "cliente", "documento",
            "referencia", "tipo", "monto_recibido",
            "monto_aplicado", "saldo", "estado"
        )

        self.table = ttk.Treeview(
            self.frm_table,
            columns=columns,
            show="headings"
        )

        vsb = ttk.Scrollbar(
            self.frm_table, orient="vertical", command=self.table.yview
        )
        hsb = ttk.Scrollbar(
            self.frm_table, orient="horizontal", command=self.table.xview
        )
        self.table.configure(
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set
        )

        self.table.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        self.frm_table.rowconfigure(0, weight=1)
        self.frm_table.columnconfigure(0, weight=1)

        headers = {
            "banco": "Banco",
            "fecha_pago": "Fecha de Pago",
            "cliente": "Cliente",
            "documento": "Documento",
            "referencia": "Referencia",
            "tipo": "Tipo",
            "monto_recibido": "Monto Recibido",
            "monto_aplicado": "Monto Aplicado",
            "saldo": "Saldo",
            "estado": "Estado"
        }

        for col, text in headers.items():
            self.table.heading(col, text=text)
            self.table.column(col, width=140, anchor="center")

        self.table.bind("<Double-1>", self._on_double_click)

    # =========================================================
    # PAGINACIÓN
    # =========================================================
    def _build_pagination(self):

        frm_pagination = ttk.Frame(self)
        frm_pagination.pack(fill="x", padx=10, pady=5)

        ttk.Button(frm_pagination, text="◀ Anterior").pack(side="left")

        self.lbl_page = ttk.Label(
            frm_pagination, text="Página 1 de 1"
        )
        self.lbl_page.pack(side="left", padx=10)

        ttk.Button(frm_pagination, text="Siguiente ▶").pack(side="left")

    # =========================================================
    # EVENTOS
    # =========================================================
    def _on_search(self):

        codigo_cliente = None
        if self.cmb_cliente.get():
            codigo_cliente = self.clientes_map.get(self.cmb_cliente.get())

        referencia = self.txt_referencia.get().strip()
        ver_todos = self.var_ver_todos.get()

        if not ver_todos and not codigo_cliente and not referencia:
            messagebox.showwarning(
                "Filtros requeridos",
                "Seleccione un cliente, ingrese una referencia o marque 'Ver todos'."
            )
            return

        if not self.table:
            self._build_table()

        self.table.delete(*self.table.get_children())
        self.current_data.clear()

        try:
            resp = get_bank_reconciliation_api(
                codigo_cliente=codigo_cliente,
                referencia=referencia or None,
                ver_todos=ver_todos,
                page=self.page,
                page_size=self.page_size
            )

            data = resp.get("data", [])

            for row in data:
                self.current_data[row["id"]] = row

                self.table.insert(
                    "",
                    "end",
                    iid=row["id"],
                    values=(
                        row["banco"],
                        row["fecha_pago"],
                        row["nombre_cliente"],
                        row["numero_documento"],
                        row["referencia"],
                        row["tipo_aplicacion"],
                        f"{row['monto_pagado']:,.2f}",
                        f"{row.get('monto_aplicado', 0):,.2f}",
                        f"{row.get('saldo', row['monto_pagado']):,.2f}",
                        row.get("estado", "APLICADO")
                    )
                )

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo cargar la información:\n{e}"
            )

    def _on_view_applied(self):

        if not self.table:
            return

        selected = self.table.selection()
        if not selected:
            messagebox.showwarning(
                "Selección requerida",
                "Seleccione un pago para ver el detalle."
            )
            return

        payment_iid = selected[0]

        payment_data = None

        # 1️⃣ Intentar como string (incoming_payments)
        if payment_iid in self.current_data:
            payment_data = self.current_data.get(payment_iid)

        # 2️⃣ Fallback: intentar como int (cash_app)
        else:
            try:
                payment_id_int = int(payment_iid)
                payment_data = self.current_data.get(payment_id_int)
            except ValueError:
                payment_data = None

        if not payment_data:
            messagebox.showerror(
                "Error",
                "No se pudo obtener la información del pago."
            )
            return

        PopupViewApplied(self, payment_data)

    def _on_registrar_pago_manual(self):
        PopupRegistrarPagoManual(
            self,
            on_success=self._on_search  # refresca tabla automáticamente
        )

    def _on_double_click(self, event):
        self._on_view_applied()

    def _on_clear(self):

        self.cmb_cliente.set("")
        self.txt_referencia.delete(0, "end")
        self.var_ver_todos.set(False)

        if self.table:
            self.frm_table.destroy()
            self.table = None
            self.current_data.clear()
