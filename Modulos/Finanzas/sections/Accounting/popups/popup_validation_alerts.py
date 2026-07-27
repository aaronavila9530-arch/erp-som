import json
import tkinter as tk
from tkinter import ttk, messagebox

from api_client import get_accounting_validation_alerts_api


class PopupAccountingValidationAlerts(tk.Toplevel):
    def __init__(self, parent, filters=None):
        super().__init__(parent)
        self.filters = filters or {}
        self.rows = []
        self.title("Alertas y validaciones contables")
        self.geometry("1180x620")
        self.transient(parent)
        self.grab_set()
        self._build_ui()
        self._load()

    def _build_ui(self):
        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")

        self.summary_var = tk.StringVar(value="Validando...")
        ttk.Label(top, textvariable=self.summary_var, font=("Segoe UI", 10, "bold")).pack(side="left")
        ttk.Button(top, text="Actualizar", command=self._load).pack(side="right")

        cols = ("severity", "code", "title", "message", "entity")
        self.tree = ttk.Treeview(self, columns=cols, show="headings")
        labels = {
            "severity": "Semaforo",
            "code": "Codigo",
            "title": "Alerta",
            "message": "Detalle",
            "entity": "Entidad",
        }
        widths = {
            "severity": 95,
            "code": 230,
            "title": 220,
            "message": 460,
            "entity": 150,
        }
        for col in cols:
            self.tree.heading(col, text=labels[col])
            self.tree.column(col, width=widths[col], anchor="w")
        self.tree.tag_configure("critical", background="#ffd6d6")
        self.tree.tag_configure("warning", background="#fff1bf")
        self.tree.tag_configure("info", background="#dff0ff")
        self.tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.tree.bind("<Double-1>", self._show_detail)

    def _load(self):
        try:
            data = get_accounting_validation_alerts_api(**self.filters, limit=500)
        except Exception as exc:
            messagebox.showerror("Alertas", f"No se pudieron cargar alertas:\n{exc}")
            data = {"counts": {}, "alerts": []}

        counts = data.get("counts") or {}
        self.rows = data.get("alerts") or []
        self.summary_var.set(
            f"Criticas: {counts.get('critical', 0)}   "
            f"Advertencias: {counts.get('warning', 0)}   "
            f"Info: {counts.get('info', 0)}"
        )
        self.tree.delete(*self.tree.get_children())
        for idx, row in enumerate(self.rows):
            severity = row.get("severity") or "info"
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
                tags=(severity,),
                values=(
                    self._label(severity),
                    row.get("code") or "",
                    row.get("title") or "",
                    row.get("message") or "",
                    entity,
                ),
            )

    def _label(self, severity):
        if severity == "critical":
            return "ROJO"
        if severity == "warning":
            return "AMARILLO"
        return "AZUL"

    def _show_detail(self, _event=None):
        selected = self.tree.selection()
        if not selected:
            return
        row = self.rows[int(selected[0])]
        detail = tk.Toplevel(self)
        detail.title("Detalle de alerta")
        detail.geometry("850x560")
        text = tk.Text(detail, wrap="word")
        text.pack(fill="both", expand=True, padx=8, pady=8)
        text.insert("1.0", json.dumps(row, indent=2, default=str, ensure_ascii=False))
        text.configure(state="disabled")
