import tkinter as tk
from tkinter import ttk, messagebox

from api_client import (
    hr_salary_calculator_calculate_api,
    hr_salary_calculator_history_api,
    hr_salary_calculator_rules_api,
)


SCENARIOS = {"EMPLOYEE": "Asalariado", "INDEPENDENT": "Independiente", "OWNER": "Dueño de empresa"}
DISTRIBUTIONS = {"NONE": "No aplica", "DIETAS": "Dietas", "DIVIDENDS": "Dividendos"}
LABELS = {
    "gross_salary": "Salario bruto",
    "worker_contributions_total": "Total deducciones trabajador",
    "salary_income_tax": "Impuesto al salario",
    "net_salary": "Salario neto",
    "employer_contributions_total": "Total aporte patronal",
    "total_company_cost": "Costo total empresa",
    "monthly_invoice_subtotal": "Subtotal factura mensual",
    "vat_13": "IVA 13%",
    "monthly_invoice_total": "Total factura con IVA",
    "deductible_expenses_total": "Total gastos deducibles",
    "deductible_expenses_total_monthly": "Total gastos deducibles mensual",
    "net_before_ccss": "Ingreso neto antes de CCSS",
    "ccss_rate": "Tasa CCSS",
    "ccss_independent": "CCSS independiente",
    "taxable_income_monthly_reference": "Base imponible mensual ref.",
    "taxable_income_annual_reference": "Base imponible anual ref.",
    "annual_income_tax": "Renta anual",
    "monthly_income_tax_reference": "Renta mensual ref.",
    "net_after_ccss_and_tax_monthly_reference": "Neto mensual ref.",
    "monthly_gross_income": "Ingreso bruto mensual",
    "monthly_income_total_with_vat": "Ingreso mensual con IVA",
    "annual_gross_income": "Ingreso bruto anual",
    "distribution_type": "Tipo de pago socio",
    "distribution_gross_monthly": "Monto bruto dietas/dividendos",
    "distribution_withholding_15": "Retencion 15%",
    "distribution_net_monthly": "Neto despues del 15%",
    "distribution_is_deductible": "Deducible para empresa",
    "annual_net_taxable_income": "Renta neta imponible anual",
    "corporate_regime": "Regimen renta juridica",
    "base_corporate_income_tax": "Impuesto base",
    "pyme_exemption_rate": "Exoneracion PYME",
    "annual_corporate_income_tax": "Renta juridica anual",
    "monthly_corporate_income_tax_reference": "Renta juridica mensual ref.",
}


def _fmt(value):
    try:
        return f"CRC {float(value or 0):,.2f}"
    except Exception:
        return str(value or "")


