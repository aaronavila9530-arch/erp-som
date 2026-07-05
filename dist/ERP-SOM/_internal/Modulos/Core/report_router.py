from tkinter import messagebox
import tkinter as tk
import api_client


class ReportRouter:

    # =========================================================
    # HOST CLEANER + ROUTER BAR
    # =========================================================
    @staticmethod
    def _prepare_host(parent, title="Informe SOM"):

        root = parent.winfo_toplevel()
        win = tk.Toplevel(root)
        win.title(title)
        win.geometry("1280x760")
        win.minsize(980, 620)

        try:
            win.transient(root)
        except Exception:
            pass

        try:
            win.state("zoomed")
        except Exception:
            pass

        container = tk.Frame(win, bg="white")
        container.pack(fill="both", expand=True)

        topbar = tk.Frame(container, bg="#f4f4f4")
        topbar.pack(side="top", fill="x")

        tk.Button(
            topbar,
            text="Cerrar",
            font=("Segoe UI", 9, "bold"),
            command=win.destroy
        ).pack(side="right", padx=10, pady=6)

        host = tk.Frame(container, bg="white")
        host.pack(side="top", fill="both", expand=True)

        try:
            host.grid_rowconfigure(0, weight=1)
            host.grid_columnconfigure(0, weight=1)
        except Exception:
            pass

        return host

        try:
            for child in parent.winfo_children():
                child.destroy()
        except Exception:
            pass

        container = tk.Frame(parent, bg="white")
        container.pack(fill="both", expand=True)

        # ---------------- TOP BAR ----------------
        topbar = tk.Frame(container, bg="#f4f4f4")
        topbar.pack(side="top", fill="x")

        topbar_inner = tk.Frame(topbar, bg="#f4f4f4")
        topbar_inner.pack(fill="x")

        btn_back = tk.Button(
            topbar_inner,
            text="← Volver a Servicios",
            font=("Segoe UI", 9, "bold"),
            command=lambda: ReportRouter._go_back_to_services(parent)
        )

        btn_back.pack(side="left", padx=10, pady=6)

        # ---------------- HOST FOR FORM ----------------
        host = tk.Frame(container, bg="white")
        host.pack(side="top", fill="both", expand=True)

        try:
            host.grid_rowconfigure(0, weight=1)
            host.grid_columnconfigure(0, weight=1)
        except Exception:
            pass

        return host

    # =========================================================
    # SAFE LIST EXTRACTOR
    # =========================================================
    @staticmethod
    def _extract_list(data):

        if isinstance(data, list):
            return data

        if isinstance(data, dict):
            rows = data.get("data")
            if isinstance(rows, list):
                return rows

        return []

    # =========================================================
    # SAFE RECORD FINDER
    # =========================================================
    @staticmethod
    def _find_record(records, field, value):

        target = str(value or "").strip()

        for r in (records or []):
            try:
                if str(r.get(field) or "").strip() == target:
                    return r
            except Exception:
                continue

        return None

    # =========================================================
    # SAFE RESPONSE -> PAYLOAD
    # =========================================================
    @staticmethod
    def _extract_payload(resp):

        if not resp:
            return None

        if isinstance(resp, dict):
            if isinstance(resp.get("data"), dict):
                return resp.get("data")
            return resp

        return None

    # =========================================================
    # SAFE SUCCESS CHECK
    # =========================================================
    @staticmethod
    def _is_success_response(resp):

        if resp is None:
            return False

        if isinstance(resp, dict):
            if "success" in resp:
                return bool(resp.get("success"))
            return True

        return False

    # =========================================================
    # GRAIN MANUAL LOADER
    # El form subido no expone load_record/set_payload.
    # =========================================================
    @staticmethod
    def _load_grain_payload_into_form(form, payload):

        payload = payload or {}

        try:
            form.cert_no.delete(0, "end")
            form.cert_no.insert(0, str(payload.get("cert_no") or ""))
        except Exception:
            pass

        try:
            form.port_entry.config(state="normal")
            form.port_entry.delete(0, "end")
            form.port_entry.insert(0, str(payload.get("place") or payload.get("port") or ""))
            form.port_entry.config(state="readonly")
        except Exception:
            pass

        try:
            form.vessel_entry.config(state="normal")
            form.vessel_entry.delete(0, "end")
            form.vessel_entry.insert(0, str(payload.get("vessel_name") or ""))
            form.vessel_entry.config(state="readonly")
        except Exception:
            pass

        try:
            form.client_entry.config(state="normal")
            form.client_entry.delete(0, "end")
            form.client_entry.insert(0, str(payload.get("requested_by") or ""))
            form.client_entry.config(state="readonly")
        except Exception:
            pass

        try:
            form.captain.delete(0, "end")
            form.captain.insert(0, str(payload.get("captain") or ""))
        except Exception:
            pass

        try:
            form.chief_officer.delete(0, "end")
            form.chief_officer.insert(0, str(payload.get("chief_officer") or ""))
        except Exception:
            pass

        try:
            form.ship_flag.delete(0, "end")
            form.ship_flag.insert(0, str(payload.get("ship_flag") or ""))
        except Exception:
            pass

        try:
            form.ship_grt.delete(0, "end")
            form.ship_grt.insert(0, str(payload.get("ship_grt") or ""))
        except Exception:
            pass

        try:
            form.ship_nrt.delete(0, "end")
            form.ship_nrt.insert(0, str(payload.get("ship_nrt") or ""))
        except Exception:
            pass

        try:
            form.ship_imo.delete(0, "end")
            form.ship_imo.insert(0, str(payload.get("ship_imo") or ""))
        except Exception:
            pass

        # tiempos
        try:
            for key, widget in getattr(form, "times", {}).items():
                value = payload.get(key)
                if value is None:
                    continue
                try:
                    widget.delete(0, "end")
                    widget.insert(0, str(value))
                except Exception:
                    pass
        except Exception:
            pass

        # tonnage / holds
        try:
            form.tonnage.delete(0, "end")
            form.tonnage.insert(0, str(payload.get("products_total") or ""))
        except Exception:
            pass

        try:
            form.holds.delete(0, "end")
            form.holds.insert(0, str(payload.get("holds") or ""))
        except Exception:
            pass

        # productos dinámicos 1..5
        try:
            for idx, row in enumerate(getattr(form, "hold_rows", []), start=1):
                hold_key = f"product_hold_{idx}"
                ton_key = f"product_tonnage_{idx}"

                if "hold" in row:
                    row["hold"].delete(0, "end")
                    row["hold"].insert(0, str(payload.get(hold_key) or ""))

                if "tonnage" in row:
                    row["tonnage"].delete(0, "end")
                    row["tonnage"].insert(0, str(payload.get(ton_key) or ""))
        except Exception:
            pass

        # conclusion
        try:
            form.conclusion.delete("1.0", "end")
            form.conclusion.insert("1.0", str(payload.get("conclusion") or ""))
        except Exception:
            pass

    # =========================================================
    # MAIN ROUTER
    # =========================================================
    @staticmethod
    def open_report(parent, num_informe, operacion, estado):

        if str(estado or "").strip().lower() != "finalizado":
            messagebox.showwarning(
                "Informe",
                "El informe no está finalizado"
            )
            return

        num_informe = str(num_informe or "").strip()
        operacion = str(operacion or "").strip().upper()
        operacion = operacion.replace("SUPERVISON", "SUPERVISION")

        if not num_informe:
            messagebox.showwarning(
                "Informe",
                "El registro no tiene número de informe."
            )
            return

        try:

            # =====================================================
            # LOGISTICS SUPERVISION
            # servicios.num_informe -> vessel_truck_supervision_reports.cert_no
            # luego GET BY ID
            # =====================================================
            if operacion in [
                "LOGISTICS SUPERVISION",
                "TRUCK SUPERVISION",
                "TRUCKS SUPERVISION",
                "SUPERVISION DE CAMIONES",
                "SUPERVISION CAMIONES"
            ]:

                data = api_client.get_vessel_truck_supervision_list_api()
                records = ReportRouter._extract_list(data)

                record = ReportRouter._find_record(records, "cert_no", num_informe)

                if not record:
                    messagebox.showwarning("Informe", f"No se encontró:\n{num_informe}")
                    return

                report_id = record.get("id")

                if not report_id:
                    messagebox.showwarning("Informe", f"Se encontró el número, pero no el ID:\n{num_informe}")
                    return

                from Modulos.Informes.vessel_truck_supervision.vessel_truck_supervision_form import (
                    VesselTruckSupervisionForm
                )

                host = ReportRouter._prepare_host(parent, f"Truck Supervision - {num_informe}")
                form = VesselTruckSupervisionForm(host, mode="review")

                # Igual que tu REVIEW real de tabla
                form.load_report(int(report_id))
                return

            # =====================================================
            # DRAFT SURVEY
            # servicios.num_informe -> draft_report_number / survey_no
            # tu form ya autoload con mode=edit + draft_report_number
            # =====================================================
            if operacion in [
                "DRAFT SURVEY",
                "DRAFT SURVEY (INITIAL & FINAL)",
                "DRAFT SURVEY INITIAL AND FINAL",
                "DRAFT SURVEY INITIAL & FINAL",
                "INTERMEDIATE DRAFT SURVEY",
                "DRAFT SURVEY INTERMEDIATE"
            ]:

                resp = api_client.get_full_draft_survey_api(num_informe)

                if not resp:
                    messagebox.showwarning("Informe", f"No se encontró:\n{num_informe}")
                    return

                if isinstance(resp, dict) and resp.get("success") is False:
                    messagebox.showwarning(
                        "Informe",
                        resp.get("message") or f"No se encontró:\n{num_informe}"
                    )
                    return

                from Modulos.Informes.Vessel_Draft_Survey.draft_survey_form import (
                    DraftSurveyForm
                )

                host = ReportRouter._prepare_host(parent, f"Draft Survey - {num_informe}")

                DraftSurveyForm(
                    host,
                    mode="edit",
                    draft_report_number=num_informe
                )
                return

            # =====================================================
            # GRAIN SAMPLING
            # servicios.num_informe -> vessel_grain_sampling_reports.cert_no
            # luego GET BY ID
            # =====================================================
            if operacion in [
                "SUPERVISION MUESTREO DE GRANOS",
                "SAMPLING SUPERVISION",
                "TOMA DE MUESTRAS MAG"
            ]:

                data = api_client.get_vessel_grain_sampling_list_api()
                records = ReportRouter._extract_list(data)

                record = ReportRouter._find_record(records, "cert_no", num_informe)

                if not record:
                    messagebox.showwarning("Informe", f"No se encontró:\n{num_informe}")
                    return

                report_id = record.get("id")

                if not report_id:
                    messagebox.showwarning("Informe", f"Se encontró el número, pero no el ID:\n{num_informe}")
                    return

                resp = api_client.get_vessel_grain_sampling_by_id_api(int(report_id))
                payload = ReportRouter._extract_payload(resp)

                if not payload:
                    messagebox.showwarning("Informe", f"No se pudo cargar el informe:\n{num_informe}")
                    return

                from Modulos.Informes.vessel.vessel_grain_sampling_form import (
                    GrainSamplingVesselForm
                )

                host = ReportRouter._prepare_host(parent, f"Grain Sampling - {num_informe}")
                form = GrainSamplingVesselForm(host)

                ReportRouter._load_grain_payload_into_form(form, payload)
                return

            # =====================================================
            # CARGO CONDITION
            # servicios.num_informe -> vessel_cargo_condition_surveys.report_number
            # luego GET BY ID
            # =====================================================
            if operacion in [
                "CARGO CONDITION",
                "CARGO DISCHARGE SUPERVISION",
                "CARGO LOADING SUPERVISION"
            ]:

                data = api_client.get_all_vessel_cargo_condition_api()
                records = ReportRouter._extract_list(data)

                record = ReportRouter._find_record(records, "report_number", num_informe)

                if not record:
                    messagebox.showwarning("Informe", f"No se encontró:\n{num_informe}")
                    return

                report_id = record.get("id")

                if not report_id:
                    messagebox.showwarning("Informe", f"Se encontró el número, pero no el ID:\n{num_informe}")
                    return

                resp = api_client.get_vessel_cargo_condition_by_id_api(int(report_id))
                payload = ReportRouter._extract_payload(resp)

                if not payload:
                    messagebox.showwarning("Informe", f"No se pudo cargar el informe:\n{num_informe}")
                    return

                from Modulos.Informes.vessel_cargo_condition_survey.vessel_cargo_condition_survey_form import (
                    VesselCargoConditionSurveyForm
                )

                host = ReportRouter._prepare_host(parent, f"Cargo Condition - {num_informe}")
                form = VesselCargoConditionSurveyForm(host)

                # Igual que review real del form
                form.load_record(payload)
                return

            # =====================================================
            # BUNKER SURVEY
            # servicios.num_informe -> vessel_bunker_reports.bunker_cert_no
            # luego GET BY ID
            # =====================================================
            if operacion in [
                "BUNKER SURVEY",
                "BQS BUNKER QUANTITY SURVEY",
                "SPOT BUNKER SURVEY",
                "ON HIRE BUNKER SURVEY 3 PTY",
                "ON HIRE BUNKER SURVEY 2 PTY",
                "ON HIRE BUNKER 2 PARTIES",
                "ON HIRE BUNKER 3 PARTIES",
                "ON HIRE BUNKER & CONDITION SURVEY 2 PARTY",
                "ON HIRE BUNKER & CONDITION SURVEY 3 PARTY",
                "ON HIRE BUNKER AND CONDITION SURVEY 2 PARTY",
                "ON HIRE BUNKER AND CONDITION SURVEY 3 PARTY",
                "ON HIRE BUNKER AND CONDITION 2 PARTIES",
                "ON HIRE BUNKER AND CONDITION 3 PARTIES",
                "OFF HIRE BUNKER SURVEY 2 PARTY",
                "OFF HIRE BUNKER SURVEY 3 PARTY",
                "OFF HIRE BUNKER 2 PARTIES",
                "OFF HIRE BUNKER 3 PARTIES",
                "OFF HIRE BUNKER & COND SURVEY 3 PARTY",
                "OFF HIRE BUNKER & COND SURVEY 2 PARTY",
                "OFF HIRE BUNKER & CONDITION SURVEY 2 PARTY",
                "OFF HIRE BUNKER & CONDITION SURVEY 3 PARTY",
                "OFF HIRE BUNKER AND CONDITION SURVEY 2 PARTY",
                "OFF HIRE BUNKER AND CONDITION SURVEY 3 PARTY",
                "OFF HIRE BUNKER AND CONDITION 2 PARTIES",
                "OFF HIRE BUNKER AND CONDITION 3 PARTIES"
            ]:

                data = api_client.get_all_vessel_bunker_reports_api(limit=500)
                records = ReportRouter._extract_list(data)

                record = ReportRouter._find_record(records, "bunker_cert_no", num_informe)

                if not record:
                    messagebox.showwarning("Informe", f"No se encontró:\n{num_informe}")
                    return

                report_id = record.get("id")

                if not report_id:
                    messagebox.showwarning("Informe", f"Se encontró el número, pero no el ID:\n{num_informe}")
                    return

                resp = api_client.get_vessel_bunker_report_api(int(report_id))

                if not isinstance(resp, dict) or not resp.get("success"):
                    raise Exception(
                        (resp or {}).get("detail")
                        or (resp or {}).get("error")
                        or "Error loading report"
                    )

                payload = resp.get("data") or {}

                from Modulos.Informes.vessel_bunker.vessel_bunker_form import (
                    VesselBunkerReportForm
                )

                host = ReportRouter._prepare_host(parent, f"Bunker Survey - {num_informe}")
                form = VesselBunkerReportForm(host)

                # Igual que REVIEW real de tabla
                form.report_id = int(payload.get("id") or report_id)
                form.set_payload(payload, from_review=True)
                return

            # =====================================================
            # CRANE INSPECTION
            # servicios.num_informe -> vessel_crane_inspection_reports.report_number
            # luego GET BY ID
            # =====================================================
            if operacion in [
                "CRANE INSPECTION",
                "CRANE INSPECTION SURVEY",
                "CRANE DAMAGE INSPECTION",
                "CONTAINER INSPECTION"
            ]:

                data = api_client.get_crane_inspections_api()
                records = ReportRouter._extract_list(data)

                record = ReportRouter._find_record(records, "report_number", num_informe)

                if not record:
                    messagebox.showwarning("Informe", f"No se encontró:\n{num_informe}")
                    return

                report_id = record.get("id")

                if not report_id:
                    messagebox.showwarning("Informe", f"Se encontró el número, pero no el ID:\n{num_informe}")
                    return

                resp = api_client.get_crane_inspection_api(int(report_id))

                if not isinstance(resp, dict) or not resp.get("success"):
                    raise Exception(
                        (resp or {}).get("error")
                        or (resp or {}).get("detail")
                        or "No se pudo cargar el reporte."
                    )

                from Modulos.Informes.crane_inspection.crane_inspection_form import (
                    CraneInspectionForm
                )

                host = ReportRouter._prepare_host(parent, f"Crane Inspection - {num_informe}")
                form = CraneInspectionForm(host)

                # Igual que REVIEW real de tabla
                form.load_record(resp)
                return

            # =====================================================
            # VESSEL CONDITION SURVEY
            # servicios.num_informe -> vessel_condition_surveys.report_number
            # con los APIs actuales tu GET existente es por report_number
            # =====================================================
            if operacion in [
                "DAMAGE INVESTIGATION SURVEY",
                "HULL DAMAGE SURVEY",
                "MOORING INSPECTION",
                "MOORING LINES DAMAGES INSPECTION",
                "OPEN HATCH SURVEY",
                "P&I SURVEY"
            ]:

                data = api_client.get_all_vessel_condition_surveys_api()
                records = ReportRouter._extract_list(data)

                record = ReportRouter._find_record(records, "report_number", num_informe)

                if not record:
                    messagebox.showwarning("Informe", f"No se encontró:\n{num_informe}")
                    return

                # Tu API disponible de review actual carga por report_number
                resp = api_client.get_vessel_condition_survey_api(num_informe)

                if not resp:
                    messagebox.showwarning("Informe", f"No se pudo cargar el informe:\n{num_informe}")
                    return

                from Modulos.Informes.vessel_condition_survey.vessel_condition_survey_form import (
                    VesselConditionSurveyForm
                )

                host = ReportRouter._prepare_host(parent, f"Vessel Condition - {num_informe}")
                form = VesselConditionSurveyForm(host)

                # Igual que REVIEW real de tabla
                payload = ReportRouter._extract_payload(resp)
                if isinstance(payload, dict) and record.get("id") and not payload.get("id"):
                    payload["id"] = record.get("id")
                form.load_record(payload, from_review=True)
                return

            # =====================================================
            # PORT CAPTANCY
            # servicios.num_informe -> port_captancy_reports.report_number
            # GET directo por report_number
            # =====================================================
            if operacion in [
                "PORT CAPTANCY"
            ]:

                data = api_client.get_all_port_captancy_reports_api()
                records = ReportRouter._extract_list(data)

                record = ReportRouter._find_record(records, "report_number", num_informe)

                if not record:
                    messagebox.showwarning(
                        "Informe",
                        f"No se encontró:\n{num_informe}"
                    )
                    return

                resp = api_client.get_port_captancy_report_api(num_informe)

                if not resp:
                    messagebox.showwarning(
                        "Informe",
                        f"No se pudo cargar el informe:\n{num_informe}"
                    )
                    return

                from Modulos.Informes.port_captancy.port_captancy_form import (
                    PortCaptancyForm
                )

                host = ReportRouter._prepare_host(parent, f"Port Captancy - {num_informe}")
                form = PortCaptancyForm(host)

                try:
                    form.load_record(resp)
                except Exception:
                    pass

                return


            # =====================================================
            # NO MATCH
            # =====================================================
            messagebox.showwarning(
                "Informe",
                f"No existe formulario para la operación:\n{operacion}"
            )

        except Exception as e:
            messagebox.showerror(
                "Error al abrir informe",
                str(e)
            )

    # =========================================================
    # VOLVER A SERVICIOS
    # =========================================================
    @staticmethod
    def _go_back_to_services(parent):

        try:

            for child in parent.winfo_children():
                child.destroy()

            from Modulos.Servicios.vista_servicios import VistaServicios

            # filtros vacíos al regresar
            filtros = {}

            VistaServicios(
                parent,
                filtros,
                on_back=lambda: None
            ).pack(fill="both", expand=True)

        except Exception as e:

            messagebox.showerror(
                "Error",
                f"No se pudo volver a Servicios:\n{str(e)}"
            )
