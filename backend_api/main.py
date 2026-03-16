# ============================================================
# main.py — API backend ERP-SOM (FASTAPI)
# ============================================================

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Conexión SQL
import database

# ============================================================
# Routers
# ============================================================

from routers.empleados import router as empleados_router
from routers.surveyores import router as surveyores_router
from routers.clientes import router as clientes_router
from routers.proveedores import router as proveedores_router
from routers.servicios_md import router as servicios_md_router
from routers.servicios_op import router as servicios_router
from routers.continentes_paises_puertos import router as cpp_router
from routers.version import router as version_router
from routers.cliente_credito import router as cliente_credito_router
from routers.factura import router as factura_router
from routers.invoicing import router as invoicing_router
from routers.billing import router as billing_router
from routers.collections import router as collections_router
from routers.bank_reconciliation import router as bank_reconciliation_router
from routers.incoming_payments import router as incoming_payments_router
from routers.dispute_management import router as dispute_management_router
from routers.dispute_notes import router as dispute_notes_router
from routers.disputa import router as disputa_router
from routers.invoice_to_pay import router as invoice_to_pay_router

# Accounting
from routers.accounting import router as accounting_router
from routers.accounting_adjustments import router as accounting_adjustments_router
from routers.closing import router as closing_router
from routers.closing_reports import router as closing_reports_router
from routers.closing_status import router as closing_status_router
from routers.accounting_lines import router as accounting_lines_router

from routers.exchange_rate import router as exchange_rate_router

from routers.password_reset import router as password_reset_router

# HHRR
from routers import hr
from routers import hr_ot_log
from routers.payroll import router as payroll_router
from routers.hr_events import router as hr_events_router
from routers.hr_empleados import router as hr_empleados_router
from routers import noticias
from routers.hr_policies import router as hr_policies_router


# Informes
from routers.reports_ai import router as reports_ai_router
from routers.container_reports import router as container_reports_router
from routers.container_presentation import router as container_presentation_router
from routers.container_presentation_pdf import router as container_presentation_pdf_router
from routers import proyectos_calculo
from routers import vessel_grain_sampling
from routers import status_informes
from routers.vessel_truck_supervision import router as vessel_truck_supervision_router
from routers.draft_survey_router import router as draft_survey_router
from routers.draft_survey_extra_router import router as draft_survey_extra_router
from routers.draft_survey_filters_router import router as draft_survey_filters_router
from routers.draft_survey_unified_router import router as draft_survey_unified_router
from routers.draft_survey_headers_router import router as draft_survey_headers_router
from routers.draft_survey_word_router import router as draft_survey_word_router
from routers.draft_survey_excel_router import router as draft_survey_excel_router
from routers.draft_survey_final_router import router as draft_survey_final_router
from routers.vessel_bunker_reports_router import router as vessel_bunker_reports_router
from routers.vessel_bunker_excel_router import router as vessel_bunker_excel_router
from routers.vessel_bunker_presentation_router import router as vessel_bunker_presentation_router
from routers.vessel_bunker_preview_router import router as vessel_bunker_preview_router
from routers.vessel_cargo_condition_router import router as vessel_cargo_condition_router
from routers.vessel_crane_inspection_router import router as crane_router
from routers.vessel_crane_inspection_reports_router import router as crane_reports_router
from routers.vessel_condition_surveys_router import router as vessel_condition_surveys_router
from routers.port_captancy_reports_router import router as port_captancy_reports_router
from routers.weight_certificates_router import router as weight_certificates_router
from routers.vessel_holds_inspection_certificates_router import router as vessel_holds_inspection_certificates_router
from routers.sampling_certificates_router import router as sampling_certificates_router
from routers.sealing_certificates_router import router as sealing_certificates_router
from routers.lashing_certificates_router import router as lashing_certificates_router

# Comercial
from routers.comercial import router as comercial_router
from routers.comercial_clients_analytics import router as comercial_clients_analytics_router
from routers.comercial_ports_analytics import router as comercial_ports_analytics_router
from routers.comercial_servicios_analytics import router as comercial_servicios_analytics_router
from routers.servicios_precios import router as servicios_precios_router
from routers.cotizaciones import router as cotizaciones_router

#Dashboards
from routers.dashboard_servicios_router import router as dashboard_servicios_router


# ============================================================
# CONFIGURACIÓN FASTAPI
# ============================================================
app = FastAPI(
    title="ERP-SOM API",
    version="1.0",
    description="API para Continentes, Países, Puertos y Empleados — ERP SOM"
    
)

