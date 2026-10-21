import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date

from api_client import hr_list_payroll_employees
from Modulos.HHRR.popups.popup_colilla_pago import PopupColillaPago
from Modulos.HHRR.ui_lazy_table import TablaLazy


class VistaPayrollAdmin(ttk.Frame):
    """
    Vista PAYROLL — Solo ADMIN / MASTER
    Tabla base = empleados activos
    Generación de planilla = Popup
    """

    def __init__(self, parent, usuario, rol):
        super().__init__(parent)

        self.usuario = usuario
        self.rol = rol
        self.data = []

        self._build_ui()
        self._load_empleados()

    # =========================================================
    # UI
    # =========================================================
    def _build_ui(self):

        # -----------------------------------------------------
        # HEADER
        # -----------------------------------------------------
        header = ttk.Frame(self)
        header.pack(fill="x", pady=10)

        ttk.Label(
            header,
            text="Payroll / Planilla",
            font=("Segoe UI", 14, "bold")
        ).pack(side="left", padx=10)

        # -----------------------------------------------------
        # FILTROS DE PERIODO (REFERENCIA VISUAL)
        # -----------------------------------------------------
        filtros = ttk.Frame(self)
        filtros.pack(fill="x", padx=10, pady=5)

        ttk.Label(filtros, text="Año:").pack(side="left")

        self.cmb_year = ttk.Combobox(
            filtros,
            values=[str(y) for y in range(2024, 2031)],
            width=6,
            state="readonly"
        )
        self.cmb_year.set(str(date.today().year))
        self.cmb_year.pack(side="left", padx=5)

        ttk.Label(filtros, text="Mes:").pack(side="left")

        self.cmb_month = ttk.Combobox(
            filtros,
            values=[f"{m:02d}" for m in range(1, 13)],
            width=4,
            state="readonly"
        )
        self.cmb_month.set(f"{date.today().month:02d}")
        self.cmb_month.pack(side="left", padx=5)

        ttk.Label(
            filtros,
            text="(Solo se permite generar el mes en curso)",
            foreground="gray"
        ).pack(side="left", padx=15)

        # -----------------------------------------------------
        # TABLA EMPLEADOS
        # -----------------------------------------------------
        columnas = [
            "usuario",
            "nombre",
            "apellidos",
            "jornada",
            "salario",
            "pago",
            "estado"
        ]

        self.tabla = TablaLazy(
            self,
            columnas=columnas,
            alto=16
        )
        self.tabla.pack(fill="both", expand=True, padx=10, pady=10)

        # -----------------------------------------------------
        # ACCIONES
        # -----------------------------------------------------
        acciones = ttk.Frame(self)
        acciones.pack(fill="x", padx=10, pady=5)

        ttk.Button(
            acciones,
            text="Generar Planilla",
            command=self._generar_planilla
        ).pack(side="left")

    # =========================================================
    # DATA
    # =========================================================
    def _load_empleados(self):
        """
        Carga empleados ACTIVOS para payroll
        """
        try:
            resp = hr_list_payroll_employees()
            self.data = resp.get("data", [])
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        self.tabla.cargar_datos(self.data)

    # =========================================================
    # ACCIÓN PRINCIPAL
    # =========================================================
    def _generar_planilla(self):
        """
        Abre el popup de generación / preview de planilla
        """
        row = self.tabla.obtener_seleccionado()
        if not row:
            messagebox.showwarning(
                "Selección requerida",
                "Seleccione un empleado."
            )
            return

        PopupColillaPago(
            parent=self,
            empleado_row=row
        )