class VistaCalculadoraSalarial(ttk.Frame):
    def __init__(self, parent, usuario=None, rol=None):
        super().__init__(parent)
        self.usuario = usuario
        self.rol = rol
        self.rules = {}
        self.expense_rows = []
        self.expense_combos = []
        self.expense_lists = []
        self._build_ui()
        self._load_rules()
        self._load_history()

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        header = ttk.Frame(self)
        header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 6))
        ttk.Label(header, text="Calculadora salarial", font=("Segoe UI", 14, "bold")).pack(side="left")
        ttk.Button(header, text="Historial", command=self._load_history).pack(side="right")

        body = ttk.PanedWindow(self, orient="horizontal")
        body.grid(row=1, column=0, sticky="nsew", padx=10, pady=6)
        left = ttk.Frame(body)
        right = ttk.Frame(body)
        body.add(left, weight=1)
        body.add(right, weight=1)
        left.columnconfigure(0, weight=1)
        left.rowconfigure(0, weight=1)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)

        self.tabs = ttk.Notebook(left)
        self.tabs.grid(row=0, column=0, sticky="nsew")
        self.employee_vars = {"amount": tk.StringVar(value="0"), "label": tk.StringVar()}
        self.independent_vars = {
            "amount": tk.StringVar(value="0"),
            "vehicle_debt_amount": tk.StringVar(value="0"),
            "vehicle_purchase_year": tk.StringVar(value=str(self._current_year())),
            "vehicle_useful_life_years": tk.StringVar(value="10"),
            "vehicle_monthly_payment": tk.StringVar(value="0"),
            "label": tk.StringVar(),
        }
        self.owner_vars = {
            "amount": tk.StringVar(value="0"),
            "vehicle_debt_amount": tk.StringVar(value="0"),
            "vehicle_purchase_year": tk.StringVar(value=str(self._current_year())),
            "vehicle_useful_life_years": tk.StringVar(value="10"),
            "vehicle_monthly_payment": tk.StringVar(value="0"),
            "distribution_type": tk.StringVar(value="NONE"),
            "is_pyme": tk.BooleanVar(value=False),
            "pyme_year": tk.StringVar(value="1"),
            "label": tk.StringVar(),
        }

        self._build_employee_tab()
        self._build_independent_tab()
        self._build_owner_tab()

        actions = ttk.Frame(left)
        actions.grid(row=1, column=0, sticky="ew", pady=8)
        ttk.Button(actions, text="Calcular", command=lambda: self._calculate(False)).pack(side="left", padx=4)
        ttk.Button(actions, text="Calcular y guardar", command=lambda: self._calculate(True)).pack(side="left", padx=4)
        ttk.Button(actions, text="Limpiar gastos", command=self._clear_expenses).pack(side="left", padx=4)

        result_box = ttk.LabelFrame(right, text="Resultado")
        result_box.grid(row=0, column=0, sticky="nsew")
        result_box.rowconfigure(0, weight=1)
        result_box.columnconfigure(0, weight=1)
        self.result = tk.Text(result_box, height=24, wrap="word")
        self.result.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(result_box, command=self.result.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.result.configure(yscrollcommand=scroll.set)

        history_box = ttk.LabelFrame(right, text="Historial")
        history_box.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        self.history = ttk.Treeview(history_box, columns=("id", "scenario", "label", "created_at"), show="headings", height=6)
        for col, title, width in (("id", "#", 50), ("scenario", "Escenario", 120), ("label", "Etiqueta", 180), ("created_at", "Fecha", 150)):
            self.history.heading(col, text=title)
            self.history.column(col, width=width)
        self.history.pack(fill="x")

    def _current_year(self):
        from datetime import datetime
        return datetime.now().year

    def _year_values(self, start=1995):
        return [str(year) for year in range(self._current_year(), start - 1, -1)]

    def _field(self, parent, row, label, var):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=6, pady=4)
        ttk.Entry(parent, textvariable=var, width=24).grid(row=row, column=1, sticky="ew", padx=6, pady=4)

    def _combo_field(self, parent, row, label, var, values):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=6, pady=4)
        ttk.Combobox(parent, textvariable=var, values=values, state="readonly").grid(row=row, column=1, sticky="ew", padx=6, pady=4)

    def _build_employee_tab(self):
        tab = ttk.Frame(self.tabs)
        tab.columnconfigure(1, weight=1)
        self.tabs.add(tab, text="Asalariado")
        self._field(tab, 0, "Etiqueta", self.employee_vars["label"])
        self._field(tab, 1, "Salario mensual bruto", self.employee_vars["amount"])
        ttk.Label(tab, text="Calcula deducciones del trabajador, cargas patronales y renta salarial 2026.").grid(row=2, column=0, columnspan=2, sticky="w", padx=6, pady=8)

    def _expense_editor(self, parent, row):
        box = ttk.LabelFrame(parent, text="Gastos deducibles")
        box.grid(row=row, column=0, columnspan=2, sticky="nsew", padx=6, pady=8)
        box.columnconfigure(1, weight=1)
        ttk.Label(box, text="Rubro").grid(row=0, column=0, sticky="w", padx=4)
        ttk.Label(box, text="Monto").grid(row=0, column=1, sticky="w", padx=4)
        ttk.Label(box, text="Año compra").grid(row=0, column=2, sticky="w", padx=4)
        ttk.Label(box, text="Vida útil").grid(row=0, column=3, sticky="w", padx=4)
        ttk.Label(box, text="Nota").grid(row=0, column=4, sticky="w", padx=4)
        category = tk.StringVar()
        amount = tk.StringVar(value="0")
        purchase_year = tk.StringVar()
        useful_life = tk.StringVar(value="10")
        note = tk.StringVar()
        combo = ttk.Combobox(box, textvariable=category, values=[], state="normal", width=22)
        combo.grid(row=1, column=0, padx=4, pady=4)
        ttk.Entry(box, textvariable=amount, width=14).grid(row=1, column=1, padx=4, pady=4, sticky="ew")
        ttk.Combobox(box, textvariable=purchase_year, values=[""] + self._year_values(), state="readonly", width=10).grid(row=1, column=2, padx=4, pady=4)
        ttk.Entry(box, textvariable=useful_life, width=8).grid(row=1, column=3, padx=4, pady=4)
        ttk.Entry(box, textvariable=note, width=18).grid(row=1, column=4, padx=4, pady=4)
        ttk.Button(box, text="Agregar", command=lambda: self._add_expense(category, amount, purchase_year, useful_life, note)).grid(row=1, column=5, padx=4, pady=4)
        frame = ttk.Frame(box)
        frame.grid(row=2, column=0, columnspan=6, sticky="nsew", padx=4, pady=4)
        frame.columnconfigure(0, weight=1)
        listbox = tk.Listbox(frame, height=6)
        listbox.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(frame, orient="vertical", command=listbox.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        listbox.configure(yscrollcommand=scroll.set)
        self.expense_combos.append((combo, category))
        self.expense_lists.append(listbox)

    def _build_independent_tab(self):
        tab = ttk.Frame(self.tabs)
        tab.columnconfigure(1, weight=1)
        self.tabs.add(tab, text="Independiente")
        self._field(tab, 0, "Etiqueta", self.independent_vars["label"])
        self._field(tab, 1, "Monto mensual a facturar sin IVA", self.independent_vars["amount"])
        self._field(tab, 2, "Monto deuda vehicular / costo original", self.independent_vars["vehicle_debt_amount"])
        self._combo_field(tab, 3, "Año compra vehículo", self.independent_vars["vehicle_purchase_year"], self._year_values())
        self._field(tab, 4, "Vida útil vehículo en años", self.independent_vars["vehicle_useful_life_years"])
        self._field(tab, 5, "Cuota vehicular mensual", self.independent_vars["vehicle_monthly_payment"])
        self._expense_editor(tab, 6)

    def _build_owner_tab(self):
        tab = ttk.Frame(self.tabs)
        tab.columnconfigure(1, weight=1)
        self.tabs.add(tab, text="Dueño de empresa")
        self._field(tab, 0, "Etiqueta", self.owner_vars["label"])
        self._field(tab, 1, "Ingreso bruto mensual empresa sin IVA", self.owner_vars["amount"])
        self._combo_field(tab, 2, "Tipo pago socio", self.owner_vars["distribution_type"], ["NONE", "DIETAS", "DIVIDENDS"])
        ttk.Label(tab, text="El sistema calcula automaticamente el 15% y el neto de dietas/dividendos sobre el ingreso mensual.").grid(row=3, column=0, columnspan=2, sticky="w", padx=6, pady=4)
        ttk.Checkbutton(tab, text="PYME registrada", variable=self.owner_vars["is_pyme"]).grid(row=4, column=0, sticky="w", padx=6, pady=4)
        self._combo_field(tab, 5, "Año PYME", self.owner_vars["pyme_year"], ["1", "2", "3", "4", "5", "6"])
        self._field(tab, 6, "Monto deuda vehicular / costo original", self.owner_vars["vehicle_debt_amount"])
        self._combo_field(tab, 7, "Año compra vehículo", self.owner_vars["vehicle_purchase_year"], self._year_values())
        self._field(tab, 8, "Vida útil vehículo en años", self.owner_vars["vehicle_useful_life_years"])
        self._field(tab, 9, "Cuota vehicular mensual", self.owner_vars["vehicle_monthly_payment"])
        self._expense_editor(tab, 10)

    def _load_rules(self):
        try:
            self.rules = hr_salary_calculator_rules_api()
            categories = self.rules.get("expense_categories") or []
            for combo, var in self.expense_combos:
                combo.configure(values=categories)
                if categories and not var.get():
                    var.set(categories[0])
        except Exception as exc:
            messagebox.showwarning("Calculadora salarial", f"No se pudieron cargar reglas: {exc}")

    def _num(self, value):
        try:
            return float(str(value or "0").replace(",", "").strip() or 0)
        except Exception:
            return 0.0

    def _int_or_none(self, value):
        try:
            return int(float(str(value or "").strip()))
        except Exception:
            return None

    def _add_expense(self, category_var, amount_var, purchase_year_var, useful_life_var, note_var):
        category = category_var.get().strip() or "Otro gasto deducible"
        amount = self._num(amount_var.get())
        purchase_year = self._int_or_none(purchase_year_var.get())
        useful_life = self._int_or_none(useful_life_var.get())
        note = note_var.get().strip() or None
        row = {"category": category, "amount": amount, "note": note, "purchase_year": purchase_year, "useful_life_years": useful_life}
        self.expense_rows.append(row)
        text = f"{category}: {_fmt(amount)}"
        if purchase_year:
            text += f" | compra {purchase_year} | vida útil {useful_life or 10} años"
        for listbox in self.expense_lists:
            listbox.insert("end", text)
            listbox.yview_moveto(1)
        amount_var.set("0")
        note_var.set("")
        purchase_year_var.set("")

    def _clear_expenses(self):
        self.expense_rows.clear()
        for listbox in self.expense_lists:
            listbox.delete(0, "end")

    def _payload(self, save):
        index = self.tabs.index(self.tabs.select())
        if index == 0:
            return {"scenario": "EMPLOYEE", "amount": self._num(self.employee_vars["amount"].get()), "label": self.employee_vars["label"].get().strip() or None, "save": save}
        if index == 1:
            return {
                "scenario": "INDEPENDENT",
                "amount": self._num(self.independent_vars["amount"].get()),
                "vehicle_debt_amount": self._num(self.independent_vars["vehicle_debt_amount"].get()),
                "vehicle_purchase_year": self._int_or_none(self.independent_vars["vehicle_purchase_year"].get()),
                "vehicle_useful_life_years": int(self._num(self.independent_vars["vehicle_useful_life_years"].get()) or 10),
                "vehicle_monthly_payment": self._num(self.independent_vars["vehicle_monthly_payment"].get()),
                "expenses": self.expense_rows,
                "label": self.independent_vars["label"].get().strip() or None,
                "save": save,
            }
        return {
            "scenario": "OWNER",
            "amount": self._num(self.owner_vars["amount"].get()),
            "vehicle_debt_amount": self._num(self.owner_vars["vehicle_debt_amount"].get()),
            "vehicle_purchase_year": self._int_or_none(self.owner_vars["vehicle_purchase_year"].get()),
            "vehicle_useful_life_years": int(self._num(self.owner_vars["vehicle_useful_life_years"].get()) or 10),
            "vehicle_monthly_payment": self._num(self.owner_vars["vehicle_monthly_payment"].get()),
            "distribution_type": self.owner_vars["distribution_type"].get(),
            "distribution_amount": 0,
            "is_pyme": bool(self.owner_vars["is_pyme"].get()),
            "pyme_year": int(self._num(self.owner_vars["pyme_year"].get()) or 0),
            "expenses": self.expense_rows,
            "label": self.owner_vars["label"].get().strip() or None,
            "save": save,
        }

    def _calculate(self, save):
        try:
            data = hr_salary_calculator_calculate_api(self._payload(save))
            self._render_result(data)
            if save:
                self._load_history()
        except Exception as exc:
            messagebox.showerror("Calculadora salarial", str(exc))

    def _label(self, key):
        return LABELS.get(key, key.replace("_", " ").title())

    def _render_result(self, data):
        self.result.delete("1.0", "end")
        scenario = SCENARIOS.get(data.get("scenario"), data.get("scenario"))
        lines = [f"Escenario: {scenario}", f"Regla: {data.get('rule_version')}", ""]
        for key, value in data.items():
            if key in {"scenario", "rule_version", "currency", "disclaimer"}:
                continue
            if isinstance(value, list):
                lines.append(self._label(key))
                for item in value:
                    if isinstance(item, dict):
                        name = item.get("name") or item.get("category") or f"{item.get('from')} - {item.get('to')}"
                        amount = item.get("amount", item.get("tax", ""))
                        rate = item.get("rate")
                        suffix = f" ({rate:.2%})" if isinstance(rate, (int, float)) else ""
                        extra = ""
                        if item.get("remaining_book_value") is not None:
                            extra = f" | saldo libro {_fmt(item.get('remaining_book_value'))}"
                        lines.append(f"  - {name}: {_fmt(amount)}{suffix}{extra}")
                lines.append("")
            elif isinstance(value, (int, float)):
                if key.endswith("_rate"):
                    lines.append(f"{self._label(key)}: {value:.2%}")
                else:
                    lines.append(f"{self._label(key)}: {_fmt(value)}")
            else:
                label_value = DISTRIBUTIONS.get(value, value) if key == "distribution_type" else value
                lines.append(f"{self._label(key)}: {label_value}")
        lines.append("")
        lines.append(str(data.get("disclaimer") or ""))
        self.result.insert("1.0", "\n".join(lines))

    def _load_history(self):
        try:
            payload = hr_salary_calculator_history_api()
            rows = payload.get("data", [])
            self.history.delete(*self.history.get_children())
            for row in rows:
                self.history.insert("", "end", values=(row.get("id"), SCENARIOS.get(row.get("scenario"), row.get("scenario")), row.get("label") or "", row.get("created_at")))
        except Exception:
            pass
