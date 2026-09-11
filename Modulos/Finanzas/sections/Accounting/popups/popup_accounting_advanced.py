import threading
import tkinter as tk
from datetime import date
from tkinter import filedialog, messagebox, simpledialog, ttk

from api_client import (
    delete_accounting_budget_api,
    download_accounting_budget_report_api,
    get_accounting_advanced_dashboard_api,
    get_accounting_bank_accounts_api,
    get_accounting_budgets_api,
    get_accounting_budget_vs_actual_api,
    get_accounting_fx_revaluation_preview_api,
    get_accounting_smart_alerts_api,
    get_accounting_tax_deep_summary_api,
    post_accounting_budget_contribution_api,
    post_accounting_fx_revaluation_api,
    post_portia_accounting_review_api,
    upsert_accounting_budget_api,
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
        self.purpose = tk.StringVar(value="ALL")
        self.budget_status = tk.StringVar(value="ALL")
        self.date_from = tk.StringVar(value="")
        self.date_to = tk.StringVar(value="")
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
        ttk.Label(top, text="Tipo").pack(side="left", padx=(12, 3))
        ttk.Combobox(top, textvariable=self.purpose, values=("ALL", "BUDGET", "SAVINGS", "GOAL"), width=10, state="readonly").pack(side="left")
        ttk.Label(top, text="Estado").pack(side="left", padx=(8, 3))
        ttk.Combobox(top, textvariable=self.budget_status, values=("ALL", "ACTIVE", "PAUSED", "DONE", "CANCELLED"), width=11, state="readonly").pack(side="left")
        ttk.Button(top, text="Contabilizar revaluacion USD", command=self._post_fx).pack(side="left", padx=4)
        ttk.Label(top, text="PORTIA").pack(side="left", padx=(20, 3))
        ttk.Combobox(top, textvariable=self.language, values=("ES", "EN"), width=5, state="readonly").pack(side="left")
        ttk.Button(top, text="Analizar", command=self._portia).pack(side="left", padx=4)
        ttk.Button(top, text="Minimizar", command=self.iconify).pack(side="right", padx=4)
        ttk.Button(top, text="Maximizar / restaurar", command=self._toggle_zoom).pack(side="right", padx=4)
        ttk.Button(top, text="Cerrar", command=self.destroy).pack(side="right")

        budget_bar = ttk.Frame(self, padding=(10, 0, 10, 7))
        budget_bar.pack(fill="x")
        ttk.Label(budget_bar, text="Desde").pack(side="left")
        ttk.Entry(budget_bar, textvariable=self.date_from, width=12).pack(side="left", padx=4)
        ttk.Label(budget_bar, text="Hasta").pack(side="left", padx=(8, 0))
        ttk.Entry(budget_bar, textvariable=self.date_to, width=12).pack(side="left", padx=4)
        ttk.Label(budget_bar, text="YYYY-MM-DD opcional").pack(side="left", padx=(4, 14))
        ttk.Button(budget_bar, text="Agregar", command=self._new_budget).pack(side="left", padx=3)
        ttk.Button(budget_bar, text="Modificar", command=self._edit_budget).pack(side="left", padx=3)
        ttk.Button(budget_bar, text="Eliminar", command=self._delete_budget).pack(side="left", padx=3)
        ttk.Button(budget_bar, text="Aportar / reducir banco", command=self._contribute_budget).pack(side="left", padx=3)
        ttk.Button(budget_bar, text="Exportar Excel", command=self._export_budget).pack(side="right", padx=3)

        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True, padx=10, pady=(0, 5))
        for key, title, columns in (
            ("dashboard", "Dashboard ejecutivo", ("metric", "value", "detail")),
            ("alerts", "Alertas inteligentes", ("severity", "code", "title", "message")),
            ("tax", "Impuestos CR", ("section", "metric", "value", "detail")),
            ("fx", "Multi-moneda / USD", ("entity_type", "entity_name", "document_number", "open_amount", "current_crc_value", "difference_crc")),
            ("budgets", "Presupuesto / ahorro / metas", ("id", "period", "purpose", "name", "account_code", "account_name", "budget_amount", "target_amount", "monthly_contribution", "target_date", "progress_amount", "progress_pct", "funding_bank_account_code", "status")),
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
                "budgets": get_accounting_budgets_api(period=period, date_from=self.date_from.get().strip() or None, date_to=self.date_to.get().strip() or None, purpose=self.purpose.get(), status=self.budget_status.get()),
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
        self._fill_simple("budgets", data["budgets"].get("data", []))
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

    def _toggle_zoom(self):
        try:
            self.state("normal" if self.state() == "zoomed" else "zoomed")
        except Exception:
            self.geometry("1260x760")

    def _selected_budget(self):
        tree = self.trees.get("budgets")
        if not tree:
            return None
        selected = tree.focus()
        if not selected:
            messagebox.showwarning("Presupuesto", "Selecciona una linea de presupuesto / meta.", parent=self)
            return None
        values = tree.item(selected, "values")
        columns = tree["columns"]
        return dict(zip(columns, values))

    def _budget_dialog(self, initial=None):
        initial = initial or {}
        win = tk.Toplevel(self)
        win.title("Presupuesto / ahorro / meta")
        win.geometry("650x560")
        win.transient(self)
        win.grab_set()
        fields = {
            "period": tk.StringVar(value=initial.get("period") or self.period.get()),
            "purpose": tk.StringVar(value=initial.get("purpose") or "BUDGET"),
            "name": tk.StringVar(value=initial.get("name") or ""),
            "account_code": tk.StringVar(value=initial.get("account_code") or ""),
            "cost_center_code": tk.StringVar(value=initial.get("cost_center_code") or ""),
            "currency_code": tk.StringVar(value=initial.get("currency_code") or "CRC"),
            "budget_amount": tk.StringVar(value=initial.get("budget_amount") or "0"),
            "target_amount": tk.StringVar(value=initial.get("target_amount") or "0"),
            "current_amount": tk.StringVar(value=initial.get("current_amount") or "0"),
            "monthly_contribution": tk.StringVar(value=initial.get("monthly_contribution") or "0"),
            "target_date": tk.StringVar(value=initial.get("target_date") or ""),
            "funding_bank_account_code": tk.StringVar(value=initial.get("funding_bank_account_code") or ""),
            "status": tk.StringVar(value=initial.get("status") or "ACTIVE"),
            "notes": tk.StringVar(value=initial.get("notes") or ""),
        }
        account_options = self._account_options()
        bank_options = self._bank_options()
        rows = [
            ("Periodo", "period", "entry"),
            ("Tipo", "purpose", "purpose"),
            ("Nombre", "name", "entry"),
            ("Cuenta contable objetivo", "account_code", "account"),
            ("Centro costo", "cost_center_code", "entry"),
            ("Moneda", "currency_code", "currency"),
            ("Presupuesto mensual", "budget_amount", "entry"),
            ("Meta total", "target_amount", "entry"),
            ("Actual inicial", "current_amount", "entry"),
            ("Aporte mensual sugerido", "monthly_contribution", "entry"),
            ("Fecha a cumplir", "target_date", "entry"),
            ("Banco de fondeo", "funding_bank_account_code", "bank"),
            ("Estado", "status", "status"),
            ("Notas", "notes", "entry"),
        ]
        for idx, (label, key, kind) in enumerate(rows):
            ttk.Label(win, text=label).grid(row=idx, column=0, sticky="w", padx=12, pady=6)
            if kind == "purpose":
                widget = ttk.Combobox(win, textvariable=fields[key], values=("BUDGET", "SAVINGS", "GOAL"), state="readonly")
            elif kind == "currency":
                widget = ttk.Combobox(win, textvariable=fields[key], values=("CRC", "USD"), state="readonly")
            elif kind == "status":
                widget = ttk.Combobox(win, textvariable=fields[key], values=("ACTIVE", "PAUSED", "DONE", "CANCELLED"), state="readonly")
            elif kind == "account":
                widget = ttk.Combobox(win, textvariable=fields[key], values=account_options)
            elif kind == "bank":
                widget = ttk.Combobox(win, textvariable=fields[key], values=bank_options)
            else:
                widget = ttk.Entry(win, textvariable=fields[key])
            widget.grid(row=idx, column=1, sticky="ew", padx=12, pady=6)
        win.columnconfigure(1, weight=1)
        result = {}

        def code_only(value):
            return str(value or "").split(" - ", 1)[0].strip()

        def save():
            if not fields["period"].get().strip() or not code_only(fields["account_code"].get()):
                messagebox.showwarning("Presupuesto", "Periodo y cuenta contable son obligatorios.", parent=win)
                return
            result.update({key: value.get().strip() for key, value in fields.items()})
            result["account_code"] = code_only(result["account_code"])
            result["funding_bank_account_code"] = code_only(result["funding_bank_account_code"])
            win.destroy()

        footer = ttk.Frame(win)
        footer.grid(row=len(rows), column=0, columnspan=2, sticky="e", padx=12, pady=12)
        ttk.Button(footer, text="Guardar", command=save).pack(side="left", padx=4)
        ttk.Button(footer, text="Cancelar", command=win.destroy).pack(side="left", padx=4)
        self.wait_window(win)
        return result or None

    def _account_options(self):
        try:
            from api_client import get_accounting_accounts_api
            return [f"{row.get('account_code')} - {row.get('account_name')}" for row in get_accounting_accounts_api() if row.get("account_code")]
        except Exception:
            return []

    def _bank_options(self):
        try:
            return [f"{row.get('account_code')} - {row.get('account_name')}" for row in get_accounting_bank_accounts_api() if row.get("account_code")]
        except Exception:
            return []

    def _new_budget(self):
        payload = self._budget_dialog()
        if not payload:
            return
        try:
            upsert_accounting_budget_api(payload)
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Presupuesto", str(exc), parent=self)

    def _edit_budget(self):
        row = self._selected_budget()
        if not row:
            return
        payload = self._budget_dialog(row)
        if not payload:
            return
        try:
            upsert_accounting_budget_api(payload)
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Presupuesto", str(exc), parent=self)

    def _delete_budget(self):
        row = self._selected_budget()
        if not row:
            return
        if not messagebox.askyesno("Presupuesto", f"Eliminar presupuesto/meta {row.get('id')}?", parent=self):
            return
        try:
            delete_accounting_budget_api(row.get("id"))
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Presupuesto", str(exc), parent=self)

    def _contribute_budget(self):
        row = self._selected_budget()
        if not row:
            return
        amount = simpledialog.askfloat("Aporte", "Monto a aportar / ejecutar:", parent=self, minvalue=0.01)
        if not amount:
            return
        reference = simpledialog.askstring("Aporte", "Numero de comprobante / referencia:", parent=self)
        if not reference:
            messagebox.showwarning("Aporte", "La referencia es obligatoria.", parent=self)
            return
        bank_code = row.get("funding_bank_account_code") or ""
        if not bank_code:
            bank_code = simpledialog.askstring("Aporte", "Cuenta contable banco de salida:", parent=self)
        if not bank_code:
            messagebox.showwarning("Aporte", "La cuenta bancaria contable es obligatoria.", parent=self)
            return
        try:
            result = post_accounting_budget_contribution_api(row.get("id"), {
                "amount": amount,
                "currency_code": row.get("currency_code") or "CRC",
                "contribution_date": date.today().isoformat(),
                "bank_account_code": str(bank_code).split(" - ", 1)[0].strip(),
                "reference": reference,
            })
            messagebox.showinfo("Aporte", f"Aporte contabilizado. Asiento: {result.get('entry_id')}", parent=self)
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Aporte", str(exc), parent=self)

    def _export_budget(self):
        path = filedialog.asksaveasfilename(
            parent=self,
            defaultextension=".xlsx",
            initialfile=f"Presupuesto_Ahorro_Metas_{self.period.get()}_{self.purpose.get()}_{self.budget_status.get()}.xlsx",
            filetypes=[("Excel", "*.xlsx")],
        )
        if not path:
            return
        try:
            download_accounting_budget_report_api(
                path,
                period=self.period.get().strip() or None,
                date_from=self.date_from.get().strip() or None,
                date_to=self.date_to.get().strip() or None,
                purpose=self.purpose.get(),
                status=self.budget_status.get(),
            )
            messagebox.showinfo("Exportar", f"Excel generado:\n{path}", parent=self)
        except Exception as exc:
            messagebox.showerror("Exportar", str(exc), parent=self)

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
            "budgets": "No hay presupuestos, ahorros o metas con los filtros actuales.",
            "budget": "No hay presupuesto cargado para este periodo; por eso no existe comparacion budget vs real.",
            "portia": "Pulse Analizar para que PORTIA explique diferencias, alertas y reclasificaciones sugeridas.",
            "alerts": "No hay alertas inteligentes para este periodo.",
            "fx": "No hay saldos abiertos en USD para revaluar.",
        }.get(key, "No hay datos para mostrar.")
