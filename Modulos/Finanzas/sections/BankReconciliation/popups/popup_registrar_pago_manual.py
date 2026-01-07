import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import requests

from api_client import (
    BASE_URL,
    get_clientes_finanzas_api
)


class PopupRegistrarPagoManual(tk.Toplevel):

    def __init__(self, parent, on_success=None):
        super().__init__(parent)

        self.on_success = on_success
        self.clientes_map = {}

        self.title("Registrar Pago Manual")
        self.geometry("520x420")
        self.resizable(False, False)

        self.transient(parent)
        self.grab_set()
        self.focus_force()

        self._build_ui()
        self._load_clientes()

    # =========================================================
    # UI
    # =========================================================
    def _build_ui(self):

        frm = ttk.Frame(self)
        frm.pack(fill="both", expand=True, padx=15, pady=10)

        row = 0

        # -------------------------
        # Cliente
        # -------------------------
        ttk.Label(frm, text="Cliente").grid(row=row, column=0, sticky="w", pady=5)
        self.cmb_cliente = ttk.Combobox(frm, state="readonly", width=40)
        self.cmb_cliente.grid(row=row, column=1, sticky="ew", pady=5)
        row += 1

        # -------------------------
        # Banco
        # -------------------------
        ttk.Label(frm, text="Banco").grid(row=row, column=0, sticky="w", pady=5)
        self.txt_banco = ttk.Entry(frm)
        self.txt_banco.grid(row=row, column=1, sticky="ew", pady=5)
        row += 1

        # -------------------------
        # Número de referencia
        # -------------------------
        ttk.Label(frm, text="Número de Referencia").grid(row=row, column=0, sticky="w", pady=5)
        self.txt_referencia = ttk.Entry(frm)
        self.txt_referencia.grid(row=row, column=1, sticky="ew", pady=5)
        row += 1

        # -------------------------
        # Fecha de pago
        # -------------------------
        ttk.Label(frm, text="Fecha de Pago (YYYY-MM-DD)").grid(row=row, column=0, sticky="w", pady=5)
        self.txt_fecha = ttk.Entry(frm)
        self.txt_fecha.insert(0, datetime.today().strftime("%Y-%m-%d"))
        self.txt_fecha.grid(row=row, column=1, sticky="ew", pady=5)
        row += 1

        # -------------------------
        # Documento (opcional)
        # -------------------------
        ttk.Label(frm, text="Documento").grid(row=row, column=0, sticky="w", pady=5)
        self.txt_documento = ttk.Entry(frm)
        self.txt_documento.grid(row=row, column=1, sticky="ew", pady=5)
        row += 1

        # -------------------------
        # Monto
        # -------------------------
        ttk.Label(frm, text="Monto").grid(row=row, column=0, sticky="w", pady=5)
        self.txt_monto = ttk.Entry(frm)
        self.txt_monto.grid(row=row, column=1, sticky="ew", pady=5)
        row += 1

        frm.columnconfigure(1, weight=1)

        # -------------------------
        # Botones
        # -------------------------
        frm_btn = ttk.Frame(self)
        frm_btn.pack(fill="x", pady=15)

        ttk.Button(
            frm_btn,
            text="💾 Registrar Pago",
            command=self._on_save
        ).pack(side="right", padx=5)

        ttk.Button(
            frm_btn,
            text="Cancelar",
            command=self.destroy
        ).pack(side="right")

    # =========================================================
    # Cargar clientes
    # =========================================================
    def _load_clientes(self):

        try:
            clientes = get_clientes_finanzas_api()
            valores = []

            for c in clientes:
                texto = f"{c['codigo']} - {c['nombre']}"
                valores.append(texto)
                self.clientes_map[texto] = c["codigo"]

            self.cmb_cliente["values"] = valores

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudieron cargar los clientes:\n{e}"
            )

    # =========================================================
    # Guardar pago
    # =========================================================
    def _on_save(self):

        if not self.cmb_cliente.get():
            messagebox.showwarning("Requerido", "Seleccione un cliente.")
            return

        if not self.txt_banco.get().strip():
            messagebox.showwarning("Requerido", "Ingrese el banco.")
            return

        if not self.txt_referencia.get().strip():
            messagebox.showwarning("Requerido", "Ingrese el número de referencia.")
            return

        if not self.txt_monto.get().strip():
            messagebox.showwarning("Requerido", "Ingrese el monto.")
            return

        try:
            monto = float(self.txt_monto.get())
            if monto <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Monto inválido", "El monto debe ser numérico y mayor a 0.")
            return

        codigo_cliente = self.clientes_map[self.cmb_cliente.get()]
        nombre_cliente = self.cmb_cliente.get().split(" - ", 1)[1]

        payload = {
            "origen": "MANUAL",
            "codigo_cliente": codigo_cliente,
            "nombre_cliente": nombre_cliente,
            "banco": self.txt_banco.get().strip(),
            "numero_referencia": self.txt_referencia.get().strip(),
            "fecha_pago": self.txt_fecha.get().strip(),
            "documento": self.txt_documento.get().strip() or None,
            "monto": monto
        }

        try:
            r = requests.post(
                f"{BASE_URL}/incoming-payments",
                json=payload,
                timeout=20
            )
            r.raise_for_status()
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo registrar el pago:\n{e}"
            )
            return

        messagebox.showinfo("OK", "Pago manual registrado correctamente.")

        if self.on_success:
            self.on_success()

        self.destroy()
