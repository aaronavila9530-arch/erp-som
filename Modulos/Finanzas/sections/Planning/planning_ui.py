import threading
import tkinter as tk
from datetime import date
from tkinter import ttk, messagebox

from api_client import (
    create_finance_planning_project_api,
    delete_finance_planning_project_api,
    get_finance_planning_summary_api,
    update_finance_planning_project_api,
)


class FinancePlanningUI(tk.Frame):
    def __init__(self, parent, period=None):
        super().__init__(parent, bg="white")
        self.period = tk.StringVar(value=period or date.today().strftime("%Y-%m"))
        self.months = tk.StringVar(value="4")
        self.status = tk.StringVar(value="Presione Buscar para consultar PLN.")
        self.scenario_revenue = tk.StringVar(value="0")
        self.scenario_expense = tk.StringVar(value="0")
        self.scenario_saving = tk.StringVar(value="0")
        self.scenario_result = tk.StringVar(value="Cargue PLN para comparar contra el periodo.")
        self.last_payload = {}
        self.trees = {}
        self._build()

    def _build(self):
        header = tk.Frame(self, bg="white")
        header.pack(fill="x", padx=12, pady=(8, 4))
        title = tk.Frame(header, bg="white")
        title.pack(side="left", fill="x", expand=True)
        tk.Label(title, text="PLN / Planificación financiera", bg="white", font=("Segoe UI", 16, "bold")).pack(anchor="w")
        tk.Label(
            title,
            text="Planificación de caja, obligaciones, gastos, metas, proyectos, ahorros y escenarios.",
            bg="white",
            fg="#607086",
        ).pack(anchor="w")
        controls = ttk.Frame(header)
        controls.pack(side="right")
        ttk.Label(controls, text="Periodo").grid(row=0, column=0, padx=(0, 4))
        ttk.Entry(controls, textvariable=self.period, width=10).grid(row=0, column=1, padx=(0, 10))
        ttk.Label(controls, text="Meses").grid(row=0, column=2, padx=(0, 4))
        ttk.Combobox(controls, textvariable=self.months, values=("1", "2", "3", "4", "6", "12"), width=5, state="readonly").grid(row=0, column=3, padx=(0, 10))
        ttk.Button(controls, text="Buscar", command=self.search).grid(row=0, column=4, padx=4)
        ttk.Button(controls, text="Agregar proyecto", command=self._new_project).grid(row=0, column=5, padx=4)
        ttk.Button(controls, text="Modificar", command=self._edit_project).grid(row=0, column=6, padx=4)
        ttk.Button(controls, text="Eliminar", command=self._delete_project).grid(row=0, column=7, padx=4)
        ttk.Label(self, textvariable=self.status, background="white", foreground="#475467").pack(anchor="w", padx=14)

        self.kpis = tk.Frame(self, bg="white")
        self.kpis.pack(fill="x", padx=12, pady=8)

        scenario = ttk.LabelFrame(self, text="Comparador rápido")
        scenario.pack(fill="x", padx=12, pady=(0, 8))
        ttk.Label(scenario, text="Ingreso %").grid(row=0, column=0, padx=8, pady=8, sticky="w")
        ttk.Entry(scenario, textvariable=self.scenario_revenue, width=8).grid(row=0, column=1, padx=(0, 12), pady=8)
        ttk.Label(scenario, text="Gasto %").grid(row=0, column=2, padx=8, pady=8, sticky="w")
        ttk.Entry(scenario, textvariable=self.scenario_expense, width=8).grid(row=0, column=3, padx=(0, 12), pady=8)
        ttk.Label(scenario, text="Ahorro extra").grid(row=0, column=4, padx=8, pady=8, sticky="w")
        ttk.Entry(scenario, textvariable=self.scenario_saving, width=12).grid(row=0, column=5, padx=(0, 12), pady=8)
        ttk.Button(scenario, text="Comparar escenario", command=self._calculate_scenario).grid(row=0, column=6, padx=8, pady=8)
        ttk.Label(scenario, textvariable=self.scenario_result, foreground="#334155").grid(row=0, column=7, padx=8, pady=8, sticky="w")
        scenario.columnconfigure(7, weight=1)

        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self._add_tree("obligation_buckets", "Calendario ITP", ("currency", "bucket", "count", "amount"))
        self._add_tree("profitability", "Rentabilidad", ("metric", "value"))
        self._add_tree("obligations", "Obligaciones", ("id", "payee_name", "obligation_type", "due_date", "currency", "balance", "status", "origin"))
        self._add_tree("applied_payments", "Pagos aplicados", ("currency", "count", "amount"))
        self._add_tree("expenses", "Gastos Accounting", ("period", "account_code", "account_name", "actual_amount"))
        self._add_tree("goals", "Metas / ahorros", ("id", "period", "purpose", "name", "account_code", "currency_code", "target_amount", "progress_amount", "progress_pct", "target_date", "status"))
        self._add_tree("projects", "Proyectos", ("id", "name", "client_name", "status", "priority", "target_date", "currency_code", "expected_revenue", "expected_cost", "expected_profit", "expected_margin_pct", "monthly_savings"))
        self._add_tree("project_schedule", "Cronograma", ("due_date", "concept", "direction", "currency_code", "amount", "status", "project_id"))
        self._add_tree("monthly_plan", "Ahorro mensual", ("month", "currency_code", "planned_inflow", "planned_outflow", "planned_saving"))
        self._add_tree("alerts", "Alertas", ("severity", "code", "message"))
        self.search()

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
        self.last_payload = payload or {}
        totals = payload.get("totals") or {}
        self._render_kpis(totals, payload)
        profitability = payload.get("profitability") or {}
        payload["profitability"] = [
            {"metric": "Ingresos", "value": profitability.get("revenue")},
            {"metric": "Gastos", "value": profitability.get("expenses")},
            {"metric": "Utilidad", "value": profitability.get("profit")},
            {"metric": "Margen %", "value": profitability.get("margin_pct")},
        ]
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
        self._calculate_scenario()

    def _render_kpis(self, totals, payload):
        for widget in self.kpis.winfo_children():
            widget.destroy()
        pending = totals.get("pending_by_currency") or {}
        cards = [
            ("Pendiente ITP", " | ".join(f"{cur} {self._money(amount)}" for cur, amount in pending.items()) or "0.00"),
            ("Lineas", totals.get("obligation_lines", 0)),
            ("Metas activas", totals.get("goals_active", 0)),
            ("Proyectos", totals.get("projects", 0)),
            ("Utilidad proyectos", self._money(totals.get("project_expected_profit"))),
            ("Ahorro mensual", self._money(totals.get("monthly_savings"))),
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

    def _calculate_scenario(self):
        payload = self.last_payload or {}
        profitability = payload.get("profitability") or {}
        totals = payload.get("totals") or {}
        try:
            revenue = float(profitability.get("revenue") or 0)
            expenses = float(profitability.get("expenses") or 0)
            savings = float(totals.get("monthly_savings") or 0)
            revenue_pct = float(self.scenario_revenue.get() or 0) / 100
            expense_pct = float(self.scenario_expense.get() or 0) / 100
            extra_saving = float(self.scenario_saving.get() or 0)
        except Exception:
            self.scenario_result.set("Revise los porcentajes del escenario.")
            return
        scenario_revenue = revenue * (1 + revenue_pct)
        scenario_expenses = expenses * (1 + expense_pct)
        scenario_profit = scenario_revenue - scenario_expenses
        margin = (scenario_profit / scenario_revenue * 100) if scenario_revenue else 0
        self.scenario_result.set(
            f"Utilidad {self._money(scenario_profit)} · margen {margin:.2f}% · ahorro mensual {self._money(savings + extra_saving)}"
        )

    def _selected_project(self):
        tree = self.trees.get("projects")
        selected = tree.focus() if tree else ""
        if not selected:
            messagebox.showwarning("PLN", "Seleccione un proyecto.", parent=self)
            return None
        values = tree.item(selected, "values")
        return dict(zip(tree["columns"], values))

    def _project_dialog(self, initial=None):
        initial = initial or {}
        win = tk.Toplevel(self)
        win.title("Proyecto PLN")
        win.geometry("620x560")
        win.transient(self)
        win.grab_set()
        fields = {
            "name": tk.StringVar(value=initial.get("name") or ""),
            "client_name": tk.StringVar(value=initial.get("client_name") or ""),
            "owner": tk.StringVar(value=initial.get("owner") or ""),
            "start_date": tk.StringVar(value=initial.get("start_date") or date.today().isoformat()),
            "target_date": tk.StringVar(value=initial.get("target_date") or date.today().isoformat()),
            "currency_code": tk.StringVar(value=initial.get("currency_code") or "USD"),
            "expected_revenue": tk.StringVar(value=initial.get("expected_revenue") or "0"),
            "expected_cost": tk.StringVar(value=initial.get("expected_cost") or "0"),
            "monthly_savings": tk.StringVar(value=initial.get("monthly_savings") or "0"),
            "probability_pct": tk.StringVar(value=initial.get("probability_pct") or "100"),
            "status": tk.StringVar(value=initial.get("status") or "PLANNED"),
            "priority": tk.StringVar(value=initial.get("priority") or "MEDIUM"),
            "notes": tk.StringVar(value=initial.get("notes") or ""),
        }
        rows = [
            ("Nombre", "name", "entry"),
            ("Cliente", "client_name", "entry"),
            ("Responsable", "owner", "entry"),
            ("Inicio", "start_date", "entry"),
            ("Fecha objetivo", "target_date", "entry"),
            ("Moneda", "currency_code", "currency"),
            ("Ingreso esperado", "expected_revenue", "entry"),
            ("Costo esperado", "expected_cost", "entry"),
            ("Ahorro mensual", "monthly_savings", "entry"),
            ("Probabilidad %", "probability_pct", "entry"),
            ("Estado", "status", "status"),
            ("Prioridad", "priority", "priority"),
            ("Notas", "notes", "entry"),
        ]
        for idx, (label, key, kind) in enumerate(rows):
            ttk.Label(win, text=label).grid(row=idx, column=0, sticky="w", padx=12, pady=6)
            if kind == "currency":
                widget = ttk.Combobox(win, textvariable=fields[key], values=("USD", "CRC"), state="readonly")
            elif kind == "status":
                widget = ttk.Combobox(win, textvariable=fields[key], values=("PLANNED", "ACTIVE", "PAUSED", "DONE", "CANCELLED"), state="readonly")
            elif kind == "priority":
                widget = ttk.Combobox(win, textvariable=fields[key], values=("LOW", "MEDIUM", "HIGH", "CRITICAL"), state="readonly")
            else:
                widget = ttk.Entry(win, textvariable=fields[key])
            widget.grid(row=idx, column=1, sticky="ew", padx=12, pady=6)
        win.columnconfigure(1, weight=1)
        result = {}

        def save():
            if not fields["name"].get().strip():
                messagebox.showwarning("PLN", "Nombre es obligatorio.", parent=win)
                return
            result.update({key: value.get().strip() for key, value in fields.items()})
            win.destroy()

        footer = ttk.Frame(win)
        footer.grid(row=len(rows), column=0, columnspan=2, sticky="e", padx=12, pady=12)
        ttk.Button(footer, text="Guardar", command=save).pack(side="left", padx=4)
        ttk.Button(footer, text="Cancelar", command=win.destroy).pack(side="left", padx=4)
        self.wait_window(win)
        return result or None

    def _new_project(self):
        payload = self._project_dialog()
        if not payload:
            return
        try:
            create_finance_planning_project_api(payload)
            self.search()
        except Exception as exc:
            messagebox.showerror("PLN", str(exc), parent=self)

    def _edit_project(self):
        row = self._selected_project()
        if not row:
            return
        payload = self._project_dialog(row)
        if not payload:
            return
        try:
            update_finance_planning_project_api(row.get("id"), payload)
            self.search()
        except Exception as exc:
            messagebox.showerror("PLN", str(exc), parent=self)

    def _delete_project(self):
        row = self._selected_project()
        if not row:
            return
        if not messagebox.askyesno("PLN", f"Eliminar proyecto {row.get('name')}?", parent=self):
            return
        try:
            delete_finance_planning_project_api(row.get("id"))
            self.search()
        except Exception as exc:
            messagebox.showerror("PLN", str(exc), parent=self)
