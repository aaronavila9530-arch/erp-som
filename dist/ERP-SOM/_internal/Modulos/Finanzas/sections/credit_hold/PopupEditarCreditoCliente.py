import tkinter as tk
from tkinter import ttk, messagebox
import requests

from api_client import BASE_URL


class PopupEditarCreditoCliente(tk.Toplevel):

    def __init__(self, parent, codigo_cliente: str, on_save=None):
        super().__init__(parent)

        self.codigo_cliente = codigo_cliente
        self.on_save = on_save

        # ================= VARIABLES =================
        self.termino_pago = tk.StringVar()
        self.limite_credito = tk.StringVar()
        self.moneda = tk.StringVar()
        self.estado_credito = tk.StringVar()
        self.hold_manual = tk.BooleanVar()
        self.observaciones = tk.StringVar()

        self.title("Editar condiciones crediticias")
        self.geometry("420x360")
        self.resizable(False, False)

        self.transient(parent)
        self.grab_set()

        self._build_ui()
        self._load_from_backend()

    # ======================================================
    # UI
    # ======================================================
    def _build_ui(self):

        frm = tk.Frame(self, bg="white")
        frm.pack(fill="both", expand=True, padx=20, pady=20)

        self._field(frm, "Término de pago (días):", self.termino_pago, 0)
        self._field(frm, "Límite de crédito:", self.limite_credito, 1)
        self._field(frm, "Moneda:", self.moneda, 2)
        self._field(frm, "Estado:", self.estado_credito, 3)

        ttk.Checkbutton(
            frm,
            text="Hold manual",
            variable=self.hold_manual
        ).grid(row=4, column=1, sticky="w", pady=5)

        ttk.Label(frm, text="Observaciones:").grid(
            row=5, column=0, sticky="nw", pady=5
        )

        self.txt_obs = tk.Text(frm, height=4, width=30)
        self.txt_obs.grid(row=5, column=1, sticky="w", pady=5)

        actions = tk.Frame(frm, bg="white")
        actions.grid(row=6, column=1, sticky="e", pady=15)

        ttk.Button(actions, text="Cancelar", command=self.destroy).pack(
            side="right", padx=5
        )

        ttk.Button(actions, text="Guardar cambios", command=self._guardar).pack(
            side="right"
        )

    def _field(self, parent, label, variable, row):
        ttk.Label(parent, text=label).grid(
            row=row, column=0, sticky="w", pady=5
        )
        ttk.Entry(parent, textvariable=variable, width=25).grid(
            row=row, column=1, sticky="w", pady=5
        )

    # ======================================================
    # CARGA DESDE BACKEND (OBLIGATORIA)
    # ======================================================
    def _load_from_backend(self):
        try:
            r = requests.get(
                f"{BASE_URL}/cliente-credito/{self.codigo_cliente}",
                timeout=15
            )
            r.raise_for_status()

            payload = r.json()

            if not payload.get("exists"):
                messagebox.showerror(
                    "Error",
                    "Este cliente no tiene configuración crediticia"
                )
                self.destroy()
                return

            data = payload["data"]  # 🔑 CLAVE

            self.termino_pago.set(data.get("termino_pago", ""))
            self.limite_credito.set(data.get("limite_credito", ""))
            self.moneda.set(data.get("moneda", "USD"))
            self.estado_credito.set(data.get("estado_credito", "ACTIVE"))
            self.hold_manual.set(bool(data.get("hold_manual")))
            self.txt_obs.insert("1.0", data.get("observaciones") or "")

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo cargar datos de crédito:\n{e}"
            )
            self.destroy()

    # ======================================================
    # GUARDAR (BLINDADO)
    # ======================================================
    def _guardar(self):

        if not messagebox.askyesno(
            "Confirmar",
            "¿Está seguro que desea guardar estos cambios?"
        ):
            return

        payload = {}

        if self.termino_pago.get().strip():
            payload["termino_pago"] = self.termino_pago.get().strip()

        if self.limite_credito.get().strip():
            payload["limite_credito"] = self.limite_credito.get().strip()

        if self.moneda.get().strip():
            payload["moneda"] = self.moneda.get().strip()

        if self.estado_credito.get().strip():
            payload["estado_credito"] = self.estado_credito.get().strip()

        # Boolean SIEMPRE se envía (no rompe)
        payload["hold_manual"] = self.hold_manual.get()

        obs = self.txt_obs.get("1.0", "end").strip()
        if obs:
            payload["observaciones"] = obs

        if not payload:
            messagebox.showwarning(
                "Sin cambios",
                "No se detectaron cambios para guardar."
            )
            return

        try:
            r = requests.put(
                f"{BASE_URL}/cliente-credito/{self.codigo_cliente}",
                json=payload,
                timeout=15
            )
            r.raise_for_status()

            messagebox.showinfo(
                "Éxito",
                "Condiciones crediticias actualizadas correctamente"
            )

            if self.on_save:
                self.on_save()

            self.destroy()

        except Exception as e:
            messagebox.showerror("Error", str(e))
