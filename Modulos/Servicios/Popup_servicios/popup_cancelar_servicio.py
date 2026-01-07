import tkinter as tk
from tkinter import ttk, messagebox

class PopupCancelarServicio(tk.Toplevel):

    def __init__(self, parent, consec, on_success):
        super().__init__(parent)
        self.title(f"Cancelar servicio {consec}")
        self.geometry("450x350")
        self.configure(bg="white")

        self.consec = consec
        self.on_success = on_success

        # TITULO
        tk.Label(self, text=f"Cancelar servicio {consec}",
                 bg="white", fg="black",
                 font=("Segoe UI", 12, "bold")
        ).pack(pady=10)

        # MOTIVO
        tk.Label(self, text="Motivo de cancelación:",
                 bg="white", font=("Segoe UI", 10, "bold")
        ).pack(anchor="w", padx=10)

        self.cmb_motivo = ttk.Combobox(
            self,
            values=[
                "Precio",
                "Buque atraca en otro puerto",
                "Respuesta tardía",
                "Buque no requerirá los servicios",
            ],
            state="readonly",
            width=40
        )
        self.cmb_motivo.pack(padx=10, pady=5)

        # DESCRIPCIÓN
        tk.Label(self, text="Descripción adicional:",
                 bg="white", font=("Segoe UI", 10, "bold")
        ).pack(anchor="w", padx=10)

        self.txt_extra = tk.Text(self, width=50, height=6)
        self.txt_extra.pack(padx=10, pady=5)

        # BOTONES
        frame_btn = tk.Frame(self, bg="white")
        frame_btn.pack(pady=10)

        ttk.Button(frame_btn, text="Cancelar servicio",
                   command=self.confirmar).pack(side="left", padx=5)

        ttk.Button(frame_btn, text="Cerrar",
                   command=self.destroy).pack(side="left", padx=5)


    def confirmar(self):
        motivo = self.cmb_motivo.get().strip()
        comentario = self.txt_extra.get("1.0", "end").strip()

        if not motivo:
            messagebox.showwarning("Incompleto", "Debe seleccionar un motivo.")
            return

        if not comentario:
            messagebox.showwarning("Incompleto", "Debe escribir una descripción adicional.")
            return

        payload = {
            "estado": "Cancelado",
            "razon_cancelacion": motivo,
            "comentario_cancelacion": comentario
        }

        from api_client import cancelar_servicio_api
        respuesta = cancelar_servicio_api(self.consec, payload)

        if respuesta.get("status") == "ok":
            messagebox.showinfo("Cancelado",
                                f"Servicio {self.consec} cancelado correctamente.")
            self.on_success()  # refrescar tabla
            self.destroy()
        else:
            err = respuesta.get("error", "Error desconocido")
            messagebox.showerror("Error", err)
