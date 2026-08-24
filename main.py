# ============================================================
# ERP-SOM (Versión Base Nueva)
# Ventana Principal + Menú Lateral + Router de Módulos
# ============================================================

import os
import sys
import ctypes
import tkinter as tk
from tkinter import messagebox
from datetime import datetime, timedelta

from window_placement import install_same_monitor_policy

# Every popup and native dialog follows the monitor where ERP-SOM is active.
install_same_monitor_policy()

from resource_utils import resource_path
from splash_screen import SplashScreen
import api_client

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(BASE_DIR, "backend_api")

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# ============================================================
# Asegurar raíz del proyecto en sys.path
# ============================================================
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# ============================================================
# VERSION DEL ERP
# ============================================================
APP_NAME = "ERP-SOM"
from version import APP_VERSION

# ============================================================
# Colores Corporativos
# ============================================================
COLOR_MENU = "#003A75"
COLOR_BG = "white"


# ============================================================
# Windows App ID (Taskbar / Alt+Tab)
# ============================================================
if os.name == "nt":
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
        "MSLTECH.ERPSOM.Desktop"
    )

# ============================================================
# Clase Ventana Principal ERP-SOM
# ============================================================
class MainApp(tk.Frame):

    def __init__(self, parent, usuario, rol):
        super().__init__(parent, bg=COLOR_BG)

        self.parent = parent
        self.usuario = usuario
        self.rol = rol

        self.pack(fill="both", expand=True)

        parent.title(f"{APP_NAME} v{APP_VERSION} — MSL Tech")
        parent.geometry("1200x700")
        parent.minsize(1000, 600)
        parent.protocol("WM_DELETE_WINDOW", self.on_close)

        self.menu_visible = True
        self._logra_alert_shown = set()
        self._global_alert_shown = {}
        self._permission_cache = {}

        self._build_menu_lateral()
        self._build_content_area()

        tk.Label(
            self.menu_frame,
            text=f"{self.usuario}\n({self.rol})",
            bg=COLOR_MENU,
            fg="white",
            font=("Segoe UI", 9),
            justify="center"
        ).pack(pady=(5, 15))

        self.cambiar_modulo(self._initial_module())
        self._start_logra_global_alerts()
        self._start_global_business_alerts()
        self._start_outlook_fiscal_background_sync()

    def _initial_module(self) -> str:
        """Open the first module the current role can actually access."""
        rol = (self.rol or "").strip().lower()
        if rol == "accounting":
            return "Finanzas"
        if self._has_permission("dashboard", "view"):
            return "Dashboard"
        for label, module_code in [
            ("Finanzas", "finanzas"),
            ("Informes", "informes"),
            ("Servicios", "servicios"),
            ("Comercial", "comercial"),
            ("HHRR", "hhrre"),
            ("Master Data", "master_data"),
            ("Q&A SOM", "qa_som"),
        ]:
            if self._has_permission(module_code, "view"):
                return label
        return "Q&A SOM"

    def _start_outlook_fiscal_background_sync(self):
        try:
            from Modulos.Finanzas.sections.Accounting.outlook_fiscal_importer import start_background_sync
            start_background_sync()
        except Exception as exc:
            print(f"Outlook fiscal automatico no iniciado: {exc}")

    # --------------------------------------------------------
    # Menú lateral (RBAC)
    # --------------------------------------------------------
    def _build_menu_lateral(self):
        self.menu_frame = tk.Frame(self, bg=COLOR_MENU, width=220)
        self.menu_frame.pack(side="left", fill="y")

        tk.Button(
            self.menu_frame,
            text="☰",
            bg=COLOR_MENU,
            fg="white",
            relief="flat",
            font=("Segoe UI", 14),
            command=self.toggle_menu
        ).pack(pady=10)

        modules_config = [
            ("Dashboard", "dashboard"),
            ("Master Data", "master_data"),
            ("Servicios", "servicios"),
            ("Finanzas", "finanzas"),
            ("HHRR", "hhrre"),
            ("Comercial", "comercial"),
            ("Informes", "informes"),
            ("PORTIA", "portia"),
            ("Q&A SOM", "qa_som"),
            ("Admin", "admin_users"),
        ]

        for label, module_code in modules_config:
            if self._has_permission(module_code, "view"):
                tk.Button(
                    self.menu_frame,
                    text=label,
                    bg=COLOR_MENU,
                    fg="white",
                    activebackground="#0052A2",
                    relief="flat",
                    font=("Segoe UI", 11),
                    command=lambda m=label: self.cambiar_modulo(m)
                ).pack(fill="x", pady=2, padx=5)

        tk.Label(
            self.menu_frame,
            text=f"Versión {APP_VERSION}",
            bg=COLOR_MENU,
            fg="white",
            font=("Segoe UI", 8)
        ).pack(side="bottom", pady=10)

    # --------------------------------------------------------
    # Área de contenido
    # --------------------------------------------------------
    def _build_content_area(self):
        self.content = tk.Frame(self, bg=COLOR_BG)
        self.content.pack(side="right", fill="both", expand=True)

    # --------------------------------------------------------
    # Router de módulos
    # --------------------------------------------------------
    def cambiar_modulo(self, modulo):

        module_map = {
            "Dashboard": "dashboard",
            "Master Data": "master_data",
            "Servicios": "servicios",
            "Finanzas": "finanzas",
            "HHRR": "hhrre",
            "Comercial": "comercial",
            "Informes": "informes",
            "PORTIA": "portia",
            "Q&A SOM": "qa_som",
            "Admin": "admin_users",
        }

        module_code = module_map.get(modulo)

        if module_code and not self._has_permission(module_code, "view"):
            messagebox.showerror(
                "Acceso denegado",
                "No tienes permisos para acceder a este módulo.",
                parent=self.parent
            )
            return

        for w in self.content.winfo_children():
            w.destroy()

        if modulo == "Dashboard":

            from Modulos.Dashboards.dashboards_home_ui import DashboardsHomeUI

            DashboardsHomeUI(
                parent=self.content
            ).pack(
                fill="both",
                expand=True
            )

        elif modulo == "Master Data":
            from Modulos.MasterData.ui_masterdata import MasterDataUI
            MasterDataUI(self.content, go_back_callback=self.mostrar_menu)\
                .pack(fill="both", expand=True)

        elif modulo == "Servicios":
            from Modulos.Servicios.ui_servicios import ServiciosUI
            ServiciosUI(self.content).pack(fill="both", expand=True)

        elif modulo == "Finanzas":
            from Modulos.Finanzas.ui_finanzas import FinanzasUI
            FinanzasUI(self.content, on_back=self.mostrar_menu)\
                .pack(fill="both", expand=True)

        elif modulo == "HHRR":
            from Modulos.HHRR.ui_hhrre import HHRRUI
            HHRRUI(
                parent=self.content,
                usuario=self.usuario,
                rol=self.rol,
                empleado_id=None,
                on_back=self.mostrar_menu
            ).pack(fill="both", expand=True)

        elif modulo == "Informes":
            from Modulos.Informes.informes_home_ui import InformesHomeUI
            InformesHomeUI(
                parent=self.content,
                usuario=self.usuario,
                rol=self.rol,
                logra_only=not self._has_permission("informes", "view", include_logra_override=False),
                callbacks={
                    "open_report_selector": self._open_report_selector,
                    "open_logra": self._open_logra_questionnaires,
                    "fetch_reports": self._fetch_reports,
                    "preview_report": self._preview_report,
                    "edit_report": self._edit_report,
                    "submit_report": self._submit_report,
                    "generate_report_doc": self._generate_report_doc,
                }
            ).pack(fill="both", expand=True)

        elif modulo == "Comercial":
            from Modulos.Comercial.comercial_home_ui import ComercialHomeUI
            ComercialHomeUI(
                parent=self.content,
                usuario=self.usuario,
                rol=self.rol
            ).pack(fill="both", expand=True)

        elif modulo == "PORTIA":
            from Modulos.Portia.portia_ui import PortiaUI
            PortiaUI(
                parent=self.content,
                usuario=self.usuario,
                rol=self.rol,
                on_back=self.mostrar_menu
            ).pack(fill="both", expand=True)

        elif modulo == "Q&A SOM":
            from Modulos.Portia.qa_ui import QASomUI
            QASomUI(
                parent=self.content,
                usuario=self.usuario,
                rol=self.rol,
                on_back=self.mostrar_menu
            ).pack(fill="both", expand=True)

        elif modulo == "Admin":
            from Modulos.Admin.user_admin_ui import UserAdminUI
            UserAdminUI(
                parent=self.content,
                usuario=self.usuario,
                rol=self.rol,
                on_back=self.mostrar_menu
            ).pack(fill="both", expand=True)

    # --------------------------------------------------------
    # Utilidades generales
    # --------------------------------------------------------
    def toggle_menu(self):
        if self.menu_visible:
            self.menu_frame.pack_forget()
            self.menu_visible = False
            self.btn_show = tk.Button(
                self,
                text="☰",
                bg=COLOR_MENU,
                fg="white",
                relief="flat",
                font=("Segoe UI", 16),
                command=self.toggle_menu
            )
            self.btn_show.place(x=10, y=10)
        else:
            self.menu_frame.pack(side="left", fill="y")
            self.menu_visible = True
            if hasattr(self, "btn_show"):
                self.btn_show.destroy()

    def on_close(self):
        if messagebox.askyesno(
            "Confirmar salida",
            "¿Seguro que deseas salir del sistema?",
            parent=self.parent
        ):
            self.parent.destroy()
            sys.exit(0)

    def mostrar_menu(self):
        self.cambiar_modulo("Dashboard")

    # =========================================================
    # ONG global agenda alerts
    # =========================================================
    def _start_logra_global_alerts(self):
        self.after(15000, self._check_logra_global_alerts)

    def _parse_logra_agenda_datetime(self, item, time_key):
        date_value = item.get("date_iso") or item.get("date") or ""
        time_value = item.get(time_key) or ""
        for date_format in ("%Y-%m-%d", "%B %d, %Y"):
            try:
                parsed_date = datetime.strptime(date_value, date_format).date()
                parsed_time = datetime.strptime(time_value, "%H:%M").time()
                return datetime.combine(parsed_date, parsed_time)
            except Exception:
                continue
        return None

    def _should_show_logra_alert(self, key):
        if key in self._logra_alert_shown:
            return False
        self._logra_alert_shown.add(key)
        return True

    def _should_show_global_alert(self, key, cooldown_hours=24):
        now = datetime.now()
        previous = self._global_alert_shown.get(key)
        if previous and now - previous < timedelta(hours=cooldown_hours):
            return False
        self._global_alert_shown[key] = now
        return True

    def _check_logra_global_alerts(self):
        try:
            resp = api_client.list_logra_reports_api()
            rows = resp.get("data") or []
            now = datetime.now()
            for report in rows:
                report_title = report.get("title") or f"ONG #{report.get('id')}"
                for idx, item in enumerate(report.get("agenda_items") or []):
                    if not isinstance(item, dict):
                        continue
                    status = str(item.get("status") or "").strip().lower()
                    if "complet" in status:
                        continue

                    start = self._parse_logra_agenda_datetime(item, "start_time")
                    end = self._parse_logra_agenda_datetime(item, "end_time")
                    if not start:
                        continue
                    try:
                        reminder = int(item.get("reminder_minutes") or 0)
                    except Exception:
                        reminder = 0

                    label = item.get("topic") or item.get("person") or "Reunion ONG"
                    base_key = (
                        report.get("id"),
                        idx,
                        item.get("date_iso") or item.get("date"),
                        item.get("start_time"),
                    )

                    if reminder > 0 and start - timedelta(minutes=reminder) <= now < start:
                        key = base_key + ("before",)
                        if self._should_show_logra_alert(key):
                            messagebox.showinfo(
                                "Agenda ONG",
                                f"{report_title}\n\n'{label}' inicia en menos de {reminder} minutos.",
                                parent=self.parent
                            )

                    if start <= now and (not end or now <= end):
                        key = base_key + ("current",)
                        if self._should_show_logra_alert(key):
                            messagebox.showinfo(
                                "Agenda ONG",
                                f"{report_title}\n\n'{label}' esta en curso.",
                                parent=self.parent
                            )
        except Exception:
            pass
        finally:
            if self.winfo_exists():
                self.after(60000, self._check_logra_global_alerts)

    # =========================================================
    # Global ERP alerts: tax declarations, birthdays, reports
    # =========================================================
    def _start_global_business_alerts(self):
        self.after(20000, self._check_global_business_alerts)

    def _check_global_business_alerts(self):
        try:
            self._check_tax_declaration_alerts()
            self._check_employee_birthday_alerts()
            self._check_pending_report_alerts()
        except Exception:
            pass
        finally:
            if self.winfo_exists():
                self.after(60 * 60 * 1000, self._check_global_business_alerts)

    def _check_tax_declaration_alerts(self):
        period = datetime.now().strftime("%Y-%m")
        try:
            data = api_client.get_tax_obligations_api(datetime.now().year, period=period, pending_only=True)
        except Exception:
            return

        alerts = []
        for item in (data.get("data") or []):
            for due in (item.get("calendar") or []):
                status = str(due.get("alert_status") or "").upper()
                if status not in {"DUE_TODAY", "DUE_TOMORROW"}:
                    continue
                due_date = due.get("estimated_due_date") or "sin fecha"
                obligation = item.get("name") or item.get("tax_code") or "Declaracion"
                due_period = due.get("period") or ""
                key = ("tax", item.get("tax_code"), due_period, due_date)
                if self._should_show_global_alert(key, cooldown_hours=12):
                    alerts.append(f"{obligation} {due_period}: vence {due_date}")

        if alerts:
            messagebox.showwarning(
                "Declaraciones pendientes",
                "Hay declaraciones pendientes por presentar:\n\n" + "\n".join(alerts[:8]),
                parent=self.parent,
            )

    def _parse_date_only(self, value):
        text = str(value or "").strip()
        for fmt in ("%Y-%m-%d", "%B %d, %Y", "%d/%m/%Y", "%m/%d/%Y"):
            try:
                return datetime.strptime(text[:10] if fmt == "%Y-%m-%d" else text, fmt).date()
            except Exception:
                continue
        return None

    def _check_employee_birthday_alerts(self):
        current_role = str(getattr(self, "rol", "") or "").strip().lower()
        if current_role not in {"master", "admin"}:
            return

        try:
            resp = api_client.hr_listar_empleados(page=1, page_size=500, estado="ACTIVO")
        except Exception:
            return

        today = datetime.now().date()
        alerts = []
        for emp in (resp.get("data") or []):
            birth = self._parse_date_only(emp.get("fecha_nacimiento"))
            if not birth:
                continue
            this_year = birth.replace(year=today.year)
            days = (this_year - today).days
            if days < 0:
                days = ((birth.replace(year=today.year + 1)) - today).days
            if days not in {0, 3}:
                continue
            name = emp.get("nombre_completo") or emp.get("nombre") or emp.get("usuario") or "Empleado"
            key = ("birthday", emp.get("id") or emp.get("usuario") or name, days, today.isoformat())
            if self._should_show_global_alert(key, cooldown_hours=24):
                when = "hoy" if days == 0 else "en 3 dias"
                alerts.append(f"{name}: cumpleanos {when}")

        if alerts:
            messagebox.showinfo(
                "Cumpleanos de empleados",
                "Recordatorio de cumpleanos:\n\n" + "\n".join(alerts[:8]),
                parent=self.parent,
            )

    def _check_pending_report_alerts(self):
        total = 0
        try:
            resp = api_client.get_status_informes_api(status="Pending")
            total += int(resp.get("count") or len(resp.get("data") or []))
        except Exception:
            pass
        try:
            resp = api_client.list_logra_reports_api()
            for row in resp.get("data") or []:
                status = str(row.get("status") or "").strip().lower()
                if status == "pending":
                    total += 1
        except Exception:
            pass

        if total and self._should_show_global_alert(("reports_pending",), cooldown_hours=24):
            messagebox.showwarning(
                "Informes pendientes",
                f"Hay {total} informe(s) en estado Pending. Se avisara cada 24 horas hasta aprobarlos o rechazarlos.",
                parent=self.parent,
            )

    # =========================================================
    # INFORMES — callbacks
    # =========================================================
    def _open_report_selector(self):
        from Modulos.Informes.report_type_selector import ReportTypeSelector
        for w in self.content.winfo_children():
            w.destroy()
        ReportTypeSelector(
            parent=self.content,
            on_container_report=self._open_container_report_form,
            on_back=lambda: self.cambiar_modulo("Informes"),
            usuario=self.usuario,
            rol=self.rol
        ).pack(fill="both", expand=True)

    def _open_logra_questionnaires(self):
        from Modulos.Informes.logra_questionnaires_form import LograQuestionnairesForm
        for w in self.content.winfo_children():
            w.destroy()
        LograQuestionnairesForm(
            parent=self.content,
            usuario=self.usuario,
            rol=self.rol,
            on_back=lambda: self.cambiar_modulo("Informes")
        ).pack(fill="both", expand=True)

    def _open_container_report_form(self):
        from Modulos.Informes.container_report_form import ContainerReportForm
        for w in self.content.winfo_children():
            w.destroy()
        ContainerReportForm(
            parent=self.content,
            usuario=self.usuario,
            rol=self.rol,
            on_back=lambda: self._open_report_selector()
        ).pack(fill="both", expand=True)

    def _fetch_reports(self):
        return []

    def _preview_report(self, report_id):
        pass

    def _edit_report(self, report_id):
        pass

    def _submit_report(self, report_id):
        pass

    def _generate_report_doc(self, report_id):
        pass



    # --------------------------------------------------------
    # RBAC LOCAL (VISUAL UI)
    # --------------------------------------------------------
    def _db_permission_decision(self, usuario: str, module_code: str, action: str):
        key = (usuario, module_code, action)
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
                (usuario,),
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
                      AND lower(module_code)=lower(%s)
                      AND lower(action_code) IN (lower(%s), 'admin')
                      AND allowed=TRUE
                    LIMIT 1
                    """,
                    (usuario, module_code, action),
                )
                decision = cur.fetchone() is not None
            cur.close()
            conn.close()
        except Exception:
            decision = None
        self._permission_cache[key] = decision
        return decision

    def _has_permission(self, module_code: str, action: str, include_logra_override: bool = True) -> bool:

        usuario = (self.usuario or "").lower()
        rol = (self.rol or "").lower()
        module_code = (module_code or "").lower()
        action = (action or "").lower()

        if rol in ("master", "admin") or usuario in ("gerencia1", "captain", "aaron01", "admin"):
            return True

        db_decision = self._db_permission_decision(usuario, module_code, action)
        if db_decision is not None:
            return db_decision

        # Perfil contable restringido: únicamente Finanzas y Q&A SOM.
        # Se evalúa antes de las excepciones globales (por ejemplo, ONG en
        # Informes) para impedir que aparezcan módulos adicionales.
        if rol == "accounting":
            return action == "view" and module_code in {"finanzas", "qa_som"}

        # ONG queda disponible para todo usuario. Visualmente se expone por
        # Informes, pero usuarios sin permiso general solo ven ONG.
        if include_logra_override and module_code == "informes" and action == "view":
            return True

        # Q&A SOM es la base de conocimiento/manual y queda disponible para todos.
        if module_code == "qa_som" and action == "view":
            return True

        # ====================================================
        # ADMINISTRADORES → ACCESO TOTAL
        # ====================================================

        # ====================================================
        # SURVEYORS
        # SOLO PUEDEN VER:
        # Comercial / HHRR / Informes
        # ====================================================

        if usuario in ("surveyor01", "surveyor02", "surveyor03"):

            allowed_modules = {
                "comercial",
                "hhrre",
                "informes",
                "qa_som",
            }

            if module_code in allowed_modules and action == "view":
                return True

            return False

        # ====================================================
        # CONTADOR
        # SOLO PUEDE VER:
        # Finanzas / HHRR
        # ====================================================

        if usuario == "contador01":

            allowed_modules = {
                "finanzas",
                "hhrre",
                "qa_som",
            }

            if module_code in allowed_modules and action == "view":
                return True

            return False

        # ====================================================
        # FALLBACK POR ROL
        # ====================================================

        role_permissions = {
            "user": {
                "dashboard": ["view"],
                "servicios": ["view"],
                "informes": ["view"],
                "qa_som": ["view"],
            },
            "finance": {
                "dashboard": ["view"],
                "finanzas": ["view"],
                "qa_som": ["view"],
            },
            "hr": {
                "dashboard": ["view"],
                "hhrre": ["view"],
                "qa_som": ["view"],
            }
        }

        allowed = role_permissions.get(rol, {})
        actions = allowed.get(module_code, [])

        return action in actions


# ============================================================
# BOOTSTRAP
# ============================================================
if __name__ == "__main__":
    root = tk.Tk()
    root.iconbitmap(resource_path("assets/logo_menu_tareas.ico"))
    root.withdraw()

    def iniciar_login():
        from login_window import LoginWindow
        LoginWindow(root)

    SplashScreen(root, iniciar_login)
    root.mainloop()
