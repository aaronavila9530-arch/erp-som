import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from api_client import crear_ot_log, hr_update_ot_log
from Modulos.HHRR.date_utils import LONG_DATE_FORMAT, parse_hhrr_date, parse_hhrr_datetime, to_long_english_date
from Modulos.Servicios.widgets.date_picker import DatePicker


class PopupRegistroHoras(tk.Toplevel):

    def __init__(self, parent, on_success=None, data=None, duplicate=False):
        super().__init__(parent)

        self.parent = parent
        self.on_success = on_success
        self.data = data or {}
        self.duplicate = duplicate
        self.editing_id = None if duplicate else self.data.get("id")

        self.title("Editar horas" if self.editing_id else "Registrar horas")
        self.geometry("760x620")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._build_ui()
        self._load_initial_values()
        self._refresh_duration()

    # =========================================================
    # UI
    # =========================================================
    def _build_ui(self):

        main = ttk.Frame(self)
        main.pack(fill="both", expand=True, padx=15, pady=15)

        ttk.Label(
            main,
            text="Registro inteligente de horas",
            font=("Segoe UI", 13, "bold")
        ).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 8))

        self.lbl_duration = ttk.Label(
            main,
            text="Duración: 0.00 h",
            font=("Segoe UI", 11, "bold"),
            foreground="#0b4f86"
        )
        self.lbl_duration.grid(row=0, column=3, sticky="e", pady=(0, 8))

        ttk.Label(main, text="Actividad *").grid(row=1, column=0, sticky="w")

        self.cmb_tipo = ttk.Combobox(
            main,
            values=["OPERACION", "INFORME"],
            state="readonly",
            width=20
        )
        self.cmb_tipo.grid(row=1, column=1, sticky="w", pady=4)
        self.cmb_tipo.current(0)

        quick = ttk.LabelFrame(main, text="Plantillas rápidas")
        quick.grid(row=2, column=0, columnspan=4, sticky="ew", pady=(6, 10))
        for label, hours in (
            ("Hoy 8 h", 8),
            ("Hoy 10 h", 10),
            ("Hoy 12 h", 12),
            ("Turno noche 12 h", 12),
        ):
            ttk.Button(
                quick,
                text=label,
                command=lambda h=hours, l=label: self._apply_quick_shift(h, night=("noche" in l.lower()))
            ).pack(side="left", padx=5, pady=6)

        ttk.Label(main, text="Fecha inicio *").grid(row=3, column=0, sticky="w")

        self.cal_inicio = ttk.Entry(main, width=15)
        self.cal_inicio.insert(0, to_long_english_date(datetime.today()))
        self.cal_inicio.grid(row=3, column=1, sticky="w", pady=4)
        ttk.Button(
            main,
            text="Calendario",
            width=10,
            command=lambda: DatePicker(self, self.cal_inicio, output_format=LONG_DATE_FORMAT)
        ).grid(row=3, column=1, padx=(120, 0), sticky="w")

        hora_inicio = ttk.Frame(main)
        hora_inicio.grid(row=3, column=2, padx=8, sticky="w")

        self.spin_hi = tk.Spinbox(hora_inicio, from_=0, to=23, width=3, format="%02.0f")
        self.spin_mi = tk.Spinbox(hora_inicio, from_=0, to=59, width=3, format="%02.0f")

        self.spin_hi.delete(0, "end")
        self.spin_hi.insert(0, "08")
        self.spin_mi.delete(0, "end")
        self.spin_mi.insert(0, "00")

        self.spin_hi.pack(side="left")
        ttk.Label(hora_inicio, text=":").pack(side="left", padx=2)
        self.spin_mi.pack(side="left")

        ttk.Label(main, text="Fecha fin *").grid(row=4, column=0, sticky="w")

        self.cal_fin = ttk.Entry(main, width=15)
        self.cal_fin.insert(0, to_long_english_date(datetime.today()))
        self.cal_fin.grid(row=4, column=1, sticky="w", pady=4)
        ttk.Button(
            main,
            text="Calendario",
            width=10,
            command=lambda: DatePicker(self, self.cal_fin, output_format=LONG_DATE_FORMAT)
        ).grid(row=4, column=1, padx=(120, 0), sticky="w")

        hora_fin = ttk.Frame(main)
        hora_fin.grid(row=4, column=2, padx=8, sticky="w")

        self.spin_hf = tk.Spinbox(hora_fin, from_=0, to=23, width=3, format="%02.0f")
        self.spin_mf = tk.Spinbox(hora_fin, from_=0, to=59, width=3, format="%02.0f")

        self.spin_hf.delete(0, "end")
        self.spin_hf.insert(0, "17")
        self.spin_mf.delete(0, "end")
        self.spin_mf.insert(0, "00")

        self.spin_hf.pack(side="left")
        ttk.Label(hora_fin, text=":").pack(side="left", padx=2)
        self.spin_mf.pack(side="left")

        for widget in (self.spin_hi, self.spin_mi, self.spin_hf, self.spin_mf):
            widget.configure(command=self._refresh_duration)
            widget.bind("<KeyRelease>", lambda _e: self._refresh_duration())
            widget.bind("<FocusOut>", lambda _e: self._refresh_duration())

        self.cal_inicio.bind("<FocusOut>", lambda _e: self._refresh_duration())
        self.cal_fin.bind("<FocusOut>", lambda _e: self._refresh_duration())

        ttk.Label(main, text="Referencia *").grid(row=5, column=0, sticky="w")
        self.cmb_referencia_tipo = ttk.Combobox(
            main,
            values=["BUQUE", "CONTENEDOR"],
            state="readonly",
            width=20
        )
        self.cmb_referencia_tipo.grid(row=5, column=1, sticky="w", pady=4)
        self.cmb_referencia_tipo.current(0)

        self.ent_referencia = ttk.Entry(main, width=42)
        self.ent_referencia.grid(row=5, column=2, columnspan=2, sticky="w", pady=4)

        ttk.Label(main, text="Detalle de trabajo").grid(row=6, column=0, sticky="w")
        self.ent_actividad_detalle = ttk.Entry(main, width=72)
        self.ent_actividad_detalle.grid(row=6, column=1, columnspan=3, sticky="w", pady=4)

        ttk.Label(main, text="Comentario").grid(row=7, column=0, sticky="nw")
        self.txt_comentario = tk.Text(main, height=7, width=58, wrap="word")
        self.txt_comentario.grid(row=7, column=1, columnspan=3, sticky="w", pady=4)

        self.lbl_preview = ttk.Label(
            main,
            text="",
            foreground="#555555",
            wraplength=680
        )
        self.lbl_preview.grid(row=8, column=0, columnspan=4, sticky="w", pady=(8, 0))

        btns = ttk.Frame(main)
        btns.grid(row=9, column=0, columnspan=4, pady=20, sticky="e")

        ttk.Button(btns, text="Cancelar", command=self.destroy).pack(side="right", padx=5)

        ttk.Button(
            btns,
            text="Guardar cambios" if self.editing_id else "Registrar",
            command=self._guardar
        ).pack(side="right", padx=5)

    def _load_initial_values(self):
        if not self.data:
            return

        def _set_combo(combo, value):
            value = str(value or "").strip().upper()
            if value in combo["values"]:
                combo.set(value)

        _set_combo(self.cmb_tipo, self.data.get("tipo"))

        inicio = parse_hhrr_datetime(self.data.get("fecha_inicio"))
        fin = parse_hhrr_datetime(self.data.get("fecha_fin"))
        if inicio:
            self.cal_inicio.delete(0, "end")
            self.cal_inicio.insert(0, to_long_english_date(inicio))
            self.spin_hi.delete(0, "end")
            self.spin_hi.insert(0, f"{inicio.hour:02d}")
            self.spin_mi.delete(0, "end")
            self.spin_mi.insert(0, f"{inicio.minute:02d}")
        if fin:
            self.cal_fin.delete(0, "end")
            self.cal_fin.insert(0, to_long_english_date(fin))
            self.spin_hf.delete(0, "end")
            self.spin_hf.insert(0, f"{fin.hour:02d}")
            self.spin_mf.delete(0, "end")
            self.spin_mf.insert(0, f"{fin.minute:02d}")

        ref_tipo = "CONTENEDOR" if self.data.get("contenedor") else "BUQUE"
        self.cmb_referencia_tipo.set(ref_tipo)
        self.ent_referencia.insert(
            0,
            self.data.get("referencia") or self.data.get("buque") or self.data.get("contenedor") or ""
        )
        self.ent_actividad_detalle.insert(0, self.data.get("actividad_detalle") or "")
        self.txt_comentario.insert("1.0", self.data.get("comentario") or "")

    def _apply_quick_shift(self, hours: int, night=False):
        today = datetime.today()
        start_hour = 18 if night else 8
        end_hour = (start_hour + hours) % 24
        end_day = today
        if night or end_hour <= start_hour:
            from datetime import timedelta
            end_day = today + timedelta(days=1)

        self.cal_inicio.delete(0, "end")
        self.cal_inicio.insert(0, to_long_english_date(today))
        self.cal_fin.delete(0, "end")
        self.cal_fin.insert(0, to_long_english_date(end_day))
        self._set_time(self.spin_hi, self.spin_mi, start_hour, 0)
        self._set_time(self.spin_hf, self.spin_mf, end_hour, 0)
        self._refresh_duration()

    def _set_time(self, spin_h, spin_m, hour, minute):
        spin_h.delete(0, "end")
        spin_h.insert(0, f"{hour:02d}")
        spin_m.delete(0, "end")
        spin_m.insert(0, f"{minute:02d}")

    def _build_datetimes(self):
        fecha_inicio = parse_hhrr_date(self.cal_inicio.get())
        fecha_fin = parse_hhrr_date(self.cal_fin.get())
        if not fecha_inicio or not fecha_fin:
            raise ValueError("Debe seleccionar fechas validas")

        inicio_dt = datetime.combine(fecha_inicio, datetime.min.time()).replace(
            hour=int(self.spin_hi.get()),
            minute=int(self.spin_mi.get())
        )
        fin_dt = datetime.combine(fecha_fin, datetime.min.time()).replace(
            hour=int(self.spin_hf.get()),
            minute=int(self.spin_mf.get())
        )
        if fin_dt <= inicio_dt:
            raise ValueError("La fecha fin debe ser mayor a inicio")
        return inicio_dt, fin_dt

    def _refresh_duration(self):
        try:
            inicio_dt, fin_dt = self._build_datetimes()
            duracion = round((fin_dt - inicio_dt).total_seconds() / 3600, 2)
            self.lbl_duration.config(text=f"Duración: {duracion:.2f} h")
            self.lbl_preview.config(
                text=f"Se registrará de {inicio_dt:%Y-%m-%d %H:%M} a {fin_dt:%Y-%m-%d %H:%M}."
            )
        except Exception:
            self.lbl_duration.config(text="Duración: revisar fechas")
            self.lbl_preview.config(text="")

    # =========================================================
    # LOGICA
    # =========================================================
    def _guardar(self):

        try:
            tipo = (self.cmb_tipo.get() or "").strip().upper()

            if tipo not in ("OPERACION", "INFORME"):
                raise ValueError("Tipo inválido")

            inicio_dt, fin_dt = self._build_datetimes()

            referencia_tipo = (self.cmb_referencia_tipo.get() or "BUQUE").strip().upper()
            referencia = self.ent_referencia.get().strip()

            if not referencia:
                raise ValueError("Debe indicar el buque o contenedor trabajado")

            payload = {
                "tipo": tipo,
                "fecha_inicio": inicio_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "fecha_fin": fin_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "usuario": self.data.get("usuario"),
                "referencia_tipo": referencia_tipo,
                "referencia": referencia,
                "buque": referencia if referencia_tipo == "BUQUE" else None,
                "contenedor": referencia if referencia_tipo == "CONTENEDOR" else None,
                "actividad_detalle": self.ent_actividad_detalle.get().strip() or None,
                "comentario": self.txt_comentario.get("1.0", "end").strip() or None
            }

            if self.editing_id:
                result = hr_update_ot_log(self.editing_id, payload)
            else:
                result = crear_ot_log(payload)

        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        status = result.get("hours_status", {}) if isinstance(result, dict) else {}
        mensaje = status.get("mensaje") or ("Horas actualizadas correctamente." if self.editing_id else "Horas registradas correctamente.")
        if status.get("alert_level") in ("LIMIT", "OVER_MAX", "WARNING"):
            messagebox.showwarning("Horas registradas", mensaje)
        else:
            messagebox.showinfo("Éxito", mensaje)

        if self.on_success:
            self.on_success()

        self.destroy()
