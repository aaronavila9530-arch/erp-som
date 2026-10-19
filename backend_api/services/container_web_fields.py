"""Web form contract. Existing desktop payload names remain unchanged."""


def section(title, kind, entries):
    return {"title": title, "fields": [
        {"key": key, "label": label, "type": kind} for key, label in entries
    ]}


SECTIONS = [
    section("General information", "text", [
        ("linked_report_number", "Service report number"),
        ("container_type_text", "Container type"), ("report_no", "Container No."),
        ("bl", "B / L"), ("seals", "Seals"), ("appointment", "Appointment"),
        ("shippers", "Shippers"), ("inspection_place", "Inspection place"),
        ("contact_person", "Contact person"), ("on_behalf_of", "On behalf of"),
        ("consignee_notify", "Consignee / Notify"), ("vessel", "Vessel")]),
    section("Inspection dates", "datetime-local", [
        ("contact_datetime", "Contact date / time"),
        ("init_inspection_datetime", "Initial inspection - From"), ("init_to", "Initial inspection - To"),
        ("final_inspection_datetime", "Final inspection - From"), ("final_to", "Final inspection - To")]),
    section("Container description", "checkbox", [
        ("container_size_20", "20 Foot"), ("container_size_40", "40 Foot"),
        ("container_type_dry", "Dry"), ("container_type_reefer", "Reefer"),
        ("container_type_iso", "ISO Tank"), ("container_type_flat_rack", "Flat Rack"),
        ("container_load_fcl", "FCL"), ("container_load_lcl", "LCL")]),
    section("Cause of inspection", "checkbox", [
        ("cause_seals_bl", "Seals differ from B/L"), ("cause_change_seals", "Change seals"),
        ("cause_customs", "Customs"), ("cause_transfer", "Transfer"), ("cause_leaking", "Leaking"),
        ("cause_damage", "Damage"), ("cause_stuff_condition", "Stuff / D condition")]),
    section("Goods and observations", "textarea", [
        ("cause_detail", "Detail of cause"), ("goods_description", "Goods description"),
        ("package_marking", "Package and marking description"), ("goods_condition", "Goods condition"),
        ("damage_details", "Details of damage / shortage"), ("remarks", "Remarks"), ("conclusion", "Conclusion")]),
    section("Type of package", "checkbox", [("package_" + key, label) for key, label in [
        ("carton", "Carton"), ("bags", "Bags"), ("boxes", "Boxes"), ("drums", "Drums"),
        ("pallets", "Pallets"), ("bulk", "Bulk"), ("bales", "Bales"), ("crates", "Crates"), ("other", "Other")]]),
    section("Quantity of packages", "text", [(f"qty_{n}_{side}", f"{n} - {label}")
        for n in (1, 2, 3) for side, label in (("left", "Description"), ("right", "Quantity"))]),
    section("Collected documents", "checkbox", [("doc_" + key, label) for key, label in [
        ("bl", "B/L"), ("packing_list", "Packing list"), ("shipping_invoice", "Shipping invoice"),
        ("cargo_manifest", "Cargo manifest"), ("commercial_invoice", "Commercial invoice"),
        ("delivery_record", "Delivery / Received record"), ("notice_loss", "Notice of loss / damage"),
        ("insurance_policy", "Insurance policy"), ("other", "Other")]]),
    section("Quality", "checkbox", [("quality_" + key, label) for key, label in [
        ("packing_exam", "Packing examination"), ("un_witness", "UN / Stuffed witness"),
        ("visual_exam", "Visual examination"), ("product_exam", "Product examination"),
        ("documents", "Quality documents"), ("sanitary_cert", "Sanitary certificate"),
        ("phytosanitary_cert", "Phytosanitary certificate"), ("factory_cert", "Factory certificate"),
        ("origin_cert", "Certificate of origin")]]),
    section("Inspected container", "text", [("ic_" + key, label) for key, label in [
        ("manuf", "Manufacturer No."), ("csc", "CSC Safety approval"), ("max_gw", "Maximum gross weight (kg)"), ("tare", "Tare (kg)")]]),
    section("Commodity", "checkbox", [("new_commodity", "New commodity"), ("used_commodity", "Used commodity")]),
    section("General details", "text", [("net_weight", "Net weight (kg)"), ("gross_weight", "Gross weight (kg)"), ("volume", "Volume (m3)")]),
    section("Transfer to container", "text", [("tr_" + key, label) for key, label in [
        ("number", "Container No."), ("manuf", "Manufacturer No."), ("csc", "CSC Safety approval"),
        ("seal", "Seal"), ("max_gw", "Maximum gross weight (kg)"), ("tare", "Tare (kg)")]]),
    section("Scope of inspection", "checkbox", [("scope_100", "100%"), ("scope_random", "Random")]),
    section("Scope and photographs", "text", [("scope_items", "Items inspected"), ("picture_link", "Picture link")]),
    section("Persons present at survey", "text", [(f"person_{n}_{key}", f"Person {n} - {label}")
        for n in (1, 2, 3) for key, label in (("name", "Name"), ("position", "Position"))]),
]
FIELDS = {field["key"]: field for group in SECTIONS for field in group["fields"]}
BOOLEAN_FIELDS = {key for key, field in FIELDS.items() if field["type"] == "checkbox"}
DATE_FIELDS = {key for key, field in FIELDS.items() if field["type"] == "datetime-local"}
NARRATIVE_FIELDS = {key for key, field in FIELDS.items() if field["type"] == "textarea"}
