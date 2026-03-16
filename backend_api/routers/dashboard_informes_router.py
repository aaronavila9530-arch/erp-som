# ============================================================
# ERP-SOM
# DASHBOARD INFORMES ROUTER
# ============================================================

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from database import get_db

router = APIRouter(
    prefix="/dashboard-informes",
    tags=["Dashboard Informes"]
)

# ============================================================
# FILTROS DINÁMICOS
# ============================================================

@router.get("/filtros")
def dashboard_informes_filtros(
    anio: int | None = Query(default=None),
    pais: str | None = Query(default=None),
    puerto: str | None = Query(default=None),
    cliente: str | None = Query(default=None),
    operacion: str | None = Query(default=None),
    tipo_informe: str | None = Query(default=None),
    db=Depends(get_db)
):

    try:

        cursor = db.cursor()
        anio_final = anio if anio else datetime.now().year

        query = """

        WITH base AS (

            SELECT
                s.num_informe,
                s.pais,
                s.puerto,
                s.cliente,
                s.operacion,
                EXTRACT(YEAR FROM s.fecha_fin)::int AS anio
            FROM servicios s
            WHERE s.fecha_fin IS NOT NULL

        ),

        informes_union AS (

            SELECT report_number AS num_informe,'Weight Certificate' tipo FROM weight_certificates
            UNION ALL SELECT cert_no,'Truck Supervision' FROM vessel_truck_supervision_reports
            UNION ALL SELECT report_number,'Holds Inspection' FROM vessel_holds_inspection_certificates
            UNION ALL SELECT cert_no,'Grain Sampling' FROM vessel_grain_sampling_reports
            UNION ALL SELECT report_number,'Crane Inspection' FROM vessel_crane_inspection_reports
            UNION ALL SELECT report_number,'Condition Survey' FROM vessel_condition_surveys
            UNION ALL SELECT report_number,'Cargo Condition' FROM vessel_cargo_condition_surveys
            UNION ALL SELECT bunker_cert_no,'Bunker Survey' FROM vessel_bunker_reports
            UNION ALL SELECT report_no,'Sealing Certificate' FROM sealing_certificates
            UNION ALL SELECT report_no,'Sampling Certificate' FROM sampling_certificates
            UNION ALL SELECT report_number,'Port Captancy' FROM port_captancy_reports
            UNION ALL SELECT report_no,'Lashing Certificate' FROM lashing_certificates
            UNION ALL SELECT draft_report_number,'Draft Survey' FROM draft_survey

        ),

        base_final AS (

            SELECT
                b.*,
                i.tipo
            FROM base b
            LEFT JOIN informes_union i
            ON b.num_informe=i.num_informe

        )

        SELECT json_build_object(

            'anios',
            (SELECT json_agg(DISTINCT anio) FROM base_final),

            'paises',
            (SELECT json_agg(DISTINCT pais) FROM base_final WHERE anio=%s),

            'puertos',
            (SELECT json_agg(DISTINCT puerto) FROM base_final WHERE anio=%s),

            'clientes',
            (SELECT json_agg(DISTINCT cliente) FROM base_final WHERE anio=%s),

            'operaciones',
            (SELECT json_agg(DISTINCT operacion) FROM base_final WHERE anio=%s),

            'tipos_informe',
            (SELECT json_agg(DISTINCT tipo) FROM base_final)

        )

        """

        cursor.execute(query,(anio_final,anio_final,anio_final,anio_final))
        result = cursor.fetchone()

        return result[0] if result else {}

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Error filtros informes: {str(e)}"
        )

# ============================================================
# DASHBOARD INFORMES
# ============================================================

