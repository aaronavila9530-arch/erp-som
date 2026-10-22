"""Web field contract mirrored from GrainSamplingVesselForm; no desktop changes."""
def field(key, label, kind="text"):
    return {"key": key, "label": label, "type": kind}


def section(title, fields):
    return {"title": title, "fields": fields}


TIMES = {
    "arrival_buoy_time": "Arribo a boya", "nor_tendered_time": "NOR presentado",
    "holds_opening_time": "Apertura de bodegas", "surveyors_onboard_time": "Surveyors a bordo",
    "seals_verification_time": "Verificacion de sellos", "sampling_start_time": "Inicio del muestreo",
    "sampling_end_time": "Fin del muestreo", "surveyors_disembark_time": "Desembarque de surveyors",
}
SECTIONS = [
    section("Servicio y buque", [field("cert_no", "Numero de informe"), field("place_date", "Fecha de inspeccion", "date"),
        field("vessel_name", "Buque"), field("requested_by", "Solicitado por"), field("captain", "Capitan"), field("chief_officer", "Primer oficial")]),
    section("Caracteristicas del buque", [field("ship_flag", "Bandera"), field("ship_grt", "GRT"), field("ship_nrt", "NRT"), field("ship_imo", "IMO"), field("ship_year", "Ano de construccion")]),
    section("Registro de operaciones", [field(k, v, "datetime") for k, v in TIMES.items()]),
    section("Productos por bodega", [item for i in range(1, 11) for item in [field(f"hold{i}_product", f"{i}. Producto"), field(f"hold{i}_hold", f"{i}. Bodega"), field(f"hold{i}_tonnage", f"{i}. Toneladas")]]),
    section("Cantidad declarada", [field("products_total", "Total de productos (MT)")]),
    section("Puntos de muestreo", [field(f"sample{i}_{k}", f"{i}. {label}") for i in range(1, 11) for k, label in [
        ("hold", "Bodega"), ("proa_babor", "Proa babor"), ("proa_estribor", "Proa estribor"),
        ("centro", "Centro"), ("popa_babor", "Popa babor"), ("popa_estribor", "Popa estribor")]]),
    section("Supervision y conclusion", [field("supervision", "Fecha y hora de supervision", "datetime"), field("conclusion", "Conclusion", "textarea")]),
]
SPEC = {"title": "Muestreos de Granos", "label": "Muestreos de Granos", "table": "vessel_grain_sampling_reports",
        "number": "cert_no", "document": "word", "sections": SECTIONS,
        "fields": {f["key"]: f for s in SECTIONS for f in s["fields"]}}
