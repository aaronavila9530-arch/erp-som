import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

import api_client
from Modulos.Informes.logra_questionnaires_data import LOGRA_QUESTIONNAIRES
from Modulos.Informes.popup.popup_ai_compare import PopupAICompare
from session_context import get_user


class LograQuestionnairesForm(ttk.Frame):
    ITEMS_PER_PAGE = 5
    MAX_BULLETS = 20

    SECTION_LABELS = {
        "critical_questions": "Preguntas criticas",
        "detailed_questions": "Cuestionario detallado",
    }

    def __init__(self, parent, usuario=None, rol=None, on_back=None):
        super().__init__(parent)
        self.parent = parent
        self.usuario = usuario
        self.rol = rol
        self.on_back = on_back

        self.report_id = None
        self.form_var = tk.StringVar()
        self.search_var = tk.StringVar()
        self.section_var = tk.StringVar(value="critical_questions")
        self.page_index = 0
        self.answers = {}
        self.text_widgets = {}

        self.pack(fill="both", expand=True)
        self._build_ui()

    # =========================================================
    # UI
    # =========================================================
    def _build_ui(self):
        self._build_topbar()
        self._build_filters()
        self._build_content()
        self.form_var.set(LOGRA_QUESTIONNAIRES[0]["title"])
        self._render_current_page()

    def _build_topbar(self):
        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=12, pady=(10, 6))
        bar.columnconfigure(0, weight=1)

        title_box = ttk.Frame(bar)
        title_box.grid(row=0, column=0, sticky="ew")
        ttk.Label(
            title_box,
            text="LOGRA - Cuestionarios",
            font=("Segoe UI", 14, "bold")
        ).pack(anchor="w")
        ttk.Label(
            title_box,
            text="Cada pregunta se documenta con hasta 20 bullet points y adjuntos guardados en backend.",
            foreground="#555555"
        ).pack(anchor="w", pady=(2, 0))

        actions = ttk.Frame(bar)
        actions.grid(row=0, column=1, sticky="e")
        ttk.Button(actions, text="Mejorar con PORTIA", command=self._open_portia).pack(side="left", padx=4)
        ttk.Button(actions, text="Abrir", command=self._open_saved_report).pack(side="left", padx=4)
        ttk.Button(actions, text="Guardar", command=self._save_report).pack(side="left", padx=4)
        ttk.Button(actions, text="Home", command=self._go_home).pack(side="left", padx=4)

    def _build_filters(self):
        filters = ttk.Frame(self)
        filters.pack(fill="x", padx=12, pady=(0, 8))
        filters.columnconfigure(1, weight=1)
        filters.columnconfigure(3, weight=1)

        ttk.Label(filters, text="Formulario").grid(row=0, column=0, sticky="w", padx=(0, 6))
        cb = ttk.Combobox(
            filters,
            textvariable=self.form_var,
            state="readonly",
            values=[item["title"] for item in LOGRA_QUESTIONNAIRES],
        )
        cb.grid(row=0, column=1, sticky="ew", padx=(0, 12))
        cb.bind("<<ComboboxSelected>>", self._on_context_changed)

        ttk.Label(filters, text="Buscar").grid(row=0, column=2, sticky="w", padx=(0, 6))
        search = ttk.Entry(filters, textvariable=self.search_var)
        search.grid(row=0, column=3, sticky="ew")
        search.bind("<KeyRelease>", self._on_context_changed)

    def _build_content(self):
        shell = ttk.Frame(self)
        shell.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        shell.columnconfigure(1, weight=1)
        shell.rowconfigure(0, weight=1)

        nav = ttk.LabelFrame(shell, text="Secciones", padding=10)
        nav.grid(row=0, column=0, sticky="ns", padx=(0, 10))

        for key, label in self.SECTION_LABELS.items():
            ttk.Radiobutton(
                nav,
                text=label,
                value=key,
                variable=self.section_var,
                command=self._on_context_changed
            ).pack(anchor="w", pady=4)

        self.count_label = ttk.Label(nav, text="", justify="left")
        self.count_label.pack(anchor="w", pady=(18, 0))

        content = ttk.Frame(shell)
        content.grid(row=0, column=1, sticky="nsew")
        content.rowconfigure(1, weight=1)
        content.columnconfigure(0, weight=1)

        pager = ttk.Frame(content)
        pager.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        pager.columnconfigure(1, weight=1)
        ttk.Button(pager, text="Anterior", command=self._prev_page).grid(row=0, column=0, sticky="w")
        self.page_label = ttk.Label(pager, text="", anchor="center")
        self.page_label.grid(row=0, column=1, sticky="ew")
        ttk.Button(pager, text="Siguiente", command=self._next_page).grid(row=0, column=2, sticky="e")

        canvas_wrap = ttk.Frame(content)
        canvas_wrap.grid(row=1, column=0, sticky="nsew")
        canvas_wrap.rowconfigure(0, weight=1)
        canvas_wrap.columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(canvas_wrap, highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(canvas_wrap, orient="vertical", command=self.canvas.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.canvas.configure(yscrollcommand=scroll.set)

        self.scroll_frame = ttk.Frame(self.canvas)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self.scroll_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width))
        self.scroll_frame.bind("<Enter>", self._bind_mousewheel)
        self.scroll_frame.bind("<Leave>", self._unbind_mousewheel)

    # =========================================================
    # Scroll wheel
    # =========================================================
    def _bind_mousewheel(self, event=None):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", lambda e: self.canvas.yview_scroll(-3, "units"))
        self.canvas.bind_all("<Button-5>", lambda e: self.canvas.yview_scroll(3, "units"))

    def _unbind_mousewheel(self, event=None):
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)) * 3, "units")

    # =========================================================
    # Data helpers
    # =========================================================
    def _current_form(self):
        title = self.form_var.get()
        return next((item for item in LOGRA_QUESTIONNAIRES if item["title"] == title), LOGRA_QUESTIONNAIRES[0])

    def _all_questions(self, form=None, section=None):
        form = form or self._current_form()
        section = section or self.section_var.get()
        return list(form.get(section, []))

    def _items(self):
        items = self._all_questions()
        query = self.search_var.get().strip().lower()
        if query:
            filtered = []
            for item in items:
                text = " ".join([
                    str(item.get("id") or item.get("number") or ""),
                    str(item.get("block") or ""),
                    str(item.get("question") or ""),
                ]).lower()
                if query in text:
                    filtered.append(item)
            return filtered
        return items

    def _item_key(self, item):
        return str(item.get("id") or item.get("number") or "").strip()

    def _answer_key(self, form, section, item):
        return f"{form['slug']}|{section}|{self._item_key(item)}"

    def _get_bullets(self, form, section, item):
        key = self._answer_key(form, section, item)
        self.answers.setdefault(key, [""])
        return self.answers[key]

    def _collect_visible_text(self):
        for key, widgets in list(self.text_widgets.items()):
            self.answers[key] = [
                widget.get("1.0", "end-1c").strip()
                for widget in widgets
            ][:self.MAX_BULLETS]

    def _on_context_changed(self, event=None):
        self._collect_visible_text()
        self.page_index = 0
        self._render_current_page()

    def _prev_page(self):
        self._collect_visible_text()
        if self.page_index > 0:
            self.page_index -= 1
            self._render_current_page()

    def _next_page(self):
        self._collect_visible_text()
        items = self._items()
        max_page = max(0, (len(items) - 1) // self.ITEMS_PER_PAGE)
        if self.page_index < max_page:
            self.page_index += 1
            self._render_current_page()

    # =========================================================
    # Render
    # =========================================================
    def _render_current_page(self):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        self.text_widgets.clear()

        form = self._current_form()
        section = self.section_var.get()
        items = self._items()
        total_pages = max(1, (len(items) + self.ITEMS_PER_PAGE - 1) // self.ITEMS_PER_PAGE)
        self.page_index = min(self.page_index, total_pages - 1)
        start = self.page_index * self.ITEMS_PER_PAGE
        visible = items[start:start + self.ITEMS_PER_PAGE]

        self.count_label.configure(
            text=(
                f"Criticas: {len(form.get('critical_questions', []))}\n"
                f"Detalladas: {len(form.get('detailed_questions', []))}\n"
                f"Total: {len(form.get('critical_questions', [])) + len(form.get('detailed_questions', []))}"
            )
        )
        self.page_label.configure(text=f"Pagina {self.page_index + 1} de {total_pages} - {len(items)} preguntas")

        if not visible:
            ttk.Label(self.scroll_frame, text="No hay resultados.").pack(anchor="w", padx=8, pady=8)
            return

        for item in visible:
            self._build_question_card(form, section, item)

    def _build_question_card(self, form, section, item):
        item_key = self._item_key(item)
        title_bits = [item_key]
        if section == "detailed_questions":
            title_bits.append(item.get("block") or "Pregunta")

        card = ttk.LabelFrame(self.scroll_frame, text=" - ".join(title_bits), padding=10)
        card.pack(fill="x", padx=4, pady=7)
        card.columnconfigure(0, weight=1)

        if section == "detailed_questions" and item.get("priority"):
            ttk.Label(card, text=f"Prioridad: {item.get('priority')}", foreground="#555555").grid(
                row=0, column=0, sticky="w"
            )

        ttk.Label(
            card,
            text=item.get("question", ""),
            wraplength=1080,
            justify="left",
            font=("Segoe UI", 9, "bold")
        ).grid(row=1, column=0, sticky="ew", pady=(6, 8))

        key = self._answer_key(form, section, item)
        bullets = self._get_bullets(form, section, item)
        self.text_widgets[key] = []

        bullets_box = ttk.Frame(card)
        bullets_box.grid(row=2, column=0, sticky="ew")
        bullets_box.columnconfigure(1, weight=1)

        for idx, value in enumerate(bullets, start=1):
            ttk.Label(bullets_box, text=f"{idx}.").grid(row=idx - 1, column=0, sticky="nw", padx=(0, 6), pady=3)
            text = ScrolledText(bullets_box, height=2, wrap="word", font=("Segoe UI", 9))
            text.insert("1.0", value)
            text.grid(row=idx - 1, column=1, sticky="ew", pady=3)
            self.text_widgets[key].append(text)

        actions = ttk.Frame(card)
        actions.grid(row=3, column=0, sticky="ew", pady=(8, 0))

        ttk.Button(actions, text="+ Bullet", command=lambda f=form, s=section, i=item: self._add_bullet(f, s, i)).pack(
            side="left", padx=(0, 4)
        )
        ttk.Button(actions, text="- Bullet", command=lambda f=form, s=section, i=item: self._remove_bullet(f, s, i)).pack(
            side="left", padx=(0, 12)
        )
        ttk.Button(actions, text="Adjuntar", command=lambda f=form, s=section, i=item: self._attach_file(f, s, i)).pack(
            side="left"
        )

        self._build_attachments(card, form, section, item)

    def _build_attachments(self, parent, form, section, item):
        if not self.report_id:
            ttk.Label(parent, text="Guarda primero para habilitar adjuntos persistentes.", foreground="#777777").grid(
                row=4, column=0, sticky="w", pady=(8, 0)
            )
            return

        item_key = self._item_key(item)
        resp = api_client.list_logra_attachments_api(self.report_id, form["slug"], section, item_key)
        attachments = resp.get("data") or []
        if not attachments:
            return

        box = ttk.Frame(parent)
        box.grid(row=4, column=0, sticky="ew", pady=(8, 0))
        ttk.Label(box, text="Adjuntos:", foreground="#555555").pack(side="left", padx=(0, 6))
        for att in attachments[:5]:
            ttk.Button(
                box,
                text=att.get("original_filename") or f"Adjunto {att.get('id')}",
                command=lambda a=att: self._open_attachment(a)
            ).pack(side="left", padx=3)

    # =========================================================
    # Actions
    # =========================================================
    def _add_bullet(self, form, section, item):
        self._collect_visible_text()
        bullets = self._get_bullets(form, section, item)
        if len(bullets) >= self.MAX_BULLETS:
            messagebox.showwarning("LOGRA", "Cada pregunta permite maximo 20 bullet points.")
            return
        bullets.append("")
        self._render_current_page()

    def _remove_bullet(self, form, section, item):
        self._collect_visible_text()
        bullets = self._get_bullets(form, section, item)
        if len(bullets) <= 1:
            bullets[0] = ""
        else:
            bullets.pop()
        self._render_current_page()

    def _answers_payload(self):
        self._collect_visible_text()
        payload = []
        for form in LOGRA_QUESTIONNAIRES:
            for section in self.SECTION_LABELS:
                for item in form.get(section, []):
                    key = self._answer_key(form, section, item)
                    bullets = [value.strip() for value in self.answers.get(key, []) if value.strip()]
                    if not bullets:
                        continue
                    payload.append({
                        "form_slug": form["slug"],
                        "form_title": form["title"],
                        "section": section,
                        "item_key": self._item_key(item),
                        "question_text": item.get("question", ""),
                        "bullets": bullets,
                    })
        return payload

    def _save_report(self, silent=False):
        title = f"LOGRA - {self.form_var.get() or 'Cuestionarios'}"
        payload = {
            "id": self.report_id,
            "title": title,
            "created_by": self.usuario or get_user(),
            "answers": self._answers_payload(),
        }
        resp = api_client.save_logra_report_api(payload)
        if not resp.get("success"):
            if not silent:
                messagebox.showerror("LOGRA", f"No se pudo guardar:\n{resp.get('error') or resp}")
            return False
        self.report_id = (resp.get("report") or {}).get("id") or self.report_id
        if not silent:
            messagebox.showinfo("LOGRA", "Guardado correctamente.")
            self._render_current_page()
        return True

    def _attach_file(self, form, section, item):
        if not self.report_id:
            if not self._save_report(silent=True):
                return

        path = filedialog.askopenfilename(title="Seleccionar adjunto")
        if not path:
            return

        resp = api_client.upload_logra_attachment_api(
            self.report_id,
            form["slug"],
            section,
            self._item_key(item),
            path
        )
        if not resp.get("success"):
            messagebox.showerror("LOGRA", f"No se pudo subir el adjunto:\n{resp.get('error') or resp}")
            return

        messagebox.showinfo("LOGRA", "Adjunto guardado correctamente.")
        self._render_current_page()

    def _open_attachment(self, attachment):
        resp = api_client.open_logra_attachment_api(attachment.get("id"))
        if not resp.get("success"):
            messagebox.showerror("LOGRA", f"No se pudo abrir el adjunto:\n{resp.get('error') or resp}")

    def _open_portia(self):
        self._collect_visible_text()
        PopupLograPortia(self, self)

    def _open_saved_report(self):
        PopupLograOpen(self, self)

    def load_report(self, report_id):
        resp = api_client.get_logra_report_api(report_id)
        if resp.get("success") is False:
            messagebox.showerror("LOGRA", f"No se pudo abrir el reporte:\n{resp.get('error') or resp}")
            return

        self.report_id = (resp.get("report") or {}).get("id")
        self.answers.clear()
        for item in resp.get("answers") or []:
            key = f"{item.get('form_slug')}|{item.get('section')}|{item.get('item_key')}"
            bullets = item.get("bullets") or []
            self.answers[key] = bullets if bullets else [""]

        messagebox.showinfo("LOGRA", f"Reporte LOGRA #{self.report_id} cargado.")
        self._render_current_page()

    def _go_home(self):
        for widget in self.parent.winfo_children():
            widget.destroy()
        from Modulos.Informes.informes_home_ui import InformesHomeUI

        InformesHomeUI(self.parent, usuario=self.usuario, rol=self.rol)


class PopupLograOpen(tk.Toplevel):
    def __init__(self, parent, form_instance):
        super().__init__(parent)
        self.form_instance = form_instance
        self.title("Abrir LOGRA guardado")
        self.geometry("760x420")
        self.transient(parent)
        self.grab_set()
        self.rows = []
        self._build_ui()
        self._load()

    def _build_ui(self):
        container = ttk.Frame(self, padding=12)
        container.pack(fill="both", expand=True)
        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)

        columns = ("id", "title", "status", "updated_at")
        self.tree = ttk.Treeview(container, columns=columns, show="headings", height=12)
        for col, title, width in [
            ("id", "ID", 70),
            ("title", "Titulo", 360),
            ("status", "Estado", 110),
            ("updated_at", "Actualizado", 180),
        ]:
            self.tree.heading(col, text=title)
            self.tree.column(col, width=width, anchor="w")
        self.tree.grid(row=0, column=0, sticky="nsew")

        scroll = ttk.Scrollbar(container, orient="vertical", command=self.tree.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scroll.set)

        actions = ttk.Frame(container)
        actions.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        ttk.Button(actions, text="Cancelar", command=self.destroy).pack(side="right")
        ttk.Button(actions, text="Abrir seleccionado", command=self._open_selected).pack(side="right", padx=6)

    def _load(self):
        resp = api_client.list_logra_reports_api()
        self.rows = resp.get("data") or []
        for row in self.rows:
            self.tree.insert(
                "",
                "end",
                iid=str(row.get("id")),
                values=(
                    row.get("id"),
                    row.get("title") or "",
                    row.get("status") or "",
                    str(row.get("updated_at") or ""),
                )
            )

    def _open_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("LOGRA", "Selecciona un reporte.")
            return
        self.form_instance.load_report(int(selected[0]))
        self.destroy()


class PopupLograPortia(tk.Toplevel):
    def __init__(self, parent, form_instance):
        super().__init__(parent)
        self.form_instance = form_instance
        self.title("Mejorar con PORTIA - LOGRA")
        self.geometry("720x520")
        self.transient(parent)
        self.grab_set()

        self.form_var = tk.StringVar(value=form_instance.form_var.get())
        self.section_var = tk.StringVar(value=form_instance.section_var.get())
        self.question_var = tk.StringVar()
        self.bullet_var = tk.StringVar()
        self.language_var = tk.StringVar(value="ES")
        self.question_items = []
        self._build_ui()
        self._load_questions()

    def _build_ui(self):
        root = ttk.Frame(self, padding=14)
        root.pack(fill="both", expand=True)
        root.columnconfigure(1, weight=1)
        root.rowconfigure(5, weight=1)

        ttk.Label(root, text="Formulario").grid(row=0, column=0, sticky="w", pady=4)
        form_cb = ttk.Combobox(
            root,
            textvariable=self.form_var,
            state="readonly",
            values=[item["title"] for item in LOGRA_QUESTIONNAIRES],
        )
        form_cb.grid(row=0, column=1, sticky="ew", pady=4)
        form_cb.bind("<<ComboboxSelected>>", lambda e: self._load_questions())

        ttk.Label(root, text="Tipo").grid(row=1, column=0, sticky="w", pady=4)
        section_cb = ttk.Combobox(
            root,
            textvariable=self.section_var,
            state="readonly",
            values=list(LograQuestionnairesForm.SECTION_LABELS.keys()),
        )
        section_cb.grid(row=1, column=1, sticky="ew", pady=4)
        section_cb.bind("<<ComboboxSelected>>", lambda e: self._load_questions())

        ttk.Label(root, text="Pregunta").grid(row=2, column=0, sticky="w", pady=4)
        self.question_cb = ttk.Combobox(root, textvariable=self.question_var, state="readonly")
        self.question_cb.grid(row=2, column=1, sticky="ew", pady=4)
        self.question_cb.bind("<<ComboboxSelected>>", lambda e: self._load_bullets())

        ttk.Label(root, text="Bullet").grid(row=3, column=0, sticky="w", pady=4)
        self.bullet_cb = ttk.Combobox(root, textvariable=self.bullet_var, state="readonly")
        self.bullet_cb.grid(row=3, column=1, sticky="ew", pady=4)

        lang = ttk.LabelFrame(root, text="Salida")
        lang.grid(row=4, column=1, sticky="w", pady=8)
        ttk.Radiobutton(lang, text="Espanol", value="ES", variable=self.language_var).pack(side="left", padx=8)
        ttk.Radiobutton(lang, text="Ingles", value="EN", variable=self.language_var).pack(side="left", padx=8)

        self.preview = ScrolledText(root, height=9, wrap="word", font=("Segoe UI", 9))
        self.preview.grid(row=5, column=0, columnspan=2, sticky="nsew", pady=(8, 10))

        actions = ttk.Frame(root)
        actions.grid(row=6, column=0, columnspan=2, sticky="ew")
        ttk.Button(actions, text="Cancelar", command=self.destroy).pack(side="right")
        ttk.Button(actions, text="Mejorar con PORTIA", command=self._execute).pack(side="right", padx=6)

    def _selected_form(self):
        return next((item for item in LOGRA_QUESTIONNAIRES if item["title"] == self.form_var.get()), LOGRA_QUESTIONNAIRES[0])

    def _load_questions(self):
        form = self._selected_form()
        section = self.section_var.get()
        self.question_items = form.get(section, [])
        values = []
        for item in self.question_items:
            label = f"{item.get('id') or item.get('number')} - {item.get('question', '')[:120]}"
            values.append(label)
        self.question_cb.configure(values=values)
        if values:
            self.question_var.set(values[0])
        else:
            self.question_var.set("")
        self._load_bullets()

    def _selected_question(self):
        value = self.question_var.get()
        values = list(self.question_cb.cget("values") or [])
        try:
            index = values.index(value)
            return self.question_items[index]
        except Exception:
            return None

    def _load_bullets(self):
        form = self._selected_form()
        section = self.section_var.get()
        item = self._selected_question()
        if not item:
            self.bullet_cb.configure(values=[])
            self.bullet_var.set("")
            return
        bullets = self.form_instance._get_bullets(form, section, item)
        values = [f"{idx}. {text[:100] if text else '(vacio)'}" for idx, text in enumerate(bullets, start=1)]
        self.bullet_cb.configure(values=values)
        self.bullet_var.set(values[0] if values else "")

    def _execute(self):
        form = self._selected_form()
        section = self.section_var.get()
        item = self._selected_question()
        if not item:
            messagebox.showwarning("PORTIA", "Selecciona una pregunta.")
            return

        values = list(self.bullet_cb.cget("values") or [])
        try:
            bullet_index = values.index(self.bullet_var.get())
        except ValueError:
            bullet_index = 0

        bullets = self.form_instance._get_bullets(form, section, item)
        current_text = bullets[bullet_index].strip() if bullet_index < len(bullets) else ""
        if not current_text:
            messagebox.showwarning("PORTIA", "El bullet seleccionado esta vacio.")
            return

        payload = {
            "text": current_text,
            "language": self.language_var.get(),
            "report_type": LograQuestionnairesForm.SECTION_LABELS.get(section, section),
            "form_title": form["title"],
            "question": item.get("question", ""),
        }
        resp = api_client.improve_logra_text_api(payload)
        if not resp.get("success"):
            messagebox.showerror("PORTIA", f"No se pudo mejorar el texto:\n{resp.get('error') or resp}")
            return

        improved = resp.get("text") or ""
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", improved)

        PopupAICompare(
            self,
            original_text=current_text,
            ai_text=improved,
            on_accept=lambda: self._accept_text(form, section, item, bullet_index, improved),
            on_retry=self._execute,
        )

    def _accept_text(self, form, section, item, bullet_index, text):
        bullets = self.form_instance._get_bullets(form, section, item)
        while len(bullets) <= bullet_index:
            bullets.append("")
        bullets[bullet_index] = text
        self.form_instance._render_current_page()
        self.destroy()
