import tkinter as tk
from tkinter import ttk, messagebox

from Modulos.HHRR.ui_lazy_table import TablaLazy
from Modulos.HHRR.popups.popup_aprobacion import PopupAprobacion
from Modulos.HHRR.widgets.badge import Badge

from api_client import listar_eventos_hr


class VistaAdminHHRR(ttk.Frame):
    """
    Vista HHRR para ADMIN / GERENCIA / MASTER.
    Pool de aprobaciones.
    TODO es LAZY.
    """

    def __init__(self, parent, rol_usuario, usuario_actual):
        super().__init__(parent)

        self.rol_usuario = rol_usuario
        self.usuario_actual = usuario_actual

        self._construir_ui()

    # =========================================================
    # UI
    # =========================================================
    def _construir_ui(self):

        ttk.Label(
            self,
            text="Pool de Aprobaciones HHRR",
            font=("Segoe UI", 12, "bold")
        ).pack(pady=10)

        columnas = [
            "id",
            "empleado_id",
            "event_type",
            "event_date",
            "status"
        ]

        self.tabla_pool = TablaLazy(
            self,
            columnas=columnas,
            ancho_columnas={
                "id": 80,
                "empleado_id": 120,
                "event_type": 200,
                "event_date": 120,
                "status": 120
            },
            alto=18
        )
        self.tabla_pool.pack(fill="both", expand=True, padx=10, pady=10)

        # -------------------------------
        # Botones
        # -------------------------------
        self.cont_btn = ttk.Frame(self)
        self.cont_btn.pack(fill="x", pady=5)

        ttk.Button(
            self.cont_btn,
            text="Cargar solicitudes pendientes",
            command=self._cargar_pendientes
        ).pack(side="left", padx=5)

        ttk.Button(
            self.cont_btn,
            text="Actualizar alertas",
            command=self.actualizar_alertas
        ).pack(side="left", padx=5)

        ttk.Button(
            self.cont_btn,
            text="Abrir solicitud",
            command=self._abrir_solicitud
        ).pack(side="right", padx=5)

        # -------------------------------
        # Badge
        # -------------------------------
        self.badge_pool = Badge(self, bg="#f57c00")
        self.badge_pool.pack(anchor="ne", padx=10, pady=5)

    # =========================================================
    # LOGICA
    # =========================================================
    def _cargar_pendientes(self):
        try:
            datos = listar_eventos_hr(status="PENDING")
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudieron cargar las solicitudes:\n{e}"
            )
            return

        self.tabla_pool.cargar_datos(datos)
        self._actualizar_badge(datos)

    def _abrir_solicitud(self):
        seleccionado = self.tabla_pool.obtener_seleccionado()

        if not seleccionado:
            messagebox.showwarning(
                "Selección requerida",
                "Debe seleccionar una solicitud."
            )
            return

        PopupAprobacion(
            parent=self,
            evento=seleccionado,
            usuario_actual=self.usuario_actual,
            on_success=self._cargar_pendientes
        )

    def actualizar_alertas(self):
        """
        Actualiza badge SIN precargar tabla.
        """
        try:
            datos = listar_eventos_hr(status="PENDING")
        except Exception:
            self.badge_pool.set_valor(0)
            return

        self._actualizar_badge(datos)

    def _actualizar_badge(self, datos):
        total = len(datos) if datos else 0
        self.badge_pool.set_valor(total)
