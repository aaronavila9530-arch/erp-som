import tkinter as tk
from tkinter import ttk, messagebox

from Modulos.HHRR.ui_lazy_table import TablaLazy
from Modulos.HHRR.popups.popup_ot_log import PopupRegistroHoras
from Modulos.HHRR.widgets.badge import Badge

from api_client import (
    listar_ot_logs,
    listar_eventos_hr
)


class VistaEmployee(ttk.Frame):
    """
    Vista HHRR para EMPLOYEE.
    CERO precarga.
    Todo se carga SOLO bajo acción explícita del usuario.
    """

    def __init__(self, parent, usuario, empleado_id):
        super().__init__(parent)

        self.usuario = usuario
        self.empleado_id = empleado_id

        self._construir_ui()

    # =========================================================
    # UI GENERAL
    # =========================================================
    def _construir_ui(self):

        header = ttk.Frame(self)
        header.pack(fill="x", padx=10, pady=5)

        ttk.Label(
            header,
            text="Mi panel HHRR",
            font=("Segoe UI", 12, "bold")
        ).pack(side="left")

        self.badge_solicitudes = Badge(header, bg="#f57c00")
        self.badge_solicitudes.pack(side="right", padx=5)

        self.badge_colillas = Badge(header, bg="#2e7d32")
        self.badge_colillas.pack(side="right", padx=5)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)

        self._tab_mis_horas()
        self._tab_registrar_horas()
        self._tab_solicitudes()
        self._tab_vacaciones()
        self._tab_colillas()
        self._tab_documentos()
        self._tab_codigo_trabajo()

    # =========================================================
    # TAB 1 - MIS HORAS
    # =========================================================
    def _tab_mis_horas(self):

        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Mis horas trabajadas")

        columnas = [
            "fecha_inicio",
            "fecha_fin",
            "duracion_horas",
            "tipo",
            "buque"
        ]

        self.tabla_horas = TablaLazy(
            tab,
            columnas=columnas,
            ancho_columnas={
                "fecha_inicio": 150,
                "fecha_fin": 150,
                "duracion_horas": 120,
                "tipo": 120,
                "buque": 200
            }
        )
        self.tabla_horas.pack(fill="both", expand=True, padx=10, pady=10)

        ttk.Button(
            tab,
            text="Cargar mis horas",
            command=self._cargar_mis_horas
        ).pack(pady=5)

    def _cargar_mis_horas(self):
        try:
            datos = listar_ot_logs(usuario=self.usuario)
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudieron cargar las horas:\n{e}"
            )
            return

        self.tabla_horas.cargar_datos(datos or [])

    # =========================================================
    # TAB 2 - REGISTRAR HORAS
    # =========================================================
    def _tab_registrar_horas(self):

        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Registrar horas")

        ttk.Label(
            tab,
            text="Registro manual de horas trabajadas",
            font=("Segoe UI", 11, "bold")
        ).pack(pady=20)

        ttk.Button(
            tab,
            text="Registrar nuevas horas",
            command=self._abrir_popup_registro
        ).pack()

    def _abrir_popup_registro(self):
        PopupRegistroHoras(
            self,
            usuario=self.usuario,
            on_success=self._cargar_mis_horas
        )

    # =========================================================
    # TAB 3 - SOLICITUDES
    # =========================================================
    def _tab_solicitudes(self):

        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Mis solicitudes")

        columnas = [
            "event_type",
            "event_date",
            "status"
        ]

        self.tabla_solicitudes = TablaLazy(
            tab,
            columnas=columnas,
            ancho_columnas={
                "event_type": 200,
                "event_date": 120,
                "status": 120
            }
        )
        self.tabla_solicitudes.pack(fill="both", expand=True, padx=10, pady=10)

        ttk.Button(
            tab,
            text="Cargar mis solicitudes",
            command=self._cargar_solicitudes
        ).pack(pady=5)

    def _cargar_solicitudes(self):
        try:
            datos = listar_eventos_hr(empleado_id=self.empleado_id)
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudieron cargar las solicitudes:\n{e}"
            )
            return

        datos = datos or []
        self.tabla_solicitudes.cargar_datos(datos)
        self.badge_solicitudes.set_valor(len(datos))

    # =========================================================
    # TAB 4 - VACACIONES / INCAPACIDADES
    # =========================================================
    def _tab_vacaciones(self):

        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Vacaciones / Incapacidades")

        ttk.Label(
            tab,
            text="Solicitudes de vacaciones e incapacidades",
            font=("Segoe UI", 11, "bold")
        ).pack(pady=20)

        ttk.Button(
            tab,
            text="Solicitar vacaciones",
            command=lambda: messagebox.showinfo(
                "Pendiente",
                "Popup de vacaciones se implementa en el siguiente paso."
            )
        ).pack(pady=5)

        ttk.Button(
            tab,
            text="Registrar incapacidad",
            command=lambda: messagebox.showinfo(
                "Pendiente",
                "Popup de incapacidad se implementa en el siguiente paso."
            )
        ).pack(pady=5)

    # =========================================================
    # TAB 5 - COLILLAS
    # =========================================================
    def _tab_colillas(self):

        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Colillas de pago")

        columnas = ["periodo", "status"]

        self.tabla_colillas = TablaLazy(
            tab,
            columnas=columnas,
            ancho_columnas={
                "periodo": 150,
                "status": 120
            }
        )
        self.tabla_colillas.pack(fill="both", expand=True, padx=10, pady=10)

        cont_btn = ttk.Frame(tab)
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
                "status": d.get("status"),
                "_pdf_path": payload.get("pdf_path")
            })

        self.tabla_colillas.cargar_datos(filas)
        self.badge_colillas.set_valor(len(filas))

    def _descargar_colilla(self):
        seleccionado = self.tabla_colillas.obtener_seleccionado()

        if not seleccionado:
            messagebox.showwarning(
                "Selección requerida",
                "Seleccione una colilla."
            )
            return

        pdf_path = seleccionado.get("_pdf_path")
        if not pdf_path:
            messagebox.showerror(
                "Archivo no disponible",
                "No hay PDF asociado."
            )
            return

        try:
            import os, webbrowser
            webbrowser.open(f"file:///{os.path.abspath(pdf_path)}")
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo abrir el PDF:\n{e}"
            )

    # =========================================================
    # TAB 6 - DOCUMENTOS
    # =========================================================
    def _tab_documentos(self):

        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Documentos y políticas")

        ttk.Label(
            tab,
            text="Documentos internos y políticas de la empresa",
            font=("Segoe UI", 11, "bold")
        ).pack(pady=20)

        ttk.Button(
            tab,
            text="Políticas internas",
            command=lambda: messagebox.showinfo(
                "Documento",
                "Políticas internas."
            )
        ).pack(pady=5)

        ttk.Button(
            tab,
            text="Reglamento interno",
            command=lambda: messagebox.showinfo(
                "Documento",
                "Reglamento interno."
            )
        ).pack(pady=5)

    # =========================================================
    # TAB 7 - CÓDIGO DE TRABAJO
    # =========================================================
    def _tab_codigo_trabajo(self):

        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Código de Trabajo")

        ttk.Label(
            tab,
            text="Código de Trabajo de Costa Rica",
            font=("Segoe UI", 11, "bold")
        ).pack(pady=20)

        ttk.Button(
            tab,
            text="Abrir Código de Trabajo",
            command=lambda: messagebox.showinfo(
                "Código de Trabajo",
                "Aquí se abrirá el Código de Trabajo."
            )
        ).pack()
