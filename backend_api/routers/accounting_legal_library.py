from __future__ import annotations

from fastapi import APIRouter, Query


router = APIRouter(prefix="/accounting/legal-library", tags=["Accounting Legal Library"])


LEGAL_ITEMS = [
    {
        "code": "CR-TAX-9635",
        "category": "Hacienda",
        "title": "Ley de Fortalecimiento de las Finanzas Publicas",
        "norm_type": "Ley vigente consolidada",
        "number": "9635",
        "issuer": "Asamblea Legislativa",
        "date": "2018-12-03",
        "summary": "Ley marco moderna que introdujo el IVA y reformas fiscales relevantes para renta, reglas fiscales y cumplimiento tributario.",
        "erp_relevance": "Referencia prioritaria para IVA, cierre fiscal, conciliacion tributaria, reportes ejecutivos y controles de cumplimiento.",
        "keywords": ["iva", "renta", "finanzas publicas", "hacienda", "cumplimiento", "ley 9635", "vigente"],
        "official_url": "https://pgrweb.go.cr/scij/Busqueda/Normativa/Normas/nrm_texto_completo.aspx?nValor1=1&nValor2=87720&nValor3=143345&param1=NRTC&strTipM=TC",
    },
    {
        "code": "CR-VAT-41779-H",
        "category": "Hacienda",
        "title": "Reglamento de la Ley del Impuesto sobre el Valor Agregado",
        "norm_type": "Decreto Ejecutivo vigente consolidado",
        "number": "41779-H",
        "issuer": "Poder Ejecutivo / Ministerio de Hacienda",
        "date": "2019-06-07",
        "summary": "Reglamento operativo del IVA: hecho generador, tarifas, exenciones, creditos fiscales, documentacion y reglas de aplicacion.",
        "erp_relevance": "Base de trabajo para Centro fiscal, libros de compras/ventas, credito fiscal, D-150 y revision documental.",
        "keywords": ["iva", "reglamento iva", "credito fiscal", "exenciones", "d150", "hacienda", "vigente"],
        "official_url": "https://pgrweb.go.cr/scij/Busqueda/Normativa/Normas/nrm_texto_completo.aspx?nValor1=1&nValor2=88953&nValor3=138939&param1=NRTC&strTipM=TC",
    },
    {
        "code": "CR-TAX-10386",
        "category": "Hacienda",
        "title": "Reforma a Ley de Fortalecimiento de las Finanzas Publicas",
        "norm_type": "Ley",
        "number": "10386",
        "issuer": "Asamblea Legislativa",
        "date": "2023-09-26",
        "summary": "Reforma reciente vinculada con la Ley 9635 y su marco de responsabilidad fiscal.",
        "erp_relevance": "Referencia para mantener actualizada la biblioteca legal y separar normativa historica de reformas recientes.",
        "keywords": ["reforma", "ley 9635", "finanzas publicas", "responsabilidad fiscal", "vigente"],
        "official_url": "https://pgrweb.go.cr/scij/Busqueda/Normativa/Normas/nrm_texto_completo.aspx?nValor1=1&nValor2=100319&nValor3=137721&param1=NRTC",
    },
    {
        "code": "CR-COM-3284",
        "category": "Comercial",
        "title": "Codigo de Comercio",
        "norm_type": "Ley",
        "number": "3284",
        "issuer": "Asamblea Legislativa",
        "date": "1964-04-30",
        "summary": "Marco mercantil general de Costa Rica: actos de comercio, sociedades, obligaciones de comerciantes, libros, documentos y conservacion de comprobantes.",
        "erp_relevance": "Soporta obligaciones comerciales, facturacion, sociedades, conservacion documental y controles contables basicos.",
        "keywords": ["comercio", "sociedades", "contabilidad", "libros", "facturas", "comprobantes", "mercantil"],
        "official_url": "https://pgrweb.go.cr/scij/Busqueda/Normativa/Normas/nrm_texto_completo.aspx?nValor1=1&nValor2=6239&nValor3=113791&param1=NRTC&strTipM=TC",
    },
    {
        "code": "CR-COM-3284-234",
        "category": "Contable",
        "title": "Codigo de Comercio - obligaciones contables del comerciante",
        "norm_type": "Ley / Articulo",
        "number": "3284 art. 234",
        "issuer": "Asamblea Legislativa",
        "date": "1964-04-30",
        "summary": "Referencia especifica sobre llevar contabilidad del negocio en orden y conservar libros, correspondencia, facturas y comprobantes.",
        "erp_relevance": "Base legal para auditoria documental, archivo de soportes, anexos, comprobantes y trazabilidad de Accounting.",
        "keywords": ["contabilidad", "libros", "facturas", "comprobantes", "conservar", "archivo", "soportes"],
        "official_url": "https://pgrweb.go.cr/scij/Busqueda/Normativa/normas/nrm_articulo.aspx?nValor1=1&nValor2=6239&nValor3=100547&nValor5=34367&param1=NRA",
    },
    {
        "code": "CR-TAX-4755",
        "category": "Hacienda",
        "title": "Codigo de Normas y Procedimientos Tributarios",
        "norm_type": "Ley",
        "number": "4755",
        "issuer": "Asamblea Legislativa",
        "date": "1971-05-03",
        "summary": "Codigo Tributario: normas generales, potestades de fiscalizacion, deberes formales, procedimientos, infracciones y sanciones tributarias.",
        "erp_relevance": "Base para controles de cumplimiento, auditoria fiscal, obligaciones formales y evidencia ante Hacienda.",
        "keywords": ["tributario", "hacienda", "fiscalizacion", "sanciones", "deberes formales", "procedimiento"],
        "official_url": "https://pgrweb.go.cr/scij/Busqueda/Normativa/Normas/nrm_texto_completo.aspx?nValor1=1&nValor2=6530&nValor3=100658&param1=NRTC&strTipM=TC",
    },
    {
        "code": "CR-TAX-7092",
        "category": "Hacienda",
        "title": "Ley del Impuesto sobre la Renta",
        "norm_type": "Ley",
        "number": "7092",
        "issuer": "Asamblea Legislativa",
        "date": "1988-04-21",
        "summary": "Regula el impuesto sobre utilidades y rentas de fuente costarricense, gastos deducibles, pagos parciales, retenciones y obligaciones conexas.",
        "erp_relevance": "Relacionada con D-101, cierre anual, gastos deducibles, conciliacion fiscal y analisis de resultados.",
        "keywords": ["renta", "utilidades", "deducible", "d101", "retenciones", "periodo fiscal"],
        "official_url": "https://pgrweb.go.cr/scij/Busqueda/Normativa/Normas/nrm_texto_completo.aspx?nValor1=1&nValor2=10969&nValor3=148975&param1=NRTC&strTipM=TC",
    },
    {
        "code": "CR-TAX-43198-H",
        "category": "Hacienda",
        "title": "Reglamento de la Ley del Impuesto sobre la Renta",
        "norm_type": "Decreto Ejecutivo",
        "number": "43198-H",
        "issuer": "Poder Ejecutivo / Ministerio de Hacienda",
        "date": "2021-07-22",
        "summary": "Desarrolla reglas reglamentarias de renta, administracion, fiscalizacion y obligaciones asociadas.",
        "erp_relevance": "Referencia para clasificacion de gastos, soporte fiscal, comprobantes y controles del cierre.",
        "keywords": ["reglamento renta", "hacienda", "gastos", "fiscalizacion", "comprobantes"],
        "official_url": "https://pgrweb.go.cr/scij/Busqueda/Normativa/Normas/nrm_texto_completo.aspx?nValor1=1&nValor2=95992&nValor3=139872&param1=NRTC&strTipM=TC",
    },
    {
        "code": "CR-VAT-6826",
        "category": "Hacienda",
        "title": "Ley de Impuesto al Valor Agregado",
        "norm_type": "Ley",
        "number": "6826",
        "issuer": "Asamblea Legislativa",
        "date": "1982-11-08",
        "summary": "Regula el IVA aplicable a venta de bienes y prestacion de servicios en Costa Rica, creditos fiscales, tarifas y obligaciones.",
        "erp_relevance": "Base legal para IVA, D-104/D-150, libro de ventas/compras, credito fiscal y conciliacion tributaria.",
        "keywords": ["iva", "valor agregado", "credito fiscal", "ventas", "servicios", "d104", "d150"],
        "official_url": "https://pgrweb.go.cr/SCIJ/Busqueda/Normativa/Normas/nrm_norma.aspx?nValor1=1&nValor2=32526&nValor3=34312&param1=NRM&strTipM=VA",
    },
    {
        "code": "CR-EINV-44739-H",
        "category": "Hacienda",
        "title": "Reglamento de comprobantes electronicos para efectos tributarios",
        "norm_type": "Decreto Ejecutivo",
        "number": "44739-H",
        "issuer": "Poder Ejecutivo / Ministerio de Hacienda",
        "date": "2024-10-02",
        "summary": "Regula comprobantes electronicos autorizados por Tributacion, XML, requisitos, eficacia juridica, fuerza probatoria y sistemas de emision.",
        "erp_relevance": "Base para XML, factura electronica, validacion de Hacienda, soportes fiscales y evidencia digital.",
        "keywords": ["comprobantes electronicos", "xml", "factura electronica", "hacienda", "recibo electronico", "fuerza probatoria"],
        "official_url": "https://pgrweb.go.cr/scij/Busqueda/Normativa/Normas/nrm_texto_completo.aspx?nValor1=1&nValor2=103206",
    },
    {
        "code": "CR-EINV-DGT-0027-2024",
        "category": "Hacienda",
        "title": "Disposiciones tecnicas de comprobantes electronicos version 4.4",
        "norm_type": "Resolucion",
        "number": "DGT 0027-2024",
        "issuer": "Direccion General de Tributacion",
        "date": "2024-11-13",
        "summary": "Anexos y estructuras tecnicas para emision de comprobantes electronicos, incluyendo version 4.4.",
        "erp_relevance": "Referencia tecnica para XML, estructura de comprobantes, validaciones y campos obligatorios del ERP.",
        "keywords": ["xml", "version 4.4", "estructura", "comprobantes electronicos", "factura", "tributacion"],
        "official_url": "https://pgrweb.go.cr/scij/Busqueda/Normativa/Normas/nrm_articulo.aspx?nValor1=1&nValor2=103276&nValor3=144883&nValor5=20&param1=NRA&strTipM=FA",
    },
    {
        "code": "CR-HACIENDA-NORMATIVA",
        "category": "Hacienda",
        "title": "Ministerio de Hacienda - Normativa tributaria",
        "norm_type": "Portal oficial",
        "number": "Portal",
        "issuer": "Ministerio de Hacienda",
        "date": "",
        "summary": "Portal oficial para normativa, resoluciones, avisos, comprobantes electronicos y recursos tributarios publicados por Hacienda.",
        "erp_relevance": "Acceso rapido a normativa operativa actualizada y avisos oficiales de implementacion.",
        "keywords": ["hacienda", "normativa", "resoluciones", "avisos", "tributacion", "portal"],
        "official_url": "https://www.hacienda.go.cr/",
    },
]


@router.get("")
def list_legal_library(
    category: str | None = None,
    q: str | None = Query(None, min_length=1),
):
    query = (q or "").strip().lower()
    selected_category = (category or "").strip().lower()
    rows = []
    for item in LEGAL_ITEMS:
        if selected_category and selected_category not in {"todos", "all"}:
            if item["category"].lower() != selected_category:
                continue
        haystack = " ".join(
            [
                item["code"],
                item["category"],
                item["title"],
                item["norm_type"],
                item["number"],
                item["issuer"],
                item["summary"],
                item["erp_relevance"],
                " ".join(item["keywords"]),
            ]
        ).lower()
        if query and query not in haystack:
            continue
        rows.append(item)
    rows.sort(key=lambda item: item.get("date") or "0000-00-00", reverse=True)
    categories = sorted({item["category"] for item in LEGAL_ITEMS})
    return {"status": "ok", "categories": categories, "count": len(rows), "data": rows}
