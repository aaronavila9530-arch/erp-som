# ============================================================
# ERP-SOM (Versión Base Nueva)
# Ventana Principal + Menú Lateral + Router de Módulos
# ============================================================

import os
import sys
import ctypes
import tkinter as tk
from tkinter import messagebox

from resource_utils import resource_path
from splash_screen import SplashScreen

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

        self.cambiar_modulo("Dashboard")

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
            from Modulos.Dashboard.ui_dashboard import DashboardUI
            DashboardUI(self.content, go_back_callback=self.mostrar_menu)\
                .pack(fill="both", expand=True)

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
                callbacks={
                    "open_report_selector": self._open_report_selector,
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
    # INFORMES — callbacks
    # =========================================================
    def _open_report_selector(self):
        from Modulos.Informes.report_type_selector import ReportTypeSelector
        for w in self.content.winfo_children():
            w.destroy()
        ReportTypeSelector(
            parent=self.content,
            on_container_report=self._open_container_report_form,
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
    # RBAC LOCAL (SOLO VISUAL — SEGURIDAD REAL EN BACKEND)
    # --------------------------------------------------------
    def _has_permission(self, module_code: str, action: str) -> bool:
        """
        Control visual de permisos basado en rol.
        La seguridad real se valida en backend.
        """

        # Master / Admin → acceso total
        if self.rol.lower() in ("master", "admin"):
            return True

        # Ejemplo básico de roles
        role_permissions = {
            "user": {
                "dashboard": ["view"],
                "servicios": ["view"],
                "informes": ["view"],
            },
            "finance": {
                "dashboard": ["view"],
                "finanzas": ["view"],
                "informes": ["view"],
            },
            "hr": {
                "dashboard": ["view"],
                "hhrre": ["view"],
            }
        }

        allowed = role_permissions.get(self.rol.lower(), {})
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
