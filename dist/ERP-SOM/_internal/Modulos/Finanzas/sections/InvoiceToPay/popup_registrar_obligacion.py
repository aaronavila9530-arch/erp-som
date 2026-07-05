import tkinter as tk
from tkinter import ttk, messagebox

import requests
from api_client import BASE_URL


class PopupRegistrarObligacion(tk.Toplevel):

    def __init__(self, parent, on_success=None):
        super().__init__(parent)
        self.on_success = on_success

        self.title("Registrar obligación manual")
        self.geometry("480x420")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._build_ui()

    # ============================================================
    # UI
    # ============================================================
    def _build_ui(self):

        container = tk.Frame(self)
        container.pack(fill="both", expand=True, padx=15, pady=15)

        # ---------------- Beneficiario ----------------
        ttk.Label(container, text="Beneficiario").pack(anchor="w")
        self.txt_payee = ttk.Entry(container)
        self.txt_payee.pack(fill="x", pady=5)

        # ---------------- Tipo obligación ----------------
        ttk.Label(container, text="Tipo de obligación").pack(anchor="w")
        self.cmb_type = ttk.Combobox(
            container,
            values=["MANUAL", "SERVICIO", "PROVEEDOR", "OTRO"],
            state="readonly"
        )
        self.cmb_type.set("MANUAL")
        self.cmb_type.pack(fill="x", pady=5)

        # ---------------- Detalle ----------------
        ttk.Label(container, text="Detalle / Concepto").pack(anchor="w")
        self.txt_notes = tk.Text(container, height=4)
        self.txt_notes.pack(fill="x", pady=5)

        # ---------------- Referencia ----------------
        ttk.Label(container, text="Referencia").pack(anchor="w")
        self.txt_reference = ttk.Entry(container)
        self.txt_reference.pack(fill="x", pady=5)

        # ---------------- Moneda ----------------
        ttk.Label(container, text="Moneda").pack(anchor="w")
        self.cmb_currency = ttk.Combobox(
            container,
            values=["USD", "CRC", "EUR"],
            state="readonly",
            width=10
        )
        self.cmb_currency.set("USD")
        self.cmb_currency.pack(anchor="w", pady=5)

        # ---------------- Total ----------------
        ttk.Label(container, text="Monto total").pack(anchor="w")
        self.txt_total = ttk.Entry(container)
        self.txt_total.pack(fill="x", pady=5)

        # ---------------- Botones ----------------
        btn_frame = tk.Frame(container)
        btn_frame.pack(fill="x", pady=15)

        ttk.Button(
            btn_frame,
            text="Guardar",
            command=self._save
        ).pack(side="right", padx=5)

        ttk.Button(
            btn_frame,
            text="Cancelar",
            command=self.destroy
        ).pack(side="right")

    # ============================================================
    # SAVE
    # ============================================================
    def _save(self):

        try:
            payee_name = self.txt_payee.get().strip()
            obligation_type = self.cmb_type.get()
            notes = self.txt_notes.get("1.0", "end").strip()
            reference = self.txt_reference.get().strip()
            currency = self.cmb_currency.get()
            total = float(self.txt_total.get())

            if not payee_name:
                raise ValueError("Debe indicar un beneficiario")

            if total <= 0:
                raise ValueError("El monto debe ser mayor a cero")

        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        try:
            r = requests.post(
                f"{BASE_URL}/invoice-to-pay/manual",
                params={
                    "payee_name": payee_name,
                    "obligation_type": obligation_type,
                    "total": total,
                    "currency": currency,
                    "reference": reference,
                    "notes": notes
                },
                timeout=15
            )
            r.raise_for_status()

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo registrar la obligación:\n{e}"
            )
            return

        messagebox.showinfo(
            "Éxito",
            "Obligación registrada correctamente"
        )

        if self.on_success:
            self.on_success()

        self.destroy()
