import tkinter as tk
from tkinter import ttk, messagebox

from api_client import (
    get_crane_inspections_api,
    get_crane_inspection_api,
    update_crane_inspection_api,
    approve_crane_inspection_api
)


class CraneInspectionTable(ttk.Frame):

    PAGE_SIZE = 50

    # =========================================================
    # INIT
    # =========================================================

    def __init__(self, parent, usuario=None, rol=None):

        super().__init__(parent)

        self.parent = parent
        self.usuario = usuario
        self.rol = rol

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
            text="Crane Inspection Reports",
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

        container = ttk.Frame(self)
        container.pack(fill="both", expand=True, padx=10)

        self._build_table(container)

        pag = ttk.Frame(self)
        pag.pack(fill="x", padx=10, pady=10)

        self._build_pagination(pag)

        self.actions_menu = tk.Menu(self, tearoff=0)

        self.actions_menu.add_command(
            label="✏ Review",
            command=self._open_review
        )

        self.actions_menu.add_command(
            label="📄 Generate Word",
            command=self._generate_word
        )

        self.actions_menu.add_command(
            label="📑 Crear Informe Final",
            command=self._open_final_report_popup
        )

        self.actions_menu.add_separator()


        self.actions_menu.add_command(
            label="❌ Reject",
            command=lambda: self._change_status("Rejected")
        )

        self.actions_menu.add_command(
            label="✅ Approve",
            command=self._approve_selected
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
            "report_date",
            "status",
            "created_at"
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
            "report_date": "Date",
            "status": "Status",
            "created_at": "Created"
        }

        widths = {
            "id": 80,
            "report_number": 150,
            "vessel": 220,
            "port": 150,
            "country": 150,
            "report_date": 120,
            "status": 150,
            "created_at": 180
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
    # SEARCH
    # =========================================================
    def _on_search(self):

        try:

            self.lbl_info.config(text="Buscando...")
            self.update_idletasks()

            resp = get_crane_inspections_api()

            # -------------------------------------------------
            # SI API FALLA → mostrar error real
            # -------------------------------------------------
            if not resp.get("success"):

                error = resp.get("error", "Unknown error")
                detail = resp.get("detail", "")

                messagebox.showerror(
                    "API Error",
                    f"{error}\n\n{detail}"
                )

                self._data_all = []
                self._render_page()
                return

            rows = resp.get("data", []) or []

            rows.sort(
                key=lambda x: x.get("id", 0),
                reverse=True
            )

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
                    r.get("report_date") or "",
                    r.get("status") or "",
                    r.get("created_at") or ""
                )
            )

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

        x = self.btn_actions.winfo_rootx()
        y = self.btn_actions.winfo_rooty() + self.btn_actions.winfo_height()

        self.actions_menu.tk_popup(x, y)

    # =========================================================
    # REVIEW
    # =========================================================
    def _open_review(self):

        report_id = self._get_selected_id()

        if not report_id:
            messagebox.showwarning(
                "Review",
                "Selecciona un reporte."
            )
            return

        try:

            resp = get_crane_inspection_api(report_id)

            if not isinstance(resp, dict):
                raise Exception("La respuesta del API no es válida.")

            if not resp.get("success"):
                raise Exception(
                    resp.get("error")
                    or resp.get("detail")
                    or "No se pudo cargar el reporte."
                )

            raw_data = resp.get("data")

            print("\n================ REVIEW DEBUG ================")
            print("report_id:", report_id)
            print("response keys:", list(resp.keys()))
            print("data type:", type(raw_data).__name__)

            if isinstance(raw_data, dict):
                print("crane1_remark_1:", raw_data.get("crane1_remark_1"))
                print("crane1_remark_2:", raw_data.get("crane1_remark_2"))
                print("recommendation_1:", raw_data.get("recommendation_1"))
                print("recommendation_2:", raw_data.get("recommendation_2"))
                print("grabs_condition_1:", raw_data.get("grabs_condition_1"))
                print("grabs_condition_2:", raw_data.get("grabs_condition_2"))
                print("conclusion_1:", raw_data.get("conclusion_1"))
                print("conclusion_2:", raw_data.get("conclusion_2"))
            else:
                print("raw_data:", raw_data)

            print("==============================================\n")

            from Modulos.Informes.crane_inspection.crane_inspection_form import CraneInspectionForm

            self.destroy()

            form = CraneInspectionForm(
                self.parent,
                usuario=self.usuario,
                rol=self.rol
            )

            form.load_record(resp)

        except Exception as e:

            messagebox.showerror(
                "Error",
                str(e)
            )

    # =========================================================
    # CHANGE STATUS
    # =========================================================

    def _change_status(self, new_status):

        report_id = self._get_selected_id()

        if not report_id:
            messagebox.showwarning("Status", "Selecciona un reporte.")
            return

        try:

            result = update_crane_inspection_api(
                report_id,
                {"status": new_status}
            )

            if not result.get("success"):
                raise Exception(result.get("error"))

            messagebox.showinfo("OK", "Estado actualizado.")

            self._on_search()

        except Exception as e:

            messagebox.showerror("Error", str(e))

    def _approve_selected(self):

        report_id = self._get_selected_id()

        if not report_id:
            messagebox.showwarning("Approve", "Selecciona un reporte.")
            return

        try:

            result = approve_crane_inspection_api(report_id)

            if not result.get("success"):
                raise Exception(result.get("error"))

            messagebox.showinfo("OK", "Reporte aprobado.")

            self._on_search()

        except Exception as e:

            messagebox.showerror("Error", str(e))


    # =========================================================
    # GENERATE WORD
    # =========================================================
    def _generate_word(self):

        report_id = self._get_selected_id()

        if not report_id:
            messagebox.showwarning(
                "Generate Word",
                "Selecciona un reporte."
            )
            return

        try:

            from api_client import generate_crane_inspection_word_api

            resp = generate_crane_inspection_word_api(report_id)

            if not resp.get("success"):
                raise Exception(resp.get("error") or "Failed to generate Word")

            file_bytes = resp.get("file_bytes")

            if not file_bytes:
                raise Exception("Empty Word file returned")

            from tkinter import filedialog

            path = filedialog.asksaveasfilename(
                title="Guardar Reporte Crane Inspection",
                defaultextension=".docx",
                filetypes=[("Word Document", "*.docx")]
            )

            if not path:
                return

            with open(path, "wb") as f:
                f.write(file_bytes)

            messagebox.showinfo(
                "Word generado",
                "El reporte Word fue generado correctamente."
            )

        except Exception as e:

            messagebox.showerror(
                "Generate Word Error",
                str(e)
            )



    # =========================================================
    # FINAL REPORT POPUP
    # =========================================================
    def _open_final_report_popup(self):

        report_id = self._get_selected_id()

        if not report_id:

            messagebox.showwarning(
                "Crear Informe Final",
                "Selecciona un reporte."
            )
            return

        try:

            from Modulos.Informes.crane_inspection.popup_crane_inspection_presentation import (
                PopupCraneInspectionPresentation
            )

            PopupCraneInspectionPresentation(
                self.parent,
                report_id
            )

        except Exception as e:

            messagebox.showerror(
                "Error",
                str(e)
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