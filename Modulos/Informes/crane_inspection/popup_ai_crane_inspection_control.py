import tkinter as tk
from tkinter import ttk, messagebox


class PopupAICraneInspectionControl(tk.Toplevel):

    """
    Popup previo a ejecutar IA para Crane Inspection.

    Permite:
    - Seleccionar sección
    - Seleccionar idioma
    - Confirmar cantidad de bullets detectados
    """

    SECTIONS = [
        ("Remarks by Crane", "remarks_crane"),
        ("Recommendations", "recommendations"),
        ("Grabs Condition Survey", "grabs_condition"),
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

        self.title("Improve Crane Inspection with IA")
        self.geometry("500x430")
        self.transient(parent)
        self.grab_set()

        self.form = form_instance
        self.on_execute = on_execute

        self.section_var = tk.StringVar(value="remarks_crane")
        self.language_var = tk.StringVar(value="EN")

        self._build_ui()

    # =========================================================
    # UI
    # =========================================================

    def _build_ui(self):

        container = ttk.Frame(self, padding=15)
        container.pack(fill="both", expand=True)

        ttk.Label(
            container,
            text="AI Crane Inspection Enhancement",
            font=("Segoe UI", 12, "bold")
        ).pack(pady=(0, 10))

        # ---------------- SECTION ----------------

        section_box = ttk.LabelFrame(container, text="Select Section")
        section_box.pack(fill="x", pady=10)

        for text, value in self.SECTIONS:

            ttk.Radiobutton(
                section_box,
                text=text,
                value=value,
                variable=self.section_var,
                command=self._update_preview
            ).pack(anchor="w", padx=10, pady=3)

        # ---------------- LANGUAGE ----------------

        lang_box = ttk.LabelFrame(container, text="Output Language")
        lang_box.pack(fill="x", pady=10)

        for text, value in self.LANGUAGES:

            ttk.Radiobutton(
                lang_box,
                text=text,
                value=value,
                variable=self.language_var
            ).pack(anchor="w", padx=10, pady=3)

        # ---------------- INFO ----------------

        self.lbl_info = ttk.Label(
            container,
            text="",
            foreground="#555"
        )
        self.lbl_info.pack(pady=10)

        # ---------------- ACTIONS ----------------

        actions = ttk.Frame(container)
        actions.pack(fill="x", pady=10)

        ttk.Button(
            actions,
            text="Cancel",
            command=self.destroy
        ).pack(side="left")

        ttk.Button(
            actions,
            text="Improve with IA",
            command=self._execute
        ).pack(side="right")

        self._update_preview()

    # =========================================================
    # DETECT BULLET COUNT
    # =========================================================

    def _update_preview(self):

        section = self.section_var.get()

        try:

            lines = getattr(self.form, f"{section}_lines", [])

            count = len([
                txt.get("1.0", "end-1c").strip()
                for txt in lines
                if txt.get("1.0", "end-1c").strip()
            ])

            section_name = section.replace("_", " ").title()

            self.lbl_info.config(
                text=f"Detected {count} bullet(s) in '{section_name}' section."
            )

        except Exception:

            self.lbl_info.config(
                text="Section not available."
            )

    # =========================================================
    # EXECUTE IA
    # =========================================================

    def _execute(self):

        section = self.section_var.get()
        language = self.language_var.get()

        lines = getattr(self.form, f"{section}_lines", [])

        items = [
            txt.get("1.0", "end-1c").strip()
            for txt in lines
            if txt.get("1.0", "end-1c").strip()
        ]

        if not items:

            messagebox.showwarning(
                "IA Crane Inspection",
                "No text found in selected section."
            )
            return

        self.destroy()

        # Ejecuta IA desde el form
        self.on_execute(
            section=section,
            language=language,
            items=items
        )