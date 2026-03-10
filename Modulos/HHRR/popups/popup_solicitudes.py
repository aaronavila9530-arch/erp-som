import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date

# =========================================================
# API CLIENT REAL (EXISTE)
# =========================================================
from api_client import crear_evento_hr


class PopupSolicitudesHHRR(tk.Toplevel):
    """
    Popup para solicitudes HHRR:
    - Vacaciones
    - Documentos
    - Incapacidades

    TODO es LAZY:
    - NO consulta nada al abrir
    - El usuario debe presiona acciones explícitas
    """

    def __init__(self, parent, empleado_id, usuario, on_success=None):
        super().__init__(parent)

        self.empleado_id = empleado_id
        self.usuario = usuario  # solo informativo (NO se envía al backend)
        self.on_success = on_success

        self.title("Solicitudes HHRR")
        self.geometry("480x620")
        self.resizable(False, False)

        # Modal
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

        # -------------------------------
        # Tipo de solicitud
        # -------------------------------
        ttk.Label(cont, text="Tipo de solicitud").pack(anchor="w")

        self.var_tipo = tk.StringVar()
        ttk.Combobox(
            cont,
            textvariable=self.var_tipo,
            values=["VACACIONES", "DOCUMENTO", "INCAPACIDAD"],
            state="readonly"
        ).pack(fill="x", pady=5)

        # -------------------------------
        # Vacaciones
        # -------------------------------
        self.frm_vacaciones = ttk.LabelFrame(cont, text="Vacaciones")
        self.frm_vacaciones.pack(fill="x", pady=10)

        self.lbl_saldo = ttk.Label(
            self.frm_vacaciones,
            text="Saldo disponible: (cálculo manual)"
        )
        self.lbl_saldo.pack(anchor="w", pady=5)

        ttk.Label(self.frm_vacaciones, text="Desde (YYYY-MM-DD)").pack(anchor="w")
        self.var_vac_desde = tk.StringVar()
        ttk.Entry(self.frm_vacaciones, textvariable=self.var_vac_desde).pack(fill="x")

        ttk.Label(self.frm_vacaciones, text="Hasta (YYYY-MM-DD)").pack(anchor="w")
        self.var_vac_hasta = tk.StringVar()
        ttk.Entry(self.frm_vacaciones, textvariable=self.var_vac_hasta).pack(fill="x")

        # -------------------------------
        # Documentos
        # -------------------------------
        self.frm_documentos = ttk.LabelFrame(cont, text="Documentos")
        self.frm_documentos.pack(fill="x", pady=10)

        ttk.Label(self.frm_documentos, text="Tipo de documento").pack(anchor="w")
        self.var_doc_tipo = tk.StringVar()
        ttk.Combobox(
            self.frm_documentos,
            textvariable=self.var_doc_tipo,
            values=[
                "CONSTANCIA SALARIAL",
                "CONSTANCIA LABORAL",
                "OTROS"
            ],
            state="readonly"
        ).pack(fill="x")

        ttk.Label(self.frm_documentos, text="Detalle").pack(anchor="w")
        self.txt_doc_detalle = tk.Text(self.frm_documentos, height=3)
        self.txt_doc_detalle.pack(fill="x")

        # -------------------------------
        # Incapacidad
        # -------------------------------
        self.frm_incapacidad = ttk.LabelFrame(cont, text="Incapacidad")
        self.frm_incapacidad.pack(fill="x", pady=10)

        ttk.Label(self.frm_incapacidad, text="Desde (YYYY-MM-DD)").pack(anchor="w")
        self.var_inc_desde = tk.StringVar()
        ttk.Entry(self.frm_incapacidad, textvariable=self.var_inc_desde).pack(fill="x")

        ttk.Label(self.frm_incapacidad, text="Hasta (YYYY-MM-DD)").pack(anchor="w")
        self.var_inc_hasta = tk.StringVar()
        ttk.Entry(self.frm_incapacidad, textvariable=self.var_inc_hasta).pack(fill="x")

        ttk.Label(self.frm_incapacidad, text="Observaciones").pack(anchor="w")
        self.txt_inc_obs = tk.Text(self.frm_incapacidad, height=3)
        self.txt_inc_obs.pack(fill="x")

        # -------------------------------
        # Botones
        # -------------------------------
        cont_btn = ttk.Frame(cont)
        cont_btn.pack(fill="x", pady=15)

        ttk.Button(
            cont_btn,
            text="Enviar solicitud",
            command=self._enviar_solicitud
        ).pack(side="right")

        ttk.Button(
            cont_btn,
            text="Cancelar",
            command=self.destroy
        ).pack(side="right", padx=5)

    # =========================================================
    # LÓGICA
    # =========================================================
    def _enviar_solicitud(self):

        tipo = self.var_tipo.get()
        if not tipo:
            messagebox.showerror(
                "Error",
                "Debe seleccionar un tipo de solicitud."
            )
            return

        # -------------------------------
        # Construcción de evento
        # -------------------------------
        if tipo == "VACACIONES":
            if not self.var_vac_desde.get() or not self.var_vac_hasta.get():
                messagebox.showerror(
                    "Error",
                    "Debe indicar fechas de vacaciones."
                )
                return

            event_type = "VACATION"
            payload = {
                "desde": self.var_vac_desde.get(),
                "hasta": self.var_vac_hasta.get()
            }

        elif tipo == "DOCUMENTO":
            if not self.var_doc_tipo.get():
                messagebox.showerror(
                    "Error",
                    "Debe seleccionar tipo de documento."
                )
                return

            event_type = "DOCUMENT_REQUEST"
            payload = {
                "tipo_documento": self.var_doc_tipo.get(),
                "detalle": self.txt_doc_detalle.get("1.0", "end").strip()
            }

        elif tipo == "INCAPACIDAD":
            if not self.var_inc_desde.get() or not self.var_inc_hasta.get():
                messagebox.showerror(
                    "Error",
                    "Debe indicar fechas de incapacidad."
                )
                return

            event_type = "INCAPACITY"
            payload = {
                "desde": self.var_inc_desde.get(),
                "hasta": self.var_inc_hasta.get(),
                "observaciones": self.txt_inc_obs.get("1.0", "end").strip()
            }

        else:
            return

        # -------------------------------
        # Envío al backend (REAL)
        # -------------------------------
        try:
            crear_evento_hr({
                "empleado_id": self.empleado_id,
                "event_type": event_type,
                "event_date": date.today().isoformat(),
                "status": "PENDING",
                "payload": payload
            })
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo enviar la solicitud:\n{e}"
            )
            return

        messagebox.showinfo(
            "Solicitud enviada",
            "La solicitud fue enviada correctamente."
        )

        if callable(self.on_success):
            self.on_success()

        self.destroy()
