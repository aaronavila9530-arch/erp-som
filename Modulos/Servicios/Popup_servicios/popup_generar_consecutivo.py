import tkinter as tk
from tkinter import ttk, messagebox

from Modulos.Servicios.widgets.date_picker import DatePicker
from Modulos.Servicios.widgets.time_picker import TimePicker

from api_client import confirmar_servicio_api, get_servicio_api


class PopupGenerarConsecutivo(tk.Toplevel):

    def __init__(self, parent, consec, valores, callback):
        super().__init__(parent)

        self.parent = parent
        self.consec = consec
        self.valores = valores
        self.callback = callback

        # ==============================
        # CONFIGURACIÓN VENTANA
        # ==============================
        self.title(f"Generar Consecutivo - {consec}")
        self.geometry("420x360")
        self.configure(bg="white")
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)

        self._build_ui()

    # ==========================================================
    # UI
    # ==========================================================
    def _build_ui(self):

        tk.Label(
            self,
            text=f"Generar Consecutivo\nServicio {self.consec}",
            bg="white",
            fg="black",
            font=("Segoe UI", 14, "bold")
        ).pack(pady=15)

        # ========================
        # FECHA INICIO
        # ========================
        tk.Label(
            self,
            text="Fecha de Inicio:",
            bg="white",
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="w", padx=20)

        self.fecha_entry = ttk.Entry(self, width=25)
        self.fecha_entry.pack(padx=20, pady=5)

        fecha_actual = self._get_valor_columna("fecha_inicio")
        if fecha_actual:
            self.fecha_entry.insert(0, fecha_actual)

        ttk.Button(
            self,
            text="📅 Seleccionar fecha",
            command=self._abrir_datepicker
        ).pack(pady=3)

        # ========================
        # HORA INICIO
        # ========================
        tk.Label(
            self,
            text="Hora de Inicio:",
            bg="white",
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="w", padx=20, pady=(10, 0))

        self.hora_entry = ttk.Entry(self, width=25)
        self.hora_entry.pack(padx=20, pady=5)

        hora_actual = self._get_valor_columna("hora_inicio")
        if hora_actual:
            self.hora_entry.insert(0, hora_actual)

        ttk.Button(
            self,
            text="⏰ Seleccionar hora",
            command=self._abrir_timepicker
        ).pack(pady=3)

        # ========================
        # BOTONES
        # ========================
        frame_btn = tk.Frame(self, bg="white")
        frame_btn.pack(pady=25)

        ttk.Button(
            frame_btn,
            text="Generar Consecutivo",
            command=self._confirmar
        ).pack(side="left", padx=10)

        ttk.Button(
            frame_btn,
            text="Cancelar",
            command=self.destroy
        ).pack(side="left", padx=10)

    # ==========================================================
    # HELPERS
    # ==========================================================
    def _abrir_datepicker(self):
        DatePicker(self, self.fecha_entry)

    def _abrir_timepicker(self):
        TimePicker(self, self.hora_entry)

    def _get_valor_columna(self, nombre_columna):

        columnas = [
            "consec","tipo","estado","num_informe","buque_contenedor","cliente",
            "contacto","detalle","continente","pais","puerto","operacion","surveyor",
            "honorarios","costo_operativo","fecha_inicio","hora_inicio","fecha_fin",
            "hora_fin","demoras","duracion","factura","valor_factura","fecha_factura",
            "terminos_pago","fecha_vencimiento","dias_vencido",
            "razon_cancelacion","comentario_cancelacion"
        ]

        try:
            idx = columnas.index(nombre_columna)
            return self.valores[idx] if idx < len(self.valores) else ""
        except ValueError:
            return ""

    # ==========================================================
    # CONFIRMAR → BACKEND GENERA CONSECUTIVO
    # ==========================================================
    def _confirmar(self):

        fecha = self.fecha_entry.get().strip()
        hora = self.hora_entry.get().strip()

        if not fecha or not hora:
            messagebox.showwarning(
                "Campos incompletos",
                "Debe indicar fecha y hora de inicio."
            )
            return

        try:
            # ---------------------------------------------
            # 1️⃣ Confirmar + Generar consecutivo
            # ---------------------------------------------
            resp = confirmar_servicio_api(
                self.consec,
                fecha,
                hora
            )

            if resp.get("status") != "ok":
                messagebox.showerror(
                    "Error",
                    resp.get("error", "Error actualizando servicio.")
                )
                return

            # ---------------------------------------------
            # 2️⃣ Obtener servicio actualizado
            # ---------------------------------------------
            servicio_actualizado = get_servicio_api(self.consec)

            if not servicio_actualizado:
                messagebox.showerror(
                    "Error",
                    "No se pudo obtener el servicio actualizado."
                )
                return

            nuevo_estado = servicio_actualizado.get("estado")
            num_informe = servicio_actualizado.get("num_informe")

            messagebox.showinfo(
                "Consecutivo generado",
                f"Número de informe asignado:\n\n"
                f"{num_informe}\n\n"
                f"Nuevo estado: {nuevo_estado}"
            )

            if self.callback:
                self.callback()

            self.destroy()

        except Exception as e:
            messagebox.showerror(
                "Error inesperado",
                str(e)
            )
