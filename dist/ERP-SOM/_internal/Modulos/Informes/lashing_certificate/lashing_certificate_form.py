import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from tkcalendar import DateEntry

from Modulos.Informes.informes_home_ui import InformesHomeUI
from Modulos.Informes.Vessel_Draft_Survey.popup_servicio_draft_selector import PopupServicioDraftSelector
from Modulos.Informes.date_utils import to_db_date, to_long_english_date

import api_client


class LashingCertificateForm(ttk.Frame):

    # =========================================================
    # INIT
    # =========================================================
    def __init__(self, parent, usuario=None, rol=None, record=None, on_back=None):

        super().__init__(parent)

        self.parent = parent
        self.usuario = usuario
        self.rol = rol
        self.record = record
        self.on_back = on_back

        self.vars = {}
        self.record_id = None
        self.edit_mode = False

        self.pack(fill="both", expand=True)

        self._build_scrollable()
        self._build_ui()

        if self.record:
            try:
                record_id = self.record.get("id")
                if record_id:
                    self.load_record(record_id)
                    self.set_edit_mode(record_id)
            except Exception:
                pass

    # =========================================================
    # SCROLL
    # =========================================================
    def _build_scrollable(self):

        self.canvas = tk.Canvas(self, highlightthickness=0, bd=0)

        self.scrollbar = ttk.Scrollbar(
            self,
            orient="vertical",
            command=self.canvas.yview
        )

        self.scroll_frame = ttk.Frame(self.canvas)

        self.scroll_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        self.canvas_window = self.canvas.create_window(
            (0, 0),
            window=self.scroll_frame,
            anchor="nw"
        )

        self.canvas.configure(
            yscrollcommand=self.scrollbar.set
        )

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.canvas.bind("<Configure>", self._on_canvas_configure)

        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel_linux_up)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel_linux_down)

    def _on_canvas_configure(self, event=None):

        try:
            self.canvas.itemconfig(
                self.canvas_window,
                width=self.canvas.winfo_width()
            )
        except Exception:
            pass

    def _on_mousewheel(self, event):

        try:
            self.canvas.yview_scroll(
                int(-1 * (event.delta / 120)),
                "units"
            )
        except Exception:
            pass

    def _on_mousewheel_linux_up(self, event):

        try:
            self.canvas.yview_scroll(-1, "units")
        except Exception:
            pass

    def _on_mousewheel_linux_down(self, event):

        try:
            self.canvas.yview_scroll(1, "units")
        except Exception:
            pass

    # =========================================================
    # UI
    # =========================================================
    def _build_ui(self):

        frame = ttk.Frame(self.scroll_frame, padding=20)
        frame.pack(fill="both", expand=True)

        ttk.Label(
            frame,
            text="Cargo Lashing Certificate",
            font=("Segoe UI", 16, "bold")
        ).pack(anchor="center", pady=(0, 20))

        # =====================================================
        # TOP BAR
        # =====================================================

        top = ttk.Frame(frame)
        top.pack(fill="x", pady=(0, 20))

        left = ttk.Frame(top)
        left.pack(side="left", fill="x", expand=True)

        ttk.Button(
            left,
            text="HOME",
            command=self._go_home
        ).pack(side="left")

        ttk.Button(
            left,
            text="SELECT REPORT",
            command=self._open_report_selector
        ).pack(side="left", padx=10)

        right = ttk.Frame(top)
        right.pack(side="right")

        self.btn_send = ttk.Button(
            right,
            text="Enviar a Revisión",
            command=self._send_review
        )
        self.btn_send.pack()

        self.btn_edit = ttk.Button(
            right,
            text="Editar",
            command=self._enable_edit_mode
        )

        self.btn_save_changes = ttk.Button(
            right,
            text="Guardar Cambios",
            command=self._save_changes
        )

        # =====================================================
        # HEADER
        # =====================================================

        header = ttk.LabelFrame(frame, text="Report Header")
        header.pack(fill="x", pady=10)

        self.vars["report_no"] = tk.StringVar()
        self.vars["customer"] = tk.StringVar()
        self.vars["port"] = tk.StringVar()
        self.vars["country"] = tk.StringVar()

        self._field(header, "Report No", "report_no", 0)
        self._field(header, "Customer", "customer", 1)
        self._field(header, "Port", "port", 2)
        self._field(header, "Country", "country", 3)

        # =====================================================
        # LASHING SECTION
        # =====================================================

        section = ttk.LabelFrame(frame, text="Lashing Details")
        section.pack(fill="x", pady=10)

        self.vars["flat_rack_container"] = tk.StringVar()
        self.vars["cargo_type"] = tk.StringVar()
        self.vars["lashing_material"] = tk.StringVar()
        self.vars["place"] = tk.StringVar()

        self._field(section, "Flat Rack Container No", "flat_rack_container", 0)
        self._field(section, "Type of Cargo", "cargo_type", 1)
        self._field(section, "Lashing Material", "lashing_material", 2)

        # DATE LONG ENGLISH
        ttk.Label(section, text="Date").grid(
            row=3, column=0, sticky="w", padx=8, pady=6
        )

        self.date_var = tk.StringVar()

        self.date_entry = DateEntry(
            section,
            width=30,
            textvariable=self.date_var
        )

        self.date_entry.grid(
            row=3, column=1,
            sticky="w",
            padx=8,
            pady=6
        )

        self.date_entry.bind(
            "<<DateEntrySelected>>",
            self._set_long_date
        )

        self._field(section, "Place", "place", 4)

        # =====================================================
        # RATChet SECTION
        # =====================================================

        ratchet = ttk.LabelFrame(frame, text="Ratchet Lashings")
        ratchet.pack(fill="x", pady=10)

        self.vars["ratchet_quantity"] = tk.StringVar()
        self.vars["where_carry_out"] = tk.StringVar()
        self.vars["completion_date"] = tk.StringVar()

        self._field(ratchet, "Ratchet Lashing Quantity", "ratchet_quantity", 0)
        self._field(ratchet, "Where Was Carry Out", "where_carry_out", 1)

        ttk.Label(ratchet, text="Completion Date").grid(
            row=2, column=0, sticky="w", padx=8, pady=6
        )

        self.completion_date_entry = DateEntry(
            ratchet,
            width=30,
            textvariable=self.vars["completion_date"]
        )

        self.completion_date_entry.grid(
            row=2,
            column=1,
            sticky="w",
            padx=8,
            pady=6
        )

        self.completion_date_entry.bind(
            "<<DateEntrySelected>>",
            self._set_long_completion_date
        )

        self._set_long_date()
        self._set_long_completion_date()

    # =========================================================
    # FIELD HELPER
    # =========================================================
    def _field(self, parent, label, var, row):

        ttk.Label(parent, text=label).grid(
            row=row,
            column=0,
            sticky="w",
            padx=8,
            pady=6
        )

        ttk.Entry(
            parent,
            textvariable=self.vars[var],
            width=40
        ).grid(
            row=row,
            column=1,
            sticky="w",
            padx=8,
            pady=6
        )

    # =========================================================
    # REPORT SELECTOR
    # =========================================================
    def _open_report_selector(self):

        PopupServicioDraftSelector(
            self,
            self._fill_from_report
        )

    def _fill_from_report(self, values):

        if not values:
            return

        (
            num_informe,
            vessel,
            cliente,
            continente,
            pais,
            puerto,
            operacion,
            fecha_inicio
        ) = values

        self.vars["report_no"].set(num_informe or "")
        self.vars["customer"].set(cliente or "")
        self.vars["port"].set(puerto or "")
        self.vars["country"].set(pais or "")

    # =========================================================
    # HOME
    # =========================================================
    def _go_home(self):

        try:

            for child in self.parent.winfo_children():
                child.destroy()

            InformesHomeUI(
                self.parent,
                usuario=self.usuario,
                rol=self.rol
            )

        except Exception as e:

            messagebox.showerror(
                "ERP-SOM",
                str(e)
            )

    # =========================================================
    # DATE FORMAT LONG ENGLISH
    # =========================================================
    def _set_long_date(self, event=None):

        try:
            d = self.date_entry.get_date()
            text = to_long_english_date(d)

            self.date_var.set(text)
            self.date_entry.delete(0, "end")
            self.date_entry.insert(0, text)

        except Exception:
            pass

    def _set_long_completion_date(self, event=None):

        try:

            d = self.completion_date_entry.get_date()
            text = to_long_english_date(d)

            self.vars["completion_date"].set(text)

            self.completion_date_entry.delete(0, "end")
            self.completion_date_entry.insert(0, text)

        except Exception:
            pass

    # =========================================================
    # SEND REVIEW (POST)
    # =========================================================
    def _send_review(self):

        try:

            payload = self._build_payload()

            # Nuevo registro siempre inicia como Draft
            payload["status"] = "Draft"

            response = api_client.create_lashing_certificate_api(payload)

            record_id = None

            if isinstance(response, dict):
                record_id = response.get("id")

            elif isinstance(response, list):
                if len(response) > 0 and isinstance(response[0], dict):
                    record_id = response[0].get("id")

            if not record_id:
                raise Exception("Unexpected API response")

            self.record_id = record_id

            messagebox.showinfo(
                "ERP-SOM",
                "Certificate sent for review successfully."
            )

            # Cambiar a modo edición
        except Exception as e:

            messagebox.showerror(
                "ERP-SOM",
                str(e)
            )


    # =========================================================
    # EDIT MODE
    # =========================================================
    def set_edit_mode(self, record_id):

        self.record_id = record_id
        self.edit_mode = True

        self.btn_send.pack_forget()
        self.btn_edit.pack(side="left", padx=4)
        self.btn_save_changes.pack(side="left", padx=4)

    def _enable_edit_mode(self):
        self.btn_save_changes.config(state="normal")

    # =========================================================
    # SAVE CHANGES (PUT)
    # =========================================================
    def _save_changes(self):

        try:

            if not self.record_id:
                raise Exception("Record ID not defined")

            payload = self._build_payload()

            response = api_client.update_lashing_certificate_api(
                self.record_id,
                payload
            )

            messagebox.showinfo(
                "ERP-SOM",
                "Changes saved successfully."
            )

        except Exception as e:

            messagebox.showerror(
                "ERP-SOM",
                str(e)
            )


    # =========================================================
    # LOAD RECORD (GET ID)
    # =========================================================
    def load_record(self, record_id):

        try:

            data = api_client.get_lashing_certificate_api(record_id)

            if not data:
                raise Exception("Record not found")

            # cargar variables normales
            for key, var in self.vars.items():

                if key in data and data[key] is not None:
                    var.set(str(data[key]))
                else:
                    var.set("")

            # sincronizar DateEntry principal
            if data.get("date"):
                self.date_var.set(str(data["date"]))
                try:
                    self.date_entry.delete(0, "end")
                    self.date_entry.insert(0, str(data["date"]))
                except Exception:
                    pass

            # sincronizar completion_date
            if data.get("completion_date"):
                self.vars["completion_date"].set(str(data["completion_date"]))
                try:
                    self.completion_date_entry.delete(0, "end")
                    self.completion_date_entry.insert(0, str(data["completion_date"]))
                except Exception:
                    pass

        except Exception as e:

            messagebox.showerror(
                "ERP-SOM",
                f"Unable to load record:\n{str(e)}"
            )



    # =========================================================
    # BUILD PAYLOAD (POST / PUT)
    # =========================================================
    def _build_payload(self):

        payload = {}

        for key, var in self.vars.items():

            value = (var.get() or "").strip()

            if value == "":
                payload[key] = None
            else:
                payload[key] = value

        # asegurar formato de fechas
        try:
            payload["date"] = to_db_date(self.date_var.get()) or None
        except Exception:
            payload["date"] = None

        try:
            payload["completion_date"] = to_db_date(self.vars["completion_date"].get()) or None
        except Exception:
            payload["completion_date"] = None

        return payload

