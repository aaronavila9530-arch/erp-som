import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from datetime import datetime

from Modulos.Informes.Vessel_Draft_Survey.popup_servicio_draft_selector import PopupServicioDraftSelector
from Modulos.Informes.informes_home_ui import InformesHomeUI
from Modulos.Informes.date_utils import to_db_date, to_long_english_date

from api_client import (
    create_vessel_holds_certificate_api,
    update_vessel_holds_certificate_api,
    get_vessel_holds_certificate_api
)


class VesselHoldsInspectionCertificateForm(ttk.Frame):

    def __init__(self, parent, usuario=None, rol=None, on_back=None, record_id=None):

        super().__init__(parent)

        self.parent = parent
        self.usuario = usuario
        self.rol = rol
        self.on_back = on_back

        self.record_id = record_id
        self.edit_mode = False

        self.vars = {}

        self.pack(fill="both", expand=True)

        self._build_ui()

        # si viene desde tabla
        if self.record_id:
            self.set_edit_mode(self.record_id)
            self._load_record(self.record_id)

    # =========================================================
    # VAR HELPER
    # =========================================================

    def _v(self, key):

        if key not in self.vars:
            self.vars[key] = tk.StringVar()

        return self.vars[key]

    # =========================================================
    # BUILD UI
    # =========================================================

    def _build_ui(self):

        self._build_topbar()
        self._build_scrollable()

        self._build_report_header()
        self._build_certificate_header()
        self._build_survey_section()
        self._build_cargo_section()
        self._build_location_section()
        self._build_hose_test()
        self._build_remarks()

    # =========================================================
    # TOPBAR (NO TOCADO)
    # =========================================================

    def _build_topbar(self):

        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=10, pady=(10, 0))

        left = ttk.Frame(bar)
        left.pack(side="left", fill="x", expand=True)

        ttk.Label(
            left,
            text="VESSEL HOLDS INSPECTION CERTIFICATE",
            font=("Segoe UI", 14, "bold")
        ).pack(side="left")

        right = ttk.Frame(bar)
        right.pack(side="right")

        ttk.Button(
            right,
            text="Seleccionar Informe",
            command=self._select_service
        ).pack(side="left", padx=4)

        self.btn_send = ttk.Button(
            right,
            text="Enviar a Revisión",
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

        ttk.Button(
            right,
            text="Home",
            command=self._go_home
        ).pack(side="left", padx=4)

    # =========================================================
    # SCROLLABLE
    # =========================================================

    def _build_scrollable(self):

        container = ttk.Frame(self)
        container.pack(fill="both", expand=True, padx=10, pady=10)

        self.canvas = tk.Canvas(container)

        scrollbar = ttk.Scrollbar(
            container,
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

        self.canvas.create_window(
            (0, 0),
            window=self.scroll_frame,
            anchor="nw"
        )

        self.canvas.configure(
            yscrollcommand=scrollbar.set
        )

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # SCROLL CON RUEDA
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_mousewheel(self, event):

        self.canvas.yview_scroll(
            int(-1 * (event.delta / 120)),
            "units"
        )


    # =========================================================
    # REPORT HEADER
    # =========================================================

    def _build_report_header(self):

        box = ttk.LabelFrame(self.scroll_frame, text="Report Header")
        box.pack(fill="x", pady=10)

        inner = ttk.Frame(box)
        inner.pack(fill="x", padx=10, pady=10)

        fields = [
            ("Report Number", "report_number"),
            ("Port", "port"),
            ("Country", "country")
        ]

        for i,(label,key) in enumerate(fields):

            ttk.Label(inner,text=label,width=18).grid(row=i,column=0,sticky="w",padx=5,pady=4)

            ttk.Entry(inner,textvariable=self._v(key),width=40).grid(row=i,column=1,sticky="w")

    # =========================================================
    # CERTIFICATE HEADER
    # =========================================================

    def _build_certificate_header(self):

        box = ttk.LabelFrame(self.scroll_frame, text="Certificate Header")
        box.pack(fill="x", pady=10)

        inner = ttk.Frame(box)
        inner.pack(fill="x", padx=10, pady=10)

        fields = [
            ("Vessel", "vessel"),
            ("Voyage", "voyage"),
            ("Load Port", "load_port"),
            ("Place", "place"),
            ("Installation", "installation"),
            ("Product", "product")
        ]

        for i, (label, key) in enumerate(fields):

            ttk.Label(
                inner,
                text=label,
                width=18
            ).grid(row=i, column=0, sticky="w", padx=5, pady=4)

            ttk.Entry(
                inner,
                textvariable=self._v(key),
                width=40
            ).grid(row=i, column=1, sticky="w")

        # DATE

        ttk.Label(inner, text="Date", width=18).grid(
            row=len(fields),
            column=0,
            sticky="w"
        )

        self.date_var = tk.StringVar()

        self.date_picker = DateEntry(
            inner,
            width=18,
            textvariable=self.date_var,
            date_pattern="yyyy-mm-dd"
        )

        self.date_picker.grid(
            row=len(fields),
            column=1,
            sticky="w"
        )

        # cuando se selecciona fecha
        self.date_picker.bind(
            "<<DateEntrySelected>>",
            self._set_long_date
        )

        # cuando pierde foco (esto evita que vuelva al formato ISO)
        self.date_picker.bind(
            "<FocusOut>",
            self._set_long_date
        )


    # =========================================================
    # SURVEY SECTION
    # =========================================================

    def _build_survey_section(self):

        box = ttk.LabelFrame(self.scroll_frame,text="Survey Information")
        box.pack(fill="x", pady=10)

        inner = ttk.Frame(box)
        inner.pack(fill="x", padx=10, pady=10)

        ttk.Label(inner,text="Inspection Time",width=18).grid(row=0,column=0,sticky="w")

        time_frame = ttk.Frame(inner)
        time_frame.grid(row=0,column=1,sticky="w")

        self.inspect_h = ttk.Entry(time_frame,width=3,justify="center")
        self.inspect_h.pack(side="left")

        ttk.Label(time_frame,text=":").pack(side="left",padx=2)

        self.inspect_m = ttk.Entry(time_frame,width=3,justify="center")
        self.inspect_m.pack(side="left")


        ttk.Label(inner,text="Vessel Holds",width=18).grid(row=1,column=0,sticky="w")

        ttk.Entry(inner,textvariable=self._v("vessel_holds"),width=40).grid(row=1,column=1,columnspan=3,sticky="w")

        ttk.Label(inner,text="Vessel Holds Status").grid(row=2,column=0,sticky="nw")

        self.vessel_status = tk.Text(inner,height=5,width=60)
        self.vessel_status.grid(row=2,column=1,columnspan=3,pady=5)

    # =========================================================
    # CARGO SECTION
    # =========================================================

    def _build_cargo_section(self):

        box = ttk.LabelFrame(self.scroll_frame,text="Cargo")
        box.pack(fill="x", pady=10)

        inner = ttk.Frame(box)
        inner.pack(fill="x", padx=10, pady=10)

        ttk.Label(inner,text="Cargo Holds",width=18).grid(row=0,column=0,sticky="w")

        ttk.Entry(inner,textvariable=self._v("cargo_holds"),width=40).grid(row=0,column=1)

        ttk.Label(inner,text="Accepted Time").grid(row=1,column=0,sticky="w")

        time_frame = ttk.Frame(inner)
        time_frame.grid(row=1,column=1,sticky="w")

        self.accept_h = ttk.Entry(time_frame,width=3,justify="center")
        self.accept_h.pack(side="left")

        ttk.Label(time_frame,text=":").pack(side="left",padx=2)

        self.accept_m = ttk.Entry(time_frame,width=3,justify="center")
        self.accept_m.pack(side="left")


    # =========================================================
    # LOCATION
    # =========================================================

    def _build_location_section(self):

        box = ttk.LabelFrame(self.scroll_frame,text="Location")
        box.pack(fill="x", pady=10)

        inner = ttk.Frame(box)
        inner.pack(fill="x", padx=10, pady=10)

        ttk.Label(inner,text="Place",width=18).grid(row=0,column=0,sticky="w")
        ttk.Entry(inner,textvariable=self._v("place_location"),width=40).grid(row=0,column=1)

        ttk.Label(inner,text="Date").grid(row=1,column=0,sticky="w")

        self.place_date_var = tk.StringVar()

        self.place_date = DateEntry(
            inner,
            width=18,
            textvariable=self.place_date_var,
            date_pattern="yyyy-mm-dd"
        )

        self.place_date.grid(row=1,column=1,sticky="w")

        # LONG DATE LOCATION
        self.place_date.bind(
            "<<DateEntrySelected>>",
            self._set_long_place_date
        )

        self.place_date.bind(
            "<FocusOut>",
            self._set_long_place_date
        )

    # =========================================================
    # HOSE TEST
    # =========================================================

    def _build_hose_test(self):

        box = ttk.LabelFrame(self.scroll_frame,text="Water Tightness / Hose Test")
        box.pack(fill="x", pady=10)

        inner = ttk.Frame(box)
        inner.pack(fill="x", padx=10, pady=10)

        ttk.Label(inner,text="Hose Test Time",width=18).grid(row=0,column=0,sticky="w")

        self.hose_start_h = ttk.Entry(inner,width=3)
        self.hose_start_h.grid(row=0,column=1)

        ttk.Label(inner,text=":").grid(row=0,column=2)

        self.hose_start_m = ttk.Entry(inner,width=3)
        self.hose_start_m.grid(row=0,column=3)

        ttk.Label(inner,text="to").grid(row=0,column=4)

        self.hose_end_h = ttk.Entry(inner,width=3)
        self.hose_end_h.grid(row=0,column=5)

        ttk.Label(inner,text=":").grid(row=0,column=6)

        self.hose_end_m = ttk.Entry(inner,width=3)
        self.hose_end_m.grid(row=0,column=7)

    # =========================================================
    # REMARKS
    # =========================================================

    # =========================================================
    # REMARKS
    # =========================================================

    def _build_remarks(self):

        box = ttk.LabelFrame(self.scroll_frame,text="Remarks")
        box.pack(fill="both", pady=10)

        self.remarks = tk.Text(box,height=6,wrap="word")
        self.remarks.pack(fill="both",expand=True,padx=10,pady=10)

        # MASTER / CHIEF OFFICER
        sign_frame = ttk.Frame(box)
        sign_frame.pack(fill="x", padx=10, pady=(5,10))

        ttk.Label(
            sign_frame,
            text="MASTER / CHIEF OFFICER",
            width=22
        ).grid(row=0,column=0,sticky="w")

        ttk.Entry(
            sign_frame,
            textvariable=self._v("master_chief_officer"),
            width=40
        ).grid(row=0,column=1,sticky="w")

    # =========================================================
    # SELECT SERVICE
    # =========================================================

    def _select_service(self):

        PopupServicioDraftSelector(
            self.parent,
            on_select=self._on_service_selected
        )

    def _on_service_selected(self, values):

        if not values:
            return

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

        # REPORT HEADER
        self._v("report_number").set(num_informe)
        self._v("port").set(puerto)
        self._v("country").set(pais)

        # CERTIFICATE HEADER
        self._v("vessel").set(buque)
        self._v("load_port").set(puerto)



    # =========================================================
    # BUILD PAYLOAD
    # =========================================================

    def _build_payload(self):

        payload = {}

        for key, var in self.vars.items():

            value = var.get()

            payload[key] = value if value else None

        # TIMES

        h = self.inspect_h.get().strip()
        m = self.inspect_m.get().strip()

        payload["inspection_time"] = f"{h}:{m}" if h and m else None

        h = self.accept_h.get().strip()
        m = self.accept_m.get().strip()

        payload["accepted_time"] = f"{h}:{m}" if h and m else None

        h = self.hose_start_h.get().strip()
        m = self.hose_start_m.get().strip()

        payload["hose_test_start"] = f"{h}:{m}" if h and m else None

        h = self.hose_end_h.get().strip()
        m = self.hose_end_m.get().strip()

        payload["hose_test_end"] = f"{h}:{m}" if h and m else None

        # DATE

        payload["date"] = to_db_date(self.date_picker.get()) or None

        payload["place_date"] = to_db_date(self.place_date.get()) or None

        # TEXT AREAS

        try:
            payload["vessel_holds_status"] = self.vessel_status.get("1.0", "end").strip()
        except:
            payload["vessel_holds_status"] = None

        try:
            payload["remarks"] = self.remarks.get("1.0", "end").strip()
        except:
            payload["remarks"] = None

        # MASTER / CHIEF OFFICER

        payload["master_chief_officer"] = self._v("master_chief_officer").get() or None

        return payload


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

                messagebox.showwarning(
                    "ERP-SOM",
                    "Record ID not found."
                )
                return

            payload = self._build_payload()

            update_vessel_holds_certificate_api(
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
    # DATE LONG FORMAT (LOCKED)
    # =========================================================

    def _set_long_date(self, event=None):

        try:

            d = self.date_picker.get_date()

            long_date = to_long_english_date(d)

            # fijar el valor permanentemente
            self.date_var.set(long_date)

        except Exception:
            pass

    # =========================================================
    # LOCATION DATE LONG FORMAT (LOCKED)
    # =========================================================

    def _set_long_place_date(self, event=None):

        try:

            d = self.place_date.get_date()

            long_date = to_long_english_date(d)

            self.place_date_var.set(long_date)

        except Exception:
            pass

    # =========================================================
    # SEND REVIEW (POST)
    # =========================================================

    def _send_review(self):

        try:

            payload = self._build_payload()

            result = create_vessel_holds_certificate_api(payload)

            messagebox.showinfo(
                "ERP-SOM",
                f"Report submitted for review.\n\nID: {result.get('id')}"
            )

            self.record_id = result.get("id")

        except Exception as e:

            messagebox.showerror(
                "ERP-SOM",
                f"Error sending report:\n{str(e)}"
            )


    # =========================================================
    # LOAD RECORD (GET BY ID)
    # =========================================================

    def _load_record(self, record_id):

        try:

            data = get_vessel_holds_certificate_api(record_id)

            if not data:
                return

            for key, value in data.items():

                if key in self.vars and value is not None:
                    self._v(key).set(value)

            # TIMES

            if data.get("inspection_time"):
                h, m = data["inspection_time"].split(":")
                self.inspect_h.insert(0, h)
                self.inspect_m.insert(0, m)

            if data.get("accepted_time"):
                h, m = data["accepted_time"].split(":")
                self.accept_h.insert(0, h)
                self.accept_m.insert(0, m)

            if data.get("hose_test_start"):
                h, m = data["hose_test_start"].split(":")
                self.hose_start_h.insert(0, h)
                self.hose_start_m.insert(0, m)

            if data.get("hose_test_end"):
                h, m = data["hose_test_end"].split(":")
                self.hose_end_h.insert(0, h)
                self.hose_end_m.insert(0, m)

            # DATE

            if data.get("date"):
                self.date_var.set(data["date"])

            if data.get("place_date"):

                try:

                    d = datetime.strptime(data["place_date"], "%Y-%m-%d")

                    long_date = to_long_english_date(d)

                    self.place_date_var.set(long_date)

                except:
                    self.place_date_var.set(data["place_date"])

            # TEXT AREAS

            if data.get("vessel_holds_status"):
                self.vessel_status.insert("1.0", data["vessel_holds_status"])

            if data.get("remarks"):
                self.remarks.insert("1.0", data["remarks"])

            if data.get("master_chief_officer"):
                self._v("master_chief_officer").set(data["master_chief_officer"])

        except Exception as e:

            messagebox.showerror(
                "ERP-SOM",
                f"Error loading record:\n{str(e)}"
            )


    # =========================================================
    # HOME (NO TOCADO)
    # =========================================================

    def _go_home(self):

        self.destroy()

        InformesHomeUI(
            self.parent,
            usuario=self.usuario,
            rol=self.rol
        )
