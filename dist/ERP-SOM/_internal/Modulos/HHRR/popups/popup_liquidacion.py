import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date

from Modulos.HHRR.date_utils import LONG_DATE_FORMAT, parse_hhrr_date, to_db_date
from Modulos.Servicios.widgets.date_picker import DatePicker

# =========================================================
# SERVICIO REAL (NO API)
# =========================================================
from backend_api.services.liquidacion_calculator import CalculadoraLiquidacionCR

# =========================================================
# API REAL
# =========================================================
from api_client import crear_evento_hr, hr_listar_empleados


class PopupLiquidacion(tk.Toplevel):
    """
    Popup de Liquidación Costa Rica.
    SOLO Admin / Gerencia / Master.
    """

    def __init__(self, parent, empleado_id=None, usuario=None):
        super().__init__(parent)

        self.empleado_id = empleado_id
        self.usuario = usuario
        self.calculo = None
        self.empleados = []

        self.title("Liquidación Laboral")
        self.geometry("620x700")
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

        ttk.Label(cont, text="Empleado").pack(anchor="w")
        self.var_empleado = tk.StringVar()
        self.cmb_empleado = ttk.Combobox(cont, textvariable=self.var_empleado, state="readonly")
        self.cmb_empleado.pack(fill="x", pady=5)
        self.cmb_empleado.bind("<<ComboboxSelected>>", lambda _e: self._cargar_empleado_seleccionado())

        # -------------------------------
        # Tipo de despido
        # -------------------------------
        ttk.Label(cont, text="Tipo de despido").pack(anchor="w")
        self.var_tipo = tk.StringVar(value="CON RESPONSABILIDAD")

        ttk.Combobox(
            cont,
            textvariable=self.var_tipo,
            values=[
                "CON RESPONSABILIDAD",
                "SIN RESPONSABILIDAD"
            ],
            state="readonly"
        ).pack(fill="x", pady=5)

        ttk.Label(cont, text="Orden patronal").pack(anchor="w")
        self.var_orden = tk.StringVar(value="CON ORDEN PATRONAL")
        ttk.Combobox(
            cont,
            textvariable=self.var_orden,
            values=["CON ORDEN PATRONAL", "SIN ORDEN PATRONAL"],
            state="readonly"
        ).pack(fill="x", pady=5)

        ttk.Label(cont, text="Fecha de ingreso").pack(anchor="w")
        self.var_fecha_ingreso = tk.StringVar()
        ingreso_frame = ttk.Frame(cont)
        ingreso_frame.pack(fill="x")
        self.ent_fecha_ingreso = ttk.Entry(ingreso_frame, textvariable=self.var_fecha_ingreso)
        self.ent_fecha_ingreso.pack(side="left", fill="x", expand=True)
        ttk.Button(
            ingreso_frame,
            text="📅",
            width=3,
            command=lambda: DatePicker(self, self.ent_fecha_ingreso, output_format=LONG_DATE_FORMAT)
        ).pack(side="left", padx=(5, 0))

        # -------------------------------
        # Fecha salida
        # -------------------------------
        ttk.Label(cont, text="Fecha de salida").pack(anchor="w")
        self.var_fecha_salida = tk.StringVar()
        fecha_frame = ttk.Frame(cont)
        fecha_frame.pack(fill="x")
        self.ent_fecha_salida = ttk.Entry(fecha_frame, textvariable=self.var_fecha_salida)
        self.ent_fecha_salida.pack(side="left", fill="x", expand=True)
        ttk.Button(
            fecha_frame,
            text="📅",
            width=3,
            command=lambda: DatePicker(self, self.ent_fecha_salida, output_format=LONG_DATE_FORMAT)
        ).pack(side="left", padx=(5, 0))

        # -------------------------------
        # Salario mensual
        # -------------------------------
        ttk.Label(cont, text="Salario mensual (CRC)").pack(anchor="w")
        self.var_salario = tk.StringVar()
        ttk.Entry(cont, textvariable=self.var_salario).pack(fill="x")

        # -------------------------------
        # Vacaciones
        # -------------------------------
        ttk.Label(cont, text="Vacaciones pendientes (días)").pack(anchor="w")
        self.var_vacaciones = tk.StringVar(value="0")
        ttk.Entry(cont, textvariable=self.var_vacaciones).pack(fill="x")

        ttk.Button(
            cont,
            text="Calcular liquidación",
            command=self._calcular
        ).pack(pady=10)

        self.txt_resultado = tk.Text(cont, height=12)
        self.txt_resultado.pack(fill="both", pady=5)
        self.txt_resultado.config(state="disabled")

        ttk.Button(
            cont,
            text="Registrar liquidación",
            command=self._registrar
        ).pack(pady=10)

        self._load_empleados()

    def _load_empleados(self):
        try:
            resp = hr_listar_empleados(page=1, page_size=100, estado="Activo")
            self.empleados = resp.get("data", []) if isinstance(resp, dict) else []
        except Exception:
            self.empleados = []

        labels = []
        for emp in self.empleados:
            label = f"{emp.get('id')} - {emp.get('nombre','')} {emp.get('apellidos','')}".strip()
            labels.append(label)
            if self.empleado_id and str(emp.get("id")) == str(self.empleado_id):
                self.var_empleado.set(label)
        self.cmb_empleado["values"] = labels
        if labels and not self.var_empleado.get():
            self.var_empleado.set(labels[0])
        self._cargar_empleado_seleccionado()

    def _selected_emp(self):
        selected = (self.var_empleado.get() or "").split(" - ", 1)[0].strip()
        for emp in self.empleados:
            if str(emp.get("id")) == selected:
                return emp
        return None

    def _set_date_var(self, var, value):
        if not value:
            return
        try:
            parsed = date.fromisoformat(str(value)[:10])
            var.set(parsed.strftime(LONG_DATE_FORMAT))
        except Exception:
            var.set(str(value))

    def _cargar_empleado_seleccionado(self):
        emp = self._selected_emp()
        if not emp:
            return
        self.empleado_id = emp.get("id")
        self.usuario = emp.get("usuario") or self.usuario
        self.var_salario.set(str(emp.get("salario") or "0"))
        self.var_vacaciones.set(str(emp.get("vacaciones") or "0"))
        self._set_date_var(self.var_fecha_ingreso, emp.get("fecha_ingreso"))

    # =========================================================
    # LÓGICA
    # =========================================================
    def _calcular(self):

        try:
            fecha_salida = parse_hhrr_date(self.var_fecha_salida.get())
            fecha_ingreso = parse_hhrr_date(self.var_fecha_ingreso.get())
            if not fecha_salida:
                raise ValueError("Fecha de salida invalida")
            if not fecha_ingreso:
                raise ValueError("Fecha de ingreso invalida")
            salario = float(self.var_salario.get())
            vacaciones = float(self.var_vacaciones.get())
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Datos inválidos para el cálculo:\n{e}"
            )
            return

        con_responsabilidad = self.var_tipo.get().startswith("CON")
        con_orden = self.var_orden.get().startswith("CON")

        self.calculo = CalculadoraLiquidacionCR.calcular(
            salario_mensual=salario,
            fecha_ingreso=fecha_ingreso,
            fecha_salida=fecha_salida,
            vacaciones_pendientes=vacaciones,
            con_responsabilidad=con_responsabilidad,
            con_orden_patronal=con_orden
        )

        self._mostrar_resultado()

    def _mostrar_resultado(self):

        self.txt_resultado.config(state="normal")
        self.txt_resultado.delete("1.0", "end")

        for k, v in self.calculo.items():
            self.txt_resultado.insert("end", f"{k}: {v}\n")

        self.txt_resultado.config(state="disabled")

    def _registrar(self):

        if not self.calculo:
            messagebox.showerror(
                "Error",
                "Debe calcular la liquidación antes de registrar."
            )
            return

        try:
            crear_evento_hr({
                "empleado_id": self.empleado_id,
                "event_type": "LIQUIDATION",
                "event_date": to_db_date(date.today()),
                "status": "CLOSED",
                "payload": self.calculo
            })
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo registrar la liquidación:\n{e}"
            )
            return

        messagebox.showinfo(
            "Liquidación registrada",
            "La liquidación fue registrada correctamente."
        )

        self.destroy()
