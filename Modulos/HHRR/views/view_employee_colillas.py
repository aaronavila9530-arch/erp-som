import os
import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser

from Modulos.HHRR.ui_lazy_table import TablaLazy
from api_client import listar_eventos_hr


class VistaColillasEmployee(ttk.Frame):
    """
    Vista de descarga de colillas de pago para EMPLOYEE.
    TODO es LAZY.
    """

    def __init__(self, parent, empleado_id):
        super().__init__(parent)

        self.empleado_id = empleado_id
        self._construir_ui()

    # =========================================================
    # UI
    # =========================================================
    def _construir_ui(self):

        columnas = [
            "periodo",
            "status"
        ]

        self.tabla = TablaLazy(
            self,
            columnas=columnas,
            ancho_columnas={
                "periodo": 150,
                "status": 120
            }
        )
        self.tabla.pack(fill="both", expand=True, padx=10, pady=10)

        cont_btn = ttk.Frame(self)
        cont_btn.pack(fill="x", pady=5)

        ttk.Button(
            cont_btn,
            text="Cargar colillas",
            command=self._cargar_colillas
        ).pack(side="left", padx=5)

        ttk.Button(
            cont_btn,
            text="Descargar colilla",
            command=self._descargar_colilla
        ).pack(side="right", padx=5)

    # =========================================================
    # LÓGICA
    # =========================================================
    def _cargar_colillas(self):
        try:
            datos = listar_eventos_hr(
                empleado_id=self.empleado_id,
                event_type="PAYSLIP"
            )
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudieron cargar las colillas:\n{e}"
            )
            return

        filas = []

        for d in datos or []:
            payload = d.get("payload") or {}

            filas.append({
                "periodo": payload.get("periodo", "—"),
                "status": d.get("status", "—"),
                "_pdf_path": payload.get("pdf_path")
            })

        self.tabla.cargar_datos(filas)

    def _descargar_colilla(self):

        seleccionado = self.tabla.obtener_seleccionado()

        if not seleccionado:
            messagebox.showwarning(
                "Selección requerida",
                "Debe seleccionar una colilla."
            )
            return

        path = seleccionado.get("_pdf_path")

        if not path:
            messagebox.showerror(
                "Archivo no disponible",
                "No se encontró el archivo de la colilla."
            )
            return

        try:
            webbrowser.open(
                f"file:///{os.path.abspath(path)}"
            )
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo abrir la colilla:\n{e}"
            )
