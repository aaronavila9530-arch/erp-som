import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from api_client import crear_evento_hr, obtener_vacaciones_disponibles
from Modulos.Servicios.widgets.date_picker import DatePicker


class PopupSolicitud(tk.Toplevel):
    """
    Popup para crear solicitudes HHRR
    Compatible 100% con router backend existente
    """

    def __init__(self, parent, on_success):
        super().__init__(parent)

        self.on_success = on_success
        self.title("Nueva Solicitud HHRR")
        self.geometry("480x520")
        self.resizable(False, False)

        self._build_ui()

    # =========================================================
    # UI
    # =========================================================
    def _build_ui(self):
        pad = 8

        ttk.Label(self, text="Tipo de solicitud").grid(
            row=0, column=0, padx=pad, pady=pad, sticky="w"
        )

        self.cmb_tipo = ttk.Combobox(
            self,
            state="readonly",
            values=[
                "VACACIONES",
                "CONSTANCIA_SALARIAL",
                "CONSTANCIA_LABORAL",
                "INCAPACIDAD",
                "LICENCIA"
            ]
        )
        self.cmb_tipo.grid(row=0, column=1, padx=pad, pady=pad)
        self.cmb_tipo.bind("<<ComboboxSelected>>", self._render_dynamic_fields)

        self.frm_dynamic = ttk.Frame(self)
        self.frm_dynamic.grid(
            row=1, column=0, columnspan=2, padx=pad, pady=pad, sticky="nsew"
        )

        ttk.Button(self, text="Enviar", command=self._submit).grid(
            row=30, column=0, padx=pad, pady=pad
        )
        ttk.Button(self, text="Cancelar", command=self.destroy).grid(
            row=30, column=1, padx=pad, pady=pad
        )

    # =========================================================
    # CAMPOS DINÁMICOS
    # =========================================================
    def _clear_dynamic(self):
        for w in self.frm_dynamic.winfo_children():
            w.destroy()

    def _render_dynamic_fields(self, *_):
        self._clear_dynamic()
        tipo = self.cmb_tipo.get()
        pad = 6
        row = 0

        def fecha(label, attr):
            nonlocal row
            ttk.Label(self.frm_dynamic, text=label).grid(
                row=row, column=0, padx=pad, pady=pad, sticky="w"
            )
            entry = ttk.Entry(self.frm_dynamic, width=15)
            entry.grid(row=row, column=1)
            ttk.Button(
                self.frm_dynamic,
                text="📅",
                width=3,
                command=lambda e=entry: self._pick_date(e)
            ).grid(row=row, column=2)
            setattr(self, attr, entry)
            row += 1

        if tipo in ("VACACIONES", "INCAPACIDAD", "LICENCIA"):

            if tipo == "LICENCIA":
                ttk.Label(self.frm_dynamic, text="Tipo licencia").grid(
                    row=row, column=0, padx=pad, pady=pad, sticky="w"
                )
                self.tipo_licencia = ttk.Combobox(
                    self.frm_dynamic,
                    state="readonly",
                    values=[
                        "PERSONAL",
                        "PATERNIDAD",
                        "MATERNIDAD",
                        "DUELO",
                        "ESTUDIO"
                    ]
                )
                self.tipo_licencia.grid(row=row, column=1)
                row += 1

            fecha("Fecha inicio", "fecha_inicio")
            fecha("Fecha fin", "fecha_fin")

            ttk.Label(self.frm_dynamic, text="Días solicitados").grid(
                row=row, column=0, padx=pad, pady=pad, sticky="w"
            )
            self.lbl_dias = ttk.Label(self.frm_dynamic, text="0")
            self.lbl_dias.grid(row=row, column=1, sticky="w")
            row += 1

            ttk.Label(self.frm_dynamic, text="Días disponibles").grid(
                row=row, column=0, padx=pad, pady=pad, sticky="w"
            )
            self.lbl_disponibles = ttk.Label(self.frm_dynamic, text="—")
            self.lbl_disponibles.grid(row=row, column=1, sticky="w")
            row += 1

            ttk.Label(self.frm_dynamic, text="Saldo restante").grid(
                row=row, column=0, padx=pad, pady=pad, sticky="w"
            )
            self.lbl_saldo = ttk.Label(self.frm_dynamic, text="—")
            self.lbl_saldo.grid(row=row, column=1, sticky="w")

            if tipo == "VACACIONES":
                try:
                    data = obtener_vacaciones_disponibles()
                    self.dias_disponibles = float(data.get("dias_disponibles", 0))
                    self.lbl_disponibles.config(text=str(self.dias_disponibles))
                except Exception:
                    self.dias_disponibles = 0
                    self.lbl_disponibles.config(text="0")

        elif tipo in ("CONSTANCIA_SALARIAL", "CONSTANCIA_LABORAL"):
            ttk.Label(self.frm_dynamic, text="Motivo").grid(
                row=row, column=0, padx=pad, pady=pad, sticky="w"
            )
            self.motivo = ttk.Entry(self.frm_dynamic, width=34)
            self.motivo.grid(row=row, column=1, columnspan=2)

    # =========================================================
    # UTILIDADES
    # =========================================================
    def _pick_date(self, entry):
        DatePicker(self, entry)
        self.after(200, self._calcular_dias)

    def _calcular_dias(self):
        try:
            fi = datetime.strptime(self.fecha_inicio.get(), "%Y-%m-%d").date()
            ff = datetime.strptime(self.fecha_fin.get(), "%Y-%m-%d").date()
            dias = (ff - fi).days + 1
            if dias < 0:
                dias = 0
        except Exception:
            dias = 0

        if hasattr(self, "lbl_dias"):
            self.lbl_dias.config(text=str(dias))

        if hasattr(self, "lbl_saldo") and hasattr(self, "dias_disponibles"):
            saldo = self.dias_disponibles - dias
            self.lbl_saldo.config(text=str(round(saldo, 2)))

    # =========================================================
    # SUBMIT
    # =========================================================
    def _submit(self):
        tipo = self.cmb_tipo.get()
        if not tipo:
            messagebox.showerror("Error", "Seleccione un tipo de solicitud")
            return

        try:
            payload = {}

            if tipo in ("VACACIONES", "INCAPACIDAD", "LICENCIA"):
                self._calcular_dias()
                dias = int(self.lbl_dias.cget("text"))

                if dias <= 0:
                    raise ValueError("Fechas inválidas")

                payload = {
                    "fecha_inicio": self.fecha_inicio.get(),
                    "fecha_fin": self.fecha_fin.get(),
                    "dias_solicitados": dias
                }

                if tipo == "LICENCIA":
                    if not self.tipo_licencia.get():
                        raise ValueError("Seleccione tipo de licencia")
                    payload["tipo_licencia"] = self.tipo_licencia.get()

            elif tipo in ("CONSTANCIA_SALARIAL", "CONSTANCIA_LABORAL"):
                if not self.motivo.get().strip():
                    raise ValueError("Debe indicar un motivo")
                payload = {"motivo": self.motivo.get().strip()}

            crear_evento_hr(
                event_type=tipo,
                payload=payload,
                event_date=datetime.today().strftime("%Y-%m-%d")
            )

            messagebox.showinfo("Éxito", "Solicitud enviada correctamente")

            # 🔁 AUTO REFRESH TABLA
            if callable(self.on_success):
                self.on_success()

            # ❌ AUTO CLOSE
            self.destroy()

        except Exception as e:
            messagebox.showerror("Error", str(e))
