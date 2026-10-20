"""Explicit desktop certificate contracts. Field names are database allowlists."""


def f(key, label, kind="text"):
    return {"key": key, "label": label, "type": kind}


def section(title, fields):
    return {"title": title, "fields": fields}


def header(number="report_no", customer=True):
    return section("Servicio", [f(number, "Numero de informe"), f("port", "Puerto"),
                               f("country", "Pais")] + ([f("customer", "Cliente")] if customer else []))


TYPES = {
    "weight": {
        "title": "Weight Certificate", "label": "Peso", "table": "weight_certificates",
        "number": "report_number", "document": "word",
        "sections": [
            section("Servicio", [f("report_number", "Numero de informe"), f("continent", "Continente"),
                    f("country", "Pais"), f("port", "Puerto"), f("operation", "Operacion")]),
            section("Certificado de peso", [
                f("vessel", "Buque"), f("voyage", "Viaje"), f("commodity", "Mercancia"),
                f("bl_figure", "Cantidad B/L"), f("cargo_hold", "Bodegas"), f("shipper", "Embarcador"),
                f("consignee", "Consignatario"), f("terminal", "Terminal"), f("loading_port", "Puerto de carga"),
                f("weight_determination", "Metodo de determinacion del peso"), f("date", "Fecha", "date"),
                f("quantity", "Cantidad cargada (MT)")]),
            section("Observaciones", [f("remarks", "Remarks", "textarea")]),
        ],
    },
    "holds": {
        "title": "Holds Inspection Certificate", "label": "Inspeccion de bodegas",
        "table": "vessel_holds_inspection_certificates", "number": "report_number", "document": "excel",
        "sections": [
            header("report_number", False),
            section("Buque y carga", [f("vessel", "Buque"), f("voyage", "Viaje"), f("load_port", "Puerto de carga"),
                    f("place", "Lugar"), f("installation", "Instalacion"), f("product", "Producto"), f("date", "Fecha", "date")]),
            section("Inspeccion y aceptacion", [
                f("inspection_time", "Hora de inspeccion", "time"), f("vessel_holds", "Bodegas del buque"),
                f("vessel_holds_status", "Estado de las bodegas", "textarea"), f("cargo_holds", "Bodegas de carga"),
                f("accepted_time", "Hora de aceptacion", "time"), f("place_location", "Lugar de aceptacion"),
                f("place_date", "Fecha de aceptacion", "date")]),
            section("Prueba de estanqueidad", [f("hose_test_start", "Inicio", "time"), f("hose_test_end", "Fin", "time")]),
            section("Observaciones y firma", [f("remarks", "Remarks", "textarea"), f("master_chief_officer", "Master / Chief Officer")]),
        ],
    },
    "sampling": {
        "title": "Sampling Certificate", "label": "Muestreo", "table": "sampling_certificates",
        "number": "report_no", "document": "excel",
        "sections": [
            header(),
            section("Certificado", [f("certificate_no", "Numero de certificado"), f("vessel", "Buque"),
                    f("date", "Fecha", "date"), f("place", "Lugar"), f("cargo", "Carga"), f("holds_inspected", "Bodegas inspeccionadas")]),
            section("Sellos por bodega", [f(f"hold_{i}_seal", f"Bodega {i} - Sello") for i in range(1, 11)]),
            section("Observaciones y cierre", [f("observations", "Observaciones", "textarea"),
                    f("closing_date", "Fecha de cierre", "date"), f("closing_time", "Hora de cierre", "time"), f("master", "Master / Chief Officer")]),
        ],
    },
    "sealing": {
        "title": "Sealing Certificate", "label": "Sellado", "table": "sealing_certificates",
        "number": "report_no", "document": "excel",
        "sections": [
            header(),
            section("Certificado", [f("certificate_no", "Numero de certificado"), f("vessel", "Buque"),
                    f("date", "Fecha", "date"), f("location", "Ubicacion"), f("cargo", "Carga")]),
            *[section(f"Bodega {i}", [f(f"hold_{i}_fwd_escape", "FWD ESCAPE"),
                    f(f"hold_{i}_fwd_aft_hatch", "FWD/AFT HATCH"), f(f"hold_{i}_aft_escape", "AFT ESCAPE")]) for i in range(1, 7)],
            section("Observaciones y cierre", [f("remarks", "Remarks", "textarea"), f("chief_officer", "Chief Officer"),
                    f("closing_date", "Fecha de cierre", "date"), f("closing_time", "Hora de cierre", "time")]),
        ],
    },
    "lashing": {
        "title": "Cargo Lashing Certificate", "label": "Trincado", "table": "lashing_certificates",
        "number": "report_no", "document": "word",
        "sections": [
            header(),
            section("Trincado", [f("flat_rack_container", "Contenedor Flat Rack"), f("cargo_type", "Tipo de carga"),
                    f("lashing_material", "Material de trincado"), f("date", "Fecha", "date"), f("place", "Lugar")]),
            section("Tensores y finalizacion", [f("ratchet_quantity", "Cantidad de tensores"),
                    f("where_carry_out", "Lugar de ejecucion"), f("completion_date", "Fecha de finalizacion", "date")]),
        ],
    },
}

for spec in TYPES.values():
    spec["fields"] = {field["key"]: field for group in spec["sections"] for field in group["fields"]}

# Exact row order consumed by the original Excel templates' data!B cells.
EXCEL_FIELDS = {
    "holds": "id report_number port country vessel voyage load_port place installation product date inspection_time vessel_holds vessel_holds_status cargo_holds accepted_time place_location place_date hose_test_start hose_test_end remarks created_at updated_at status master_chief_officer".split(),
    "sampling": ("id report_no port country customer certificate_no vessel date place cargo holds_inspected".split()
                 + [f"hold_{i}_seal" for i in range(1, 11)]
                 + "observations closing_date closing_time master created_at updated_at status".split()),
    "sealing": ("id report_no port country customer certificate_no vessel date location cargo".split()
                + [f"hold_{i}_{part}" for i in range(1, 7) for part in ("fwd_escape", "fwd_aft_hatch", "aft_escape")]
                + "remarks chief_officer closing_date closing_time created_at status".split()),
}
