import tkinter as tk
from tkinter import ttk, messagebox

from api_client import BASE_URL, api_request, sync_collections_from_invoicing_api
from Modulos.Finanzas.sections.Collections.tabla_collections import TablaCollections


class CollectionsUI(tk.Frame):

    def __init__(self, parent, on_back=None):
        super().__init__(parent)

        self.on_back = on_back
        self.tabla = None
        self.kpi_cards = {}

        # estado clientes
        self.clientes_loaded = False

        self._build_ui()

    # ============================================================
    # UI
    # ============================================================
    def _build_ui(self):

        # ================= HEADER =================
        header = tk.Frame(self)
        header.pack(fill="x", padx=15, pady=(10, 5))

        ttk.Button(
            header,
            text="⬅ Volver",
            command=self.on_back if self.on_back else None
        ).pack(side="left")

        tk.Label(
            header,
            text="Collections — Accounts Receivable",
            font=("Segoe UI", 14, "bold")
        ).pack(side="left", padx=15)

        ttk.Button(
            header,
            text="🔄 Sincronizar facturas",
            command=self._sync_collections
        ).pack(side="right")

        # ================= FILTROS =================
        filtros = tk.LabelFrame(self, text="Filtros")
        filtros.pack(fill="x", padx=15, pady=10)

        self.cliente = tk.StringVar(value="ALL")
        self.bucket = tk.StringVar()
        self.estado = tk.StringVar()
        self.disputada = tk.StringVar()

        row = tk.Frame(filtros)
        row.pack(fill="x", padx=10, pady=8)

        # -------- CLIENTE (COMBOBOX LAZY LOAD) --------
        ttk.Label(row, text="Cliente").pack(side="left")

        self.cbo_cliente = ttk.Combobox(
            row,
            textvariable=self.cliente,
            state="readonly",
            width=25
        )
        self.cbo_cliente.pack(side="left", padx=5)
        self.cbo_cliente.bind("<Button-1>", self._load_clientes_collections)

        # -------- AGING --------
        ttk.Label(row, text="Aging").pack(side="left", padx=(15, 0))
        ttk.Combobox(
            row,
            textvariable=self.bucket,
            values=["", "CURRENT", "1-30", "31-60", "61-90", "90+"],
            width=10,
            state="readonly"
        ).pack(side="left", padx=5)

        # -------- ESTADO --------
        ttk.Label(row, text="Estado").pack(side="left", padx=(15, 0))
        ttk.Combobox(
            row,
            textvariable=self.estado,
            values=["", "EMITIDA", "PENDIENTE_PAGO", "PAGADA", "DISPUTADA", "WRITE_OFF"],
            width=15,
            state="readonly"
        ).pack(side="left", padx=5)

        # -------- DISPUTADA --------
        ttk.Label(row, text="Disputada").pack(side="left", padx=(15, 0))
        ttk.Combobox(
            row,
            textvariable=self.disputada,
            values=["", "True", "False"],
            width=8,
            state="readonly"
        ).pack(side="left", padx=5)

        ttk.Button(
            row,
            text="🔍 Buscar",
            command=self._buscar
        ).pack(side="right", padx=10)

        # ================= KPI CONTAINER =================
        self.kpi_container = tk.Frame(self)
        self.kpi_container.pack(fill="x", padx=15, pady=(0, 10))

        # ================= CONTENEDOR TABLA =================
        self.table_container = tk.Frame(self)
        self.table_container.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        self._show_placeholder()

    # ============================================================
    # CLIENTES (LAZY LOAD DESDE COLLECTIONS)
    # ============================================================
    def _load_clientes_collections(self, *_):

        if self.clientes_loaded:
            return

        try:
            # ✅ /collections/search valida page_size <= 200 (si mandas 500 da 422)
            clientes_set = set()

            page = 1
            page_size = 200  # <-- FIX: máximo permitido por tu API

            while True:
                r = api_request(
                    "GET",
                    f"{BASE_URL}/collections/search",
                    params={
                        "page": page,
                        "page_size": page_size
                    },
                    timeout=20
                )
                r.raise_for_status()

                payload = r.json()
                data = payload.get("data", []) or []

                for row in data:
                    nombre = row.get("nombre_cliente")
                    if nombre:
                        clientes_set.add(nombre)

                total = int(payload.get("total") or 0)

                if not data:
                    break

                if page * page_size >= total:
                    break

                page += 1

            clientes = ["ALL"] + sorted(clientes_set)

            self.cbo_cliente["values"] = clientes
            self.clientes_loaded = True

        except Exception as e:
            messagebox.showerror(
                "Collections",
                f"No se pudieron cargar clientes\n\n{e}"
            )

    # ============================================================
    # PLACEHOLDER
    # ============================================================
    def _show_placeholder(self):
        for w in self.table_container.winfo_children():
            w.destroy()

        ttk.Label(
            self.table_container,
            text="Use los filtros y presione Buscar para cargar Collections",
            foreground="gray"
        ).pack(expand=True)

    # ============================================================
    # ACTIONS
    # ============================================================
    def _buscar(self):

        filtros = {
            "bucket_aging": self.bucket.get() or None,
            "estado_factura": self.estado.get() or None,
            "disputada": (
                None if self.disputada.get() == ""
                else self.disputada.get() == "True"
            )
        }

        if self.cliente.get() and self.cliente.get() != "ALL":
            filtros["cliente"] = self.cliente.get()

        if not self.tabla:
            self._crear_tabla()

        self.tabla.buscar(
            filtros,
            on_kpis=self._actualizar_kpis
        )

    def _crear_tabla(self):
        for w in self.table_container.winfo_children():
            w.destroy()

        self.tabla = TablaCollections(self.table_container)
        self.tabla.pack(fill="both", expand=True)

    # ============================================================
    # KPI CARDS
    # ============================================================
    def _init_kpi_cards(self):

        if self.kpi_cards:
            return

        def _card(parent, title):
            frame = tk.Frame(parent, bg="#0F4C75", padx=18, pady=12)

            lbl_title = tk.Label(
                frame,
                text=title,
                fg="white",
                bg="#0F4C75",
                font=("Segoe UI", 9)
            )
            lbl_value = tk.Label(
                frame,
                text="—",
                fg="white",
                bg="#0F4C75",
                font=("Segoe UI", 15, "bold")
            )

            lbl_title.pack(anchor="w")
            lbl_value.pack(anchor="w")

            return frame, lbl_value

        cards = [
            ("Total AR (Saldo)", "total_ar"),
            ("Current (Saldo)", "current"),
            ("Overdue (Saldo)", "overdue"),
            ("Over 90 (Saldo)", "over_90"),
        ]

        for title, key in cards:
            frame, lbl = _card(self.kpi_container, title)
            frame.pack(side="left", padx=8)
            self.kpi_cards[key] = lbl

    def _actualizar_kpis(self, resumen: dict):

        self._init_kpi_cards()

        self.kpi_cards["total_ar"].config(text=f"{resumen.get('total_ar', 0):,.2f}")
        self.kpi_cards["current"].config(text=f"{resumen.get('current', 0):,.2f}")
        self.kpi_cards["overdue"].config(text=f"{resumen.get('overdue', 0):,.2f}")
        self.kpi_cards["over_90"].config(text=f"{resumen.get('over_90', 0):,.2f}")


    # ============================================================
    # SYNC DESDE INVOICING → COLLECTIONS
    # ============================================================
    def _sync_collections(self):

        if not messagebox.askyesno(
            "Sincronizar facturas",
            "Esto sincronizará las facturas emitidas hacia Collections.\n¿Desea continuar?"
        ):
            return

        try:
            result = sync_collections_from_invoicing_api()

            inserted = result.get("inserted", 0)

            messagebox.showinfo(
                "Collections",
                f"Sincronización completada.\nFacturas nuevas: {inserted}"
            )

            # Refrescar tabla y KPIs
            if self.tabla:
                self.tabla.buscar(
                    self.tabla.filtros,
                    on_kpis=self._actualizar_kpis
                )

        except Exception as e:
            messagebox.showerror(
                "Collections",
                f"No se pudo sincronizar Collections\n\n{e}"
            )

