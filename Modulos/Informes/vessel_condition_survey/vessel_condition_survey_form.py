import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from tkcalendar import DateEntry

from Modulos.Informes.Vessel_Draft_Survey.popup_servicio_draft_selector import PopupServicioDraftSelector
from Modulos.Informes.informes_home_ui import InformesHomeUI


class VesselConditionSurveyForm(ttk.Frame):
    """
    ERP-SOM — VESSEL CONDITION SURVEY

    Reportes soportados:
    - Cargo Holds Condition
    - Hull Condition
    - Mooring Lines Condition (Mooring Ropes)
    - P&I Vessel Condition Survey

    Requerimientos implementados:
    - Botón Home -> InformesHomeUI
    - Botón Enviar a Revisión -> STUB listo para conectar después
    - Botón Improve Maritime IA -> STUB listo para conectar después
    - Botón Seleccionar Reporte -> PopupServicioDraftSelector
    - Autofill desde popup
    - Scroll vertical con barra + mouse wheel
    - Fechas en formato LONG en inglés apenas se seleccionan
    - Secciones 4, 5, 6 y 7 con bullets dinámicos hasta 20 por sección
    - Sección 8 con Link Picture
    """

    MAX_DYNAMIC_ITEMS = 20

    REPORT_TYPE_OPTIONS = [
        "Cargo Holds Condition",
        "Hull Condition",
        "Mooring Lines Condition (Mooring Ropes)",
        "P&I Vessel Condition Survey"
    ]

    OPERATION_OPTIONS = [
        "",
        "Charging",
        "Discharge"
    ]

    # =========================================================
    # INIT
    # =========================================================
    def __init__(self, parent, usuario=None, rol=None, on_back=None):
        super().__init__(parent)

        self.parent = parent
        self.usuario = usuario
        self.rol = rol
        self.on_back = on_back

        self.vars = {}
        self.date_widgets = {}
        self.dynamic_sections = {}

        self.pack(fill="both", expand=True)
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
        self._build_topbar()
        self._build_scrollable_area()
        self._build_header_section()
        self._build_section_1_introduction()
        self._build_section_2_vessel()
        self._build_section_3_extract_time_sheet()
        self._build_dynamic_text_section("4. NARRATIVE", "narrative")
        self._build_dynamic_text_section("5. SURVEY FINDINGS", "survey_findings")
        self._build_dynamic_text_section("6. REMARKS", "remarks")
        self._build_dynamic_text_section("7. CONCLUSION", "conclusion")
        self._build_section_8_enclosure()

        ttk.Label(self.scroll_frame, text="").pack(pady=10)

    # =========================================================
    # TOPBAR
    # =========================================================
    def _build_topbar(self):
        topbar = ttk.Frame(self)
        topbar.pack(fill="x", padx=10, pady=(10, 0))

        left = ttk.Frame(topbar)
        left.pack(side="left", fill="x", expand=True)

        ttk.Label(
            left,
            text="VESSEL CONDITION SURVEY",
            font=("Segoe UI", 14, "bold")
        ).pack(side="left")

        right = ttk.Frame(topbar)
        right.pack(side="right")

        ttk.Button(
            right,
            text="Seleccionar Reporte",
            command=self._select_service
        ).pack(side="left", padx=4)

        ttk.Button(
            right,
            text="Improve Maritime IA",
            command=self._improve_ai_maritime
        ).pack(side="left", padx=4)

        ttk.Button(
            right,
            text="Enviar a Revisión",
            command=self._send_to_review
        ).pack(side="left", padx=4)

        ttk.Button(
            right,
            text="Home",
            command=self._go_home
        ).pack(side="left", padx=4)

    # =========================================================
    # SCROLL AREA
    # =========================================================
    def _build_scrollable_area(self):
        container = ttk.Frame(self)
        container.pack(fill="both", expand=True, padx=10, pady=10)

        self.canvas = tk.Canvas(container, highlightthickness=0)
        self.v_scroll = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)

        self.canvas.configure(yscrollcommand=self.v_scroll.set)

        self.v_scroll.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.scroll_frame = ttk.Frame(self.canvas)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")

        self.scroll_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        self.scroll_frame.bind("<Enter>", self._bind_mousewheel)
        self.scroll_frame.bind("<Leave>", self._unbind_mousewheel)

    def _on_frame_configure(self, event=None):
        try:
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        except Exception:
            pass

    def _on_canvas_configure(self, event):
        try:
            self.canvas.itemconfig(self.canvas_window, width=event.width)
        except Exception:
            pass

    def _bind_mousewheel(self, event=None):
        try:
            self.canvas.bind_all("<MouseWheel>", self._on_mousewheel_windows)
            self.canvas.bind_all("<Button-4>", self._on_mousewheel_linux_up)
            self.canvas.bind_all("<Button-5>", self._on_mousewheel_linux_down)
        except Exception:
            pass

    def _unbind_mousewheel(self, event=None):
        try:
            self.canvas.unbind_all("<MouseWheel>")
            self.canvas.unbind_all("<Button-4>")
            self.canvas.unbind_all("<Button-5>")
        except Exception:
            pass

    def _on_mousewheel_windows(self, event):
        try:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
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
    # COMMON HELPERS
    # =========================================================
    def _section_title(self, parent, number_text, title_text):
        wrapper = ttk.Frame(parent)
        wrapper.pack(fill="x", pady=(0, 8))

        ttk.Label(
            wrapper,
            text=number_text,
            font=("Segoe UI", 11, "bold")
        ).pack(side="left", padx=(0, 16))

        ttk.Label(
            wrapper,
            text=title_text,
            font=("Segoe UI", 11, "bold")
        ).pack(side="left")

        return wrapper

    def _make_row(self, parent, left_text, right_widget_builder=None, pady=2):
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=pady)

        left_lbl = ttk.Label(row, text=left_text)
        left_lbl.pack(side="left", anchor="w")

        if right_widget_builder:
            right_frame = ttk.Frame(row)
            right_frame.pack(side="left", fill="x", expand=True, padx=(10, 0))
            right_widget_builder(right_frame)

        return row

    def _readonly_entry(self, parent, key, width=40):
        entry = ttk.Entry(parent, textvariable=self._v(key), width=width, state="readonly")
        entry.pack(side="left", fill="x", expand=True)
        return entry

    def _normal_entry(self, parent, key, width=40):
        entry = ttk.Entry(parent, textvariable=self._v(key), width=width)
        entry.pack(side="left", fill="x", expand=True)
        return entry

    def _combobox(self, parent, key, values, width=38, readonly=True):
        combo = ttk.Combobox(
            parent,
            textvariable=self._v(key),
            values=values,
            width=width,
            state="readonly" if readonly else "normal"
        )
        combo.pack(side="left", fill="x", expand=True)
        return combo

    def _format_text_date_long(self, value):
        if not value:
            return ""

        value = str(value).strip()
        if not value:
            return ""

        for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%B %d, %Y", "%Y/%m/%d"):
            try:
                dt = datetime.strptime(value[:19], fmt)
                return dt.strftime("%B %d, %Y")
            except Exception:
                continue

        try:
            dt = datetime.fromisoformat(value.replace("Z", ""))
            return dt.strftime("%B %d, %Y")
        except Exception:
            pass

        return value

    def _normalize_date_for_db(self, value):
        if not value:
            return None

        raw = str(value).strip()
        if not raw:
            return None

        for fmt in ("%Y-%m-%d", "%B %d, %Y", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
            except Exception:
                continue

        try:
            return datetime.fromisoformat(raw.replace("Z", "")).strftime("%Y-%m-%d")
        except Exception:
            return None

    def _normalize_hh(self, value):
        if value is None:
            return None
        s = str(value).strip()
        if not s.isdigit():
            return None
        n = int(s)
        if n < 0 or n > 23:
            return None
        return f"{n:02d}"

    def _normalize_mm(self, value):
        if value is None:
            return None
        s = str(value).strip()
        if not s.isdigit():
            return None
        n = int(s)
        if n < 0 or n > 59:
            return None
        return f"{n:02d}"

    def _set_var_safely(self, key, value):
        self._v(key).set("" if value is None else str(value))

    # =========================================================
    # DATE / DATETIME WIDGET
    # =========================================================
    def _build_datetime_row(self, parent, label_text, key_prefix):
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=2)

        ttk.Label(row, text=label_text, width=38).pack(side="left", anchor="w")

        date_frame = ttk.Frame(row)
        date_frame.pack(side="left")

        date_var = self._v(f"{key_prefix}_date")

        date_entry = DateEntry(
            date_frame,
            textvariable=date_var,
            width=18,
            locale="en_US",
            date_pattern="yyyy-mm-dd"
        )
        date_entry.pack(side="left")

        self.date_widgets[key_prefix] = date_entry

        date_entry.bind("<<DateEntrySelected>>", lambda e, k=key_prefix: self._lock_long_date(k))
        date_entry.bind("<FocusOut>", lambda e, k=key_prefix: self._lock_long_date(k))

        ttk.Label(date_frame, text="  HH").pack(side="left", padx=(8, 2))
        hh_entry = ttk.Entry(
            date_frame,
            textvariable=self._v(f"{key_prefix}_hour"),
            width=4
        )
        hh_entry.pack(side="left")

        ttk.Label(date_frame, text="  MM").pack(side="left", padx=(8, 2))
        mm_entry = ttk.Entry(
            date_frame,
            textvariable=self._v(f"{key_prefix}_minute"),
            width=4
        )
        mm_entry.pack(side="left")

        return row

    def _lock_long_date(self, key_prefix):
        var = self._v(f"{key_prefix}_date")
        current = var.get()

        if not current:
            return

        formatted = self._format_text_date_long(current)
        if formatted:
            var.set(formatted)

    def _set_long_date_value(self, key_prefix, value):
        formatted = self._format_text_date_long(value)
        self._v(f"{key_prefix}_date").set(formatted)

    # =========================================================
    # HEADER SECTION
    # =========================================================
    def _build_header_section(self):
        box = ttk.LabelFrame(self.scroll_frame, text="Header")
        box.pack(fill="x", pady=(0, 10))

        inner = ttk.Frame(box)
        inner.pack(fill="x", padx=12, pady=10)

        # ================= REPORT NUMBER =================

        ttk.Label(inner, text="Report Number").grid(
            row=0, column=0, sticky="w", padx=5, pady=4
        )

        ttk.Entry(
            inner,
            textvariable=self._v("report_number"),
            state="readonly",
            width=30
        ).grid(
            row=0, column=1, sticky="w", padx=5, pady=4
        )

        ttk.Label(inner, text="Continent").grid(
            row=1, column=0, sticky="w", padx=5, pady=4
        )

        ttk.Entry(
            inner,
            textvariable=self._v("continent"),
            state="readonly",
            width=30
        ).grid(
            row=1, column=1, sticky="w", padx=5, pady=4
        )

        ttk.Label(inner, text="Country").grid(
            row=1, column=2, sticky="w", padx=5, pady=4
        )

        ttk.Entry(
            inner,
            textvariable=self._v("country"),
            state="readonly",
            width=30
        ).grid(
            row=1, column=3, sticky="w", padx=5, pady=4
        )

        ttk.Label(inner, text="Port").grid(
            row=2, column=0, sticky="w", padx=5, pady=4
        )

        ttk.Entry(
            inner,
            textvariable=self._v("port"),
            state="readonly",
            width=30
        ).grid(
            row=2, column=1, sticky="w", padx=5, pady=4
        )

        ttk.Label(inner, text="Operation (popup)").grid(
            row=2, column=2, sticky="w", padx=5, pady=4
        )

        ttk.Entry(
            inner,
            textvariable=self._v("popup_operation"),
            state="readonly",
            width=30
        ).grid(
            row=2, column=3, sticky="w", padx=5, pady=4
        )

    # =========================================================
    # SECTION 1 - INTRODUCTIONS
    # =========================================================
    def _build_section_1_introduction(self):
        box = ttk.LabelFrame(self.scroll_frame, text="")
        box.pack(fill="x", pady=(0, 10), padx=0)

        inner = ttk.Frame(box)
        inner.pack(fill="x", padx=12, pady=12)

        self._section_title(inner, "1.", "INTRODUCTIONS")

        # 1.1 Purpose
        row_11 = ttk.Frame(inner)
        row_11.pack(fill="x", pady=(10, 0))
        ttk.Label(row_11, text="1.1.", width=8).pack(side="left", anchor="n")
        ttk.Label(row_11, text="Purpose", font=("Segoe UI", 10)).pack(side="left", anchor="n")

        # Narrative intro + dropdown
        intro_row = ttk.Frame(inner)
        intro_row.pack(fill="x", pady=(10, 8))

        ttk.Label(intro_row, text="", width=8).pack(side="left")

        intro_text_frame = ttk.Frame(intro_row)
        intro_text_frame.pack(side="left", fill="x", expand=True)

        line_1 = ttk.Frame(intro_text_frame)
        line_1.pack(fill="x")

        ttk.Label(
            line_1,
            text="We, MSL Marine Surveyors and Logistics Group, SRL, were appointed to inspect and carry out the",
            wraplength=900,
            justify="left"
        ).pack(side="left")

        report_combo = ttk.Combobox(
            line_1,
            textvariable=self._v("report_type"),
            values=self.REPORT_TYPE_OPTIONS,
            width=42,
            state="readonly"
        )
        report_combo.pack(side="left", padx=(8, 0))

        line_2 = ttk.Frame(intro_text_frame)
        line_2.pack(fill="x", pady=(4, 0))

        ttk.Label(
            line_2,
            text='in ',
            justify="left"
        ).pack(side="left")

        vessel_lbl = ttk.Label(
            line_2,
            textvariable=self._v("vessel_display_bold"),
            font=("Segoe UI", 10, "bold")
        )
        vessel_lbl.pack(side="left")

        ttk.Label(
            line_2,
            text=" at ",
            justify="left"
        ).pack(side="left")

        port_lbl = ttk.Label(
            line_2,
            textvariable=self._v("port_country_display"),
            font=("Segoe UI", 10)
        )
        port_lbl.pack(side="left")

        ttk.Label(
            line_2,
            text=".",
            justify="left"
        ).pack(side="left")

        # INSTRUCTIONS
        instr_title = ttk.Frame(inner)
        instr_title.pack(fill="x", pady=(14, 0))
        ttk.Label(instr_title, text="", width=8).pack(side="left")
        ttk.Label(instr_title, text="INSTRUCTIONS", font=("Segoe UI", 10, "bold")).pack(side="left")

        req_row = ttk.Frame(inner)
        req_row.pack(fill="x", pady=(6, 0))
        ttk.Label(req_row, text="1.1.1.", width=8).pack(side="left")
        ttk.Label(req_row, text="SURVEY REQUESTED BY", width=24, font=("Segoe UI", 10)).pack(side="left")

        req_right = ttk.Frame(req_row)
        req_right.pack(side="left")

        ttk.Entry(
            req_right,
            textvariable=self._v("requested_by"),
            state="readonly",
            width=28 
        ).pack(side="left")

        # 1.2 Time and place
        section_12 = ttk.Frame(inner)
        section_12.pack(fill="x", pady=(14, 0))
        ttk.Label(section_12, text="1.2.", width=8).pack(side="left")
        ttk.Label(
            section_12,
            text="TIME AND PLACE OF ARRIVAL OF THE SHIP AND INSPECTION:",
            font=("Segoe UI", 10, "bold")
        ).pack(side="left")

        sub_121 = ttk.Frame(inner)
        sub_121.pack(fill="x", pady=(6, 0))
        ttk.Label(sub_121, text="1.2.1.", width=8).pack(side="left")
        ttk.Label(sub_121, text="DATE OF ARRIVAL", width=34).pack(side="left")
        right_121 = ttk.Frame(sub_121)
        right_121.pack(side="left", fill="x", expand=True)
        self._build_datetime_row(right_121, "", "arrival")
        # quitar label interno vacío
        for child in right_121.winfo_children():
            if isinstance(child, ttk.Frame):
                for sub in child.winfo_children():
                    pass

        sub_122 = ttk.Frame(inner)
        sub_122.pack(fill="x", pady=(4, 0))
        ttk.Label(sub_122, text="1.2.2.", width=8).pack(side="left")
        ttk.Label(sub_122, text="DATE / TIME OF INSPECTION", width=34).pack(side="left")
        right_122 = ttk.Frame(sub_122)
        right_122.pack(side="left", fill="x", expand=True)
        self._build_datetime_row(right_122, "", "inspection")

        # 1.3 Representatives
        section_13 = ttk.Frame(inner)
        section_13.pack(fill="x", pady=(14, 0))
        ttk.Label(section_13, text="1.3.", width=8).pack(side="left")
        ttk.Label(section_13, text="REPRESENTATIVES", font=("Segoe UI", 10, "bold")).pack(side="left")

        rep_131 = ttk.Frame(inner)
        rep_131.pack(fill="x", pady=(6, 0))
        ttk.Label(rep_131, text="1.3.1.", width=8).pack(side="left")
        ttk.Label(rep_131, text="MASTER OF THE SHIP", width=34).pack(side="left")
        rep_131_right = ttk.Frame(rep_131)
        rep_131_right.pack(side="left")
        ttk.Entry(
            rep_131_right,
            textvariable=self._v("master_of_ship"),
            width=28
        ).pack(side="left")

        rep_132 = ttk.Frame(inner)
        rep_132.pack(fill="x", pady=(4, 0))
        ttk.Label(rep_132, text="1.3.2.", width=8).pack(side="left")
        ttk.Label(rep_132, text="CHIEF OFFICER", width=34).pack(side="left")
        rep_132_right = ttk.Frame(rep_132)
        rep_132_right.pack(side="left")
        ttk.Entry(
            rep_132_right,
            textvariable=self._v("chief_officer"),
            width=28
        ).pack(side="left")

    # =========================================================
    # SECTION 2 - THE VESSEL
    # =========================================================
    def _build_section_2_vessel(self):
        box = ttk.LabelFrame(self.scroll_frame, text="")
        box.pack(fill="x", pady=(0, 10))

        inner = ttk.Frame(box)
        inner.pack(fill="x", padx=12, pady=12)

        self._section_title(inner, "2.", "THE VESSEL")

        rows = ttk.Frame(inner)
        rows.pack(fill="x", pady=(8, 0))

        # 2.1
        r1 = ttk.Frame(rows)
        r1.pack(fill="x", pady=1)
        ttk.Label(r1, text="2.1.", width=8).pack(side="left")
        ttk.Label(r1, text="Name", width=24).pack(side="left")
        ttk.Entry(r1, textvariable=self._v("vessel"), state="readonly", width=28).pack(side="left")

        # 2.2
        r2 = ttk.Frame(rows)
        r2.pack(fill="x", pady=1)
        ttk.Label(r2, text="2.2.", width=8).pack(side="left")
        ttk.Label(r2, text="Port Of Registry / Flag", width=24).pack(side="left")
        ttk.Entry(r2, textvariable=self._v("port_registry_flag"), width=28).pack(side="left")

        # 2.3
        r3 = ttk.Frame(rows)
        r3.pack(fill="x", pady=1)
        ttk.Label(r3, text="2.3.", width=8).pack(side="left")
        ttk.Label(r3, text="GRT", width=24).pack(side="left")
        ttk.Entry(r3, textvariable=self._v("grt"), width=28).pack(side="left")

        # 2.4
        r4 = ttk.Frame(rows)
        r4.pack(fill="x", pady=1)
        ttk.Label(r4, text="2.4.", width=8).pack(side="left")
        ttk.Label(r4, text="Operation", width=24).pack(side="left")
        ttk.Combobox(
            r4,
            textvariable=self._v("operation"),
            values=self.OPERATION_OPTIONS,
            width=26,
            state="readonly"
        ).pack(side="left")

        # 2.5
        r5 = ttk.Frame(rows)
        r5.pack(fill="x", pady=1)
        ttk.Label(r5, text="2.5.", width=8).pack(side="left")
        ttk.Label(r5, text="NRT", width=24).pack(side="left")
        ttk.Entry(r5, textvariable=self._v("nrt"), width=28).pack(side="left")

        # 2.6
        r6 = ttk.Frame(rows)
        r6.pack(fill="x", pady=1)
        ttk.Label(r6, text="2.6.", width=8).pack(side="left")
        ttk.Label(r6, text="IMO N°", width=24).pack(side="left")
        ttk.Entry(r6, textvariable=self._v("imo_no"), width=28).pack(side="left")

        # 2.7
        r7 = ttk.Frame(rows)
        r7.pack(fill="x", pady=1)
        ttk.Label(r7, text="2.7.", width=8).pack(side="left")
        ttk.Label(r7, text="Year Built", width=24).pack(side="left")
        ttk.Entry(r7, textvariable=self._v("year_built"), width=28).pack(side="left")

    # =========================================================
    # SECTION 3 - EXTRACT TIME SHEET
    # =========================================================
    def _build_section_3_extract_time_sheet(self):
        box = ttk.LabelFrame(self.scroll_frame, text="")
        box.pack(fill="x", pady=(0, 10))

        inner = ttk.Frame(box)
        inner.pack(fill="x", padx=12, pady=12)

        self._section_title(inner, "3.", "EXTRACT TIME SHEET")

        self.time_sheet_rows = [
            ("3.1.", "Vessel Arrived at sea buoy", "ts_1"),
            ("3.2.", "N.O.R Tendered", "ts_2"),
            ("3.3.", "Vessel Berthed", "ts_3"),
            ("3.4.", "Discharge commenced", "ts_4"),
            ("3.5.", "Surveyor on board", "ts_5"),
            ("3.6.", "Master Meeting", "ts_6"),
            ("3.7.", "Visual Inspection", "ts_7"),
            ("3.8.", "Surveyor off", "ts_8"),
        ]

        table = ttk.Frame(inner)
        table.pack(fill="x", pady=(8, 0))

        for num, label, key in self.time_sheet_rows:
            row = ttk.Frame(table)
            row.pack(fill="x", pady=1)

            ttk.Label(row, text=num, width=8).pack(side="left")
            ttk.Label(row, text=label, width=28).pack(side="left")
            right = ttk.Frame(row)
            right.pack(side="left")

            self._build_datetime_row(right, "", key)

    # =========================================================
    # SECTION 4/5/6/7 - DYNAMIC TEXT
    # =========================================================
    def _build_dynamic_text_section(self, title, section_key):
        box = ttk.LabelFrame(self.scroll_frame, text="")
        box.pack(fill="x", pady=(0, 10))

        inner = ttk.Frame(box)
        inner.pack(fill="x", padx=12, pady=12)

        parts = title.split(" ", 1)
        number_text = parts[0]
        title_text = parts[1] if len(parts) > 1 else title
        self._section_title(inner, number_text, title_text)

        toolbar = ttk.Frame(inner)
        toolbar.pack(fill="x", pady=(8, 6))

        ttk.Button(
            toolbar,
            text="+ Add bullet",
            command=lambda s=section_key: self._add_dynamic_item(s)
        ).pack(side="right")

        container = ttk.Frame(inner)
        container.pack(fill="x")

        self.dynamic_sections[section_key] = {
            "container": container,
            "items": []
        }

        self._add_dynamic_item(section_key)

    def _add_dynamic_item(self, section_key, value=""):
        section = self.dynamic_sections.get(section_key)
        if not section:
            return

        items = section["items"]
        container = section["container"]

        if len(items) >= self.MAX_DYNAMIC_ITEMS:
            messagebox.showwarning(
                "Límite alcanzado",
                f"Solo se permiten hasta {self.MAX_DYNAMIC_ITEMS} bullet points en esta sección."
            )
            return

        item_frame = ttk.Frame(container)
        item_frame.pack(fill="x", pady=4)

        number_label = ttk.Label(item_frame, text="", width=8)
        number_label.pack(side="left", anchor="n", pady=(4, 0))

        bullet_label = ttk.Label(item_frame, text="•", width=2)
        bullet_label.pack(side="left", anchor="n", pady=(4, 0))

        text_widget = tk.Text(
            item_frame,
            height=4,
            wrap="word",
            undo=True
        )
        text_widget.pack(side="left", fill="x", expand=True)

        if value:
            text_widget.insert("1.0", value)

        actions = ttk.Frame(item_frame)
        actions.pack(side="left", padx=(6, 0), anchor="n")

        ttk.Button(
            actions,
            text="-",
            width=3,
            command=lambda s=section_key, f=item_frame: self._remove_dynamic_item(s, f)
        ).pack()

        item_meta = {
            "frame": item_frame,
            "number_label": number_label,
            "text": text_widget
        }
        items.append(item_meta)

        self._refresh_dynamic_numbers(section_key)

    def _remove_dynamic_item(self, section_key, frame):
        section = self.dynamic_sections.get(section_key)
        if not section:
            return

        items = section["items"]

        if len(items) <= 1:
            for meta in items:
                if meta["frame"] == frame:
                    meta["text"].delete("1.0", "end")
                    return
            return

        new_items = []
        for meta in items:
            if meta["frame"] == frame:
                try:
                    meta["frame"].destroy()
                except Exception:
                    pass
            else:
                new_items.append(meta)

        section["items"] = new_items
        self._refresh_dynamic_numbers(section_key)

    def _refresh_dynamic_numbers(self, section_key):
        section = self.dynamic_sections.get(section_key)
        if not section:
            return

        items = section["items"]
        section_number = {
            "narrative": "4",
            "survey_findings": "5",
            "remarks": "6",
            "conclusion": "7",
        }.get(section_key, "")

        for idx, meta in enumerate(items, start=1):
            meta["number_label"].configure(text=f"{section_number}.{idx}.")

    # =========================================================
    # SECTION 8 - ENCLOSURE
    # =========================================================
    def _build_section_8_enclosure(self):
        box = ttk.LabelFrame(self.scroll_frame, text="")
        box.pack(fill="x", pady=(0, 10))

        inner = ttk.Frame(box)
        inner.pack(fill="x", padx=12, pady=12)

        self._section_title(inner, "8.", "ENCLOSURE")

        row = ttk.Frame(inner)
        row.pack(fill="x", pady=(10, 0))

        ttk.Label(row, text="8.1.", width=8).pack(side="left")
        ttk.Label(row, text="LINK PICTURE", width=24).pack(side="left")
        ttk.Entry(
            row,
            textvariable=self._v("link_picture")
        ).pack(side="left")

    # =========================================================
    # POPUP SELECTOR
    # =========================================================
    def _select_service(self):
        try:
            PopupServicioDraftSelector(
                self.parent,
                on_select=self._on_service_selected
            )
        except Exception as e:
            messagebox.showerror("Seleccionar Reporte", str(e))

    def _on_service_selected(self, values):
        """
        popup returns:
        (
            num_informe,
            buque,
            cliente,
            continente,
            pais,
            puerto,
            operacion,
            fecha_inicio
        )
        """
        try:
            if not values or len(values) < 8:
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

            self._set_var_safely("report_number", num_informe)
            self._set_var_safely("vessel", buque)
            self._set_var_safely("requested_by", cliente)
            self._set_var_safely("continent", continente)
            self._set_var_safely("country", pais)
            self._set_var_safely("port", puerto)
            self._set_var_safely("popup_operation", operacion)

            # operation user-facing normalized
            op = str(operacion or "").strip().lower()
            if op in ("carga", "loading", "charge", "charging"):
                self._set_var_safely("operation", "Charging")
            elif op in ("descarga", "discharge", "unloading"):
                self._set_var_safely("operation", "Discharge")

            self._set_var_safely("service_start_date", fecha_inicio)

            # Arrival date autofill from popup date
            if fecha_inicio:
                self._set_long_date_value("arrival", fecha_inicio)

            # textos de introducción
            vessel_text = f'MV "{buque}"' if buque else ""
            port_country = ""
            if puerto and pais:
                port_country = f"{puerto} – {pais}"
            elif puerto:
                port_country = str(puerto)
            elif pais:
                port_country = str(pais)

            self._set_var_safely("vessel_display_bold", vessel_text)
            self._set_var_safely("port_country_display", port_country)

        except Exception as e:
            messagebox.showerror("Autofill Reporte", str(e))

    # =========================================================
    # STUB BUTTONS
    # =========================================================
    def _improve_ai_maritime(self):
        messagebox.showinfo(
            "Improve Maritime IA",
            "Este botón ya quedó creado en el form.\n\nLa conexión lógica con IA se activará después."
        )

    def _send_to_review(self):
        try:
            payload = self._build_payload()

            # Stub actual
            messagebox.showinfo(
                "Enviar a Revisión",
                "El botón ya quedó creado y el payload ya se construye correctamente.\n\n"
                "Luego conectamos el endpoint.\n\n"
                f"Preview payload keys: {len(payload)} campos."
            )
        except Exception as e:
            messagebox.showerror("Enviar a Revisión", str(e))

    # =========================================================
    # PAYLOAD
    # =========================================================
    def _build_payload(self):
        payload = {}

        # Header / popup
        payload["report_number"] = self._v("report_number").get() or None
        payload["continent"] = self._v("continent").get() or None
        payload["country"] = self._v("country").get() or None
        payload["port"] = self._v("port").get() or None
        payload["popup_operation"] = self._v("popup_operation").get() or None
        payload["service_start_date"] = self._normalize_date_for_db(self._v("service_start_date").get())

        # Section 1
        payload["report_type"] = self._v("report_type").get() or None
        payload["requested_by"] = self._v("requested_by").get() or None
        payload["arrival_date"] = self._normalize_date_for_db(self._v("arrival_date").get())
        payload["arrival_hour"] = self._normalize_hh(self._v("arrival_hour").get())
        payload["arrival_minute"] = self._normalize_mm(self._v("arrival_minute").get())

        payload["inspection_date"] = self._normalize_date_for_db(self._v("inspection_date").get())
        payload["inspection_hour"] = self._normalize_hh(self._v("inspection_hour").get())
        payload["inspection_minute"] = self._normalize_mm(self._v("inspection_minute").get())

        payload["master_of_ship"] = self._v("master_of_ship").get() or None
        payload["chief_officer"] = self._v("chief_officer").get() or None

        # Section 2
        payload["vessel"] = self._v("vessel").get() or None
        payload["port_registry_flag"] = self._v("port_registry_flag").get() or None
        payload["grt"] = self._v("grt").get() or None
        payload["operation"] = self._v("operation").get() or None
        payload["nrt"] = self._v("nrt").get() or None
        payload["imo_no"] = self._v("imo_no").get() or None
        payload["year_built"] = self._v("year_built").get() or None

        # Section 3
        for _, _, key in self.time_sheet_rows:
            payload[f"{key}_date"] = self._normalize_date_for_db(self._v(f"{key}_date").get())
            payload[f"{key}_hour"] = self._normalize_hh(self._v(f"{key}_hour").get())
            payload[f"{key}_minute"] = self._normalize_mm(self._v(f"{key}_minute").get())

        # Dynamic sections 4-7
        for section_key in ["narrative", "survey_findings", "remarks", "conclusion"]:
            section = self.dynamic_sections.get(section_key, {})
            items = section.get("items", [])

            for i in range(1, self.MAX_DYNAMIC_ITEMS + 1):
                payload[f"{section_key}_{i}"] = None

            for idx, meta in enumerate(items, start=1):
                if idx > self.MAX_DYNAMIC_ITEMS:
                    break
                text = meta["text"].get("1.0", "end").strip()
                payload[f"{section_key}_{idx}"] = text if text else None

        # Section 8
        payload["link_picture"] = self._v("link_picture").get() or None

        return payload

    # =========================================================
    # LOAD RECORD
    # =========================================================
    def load_record(self, data):
        try:
            if not data:
                return

            # normal vars
            normal_fields = [
                "report_number",
                "continent",
                "country",
                "port",
                "popup_operation",
                "service_start_date",
                "report_type",
                "requested_by",
                "master_of_ship",
                "chief_officer",
                "vessel",
                "port_registry_flag",
                "grt",
                "operation",
                "nrt",
                "imo_no",
                "year_built",
                "link_picture",
            ]

            for key in normal_fields:
                if key in data:
                    self._set_var_safely(key, data.get(key))

            # date fields section 1
            if data.get("arrival_date"):
                self._set_long_date_value("arrival", data.get("arrival_date"))
            self._set_var_safely("arrival_hour", data.get("arrival_hour"))
            self._set_var_safely("arrival_minute", data.get("arrival_minute"))

            if data.get("inspection_date"):
                self._set_long_date_value("inspection", data.get("inspection_date"))
            self._set_var_safely("inspection_hour", data.get("inspection_hour"))
            self._set_var_safely("inspection_minute", data.get("inspection_minute"))

            # section 3
            for _, _, key in self.time_sheet_rows:
                if data.get(f"{key}_date"):
                    self._set_long_date_value(key, data.get(f"{key}_date"))
                self._set_var_safely(f"{key}_hour", data.get(f"{key}_hour"))
                self._set_var_safely(f"{key}_minute", data.get(f"{key}_minute"))

            # intro display fields
            vessel = self._v("vessel").get()
            port = self._v("port").get()
            country = self._v("country").get()

            self._set_var_safely("vessel_display_bold", f'MV "{vessel}"' if vessel else "")

            port_country = ""
            if port and country:
                port_country = f"{port} – {country}"
            elif port:
                port_country = port
            elif country:
                port_country = country
            self._set_var_safely("port_country_display", port_country)

            # dynamic sections
            for section_key in ["narrative", "survey_findings", "remarks", "conclusion"]:
                incoming_values = []
                for i in range(1, self.MAX_DYNAMIC_ITEMS + 1):
                    value = data.get(f"{section_key}_{i}")
                    if value:
                        incoming_values.append(str(value))

                section = self.dynamic_sections.get(section_key)
                if not section:
                    continue

                items = section["items"]

                # limpiar primero
                for meta in items:
                    meta["text"].delete("1.0", "end")

                # agregar cajas si hacen falta
                while len(section["items"]) < max(1, len(incoming_values)):
                    self._add_dynamic_item(section_key)

                items = section["items"]

                if not incoming_values:
                    continue

                for idx, value in enumerate(incoming_values):
                    items[idx]["text"].delete("1.0", "end")
                    items[idx]["text"].insert("1.0", value)

        except Exception as e:
            messagebox.showerror("Load Record", str(e))

    # =========================================================
    # HOME
    # =========================================================
    def _go_home(self):
        try:
            self.destroy()

            if callable(self.on_back):
                self.on_back()
                return

            InformesHomeUI(
                self.parent,
                usuario=self.usuario,
                rol=self.rol
            )

        except Exception as e:
            messagebox.showerror("Home", str(e))