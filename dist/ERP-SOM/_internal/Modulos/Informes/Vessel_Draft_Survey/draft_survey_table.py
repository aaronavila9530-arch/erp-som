import tkinter as tk
from tkinter import ttk, messagebox

from api_client import (
    get_draft_survey_headers_api,
    update_draft_survey_api
)


class DraftSurveyTable(ttk.Frame):

    PAGE_SIZE = 50

    # =========================================================
    # INIT
    # =========================================================
    def __init__(self, parent):
        super().__init__(parent)

        # 🔒 Usuario heredado (estándar ERP)
        self.usuario = getattr(parent, "usuario", None)

        self._data_all = []
        self._data_map = {}
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
            text="Draft Survey Reports",
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
        table_container = ttk.Frame(self)
        table_container.pack(fill="both", expand=True, padx=10)

        self._build_table(table_container)

        # ---------------- PAGINATION ----------------
        pagination_container = ttk.Frame(self)
        pagination_container.pack(fill="x", padx=10, pady=10)

        self._build_pagination(pagination_container)

        # ---------------- ACTION MENU ----------------
        self.actions_menu = tk.Menu(self, tearoff=0)

        self.actions_menu.add_command(
            label="🔍 Review",
            command=self._review_selected
        )

        self.actions_menu.add_separator()

        # ✅ Approve (queda tal cual)
        self.actions_menu.add_command(
            label="✅ Approve",
            command=self._approve_selected
        )

        # ✅ NUEVO: Generar Word (mismo flujo de Approve)
        self.actions_menu.add_command(
            label="📄 Generar Word (Aprueba)",
            command=self._approve_selected
        )

        # ✅ NUEVO: Generar Excel (NO aprueba)
        self.actions_menu.add_command(
            label="📊 Generar Excel (PDF)",
            command=self._generate_excel_selected
        )

        self.actions_menu.add_command(
            label="❌ Reject",
            command=lambda: self._change_status("Rejected")
        )

        self.actions_menu.add_separator()

        # ✅ Generar Informe Final (abre popup)
        self.actions_menu.add_command(
            label="🧾 Generar Informe Final",
            command=self._open_final_popup
        )

    # =========================================================
    # GENERATE EXCEL PDF (NO APPROVE)
    # =========================================================
    def _generate_excel_selected(self):

        draft_report_number = self._get_selected_id()

        if not draft_report_number:
            messagebox.showwarning(
                "Excel",
                "Selecciona un reporte."
            )
            return

        confirm = messagebox.askyesno(
            "Generar Excel (PDF)",
            "¿Desea generar el PDF desde el Excel del Draft Survey?"
        )

        if not confirm:
            return

        try:
            # -------------------------------------------------
            # 1️⃣ GENERAR PDF EXCEL DESDE BACKEND
            # -------------------------------------------------
            from api_client import generate_draft_survey_excel_pdf_api

            result = generate_draft_survey_excel_pdf_api(
                str(draft_report_number)
            )

            if not result.get("success"):
                raise Exception(
                    result.get("error") or
                    "Error generating Excel PDF."
                )

            pdf_binary = result.get("content")

            if not pdf_binary:
                raise Exception(
                    "Backend did not return file content."
                )

            # -------------------------------------------------
            # 2️⃣ SAVE AS
            # -------------------------------------------------
            from tkinter import filedialog

            default_name = f"{draft_report_number}_DRAFT_SURVEY.pdf"

            save_path = filedialog.asksaveasfilename(
                title="Guardar Draft Survey (Excel PDF)",
                defaultextension=".pdf",
                initialfile=default_name,
                filetypes=[("PDF", "*.pdf")]
            )

            if not save_path:
                return  # usuario canceló

            with open(save_path, "wb") as f:
                f.write(pdf_binary)

            messagebox.showinfo(
                "OK",
                "PDF Excel generado correctamente."
            )

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo generar el PDF Excel:\n{str(e)}"
            )

    # =========================================================
    # TABLE
    # =========================================================
    def _build_table(self, parent):

        columns = (
            "draft_report_number",
            "client",
            "port",
            "country",
            "continent",
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
            "draft_report_number": "Draft No",
            "client": "Client",
            "port": "Port",
            "country": "Country",
            "continent": "Continent",
            "year": "Year",
            "month": "Month",
            "status": "Status"
        }

        widths = {
            "draft_report_number": 170,
            "client": 220,
            "port": 160,
            "country": 150,
            "continent": 140,
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
    # PAGINATION
    # =========================================================
    def _build_pagination(self, parent):

        nav = ttk.Frame(parent)
        nav.pack(fill="x")

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
    # SEARCH (GET) — HEADERS
    # =========================================================
    def _on_search(self):

        try:
            self.lbl_info.config(text="Buscando...")
            self.update_idletasks()

            resp = get_draft_survey_headers_api()

            if not resp.get("success"):
                self._data_all = []
                self._data_map = {}
            else:
                rows = resp.get("data", []) or []

                normalized = []
                self._data_map = {}

                for r in rows:
                    draft_no = r.get("draft_report_number")

                    if not draft_no:
                        continue

                    record = {
                        "draft_report_number": draft_no,
                        "status": r.get("status"),
                        "year": r.get("year"),
                        "month": r.get("month"),
                        "continent": r.get("continent"),
                        "country": r.get("country"),
                        "port": r.get("port"),
                        "client": r.get("client")
                    }

                    normalized.append(record)
                    self._data_map[str(draft_no)] = r

                normalized.sort(
                    key=lambda x: str(x.get("draft_report_number") or ""),
                    reverse=True
                )

                self._data_all = normalized

            self._page = 1
            self._render_page()

        except Exception as e:
            messagebox.showerror("Error", str(e))

    # =========================================================
    # RENDER
    # =========================================================
    def _render_page(self):

        self.tree.delete(*self.tree.get_children())

        total = len(self._data_all)

        if total == 0:
            self.lbl_page.config(text="Page 0 / 0")
            self.btn_prev.config(state="disabled")
            self.btn_next.config(state="disabled")
            self.lbl_info.config(text="Sin resultados")
            return

        total_pages = (total + self.PAGE_SIZE - 1) // self.PAGE_SIZE

        start = (self._page - 1) * self.PAGE_SIZE
        end = start + self.PAGE_SIZE

        for r in self._data_all[start:end]:

            iid = str(r.get("draft_report_number"))

            self.tree.insert(
                "",
                "end",
                iid=iid,
                values=(
                    r.get("draft_report_number"),
                    r.get("client"),
                    r.get("port"),
                    r.get("country"),
                    r.get("continent"),
                    r.get("year"),
                    r.get("month"),
                    r.get("status")
                )
            )

        self.lbl_page.config(
            text=f"Page {self._page} / {total_pages}"
        )

        self.lbl_info.config(
            text=f"Resultados: {total}"
        )

        self.btn_prev.config(
            state="normal" if self._page > 1 else "disabled"
        )

        self.btn_next.config(
            state="normal" if self._page < total_pages else "disabled"
        )

    # =========================================================
    # ACTIONS
    # =========================================================
    def _get_selected_id(self):
        sel = self.tree.selection()
        return sel[0] if sel else None

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

            self.actions_menu.add_separator()

            # --- Approve / Word (mismo flujo) ---
            if is_restricted:
                self.actions_menu.add_command(
                    label="✅ Approve",
                    state="disabled"
                )
                self.actions_menu.add_command(
                    label="📄 Generar Word (Aprueba)",
                    state="disabled"
                )
            else:
                self.actions_menu.add_command(
                    label="✅ Approve",
                    command=self._approve_selected
                )
                self.actions_menu.add_command(
                    label="📄 Generar Word (Aprueba)",
                    command=self._approve_selected
                )

            # --- Excel (SIEMPRE permitido) ---
            self.actions_menu.add_command(
                label="📊 Generar Excel (PDF)",
                command=self._generate_excel_selected
            )

            # --- Reject ---
            if is_restricted:
                self.actions_menu.add_command(
                    label="❌ Reject",
                    state="disabled"
                )
            else:
                self.actions_menu.add_command(
                    label="❌ Reject",
                    command=lambda: self._change_status("Rejected")
                )

            self.actions_menu.add_separator()

            # --- Final Report Popup ---
            self.actions_menu.add_command(
                label="🧾 Generar Informe Final",
                command=self._open_final_popup
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
    # REVIEW (OPEN FULL DRAFT FORM)
    # =========================================================
    def _review_selected(self):

        draft_report_number = self._get_selected_id()

        if not draft_report_number:
            messagebox.showwarning(
                "Review",
                "Selecciona un reporte."
            )
            return

        try:
            from Modulos.Informes.Vessel_Draft_Survey.draft_survey_form import DraftSurveyForm
            from api_client import get_full_draft_survey_api

            data = get_full_draft_survey_api(str(draft_report_number))

            if not data:
                messagebox.showerror(
                    "Error",
                    "No se pudo obtener la información del Draft."
                )
                return

            # 🔒 Destruir vista actual (tabla)
            for widget in self.master.winfo_children():
                widget.destroy()

            # 🔥 Abrir formulario completo
            form = DraftSurveyForm(self.master)

            # 🔥 Cargar payload unificado
            form.set_payload(data)

            form.pack(fill="both", expand=True)

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo abrir el Draft:\n{e}"
            )

    # =========================================================
    # CHANGE STATUS (REJECT / OTHER)
    # =========================================================
    def _change_status(self, new_status: str):

        draft_report_number = self._get_selected_id()

        if not draft_report_number:
            messagebox.showwarning(
                "Status",
                "Selecciona un reporte."
            )
            return

        confirm = messagebox.askyesno(
            "Confirm",
            f"¿Desea cambiar el estado a '{new_status}'?"
        )

        if not confirm:
            return

        try:
            payload = {"status": new_status}

            result = update_draft_survey_api(
                draft_report_number=str(draft_report_number),
                payload=payload
            )

            if not result.get("success"):
                messagebox.showerror(
                    "Error",
                    result.get("message", "No se pudo actualizar el estado.")
                )
                return

            messagebox.showinfo(
                "OK",
                f"Estado actualizado a '{new_status}'."
            )

            self._on_search()

        except Exception as e:
            messagebox.showerror("Error", str(e))

    # =========================================================
    # APPROVE + GENERATE FINAL PDF (WORD + EXCEL MERGED)
    # =========================================================
    def _approve_selected(self):

        draft_report_number = self._get_selected_id()

        if not draft_report_number:
            messagebox.showwarning(
                "Approve",
                "Selecciona un reporte."
            )
            return

        confirm = messagebox.askyesno(
            "Confirm Approve",
            "¿Desea aprobar el Draft y generar el Informe Final (Word + Excel)?"
        )

        if not confirm:
            return

        try:
            # -------------------------------------------------
            # 1️⃣ GENERAR FINAL PDF DESDE BACKEND (MERGE)
            # -------------------------------------------------
            from api_client import generate_draft_survey_final_pdf_api

            result = generate_draft_survey_final_pdf_api(
                str(draft_report_number)
            )

            if not result.get("success"):
                raise Exception(
                    result.get("error") or
                    result.get("message") or
                    "Error generating Final PDF."
                )

            pdf_binary = result.get("content")

            if not pdf_binary:
                raise Exception(
                    "Backend did not return Final PDF content."
                )

            # -------------------------------------------------
            # 2️⃣ SAVE AS (SOLO FINAL)
            # -------------------------------------------------
            from tkinter import filedialog

            default_name = f"{draft_report_number}_FINAL.pdf"

            save_path = filedialog.asksaveasfilename(
                title="Guardar Informe Final (PDF)",
                defaultextension=".pdf",
                initialfile=default_name,
                filetypes=[("PDF", "*.pdf")]
            )

            if not save_path:
                return

            with open(save_path, "wb") as f:
                f.write(pdf_binary)

            # -------------------------------------------------
            # 3️⃣ ACTUALIZAR STATUS A APPROVED
            # -------------------------------------------------
            update_result = update_draft_survey_api(
                str(draft_report_number),
                {"status": "Approved"}
            )

            if not update_result.get("success"):
                messagebox.showwarning(
                    "Aviso",
                    "Informe generado pero no se pudo actualizar el estado."
                )
            else:
                messagebox.showinfo(
                    "OK",
                    "Informe Final generado y Draft aprobado correctamente."
                )

            self._on_search()

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo completar Approve:\n{str(e)}"
            )




    # =========================================================
    # OPEN FINAL REPORT POPUP (Presentation + Final)
    # =========================================================
    def _open_final_popup(self):

        draft_report_number = self._get_selected_id()

        if not draft_report_number:
            messagebox.showwarning(
                "Informe Final",
                "Selecciona un reporte."
            )
            return

        try:
            from Modulos.Informes.Vessel_Draft_Survey.popup_draft_survey_presentation import (
                PopupDraftSurveyPresentation
            )

            PopupDraftSurveyPresentation(
                self,
                draft_report_number
            )

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo abrir el popup de Informe Final:\n{str(e)}"
            )


    # =========================================================
    # SAVE PDF BYTES (HELPER)
    # =========================================================
    def _save_pdf_bytes(self, pdf_binary: bytes, default_name: str, title: str) -> str:

        if not pdf_binary:
            raise Exception("Empty PDF content")

        from tkinter import filedialog

        save_path = filedialog.asksaveasfilename(
            title=title,
            defaultextension=".pdf",
            initialfile=default_name,
            filetypes=[("PDF", "*.pdf")]
        )

        if not save_path:
            return ""  # usuario canceló

        with open(save_path, "wb") as f:
            f.write(pdf_binary)

        return save_path


    # =========================================================
    # PAGINATION NAV
    # =========================================================
    def _prev_page(self):
        if self._page > 1:
            self._page -= 1
            self._render_page()

    def _next_page(self):
        self._page += 1
        self._render_page()