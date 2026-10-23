"""MSL web fields mirrored from desktop; never used for MCI generic reports."""
from services.grain_web_fields import field, section


def make_spec(kind):
    cargo = kind == "cargo_condition"
    general = ["report_number", "continent", "country", "port", "service_start_date",
               "requested_by", "vessel", "chief_officer", "link_picture"]
    general += (["operation", "master", "cargo_type"] if cargo else
                ["popup_operation", "report_type", "master_of_ship", "operation"])
    particulars = (["vessel_port_registry_flag", "vessel_grt", "vessel_nrt", "vessel_imo_no", "vessel_year_build"]
                   if cargo else ["port_registry_flag", "grt", "nrt", "imo_no", "year_built"])
    def label(key):
        return {"report_number": "Numero de informe", "requested_by": "Preparado para",
                "vessel": "Buque", "link_picture": "Enlace de fotografias"}.get(key, key.replace("_", " ").capitalize())
    groups = [section("Servicio", [field(k, label(k), "date" if k.endswith("_date") else "text") for k in general]),
              section("Caracteristicas del buque", [field(k, label(k)) for k in particulars])]
    times = ["arrival", "inspection"] + ([f"time_{i}" for i in range(8)] if cargo else [f"ts_{i}" for i in range(1, 9)])
    groups.append(section("Registro de operaciones", [field(f"{k}_{part}", f"{label(k)} / {part}", "date" if part == "date" else "text")
                                                       for k in times for part in ("date", "hour", "minute")]))
    for key, title in [("narrative", "Narrative"), ("findings" if cargo else "survey_findings", "Survey findings"),
                       ("remarks", "Remarks"), ("conclusion", "Conclusion")]:
        group = section(title, [field(f"{key}_{i}", f"{title} {i}", "textarea") for i in range(1, 11 if cargo else 21)])
        group["repeatable"] = True
        groups.append(group)
    title = "Cargo Condition Survey" if cargo else "Vessel Condition Survey"
    return {"title": title, "label": title, "table": "vessel_cargo_condition_surveys" if cargo else "vessel_condition_surveys",
            "number": "report_number", "document": "word", "sections": groups,
            "fields": {f["key"]: f for group in groups for f in group["fields"]}}


VESSEL_TYPES = {kind: make_spec(kind) for kind in ("condition", "cargo_condition")}
