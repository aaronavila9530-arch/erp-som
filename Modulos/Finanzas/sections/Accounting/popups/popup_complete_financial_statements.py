import csv
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from datetime import date

from api_client import (
    get_accounting_complete_financial_statements_api,
    get_accounting_periods_api,
)


class PopupCompleteFinancialStatements(tk.Toplevel):
    def __init__(self, parent, period=None):
        super().__init__(parent)
        self.title("Estados financieros completos")
        self.geometry("1320x780")
        self.minsize(1100, 650)
        self.configure(bg="white")
        self.periods = self._load_periods()
        current = period or date.today().strftime("%Y-%m")
        if current not in self.periods and self.periods:
            current = self.periods[-1]
        self.mode = tk.StringVar(value="PERIOD")
        self.period = tk.StringVar(value=current)
        self.period_from = tk.StringVar(value=current)
        self.period_to = tk.StringVar(value=current)
        self.status = tk.StringVar(value="Listo")
        self.scope = tk.StringVar(value="")
        self.data = {}
        self.trees = {}
        self._build()
        self.after(150, self.refresh)

    def _load_periods(self):
        try:
            periods = get_accounting_periods_api()
            if isinstance(periods, dict):
                periods = periods.get("data", [])
            return list(periods or [])
        except Exception:
            return [date.today().strftime("%Y-%m")]

    def _build(self):
        header = ttk.Frame(self, padding=10)
        header.pack(fill="x")
        ttk.Label(header, text="Estados financieros completos", font=("Segoe UI", 14, "bold")).pack(side="left")
        ttk.Label(header, textvariable=self.scope, foreground="#555").pack(side="left", padx=18)

        filters = ttk.LabelFrame(self, text="Filtros", padding=8)
        filters.pack(fill="x", padx=10, pady=(0, 8))
        ttk.Radiobutton(filters, text="Periodo", value="PERIOD", variable=self.mode, command=self._toggle_mode).grid(row=0, column=0, padx=4)
        self.cmb_period = ttk.Combobox(filters, textvariable=self.period, values=self.periods, width=10, state="readonly")
        self.cmb_period.grid(row=0, column=1, padx=4)
        ttk.Radiobutton(filters, text="Rango", value="RANGE", variable=self.mode, command=self._toggle_mode).grid(row=0, column=2, padx=(16, 4))
        ttk.Label(filters, text="Desde").grid(row=0, column=3, padx=4)
        self.cmb_from = ttk.Combobox(filters, textvariable=self.period_from, values=self.periods, width=10, state="readonly")
        self.cmb_from.grid(row=0, column=4, padx=4)
        ttk.Label(filters, text="Hasta").grid(row=0, column=5, padx=4)
        self.cmb_to = ttk.Combobox(filters, textvariable=self.period_to, values=self.periods, width=10, state="readonly")
        self.cmb_to.grid(row=0, column=6, padx=4)
        ttk.Button(filters, text="Buscar", command=self.refresh).grid(row=0, column=7, padx=(18, 4))
        ttk.Button(filters, text="Exportar pestana CSV", command=self.export_current_tab).grid(row=0, column=8, padx=4)
        ttk.Button(filters, text="Cerrar", command=self.destroy).grid(row=0, column=9, padx=(18, 4))

        self.summary = ttk.LabelFrame(self, text="Resumen ejecutivo", padding=8)
        self.summary.pack(fill="x", padx=10, pady=(0, 8))
        self.summary_vars = {}
        for idx, (key, label) in enumerate((
            ("assets", "Activos"),
            ("liabilities", "Pasivos"),
            ("equity", "Patrimonio + resultado"),
            ("net_income", "Resultado neto"),
            ("cash_flow", "Flujo neto caja"),
            ("iva", "IVA neto documental"),
        )):
            box = ttk.LabelFrame(self.summary, text=label, padding=7)
            box.grid(row=0, column=idx, sticky="nsew", padx=3)
            self.summary.columnconfigure(idx, weight=1)
            var = tk.StringVar(value="0.00")
            ttk.Label(box, textvariable=var, font=("Segoe UI", 11, "bold")).pack()
            self.summary_vars[key] = var

        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True, padx=10, pady=(0, 5))
        self._add_tab("balance_sheet", "Balance general")
        self._add_tab("income_statement", "Estado resultados")
        self._add_tab("cash_flow", "Flujo de caja")
        self._add_tab("equity_changes", "Cambios patrimonio")
        self._add_tab("trial_balance", "Trial balance")
        self._add_tab("general_ledger", "Mayor")
        self._add_tab("journal", "Diario")
        self._add_tab("aging_ar", "Aging CxC")
        self._add_tab("aging_ap", "Aging CxP")
        self._add_tab("tax_summary", "IVA y retenciones")
        self._add_tab("profitability", "Rentabilidad")
        ttk.Label(self, textvariable=self.status, anchor="w").pack(fill="x", padx=12, pady=(0, 7))
        self._toggle_mode()

    def _add_tab(self, key, title):
        frame = ttk.Frame(self.tabs, padding=5)
        self.tabs.add(frame, text=title)
        container = ttk.Frame(frame)
        container.pack(fill="both", expand=True)
        tree = ttk.Treeview(container, show="headings")
        yscroll = ttk.Scrollbar(container, orient="vertical", command=tree.yview)
        xscroll = ttk.Scrollbar(container, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)
        self.trees[key] = tree

    def _toggle_mode(self):
        period_state = "readonly" if self.mode.get() == "PERIOD" else "disabled"
        range_state = "readonly" if self.mode.get() == "RANGE" else "disabled"
        self.cmb_period.configure(state=period_state)
        self.cmb_from.configure(state=range_state)
        self.cmb_to.configure(state=range_state)

    def refresh(self):
        self.status.set("Cargando estados financieros...")
        threading.Thread(target=self._refresh_worker, daemon=True).start()

    def _refresh_worker(self):
        try:
            kwargs = {}
            if self.mode.get() == "PERIOD":
                kwargs["period"] = self.period.get()
            else:
                kwargs["period_from"] = self.period_from.get()
                kwargs["period_to"] = self.period_to.get()
            data = get_accounting_complete_financial_statements_api(**kwargs)
            self.after(0, self._apply_data, data)
        except Exception as exc:
            self.after(0, self._error, str(exc))

    def _error(self, message):
        self.status.set("Error")
        messagebox.showerror("Estados financieros", message, parent=self)

    def _apply_data(self, data):
        self.data = data or {}
        scope = self.data.get("scope") or {}
        self.scope.set(f"{scope.get('label','')} | Base: {scope.get('basis','')}")
        bs = self.data.get("balance_sheet", {}).get("totals", {})
        er = self.data.get("income_statement", {}).get("totals", {})
        cf = self.data.get("cash_flow", {}).get("totals", {})
        tax = self.data.get("tax_summary", {}).get("iva", {})
        self.summary_vars["assets"].set(self._money(bs.get("assets")))
        self.summary_vars["liabilities"].set(self._money(bs.get("liabilities")))
        self.summary_vars["equity"].set(self._money(bs.get("equity_plus_result")))
        self.summary_vars["net_income"].set(self._money(er.get("net_income")))
        self.summary_vars["cash_flow"].set(self._money(cf.get("net_cash_flow")))
        self.summary_vars["iva"].set(self._money(tax.get("net_documental")))
        self._render_all()
        self.status.set("Estados financieros actualizados")

    def _render_all(self):
        self._render("balance_sheet", ("section", "account_code", "account_name", "balance"), self._balance_rows())
        self._render("income_statement", ("section", "account_code", "account_name", "balance"), self._income_rows())
        self._render("cash_flow", ("section", "account_code", "account_name", "cash_movement"), self.data.get("cash_flow", {}).get("rows", []))
        self._render("equity_changes", ("account_code", "account_name", "opening", "movement", "ending"), self.data.get("equity_changes", {}).get("rows", []))
        self._render("trial_balance", ("account_code", "account_name", "period_debit", "period_credit", "debit_balance", "credit_balance"), self.data.get("trial_balance", {}).get("rows", []))
        self._render("general_ledger", ("account_code", "account_name", "entry_date", "entry_id", "origin", "description", "debit", "credit", "running_balance"), self.data.get("general_ledger", {}).get("rows", []))
        self._render("journal", ("entry_date", "entry_id", "period", "origin", "description", "account_code", "account_name", "debit", "credit"), self.data.get("journal", {}).get("rows", []))
        self._render("aging_ar", ("entity_code", "entity_name", "document_number", "due_date", "days_due", "bucket", "currency_code", "open_amount"), self.data.get("aging_ar", {}).get("rows", []))
        self._render("aging_ap", ("entity_code", "entity_name", "document_number", "due_date", "days_due", "bucket", "currency_code", "open_amount"), self.data.get("aging_ap", {}).get("rows", []))
        self._render("tax_summary", ("section", "account_code", "account_name", "balance"), self._tax_rows())
        self._render("profitability", ("client", "service", "services_count", "revenue", "direct_cost", "gross_profit", "margin_pct"), self.data.get("profitability", {}).get("rows", []))

    def _balance_rows(self):
        rows = []
        sections = self.data.get("balance_sheet", {}).get("sections", {})
        for label, key in (("Activos", "assets"), ("Pasivos", "liabilities"), ("Patrimonio", "equity")):
            for row in sections.get(key, []):
                rows.append({"section": label, **row})
        totals = self.data.get("balance_sheet", {}).get("totals", {})
        rows.append({"section": "Resultado acumulado", "account_code": "", "account_name": "Resultado del periodo sin cierre", "balance": totals.get("current_result")})
        rows.append({"section": "Control", "account_code": "", "account_name": "Diferencia Activo - Pasivo - Patrimonio", "balance": totals.get("difference")})
        return rows

    def _income_rows(self):
        rows = []
        for row in self.data.get("income_statement", {}).get("revenue", []):
            rows.append({"section": "Ingresos", **row})
        for row in self.data.get("income_statement", {}).get("expenses", []):
            rows.append({"section": "Gastos / costos", **row})
        totals = self.data.get("income_statement", {}).get("totals", {})
        rows.append({"section": "Resultado", "account_code": "", "account_name": "Resultado neto", "balance": totals.get("net_income")})
        return rows

    def _tax_rows(self):
        rows = []
        for row in self.data.get("tax_summary", {}).get("accounts", []):
            rows.append({"section": "Mayor contable", **row})
        iva = self.data.get("tax_summary", {}).get("iva", {})
        for key, label in (
            ("debit_fiscal", "IVA debito fiscal"),
            ("credit_fiscal", "IVA credito fiscal"),
            ("net_documental", "IVA neto documental"),
            ("net_accounting", "IVA neto contable"),
            ("difference", "Diferencia IVA"),
        ):
            rows.append({"section": "Resumen IVA", "account_code": "", "account_name": label, "balance": iva.get(key)})
        ret = self.data.get("tax_summary", {}).get("retentions", {})
        rows.append({"section": "Retenciones", "account_code": "", "account_name": "Saldo retenciones", "balance": ret.get("balance")})
        return rows

    def _render(self, key, columns, rows):
        tree = self.trees[key]
        tree.delete(*tree.get_children())
        tree["columns"] = columns
        for col in columns:
            tree.heading(col, text=col.replace("_", " ").title())
            width = 120
            if col in {"account_name", "description", "entity_name", "client", "service"}:
                width = 260
            elif col in {"entry_id", "period", "bucket", "origin"}:
                width = 95
            tree.column(col, width=width, anchor="e" if col in {"debit", "credit", "balance", "open_amount", "revenue", "direct_cost", "gross_profit", "cash_movement", "running_balance", "period_debit", "period_credit", "debit_balance", "credit_balance", "margin_pct"} else "w")
        for row in rows or []:
            values = [self._cell(row.get(col)) for col in columns]
            tree.insert("", "end", values=values)

    def export_current_tab(self):
        tab_id = self.tabs.select()
        if not tab_id:
            return
        key = next((name for name, tree in self.trees.items() if str(tree.master.master) == tab_id), None)
        if not key:
            index = self.tabs.index(tab_id)
            key = list(self.trees.keys())[index]
        tree = self.trees[key]
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Exportar CSV",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile=f"{key}_{self.period.get() or self.period_from.get()}.csv",
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8-sig") as fh:
            writer = csv.writer(fh)
            writer.writerow(tree["columns"])
            for item in tree.get_children():
                writer.writerow(tree.item(item, "values"))
        messagebox.showinfo("Estados financieros", "CSV exportado correctamente.", parent=self)

    def _cell(self, value):
        if isinstance(value, float):
            return self._money(value)
        return "" if value is None else value

    def _money(self, value):
        try:
            return f"{float(value or 0):,.2f}"
        except Exception:
            return "0.00"
