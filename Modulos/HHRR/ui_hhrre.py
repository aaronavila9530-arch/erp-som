import tkinter as tk
from tkinter import ttk, messagebox

# ============================
# HOME
# ============================
from Modulos.HHRR.home_ui import HHRRHomeUI

# ============================
# VISTAS
# ============================
from Modulos.HHRR.views.view_admin import VistaAdminHHRR
from Modulos.HHRR.views.view_employee import VistaEmployee
from Modulos.HHRR.views.ui_payslips import VistaColillasEmployee
from Modulos.HHRR.views.view_payroll_admin import VistaPayrollAdmin
from Modulos.HHRR.views.view_registro_horas import VistaRegistroHoras
from Modulos.HHRR.views.view_registro_horas_admin import VistaRegistroHorasAdmin
from Modulos.HHRR.views.ui_policies import VistaPoliticasHHRR

# ➕ VISTA SOLICITUDES
from Modulos.HHRR.views.vista_solicitudes import VistaSolicitudesHHRR

# ➕ VISTA EMPLEADOS (NUEVA)
from Modulos.HHRR.views.vista_empleados import VistaEmpleadosHHRR


class HHRRUI(ttk.Frame):
    """
    Router visual del módulo HHRR.

    ✔ HOME sin botón volver
    ✔ Vistas internas con botón volver
    ✔ Routing estricto por rol
    ✔ NO lógica operativa aquí
    """

    def __init__(self, parent, usuario, rol, empleado_id=None, on_back=None):
        super().__init__(parent)

        self.parent = parent
        self.usuario = usuario
        self.rol = (rol or "").lower()
        self.empleado_id = empleado_id
        self.on_back = on_back

        self._build_base_ui()
        self._mostrar_home()

    # =========================================================
    # UI BASE
    # =========================================================
    def _build_base_ui(self):

        self.header = ttk.Frame(self)
        self.header.pack(fill="x", padx=10, pady=5)

        ttk.Label(
            self.header,
            text="Módulo HHRR",
            font=("Segoe UI", 13, "bold")
        ).pack(side="left")

        self.btn_volver = ttk.Button(
            self.header,
            text="← Volver",
            command=self._mostrar_home
        )
        self.btn_volver.pack(side="right")
        self.btn_volver.pack_forget()

        self.contenedor = ttk.Frame(self)
        self.contenedor.pack(fill="both", expand=True)

    # =========================================================
    # UTILIDADES
    # =========================================================
    def _limpiar_contenedor(self):
        for w in self.contenedor.winfo_children():
            w.destroy()

    def _mostrar_boton_volver(self):
        self.btn_volver.pack(side="right")

    def _ocultar_boton_volver(self):
        self.btn_volver.pack_forget()

    # =========================================================
    # HOME
    # =========================================================
    def _mostrar_home(self):

        self._limpiar_contenedor()
        self._ocultar_boton_volver()

        callbacks = {
            "payroll": self._abrir_payroll,
            "paylips": self._abrir_paylips,
            "solicitudes": self._abrir_solicitudes,
            "horas": self._abrir_horas,
            "empleados": self._abrir_empleados,  # ➕ BOTÓN EMPLEADOS
            "politicas": self._abrir_politicas,
        }

        HHRRHomeUI(
            parent=self.contenedor,
            usuario=self.usuario,
            rol=self.rol,
            callbacks=callbacks
        ).pack(fill="both", expand=True)

    # =========================================================
    # PAYROLL (ADMIN / MASTER)
    # =========================================================
    def _abrir_payroll(self):

        if self.rol not in ("admin", "master"):
            messagebox.showwarning(
                "Acceso denegado",
                "No tienes permisos para acceder a Payroll."
            )
            return

        self._limpiar_contenedor()
        self._mostrar_boton_volver()

        VistaPayrollAdmin(
            parent=self.contenedor,
            usuario=self.usuario,
            rol=self.rol
        ).pack(fill="both", expand=True)

    # =========================================================
    # SOLICITUDES (USER / ADMIN / MASTER)
    # =========================================================
    def _abrir_solicitudes(self):

        self._limpiar_contenedor()
        self._mostrar_boton_volver()

        VistaSolicitudesHHRR(
            parent=self.contenedor,
            rol_usuario=self.rol,
            on_back=self._mostrar_home
        ).pack(fill="both", expand=True)

    # =========================================================
    # EMPLEADOS (ADMIN / MASTER)
    # =========================================================
    def _abrir_empleados(self):

        if self.rol not in ("admin", "master"):
            messagebox.showwarning(
                "Acceso denegado",
                "No tienes permisos para acceder a Empleados."
            )
            return

        self._limpiar_contenedor()
        self._mostrar_boton_volver()

        VistaEmpleadosHHRR(
            parent=self.contenedor,
            rol_usuario=self.rol
        ).pack(fill="both", expand=True)

    # =========================================================
    # HORAS
    # =========================================================
    def _abrir_horas(self):

        self._limpiar_contenedor()
        self._mostrar_boton_volver()

        if self.rol in ("admin", "master"):
            VistaRegistroHorasAdmin(
                self.contenedor,
                usuario=self.usuario,
                rol=self.rol,
                on_back=self._mostrar_home
            ).pack(fill="both", expand=True)
        else:
            VistaRegistroHoras(
                self.contenedor,
                usuario=self.usuario,
                rol=self.rol,
                on_back=self._mostrar_home
            ).pack(fill="both", expand=True)

    # =========================================================
    # PAYSLIPS (EMPLOYEE / ADMIN / MASTER)
    # =========================================================
    def _abrir_paylips(self):

        if self.rol not in ("user", "admin", "master"):
            messagebox.showwarning(
                "Acceso denegado",
                "No tienes permisos para acceder a Colillas de Pago."
            )
            return

        if self.rol == "user" and not self.empleado_id:
            messagebox.showerror(
                "Error",
                "Empleado no asociado."
            )
            return

        self._limpiar_contenedor()
        self._mostrar_boton_volver()

        VistaColillasEmployee(
            parent=self.contenedor,
            empleado_id=self.empleado_id
        ).pack(fill="both", expand=True)


    # =========================================================
    # POLÍTICAS (USER / ADMIN / MASTER)
    # =========================================================
    def _abrir_politicas(self):

        self._limpiar_contenedor()
        self._mostrar_boton_volver()

        VistaPoliticasHHRR(
            parent=self.contenedor
        ).pack(fill="both", expand=True)
