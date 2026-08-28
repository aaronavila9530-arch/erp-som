import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from api_client import (
    get_vessel_grain_sampling_list_api,
    get_vessel_grain_sampling_by_id_api,
    generate_grain_sampling_word_api
)

from Modulos.Informes.popup.popup_vessel_grain_sampling_preview import (
    PopupVesselGrainSamplingPreview
)

from desktop_services.word_pdf_service import convert_word_to_pdf
from Modulos.Informes.date_utils import to_long_english_date

class VesselGrainSamplingTable(ttk.Frame):

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
            text="Vessel Grain Sampling Reports",
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

        # ---------------- ACTIONS MENU ----------------
        self.actions_menu = tk.Menu(self, tearoff=0)

        self.actions_menu.add_command(
            label="🔍 Review",
            command=self._review_selected
        )

        self.actions_menu.add_separator()

        self.actions_menu.add_command(
            label="📄 Export Word",
            command=self._export_word_selected
        )

        self.actions_menu.add_separator()

        self.actions_menu.add_command(
            label="✅ Approve",
            command=self._approve_report
        )

        self.actions_menu.add_command(
            label="❌ Reject",
            command=lambda: self._change_status("Rejected")
        )

        self.actions_menu.add_separator()

        self.actions_menu.add_command(
            label="📝 Crear Informe Final",
            command=self._create_final_report
        )

    # =========================================================
    # TABLE
    # =========================================================
    def _build_table(self, parent):

        columns = (
            "id",
            "cert_no",
            "client",
            "vessel",
            "date",
            "total"
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
            "client": "Client",
            "vessel": "Vessel",
            "date": "Date",
            "total": "Total MT"
        }

        widths = {
            "id": 70,
            "cert_no": 160,
            "client": 200,
            "vessel": 200,
            "date": 120,
            "total": 120
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

        self.tree.bind("<Double-1>", lambda e: self._review_selected())

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
    # SEARCH
    # =========================================================
    def _on_search(self):

        try:
            self.lbl_info.config(text="Buscando...")
            self.update_idletasks()

            resp = get_vessel_grain_sampling_list_api()

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
                        "client": r.get("requested_by"),
                        "vessel": r.get("vessel_name"),
                        "date": to_long_english_date(r.get("place_date")),
                        "total": r.get("products_total")
                    }

                    normalized.append(record)
                    self._data_map[str(r.get("id"))] = record

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
                    r.get("client"),
                    r.get("vessel"),
                    to_long_english_date(r.get("date")),
                    r.get("total")
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

            # --- Export Word ---
            self.actions_menu.add_command(
                label="📄 Export Word",
                command=self._export_word_selected
            )

            self.actions_menu.add_separator()

            # --- Approve / Reject ---
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
                    command=self._approve_report
                )
                self.actions_menu.add_command(
                    label="❌ Reject",
                    command=lambda: self._change_status("Rejected")
                )

            self.actions_menu.add_separator()

            # --- Final Report ---
            self.actions_menu.add_command(
                label="📝 Crear Informe Final",
                command=self._create_final_report
            )

            # ==================================================
            # 📍 MOSTRAR MENU
            # ==================================================
            x = self.btn_actions.winfo_rootx()
            y = self.btn_actions.winfo_rooty() + self.btn_actions.winfo_height()

            self.actions_menu.tk_popup(x, y)

        finally:
            self.actions_menu.grab_release()

    def _review_selected(self):
        rid = self._get_selected_id()
        if not rid:
            messagebox.showwarning("Review", "Selecciona un reporte.")
            return

        PopupVesselGrainSamplingPreview(
            parent=self,
            report_id=int(rid)
        )

    # =========================================================
    # EXPORT WORD
    # =========================================================
    def _export_word_selected(self):

        rid = self._get_selected_id()
        if not rid:
            messagebox.showwarning(
                "Export Word",
                "Selecciona un reporte."
            )
            return

        try:
            # 🔥 Llamada al backend
            resp = generate_grain_sampling_word_api(int(rid))

            file_path = filedialog.asksaveasfilename(
                defaultextension=".docx",
                filetypes=[("Word Document", "*.docx")],
                initialfile=f"Grain_Sampling_{rid}.docx"
            )

            if not file_path:
                return

            # 🔥 Guardar archivo binario
            with open(file_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            messagebox.showinfo(
                "Export Word",
                "Documento generado correctamente."
            )

        except Exception as e:
            messagebox.showerror(
                "Export Error",
                str(e)
            )

    def _change_status(self, new_status):
        rid = self._get_selected_id()
        if not rid:
            messagebox.showwarning("Status", "Selecciona un reporte.")
            return

        messagebox.showinfo(
            "Status",
            f"Aquí debes conectar endpoint PUT para cambiar a {new_status}.\nReport ID: {rid}"
        )

    # =========================================================
    # CREATE FINAL REPORT (POPUP)
    # =========================================================
    def _create_final_report(self):

        rid = self._get_selected_id()
        if not rid:
            messagebox.showwarning(
                "Informe Final",
                "Selecciona un reporte."
            )
            return

        from Modulos.Informes.popup.popup_vessel_final_report import (
            PopupVesselFinalReport
        )

        PopupVesselFinalReport(
            parent=self,
            report_id=int(rid)
        )

    # =========================================================
    # APPROVE + GENERATE PDF (FRONTEND WORD ENGINE)
    # =========================================================
    def _approve_report(self):

        rid = self._get_selected_id()
        if not rid:
            messagebox.showwarning(
                "Approve",
                "Selecciona un reporte."
            )
            return

        confirm = messagebox.askyesno(
            "Confirm",
            "¿Desea aprobar el informe y generar el PDF?"
        )

        if not confirm:
            return

        try:
            # --------------------------------------------------
            # 1️⃣ Cambiar status en backend
            # --------------------------------------------------
            from api_client import approve_vessel_grain_sampling_api

            approve_vessel_grain_sampling_api(int(rid))

            # --------------------------------------------------
            # 2️⃣ Generar WORD desde backend
            # --------------------------------------------------
            resp = generate_grain_sampling_word_api(int(rid))

            import tempfile
            import os

            temp_dir = tempfile.gettempdir()
            temp_word_path = os.path.join(
                temp_dir,
                f"Grain_Sampling_{rid}.docx"
            )

            # Guardar Word temporal
            with open(temp_word_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            # --------------------------------------------------
            # 3️⃣ Convertir Word a PDF usando Word real
            # --------------------------------------------------
            pdf_temp_path = convert_word_to_pdf(temp_word_path)

            # --------------------------------------------------
            # 4️⃣ Mostrar Save As para PDF final
            # --------------------------------------------------
            final_path = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF File", "*.pdf")],
                initialfile=f"Grain_Sampling_{rid}.pdf"
            )

            if not final_path:
                return

            # Copiar PDF final
            import shutil
            shutil.copy(pdf_temp_path, final_path)

            messagebox.showinfo(
                "Success",
                "Informe aprobado y PDF generado correctamente."
            )

            # --------------------------------------------------
            # 5️⃣ Refrescar tabla
            # --------------------------------------------------
            self._on_search()

            # --------------------------------------------------
            # 6️⃣ Limpieza archivos temporales
            # --------------------------------------------------
            try:
                os.remove(temp_word_path)
                os.remove(pdf_temp_path)
            except Exception:
                pass

        except Exception as e:
            messagebox.showerror("Error", str(e))


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
