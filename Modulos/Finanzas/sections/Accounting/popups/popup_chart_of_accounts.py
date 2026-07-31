import tkinter as tk
from tkinter import ttk, messagebox

from api_client import (
    create_accounting_account_api,
    get_accounting_accounts_api,
    harden_accounting_chart_api,
    update_accounting_account_api,
)
from session_context import get_user


class PopupChartOfAccounts(tk.Toplevel):
    """Administrador sencillo del catálogo maestro de cuentas."""

    TYPES = ("ACTIVO", "PASIVO", "PATRIMONIO", "INGRESO", "COSTO", "GASTO")

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Catálogo maestro de cuentas")
        self.geometry("1050x650")
        self.transient(parent)
        self.grab_set()
        self.selected_code = None
        self.accounts = []
        self._build_ui()
        self._load()

    def _build_ui(self):
        form = ttk.LabelFrame(self, text="Cuenta contable", padding=10)
        form.pack(fill="x", padx=12, pady=10)

        self.code = tk.StringVar()
        self.name = tk.StringVar()
        self.account_type = tk.StringVar(value="ACTIVO")
        self.normal_balance = tk.StringVar(value="DEBIT")
        self.level = tk.StringVar(value="1")
        self.parent_account = tk.StringVar()
        self.currency = tk.StringVar()
        self.accepts_posting = tk.BooleanVar(value=True)
        self.requires_third_party = tk.BooleanVar()
        self.requires_cost_center = tk.BooleanVar()
        self.active = tk.BooleanVar(value=True)
        self.show_inactive = tk.BooleanVar(value=True)

        fields = (
            ("Código", self.code), ("Nombre", self.name), ("Nivel", self.level),
            ("Cuenta padre", self.parent_account), ("Moneda", self.currency),
        )
        for index, (label, variable) in enumerate(fields):
            ttk.Label(form, text=label).grid(row=index // 3 * 2, column=(index % 3) * 2, sticky="w", padx=5)
            ttk.Entry(form, textvariable=variable, width=30).grid(row=index // 3 * 2 + 1, column=(index % 3) * 2, sticky="w", padx=5, pady=(0, 8))

        ttk.Label(form, text="Tipo").grid(row=4, column=0, sticky="w", padx=5)
        ttk.Combobox(form, textvariable=self.account_type, values=self.TYPES, state="readonly", width=27).grid(row=5, column=0, sticky="w", padx=5)
        ttk.Label(form, text="Naturaleza").grid(row=4, column=2, sticky="w", padx=5)
        ttk.Combobox(form, textvariable=self.normal_balance, values=("DEBIT", "CREDIT"), state="readonly", width=27).grid(row=5, column=2, sticky="w", padx=5)

        checks = ttk.Frame(form)
        checks.grid(row=6, column=0, columnspan=6, sticky="w", pady=8)
        ttk.Checkbutton(checks, text="Acepta movimientos", variable=self.accepts_posting).pack(side="left", padx=5)
        ttk.Checkbutton(checks, text="Exige tercero", variable=self.requires_third_party).pack(side="left", padx=5)
        ttk.Checkbutton(checks, text="Exige centro de costo", variable=self.requires_cost_center).pack(side="left", padx=5)
        ttk.Checkbutton(checks, text="Activa", variable=self.active).pack(side="left", padx=5)
        ttk.Button(checks, text="Nueva", command=self._clear).pack(side="left", padx=20)
        ttk.Button(checks, text="Guardar", command=self._save).pack(side="left", padx=5)
        ttk.Checkbutton(checks, text="Mostrar inactivas", variable=self.show_inactive, command=self._load).pack(side="left", padx=12)
        ttk.Button(checks, text="Bloquear/Sanear plan", command=self._harden_chart).pack(side="left", padx=5)

        columns = ("code", "name", "type", "nature", "level", "posting", "third", "cost", "active", "locked")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=18)
        headers = ("Código", "Nombre", "Tipo", "Naturaleza", "Nivel", "Movimientos", "Tercero", "Centro costo", "Activa", "Bloqueada")
        for col, title in zip(columns, headers):
            self.tree.heading(col, text=title)
            self.tree.column(col, width=95 if col != "name" else 260)
        self.tree.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.tree.bind("<<TreeviewSelect>>", self._select)

    def _load(self):
        self.tree.delete(*self.tree.get_children())
        self.accounts = get_accounting_accounts_api(include_inactive=self.show_inactive.get())
        for account in self.accounts:
            self.tree.insert("", "end", values=(
                account.get("account_code"), account.get("account_name"), account.get("account_type"),
                account.get("normal_balance"), account.get("account_level"),
                "Sí" if account.get("accepts_posting") else "No",
                "Sí" if account.get("requires_third_party") else "No",
                "Sí" if account.get("requires_cost_center") else "No",
                "Sí" if account.get("active") else "No",
                "Sí" if account.get("locked") else "No",
            ))

    def _select(self, _event=None):
        selection = self.tree.selection()
        if not selection:
            return
        values = self.tree.item(selection[0], "values")
        self.selected_code = values[0]
        account = next((item for item in self.accounts if item.get("account_code") == self.selected_code), None)
        if not account:
            return
        self.code.set(account.get("account_code") or "")
        self.name.set(account.get("account_name") or "")
        self.account_type.set(account.get("account_type") or "ACTIVO")
        self.normal_balance.set(account.get("normal_balance") or "DEBIT")
        self.level.set(str(account.get("account_level") or 1))
        self.parent_account.set(account.get("parent_account") or "")
        self.currency.set(account.get("currency_code") or "")
        self.accepts_posting.set(bool(account.get("accepts_posting")))
        self.requires_third_party.set(bool(account.get("requires_third_party")))
        self.requires_cost_center.set(bool(account.get("requires_cost_center")))
        self.active.set(bool(account.get("active")))

    def _payload(self):
        return {
            "account_code": self.code.get().strip(), "account_name": self.name.get().strip(),
            "account_type": self.account_type.get(), "normal_balance": self.normal_balance.get(),
            "account_level": int(self.level.get() or 1), "parent_account": self.parent_account.get().strip() or None,
            "currency_code": self.currency.get().strip().upper() or None,
            "accepts_posting": self.accepts_posting.get(),
            "requires_third_party": self.requires_third_party.get(),
            "requires_cost_center": self.requires_cost_center.get(), "active": self.active.get(),
            "updated_by": get_user() or "unknown",
        }

    def _save(self):
        try:
            payload = self._payload()
            if not payload["account_code"] or not payload["account_name"]:
                raise ValueError("Código y nombre son obligatorios.")
            if self.selected_code:
                update_accounting_account_api(self.selected_code, payload)
            else:
                create_accounting_account_api(payload)
            self._clear()
            self._load()
            messagebox.showinfo("Catálogo", "Cuenta guardada correctamente.")
        except Exception as exc:
            messagebox.showerror("Catálogo", str(exc))

    def _harden_chart(self):
        if not messagebox.askyesno(
            "Plan contable",
            "Esto eliminara Banco Nacional si no tiene uso, inactivara cuentas sin movimientos y bloqueara el plan activo.\n\nDeseas continuar?",
            parent=self,
        ):
            return
        try:
            result = harden_accounting_chart_api(
                user=get_user() or "unknown",
                reason="Fase 1: plan contable definitivo y bloqueado",
            )
            self.show_inactive.set(True)
            self._load()
            messagebox.showinfo(
                "Plan contable",
                "Plan saneado correctamente.\n\n"
                f"Banco Nacional eliminado: {result.get('deleted_banco_nacional', 0)}\n"
                f"Banco Nacional inactivado: {result.get('inactive_banco_nacional', 0)}\n"
                f"Cuentas sin uso inactivadas: {result.get('inactivated_unused', 0)}\n"
                f"Cuentas activas bloqueadas: {result.get('locked_active', 0)}",
                parent=self,
            )
        except Exception as exc:
            messagebox.showerror("Plan contable", str(exc), parent=self)

    def _clear(self):
        self.selected_code = None
        self.code.set("")
        self.name.set("")
        self.account_type.set("ACTIVO")
        self.normal_balance.set("DEBIT")
        self.level.set("1")
        self.parent_account.set("")
        self.currency.set("")
        self.accepts_posting.set(True)
        self.requires_third_party.set(False)
        self.requires_cost_center.set(False)
        self.active.set(True)
