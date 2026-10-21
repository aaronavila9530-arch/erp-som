import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date
from decimal import Decimal, InvalidOperation

from Modulos.Finanzas.date_utils import LONG_DATE_FORMAT, to_db_date, to_long_english_date
from Modulos.Servicios.widgets.date_picker import DatePicker
from api_client import (
    get_accounting_accounts_api,
    post_accounting_manual_entry_api
)
from session_context import get_user


class PopupManualEntry(tk.Toplevel):
    """
    Popup para crear Asiento Manual
    """

    def __init__(self, parent, on_success=None):
        super().__init__(parent)
        self.title("Asiento Manual")
        self.geometry("720x420")
        self.resizable(False, False)

        self.on_success = on_success
        self.accounts = []
        self.catalog_map = {}   # "1010 - Bancos" -> dict
        self.lines_widgets = []

        self._load_catalog()
        self._build_ui()

    # ============================================================
    # CARGAR CATÁLOGO CONTABLE
    # ============================================================
    def _load_catalog(self):
        accounts = get_accounting_accounts_api()
        self.accounts = accounts or []

        for a in self.accounts:
            key = f"{a['account_code']} - {a['account_name']}"
            self.catalog_map[key] = a

    # ============================================================
    # UI
    # ============================================================
    def _build_ui(self):

        # -------- Detalle general --------
        frm_top = tk.Frame(self)
        frm_top.pack(fill="x", padx=10, pady=5)

        tk.Label(frm_top, text="Detalle del asiento").grid(row=0, column=0, sticky="w")
        self.txt_detail = tk.Entry(frm_top, width=80)
        self.txt_detail.grid(row=1, column=0, columnspan=6, pady=5)

        tk.Label(frm_top, text="Fecha del asiento").grid(row=2, column=0, sticky="w")
        self.txt_entry_date = tk.Entry(frm_top, width=16)
        self.txt_entry_date.insert(0, to_long_english_date(date.today()))
        self.txt_entry_date.grid(row=3, column=0, sticky="w", pady=5)
        ttk.Button(
            frm_top,
            text="📅",
            width=3,
            command=lambda: DatePicker(self, self.txt_entry_date, output_format=LONG_DATE_FORMAT)
        ).grid(row=3, column=1, sticky="w", padx=5)

        # -------- Tabla de líneas --------
        self.frm_lines = tk.Frame(self)
        self.frm_lines.pack(fill="both", expand=True, padx=10)

        headers = ["Cuenta", "Debe / Haber", "Monto", ""]
        for i, h in enumerate(headers):
            tk.Label(self.frm_lines, text=h, font=("Segoe UI", 9, "bold")).grid(row=0, column=i)

        self._add_line()

        # -------- Botones --------
        frm_btn = tk.Frame(self)
        frm_btn.pack(fill="x", pady=10)

        ttk.Button(frm_btn, text="➕ Agregar línea", command=self._add_line).pack(side="left", padx=10)
        ttk.Button(frm_btn, text="Guardar", command=self._save).pack(side="right", padx=10)
        ttk.Button(frm_btn, text="Cancelar", command=self.destroy).pack(side="right")

    # ============================================================
    # AGREGAR LÍNEA
    # ============================================================
    def _add_line(self):

        row = len(self.lines_widgets) + 1

        cmb_account = ttk.Combobox(
            self.frm_lines,
            values=list(self.catalog_map.keys()),
            width=40,
            state="readonly"
        )
        cmb_account.grid(row=row, column=0, padx=5, pady=3)

        cmb_dc = ttk.Combobox(
            self.frm_lines,
            values=["Debe", "Haber"],
            width=10,
            state="readonly"
        )
        cmb_dc.grid(row=row, column=1, padx=5)
        cmb_dc.set("Debe")

        txt_amount = tk.Entry(self.frm_lines, width=15, justify="right")
        txt_amount.grid(row=row, column=2, padx=5)

        btn_del = ttk.Button(
            self.frm_lines,
            text="✖",
            command=lambda r=row: self._remove_line(r)
        )
        btn_del.grid(row=row, column=3)

        self.lines_widgets.append((cmb_account, cmb_dc, txt_amount))

    def _remove_line(self, row):
        if row <= 1:
            return

        widgets = self.lines_widgets.pop(row - 1)
        for w in widgets:
            w.destroy()

    # ============================================================
    # GUARDAR ASIENTO
    # ============================================================
    def _save(self):

        detail_user = self.txt_detail.get().strip()
        if not detail_user:
            messagebox.showwarning("Validación", "Debe ingresar un detalle.")
            return

        lines = []
        total_debit = Decimal("0.00")
        total_credit = Decimal("0.00")

        for cmb_account, cmb_dc, txt_amount in self.lines_widgets:

            if not cmb_account.get():
                continue

            try:
                amount = Decimal(txt_amount.get().replace(",", "")).quantize(Decimal("0.01"))
            except (InvalidOperation, ValueError):
                messagebox.showerror("Error", "Monto inválido.")
                return
            if amount <= 0:
                messagebox.showerror("Error", "El monto debe ser mayor que cero.")
                return

            acc = self.catalog_map[cmb_account.get()]

            debit = amount if cmb_dc.get() == "Debe" else Decimal("0.00")
            credit = amount if cmb_dc.get() == "Haber" else Decimal("0.00")

            total_debit += debit
            total_credit += credit

            lines.append({
                "account_code": acc["account_code"],
                "account_name": acc["account_name"],
                "debit": str(debit),
                "credit": str(credit),
                "line_description": detail_user
            })

        if not lines or len(lines) < 2:
            messagebox.showwarning("Validación", "Debe ingresar al menos dos líneas.")
            return

        if total_debit != total_credit:
            messagebox.showerror(
                "Asiento descuadrado",
                f"Debe: {total_debit:,.2f}\nHaber: {total_credit:,.2f}"
            )
            return

        payload = {
            "entry_date": to_db_date(self.txt_entry_date.get().strip()),
            "description": f"FROM Asiento Manual – {detail_user}",
            "created_by": get_user() or "unknown",
            "lines": lines
        }

        try:
            post_accounting_manual_entry_api(payload)
            messagebox.showinfo(
                "Borrador creado",
                "El asiento quedó como BORRADOR. Debe enviarse a revisión, aprobarse y contabilizarse."
            )
            if self.on_success:
                self.on_success()
            self.destroy()

        except Exception as e:
            messagebox.showerror("Error", str(e))
