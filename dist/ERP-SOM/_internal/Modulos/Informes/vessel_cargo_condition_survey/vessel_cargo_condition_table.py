import tkinter as tk
from tkinter import ttk, messagebox

from api_client import (
    get_all_vessel_cargo_condition_api,
    get_vessel_cargo_condition_by_id_api,
    update_vessel_cargo_condition_api
)


import os
from tkinter import filedialog

from api_client import generate_vessel_cargo_condition_word_api

from Modulos.Informes.vessel_cargo_condition_survey.popup_vessel_cargo_condition_word import (
    PopupVesselCargoConditionWord
)



class VesselCargoConditionTable(ttk.Frame):

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

        # evitar crash si _render_page corre antes de crear paginación
        self.lbl_page = None

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
            text="Cargo Condition Surveys",
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
            label="❌ Rechazar",
            command=lambda: self._change_status("Rejected")
        )

        self.actions_menu.add_command(
            label="✅ Aprobar",
            command=lambda: self._change_status("Approved")
        )

        self.actions_menu.add_separator()

        self.actions_menu.add_command(
            label="📄 Generar Word",
            command=self._generate_word_selected
        )

        self.actions_menu.add_command(
            label="📑 Generar Informe Final",
            command=self._generate_final_report_selected
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
            "id": "ID",
            "report_number": "Report No",
            "vessel": "Vessel",
            "port": "Port",
            "country": "Country",
            "date": "Date",
            "status": "Status"
        }

        widths = {
            "id": 90,
            "report_number": 150,
            "vessel": 220,
            "port": 160,
            "country": 150,
            "date": 120,
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

            resp = get_all_vessel_cargo_condition_api()

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

        self.tree.delete(*self.tree.get_children())

        total = len(self._data_all or [])

        if total == 0:
            if self.lbl_page:
                self.lbl_page.config(text="Page 0 / 0")
            self.lbl_info.config(text="Sin resultados")
            return

        total_pages = (total + self.PAGE_SIZE - 1) // self.PAGE_SIZE

        if self._page < 1:
            self._page = 1
        if self._page > total_pages:
            self._page = total_pages

        start = (self._page - 1) * self.PAGE_SIZE
        end = start + self.PAGE_SIZE

        for r in (self._data_all[start:end] or []):

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

        if self.lbl_page:
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
                    label="❌ Rechazar",
                    state="disabled"
                )
                self.actions_menu.add_command(
                    label="✅ Aprobar",
                    state="disabled"
                )
            else:
                self.actions_menu.add_command(
                    label="❌ Rechazar",
                    command=lambda: self._change_status("Rejected")
                )
                self.actions_menu.add_command(
                    label="✅ Aprobar",
                    command=lambda: self._change_status("Approved")
                )

            self.actions_menu.add_separator()

            # --- Word ---
            self.actions_menu.add_command(
                label="📄 Generar Word",
                command=self._generate_word_selected
            )

            # --- Final Report ---
            self.actions_menu.add_command(
                label="📑 Generar Informe Final",
                command=self._generate_final_report_selected
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
    # REVIEW REPORT
    # =========================================================
    def _review_selected(self):

        report_id = self._get_selected_id()

        if not report_id:
            messagebox.showwarning(
                "Review",
                "Selecciona un reporte."
            )
            return

        try:

            from Modulos.Informes.vessel_cargo_condition_survey.vessel_cargo_condition_survey_form import (
                VesselCargoConditionSurveyForm
            )

            resp = get_vessel_cargo_condition_by_id_api(report_id)

            if not resp.get("success"):
                raise Exception(resp.get("error"))

            data = resp.get("data") or {}

            # cerrar tabla actual
            self.destroy()

            # abrir form
            form = VesselCargoConditionSurveyForm(
                self.master,
                usuario=self.usuario,
                rol=getattr(self.master, "rol", None)
            )

            # cargar datos completos
            form.load_record(data)

        except Exception as e:
            messagebox.showerror("Error", str(e))


    # =========================================================
    # CHANGE STATUS
    # =========================================================
    def _change_status(self, new_status: str):

        report_id = self._get_selected_id()

        if not report_id:
            messagebox.showwarning("Status", "Selecciona un reporte.")
            return

        confirm = messagebox.askyesno(
            "Confirmar",
            f"¿Cambiar estado a '{new_status}'?"
        )

        if not confirm:
            return

        try:
            result = update_vessel_cargo_condition_api(
                report_id,
                {"status": new_status}
            )

            if not result.get("success"):
                raise Exception(result.get("error"))

            messagebox.showinfo("OK", "Estado actualizado.")
            self._on_search()

        except Exception as e:
            messagebox.showerror("Error", str(e))

    # =========================================================
    # GENERATE WORD
    # =========================================================
    def _generate_word_selected(self):

        report_id = self._get_selected_id()

        if not report_id:
            messagebox.showwarning("Word", "Selecciona un reporte.")
            return

        try:
            save_path = filedialog.asksaveasfilename(
                defaultextension=".docx",
                filetypes=[("Word File", "*.docx")],
                initialfile=f"Cargo_Condition_{report_id}.docx"
            )

            if not save_path:
                return

            resp = generate_vessel_cargo_condition_word_api(
                report_id,
                save_path
            )

            if not resp.get("success"):
                raise Exception(resp.get("error"))

            messagebox.showinfo("OK", "Word generado correctamente.")

            os.startfile(save_path)

        except Exception as e:
            messagebox.showerror("Error", str(e))


    # =========================================================
    # GENERATE FINAL REPORT (POPUP)
    # =========================================================
    def _generate_final_report_selected(self):

        report_id = self._get_selected_id()

        if not report_id:
            messagebox.showwarning(
                "Informe Final",
                "Selecciona un reporte."
            )
            return

        PopupVesselCargoConditionWord(
            self,
            report_id
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