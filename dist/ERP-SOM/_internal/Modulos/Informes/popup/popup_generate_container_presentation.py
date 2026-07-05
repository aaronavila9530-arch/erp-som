import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkcalendar import DateEntry

from api_client import (
    get_container_presentation_data_api,
    generate_container_presentation_pdf_api,
    generate_container_unified_pdf_api
)
from Modulos.Informes.date_utils import to_long_english_date


class PopupGenerateContainerPresentation(tk.Toplevel):
    """
    Popup — Generate Container Presentation
    Datos cargados SOLO bajo acción explícita (Buscar)
    """

    def __init__(self, parent, container_report_id: int):
        super().__init__(parent)

        self.parent = parent
        self.container_report_id = container_report_id
        self._data_loaded = False

        self.title("Generate Container Presentation")
        self.geometry("520x430")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        # =====================================================
        # MAIN FRAME
        # =====================================================
        main = ttk.Frame(self, padding=16)
        main.pack(fill="both", expand=True)

        # =====================================================
        # VARIABLES
        # =====================================================
        self.var_cert_no = tk.StringVar()
        self.var_container = tk.StringVar()
        self.var_to = tk.StringVar()
        self.var_place = tk.StringVar()
        self.var_date = tk.StringVar()

        # =====================================================
        # SEARCH BUTTON (TOP — SOLO)
        # =====================================================
        ttk.Button(
            main,
            text="Buscar",
            command=self._on_search
        ).grid(row=0, column=0, sticky="w", pady=(0, 12))

        # =====================================================
        # FORM
        # =====================================================
        row = 1

        ttk.Label(main, text="CERT No.").grid(row=row, column=0, sticky="w")
        ttk.Entry(main, textvariable=self.var_cert_no, state="readonly", width=40)\
            .grid(row=row + 1, column=0, sticky="w", pady=(0, 10))
        row += 2

        ttk.Label(main, text="CONTAINER").grid(row=row, column=0, sticky="w")
        ttk.Entry(main, textvariable=self.var_container, state="readonly", width=40)\
            .grid(row=row + 1, column=0, sticky="w", pady=(0, 10))
        row += 2

        ttk.Label(main, text="TO").grid(row=row, column=0, sticky="w")
        ttk.Entry(main, textvariable=self.var_to, state="readonly", width=40)\
            .grid(row=row + 1, column=0, sticky="w", pady=(0, 10))
        row += 2

        ttk.Label(main, text="PLACE").grid(row=row, column=0, sticky="w")
        ttk.Entry(main, textvariable=self.var_place, state="readonly", width=40)\
            .grid(row=row + 1, column=0, sticky="w", pady=(0, 10))
        row += 2

        ttk.Label(main, text="DATE").grid(row=row, column=0, sticky="w")
        DateEntry(
            main,
            textvariable=self.var_date,
            date_pattern="yyyy-mm-dd",
            state="readonly",
            width=18
        ).grid(row=row + 1, column=0, sticky="w", pady=(0, 14))

        # =====================================================
        # ACTION BUTTONS
        # =====================================================
        actions = ttk.Frame(main)
        actions.grid(row=row + 2, column=0, sticky="e", pady=(10, 0))

        self.btn_generate_presentation = ttk.Button(
            actions,
            text="Generate Presentation",
            command=self._generate_presentation,
            state="disabled"
        )
        self.btn_generate_presentation.pack(side="left", padx=6)

        self.btn_generate_unified = ttk.Button(
            actions,
            text="Generate Unified Report",
            command=self._generate_unified_report,
            state="disabled"
        )
        self.btn_generate_unified.pack(side="left")

    # =====================================================
    # ACTIONS
    # =====================================================
    def _on_search(self):
        try:
            response = get_container_presentation_data_api(
                self.container_report_id
            )

            data = response.json()  # 🔴 FIX CRÍTICO

            self.var_cert_no.set(data.get("cert_no") or "")
            self.var_container.set(data.get("container") or "")
            self.var_to.set(data.get("to") or "")
            self.var_place.set(data.get("place") or "")
            self.var_date.set(to_long_english_date(data.get("date")) or "")

            self._data_loaded = True
            self.btn_generate_presentation.config(state="normal")
            self.btn_generate_unified.config(state="normal")

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Unable to load presentation data.\n\n{e}"
            )

    def _save_stream_to_file(self, response, default_name: str):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            initialfile=default_name,
            filetypes=[("PDF files", "*.pdf")]
        )
        if not file_path:
            return

        with open(file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        messagebox.showinfo(
            "Success",
            f"PDF generated successfully:\n\n{file_path}"
        )

    def _generate_presentation(self):
        if not self._data_loaded:
            return

        try:
            response = generate_container_presentation_pdf_api(
                self.container_report_id
            )
            self._save_stream_to_file(
                response,
                "container_presentation.pdf"
            )

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Unable to generate presentation PDF.\n\n{e}"
            )

    def _generate_unified_report(self):
        if not self._data_loaded:
            return

        try:
            response = generate_container_unified_pdf_api(
                self.container_report_id
            )
            self._save_stream_to_file(
                response,
                "container_report_unified.pdf"
            )

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Unable to generate unified report.\n\n{e}"
            )
