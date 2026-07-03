import tkinter as tk
from tkinter import ttk, messagebox

import api_client


class LograReportsTable(ttk.Frame):
    PAGE_SIZE = 50

    def __init__(self, parent):
        super().__init__(parent)
        self.rows = []
        self.row_map = {}
        self._build_ui()
        self._load()

    def _build_ui(self):
        self.pack(fill="both", expand=True)
        top = ttk.Frame(self)
        top.pack(fill="x", padx=10, pady=10)

        ttk.Button(top, text="Buscar", command=self._load).pack(side="left")
        ttk.Button(top, text="Revisar", command=self._review_selected).pack(side="left", padx=6)
        ttk.Button(top, text="Ver adjunto", command=self._open_selected_attachment).pack(side="left")
        self.info_label = ttk.Label(top, text="")
        self.info_label.pack(side="right")

        columns = ("id", "title", "status", "agenda", "attachments", "updated_at")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=12)
        headers = {
            "id": "ID",
            "title": "Titulo",
            "status": "Status",
            "agenda": "Agenda",
            "attachments": "Adjuntos",
            "updated_at": "Actualizado",
        }
        widths = {
            "id": 70,
            "title": 360,
            "status": 120,
            "agenda": 90,
            "attachments": 90,
            "updated_at": 180,
        }
        for col in columns:
            self.tree.heading(col, text=headers[col])
            self.tree.column(col, width=widths[col], anchor="w")
        self.tree.pack(fill="both", expand=True, padx=10, pady=(0, 8), side="top")
        self.tree.bind("<Double-1>", lambda e: self._review_selected())

    def _load(self):
        resp = api_client.list_logra_reports_api()
        self.rows = resp.get("data") or []
        self.row_map = {str(row.get("id")): row for row in self.rows}
        for item in self.tree.get_children():
            self.tree.delete(item)
        for row in self.rows:
            agenda_count = len(row.get("agenda_items") or [])
            self.tree.insert(
                "",
                "end",
                iid=str(row.get("id")),
                values=(
                    row.get("id"),
                    row.get("title") or "",
                    row.get("status") or "",
                    agenda_count,
                    row.get("attachment_count") or 0,
                    str(row.get("updated_at") or ""),
                ),
            )
        self.info_label.config(text=f"Resultados: {len(self.rows)}")

    def _selected_report_id(self):
        selected = self.tree.selection()
        return int(selected[0]) if selected else None

    def _review_selected(self):
        report_id = self._selected_report_id()
        if not report_id:
            messagebox.showwarning("LOGRA", "Selecciona un reporte LOGRA.")
            return
        from Modulos.Informes.logra_questionnaires_form import LograQuestionnairesForm

        for widget in self.master.winfo_children():
            widget.destroy()
        form = LograQuestionnairesForm(self.master, review_mode=True)
        form.load_report(report_id)

    def _open_selected_attachment(self):
        report_id = self._selected_report_id()
        if not report_id:
            messagebox.showwarning("LOGRA", "Selecciona un reporte LOGRA.")
            return
        resp = api_client.list_logra_attachments_api(report_id)
        attachments = resp.get("data") or []
        if not attachments:
            messagebox.showinfo("LOGRA", "Este reporte no tiene adjuntos.")
            return
        if len(attachments) == 1:
            self._open_attachment_id(attachments[0].get("id"))
            return
        PopupLograAttachments(self, attachments, self._open_attachment_id)

    def _open_attachment_id(self, attachment_id):
        resp = api_client.open_logra_attachment_api(int(attachment_id))
        if not resp.get("success"):
            messagebox.showerror("LOGRA", f"No se pudo abrir el adjunto:\n{resp.get('error') or resp}")


class PopupLograAttachments(tk.Toplevel):
    def __init__(self, parent, attachments, on_open):
        super().__init__(parent)
        self.attachments = attachments
        self.on_open = on_open
        self.title("Adjuntos LOGRA")
        self.geometry("780x320")
        self.transient(parent)
        self.grab_set()
        self._build_ui()

    def _build_ui(self):
        root = ttk.Frame(self, padding=10)
        root.pack(fill="both", expand=True)
        root.rowconfigure(0, weight=1)
        root.columnconfigure(0, weight=1)

        self.tree = ttk.Treeview(
            root,
            columns=("id", "filename", "question", "created_at"),
            show="headings",
            height=8,
        )
        for col, title, width in [
            ("id", "ID", 60),
            ("filename", "Archivo", 320),
            ("question", "Pregunta", 180),
            ("created_at", "Fecha", 180),
        ]:
            self.tree.heading(col, text=title)
            self.tree.column(col, width=width, anchor="w")
        self.tree.grid(row=0, column=0, sticky="nsew")
        for att in self.attachments:
            self.tree.insert(
                "",
                "end",
                iid=str(att.get("id")),
                values=(
                    att.get("id"),
                    att.get("original_filename") or "",
                    att.get("item_key") or "",
                    str(att.get("created_at") or ""),
                ),
            )
        self.tree.bind("<Double-1>", lambda e: self._open())

        actions = ttk.Frame(root)
        actions.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        ttk.Button(actions, text="Cerrar", command=self.destroy).pack(side="right")
        ttk.Button(actions, text="Ver adjunto", command=self._open).pack(side="right", padx=6)

    def _open(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("LOGRA", "Selecciona un adjunto.")
            return
        self.on_open(int(selected[0]))
        self.destroy()
