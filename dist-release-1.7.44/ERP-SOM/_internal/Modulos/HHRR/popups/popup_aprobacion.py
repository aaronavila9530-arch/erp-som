import tkinter as tk
from tkinter import ttk, messagebox
import json

# =========================================================
# IMPORT ÚNICO Y REAL DESDE api_client
# =========================================================
from api_client import actualizar_estado_evento_hr


class PopupAprobacion(tk.Toplevel):
    """
    Popup de aprobación de solicitudes HHRR.
    Usa EXCLUSIVAMENTE:
    - actualizar_estado_evento_hr (API real)
    """

    def __init__(self, parent, evento: dict, usuario_actual: str, on_success=None):
        super().__init__(parent)

        # -------------------------------
        # Datos base (defensivo)
        # -------------------------------
        self.evento = evento or {}
        self.usuario_actual = usuario_actual
        self.on_success = on_success

        self.title("Aprobación de Solicitud")
        self.geometry("520x520")
        self.resizable(False, False)

        self.transient(parent)
        self.grab_set()
        self.focus_force()

        self._construir_ui()

    # =========================================================
    # UI
    # =========================================================
    def _construir_ui(self):

        cont = ttk.Frame(self, padding=20)
        cont.pack(fill="both", expand=True)

        ttk.Label(
            cont,
            text=f"Solicitud #{self.evento.get('id', '—')}",
            font=("Segoe UI", 11, "bold")
        ).pack(anchor="w", pady=5)

        ttk.Label(
            cont,
            text=f"Tipo: {self.evento.get('event_type', '—')}"
        ).pack(anchor="w")

        ttk.Label(
            cont,
            text=f"Fecha: {self.evento.get('event_date', '—')}"
        ).pack(anchor="w")

        ttk.Label(
            cont,
            text="Detalle de la solicitud:"
        ).pack(anchor="w", pady=10)

        txt_detalle = tk.Text(cont, height=10)
        txt_detalle.insert(
            "1.0",
            json.dumps(
                self.evento.get("payload", {}),
                indent=4,
                ensure_ascii=False
            )
        )
        txt_detalle.config(state="disabled")
        txt_detalle.pack(fill="both", expand=True)

        # -------------------------------
        # Botones
        # -------------------------------
        cont_btn = ttk.Frame(cont)
        cont_btn.pack(fill="x", pady=15)

        ttk.Button(
            cont_btn,
            text="Aprobar",
            command=lambda: self._procesar("APPROVED")
        ).pack(side="right", padx=5)

        ttk.Button(
            cont_btn,
            text="Rechazar",
            command=lambda: self._procesar("REJECTED")
        ).pack(side="right", padx=5)

        ttk.Button(
            cont_btn,
            text="Cerrar",
            command=self.destroy
        ).pack(side="left")

    # =========================================================
    # LÓGICA
    # =========================================================
    def _procesar(self, estado: str):

        event_id = self.evento.get("id")
        if not event_id:
            messagebox.showerror(
                "Error",
                "No se encontró el ID del evento a procesar."
            )
            return

        try:
            actualizar_estado_evento_hr(
                event_id=event_id,
                status=estado,
                approved_by=self.usuario_actual
            )
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo procesar la solicitud:\n{e}"
            )
            return

        messagebox.showinfo(
            "Proceso exitoso",
            f"La solicitud fue "
            f"{'aprobada' if estado == 'APPROVED' else 'rechazada'}."
        )

        if callable(self.on_success):
            self.on_success()

        self.destroy()
