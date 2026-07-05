import tkinter as tk
from tkinter import ttk, messagebox

import api_client
from Modulos.Informes.popup.popup_ai_compare import PopupAICompare


class PopupAIMaritimeControlPortCaptancy(tk.Toplevel):

    """
    ERP-SOM
    PORTIA Control Popup — PORT CAPTANCY

    Permite:
    - Seleccionar sección
    - Seleccionar idioma
    - Seleccionar bullets específicos
    """

    SECTIONS = [
        ("Operation Summary", "operation_summary"),
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
    def __init__(self, parent, form_instance):

        super().__init__(parent)

        self.title("Mejorar con PORTIA — Port Captancy")
        self.geometry("560x660")

        self.transient(parent)
        self.grab_set()

        self.form = form_instance

        self.section_var = tk.StringVar(value="operation_summary")
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

            section_data = self.form.dynamic_sections.get(section)

            if not section_data:
                return

            items = section_data.get("items", [])

            valid_lines = []

            for idx, txt in enumerate(items):

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

        section = self.section_var.get()
        language = self.language_var.get()

        selected_indexes = [
            idx for idx, var in self.checkbox_vars if var.get()
        ]

        if not selected_indexes:

            messagebox.showwarning(
                "PORTIA",
                "Please select at least one bullet."
            )
            return

        try:

            section_data = self.form.dynamic_sections.get(section)
            items = section_data.get("items", [])

            original_text = []
            ai_payload_items = []

            for idx in selected_indexes:

                text = items[idx].get("1.0", "end-1c").strip()

                original_text.append(text)
                ai_payload_items.append(text)

            payload = {
                "section": section,
                "language": language,
                "vessel": self.form._v("vessel").get(),
                "port": self.form._v("port").get(),
                "operation": self.form._v("operation").get(),
                "items": ai_payload_items
            }

            result = api_client.improve_port_captancy_api(payload)

            ai_text = result.get("items", [])

            def apply_ai():

                for i, idx in enumerate(selected_indexes):

                    try:

                        items[idx].delete("1.0", "end")
                        items[idx].insert("1.0", ai_text[i])

                    except Exception:
                        pass

            PopupAICompare(
                self,
                original_text=original_text,
                ai_text=ai_text,
                on_accept=apply_ai,
                on_retry=lambda: PopupAIMaritimeControlPortCaptancy(
                    self.form.parent,
                    self.form
                )
            )

        except Exception as e:

            messagebox.showerror(
                "PORTIA",
                str(e)
            )