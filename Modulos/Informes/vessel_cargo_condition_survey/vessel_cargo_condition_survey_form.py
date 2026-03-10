import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from tkcalendar import DateEntry

from Modulos.Informes.Vessel_Draft_Survey.popup_servicio_draft_selector import PopupServicioDraftSelector
from Modulos.Informes.informes_home_ui import InformesHomeUI

from Modulos.Informes.vessel_cargo_condition_survey.popup_ai_maritime_control import PopupAIMaritimeControl
from Modulos.Informes.popup.popup_ai_compare import PopupAICompare
import api_client


class VesselCargoConditionSurveyForm(ttk.Frame):
    """
    ERP-SOM — Cargo Condition Survey Form
    """

    # =========================================================
    # INIT
    # =========================================================
    def __init__(self, parent, usuario=None, rol=None, on_back=None):
        super().__init__(parent)

        self.parent = parent
        self.usuario = usuario
        self.rol = rol
        self.on_back = on_back

        self.pack(fill="both", expand=True)

        self.vars = {}
        self.readonly_widgets = []

        self._build_ui()

    # =========================================================
    # VAR HELPER
    # =========================================================
    def _v(self, key):
        if key not in self.vars:
            self.vars[key] = tk.StringVar()
        return self.vars[key]

    # =========================================================
    # UI ROOT
    # =========================================================
    def _build_ui(self):

        topbar = ttk.Frame(self)
        topbar.pack(fill="x", padx=10, pady=(10, 0))

        ttk.Label(
            topbar,
            text="CARGO CONDITION SURVEY",
            font=("Segoe UI", 13, "bold")
        ).pack(side="left")

        btn_frame = ttk.Frame(topbar)
        btn_frame.pack(side="right")

        ttk.Button(
            btn_frame,
            text="Seleccionar Reporte",
            command=self._select_service
        ).pack(side="left", padx=4)

        ttk.Button(
            btn_frame,
            text="Improve IA Maritime",
            command=self._improve_ai_maritime
        ).pack(side="left", padx=4)

        ttk.Button(
            btn_frame,
            text="Enviar a Revisión",
            command=self._send_to_review
        ).pack(side="left", padx=4)

        ttk.Button(
            btn_frame,
            text="Home",
            command=self._go_home
        ).pack(side="left", padx=4)

        container = ttk.Frame(self)
        container.pack(fill="both", expand=True, padx=10, pady=10)

        self.canvas = tk.Canvas(container, highlightthickness=0)
        vbar = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=vbar.set)

        vbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.scroll_frame = ttk.Frame(self.canvas)

        self.scroll_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")

        self.canvas.bind_all(
            "<MouseWheel>",
            lambda e: self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        )

        self._build_main_data_section()
        self._build_cargo_type_section()
        self._build_vessel_section()
        self._build_time_sheet_section()
        self._build_bullet_section("Narrative", "narrative")
        self._build_bullet_section("Survey Findings", "findings")
        self._build_bullet_section("Remarks", "remarks")
        self._build_bullet_section("Conclusion", "conclusion")
        self._build_link_picture_section()

        ttk.Label(self.scroll_frame, text="").pack(pady=10)

    # =========================================================
    # DATE FIELD (ISO STABLE)
    # =========================================================
    # =========================================================
    # DATE FIELD (ISO + VISUAL LONG COMO BUNKER)
    # =========================================================
    def _datetime_field(self, parent, label, key_prefix, row, col):

        ttk.Label(parent, text=label).grid(
            row=row, column=col, sticky="w", padx=5, pady=3
        )

        frame = ttk.Frame(parent)
        frame.grid(row=row, column=col + 1, sticky="w", padx=5, pady=3)

        # 🔹 DateEntry en ISO estable
        date_entry = DateEntry(
            frame,
            textvariable=self._v(f"{key_prefix}_date"),
            width=18,
            locale="en_US",
            date_pattern="yyyy-mm-dd"
        )
        date_entry.pack(side="left")

        # 🔹 Al perder foco → mostrar formato LONG
        date_entry.bind(
            "<FocusOut>",
            lambda e: self._format_date_long(f"{key_prefix}_date")
        )

        # 🔹 Hora HH
        ttk.Entry(
            frame,
            textvariable=self._v(f"{key_prefix}_hour"),
            width=3
        ).pack(side="left", padx=(8, 0))

        ttk.Label(frame, text=":").pack(side="left")

        # 🔹 Minutos MM
        ttk.Entry(
            frame,
            textvariable=self._v(f"{key_prefix}_minute"),
            width=3
        ).pack(side="left")


    # =========================================================
    # NORMALIZERS
    # =========================================================
    def _normalize_date_for_db(self, value):

        if not value:
            return None

        value = value.strip()

        # ISO format
        try:
            dt = datetime.strptime(value, "%Y-%m-%d")
            return dt.strftime("%Y-%m-%d")
        except Exception:
            pass

        # LONG format (March 02, 2026)
        try:
            dt = datetime.strptime(value, "%B %d, %Y")
            return dt.strftime("%Y-%m-%d")
        except Exception:
            pass

        return None

    def _normalize_hhmm(self, value, max_value):

        if value is None:
            return None

        s = str(value).strip()
        if not s.isdigit():
            return None

        n = int(s)
        if n < 0 or n > max_value:
            return None

        return f"{n:02d}"

    # =========================================================
    # MAIN DATA
    # =========================================================
    def _build_main_data_section(self):

        box = ttk.LabelFrame(self.scroll_frame, text="1. General Information")
        box.pack(fill="x", pady=(0, 10))

        inner = ttk.Frame(box)
        inner.pack(fill="x", padx=10, pady=10)

        inner.columnconfigure(1, weight=1)
        inner.columnconfigure(3, weight=1)

        self._ro_entry(inner, "Vessel", "vessel", 0, 0)
        self._ro_entry(inner, "Port", "port", 0, 2)

        self._ro_entry(inner, "Country", "country", 1, 0)
        self._ro_entry(inner, "Survey Requested By", "requested_by", 1, 2)

        self._datetime_field(inner, "Date Arrival", "arrival", 2, 0)
        self._datetime_field(inner, "Date/Time Inspection", "inspection", 2, 2)

        self._entry(inner, "Master of the Ship", "master", 3, 0)
        self._entry(inner, "Chief Officer", "chief_officer", 3, 2)

    def _ro_entry(self, parent, label, key, row, col):
        ttk.Label(parent, text=label).grid(
            row=row, column=col, sticky="w", padx=5, pady=3
        )
        e = ttk.Entry(parent, textvariable=self._v(key))
        e.grid(row=row, column=col + 1, sticky="ew", padx=5, pady=3)
        e.configure(state="readonly")


    # =========================================================
    # NORMAL EDITABLE ENTRY
    # =========================================================
    def _entry(self, parent, label, key, row, col):
        ttk.Label(parent, text=label).grid(
            row=row, column=col, sticky="w", padx=5, pady=3
        )
        e = ttk.Entry(parent, textvariable=self._v(key))
        e.grid(row=row, column=col + 1, sticky="ew", padx=5, pady=3)


    # =========================================================
    # TIME SHEET
    # =========================================================
    def _build_time_sheet_section(self):

        box = ttk.LabelFrame(self.scroll_frame, text="3. Extract Time Sheet")
        box.pack(fill="x", pady=(0, 10))

        inner = ttk.Frame(box)
        inner.pack(fill="x", padx=10, pady=10)

        events = [
            "Vessel Arrived at sea buoy",
            "N.O.R Tendered",
            "Unsealing Inspection",
            "All fast",
            "Free pratique",
            "Surveyor Onboard",
            "Discharging commenced",
            "Discharging completed",
        ]

        for i, ev in enumerate(events):
            self._datetime_field(inner, ev, f"time_{i}", i, 0)

    # =========================================================
    # BULLET SECTIONS
    # =========================================================
    def _build_bullet_section(self, title, key_prefix):

        box = ttk.LabelFrame(self.scroll_frame, text=title)
        box.pack(fill="x", pady=(0, 10))

        toolbar = ttk.Frame(box)
        toolbar.pack(fill="x", padx=10, pady=(5, 0))

        ttk.Button(
            toolbar,
            text="+",
            width=3,
            command=lambda: self._add_bullet_line(key_prefix)
        ).pack(side="right")

        container = ttk.Frame(box)
        container.pack(fill="x", padx=10, pady=10)

        setattr(self, f"{key_prefix}_container", container)
        setattr(self, f"{key_prefix}_lines", [])

        self._add_bullet_line(key_prefix)

    def _add_bullet_line(self, key_prefix):

        container = getattr(self, f"{key_prefix}_container")
        lines = getattr(self, f"{key_prefix}_lines")

        frame = ttk.Frame(container)
        frame.pack(fill="x", pady=2)

        ttk.Label(frame, text="•").pack(side="left", padx=(0, 5))

        txt = tk.Text(frame, height=3, width=110)
        txt.pack(side="left", fill="x", expand=True)

        lines.append(txt)

    # =========================================================
    # CARGO TYPE SECTION (SINGLE TEXTBOX)
    # =========================================================
    def _build_cargo_type_section(self):

        box = ttk.LabelFrame(self.scroll_frame, text="2. Cargo Type")
        box.pack(fill="x", pady=(0, 10))

        container = ttk.Frame(box)
        container.pack(fill="x", padx=10, pady=10)

        ttk.Label(
            container,
            text="Cargo Type:"
        ).grid(row=0, column=0, sticky="w", padx=5, pady=3)

        entry = ttk.Entry(
            container,
            textvariable=self._v("cargo_type")
        )
        entry.grid(row=0, column=1, sticky="ew", padx=5, pady=3)

        container.columnconfigure(1, weight=1)


    # =========================================================
    # THE VESSEL SECTION
    # =========================================================
    def _build_vessel_section(self):

        box = ttk.LabelFrame(self.scroll_frame, text="THE VESSEL")
        box.pack(fill="x", pady=(0, 10))

        container = ttk.Frame(box)
        container.pack(fill="x", padx=10, pady=10)

        container.columnconfigure(1, weight=1)
        container.columnconfigure(3, weight=1)

        # Row 0
        ttk.Label(container, text="Name").grid(
            row=0, column=0, sticky="w", padx=5, pady=3
        )
        ttk.Entry(
            container,
            textvariable=self._v("vessel")
        ).grid(row=0, column=1, sticky="ew", padx=5, pady=3)

        ttk.Label(container, text="Port of Registry / Flag").grid(
            row=0, column=2, sticky="w", padx=5, pady=3
        )
        ttk.Entry(
            container,
            textvariable=self._v("vessel_port_registry_flag")
        ).grid(row=0, column=3, sticky="ew", padx=5, pady=3)

        # Row 1
        ttk.Label(container, text="GRT").grid(
            row=1, column=0, sticky="w", padx=5, pady=3
        )
        ttk.Entry(
            container,
            textvariable=self._v("vessel_grt")
        ).grid(row=1, column=1, sticky="ew", padx=5, pady=3)

        ttk.Label(container, text="NRT").grid(
            row=1, column=2, sticky="w", padx=5, pady=3
        )
        ttk.Entry(
            container,
            textvariable=self._v("vessel_nrt")
        ).grid(row=1, column=3, sticky="ew", padx=5, pady=3)

        # Row 2
        ttk.Label(container, text="IMO No").grid(
            row=2, column=0, sticky="w", padx=5, pady=3
        )
        ttk.Entry(
            container,
            textvariable=self._v("vessel_imo_no")
        ).grid(row=2, column=1, sticky="ew", padx=5, pady=3)

        ttk.Label(container, text="Year Build").grid(
            row=2, column=2, sticky="w", padx=5, pady=3
        )

        current_year = datetime.now().year
        years = [str(y) for y in range(current_year, 1950, -1)]

        ttk.Combobox(
            container,
            textvariable=self._v("vessel_year_build"),
            values=years,
            state="readonly"
        ).grid(row=2, column=3, sticky="ew", padx=5, pady=3)


    # =========================================================
    # LINK PICTURE SECTION (SINGLE TEXTBOX)
    # =========================================================
    def _build_link_picture_section(self):

        box = ttk.LabelFrame(self.scroll_frame, text="Link Picture")
        box.pack(fill="x", pady=(0, 10))

        container = ttk.Frame(box)
        container.pack(fill="x", padx=10, pady=10)

        ttk.Label(
            container,
            text="Image URL:"
        ).grid(row=0, column=0, sticky="w", padx=5, pady=3)

        entry = ttk.Entry(
            container,
            textvariable=self._v("link_picture")
        )
        entry.grid(row=0, column=1, sticky="ew", padx=5, pady=3)

        container.columnconfigure(1, weight=1)


    # =========================================================
    # POPUP SELECTOR (RESTORED)
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

        # -------------------------------------------------
        # IMPORTANT FIELDS (WERE MISSING)
        # -------------------------------------------------
        self._v("report_number").set(num_informe or "")
        self._v("continent").set(continente or "")
        self._v("operation").set(operacion or "")

        # Si fecha_inicio viene datetime o string
        if fecha_inicio:
            try:
                if isinstance(fecha_inicio, datetime):
                    self._v("service_start_date").set(
                        fecha_inicio.strftime("%Y-%m-%d")
                    )
                else:
                    self._v("service_start_date").set(str(fecha_inicio))
            except Exception:
                self._v("service_start_date").set(str(fecha_inicio))
        else:
            self._v("service_start_date").set("")

        # -------------------------------------------------
        # EXISTING FIELDS
        # -------------------------------------------------
        self._v("vessel").set(buque or "")
        self._v("port").set(puerto or "")
        self._v("country").set(pais or "")
        self._v("requested_by").set(cliente or "")

        # No tocar master ni chief_officer



    def _format_date_long(self, var_key):

        value = self._v(var_key).get()
        if not value:
            return

        value = value.strip()

        # Si viene en ISO
        try:
            dt = datetime.strptime(value, "%Y-%m-%d")
            self._v(var_key).set(dt.strftime("%B %d, %Y"))
            return
        except Exception:
            pass

        # Si ya está en formato largo válido → no tocar
        try:
            datetime.strptime(value, "%B %d, %Y")
            return
        except Exception:
            pass


    # =========================================================
    # IA BUTTON
    # =========================================================
    def _improve_ai_maritime(self):

        PopupAIMaritimeControl(
            parent=self,
            form_instance=self,
            on_execute=self._execute_ai_improvement
        )




    # =========================================================
    # EXECUTE AI IMPROVEMENT
    # =========================================================
    def _execute_ai_improvement(self, section, language, items):

        vessel = self._v("vessel").get()
        port = self._v("port").get()

        response = api_client.improve_cargo_condition_ai_api(
            section=section,
            language=language,
            vessel=vessel,
            port=port,
            items=items
        )

        if not response.get("success"):
            messagebox.showerror(
                "IA Maritime",
                response.get("error") or "AI processing failed."
            )
            return

        ai_items = response.get("items")

        if not ai_items:
            messagebox.showerror(
                "IA Maritime",
                "AI returned empty response."
            )
            return

        PopupAICompare(
            parent=self,
            original_text="\n\n".join(items),
            ai_text="\n\n".join(ai_items),
            on_accept=lambda new_text: self._apply_ai_text(section, new_text),
            on_retry=lambda: self._execute_ai_improvement(section, language, items)
        )


    # =========================================================
    # BUILD PAYLOAD (1:1 WITH DB)
    # =========================================================
    def _build_payload(self):

        payload = {}

        # -----------------------------------------------------
        # GENERAL FIELDS
        # -----------------------------------------------------
        general_fields = [
            "report_number",
            "continent",
            "operation",
            "service_start_date",
            "vessel",
            "port",
            "country",
            "requested_by",
            "master",
            "chief_officer",
            "cargo_type",
            "link_picture",

            # ---- THE VESSEL ----
            "vessel_port_registry_flag",
            "vessel_grt",
            "vessel_nrt",
            "vessel_imo_no",
            "vessel_year_build",
        ]

        for field in general_fields:
            payload[field] = self._v(field).get() or None

        # -----------------------------------------------------
        # ARRIVAL / INSPECTION
        # -----------------------------------------------------
        payload["arrival_date"] = self._normalize_date_for_db(self._v("arrival_date").get())
        payload["arrival_hour"] = self._normalize_hhmm(self._v("arrival_hour").get(), 23)
        payload["arrival_minute"] = self._normalize_hhmm(self._v("arrival_minute").get(), 59)

        payload["inspection_date"] = self._normalize_date_for_db(self._v("inspection_date").get())
        payload["inspection_hour"] = self._normalize_hhmm(self._v("inspection_hour").get(), 23)
        payload["inspection_minute"] = self._normalize_hhmm(self._v("inspection_minute").get(), 59)

        # -----------------------------------------------------
        # TIME SHEET (0..7)
        # -----------------------------------------------------
        for i in range(8):

            payload[f"time_{i}_date"] = self._normalize_date_for_db(
                self._v(f"time_{i}_date").get()
            )

            payload[f"time_{i}_hour"] = self._normalize_hhmm(
                self._v(f"time_{i}_hour").get(), 23
            )

            payload[f"time_{i}_minute"] = self._normalize_hhmm(
                self._v(f"time_{i}_minute").get(), 59
            )

        # -----------------------------------------------------
        # BULLETS (10 MAX PER SECTION)
        # -----------------------------------------------------
        sections = ["narrative", "findings", "remarks", "conclusion"]

        for sec in sections:

            lines = getattr(self, f"{sec}_lines", [])

            for i in range(10):

                key = f"{sec}_{i+1}"

                if i < len(lines):
                    text = lines[i].get("1.0", "end").strip()
                    payload[key] = text if text else None
                else:
                    payload[key] = None

        return payload


    # =========================================================
    # APPLY AI TEXT TO FORM
    # =========================================================
    def _apply_ai_text(self, section, new_text):

        lines = getattr(self, f"{section}_lines", [])

        # Separar por doble salto de línea
        parsed = [
            block.strip()
            for block in new_text.split("\n\n")
            if block.strip()
        ]

        # Limpiar campos actuales
        for txt in lines:
            txt.delete("1.0", "end")

        # Ajustar cantidad de cajas si es necesario
        while len(lines) < len(parsed):
            self._add_bullet_line(section)
            lines = getattr(self, f"{section}_lines", [])

        # Insertar texto mejorado
        for i, block in enumerate(parsed):
            lines[i].delete("1.0", "end")
            lines[i].insert("1.0", block)



    # =========================================================
    # SEND TO REVIEW (POST + RETURN HOME)
    # =========================================================
    def _send_to_review(self):

        confirm = messagebox.askyesno(
            "Confirmar",
            "¿Deseas enviar el informe a revisión?"
        )

        if not confirm:
            return

        try:
            payload = self._build_payload()

            # 🔹 Forzar status
            payload["status"] = "Pending for review"

            response = api_client.create_vessel_cargo_condition_api(payload)

            if not response.get("success"):
                messagebox.showerror(
                    "Error",
                    response.get("error") or "Error enviando a revisión."
                )
                return

            messagebox.showinfo(
                "Enviado",
                "Informe enviado correctamente a revisión."
            )

            # 🔹 Destruir form
            self.destroy()

            # 🔹 Regresar al Home
            InformesHomeUI(
                self.parent,
                usuario=self.usuario,
                rol=self.rol
            )

        except Exception as e:
            messagebox.showerror("Error", str(e))

    # =========================================================
    # LOAD DATA INTO FORM (USED BY REVIEW)
    # =========================================================
    def load_record(self, data):

        if not data:
            return

        # -----------------------------------------
        # 1. NORMAL VAR FIELDS
        # -----------------------------------------
        for k, v in data.items():

            # asegurar que el StringVar exista
            var = self._v(k)

            if v is not None:
                var.set(str(v))
            else:
                var.set("")

        # -----------------------------------------
        # 2. BULLET SECTIONS
        # -----------------------------------------
        sections = ["narrative", "findings", "remarks", "conclusion"]

        for sec in sections:

            lines = getattr(self, f"{sec}_lines")

            for i in range(10):

                key = f"{sec}_{i+1}"
                value = data.get(key)

                if value:

                    while len(lines) <= i:
                        self._add_bullet_line(sec)
                        lines = getattr(self, f"{sec}_lines")

                    lines[i].delete("1.0", "end")
                    lines[i].insert("1.0", value)



    # =========================================================
    # HOME
    # =========================================================
    def _go_home(self):
        try:
            self.destroy()
            InformesHomeUI(
                self.parent,
                usuario=self.usuario,
                rol=self.rol
            )
        except Exception as e:
            messagebox.showerror("Home", str(e))