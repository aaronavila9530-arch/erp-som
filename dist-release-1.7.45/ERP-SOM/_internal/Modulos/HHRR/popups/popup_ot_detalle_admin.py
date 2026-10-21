import tkinter as tk
from tkinter import ttk, messagebox

from api_client import hr_update_ot_status


class PopupDetalleOTAdmin(tk.Toplevel):
    """
    Popup ADMIN para ver / aprobar / rechazar un registro de horas
    """

    def __init__(self, parent, data: dict, on_success=None):
        super().__init__(parent)

        self.data = data
        self.on_success = on_success

        self.title("Detalle Registro de Horas")
        self.geometry("420x420")
        self.resizable(False, False)

        self.transient(parent)
        self.grab_set()

        self._build_ui()

    # =========================================================
    # UI
    # =========================================================
    def _build_ui(self):

        cont = ttk.Frame(self, padding=15)
        cont.pack(fill="both", expand=True)

        ttk.Label(
            cont,
            text="Registro de Horas",
            font=("Segoe UI", 13, "bold")
        ).pack(anchor="w", pady=(0, 10))

        self._row(cont, "Usuario:", self.data.get("usuario"))
        self._row(cont, "Tipo:", self.data.get("tipo"))

        estado_raw = self.data.get("estado", "PENDIENTE")
        estado_icon = self._estado_icon(estado_raw)
        self._row(cont, "Estado:", f"{estado_icon} {estado_raw}")

        self._row(cont, "Fecha inicio:", self.data.get("fecha_inicio"))
        self._row(cont, "Fecha fin:", self.data.get("fecha_fin"))
        self._row(cont, "Duración (h):", self.data.get("duracion_horas"))
        self._row(cont, "Buque:", self.data.get("buque") or "-")

        ttk.Label(cont, text="Comentario:").pack(anchor="w", pady=(10, 2))
        txt = tk.Text(cont, height=4, wrap="word")
        txt.insert("1.0", self.data.get("comentario") or "")
        txt.configure(state="disabled")
        txt.pack(fill="x")

        # -------------------------------
        # BOTONES
        # -------------------------------
        btns = ttk.Frame(cont)
        btns.pack(fill="x", pady=15)

        ttk.Button(
            btns,
            text="Aprobar",
            command=lambda: self._set_estado("APROBADO")
        ).pack(side="left", expand=True)

        ttk.Button(
            btns,
            text="Rechazar",
            command=lambda: self._set_estado("RECHAZADO")
        ).pack(side="left", expand=True, padx=5)

        ttk.Button(
            btns,
            text="Cerrar",
            command=self.destroy
        ).pack(side="right")

    # =========================================================
    # HELPERS
    # =========================================================
    def _row(self, parent, label, value):
        frm = ttk.Frame(parent)
        frm.pack(fill="x", pady=2)

        ttk.Label(frm, text=label, width=14).pack(side="left")
        ttk.Label(frm, text=str(value)).pack(side="left")

    def _estado_icon(self, estado: str) -> str:
        if estado == "APROBADO":
            return "🟢"
        if estado == "RECHAZADO":
            return "🔴"
        return "🟡"

    # =========================================================
    # ACTION
    # =========================================================
    def _set_estado(self, nuevo_estado: str):

        if not messagebox.askyesno(
            "Confirmar",
            f"¿Desea marcar este registro como {nuevo_estado}?"
        ):
            return

        try:
            hr_update_ot_status(
                log_id=self.data["id"],
                estado=nuevo_estado
            )
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        if self.on_success:
            self.on_success()

        self.destroy()
