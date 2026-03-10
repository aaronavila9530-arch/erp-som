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
        self.geometry("520x470")
        self.config(bg="white")

        # =========================
        # CARGAR DATOS ACTUALES
        # =========================
        data = get_servicio_api(consec)

        # País actual del servicio
        self.pais_actual = (data.get("pais") or "").strip()

        # =========================
        # FORMULARIO
        # =========================
        form = tk.Frame(self, bg="white")
        form.pack(padx=20, pady=20, fill="both", expand=True)

        def label(text, r):
            tk.Label(
                form,
                text=text,
                bg="white"
            ).grid(row=r, column=0, sticky="w", pady=5)

        # =========================
        # Surveyor
        # =========================
        label("Surveyor:", 0)

        self.surveyor = ttk.Entry(form, width=30)
        self.surveyor.insert(0, data.get("surveyor", ""))
        self.surveyor.grid(row=0, column=1)

        self.surveyor.bind(
            "<KeyRelease>",
            self._toggle_costo_tarjetas
        )

        # =========================
        # Honorarios
        # =========================
        label("Honorarios:", 1)

        self.honorarios = ttk.Entry(form)
        self.honorarios.insert(0, data.get("honorarios", ""))
        self.honorarios.grid(row=1, column=1)

        # =========================
        # Costo Operativo
        # =========================
        label("Costo Operativo:", 2)

        self.costo = ttk.Entry(form)
        self.costo.insert(0, data.get("costo_operativo", ""))
        self.costo.grid(row=2, column=1)

        # =========================
        # Costo Tarjetas
        # =========================
        label("Costo Tarjetas:", 3)

        self.costo_tarjetas = ttk.Entry(form)
        self.costo_tarjetas.insert(
            0,
            data.get("costo_tarjetas", "")
        )
        self.costo_tarjetas.grid(row=3, column=1)

        # =========================
        # Fecha inicio
        # =========================
        label("Fecha Inicio:", 4)

        self.fecha_ini = tk.Entry(form, width=12)
        self.fecha_ini.insert(0, data.get("fecha_inicio", ""))
        self.fecha_ini.grid(row=4, column=1, sticky="w")

        tk.Button(
            form,
            text="📅",
            command=lambda: DatePicker(self, self.fecha_ini)
        ).grid(row=4, column=2, padx=5)

        # =========================
        # Hora inicio
        # =========================
        label("Hora Inicio:", 5)

        self.hora_ini = tk.Entry(form, width=10)
        self.hora_ini.insert(0, data.get("hora_inicio", ""))
        self.hora_ini.grid(row=5, column=1, sticky="w")

        tk.Button(
            form,
            text="⏰",
            command=lambda: TimePicker(self, self.hora_ini)
        ).grid(row=5, column=2, padx=5)

        # Evaluar estado inicial
        self._toggle_costo_tarjetas()

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
    # LÓGICA COSTO TARJETAS
    # ============================================================
    def _toggle_costo_tarjetas(self, event=None):

        surveyor = (self.surveyor.get() or "").strip()

        pais = (self.pais_actual or "").strip()

        surveyor_normalizado = surveyor.lower()
        pais_normalizado = pais.lower()

        permitir = (
            pais_normalizado != "costa rica"
            and surveyor_normalizado == "pabel peña barreto"
        )

        if permitir:
            self.costo_tarjetas.config(state="normal")
        else:
            self.costo_tarjetas.delete(0, tk.END)
            self.costo_tarjetas.config(state="disabled")

    # ============================================================
    # GUARDAR
    # ============================================================
    def guardar(self):

        def _to_float_or_none(valor):

            valor = (valor or "").strip()

            if valor == "":
                return None

            valor = valor.replace(",", ".")

            try:
                return float(valor)
            except Exception:
                return None

        surveyor = (self.surveyor.get() or "").strip()
        pais = (self.pais_actual or "").strip()

        surveyor_normalizado = surveyor.lower()
        pais_normalizado = pais.lower()

        permitir_tarjeta = (
            pais_normalizado != "costa rica"
            and surveyor_normalizado == "pabel peña barreto"
        )

        payload = {
            "surveyor": surveyor,
            "honorarios": _to_float_or_none(self.honorarios.get()),
            "costo_operativo": _to_float_or_none(self.costo.get()),
            "fecha_inicio": self.fecha_ini.get().strip(),
            "hora_inicio": self.hora_ini.get().strip(),
        }

        if permitir_tarjeta:

            payload["costo_tarjetas"] = _to_float_or_none(
                self.costo_tarjetas.get()
            )

        else:

            payload["costo_tarjetas"] = None

        resp = editar_servicio_api(
            self.consec,
            payload
        )

        if resp.get("status") == "ok":

            messagebox.showinfo(
                "OK",
                "Servicio actualizado correctamente."
            )

            self.on_success()

            self.destroy()

        else:

            err = (
                resp.get("error")
                or resp.get("detail")
                or "Error desconocido"
            )

            messagebox.showerror(
                "Error",
                err
            )