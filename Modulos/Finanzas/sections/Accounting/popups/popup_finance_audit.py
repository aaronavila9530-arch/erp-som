import tkinter as tk
from tkinter import ttk, messagebox

from api_client import get_finance_audit_api


class PopupFinanceAudit(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Auditoria financiera")
        self.geometry("1150x620")
        self.transient(parent)
        self.grab_set()
        self._build_ui()
        self._load()

    def _build_ui(self):
        filters = ttk.LabelFrame(self, text="Filtros")
        filters.pack(fill="x", padx=10, pady=10)

        ttk.Label(filters, text="Modulo").grid(row=0, column=0, padx=5, pady=6, sticky="w")
        self.module = ttk.Combobox(
            filters,
            values=["", "accounting", "collections", "itp", "bank_reconciliation"],
            state="readonly",
            width=22,
        )
        self.module.grid(row=0, column=1, padx=5, pady=6, sticky="w")

        ttk.Label(filters, text="Usuario").grid(row=0, column=2, padx=5, pady=6, sticky="w")
        self.user = ttk.Entry(filters, width=24)
        self.user.grid(row=0, column=3, padx=5, pady=6, sticky="w")

        ttk.Label(filters, text="Entidad").grid(row=0, column=4, padx=5, pady=6, sticky="w")
        self.entity_type = ttk.Entry(filters, width=24)
        self.entity_type.grid(row=0, column=5, padx=5, pady=6, sticky="w")

        ttk.Label(filters, text="ID").grid(row=0, column=6, padx=5, pady=6, sticky="w")
        self.entity_id = ttk.Entry(filters, width=16)
        self.entity_id.grid(row=0, column=7, padx=5, pady=6, sticky="w")

        ttk.Button(filters, text="Buscar", command=self._load).grid(row=0, column=8, padx=5, pady=6)
        ttk.Button(filters, text="Limpiar", command=self._clear).grid(row=0, column=9, padx=5, pady=6)

        cols = ("created_at", "module", "action", "performed_by", "role", "entity", "reason")
        self.tree = ttk.Treeview(self, columns=cols, show="headings")
        headers = {
            "created_at": "Fecha",
            "module": "Modulo",
            "action": "Accion",
            "performed_by": "Usuario",
            "role": "Rol",
            "entity": "Entidad",
            "reason": "Motivo",
        }
        widths = {
            "created_at": 185,
            "module": 150,
            "action": 210,
            "performed_by": 150,
            "role": 110,
            "entity": 190,
            "reason": 320,
        }
        for col in cols:
            self.tree.heading(col, text=headers[col])
            self.tree.column(col, width=widths[col], anchor="w")
        self.tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.tree.bind("<Double-1>", self._show_detail)

    def _clear(self):
        self.module.set("")
        self.user.delete(0, "end")
        self.entity_type.delete(0, "end")
        self.entity_id.delete(0, "end")
        self._load()

    def _load(self):
        try:
            self.rows = get_finance_audit_api(
                module=self.module.get().strip() or None,
                entity_type=self.entity_type.get().strip() or None,
                entity_id=self.entity_id.get().strip() or None,
                performed_by=self.user.get().strip() or None,
                limit=500,
            )
        except Exception as exc:
            messagebox.showerror("Auditoria", f"No se pudo cargar auditoria:\n{exc}")
            self.rows = []

        self.tree.delete(*self.tree.get_children())
        for idx, row in enumerate(self.rows):
            entity = " ".join(
                part for part in (
                    str(row.get("entity_type") or ""),
                    str(row.get("entity_id") or ""),
                )
                if part
            )
            self.tree.insert(
                "",
                "end",
                iid=str(idx),
                values=(
                    row.get("created_at") or "",
                    row.get("module") or "",
                    row.get("action") or "",
                    row.get("performed_by") or "",
                    row.get("performed_role") or "",
                    entity,
                    row.get("reason") or "",
                ),
            )

    def _show_detail(self, _event=None):
        selected = self.tree.selection()
        if not selected:
            return
        row = self.rows[int(selected[0])]
        detail = tk.Toplevel(self)
        detail.title("Detalle de auditoria")
        detail.geometry("850x560")
        text = tk.Text(detail, wrap="word")
        text.pack(fill="both", expand=True, padx=8, pady=8)
        import json
        text.insert("1.0", json.dumps(row, indent=2, default=str, ensure_ascii=False))
        text.configure(state="disabled")
