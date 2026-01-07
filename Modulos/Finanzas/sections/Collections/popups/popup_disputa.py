import tkinter as tk
from tkinter import ttk, messagebox
import requests

from api_client import BASE_URL


class PopupDisputa(tk.Toplevel):

    def __init__(self, parent, row_data, on_success=None):
        super().__init__(parent)

        self.row = row_data
        self.on_success = on_success

        self.title("Disputa de Factura")
        self.geometry("520x520")
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

        # ================= HEADER =================
        tk.Label(
            container,
            text="Crear Disputa",
            font=("Segoe UI", 13, "bold")
        ).pack(anchor="w", pady=(0, 10))

        # ================= INFO FACTURA =================
        info = tk.LabelFrame(container, text="Factura")
        info.pack(fill="x", pady=5)

        def info_row(lbl, val):
            r = tk.Frame(info)
            r.pack(fill="x", padx=8, pady=2)
            tk.Label(r, text=lbl, width=18, anchor="w").pack(side="left")
            tk.Label(r, text=val or "", anchor="w").pack(side="left")

        info_row("N° Factura:", self.row[4])
        info_row("Cliente:", self.row[1])
        info_row("Fecha emisión:", self.row[5])
        info_row("Fecha vencimiento:", self.row[6])
        info_row("Monto:", f"{self.row[8]} {self.row[9]}")

        # ================= DISPUTA =================
        disputa = tk.LabelFrame(container, text="Detalle de la Disputa")
        disputa.pack(fill="both", expand=True, pady=10)

        tk.Label(disputa, text="Motivo").pack(anchor="w", padx=8, pady=(5, 0))

        self.motivo = tk.StringVar()
        ttk.Combobox(
            disputa,
            textvariable=self.motivo,
            state="readonly",
            values=[
                "PRECIO",
                "DESCUENTO",
                "CALIDAD",
                "WRITE_OFF",
                "CLIENTE_INCORRECTO"
            ]
        ).pack(fill="x", padx=8, pady=5)

        tk.Label(disputa, text="Comentario").pack(anchor="w", padx=8)

        self.comentario = tk.Text(disputa, height=6, wrap="word")
        self.comentario.pack(fill="x", padx=8, pady=(0, 5))

        # ================= BOTONES =================
        actions = tk.Frame(container)
        actions.pack(fill="x", pady=10)

        ttk.Button(actions, text="Cancelar", command=self.destroy).pack(side="right", padx=5)
        ttk.Button(actions, text="Confirmar Disputa", command=self._confirmar).pack(side="right")

    # ============================================================
    # CONFIRMAR
    # ============================================================
    def _confirmar(self):

        if not self.motivo.get():
            messagebox.showwarning("Validación", "Seleccione un motivo de disputa")
            return

        comentario = self.comentario.get("1.0", "end").strip()
        if not comentario:
            messagebox.showwarning("Validación", "Debe ingresar un comentario")
            return

        payload = {
            "numero_documento": self.row[4],
            "codigo_cliente": self.row[0],
            "nombre_cliente": self.row[1],
            "fecha_factura": self.row[5],
            "fecha_vencimiento": self.row[6],
            "monto": self.row[9],
            "motivo": self.motivo.get(),
            "comentario": comentario,
            "buque_contenedor": self.row[11],
            "operacion": self.row[12],
            "periodo_operacion": self.row[13],
            "descripcion_servicio": None  # ✅ CORREGIDO
        }

        try:
            r = requests.post(
                f"{BASE_URL}/collections/disputa",
                json=payload,
                timeout=15
            )
            r.raise_for_status()

            messagebox.showinfo("OK", "Disputa registrada correctamente")

            if self.on_success:
                self.on_success()

            self.destroy()

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo registrar la disputa\n\n{e}"
            )
