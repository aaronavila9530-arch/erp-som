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
from Modulos.HHRR.views.view_salary_calculator import VistaCalculadoraSalarial
from Modulos.HHRR.views.view_medical_network import VistaRedMedicaHHRR

# ➕ VISTA SOLICITUDES
from Modulos.HHRR.views.vista_solicitudes import VistaSolicitudesHHRR

# ➕ VISTA EMPLEADOS (NUEVA)
from Modulos.HHRR.views.vista_empleados import VistaEmpleadosHHRR


class HHRRUI(ttk.Frame):

    def __init__(self, parent, usuario, rol, empleado_id=None, on_back=None):
        super().__init__(parent)

        self.parent = parent
        self.usuario = usuario
        self.rol = (rol or "").lower()
        self.empleado_id = empleado_id  # ⚠️ ya NO es crítico
        self.on_back = on_back
        self._permission_cache = {}

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

        callbacks = self._available_callbacks()

        HHRRHomeUI(
            parent=self.contenedor,
            usuario=self.usuario,
            rol=self.rol,
            callbacks=callbacks
        ).pack(fill="both", expand=True)

    def _db_hr_permission_decision(self, action: str):
        key = ((self.usuario or "").lower(), action)
        if key in self._permission_cache:
            return self._permission_cache[key]
        try:
            from backend_api.database import connect
            conn = connect()
            cur = conn.cursor()
            cur.execute(
                """
                SELECT COUNT(*)
                FROM user_module_permissions
                WHERE lower(usuario)=lower(%s)
                  AND allowed=TRUE
                """,
                (self.usuario,),
            )
            has_rows = (cur.fetchone() or [0])[0] > 0
            if not has_rows:
                decision = None
            else:
                cur.execute(
                    """
                    SELECT 1
                    FROM user_module_permissions
                    WHERE lower(usuario)=lower(%s)
                      AND module_code='hhrre'
                      AND lower(action_code) IN (lower(%s), 'admin')
                      AND allowed=TRUE
                    LIMIT 1
                    """,
                    (self.usuario, action),
                )
                decision = cur.fetchone() is not None
            cur.close()
            conn.close()
        except Exception:
            decision = None
        self._permission_cache[key] = decision
        return decision

    def _has_hr_permission(self, action: str) -> bool:
        if self.rol in ("admin", "master") or (self.usuario or "").lower() in {"admin", "aaron01", "gerencia1"}:
            return True
        db_decision = self._db_hr_permission_decision(action)
        if db_decision is not None:
            return db_decision
        if action in {"payslips_view", "payslips_download", "requests_view", "requests_create", "hours_view", "hours_register", "medical_network", "policies_view"}:
            return self.rol in {"user", "hr", "finance", "accounting"}
        if action in {"payroll_view", "payroll_generate", "employees_view", "employees_edit", "requests_approve", "hours_approve", "policies_edit", "news_publish", "salary_calculator"}:
            return self.rol in {"admin", "master", "hr"}
        return False

    def _available_callbacks(self):
        specs = {
            "payroll": ("payroll_view", self._abrir_payroll),
            "paylips": ("payslips_view", self._abrir_paylips),
            "solicitudes": ("requests_view", self._abrir_solicitudes),
            "horas": ("hours_view", self._abrir_horas),
            "empleados": ("employees_view", self._abrir_empleados),
            "calculadora_salarial": ("salary_calculator", self._abrir_calculadora_salarial),
            "red_medica": ("medical_network", self._abrir_red_medica),
            "politicas": ("policies_view", self._abrir_politicas),
            "publicar_noticia": ("news_publish", self._publicar_noticia),
        }
        return {key: callback for key, (action, callback) in specs.items() if callback and self._has_hr_permission(action)}

    def _publicar_noticia(self):
        from api_client import hr_publicar_noticias
        from Modulos.HHRR.popups.popup_noticias import PopupNoticias

        def _save(payload):
            hr_publicar_noticias(
                noticia_1=payload.get("noticia_1"),
                noticia_2=payload.get("noticia_2"),
                noticia_3=payload.get("noticia_3"),
                noticia_4=payload.get("noticia_4"),
                noticia_5=payload.get("noticia_5"),
            )
            self._mostrar_home()

        PopupNoticias(parent=self, on_save=_save)

    # =========================================================
    # PAYROLL (ADMIN / MASTER)
    # =========================================================
    def _abrir_payroll(self):

        if not self._has_hr_permission("payroll_view"):
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
    # SOLICITUDES
    # =========================================================
    def _abrir_solicitudes(self):

        self._limpiar_contenedor()
        self._mostrar_boton_volver()

        VistaSolicitudesHHRR(
            parent=self.contenedor,      # 🔥 FIX (no self)
            usuario=self.usuario,        # 🔥 FIX CLAVE
            rol_usuario=self.rol,
            on_back=self._mostrar_home   # 🔥 FIX (tu método correcto)
        ).pack(fill="both", expand=True)

    # =========================================================
    # EMPLEADOS (ADMIN / MASTER)
    # =========================================================
    def _abrir_empleados(self):

        if not self._has_hr_permission("employees_view"):
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
    # PAYSLIPS (FIX REAL)
    # =========================================================
    def _abrir_paylips(self):

        if not self._has_hr_permission("payslips_view"):
            messagebox.showwarning(
                "Acceso denegado",
                "No tienes permisos para acceder a Colillas."
            )
            return

        # 🔥 FIX CRÍTICO: eliminar dependencia de empleado_id
        self._limpiar_contenedor()
        self._mostrar_boton_volver()

        VistaColillasEmployee(
            parent=self.contenedor,
            empleado_id=self.usuario   # 👉 usamos usuario directamente
        ).pack(fill="both", expand=True)

    # =========================================================
    # POLÍTICAS
    # =========================================================
    def _abrir_calculadora_salarial(self):

        self._limpiar_contenedor()
        self._mostrar_boton_volver()

        VistaCalculadoraSalarial(
            parent=self.contenedor,
            usuario=self.usuario,
            rol=self.rol
        ).pack(fill="both", expand=True)

    def _abrir_politicas(self):

        self._limpiar_contenedor()
        self._mostrar_boton_volver()

        VistaPoliticasHHRR(
            parent=self.contenedor
        ).pack(fill="both", expand=True)

    def _abrir_red_medica(self):

        self._limpiar_contenedor()
        self._mostrar_boton_volver()

        VistaRedMedicaHHRR(
            parent=self.contenedor,
            usuario=self.usuario,
            rol=self.rol
        ).pack(fill="both", expand=True)
