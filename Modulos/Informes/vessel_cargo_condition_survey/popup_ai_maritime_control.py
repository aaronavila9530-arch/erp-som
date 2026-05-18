import tkinter as tk
from tkinter import ttk, messagebox


class PopupAIMaritimeControl(tk.Toplevel):

    """
    ERP-SOM
    PORTIA Control Popup

    Permite:
    - Seleccionar sección
    - Seleccionar idioma
    - Seleccionar bullets específicos
    """

    SECTIONS = [
        ("Narrative", "narrative"),
        ("Findings", "findings"),
        ("Remarks", "remarks"),
        ("Conclusion", "conclusion"),
    ]

    LANGUAGES = [
        ("English", "EN"),
        ("Español", "ES"),
    ]

    # =========================================================
    # INIT
    # =========================================================
    def __init__(self, parent, form_instance, on_execute):

        super().__init__(parent)

        self.title("Mejorar con PORTIA")
        self.geometry("560x660")

        self.transient(parent)
        self.grab_set()

        self.form = form_instance
        self.on_execute = on_execute

        self.section_var = tk.StringVar(value="narrative")
        self.language_var = tk.StringVar(value="EN")

        self.checkbox_vars = []
        self.lines = []

        self._build_ui()

    # =========================================================
    # BUILD UI
    # =========================================================
    def _build_ui(self):

        container = ttk.Frame(self, padding=15)
        container.pack(fill="both", expand=True)

        ttk.Label(
            container,
            text="PORTIA Text Enhancement",
            font=("Segoe UI", 12, "bold")
        ).pack(pady=(0, 10))

        # =====================================================
        # SECTION SELECTOR
        # =====================================================
        section_box = ttk.LabelFrame(container, text="Select Section")
        section_box.pack(fill="x", pady=8)

        for text, value in self.SECTIONS:

            ttk.Radiobutton(
                section_box,
                text=text,
                value=value,
                variable=self.section_var,
                command=self._load_section_bullets
            ).pack(anchor="w", padx=10, pady=3)

        # =====================================================
        # LANGUAGE
        # =====================================================
        lang_box = ttk.LabelFrame(container, text="Output Language")
        lang_box.pack(fill="x", pady=8)

        for text, value in self.LANGUAGES:

            ttk.Radiobutton(
                lang_box,
                text=text,
                value=value,
                variable=self.language_var
            ).pack(anchor="w", padx=10, pady=3)

        # =====================================================
        # BULLET SELECTION
        # =====================================================
        bullets_box = ttk.LabelFrame(container, text="Select Bullet(s) to Improve")
        bullets_box.pack(fill="both", expand=True, pady=10)

        self.bullet_container = ttk.Frame(bullets_box)
        self.bullet_container.pack(fill="both", expand=True, padx=5, pady=5)

        canvas = tk.Canvas(self.bullet_container, height=200, highlightthickness=0)

        scrollbar = ttk.Scrollbar(
            self.bullet_container,
            orient="vertical",
            command=canvas.yview
        )

        self.bullet_frame = ttk.Frame(canvas)

        self.bullet_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        canvas.create_window(
            (0, 0),
            window=self.bullet_frame,
            anchor="nw"
        )

        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # =====================================================
        # INFO LABEL
        # =====================================================
        self.lbl_info = ttk.Label(
            container,
            text="",
            foreground="#555"
        )
        self.lbl_info.pack(pady=5)

        # =====================================================
        # ACTION BUTTONS
        # =====================================================
        actions = ttk.Frame(container)
        actions.pack(fill="x", pady=10)

        ttk.Button(
            actions,
            text="Select All",
            command=self._select_all
        ).pack(side="left", padx=3)

        ttk.Button(
            actions,
            text="Clear",
            command=self._clear_all
        ).pack(side="left", padx=3)

        ttk.Button(
            actions,
            text="Cancel",
            command=self.destroy
        ).pack(side="right")

        ttk.Button(
            actions,
            text="Mejorar con PORTIA",
            command=self._execute
        ).pack(side="right", padx=5)

        self._load_section_bullets()

    # =========================================================
    # LOAD BULLETS FROM FORM
    # =========================================================
    def _load_section_bullets(self):

        for widget in self.bullet_frame.winfo_children():
            widget.destroy()

        self.checkbox_vars.clear()

        section = self.section_var.get()

        try:

            self.lines = getattr(self.form, f"{section}_lines", [])

            valid_lines = []

            for idx, txt in enumerate(self.lines):

                try:

                    value = txt.get("1.0", "end-1c").strip()

                    if value:
                        valid_lines.append((idx, value))

                except Exception:
                    continue

            for idx, text in valid_lines:

                var = tk.BooleanVar(value=True)

                preview = text.replace("\n", " ")

                if len(preview) > 120:
                    preview = preview[:120] + "..."

                chk = ttk.Checkbutton(
                    self.bullet_frame,
                    text=f"{idx+1}. {preview}",
                    variable=var
                )

                chk.pack(anchor="w", pady=2)

                self.checkbox_vars.append((idx, var))

            self.lbl_info.config(
                text=f"Detected {len(valid_lines)} text block(s) in '{section.replace('_',' ').title()}' section."
            )

        except Exception:

            self.lbl_info.config(
                text="Section not available."
            )

    # =========================================================
    # SELECT ALL
    # =========================================================
    def _select_all(self):

        for _, var in self.checkbox_vars:
            var.set(True)

    # =========================================================
    # CLEAR ALL
    # =========================================================
    def _clear_all(self):

        for _, var in self.checkbox_vars:
            var.set(False)

    # =========================================================
    # EXECUTE PORTIA
    # =========================================================
    def _execute(self):

        section = (self.section_var.get() or "").strip()
        language = (self.language_var.get() or "").strip().upper()

        if not section:
            section = "narrative"

        if language not in ("EN", "ES"):
            language = "EN"

        selected_indexes = []
        selected_items = []

        # -----------------------------------------------------
        # RECOLECTAR SOLO LOS BULLETS MARCADOS
        # -----------------------------------------------------
        for idx, var in self.checkbox_vars:

            if not var.get():
                continue

            try:
                if idx < len(self.lines):
                    txt_widget = self.lines[idx]

                    if txt_widget:
                        text = txt_widget.get("1.0", "end-1c").strip()

                        if text:
                            selected_indexes.append(idx)
                            selected_items.append(text)

            except Exception:
                continue

        # -----------------------------------------------------
        # VALIDACIÓN
        # -----------------------------------------------------
        if not selected_items:

            messagebox.showwarning(
                "PORTIA",
                "Please select at least one valid text block."
            )
            return

        # -----------------------------------------------------
        # EJECUCIÓN SEGURA
        # -----------------------------------------------------
        try:
            self.destroy()

            self.on_execute(
                section=section,
                language=language,
                items=selected_items,
                selected_indexes=selected_indexes
            )

        except Exception as e:

            messagebox.showerror(
                "PORTIA",
                f"Execution failed:\n{str(e)}"
            )
