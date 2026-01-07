import tkinter as tk
from tkinter import ttk, messagebox
from Modulos.Servicios.widgets.date_picker import DatePicker
from Modulos.Servicios.widgets.time_picker import TimePicker

class PopupConfirmarServicio(tk.Toplevel):

    def __init__(self, parent, consec, valores, callback):
        super().__init__(parent)
        self.title(f"Confirmar servicio {consec}")
        self.geometry("420x350")
        self.configure(bg="white")

        self.consec = consec
        self.callback = callback
        self.valores = valores  # valores de la fila actual

        # EXTRAER FECHA Y HORA ACTUAL
        fecha_actual = valores[self._col_index("fecha_inicio")]
        hora_actual = valores[self._col_index("hora_inicio")]

        tk.Label(self, text=f"Confirmar Servicio {consec}",
                 bg="white", fg="black", font=("Segoe UI", 14, "bold")
                 ).pack(pady=10)

        # ========================
        # FECHA INICIO
        # ========================
        tk.Label(self, text="Fecha de Inicio:", bg="white", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=10)

        self.fecha_entry = ttk.Entry(self, width=20)
        self.fecha_entry.pack(padx=10, pady=5)
        self.fecha_entry.insert(0, fecha_actual)

        ttk.Button(self, text="📅 Seleccionar fecha",
                   command=self._abrir_datepicker).pack(pady=3)

        # ========================
        # HORA INICIO
        # ========================
        tk.Label(self, text="Hora de Inicio:", bg="white", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=10)

        self.hora_entry = ttk.Entry(self, width=20)
        self.hora_entry.pack(padx=10, pady=5)
        self.hora_entry.insert(0, hora_actual)

        ttk.Button(self, text="⏱ Seleccionar hora",
                   command=self._abrir_timepicker).pack(pady=3)

        # ========================
        # BOTONES
        # ========================
        frame_btn = tk.Frame(self, bg="white")
        frame_btn.pack(pady=20)

        ttk.Button(frame_btn, text="Confirmar", command=self._confirmar).pack(side="left", padx=5)
        ttk.Button(frame_btn, text="Cancelar", command=self.destroy).pack(side="left", padx=5)

    # --------------------------
    def _abrir_datepicker(self):
        dp = DatePicker(self, self.fecha_entry)
        dp.grab_set()

    # --------------------------
    def _abrir_timepicker(self):
        tp = TimePicker(self, self.hora_entry)
        tp.grab_set()

    # --------------------------
    def _col_index(self, nombre):
        """Retorna el índice de la columna por nombre para extraer valores."""
        columnas = [
            "consec","tipo","estado","num_informe","buque_contenedor","cliente",
            "contacto","detalle","continente","pais","puerto","operacion","surveyor",
            "honorarios","costo_operativo","fecha_inicio","hora_inicio","fecha_fin",
            "hora_fin","demoras","duracion","factura","valor_factura","fecha_factura",
            "terminos_pago","fecha_vencimiento","dias_vencido",
            "razon_cancelacion","comentario_cancelacion"
        ]
        return columnas.index(nombre)

    # --------------------------
    def _confirmar(self):
        fecha = self.fecha_entry.get().strip()
        hora = self.hora_entry.get().strip()

        if not fecha or not hora:
            messagebox.showwarning("Campos incompletos", "Debe indicar fecha y hora.")
            return

        from api_client import confirmar_servicio_api
        r = confirmar_servicio_api(self.consec, fecha, hora)

        if r.get("status") == "ok":
            messagebox.showinfo("Confirmado", "Servicio confirmado correctamente.")
            self.callback()  # refrescar tabla
            self.destroy()
        else:
            messagebox.showerror("Error", r.get("error", "Error desconocido"))
