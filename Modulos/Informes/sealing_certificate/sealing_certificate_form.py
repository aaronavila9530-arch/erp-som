import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from tkcalendar import DateEntry

from Modulos.Informes.informes_home_ui import InformesHomeUI
from Modulos.Informes.Vessel_Draft_Survey.popup_servicio_draft_selector import PopupServicioDraftSelector
from Modulos.Informes.date_utils import to_db_date, to_long_english_date

import api_client


class SealingCertificateForm(ttk.Frame):

    MAX_HOLDS = 6

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
        self.hold_fields = {}
        self.record_id = None
        self.edit_mode = False

        self.pack(fill="both", expand=True)

        self._build_scrollable()
        self._build_ui()

        # Cargar registro si viene desde tabla
        if self.record:
            try:
                record_id = self.record.get("id")
                if record_id:
                    self.load_record(record_id)
                    self.set_edit_mode(record_id)
            except Exception:
                pass

    # =========================================================
    # SCROLLABLE FRAME
    # =========================================================
    def _build_scrollable(self):

        self.canvas = tk.Canvas(
            self,
            highlightthickness=0,
            bd=0
        )

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

        self.canvas.pack(
            side="left",
            fill="both",
            expand=True
        )

        self.scrollbar.pack(
            side="right",
            fill="y"
        )

        self.canvas.bind(
            "<Configure>",
            self._on_canvas_configure
        )

        # Mouse wheel Windows / Mac
        self.canvas.bind_all(
            "<MouseWheel>",
            self._on_mousewheel
        )

        # Linux
        self.canvas.bind_all(
            "<Button-4>",
            self._on_mousewheel_linux_up
        )

        self.canvas.bind_all(
            "<Button-5>",
            self._on_mousewheel_linux_down
        )

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

        # =====================================================
        # FORM TITLE
        # =====================================================
        ttk.Label(
            frame,
            text="Sealing Certificate Form",
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
            text="Enviar a RevisiÃ³n",
            command=self._send_review
        )
        self.btn_send.pack(side="left", padx=4)

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
        self.vars["port"] = tk.StringVar()
        self.vars["country"] = tk.StringVar()
        self.vars["customer"] = tk.StringVar()

        self._field(header, "Report No", "report_no", 0)
        self._field(header, "Port", "port", 1)
        self._field(header, "Country", "country", 2)
        self._field(header, "Customer", "customer", 3)

        # =====================================================
        # SEALING CERTIFICATE HEADER
        # =====================================================
        cert = ttk.LabelFrame(frame, text="Sealing Certificate")
        cert.pack(fill="x", pady=10)

        cert.grid_columnconfigure(0, weight=0)
        cert.grid_columnconfigure(1, weight=1)
        cert.grid_columnconfigure(2, weight=0)
        cert.grid_columnconfigure(3, weight=1)

        self.vars["certificate_no"] = tk.StringVar()
        self.vars["vessel"] = tk.StringVar()
        self.vars["location"] = tk.StringVar()
        self.vars["cargo"] = tk.StringVar()

        ttk.Label(cert, text="Certificate No").grid(
            row=0, column=0, sticky="w", padx=8, pady=6
        )
        ttk.Entry(
            cert,
            textvariable=self.vars["certificate_no"],
            width=35
        ).grid(
            row=0, column=1, sticky="w", padx=8, pady=6
        )

        ttk.Label(cert, text="Vessel").grid(
            row=1, column=0, sticky="w", padx=8, pady=6
        )
        ttk.Entry(
            cert,
            textvariable=self.vars["vessel"],
            width=45
        ).grid(
            row=1, column=1, sticky="w", padx=8, pady=6
        )

        ttk.Label(cert, text="Date").grid(
            row=1, column=2, sticky="w", padx=8, pady=6
        )

        self.date_var = tk.StringVar()

        self.date_entry = DateEntry(
            cert,
            width=24,
            textvariable=self.date_var,
            date_pattern="yyyy-mm-dd"
        )
        self.date_entry.grid(
            row=1, column=3, sticky="w", padx=8, pady=6
        )

        self.date_entry.bind(
            "<<DateEntrySelected>>",
            self._set_long_date
        )
        self.date_entry.bind(
            "<FocusOut>",
            self._set_long_date
        )

        ttk.Label(cert, text="Location").grid(
            row=2, column=0, sticky="w", padx=8, pady=6
        )
        ttk.Entry(
            cert,
            textvariable=self.vars["location"],
            width=45
        ).grid(
            row=2, column=1, sticky="w", padx=8, pady=6
        )

        ttk.Label(cert, text="Cargo").grid(
            row=2, column=2, sticky="w", padx=8, pady=6
        )
        ttk.Entry(
            cert,
            textvariable=self.vars["cargo"],
            width=30
        ).grid(
            row=2, column=3, sticky="w", padx=8, pady=6
        )

        # =====================================================
        # SEALS TEXT
        # =====================================================
        intro = ttk.LabelFrame(frame, text="Seal Placement")
        intro.pack(fill="x", pady=10)

        ttk.Label(
            intro,
            text="The seals of hatch covers were placed in Port/Std. Side positions.",
            font=("Segoe UI", 10)
        ).pack(anchor="w", padx=10, pady=10)

        # =====================================================
        # HOLDS
        # =====================================================
        holds_frame = ttk.LabelFrame(frame, text="Holds")
        holds_frame.pack(fill="x", pady=10)

        holds_frame.grid_columnconfigure(0, weight=1)
        holds_frame.grid_columnconfigure(1, weight=1)

        for hold_no in range(1, self.MAX_HOLDS + 1):

            container = ttk.LabelFrame(
                holds_frame,
                text=f"HOLD #{hold_no}"
            )

            row = 0 if hold_no <= 3 else 1
            col = (hold_no - 1) if hold_no <= 3 else (hold_no - 4)

            container.grid(
                row=row,
                column=col,
                sticky="nsew",
                padx=8,
                pady=8
            )

            container.grid_columnconfigure(0, weight=0)
            container.grid_columnconfigure(1, weight=1)

            fwd_escape_key = f"hold_{hold_no}_fwd_escape"
            fwd_aft_hatch_key = f"hold_{hold_no}_fwd_aft_hatch"
            aft_escape_key = f"hold_{hold_no}_aft_escape"

            self.vars[fwd_escape_key] = tk.StringVar()
            self.vars[fwd_aft_hatch_key] = tk.StringVar()
            self.vars[aft_escape_key] = tk.StringVar()

            ttk.Label(
                container,
                text="FWD ESCAPE"
            ).grid(
                row=0,
                column=0,
                sticky="w",
                padx=8,
                pady=4
            )

            ttk.Entry(
                container,
                textvariable=self.vars[fwd_escape_key],
                width=18
            ).grid(
                row=0,
                column=1,
                sticky="w",
                padx=8,
                pady=4
            )

            ttk.Label(
                container,
                text="FWD/AFT HATCH"
            ).grid(
                row=1,
                column=0,
                sticky="w",
                padx=8,
                pady=4
            )

            ttk.Entry(
                container,
                textvariable=self.vars[fwd_aft_hatch_key],
                width=18
            ).grid(
                row=1,
                column=1,
                sticky="w",
                padx=8,
                pady=4
            )

            ttk.Label(
                container,
                text="AFT ESCAPE"
            ).grid(
                row=2,
                column=0,
                sticky="w",
                padx=8,
                pady=4
            )

            ttk.Entry(
                container,
                textvariable=self.vars[aft_escape_key],
                width=18
            ).grid(
                row=2,
                column=1,
                sticky="w",
                padx=8,
                pady=4
            )

            self.hold_fields[hold_no] = {
                "fwd_escape": self.vars[fwd_escape_key],
                "fwd_aft_hatch": self.vars[fwd_aft_hatch_key],
                "aft_escape": self.vars[aft_escape_key]
            }

        # =====================================================
        # REMARKS
        # =====================================================
        remarks_frame = ttk.LabelFrame(frame, text="Remarks")
        remarks_frame.pack(fill="both", expand=True, pady=10)

        self.remarks_text = tk.Text(
            remarks_frame,
            height=8,
            wrap="word"
        )
        self.remarks_text.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=10
        )

        # =====================================================
        # WITNESSED / CLOSING
        # =====================================================
        closing = ttk.LabelFrame(frame, text="Witnessed / Closing")
        closing.pack(fill="x", pady=10)

        closing.grid_columnconfigure(0, weight=0)
        closing.grid_columnconfigure(1, weight=1)
        closing.grid_columnconfigure(2, weight=0)
        closing.grid_columnconfigure(3, weight=1)

        self.vars["chief_officer"] = tk.StringVar()

        ttk.Label(
            closing,
            text="Chief Officer"
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=8,
            pady=6
        )

        ttk.Entry(
            closing,
            textvariable=self.vars["chief_officer"],
            width=45
        ).grid(
            row=0,
            column=1,
            sticky="w",
            padx=8,
            pady=6
        )

        ttk.Label(
            closing,
            text="Date"
        ).grid(
            row=0,
            column=2,
            sticky="w",
            padx=8,
            pady=6
        )

        self.closing_date_var = tk.StringVar()

        self.closing_date_entry = DateEntry(
            closing,
            width=24,
            textvariable=self.closing_date_var,
            date_pattern="yyyy-mm-dd"
        )
        self.closing_date_entry.grid(
            row=0,
            column=3,
            sticky="w",
            padx=8,
            pady=6
        )

        self.closing_date_entry.bind(
            "<<DateEntrySelected>>",
            self._set_long_closing_date
        )
        self.closing_date_entry.bind(
            "<FocusOut>",
            self._set_long_closing_date
        )

        ttk.Label(
            closing,
            text="Time"
        ).grid(
            row=1,
            column=2,
            sticky="w",
            padx=8,
            pady=6
        )

        time_frame = ttk.Frame(closing)
        time_frame.grid(
            row=1,
            column=3,
            sticky="w",
            padx=8,
            pady=6
        )

        self.hour_var = tk.StringVar()
        self.minute_var = tk.StringVar()

        self.hour_entry = ttk.Entry(
            time_frame,
            textvariable=self.hour_var,
            width=6
        )
        self.hour_entry.pack(side="left")

        ttk.Label(
            time_frame,
            text=":"
        ).pack(side="left", padx=4)

        self.minute_entry = ttk.Entry(
            time_frame,
            textvariable=self.minute_var,
            width=6
        )
        self.minute_entry.pack(side="left")

        ttk.Label(
            time_frame,
            text="Hours"
        ).pack(side="left", padx=(8, 0))

        # =====================================================
        # INITIAL LONG DATES
        # =====================================================
        self._set_long_date()
        self._set_long_closing_date()

    # =========================================================
    # FIELD HELPER
    # =========================================================
    def _field(self, parent, label, var, row):

        ttk.Label(
            parent,
            text=label
        ).grid(
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
    # SELECT REPORT
    # =========================================================
    def _open_report_selector(self):

        try:
            PopupServicioDraftSelector(
                self,
                self._fill_from_report
            )
        except Exception as e:
            messagebox.showerror(
                "ERP-SOM",
                f"Unable to open report selector:\n{str(e)}"
            )

    def _fill_from_report(self, values):

        if not values:
            return

        try:
            (
                num_informe,
                buque,
                cliente,
                continente,
                pais,
                puerto,
                operacion,
                fecha_inicio
            ) = values

            self.vars["report_no"].set(num_informe or "")
            self.vars["port"].set(puerto or "")
            self.vars["country"].set(pais or "")
            self.vars["customer"].set(cliente or "")

            self.vars["certificate_no"].set(num_informe or "")
            self.vars["vessel"].set(buque or "")

            location_parts = []
            if puerto:
                location_parts.append(puerto)
            if pais:
                location_parts.append(pais)

            self.vars["location"].set(", ".join(location_parts))

        except Exception as e:
            messagebox.showerror(
                "ERP-SOM",
                f"Unable to fill report data:\n{str(e)}"
            )

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
                f"Unable to return to Informes Home:\n{str(e)}"
            )

    # =========================================================
    # DATE HELPERS
    # =========================================================
    def _set_dateentry_long_text(self, widget, string_var):

        try:
            d = widget.get_date()
            long_date = to_long_english_date(d)

            try:
                string_var.set(long_date)
            except Exception:
                pass

            try:
                widget.delete(0, "end")
                widget.insert(0, long_date)
            except Exception:
                pass

        except Exception:
            pass

    def _set_long_date(self, event=None):

        self._set_dateentry_long_text(
            self.date_entry,
            self.date_var
        )

    def _set_long_closing_date(self, event=None):

        self._set_dateentry_long_text(
            self.closing_date_entry,
            self.closing_date_var
        )

    def _normalize_date_value(self, value):

        if not value:
            return None

        value = str(value).strip()

        if not value:
            return None

        # Intentar parsear formatos comunes
        formats = [
            "%B %d, %Y",
            "%b %d, %Y",
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%m/%d/%Y",
            "%d-%m-%Y",
            "%Y/%m/%d"
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(value, fmt)
                return dt
            except Exception:
                continue

        return None

    def _set_widget_date_from_value(self, widget, string_var, value):

        try:
            parsed = self._normalize_date_value(value)

            if parsed:
                widget.set_date(parsed)
                long_date = to_long_english_date(parsed)
                string_var.set(long_date)

                try:
                    widget.delete(0, "end")
                    widget.insert(0, long_date)
                except Exception:
                    pass
            else:
                string_var.set(str(value).strip())
                try:
                    widget.delete(0, "end")
                    widget.insert(0, str(value).strip())
                except Exception:
                    pass

        except Exception:
            try:
                string_var.set(str(value).strip())
            except Exception:
                pass

    # =========================================================
    # TIME HELPERS
    # =========================================================
    def _build_time_value(self):

        hour = (self.hour_var.get() or "").strip()
        minute = (self.minute_var.get() or "").strip()

        if not hour and not minute:
            return None

        if not hour.isdigit() or not minute.isdigit():
            raise ValueError("Time must contain only numeric values.")

        hh = int(hour)
        mm = int(minute)

        if hh < 0 or hh > 23:
            raise ValueError("Hour must be between 00 and 23.")

        if mm < 0 or mm > 59:
            raise ValueError("Minute must be between 00 and 59.")

        return f"{hh:02d}:{mm:02d}"

    def _load_time_value(self, value):

        if not value:
            self.hour_var.set("")
            self.minute_var.set("")
            return

        text = str(value).strip()

        if ":" in text:
            parts = text.split(":")
            if len(parts) >= 2:
                self.hour_var.set(parts[0].strip())
                self.minute_var.set(parts[1].strip())
                return

        self.hour_var.set("")
        self.minute_var.set("")

    # =========================================================
    # BUILD PAYLOAD
    # =========================================================
    def _build_payload(self):

        payload = {}

        # Variables normales
        for key, var in self.vars.items():

            value = (var.get() or "").strip()
            payload[key] = value if value else None

        # Dates
        payload["date"] = to_db_date(self.date_var.get()) or None
        payload["closing_date"] = to_db_date(self.closing_date_var.get()) or None

        # Remarks
        try:
            remarks = self.remarks_text.get("1.0", "end").strip()
            payload["remarks"] = remarks if remarks else None
        except Exception:
            payload["remarks"] = None

        # Time
        payload["closing_time"] = self._build_time_value()

        return payload

    # =========================================================
    # SEND REVIEW (POST)
    # =========================================================
    def _send_review(self):

        try:

            payload = self._build_payload()

            response = api_client.create_sealing_certificate_api(
                payload
            )

            # -------------------------------------------------
            # BLINDAR RESPUESTA
            # -------------------------------------------------
            record_id = None

            if isinstance(response, dict):

                record_id = response.get("id")

            elif isinstance(response, list):

                if len(response) > 0:

                    first = response[0]

                    if isinstance(first, dict):
                        record_id = first.get("id")

                    elif isinstance(first, int):
                        record_id = first

                else:
                    # lista vacÃ­a -> asumir Ã©xito
                    record_id = True

            # -------------------------------------------------
            # VALIDAR RESPUESTA
            # -------------------------------------------------
            if not record_id:

                raise Exception(
                    f"Unexpected response from API: {response}"
                )

            self.record_id = record_id if isinstance(record_id, int) else None

            messagebox.showinfo(
                "ERP-SOM",
                "Sealing Certificate sent for review successfully."
            )

        except Exception as e:

            messagebox.showerror(
                "ERP-SOM",
                f"Error sending to review:\n{str(e)}"
            )


    # =========================================================
    # SAVE CHANGES (PUT)
    # =========================================================
    def _save_changes(self):

        try:

            if not self.record_id:
                raise Exception("Record ID not defined.")

            payload = self._build_payload()

            api_client.update_sealing_certificate_api(
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
                f"Error saving changes:\n{str(e)}"
            )


    # =========================================================
    # LOAD RECORD (GET BY ID)
    # =========================================================
    def load_record(self, record_id):

        try:

            data = api_client.get_sealing_certificate_api(
                record_id
            )

            if not data:
                raise Exception("Record not found.")

            # =========================
            # VARIABLES
            # =========================
            for key, var in self.vars.items():

                if key in data and data[key] is not None:
                    var.set(str(data[key]))
                else:
                    var.set("")

            # =========================
            # DATE
            # =========================
            self._set_widget_date_from_value(
                self.date_entry,
                self.date_var,
                data.get("date")
            )

            self._set_widget_date_from_value(
                self.closing_date_entry,
                self.closing_date_var,
                data.get("closing_date")
            )

            # =========================
            # TIME
            # =========================
            self._load_time_value(
                data.get("closing_time")
            )

            # =========================
            # REMARKS
            # =========================
            try:

                self.remarks_text.delete("1.0", "end")

                if data.get("remarks"):
                    self.remarks_text.insert(
                        "1.0",
                        data.get("remarks")
                    )

            except Exception:
                pass

        except Exception as e:

            messagebox.showerror(
                "ERP-SOM",
                f"Unable to load record:\n{str(e)}"
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
