import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import csv

from api_client import (
    hr_list_ot_logs,
    hr_delete_ot_log,
    hr_update_ot_status
)

from Modulos.HHRR.ui_lazy_table import TablaLazy
from Modulos.HHRR.popups.popup_ot_detalle_admin import PopupDetalleOTAdmin
from Modulos.HHRR.popups.popup_registro_horas import PopupRegistroHoras


class VistaRegistroHorasAdmin(ttk.Frame):
    """
    Vista ADMIN — Registro de Horas
    Ver, aprobar y rechazar horas de TODOS los empleados
    """

    PAGE_SIZE = 50

    def __init__(self, parent, usuario, rol, on_back):
        super().__init__(parent)

        self.usuario = usuario
        self.rol = rol
        self.on_back = on_back

        self.page = 1
        self.total = 0

        self._build_ui()
        self._load_summary()
        self._load_data()
        self._load_usuarios()

    # =========================================================
    # UI
    # =========================================================
    def _build_ui(self):

        # -------------------------------
        # HEADER
        # -------------------------------
        header = ttk.Frame(self)
        header.pack(fill="x", pady=5)

        ttk.Button(
            header,
            text="← Volver",
            command=self.on_back
        ).pack(side="left")

        ttk.Label(
            header,
            text="Registro de Horas — Administración",
            font=("Segoe UI", 14, "bold")
        ).pack(side="left", padx=10)

        # -------------------------------
        # RESUMEN
        # -------------------------------
        self.lbl_summary = ttk.Label(
            self,
            text="Cargando resumen...",
            font=("Segoe UI", 10)
        )
        self.lbl_summary.pack(anchor="w", padx=10, pady=5)

        # -------------------------------
        # FILTROS
        # -------------------------------
        filtros = ttk.Frame(self)
        filtros.pack(fill="x", padx=10, pady=5)

        ttk.Label(filtros, text="Usuario:").pack(side="left")
        self.cmb_usuario = ttk.Combobox(
            filtros,
            width=20,
            state="readonly"
        )
        self.cmb_usuario.pack(side="left", padx=5)

        ttk.Label(filtros, text="Tipo:").pack(side="left")

        self.cmb_tipo = ttk.Combobox(
            filtros,
            values=["", "OPERACION", "INFORME"],
            width=15,
            state="readonly"
        )
        self.cmb_tipo.pack(side="left", padx=5)

        # ------------------------------------------------
        # NUEVO FILTRO ESTADO
        # ------------------------------------------------
        ttk.Label(filtros, text="Estado:").pack(side="left", padx=(10, 0))

        self.cmb_estado = ttk.Combobox(
            filtros,
            values=["", "Pendiente", "Aprobado", "Rechazado"],
            width=15,
            state="readonly"
        )
        self.cmb_estado.pack(side="left", padx=5)

        ttk.Button(
            filtros,
            text="Filtrar",
            command=self._reload
        ).pack(side="left", padx=10)

        ttk.Button(
            filtros,
            text="Exportar CSV",
            command=self._export_csv
        ).pack(side="right")

        # -------------------------------
        # TABLA
        # -------------------------------
        columnas = [
            "id",
            "estado_ui",
            "usuario",
            "tipo",
            "fecha_inicio",
            "fecha_fin",
            "duracion_horas",
            "buque",
            "comentario"
        ]

        self.tabla = TablaLazy(
            self,
            columnas=columnas,
            alto=18
        )
        self.tabla.pack(fill="both", expand=True, padx=10, pady=5)

        self.tabla.bind("<<TreeviewSelect>>", self._on_select)

        # -------------------------------
        # ACCIONES
        # -------------------------------
        acciones = ttk.Frame(self)
        acciones.pack(fill="x", padx=10, pady=5)

        ttk.Button(
            acciones,
            text="Registrar horas",
            command=self._abrir_popup_registro
        ).pack(side="left")

        ttk.Button(
            acciones,
            text="Ver / Aprobar / Rechazar",
            command=self._abrir_detalle
        ).pack(side="left", padx=5)

        ttk.Button(
            acciones,
            text="Eliminar",
            command=self._eliminar
        ).pack(side="left", padx=5)

        self.lbl_paginacion = ttk.Label(acciones, text="")
        self.lbl_paginacion.pack(side="right")

        ttk.Button(
            acciones,
            text="◀",
            command=self._prev_page
        ).pack(side="right")

        ttk.Button(
            acciones,
            text="▶",
            command=self._next_page
        ).pack(side="right")

    # =========================================================
    # DATA
    # =========================================================
    def _load_summary(self):
        try:
            resp = hr_list_ot_logs(
                page=1,
                page_size=1
            )

            total = resp.get("total", 0)

        except Exception as e:
            self.lbl_summary.config(
                text=f"Error cargando resumen: {str(e)}"
            )
            return

        self.lbl_summary.config(
            text=(
                f"Total de registros en sistema: {total} | "
                f"Rol: {self.rol.upper()}"
            )
        )

    def _load_usuarios(self):
        try:
            resp = hr_list_ot_logs(
                page=1,
                page_size=500
            )

            usuarios = sorted({
                r.get("usuario")
                for r in resp.get("data", [])
                if r.get("usuario")
            })

            self.cmb_usuario["values"] = [""] + usuarios
            self.cmb_usuario.current(0)

        except Exception:
            self.cmb_usuario["values"] = [""]


    # =========================================================
    # DATA
    # =========================================================
    def _load_data(self):
        try:
            # ----------------------------------------------
            # CONVERTIR ESTADO UI A ESTADO REAL BACKEND
            # ----------------------------------------------
            estado_map = {
                "Pendiente": "PENDIENTE",
                "Aprobado": "APROBADO",
                "Rechazado": "RECHAZADO",
                "● Pendiente": "PENDIENTE",
                "● Aprobado": "APROBADO",
                "● Rechazado": "RECHAZADO",
                "🟡": "PENDIENTE",
                "🟢": "APROBADO",
                "🔴": "RECHAZADO",
                "": None,
                None: None
            }

            estado_backend = estado_map.get(
                (self.cmb_estado.get() or "").strip(),
                None
            )

            resp = hr_list_ot_logs(
                page=self.page,
                page_size=self.PAGE_SIZE,
                usuario=(self.cmb_usuario.get() or None),
                tipo=(self.cmb_tipo.get() or None),
                estado=estado_backend
            )

        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        self.total = resp.get("total", 0)

        data = []
        for row in (resp.get("data") or []):

            estado_real = str(
                row.get("estado") or "PENDIENTE"
            ).upper().strip()

            row["estado_real"] = estado_real

            # ICONO UI SEGÚN ESTADO
            if estado_real == "APROBADO":
                row["estado_ui"] = "🟢"
            elif estado_real == "RECHAZADO":
                row["estado_ui"] = "🔴"
            else:
                row["estado_ui"] = "🟡"

            data.append(row)

        self.tabla.cargar_datos(data)

        total_pages = max(
            1,
            (self.total + self.PAGE_SIZE - 1) // self.PAGE_SIZE
        )
        self.lbl_paginacion.config(
            text=f"Página {self.page} de {total_pages}"
        )


    def _reload(self):
        self.page = 1
        self._load_data()

    # =========================================================
    # EVENTOS
    # =========================================================
    def _on_select(self, event=None):
        row = self.tabla.obtener_seleccionado()
        if not row:
            return

        self.lbl_summary.config(
            text=f"Usuario: {row['usuario']} | Tipo: {row['tipo']} | "
                 f"Horas: {row['duracion_horas']} | Estado: {row['estado_real']}"
        )

    def _abrir_popup_registro(self):
        PopupRegistroHoras(
            parent=self,
            on_success=self._reload
        )

    def _abrir_detalle(self):
        row = self.tabla.obtener_seleccionado()
        if not row:
            messagebox.showwarning("Selección", "Seleccione un registro.")
            return

        PopupDetalleOTAdmin(
            parent=self,
            data=row,
            on_success=self._reload
        )

    def _eliminar(self):
        row = self.tabla.obtener_seleccionado()
        if not row:
            return

        if not messagebox.askyesno(
            "Confirmar",
            "Eliminar este registro es irreversible. ¿Continuar?"
        ):
            return

        try:
            hr_delete_ot_log(row["id"])
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        self._reload()

    # =========================================================
    # PAGINACIÓN
    # =========================================================
    def _prev_page(self):
        if self.page > 1:
            self.page -= 1
            self._load_data()

    def _next_page(self):
        if self.page * self.PAGE_SIZE < self.total:
            self.page += 1
            self._load_data()

    # =========================================================
    # EXPORTAR
    # =========================================================
    def _export_csv(self):
        rows = self.tabla.get_all_rows()
        if not rows:
            messagebox.showwarning("Exportar", "No hay datos para exportar.")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")]
        )
        if not path:
            return

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

        messagebox.showinfo("Exportar", "Archivo CSV generado correctamente.")
