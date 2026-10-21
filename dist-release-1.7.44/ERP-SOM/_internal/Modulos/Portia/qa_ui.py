import tkinter as tk
from tkinter import ttk

try:
    from backend_api.ai.som_portia_knowledge import SOM_QA
except Exception:
    SOM_QA = []


NAVY = "#003A75"
BG = "#F3F6FA"
CARD = "#FFFFFF"
BORDER = "#D8E0EA"
TEXT = "#172033"
MUTED = "#667085"


class QASomUI(tk.Frame):
    def __init__(self, parent, usuario=None, rol=None, on_back=None):
        super().__init__(parent, bg=BG)
        self.parent = parent
        self.usuario = usuario
        self.rol = rol
        self.on_back = on_back
        self.filtered = list(SOM_QA)
        self.selected_module = None

        self.pack(fill="both", expand=True)
        self._build_ui()
        self._render_modules()

    def _build_ui(self):
        header = tk.Frame(self, bg=NAVY, height=72)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="Q&A SOM",
            bg=NAVY,
            fg="white",
            font=("Segoe UI", 18, "bold"),
        ).pack(side="left", padx=22)

        if self.on_back:
            tk.Button(
                header,
                text="Volver",
                command=self.on_back,
                bg="#40617F",
                fg="white",
                activebackground=NAVY,
                activeforeground="white",
                relief="flat",
                padx=14,
                pady=7,
                font=("Segoe UI", 9, "bold"),
            ).pack(side="right", padx=16)

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=18, pady=16)
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=2)
        body.grid_columnconfigure(2, weight=3)
        body.grid_rowconfigure(1, weight=1)

        search_card = tk.Frame(body, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        search_card.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))

        tk.Label(search_card, text="Buscar en la base Q&A", bg=CARD, fg=TEXT, font=("Segoe UI", 11, "bold")).pack(side="left", padx=12, pady=10)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_card, textvariable=self.search_var, width=55)
        search_entry.pack(side="left", padx=8, pady=10)
        search_entry.bind("<KeyRelease>", lambda event: self._filter_rows())
        search_entry.bind("<Return>", lambda event: self._filter_rows())

        tk.Button(
            search_card,
            text="Buscar",
            command=self._filter_rows,
            bg=NAVY,
            fg="white",
            activebackground="#0057A8",
            activeforeground="white",
            relief="flat",
            padx=16,
            pady=6,
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left", padx=(6, 12), pady=10)

        tk.Button(
            search_card,
            text="Limpiar",
            command=self._clear_search,
            bg="#E8EEF5",
            fg=TEXT,
            activebackground="#D9E4EF",
            activeforeground=TEXT,
            relief="flat",
            padx=12,
            pady=6,
            font=("Segoe UI", 9),
        ).pack(side="left", padx=(0, 12), pady=10)

        modules = tk.Frame(body, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        modules.grid(row=1, column=0, sticky="nsew", padx=(0, 10))

        functions = tk.Frame(body, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        functions.grid(row=1, column=1, sticky="nsew", padx=(0, 10))

        right = tk.Frame(body, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        right.grid(row=1, column=2, sticky="nsew")

        tk.Label(modules, text="Modulos", bg=CARD, fg=TEXT, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=12, pady=(12, 8))

        self.module_tree = ttk.Treeview(modules, columns=("module", "count"), show="headings", height=18)
        self.module_tree.heading("module", text="Modulo")
        self.module_tree.heading("count", text="#")
        self.module_tree.column("module", width=150, anchor="w")
        self.module_tree.column("count", width=45, anchor="center")
        self.module_tree.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.module_tree.bind("<<TreeviewSelect>>", self._on_module_selected)

        tk.Label(functions, text="Funciones / paso a paso", bg=CARD, fg=TEXT, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=12, pady=(12, 8))

        self.tree = ttk.Treeview(functions, columns=("question",), show="headings")
        self.tree.heading("question", text="Pregunta")
        self.tree.column("question", width=420, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.tree.bind("<<TreeviewSelect>>", self._show_selected)

        tk.Label(right, text="Respuesta", bg=CARD, fg=TEXT, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=14, pady=(12, 8))
        self.answer = tk.Text(right, wrap="word", relief="flat", bg="white", fg=TEXT, font=("Segoe UI", 10), padx=12, pady=10)
        self.answer.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        self.answer.configure(state="disabled")

        tk.Label(
            right,
            text="Este modulo es la base de conocimiento funcional de SOM. PORTIA usa esta base como referencia consultiva.",
            bg=CARD,
            fg=MUTED,
            font=("Segoe UI", 9),
            wraplength=680,
            justify="left",
        ).pack(anchor="w", padx=14, pady=(0, 12))

    def _filter_rows(self):
        term = self.search_var.get().strip().lower()
        if not term:
            self.filtered = list(SOM_QA)
        else:
            self.filtered = [
                item for item in SOM_QA
                if term in item.get("category", "").lower()
                or term in item.get("question", "").lower()
                or term in item.get("answer", "").lower()
            ]
        self.selected_module = None
        self._render_modules()

    def _clear_search(self):
        self.search_var.set("")
        self._filter_rows()

    def _module_name(self, item):
        category = item.get("category", "General")
        return category.split(" - ", 1)[0].strip() or "General"

    def _modules(self):
        counts = {}
        for item in self.filtered:
            module = self._module_name(item)
            counts[module] = counts.get(module, 0) + 1
        preferred = [
            "General",
            "Dashboard",
            "Master Data",
            "Servicios",
            "Finanzas",
            "Comercial",
            "Informes",
            "HHRR",
            "PORTIA",
        ]
        ordered = [module for module in preferred if module in counts]
        ordered.extend(sorted(module for module in counts if module not in preferred))
        return [(module, counts[module]) for module in ordered]

    def _render_modules(self):
        self.module_tree.delete(*self.module_tree.get_children())
        modules = self._modules()
        for idx, (module, count) in enumerate(modules):
            self.module_tree.insert("", "end", iid=str(idx), values=(module, count))

        if modules:
            if self.selected_module not in {module for module, _ in modules}:
                self.selected_module = modules[0][0]
            selected_idx = next((str(i) for i, (module, _) in enumerate(modules) if module == self.selected_module), "0")
            self.module_tree.selection_set(selected_idx)
            self._render_rows()
        else:
            self.tree.delete(*self.tree.get_children())
            self._set_answer("No hay resultados para la busqueda.")

    def _on_module_selected(self, event=None):
        selected = self.module_tree.selection()
        if not selected:
            return
        values = self.module_tree.item(selected[0], "values")
        if not values:
            return
        self.selected_module = values[0]
        self._render_rows()

    def _items_for_selected_module(self):
        if not self.selected_module:
            return list(self.filtered)
        return [
            item for item in self.filtered
            if self._module_name(item) == self.selected_module
        ]

    def _render_rows(self):
        self.tree.delete(*self.tree.get_children())
        self.current_items = self._items_for_selected_module()
        for idx, item in enumerate(self.current_items):
            self.tree.insert(
                "",
                "end",
                iid=str(idx),
                values=(item.get("question", ""),),
            )

        if self.current_items:
            self.tree.selection_set("0")
            self._set_answer(self.current_items[0].get("answer", ""))
        else:
            self._set_answer("Este modulo no tiene entradas para el filtro actual.")

    def _show_selected(self, event=None):
        selected = self.tree.selection()
        if not selected:
            return
        idx = int(selected[0])
        if 0 <= idx < len(self.current_items):
            self._set_answer(self.current_items[idx].get("answer", ""))

    def _set_answer(self, value):
        self.answer.configure(state="normal")
        self.answer.delete("1.0", "end")
        self.answer.insert("1.0", value)
        self.answer.configure(state="disabled")
