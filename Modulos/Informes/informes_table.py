import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
from api_client import get_vessel_grain_sampling_list_api


from api_client import (
    api_request,
    get_container_report_excel_api,
    get_container_report_statuses_api
)
from Modulos.Informes.date_utils import to_db_date

from Modulos.Informes.popup.popup_generate_container_presentation import (
    PopupGenerateContainerPresentation
)

from api_client import generate_container_report_pdf_api


# =========================================================
# IMPORT DEL POPUP (CONEXIÓN REAL)
# =========================================================
from Modulos.Informes.popup.popup_container_report_preview import (
    PopupContainerReportPreview
)


class InformesTable(ttk.Frame):
    """
    Tabla consolidada de Informes — Container Reports

    Columnas:
    ID | Report No | User | Status | Vessel | Customer | Year | Month
    """

    PAGE_SIZE = 50

    # =========================================================
    # INIT
    # =========================================================
    def __init__(self, parent):
        super().__init__(parent)

        self.usuario = parent.usuario if hasattr(parent, "usuario") else None


        self._data_all = []
        self._data_map = {}
        self._page = 1
        self._searched = False

        # Blindaje UI
        self.lbl_page = ttk.Label(self, text="")
        self.lbl_info = ttk.Label(self, text="")
        self.btn_prev = ttk.Button(self, text="", state="disabled")
        self.btn_next = ttk.Button(self, text="", state="disabled")

        self.filter_report_no = tk.StringVar()
        self.filter_user = tk.StringVar()
        self.filter_status = tk.StringVar(value="All")
        self.filter_vessel = tk.StringVar()
        self.filter_customer = tk.StringVar()
        self.filter_year = tk.StringVar()
        self.filter_month = tk.StringVar()


        self._build_ui()

    # =========================================================
    # UI
    # =========================================================
    def _build_ui(self):
        self.pack(fill="both", expand=True)

        # ---------- Top bar ----------
        top = ttk.Frame(self)
        top.pack(fill="x", padx=10, pady=10)

        ttk.Label(top, text="Status:").pack(side="left")

        self.status_var = tk.StringVar(value="Pending review")
        self.status_cb = ttk.Combobox(
            top,
            textvariable=self.status_var,
            values=["Pending review", "Approved", "Rejected", "All"],
            width=20,
            state="readonly"
        )
        self.status_cb.pack(side="left", padx=(6, 10))


        ttk.Button(
            top,
            text="🔎 Buscar",
            command=self._on_search
        ).pack(side="left")

        self.lbl_info = ttk.Label(top, text="(Sin resultados — presiona Buscar)")
        self.lbl_info.pack(side="right")

        # ---------- Acciones (Dropdown único) ----------
        self.btn_actions = ttk.Button(
            top,
            text="⚙ Acciones",
            command=self._open_actions_menu
        )
        self.btn_actions.pack(side="right", padx=(10, 0))



        # ---------- Filters ----------
        filters = ttk.Frame(self)
        filters.pack(fill="x", padx=10, pady=(0, 6))

        def _cb(lbl, var, w=14):
            ttk.Label(filters, text=lbl).pack(side="left", padx=(0, 4))
            cb = ttk.Combobox(filters, textvariable=var, width=w, state="readonly")
            cb.pack(side="left", padx=(0, 10))
            cb.bind("<<ComboboxSelected>>", lambda e: self._apply_filters())
            return cb

        self.cb_report_no = _cb("Report No.", self.filter_report_no, 14)
        self.cb_user = _cb("User", self.filter_user, 14)
        self.cb_status = _cb("Status", self.filter_status, 14)
        self.cb_vessel = _cb("Vessel", self.filter_vessel, 14)
        self.cb_customer = _cb("Customer", self.filter_customer, 16)
        self.cb_year = _cb("Year", self.filter_year, 8)
        self.cb_month = _cb("Month", self.filter_month, 8)

        self.actions_menu = tk.Menu(self, tearoff=0)
        self.actions_menu.add_command(
            label="🔍 Review",
            command=self._review_selected
        )
        self.actions_menu.add_separator()
        self.actions_menu.add_command(
            label="📊 Export Excel",
            command=self._export_excel_selected
        )
        self.actions_menu.add_separator()
        self.actions_menu.add_command(
            label="✅ Approve",
            command=lambda: self._change_status_selected("Approved")
        )
        self.actions_menu.add_command(
            label="❌ Reject",
            command=lambda: self._change_status_selected("Rejected")
        )

        self.actions_menu.add_command(
            label="📄 Crear Informe Final",
            command=self._create_final_report_selected
        )
        self.actions_menu.add_separator()


        # ---------- Table ----------
        table_container = ttk.Frame(self)
        table_container.pack(fill="both", expand=True, padx=10, pady=(0, 4))

        self._build_table(table_container)

        # ---------- Pagination ----------
        pagination_container = ttk.Frame(self)
        pagination_container.pack(fill="x", padx=10, pady=(0, 10))

        self._build_pagination(pagination_container)
        # Cargar status desde backend (cuando todos los combobox existen)
        self._load_statuses()


    def _build_table(self, parent):

        columns = (
            "id",
            "report_no",
            "user",
            "status",
            "vessel",
            "customer",
            "year",
            "month"
        )

        self.tree = ttk.Treeview(
            parent,
            columns=columns,
            show="headings",
            height=16
        )

        headers = {
            "id": "ID",
            "report_no": "Report No.",
            "user": "User",
            "status": "Status",
            "vessel": "Vessel",
            "customer": "Customer",
            "year": "Year",
            "month": "Month"
        }

        widths = {
            "id": 60,
            "report_no": 150,
            "user": 140,
            "status": 140,
            "vessel": 160,
            "customer": 200,
            "year": 80,
            "month": 80
        }

        for col in columns:
            self.tree.heading(col, text=headers[col])
            self.tree.column(col, anchor="center", width=widths[col])

        self.tree.pack(fill="both", expand=True, side="left")

        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.bind("<Double-1>", lambda e: self._review_selected())
        

    def _build_pagination(self, parent):
        nav = ttk.Frame(parent)
        nav.pack(fill="x", pady=(8, 0))

        self.btn_prev = ttk.Button(
            nav,
            text="← Prev",
            command=self._prev_page,
            state="disabled"
        )
        self.btn_prev.pack(side="left")

        self.lbl_page = ttk.Label(nav, text="Page 0 / 0")
        self.lbl_page.pack(side="left", padx=10)

        self.btn_next = ttk.Button(
            nav,
            text="Next →",
            command=self._next_page,
            state="disabled"
        )
        self.btn_next.pack(side="left")

    # =========================================================
    # DATA
    # =========================================================
    def _on_search(self):
        try:
            self.lbl_info.config(text="Buscando...")
            self.update_idletasks()

            normalized = []
            self._data_map = {}

            # ==================================================
            # 1️⃣ CONTAINER REPORTS
            # ==================================================
            try:
                resp_container = api_request(
                    "GET",
                    "/container-reports/list"
                ).json()

                rows_container = resp_container.get("data", [])

                for r in rows_container:
                    if not isinstance(r, dict):
                        continue

                    rid = r.get("id")
                    if not rid:
                        continue

                    self._data_map[str(rid)] = r
                    normalized.append(r)

            except Exception:
                pass  # no rompemos si container falla

            # ==================================================
            # 2️⃣ VESSEL GRAIN SAMPLING
            # ==================================================
            try:
                resp_vessel = get_vessel_grain_sampling_list_api()

                if resp_vessel.get("success"):
                    rows_vessel = resp_vessel.get("data", [])

                    for r in rows_vessel:
                        if not isinstance(r, dict):
                            continue

                        rid = f"V{r.get('id')}"  # Prefijo para no colisionar IDs

                        r_normalized = {
                            "id": rid,
                            "report_no": r.get("cert_no"),
                            "user": r.get("requested_by"),
                            "status": "Vessel",
                            "vessel": r.get("vessel_name"),
                            "customer": r.get("requested_by"),
                            "year": to_db_date(r.get("place_date"))[:4] if r.get("place_date") else "",
                            "month": ""
                        }

                        self._data_map[str(rid)] = r_normalized
                        normalized.append(r_normalized)

            except Exception:
                pass  # no rompemos si vessel falla

            # ==================================================
            # ORDENAR POR ID DESC
            # ==================================================
            normalized.sort(
                key=lambda x: str(x.get("id")),
                reverse=True
            )

            self._data_all = normalized
            self._page = 1
            self._searched = True

            self._populate_filters(normalized)
            self._render_page()

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo cargar data:\n{e}"
            )

           

    def _render_page(self):
        self.tree.delete(*self.tree.get_children())

        total = len(self._data_all)
        if total == 0:
            self.lbl_page.config(text="Page 0 / 0")
            self.btn_prev.config(state="disabled")
            self.btn_next.config(state="disabled")
            return

        total_pages = (total + self.PAGE_SIZE - 1) // self.PAGE_SIZE

        start = (self._page - 1) * self.PAGE_SIZE
        end = start + self.PAGE_SIZE

        for r in self._data_all[start:end]:
            self.tree.insert(
                "",
                "end",
                iid=str(r["id"]),
                values=(
                    r.get("id"),
                    r.get("report_no"),
                    r.get("created_by") or r.get("user"),
                    r.get("status"),
                    r.get("vessel"),
                    r.get("customer"),
                    r.get("year"),
                    r.get("month")
                )
            )

        self.lbl_page.config(text=f"Page {self._page} / {total_pages}")
        self.lbl_info.config(text=f"Resultados: {total}")

        self.btn_prev.config(
            state="normal" if self._page > 1 else "disabled"
        )
        self.btn_next.config(
            state="normal" if self._page < total_pages else "disabled"
        )

    def _prev_page(self):
        if self._page > 1:
            self._page -= 1
            self._render_page()

    def _next_page(self):
        self._page += 1
        self._render_page()

    # =========================================================
    # ACTIONS
    # =========================================================

    def _get_selected_id(self):
        sel = self.tree.selection()
        return sel[0] if sel else None

    def _review_selected(self):
        rid = self._get_selected_id()
        if not rid:
            messagebox.showwarning("Review", "Selecciona un reporte.")
            return

        row = self._data_map.get(str(rid))
        if not row:
            messagebox.showerror("Review", "No se pudo obtener el reporte.")
            return

        # 🔥 Si es Vessel
        if str(rid).startswith("V"):
            vessel_id = str(rid)[1:]  # quitar prefijo V

            messagebox.showinfo(
                "Vessel Report",
                f"Aquí debes abrir el popup de Vessel.\nID: {vessel_id}"
            )

            # Aquí luego puedes abrir:
            # PopupVesselGrainSamplingPreview(...)

            return

        # 🔵 Si es Container (normal)
        PopupContainerReportPreview(
            parent=self,
            report=row
        )

    def _export_excel_selected(self):
        rid = self._get_selected_id()
        if not rid:
            messagebox.showwarning("Export", "Selecciona un reporte.")
            return

        try:
            resp = get_container_report_excel_api(rid)

            path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                initialfile=f"container_report_{rid}.xlsx",
                filetypes=[("Excel", "*.xlsx")]
            )
            if not path:
                return

            with open(path, "wb") as f:
                for chunk in resp.iter_content(8192):
                    if chunk:
                        f.write(chunk)

            messagebox.showinfo("Export", "Excel generado correctamente.")

        except Exception as e:
            messagebox.showerror(
                "Export",
                f"Error exportando Excel:\n{e}"
            )


    def _populate_filters(self, rows):

        def uniq(key):
            return sorted({str(r.get(key)) for r in rows if r.get(key)})

        self.cb_report_no["values"] = [""] + uniq("report_no")
        self.cb_user["values"] = [""] + sorted({
            str(r.get("user"))
            for r in rows
            if r.get("user")
        })
        self.cb_status["values"] = ["All", "Pending review", "Approved", "Rejected"]
        self.cb_vessel["values"] = [""] + uniq("vessel")
        self.cb_customer["values"] = [""] + uniq("customer")
        self.cb_year["values"] = [""] + uniq("year")
        self.cb_month["values"] = [""] + uniq("month")


    def _apply_filters(self):
        data = self._data_all

        def f(val, key):
            return not val or str(key) == val

        filtered = []
        for r in data:
            if self.filter_report_no.get() and str(r.get("report_no")) != self.filter_report_no.get():
                continue
            if self.filter_user.get() and str(r.get("user")) != self.filter_user.get():
                continue
            if self.filter_status.get() != "All" and r.get("status") != self.filter_status.get():
                continue
            if self.filter_vessel.get() and str(r.get("vessel")) != self.filter_vessel.get():
                continue
            if self.filter_customer.get() and str(r.get("customer")) != self.filter_customer.get():
                continue
            if self.filter_year.get() and str(r.get("year")) != self.filter_year.get():
                continue
            if self.filter_month.get() and str(r.get("month")) != self.filter_month.get():
                continue

            filtered.append(r)

        self._data_all = filtered
        self._page = 1
        self._render_page()

    def _change_status_selected(self, status):
        rid = self._get_selected_id()
        if not rid:
            messagebox.showwarning(
                "Status",
                "Selecciona un reporte."
            )
            return

        try:
            # ==================================================
            # 1) Actualizar status
            # ==================================================
            api_request(
                "PUT",
                f"/container-reports/{rid}",
                json={"status": status}
            )

            # ==================================================
            # 2) Si se aprueba → generar Excel + PDF (SAVE AS)
            # ==================================================
            if status == "Approved":

                # ----------------------------------------------
                # 2.1 Disparar generación de Excel (backend)
                #     (NO se guarda, solo asegura template OK)
                # ----------------------------------------------
                try:
                    resp = get_container_report_excel_api(rid)
                    try:
                        for _ in resp.iter_content(8192):
                            break
                    finally:
                        resp.close()
                except Exception as e:
                    raise Exception(
                        f"Error generando Excel desde template:\n{e}"
                    )

                # ----------------------------------------------
                # 2.2 Generar PDF REAL + Save As (DIRECTO)
                # ----------------------------------------------
                try:
                    resp = generate_container_report_pdf_api(rid)

                    path = filedialog.asksaveasfilename(
                        defaultextension=".pdf",
                        initialfile=f"container_report_{rid}.pdf",
                        filetypes=[("PDF", "*.pdf")]
                    )

                    if not path:
                        resp.close()
                        return

                    with open(path, "wb") as f:
                        for chunk in resp.iter_content(8192):
                            if chunk:
                                f.write(chunk)

                    resp.close()

                except Exception as e:
                    raise Exception(
                        f"Error generando / guardando PDF:\n{e}"
                    )

            # ==================================================
            # 3) Refrescar tabla
            # ==================================================
            self._on_search()

        except Exception as e:
            messagebox.showerror(
                "Status",
                f"Error actualizando status:\n{e}"
            )


    def _load_statuses(self):
        """
        Carga los status disponibles desde el backend
        """
        try:
            statuses = get_container_report_statuses_api()

            if not statuses:
                statuses = ["All"]

            self.status_cb["values"] = statuses
            self.cb_status["values"] = statuses

            if self.status_var.get() not in statuses:
                self.status_var.set("All")

            if self.filter_status.get() not in statuses:
                self.filter_status.set("All")

        except Exception:
            self.status_cb["values"] = ["All"]
            self.cb_status["values"] = ["All"]
            self.status_var.set("All")
            self.filter_status.set("All")


    def _open_actions_menu(self, event=None):
        rid = self._get_selected_id()
        if not rid:
            messagebox.showwarning(
                "Acciones",
                "Selecciona un reporte primero."
            )
            return

        try:
            # ==================================================
            # 🔒 CONTROL DE USUARIOS RESTRINGIDOS
            # ==================================================
            restricted_users = {"surveyor01", "surveyor02", "surveyor03"}

            is_restricted = str(self.usuario or "").strip().lower() in restricted_users

            # ==================================================
            # 🔁 RECONSTRUIR MENU DINÁMICAMENTE
            # ==================================================
            self.actions_menu.delete(0, "end")

            # --- Review ---
            self.actions_menu.add_command(
                label="🔍 Review",
                command=self._review_selected
            )

            self.actions_menu.add_separator()

            # --- Export ---
            self.actions_menu.add_command(
                label="📊 Export Excel",
                command=self._export_excel_selected
            )

            self.actions_menu.add_separator()

            # --- Approve / Reject (CONDICIONAL) ---
            if is_restricted:
                self.actions_menu.add_command(
                    label="✅ Approve",
                    state="disabled"
                )
                self.actions_menu.add_command(
                    label="❌ Reject",
                    state="disabled"
                )
            else:
                self.actions_menu.add_command(
                    label="✅ Approve",
                    command=lambda: self._change_status_selected("Approved")
                )
                self.actions_menu.add_command(
                    label="❌ Reject",
                    command=lambda: self._change_status_selected("Rejected")
                )

            self.actions_menu.add_separator()

            # --- Final Report ---
            self.actions_menu.add_command(
                label="📄 Crear Informe Final",
                command=self._create_final_report_selected
            )

            # ==================================================
            # 📍 MOSTRAR MENU
            # ==================================================
            x = self.btn_actions.winfo_rootx()
            y = self.btn_actions.winfo_rooty() + self.btn_actions.winfo_height()

            self.actions_menu.tk_popup(x, y)

        finally:
            self.actions_menu.grab_release()



    def _create_final_report_selected(self):
        rid = self._get_selected_id()
        if not rid:
            messagebox.showwarning(
                "Informe Final",
                "Selecciona un reporte."
            )
            return

        try:
            PopupGenerateContainerPresentation(
                parent=self,
                container_report_id=int(rid)
            )

        except Exception as e:
            messagebox.showerror(
                "Informe Final",
                f"No se pudo abrir el generador de informe final:\n{e}"
            )

