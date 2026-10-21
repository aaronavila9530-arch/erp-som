import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from api_client import crear_ot_log
from Modulos.HHRR.date_utils import LONG_DATE_FORMAT, parse_hhrr_datetime
from Modulos.Servicios.widgets.date_picker import DatePicker


class PopupRegistroHoras(tk.Toplevel):

    def __init__(self, parent, usuario, on_success=None):
        super().__init__(parent)

        self.usuario = usuario
        self.on_success = on_success

        self.title("Registro de Horas Trabajadas")
        self.geometry("420x520")
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

        ttk.Label(cont, text="Tipo de actividad").pack(anchor="w")

        self.var_tipo = tk.StringVar(value="OPERACION")

        self.cmb_tipo = ttk.Combobox(
            cont,
            textvariable=self.var_tipo,
            values=["OPERACION", "INFORME"],
            state="readonly"
        )
        self.cmb_tipo.pack(fill="x", pady=5)

        ttk.Label(
            cont,
            text="Fecha y hora de inicio"
        ).pack(anchor="w")

        self.var_inicio = tk.StringVar()
        self._date_time_entry(cont, self.var_inicio).pack(fill="x", pady=5)

        ttk.Label(
            cont,
            text="Fecha y hora de fin"
        ).pack(anchor="w")

        self.var_fin = tk.StringVar()
        self._date_time_entry(cont, self.var_fin).pack(fill="x", pady=5)

        ttk.Label(cont, text="Referencia").pack(anchor="w")
        self.var_referencia_tipo = tk.StringVar(value="BUQUE")
        ttk.Combobox(
            cont,
            textvariable=self.var_referencia_tipo,
            values=["BUQUE", "CONTENEDOR"],
            state="readonly"
        ).pack(fill="x", pady=5)

        self.var_referencia = tk.StringVar()
        ttk.Entry(cont, textvariable=self.var_referencia).pack(fill="x", pady=5)

        ttk.Label(cont, text="Detalle de trabajo").pack(anchor="w")
        self.var_actividad_detalle = tk.StringVar()
        ttk.Entry(cont, textvariable=self.var_actividad_detalle).pack(fill="x", pady=5)

        ttk.Label(cont, text="Comentario").pack(anchor="w")
        self.txt_comentario = tk.Text(cont, height=4)
        self.txt_comentario.pack(fill="x", pady=5)

        cont_btn = ttk.Frame(cont)
        cont_btn.pack(fill="x", pady=15)

        ttk.Button(
            cont_btn,
            text="Guardar registro",
            command=self._guardar
        ).pack(side="right")

        ttk.Button(
            cont_btn,
            text="Cancelar",
            command=self.destroy
        ).pack(side="right", padx=5)

    def _date_time_entry(self, parent, var):
        frame = ttk.Frame(parent)
        entry = ttk.Entry(frame)
        entry.pack(side="left", fill="x", expand=True)

        ttk.Button(
            frame,
            text="📅",
            width=3,
            command=lambda: DatePicker(self, entry, output_format=LONG_DATE_FORMAT)
        ).pack(side="left", padx=(5, 0))

        ttk.Label(frame, text="HH:MM").pack(side="left", padx=(8, 3))
        time_entry = ttk.Entry(frame, width=6)
        time_entry.pack(side="left")

        def sync_value(*_):
            date_text = entry.get().strip()
            time_text = time_entry.get().strip()
            if date_text and time_text:
                var.set(f"{date_text} {time_text}")

        entry.bind("<FocusOut>", sync_value)
        time_entry.bind("<FocusOut>", sync_value)
        return frame

    # =========================================================
    # LÓGICA
    # =========================================================
    def _guardar(self):

        # -------------------------------
        # LIMPIEZA / NORMALIZACIÓN
        # -------------------------------
        tipo = (self.var_tipo.get() or "").strip().upper()
        inicio_str = (self.var_inicio.get() or "").strip()
        fin_str = (self.var_fin.get() or "").strip()
        referencia_tipo = (self.var_referencia_tipo.get() or "BUQUE").strip().upper()
        referencia = (self.var_referencia.get() or "").strip()
        comentario = self.txt_comentario.get("1.0", "end").strip() or None

        # -------------------------------
        # VALIDACIONES
        # -------------------------------
        if tipo not in ("OPERACION", "INFORME"):
            messagebox.showerror("Error", "Tipo inválido")
            return

        if not inicio_str or not fin_str:
            messagebox.showerror("Error", "Debe completar fechas")
            return

        if not referencia:
            messagebox.showerror("Error", "Debe indicar el buque o contenedor trabajado")
            return

        try:
            inicio = parse_hhrr_datetime(inicio_str)
            fin = parse_hhrr_datetime(fin_str)
            if not inicio or not fin:
                raise ValueError
        except ValueError:
            messagebox.showerror(
                "Formato inválido",
                "Seleccione la fecha y complete la hora en formato HH:MM"
            )
            return

        if fin <= inicio:
            messagebox.showerror(
                "Error",
                "La fecha fin debe ser mayor a inicio"
            )
            return

        # -------------------------------
        # PAYLOAD LIMPIO (SIN DURACIÓN)
        # -------------------------------
        data = {
            "tipo": tipo,
            "fecha_inicio": inicio.strftime("%Y-%m-%d %H:%M:%S"),
            "fecha_fin": fin.strftime("%Y-%m-%d %H:%M:%S"),
            "referencia_tipo": referencia_tipo,
            "referencia": referencia,
            "buque": referencia if referencia_tipo == "BUQUE" else None,
            "contenedor": referencia if referencia_tipo == "CONTENEDOR" else None,
            "actividad_detalle": (self.var_actividad_detalle.get() or "").strip() or None,
            "comentario": comentario
        }

        # -------------------------------
        # API CALL
        # -------------------------------
        try:
            result = crear_ot_log(data)
        except Exception as e:
            messagebox.showerror(
                "Error backend",
                f"No se pudo guardar:\n{e}"
            )
            return

        status = result.get("hours_status", {}) if isinstance(result, dict) else {}
        mensaje = status.get("mensaje") or "Horas registradas correctamente"
        if status.get("alert_level") in ("WARNING", "LIMIT", "OVER_MAX"):
            messagebox.showwarning("Horas registradas", mensaje)
        else:
            messagebox.showinfo("Éxito", mensaje)

        if callable(self.on_success):
            self.on_success()

        self.destroy()
