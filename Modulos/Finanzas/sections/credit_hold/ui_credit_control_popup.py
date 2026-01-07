import tkinter as tk
from tkinter import ttk, messagebox
import requests

from api_client import BASE_URL


class CreditControlPopup(tk.Toplevel):

    def __init__(self, parent, codigo_cliente, on_save):
        super().__init__(parent)

        self.codigo_cliente = codigo_cliente
        self.on_save = on_save

        self.termino_pago = tk.StringVar()
        self.limite_credito = tk.StringVar()
        self.moneda = tk.StringVar(value="USD")

        self.title("Asignar condiciones crediticias")
        self.geometry("400x300")
        self.transient(parent)
        self.grab_set()

        self._build_ui()

    def _build_ui(self):
        frame = tk.Frame(self)
        frame.pack(padx=20, pady=20)

        self._field(frame, "Término de pago:", self.termino_pago, 0)
        self._field(frame, "Límite de crédito:", self.limite_credito, 1)
        self._field(frame, "Moneda:", self.moneda, 2)

        ttk.Label(frame, text="Observaciones:").grid(row=3, column=0, sticky="nw")
        self.txt_obs = tk.Text(frame, height=4, width=30)
        self.txt_obs.grid(row=3, column=1, pady=5)

        ttk.Button(
            frame,
            text="Guardar",
            command=self._guardar
        ).grid(row=4, column=1, sticky="e", pady=10)

    def _field(self, parent, label, var, row):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=5)
        ttk.Entry(parent, textvariable=var).grid(row=row, column=1, pady=5)

    def _guardar(self):
        payload = {
            "codigo_cliente": self.codigo_cliente,
            "termino_pago": int(self.termino_pago.get()),
            "limite_credito": float(self.limite_credito.get() or 0),
            "moneda": self.moneda.get(),
            "observaciones": self.txt_obs.get("1.0", "end").strip()
        }

        try:
            r = requests.post(
                f"{BASE_URL}/cliente-credito/",  # ← SLASH FINAL CORRECTO
                json=payload,
                timeout=15
            )
            r.raise_for_status()

            messagebox.showinfo("OK", "Configuración creada")
            self.destroy()
            self.on_save()

        except Exception as e:
            messagebox.showerror("Error", str(e))
