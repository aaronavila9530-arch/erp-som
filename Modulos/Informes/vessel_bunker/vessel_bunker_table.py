import tkinter as tk
from tkinter import ttk, messagebox

from api_client import (
    get_all_vessel_bunker_reports_api,
    get_vessel_bunker_report_api,
    update_vessel_bunker_report_api,
    generate_vessel_bunker_excel_api
)
from Modulos.Informes.date_utils import to_db_date

class VesselBunkerTable(ttk.Frame):

    PAGE_SIZE = 50

    # =========================================================
    # INIT
    # =========================================================
    def __init__(self, parent):
        super().__init__(parent)

        # 🔒 Usuario heredado (estándar ERP)
        self.usuario = getattr(parent, "usuario", None)

        self._data_all = []
        self._page = 1

        self._build_ui()

    # =========================================================
    # UI
    # =========================================================
    def _build_ui(self):

        self.pack(fill="both", expand=True)

        # ---------------- TOP BAR ----------------
        top = ttk.Frame(self)
        top.pack(fill="x", padx=10, pady=10)

        ttk.Label(
            top,
            text="Vessel Bunker Reports",
            font=("Segoe UI", 12, "bold")
        ).pack(side="left")

        ttk.Button(
            top,
            text="🔎 Buscar",
            command=self._on_search
        ).pack(side="right")

        self.btn_actions = ttk.Button(
            top,
            text="⚙ Acciones",
            command=self._open_actions_menu
        )
        self.btn_actions.pack(side="right", padx=(0, 10))

        self.lbl_info = ttk.Label(
            top,
            text="(Sin resultados — presiona Buscar)"
        )
        self.lbl_info.pack(side="right", padx=10)

        # ---------------- TABLE ----------------
        container = ttk.Frame(self)
        container.pack(fill="both", expand=True, padx=10)

        self._build_table(container)

        # ---------------- PAGINATION ----------------
        pag = ttk.Frame(self)
        pag.pack(fill="x", padx=10, pady=10)

        self._build_pagination(pag)

        # ---------------- ACTION MENU ----------------
        self.actions_menu = tk.Menu(self, tearoff=0)

        self.actions_menu.add_command(
            label="🔍 Review",
            command=self._review_selected
        )

        self.actions_menu.add_command(
            label="❌ Reject",
            command=lambda: self._change_status("Rejected")
        )

        self.actions_menu.add_command(
            label="✅ Approve",
            command=lambda: self._change_status("Approved")
        )

        self.actions_menu.add_separator()

        self.actions_menu.add_command(
            label="📊 Generate Excel",
            command=self._generate_excel_selected
        )

        self.actions_menu.add_command(
            label="📄 Crear Informe Final",
            command=self._create_final_report_selected
        )


    # =========================================================
    # TABLE
    # =========================================================
    def _build_table(self, parent):

        columns = (
            "id",
            "vessel_name",
            "port",
            "country",
            "year",
            "month",
            "status"
        )

        self.tree = ttk.Treeview(
            parent,
            columns=columns,
            show="headings",
            height=18
        )

        headers = {
            "id": "ID",
            "vessel_name": "Vessel",
            "port": "Port",
            "country": "Country",
            "year": "Year",
            "month": "Month",
            "status": "Status"
        }

        widths = {
            "id": 100,
            "vessel_name": 250,
            "port": 160,
            "country": 150,
            "year": 80,
            "month": 80,
            "status": 150
        }

        for col in columns:
            self.tree.heading(col, text=headers[col])
            self.tree.column(col, width=widths[col], anchor="center")

        self.tree.pack(fill="both", expand=True, side="left")

        scrollbar = ttk.Scrollbar(
            parent,
            orient="vertical",
            command=self.tree.yview
        )
        scrollbar.pack(side="right", fill="y")

        self.tree.configure(yscrollcommand=scrollbar.set)

    # =========================================================
    # SEARCH (GET ALL)
    # =========================================================
    def _on_search(self):

        try:
            self.lbl_info.config(text="Buscando...")
            self.update_idletasks()

            resp = get_all_vessel_bunker_reports_api(limit=500)

            if not resp.get("success"):
                self._data_all = []
            else:
                rows = resp.get("data", []) or []
                rows.sort(key=lambda x: x.get("id", 0), reverse=True)
                self._data_all = rows

            self._page = 1
            self._render_page()

        except Exception as e:
            messagebox.showerror("Error", str(e))

    # =========================================================
    # RENDER
    # =========================================================
    def _render_page(self):

        # -----------------------------------------------------
        # Clear table
        # -----------------------------------------------------
        self.tree.delete(*self.tree.get_children())

        total = len(self._data_all or [])

        if total == 0:
            self.lbl_page.config(text="Page 0 / 0")
            self.lbl_info.config(text="Sin resultados")
            return

        # -----------------------------------------------------
        # Pagination safety
        # -----------------------------------------------------
        total_pages = (total + self.PAGE_SIZE - 1) // self.PAGE_SIZE

        if self._page < 1:
            self._page = 1
        if self._page > total_pages:
            self._page = total_pages

        start = (self._page - 1) * self.PAGE_SIZE
        end = start + self.PAGE_SIZE

        # -----------------------------------------------------
        # Render rows
        # -----------------------------------------------------
        for r in (self._data_all[start:end] or []):

            # Defensive read
            report_id = r.get("id")
            ship_name = r.get("ship_name") or ""
            port = r.get("port") or ""
            country = r.get("country") or ""
            status = r.get("status") or ""

            # Derive year / month from report_date
            year = ""
            month = ""

            report_date = r.get("report_date")

            if report_date:
                try:
                    date_str = to_db_date(report_date)
                    # Expecting YYYY-MM-DD
                    if len(date_str) >= 7:
                        year = date_str[0:4]
                        month = date_str[5:7]
                except Exception:
                    year = ""
                    month = ""

            iid = str(report_id) if report_id is not None else ""

            self.tree.insert(
                "",
                "end",
                iid=iid,
                values=(
                    report_id,
                    ship_name,   # ✅ correct field from DB
                    port,
                    country,
                    year,        # ✅ derived from report_date
                    month,       # ✅ derived from report_date
                    status
                )
            )

        # -----------------------------------------------------
        # Update labels
        # -----------------------------------------------------
        self.lbl_page.config(text=f"Page {self._page} / {total_pages}")
        self.lbl_info.config(text=f"Resultados: {total}")


    # =========================================================
    # ACTIONS
    # =========================================================
    def _get_selected_id(self):
        sel = self.tree.selection()
        return int(sel[0]) if sel else None

    def _open_actions_menu(self):

        rid = self._get_selected_id()
        if not rid:
            messagebox.showwarning("Acciones", "Selecciona un reporte.")
            return

        try:
            # ==================================================
            # 🔒 CONTROL DE USUARIOS RESTRINGIDOS
            # ==================================================
            restricted_users = {"surveyor01", "surveyor02"}
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

            # --- Reject / Approve ---
            if is_restricted:
                self.actions_menu.add_command(
                    label="❌ Reject",
                    state="disabled"
                )
                self.actions_menu.add_command(
                    label="✅ Approve",
                    state="disabled"
                )
            else:
                self.actions_menu.add_command(
                    label="❌ Reject",
                    command=lambda: self._change_status("Rejected")
                )
                self.actions_menu.add_command(
                    label="✅ Approve",
                    command=lambda: self._change_status("Approved")
                )

            self.actions_menu.add_separator()

            # --- Excel ---
            self.actions_menu.add_command(
                label="📊 Generate Excel",
                command=self._generate_excel_selected
            )

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

    # =========================================================
    # REVIEW (OPEN FORM + GET BY ID)
    # =========================================================
    def _review_selected(self):

        report_id = self._get_selected_id()

        if not report_id:
            messagebox.showwarning("Review", "Selecciona un reporte.")
            return

        try:
            resp = get_vessel_bunker_report_api(report_id)

            if not resp.get("success"):
                raise Exception(resp.get("detail") or resp.get("error") or "Error loading report")

            payload = resp.get("data") or {}

            # ✅ OJO: tu form se llama VesselBunkerReportForm (no VesselBunkerForm)
            from Modulos.Informes.vessel_bunker.vessel_bunker_form import VesselBunkerReportForm

            # 🔒 Destruir vista actual (tabla)
            for widget in self.master.winfo_children():
                widget.destroy()

            # 🔥 Abrir formulario
            form = VesselBunkerReportForm(self.master)

            # ✅ Importantísimo: setear report_id para que el PUT funcione
            form.report_id = int(payload.get("id") or report_id)

            # 🔥 Cargar payload
            form.set_payload(payload, from_review=True)

            form.pack(fill="both", expand=True)

        except Exception as e:
            messagebox.showerror("Error", str(e))


    # =========================================================
    # CHANGE STATUS (PUT)
    # =========================================================
    def _change_status(self, new_status: str):

        report_id = self._get_selected_id()

        if not report_id:
            messagebox.showwarning("Status", "Selecciona un reporte.")
            return

        confirm = messagebox.askyesno(
            "Confirm",
            f"¿Desea cambiar el estado a '{new_status}'?"
        )

        if not confirm:
            return

        try:
            payload = {"status": new_status}

            result = update_vessel_bunker_report_api(
                report_id,
                payload
            )

            if not result.get("success"):
                raise Exception(result.get("error"))

            messagebox.showinfo("OK", "Estado actualizado correctamente.")
            self._on_search()

        except Exception as e:
            messagebox.showerror("Error", str(e))



    # =========================================================
    # GENERATE EXCEL
    # =========================================================
    def _generate_excel_selected(self):

        report_id = self._get_selected_id()

        if not report_id:
            messagebox.showwarning("Excel", "Selecciona un reporte.")
            return

        try:
            self.lbl_info.config(text="Generando Excel...")
            self.update_idletasks()

            resp = generate_vessel_bunker_excel_api(report_id)

            if not resp.get("success"):
                raise Exception(
                    resp.get("detail")
                    or resp.get("error")
                    or "Error generando Excel"
                )

            content = resp.get("content")

            if not content:
                raise Exception("No se recibió contenido del archivo.")

            # ---------------------------------------------
            # Guardar archivo temporal
            # ---------------------------------------------
            import tempfile
            import os

            tmp_dir = tempfile.mkdtemp(prefix="bunker_excel_")
            file_path = os.path.join(
                tmp_dir,
                f"vessel_bunker_report_{report_id}.xlsx"
            )

            with open(file_path, "wb") as f:
                f.write(content)

            # ---------------------------------------------
            # Abrir Excel automáticamente
            # ---------------------------------------------
            os.startfile(file_path)

            self.lbl_info.config(text="Excel generado correctamente.")

        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.lbl_info.config(text="Error generando Excel.")



    # =========================================================
    # CREATE FINAL REPORT (OPEN PDF POPUP)
    # =========================================================
    def _create_final_report_selected(self):

        report_id = self._get_selected_id()

        if not report_id:
            messagebox.showwarning(
                "Informe Final",
                "Selecciona un reporte."
            )
            return

        try:
            # Import dinámico para evitar circular imports
            from Modulos.Informes.vessel_bunker.popup_vessel_bunker_pdf import (
                PopupVesselBunkerPDF
            )

            PopupVesselBunkerPDF(
                self.master,
                report_id
            )

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo abrir el generador de informe.\n{e}"
            )



    # =========================================================
    # PAGINATION
    # =========================================================
    def _build_pagination(self, parent):

        nav = ttk.Frame(parent)
        nav.pack(fill="x")

        self.btn_prev = ttk.Button(nav, text="← Prev", command=self._prev_page)
        self.btn_prev.pack(side="left")

        self.lbl_page = ttk.Label(nav, text="Page 0 / 0")
        self.lbl_page.pack(side="left", padx=10)

        self.btn_next = ttk.Button(nav, text="Next →", command=self._next_page)
        self.btn_next.pack(side="left")

    def _prev_page(self):
        if self._page > 1:
            self._page -= 1
            self._render_page()

    def _next_page(self):
        self._page += 1
        self._render_page()
