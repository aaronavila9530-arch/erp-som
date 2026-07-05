import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from api_client import (
    get_full_draft_survey_api,
    generate_draft_survey_presentation_pdf_api,
    generate_draft_survey_final_pdf_api  # si ya lo tienes
)


class PopupDraftSurveyPresentation(tk.Toplevel):

    def __init__(self, parent, draft_report_number):
        super().__init__(parent)

        self.parent = parent
        self.draft_report_number = draft_report_number
        self.report_data = None

        self.title("Generate Draft Survey Presentation")
        self.geometry("450x670")
        self.resizable(False, False)
        self.grab_set()

        self.pdf_files = []

        self._build_ui()

    # =====================================================
    # UI
    # =====================================================
    def _build_ui(self):

        # ================= CONTAINER SCROLL =================
        container = ttk.Frame(self)
        container.pack(fill="both", expand=True)

        canvas = tk.Canvas(container)
        canvas.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollbar.pack(side="right", fill="y")

        canvas.configure(yscrollcommand=scrollbar.set)

        self.frame = ttk.Frame(canvas, padding=20)
        canvas.create_window((0, 0), window=self.frame, anchor="nw")

        self.frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        # ================= SCROLL CON MOUSE =================
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        frame = self.frame

        # ================= CONTENIDO =================

        ttk.Button(
            frame,
            text="Buscar",
            command=self._load_backend_data
        ).pack(fill="x", pady=(0, 15))

        self.cert_entry = self._readonly_field(frame, "DRAFT NO.")
        self.vessel_entry = self._readonly_field(frame, "VESSEL")
        self.client_entry = self._readonly_field(frame, "CLIENT")
        self.place_entry = self._readonly_field(frame, "PLACE")
        self.date_entry = self._readonly_field(frame, "DATE")

        # ================= OPCIÓN 1 =================
        ttk.Label(frame, text="Recrear Informe Final", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(10,5))

        ttk.Button(
            frame,
            text="Recrear Informe (Backend)",
            command=self._generate_unified
        ).pack(fill="x")

        ttk.Separator(frame).pack(fill="x", pady=15)

        # ================= OPCIÓN 2 =================
        ttk.Label(frame, text="Crear Informe Final (Subir PDFs)", font=("Segoe UI", 10, "bold")).pack(anchor="w")

        ttk.Label(
            frame,
            text="PDF Files",
            font=("Segoe UI", 11, "bold")
        ).pack(anchor="w")

        list_frame = ttk.Frame(frame)
        list_frame.pack(fill="both", expand=True)

        self.listbox = tk.Listbox(list_frame, height=6)
        self.listbox.pack(side="left", fill="both", expand=True)

        scrollbar_list = ttk.Scrollbar(
            list_frame,
            orient="vertical",
            command=self.listbox.yview
        )
        scrollbar_list.pack(side="right", fill="y")

        self.listbox.configure(yscrollcommand=scrollbar_list.set)

        ttk.Button(
            frame,
            text="➕ Agregar PDF",
            command=self._add_pdf
        ).pack(fill="x", pady=2)

        ttk.Button(
            frame,
            text="❌ Quitar PDF",
            command=self._remove_pdf
        ).pack(fill="x", pady=2)

        ttk.Button(
            frame,
            text="Generar Informe Final (Manual)",
            command=self._generate_final_full
        ).pack(fill="x", pady=10, ipady=6)


    # =====================================================
    # READONLY FIELD
    # =====================================================
    def _readonly_field(self, parent, label):

        ttk.Label(parent, text=label).pack(anchor="w")
        entry = ttk.Entry(parent, state="readonly")
        entry.pack(fill="x", pady=5)
        return entry

    # =====================================================
    # LOAD DATA FROM BACKEND
    # =====================================================
    def _load_backend_data(self):

        try:
            resp = get_full_draft_survey_api(self.draft_report_number)

            if not resp or not resp.get("success"):
                messagebox.showerror(
                    "Error",
                    resp.get("error", "No data found.")
                )
                return

            self.report_data = resp.get("data")

            if not self.report_data:
                messagebox.showerror("Error", "Empty backend response.")
                return

            self._set_entry(
                self.cert_entry,
                self.report_data.get("draft_report_number")
            )

            self._set_entry(
                self.vessel_entry,
                self.report_data.get("word_vessel")
            )

            self._set_entry(
                self.client_entry,
                self.report_data.get("word_survey_requested_by")
            )

            place = f"{self.report_data.get('word_port') or ''} – {self.report_data.get('word_country') or ''}"
            self._set_entry(self.place_entry, place)

            self._set_entry(
                self.date_entry,
                self.report_data.get("word_commenced")
            )

        except Exception as e:
            messagebox.showerror("Error", str(e))

    # =====================================================
    # SAFE SET ENTRY
    # =====================================================
    def _set_entry(self, entry, value):

        entry.config(state="normal")
        entry.delete(0, "end")
        entry.insert(0, value if value else "")
        entry.config(state="readonly")

    # =====================================================
    # GENERATE PRESENTATION
    # =====================================================
    def _generate_presentation(self):

        if not self.report_data:
            messagebox.showwarning(
                "Warning",
                "Debe presionar Buscar primero."
            )
            return

        if not self.pdf_files:
            confirm = messagebox.askyesno(
                "Confirmación",
                "No has agregado PDFs.\n\n¿Deseas generar solo la presentación?"
            )
            if not confirm:
                return

        try:
            resp = generate_draft_survey_presentation_pdf_api(
                self.draft_report_number
            )

            if isinstance(resp, dict):
                messagebox.showerror(
                    "Error",
                    resp.get("error", "Unknown error")
                )
                return

            if resp.status_code != 200:
                try:
                    error_json = resp.json()
                    messagebox.showerror(
                        "Error",
                        error_json.get("detail", f"HTTP {resp.status_code}")
                    )
                except Exception:
                    messagebox.showerror(
                        "Error",
                        f"HTTP {resp.status_code}"
                    )
                return

            final_path = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF File", "*.pdf")],
                initialfile=f"Presentation_{self.draft_report_number}.pdf"
            )

            if not final_path:
                return

            with open(final_path, "wb") as f:
                for chunk in resp.iter_content(8192):
                    if chunk:
                        f.write(chunk)

            messagebox.showinfo(
                "Success",
                "Presentation generated successfully."
            )

        except Exception as e:
            messagebox.showerror("Error", str(e))

    # =====================================================
    # GENERATE UNIFIED REPORT
    # =====================================================
    def _generate_unified(self):

        if not self.report_data:
            messagebox.showwarning(
                "Warning",
                "Debe presionar Buscar primero."
            )
            return

        try:
            from api_client import generate_draft_survey_unified_pdf_api

            resp = generate_draft_survey_unified_pdf_api(
                self.draft_report_number
            )

            if isinstance(resp, dict):
                messagebox.showerror(
                    "Error",
                    resp.get("error", "Unknown error")
                )
                return

            if resp.status_code != 200:
                try:
                    error_json = resp.json()
                    messagebox.showerror(
                        "Error",
                        error_json.get("detail", f"HTTP {resp.status_code}")
                    )
                except Exception:
                    messagebox.showerror(
                        "Error",
                        f"HTTP {resp.status_code}"
                    )
                return

            final_path = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF File", "*.pdf")],
                initialfile=f"{self.draft_report_number}_UNIFIED.pdf"
            )

            if not final_path:
                return

            with open(final_path, "wb") as f:
                for chunk in resp.iter_content(8192):
                    if chunk:
                        f.write(chunk)

            messagebox.showinfo(
                "Success",
                "Unified report generated successfully."
            )

        except Exception as e:
            messagebox.showerror("Error", str(e))


    def _add_pdf(self):

        files = filedialog.askopenfilenames(
            filetypes=[("PDF Files", "*.pdf")]
        )

        if not files:
            return

        for f in files:
            self.pdf_files.append(f)
            self.listbox.insert("end", f.split("/")[-1])


    def _remove_pdf(self):

        sel = self.listbox.curselection()

        if not sel:
            return

        index = sel[0]

        self.listbox.delete(index)
        self.pdf_files.pop(index)

    def _generate_final_full(self):

        if not self.report_data:
            messagebox.showwarning(
                "Warning",
                "Debe presionar Buscar primero."
            )
            return

        try:
            from pypdf import PdfWriter, PdfReader
            import tempfile
            import os

            self.config(cursor="watch")
            self.update_idletasks()

            # =====================================================
            # 1️⃣ PRESENTATION (SIEMPRE PRIMERO)
            # =====================================================
            resp_presentation = generate_draft_survey_presentation_pdf_api(
                self.draft_report_number
            )

            if isinstance(resp_presentation, dict) or resp_presentation.status_code != 200:
                messagebox.showerror("Error", "Error generando Presentation.")
                return

            temp_presentation = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            presentation_path = temp_presentation.name
            temp_presentation.close()

            with open(presentation_path, "wb") as f:
                for chunk in resp_presentation.iter_content(8192):
                    if chunk:
                        f.write(chunk)

            # =====================================================
            # 2️⃣ WORD PDF (SERVICE CORRECTO)
            # =====================================================
            from api_client import generate_draft_survey_word_pdf_api

            resp_word_pdf = generate_draft_survey_word_pdf_api(
                self.draft_report_number
            )

            if not resp_word_pdf or not resp_word_pdf.get("success"):
                try:
                    os.remove(presentation_path)
                except Exception:
                    pass

                messagebox.showerror(
                    "Error",
                    resp_word_pdf.get("message", "Error generando Word PDF.")
                )
                return

            temp_word = tempfile.NamedTemporaryFile(
                delete=False,
                suffix=".pdf"
            )
            word_pdf_path = temp_word.name
            temp_word.close()

            with open(word_pdf_path, "wb") as f:
                f.write(resp_word_pdf["content"])

            # =====================================================
            # 3️⃣ SAVE AS FINAL
            # =====================================================
            save_path = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF File", "*.pdf")],
                initialfile=f"{self.draft_report_number}_FINAL.pdf"
            )

            if not save_path:
                os.remove(presentation_path)
                os.remove(word_pdf_path)
                return

            writer = PdfWriter()

            # =====================================================
            # 4️⃣ MERGE ORDEN CORRECTO
            # =====================================================

            # A) PRESENTATION
            reader_presentation = PdfReader(presentation_path)
            for page in reader_presentation.pages:
                writer.add_page(page)

            # B) WORD PDF COMPLETO (YA NO CORTAMOS PÁGINAS)
            reader_word = PdfReader(word_pdf_path)
            for page in reader_word.pages:
                writer.add_page(page)

            # C) PDFs DEL USUARIO (AL FINAL)
            for pdf in self.pdf_files:

                if not os.path.exists(pdf):
                    continue

                try:
                    reader = PdfReader(pdf)
                    for page in reader.pages:
                        writer.add_page(page)
                except Exception:
                    messagebox.showwarning(
                        "PDF inválido",
                        f"Se omitió:\n{pdf}"
                    )

            # =====================================================
            # 5️⃣ WRITE FINAL
            # =====================================================
            with open(save_path, "wb") as f:
                writer.write(f)

            writer.close()

            # =====================================================
            # CLEANUP
            # =====================================================
            try:
                os.remove(presentation_path)
            except Exception:
                pass

            try:
                os.remove(word_pdf_path)
            except Exception:
                pass

            messagebox.showinfo(
                "Success",
                "Informe final generado correctamente."
            )

            os.startfile(save_path)

        except Exception as e:
            messagebox.showerror("Error", str(e))

        finally:
            self.config(cursor="")


    def _bind_mousewheel(self, widget):

        def _on_mousewheel(event):
            widget.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _on_mousewheel_linux_up(event):
            widget.yview_scroll(-1, "units")

        def _on_mousewheel_linux_down(event):
            widget.yview_scroll(1, "units")

        widget.bind_all("<MouseWheel>", _on_mousewheel)
        widget.bind_all("<Button-4>", _on_mousewheel_linux_up)
        widget.bind_all("<Button-5>", _on_mousewheel_linux_down)

