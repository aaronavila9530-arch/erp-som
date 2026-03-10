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

    # =========================================================
    # MAPA VISUAL DE ESTADOS (SOLO PRESENTACIÓN)
    # =========================================================
    ESTADO_LABELS = {
        "PENDING": "● Pendiente",
        "APPROVED": "● Aprobado",
        "REJECTED": "● Rechazado",
    }


    def __init__(self, parent, rol_usuario: str, on_back=None, **kwargs):
        super().__init__(parent)

        self.rol_usuario = (rol_usuario or "").lower()
        self.on_back = on_back

        self._raw_rows = []
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

        # ---------------- FILTROS + BOTONES ----------------
        filtros = ttk.Frame(self)
        filtros.pack(fill="x", padx=10, pady=5)

        ttk.Label(filtros, text="Empleado").grid(row=0, column=0, padx=5)
        self.cmb_empleado = ttk.Combobox(filtros, state="readonly", width=25)
        self.cmb_empleado.grid(row=0, column=1, padx=5)

        ttk.Label(filtros, text="Estado").grid(row=0, column=2, padx=5)
        self.cmb_status = ttk.Combobox(filtros, state="readonly", width=15)
        self.cmb_status.grid(row=0, column=3, padx=5)

        ttk.Label(filtros, text="Tipo").grid(row=0, column=4, padx=5)
        self.cmb_tipo = ttk.Combobox(filtros, state="readonly", width=20)
        self.cmb_tipo.grid(row=0, column=5, padx=5)

        ttk.Button(filtros, text="Filtrar", command=self._aplicar_filtros)\
            .grid(row=0, column=6, padx=6)

        ttk.Button(filtros, text="Limpiar", command=self._limpiar_filtros)\
            .grid(row=0, column=7, padx=4)

        ttk.Button(filtros, text="+ Nueva Solicitud", command=self._abrir_popup_solicitud)\
            .grid(row=0, column=8, padx=6)

        if self.rol_usuario in ("admin", "master"):
            ttk.Button(filtros, text="Aprobaciones", command=self._info_aprobaciones)\
                .grid(row=0, column=9, padx=4)

        self.btn_exportar = ttk.Button(
            filtros,
            text="Exportar",
            command=self._exportar_menu
        )
        self.btn_exportar.grid(row=0, column=10, padx=6)

        # ---------------- TABLA ----------------
        columnas = [
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

        self.tabla = TablaLazy(parent=table_frame, columnas=columnas, alto=15)
        self.tabla.pack(fill="both", expand=True)

        # 🔒 FORZAR OVERFLOW HORIZONTAL
        for col in columnas:
            self.tabla.tree.column(col, width=140, stretch=False)

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

        self.tabla.tree.bind("<<TreeviewSelect>>", self._on_row_selected)
        self.tabla.tree.bind("<Button-3>", self._menu_contextual)

        # ---------------- PAGINACIÓN ----------------
        pag = ttk.Frame(self)
        pag.pack(fill="x", padx=10, pady=6)

        ttk.Button(pag, text="◀ Anterior", command=self._pagina_anterior)\
            .pack(side="left")

        ttk.Button(pag, text="Siguiente ▶", command=self._pagina_siguiente)\
            .pack(side="right")

    # =========================================================
    # DATA
    # =========================================================
    def _load_data(self):
        self._raw_rows = listar_eventos_hr() or []
        self._current_page = 0
        self._cargar_filtros(self._raw_rows)
        self._render_page()

    def _render_page(self):
        s = self._current_page * self.PAGE_SIZE
        e = s + self.PAGE_SIZE
        self._render_rows(self._raw_rows[s:e])

    def _render_rows(self, rows):
        filas = []

        for r in rows:
            d = r.get("event_date") or ""

            payload = r.get("payload") or {}
            dias = ""

            # =====================================================
            # EXTRAER DIAS DE VACACIONES
            # =====================================================
            if r.get("event_type") == "VACACIONES":

                # prioridad payload
                dias = payload.get("dias_solicitados")

                # fallback columna calculada
                if not dias:
                    dias = r.get("vacaciones")

            filas.append({
                "id": r.get("id"),
                "empleado": r.get("empleado"),
                "event_type": r.get("event_type"),
                "event_date": d,
                "period_year": d[:4] if len(d) >= 4 else "",
                "period_month": d[5:7] if len(d) >= 7 else "",
                "dias": dias or "",
                "status": self.ESTADO_LABELS.get(
                    r.get("status"),
                    "● Desconocido"
                ),
                "razon_solicitud": r.get("comentario_solicitud"),
                "created_by": r.get("created_by"),
                "approved_by": r.get("approved_by"),
                "created_at": r.get("created_at"),
                "approved_at": r.get("approved_at")
            })

        self.tabla.cargar_datos(filas)

        # =====================================================
        # COLORES VISUALES POR ESTADO (Treeview tags)
        # =====================================================
        tree = self.tabla.tree

        tree.tag_configure(
            "Pendiente",
            foreground="#D4A017"  # amarillo
        )
        tree.tag_configure(
            "Aprobado",
            foreground="#2E8B57"  # verde
        )
        tree.tag_configure(
            "Rechazado",
            foreground="#B22222"  # rojo
        )

        for item in tree.get_children():
            values = tree.item(item, "values")
            estado_ui = values[6]  # columna 'status'

            if "Pendiente" in estado_ui:
                tree.item(item, tags=("Pendiente",))
            elif "Aprobado" in estado_ui:
                tree.item(item, tags=("Aprobado",))
            elif "Rechazado" in estado_ui:
                tree.item(item, tags=("Rechazado",))


    # =========================================================
    # EXPORTAR
    # =========================================================
    def _exportar_menu(self):
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Exportar a CSV", command=self._exportar_csv)
        menu.add_command(label="Exportar a Excel", command=self._exportar_excel)

        x = self.btn_exportar.winfo_rootx()
        y = self.btn_exportar.winfo_rooty() + self.btn_exportar.winfo_height()

        menu.tk_popup(x, y)

    def _exportar_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv")
        if not path:
            return

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.tabla.columnas)
            writer.writeheader()
            for r in self._raw_rows:
                writer.writerow(r)

        messagebox.showinfo("Exportar", "Archivo CSV exportado correctamente")

    def _exportar_excel(self):
        path = filedialog.asksaveasfilename(defaultextension=".xlsx")
        if not path:
            return

        wb = Workbook()
        ws = wb.active
        ws.append(self.tabla.columnas)

        for r in self._raw_rows:
            ws.append([r.get(col) for col in self.tabla.columnas])

        wb.save(path)
        messagebox.showinfo("Exportar", "Archivo Excel exportado correctamente")

    def _menu_contextual(self, event):
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Exportar a CSV", command=self._exportar_csv)
        menu.add_command(label="Exportar a Excel", command=self._exportar_excel)
        menu.tk_popup(event.x_root, event.y_root)

    # =========================================================
    # PAGINACIÓN
    # =========================================================
    def _pagina_siguiente(self):
        if (self._current_page + 1) * self.PAGE_SIZE < len(self._raw_rows):
            self._current_page += 1
            self._render_page()

    def _pagina_anterior(self):
        if self._current_page > 0:
            self._current_page -= 1
            self._render_page()

    # =========================================================
    # FILTROS
    # =========================================================
    def _cargar_filtros(self, rows):
        self.cmb_empleado["values"] = [""] + sorted({r.get("empleado") for r in rows if r.get("empleado")})
        self.cmb_status["values"] = [""] + sorted(self.ESTADO_LABELS.values())
        self.cmb_tipo["values"] = [""] + sorted({r.get("event_type") for r in rows if r.get("event_type")})

    def _aplicar_filtros(self):
        emp = self.cmb_empleado.get().strip()
        st = self.cmb_status.get().strip()
        tp = self.cmb_tipo.get().strip()

        self._current_page = 0
        self._render_rows([
            r for r in self._raw_rows
            if (not emp or r.get("empleado") == emp)
            and (not st or r.get("status") == st)
            and (not tp or r.get("event_type") == tp)
        ][:self.PAGE_SIZE])

    def _limpiar_filtros(self):
        self.cmb_empleado.set("")
        self.cmb_status.set("")
        self.cmb_tipo.set("")
        self._current_page = 0
        self._render_page()

    # =========================================================
    # EVENTOS
    # =========================================================
    def _on_row_selected(self, *_):
            return

    def _aprobar(self, event_id):
        aprobar_evento_hr(event_id)
        self._load_data()

    def _rechazar(self, event_id, comentario):
        rechazar_evento_hr(event_id, comentario)
        self._load_data()

    def _abrir_popup_solicitud(self):
        PopupSolicitud(self, on_success=self._load_data)

    # =========================================================
    # Aprobaciones
    # =========================================================
    def _on_row_selected(self, *_):
        # Solo selección de fila, NO abrir popup
        return


    def _info_aprobaciones(self):
        """
        Abre el popup de aprobación SOLO desde el botón
        """
        if self.rol_usuario not in ("admin", "master"):
            return

        row = self.tabla.obtener_seleccionado()

        if not row:
            messagebox.showwarning(
                "Aprobaciones",
                "Debe seleccionar una solicitud."
            )
            return

        if "Pendiente" not in str(row.get("status")):
            messagebox.showwarning(
                "Aprobaciones",
                "Solo se pueden aprobar solicitudes en estado PENDING."
            )
            return

        PopupAprobacion(
            self,
            row_id=row["id"],
            on_approve=self._aprobar,
            on_reject=self._rechazar
        )


    def _aprobar(self, event_id: int, comentario: str | None = None):
        """
        Callback desde el popup
        """
        aprobar_evento_hr(event_id, comentario)
        self._load_data()


    def _rechazar(self, event_id: int, comentario: str):
        """
        Callback desde el popup
        """
        rechazar_evento_hr(event_id, comentario)
        self._load_data()

