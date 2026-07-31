import tkinter as tk
from tkinter import ttk, messagebox

from Modulos.Informes.Vessel_Draft_Survey.popup_servicio_draft_selector import PopupServicioDraftSelector
from Modulos.Informes.informes_home_ui import InformesHomeUI
from Modulos.Informes.date_utils import to_db_date, to_long_english_date
from api_client import create_weight_certificate_api


class WeightCertificateForm(ttk.Frame):

    def __init__(self, parent, usuario=None, rol=None, on_back=None):

        super().__init__(parent)

        self.parent = parent
        self.usuario = usuario
        self.rol = rol
        self.on_back = on_back

        self.vars = {}

        # ================================
        # EDIT MODE
        # ================================
        self.record_id = None
        self.edit_mode = False


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
    # BUILD UI
    # =========================================================

    def _build_ui(self):

        self._build_topbar()
        self._build_scrollable()

        self._build_header()
        self._build_certificate_data()
        self._build_quantity()
        self._build_remarks()

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
            text="WEIGHT CERTIFICATE",
            font=("Segoe UI", 14, "bold")
        ).pack(side="left")

        right = ttk.Frame(bar)
        right.pack(side="right")

        ttk.Button(
            right,
            text="Seleccionar Servicio",
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
            (0,0),
            window=self.scroll_frame,
            anchor="nw"
        )

        self.canvas.configure(
            yscrollcommand=scrollbar.set
        )

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.canvas.bind_all(
            "<MouseWheel>",
            self._on_mousewheel
        )

    def _on_mousewheel(self, event):

        self.canvas.yview_scroll(
            int(-1*(event.delta/120)),
            "units"
        )

    # =========================================================
    # HEADER
    # =========================================================

    def _build_header(self):

        box = ttk.LabelFrame(
            self.scroll_frame,
            text="Header"
        )
        box.pack(fill="x", pady=(0,10))

        inner = ttk.Frame(box)
        inner.pack(fill="x", padx=10, pady=10)

        fields = [

            ("Report Number","report_number"),
            ("Continent","continent"),
            ("Country","country"),
            ("Port","port"),
            ("Operation","operation")

        ]

        for i,(label,key) in enumerate(fields):

            ttk.Label(
                inner,
                text=label,
                width=24
            ).grid(
                row=i,
                column=0,
                sticky="w",
                padx=5,
                pady=4
            )

            entry = ttk.Entry(
                inner,
                textvariable=self._v(key),
                width=50
            )

            entry.grid(
                row=i,
                column=1,
                sticky="w",
                padx=5,
                pady=4
            )

            # Aplicar formato LONG al campo Date
            if key == "date":

                entry.bind(
                    "<FocusOut>",
                    lambda e, v=self._v("date"): self._fix_date_format(e, v)
                )


    # =========================================================
    # CERTIFICATE DATA
    # =========================================================

    def _build_certificate_data(self):

        box = ttk.LabelFrame(
            self.scroll_frame,
            text="Weight Certificate Data"
        )
        box.pack(fill="x", pady=(0,10))

        inner = ttk.Frame(box)
        inner.pack(fill="x", padx=10, pady=10)

        fields = [

            ("Vessel","vessel"),
            ("Voyage Number","voyage"),
            ("Commodity Described As","commodity"),
            ("Bill of Lading Figure","bl_figure"),
            ("Cargo Hold","cargo_hold"),
            ("Shipper","shipper"),
            ("Consignee","consignee"),
            ("Terminal","terminal"),
            ("Loading Port","loading_port"),
            ("Weight Determination","weight_determination"),
            ("Date","date")

        ]

        for i,(label,key) in enumerate(fields):

            ttk.Label(
                inner,
                text=label,
                width=24
            ).grid(
                row=i,
                column=0,
                sticky="w",
                padx=5,
                pady=4
            )

            ttk.Entry(
                inner,
                textvariable=self._v(key),
                width=50
            ).grid(
                row=i,
                column=1,
                sticky="w",
                padx=5,
                pady=4
            )

    # =========================================================
    # QUANTITY
    # =========================================================

    def _build_quantity(self):

        box = ttk.LabelFrame(
            self.scroll_frame,
            text="Loaded Quantity"
        )
        box.pack(fill="x", pady=(0,10))

        row = ttk.Frame(box)
        row.pack(fill="x", padx=10, pady=10)

        ttk.Label(
            row,
            text="Metric Tons",
            width=20
        ).pack(side="left")

        ttk.Entry(
            row,
            textvariable=self._v("quantity"),
            width=20
        ).pack(side="left")

    # =========================================================
    # REMARKS
    # =========================================================

    def _build_remarks(self):

        box = ttk.LabelFrame(
            self.scroll_frame,
            text="Remarks"
        )
        box.pack(fill="both", pady=(0,10))

        self.remarks = tk.Text(
            box,
            height=6,
            wrap="word"
        )

        self.remarks.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=10
        )

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

        self._v("report_number").set(num_informe)
        self._v("vessel").set(buque)
        self._v("continent").set(continente)
        self._v("country").set(pais)
        self._v("port").set(puerto)
        self._v("operation").set(operacion)


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

            create_weight_certificate_api(payload)

            messagebox.showinfo(
                "ERP-SOM",
                "Weight Certificate successfully sent for review."
            )

        except Exception as e:

            messagebox.showerror(
                "ERP-SOM",
                f"Error sending report:\n{str(e)}"
            )

    # =========================================================
    # BUILD PAYLOAD
    # =========================================================
    def _build_payload(self):

        payload = {}

        # ================================
        # NORMAL FIELDS
        # ================================

        for key, var in self.vars.items():

            value = var.get()

            if key == "date":
                payload[key] = to_db_date(value) or None
            else:
                payload[key] = value if value else None

        # ================================
        # REMARKS
        # ================================

        try:

            remarks = self.remarks.get("1.0", "end").strip()

        except Exception:

            remarks = ""

        payload["remarks"] = remarks if remarks else None

        return payload

    # =========================================================
    # DATE FORMAT LONG (ENGLISH)
    # =========================================================

    def _format_long_date(self, value):

        if not value:
            return ""

        return to_long_english_date(value)


    def _fix_date_format(self, event, var):

        value = var.get()

        formatted = self._format_long_date(value)

        var.set(formatted)


    # =========================================================
    # SET EDIT MODE (cuando viene desde tabla)
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
    # LOAD RECORD (desde tabla)
    # =========================================================
    def load_record(self, data):

        if not data:
            return

        for key, var in self.vars.items():

            value = data.get(key)

            if value is not None:
                var.set(str(value))

        try:

            remarks = data.get("remarks")

            if remarks:

                self.remarks.delete("1.0", "end")
                self.remarks.insert("1.0", remarks)

        except Exception:
            pass



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

            from api_client import update_weight_certificate_api

            update_weight_certificate_api(
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
    # HOME
    # =========================================================

    def _go_home(self):

        self.destroy()

        InformesHomeUI(
            self.parent,
            usuario=self.usuario,
            rol=self.rol
        )
