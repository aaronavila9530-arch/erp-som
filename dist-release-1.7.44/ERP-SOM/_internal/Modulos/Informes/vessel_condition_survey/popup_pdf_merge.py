import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pypdf import PdfWriter, PdfReader

import api_client


class PopupPDFMerge(tk.Toplevel):

    PRESENTATION_OPTIONS = [
        "P&I Vessel Condition Survey",
        "Mooring Lines Condition (Mooring Ropes)",
        "Hull Condition",
        "Cargo Holds Condition"
    ]

    def __init__(self, parent, record_id: int):
        super().__init__(parent)

        self.parent = parent
        self.record_id = record_id

        self.report_data = None
        self.pdf_files = []

        self.title("Generate Vessel Condition Presentation")
        self._fit_to_screen()
        self.resizable(True, True)
        self.grab_set()

        self._build_ui()

    def _fit_to_screen(self):
        self.update_idletasks()

        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()

        width = min(700, max(560, screen_w - 80))
        height = min(860, max(420, screen_h - 120))

        x = max(0, (screen_w - width) // 2)
        y = max(0, (screen_h - height) // 2)

        self.geometry(f"{width}x{height}+{x}+{y}")
        self.minsize(560, 420)

    # =====================================================
    # UI
    # =====================================================

    def _build_ui(self):

        outer = ttk.Frame(self)
        outer.pack(fill="both", expand=True)

        footer = ttk.Frame(outer, padding=(20, 10))
        footer.pack(side="bottom", fill="x")

        self.btn_final = ttk.Button(
            footer,
            text="Generar Informe Final",
            command=self._create_final_report,
            state="disabled"
        )
        self.btn_final.pack(fill="x", ipady=8)

        canvas = tk.Canvas(outer, highlightthickness=0)
        canvas.pack(side="left", fill="both", expand=True)

        main_scroll = ttk.Scrollbar(
            outer,
            orient="vertical",
            command=canvas.yview
        )
        main_scroll.pack(side="right", fill="y")

        canvas.configure(yscrollcommand=main_scroll.set)

        frame = ttk.Frame(canvas, padding=20)
        window_id = canvas.create_window((0, 0), window=frame, anchor="nw")

        def _refresh_scroll_region(event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _sync_inner_width(event):
            canvas.itemconfigure(window_id, width=event.width)

        frame.bind("<Configure>", _refresh_scroll_region)
        canvas.bind("<Configure>", _sync_inner_width)

        def _mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind("<MouseWheel>", _mousewheel)
        frame.bind("<MouseWheel>", _mousewheel)

        ttk.Button(
            frame,
            text="Buscar",
            command=self._load_backend_data
        ).pack(fill="x", pady=(0, 15), ipady=6)

        self.report_entry = self._readonly_field(frame, "REPORT NUMBER")
        self.vessel_entry = self._readonly_field(frame, "VESSEL")
        self.client_entry = self._readonly_field(frame, "CLIENT")
        self.port_entry = self._readonly_field(frame, "PORT")

        ttk.Label(
            frame,
            text="PRESENTATION TYPE"
        ).pack(anchor="w")

        self.presentation_type_var = tk.StringVar()

        self.presentation_type_combo = ttk.Combobox(
            frame,
            textvariable=self.presentation_type_var,
            values=self.PRESENTATION_OPTIONS,
            state="readonly"
        )
        self.presentation_type_combo.pack(fill="x", pady=5)
        self.presentation_type_combo.bind(
            "<<ComboboxSelected>>",
            lambda e: self._refresh_generate_button()
        )

        ttk.Separator(frame).pack(fill="x", pady=15)

        ttk.Label(
            frame,
            text="PDF Files",
            font=("Segoe UI", 11, "bold")
        ).pack(anchor="w")

        ttk.Separator(frame).pack(fill="x", pady=10)

        list_frame = ttk.Frame(frame)
        list_frame.pack(fill="both", expand=True)

        self.listbox = tk.Listbox(
            list_frame,
            height=14
        )
        self.listbox.pack(
            side="left",
            fill="both",
            expand=True
        )

        scrollbar = ttk.Scrollbar(
            list_frame,
            orient="vertical",
            command=self.listbox.yview
        )
        scrollbar.pack(side="right", fill="y")

        self.listbox.configure(
            yscrollcommand=scrollbar.set
        )

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill="x", pady=15)

        ttk.Button(
            btn_frame,
            text="➕ Agregar PDF",
            command=self._add_pdf
        ).pack(fill="x", ipady=6)

        ttk.Button(
            btn_frame,
            text="❌ Quitar seleccionado",
            command=self._remove_selected
        ).pack(fill="x", pady=5, ipady=6)

        ttk.Separator(frame).pack(fill="x", pady=15)

    # =====================================================
    # READONLY FIELD
    # =====================================================

    def _readonly_field(self, parent, label):

        ttk.Label(parent, text=label).pack(anchor="w")

        entry = ttk.Entry(parent, state="readonly")
        entry.pack(fill="x", pady=5)

        return entry

    # =====================================================
    # SET ENTRY
    # =====================================================

    def _set_entry(self, entry, value):

        entry.config(state="normal")
        entry.delete(0, "end")
        entry.insert(0, value if value else "")
        entry.config(state="readonly")

    # =====================================================
    # LOAD BACKEND DATA (MISMA LÓGICA QUE CRANE)
    # =====================================================

    def _load_backend_data(self):

        try:

            resp = api_client.get_vessel_condition_survey_by_id_api(
                self.record_id
            )

            if not resp:
                messagebox.showerror(
                    "Error",
                    "No data found."
                )
                return

            # -------------------------------------------------
            # SOPORTA DOS FORMATOS:
            # 1) { success: True, data: {...} }
            # 2) {...}
            # -------------------------------------------------

            if isinstance(resp, dict) and resp.get("success") is True:

                self.report_data = resp.get("data")

            else:

                self.report_data = resp

            if not self.report_data:

                messagebox.showerror(
                    "Error",
                    "Empty backend response."
                )
                return

            # -------------------------------------------------
            # LLENAR CAMPOS
            # -------------------------------------------------

            self._set_entry(
                self.report_entry,
                self.report_data.get("report_number")
            )

            self._set_entry(
                self.vessel_entry,
                self.report_data.get("vessel")
            )

            self._set_entry(
                self.client_entry,
                self.report_data.get("client") or self.report_data.get("requested_by")
            )

            self._set_entry(
                self.port_entry,
                f"{self.report_data.get('port') or ''} – {self.report_data.get('country') or ''}"
            )

            # -------------------------------------------------
            # REPORT TYPE
            # -------------------------------------------------

            backend_report_type = self._normalize_report_type(
                self.report_data.get("report_type")
            )

            if backend_report_type:
                self.presentation_type_var.set(backend_report_type)
            else:
                self.presentation_type_var.set("")

            self._refresh_generate_button()

        except Exception as e:

            messagebox.showerror(
                "Error",
                str(e)
            )

    # =====================================================
    # NORMALIZE REPORT TYPE
    # =====================================================

    def _normalize_report_type(self, value):

        raw = str(value or "").strip().lower()

        if raw == "p&i vessel condition survey":
            return "P&I Vessel Condition Survey"

        if raw == "mooring lines condition (mooring ropes)":
            return "Mooring Lines Condition (Mooring Ropes)"

        if raw == "hull condition":
            return "Hull Condition"

        if raw == "cargo holds condition":
            return "Cargo Holds Condition"

        return ""

    # =====================================================
    # ADD PDF
    # =====================================================

    def _add_pdf(self):

        files = filedialog.askopenfilenames(
            filetypes=[("PDF Files", "*.pdf")]
        )

        if not files:
            return

        added = 0

        for file_path in files:

            if not file_path:
                continue

            if not os.path.exists(file_path):
                continue

            if not file_path.lower().endswith(".pdf"):

                messagebox.showerror(
                    "Error",
                    "Solo se permiten archivos PDF."
                )
                return

            try:
                PdfReader(file_path)
            except Exception:
                messagebox.showerror(
                    "Error",
                    f"El archivo no es un PDF válido:\n{file_path}"
                )
                return

            self.pdf_files.append(file_path)
            self.listbox.insert("end", os.path.basename(file_path))
            added += 1

        if added > 0:
            self._refresh_generate_button()

    # =====================================================
    # REMOVE SELECTED
    # =====================================================

    def _remove_selected(self):

        selection = self.listbox.curselection()

        if not selection:
            return

        index = selection[0]

        try:
            self.listbox.delete(index)
            self.pdf_files.pop(index)
        except Exception:
            pass

        self._refresh_generate_button()

    # =====================================================
    # ENABLE / DISABLE FINAL BUTTON
    # =====================================================

    def _refresh_generate_button(self):

        has_backend = self.report_data is not None
        has_type = bool(self.presentation_type_var.get().strip())
        has_pdfs = len(self.pdf_files) > 0

        if has_backend and has_type and has_pdfs:
            self.btn_final.config(state="normal")
        else:
            self.btn_final.config(state="disabled")

    # =====================================================
    # VALIDATE TYPE (SOLO QUE EXISTA SELECCIÓN)
    # =====================================================

    def _validate_selected_type(self):

        if not self.report_data:
            raise ValueError("Debe presionar Buscar primero.")

        selected_type = (self.presentation_type_var.get() or "").strip()

        if not selected_type:
            raise ValueError("Debe seleccionar el tipo de presentación.")

    # =====================================================
    # CREATE FINAL REPORT
    # =====================================================

    def _create_final_report(self):

        if not self.report_data:

            messagebox.showwarning(
                "Warning",
                "Debe presionar Buscar primero."
            )
            return

        if not self.presentation_type_var.get().strip():

            messagebox.showwarning(
                "Warning",
                "Debe seleccionar el tipo de presentación."
            )
            return

        if not self.pdf_files:

            messagebox.showwarning(
                "Warning",
                "Debe agregar al menos un PDF."
            )
            return

        try:

            self._validate_selected_type()

            presentation_pdf = api_client.generate_vessel_condition_presentation_api(
                self.record_id
            )

            if not presentation_pdf or not os.path.exists(presentation_pdf):

                messagebox.showerror(
                    "Error",
                    "No se pudo generar la presentación."
                )
                return

            save_path = filedialog.asksaveasfilename(
                title="Guardar Informe Final",
                defaultextension=".pdf",
                filetypes=[("PDF File", "*.pdf")],
                initialfile=f"Final_Vessel_Condition_{self.record_id}.pdf"
            )

            if not save_path:
                return

            writer = PdfWriter()

            try:

                presentation_reader = PdfReader(presentation_pdf)

                for page in presentation_reader.pages:
                    writer.add_page(page)

                for pdf_path in self.pdf_files:

                    if not os.path.exists(pdf_path):
                        raise FileNotFoundError(
                            f"No existe el archivo:\n{pdf_path}"
                        )

                    reader = PdfReader(pdf_path)

                    for page in reader.pages:
                        writer.add_page(page)

                with open(save_path, "wb") as f:
                    writer.write(f)

            finally:
                try:
                    writer.close()
                except Exception:
                    pass

            messagebox.showinfo(
                "Success",
                "Informe final creado correctamente."
            )

            try:
                os.startfile(save_path)
            except Exception:
                pass

        except Exception as e:

            messagebox.showerror(
                "Error",
                str(e)
            )