@router.get("/resumen")
def dashboard_informes_resumen(
    anio: int | None = Query(default=None),
    pais: str | None = Query(default=None),
    puerto: str | None = Query(default=None),
    cliente: str | None = Query(default=None),
    operacion: str | None = Query(default=None),
    tipo_informe: str | None = Query(default=None),
    db=Depends(get_db)
):

    try:

        cursor = db.cursor()
        anio_final = anio if anio else datetime.now().year

        query = """

        WITH servicios_base AS (

            SELECT
                num_informe,
                fecha_fin,
                pais,
                puerto,
                cliente,
                operacion,
                EXTRACT(YEAR FROM fecha_fin)::int AS anio
            FROM servicios
            WHERE fecha_fin IS NOT NULL

        ),

        informes_union AS (

            SELECT report_number AS num_informe, weight_certificates.created_at, 'Weight Certificate' tipo
            FROM weight_certificates

            UNION ALL
            SELECT cert_no, vessel_truck_supervision_reports.created_at,'Truck Supervision'
            FROM vessel_truck_supervision_reports

            UNION ALL
            SELECT report_number, vessel_holds_inspection_certificates.created_at,'Holds Inspection'
            FROM vessel_holds_inspection_certificates

            UNION ALL
            SELECT cert_no, vessel_grain_sampling_reports.created_at,'Grain Sampling'
            FROM vessel_grain_sampling_reports

            UNION ALL
            SELECT report_number, vessel_crane_inspection_reports.created_at,'Crane Inspection'
            FROM vessel_crane_inspection_reports

            UNION ALL
            SELECT report_number, vessel_condition_surveys.created_at,'Condition Survey'
            FROM vessel_condition_surveys

            UNION ALL
            SELECT report_number, vessel_cargo_condition_surveys.created_at,'Cargo Condition'
            FROM vessel_cargo_condition_surveys

            UNION ALL
            SELECT bunker_cert_no, vessel_bunker_reports.created_at,'Bunker Survey'
            FROM vessel_bunker_reports

            UNION ALL
            SELECT report_no, sealing_certificates.created_at,'Sealing Certificate'
            FROM sealing_certificates

            UNION ALL
            SELECT report_no, sampling_certificates.created_at,'Sampling Certificate'
            FROM sampling_certificates

            UNION ALL
            SELECT report_number, port_captancy_reports.created_at,'Port Captancy'
            FROM port_captancy_reports

            UNION ALL
            SELECT report_no, NULL::timestamp,'Lashing Certificate'
            FROM lashing_certificates

            UNION ALL
            SELECT draft_report_number, NULL::timestamp,'Draft Survey'
            FROM draft_survey

        ),

        base AS (

            SELECT
                s.*,
                i.tipo,
                i.created_at AS fecha_informe,
                CASE
                    WHEN i.created_at IS NULL THEN NULL
                    ELSE EXTRACT(EPOCH FROM (i.created_at - s.fecha_fin))/3600
                END AS horas_para_informe

            FROM servicios_base s
            LEFT JOIN informes_union i
            ON s.num_informe=i.num_informe

        ),

        filtrada AS (

            SELECT *
            FROM base
            WHERE anio=%s
            AND (%s IS NULL OR pais=%s)
            AND (%s IS NULL OR puerto=%s)
            AND (%s IS NULL OR cliente=%s)
            AND (%s IS NULL OR operacion=%s)
            AND (%s IS NULL OR tipo=%s)

        )

        SELECT json_build_object(

            'kpis', json_build_object(

                'tiempo_promedio_horas',
                COALESCE((SELECT AVG(horas_para_informe) FROM filtrada),0),

                'total_informes',
                COALESCE((SELECT COUNT(*) FROM filtrada),0),

                'clientes_con_informes',
                COALESCE((SELECT COUNT(DISTINCT cliente) FROM filtrada),0),

                'puertos_con_informes',
                COALESCE((SELECT COUNT(DISTINCT puerto) FROM filtrada),0)

            ),

            'informes_por_tipo',
            COALESCE((SELECT json_agg(t)
             FROM (
                SELECT tipo,COUNT(*) total
                FROM filtrada
                GROUP BY tipo
                ORDER BY total DESC
             ) t),'[]'::json),

            'informes_por_pais',
            COALESCE((SELECT json_agg(t)
             FROM (
                SELECT pais,COUNT(*) total
                FROM filtrada
                GROUP BY pais
                ORDER BY total DESC
             ) t),'[]'::json),

            'informes_por_puerto',
            COALESCE((SELECT json_agg(t)
             FROM (
                SELECT puerto,COUNT(*) total
                FROM filtrada
                GROUP BY puerto
                ORDER BY total DESC
             ) t),'[]'::json),

            'informes_por_cliente',
            COALESCE((SELECT json_agg(t)
             FROM (
                SELECT cliente,COUNT(*) total
                FROM filtrada
                GROUP BY cliente
                ORDER BY total DESC
             ) t),'[]'::json),

            'tiempo_por_operacion',
            COALESCE((SELECT json_agg(t)
             FROM (
                SELECT operacion,
                       AVG(horas_para_informe) horas_promedio
                FROM filtrada
                GROUP BY operacion
             ) t),'[]'::json)

        )

        """

        params = (
            anio_final,
            pais,pais,
            puerto,puerto,
            cliente,cliente,
            operacion,operacion,
            tipo_informe,tipo_informe
        )

        cursor.execute(query,params)
        result = cursor.fetchone()

        return result[0] if result else {}

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Error dashboard informes: {str(e)}"
        )