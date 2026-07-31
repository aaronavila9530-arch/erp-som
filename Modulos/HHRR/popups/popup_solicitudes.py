import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date

from api_client import crear_evento_hr
from Modulos.HHRR.date_utils import LONG_DATE_FORMAT, to_db_date
from Modulos.Servicios.widgets.date_picker import DatePicker


class PopupSolicitudesHHRR(tk.Toplevel):

    def __init__(self, parent, empleado_id, usuario, rol, on_success=None):
        super().__init__(parent)

        self.usuario = (usuario or "").strip().lower()   # 🔥 FIX
        self.rol = (rol or "").strip().lower()           # 🔥 FIX
        self.on_success = on_success

        self.title("Solicitudes HHRR")
        self.geometry("480x620")
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

        ttk.Label(cont, text="Tipo de solicitud").pack(anchor="w")

        self.var_tipo = tk.StringVar()
        ttk.Combobox(
            cont,
            textvariable=self.var_tipo,
            values=["VACACIONES", "CONSTANCIA_SALARIAL", "CONSTANCIA_LABORAL", "INCAPACIDAD"],
            state="readonly"
        ).pack(fill="x", pady=5)

        # ================= VACACIONES =================
        self.frm_vacaciones = ttk.LabelFrame(cont, text="Vacaciones")
        self.frm_vacaciones.pack(fill="x", pady=10)

        ttk.Label(self.frm_vacaciones, text="Desde").pack(anchor="w")
        self.var_vac_desde = tk.StringVar()
        self._date_entry(self.frm_vacaciones, self.var_vac_desde).pack(fill="x")

        ttk.Label(self.frm_vacaciones, text="Hasta").pack(anchor="w")
        self.var_vac_hasta = tk.StringVar()
        self._date_entry(self.frm_vacaciones, self.var_vac_hasta).pack(fill="x")

        # ================= DOCUMENTOS =================
        self.frm_documentos = ttk.LabelFrame(cont, text="Documentos")
        self.frm_documentos.pack(fill="x", pady=10)

        ttk.Label(self.frm_documentos, text="Tipo de documento").pack(anchor="w")
        self.var_doc_tipo = tk.StringVar()
        ttk.Combobox(
            self.frm_documentos,
            textvariable=self.var_doc_tipo,
            values=["CONSTANCIA_SALARIAL", "CONSTANCIA_LABORAL"],
            state="readonly"
        ).pack(fill="x")

        ttk.Label(self.frm_documentos, text="Detalle").pack(anchor="w")
        self.txt_doc_detalle = tk.Text(self.frm_documentos, height=3)
        self.txt_doc_detalle.pack(fill="x")

        # ================= INCAPACIDAD =================
        self.frm_incapacidad = ttk.LabelFrame(cont, text="Incapacidad")
        self.frm_incapacidad.pack(fill="x", pady=10)

        ttk.Label(self.frm_incapacidad, text="Desde").pack(anchor="w")
        self.var_inc_desde = tk.StringVar()
        self._date_entry(self.frm_incapacidad, self.var_inc_desde).pack(fill="x")

        ttk.Label(self.frm_incapacidad, text="Hasta").pack(anchor="w")
        self.var_inc_hasta = tk.StringVar()
        self._date_entry(self.frm_incapacidad, self.var_inc_hasta).pack(fill="x")

        ttk.Label(self.frm_incapacidad, text="Observaciones").pack(anchor="w")
        self.txt_inc_obs = tk.Text(self.frm_incapacidad, height=3)
        self.txt_inc_obs.pack(fill="x")

        # ================= BOTONES =================
        cont_btn = ttk.Frame(cont)
        cont_btn.pack(fill="x", pady=15)

        ttk.Button(cont_btn, text="Enviar solicitud", command=self._enviar_solicitud).pack(side="right")
        ttk.Button(cont_btn, text="Cancelar", command=self.destroy).pack(side="right", padx=5)

    # =========================================================
    # LÓGICA
    # =========================================================
    def _enviar_solicitud(self):

        tipo = (self.var_tipo.get() or "").strip().upper()

        if not tipo:
            messagebox.showerror("Error", "Seleccione un tipo")
            return

        try:

            payload = {}

            if tipo == "VACACIONES":
                fi = to_db_date(self.var_vac_desde.get().strip())
                ff = to_db_date(self.var_vac_hasta.get().strip())

                if not fi or not ff:
                    raise ValueError("Debe indicar fechas")

                payload = {
                    "fecha_inicio": fi,
                    "fecha_fin": ff
                }

            elif tipo in ("CONSTANCIA_SALARIAL", "CONSTANCIA_LABORAL"):

                motivo = self.txt_doc_detalle.get("1.0", "end").strip()
                if not motivo:
                    raise ValueError("Debe indicar detalle")

                payload = {"motivo": motivo}

            elif tipo == "INCAPACIDAD":

                fi = to_db_date(self.var_inc_desde.get().strip())
                ff = to_db_date(self.var_inc_hasta.get().strip())

                if not fi or not ff:
                    raise ValueError("Debe indicar fechas")

                payload = {
                    "fecha_inicio": fi,
                    "fecha_fin": ff,
                    "observaciones": self.txt_inc_obs.get("1.0", "end").strip() or None
                }

            else:
                raise ValueError("Tipo inválido")

            # 🔥 FIX REAL (SIN empleado_id)
            crear_evento_hr(
                event_type=tipo,
                payload=payload,
                event_date=to_db_date(date.today()),
                usuario=self.usuario,     # 🔥 FIX
                rol=self.rol              # 🔥 FIX
            )

        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        messagebox.showinfo("Éxito", "Solicitud enviada correctamente")

        if callable(self.on_success):
            self.on_success()

        self.destroy()

    def _date_entry(self, parent, var):
        frame = ttk.Frame(parent)
        entry = ttk.Entry(frame, textvariable=var)
        entry.pack(side="left", fill="x", expand=True)
        ttk.Button(
            frame,
            text="📅",
            width=3,
            command=lambda: DatePicker(self, entry, output_format=LONG_DATE_FORMAT)
        ).pack(side="left", padx=(5, 0))
        return frame
