import tkinter as tk
from tkinter import ttk, messagebox
import requests

from api_client import BASE_URL


class PopupViewApplied(tk.Toplevel):

    def __init__(self, parent, payment_data):
        super().__init__(parent)

        self.payment_data = payment_data

        # -----------------------------------------
        # DETECTAR ORIGEN DEL REGISTRO
        # -----------------------------------------
        raw_id = str(payment_data.get("id"))

        if raw_id.startswith("incoming_"):
            self.source = "incoming"
            self.payment_id = int(raw_id.replace("incoming_", ""))
        else:
            self.source = "cash_app"
            self.payment_id = int(raw_id)

        self.title("Detalle de Pago – Bank Reconciliation")
        self.geometry("700x360")
        self.resizable(False, False)

        self.transient(parent)
        self.grab_set()
        self.focus_force()

        self._build_ui()

    # =========================================================
    # UI
    # =========================================================
    def _build_ui(self):

        frm_info = ttk.LabelFrame(self, text="Información del Pago")
        frm_info.pack(fill="x", padx=10, pady=10)

        fields = [
            ("Banco", "banco"),
            ("Fecha de Pago", "fecha_pago"),
            ("Código Cliente", "codigo_cliente"),
            ("Nombre Cliente", "nombre_cliente"),
            ("Documento", "numero_documento"),
            ("Referencia", "referencia"),
            ("Monto Pagado", "monto_pagado"),
            ("Tipo Aplicación", "tipo_aplicacion"),
            ("Estado", "estado"),
            ("Creado", "created_at"),
        ]

        for i, (label, key) in enumerate(fields):
            ttk.Label(frm_info, text=label + ":").grid(
                row=i // 2,
                column=(i % 2) * 2,
                sticky="w",
                padx=5,
                pady=4
            )
            ttk.Label(
                frm_info,
                text=str(self.payment_data.get(key, ""))
            ).grid(
                row=i // 2,
                column=(i % 2) * 2 + 1,
                sticky="w",
                padx=5,
                pady=4
            )

        # -----------------------------------------------------
        # ACCIONES
        # -----------------------------------------------------
        frm_actions = ttk.Frame(self)
        frm_actions.pack(fill="x", padx=10, pady=15)

        ttk.Button(
            frm_actions,
            text="↩ Reversar Pago (Eliminar)",
            command=self._reverse_payment
        ).pack(side="right")

        ttk.Button(
            frm_actions,
            text="Cerrar",
            command=self.destroy
        ).pack(side="right", padx=5)

    # =========================================================
    # REVERSA (cash_app e incoming) — MISMO ENDPOINT
    # =========================================================
    def _reverse_payment(self):

        reason = self._simple_input(
            "Razón de reversa",
            "Indique la razón de la reversa:"
        )
        if not reason:
            return

        comment = self._simple_input(
            "Comentario",
            "Indique un comentario adicional:"
        )
        if not comment:
            return

        origen_txt = (
            "incoming payments" if self.source == "incoming"
            else "cash_app"
        )

        confirm = messagebox.askyesno(
            "Confirmación",
            f"¿Está seguro de proceder?\n\n"
            f"Este pago será revertido desde {origen_txt}."
        )
        if not confirm:
            return

        # 🔒 MISMO ENDPOINT PARA AMBOS
        url = f"{BASE_URL}/bank-reconciliation/{self.payment_id}/reverse"

        try:
            r = requests.post(
                url,
                json={
                    "reason": reason,
                    "comment": comment
                },
                timeout=20
            )
            r.raise_for_status()
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo reversar el pago:\n{e}"
            )
            return

        messagebox.showinfo(
            "Éxito",
            "Pago revertido correctamente."
        )

        self.destroy()

    # =========================================================
    # INPUT SIMPLE
    # =========================================================
    def _simple_input(self, title, prompt):

        win = tk.Toplevel(self)
        win.title(title)
        win.geometry("420x140")
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()

        ttk.Label(win, text=prompt).pack(
            padx=10, pady=(10, 5), anchor="w"
        )

        entry = ttk.Entry(win)
        entry.pack(fill="x", padx=10)
        entry.focus()

        result = {"value": None}

        def ok():
            val = entry.get().strip()
            if not val:
                messagebox.showwarning(
                    "Requerido",
                    "Este campo es obligatorio."
                )
                return
            result["value"] = val
            win.destroy()

        def cancel():
            win.destroy()

        frm = ttk.Frame(win)
        frm.pack(fill="x", padx=10, pady=10)

        ttk.Button(frm, text="Cancelar", command=cancel).pack(side="right")
        ttk.Button(frm, text="Aceptar", command=ok).pack(
            side="right", padx=5
        )

        win.wait_window()
        return result["value"]
