import tkinter as tk
from tkinter import ttk, messagebox

from api_client import (
    get_vessel_truck_supervision_list_api,
    update_vessel_truck_supervision_api,
    approve_vessel_truck_supervision_api
)

from tkinter import filedialog
from Modulos.Informes.date_utils import to_long_english_date


class VesselTruckSupervisionTable(ttk.Frame):

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
            text="Vessel Truck Supervision Reports",
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

        self.actions_menu.add_command(
            label="✅ Approve",
            command=self._approve_selected
        )

        self.actions_menu.add_command(
            label="❌ Reject",
            command=lambda: self._change_status("Rejected")
        )

        self.actions_menu.add_separator()

        self.actions_menu.add_command(
            label="📄 Crear Informe Final",
            command=self._open_final_report_popup
        )

    # =========================================================
    # TABLE
    # =========================================================
    def _build_table(self, parent):

        columns = (
            "id",
            "cert_no",
            "vessel",
            "port",
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
            "cert_no": "Cert No",
            "vessel": "Vessel",
            "port": "Port",
            "date": "Report Date",
            "status": "Status"
        }

        widths = {
            "id": 70,
            "cert_no": 150,
            "vessel": 200,
            "port": 150,
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
    # SEARCH (GET)
    # =========================================================
    def _on_search(self):

        try:
            self.lbl_info.config(text="Buscando...")
            self.update_idletasks()

            resp = get_vessel_truck_supervision_list_api()

            if not resp.get("success"):
                self._data_all = []
                self._data_map = {}
            else:
                rows = resp.get("data", [])

                normalized = []

                for r in rows:
                    record = {
                        "id": r.get("id"),
                        "cert_no": r.get("cert_no"),
                        "vessel": r.get("vessel_name"),
                        "port": r.get("port"),
                        "date": to_long_english_date(r.get("report_date")),
                        "status": r.get("status")
                    }

                    normalized.append(record)
                    self._data_map[str(r.get("id"))] = r

                normalized.sort(
                    key=lambda x: str(x.get("id")),
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
            self.tree.insert(
                "",
                "end",
                iid=str(r["id"]),
                values=(
                    r.get("id"),
                    r.get("cert_no"),
                    r.get("vessel"),
                    r.get("port"),
                    to_long_english_date(r.get("date")),
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

            # --- Approve ---
            if is_restricted:
                self.actions_menu.add_command(
                    label="✅ Approve",
                    state="disabled"
                )
            else:
                self.actions_menu.add_command(
                    label="✅ Approve",
                    command=self._approve_selected
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

            # --- Final Report (SIEMPRE permitido) ---
            self.actions_menu.add_command(
                label="📄 Crear Informe Final",
                command=self._open_final_report_popup
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
    # REVIEW (OPEN FORM + GET DATA)
    # =========================================================
    def _review_selected(self):

        rid = self._get_selected_id()

        if not rid:
            messagebox.showwarning(
                "Review",
                "Selecciona un reporte."
            )
            return

        try:

            from Modulos.Informes.vessel_truck_supervision.vessel_truck_supervision_form import (
                VesselTruckSupervisionForm
            )

            # destruir vista actual
            for widget in self.master.winfo_children():
                widget.destroy()

            form = VesselTruckSupervisionForm(self.master, mode="review")

            form.load_report(int(rid))

            form.pack(fill="both", expand=True)

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo abrir el review:\n{e}"
            )


    # =========================================================
    # APPROVE (GENERATE PDF + SAVE AS) — GRAIN STYLE
    # =========================================================
    def _approve_selected(self):

        rid = self._get_selected_id()

        if not rid:
            messagebox.showwarning(
                "Approve",
                "Selecciona un reporte."
            )
            return

        confirm = messagebox.askyesno(
            "Confirm",
            "¿Desea aprobar este informe y generar el PDF?"
        )

        if not confirm:
            return

        try:

            self.lbl_info.config(text="Generando PDF...")
            self.update_idletasks()

            # -------------------------------------------------
            # 1️⃣ Llamar backend
            # -------------------------------------------------
            result = approve_vessel_truck_supervision_api(int(rid))

            if not result.get("success"):
                messagebox.showerror(
                    "Error",
                    result.get("message", "Error desconocido.")
                )
                return

            pdf_bytes = result.get("file_bytes")

            # -------------------------------------------------
            # 2️⃣ SAVE AS (SIN TEMPORAL)
            # -------------------------------------------------
            save_path = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf")],
                initialfile=f"Truck_Supervision_{rid}.pdf"
            )

            if not save_path:
                return

            with open(save_path, "wb") as f:
                f.write(pdf_bytes)

            messagebox.showinfo(
                "Success",
                "Informe aprobado y PDF generado correctamente."
            )

            # -------------------------------------------------
            # 3️⃣ Refresh
            # -------------------------------------------------
            self._on_search()

        except Exception as e:
            messagebox.showerror("Error", str(e))


    # =========================================================
    # FINAL REPORT (OPEN PRESENTATION POPUP)
    # =========================================================
    def _open_final_report_popup(self):

        rid = self._get_selected_id()

        if not rid:
            messagebox.showwarning(
                "Informe Final",
                "Selecciona un reporte."
            )
            return

        try:
            from Modulos.Informes.vessel_truck_supervision.popup_truck_supervision_final_report import (
                PopupTruckSupervisionFinalReport
            )

            PopupTruckSupervisionFinalReport(
                parent=self,
                report_id=int(rid)
            )

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo abrir el generador de informe final:\n{e}"
            )




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
