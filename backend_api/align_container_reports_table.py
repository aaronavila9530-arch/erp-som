import psycopg2
from psycopg2 import sql

DATABASE_URL = "postgresql://postgres:LjjyuIUsTSCdiwPVHSSwtIYPOsRQytGX@shortline.proxy.rlwy.net:50018/railway"


COLUMNS = {
    # ==============================
    # META
    # ==============================
    "linked_report_number": "TEXT",
    "container_type_text": "TEXT",

    "user": "TEXT",
    "status": "TEXT",

    # ==============================
    # GENERAL INFORMATION
    # ==============================
    "report_no": "TEXT",
    "bl": "TEXT",
    "seals": "TEXT",
    "appointment": "TEXT",
    "shippers": "TEXT",
    "inspection_place": "TEXT",
    "contact_person": "TEXT",
    "on_behalf_of": "TEXT",
    "consignee_notify": "TEXT",
    "vessel": "TEXT",
    "contact_datetime": "TEXT",
    "init_inspection_datetime": "TEXT",
    "init_to": "TEXT",
    "final_inspection_datetime": "TEXT",
    "final_to": "TEXT",

    # ==============================
    # CONTAINER DESCRIPTION (CHECKS)
    # ==============================
    "container_size_20": "BOOLEAN",
    "container_size_40": "BOOLEAN",

    "container_type_dry": "BOOLEAN",
    "container_type_reefer": "BOOLEAN",
    "container_type_iso": "BOOLEAN",
    "container_type_flat_rack": "BOOLEAN",

    "container_load_fcl": "BOOLEAN",
    "container_load_lcl": "BOOLEAN",

    # ==============================
    # CAUSE OF INSPECTION
    # ==============================
    "cause_seals_bl": "BOOLEAN",
    "cause_change_seals": "BOOLEAN",
    "cause_customs": "BOOLEAN",
    "cause_transfer": "BOOLEAN",
    "cause_leaking": "BOOLEAN",
    "cause_damage": "BOOLEAN",
    "cause_stuff_condition": "BOOLEAN",
    "cause_detail": "TEXT",

    # ==============================
    # GOODS & PACKAGES
    # ==============================
    "goods_description": "TEXT",

    "package_carton": "BOOLEAN",
    "package_bags": "BOOLEAN",
    "package_boxes": "BOOLEAN",
    "package_drums": "BOOLEAN",
    "package_pallets": "BOOLEAN",
    "package_bulk": "BOOLEAN",
    "package_bales": "BOOLEAN",
    "package_crates": "BOOLEAN",
    "package_other": "BOOLEAN",

    "qty_1_left": "TEXT",
    "qty_1_right": "TEXT",
    "qty_2_left": "TEXT",
    "qty_2_right": "TEXT",
    "qty_3_left": "TEXT",
    "qty_3_right": "TEXT",

    "package_marking": "TEXT",
    "goods_condition": "TEXT",

    # ==============================
    # NARRATIVES
    # ==============================
    "damage_details": "TEXT",
    "remarks": "TEXT",
    "conclusion": "TEXT",

    # ==============================
    # LINKS & DOCS
    # ==============================
    "picture_link": "TEXT",

    "doc_bl": "BOOLEAN",
    "doc_packing_list": "BOOLEAN",
    "doc_shipping_invoice": "BOOLEAN",
    "doc_cargo_manifest": "BOOLEAN",
    "doc_commercial_invoice": "BOOLEAN",
    "doc_delivery_record": "BOOLEAN",
    "doc_notice_loss": "BOOLEAN",
    "doc_insurance_policy": "BOOLEAN",
    "doc_other": "BOOLEAN",

    # ==============================
    # QUALITY
    # ==============================
    "quality_packing_exam": "BOOLEAN",
    "quality_un_witness": "BOOLEAN",
    "quality_visual_exam": "BOOLEAN",
    "quality_product_exam": "BOOLEAN",
    "quality_documents": "BOOLEAN",
    "quality_sanitary_cert": "BOOLEAN",
    "quality_phytosanitary_cert": "BOOLEAN",
    "quality_factory_cert": "BOOLEAN",
    "quality_origin_cert": "BOOLEAN",

    # ==============================
    # PERSONS
    # ==============================
    "person_1_name": "TEXT",
    "person_1_position": "TEXT",
    "person_2_name": "TEXT",
    "person_2_position": "TEXT",
    "person_3_name": "TEXT",
    "person_3_position": "TEXT",

    # ==============================
    # INSPECTED CONTAINER
    # ==============================
    "ic_manuf": "TEXT",
    "ic_csc": "TEXT",
    "ic_max_gw": "TEXT",
    "ic_tare": "TEXT",

    # ==============================
    # GENERAL DETAILS
    # ==============================
    "new_commodity": "BOOLEAN",
    "used_commodity": "BOOLEAN",
    "net_weight": "TEXT",
    "gross_weight": "TEXT",
    "volume": "TEXT",

    # ==============================
    # TRANSFER TO CONTAINER
    # ==============================
    "tr_number": "TEXT",
    "tr_manuf": "TEXT",
    "tr_csc": "TEXT",
    "tr_seal": "TEXT",
    "tr_max_gw": "TEXT",
    "tr_tare": "TEXT",

    # ==============================
    # SCOPE OF INSPECTION
    # ==============================
    "scope_100": "BOOLEAN",
    "scope_random": "BOOLEAN",
    "scope_items": "TEXT",
}


def main():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS container_reports (
            id SERIAL PRIMARY KEY,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    for col, col_type in COLUMNS.items():
        cur.execute(
            sql.SQL("""
                ALTER TABLE container_reports
                ADD COLUMN IF NOT EXISTS {} {};
            """).format(
                sql.Identifier(col),
                sql.SQL(col_type)
            )
        )

    conn.commit()
    cur.close()
    conn.close()

    print("✅ container_reports aligned successfully.")


if __name__ == "__main__":
    main()
