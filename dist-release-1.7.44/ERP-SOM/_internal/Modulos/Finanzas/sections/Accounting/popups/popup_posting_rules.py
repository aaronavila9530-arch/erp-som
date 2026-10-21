import tkinter as tk
from tkinter import messagebox, ttk

from api_client import (
    get_accounting_posting_rules_api,
    seed_accounting_posting_rules_api,
)

try:
    from session_context import get_user
except Exception:  # pragma: no cover - desktop fallback
    def get_user():
        return "ERP_USER"


ORIGINS = [
    "TODOS",
    "Collections",
    "ITP",
    "Payroll",
    "Bank Reconciliation",
    "Invoicing",
    "XML",
    "Manual",
]


class PopupPostingRules(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Motor de contabilizacion")
        self.geometry("1380x680")
        self.minsize(1100, 520)
        self.configure(bg="#f3f2ee")

        self.origin_var = tk.StringVar(value="TODOS")
        self.include_inactive_var = tk.BooleanVar(value=False)
        self.summary_var = tk.StringVar(value="")
        self.action_var = tk.StringVar(value="Ver detalle de regla")

        self._build_ui()
        self._load_rules()

    def _build_ui(self):
        top = tk.LabelFrame(self, text="Reglas por origen", bg="#f3f2ee")
        top.pack(fill="x", padx=10, pady=8)

        ttk.Label(top, text="Origen").grid(row=0, column=0, padx=(8, 4), pady=8, sticky="w")
        ttk.Combobox(
            top,
            textvariable=self.origin_var,
            values=ORIGINS,
            state="readonly",
            width=24,
        ).grid(row=0, column=1, padx=4, pady=8, sticky="w")

        ttk.Checkbutton(
            top,
            text="Mostrar inactivas",
            variable=self.include_inactive_var,
        ).grid(row=0, column=2, padx=12, pady=8, sticky="w")

        ttk.Button(top, text="Buscar", command=self._load_rules).grid(row=0, column=3, padx=4, pady=8)
        ttk.Label(top, text="Acciones").grid(row=0, column=4, padx=(14, 4), pady=8, sticky="e")
        ttk.Combobox(
            top,
            textvariable=self.action_var,
            values=(
                "Que hace este motor",
                "Ver detalle de regla",
                "Ver ejemplo practico",
                "Copiar resumen de regla",
                "Restaurar reglas base",
            ),
            state="readonly",
            width=24,
        ).grid(row=0, column=5, padx=4, pady=8)
        ttk.Button(top, text="Ejecutar", command=self._run_action).grid(row=0, column=6, padx=4, pady=8)
        ttk.Button(top, text="Cerrar", command=self.destroy).grid(row=0, column=7, padx=4, pady=8)

        tk.Label(
            top,
            textvariable=self.summary_var,
            bg="#f3f2ee",
            fg="#253746",
            font=("Segoe UI", 9, "bold"),
        ).grid(row=1, column=0, columnspan=8, padx=8, pady=(0, 8), sticky="w")
        tk.Label(
            top,
            text=(
                "Este motor no es para digitar asientos: es el mapa de control que usa el ERP para crear asientos automaticos. "
                "Seleccione una regla y use Acciones para ver, copiar o resembrar las reglas base."
            ),
            bg="#f3f2ee",
            fg="#374151",
            wraplength=1220,
            justify="left",
        ).grid(row=2, column=0, columnspan=8, padx=8, pady=(0, 8), sticky="w")

        columns = (
            "origin",
            "event_type",
            "debit",
            "credit",
            "third_party",
            "currency",
            "bank",
            "iva",
            "retention",
            "description",
            "template",
            "active",
        )
        headers = {
            "origin": "Origen",
            "event_type": "Regla / evento",
            "debit": "Debito",
            "credit": "Credito",
            "third_party": "Tercero",
            "currency": "Moneda",
            "bank": "Banco",
            "iva": "IVA",
            "retention": "Retencion",
            "description": "Descripcion",
            "template": "Plantilla asiento",
            "active": "Activa",
        }
        widths = {
            "origin": 130,
            "event_type": 160,
            "debit": 245,
            "credit": 245,
            "third_party": 170,
            "currency": 140,
            "bank": 260,
            "iva": 240,
            "retention": 260,
            "description": 320,
            "template": 280,
            "active": 70,
        }

        table_frame = tk.Frame(self, bg="#f3f2ee")
        table_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.table = ttk.Treeview(table_frame, columns=columns, show="headings")
        for col in columns:
            self.table.heading(col, text=headers[col])
            self.table.column(col, width=widths[col], minwidth=80, stretch=False)

        yscroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.table.yview)
        xscroll = ttk.Scrollbar(table_frame, orient="horizontal", command=self.table.xview)
        self.table.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)

        self.table.grid(row=0, column=0, sticky="nsew")
        self.table.bind("<Double-1>", lambda _event: self._show_rule_detail())
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

    def _load_rules(self):
        try:
            origin = self.origin_var.get()
            data = get_accounting_posting_rules_api(
                origin=None if origin == "TODOS" else origin,
                include_inactive=self.include_inactive_var.get(),
            )
            self.table.delete(*self.table.get_children())
            for rule in data:
                debit = self._account_label(rule.get("debit_account_code"), rule.get("debit_account_name"))
                credit = self._account_label(rule.get("credit_account_code"), rule.get("credit_account_name"))
                self.table.insert("", "end", values=(
                    rule.get("origin") or "",
                    rule.get("event_type") or "",
                    debit,
                    credit,
                    rule.get("third_party_policy") or "",
                    rule.get("currency_policy") or "",
                    rule.get("bank_policy") or "",
                    rule.get("iva_policy") or "",
                    rule.get("retention_policy") or "",
                    rule.get("description") or "",
                    rule.get("line_description_template") or "",
                    "Si" if rule.get("active") else "No",
                ))
            self.summary_var.set(f"Reglas cargadas: {len(data)}")
        except Exception as exc:
            messagebox.showerror("Motor de contabilizacion", f"No se pudieron cargar reglas:\n{exc}")

    def _seed_rules(self):
        try:
            result = seed_accounting_posting_rules_api(
                user=get_user() or "ERP_USER",
                reason="Seed formal accounting engine from desktop",
            )
            self._load_rules()
            messagebox.showinfo(
                "Motor de contabilizacion",
                f"Reglas base listas.\nInsertadas: {result.get('inserted', 0)}\nActualizadas: {result.get('updated', 0)}",
            )
        except Exception as exc:
            messagebox.showerror("Motor de contabilizacion", f"No se pudo sembrar el motor:\n{exc}")

    def _run_action(self):
        action = self.action_var.get()
        if action == "Restaurar reglas base":
            self._seed_rules()
        elif action == "Copiar resumen de regla":
            self._copy_rule_summary()
        elif action == "Ver ejemplo practico":
            self._show_practical_example()
        elif action == "Que hace este motor":
            self._show_engine_help()
        else:
            self._show_rule_detail()

    def _selected_values(self):
        selected = self.table.selection()
        if not selected:
            messagebox.showwarning("Motor de contabilizacion", "Seleccione una regla.", parent=self)
            return None
        return dict(zip(self.table["columns"], self.table.item(selected[0], "values")))

    def _rule_summary(self, values):
        return (
            f"Origen: {values.get('origin')}\n"
            f"Evento: {values.get('event_type')}\n"
            f"Debita: {values.get('debit')}\n"
            f"Acredita: {values.get('credit')}\n"
            f"Tercero: {values.get('third_party')}\n"
            f"Moneda: {values.get('currency')}\n"
            f"Banco: {values.get('bank')}\n"
            f"IVA: {values.get('iva')}\n"
            f"Retencion: {values.get('retention')}\n"
            f"Descripcion: {values.get('description')}\n"
        )

    def _show_rule_detail(self):
        values = self._selected_values()
        if not values:
            return
        messagebox.showinfo("Detalle de regla contable", self._rule_summary(values), parent=self)

    def _show_engine_help(self):
        messagebox.showinfo(
            "Motor de contabilizacion",
            (
                "El motor define como el ERP crea asientos automaticos.\n\n"
                "Ejemplo: cuando Collections emite una factura, la regla indica que debe debitar CxC "
                "y acreditar ingresos/IVA. Cuando ITP registra una compra, indica gasto o activo, "
                "CxP, IVA credito, banco, tercero y moneda.\n\n"
                "No reemplaza el diario: controla que cada modulo contabilice igual, sin improvisar cuentas."
            ),
            parent=self,
        )

    def _show_practical_example(self):
        values = self._selected_values()
        if not values:
            return
        messagebox.showinfo(
            "Ejemplo practico",
            (
                f"Si ocurre el evento '{values.get('event_type')}' en {values.get('origin')}:\n\n"
                f"1. El ERP debita: {values.get('debit')}\n"
                f"2. El ERP acredita: {values.get('credit')}\n"
                f"3. Aplica tercero: {values.get('third_party')}\n"
                f"4. Aplica banco: {values.get('bank')}\n"
                f"5. Aplica IVA: {values.get('iva')}\n\n"
                "La regla se usa como politica formal para crear o validar el asiento."
            ),
            parent=self,
        )

    def _copy_rule_summary(self):
        values = self._selected_values()
        if not values:
            return
        self.clipboard_clear()
        self.clipboard_append(self._rule_summary(values))
        messagebox.showinfo("Motor de contabilizacion", "Resumen copiado al portapapeles.", parent=self)

    @staticmethod
    def _account_label(code, name):
        code = str(code or "").strip()
        name = str(name or "").strip()
        if name:
            return f"{code} - {name}"
        return code
