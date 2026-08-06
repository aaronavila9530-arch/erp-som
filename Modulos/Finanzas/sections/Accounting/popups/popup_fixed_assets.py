import tkinter as tk
from tkinter import ttk, messagebox

from api_client import (
    create_accounting_fixed_asset_api,
    disable_accounting_fixed_asset_api,
    get_accounting_fixed_asset_schedule_api,
    get_accounting_fixed_assets_api,
    update_accounting_fixed_asset_api,
)


class PopupFixedAssets(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Activos fijos")
        self.geometry("1280x760")
        self.transient(parent)
        self.grab_set()
        self.search_var = tk.StringVar()
        self.status_var = tk.StringVar(value="ACTIVE")
        self.asset_rows = {}
        self.summary_vars = {
            "assets": tk.StringVar(value="0"),
            "value": tk.StringVar(value="0.00"),
            "depr": tk.StringVar(value="0.00"),
            "book": tk.StringVar(value="0.00"),
        }
        self._build_ui()
        self._load_assets()

    def _build_ui(self):
        toolbar = ttk.Frame(self, padding=10)
        toolbar.pack(fill="x")

        ttk.Label(toolbar, text="Buscar").pack(side="left")
        search = ttk.Entry(toolbar, textvariable=self.search_var, width=36)
        search.pack(side="left", padx=6)
        search.bind("<Return>", lambda _e: self._load_assets())

        ttk.Label(toolbar, text="Status").pack(side="left", padx=(12, 4))
        ttk.Combobox(
            toolbar,
            textvariable=self.status_var,
            values=("ACTIVE", "TODOS", "DISPOSED", "INACTIVE"),
            state="readonly",
            width=12,
        ).pack(side="left")
        ttk.Button(toolbar, text="Buscar", command=self._load_assets).pack(side="left", padx=6)
        ttk.Button(toolbar, text="+ Agregar activo", command=self._new_asset).pack(side="left", padx=(16, 4))
        ttk.Button(toolbar, text="Editar seleccionado", command=self._edit_asset).pack(side="left", padx=4)
        ttk.Button(toolbar, text="Inhabilitar", command=self._disable_asset).pack(side="left", padx=4)
        ttk.Button(toolbar, text="Cerrar", command=self.destroy).pack(side="right")

        summary = ttk.LabelFrame(self, text="Resumen de activos", padding=8)
        summary.pack(fill="x", padx=10, pady=(0, 8))
        self._summary_cell(summary, "Activos", self.summary_vars["assets"], 0)
        self._summary_cell(summary, "Costo CRC", self.summary_vars["value"], 1)
        self._summary_cell(summary, "Depreciacion acumulada", self.summary_vars["depr"], 2)
        self._summary_cell(summary, "Valor en libros", self.summary_vars["book"], 3)

        body = ttk.PanedWindow(self, orient="vertical")
        body.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        assets_frame = ttk.LabelFrame(body, text="Registro de activos cargados", padding=4)
        schedule_frame = ttk.LabelFrame(body, text="Depreciacion del activo seleccionado", padding=4)
        body.add(assets_frame, weight=3)
        body.add(schedule_frame, weight=2)

        asset_cols = (
            "id", "code", "desc", "class", "purchase", "usd", "tc", "crc",
            "monthly", "accum", "book", "resp", "location", "account",
        )
        self.assets_tree = self._tree(
            assets_frame,
            asset_cols,
            {
                "id": ("ID", 65),
                "code": ("Codigo", 110),
                "desc": ("Descripcion", 310),
                "class": ("Clasificacion", 145),
                "purchase": ("Compra", 90),
                "usd": ("USD", 95),
                "tc": ("TC", 80),
                "crc": ("Costo CRC", 115),
                "monthly": ("Dep. mensual", 110),
                "accum": ("Dep. acum.", 115),
                "book": ("Valor libros", 115),
                "resp": ("Responsable", 140),
                "location": ("Ubicacion", 130),
                "account": ("Cuenta activo", 120),
            },
        )
        self.assets_tree.bind("<<TreeviewSelect>>", lambda _e: self._load_schedule())

        schedule_cols = ("period", "date", "amount", "accum", "book", "status", "entry")
        self.schedule_tree = self._tree(
            schedule_frame,
            schedule_cols,
            {
                "period": ("Periodo", 95),
                "date": ("Fecha", 100),
                "amount": ("Depreciacion", 130),
                "accum": ("Acumulada", 130),
                "book": ("Valor libros", 130),
                "status": ("Status", 110),
                "entry": ("Asiento", 90),
            },
        )

    def _summary_cell(self, parent, label, var, column):
        frame = ttk.Frame(parent)
        frame.grid(row=0, column=column, sticky="ew", padx=8)
        parent.columnconfigure(column, weight=1)
        ttk.Label(frame, text=label).pack(anchor="w")
        ttk.Label(frame, textvariable=var, font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(3, 0))

    def _tree(self, parent, columns, config):
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True)
        tree = ttk.Treeview(frame, columns=columns, show="headings")
        for col in columns:
            heading, width = config[col]
            tree.heading(col, text=heading)
            tree.column(col, width=width, anchor="w")
        yscroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        xscroll = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        return tree

    @staticmethod
    def _money(value):
        try:
            return f"{float(value or 0):,.2f}"
        except Exception:
            return "0.00"

    def _load_assets(self):
        try:
            payload = get_accounting_fixed_assets_api(
                search=self.search_var.get().strip() or None,
                status=self.status_var.get(),
                limit=2000,
            )
        except Exception as exc:
            try:
                payload = self._load_assets_direct()
            except Exception:
                messagebox.showerror("Activos fijos", str(exc), parent=self)
                return

        summary = payload.get("summary") or {}
        self.summary_vars["assets"].set(str(int(summary.get("assets") or 0)))
        self.summary_vars["value"].set(self._money(summary.get("value_crc")))
        self.summary_vars["depr"].set(self._money(summary.get("accumulated_depreciation_crc")))
        self.summary_vars["book"].set(self._money(summary.get("book_value_crc")))

        self.assets_tree.delete(*self.assets_tree.get_children())
        self.schedule_tree.delete(*self.schedule_tree.get_children())
        self.asset_rows = {}
        for row in payload.get("data") or []:
            item_id = self.assets_tree.insert(
                "",
                "end",
                values=(
                    row.get("id"),
                    row.get("asset_code") or "",
                    row.get("description") or "",
                    row.get("classification") or "",
                    row.get("purchase_date") or "",
                    self._money(row.get("original_amount")),
                    self._money(row.get("exchange_rate")),
                    self._money(row.get("value_crc")),
                    self._money(row.get("monthly_depreciation_crc")),
                    self._money(row.get("accumulated_depreciation_crc")),
                    self._money(row.get("book_value_crc")),
                    row.get("responsible") or "",
                    row.get("location") or "",
                    row.get("asset_account_code") or "",
                ),
            )
            self.asset_rows[str(row.get("id"))] = row

    def _load_schedule(self):
        selected = self.assets_tree.selection()
        if not selected:
            return
        asset_id = self.assets_tree.item(selected[0], "values")[0]
        try:
            rows = get_accounting_fixed_asset_schedule_api(asset_id)
        except Exception as exc:
            try:
                rows = self._load_schedule_direct(asset_id)
            except Exception:
                messagebox.showerror("Activos fijos", str(exc), parent=self)
                return
        self.schedule_tree.delete(*self.schedule_tree.get_children())
        for row in rows:
            self.schedule_tree.insert(
                "",
                "end",
                values=(
                    row.get("period") or "",
                    row.get("depreciation_date") or "",
                    self._money(row.get("depreciation_amount_crc")),
                    self._money(row.get("accumulated_depreciation_crc")),
                    self._money(row.get("book_value_crc")),
                    row.get("status") or "",
                    row.get("accounting_entry_id") or "",
                ),
            )

    def _selected_asset(self):
        selected = self.assets_tree.selection()
        if not selected:
            messagebox.showwarning("Activos fijos", "Seleccione un activo.", parent=self)
            return None
        asset_id = str(self.assets_tree.item(selected[0], "values")[0])
        return self.asset_rows.get(asset_id)

    def _new_asset(self):
        PopupFixedAssetEditor(self, on_save=self._save_new_asset)

    def _edit_asset(self):
        row = self._selected_asset()
        if not row:
            return
        PopupFixedAssetEditor(self, asset=row, on_save=lambda payload: self._save_existing_asset(row["id"], payload))

    def _disable_asset(self):
        row = self._selected_asset()
        if not row:
            return
        if not messagebox.askyesno(
            "Activos fijos",
            f"Inhabilitar el activo {row.get('asset_code')}?",
            parent=self,
        ):
            return
        try:
            try:
                disable_accounting_fixed_asset_api(row["id"])
            except Exception:
                self._disable_asset_direct(row["id"])
            self._load_assets()
        except Exception as exc:
            messagebox.showerror("Activos fijos", str(exc), parent=self)

    def _save_new_asset(self, payload):
        try:
            try:
                create_accounting_fixed_asset_api(payload)
            except Exception:
                self._create_asset_direct(payload)
            self._load_assets()
            return True
        except Exception as exc:
            messagebox.showerror("Activos fijos", str(exc), parent=self)
            return False

    def _save_existing_asset(self, asset_id, payload):
        try:
            try:
                update_accounting_fixed_asset_api(asset_id, payload)
            except Exception:
                self._update_asset_direct(asset_id, payload)
            self._load_assets()
            return True
        except Exception as exc:
            messagebox.showerror("Activos fijos", str(exc), parent=self)
            return False

    def _load_assets_direct(self):
        from psycopg2.extras import RealDictCursor
        from backend_api.database import connect

        conn = connect()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                filters = []
                params = []
                status = self.status_var.get()
                search = self.search_var.get().strip()
                if status and status != "TODOS":
                    filters.append("status = %s")
                    params.append(status)
                if search:
                    filters.append("(asset_code ILIKE %s OR description ILIKE %s OR responsible ILIKE %s OR location ILIKE %s)")
                    like = f"%{search}%"
                    params.extend([like, like, like, like])
                where = "WHERE " + " AND ".join(filters) if filters else ""
                cur.execute(
                    f"""
                    SELECT COUNT(*) AS assets, COALESCE(SUM(value_crc),0) AS value_crc,
                           COALESCE(SUM(accumulated_depreciation_crc),0) AS accumulated_depreciation_crc,
                           COALESCE(SUM(book_value_crc),0) AS book_value_crc
                    FROM fixed_assets
                    {where}
                    """,
                    params,
                )
                summary = dict(cur.fetchone() or {})
                cur.execute(
                    f"""
                    SELECT *
                    FROM fixed_assets
                    {where}
                    ORDER BY classification NULLS LAST, asset_code
                    LIMIT 2000
                    """,
                    params,
                )
                return {"summary": summary, "data": cur.fetchall()}
        finally:
            conn.close()

    def _create_asset_direct(self, payload):
        import os
        import sys
        sys.path.insert(0, os.path.join(os.getcwd(), "backend_api"))
        from backend_api.database import connect
        from backend_api.routers.fixed_assets import create_fixed_asset

        conn = connect()
        try:
            result = create_fixed_asset(payload, db=conn)
            return result
        finally:
            conn.close()

    def _update_asset_direct(self, asset_id, payload):
        import os
        import sys
        sys.path.insert(0, os.path.join(os.getcwd(), "backend_api"))
        from backend_api.database import connect
        from backend_api.routers.fixed_assets import update_fixed_asset

        conn = connect()
        try:
            result = update_fixed_asset(int(asset_id), payload, db=conn)
            return result
        finally:
            conn.close()

    def _disable_asset_direct(self, asset_id):
        import os
        import sys
        sys.path.insert(0, os.path.join(os.getcwd(), "backend_api"))
        from backend_api.database import connect
        from backend_api.routers.fixed_assets import disable_fixed_asset

        conn = connect()
        try:
            result = disable_fixed_asset(int(asset_id), {}, db=conn)
            return result
        finally:
            conn.close()

    def _load_schedule_direct(self, asset_id):
        from psycopg2.extras import RealDictCursor
        from backend_api.database import connect

        conn = connect()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT period, depreciation_date, depreciation_amount_crc,
                           accumulated_depreciation_crc, book_value_crc, status,
                           accounting_entry_id
                    FROM fixed_asset_depreciation_schedule
                    WHERE asset_id = %s
                    ORDER BY period
                    """,
                    (asset_id,),
                )
                return cur.fetchall()
        finally:
            conn.close()


class PopupFixedAssetEditor(tk.Toplevel):
    def __init__(self, parent, asset=None, on_save=None):
        super().__init__(parent)
        self.title("Editar activo" if asset else "Agregar activo")
        self.geometry("620x520")
        self.transient(parent)
        self.grab_set()
        self.asset = asset or {}
        self.on_save = on_save
        self.vars = {
            "description": tk.StringVar(value=self.asset.get("description") or ""),
            "classification": tk.StringVar(value=self.asset.get("classification") or "Muebles y enseres"),
            "location": tk.StringVar(value=self.asset.get("location") or ""),
            "responsible": tk.StringVar(value=self.asset.get("responsible") or ""),
            "serial": tk.StringVar(value=self.asset.get("serial") or ""),
            "plate": tk.StringVar(value=self.asset.get("plate") or ""),
            "condition": tk.StringVar(value=self.asset.get("condition") or "Nuevo"),
            "purchase_date": tk.StringVar(value=str(self.asset.get("purchase_date") or "2024-12-31")),
            "currency_code": tk.StringVar(value=self.asset.get("currency_code") or "USD"),
            "original_amount": tk.StringVar(value=str(self.asset.get("original_amount") or "")),
            "notes": tk.StringVar(value=self.asset.get("notes") or ""),
        }
        self._build_ui()

    def _build_ui(self):
        frame = ttk.Frame(self, padding=14)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)

        fields = [
            ("Descripcion", "description", "entry"),
            ("Clasificacion", "classification", "combo_class"),
            ("Ubicacion", "location", "entry"),
            ("Responsable", "responsible", "entry"),
            ("Serie", "serial", "entry"),
            ("Placa", "plate", "entry"),
            ("Estado", "condition", "combo_status"),
            ("Compra YYYY-MM-DD", "purchase_date", "entry"),
            ("Moneda", "currency_code", "combo_currency"),
            ("Monto original", "original_amount", "entry"),
            ("Notas", "notes", "entry"),
        ]
        for row, (label, key, kind) in enumerate(fields):
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", pady=5, padx=(0, 8))
            if kind == "combo_class":
                widget = ttk.Combobox(
                    frame,
                    textvariable=self.vars[key],
                    values=(
                        "Muebles y enseres",
                        "Equipos de oficina",
                        "Equipos de comunicacion",
                        "Equipos de cocina",
                        "Maquinaria y equipo",
                        "Equipos de transporte",
                    ),
                    width=42,
                )
            elif kind == "combo_status":
                widget = ttk.Combobox(
                    frame,
                    textvariable=self.vars[key],
                    values=("Nuevo", "Bueno", "Regular", "Deteriorado"),
                    width=42,
                )
            elif kind == "combo_currency":
                widget = ttk.Combobox(
                    frame,
                    textvariable=self.vars[key],
                    values=("USD", "CRC"),
                    state="readonly",
                    width=12,
                )
            else:
                widget = ttk.Entry(frame, textvariable=self.vars[key], width=48)
            widget.grid(row=row, column=1, sticky="ew", pady=5)

        actions = ttk.Frame(frame)
        actions.grid(row=len(fields), column=0, columnspan=2, sticky="e", pady=(18, 0))
        ttk.Button(actions, text="Cancelar", command=self.destroy).pack(side="right", padx=5)
        ttk.Button(actions, text="Guardar", command=self._save).pack(side="right")

    def _save(self):
        payload = {key: var.get().strip() for key, var in self.vars.items()}
        if not payload["description"]:
            messagebox.showwarning("Activos fijos", "La descripcion es requerida.", parent=self)
            return
        if not payload["original_amount"]:
            messagebox.showwarning("Activos fijos", "El monto original es requerido.", parent=self)
            return
        if self.on_save and self.on_save(payload):
            self.destroy()
