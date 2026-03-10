import tkinter as tk
from tkinter import ttk, messagebox

from api_client import (
    get_servicio_api,
    cerrar_operacion_api
)

from Modulos.Servicios.widgets.date_picker import DatePicker
from Modulos.Servicios.widgets.time_picker import TimePicker
from Modulos.Servicios.Popup_servicios.popup_editar_servicio import PopupEditarServicio


class PopupFinalizarServicio(tk.Toplevel):

    def __init__(self, parent, consec, on_success=None):
        super().__init__(parent)

        self.parent = parent
        self.consec = consec
        self.on_success = on_success

        self.title("Finalizar Servicio")
        self.geometry("520x540")
        self.config(bg="white")
        self.transient(parent)
        self.grab_set()

        self._cargar_datos()
        self._build_ui()

    # ============================================================
    # DATA
    # ============================================================
    def _cargar_datos(self):
        self.data = get_servicio_api(self.consec)

        if not self.data:
            messagebox.showerror(
                "Error",
                "No se pudo cargar la información del servicio."
            )
            self.destroy()

    # ============================================================
    # UI
    # ============================================================
    def _build_ui(self):

        self.frame = tk.Frame(self, bg="white")
        self.frame.pack(fill="both", expand=True, padx=20, pady=15)

        def row(label, value, r):
            ttk.Label(
                self.frame,
                text=label,
                font=("Segoe UI", 9)
            ).grid(row=r, column=0, sticky="w", pady=4)

            ttk.Label(
                self.frame,
                text=value if value not in (None, "") else "-",
                font=("Segoe UI", 9),
                foreground="black"
            ).grid(row=r, column=1, sticky="w", pady=4)

        row("Cliente:", self.data.get("cliente"), 0)
        row("Buque:", self.data.get("buque_contenedor"), 1)
        row("Operación:", self.data.get("operacion"), 2)
        row("Detalle:", self.data.get("detalle"), 3)
        row("Surveyor:", self.data.get("surveyor"), 4)
        row("País:", self.data.get("pais"), 5)
        row("Honorarios:", self.data.get("honorarios"), 6)
        row("Costo operativo:", self.data.get("costo_operativo"), 7)
        row("Costo tarjetas:", self.data.get("costo_tarjetas"), 8)
        row("Fecha inicio:", self.data.get("fecha_inicio"), 9)
        row("Hora inicio:", self.data.get("hora_inicio"), 10)

        ttk.Separator(self.frame).grid(
            row=11, columnspan=2, sticky="ew", pady=12
        )

        btns = tk.Frame(self.frame, bg="white")
        btns.grid(row=12, columnspan=2, pady=10, sticky="e")

        ttk.Button(
            btns,
            text="Editar",
            command=self._editar
        ).pack(side="left", padx=5)

        ttk.Button(
            btns,
            text="Finalizar Servicio",
            command=self._abrir_finalizacion
        ).pack(side="left", padx=5)

    # ============================================================
    # EDITAR
    # ============================================================
    def _editar(self):
        self.withdraw()

        def _refresh():
            self.deiconify()
            self.frame.destroy()
            self._cargar_datos()
            self._build_ui()

        PopupEditarServicio(
            self,
            self.consec,
            on_success=_refresh
        )

    # ============================================================
    # VALIDACIÓN INTELIGENTE
    # ============================================================
    def _validar_costos(self):

        def to_float(v):
            try:
                return float(str(v).replace(",", "."))
            except:
                return 0.0

        honorarios = to_float(self.data.get("honorarios"))
        costo_operativo = to_float(self.data.get("costo_operativo"))
        costo_tarjetas = to_float(self.data.get("costo_tarjetas"))

        pais = (self.data.get("pais") or "").strip()
        surveyor = (self.data.get("surveyor") or "").strip()

        # --------------------------------------------------------
        # Regla 1: Al menos uno > 0
        # --------------------------------------------------------
        if honorarios <= 0 and costo_operativo <= 0 and costo_tarjetas <= 0:
            messagebox.showerror(
                "Validación financiera",
                "Debe existir al menos un valor mayor a 0.00\n"
                "(Honorarios, Costo Operativo o Costo Tarjetas)."
            )
            return False

        # --------------------------------------------------------
        # Regla 2: Costa Rica + Pabel Peña
        # --------------------------------------------------------
        if pais == "Costa Rica" and surveyor == "Pabel Peña":
            if costo_tarjetas <= 0:
                messagebox.showerror(
                    "Costo obligatorio",
                    "Para Costa Rica con Pabel Peña\n"
                    "el Costo Tarjetas es obligatorio y debe ser mayor a 0.00."
                )
                return False

        return True

    # ============================================================
    # ABRIR FINALIZACIÓN
    # ============================================================
    def _abrir_finalizacion(self):

        if not self._validar_costos():
            return

        self.top_fin = tk.Toplevel(self)
        self.top_fin.title("Finalizar Servicio")
        self.top_fin.geometry("300x220")
        self.top_fin.transient(self)
        self.top_fin.grab_set()

        tk.Label(self.top_fin, text="Fecha finalización").pack(pady=5)
        self.entry_fecha_fin = tk.Entry(self.top_fin)
        self.entry_fecha_fin.pack()

        tk.Button(
            self.top_fin,
            text="📅",
            command=lambda: DatePicker(self.top_fin, self.entry_fecha_fin)
        ).pack()

        tk.Label(self.top_fin, text="Hora finalización").pack(pady=5)
        self.entry_hora_fin = tk.Entry(self.top_fin)
        self.entry_hora_fin.pack()

        tk.Button(
            self.top_fin,
            text="⏰",
            command=lambda: TimePicker(self.top_fin, self.entry_hora_fin)
        ).pack()

        ttk.Button(
            self.top_fin,
            text="Confirmar",
            command=self._finalizar
        ).pack(pady=10)

    # ============================================================
    # FINALIZAR → BACKEND
    # ============================================================
    def _finalizar(self):

        fecha_fin = self.entry_fecha_fin.get().strip()
        hora_fin = self.entry_hora_fin.get().strip()

        if not fecha_fin or not hora_fin:
            messagebox.showerror(
                "Error",
                "Debe ingresar fecha y hora final."
            )
            return

        # 1️⃣ Cerrar operación
        resp_cierre = cerrar_operacion_api(
            self.consec,
            fecha_fin,
            hora_fin
        )

        if resp_cierre.get("status") != "ok":
            messagebox.showerror(
                "Error",
                resp_cierre.get("error", "No se pudo cerrar la operación.")
            )
            return

        # 2️⃣ Cambiar estado
        from api_client import finalizar_servicio_api

        resp_final = finalizar_servicio_api(self.consec)

        if resp_final.get("status") != "ok":
            messagebox.showerror(
                "Error",
                resp_final.get("error", "No se pudo finalizar el servicio.")
            )
            return

        messagebox.showinfo(
            "Servicio Finalizado",
            f"Servicio {self.consec} finalizado correctamente."
        )

        self.top_fin.destroy()
        self.destroy()

        if self.on_success:
            self.on_success()