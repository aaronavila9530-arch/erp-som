import tkinter as tk
from tkinter import ttk, messagebox
import psycopg2
from datetime import date


DB_URL = "postgresql://postgres:LjjyuIUsTSCdiwPVHSSwtIYPOsRQytGX@shortline.proxy.rlwy.net:50018/railway"


class PopupApplyPayment(tk.Toplevel):

    def __init__(self, parent, obligation_data, on_success=None):
        super().__init__(parent)
        self.parent = parent
        self.on_success = on_success
        self.obligation = obligation_data

        self.title("Apply Payment")
        self.geometry("420x420")
        self.resizable(False, False)
        self.grab_set()

        self._build_ui()

    # ============================================================
    # UI
    # ============================================================
    def _build_ui(self):

        tk.Label(self, text="Apply Payment", font=("Segoe UI", 14, "bold")).pack(pady=10)

        frm = tk.Frame(self)
        frm.pack(fill="x", padx=20)

        # ---- Info
        self._row(frm, "Payee:", self.obligation["payee"])
        self._row(frm, "Reference:", self.obligation["reference"])
        self._row(frm, "Currency:", self.obligation["currency"])
        self._row(frm, "Outstanding Balance:", f"{self.obligation['balance']:.2f}")

        ttk.Separator(self).pack(fill="x", pady=10)

        # ---- Payment amount
        tk.Label(frm, text="Payment Amount").grid(row=4, column=0, sticky="w", pady=5)
        self.ent_amount = ttk.Entry(frm)
        self.ent_amount.grid(row=4, column=1, sticky="ew", pady=5)

        # ---- Date
        tk.Label(frm, text="Payment Date").grid(row=5, column=0, sticky="w", pady=5)
        self.ent_date = ttk.Entry(frm)
        self.ent_date.insert(0, date.today().isoformat())
        self.ent_date.grid(row=5, column=1, sticky="ew", pady=5)

        # ---- Reference
        tk.Label(frm, text="Payment Reference").grid(row=6, column=0, sticky="w", pady=5)
        self.ent_ref = ttk.Entry(frm)
        self.ent_ref.grid(row=6, column=1, sticky="ew", pady=5)

        frm.columnconfigure(1, weight=1)

        ttk.Separator(self).pack(fill="x", pady=10)

        # ---- Buttons
        btn_frame = tk.Frame(self)
        btn_frame.pack(fill="x", padx=20, pady=10)

        ttk.Button(btn_frame, text="Apply Payment", command=self._apply_payment).pack(side="right")
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side="right", padx=5)

    # ============================================================
    # HELPERS
    # ============================================================
    def _row(self, parent, label, value):
        r = parent.grid_size()[1]
        tk.Label(parent, text=label).grid(row=r, column=0, sticky="w", pady=2)
        tk.Label(parent, text=value, font=("Segoe UI", 9, "bold")).grid(row=r, column=1, sticky="w", pady=2)

    # ============================================================
    # APPLY PAYMENT
    # ============================================================
    def _apply_payment(self):

        try:
            amount = float(self.ent_amount.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid payment amount.")
            return

        balance = self.obligation["balance"]

        if amount <= 0:
            messagebox.showerror("Error", "Payment amount must be greater than zero.")
            return

        if amount > balance:
            messagebox.showerror("Error", "Payment amount cannot exceed outstanding balance.")
            return

        new_balance = balance - amount
        new_status = "PAID" if new_balance == 0 else "PARTIAL"

        try:
            conn = psycopg2.connect(DB_URL)
            cur = conn.cursor()

            cur.execute("""
                UPDATE payment_obligations
                SET
                    balance = %s,
                    status = %s,
                    last_payment_date = %s,
                    updated_at = NOW()
                WHERE id = %s
            """, (
                new_balance,
                new_status,
                self.ent_date.get(),
                self.obligation["id"]
            ))

            conn.commit()

        except Exception as e:
            conn.rollback()
            messagebox.showerror("Error", f"Could not apply payment:\n{e}")
            return

        finally:
            conn.close()

        messagebox.showinfo("Success", "Payment applied successfully.")

        if self.on_success:
            self.on_success()

        self.destroy()
