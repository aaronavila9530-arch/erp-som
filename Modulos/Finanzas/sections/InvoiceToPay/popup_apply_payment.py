import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date
import requests

from Modulos.Finanzas.date_utils import LONG_DATE_FORMAT, to_db_date, to_long_english_date
from Modulos.Servicios.widgets.date_picker import DatePicker
from api_client import BASE_URL, get_accounting_bank_accounts_api
from session_context import get_rol, get_user


class PopupApplyPayment(tk.Toplevel):

    def __init__(self, parent, obligation_data, on_success=None):
        super().__init__(parent)

        self.parent = parent
        self.on_success = on_success
        self.obligation = obligation_data or {}
        self.bank_accounts = []
        self.bank_account_by_label = {}

        self.title("Apply Payment")
        self.geometry("470x475")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._build_ui()

    # ============================================================
    # UI
    # ============================================================
    def _build_ui(self):

        tk.Label(
            self,
            text="Apply Payment",
            font=("Segoe UI", 14, "bold")
        ).pack(pady=10)

        frm = tk.Frame(self)
        frm.pack(fill="x", padx=20)

        # ---- Info
        self._row(frm, "Payee:", self.obligation.get("payee", ""))
        self._row(frm, "Reference:", self.obligation.get("reference", ""))
        self._row(frm, "Currency:", self.obligation.get("currency", ""))
        self._row(
            frm,
            "Outstanding Balance:",
            f"{float(self.obligation.get('balance', 0) or 0):.2f}"
        )

        ttk.Separator(self).pack(fill="x", pady=10)

        # ---- Payment amount
        tk.Label(frm, text="Payment Amount").grid(row=4, column=0, sticky="w", pady=5)
        self.ent_amount = ttk.Entry(frm)
        self.ent_amount.grid(row=4, column=1, sticky="ew", pady=5)

        # ---- Date
        tk.Label(frm, text="Payment Date").grid(row=5, column=0, sticky="w", pady=5)
        date_frame = ttk.Frame(frm)
        date_frame.grid(row=5, column=1, sticky="ew", pady=5)
        self.ent_date = ttk.Entry(date_frame)
        self.ent_date.insert(0, to_long_english_date(date.today()))
        self.ent_date.pack(side="left", fill="x", expand=True)
        ttk.Button(
            date_frame,
            text="📅",
            width=3,
            command=lambda: DatePicker(self, self.ent_date, output_format=LONG_DATE_FORMAT)
        ).pack(side="left", padx=(5, 0))

        tk.Label(frm, text="Bank Account").grid(row=6, column=0, sticky="w", pady=5)
        self.cmb_bank = ttk.Combobox(frm, state="readonly")
        self.cmb_bank.grid(row=6, column=1, sticky="ew", pady=5)
        self._load_bank_accounts()

        frm.columnconfigure(1, weight=1)

        ttk.Separator(self).pack(fill="x", pady=10)

        # ---- Buttons
        btn_frame = tk.Frame(self)
        btn_frame.pack(fill="x", padx=20, pady=10)

        ttk.Button(
            btn_frame,
            text="Apply Payment",
            command=self._apply_payment
        ).pack(side="right")

        ttk.Button(
            btn_frame,
            text="Cancel",
            command=self.destroy
        ).pack(side="right", padx=5)

    # ============================================================
    # HELPERS
    # ============================================================
    def _row(self, parent, label, value):
        r = parent.grid_size()[1]
        tk.Label(parent, text=label).grid(row=r, column=0, sticky="w", pady=2)
        tk.Label(
            parent,
            text=value,
            font=("Segoe UI", 9, "bold")
        ).grid(row=r, column=1, sticky="w", pady=2)

    # ============================================================
    # APPLY PAYMENT (100% ALINEADO CON ROUTER)
    # ============================================================
    def _apply_payment(self):

        # ---------------- VALIDAR ID ----------------
        obligation_id = self.obligation.get("id")
        if not obligation_id:
            messagebox.showerror("Error", "Invalid obligation ID.")
            return

        # ---------------- VALIDAR MONTO ----------------
        try:
            amount = float(self.ent_amount.get())
        except Exception:
            messagebox.showerror("Error", "Invalid payment amount.")
            return

        balance = float(self.obligation.get("balance", 0) or 0)

        if amount <= 0:
            messagebox.showerror(
                "Error",
                "Payment amount must be greater than zero."
            )
            return

        if amount > balance:
            messagebox.showerror(
                "Error",
                "Payment amount cannot exceed outstanding balance."
            )
            return

        # ---------------- VALIDAR FECHA ----------------
        payment_date = to_db_date(self.ent_date.get().strip())
        if not payment_date:
            messagebox.showerror("Error", "Payment date is required.")
            return

        if not self._selected_bank():
            messagebox.showerror("Error", "Select a bank account.")
            return

        # ---------------- LLAMAR API ----------------
        try:
            response = requests.post(
                f"{BASE_URL}/invoice-to-pay/apply-payment",
                params={
                    "obligation_id": int(obligation_id),
                    "amount": float(amount),
                    "payment_date": payment_date,
                    "bank_account_code": self._selected_bank().get("account_code"),
                    "bank_account_name": self._selected_bank().get("account_name"),
                    "bank_name": self._selected_bank().get("account_name")
                },
                headers={
                    "X-User": get_user() or "unknown",
                    "X-Role": get_rol() or "",
                    "X-User-Role": get_rol() or "",
                },
                timeout=20
            )

            # Mostrar error real del backend si existe
            if response.status_code != 200:
                try:
                    detail = response.json().get("detail")
                except Exception:
                    detail = response.text

                messagebox.showerror(
                    "Error",
                    f"Backend error:\n{detail}"
                )
                return

            data = response.json()

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Connection error:\n{e}"
            )
            return

        # ---------------- SUCCESS ----------------
        rule_detail = ""
        if data.get("external_surveyor_rule_applied"):
            rule_detail = (
                "\n\nSurveyor exterior:\n"
                f"Retencion 25%: {float(data.get('withholding_usd') or 0):,.2f} USD\n"
                f"Deduccion transferencia: {float(data.get('deduction_usd') or 0):,.2f} USD\n"
                f"Neto a pagar: {float(data.get('net_payment_usd') or 0):,.2f} USD"
            )

        messagebox.showinfo(
            "Success",
            f"Payment applied successfully.\n\n"
            f"New Balance: {data.get('new_balance')}\n"
            f"Status: {data.get('status')}"
            f"{rule_detail}"
        )

        if self.on_success:
            self.on_success()

        self.destroy()

    def _load_bank_accounts(self):
        try:
            self.bank_accounts = get_accounting_bank_accounts_api()
        except Exception:
            self.bank_accounts = []

        values = []
        self.bank_account_by_label = {}
        for account in self.bank_accounts:
            code = str(account.get("account_code") or "").strip()
            name = str(account.get("account_name") or "").strip()
            if not code or not name:
                continue
            label = f"{code} - {name}"
            values.append(label)
            self.bank_account_by_label[label] = account

        self.cmb_bank["values"] = values
        if values:
            self.cmb_bank.set(values[0])

    def _selected_bank(self):
        return self.bank_account_by_label.get(self.cmb_bank.get().strip(), {})
