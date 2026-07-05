import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import csv
from openpyxl import Workbook

from Modulos.HHRR.ui_lazy_table import TablaLazy
from Modulos.HHRR.popups.popup_aprobacion_solicitudes import PopupAprobacion
from Modulos.HHRR.popups.popup_solicitud import PopupSolicitud

from api_client import (
    listar_eventos_hr,
    aprobar_evento_hr,
    rechazar_evento_hr
)


class VistaSolicitudesHHRR(ttk.Frame):

    PAGE_SIZE = 50

    ESTADO_LABELS = {
        "PENDING": "● Pendiente",
        "APPROVED": "● Aprobado",
        "REJECTED": "● Rechazado",
    }

    ESTADO_UI_TO_BACK = {
        "● Pendiente": "PENDING",
        "● Aprobado": "APPROVED",
        "● Rechazado": "REJECTED",
    }

    def __init__(self, parent, usuario, rol_usuario: str, on_back=None, **kwargs):
        super().__init__(parent)

        self.usuario = (usuario or "").strip().lower()   # 🔥 FIX
        self.rol_usuario = (rol_usuario or "").lower().strip()
        self.read_only = self.usuario in ("surveyor01", "surveyor02")
        self.on_back = on_back

        self._raw_rows = []
        self._filtered_rows = []
        self._current_page = 0

        self._build_ui()
        self._load_data()

    # =========================================================
    # UI
    # =========================================================
    def _build_ui(self):

        header = ttk.Frame(self)
        header.pack(fill="x", padx=10, pady=8)

        ttk.Label(
            header,
            text="Solicitudes HHRR",
            font=("Segoe UI", 13, "bold")
        ).pack(side="left")

        if callable(self.on_back):
            ttk.Button(
                header,
                text="← Volver",
                command=self.on_back
            ).pack(side="right")

        filtros = ttk.Frame(self)
        filtros.pack(fill="x", padx=10, pady=5)

        ttk.Label(filtros, text="Empleado").grid(row=0, column=0, padx=5, sticky="w")
        self.cmb_empleado = ttk.Combobox(filtros, state="readonly", width=25)
        self.cmb_empleado.grid(row=0, column=1, padx=5)

        ttk.Label(filtros, text="Estado").grid(row=0, column=2, padx=5, sticky="w")
        self.cmb_status = ttk.Combobox(filtros, state="readonly", width=15)
        self.cmb_status.grid(row=0, column=3, padx=5)

        ttk.Label(filtros, text="Tipo").grid(row=0, column=4, padx=5, sticky="w")
        self.cmb_tipo = ttk.Combobox(filtros, state="readonly", width=20)
        self.cmb_tipo.grid(row=0, column=5, padx=5)

        ttk.Button(
            filtros,
            text="Filtrar",
            command=self._aplicar_filtros
        ).grid(row=0, column=6, padx=6)

        ttk.Button(
            filtros,
            text="Limpiar",
            command=self._limpiar_filtros
        ).grid(row=0, column=7, padx=4)

        if not self.read_only:
            ttk.Button(
                filtros,
                text="+ Nueva Solicitud",
                command=self._abrir_popup_solicitud
            ).grid(row=0, column=8, padx=6)

        if self.rol_usuario in ("admin", "master"):
            ttk.Button(
                filtros,
                text="Aprobaciones",
                command=self._info_aprobaciones
            ).grid(row=0, column=9, padx=4)

        self.btn_exportar = ttk.Button(
            filtros,
            text="Exportar",
            command=self._exportar_menu
        )
        self.btn_exportar.grid(row=0, column=10, padx=6)

        # ================= TABLA =================
        self.columnas = [
            "id", "empleado", "event_type", "event_date",
            "period_year", "period_month", "dias",
            "status",
            "razon_solicitud", "created_by", "approved_by",
            "created_at", "approved_at"
        ]

        cont = ttk.Frame(self)
        cont.pack(fill="both", expand=True, padx=10, pady=5)

        table_frame = ttk.Frame(cont)
        table_frame.pack(fill="both", expand=True)

        self.tabla = TablaLazy(
            parent=table_frame,
            columnas=self.columnas,
            alto=15
        )
        self.tabla.pack(fill="both", expand=True)

        for col in self.columnas:
            try:
                self.tabla.tree.column(col, width=140, stretch=False)
            except Exception:
                pass

        scroll_y = ttk.Scrollbar(
            cont,
            orient="vertical",
            command=self.tabla.tree.yview
        )
        scroll_y.pack(side="right", fill="y")

        scroll_x = ttk.Scrollbar(
            cont,
            orient="horizontal",
            command=self.tabla.tree.xview
        )
        scroll_x.pack(side="bottom", fill="x")

        self.tabla.tree.configure(
            yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set
        )

        self.tabla.tree.bind("<Button-3>", self._menu_contextual)

        # ================= PAGINACIÓN =================
        pag = ttk.Frame(self)
        pag.pack(fill="x", padx=10, pady=6)

        ttk.Button(
            pag,
            text="◀ Anterior",
            command=self._pagina_anterior
        ).pack(side="left")

        ttk.Button(
            pag,
            text="Siguiente ▶",
            command=self._pagina_siguiente
        ).pack(side="right")

        self.lbl_paginacion = ttk.Label(pag, text="Página 1 de 1")
        self.lbl_paginacion.pack(side="right", padx=10)

    # =========================================================
    # DATA
    # =========================================================
    def _load_data(self):
        try:
            data = listar_eventos_hr(self.usuario, self.rol_usuario) or []
            if not isinstance(data, list):
                data = []
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self._raw_rows = []
            self._filtered_rows = []
            self._current_page = 0
            self._render_page()
            return

        # 🔥 FILTRO CRÍTICO FRONT (SEGURIDAD EXTRA)
        if self.rol_usuario not in ("admin", "master"):
            data = [
                r for r in data
                if str(r.get("created_by") or "").strip().lower() == self.usuario
            ]

        self._raw_rows = data
        self._filtered_rows = list(data)
        self._current_page = 0

        self._cargar_filtros(data)
        self._render_page()

    def _render_page(self):
        start = self._current_page * self.PAGE_SIZE
        end = start + self.PAGE_SIZE
        rows = self._filtered_rows[start:end]
        self._render_rows(rows)

        total_rows = len(self._filtered_rows)
        total_pages = max(1, (total_rows + self.PAGE_SIZE - 1) // self.PAGE_SIZE)
        current_page_ui = min(self._current_page + 1, total_pages)
        self.lbl_paginacion.config(text=f"Página {current_page_ui} de {total_pages}")

    def _render_rows(self, rows):

        filas = []

        for r in rows:
            if not isinstance(r, dict):
                continue

            payload = r.get("payload") or {}
            if not isinstance(payload, dict):
                payload = {}

            d = str(r.get("event_date") or "")

            dias = payload.get("dias_solicitados")
            if dias in ("", None):
                dias = r.get("vacaciones") or ""

            estado_backend = str(r.get("status") or "").upper().strip()

            filas.append({
                "id": r.get("id"),
                "empleado": r.get("empleado") or "",
                "event_type": r.get("event_type") or "",
                "event_date": d,
                "period_year": d[:4] if len(d) >= 4 else "",
                "period_month": d[5:7] if len(d) >= 7 else "",
                "dias": dias,
                "status": self.ESTADO_LABELS.get(estado_backend, "● Desconocido"),
                "razon_solicitud": r.get("comentario_solicitud") or "",
                "created_by": r.get("created_by") or "",
                "approved_by": r.get("approved_by") or "",
                "created_at": r.get("created_at") or "",
                "approved_at": r.get("approved_at") or ""
            })

        self.tabla.cargar_datos(filas)

        tree = self.tabla.tree
        idx_status = self.columnas.index("status")

        tree.tag_configure("Pendiente", foreground="#D4A017")
        tree.tag_configure("Aprobado", foreground="#2E8B57")
        tree.tag_configure("Rechazado", foreground="#B22222")

        for item in tree.get_children():
            values = tree.item(item, "values")
            if not values or len(values) <= idx_status:
                continue

            estado = str(values[idx_status])

            if "Pendiente" in estado:
                tree.item(item, tags=("Pendiente",))
            elif "Aprobado" in estado:
                tree.item(item, tags=("Aprobado",))
            elif "Rechazado" in estado:
                tree.item(item, tags=("Rechazado",))

    # =========================================================
    # FILTROS
    # =========================================================
    def _cargar_filtros(self, rows):
        empleados = sorted({
            str(r.get("empleado")).strip()
            for r in rows
            if isinstance(r, dict) and r.get("empleado")
        })
        tipos = sorted({
            str(r.get("event_type")).strip()
            for r in rows
            if isinstance(r, dict) and r.get("event_type")
        })

        self.cmb_empleado["values"] = [""] + empleados
        self.cmb_status["values"] = [""] + list(self.ESTADO_LABELS.values())
        self.cmb_tipo["values"] = [""] + tipos

    def _aplicar_filtros(self):

        emp = self.cmb_empleado.get().strip()
        st_ui = self.cmb_status.get().strip()
        tp = self.cmb_tipo.get().strip()

        st_backend = self.ESTADO_UI_TO_BACK.get(st_ui)

        filtradas = []
        for r in self._raw_rows:
            if not isinstance(r, dict):
                continue

            if emp and (r.get("empleado") or "") != emp:
                continue

            if st_backend and str(r.get("status") or "").upper().strip() != st_backend:
                continue

            if tp and (r.get("event_type") or "") != tp:
                continue

            filtradas.append(r)

        self._filtered_rows = filtradas
        self._current_page = 0
        self._render_page()

    def _limpiar_filtros(self):
        self.cmb_empleado.set("")
        self.cmb_status.set("")
        self.cmb_tipo.set("")
        self._filtered_rows = list(self._raw_rows)
        self._current_page = 0
        self._render_page()

    # =========================================================
    # EXPORTAR
    # =========================================================
    def _exportar_menu(self):
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Exportar CSV", command=self._exportar_csv)
        menu.add_command(label="Exportar Excel", command=self._exportar_excel)

        try:
            x = self.btn_exportar.winfo_rootx()
            y = self.btn_exportar.winfo_rooty() + self.btn_exportar.winfo_height()
            menu.tk_popup(x, y)
        finally:
            try:
                menu.grab_release()
            except Exception:
                pass

    def _menu_contextual(self, event):
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Exportar CSV", command=self._exportar_csv)
        menu.add_command(label="Exportar Excel", command=self._exportar_excel)

        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            try:
                menu.grab_release()
            except Exception:
                pass

    def _exportar_csv(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")]
        )
        if not path:
            return

        try:
            filas_export = self._build_export_rows()

            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=self.columnas)
                writer.writeheader()
                for r in filas_export:
                    writer.writerow(r)

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo exportar CSV:\n{e}")
            return

        messagebox.showinfo("OK", "CSV exportado correctamente")

    def _exportar_excel(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")]
        )
        if not path:
            return

        try:
            filas_export = self._build_export_rows()

            wb = Workbook()
            ws = wb.active
            ws.title = "Solicitudes"

            ws.append(self.columnas)

            for r in filas_export:
                ws.append([r.get(c, "") for c in self.columnas])

            wb.save(path)

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo exportar Excel:\n{e}")
            return

        messagebox.showinfo("OK", "Excel exportado correctamente")

    def _build_export_rows(self):
        filas = []

        for r in self._filtered_rows:
            if not isinstance(r, dict):
                continue

            payload = r.get("payload") or {}
            if not isinstance(payload, dict):
                payload = {}

            d = str(r.get("event_date") or "")
            dias = payload.get("dias_solicitados")
            if dias in ("", None):
                dias = r.get("vacaciones") or ""

            estado_backend = str(r.get("status") or "").upper().strip()

            filas.append({
                "id": r.get("id"),
                "empleado": r.get("empleado") or "",
                "event_type": r.get("event_type") or "",
                "event_date": d,
                "period_year": d[:4] if len(d) >= 4 else "",
                "period_month": d[5:7] if len(d) >= 7 else "",
                "dias": dias,
                "status": self.ESTADO_LABELS.get(estado_backend, "● Desconocido"),
                "razon_solicitud": r.get("comentario_solicitud") or "",
                "created_by": r.get("created_by") or "",
                "approved_by": r.get("approved_by") or "",
                "created_at": r.get("created_at") or "",
                "approved_at": r.get("approved_at") or ""
            })

        return filas

    # =========================================================
    # PAGINACIÓN
    # =========================================================
    def _pagina_siguiente(self):
        if (self._current_page + 1) * self.PAGE_SIZE < len(self._filtered_rows):
            self._current_page += 1
            self._render_page()

    def _pagina_anterior(self):
        if self._current_page > 0:
            self._current_page -= 1
            self._render_page()

    # =========================================================
    # APROBACIONES
    # =========================================================
    def _info_aprobaciones(self):

        if self.rol_usuario not in ("admin", "master"):
            messagebox.showwarning("Permiso", "No autorizado")
            return

        row = self.tabla.obtener_seleccionado()

        if not row or not row.get("id"):
            messagebox.showwarning("Aprobaciones", "Seleccione una solicitud")
            return

        if "Pendiente" not in str(row.get("status")):
            messagebox.showwarning("Aprobaciones", "Solo solicitudes pendientes")
            return

        PopupAprobacion(
            self,
            row_id=row["id"],
            on_approve=self._aprobar,
            on_reject=self._rechazar
        )

    def _aprobar(self, event_id, comentario=None):
        if self.rol_usuario not in ("admin", "master"):
            messagebox.showwarning("Permiso", "No autorizado")
            return

        try:
            aprobar_evento_hr(event_id, comentario)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo aprobar:\n{e}")
            return

        self._load_data()

    def _rechazar(self, event_id, comentario):
        if self.rol_usuario not in ("admin", "master"):
            messagebox.showwarning("Permiso", "No autorizado")
            return

        try:
            rechazar_evento_hr(event_id, comentario)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo rechazar:\n{e}")
            return

        self._load_data()

    def _abrir_popup_solicitud(self):
        if self.read_only:
            messagebox.showwarning("Permiso", "Este usuario solo tiene permisos de consulta.")
            return

        try:
            PopupSolicitud(
                self,
                usuario=self.usuario,          # 🔥 FIX
                rol=self.rol_usuario,          # 🔥 FIX
                on_success=self._load_data
            )
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir la solicitud:\n{e}")

