import tkinter as tk
import webbrowser
from tkinter import ttk, messagebox

from api_client import get_accounting_legal_library_api


class PopupLegalLibrary(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.rows = []
        self.selected_url = ""
        self.title("Biblioteca legal Costa Rica")
        self.geometry("1180x700")
        self.minsize(980, 600)
        self.transient(parent)
        self.grab_set()
        self.category_var = tk.StringVar(value="TODOS")
        self.search_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Cargando biblioteca legal...")
        self._build()
        self.after(120, self._load)

    def _build(self):
        header = ttk.Frame(self, padding=10)
        header.pack(fill="x")
        ttk.Label(header, text="Categoria").pack(side="left")
        self.category = ttk.Combobox(header, textvariable=self.category_var, values=["TODOS"], width=18, state="readonly")
        self.category.pack(side="left", padx=6)
        self.category.bind("<<ComboboxSelected>>", lambda _e: self._load())
        ttk.Label(header, text="Buscar").pack(side="left", padx=(14, 0))
        entry = ttk.Entry(header, textvariable=self.search_var, width=36)
        entry.pack(side="left", padx=6)
        entry.bind("<Return>", lambda _e: self._load())
        ttk.Button(header, text="Buscar", command=self._load).pack(side="left", padx=4)
        ttk.Button(header, text="Limpiar", command=self._clear).pack(side="left", padx=4)
        ttk.Button(header, text="Abrir fuente oficial", command=self._open_source).pack(side="right")

        note = ttk.Label(
            self,
            text="Referencia operativa. Para texto vigente, reformas y versiones oficiales, abrir siempre la fuente SCIJ/PGR o Hacienda.",
            foreground="#555",
            anchor="w",
        )
        note.pack(fill="x", padx=12, pady=(0, 6))

        body = ttk.Panedwindow(self, orient="horizontal")
        body.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        list_frame = ttk.LabelFrame(body, text="Normativa", padding=6)
        detail_frame = ttk.LabelFrame(body, text="Detalle ejecutivo", padding=6)
        body.add(list_frame, weight=3)
        body.add(detail_frame, weight=2)

        cols = ("category", "code", "title", "type", "issuer")
        self.tree = ttk.Treeview(list_frame, columns=cols, show="headings", selectmode="browse")
        for col, label, width in (
            ("category", "Categoria", 95),
            ("code", "Codigo", 170),
            ("title", "Norma / Codigo", 330),
            ("type", "Tipo", 130),
            ("issuer", "Emisor", 190),
        ):
            self.tree.heading(col, text=label)
            self.tree.column(col, width=width, anchor="w")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._show_selected)
        self.tree.bind("<Double-1>", lambda _e: self._open_source())

        self.detail = tk.Text(detail_frame, wrap="word", height=20)
        self.detail.pack(fill="both", expand=True)
        self.detail.configure(state="disabled")

        footer = ttk.Frame(self, padding=(10, 0, 10, 10))
        footer.pack(fill="x")
        ttk.Label(footer, textvariable=self.status_var).pack(side="left")
        ttk.Button(footer, text="Cerrar", command=self.destroy).pack(side="right")

    def _load(self):
        try:
            data = get_accounting_legal_library_api(
                category=self.category_var.get(),
                query=self.search_var.get().strip(),
            )
        except Exception as exc:
            messagebox.showerror("Biblioteca legal", f"No se pudo cargar:\n{exc}", parent=self)
            return
        categories = ["TODOS"] + data.get("categories", [])
        self.category.configure(values=categories)
        if self.category_var.get() not in categories:
            self.category_var.set("TODOS")
        self.rows = data.get("data") or []
        self.tree.delete(*self.tree.get_children())
        for idx, row in enumerate(self.rows):
            self.tree.insert(
                "",
                "end",
                iid=str(idx),
                values=(
                    row.get("category"),
                    row.get("code"),
                    row.get("title"),
                    row.get("norm_type"),
                    row.get("issuer"),
                ),
            )
        self.status_var.set(f"{len(self.rows)} referencias legales cargadas")
        if self.rows:
            self.tree.selection_set("0")
            self._show_selected()
        else:
            self._set_detail("Sin resultados.")

    def _clear(self):
        self.category_var.set("TODOS")
        self.search_var.set("")
        self._load()

    def _show_selected(self, _event=None):
        selected = self.tree.selection()
        if not selected:
            return
        row = self.rows[int(selected[0])]
        self.selected_url = row.get("official_url") or ""
        text = (
            f"{row.get('title')}\n"
            f"{'-' * 80}\n"
            f"Codigo ERP: {row.get('code')}\n"
            f"Categoria: {row.get('category')}\n"
            f"Tipo: {row.get('norm_type')}\n"
            f"Numero: {row.get('number')}\n"
            f"Emisor: {row.get('issuer')}\n"
            f"Fecha: {row.get('date') or '-'}\n\n"
            f"Resumen operativo:\n{row.get('summary')}\n\n"
            f"Relevancia para ERP-SOM:\n{row.get('erp_relevance')}\n\n"
            f"Palabras clave:\n{', '.join(row.get('keywords') or [])}\n\n"
            f"Fuente oficial:\n{self.selected_url}"
        )
        self._set_detail(text)

    def _set_detail(self, text):
        self.detail.configure(state="normal")
        self.detail.delete("1.0", "end")
        self.detail.insert("1.0", text)
        self.detail.configure(state="disabled")

    def _open_source(self):
        if not self.selected_url:
            messagebox.showwarning("Biblioteca legal", "Seleccione una norma con fuente oficial.", parent=self)
            return
        webbrowser.open(self.selected_url)
