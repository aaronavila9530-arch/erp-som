import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from tkcalendar import DateEntry

from Modulos.Informes.Vessel_Draft_Survey.popup_servicio_draft_selector import PopupServicioDraftSelector
from Modulos.Informes.informes_home_ui import InformesHomeUI

from Modulos.Informes.vessel_cargo_condition_survey.popup_ai_maritime_control import PopupAIMaritimeControl
from Modulos.Informes.popup.popup_ai_compare import PopupAICompare

from Modulos.Informes.port_captancy.popup_ai_maritime_control_port_captancy import (
    PopupAIMaritimeControlPortCaptancy
)

import api_client


class PortCaptancyForm(ttk.Frame):

    MAX_DYNAMIC_ITEMS = 15

    def __init__(self, parent, usuario=None, rol=None, on_back=None):

        super().__init__(parent)

        self.parent = parent
        self.usuario = usuario
        self.rol = rol
        self.on_back = on_back

        self.vars = {}
        self.dynamic_sections = {}

        self.pack(fill="both", expand=True)

        self._build_ui()

    # =========================================================
    # VAR
    # =========================================================

    def _v(self, key):

        if key not in self.vars:
            self.vars[key] = tk.StringVar()

        return self.vars[key]

    # =========================================================
    # DATE FORMAT LONG
    # =========================================================

    def _format_long_date(self, value):

        if not value:
            return ""

        try:
            dt = datetime.strptime(value, "%Y-%m-%d")
            return dt.strftime("%B %d, %Y")
        except:
            return value

    def _date_selected(self, var):

        value = var.get()

        try:
            dt = datetime.strptime(value, "%Y-%m-%d")
            var.set(dt.strftime("%B %d, %Y"))
        except:
            pass


    def _force_long_date(self, event, var):

        value = var.get()

        try:

            if "-" in value:
                dt = datetime.strptime(value, "%Y-%m-%d")
                var.set(dt.strftime("%B %d, %Y"))

        except:
            pass

    # =========================================================
    # BUILD UI
    # =========================================================

    def _build_ui(self):

        self._build_topbar()
        self._build_scrollable()

        self._build_header()
        self._build_section_introduction()
        self._build_section_vessel()
        self._build_section_timesheet()

        self._build_dynamic_text_section(
            "4. OPERATION SUMMARY",
            "operation_summary"
        )

        self._build_dynamic_text_section(
            "5. REMARKS",
            "remarks"
        )

        self._build_dynamic_text_section(
            "6. CONCLUSION",
            "conclusion"
        )

        self._build_enclosure()

    # =========================================================
    # TOPBAR
    # =========================================================

    def _build_topbar(self):

        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=10, pady=(10,0))

        left = ttk.Frame(bar)
        left.pack(side="left", fill="x", expand=True)

        ttk.Label(
            left,
            text="PORT CAPTANCY REPORT",
            font=("Segoe UI", 14, "bold")
        ).pack(side="left")

        right = ttk.Frame(bar)
        right.pack(side="right")

        ttk.Button(
            right,
            text="Seleccionar Informe",
            command=self._select_service
        ).pack(side="left", padx=4)

        ttk.Button(
            right,
            text="Mejorar con PORTIA",
            command=self._improve_ai
        ).pack(side="left", padx=4)

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
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)

        self.scroll_frame = ttk.Frame(self.canvas)

        self.scroll_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0,0), window=self.scroll_frame, anchor="nw")

        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_mousewheel(self, event):

        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    # =========================================================
    # HEADER
    # =========================================================

    def _build_header(self):

        box = ttk.LabelFrame(self.scroll_frame, text="Header")
        box.pack(fill="x", pady=(0,10))

        inner = ttk.Frame(box)
        inner.pack(fill="x", padx=10, pady=10)

        fields = [
            ("Report Number", "report_number"),
            ("Continent", "continent"),
            ("Country", "country"),
            ("Port", "port"),
            ("Operation", "operation")
        ]

        for i,(label,key) in enumerate(fields):

            ttk.Label(inner,text=label,width=18).grid(
                row=i,column=0,sticky="w",padx=5,pady=4
            )

            ttk.Entry(
                inner,
                textvariable=self._v(key),
                width=40,
                state="readonly"
            ).grid(row=i,column=1,sticky="w",padx=5,pady=4)

    def _build_section_introduction(self):

        box = ttk.LabelFrame(self.scroll_frame,text="1. INTRODUCTIONS")
        box.pack(fill="x", pady=(0,10))

        inner = ttk.Frame(box)
        inner.pack(fill="x", padx=10, pady=10)

        # ======================================================
        # PURPOSE (TAL CUAL DOCUMENTO)
        # ======================================================

        row = ttk.Frame(inner)
        row.grid(row=0,column=0,columnspan=4,sticky="w",pady=4)

        ttk.Label(
            row,
            text="We MSL Marine Surveyors and Logistics were appointed to inspect and carry out",
            wraplength=650
        ).pack(side="left")

        ttk.Entry(
            row,
            textvariable=self._v("report_type"),
            width=35
        ).pack(side="left", padx=6)

        ttk.Label(
            row,
            text="in"
        ).pack(side="left")

        ttk.Entry(
            row,
            textvariable=self._v("vessel"),
            width=20
        ).pack(side="left", padx=6)

        ttk.Label(
            row,
            text="at Puerto"
        ).pack(side="left")

        ttk.Entry(
            row,
            textvariable=self._v("port"),
            width=16
        ).pack(side="left", padx=4)

        ttk.Label(
            row,
            text="â€“"
        ).pack(side="left")

        ttk.Entry(
            row,
            textvariable=self._v("country"),
            width=16
        ).pack(side="left", padx=4)


        # ======================================================
        # SURVEY REQUESTED BY
        # ======================================================

        ttk.Label(inner,text="Survey requested by").grid(row=1,column=0,sticky="w",pady=6)

        ttk.Entry(
            inner,
            textvariable=self._v("requested_by"),
            width=45
        ).grid(row=1,column=1,sticky="w")


        # ======================================================
        # ARRIVAL DATE + TIME
        # ======================================================

        ttk.Label(inner, text="Date of arrival", width=18).grid(
            row=2, column=0, sticky="w", padx=5, pady=4
        )

        arrival_frame = ttk.Frame(inner)
        arrival_frame.grid(row=2, column=1, sticky="w")

        arrival_var = self._v("arrival_date")

        arrival = DateEntry(
            arrival_frame,
            textvariable=arrival_var,
            width=16,
            date_pattern="yyyy-mm-dd"
        )
        arrival.pack(side="left")

        arrival.bind("<<DateEntrySelected>>", lambda e: self._date_selected(arrival_var))
        arrival.bind("<FocusOut>", lambda e: self._force_long_date(e, arrival_var))

        ttk.Entry(
            arrival_frame,
            textvariable=self._v("arrival_hour"),
            width=4
        ).pack(side="left", padx=(8,2))

        ttk.Label(arrival_frame, text=":").pack(side="left")

        ttk.Entry(
            arrival_frame,
            textvariable=self._v("arrival_minute"),
            width=4
        ).pack(side="left", padx=(2,6))

        ttk.Label(arrival_frame, text="LT").pack(side="left")


        # ======================================================
        # INSPECTION DATE + TIME
        # ======================================================

        ttk.Label(inner, text="Inspection date", width=18).grid(
            row=3, column=0, sticky="w", padx=5, pady=4
        )

        inspection_frame = ttk.Frame(inner)
        inspection_frame.grid(row=3, column=1, sticky="w")

        insp_var = self._v("inspection_date")

        insp = DateEntry(
            inspection_frame,
            textvariable=insp_var,
            width=16,
            date_pattern="yyyy-mm-dd"
        )
        insp.pack(side="left")

        insp.bind("<<DateEntrySelected>>", lambda e: self._date_selected(insp_var))
        insp.bind("<FocusOut>", lambda e: self._force_long_date(e, insp_var))

        ttk.Entry(
            inspection_frame,
            textvariable=self._v("inspection_hour"),
            width=4
        ).pack(side="left", padx=(8,2))

        ttk.Label(inspection_frame, text=":").pack(side="left")

        ttk.Entry(
            inspection_frame,
            textvariable=self._v("inspection_minute"),
            width=4
        ).pack(side="left", padx=(2,6))

        ttk.Label(inspection_frame, text="LT").pack(side="left")


        # ======================================================
        # REPRESENTATIVES
        # ======================================================

        ttk.Label(inner, text="Master of the ship", width=18).grid(
            row=4, column=0, sticky="w", padx=5, pady=4
        )

        ttk.Entry(
            inner,
            textvariable=self._v("master"),
            width=45
        ).grid(row=4, column=1, sticky="w", padx=5, pady=4)

        ttk.Label(inner, text="Chief Officer", width=18).grid(
            row=5, column=0, sticky="w", padx=5, pady=4
        )

        ttk.Entry(
            inner,
            textvariable=self._v("chief"),
            width=45
        ).grid(row=5, column=1, sticky="w", padx=5, pady=4)

    # =========================================================
    # VESSEL
    # =========================================================

    def _build_section_vessel(self):

        box = ttk.LabelFrame(self.scroll_frame,text="2. THE VESSEL")
        box.pack(fill="x", pady=(0,10))

        inner = ttk.Frame(box)
        inner.pack(fill="x", padx=10, pady=10)

        fields = [
            ("Name","vessel"),
            ("Port Of Registry / Flag","flag"),
            ("GRT","grt"),
            ("NRT","nrt"),
            ("IMO","imo"),
            ("Year Built","year_built"),
        ]

        for i,(label,key) in enumerate(fields):

            ttk.Label(inner,text=label,width=24).grid(
                row=i,column=0,sticky="w",padx=5,pady=4
            )

            ttk.Entry(
                inner,
                textvariable=self._v(key),
                width=40
            ).grid(row=i,column=1,sticky="w",padx=5,pady=4)

    # =========================================================
    # TIME SHEET
    # =========================================================

    def _build_section_timesheet(self):

        box = ttk.LabelFrame(self.scroll_frame,text="3. EXTRACT TIME SHEET")
        box.pack(fill="x", pady=(0,10))

        inner = ttk.Frame(box)
        inner.pack(fill="x", padx=10, pady=10)

        events = [
            "Vessel Arrive",
            "NOR Tendered",
            "ALL Fast",
            "Supervision commenced",
            "Supervision completed"
        ]

        for i,e in enumerate(events):

            row = ttk.Frame(inner)
            row.pack(fill="x", pady=2)

            ttk.Label(row,text=e,width=30).pack(side="left")

            var = self._v(f"ts_date_{i}")

            entry = DateEntry(
                row,
                textvariable=var,
                width=18,
                date_pattern="yyyy-mm-dd"
            )

            entry.pack(side="left")

            entry.bind("<<DateEntrySelected>>",lambda ev,v=var:self._date_selected(v))
            entry.bind("<FocusOut>",lambda ev,v=var:self._force_long_date(ev,v))

            ttk.Entry(
                row,
                textvariable=self._v(f"ts_hour_{i}"),
                width=4
            ).pack(side="left", padx=2)

            ttk.Label(row,text=":").pack(side="left")

            ttk.Entry(
                row,
                textvariable=self._v(f"ts_min_{i}"),
                width=4
            ).pack(side="left", padx=2)

            ttk.Label(row,text="LT").pack(side="left", padx=4)

    # =========================================================
    # DYNAMIC TEXT
    # =========================================================

    def _build_dynamic_text_section(self,title,key):

        box = ttk.LabelFrame(self.scroll_frame,text=title)
        box.pack(fill="x", pady=(0,10))

        container = ttk.Frame(box)
        container.pack(fill="x", padx=10, pady=10)

        self.dynamic_sections[key] = {
            "container":container,
            "items":[]
        }

        ttk.Button(
            container,
            text="+ Add bullet",
            command=lambda k=key:self._add_item(k)
        ).pack(anchor="e")

        self._add_item(key)

    def _add_item(self, key):

        section = self.dynamic_sections[key]

        # evitar crear mÃ¡s de los permitidos por la tabla
        if len(section["items"]) >= self.MAX_DYNAMIC_ITEMS:
            messagebox.showwarning(
                "ERP-SOM",
                f"Maximum {self.MAX_DYNAMIC_ITEMS} bullet points allowed."
            )
            return

        container = section["container"]

        frame = ttk.Frame(container)
        frame.pack(fill="x", pady=4)

        ttk.Label(frame, text="â€¢").pack(side="left")

        text = tk.Text(frame, height=4, wrap="word")
        text.pack(side="left", fill="x", expand=True)

        ttk.Button(
            frame,
            text="-",
            width=3,
            command=lambda: self._remove_item(key, frame, text)
        ).pack(side="left", padx=4)

        section["items"].append(text)

    # =========================================================
    # ENCLOSURE
    # =========================================================

    def _build_enclosure(self):

        box = ttk.LabelFrame(self.scroll_frame,text="7. ENCLOSURE")
        box.pack(fill="x", pady=(0,10))

        row = ttk.Frame(box)
        row.pack(fill="x", padx=10, pady=10)

        ttk.Label(row,text="Link Picture",width=18).pack(side="left")

        ttk.Entry(
            row,
            textvariable=self._v("link_picture"),
            width=60
        ).pack(side="left",fill="x",expand=True)

    # =========================================================
    # SELECT SERVICE
    # =========================================================

    def _select_service(self):

        PopupServicioDraftSelector(
            self.parent,
            on_select=self._on_service_selected
        )

    def _on_service_selected(self,values):

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

        self._v("report_number").set(num_informe)
        self._v("vessel").set(buque)
        self._v("continent").set(continente)
        self._v("country").set(pais)
        self._v("port").set(puerto)
        self._v("operation").set(operacion)
        self._v("requested_by").set(cliente)

    # =========================================================
    # AI
    # =========================================================
    def _improve_ai(self):

        try:

            PopupAIMaritimeControlPortCaptancy(
                self.parent,
                form_instance=self
            )

        except Exception as e:

            messagebox.showerror(
                "ERP-SOM",
                f"PORTIA error:\n{str(e)}"
            )

    # =========================================================
    # SEND REVIEW (POST API)
    # =========================================================
    def _send_review(self):

        try:

            report_number = self._v("report_number").get()

            if not report_number:
                messagebox.showwarning(
                    "ERP-SOM",
                    "Please select a Service first."
                )
                return

            payload = self._build_payload()

            api_client.create_port_captancy_report_api(payload)

            messagebox.showinfo(
                "ERP-SOM",
                "Report successfully sent for review."
            )

        except Exception as e:

            messagebox.showerror(
                "ERP-SOM",
                f"Error sending report:\n{str(e)}"
            )

    def set_edit_mode(self):
        self.btn_send.pack_forget()
        self.btn_edit.pack(side="left", padx=4)
        self.btn_save_changes.pack(side="left", padx=4)

    def _enable_edit_mode(self):
        self.btn_save_changes.config(state="normal")

    def _save_changes(self):
        try:
            report_number = self._v("report_number").get()

            if not report_number:
                messagebox.showwarning(
                    "ERP-SOM",
                    "Report number not found."
                )
                return

            api_client.update_port_captancy_report_api(
                report_number,
                self._build_payload()
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
    # HOME
    # =========================================================

    def _go_home(self):

        self.destroy()

        InformesHomeUI(
            self.parent,
            usuario=self.usuario,
            rol=self.rol
        )


    # =========================================================
    # BUILD PAYLOAD (POST)
    # =========================================================
    def _build_payload(self):

        payload = {}

        # =========================================
        # NORMAL INPUT FIELDS
        # =========================================

        for key, var in self.vars.items():

            value = var.get()

            payload[key] = value if value else None


        # =========================================
        # DYNAMIC BULLET SECTIONS
        # =========================================

        sections = [
            "operation_summary",
            "remarks",
            "conclusion"
        ]

        MAX = self.MAX_DYNAMIC_ITEMS

        for section in sections:

            section_data = self.dynamic_sections.get(section, {})
            items = section_data.get("items", [])

            # initialize fields
            for i in range(1, MAX + 1):

                payload[f"{section}_{i}"] = None

            # populate with values
            for idx, widget in enumerate(items, start=1):

                if idx > MAX:
                    break

                try:
                    text = widget.get("1.0", "end").strip()
                except Exception:
                    text = ""

                payload[f"{section}_{idx}"] = text if text else None


        return payload


    # =========================================================
    # LOAD DYNAMIC BULLETS FROM API (GET)
    # =========================================================
    def _load_dynamic_sections(self, data):

        sections = [
            "operation_summary",
            "remarks",
            "conclusion"
        ]

        MAX = self.MAX_DYNAMIC_ITEMS

        for section in sections:

            section_data = self.dynamic_sections.get(section)

            if not section_data:
                continue

            items = section_data["items"]

            # limpiar existentes
            for text_widget in items:
                try:
                    text_widget.delete("1.0", "end")
                except Exception:
                    pass

            values = []

            for i in range(1, MAX + 1):

                field = f"{section}_{i}"

                if field in data and data[field]:

                    values.append(str(data[field]))

            # crear widgets si faltan
            while len(section_data["items"]) < max(1, len(values)):

                self._add_item(section)

            items = section_data["items"]

            for idx, value in enumerate(values):

                try:
                    items[idx].delete("1.0", "end")
                    items[idx].insert("1.0", value)
                except Exception:
                    pass

    # =========================================================
    # REMOVE BULLET ITEM SAFELY
    # =========================================================
    def _remove_item(self, key, frame, text_widget):

        try:
            frame.destroy()
        except Exception:
            pass

        try:
            section = self.dynamic_sections.get(key)

            if not section:
                return

            items = section.get("items", [])

            if text_widget in items:
                items.remove(text_widget)

        except Exception:
            pass

    # =========================================================
    # LOAD RECORD FROM API
    # =========================================================
    def load_record(self, data):

        if not data:
            return

        # =========================================
        # NORMAL FIELDS
        # =========================================

        for key, value in data.items():

            if key in self.vars:

                try:
                    self.vars[key].set("" if value is None else str(value))
                except Exception:
                    pass


        # =========================================
        # DYNAMIC BULLETS
        # =========================================

        self._load_dynamic_sections(data)
        self.set_edit_mode()
