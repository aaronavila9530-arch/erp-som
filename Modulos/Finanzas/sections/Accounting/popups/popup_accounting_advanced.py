import threading
import tkinter as tk
from datetime import date
from tkinter import messagebox, ttk

from api_client import (
    get_accounting_advanced_dashboard_api,
    get_accounting_budget_vs_actual_api,
    get_accounting_fx_revaluation_preview_api,
    get_accounting_smart_alerts_api,
    get_accounting_tax_deep_summary_api,
    post_accounting_fx_revaluation_api,
    post_portia_accounting_review_api,
)


class PopupAccountingAdvanced(tk.Toplevel):
    def __init__(self, parent, period=None):
        super().__init__(parent)
        self.title("Accounting avanzado")
        self.geometry("1260x760")
        self.minsize(1040, 620)
        self.period = tk.StringVar(value=period or date.today().strftime("%Y-%m"))
        self.status = tk.StringVar(value="Listo")
        self.language = tk.StringVar(value="ES")
        self.data = {}
        self.trees = {}
        self._build()
        self.after(150, self.refresh)

    def _build(self):
        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")
        ttk.Label(top, text="Periodo").pack(side="left")
        ttk.Entry(top, textvariable=self.period, width=10).pack(side="left", padx=5)
        ttk.Button(top, text="Actualizar", command=self.refresh).pack(side="left", padx=4)
        ttk.Button(top, text="Contabilizar revaluacion USD", command=self._post_fx).pack(side="left", padx=4)
        ttk.Label(top, text="PORTIA").pack(side="left", padx=(20, 3))
        ttk.Combobox(top, textvariable=self.language, values=("ES", "EN"), width=5, state="readonly").pack(side="left")
        ttk.Button(top, text="Analizar", command=self._portia).pack(side="left", padx=4)
        ttk.Button(top, text="Cerrar", command=self.destroy).pack(side="right")

        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True, padx=10, pady=(0, 5))
        for key, title, columns in (
            ("dashboard", "Dashboard ejecutivo", ("metric", "value", "detail")),
            ("alerts", "Alertas inteligentes", ("severity", "code", "title", "message")),
            ("tax", "Impuestos CR", ("section", "metric", "value", "detail")),
            ("fx", "Multi-moneda / USD", ("entity_type", "entity_name", "document_number", "open_amount", "current_crc_value", "difference_crc")),
            ("budget", "Budget vs real", ("account_code", "account_name", "budget_amount", "actual_amount", "variance", "variance_pct")),
            ("portia", "PORTIA contable", ("line", "commentary")),
        ):
            self._add_tree(key, title, columns)
        ttk.Label(self, textvariable=self.status, anchor="w").pack(fill="x", padx=12, pady=(0, 7))

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
            tree.column(col, width=280 if col in {"message", "detail", "commentary", "account_name", "entity_name"} else 130)
        self.trees[key] = tree

    def refresh(self):
        self.status.set("Cargando controles avanzados...")
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        period = self.period.get().strip()
        try:
            data = {
                "dashboard": get_accounting_advanced_dashboard_api(period),
                "alerts": get_accounting_smart_alerts_api(period),
                "tax": get_accounting_tax_deep_summary_api(period),
                "fx": get_accounting_fx_revaluation_preview_api(period),
                "budget": get_accounting_budget_vs_actual_api(period),
            }
            self.after(0, self._apply, data)
        except Exception as exc:
            self.after(0, self._error, str(exc))

    def _error(self, message):
        self.status.set("Error")
        messagebox.showerror("Accounting avanzado", message, parent=self)

    def _apply(self, data):
        self.data = data
        self._fill_dashboard(data["dashboard"])
        self._fill_alerts(data["alerts"])
        self._fill_tax(data["tax"])
        self._fill_simple("fx", data["fx"].get("rows", []))
        self._fill_simple("budget", data["budget"].get("data", []))
        self._fill_simple("portia", [])
        self.status.set("Controles avanzados actualizados")

    def _fill_dashboard(self, data):
        rows = []
        margin = data.get("margin", {})
        liquidity = data.get("liquidity", {})
        rows.append({"metric": "Liquidez bancos", "value": self._position(liquidity.get("banks"), "Disponible", "Sobregiro"), "detail": f"Saldo bancario contable al {liquidity.get('as_of') or data.get('period')}"})
        rows.append({"metric": "Resultado mensual", "value": self._position(margin.get("profit"), "Utilidad", "Perdida"), "detail": f"Margen {margin.get('margin_pct', 0):,.2f}%"})
        rows.append({"metric": "CxC vencida", "value": self._money((data.get("overdue_ar") or {}).get("total")), "detail": f"{(data.get('overdue_ar') or {}).get('count', 0)} facturas"})
        rows.append({"metric": "Pagos proximos", "value": self._money((data.get("upcoming_payments") or {}).get("total")), "detail": f"{(data.get('upcoming_payments') or {}).get('count', 0)} obligaciones"})
        iva = data.get("iva_estimated", {})
        rows.append({"metric": "IVA estimado", "value": self._position(iva.get("net_tax"), "Por pagar", "Credito a favor"), "detail": "Fuente documental fiscal"})
        self._fill_simple("dashboard", rows)

    def _fill_alerts(self, data):
        self._fill_simple("alerts", data.get("data", []))

    def _fill_tax(self, data):
        rows = []
        iva = data.get("iva", {})
        for section, payload in (("Fiscal", iva.get("fiscal", {})), ("Accounting", iva.get("accounting", {})), ("Differences", iva.get("differences", {})), ("Quality", iva.get("quality", {}))):
            for key, value in (payload or {}).items():
                rows.append({"section": section, "metric": key, "value": value, "detail": ""})
        ret = data.get("retentions", {})
        for key, value in ret.items():
            rows.append({"section": "Retenciones", "metric": key, "value": value, "detail": ""})
        self._fill_simple("tax", rows)

    def _fill_simple(self, key, rows):
        tree = self.trees[key]
        tree.delete(*tree.get_children())
        columns = tree["columns"]
        if not rows:
            empty = {columns[0]: "Sin datos", columns[-1]: self._empty_message(key)}
            rows = [empty]
        for row in rows or []:
            tree.insert("", "end", values=[self._cell((row or {}).get(col)) for col in columns])

    def _post_fx(self):
        period = self.period.get().strip()
        if not messagebox.askyesno("Revaluacion USD", f"Crear asiento de revaluacion USD para {period}?", parent=self):
            return
        try:
            result = post_accounting_fx_revaluation_api({"period": period, "currency_code": "USD", "user": "ERP_USER", "reason": "Monthly USD revaluation"})
            messagebox.showinfo("Revaluacion USD", f"Proceso completado. Asiento: {result.get('entry_id', '-')}", parent=self)
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Revaluacion USD", str(exc), parent=self)

    def _portia(self):
        try:
            data = post_portia_accounting_review_api(self.period.get().strip(), self.language.get())
            rows = [{"line": idx + 1, "commentary": line} for idx, line in enumerate((data.get("commentary") or "").splitlines()) if line.strip()]
            self._fill_simple("portia", rows)
            tab_index = list(self.trees.keys()).index("portia")
            self.tabs.select(self.tabs.tabs()[tab_index])
        except Exception as exc:
            messagebox.showerror("PORTIA contable", str(exc), parent=self)

    def _cell(self, value):
        if isinstance(value, float):
            return self._money(value)
        return "" if value is None else str(value)

    def _money(self, value):
        try:
            return f"{float(value or 0):,.2f}"
        except Exception:
            return "0.00"

    def _position(self, value, positive_label, negative_label):
        try:
            amount = float(value or 0)
        except Exception:
            amount = 0.0
        if abs(amount) < 0.005:
            return "Sin saldo 0.00"
        label = positive_label if amount >= 0 else negative_label
        return f"{label} {abs(amount):,.2f}"

    def _empty_message(self, key):
        return {
            "budget": "No hay presupuesto cargado para este periodo; por eso no existe comparacion budget vs real.",
            "portia": "Pulse Analizar para que PORTIA explique diferencias, alertas y reclasificaciones sugeridas.",
            "alerts": "No hay alertas inteligentes para este periodo.",
            "fx": "No hay saldos abiertos en USD para revaluar.",
        }.get(key, "No hay datos para mostrar.")
