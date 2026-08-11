import tkinter as tk
from tkinter import ttk, messagebox

from api_client import (
    hr_salary_calculator_calculate_api,
    hr_salary_calculator_history_api,
    hr_salary_calculator_rules_api,
)


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
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)

        self.tabs = ttk.Notebook(left)
        self.tabs.grid(row=0, column=0, sticky="nsew")

        self.employee_vars = {"amount": tk.StringVar(value="0"), "label": tk.StringVar()}
        self.independent_vars = {
            "amount": tk.StringVar(value="0"),
            "vehicle_debt_amount": tk.StringVar(value="0"),
            "vehicle_monthly_payment": tk.StringVar(value="0"),
            "label": tk.StringVar(),
        }
        self.owner_vars = {
            "amount": tk.StringVar(value="0"),
            "vehicle_debt_amount": tk.StringVar(value="0"),
            "vehicle_monthly_payment": tk.StringVar(value="0"),
            "distribution_type": tk.StringVar(value="NONE"),
            "distribution_amount": tk.StringVar(value="0"),
            "is_pyme": tk.BooleanVar(value=False),
            "pyme_year": tk.StringVar(value="0"),
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

    def _field(self, parent, row, label, var):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=6, pady=4)
        ttk.Entry(parent, textvariable=var, width=24).grid(row=row, column=1, sticky="ew", padx=6, pady=4)

    def _build_employee_tab(self):
        tab = ttk.Frame(self.tabs)
        tab.columnconfigure(1, weight=1)
        self.tabs.add(tab, text="Asalariado")
        self._field(tab, 0, "Etiqueta", self.employee_vars["label"])
        self._field(tab, 1, "Salario mensual bruto", self.employee_vars["amount"])
        ttk.Label(tab, text="Calcula 10.83% trabajador, 26.83% patronal y renta salarial 2026.").grid(row=2, column=0, columnspan=2, sticky="w", padx=6, pady=8)

    def _expense_editor(self, parent, row):
        box = ttk.LabelFrame(parent, text="Gastos deducibles")
        box.grid(row=row, column=0, columnspan=2, sticky="ew", padx=6, pady=8)
        box.columnconfigure(1, weight=1)
        self.expense_category = tk.StringVar()
        self.expense_amount = tk.StringVar(value="0")
        self.expense_note = tk.StringVar()
        self.expense_combo = ttk.Combobox(box, textvariable=self.expense_category, values=[], state="normal", width=25)
        self.expense_combo.grid(row=0, column=0, padx=4, pady=4)
        ttk.Entry(box, textvariable=self.expense_amount, width=14).grid(row=0, column=1, padx=4, pady=4, sticky="ew")
        ttk.Entry(box, textvariable=self.expense_note, width=22).grid(row=0, column=2, padx=4, pady=4)
        ttk.Button(box, text="Agregar", command=self._add_expense).grid(row=0, column=3, padx=4, pady=4)
        self.expense_list = tk.Listbox(box, height=5)
        self.expense_list.grid(row=1, column=0, columnspan=4, sticky="ew", padx=4, pady=4)

    def _build_independent_tab(self):
        tab = ttk.Frame(self.tabs)
        tab.columnconfigure(1, weight=1)
        self.tabs.add(tab, text="Independiente")
        self._field(tab, 0, "Etiqueta", self.independent_vars["label"])
        self._field(tab, 1, "Monto mensual a facturar sin IVA", self.independent_vars["amount"])
        self._field(tab, 2, "Monto deuda vehicular", self.independent_vars["vehicle_debt_amount"])
        self._field(tab, 3, "Cuota vehicular mensual", self.independent_vars["vehicle_monthly_payment"])
        self._expense_editor(tab, 4)

    def _build_owner_tab(self):
        tab = ttk.Frame(self.tabs)
        tab.columnconfigure(1, weight=1)
        self.tabs.add(tab, text="Dueno empresa")
        self._field(tab, 0, "Etiqueta", self.owner_vars["label"])
        self._field(tab, 1, "Ingreso bruto mensual empresa", self.owner_vars["amount"])
        ttk.Label(tab, text="Tipo pago socio").grid(row=2, column=0, sticky="w", padx=6, pady=4)
        ttk.Combobox(tab, textvariable=self.owner_vars["distribution_type"], values=["NONE", "DIETAS", "DIVIDENDS"], state="readonly").grid(row=2, column=1, sticky="ew", padx=6, pady=4)
        self._field(tab, 3, "Monto mensual dietas/dividendos", self.owner_vars["distribution_amount"])
        ttk.Checkbutton(tab, text="PYME registrada", variable=self.owner_vars["is_pyme"]).grid(row=4, column=0, sticky="w", padx=6, pady=4)
        self._field(tab, 5, "Ano PYME", self.owner_vars["pyme_year"])
        self._field(tab, 6, "Monto deuda vehicular", self.owner_vars["vehicle_debt_amount"])
        self._field(tab, 7, "Cuota vehicular mensual", self.owner_vars["vehicle_monthly_payment"])
        self._expense_editor(tab, 8)

    def _load_rules(self):
        try:
            self.rules = hr_salary_calculator_rules_api()
            categories = self.rules.get("expense_categories") or []
            if hasattr(self, "expense_combo"):
                self.expense_combo.configure(values=categories)
                if categories:
                    self.expense_category.set(categories[0])
        except Exception as exc:
            messagebox.showwarning("Calculadora salarial", f"No se pudieron cargar reglas: {exc}")

    def _num(self, value):
        try:
            return float(str(value or "0").replace(",", "").strip() or 0)
        except Exception:
            return 0.0

    def _add_expense(self):
        category = self.expense_category.get().strip() or "Otro gasto deducible"
        amount = self._num(self.expense_amount.get())
        note = self.expense_note.get().strip() or None
        self.expense_rows.append({"category": category, "amount": amount, "note": note})
        self.expense_list.insert("end", f"{category}: {_fmt(amount)}")
        self.expense_amount.set("0")
        self.expense_note.set("")

    def _clear_expenses(self):
        self.expense_rows.clear()
        if hasattr(self, "expense_list"):
            self.expense_list.delete(0, "end")

    def _payload(self, save):
        index = self.tabs.index(self.tabs.select())
        if index == 0:
            return {
                "scenario": "EMPLOYEE",
                "amount": self._num(self.employee_vars["amount"].get()),
                "label": self.employee_vars["label"].get().strip() or None,
                "save": save,
            }
        if index == 1:
            return {
                "scenario": "INDEPENDENT",
                "amount": self._num(self.independent_vars["amount"].get()),
                "vehicle_debt_amount": self._num(self.independent_vars["vehicle_debt_amount"].get()),
                "vehicle_monthly_payment": self._num(self.independent_vars["vehicle_monthly_payment"].get()),
                "expenses": self.expense_rows,
                "label": self.independent_vars["label"].get().strip() or None,
                "save": save,
            }
        return {
            "scenario": "OWNER",
            "amount": self._num(self.owner_vars["amount"].get()),
            "vehicle_debt_amount": self._num(self.owner_vars["vehicle_debt_amount"].get()),
            "vehicle_monthly_payment": self._num(self.owner_vars["vehicle_monthly_payment"].get()),
            "distribution_type": self.owner_vars["distribution_type"].get(),
            "distribution_amount": self._num(self.owner_vars["distribution_amount"].get()),
            "is_pyme": bool(self.owner_vars["is_pyme"].get()),
            "pyme_year": int(self._num(self.owner_vars["pyme_year"].get())),
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

    def _render_result(self, data):
        self.result.delete("1.0", "end")
        lines = [f"Escenario: {data.get('scenario')}", f"Regla: {data.get('rule_version')}", ""]
        for key, value in data.items():
            if key in {"scenario", "rule_version", "currency", "disclaimer"}:
                continue
            if isinstance(value, list):
                lines.append(key.replace("_", " ").title())
                for item in value:
                    if isinstance(item, dict):
                        name = item.get("name") or item.get("category") or f"{item.get('from')} - {item.get('to')}"
                        amount = item.get("amount", item.get("tax", ""))
                        rate = item.get("rate")
                        suffix = f" ({rate:.2%})" if isinstance(rate, (int, float)) else ""
                        lines.append(f"  - {name}: {_fmt(amount)}{suffix}")
                lines.append("")
            elif isinstance(value, (int, float)):
                if key.endswith("_rate"):
                    lines.append(f"{key.replace('_', ' ').title()}: {value:.2%}")
                else:
                    lines.append(f"{key.replace('_', ' ').title()}: {_fmt(value)}")
            else:
                lines.append(f"{key.replace('_', ' ').title()}: {value}")
        lines.append("")
        lines.append(str(data.get("disclaimer") or ""))
        self.result.insert("1.0", "\n".join(lines))

    def _load_history(self):
        try:
            payload = hr_salary_calculator_history_api()
            rows = payload.get("data", [])
            self.history.delete(*self.history.get_children())
            for row in rows:
                self.history.insert("", "end", values=(row.get("id"), row.get("scenario"), row.get("label") or "", row.get("created_at")))
        except Exception:
            pass
