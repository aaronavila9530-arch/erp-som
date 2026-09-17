import threading
import tkinter as tk
from datetime import date
from tkinter import ttk, messagebox

from api_client import get_finance_planning_summary_api


class FinancePlanningUI(tk.Frame):
    def __init__(self, parent, period=None):
        super().__init__(parent, bg="white")
        self.period = tk.StringVar(value=period or date.today().strftime("%Y-%m"))
        self.months = tk.StringVar(value="4")
        self.status = tk.StringVar(value="Presione Buscar para consultar PLN.")
        self.trees = {}
        self._build()

    def _build(self):
        header = tk.Frame(self, bg="white")
        header.pack(fill="x", padx=12, pady=(8, 4))
        tk.Label(header, text="PLN / Planificación financiera", bg="white", font=("Segoe UI", 14, "bold")).pack(side="left")
        ttk.Label(header, text="Periodo").pack(side="left", padx=(20, 4))
        ttk.Entry(header, textvariable=self.period, width=10).pack(side="left")
        ttk.Label(header, text="Meses").pack(side="left", padx=(12, 4))
        ttk.Combobox(header, textvariable=self.months, values=("1", "2", "3", "4", "6", "12"), width=5, state="readonly").pack(side="left")
        ttk.Button(header, text="Buscar", command=self.search).pack(side="left", padx=8)
        ttk.Label(self, textvariable=self.status, background="white", foreground="#475467").pack(anchor="w", padx=14)

        self.kpis = tk.Frame(self, bg="white")
        self.kpis.pack(fill="x", padx=12, pady=8)

        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self._add_tree("obligation_buckets", "Calendario ITP", ("currency", "bucket", "count", "amount"))
        self._add_tree("obligations", "Obligaciones", ("id", "payee_name", "obligation_type", "due_date", "currency", "balance", "status", "origin"))
        self._add_tree("applied_payments", "Pagos aplicados", ("currency", "count", "amount"))
        self._add_tree("expenses", "Gastos Accounting", ("period", "account_code", "account_name", "actual_amount"))
        self._add_tree("goals", "Metas / ahorros", ("id", "period", "purpose", "name", "account_code", "currency_code", "target_amount", "progress_amount", "progress_pct", "target_date", "status"))
        self._add_tree("projects", "Proyectos", ("nombre_proyecto", "moneda", "personas", "total_honorarios", "total_gastos", "precio", "utilidad", "creado_el"))

    def _add_tree(self, key, title, columns):
        frame = ttk.Frame(self.tabs, padding=5)
        self.tabs.add(frame, text=title)
        tree = ttk.Treeview(frame, columns=columns, show="headings")
        y = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        x = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=y.set, xscrollcommand=x.set)
        tree.grid(row=0, column=0, sticky="nsew")
        y.grid(row=0, column=1, sticky="ns")
        x.grid(row=1, column=0, sticky="ew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        for col in columns:
            tree.heading(col, text=col.replace("_", " ").title())
            tree.column(col, width=240 if col in {"payee_name", "account_name", "name", "nombre_proyecto"} else 130)
        self.trees[key] = tree

    def search(self):
        self.status.set("Consultando planificación...")
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        try:
            payload = get_finance_planning_summary_api(self.period.get().strip(), int(self.months.get() or 4))
            self.after(0, self._apply, payload)
        except Exception as exc:
            self.after(0, self._error, str(exc))

    def _error(self, message):
        self.status.set("Error al consultar PLN.")
        messagebox.showerror("PLN / Planificación", message, parent=self)

    def _apply(self, payload):
        totals = payload.get("totals") or {}
        self._render_kpis(totals, payload)
        for key, tree in self.trees.items():
            tree.delete(*tree.get_children())
            rows = payload.get(key) or []
            if not rows:
                tree.insert("", "end", values=["Sin datos"] + [""] * (len(tree["columns"]) - 1))
                continue
            columns = tree["columns"]
            for row in rows:
                tree.insert("", "end", values=[self._cell((row or {}).get(col)) for col in columns])
        self.status.set(f"PLN actualizado al {payload.get('as_of')} | horizonte {payload.get('horizon_months')} meses.")

    def _render_kpis(self, totals, payload):
        for widget in self.kpis.winfo_children():
            widget.destroy()
        pending = totals.get("pending_by_currency") or {}
        cards = [
            ("Pendiente ITP", " | ".join(f"{cur} {self._money(amount)}" for cur, amount in pending.items()) or "0.00"),
            ("Lineas", totals.get("obligation_lines", 0)),
            ("Metas activas", totals.get("goals_active", 0)),
            ("Proyectos", totals.get("projects", 0)),
        ]
        for label, value in cards:
            frame = tk.Frame(self.kpis, bg="#f3f7fb", bd=1, relief="solid", width=220, height=70)
            frame.pack(side="left", padx=5)
            frame.pack_propagate(False)
            tk.Label(frame, text=label, bg="#f3f7fb", fg="#475467").pack(anchor="w", padx=8, pady=(8, 0))
            tk.Label(frame, text=str(value), bg="#f3f7fb", fg="#003A75", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=8)

    def _cell(self, value):
        if isinstance(value, float):
            return self._money(value)
        return "" if value is None else str(value)

    def _money(self, value):
        try:
            return f"{float(value or 0):,.2f}"
        except Exception:
            return "0.00"
