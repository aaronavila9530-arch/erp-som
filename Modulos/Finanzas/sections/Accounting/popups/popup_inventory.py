import tkinter as tk
from tkinter import ttk, messagebox

from api_client import (
    create_accounting_inventory_item_api,
    get_accounting_inventory_items_api,
    update_accounting_inventory_item_api,
)


class PopupInventory(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Inventarios")
        self.geometry("1100x650")
        self.transient(parent)
        self.grab_set()
        self.search_var = tk.StringVar()
        self.status_var = tk.StringVar(value="ACTIVE")
        self.rows = {}
        self._build_ui()
        self._load()

    def _build_ui(self):
        toolbar = ttk.Frame(self, padding=10)
        toolbar.pack(fill="x")
        ttk.Label(toolbar, text="Buscar").pack(side="left")
        ttk.Entry(toolbar, textvariable=self.search_var, width=34).pack(side="left", padx=6)
        ttk.Label(toolbar, text="Status").pack(side="left", padx=(12, 4))
        ttk.Combobox(toolbar, textvariable=self.status_var, values=("ACTIVE", "TODOS", "INACTIVE"), width=12, state="readonly").pack(side="left")
        ttk.Button(toolbar, text="Buscar", command=self._load).pack(side="left", padx=6)
        ttk.Button(toolbar, text="+ Agregar", command=self._new_item).pack(side="left", padx=(18, 4))
        ttk.Button(toolbar, text="Editar", command=self._edit_item).pack(side="left", padx=4)
        ttk.Button(toolbar, text="Cerrar", command=self.destroy).pack(side="right")

        self.summary_var = tk.StringVar(value="Items: 0 | Costo CRC: 0.00")
        ttk.Label(self, textvariable=self.summary_var, font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=12, pady=(0, 6))

        frame = ttk.Frame(self, padding=(10, 0, 10, 10))
        frame.pack(fill="both", expand=True)
        cols = ("id", "code", "desc", "cat", "qty", "min", "unit", "cost", "total", "location", "resp", "status")
        self.tree = ttk.Treeview(frame, columns=cols, show="headings")
        config = {
            "id": ("ID", 60), "code": ("Codigo", 95), "desc": ("Descripcion", 260),
            "cat": ("Categoria", 140), "qty": ("Cantidad", 90), "min": ("Minimo", 90),
            "unit": ("Unidad", 80), "cost": ("Costo unit.", 110), "total": ("Total CRC", 120),
            "location": ("Ubicacion", 140), "resp": ("Responsable", 140), "status": ("Status", 90),
        }
        for col in cols:
            text, width = config[col]
            self.tree.heading(col, text=text)
            self.tree.column(col, width=width)
        yscroll = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        xscroll = ttk.Scrollbar(frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

    @staticmethod
    def _money(value):
        try:
            return f"{float(value or 0):,.2f}"
        except Exception:
            return "0.00"

    def _load(self):
        try:
            try:
                payload = get_accounting_inventory_items_api(self.search_var.get().strip() or None, self.status_var.get())
            except Exception:
                payload = self._load_direct()
        except Exception as exc:
            messagebox.showerror("Inventarios", str(exc), parent=self)
            return
        summary = payload.get("summary") or {}
        self.summary_var.set(f"Items: {int(summary.get('items') or 0)} | Costo CRC: {self._money(summary.get('total_cost_crc'))}")
        self.rows = {}
        self.tree.delete(*self.tree.get_children())
        for row in payload.get("data") or []:
            self.rows[str(row.get("id"))] = row
            self.tree.insert("", "end", values=(
                row.get("id"), row.get("item_code"), row.get("description"), row.get("category"),
                self._money(row.get("quantity")), self._money(row.get("minimum_quantity")),
                row.get("unit"), self._money(row.get("unit_cost")), self._money(row.get("total_cost_crc")),
                row.get("location"), row.get("responsible"), row.get("status"),
            ))

    def _selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Inventarios", "Seleccione una linea.", parent=self)
            return None
        item_id = str(self.tree.item(selected[0], "values")[0])
        return self.rows.get(item_id)

    def _new_item(self):
        PopupInventoryEditor(self, on_save=self._save_new)

    def _edit_item(self):
        row = self._selected()
        if row:
            PopupInventoryEditor(self, item=row, on_save=lambda payload: self._save_existing(row["id"], payload))

    def _save_new(self, payload):
        try:
            try:
                create_accounting_inventory_item_api(payload)
            except Exception:
                self._create_direct(payload)
            self._load()
            return True
        except Exception as exc:
            messagebox.showerror("Inventarios", str(exc), parent=self)
            return False

    def _save_existing(self, item_id, payload):
        try:
            try:
                update_accounting_inventory_item_api(item_id, payload)
            except Exception:
                self._update_direct(item_id, payload)
            self._load()
            return True
        except Exception as exc:
            messagebox.showerror("Inventarios", str(exc), parent=self)
            return False

    def _load_direct(self):
        import os
        import sys
        sys.path.insert(0, os.path.join(os.getcwd(), "backend_api"))
        from backend_api.database import connect
        from backend_api.routers.fixed_assets import list_inventory_items

        conn = connect()
        try:
            return list_inventory_items(self.search_var.get().strip() or None, self.status_var.get(), db=conn)
        finally:
            conn.close()

    def _create_direct(self, payload):
        import os
        import sys
        sys.path.insert(0, os.path.join(os.getcwd(), "backend_api"))
        from backend_api.database import connect
        from backend_api.routers.fixed_assets import create_inventory_item

        conn = connect()
        try:
            return create_inventory_item(payload, db=conn)
        finally:
            conn.close()

    def _update_direct(self, item_id, payload):
        import os
        import sys
        sys.path.insert(0, os.path.join(os.getcwd(), "backend_api"))
        from backend_api.database import connect
        from backend_api.routers.fixed_assets import update_inventory_item

        conn = connect()
        try:
            return update_inventory_item(int(item_id), payload, db=conn)
        finally:
            conn.close()


class PopupInventoryEditor(tk.Toplevel):
    def __init__(self, parent, item=None, on_save=None):
        super().__init__(parent)
        self.title("Editar inventario" if item else "Agregar inventario")
        self.geometry("560x440")
        self.transient(parent)
        self.grab_set()
        self.on_save = on_save
        item = item or {}
        self.vars = {
            "description": tk.StringVar(value=item.get("description") or ""),
            "category": tk.StringVar(value=item.get("category") or "Articulos de oficina"),
            "location": tk.StringVar(value=item.get("location") or ""),
            "responsible": tk.StringVar(value=item.get("responsible") or ""),
            "unit": tk.StringVar(value=item.get("unit") or "unidad"),
            "quantity": tk.StringVar(value=str(item.get("quantity") or "")),
            "minimum_quantity": tk.StringVar(value=str(item.get("minimum_quantity") or "0")),
            "unit_cost": tk.StringVar(value=str(item.get("unit_cost") or "0")),
            "currency_code": tk.StringVar(value=item.get("currency_code") or "CRC"),
            "status": tk.StringVar(value=item.get("status") or "ACTIVE"),
            "notes": tk.StringVar(value=item.get("notes") or ""),
        }
        self._build_ui()

    def _build_ui(self):
        frame = ttk.Frame(self, padding=14)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)
        fields = [
            ("Descripcion", "description", "entry"),
            ("Categoria", "category", "combo_cat"),
            ("Ubicacion", "location", "entry"),
            ("Responsable", "responsible", "entry"),
            ("Unidad", "unit", "entry"),
            ("Cantidad", "quantity", "entry"),
            ("Minimo", "minimum_quantity", "entry"),
            ("Costo unitario", "unit_cost", "entry"),
            ("Moneda", "currency_code", "combo_currency"),
            ("Status", "status", "combo_status"),
            ("Notas", "notes", "entry"),
        ]
        for row, (label, key, kind) in enumerate(fields):
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", pady=5, padx=(0, 8))
            if kind == "combo_cat":
                widget = ttk.Combobox(frame, textvariable=self.vars[key], values=("Sellos", "Limpieza", "Articulos de oficina", "Tinta", "Papeleria", "Otros"), width=36)
            elif kind == "combo_currency":
                widget = ttk.Combobox(frame, textvariable=self.vars[key], values=("CRC", "USD"), state="readonly", width=12)
            elif kind == "combo_status":
                widget = ttk.Combobox(frame, textvariable=self.vars[key], values=("ACTIVE", "INACTIVE"), state="readonly", width=12)
            else:
                widget = ttk.Entry(frame, textvariable=self.vars[key], width=40)
            widget.grid(row=row, column=1, sticky="ew", pady=5)
        actions = ttk.Frame(frame)
        actions.grid(row=len(fields), column=0, columnspan=2, sticky="e", pady=(18, 0))
        ttk.Button(actions, text="Cancelar", command=self.destroy).pack(side="right", padx=5)
        ttk.Button(actions, text="Guardar", command=self._save).pack(side="right")

    def _save(self):
        payload = {key: var.get().strip() for key, var in self.vars.items()}
        if not payload["description"]:
            messagebox.showwarning("Inventarios", "La descripcion es requerida.", parent=self)
            return
        if self.on_save and self.on_save(payload):
            self.destroy()