# ============================================================
# CORS — Permite que el ERP Tkinter acceda sin restricciones
# ============================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # luego lo puedes restringir
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# DEBUG: IMPRIMIR RUTAS REGISTRADAS EN STARTUP (SOLO /collections)
# ============================================================
@app.on_event("startup")
def _debug_routes_all():
    print("\n=== TODAS LAS RUTAS REGISTRADAS ===")
    for r in app.router.routes:
        path = getattr(r, "path", "")
        methods = getattr(r, "methods", None)
        print(path, sorted(list(methods)) if methods else [])
    print("=== FIN ===\n")

# ============================================================
# HEALTH CHECK
# ============================================================
@app.get("/")
def home():
    return {"status": "API Online ✔"}

# ============================================================
# ENDPOINT: Continentes
# ============================================================
@app.get("/continentes")
def get_continentes():
    data = database.sql("""
        SELECT nombre
        FROM continente
        ORDER BY nombre;
    """, fetch=True)
    return [row[0] for row in data]

# ============================================================
# ENDPOINT: Países por continente
# ============================================================
@app.get("/paises")
def get_paises(continente: str):
    data = database.sql("""
        SELECT p.nombre
        FROM pais p
        JOIN continente c ON c.id = p.continente_id
        WHERE unaccent(c.nombre) ILIKE unaccent(%s)
        ORDER BY p.nombre;
    """, (continente,), fetch=True)
    return [row[0] for row in data]

# ============================================================
# ENDPOINT: Puertos por país
# ============================================================
@app.get("/puertos")
def get_puertos(pais: str):
    data = database.sql("""
        SELECT pu.nombre
        FROM puerto pu
        JOIN pais pa ON pa.id = pu.pais_id
        WHERE unaccent(pa.nombre) ILIKE unaccent(%s)
        ORDER BY pu.nombre;
    """, (pais,), fetch=True)
    return [row[0] for row in data]

# ============================================================
# Include Routers
# ============================================================

app.include_router(empleados_router)
app.include_router(surveyores_router)
app.include_router(clientes_router)
app.include_router(proveedores_router)
app.include_router(servicios_router)
app.include_router(servicios_md_router)
app.include_router(cpp_router)
app.include_router(version_router)
app.include_router(cliente_credito_router)
app.include_router(factura_router)
app.include_router(invoicing_router)
app.include_router(billing_router)
app.include_router(collections_router)
app.include_router(bank_reconciliation_router)
app.include_router(incoming_payments_router)
app.include_router(dispute_management_router)
app.include_router(dispute_notes_router)
app.include_router(disputa_router)
app.include_router(invoice_to_pay_router)


app.include_router(accounting_router)
app.include_router(accounting_adjustments_router)
app.include_router(closing_router)
app.include_router(closing_reports_router)
app.include_router(closing_status_router)
app.include_router(accounting_lines_router)

app.include_router(exchange_rate_router)

app.include_router(password_reset_router)

app.include_router(hr.router)
app.include_router(hr_ot_log.router)
app.include_router(payroll_router)
app.include_router(hr_events_router)    
app.include_router(hr_empleados_router)
app.include_router(noticias.router)
app.include_router(hr_policies_router)

app.include_router(reports_ai_router)
app.include_router(container_reports_router)
app.include_router(container_presentation_router)
app.include_router(container_presentation_pdf_router)
app.include_router(proyectos_calculo.router)
app.include_router(vessel_grain_sampling.router)
app.include_router(status_informes.router)
app.include_router(vessel_truck_supervision_router)
app.include_router(draft_survey_router)
app.include_router(draft_survey_extra_router)
app.include_router(draft_survey_filters_router)
app.include_router(draft_survey_unified_router)
app.include_router(draft_survey_headers_router)
app.include_router(draft_survey_word_router)
app.include_router(draft_survey_excel_router)
app.include_router(draft_survey_final_router)
app.include_router(vessel_bunker_reports_router)
app.include_router(vessel_bunker_excel_router)
app.include_router(vessel_bunker_presentation_router)
app.include_router(vessel_bunker_preview_router)
app.include_router(vessel_cargo_condition_router)
app.include_router(crane_router)
app.include_router(crane_reports_router)
app.include_router(vessel_condition_surveys_router)
app.include_router(port_captancy_reports_router)
app.include_router(weight_certificates_router)
app.include_router(
    vessel_holds_inspection_certificates_router
)
app.include_router(sampling_certificates_router)
app.include_router(sealing_certificates_router)
app.include_router(lashing_certificates_router)

app.include_router(comercial_router)
app.include_router(comercial_clients_analytics_router)
app.include_router(comercial_ports_analytics_router)
app.include_router(comercial_servicios_analytics_router)
app.include_router(servicios_precios_router)
app.include_router(cotizaciones_router)

app.include_router(dashboard_servicios_router)


# ============================================================
# EJECUCIÓN LOCAL
# ============================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
