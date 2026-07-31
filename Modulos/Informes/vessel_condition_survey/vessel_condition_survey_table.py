import tkinter as tk
from tkinter import ttk, messagebox

from api_client import (
    get_all_vessel_condition_surveys_api,
    get_vessel_condition_survey_api,
    get_vessel_condition_survey_by_id_api,
    update_vessel_condition_survey_api,
    download_vessel_condition_survey_word
)

from Modulos.Informes.vessel_condition_survey.popup_pdf_merge import PopupPDFMerge

class VesselConditionSurveyTable(ttk.Frame):

    PAGE_SIZE = 50

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

        top = ttk.Frame(self)
        top.pack(fill="x", padx=10, pady=10)

        ttk.Label(
            top,
            text="Vessel Condition Surveys",
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
        self.btn_actions.pack(side="right", padx=(0,10))

        self.lbl_info = ttk.Label(
            top,
            text="(Sin resultados — presiona Buscar)"
        )
        self.lbl_info.pack(side="right", padx=10)


        container = ttk.Frame(self)
        container.pack(fill="both", expand=True, padx=10)

        self._build_table(container)

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
            label="📄 Crear Word",
            command=self._generate_word
        )

        self.actions_menu.add_command(
            label="📑 Crear Informe Final",
            command=self._open_final_report_popup
        )


    # =========================================================
    # TABLE
    # =========================================================

    def _build_table(self, parent):

        columns = (
            "id",
            "report_number",
            "vessel",
            "port",
            "country",
            "date",
            "status"
        )

        self.tree = ttk.Treeview(
            parent,
            columns=columns,
            show="headings",
            height=18
        )

        headers = {
            "id":"ID",
            "report_number":"Report No",
            "vessel":"Vessel",
            "port":"Port",
            "country":"Country",
            "date":"Date",
            "status":"Status"
        }

        widths = {
            "id":80,
            "report_number":150,
            "vessel":220,
            "port":150,
            "country":150,
            "date":120,
            "status":150
        }

        for col in columns:

            self.tree.heading(col,text=headers[col])
            self.tree.column(col,width=widths[col],anchor="center")

        self.tree.pack(fill="both",expand=True,side="left")

        scrollbar = ttk.Scrollbar(
            parent,
            orient="vertical",
            command=self.tree.yview
        )

        scrollbar.pack(side="right",fill="y")

        self.tree.configure(yscrollcommand=scrollbar.set)


    # =========================================================
    # SEARCH
    # =========================================================

    def _on_search(self):

        try:

            self.lbl_info.config(text="Buscando...")

            resp = get_all_vessel_condition_surveys_api()

            if not resp.get("success"):

                self._data_all = []

            else:

                rows = resp.get("data",[]) or []
                rows.sort(key=lambda x:x.get("id",0),reverse=True)

                self._data_all = rows

            self._render_page()

        except Exception as e:

            messagebox.showerror("Error",str(e))


    # =========================================================
    # RENDER
    # =========================================================

    def _render_page(self):

        self.tree.delete(*self.tree.get_children())

        for r in self._data_all:

            self.tree.insert(
                "",
                "end",
                iid=str(r.get("id")),
                values=(
                    r.get("id"),
                    r.get("report_number") or "",
                    r.get("vessel") or "",
                    r.get("port") or "",
                    r.get("country") or "",
                    r.get("service_start_date") or "",
                    r.get("status") or ""
                )
            )


    # =========================================================
    # ACTIONS
    # =========================================================

    def _get_selected_report(self):

        sel = self.tree.selection()

        if not sel:
            return None

        item = self.tree.item(sel[0])

        return item["values"][1]  # report_number


    def _open_actions_menu(self):

        report = self._get_selected_report()

        if not report:
            messagebox.showwarning("Acciones","Selecciona un reporte.")
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

            # --- Word ---
            self.actions_menu.add_command(
                label="📄 Crear Word",
                command=self._generate_word
            )

            # --- Final Report ---
            self.actions_menu.add_command(
                label="📑 Crear Informe Final",
                command=self._open_final_report_popup
            )

            # ==================================================
            # 📍 MOSTRAR MENU
            # ==================================================
            x = self.btn_actions.winfo_rootx()
            y = self.btn_actions.winfo_rooty() + self.btn_actions.winfo_height()

            self.actions_menu.tk_popup(x,y)

        finally:
            self.actions_menu.grab_release()


    # =========================================================
    # REVIEW
    # =========================================================

    def _review_selected(self):

        report_number = self._get_selected_report()
        record_id = self._get_selected_record_id()

        if not report_number:
            messagebox.showwarning("Review", "Selecciona un reporte.")
            return

        if not record_id:
            messagebox.showwarning("Review", "No se encontró el ID del registro.")
            return

        try:

            from Modulos.Informes.vessel_condition_survey.vessel_condition_survey_form import (
                VesselConditionSurveyForm
            )

            # ==================================================
            # IMPORTANTE:
            # Para review usa endpoint por ID, no por report_number
            # ==================================================
            resp = get_vessel_condition_survey_by_id_api(record_id)

            if not isinstance(resp, dict) or not resp.get("success"):
                messagebox.showerror(
                    "Review",
                    resp.get("error", "No se pudo cargar el reporte.")
                    if isinstance(resp, dict) else
                    "Respuesta inválida del backend."
                )
                return

            data = resp.get("data") or {}

            if not isinstance(data, dict):
                messagebox.showerror("Review", "La respuesta del backend no es válida.")
                return

            data["id"] = record_id

            self.destroy()

            form = VesselConditionSurveyForm(
                self.master,
                usuario=self.usuario,
                rol=getattr(self.master, "rol", None)
            )

            form.load_record(data, from_review=True)

        except Exception as e:

            messagebox.showerror("Error", str(e))


    # =========================================================
    # CHANGE STATUS
    # =========================================================

    def _change_status(self, new_status):

        record_id = self._get_selected_record_id()

        if not record_id:
            messagebox.showwarning("Status", "Selecciona un reporte.")
            return

        try:

            update_vessel_condition_survey_api(
                record_id,
                {"status": new_status}
            )

            messagebox.showinfo("OK", "Estado actualizado.")

            self._on_search()

        except Exception as e:

            messagebox.showerror("Error", str(e))


    # =========================================================
    # GENERATE WORD
    # =========================================================

    def _generate_word(self):

        sel = self.tree.selection()

        if not sel:

            messagebox.showwarning(
                "Word",
                "Selecciona un reporte."
            )
            return

        try:

            item = self.tree.item(sel[0])

            record_id = item["values"][0]

            temp_path = download_vessel_condition_survey_word(record_id)

            from tkinter import filedialog
            import shutil

            save_path = filedialog.asksaveasfilename(
                title="Guardar reporte Word",
                defaultextension=".docx",
                filetypes=[("Word Document", "*.docx")],
                initialfile=f"Vessel_Condition_Survey_{record_id}.docx"
            )

            if not save_path:
                return

            shutil.copy(temp_path, save_path)

            messagebox.showinfo(
                "OK",
                "Reporte guardado correctamente."
            )

        except Exception as e:

            messagebox.showerror(
                "Error",
                str(e)
            )


    def _get_selected_record_id(self):

        sel = self.tree.selection()

        if not sel:
            return None

        item = self.tree.item(sel[0])

        try:
            return int(item["values"][0])
        except Exception:
            return None


    # =========================================================
    # FINAL REPORT POPUP
    # =========================================================

    def _open_final_report_popup(self):

        sel = self.tree.selection()

        if not sel:

            messagebox.showwarning(
                "Informe Final",
                "Selecciona un reporte."
            )
            return

        try:

            item = self.tree.item(sel[0])

            record_id = item["values"][0]

            PopupPDFMerge(
                self,
                record_id
            )

        except Exception as e:

            messagebox.showerror(
                "Error",
                str(e)
            )
