import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date
from tkcalendar import DateEntry



from api_client import api_request
from Modulos.Informes.popup.popup_ai_compare import PopupAICompare
from api_client import create_container_report_api
from Modulos.Informes.popup.popup_container_report_selector import (
    PopupContainerReportSelector
)


class ContainerReportForm(ttk.Frame):
    """
    Container Inspection Report
    FULL STRUCTURE — aligned with real Excel inspection reports
    """

    def __init__(self, parent, usuario=None, rol=None, on_back=None):
        super().__init__(parent)

        self.parent = parent
        self.usuario = usuario
        self.rol = (rol or "").lower()
        self.on_back = on_back

        # 🔒 BLINDAJE DE LAYOUT (misma causa que ReportTypeSelector)
        try:
            parent.grid_rowconfigure(0, weight=1)
            parent.grid_columnconfigure(0, weight=1)
            parent.pack_propagate(False)
            parent.grid_propagate(False)
        except Exception:
            pass

        self.grid(row=0, column=0, sticky="nsew")
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.pack_propagate(False)

        # ==============================
        # STATE — REPORT SELECTOR
        # ==============================
        self.report_numbers = []
        self.selected_report_var = tk.StringVar()
        self.container_type_text = tk.StringVar()



        self._build_header()
        self._build_scrollable_form()

    # =========================================================
    # HEADER
    # =========================================================
    def _build_header(self):

        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 10))

        ttk.Label(
            header,
            text="Container Inspection Report",
            font=("Segoe UI", 14, "bold")
        ).pack(side="left")

        if self.on_back:
            ttk.Button(
                header,
                text="← Back",
                command=self.on_back
            ).pack(side="right")

    # =========================================================
    # SCROLLABLE FORM
    # =========================================================
    def _build_scrollable_form(self):

        canvas = tk.Canvas(self)
        canvas.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scrollbar.pack(side="right", fill="y")

        canvas.configure(yscrollcommand=scrollbar.set)

        self.form = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=self.form, anchor="nw")

        self.form.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        # 🔥 ACTIVAR SCROLL CON RUEDA (FIX REAL)
        self._bind_mousewheel(canvas)

        self._section_report_selector()

        self._section_general_information()
        self._section_container_description()
        self._section_cause_of_inspection()
        self._section_goods_and_packages()

        self._section_conditions_and_narratives()
        self._section_collected_documents()
        self._section_quality()

        self._section_inspected_container()
        self._section_general_details()
        self._section_transfer_to_container()
        self._section_scope_of_inspection()

        self._section_persons_and_signature()
        self._section_actions()

    # =========================================================
    # SECTIONS
    # =========================================================
    def _section_general_information(self):

        frm = ttk.LabelFrame(self.form, text="General Information")
        frm.pack(fill="x", pady=10)

        self.no = self._field(frm, "No.", 0)
        self.bl = self._field(frm, "B / L", 1)
        self.seals = self._field(frm, "Seals", 2)
        self.appointment = self._field(frm, "Appointment", 3)
        self.shippers = self._field(frm, "Shippers", 4)

        self.insp_place = self._field(frm, "Inspection Place", 0, col=2)
        self.cont_person = self._field(frm, "Contact Person", 1, col=2)
        self.on_behalf = self._field(frm, "On Behalf Of", 3, col=2)
        self.consignee = self._field(frm, "Consig./Notify", 4, col=2)

        self.vessel = self._field(frm, "Vessel", 0, col=4)
        self.contact_dt = self._datetime_picker(
            frm, "Contact D/Time", 1, col=4
        )

        self.init_insp_dt = self._datetime_picker(
            frm, "Init Insp. D/Time", 2, col=2
        )

        self.init_to = self._datetime_picker(
            frm, "To", 2, col=4
        )

        self.final_insp_dt = self._datetime_picker(
            frm, "Final Insp. D/Time", 3, col=4
        )

        self.final_to = self._datetime_picker(
            frm, "To", 3, col=6
        )

    def _section_container_description(self):

        frm = ttk.LabelFrame(self.form, text="Container Description")
        frm.pack(fill="x", pady=10)

        self.container_size = self._checks(
            frm,
            ["20 Foot", "40 Foot"],
            0
        )

        self.container_type = self._checks(
            frm,
            ["Dry", "Reefer", "ISO Tank", "Flat Rack"],
            1
        )

        self.container_load = self._checks(
            frm,
            ["FCL", "LCL"],
            2
        )

    def _section_cause_of_inspection(self):

        frm = ttk.LabelFrame(self.form, text="Cause of Inspection")
        frm.pack(fill="x", pady=10)

        self.cause = self._checks(
            frm,
            [
                "Seals ≠ BL",
                "Change Seals",
                "Customs",
                "Transfer",
                "Leaking",
                "Damage",
                "Stuff / D Condition"
            ],
            0,
            columns=4
        )

        ttk.Label(frm, text="Detail of Cause (if necessary)").pack(anchor="w")
        self.cause_detail = tk.Text(frm, height=3, wrap="word")
        self.cause_detail.pack(fill="x", pady=5)

    def _section_goods_and_packages(self):

        frm = ttk.LabelFrame(self.form, text="Goods & Packages")
        frm.pack(fill="x", pady=10)

        # ------------------------------
        # GOODS
        # ------------------------------
        goods_frm = ttk.LabelFrame(frm, text="Goods")
        goods_frm.pack(fill="x", pady=5)

        self.goods = tk.Text(goods_frm, height=3, wrap="word")
        self.goods.pack(fill="x", padx=5, pady=5)

        # ------------------------------
        # TYPE OF PACKAGE
        # ------------------------------
        type_frm = ttk.LabelFrame(frm, text="Type of Package")
        type_frm.pack(fill="x", pady=5)

        self.package_type = self._checks(
            type_frm,
            [
                "Carton", "Bags", "Boxes", "Drums",
                "Pallets", "Bulk", "Bales", "Crates", "Other"
            ],
            0,
            columns=4
        )

        # ------------------------------
        # QTY OF PACKAGES
        # ------------------------------
        qty = ttk.LabelFrame(frm, text="Qty Of Packages")
        qty.pack(fill="x", pady=8)

        self.qty_1 = self._qty_field(qty, "1st")
        self.qty_2 = self._qty_field(qty, "2nd")
        self.qty_3 = self._qty_field(qty, "3rd")

        ttk.Label(frm, text="Package & Marking Description").pack(anchor="w")
        self.pkg_marking = tk.Text(frm, height=3, wrap="word")
        self.pkg_marking.pack(fill="x", pady=5)

        ttk.Label(frm, text="Goods Condition (According Inspector Observations)").pack(anchor="w")
        self.goods_condition = tk.Text(frm, height=3, wrap="word")
        self.goods_condition.pack(fill="x", pady=5)


    def _section_conditions_and_narratives(self):

        self.damage_details = self._big_text("Details of Damage / Shortage")
        self.remarks = self._big_text("Remarks")
        self.conclusion = self._big_text("Conclusion")

        frm = ttk.LabelFrame(self.form, text="Picture Link")
        frm.pack(fill="x", pady=10)
        self.link_picture = ttk.Entry(frm, width=90)
        self.link_picture.pack(fill="x", padx=5, pady=5)

    def _section_collected_documents(self):

        frm = ttk.LabelFrame(self.form, text="Collected Documents")
        frm.pack(fill="x", pady=10)

        self.collected_docs = self._checks(
            frm,
            [
                "B/L", "Packing List", "Shipping Invoice",
                "Cargo Manifest", "Commercial Invoice",
                "Delivery / Received Record",
                "Notice of Loss / Damage",
                "Insurance Policy", "Other"
            ],
            0,
            columns=2
        )


    def _section_quality(self):

        frm = ttk.LabelFrame(self.form, text="Quality")
        frm.pack(fill="x", pady=10)

        self.quality = self._checks(
            frm,
            [
                "Packing Examination", "UN / Stuffed Witness",
                "Visual Examination", "Product Examination",
                "Quality Documents", "Sanitary Certificate",
                "Phytosanitary Cert.", "Factory Certificate",
                "Certificate of Origin"
            ],
            0,
            columns=2
        )



    def _section_persons_and_signature(self):

        frm = ttk.LabelFrame(self.form, text="Persons Present at Survey")
        frm.pack(fill="x", pady=10)

        def person_row(parent):
            row = ttk.Frame(parent)
            row.pack(fill="x", pady=3)

            ttk.Label(row, text="Name").grid(row=0, column=0, sticky="w")
            name = ttk.Entry(row, width=30)
            name.grid(row=0, column=1, padx=5)

            ttk.Label(row, text="Position").grid(row=0, column=2, sticky="w")
            position = ttk.Entry(row, width=30)
            position.grid(row=0, column=3, padx=5)

            return name, position

        self.person_1_name, self.person_1_position = person_row(frm)
        self.person_2_name, self.person_2_position = person_row(frm)
        self.person_3_name, self.person_3_position = person_row(frm)

        sig = ttk.LabelFrame(self.form, text="Surveyor")
        sig.pack(fill="x", pady=10)

        ttk.Label(
            sig,
            text="PABEL PEÑA\nMSL Surveyor Signature",
            font=("Segoe UI", 10, "bold")
        ).pack()

    # =========================================================
    # ACTIONS
    # =========================================================
    def _section_actions(self):

        frm = ttk.Frame(self.form)
        frm.pack(fill="x", pady=15)

        ttk.Button(
            frm,
            text="✨ Mejorar con PORTIA",
            command=self._ask_ai_target
        ).pack(side="left", padx=5)

        ttk.Button(
            frm,
            text="📤 Submit for Review",
            command=self._submit
        ).pack(side="right", padx=5)

    # =========================================================
    # HELPERS
    # =========================================================
    def _field(self, parent, label, row, col=0):
        ttk.Label(parent, text=label).grid(row=row, column=col, sticky="w")
        entry = ttk.Entry(parent, width=25)
        entry.grid(row=row, column=col + 1, sticky="w", padx=5, pady=2)
        return entry

    def _simple_field(self, parent, label):
        f = ttk.Frame(parent)
        f.pack(fill="x", pady=2)
        ttk.Label(f, text=label).pack(side="left")
        e = ttk.Entry(f, width=30)
        e.pack(side="left", padx=5)
        return e

    def _qty_field(self, parent, label):

        f = ttk.Frame(parent)
        f.pack(fill="x", pady=2)

        ttk.Label(f, text=label, width=6).pack(side="left")

        e_left = ttk.Entry(f, width=20)
        e_left.pack(side="left", padx=5)

        e_right = ttk.Entry(f, width=10)
        e_right.pack(side="left", padx=5)

        return (e_left, e_right)


    def _checks(self, parent, options, row, columns=2):
        vars_ = {}
        frame = ttk.Frame(parent)
        frame.pack(fill="x", pady=5)
        for i, opt in enumerate(options):
            var = tk.BooleanVar()
            ttk.Checkbutton(frame, text=opt, variable=var).grid(
                row=i // columns,
                column=i % columns,
                sticky="w",
                padx=5
            )
            vars_[opt] = var
        return vars_

    def _big_text(self, title):
        frm = ttk.LabelFrame(self.form, text=title)
        frm.pack(fill="both", expand=True, pady=10)
        txt = tk.Text(frm, height=6, wrap="word")
        txt.pack(fill="both", expand=True, padx=5, pady=5)
        return txt

    # =========================================================
    # LOGIC
    # =========================================================
    def _improve_with_ai(self, text_widget):

        original_text = text_widget.get("1.0", "end").strip()

        if not original_text:
            messagebox.showwarning("Warning", "No text to improve")
            return

        payload = {
            "text": original_text,
            "container_no": self.no.get(),
            "cargo": self.goods.get("1.0", "end").strip(),
            "location": self.insp_place.get(),
            "condition": "As observed during inspection"
        }

        try:
            resp = api_request(
                "POST",
                "/reports/ai/improve/container",
                json=payload
            ).json()

            ai_text = resp.get("text", "")

            PopupAICompare(
                self,
                original_text=original_text,
                ai_text=ai_text,
                on_accept=lambda t: self._apply_ai_text(text_widget, t),
                on_retry=lambda: self._improve_with_ai(text_widget)
            )

        except Exception as e:
            messagebox.showerror("PORTIA Error", str(e))

    def _apply_ai_text(self, widget, text):
        widget.delete("1.0", "end")
        widget.insert("1.0", text)

    def _submit(self):
        try:
            payload = self._build_payload()

            # ==================================================
            # STATUS AUTOMÁTICO AL ENVIAR
            # ==================================================
            payload["status"] = "Pending for review"

            resp = create_container_report_api(payload)

            if resp.get("success"):
                messagebox.showinfo(
                    "Submitted",
                    f"Report submitted successfully.\nID: {resp.get('id')}"
                )

                if self.on_back:
                    self.on_back()
            else:
                messagebox.showerror(
                    "Error",
                    resp.get("detail", "Unknown error")
                )

        except Exception as e:
            messagebox.showerror("Submit Error", str(e))


    def _ask_ai_target(self):

        options = {
            "Detail of Cause": self.cause_detail,
            "Goods & Packages": self.goods,
            "Package & Marking Description": self.pkg_marking,
            "Goods Condition": self.goods_condition,
            "Details of Damage / Shortage": self.damage_details,
            "Remarks": self.remarks,
            "Conclusion": self.conclusion
        }

        win = tk.Toplevel(self)
        win.title("Select section to improve")
        win.geometry("420x330")
        win.transient(self)
        win.grab_set()

        ttk.Label(
            win,
            text="Which section do you want to improve?",
            font=("Segoe UI", 11, "bold")
        ).pack(pady=10)

        selected = tk.StringVar(value="Conclusion")

        for label in options.keys():
            ttk.Radiobutton(
                win,
                text=label,
                variable=selected,
                value=label
            ).pack(anchor="w", padx=20)

        def proceed():
            widget = options[selected.get()]
            if not widget.get("1.0", "end").strip():
                messagebox.showwarning(
                    "Warning",
                    "The selected section has no text to improve."
                )
                return

            win.destroy()
            self._improve_with_ai(widget)

        ttk.Button(win, text="Continue", command=proceed).pack(pady=15)




    def _build_payload(self):
        return {
            # ==============================
            # LINKED REPORT (FROM SERVICES)
            # ==============================
            "linked_report_number": self.selected_report_var.get(),
            "container_type_text": self.container_type_entry.get().strip(),

            # ==============================
            # GENERAL INFORMATION
            # ==============================
            "report_no": self.no.get(),
            "bl": self.bl.get(),
            "seals": self.seals.get(),
            "appointment": self.appointment.get(),
            "shippers": self.shippers.get(),
            "inspection_place": self.insp_place.get(),
            "contact_person": self.cont_person.get(),
            "on_behalf_of": self.on_behalf.get(),
            "consignee_notify": self.consignee.get(),
            "vessel": self.vessel.get(),
            "contact_datetime": self.contact_dt["get"](),
            "init_inspection_datetime": self.init_insp_dt["get"](),
            "init_to": self.init_to["get"](),
            "final_inspection_datetime": self.final_insp_dt["get"](),
            "final_to": self.final_to["get"](),

            # ==============================
            # CONTAINER DESCRIPTION
            # ==============================
            "container_size_20": self.container_size.get("20 Foot").get(),
            "container_size_40": self.container_size.get("40 Foot").get(),

            "container_type_dry": self.container_type.get("Dry").get(),
            "container_type_reefer": self.container_type.get("Reefer").get(),
            "container_type_iso": self.container_type.get("ISO Tank").get(),
            "container_type_flat_rack": self.container_type.get("Flat Rack").get(),

            "container_load_fcl": self.container_load.get("FCL").get(),
            "container_load_lcl": self.container_load.get("LCL").get(),

            # ==============================
            # CAUSE OF INSPECTION
            # ==============================
            "cause_seals_bl": self.cause.get("Seals ≠ BL").get(),
            "cause_change_seals": self.cause.get("Change Seals").get(),
            "cause_customs": self.cause.get("Customs").get(),
            "cause_transfer": self.cause.get("Transfer").get(),
            "cause_leaking": self.cause.get("Leaking").get(),
            "cause_damage": self.cause.get("Damage").get(),
            "cause_stuff_condition": self.cause.get("Stuff / D Condition").get(),
            "cause_detail": self.cause_detail.get("1.0", "end").strip(),

            # ==============================
            # GOODS & PACKAGES
            # ==============================
            "goods_description": self.goods.get("1.0", "end").strip(),

            "package_carton": self.package_type.get("Carton").get(),
            "package_bags": self.package_type.get("Bags").get(),
            "package_boxes": self.package_type.get("Boxes").get(),
            "package_drums": self.package_type.get("Drums").get(),
            "package_pallets": self.package_type.get("Pallets").get(),
            "package_bulk": self.package_type.get("Bulk").get(),
            "package_bales": self.package_type.get("Bales").get(),
            "package_crates": self.package_type.get("Crates").get(),
            "package_other": self.package_type.get("Other").get(),

            "qty_1_left": self.qty_1[0].get(),
            "qty_1_right": self.qty_1[1].get(),
            "qty_2_left": self.qty_2[0].get(),
            "qty_2_right": self.qty_2[1].get(),
            "qty_3_left": self.qty_3[0].get(),
            "qty_3_right": self.qty_3[1].get(),

            "package_marking": self.pkg_marking.get("1.0", "end").strip(),
            "goods_condition": self.goods_condition.get("1.0", "end").strip(),

            # ==============================
            # NARRATIVES
            # ==============================
            "damage_details": self.damage_details.get("1.0", "end").strip(),
            "remarks": self.remarks.get("1.0", "end").strip(),
            "conclusion": self.conclusion.get("1.0", "end").strip(),

            # ==============================
            # LINKS & DOCS
            # ==============================
            "picture_link": self.link_picture.get(),

            "doc_bl": self.collected_docs.get("B/L").get(),
            "doc_packing_list": self.collected_docs.get("Packing List").get(),
            "doc_shipping_invoice": self.collected_docs.get("Shipping Invoice").get(),
            "doc_cargo_manifest": self.collected_docs.get("Cargo Manifest").get(),
            "doc_commercial_invoice": self.collected_docs.get("Commercial Invoice").get(),
            "doc_delivery_record": self.collected_docs.get("Delivery / Received Record").get(),
            "doc_notice_loss": self.collected_docs.get("Notice of Loss / Damage").get(),
            "doc_insurance_policy": self.collected_docs.get("Insurance Policy").get(),
            "doc_other": self.collected_docs.get("Other").get(),

            # ==============================
            # QUALITY
            # ==============================
            "quality_packing_exam": self.quality.get("Packing Examination").get(),
            "quality_un_witness": self.quality.get("UN / Stuffed Witness").get(),
            "quality_visual_exam": self.quality.get("Visual Examination").get(),
            "quality_product_exam": self.quality.get("Product Examination").get(),
            "quality_documents": self.quality.get("Quality Documents").get(),
            "quality_sanitary_cert": self.quality.get("Sanitary Certificate").get(),
            "quality_phytosanitary_cert": self.quality.get("Phytosanitary Cert.").get(),
            "quality_factory_cert": self.quality.get("Factory Certificate").get(),
            "quality_origin_cert": self.quality.get("Certificate of Origin").get(),

            # ==============================
            # PERSONS
            # ==============================
            "person_1_name": self.person_1_name.get(),
            "person_1_position": self.person_1_position.get(),
            "person_2_name": self.person_2_name.get(),
            "person_2_position": self.person_2_position.get(),
            "person_3_name": self.person_3_name.get(),
            "person_3_position": self.person_3_position.get(),

            # ==============================
            # INSPECTED CONTAINER
            # ==============================
            "ic_manuf": self.ic_manuf.get(),
            "ic_csc": self.ic_csc.get(),
            "ic_max_gw": self.ic_max_gw.get(),
            "ic_tare": self.ic_tare.get(),

            # ==============================
            # GENERAL DETAILS
            # ==============================
            "new_commodity": self.new_commodity.get(),
            "used_commodity": self.used_commodity.get(),
            "net_weight": self.net_w.get(),
            "gross_weight": self.gross_w.get(),
            "volume": self.volume.get(),

            # ==============================
            # TRANSFER TO CONTAINER
            # ==============================
            "tr_number": self.tr_number.get(),
            "tr_manuf": self.tr_manuf.get(),
            "tr_csc": self.tr_csc.get(),
            "tr_seal": self.tr_seal.get(),
            "tr_max_gw": self.tr_max_gw.get(),
            "tr_tare": self.tr_tare.get(),

            # ==============================
            # SCOPE OF INSPECTION
            # ==============================
            "scope_100": self.scope_100.get(),
            "scope_random": self.scope_random.get(),
            "scope_items": self.scope_items.get(),
        }


    # =========================================================
    # REPORT SELECTOR (ANTES DE GENERAL INFORMATION)
    # =========================================================
    def _section_report_selector(self):

        frm = ttk.LabelFrame(self.form, text="Report Link")
        frm.pack(fill="x", pady=10)

        ttk.Label(frm, text="Report Number").grid(
            row=0, column=0, sticky="w", padx=5, pady=5
        )

        ttk.Entry(
            frm,
            textvariable=self.selected_report_var,
            width=30,
            state="readonly"
        ).grid(row=0, column=1, padx=5, pady=5)

        ttk.Button(
            frm,
            text="Select…",
            command=self._open_report_selector_popup
        ).grid(row=0, column=2, padx=5, pady=5)

        ttk.Label(frm, text="Container Type").grid(
            row=1, column=0, sticky="w", padx=5
        )

        self.container_type_entry = ttk.Entry(
            frm,
            textvariable=self.container_type_text,
            width=30
        )
        self.container_type_entry.grid(row=1, column=1, padx=5)

    def _on_report_selected(self, value):
        """
        Recibe el num_informe seleccionado desde el popup
        """
        self.selected_report_var.set(value)

    def _open_report_selector_popup(self):
        PopupContainerReportSelector(
            self,
            on_select=self._on_report_selected
        )


    def _section_inspected_container(self):

        frm = ttk.LabelFrame(self.form, text="Inspected Container")
        frm.pack(fill="x", pady=10)

        self.ic_manuf = self._simple_field(frm, "Manuf. Nº")
        self.ic_csc = self._simple_field(frm, "CSC Saf. Apr.")
        self.ic_max_gw = self._simple_field(frm, "Max. Gross Weight (Kgs)")
        self.ic_tare = self._simple_field(frm, "Tare (Kgs)")


    def _section_general_details(self):

        frm = ttk.LabelFrame(self.form, text="General Details")
        frm.pack(fill="x", pady=10)

        self.new_commodity = tk.BooleanVar()
        self.used_commodity = tk.BooleanVar()

        ttk.Checkbutton(frm, text="New Commodity", variable=self.new_commodity).pack(anchor="w")
        ttk.Checkbutton(frm, text="Used Commodity", variable=self.used_commodity).pack(anchor="w")

        self.net_w = self._simple_field(frm, "Net W. (Kgs)")
        self.gross_w = self._simple_field(frm, "Gross W. (Kgs)")
        self.volume = self._simple_field(frm, "Volume (m³)")



    def _section_transfer_to_container(self):

        frm = ttk.LabelFrame(self.form, text="Transfer To Container")
        frm.pack(fill="x", pady=10)

        self.tr_number = self._simple_field(frm, "Number")
        self.tr_manuf = self._simple_field(frm, "Manuf. Nº")
        self.tr_csc = self._simple_field(frm, "CSC Saf. Apr.")
        self.tr_seal = self._simple_field(frm, "Seal Nº")
        self.tr_max_gw = self._simple_field(frm, "Max. Gross Weight (Kgs)")
        self.tr_tare = self._simple_field(frm, "Tare (Kgs)")


    def _section_scope_of_inspection(self):

        frm = ttk.LabelFrame(self.form, text="Scope of Inspection")
        frm.pack(fill="x", pady=10)

        self.scope_100 = tk.BooleanVar()
        self.scope_random = tk.BooleanVar()

        ttk.Checkbutton(frm, text="100%", variable=self.scope_100).pack(anchor="w")
        ttk.Checkbutton(frm, text="Random", variable=self.scope_random).pack(anchor="w")

        self.scope_items = self._simple_field(frm, "Nº Items")


    def _datetime_picker(self, parent, label, row, col=0):
        """
        UI: Date picker + Hour/Minute selector (24h)
        Backend: YYYY-MM-DD HH:MM
        """

        ttk.Label(parent, text=label).grid(
            row=row, column=col, sticky="w", padx=5, pady=2
        )

        frame = ttk.Frame(parent)
        frame.grid(row=row, column=col + 1, sticky="w", padx=5, pady=2)

        # ----------------------------
        # DATE
        # ----------------------------
        date_var = tk.StringVar()

        date_entry = DateEntry(
            frame,
            textvariable=date_var,
            date_pattern="dd-mm-yyyy",
            width=12
        )
        date_entry.pack(side="left")

        # ----------------------------
        # TIME (24H)
        # ----------------------------
        hour_var = tk.StringVar(value="00")
        minute_var = tk.StringVar(value="00")

        hour_spin = ttk.Spinbox(
            frame,
            from_=0,
            to=23,
            wrap=True,
            width=3,
            textvariable=hour_var,
            format="%02.0f"
        )
        hour_spin.pack(side="left", padx=(8, 2))

        ttk.Label(frame, text=":").pack(side="left")

        minute_spin = ttk.Spinbox(
            frame,
            from_=0,
            to=59,
            wrap=True,
            width=3,
            textvariable=minute_var,
            format="%02.0f"
        )
        minute_spin.pack(side="left", padx=(2, 0))

        # ----------------------------
        # BACKEND VALUE
        # ----------------------------
        def get_backend_value():
            if not date_var.get():
                return None

            try:
                dt = datetime.strptime(
                    f"{date_var.get()} {hour_var.get()}:{minute_var.get()}",
                    "%d-%m-%Y %H:%M"
                )
                return dt.strftime("%Y-%m-%d %H:%M")
            except ValueError:
                messagebox.showerror(
                    "Invalid Date / Time",
                    "Please select a valid date and time (24h format)."
                )
                return None

        return {
            "date": date_var,
            "hour": hour_var,
            "minute": minute_var,
            "get": get_backend_value
        }


    # =========================================================
    # MOUSE SCROLL — ROBUSTO (NO ROMPE OTROS MODULOS)
    # =========================================================
    def _bind_mousewheel(self, canvas):

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _on_mousewheel_linux_up(event):
            canvas.yview_scroll(-1, "units")

        def _on_mousewheel_linux_down(event):
            canvas.yview_scroll(1, "units")

        # 🔥 SOLO ACTIVO CUANDO EL MOUSE ESTÁ DENTRO DEL FORM
        def _bind(_):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
            canvas.bind_all("<Button-4>", _on_mousewheel_linux_up)
            canvas.bind_all("<Button-5>", _on_mousewheel_linux_down)

        def _unbind(_):
            canvas.unbind_all("<MouseWheel>")
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")

        self.form.bind("<Enter>", _bind)
        self.form.bind("<Leave>", _unbind)
