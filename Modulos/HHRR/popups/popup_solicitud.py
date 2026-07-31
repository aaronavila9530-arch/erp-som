import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from api_client import crear_evento_hr, obtener_vacaciones_disponibles
from Modulos.HHRR.date_utils import LONG_DATE_FORMAT, parse_hhrr_date, to_db_date
from Modulos.Servicios.widgets.date_picker import DatePicker


class PopupSolicitud(tk.Toplevel):

    def __init__(self, parent, usuario, rol, on_success):
        super().__init__(parent)

        self.usuario = (usuario or "").strip().lower()   # 🔥 FIX
        self.rol = (rol or "").strip().lower()           # 🔥 FIX
        self.on_success = on_success

        self.title("Nueva Solicitud HHRR")
        self.geometry("480x520")
        self.resizable(False, False)

        self.transient(parent)
        self.grab_set()

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

        tipo = (self.cmb_tipo.get() or "").strip().upper()
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
        DatePicker(self, entry, output_format=LONG_DATE_FORMAT)
        self.after(200, self._calcular_dias)

    def _calcular_dias(self):

        if not hasattr(self, "fecha_inicio") or not hasattr(self, "fecha_fin"):
            return

        try:
            fi = parse_hhrr_date(self.fecha_inicio.get().strip())
            ff = parse_hhrr_date(self.fecha_fin.get().strip())
            if not fi or not ff:
                raise ValueError("Fechas invalidas")
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

        tipo = (self.cmb_tipo.get() or "").strip().upper()

        if not tipo:
            messagebox.showerror("Error", "Seleccione un tipo")
            return

        try:
            payload = {}

            if tipo in ("VACACIONES", "INCAPACIDAD", "LICENCIA"):

                if not hasattr(self, "fecha_inicio") or not hasattr(self, "fecha_fin"):
                    raise ValueError("Debe ingresar fechas")

                fi = to_db_date(self.fecha_inicio.get().strip())
                ff = to_db_date(self.fecha_fin.get().strip())

                if not fi or not ff:
                    raise ValueError("Debe completar fechas")

                self._calcular_dias()
                dias = int(self.lbl_dias.cget("text"))

                if dias <= 0:
                    raise ValueError("Fechas inválidas")

                payload = {
                    "fecha_inicio": fi,
                    "fecha_fin": ff,
                    "dias_solicitados": dias
                }

                if tipo == "LICENCIA":
                    if not self.tipo_licencia.get():
                        raise ValueError("Seleccione tipo de licencia")
                    payload["tipo_licencia"] = self.tipo_licencia.get()

            elif tipo in ("CONSTANCIA_SALARIAL", "CONSTANCIA_LABORAL"):

                if not hasattr(self, "motivo") or not self.motivo.get().strip():
                    raise ValueError("Debe indicar motivo")

                payload = {"motivo": self.motivo.get().strip()}

            crear_evento_hr(
                event_type=tipo,
                payload=payload,
                event_date=to_db_date(datetime.today()),
                usuario=self.usuario,   # 🔥 CRÍTICO
                rol=self.rol            # 🔥 CRÍTICO
            )

            messagebox.showinfo("Éxito", "Solicitud enviada correctamente")

            if callable(self.on_success):
                self.on_success()

            self.destroy()

        except Exception as e:
            messagebox.showerror("Error", str(e))
