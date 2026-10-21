import tkinter as tk
from tkinter import ttk, messagebox

from api_client import aprobar_evento_hr, rechazar_evento_hr


class PopupAprobacion(tk.Toplevel):
    """
    Popup para aprobar o rechazar solicitudes HHRR
    (solo admin / master)
    """

    def __init__(self, parent, row_id, on_approve=None, on_reject=None):
        super().__init__(parent)

        self.row_id = row_id
        self.on_approve = on_approve
        self.on_reject = on_reject

        self.title("Aprobar / Rechazar Solicitud")
        self.geometry("420x260")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._build_ui()

    # =========================================================
    # UI
    # =========================================================
    def _build_ui(self):
        pad = 12

        ttk.Label(
            self,
            text=f"Solicitud ID: {self.row_id}",
            font=("Segoe UI", 11, "bold")
        ).pack(pady=(15, 8))

        ttk.Label(
            self,
            text="Comentario (obligatorio solo si se rechaza):"
        ).pack(anchor="w", padx=pad)

        self.txt_comentario = tk.Text(
            self,
            height=5,
            width=48,
            wrap="word"
        )
        self.txt_comentario.pack(padx=pad, pady=(0, 12))

        # -----------------------------------------------------
        # BOTONES
        # -----------------------------------------------------
        frm_btn = ttk.Frame(self)
        frm_btn.pack(pady=10)

        ttk.Button(
            frm_btn,
            text="✅ Aprobar",
            command=self._aprobar
        ).grid(row=0, column=0, padx=6)

        ttk.Button(
            frm_btn,
            text="❌ Rechazar",
            command=self._rechazar
        ).grid(row=0, column=1, padx=6)

        ttk.Button(
            frm_btn,
            text="Cancelar",
            command=self.destroy
        ).grid(row=0, column=2, padx=6)

    # =========================================================
    # ACCIONES
    # =========================================================
    def _aprobar(self):
        comentario = self.txt_comentario.get("1.0", "end").strip() or None

        try:
            # Enviar comentario (opcional) al backend
            aprobar_evento_hr(self.row_id, comentario)

            messagebox.showinfo(
                "Éxito",
                "Solicitud aprobada correctamente"
            )

            if callable(self.on_approve):
                self.on_approve(self.row_id)

            self.destroy()

        except Exception as e:
            messagebox.showerror(
                "Error",
                str(e)
            )

    def _rechazar(self):
        comentario = self.txt_comentario.get("1.0", "end").strip()

        if not comentario:
            messagebox.showerror(
                "Error",
                "Debe ingresar un comentario para rechazar la solicitud"
            )
            return

        try:
            rechazar_evento_hr(self.row_id, comentario)

            messagebox.showinfo(
                "Éxito",
                "Solicitud rechazada correctamente"
            )

            if callable(self.on_reject):
                self.on_reject(self.row_id, comentario)

            self.destroy()

        except Exception as e:
            messagebox.showerror(
                "Error",
                str(e)
            )
