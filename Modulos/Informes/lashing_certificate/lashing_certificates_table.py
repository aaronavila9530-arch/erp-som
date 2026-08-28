import tkinter as tk
from tkinter import ttk, messagebox

from api_client import (
    get_lashing_certificates_api,
    get_lashing_certificate_api,
    update_lashing_certificate_api,
    generate_lashing_certificate_word_api,
    generate_lashing_certificate_pdf_api
)


class LashingCertificatesTable(ttk.Frame):

    PAGE_SIZE = 50

    def __init__(self, parent):
        super().__init__(parent)

        # 🔒 Usuario heredado del parent (blindado)
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
            text="Lashing Certificates",
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
            command=lambda: self._change_status("Reject")
        )

        self.actions_menu.add_command(
            label="✅ Approve",
            command=lambda: self._change_status("Approve")
        )

        self.actions_menu.add_separator()

        self.actions_menu.add_command(
            label="📄 Crear Word",
            command=self._generate_word
        )

        self.actions_menu.add_command(
            label="📑 Crear Certificado Final",
            command=self._generate_pdf
        )


    # =========================================================
    # TABLE
    # =========================================================

    def _build_table(self, parent):

        columns = (
            "id",
            "report_no",
            "customer",
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
            "report_no":"Report No",
            "customer":"Customer",
            "port":"Port",
            "country":"Country",
            "date":"Date",
            "status":"Status"
        }

        widths = {
            "id":80,
            "report_no":160,
            "customer":220,
            "port":150,
            "country":150,
            "date":180,
            "status":140
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

            rows = get_lashing_certificates_api()

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
                    r.get("report_no") or "",
                    r.get("customer") or "",
                    r.get("port") or "",
                    r.get("country") or "",
                    r.get("date") or "",
                    r.get("status") or ""
                )
            )


    # =========================================================
    # ACTIONS
    # =========================================================

    def _get_selected_id(self):

        sel = self.tree.selection()

        if not sel:
            return None

        item = self.tree.item(sel[0])

        return item["values"][0]


    def _open_actions_menu(self):

        record_id = self._get_selected_id()

        if not record_id:
            messagebox.showwarning("Acciones","Selecciona un registro.")
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
                    command=lambda: self._change_status("Reject")
                )
                self.actions_menu.add_command(
                    label="✅ Approve",
                    command=lambda: self._change_status("Approve")
                )

            self.actions_menu.add_separator()

            # --- Word ---
            self.actions_menu.add_command(
                label="📄 Crear Word",
                command=self._generate_word
            )

            # --- PDF ---
            self.actions_menu.add_command(
                label="📑 Crear Certificado Final",
                command=self._generate_pdf
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

        record_id = self._get_selected_id()

        if not record_id:

            messagebox.showwarning("Review","Selecciona un registro.")
            return

        try:

            from Modulos.Informes.lashing_certificate.lashing_certificate_form import LashingCertificateForm

            data = get_lashing_certificate_api(record_id)

            self.destroy()

            form = LashingCertificateForm(self.master)

            form.load_record(record_id)

            form.set_edit_mode(record_id)

        except Exception as e:

            messagebox.showerror("Error",str(e))


    # =========================================================
    # GENERATE WORD
    # =========================================================

    def _generate_word(self):

        record_id = self._get_selected_id()

        if not record_id:

            messagebox.showwarning("ERP-SOM","Selecciona un registro.")
            return

        try:

            from tkinter import filedialog

            file_bytes = generate_lashing_certificate_word_api(record_id)

            filepath = filedialog.asksaveasfilename(
                title="Guardar Word",
                defaultextension=".docx",
                initialfile=f"lashing_certificate_{record_id}.docx",
                filetypes=[("Word Document","*.docx")]
            )

            if not filepath:
                return

            with open(filepath,"wb") as f:
                f.write(file_bytes)

            messagebox.showinfo("ERP-SOM","Word generado correctamente.")

        except Exception as e:

            messagebox.showerror("ERP-SOM",str(e))


    # =========================================================
    # GENERATE PDF
    # =========================================================

    def _generate_pdf(self):

        record_id = self._get_selected_id()

        if not record_id:

            messagebox.showwarning("ERP-SOM","Selecciona un registro.")
            return

        try:

            from tkinter import filedialog

            pdf_bytes = generate_lashing_certificate_pdf_api(record_id)

            filepath = filedialog.asksaveasfilename(
                title="Guardar Certificado Final",
                defaultextension=".pdf",
                initialfile=f"lashing_certificate_{record_id}.pdf",
                filetypes=[("PDF Document","*.pdf")]
            )

            if not filepath:
                return

            with open(filepath,"wb") as f:
                f.write(pdf_bytes)

            messagebox.showinfo(
                "ERP-SOM",
                "Certificado final generado correctamente."
            )

        except Exception as e:

            messagebox.showerror("ERP-SOM",str(e))


    # =========================================================
    # CHANGE STATUS
    # =========================================================

    def _change_status(self, action):

        record_id = self._get_selected_id()

        if not record_id:

            messagebox.showwarning("Status","Selecciona un registro.")
            return

        try:

            update_lashing_certificate_api(
                record_id,
                {"status": action}
            )

            messagebox.showinfo("OK","Estado actualizado.")

            self._on_search()

        except Exception as e:

            messagebox.showerror("Error",str(e))