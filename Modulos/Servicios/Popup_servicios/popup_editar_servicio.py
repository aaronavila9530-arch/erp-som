import tkinter as tk
from tkinter import ttk, messagebox

from Modulos.Servicios.widgets.date_picker import DatePicker
from Modulos.Servicios.widgets.time_picker import TimePicker
from api_client import get_servicio_api, editar_servicio_api


class PopupEditarServicio(tk.Toplevel):

    def __init__(self, parent, consec, on_success):
        super().__init__(parent)
        self.consec = consec
        self.on_success = on_success

        self.title(f"Editar Servicio {consec}")
        self.geometry("520x420")
        self.config(bg="white")

        # =========================
        # CARGAR DATOS ACTUALES
        # =========================
        data = get_servicio_api(consec)

        # =========================
        # FORMULARIO
        # =========================
        form = tk.Frame(self, bg="white")
        form.pack(padx=20, pady=20, fill="both", expand=True)

        def label(text, r):
            tk.Label(form, text=text, bg="white").grid(row=r, column=0, sticky="w", pady=5)

        # Surveyor
        label("Surveyor:", 0)
        self.surveyor = ttk.Entry(form, width=30)
        self.surveyor.insert(0, data.get("surveyor", ""))
        self.surveyor.grid(row=0, column=1)

        # Honorarios
        label("Honorarios:", 1)
        self.honorarios = ttk.Entry(form)
        self.honorarios.insert(0, data.get("honorarios", ""))
        self.honorarios.grid(row=1, column=1)

        # Costo Operativo
        label("Costo Operativo:", 2)
        self.costo = ttk.Entry(form)
        self.costo.insert(0, data.get("costo_operativo", ""))
        self.costo.grid(row=2, column=1)

        # Fecha inicio
        label("Fecha Inicio:", 3)
        self.fecha_ini = tk.Entry(form, width=12)
        self.fecha_ini.insert(0, data.get("fecha_inicio", ""))
        self.fecha_ini.grid(row=3, column=1, sticky="w")

        tk.Button(
            form,
            text="📅",
            command=lambda: DatePicker(self, self.fecha_ini)
        ).grid(row=3, column=2, padx=5)

        # Hora inicio
        label("Hora Inicio:", 4)
        self.hora_ini = tk.Entry(form, width=10)
        self.hora_ini.insert(0, data.get("hora_inicio", ""))
        self.hora_ini.grid(row=4, column=1, sticky="w")

        tk.Button(
            form,
            text="⏰",
            command=lambda: TimePicker(self, self.hora_ini)
        ).grid(row=4, column=2, padx=5)

        # =========================
        # BOTONES
        # =========================
        btns = tk.Frame(self, bg="white")
        btns.pack(pady=15)

        tk.Button(
            btns,
            text="Guardar",
            bg="#86A9D9",
            font=("Segoe UI", 10, "bold"),
            command=self.guardar
        ).pack(side="left", padx=10)

        tk.Button(
            btns,
            text="Cancelar",
            command=self.destroy
        ).pack(side="left", padx=10)

    # ============================================================
    # GUARDAR
    # ============================================================
    def guardar(self):
        def _to_float_or_none(s):
            s = (s or "").strip()
            if s == "":
                return None
            # Permitir coma decimal por si acaso
            s = s.replace(",", ".")
            return float(s)

        payload = {
            "surveyor": self.surveyor.get().strip(),
            "honorarios": _to_float_or_none(self.honorarios.get()),
            "costo_operativo": _to_float_or_none(self.costo.get()),
            "fecha_inicio": self.fecha_ini.get().strip(),
            "hora_inicio": self.hora_ini.get().strip(),
        }

        resp = editar_servicio_api(self.consec, payload)

        if resp.get("status") == "ok":
            messagebox.showinfo("OK", "Servicio actualizado correctamente.")
            self.on_success()
            self.destroy()
        else:
            # Mostrar el error real (FastAPI suele mandar 'detail')
            err = resp.get("error") or resp.get("detail") or "Error desconocido"
            messagebox.showerror("Error", err)
