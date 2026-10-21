import api_client


class ReportFinder:

    @staticmethod
    def find_report_id(num_informe: str, operacion: str):

        operacion = (operacion or "").upper().strip()

        # ------------------------------------------------
        # TRUCK SUPERVISION
        # ------------------------------------------------
        if operacion == "LOGISTICS SUPERVISON":

            data = api_client.get_vessel_truck_supervision_list_api()

            for r in data.get("data", []):
                if r.get("cert_no") == num_informe:
                    return r.get("id")

        # ------------------------------------------------
        # GRAIN SAMPLING
        # ------------------------------------------------
        if operacion in [
            "SUPERVISION MUESTREO DE GRANOS",
            "SAMPLING SUPERVISION",
            "TOMA DE MUESTRAS MAG"
        ]:

            data = api_client.get_vessel_grain_sampling_list_api()

            for r in data.get("data", []):
                if r.get("cert_no") == num_informe:
                    return r.get("id")

        # ------------------------------------------------
        # CRANE INSPECTION
        # ------------------------------------------------
        if operacion in [
            "CRANE INSPECTION SURVEY",
            "CRANE DAMAGE INSPECTION"
        ]:

            data = api_client.get_crane_inspections_api()

            for r in data.get("data", []):
                if r.get("report_number") == num_informe:
                    return r.get("id")

        # ------------------------------------------------
        # CARGO CONDITION
        # ------------------------------------------------
        if operacion in [
            "CARGO CONDITION",
            "CARGO DISCHARGE SUPERVISION",
            "CARGO LOADING SUPERVISION"
        ]:

            data = api_client.get_all_vessel_cargo_condition_api()

            for r in data.get("data", []):
                if r.get("report_number") == num_informe:
                    return r.get("id")

        # ------------------------------------------------
        # BUNKER
        # ------------------------------------------------
        if operacion in [
            "BUNKER SURVEY",
            "BQS BUNKER QUANTITY SURVEY",
            "SPOT BUNKER SURVEY"
        ]:

            data = api_client.get_all_vessel_bunker_reports_api()

            for r in data.get("data", []):
                if r.get("bunker_cert_no") == num_informe:
                    return r.get("id")

        return None