# ============================================================
# ERP-SOM (Versión Base Nueva)
# Ventana Principal + Menú Lateral + Router de Módulos
# ============================================================

import tkinter as tk
from tkinter import messagebox
import sys
import os
import ctypes


from splash_screen import SplashScreen
from backend_api.rbac_service import has_permission

# ============================================================
# VERSION DEL ERP
# ============================================================
APP_NAME = "ERP-SOM"
APP_VERSION = "1.0.0"

# ============================================================
# Colores Corporativos
# ============================================================
COLOR_MENU = "#003A75"
COLOR_BG = "white"

# ============================================================
# IMPORTS OPCIONALES (NO BLOQUEAN ARRANQUE)
# ============================================================
try:
    from version_utils import compare_versions
    from api_client_version import get_version_info
    VERSION_CHECK_AVAILABLE = True
except ModuleNotFoundError:
    VERSION_CHECK_AVAILABLE = False
    print("⚠ version_utils no disponible — chequeo de versión desactivado")

# ============================================================
# Windows App ID (Taskbar / Alt+Tab)
# ============================================================
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
    "MSLTECH.ERPSOM.Desktop"
)

# ============================================================
# Helper para rutas (PyInstaller compatible)
# ============================================================
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


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

        # Usuario activo
        tk.Label(
            self.menu_frame,
            text=f"{self.usuario}\n({self.rol})",
            bg=COLOR_MENU,
            fg="white",
            font=("Segoe UI", 9),
            justify="center"
        ).pack(pady=(5, 15))

        # Cargar Dashboard por defecto
        self.cambiar_modulo("Dashboard")

        # Chequeo de versión (solo si existe)
        if VERSION_CHECK_AVAILABLE:
            self.parent.after(500, self.check_version)

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

        # ----------------------------------------------------
        # DEFINICIÓN DE MÓDULOS Y PERMISOS
        # ----------------------------------------------------
        modules_config = [
            ("Dashboard", "dashboard"),
            ("Master Data", "master_data"),
            ("Servicios", "servicios"),
            ("Finanzas", "finanzas"),
        ]

        for label, module_code in modules_config:
            if has_permission(self.rol, module_code, "view"):
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
    # Router de módulos (PROTEGIDO POR RBAC)
    # --------------------------------------------------------
    def cambiar_modulo(self, modulo):

        module_map = {
            "Dashboard": "dashboard",
            "Master Data": "master_data",
            "Servicios": "servicios",
            "Finanzas": "finanzas"
        }

        module_code = module_map.get(modulo)

        if module_code and not has_permission(self.rol, module_code, "view"):
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
            DashboardUI(
                self.content,
                go_back_callback=self.mostrar_menu
            ).pack(fill="both", expand=True)

        elif modulo == "Master Data":
            from Modulos.MasterData.ui_masterdata import MasterDataUI
            MasterDataUI(
                self.content,
                go_back_callback=self.mostrar_menu
            ).pack(fill="both", expand=True)

        elif modulo == "Servicios":
            from Modulos.Servicios.ui_servicios import ServiciosUI
            ServiciosUI(self.content).pack(fill="both", expand=True)

        elif modulo == "Finanzas":
            from Modulos.Finanzas.ui_finanzas import FinanzasUI
            FinanzasUI(
                self.content,
                on_back=self.mostrar_menu
            ).pack(fill="both", expand=True)

    # --------------------------------------------------------
    # Mostrar / Ocultar menú
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

    # --------------------------------------------------------
    # Cerrar ERP
    # --------------------------------------------------------
    def on_close(self):
        if messagebox.askyesno(
            "Confirmar salida",
            "¿Seguro que deseas salir del sistema?",
            parent=self.parent
        ):
            self.parent.destroy()
            sys.exit(0)

    # --------------------------------------------------------
    # Volver al Dashboard
    # --------------------------------------------------------
    def mostrar_menu(self):
        self.cambiar_modulo("Dashboard")

    # --------------------------------------------------------
    # Chequeo de versión (opcional)
    # --------------------------------------------------------
    def check_version(self):
        ok, data = get_version_info()
        if not ok:
            return

        latest = data.get("latest_version")
        force = data.get("force_update", False)
        message = data.get("message", "")

        if compare_versions(APP_VERSION, latest) >= 0:
            return

        if force:
            messagebox.showwarning(
                "Actualización obligatoria",
                message or "Debe actualizar el sistema para continuar."
            )
            self.on_close()
        else:
            from update_window import UpdateWindow
            UpdateWindow(
                self.parent,
                current_version=APP_VERSION,
                latest_version=latest,
                message=message,
                download_url=data.get("download_url")
            )


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
