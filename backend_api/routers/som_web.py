from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Header, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse
from psycopg2.extras import RealDictCursor

import database
from routers.user_admin import MODULES
from services.credit_control import build_credit_decision
from services.tenanting import company_code


router = APIRouter(tags=["SOM Web"])

_ROOT = Path(__file__).resolve().parents[1]
_ASSETS = _ROOT / "assets"
_REPO_ASSETS = _ROOT.parent / "assets"
_ASSET_VERSION = "20260917-hide-service-credit-columns-1"

MODULES_WEB = [
    {"code": "dashboard", "title": "Inicio", "subtitle": "Servicios, facturación, CxC e informes desde agosto en adelante."},
    {"code": "master_data", "title": "Master Data", "subtitle": "Clientes, proveedores, empleados, surveyors, servicios, datos fiscales y datos bancarios."},
    {"code": "servicios", "title": "Servicios", "subtitle": "Registro, edición, surveyors, demoras, cierre y trazabilidad operativa."},
    {"code": "finanzas", "title": "Finanzas", "subtitle": "Facturación, Collections, ITP, bancos, Accounting, fiscal y tarjetas."},
    {"code": "hhrre", "title": "HHRR", "subtitle": "Horas, solicitudes, vacaciones, payroll, colillas, red médica y calculadora."},
    {"code": "comercial", "title": "Comercial", "subtitle": "Cotizaciones, precios, analítica y exportables."},
    {"code": "informes", "title": "Informes", "subtitle": "Draft Survey, bunker, condition, grain, truck y certificados."},
    {"code": "portia", "title": "PORTIA", "subtitle": "Asistente operativo, contable y documental."},
    {"code": "qa_som", "title": "Q&A SOM", "subtitle": "Base de conocimiento por módulo."},
    {"code": "admin_users", "title": "Admin", "subtitle": "Usuarios, permisos, roles y auditoría."},
]

MASTER_DATA_ACTIONS = [
    {"key": "clientes", "label": "+ Cliente", "kind": "create", "entity": "cliente"},
    {"key": "surveyores", "label": "+ Surveyor", "kind": "create", "entity": "surveyor"},
    {"key": "empleados", "label": "+ Empleado", "kind": "create", "entity": "empleado"},
    {"key": "proveedores", "label": "+ Proveedor", "kind": "create", "entity": "proveedor"},
    {"key": "servicios_md", "label": "+ Servicio", "kind": "create", "entity": "servicio"},
    {"key": "puertos", "label": "+ Puerto", "kind": "create", "entity": "puerto"},
    {"key": "export_form", "label": "Exportar form", "kind": "tool", "entity": "forms"},
    {"key": "import_form", "label": "Cargar form", "kind": "tool", "entity": "forms"},
    {"key": "company_fiscal", "label": "Datos fiscales", "kind": "tool", "entity": "fiscal"},
    {"key": "bank_accounts", "label": "Datos bancarios", "kind": "secure", "entity": "banks"},
]

MASTER_DATA_VIEWS = [
    {"key": "clientes", "label": "Clientes", "endpoint": "/clientes?page=1&page_size=100", "primary": ["codigo", "nombrejuridico", "nombrecomercial", "pais", "correo", "telefono"]},
    {"key": "proveedores", "label": "Proveedores", "endpoint": "/proveedores/?page=1&page_size=100", "primary": ["codigo", "nombre", "pais", "correo", "telefono", "activo"]},
    {"key": "empleados", "label": "Empleados", "endpoint": "/empleados/?page=1&page_size=100&include_inactive=true", "primary": ["codigo", "activo", "nombre", "apellidos", "horas_contratadas", "horas_tope_ordinario", "horas_tope_maximo"]},
    {"key": "surveyores", "label": "Surveyors", "endpoint": "/surveyores/?page=1&page_size=100&include_inactive=true", "primary": ["codigo", "activo", "nombre", "apellidos", "correo", "telefono"]},
    {"key": "servicios_md", "label": "Servicios", "endpoint": "/servicios_md/?page=1&page_size=100", "primary": ["codigo", "codigo_prod", "nombre", "costo"]},
    {"key": "puertos", "label": "Puertos", "endpoint": "/cpp/ports?page=1&page_size=100", "primary": ["id", "continente", "pais", "puerto"]},
    {"key": "company_fiscal", "label": "Datos fiscales", "endpoint": "/companies/current", "primary": ["company_code", "company_name", "tax_id", "economic_activity", "billing_email", "address"]},
    {"key": "bank_accounts", "label": "Datos bancarios", "endpoint": "", "primary": ["bank_name", "currency", "iban", "swift_code", "beneficiary_name"]},
]


def _period_start(year: int) -> str:
    return f"{int(year)}-08-01"


def _period_end(year: int) -> str:
    return f"{int(year) + 1}-01-01"


def _scalar(cur, sql: str, params: tuple) -> float:
    cur.execute(sql, params)
    row = cur.fetchone()
    if isinstance(row, dict):
        value = next(iter(row.values()), 0)
    else:
        value = row[0] if row else 0
    return float(value or 0)


def _safe_scalar(cur, sql: str, params: tuple) -> float:
    try:
        return _scalar(cur, sql, params)
    except Exception:
        return 0.0


@router.get("/som/catalog")
def som_web_catalog():
    module_labels = {item["code"]: item["label"] for item in MODULES}
    return {
        "modules": [{**item, "label": module_labels.get(item["code"], item["title"])} for item in MODULES_WEB],
        "master_data_actions": MASTER_DATA_ACTIONS,
        "master_data_views": MASTER_DATA_VIEWS,
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }


@router.get("/som/summary")
def som_web_summary(
    anio: int | None = Query(None),
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
):
    selected_year = int(anio or datetime.now().year)
    company = company_code(header_value=x_company_code)
    start = _period_start(selected_year)
    end = _period_end(selected_year)
    conn = database.get_conn()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        services = _scalar(
            cur,
            "SELECT COUNT(*) FROM servicios WHERE company_code=%s AND fecha_inicio >= %s AND fecha_inicio < %s",
            (company, start, end),
        )
        invoiced = _scalar(
            cur,
            "SELECT COALESCE(SUM(total),0) FROM invoicing WHERE company_code=%s AND fecha_emision >= %s AND fecha_emision < %s",
            (company, start, end),
        )
        ar = _scalar(
            cur,
            "SELECT COALESCE(SUM(saldo_pendiente),0) FROM collections WHERE company_code=%s AND saldo_pendiente > 0",
            (company,),
        )
        reports = _scalar(
            cur,
            "SELECT COUNT(*) FROM servicios WHERE company_code=%s AND fecha_inicio >= %s AND fecha_inicio < %s AND COALESCE(num_informe,'')<>''",
            (company, start, end),
        )
        cur.execute(
            """
            SELECT TO_CHAR(fecha_inicio, 'YYYY-MM') AS month,
                   COUNT(*) AS services,
                   COALESCE(SUM(valor_factura),0) AS invoiced
            FROM servicios
            WHERE company_code=%s
              AND fecha_inicio >= %s
              AND fecha_inicio < %s
            GROUP BY TO_CHAR(fecha_inicio, 'YYYY-MM')
            ORDER BY month
            """,
            (company, start, end),
        )
        monthly = cur.fetchall()
        return {
            "company_code": company,
            "year": selected_year,
            "from": start,
            "kpis": {
                "services": services,
                "invoiced": invoiced,
                "ar": ar,
                "reports": reports,
            },
            "monthly": monthly,
        }
    finally:
        database.release_conn(conn)


@router.get("/som/module-summary")
def som_web_module_summary(
    module: str = Query("dashboard"),
    anio: int | None = Query(None),
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
):
    selected_year = int(anio or datetime.now().year)
    company = company_code(header_value=x_company_code)
    conn = database.get_conn()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        if module == "master_data":
            return {
                "company_code": company,
                "module": module,
                "kpis": [
                    {
                        "label": "Clientes",
                        "value": _safe_scalar(cur, "SELECT COUNT(*) FROM cliente WHERE company_code=%s", (company,)),
                        "hint": "Activos y registrados",
                        "format": "int",
                    },
                    {
                        "label": "Proveedores",
                        "value": _safe_scalar(cur, "SELECT COUNT(*) FROM proveedor WHERE company_code=%s AND COALESCE(activo, TRUE)=TRUE", (company,)),
                        "hint": "Activos",
                        "format": "int",
                    },
                    {
                        "label": "Empleados",
                        "value": _safe_scalar(cur, "SELECT COUNT(*) FROM empleados WHERE company_code=%s AND COALESCE(activo, TRUE)=TRUE", (company,)),
                        "hint": "Activos",
                        "format": "int",
                    },
                    {
                        "label": "Surveyors",
                        "value": _safe_scalar(cur, "SELECT COUNT(*) FROM surveyor WHERE company_code=%s AND COALESCE(activo, TRUE)=TRUE", (company,)),
                        "hint": "Activos",
                        "format": "int",
                    },
                ],
            }
        if module == "servicios":
            start = _period_start(selected_year)
            end = _period_end(selected_year)
            return {
                "company_code": company,
                "module": module,
                "kpis": [
                    {
                        "label": "Servicios",
                        "value": _safe_scalar(cur, "SELECT COUNT(*) FROM servicios WHERE company_code=%s AND fecha_inicio >= %s AND fecha_inicio < %s", (company, start, end)),
                        "hint": "Desde agosto",
                        "format": "int",
                    },
                    {
                        "label": "En operación",
                        "value": _safe_scalar(cur, "SELECT COUNT(*) FROM servicios WHERE company_code=%s AND fecha_inicio >= %s AND fecha_inicio < %s AND estado=%s", (company, start, end, "En Operación")),
                        "hint": "Abiertos",
                        "format": "int",
                    },
                    {
                        "label": "Facturado",
                        "value": _safe_scalar(cur, "SELECT COALESCE(SUM(valor_factura),0) FROM servicios WHERE company_code=%s AND fecha_inicio >= %s AND fecha_inicio < %s", (company, start, end)),
                        "hint": "Servicios",
                        "format": "money",
                    },
                    {
                        "label": "Países",
                        "value": _safe_scalar(cur, "SELECT COUNT(DISTINCT pais) FROM servicios WHERE company_code=%s AND fecha_inicio >= %s AND fecha_inicio < %s AND COALESCE(pais,'')<>''", (company, start, end)),
                        "hint": "Cobertura",
                        "format": "int",
                    },
                ],
            }
        if module == "finanzas":
            open_ar = _safe_scalar(cur, "SELECT COALESCE(SUM(saldo_pendiente),0) FROM collections WHERE company_code=%s AND saldo_pendiente > 0", (company,))
            clients_hold = _safe_scalar(cur, "SELECT COUNT(*) FROM cliente_credito WHERE company_code=%s AND (COALESCE(hold_manual,FALSE)=TRUE OR estado_credito='HOLD')", (company,))
            configured = _safe_scalar(cur, "SELECT COUNT(*) FROM cliente_credito WHERE company_code=%s", (company,))
            return {
                "company_code": company,
                "module": module,
                "kpis": [
                    {"label": "CxC abierta", "value": open_ar, "hint": "Collections", "format": "money"},
                    {"label": "Clientes con credito", "value": configured, "hint": "Configurados", "format": "int"},
                    {"label": "Hold manual", "value": clients_hold, "hint": "Bloqueados", "format": "int"},
                    {"label": "Order-to-Cash", "value": 1, "hint": "Credit activo", "format": "int"},
                ],
            }
        return som_web_summary(selected_year, x_company_code)
    finally:
        database.release_conn(conn)


@router.get("/som/finance/order-to-cash/credit-hold")
def som_web_credit_hold(
    q: str | None = Query(None),
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
):
    company = company_code(header_value=x_company_code)
    conn = database.get_conn()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        params = {"company": company}
        where = "WHERE c.company_code = %(company)s"
        if q and q.strip():
            params["q"] = f"%{q.strip()}%"
            where += """
              AND (
                    c.codigo ILIKE %(q)s
                 OR c.nombrecomercial ILIKE %(q)s
                 OR c.nombrejuridico ILIKE %(q)s
              )
            """
        cur.execute(
            f"""
            SELECT c.codigo, c.nombrecomercial, c.nombrejuridico
            FROM cliente c
            {where}
            ORDER BY COALESCE(c.nombrecomercial, c.nombrejuridico, c.codigo)
            LIMIT 200
            """,
            params,
        )
        rows = []
        for client in cur.fetchall():
            decision = build_credit_decision(company, client["codigo"], projected_amount=0, projected_currency="USD")
            rows.append({
                "codigo": client["codigo"],
                "cliente": client["nombrecomercial"] or client["nombrejuridico"] or client["codigo"],
                "limite": decision.get("credit_limit"),
                "moneda": decision.get("currency"),
                "cxC_abierta": decision.get("open_ar"),
                "disponible": decision.get("available"),
                "estado": decision.get("estado_credito"),
                "hold_manual": decision.get("hold_manual"),
                "decision": decision.get("status"),
                "mensaje": decision.get("message"),
            })
        return {"company_code": company, "data": rows, "total": len(rows)}
    finally:
        database.release_conn(conn)


@router.get("/som", response_class=HTMLResponse)
def som_web_home() -> HTMLResponse:
    year = datetime.now().year
    html = """<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>SOM Web</title>
  <style>
    :root {
      color-scheme: light;
      --ink:#122033; --muted:#607086; --line:#d6e0eb; --soft:#f4f7fb;
      --panel:#fff; --nav:#071f37; --blue:#005da8; --green:#087a52;
      --amber:#a66700; --red:#b42318; --shadow:0 12px 30px rgba(15,31,53,.10);
    }
    * { box-sizing:border-box; }
    body { margin:0; font-family:Inter,Segoe UI,Roboto,Arial,sans-serif; color:var(--ink); background:#eef3f8; }
    button,input,select { font:inherit; }
    button { border:0; background:var(--blue); color:#fff; border-radius:7px; height:38px; padding:0 13px; cursor:pointer; }
    button.secondary { background:#fff; color:var(--ink); border:1px solid var(--line); }
    button.dark { background:#111827; }
    button.green { background:#00703c; }
    button.brown { background:#6f4e00; }
    button.gray { background:#4b5563; }
    input,select { width:100%; min-width:0; height:38px; border:1px solid var(--line); border-radius:7px; padding:0 11px; background:#fff; color:var(--ink); }
    select { text-overflow:ellipsis; }
    .login { min-height:100vh; display:grid; grid-template-columns:minmax(380px,38vw) minmax(0,1fr); background:#fff; }
    .login-card { width:100%; max-width:520px; min-height:100vh; margin:0 auto; padding:48px 56px; display:flex; flex-direction:column; justify-content:center; gap:16px; overflow:hidden; }
    .login-card h1 { margin:0; font-size:30px; color:#003a75; }
    .login-card p { margin:0 0 8px; color:var(--muted); line-height:1.45; }
    .form { display:grid; gap:12px; width:min(100%,420px); min-width:0; }
    .remember { display:flex; gap:8px; align-items:center; color:#334155; font-size:13px; }
    .remember input { width:16px; height:16px; }
    .hero-logo { min-height:100vh; background:#073659; display:flex; align-items:center; justify-content:center; padding:32px; overflow:hidden; }
    .hero-logo img { width:min(82%,780px); height:min(82vh,780px); object-fit:contain; object-position:center; background:white; border-radius:12px; padding:0; box-shadow:0 24px 70px rgba(0,0,0,.18); }
    .qr { max-width:220px; border:1px solid var(--line); border-radius:8px; padding:8px; background:white; }
    .app { min-height:100vh; display:grid; grid-template-columns:280px 1fr; }
    aside { background:var(--nav); color:white; padding:18px 16px; display:flex; flex-direction:column; gap:14px; }
    .brand { display:flex; gap:12px; align-items:center; padding:6px; }
    .brand img { width:50px; height:50px; object-fit:contain; background:white; border-radius:8px; padding:5px; }
    .brand strong { display:block; font-size:18px; }
    .brand span { color:#b9c7d6; font-size:12px; }
    .nav { display:grid; gap:7px; overflow:auto; }
    .nav button { text-align:left; background:transparent; color:#dce8f4; border:1px solid rgba(255,255,255,.09); }
    .nav button.active,.nav button:hover { background:rgba(255,255,255,.1); }
    .side-foot { margin-top:auto; display:grid; gap:8px; }
    main { padding:20px 20px 30px; min-width:0; }
    header { display:flex; justify-content:space-between; gap:16px; align-items:flex-start; margin-bottom:14px; }
    h1 { margin:0; font-size:25px; letter-spacing:0; }
    h2 { margin:0; font-size:17px; }
    .muted { color:var(--muted); }
    .toolbar { display:flex; gap:8px; align-items:center; flex-wrap:wrap; justify-content:flex-end; }
    .grid { display:grid; gap:12px; }
    .kpis { grid-template-columns:repeat(4,minmax(0,1fr)); }
    .card { background:var(--panel); border:1px solid var(--line); border-radius:8px; box-shadow:var(--shadow); }
    .kpi { padding:14px; min-height:96px; }
    .kpi span { display:block; color:var(--muted); font-size:12px; text-transform:uppercase; }
    .kpi strong { display:block; font-size:24px; margin-top:10px; }
    .panel { padding:14px; }
    .panel-head { display:flex; justify-content:space-between; gap:12px; align-items:center; margin-bottom:12px; }
    .home-grid { grid-template-columns:repeat(4,minmax(0,1fr)); margin-top:12px; }
    .home-card { padding:16px; min-height:118px; cursor:pointer; border-top:3px solid var(--blue); }
    .home-card:nth-child(2) { border-top-color:var(--green); }
    .home-card:nth-child(3) { border-top-color:var(--amber); }
    .home-card:nth-child(4) { border-top-color:#029fcf; }
    .md-actions { display:flex; flex-wrap:wrap; gap:10px; margin:12px 0 14px; }
    .filters { display:flex; flex-wrap:wrap; gap:10px; align-items:center; padding:12px; margin-bottom:12px; }
    .filters.service-filters { display:grid; grid-template-columns:1.4fr repeat(4,minmax(130px,1fr)) auto auto; align-items:end; }
    .form-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px; }
    .form-grid label { display:grid; gap:5px; color:#334155; font-size:13px; }
    .form-grid .wide { grid-column:1/-1; }
    .form-grid textarea { width:100%; min-height:78px; border:1px solid var(--line); border-radius:7px; padding:9px 11px; font:inherit; resize:vertical; }
    .service-actions { display:flex; flex-wrap:wrap; gap:8px; margin:12px 0; }
    .service-actions button { height:34px; }
    .tabs { display:flex; flex-wrap:wrap; gap:8px; margin:12px 0; }
    .tabs button { background:#fff; color:var(--ink); border:1px solid var(--line); }
    .tabs button.active { background:var(--blue); color:#fff; border-color:var(--blue); }
    .split-panels { display:grid; grid-template-columns:minmax(0,1fr); gap:12px; }
    .subtabs { display:inline-flex; gap:4px; padding:4px; border:1px solid var(--line); border-radius:8px; background:#f7fafc; margin:2px 0 12px; }
    .subtabs button { height:34px; background:transparent; color:var(--ink); border-radius:6px; padding:0 16px; }
    .subtabs button.active { background:var(--blue); color:#fff; }
    .billing-pane { min-width:0; padding-top:4px; }
    .section-head { display:flex; justify-content:space-between; gap:12px; align-items:flex-end; margin-bottom:12px; padding-bottom:8px; border-bottom:1px solid #edf2f7; }
    .section-head h3 { margin:0; font-size:16px; }
    .finance-filter-row { display:grid; grid-template-columns:minmax(220px,300px) repeat(4,minmax(120px,170px)) max-content max-content; gap:10px; align-items:end; margin:10px 0 12px; }
    .finance-filter-row.compact { grid-template-columns:minmax(260px,420px) max-content max-content; }
    .finance-filter-row button { justify-self:start; min-width:92px; padding:0 16px; }
    .finance-toolbar { display:flex; flex-wrap:wrap; gap:8px; margin:8px 0 12px; }
    .finance-toolbar button { height:34px; }
    .service-selected { background:#eaf6ff; }
    .pick-col { width:42px; min-width:42px; text-align:center; }
    .row-pick { appearance:none; -webkit-appearance:none; width:20px; height:20px; border:1.5px solid #8b95a5; border-radius:50%; background:#fff; display:inline-grid; place-content:center; margin:0; vertical-align:middle; cursor:pointer; }
    .row-pick::before { content:""; width:10px; height:10px; border-radius:50%; transform:scale(0); transition:transform .08s ease-in-out; background:var(--blue); }
    .row-pick:checked { border-color:var(--blue); background:#eff7ff; }
    .row-pick:checked::before { transform:scale(1); }
    .service-warning { background:#fff3f3; }
    .badge { display:inline-flex; align-items:center; min-height:24px; border:1px solid var(--line); border-radius:999px; padding:2px 9px; background:#f8fafc; font-size:12px; }
    .badge.open { border-color:#b7d8ff; color:#005da8; background:#edf7ff; }
    .badge.closed { border-color:#bde5cd; color:#087a52; background:#effaf4; }
    .badge.cancel { border-color:#f3c4c0; color:#b42318; background:#fff3f1; }
    .modal-backdrop { position:fixed; inset:0; z-index:20; background:rgba(5,18,32,.44); display:flex; align-items:center; justify-content:center; padding:22px; }
    .modal { width:min(1120px,96vw); max-height:92vh; overflow:auto; background:#fff; border:1px solid var(--line); border-radius:9px; box-shadow:0 26px 90px rgba(0,0,0,.24); padding:16px; }
    .modal.small { width:min(560px,94vw); }
    .modal-head { display:flex; justify-content:space-between; gap:12px; align-items:center; margin-bottom:14px; }
    .surveyors-box { border:1px solid var(--line); border-radius:8px; padding:10px; background:#fbfdff; }
    .surveyor-line { display:grid; grid-template-columns:minmax(220px,1fr) 140px 34px; gap:8px; align-items:center; margin-top:8px; }
    .pager { display:flex; justify-content:space-between; gap:12px; align-items:center; margin-top:10px; }
    .export-note { font-size:12px; color:var(--muted); }
    .view-grid { grid-template-columns:repeat(4,minmax(0,1fr)); }
    .view-card { padding:15px; cursor:pointer; min-height:86px; border-top:3px solid var(--blue); }
    .view-card:hover { outline:2px solid rgba(0,93,168,.18); }
    .master-empty { margin-top:12px; }
    .workspace { margin-top:12px; }
    .table-wrap { overflow:auto; border:1px solid var(--line); border-radius:8px; max-height:520px; }
    table { border-collapse:collapse; width:100%; min-width:850px; font-size:13px; }
    th,td { border-bottom:1px solid #e6edf4; padding:8px 10px; text-align:left; white-space:nowrap; }
    th { background:#f0f4f8; position:sticky; top:0; z-index:1; }
    .warn-row td { background:#fff8e6; color:#6f4a00; }
    .bar-row { display:grid; grid-template-columns:130px 1fr auto; gap:9px; align-items:center; font-size:13px; margin-bottom:9px; }
    .track { height:13px; background:#e7eef6; border-radius:999px; overflow:hidden; }
    .fill { height:100%; background:linear-gradient(90deg,var(--blue),#029fcf); min-width:2px; }
    .status { padding:10px 12px; background:var(--soft); border-radius:8px; color:var(--muted); }
    .error { color:var(--red); }
    .hidden { display:none !important; }
    @media(max-width:980px) {
      .login,.app,.kpis,.home-grid,.view-grid { grid-template-columns:1fr; }
      .login-card { max-width:none; padding:34px 24px; }
      .hero-logo { min-height:300px; padding:22px; }
      .hero-logo img { width:min(88%,520px); height:250px; }
      .form-grid { grid-template-columns:1fr; }
      .filters.service-filters { grid-template-columns:1fr; }
      .finance-filter-row,.finance-filter-row.compact { grid-template-columns:1fr; }
      .surveyor-line { grid-template-columns:1fr; }
      aside { min-height:auto; }
      header { flex-direction:column; }
    }
  </style>
</head>
<body>
  <section id="loginView" class="login">
    <div class="login-card">
      <h1>ERP-SOM Web</h1>
      <p>Ingresa con tu usuario de SOM y guarda este dispositivo para entrar luego con Windows Hello, passkey, iris o huella cuando el navegador lo permita.</p>
      <div id="loginForm" class="form">
        <input id="user" autocomplete="username" placeholder="Usuario" />
        <input id="pass" autocomplete="current-password" placeholder="Contraseña" type="password" />
        <select id="loginCompany"></select>
        <label class="remember"><input id="rememberDevice" type="checkbox" /> Guardar credenciales en este dispositivo</label>
        <button id="loginBtn">Ingresar</button>
        <button id="bioBtn" class="secondary" type="button">Entrar con Windows Hello / passkey</button>
        <div id="loginMsg" class="muted"></div>
      </div>
      <div id="totpForm" class="form hidden">
        <img id="qr" class="qr hidden" alt="QR Authenticator" />
        <input id="code" inputmode="numeric" autocomplete="one-time-code" placeholder="Código Authenticator" />
        <button id="totpBtn">Validar código</button>
        <button id="backLogin" class="secondary">Volver</button>
        <div id="totpMsg" class="muted"></div>
      </div>
    </div>
    <div class="hero-logo"><img src="/som/logo/msl?v={asset_version}" alt="MSL" /></div>
  </section>

  <section id="appView" class="app hidden">
    <aside>
      <div class="brand">
        <img id="brandLogo" src="/som/logo/msl?v={asset_version}" alt="Logo" />
        <div><strong>SOM Web</strong><span id="sessionText">Sesión activa</span></div>
      </div>
      <div class="nav" id="moduleNav"></div>
      <div class="side-foot">
        <select id="company"></select>
        <button id="setupPasskey" class="secondary">Configurar Windows Hello / passkey</button>
        <button id="logout" class="secondary">Cerrar sesión</button>
      </div>
    </aside>
    <main>
      <header>
        <div>
          <h1 id="pageTitle">Inicio</h1>
          <div id="pageSubtitle" class="muted">Servicios, facturación, CxC e informes.</div>
        </div>
        <div class="toolbar">
          <select id="companyTop"></select>
          <select id="year"></select>
          <button id="refresh">Actualizar</button>
        </div>
      </header>
      <section class="grid kpis">
        <div class="card kpi"><span id="kpiLabel1">Servicios</span><strong id="kpiValue1">-</strong><small id="kpiHint1">Desde agosto</small></div>
        <div class="card kpi"><span id="kpiLabel2">Facturación</span><strong id="kpiValue2">-</strong><small id="kpiHint2">Desde agosto</small></div>
        <div class="card kpi"><span id="kpiLabel3">CxC</span><strong id="kpiValue3">-</strong><small id="kpiHint3">Saldo pendiente</small></div>
        <div class="card kpi"><span id="kpiLabel4">Informes</span><strong id="kpiValue4">-</strong><small id="kpiHint4">Desde agosto</small></div>
      </section>
      <section id="content"></section>
    </main>
  </section>

  <script>
    const DEFAULT_COMPANIES = [
      { company_code:"MSL-CR", company_name:"MSL MARINE SURVEYORS AND LOGISTICS GROUP SRL" },
      { company_code:"MCI-CR", company_name:"MSL MARINE CLAIMS RISK & INTELLIGENCE" }
    ];
    const intFmt = new Intl.NumberFormat("en-US", { maximumFractionDigits:0 });
    const moneyFmt = new Intl.NumberFormat("en-US", { notation:"compact", maximumFractionDigits:1 });
    const $ = id => document.getElementById(id);
    const esc = value => String(value ?? "").replace(/[&<>"']/g, ch => ({ "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;" }[ch]));
    const SESSION_KEY = "somWebSession";
    const PASSKEY_KEY = "somWebPasskey";
    const SAVED_LOGIN_KEY = "somWebSavedLogin";
    const rememberedSession = JSON.parse(localStorage.getItem(SESSION_KEY) || "null");
    let session = null;
    let pendingUser = null;
    let pendingAction = null;
    let catalog = { modules:[], master_data_actions:[], master_data_views:[] };
    let currentModule = "dashboard";
    let selectedMasterView = null;
    let currentRows = [];
    let bankAccessToken = "";
    let bankRows = [];
    let serviceRows = [];
    let serviceMeta = {};
    let serviceSurveyorCatalog = [];
    let servicePage = 1;
    let serviceTotal = 0;
    let selectedServiceIndex = null;
    let selectedServiceIndexes = new Set();
    let financeTab = "finance-home";
    let billableRows = [];
    let billingRows = [];
    let advanceServiceRows = [];
    let selectedBillableIndex = null;
    let selectedBillingIndex = null;
    let selectedBillableIndexes = new Set();
    let selectedBillingIndexes = new Set();
    let billingPane = "billables";
    let creditRows = [];
    let selectedCreditIndex = null;
    let selectedCreditIndexes = new Set();
    let collectionRows = [];
    let selectedCollectionIndex = null;
    let selectedCollectionIndexes = new Set();
    let collectionPage = 1;
    let collectionTotal = 0;
    let collectionClientesLoaded = false;
    let collectionClientes = [];
    let bankRowsWeb = [];
    let selectedBankIndex = null;
    let selectedBankIndexes = new Set();
    let bankStatementRows = [];
    let selectedBankStatementId = null;
    let selectedBankStatementIds = new Set();
    let bankStatementLineRows = [];
    let selectedBankLineIndex = null;
    let selectedBankLineIndexes = new Set();
    let selectedGenericFinanceIndexes = new Set();
    let itpRows = [];
    let selectedItpIndex = null;
    let selectedItpIndexes = new Set();
    let itpBiweeklyRows = [];
    let selectedPaidInvoiceIndexes = new Set();
    let disputeRows = [];
    let disputeHistoryRows = [];
    let selectedDisputeIndex = null;
    let selectedDisputeIndexes = new Set();
    let portRows = [];
    let financeClientes = [];
    let financeClienteRows = [];
    const DISPUTE_STATUSES = ["New","In process","Process by Sales","Process by RTR","Process by Invoicing","Process by Collections","Process by Bank","Process by Disputes","Written Off","Resolved"];
    const SERVICE_COLUMNS = [
      "consec","tipo","estado","num_informe","buque_contenedor","cliente","contacto","detalle",
      "continente","pais","puerto","operacion","surveyor","honorarios","costo_operativo",
      "costo_tarjetas","fecha_inicio","hora_inicio","fecha_fin","hora_fin","demoras","duracion",
      "factura","valor_factura","fecha_factura","terminos_pago","fecha_vencimiento","dias_vencido"
    ];
    const SERVICE_HIDDEN_COLUMNS = new Set(["credit_status","credit_release_by","credit_release_at","credit_decision"]);
    const visibleServiceColumns = () => SERVICE_COLUMNS.filter(col => !SERVICE_HIDDEN_COLUMNS.has(col));

    const MASTER_CONFIG = {
      clientes: {
        title:"Cliente",
        endpoint:"/clientes",
        add:"/clientes/add",
        update:"/clientes/update",
        ultimo:"/clientes/ultimo",
        suffix:"C",
        codeKey:"Codigo",
        methodKeys:"upperClient",
        fields:[
          ["Codigo","Código","text","",true],["NombreJuridico","Nombre jurídico","text","",true],
          ["NombreComercial","Nombre comercial","text","",true],["Pais","País","text","Costa Rica",false],
          ["Correo","Correo","email","",false],["Telefono","Teléfono","text","",false],
          ["CedulaJuridicaVAT","Cédula jurídica / VAT","text","",false],["ActividadEconomica","Actividad económica","text","",false],["Prefijo","Prefijo","text","",false],
          ["Provincia","Provincia","text","",false],["Canton","Cantón","text","",false],
          ["Distrito","Distrito","text","",false],["FechaDePago","Fecha de pago","date","",false],
          ["ContactoPrincipal","Contacto principal","text","",false],["ContactoSecundario","Contacto secundario","text","",false],
          ["DireccionExacta","Dirección exacta","textarea","",false],["Comentarios","Comentarios","textarea","",false]
        ]
      },
      proveedores: {
        title:"Proveedor",
        endpoint:"/proveedores",
        add:"/proveedores/add",
        update:"/proveedores/update",
        ultimo:"/proveedores/ultimo",
        suffix:"P",
        codeKey:"Codigo",
        fields:[
          ["Codigo","Código","text","",true],["Activo","Activo","checkbox",true,false],
          ["Nombre","Nombre","text","",true],["Apellidos","Apellidos","text","",false],
          ["NombreComercial","Nombre comercial","text","",false],["Cedula","Cédula / VAT","text","",false],
          ["Pais","País","text","Costa Rica",false],["Provincia","Provincia","text","",false],
          ["Canton","Cantón","text","",false],["Distrito","Distrito","text","",false],
          ["Prefijo","Prefijo","text","",false],["Telefono","Teléfono","text","",false],
          ["Correo","Correo","email","",false],["TerminosPago","Términos pago","number","30",false],
          ["Banco","Banco","text","",false],["CuentaIBAN","Cuenta IBAN","text","",false],
          ["SwiftCode","Swift Code","text","",false],["UID","UID","text","",false],
          ["DireccionBanco","Dirección banco","textarea","",false],["DireccionExacta","Dirección exacta","textarea","",false],
          ["TipoProveeduria","Tipo proveeduría","text","",false],["Comentarios","Comentarios","textarea","",false]
        ]
      },
      empleados: {
        title:"Empleado",
        endpoint:"/empleados",
        add:"/empleados/add",
        update:"/empleados/update",
        codeKey:"codigo",
        fields:[
          ["codigo","Código","text","AUTO",true],["activo","Activo","checkbox",true,false],
          ["nombre","Nombre","text","",true],["apellidos","Apellidos","text","",true],
          ["estado_civil","Estado civil","text","",false],["genero","Género","text","",false],
          ["nacionalidad","Nacionalidad","text","Costarricense",false],["prefijo","Prefijo","text","",false],
          ["telefono","Teléfono","text","",false],["provincia","Provincia","text","",false],
          ["canton","Cantón","text","",false],["distrito","Distrito","text","",false],
          ["direccion","Dirección","textarea","",false],["jornada","Jornada","text","",false],
          ["salario","Salario","number","",false],["horas_contratadas","Horas pactadas","number","",false],
          ["horas_tope_ordinario","Tope ordinario","number","",false],["horas_tope_maximo","Tope máximo","number","",false],
          ["tarifa_hora_extra","Tarifa hora extra","number","",false],["pago_minimo_garantizado","Pago mínimo garantizado","checkbox",false,false],
          ["pago","Forma de pago","text","",false],["banco","Banco","text","",false],
          ["cuenta_iban","Cuenta IBAN","text","",false],["moneda","Moneda","text","CRC",false],
          ["enfermedades","Enfermedades","textarea","",false],["contacto_emergencia","Contacto emergencia","text","",false],
          ["telefono_emergencia","Teléfono emergencia","text","",false],["activo1","Activo 1","text","",false],
          ["marca1","Marca 1","text","",false],["serial1","Serial 1","text","",false],
          ["activo2","Activo 2","text","",false],["marca2","Marca 2","text","",false],
          ["serial2","Serial 2","text","",false],["activo3","Activo 3","text","",false],
          ["marca3","Marca 3","text","",false],["serial3","Serial 3","text","",false]
        ]
      },
      surveyores: {
        title:"Surveyor",
        endpoint:"/surveyores",
        add:"/surveyores/add",
        update:"/surveyores/update",
        ultimo:"/surveyores/ultimo",
        suffix:"S",
        codeKey:"codigo",
        fields:[
          ["codigo","Código","text","",true],["activo","Activo","checkbox",true,false],
          ["nombre","Nombre","text","",true],["apellidos","Apellidos","text","",false],
          ["email","Correo","email","",false],["estado_civil","Estado civil","text","",false],
          ["genero","Género","text","",false],["nacionalidad","Nacionalidad","text","Costarricense",false],
          ["prefijo","Prefijo","text","",false],["telefono","Teléfono","text","",false],
          ["provincia","Provincia","text","",false],["canton","Cantón","text","",false],
          ["distrito","Distrito","text","",false],["direccion","Dirección","textarea","",false],
          ["jornada","Jornada","text","",false],["puerto","Puerto","text","",false],
          ["operacion","Operación","text","",false],["honorario","Honorario","number","",false],
          ["pago","Forma de pago","text","",false],["banco","Banco","text","",false],
          ["direccion_banco","Dirección banco","textarea","",false],["cuenta_iban","Cuenta IBAN","text","",false],
          ["moneda","Moneda","text","USD",false],["swift","Swift","text","",false],
          ["uid","UID","text","",false],["enfermedades","Enfermedades","textarea","",false],
          ["contacto_emergencia","Contacto emergencia","text","",false],["telefono_emergencia","Teléfono emergencia","text","",false]
        ]
      },
      servicios_md: {
        title:"Servicio",
        endpoint:"/servicios_md",
        add:"/servicios_md/add",
        update:"/servicios_md/update",
        ultimo:"/servicios_md/ultimo",
        suffix:"SV",
        codeKey:"codigo",
        fields:[
          ["codigo","Código","text","",true],["codigo_prod","Código producto","text","",false],
          ["nombre","Nombre","text","",true],["costo","Costo","number","0",false]
        ]
      },
      puertos: {
        title:"Puerto",
        endpoint:"/cpp/ports",
        add:"/cpp/ports",
        update:"/cpp/ports/{id}",
        codeKey:"id",
        fields:[
          ["continente","Continente","text","",true],
          ["pais","País","text","",true],
          ["puerto","Puerto","text","",true]
        ]
      },
      company_fiscal: {
        title:"Datos fiscales",
        endpoint:"/companies",
        add:null,
        update:"/companies/{company}/",
        codeKey:"company_code",
        fields:[
          ["company_code","Código empresa","text","",true],["company_name","Nombre empresa","text","",true],
          ["legal_name","Razón social","text","",false],["trade_name","Nombre comercial","text","",false],
          ["tax_id","Cédula jurídica","text","",false],["economic_activity","Actividad económica","text","",false],
          ["phone","Teléfono","text","",false],["billing_email","Correo facturación","email","",false],
          ["email","Correo general","email","",false],["country","País","text","Costa Rica",false],
          ["province","Provincia","text","",false],["canton","Cantón","text","",false],
          ["district","Distrito","text","",false],["address","Dirección","textarea","",false],
          ["notes","Notas","textarea","",false]
        ]
      }
    };

    const money = value => "$" + moneyFmt.format(Number(value || 0));
    const kpiValue = item => item?.format === "money" ? money(item.value) : intFmt.format(Number(item?.value || 0));
    const headers = (extra={}) => ({
      "Content-Type":"application/json",
      "X-Company-Code": selectedCompany(),
      "X-User": session?.usuario || "",
      "X-Role": session?.rol || "",
      "X-User-Role": session?.rol || "",
      ...extra
    });
    function selectedCompany() {
      return $("companyTop")?.value || $("company")?.value || session?.company || "MSL-CR";
    }

    async function getJSON(path, extraHeaders={}) {
      const resp = await fetch(path, { headers:headers(extraHeaders) });
      if (!resp.ok) throw new Error(`${path} -> ${resp.status}`);
      return resp.json();
    }
    async function postJSON(path, payload) {
      const resp = await fetch(path, { method:"POST", headers:headers(), body:JSON.stringify(payload) });
      if (!resp.ok) {
        let msg = resp.statusText;
        try { msg = (await resp.json()).detail || msg; } catch {}
        throw new Error(msg);
      }
      return resp.json();
    }
    async function sendJSON(method, path, payload, extraHeaders={}) {
      const resp = await fetch(path, { method, headers:headers(extraHeaders), body:payload ? JSON.stringify(payload) : undefined });
      if (!resp.ok) {
        let msg = resp.statusText;
        try { msg = (await resp.json()).detail || msg; } catch {}
        throw new Error(msg);
      }
      return resp.json();
    }
    async function sendForm(path, formData) {
      const h = headers();
      delete h["Content-Type"];
      const resp = await fetch(path, { method:"POST", headers:h, body:formData });
      if (!resp.ok) {
        let msg = resp.statusText;
        try { msg = (await resp.json()).detail || msg; } catch {}
        throw new Error(msg);
      }
      return resp.json();
    }
    function rowsList(value) {
      if (Array.isArray(value)) return value;
      if (Array.isArray(value?.data)) return value.data;
      if (Array.isArray(value?.items)) return value.items;
      return [];
    }
    function firstFromSet(set) {
      const first = set.values().next();
      return first.done ? null : first.value;
    }
    function setIndexSelection(set, index, checked) {
      if (checked) set.add(index);
      else set.delete(index);
      return firstFromSet(set);
    }
    function options(values, selected="", placeholder="Todos") {
      const list = [...new Set(rowsList(values).map(v => String(v ?? "").trim()).filter(Boolean))].sort((a,b) => a.localeCompare(b));
      return `<option value="">${esc(placeholder)}</option>` + list.map(v => `<option value="${esc(v)}"${v === selected ? " selected" : ""}>${esc(v)}</option>`).join("");
    }
    function valueFrom(id) {
      return ($(id)?.value || "").trim();
    }
    function downloadText(filename, text, mime="text/plain;charset=utf-8") {
      const blob = new Blob([text], { type:mime });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    }
    function selectedService() {
      if (selectedServiceIndex === null) selectedServiceIndex = firstFromSet(selectedServiceIndexes);
      return selectedServiceIndex === null ? null : serviceRows[selectedServiceIndex];
    }
    function requireService() {
      const row = selectedService();
      if (!row) alert("Seleccione primero un servicio de la tabla.");
      return row;
    }
    function fillCompanySelect(select) {
      select.innerHTML = "";
      DEFAULT_COMPANIES.forEach(c => {
        const option = document.createElement("option");
        option.value = c.company_code;
        option.textContent = `${c.company_code} | ${c.company_name}`;
        select.appendChild(option);
      });
    }
    function bootSelectors() {
      fillCompanySelect($("loginCompany"));
      fillCompanySelect($("company"));
      fillCompanySelect($("companyTop"));
      for (let y = {year}; y >= {year} - 4; y--) {
        const option = document.createElement("option");
        option.value = String(y);
        option.textContent = String(y);
        $("year").appendChild(option);
      }
      const savedLogin = JSON.parse(localStorage.getItem(SAVED_LOGIN_KEY) || "null");
      const rememberedLogin = savedLogin || (rememberedSession ? { usuario:rememberedSession.usuario, company:rememberedSession.company } : null);
      if (rememberedLogin) {
        $("user").value = rememberedLogin.usuario || "";
        $("loginCompany").value = rememberedLogin.company || "MSL-CR";
        $("rememberDevice").checked = true;
      }
      localStorage.removeItem(SESSION_KEY);
      $("bioBtn").disabled = !window.PublicKeyCredential || !localStorage.getItem(PASSKEY_KEY);
    }
    async function loadCatalog() {
      catalog = await getJSON("/som/catalog").catch(() => ({ modules:[], master_data_actions:[], master_data_views:[] }));
    }
    function canView(code) {
      if (!session) return false;
      const role = String(session.rol || "").toLowerCase();
      if (["admin","master"].includes(role)) return true;
      const perms = session.permissions || {};
      return (session.modules || []).includes(code) || (perms[code] || []).length > 0;
    }
    function showLogin() {
      $("loginView").classList.remove("hidden");
      $("appView").classList.add("hidden");
      $("loginForm").classList.remove("hidden");
      $("totpForm").classList.add("hidden");
    }
    function showApp() {
      $("loginView").classList.add("hidden");
      $("appView").classList.remove("hidden");
      $("sessionText").textContent = `${session.usuario} · ${session.rol}`;
      $("company").value = session.company || "MSL-CR";
      $("companyTop").value = session.company || "MSL-CR";
      renderNav();
      selectModule(currentModule);
    }
    async function login() {
      $("loginMsg").textContent = "Validando...";
      try {
        const data = await postJSON("/auth/mobile/login", { usuario:$("user").value, password:$("pass").value });
        pendingUser = data.usuario || $("user").value;
        pendingAction = data.action;
        if (data.action === "ENROLL_TOTP" && data.qr_base64) {
          $("qr").src = "data:image/png;base64," + data.qr_base64;
          $("qr").classList.remove("hidden");
        } else {
          $("qr").classList.add("hidden");
        }
        $("loginForm").classList.add("hidden");
        $("totpForm").classList.remove("hidden");
        $("totpMsg").textContent = data.action === "ENROLL_TOTP" ? "Escanea el QR y valida el primer código." : "Ingresa tu código Authenticator.";
      } catch (err) {
        $("loginMsg").innerHTML = `<span class="error">${err.message}</span>`;
      }
    }
    async function validateTotp() {
      $("totpMsg").textContent = "Validando código...";
      try {
        const path = pendingAction === "ENROLL_TOTP" ? "/auth/mobile/totp/confirm" : "/auth/mobile/totp/verify";
        const data = await postJSON(path, { usuario:pendingUser, codigo:$("code").value });
        session = { ...data, company:$("loginCompany").value };
        localStorage.setItem(SESSION_KEY, JSON.stringify(session));
        if ($("rememberDevice").checked) {
          localStorage.setItem(SAVED_LOGIN_KEY, JSON.stringify({ usuario:session.usuario, company:session.company }));
        } else {
          localStorage.removeItem(SAVED_LOGIN_KEY);
        }
        $("bioBtn").disabled = !window.PublicKeyCredential || !localStorage.getItem(PASSKEY_KEY);
        await loadCatalog();
        showApp();
      } catch (err) {
        $("totpMsg").innerHTML = `<span class="error">${err.message}</span>`;
      }
    }
    function bytesFromBase64url(value) {
      const text = value.replace(/-/g, "+").replace(/_/g, "/");
      return Uint8Array.from(atob(text + "===".slice((text.length + 3) % 4)), c => c.charCodeAt(0));
    }
    function base64url(bytes) {
      return btoa(String.fromCharCode(...new Uint8Array(bytes))).replace(/\\+/g, "-").replace(/\\//g, "_").replace(/=+$/g, "");
    }
    async function registerDevicePasskey() {
      if (!window.PublicKeyCredential || !session) return;
      const challenge = crypto.getRandomValues(new Uint8Array(32));
      const userId = crypto.getRandomValues(new Uint8Array(16));
      try {
        const cred = await navigator.credentials.create({
          publicKey: {
            challenge,
            rp: { name:"ERP-SOM Web" },
            user: { id:userId, name:session.usuario, displayName:session.usuario },
            pubKeyCredParams:[{ type:"public-key", alg:-7 }, { type:"public-key", alg:-257 }],
            authenticatorSelection:{ userVerification:"required" },
            timeout:60000
          }
        });
        localStorage.setItem(PASSKEY_KEY, JSON.stringify({ id:base64url(cred.rawId), session, usuario:session.usuario, company:session.company }));
        alert("Windows Hello / passkey quedó configurado para este dispositivo.");
        $("bioBtn").disabled = false;
      } catch {
        alert("No se pudo configurar Windows Hello / passkey.");
      }
    }
    async function unlockWithPasskey() {
      const saved = JSON.parse(localStorage.getItem(PASSKEY_KEY) || "null");
      if (!saved || !window.PublicKeyCredential) return;
      $("loginMsg").textContent = "Validando dispositivo...";
      try {
        await navigator.credentials.get({
          publicKey: {
            challenge:crypto.getRandomValues(new Uint8Array(32)),
            allowCredentials:[{ type:"public-key", id:bytesFromBase64url(saved.id) }],
            userVerification:"required",
            timeout:60000
          }
        });
        pendingUser = saved.usuario || saved.session?.usuario || $("user").value;
        pendingAction = "VERIFY_TOTP";
        $("loginCompany").value = saved.company || saved.session?.company || $("loginCompany").value || "MSL-CR";
        $("loginForm").classList.add("hidden");
        $("totpForm").classList.remove("hidden");
        $("qr").classList.add("hidden");
        $("code").value = "";
        $("totpMsg").textContent = "Windows Hello validado. Ingresa tu código Authenticator para completar el ingreso.";
      } catch (err) {
        $("loginMsg").innerHTML = '<span class="error">No se pudo validar este dispositivo.</span>';
      }
    }
    function renderNav() {
      $("moduleNav").innerHTML = "";
      catalog.modules.filter(m => canView(m.code)).forEach(mod => {
        const btn = document.createElement("button");
        btn.textContent = mod.title;
        btn.className = mod.code === currentModule ? "active" : "";
        btn.onclick = () => selectModule(mod.code);
        $("moduleNav").appendChild(btn);
      });
    }
    function setBrand() {
      $("brandLogo").src = selectedCompany().startsWith("MCI") ? "/som/logo/mci?v={asset_version}" : "/som/logo/msl?v={asset_version}";
    }
    function selectModule(code) {
      currentModule = code;
      selectedMasterView = null;
      setBrand();
      const mod = catalog.modules.find(m => m.code === code) || catalog.modules[0];
      $("pageTitle").textContent = mod?.title || "SOM";
      $("pageSubtitle").textContent = mod?.subtitle || "";
      renderNav();
      if (code === "dashboard") refreshSummary();
      else resetKpisForManualLoad();
      if (code === "dashboard") renderHome();
      else if (code === "master_data") renderMasterData();
      else if (code === "servicios" || code === "servicios_op" || (mod?.title || "").toLowerCase() === "servicios") renderServicios();
      else if (code === "finanzas") renderFinanzas();
      else renderComingSoon(mod);
    }
    async function refreshSummary() {
      try {
        const path = currentModule === "dashboard"
          ? `/som/summary?anio=${$("year").value}`
          : `/som/module-summary?module=${encodeURIComponent(currentModule)}&anio=${$("year").value}`;
        const data = await getJSON(path);
        const items = data.kpis instanceof Array ? data.kpis : [
          { label:"Servicios", value:data.kpis.services || 0, hint:"Desde agosto", format:"int" },
          { label:"Facturación", value:data.kpis.invoiced || 0, hint:"Desde agosto", format:"money" },
          { label:"CxC", value:data.kpis.ar || 0, hint:"Saldo pendiente", format:"money" },
          { label:"Informes", value:data.kpis.reports || 0, hint:"Desde agosto", format:"int" }
        ];
        for (let i = 0; i < 4; i++) {
          const item = items[i] || { label:"-", value:0, hint:"" };
          $(`kpiLabel${i+1}`).textContent = item.label;
          $(`kpiValue${i+1}`).textContent = kpiValue(item);
          $(`kpiHint${i+1}`).textContent = item.hint || "";
        }
        if (currentModule === "dashboard" && data.monthly) renderHomeChart(data.monthly || []);
      } catch {
        for (let i = 1; i <= 4; i++) {
          $(`kpiValue${i}`).textContent = "0";
        }
      }
    }
    function resetKpisForManualLoad() {
      const mod = catalog.modules.find(m => m.code === currentModule);
      const labels = currentModule === "finanzas"
        ? ["CxC abierta", "Clientes con crédito", "Hold manual", "Order-to-Cash"]
        : currentModule === "master_data"
          ? ["Clientes", "Proveedores", "Empleados", "Servicios"]
          : currentModule === "servicios"
            ? ["Servicios", "Abiertos", "Finalizados", "Pendientes"]
            : [mod?.title || "SOM", "Datos", "Acciones", "Estado"];
      for (let i = 0; i < 4; i++) {
        $(`kpiLabel${i+1}`).textContent = labels[i] || "-";
        $(`kpiValue${i+1}`).textContent = "0";
        $(`kpiHint${i+1}`).textContent = "Presione Actualizar";
      }
    }
    function renderHome() {
      $("content").innerHTML = `
        <div class="grid home-grid">
          <div class="card home-card" onclick="selectModule('servicios')"><h2>Servicios</h2><p class="muted">Operaciones activas, edición y cierre.</p></div>
          <div class="card home-card" onclick="selectModule('finanzas')"><h2>Facturación</h2><p class="muted">Billing, Collections, ITP y Accounting.</p></div>
          <div class="card home-card" onclick="selectModule('finanzas')"><h2>CxC</h2><p class="muted">Saldos, aging, pagos y estados de cuenta.</p></div>
          <div class="card home-card" onclick="selectModule('informes')"><h2>Informes</h2><p class="muted">Draft, bunker, condition y certificados.</p></div>
        </div>
        <div class="card panel workspace">
          <div class="panel-head"><h2>Movimiento desde agosto</h2><span class="muted">${$("year").value}</span></div>
          <div id="homeChart" class="status">Cargando...</div>
        </div>`;
    }
    function renderHomeChart(rows) {
      const el = $("homeChart");
      if (!el) return;
      if (!rows.length) {
        el.className = "status";
        el.textContent = "Sin movimiento desde agosto para la empresa seleccionada.";
        return;
      }
      el.className = "";
      const max = Math.max(...rows.map(r => Number(r.invoiced || r.services || 0)), 1);
      el.innerHTML = rows.map(r => {
        const value = Number(r.invoiced || 0);
        return `<div class="bar-row"><div>${r.month}</div><div class="track"><div class="fill" style="width:${Math.max(5, (value || r.services) / max * 100)}%"></div></div><strong>${money(value)}</strong></div>`;
      }).join("");
    }
    function renderFinanzas() {
      if (financeTab === "invoicing") financeTab = "billing";
      $("content").innerHTML = `
        <div class="grid home-grid">
          <div class="card home-card" onclick="openFinanceBlock('order-to-cash')"><h2>Order To Cash</h2><p class="muted">Credit, Invoicing and Billing, Collections, Bank y Disputes.</p></div>
          <div class="card home-card" onclick="openFinanceBlock('invoice-to-pay')"><h2>Invoice To Pay</h2><p class="muted">Obligaciones, proveedores y pagos.</p></div>
          <div class="card home-card" onclick="openFinanceBlock('planning')"><h2>PLN / Planificación</h2><p class="muted">ITP, gastos, pagos, metas, proyectos y ahorros.</p></div>
          <div class="card home-card" onclick="openFinanceBlock('accounting')"><h2>Accounting</h2><p class="muted">Asientos, cierres, fiscal y reportes.</p></div>
        </div>
        <div id="financeWorkspace" class="workspace"></div>`;
      if (["credit","billing","collections","bank","disputes"].includes(financeTab)) {
        openFinanceBlock("order-to-cash");
        switchFinanceTab(financeTab);
      } else if (financeTab && financeTab !== "finance-home") {
        openFinanceBlock(financeTab);
      } else {
        openFinanceBlock("order-to-cash");
      }
    }
    function openFinanceBlock(block) {
      financeTab = block;
      const ws = $("financeWorkspace");
      if (block === "order-to-cash") {
        ws.innerHTML = `
          <div class="card panel">
            <div class="panel-head"><h2>Order To Cash</h2><span class="muted">Seleccione una sección y luego presione Buscar</span></div>
            <div class="tabs">
              <button onclick="switchFinanceTab('credit')">Credit, Order Hold and Release</button>
              <button onclick="switchFinanceTab('billing')">Invoicing and Billing</button>
              <button onclick="switchFinanceTab('collections')">Collections</button>
              <button onclick="switchFinanceTab('bank')">Bank</button>
              <button onclick="switchFinanceTab('disputes')">Disputes</button>
            </div>
            <div id="orderCashWorkspace" class="workspace"><div class="status">Seleccione Credit, Order Hold and Release, Invoicing and Billing, Collections, Bank o Disputes.</div></div>
          </div>`;
        switchFinanceTab("credit");
        return;
      }
      if (block === "invoice-to-pay") {
        ws.innerHTML = `<div class="card panel"><div id="itpWorkspace"></div></div>`;
        renderItpWeb($("itpWorkspace"));
        return;
      }
      if (block === "planning") {
        ws.innerHTML = `<div class="card panel"><div id="planningWorkspace"></div></div>`;
        renderFinancePlanning($("planningWorkspace"));
        return;
      }
      if (block === "accounting") {
        ws.innerHTML = `<div class="card panel"><div id="accountingWorkspace"></div></div>`;
        renderAccountingWeb($("accountingWorkspace"));
      }
    }
    function orderCashWorkspace() {
      return $("orderCashWorkspace") || $("financeWorkspace");
    }
    async function loadGenericFinance(path, targetId) {
      const target = $(targetId);
      selectedGenericFinanceIndexes = new Set();
      target.className = "status";
      target.textContent = "Consultando...";
      try {
        const payload = await getJSON(path);
        const rows = rowsList(payload);
        target.className = "";
        target.innerHTML = renderFinanceGenericTable(rows);
      } catch (err) {
        target.className = "status error";
        target.textContent = err.message;
      }
    }
    function renderFinanceGenericTable(rows) {
      if (!rows.length) return '<div class="status">Sin datos para esta consulta.</div>';
      const cols = Object.keys(rows[0]).filter(k => !String(k).toLowerCase().includes("hash")).slice(0, 12);
      return `<div class="table-wrap"><table><thead><tr><th class="pick-col"></th>${cols.map(c => `<th>${esc(c)}</th>`).join("")}</tr></thead><tbody>${rows.slice(0,100).map((row, idx) => {
        const selected = selectedGenericFinanceIndexes.has(idx);
        return `<tr class="${selected ? "service-selected" : ""}" onclick="toggleGenericFinanceRow(${idx})"><td class="pick-col"><input class="row-pick" type="checkbox" ${selected ? "checked" : ""} onclick="event.stopPropagation(); toggleGenericFinanceRow(${idx}, this.checked)" /></td>${cols.map(c => `<td>${esc(row[c])}</td>`).join("")}</tr>`;
      }).join("")}</tbody></table></div>`;
    }
    function toggleGenericFinanceRow(idx, checked=null) {
      const next = checked === null ? !selectedGenericFinanceIndexes.has(idx) : checked;
      setIndexSelection(selectedGenericFinanceIndexes, idx, next);
      document.querySelectorAll("#itpWorkspace .table-wrap tr, #accountingWorkspace .table-wrap tr, #disputesWorkspace .table-wrap tr").forEach((tr, i) => {
        if (i === 0) return;
        tr.classList.toggle("service-selected", selectedGenericFinanceIndexes.has(i - 1));
        const input = tr.querySelector("input.row-pick");
        if (input) input.checked = selectedGenericFinanceIndexes.has(i - 1);
      });
    }
    function renderAccountingWeb(target) {
      const thisPeriod = new Date().toISOString().slice(0,7);
      target.innerHTML = `
        <div class="panel-head">
          <h2>Accounting</h2>
          <span class="muted">Asientos, balance de comprobación y reportes por consulta manual</span>
        </div>
        <div class="finance-filter-row compact">
          <label>Modo<select id="accMode" onchange="toggleAccountingMode()"><option value="SINGLE">Mes específico</option><option value="RANGE">Rango / periodo fiscal</option></select></label>
          <label id="accPeriodLabel">Periodo<input id="accPeriod" type="month" value="${thisPeriod}" /></label>
          <label id="accFromLabel" style="display:none">Desde<input id="accPeriodFrom" type="month" value="${thisPeriod}" /></label>
          <label id="accToLabel" style="display:none">Hasta<input id="accPeriodTo" type="month" value="${thisPeriod}" /></label>
          <label>Reporte<select id="accReport"><option value="BC">Balance de Comprobación</option><option value="DETALLE_TIPO">Detalle por tipo de cuenta</option><option value="ASIENTOS">Asientos</option><option value="MAYOR">Libro Mayor</option><option value="ESF">Estado de Situación Financiera</option><option value="ER">Estado de Resultados</option><option value="FC">Flujo de Caja</option></select></label>
          <label>Tipo<select id="accAccountType"><option value="">Todos</option><option>ACTIVO</option><option>PASIVO</option><option>PATRIMONIO</option><option>INGRESO</option><option>COSTO</option><option>GASTO</option></select></label>
        </div>
        <div class="finance-filter-row compact">
          <label>Cuenta<input id="accAccountCode" placeholder="Código opcional" /></label>
          <label>Origen<select id="accOrigin"><option value="">Todos</option><option>ITP</option><option>ITP_PAYMENT</option><option>ITP_BIWEEKLY_PAYMENT</option><option>COLLECTIONS</option><option>INVOICING</option><option>MANUAL</option><option>CASH_APP</option></select></label>
          <button onclick="loadAccountingWeb()">Buscar</button>
          <button class="secondary" onclick="clearAccountingWeb()">Limpiar</button>
          <button class="secondary" onclick="exportAccountingReport('xlsx')">Exportar Excel</button>
          <button class="secondary" onclick="exportAccountingReport('pdf')">Exportar PDF</button>
        </div>
        <div id="accountingResult" class="status">Configure filtros y presione Buscar.</div>`;
    }
    function toggleAccountingMode() {
      const range = valueFrom("accMode") === "RANGE";
      $("accPeriodLabel").style.display = range ? "none" : "";
      $("accFromLabel").style.display = range ? "" : "none";
      $("accToLabel").style.display = range ? "" : "none";
    }
    function accountingParams() {
      const params = new URLSearchParams();
      const mode = valueFrom("accMode");
      if (mode === "RANGE") {
        const from = valueFrom("accPeriodFrom");
        const to = valueFrom("accPeriodTo");
        if (from) params.set("period_from", from);
        if (to) params.set("period_to", to);
      } else {
        const period = valueFrom("accPeriod");
        if (period) params.set("period", period);
      }
      const report = valueFrom("accReport") || "BC";
      const type = valueFrom("accAccountType");
      const account = valueFrom("accAccountCode");
      const origin = valueFrom("accOrigin");
      params.set("report", report);
      if (type) params.set("account_type", type);
      if (account) params.set("account_code", account);
      if (origin) params.set("origin", origin);
      params.set("company_code", selectedCompany());
      return params;
    }
    async function loadAccountingWeb() {
      const target = $("accountingResult");
      target.className = "status";
      target.textContent = "Consultando...";
      try {
        const params = accountingParams();
        params.delete("report");
        const payload = await getJSON(`/accounting-lines?${params.toString()}`);
        const rows = rowsList(payload);
        target.className = "";
        if (!rows.length) {
          target.innerHTML = '<div class="status">Sin datos para esta consulta.</div>';
          return;
        }
        target.innerHTML = renderAccountingPreview(rows);
      } catch (err) {
        target.className = "status error";
        target.textContent = err.message;
      }
    }
    function renderAccountingPreview(rows) {
      const report = valueFrom("accReport") || "BC";
      if (report === "BC") return renderAccountingTrialBalance(rows);
      return renderFinanceGenericTable(rows);
    }
    function renderAccountingTrialBalance(rows) {
      const map = new Map();
      rows.forEach(row => {
        const code = String(row.account_code || "").trim();
        if (!code) return;
        const key = `${code}||${row.account_name || ""}||${row.account_type || ""}`;
        const item = map.get(key) || {account_code:code, account_name:row.account_name || "", account_type:row.account_type || "", debit:0, credit:0};
        item.debit += Number(row.debit || 0);
        item.credit += Number(row.credit || 0);
        map.set(key, item);
      });
      const out = [...map.values()].sort((a,b) => a.account_code.localeCompare(b.account_code)).map(row => {
        const balance = row.debit - row.credit;
        const type = String(row.account_type || "").toUpperCase();
        const creditNature = ["PASIVO", "PATRIMONIO", "INGRESO", "LIABILITY", "EQUITY", "REVENUE", "INCOME"].includes(type) || /^[234]/.test(String(row.account_code || ""));
        const naturalBalance = creditNature ? (row.credit - row.debit) : balance;
        return {
          ...row,
          saldo_neto: balance,
          saldo_natural: naturalBalance,
          saldo_deudor: balance > 0 ? balance : 0,
          saldo_acreedor: balance < 0 ? -balance : 0,
          alerta: naturalBalance < -0.005 ? "Saldo contrario" : ""
        };
      });
      const totals = out.reduce((acc,row) => {
        acc.debit += row.debit; acc.credit += row.credit; acc.saldo_neto += row.saldo_neto; acc.saldo_natural += row.saldo_natural; acc.saldo_deudor += row.saldo_deudor; acc.saldo_acreedor += row.saldo_acreedor;
        return acc;
      }, {debit:0, credit:0, saldo_neto:0, saldo_natural:0, saldo_deudor:0, saldo_acreedor:0});
      const fmt = n => Number(n || 0).toLocaleString("en-US", {minimumFractionDigits:2, maximumFractionDigits:2});
      return `<div class="table-wrap"><table><thead><tr><th>Cuenta</th><th>Nombre</th><th>Tipo</th><th>Debe</th><th>Haber</th><th>Saldo neto</th><th>Saldo natural</th><th>Saldo deudor</th><th>Saldo acreedor</th><th>Alerta</th></tr></thead><tbody>
        ${out.map(row => `<tr class="${row.alerta ? "warn-row" : ""}"><td>${esc(row.account_code)}</td><td>${esc(row.account_name)}</td><td>${esc(row.account_type)}</td><td>${fmt(row.debit)}</td><td>${fmt(row.credit)}</td><td>${fmt(row.saldo_neto)}</td><td>${fmt(row.saldo_natural)}</td><td>${fmt(row.saldo_deudor)}</td><td>${fmt(row.saldo_acreedor)}</td><td>${esc(row.alerta)}</td></tr>`).join("")}
        <tr class="total-row"><td colspan="3"><b>Total</b></td><td><b>${fmt(totals.debit)}</b></td><td><b>${fmt(totals.credit)}</b></td><td><b>${fmt(totals.saldo_neto)}</b></td><td><b>${fmt(totals.saldo_natural)}</b></td><td><b>${fmt(totals.saldo_deudor)}</b></td><td><b>${fmt(totals.saldo_acreedor)}</b></td><td></td></tr>
      </tbody></table></div>`;
    }
    function clearAccountingWeb() {
      renderAccountingWeb($("accountingWorkspace"));
    }
    function exportAccountingReport(ext) {
      const params = accountingParams();
      const path = ext === "pdf" ? "/accounting/reports/pdf" : "/accounting/reports/excel";
      window.open(`${path}?${params.toString()}`, "_blank");
    }
    function renderItpWeb(target) {
      target.innerHTML = `
        <div class="panel-head">
          <h2>Invoice To Pay</h2>
          <span class="muted">Obligaciones, proveedores, cargas y pagos por consulta manual</span>
        </div>
        <div class="finance-filter-row compact">
          <label>Tipo obligación<select id="itpObligationType"><option value="">Todos</option><option value="SURVEYOR">Surveyor</option><option value="SUPPLIER">Proveedor</option><option value="MANUAL">Manual</option></select></label>
          <label>Beneficiario<input id="itpPayee" placeholder="Nombre beneficiario" /></label>
          <label>Estado<select id="itpStatus"><option value="ALL">Todos</option><option>PENDING</option><option>PARTIAL</option><option>PAID</option></select></label>
          <button onclick="loadItp()">Buscar</button>
          <button class="secondary" onclick="clearItp()">Limpiar</button>
        </div>
        <div class="finance-filter-row compact">
          <label>Factura desde<input id="itpIssueFrom" type="date" /></label>
          <label>Factura hasta<input id="itpIssueTo" type="date" /></label>
          <label>Vence desde<input id="itpDueFrom" type="date" /></label>
          <label>Vence hasta<input id="itpDueTo" type="date" /></label>
          <label>Pago desde<input id="itpPaymentFrom" type="date" /></label>
          <label>Pago hasta<input id="itpPaymentTo" type="date" /></label>
        </div>
        <div class="finance-toolbar">
          <button class="green" onclick="openItpManualForm()">Registrar obligación manual</button>
          <button onclick="openItpUploadForm()">Cargar factura PDF / XML</button>
          <button onclick="openItpBiweekly()">Obligaciones quincenales</button>
          <button class="green" onclick="openItpPaymentForm()">Aplicar pago</button>
          <button class="brown" onclick="deleteSelectedItp()">Eliminar</button>
          <button class="secondary" onclick="downloadItpExcel()">Exportar Excel</button>
          <button class="secondary" onclick="openItpPaymentReport()">Reporte pagos ITP / presupuesto</button>
          <button class="secondary" onclick="renderFinancePlanning($('itpTable'))">PLN / Planificación</button>
        </div>
        <div id="itpKpis" class="grid kpis hidden"></div>
        <div id="itpAlerts" class="status hidden"></div>
        <div id="itpMsg" class="status hidden"></div>
        <div id="itpTable" class="workspace"><div class="status">Configure filtros y presione Buscar para consultar ITP.</div></div>`;
    }
    function itpParams() {
      const params = new URLSearchParams();
      const pairs = [
        ["obligation_type","itpObligationType"], ["payee","itpPayee"], ["status","itpStatus"],
        ["issue_date_from","itpIssueFrom"], ["issue_date_to","itpIssueTo"],
        ["due_date_from","itpDueFrom"], ["due_date_to","itpDueTo"],
        ["payment_date_from","itpPaymentFrom"], ["payment_date_to","itpPaymentTo"]
      ];
      pairs.forEach(([key,id]) => {
        const value = valueFrom(id);
        if (value) params.set(key, value);
      });
      if (!params.has("status")) params.set("status", "ALL");
      return params.toString();
    }
    async function loadItp() {
      const msg = $("itpMsg");
      const table = $("itpTable");
      selectedItpIndex = null;
      selectedItpIndexes = new Set();
      msg.className = "status";
      msg.textContent = "Consultando ITP...";
      try {
        const [payload, kpis] = await Promise.all([
          getJSON(`/invoice-to-pay/search?${itpParams()}`),
          getJSON("/invoice-to-pay/kpis").catch(() => null)
        ]);
        itpRows = rowsList(payload);
        msg.className = "status hidden";
        renderItpKpis(kpis);
        renderItpTable();
      } catch (err) {
        itpRows = [];
        table.innerHTML = "";
        msg.className = "status error";
        msg.textContent = err.message;
      }
    }
    function renderItpKpis(kpis) {
      const box = $("itpKpis");
      if (!box || !kpis) return;
      box.className = "grid kpis";
      const cards = [
        ["Pending Payables", kpis.pending],
        ["Paid Amount", kpis.paid],
        ["Avg Payment Days", kpis.dpo],
        ["Overdue Amount", kpis.overdue_amount]
      ];
      box.innerHTML = cards.map(([label,value]) => `<div class="card kpi"><span>${esc(label)}</span><strong>${Number(value || 0).toLocaleString("en-US",{minimumFractionDigits:2, maximumFractionDigits:2})}</strong></div>`).join("");
      const alerts = $("itpAlerts");
      if (alerts) {
        alerts.className = "status";
        alerts.textContent = `Pagos próximos: ${Number(kpis.upcoming || 0)} · Pagos vencidos: ${Number(kpis.overdue || 0)}`;
      }
    }
    function renderItpTable() {
      const table = $("itpTable");
      const cols = ["id","payee_name","obligation_type","referencia","issue_date","due_date","vessel","country","operation","currency","total","balance","last_payment_date","status","origin"];
      if (!itpRows.length) {
        table.innerHTML = '<div class="status">Sin obligaciones para esta consulta.</div>';
        return;
      }
      table.innerHTML = `<div class="table-wrap"><table><thead><tr><th class="pick-col"></th>${cols.map(c => `<th>${esc(c.replace(/_/g," "))}</th>`).join("")}</tr></thead><tbody>${itpRows.map((row, idx) => {
        const due = String(row.due_date || "").slice(0,10);
        const overdue = ["PENDING","PARTIAL"].includes(String(row.status || "").toUpperCase()) && due && due < new Date().toISOString().slice(0,10);
        const selected = selectedItpIndexes.has(idx);
        return `<tr class="${selected ? "service-selected" : overdue ? "service-warning" : ""}" onclick="toggleItpRow(${idx})"><td class="pick-col"><input class="row-pick" type="checkbox" ${selected ? "checked" : ""} onclick="event.stopPropagation(); toggleItpRow(${idx}, this.checked)" /></td>${cols.map(c => `<td>${esc(["total","balance"].includes(c) ? Number(row[c] || 0).toLocaleString("en-US",{minimumFractionDigits:2, maximumFractionDigits:2}) : row[c])}</td>`).join("")}</tr>`;
      }).join("")}</tbody></table></div>`;
    }
    function toggleItpRow(idx, checked=null) {
      const next = checked === null ? !selectedItpIndexes.has(idx) : checked;
      selectedItpIndex = setIndexSelection(selectedItpIndexes, idx, next);
      renderItpTable();
    }
    function selectedItpRow() {
      if (selectedItpIndex === null) selectedItpIndex = firstFromSet(selectedItpIndexes);
      return selectedItpIndex === null ? null : itpRows[selectedItpIndex];
    }
    function requireItpRow() {
      const row = selectedItpRow();
      if (!row) alert("Seleccione primero una obligación ITP.");
      return row;
    }
    function clearItp() {
      ["itpObligationType","itpPayee","itpIssueFrom","itpIssueTo","itpDueFrom","itpDueTo","itpPaymentFrom","itpPaymentTo"].forEach(id => { if ($(id)) $(id).value = ""; });
      if ($("itpStatus")) $("itpStatus").value = "ALL";
      itpRows = [];
      selectedItpIndex = null;
      selectedItpIndexes = new Set();
      $("itpTable").innerHTML = '<div class="status">Configure filtros y presione Buscar para consultar ITP.</div>';
      $("itpMsg").className = "status hidden";
      $("itpKpis").className = "grid kpis hidden";
      $("itpAlerts").className = "status hidden";
    }
    function openItpManualForm() {
      document.body.insertAdjacentHTML("beforeend", `
        <div class="modal-backdrop" id="svcModal">
          <div class="modal small">
            <div class="modal-head"><h2>Registrar obligación manual</h2><button class="secondary" onclick="closeModal()">Cerrar</button></div>
            <div class="form-grid">
              <label>Beneficiario<input id="itpManualPayee" /></label>
              <label>Tipo beneficiario<select id="itpManualPayeeType"><option>OTHER</option><option>SUPPLIER</option><option>SURVEYOR</option><option>TAX</option><option>CARD</option></select></label>
              <label>Tipo obligación<input id="itpManualType" value="MANUAL" /></label>
              <label>Moneda<select id="itpManualCurrency"><option>USD</option><option>CRC</option></select></label>
              <label>Total<input id="itpManualTotal" type="number" step="0.01" /></label>
              <label>Referencia<input id="itpManualReference" /></label>
              <label class="wide">Notas<textarea id="itpManualNotes"></textarea></label>
            </div>
            <div class="md-actions"><button class="green" onclick="saveItpManual()">Guardar</button><button class="secondary" onclick="closeModal()">Cancelar</button></div>
            <div id="itpManualMsg" class="status hidden"></div>
          </div>
        </div>`);
    }
    async function saveItpManual() {
      const msg = $("itpManualMsg");
      msg.className = "status";
      msg.textContent = "Guardando...";
      try {
        const params = new URLSearchParams({
          payee_name:valueFrom("itpManualPayee"),
          payee_type:valueFrom("itpManualPayeeType") || "OTHER",
          obligation_type:valueFrom("itpManualType") || "MANUAL",
          total:String(Number(valueFrom("itpManualTotal") || 0)),
          currency:valueFrom("itpManualCurrency") || "USD"
        });
        if (valueFrom("itpManualReference")) params.set("reference", valueFrom("itpManualReference"));
        if (valueFrom("itpManualNotes")) params.set("notes", valueFrom("itpManualNotes"));
        if (!valueFrom("itpManualPayee") || Number(valueFrom("itpManualTotal") || 0) <= 0) throw new Error("Beneficiario y total son requeridos.");
        await postJSON(`/invoice-to-pay/manual?${params.toString()}`, {});
        closeModal();
        await loadItp();
      } catch (err) {
        msg.className = "status error";
        msg.textContent = err.message;
      }
    }
    function openItpUploadForm() {
      document.body.insertAdjacentHTML("beforeend", `
        <div class="modal-backdrop" id="svcModal">
          <div class="modal small">
            <div class="modal-head"><h2>Cargar factura PDF / XML</h2><button class="secondary" onclick="closeModal()">Cerrar</button></div>
            <div class="form-grid">
              <label>Tipo<select id="itpUploadType" onchange="toggleItpUploadType()"><option value="xml">XML</option><option value="pdf">PDF</option></select></label>
              <label class="wide">Archivo<input id="itpUploadFile" type="file" accept=".xml,.pdf,application/pdf,text/xml,application/xml" /></label>
              <label class="itpPdfOnly hidden">Referencia PDF<input id="itpPdfReference" /></label>
              <label class="itpPdfOnly hidden">Fecha factura<input id="itpPdfIssue" type="date" /></label>
              <label class="itpPdfOnly hidden">Fecha vencimiento<input id="itpPdfDue" type="date" /></label>
            </div>
            <div class="md-actions"><button onclick="submitItpUpload()">Cargar</button><button class="secondary" onclick="closeModal()">Cancelar</button></div>
            <div id="itpUploadMsg" class="status hidden"></div>
          </div>
        </div>`);
    }
    function toggleItpUploadType() {
      const isPdf = valueFrom("itpUploadType") === "pdf";
      document.querySelectorAll(".itpPdfOnly").forEach(el => el.classList.toggle("hidden", !isPdf));
    }
    async function submitItpUpload() {
      const msg = $("itpUploadMsg");
      msg.className = "status";
      msg.textContent = "Cargando...";
      try {
        const file = $("itpUploadFile")?.files?.[0];
        if (!file) throw new Error("Seleccione un archivo.");
        const fd = new FormData();
        fd.append("file", file);
        let path = "/invoice-to-pay/upload/xml";
        if (valueFrom("itpUploadType") === "pdf") {
          if (!valueFrom("itpPdfReference")) throw new Error("Referencia PDF requerida.");
          fd.append("reference", valueFrom("itpPdfReference"));
          if (valueFrom("itpPdfIssue")) fd.append("issue_date", valueFrom("itpPdfIssue"));
          if (valueFrom("itpPdfDue")) fd.append("due_date", valueFrom("itpPdfDue"));
          path = "/invoice-to-pay/upload/pdf";
        }
        await sendForm(path, fd);
        closeModal();
        await loadItp();
      } catch (err) {
        msg.className = "status error";
        msg.textContent = err.message;
      }
    }
    async function openItpPaymentForm() {
      const row = requireItpRow();
      if (!row) return;
      if (String(row.status || "").toUpperCase() === "PAID" || Number(row.balance || 0) <= 0) return alert("La obligación ya está pagada.");
      document.body.insertAdjacentHTML("beforeend", `
        <div class="modal-backdrop" id="svcModal">
          <div class="modal small">
            <div class="modal-head"><h2>Aplicar pago ITP</h2><button class="secondary" onclick="closeModal()">Cerrar</button></div>
            <div class="status">${esc(row.payee_name)} · Saldo ${esc(row.currency)} ${Number(row.balance || 0).toLocaleString("en-US",{minimumFractionDigits:2, maximumFractionDigits:2})}</div>
            <div class="form-grid">
              <label>Monto<input id="itpPayAmount" type="number" step="0.01" value="${esc(row.balance || "")}" /></label>
              <label>Fecha pago<input id="itpPayDate" type="date" value="${new Date().toISOString().slice(0,10)}" /></label>
              <label>Cuenta pago<select id="itpPayBank"><option value="">Cargando...</option></select></label>
              <label>Método<select id="itpPayMethod"><option value="BANK">Banco</option><option value="CARD_3155">Tarjeta 3155</option><option value="HAZEL_CONTRIBUTION">Aporte Hazel</option></select></label>
              <label>Comprobante<input id="itpPayReference" /></label>
              <label>Últimos 4 tarjeta<input id="itpPayCardLast4" maxlength="4" /></label>
            </div>
            <div class="md-actions"><button class="green" onclick="submitItpPayment()">Aplicar</button><button class="secondary" onclick="closeModal()">Cancelar</button></div>
            <div id="itpPayMsg" class="status hidden"></div>
          </div>
        </div>`);
      await loadItpPaymentBanks();
    }
    async function loadItpPaymentBanks() {
      const select = $("itpPayBank");
      if (!select) return;
      try {
        const rows = rowsList(await getJSON("/accounting/bank-accounts"));
        select.innerHTML = rows.map(row => {
          const code = row.account_code || "";
          const name = row.account_name || "";
          return `<option value="${esc(code)}|${esc(name)}">${esc(code)} - ${esc(name)}</option>`;
        }).join("") || '<option value="">Sin bancos disponibles</option>';
      } catch {
        select.innerHTML = '<option value="">Sin bancos disponibles</option>';
      }
    }
    async function submitItpPayment() {
      const row = requireItpRow();
      if (!row) return;
      const msg = $("itpPayMsg");
      msg.className = "status";
      msg.textContent = "Aplicando pago...";
      try {
        const [bankCode, bankName] = valueFrom("itpPayBank").split("|");
        const amount = Number(valueFrom("itpPayAmount") || 0);
        if (amount <= 0) throw new Error("Monto inválido.");
        if (!valueFrom("itpPayReference")) throw new Error("Comprobante bancario requerido.");
        const params = new URLSearchParams({
          obligation_id:String(row.id),
          amount:String(amount),
          payment_date:valueFrom("itpPayDate") || new Date().toISOString().slice(0,10),
          payment_reference:valueFrom("itpPayReference"),
          payment_method:valueFrom("itpPayMethod") || "BANK"
        });
        if (bankCode) params.set("bank_account_code", bankCode);
        if (bankName) {
          params.set("bank_account_name", bankName);
          params.set("bank_name", bankName);
        }
        if (valueFrom("itpPayCardLast4")) params.set("payment_card_last4", valueFrom("itpPayCardLast4"));
        const result = await postJSON(`/invoice-to-pay/apply-payment?${params.toString()}`, {});
        closeModal();
        alert(`Pago aplicado. Nuevo saldo: ${Number(result.new_balance || 0).toLocaleString("en-US",{minimumFractionDigits:2, maximumFractionDigits:2})}${result.accounting_warning ? "\\nAdvertencia accounting: " + result.accounting_warning : ""}`);
        await loadItp();
      } catch (err) {
        msg.className = "status error";
        msg.textContent = err.message;
      }
    }
    async function deleteSelectedItp() {
      const row = requireItpRow();
      if (!row) return;
      if (!confirm(`¿Eliminar obligación ITP ${row.id} - ${row.referencia || row.payee_name}?`)) return;
      try {
        await sendJSON("DELETE", `/invoice-to-pay/${encodeURIComponent(row.id)}`);
        await loadItp();
      } catch (err) {
        alert(err.message);
      }
    }
    function downloadItpExcel() {
      if (!itpRows.length) return alert("No hay datos para exportar.");
      const cols = ["id","payee_name","obligation_type","referencia","issue_date","due_date","vessel","country","operation","currency","total","balance","last_payment_date","status","origin"];
      downloadExcelFile(`itp_${new Date().toISOString().slice(0,10)}.xls`, itpRows, cols, "Invoice To Pay");
    }
    function openItpPaymentReport() {
      document.body.insertAdjacentHTML("beforeend", `
        <div class="modal-backdrop" id="svcModal">
          <div class="modal small">
            <div class="modal-head"><h2>Reporte pagos ITP / presupuesto</h2><button class="secondary" onclick="closeModal()">Cerrar</button></div>
            <div class="form-grid">
              <label>Periodo<input id="itpRptPeriod" value="${new Date().toISOString().slice(0,7)}" placeholder="YYYY-MM" /></label>
              <label>Meses<select id="itpRptMonths"><option>1</option><option>3</option><option>6</option><option>12</option><option>24</option><option>36</option></select></label>
              <label>Estado<select id="itpRptStatus"><option>ALL</option><option>PENDING</option><option>PARTIAL</option><option>PAID</option></select></label>
              <label>Desde<input id="itpRptFrom" type="date" /></label>
              <label>Hasta<input id="itpRptTo" type="date" /></label>
              <label>Tipo obligación<input id="itpRptType" value="ALL" /></label>
              <label>Tipo beneficiario<input id="itpRptPayeeType" value="ALL" /></label>
            </div>
            <div class="md-actions"><button onclick="downloadItpPaymentReport()">Exportar Excel</button><button class="secondary" onclick="closeModal()">Cancelar</button></div>
          </div>
        </div>`);
    }
    function downloadItpPaymentReport() {
      const params = new URLSearchParams({
        period:valueFrom("itpRptPeriod") || new Date().toISOString().slice(0,7),
        months:valueFrom("itpRptMonths") || "1",
        status:valueFrom("itpRptStatus") || "ALL",
        obligation_type:valueFrom("itpRptType") || "ALL",
        payee_type:valueFrom("itpRptPayeeType") || "ALL"
      });
      if (valueFrom("itpRptFrom")) params.set("date_from", valueFrom("itpRptFrom"));
      if (valueFrom("itpRptTo")) params.set("date_to", valueFrom("itpRptTo"));
      window.open(`/invoice-to-pay/reports/payment-report.xlsx?${params.toString()}`, "_blank");
    }
    function openItpBiweekly() {
      const period = new Date().toISOString().slice(0,7);
      document.body.insertAdjacentHTML("beforeend", `
        <div class="modal-backdrop" id="svcModal">
          <div class="modal wide">
            <div class="modal-head"><h2>Obligaciones quincenales</h2><button class="secondary" onclick="closeModal()">Cerrar</button></div>
            <div class="finance-filter-row compact">
              <label>Periodo<input id="itpBiPeriod" value="${period}" placeholder="YYYY-MM" /></label>
              <label>Quincena<select id="itpBiFortnight"><option value="1">1</option><option value="2">2</option></select></label>
              <button onclick="loadItpBiweekly(false)">Generar / buscar</button>
              <button class="secondary" onclick="loadItpBiweekly(true)">Regenerar automático</button>
              <button class="secondary" onclick="saveItpBiweeklyDraft()">Guardar borrador</button>
              <button class="green" onclick="applyItpBiweekly()">Aplicar pagos y crear asientos</button>
              <button class="secondary" onclick="exportItpBiweekly()">Exportar Excel</button>
            </div>
            <div id="itpBiMsg" class="status">Presione Generar / buscar para cargar obligaciones quincenales.</div>
            <div id="itpBiTable" class="workspace"></div>
          </div>
        </div>`);
    }
    async function loadItpBiweekly(force=false) {
      const msg = $("itpBiMsg");
      const table = $("itpBiTable");
      msg.className = "status";
      msg.textContent = "Consultando obligaciones quincenales...";
      try {
        const params = new URLSearchParams({ period:valueFrom("itpBiPeriod"), fortnight:valueFrom("itpBiFortnight") || "1", force:String(!!force) });
        const payload = await getJSON(`/invoice-to-pay/biweekly-obligations/preview?${params.toString()}`);
        itpBiweeklyRows = rowsList(payload.rows || payload);
        msg.className = "status";
        msg.textContent = payload.source === "draft" ? "Borrador cargado. Revise pendientes antes de aplicar." : "Preview generado. Complete comprobante y cuenta contable antes de aplicar.";
        renderItpBiweeklyTable();
      } catch (err) {
        itpBiweeklyRows = [];
        table.innerHTML = "";
        msg.className = "status error";
        msg.textContent = err.message;
      }
    }
    function renderItpBiweeklyTable() {
      const table = $("itpBiTable");
      if (!itpBiweeklyRows.length) {
        table.innerHTML = '<div class="status">Sin líneas para esta quincena.</div>';
        return;
      }
      const inputs = (idx,row) => `
        <td><input data-bi="${idx}" data-field="category" value="${esc(row.category)}" /></td>
        <td><input data-bi="${idx}" data-field="name" value="${esc(row.name)}" /></td>
        <td><input data-bi="${idx}" data-field="amount" type="number" step="0.01" value="${esc(row.amount)}" /></td>
        <td><select data-bi="${idx}" data-field="currency"><option${row.currency === "CRC" ? " selected" : ""}>CRC</option><option${row.currency === "USD" ? " selected" : ""}>USD</option></select></td>
        <td><input data-bi="${idx}" data-field="due_date" type="date" value="${esc(String(row.due_date || "").slice(0,10))}" /></td>
        <td><input data-bi="${idx}" data-field="bank_account" value="${esc(row.bank_account)}" /></td>
        <td><input data-bi="${idx}" data-field="bank_accounting_code" value="${esc(row.bank_accounting_code)}" /></td>
        <td><input data-bi="${idx}" data-field="bank_voucher" value="${esc(row.bank_voucher)}" /></td>
        <td><select data-bi="${idx}" data-field="payment_method"><option value="BANK"${row.payment_method === "BANK" ? " selected" : ""}>Banco</option><option value="CARD_3155"${row.payment_method === "CARD_3155" ? " selected" : ""}>Tarjeta 3155</option><option value="HAZEL_CONTRIBUTION"${row.payment_method === "HAZEL_CONTRIBUTION" ? " selected" : ""}>Aporte Hazel</option></select></td>`;
      table.innerHTML = `<div class="table-wrap"><table><thead><tr><th>Rubro</th><th>Beneficiario</th><th>Monto</th><th>Moneda</th><th>Fecha pago</th><th>Cuenta destino / IBAN</th><th>Cuenta contable pago</th><th>Comprobante</th><th>Método</th><th>ITP ID</th><th>Fuente</th></tr></thead><tbody>${itpBiweeklyRows.map((row,idx) => `<tr>${inputs(idx,row)}<td>${esc(row.obligation_id || "")}</td><td>${esc(row.source || "")}</td></tr>`).join("")}</tbody></table></div>`;
    }
    function collectItpBiweeklyRows() {
      const rows = itpBiweeklyRows.map(row => ({ ...row }));
      document.querySelectorAll("[data-bi]").forEach(input => {
        const idx = Number(input.dataset.bi);
        const field = input.dataset.field;
        if (!rows[idx]) return;
        rows[idx][field] = field === "amount" ? Number(input.value || 0) : input.value;
      });
      itpBiweeklyRows = rows;
      return rows;
    }
    async function saveItpBiweeklyDraft() {
      const msg = $("itpBiMsg");
      msg.className = "status";
      msg.textContent = "Guardando borrador...";
      try {
        const result = await postJSON("/invoice-to-pay/biweekly-obligations/save-draft", { period:valueFrom("itpBiPeriod"), fortnight:Number(valueFrom("itpBiFortnight") || 1), rows:collectItpBiweeklyRows() });
        msg.textContent = `Borrador guardado. Líneas: ${result.rows || result.saved || itpBiweeklyRows.length}`;
      } catch (err) {
        msg.className = "status error";
        msg.textContent = err.message;
      }
    }
    async function applyItpBiweekly() {
      if (!confirm("Se aplicarán pagos con comprobante y cuenta contable, y se crearán los asientos correspondientes. ¿Continuar?")) return;
      const msg = $("itpBiMsg");
      msg.className = "status";
      msg.textContent = "Aplicando pagos quincenales...";
      try {
        const result = await postJSON("/invoice-to-pay/biweekly-obligations/apply", { period:valueFrom("itpBiPeriod"), fortnight:Number(valueFrom("itpBiFortnight") || 1), rows:collectItpBiweeklyRows() });
        msg.textContent = `Aplicado. Asientos: ${result.posted || 0}. Pagos ITP: ${result.applied || 0}. Pendientes: ${result.pending || 0}.`;
        await loadItp();
      } catch (err) {
        msg.className = "status error";
        msg.textContent = err.message;
      }
    }
    async function exportItpBiweekly() {
      try {
        const payload = { period:valueFrom("itpBiPeriod"), fortnight:Number(valueFrom("itpBiFortnight") || 1), rows:collectItpBiweeklyRows() };
        const ticket = await postJSON("/invoice-to-pay/biweekly-obligations/export-ticket", payload);
        if (!ticket.ticket) throw new Error("No se pudo preparar exportación.");
        window.open(`/invoice-to-pay/biweekly-obligations/export/${encodeURIComponent(ticket.ticket)}.xlsx`, "_blank");
      } catch (err) {
        alert(err.message);
      }
    }
    function renderFinancePlanning(target) {
      const period = new Date().toISOString().slice(0,7);
      target.innerHTML = `
        <div class="panel-head"><h2>PLN / Planificación financiera</h2><span class="muted">Planificación, ITP, gastos, pagos, accounting, metas, proyectos y ahorros</span></div>
        <div class="finance-filter-row compact">
          <label>Periodo<input id="plnPeriod" value="${esc(period)}" placeholder="YYYY-MM" /></label>
          <label>Meses<select id="plnMonths"><option>1</option><option>2</option><option>3</option><option selected>4</option><option>6</option><option>12</option></select></label>
          <button onclick="loadFinancePlanning()">Buscar</button>
          <button class="green" onclick="openPlanningProjectForm()">Agregar proyecto</button>
          <button class="secondary" onclick="renderFinancePlanning($('planningWorkspace') || $('itpWorkspace'))">Limpiar</button>
        </div>
        <div id="planningMsg" class="status">Presione Buscar para consultar PLN.</div>
        <div id="planningResult" class="workspace"></div>`;
    }
    async function loadFinancePlanning() {
      const msg = $("planningMsg");
      const result = $("planningResult");
      const period = valueFrom("plnPeriod") || new Date().toISOString().slice(0,7);
      const months = valueFrom("plnMonths") || "4";
      msg.className = "status";
      msg.textContent = "Consultando planificación...";
      result.innerHTML = "";
      try {
        const payload = await getJSON(`/finance/planning/summary?period=${encodeURIComponent(period)}&months=${encodeURIComponent(months)}`);
        msg.className = "status hidden";
        result.innerHTML = renderPlanningSummary(payload);
      } catch (err) {
        msg.className = "status error";
        msg.textContent = err.message;
      }
    }
    function renderPlanningSummary(payload) {
      const totals = payload.totals || {};
      const pending = totals.pending_by_currency || {};
      const cards = [
        ["Pendiente ITP", Object.entries(pending).map(([cur,val]) => `${cur} ${money(val)}`).join(" | ") || "0.00"],
        ["Líneas", totals.obligation_lines || 0],
        ["Metas activas", totals.goals_active || 0],
        ["Proyectos", totals.projects || 0],
        ["Utilidad proyectos", money(totals.project_expected_profit || 0)],
        ["Ahorro mensual", money(totals.monthly_savings || 0)]
      ];
      const profitability = payload.profitability || {};
      return `
        <div class="grid kpis">${cards.map(([label,value]) => `<div class="card kpi"><span>${esc(label)}</span><strong>${esc(value)}</strong></div>`).join("")}</div>
        ${renderPlanningSection("Rentabilidad empresa", [
          {metric:"Ingresos", value:money(profitability.revenue || 0)},
          {metric:"Gastos", value:money(profitability.expenses || 0)},
          {metric:"Utilidad", value:money(profitability.profit || 0)},
          {metric:"Margen %", value:profitability.margin_pct || 0}
        ], ["metric","value"])}
        ${renderPlanningSection("Alertas", payload.alerts || [], ["severity","code","message"])}
        ${renderPlanningSection("Calendario ITP", payload.obligation_buckets || [], ["currency","bucket","count","amount"])}
        ${renderPlanningSection("Obligaciones", payload.obligations || [], ["id","payee_name","obligation_type","due_date","currency","balance","status","origin"])}
        ${renderPlanningSection("Pagos aplicados", payload.applied_payments || [], ["currency","count","amount"])}
        ${renderPlanningSection("Gastos Accounting", payload.expenses || [], ["period","account_code","account_name","actual_amount"])}
        ${renderPlanningSection("Metas / ahorros", payload.goals || [], ["id","period","purpose","name","account_code","currency_code","target_amount","progress_amount","progress_pct","target_date","status"])}
        ${renderPlanningSection("Proyectos", payload.projects || [], ["id","name","client_name","status","priority","target_date","currency_code","expected_revenue","expected_cost","expected_profit","expected_margin_pct","monthly_savings"])}
        ${renderPlanningSection("Cronograma", payload.project_schedule || [], ["due_date","concept","direction","currency_code","amount","status","project_id"])}
        ${renderPlanningSection("Ahorro mensual", payload.monthly_plan || [], ["month","currency_code","planned_inflow","planned_outflow","planned_saving"])}
        <div class="status">${(payload.decision_notes || []).map(esc).join("<br>")}</div>`;
    }
    function renderPlanningSection(title, rows, cols) {
      if (!rows.length) return `<h3>${esc(title)}</h3><div class="status">Sin datos.</div>`;
      return `<h3>${esc(title)}</h3><div class="table-wrap"><table><thead><tr><th class="pick-col"></th>${cols.map(c => `<th>${esc(c.replace(/_/g," "))}</th>`).join("")}<th>Acción</th></tr></thead><tbody>${rows.slice(0,120).map((row,idx) => `<tr><td class="pick-col"><input class="row-pick" type="checkbox" /></td>${cols.map(c => `<td>${esc(["amount","balance","total","target_amount","progress_amount","actual_amount","total_honorarios","total_gastos","precio","utilidad","expected_revenue","expected_cost","expected_profit","monthly_savings","planned_inflow","planned_outflow","planned_saving"].includes(c) ? money(row[c]) : row[c])}</td>`).join("")}<td>${title === "Proyectos" ? `<button onclick='openPlanningProjectForm(${JSON.stringify(row).replace(/'/g, "&#39;")})'>Editar</button><button class="brown" onclick="deletePlanningProject(${Number(row.id || 0)})">Eliminar</button>` : ""}</td></tr>`).join("")}</tbody></table></div>`;
    }
    function openPlanningProjectForm(project={}) {
      document.body.insertAdjacentHTML("beforeend", `
        <div class="modal-backdrop" id="svcModal">
          <div class="modal small">
            <div class="modal-head"><h2>${project.id ? "Modificar proyecto PLN" : "Agregar proyecto PLN"}</h2><button class="secondary" onclick="closeModal()">Cerrar</button></div>
            <div class="form-grid">
              <label>Nombre<input id="plnProjName" value="${esc(project.name || "")}" required /></label>
              <label>Cliente<input id="plnProjClient" value="${esc(project.client_name || "")}" /></label>
              <label>Responsable<input id="plnProjOwner" value="${esc(project.owner || "")}" /></label>
              <label>Fecha objetivo<input id="plnProjTarget" value="${esc(project.target_date || new Date().toISOString().slice(0,10))}" /></label>
              <label>Moneda<select id="plnProjCurrency"><option>USD</option><option>CRC</option></select></label>
              <label>Ingreso esperado<input id="plnProjRevenue" type="number" step="0.01" value="${esc(project.expected_revenue || 0)}" /></label>
              <label>Costo esperado<input id="plnProjCost" type="number" step="0.01" value="${esc(project.expected_cost || 0)}" /></label>
              <label>Ahorro mensual<input id="plnProjSaving" type="number" step="0.01" value="${esc(project.monthly_savings || 0)}" /></label>
              <label>Probabilidad %<input id="plnProjProb" type="number" step="0.01" value="${esc(project.probability_pct || 100)}" /></label>
              <label>Estado<select id="plnProjStatus"><option>PLANNED</option><option>ACTIVE</option><option>PAUSED</option><option>DONE</option><option>CANCELLED</option></select></label>
              <label>Prioridad<select id="plnProjPriority"><option>LOW</option><option>MEDIUM</option><option>HIGH</option><option>CRITICAL</option></select></label>
              <label class="wide">Notas<textarea id="plnProjNotes">${esc(project.notes || "")}</textarea></label>
            </div>
            <div class="md-actions"><button class="green" onclick="savePlanningProject(${project.id || 0})">Guardar</button><button class="secondary" onclick="closeModal()">Cancelar</button></div>
            <div id="plnProjectMsg" class="status hidden"></div>
          </div>
        </div>`);
      $("plnProjCurrency").value = project.currency_code || "USD";
      $("plnProjStatus").value = project.status || "PLANNED";
      $("plnProjPriority").value = project.priority || "MEDIUM";
    }
    async function savePlanningProject(id=0) {
      const msg = $("plnProjectMsg");
      msg.className = "status";
      msg.textContent = "Guardando proyecto...";
      const payload = {
        name:valueFrom("plnProjName"),
        client_name:valueFrom("plnProjClient"),
        owner:valueFrom("plnProjOwner"),
        target_date:valueFrom("plnProjTarget"),
        currency_code:valueFrom("plnProjCurrency") || "USD",
        expected_revenue:Number(valueFrom("plnProjRevenue") || 0),
        expected_cost:Number(valueFrom("plnProjCost") || 0),
        monthly_savings:Number(valueFrom("plnProjSaving") || 0),
        probability_pct:Number(valueFrom("plnProjProb") || 100),
        status:valueFrom("plnProjStatus") || "PLANNED",
        priority:valueFrom("plnProjPriority") || "MEDIUM",
        notes:valueFrom("plnProjNotes")
      };
      if (!payload.name) {
        msg.className = "status error";
        msg.textContent = "Nombre requerido.";
        return;
      }
      try {
        if (id) await sendJSON("PUT", `/finance/planning/projects/${id}`, payload);
        else await postJSON("/finance/planning/projects", payload);
        closeModal();
        await loadFinancePlanning();
      } catch (err) {
        msg.className = "status error";
        msg.textContent = err.message;
      }
    }
    async function deletePlanningProject(id) {
      if (!id || !confirm("Eliminar proyecto PLN?")) return;
      try {
        await sendJSON("DELETE", `/finance/planning/projects/${id}`, null);
        await loadFinancePlanning();
      } catch (err) {
        alert(err.message);
      }
    }
    function switchFinanceTab(tab) {
      financeTab = tab;
      if (tab === "billing") renderBillingWeb(orderCashWorkspace());
      else if (tab === "credit") renderCreditHoldWeb(orderCashWorkspace());
      else if (tab === "collections") renderCollectionsWeb(orderCashWorkspace());
      else if (tab === "bank") renderBankWeb(orderCashWorkspace());
      else if (tab === "disputes") renderDisputesWeb(orderCashWorkspace());
    }
    function renderCollectionsWeb(target=orderCashWorkspace()) {
      target.innerHTML = `
        <div class="panel-head">
          <h2>Collections — Accounts Receivable</h2>
          <span class="muted">Use filtros y presione Buscar</span>
        </div>
        <div class="finance-filter-row">
          <label>Cliente<select id="collectionsCliente" onpointerdown="loadCollectionsClientes()" onfocus="loadCollectionsClientes()"><option value="ALL">ALL</option></select></label>
          <label>Aging<select id="collectionsBucket"><option value="">Todos</option><option>CURRENT</option><option>1-30</option><option>31-60</option><option>61-90</option><option>90+</option></select></label>
          <label>Estado<select id="collectionsEstado"><option value="">Todos</option><option>EMITIDA</option><option>PENDIENTE_PAGO</option><option>PAGADA</option><option>DISPUTADA</option><option>WRITE_OFF</option></select></label>
          <label>Disputada<select id="collectionsDisputada"><option value="">Todos</option><option value="true">True</option><option value="false">False</option></select></label>
          <button onclick="loadCollections(1)">Buscar</button>
          <button class="secondary" onclick="clearCollections()">Limpiar</button>
        </div>
        <div class="finance-toolbar">
          <button class="secondary" onclick="syncCollectionsFromInvoicing()">Sincronizar facturas</button>
          <button onclick="viewSelectedCollectionInvoice()">Ver factura</button>
          <button class="brown" onclick="openCollectionDisputeForm()">Disputar</button>
          <button class="green" onclick="openCollectionPaymentForm()">Aplicar pago / NC</button>
          <button class="secondary" onclick="downloadCollectionsExcel()">Exportar Excel</button>
          <button class="secondary" onclick="downloadCollectionsStatementWord()">Estado de cuenta Word</button>
        </div>
        <div id="collectionsKpis" class="grid kpis hidden"></div>
        <div id="collectionsMsg" class="status hidden"></div>
        <div id="collectionsTable" class="workspace"><div class="status">Use los filtros y presione Buscar para cargar Collections.</div></div>`;
    }
    async function loadCollectionsClientes() {
      if (collectionClientesLoaded) return;
      const select = $("collectionsCliente");
      if (!select) return;
      select.innerHTML = '<option value="ALL">Cargando...</option>';
      try {
        const names = new Set();
        let page = 1;
        const pageSize = 200;
        while (page <= 20) {
          const payload = await getJSON(`/collections/search?page=${page}&page_size=${pageSize}`);
          rowsList(payload).forEach(row => {
            const name = row.nombre_cliente || row.codigo_cliente;
            if (name) names.add(String(name));
          });
          const total = Number(payload.total || 0);
          if (!rowsList(payload).length || page * pageSize >= total) break;
          page += 1;
        }
        collectionClientes = ["ALL", ...Array.from(names).sort((a,b) => a.localeCompare(b))];
        select.innerHTML = collectionClientes.map(c => `<option value="${esc(c)}">${esc(c)}</option>`).join("");
        collectionClientesLoaded = true;
      } catch (err) {
        select.innerHTML = '<option value="ALL">ALL</option>';
        alert(`No se pudieron cargar clientes de Collections: ${err.message}`);
      }
    }
    function collectionParams(page=1) {
      const params = new URLSearchParams({ page:String(page), page_size:"50" });
      const map = {
        collectionsCliente:"cliente",
        collectionsBucket:"bucket_aging",
        collectionsEstado:"estado_factura",
        collectionsDisputada:"disputada"
      };
      Object.entries(map).forEach(([id, key]) => {
        const val = valueFrom(id);
        if (val && val !== "ALL") params.set(key, val);
      });
      return params.toString();
    }
    async function loadCollections(page=1) {
      collectionPage = page;
      selectedCollectionIndex = null;
      selectedCollectionIndexes = new Set();
      const msg = $("collectionsMsg");
      const table = $("collectionsTable");
      msg.className = "status";
      msg.textContent = "Consultando Collections...";
      try {
        const payload = await getJSON(`/collections/search?${collectionParams(page)}`);
        collectionRows = rowsList(payload).sort((a,b) => Number(b.aging_dias || 0) - Number(a.aging_dias || 0));
        collectionTotal = Number(payload.total || collectionRows.length || 0);
        msg.classList.add("hidden");
        renderCollectionsKpis();
        renderCollectionsTable();
      } catch (err) {
        table.innerHTML = "";
        msg.className = "status error";
        msg.textContent = err.message;
      }
    }
    function clearCollections() {
      ["collectionsCliente","collectionsBucket","collectionsEstado","collectionsDisputada"].forEach(id => { if ($(id)) $(id).value = id === "collectionsCliente" ? "ALL" : ""; });
      collectionRows = [];
      selectedCollectionIndex = null;
      selectedCollectionIndexes = new Set();
      collectionPage = 1;
      collectionTotal = 0;
      $("collectionsKpis")?.classList.add("hidden");
      $("collectionsMsg")?.classList.add("hidden");
      if ($("collectionsTable")) $("collectionsTable").innerHTML = '<div class="status">Use los filtros y presione Buscar para cargar Collections.</div>';
    }
    function renderCollectionsKpis() {
      const totals = collectionRows.reduce((acc, row) => {
        const saldo = Number(row.saldo_pendiente || 0);
        const aging = Number(row.aging_dias || 0);
        acc.total += saldo;
        if (aging < 1) acc.current += saldo;
        else acc.overdue += saldo;
        if (aging > 90) acc.over90 += saldo;
        return acc;
      }, { total:0, current:0, overdue:0, over90:0 });
      const kpis = $("collectionsKpis");
      if (!kpis) return;
      kpis.classList.remove("hidden");
      kpis.innerHTML = [
        ["Total AR (Saldo)", totals.total],
        ["Current (Saldo)", totals.current],
        ["Overdue (Saldo)", totals.overdue],
        ["Over 90 (Saldo)", totals.over90],
      ].map(([label,value]) => `<div class="card kpi"><span>${esc(label)}</span><strong>${Number(value).toLocaleString("en-US",{minimumFractionDigits:2, maximumFractionDigits:2})}</strong></div>`).join("");
    }
    function collectionRow() {
      if (selectedCollectionIndex === null) selectedCollectionIndex = firstFromSet(selectedCollectionIndexes);
      return selectedCollectionIndex === null ? null : collectionRows[selectedCollectionIndex];
    }
    function toggleCollectionRow(idx, checked=null) {
      const next = checked === null ? !selectedCollectionIndexes.has(idx) : checked;
      selectedCollectionIndex = setIndexSelection(selectedCollectionIndexes, idx, next);
      renderCollectionsTable();
    }
    function requireCollectionRow() {
      const row = collectionRow();
      if (!row) alert("Seleccione primero una factura de Collections.");
      return row;
    }
    function renderCollectionsTable() {
      const table = $("collectionsTable");
      const cols = ["codigo_cliente","nombre_cliente","tipo_factura","tipo_documento","numero_documento","fecha_emision","dias_credito","fecha_vencimiento","aging_dias","moneda","total","saldo_pendiente","num_informe","buque_contenedor","operacion","periodo_operacion","estado_factura","disputada"];
      if (!collectionRows.length) {
        table.innerHTML = '<div class="status">Sin registros para los filtros seleccionados.</div>';
        return;
      }
      const totalPages = Math.max(1, Math.ceil(collectionTotal / 50));
      table.innerHTML = `
        <div class="table-wrap"><table><thead><tr><th class="pick-col"></th>${cols.map(c => `<th>${esc(c.replace(/_/g," "))}</th>`).join("")}</tr></thead>
        <tbody>${collectionRows.map((row, idx) => {
          const overdue = Number(row.aging_dias || 0) > 1 ? "service-warning" : "";
          const selected = selectedCollectionIndexes.has(idx);
          return `<tr class="${selected ? "service-selected" : overdue}" onclick="toggleCollectionRow(${idx})"><td class="pick-col"><input class="row-pick" type="checkbox" ${selected ? "checked" : ""} onclick="event.stopPropagation(); toggleCollectionRow(${idx}, this.checked)" /></td>${cols.map(c => `<td>${esc(["total","saldo_pendiente"].includes(c) ? Number(row[c] || 0).toLocaleString("en-US",{minimumFractionDigits:2, maximumFractionDigits:2}) : row[c])}</td>`).join("")}</tr>`;
        }).join("")}</tbody></table></div>
        <div class="pager">
          <button class="secondary" onclick="loadCollections(Math.max(1, collectionPage-1))" ${collectionPage <= 1 ? "disabled" : ""}>Anterior</button>
          <span class="muted">Página ${collectionPage} de ${totalPages} · ${collectionRows.length} visibles de ${intFmt.format(collectionTotal)}</span>
          <button class="secondary" onclick="loadCollections(collectionPage+1)" ${collectionPage >= totalPages ? "disabled" : ""}>Siguiente</button>
        </div>`;
    }
    async function syncCollectionsFromInvoicing() {
      if (!confirm("Esto sincronizará facturas emitidas hacia Collections. ¿Desea continuar?")) return;
      try {
        const result = await postJSON("/collections/sync-from-invoicing", {});
        alert(`Sincronización completada. Facturas nuevas: ${result.inserted || 0}`);
        if (collectionRows.length) await loadCollections(collectionPage);
      } catch (err) {
        alert(err.message);
      }
    }
    function viewSelectedCollectionInvoice() {
      const row = requireCollectionRow();
      if (!row) return;
      if (row.tipo_documento !== "FACTURA") return alert("Solo es posible visualizar Facturas.");
      if (row.tipo_factura === "ELECTRONICA") return alert("Para ver la factura electrónica debe dirigirse a GTI.");
      window.open(`/billing/pdf/${encodeURIComponent(row.numero_documento)}`, "_blank");
    }
    const EXCEL_TEXT_COLUMNS = new Set(["numero_documento","codigo_cliente","num_informe","referencia","factura_numero","nota_credito_numero","comprobante"]);
    function excelCell(row, col) {
      const raw = row[col] ?? "";
      const value = String(raw);
      const forceText = EXCEL_TEXT_COLUMNS.has(col) || /^0\\d+$/.test(value) || /^\\d{11,}$/.test(value);
      if (forceText) return `<td class="text-cell" style="mso-number-format:'\\@';" x:str>${esc(value)}</td>`;
      return `<td>${esc(raw)}</td>`;
    }
    function downloadExcelFile(filename, rows, cols, title="Detalle") {
      const table = `<table><thead><tr>${cols.map(c => `<th>${esc(c)}</th>`).join("")}</tr></thead><tbody>${rows.map(row => `<tr>${cols.map(c => excelCell(row, c)).join("")}</tr>`).join("")}</tbody></table>`;
      const html = `<!doctype html><html><head><meta charset="utf-8" /><style>.text-cell{mso-number-format:"\\@";}</style></head><body><h3>${esc(title)}</h3>${table}</body></html>`;
      downloadText(filename, html, "application/vnd.ms-excel;charset=utf-8");
    }
    function downloadWordFile(filename, htmlBody) {
      const html = `<!doctype html><html><head><meta charset="utf-8" /><style>body{font-family:Arial,sans-serif} table{border-collapse:collapse;width:100%} th,td{border:1px solid #999;padding:6px;font-size:10pt} th{background:#e9eef5}</style></head><body>${htmlBody}</body></html>`;
      downloadText(filename, html, "application/msword;charset=utf-8");
    }
    function downloadCollectionsExcel() {
      if (!collectionRows.length) return alert("No hay datos para exportar.");
      const cols = ["codigo_cliente","nombre_cliente","tipo_factura","tipo_documento","numero_documento","fecha_emision","dias_credito","fecha_vencimiento","aging_dias","moneda","total","saldo_pendiente","num_informe","buque_contenedor","operacion","periodo_operacion","estado_factura","disputada"];
      downloadExcelFile(`collections_${new Date().toISOString().slice(0,10)}.xls`, collectionRows, cols, "Collections - detalle de facturas");
    }
    function downloadCollectionsStatementWord() {
      if (!collectionRows.length) return alert("No hay información cargada para generar estado de cuenta.");
      const cliente = collectionRows[0]?.nombre_cliente || "Cliente";
      const today = new Date().toISOString().slice(0,10);
      const total = collectionRows.reduce((sum,row) => sum + Number(row.saldo_pendiente || 0), 0);
      const overdue = collectionRows.reduce((sum,row) => sum + (Number(row.aging_dias || 0) > 0 ? Number(row.saldo_pendiente || 0) : 0), 0);
      const cols = ["numero_documento","fecha_emision","fecha_vencimiento","aging_dias","moneda","total","saldo_pendiente","buque_contenedor","operacion","num_informe"];
      const rows = collectionRows.map(row => `<tr>${cols.map(c => `<td>${esc(["total","saldo_pendiente"].includes(c) ? Number(row[c] || 0).toLocaleString("en-US",{minimumFractionDigits:2, maximumFractionDigits:2}) : row[c])}</td>`).join("")}</tr>`).join("");
      const body = `
        <h2>Estado de cuenta</h2>
        <p><strong>Cliente:</strong> ${esc(cliente)}</p>
        <p><strong>Fecha:</strong> ${esc(today)}</p>
        <p><strong>Total pendiente:</strong> ${Number(total).toLocaleString("en-US",{minimumFractionDigits:2, maximumFractionDigits:2})}</p>
        <p><strong>Overdue:</strong> ${Number(overdue).toLocaleString("en-US",{minimumFractionDigits:2, maximumFractionDigits:2})}</p>
        <table><thead><tr>${cols.map(c => `<th>${esc(c.replace(/_/g," "))}</th>`).join("")}</tr></thead><tbody>${rows}</tbody></table>`;
      downloadWordFile(`estado_cuenta_${String(cliente).replace(/[^a-z0-9]+/gi,"_")}_${today}.doc`, body);
    }
    function openCollectionDisputeForm() {
      const row = requireCollectionRow();
      if (!row) return;
      if (row.tipo_documento !== "FACTURA") return alert("Solo se pueden disputar Facturas.");
      document.body.insertAdjacentHTML("beforeend", `
        <div class="modal-backdrop" id="svcModal">
          <div class="modal small">
            <div class="modal-head"><h2>Crear Disputa</h2><button class="secondary" onclick="closeModal()">Cerrar</button></div>
            <div class="status">Factura ${esc(row.numero_documento)} · ${esc(row.nombre_cliente)} · ${esc(row.moneda)} ${Number(row.total || 0).toLocaleString("en-US",{minimumFractionDigits:2, maximumFractionDigits:2})}</div>
            <div class="form-grid">
              <label>Motivo<select id="colDisputaMotivo"><option value="">Seleccione</option><option>PRECIO</option><option>DESCUENTO</option><option>CALIDAD</option><option>WRITE_OFF</option><option>CLIENTE_INCORRECTO</option></select></label>
              <label class="wide">Comentario<textarea id="colDisputaComentario"></textarea></label>
            </div>
            <div class="md-actions"><button class="brown" onclick="saveCollectionDispute()">Confirmar Disputa</button><button class="secondary" onclick="closeModal()">Cancelar</button></div>
            <div id="colDisputaMsg" class="status hidden"></div>
          </div>
        </div>`);
    }
    async function saveCollectionDispute() {
      const row = requireCollectionRow();
      const msg = $("colDisputaMsg");
      const motivo = valueFrom("colDisputaMotivo");
      const comentario = valueFrom("colDisputaComentario");
      if (!motivo || !comentario) return alert("Seleccione motivo e ingrese comentario.");
      msg.className = "status";
      msg.textContent = "Registrando disputa...";
      try {
        await postJSON("/collections/disputa", {
          numero_documento:row.numero_documento,
          codigo_cliente:row.codigo_cliente,
          nombre_cliente:row.nombre_cliente,
          fecha_factura:String(row.fecha_emision || "").slice(0,10),
          fecha_vencimiento:String(row.fecha_vencimiento || "").slice(0,10),
          monto:row.total,
          motivo,
          comentario,
          buque_contenedor:row.buque_contenedor,
          operacion:row.operacion,
          periodo_operacion:row.periodo_operacion,
          descripcion_servicio:row.descripcion_servicio || null
        });
        closeModal();
        await loadCollections(collectionPage);
      } catch (err) {
        msg.className = "status error";
        msg.textContent = err.message;
      }
    }
    async function openCollectionPaymentForm() {
      const row = requireCollectionRow();
      if (!row) return;
      if (row.tipo_documento !== "FACTURA") return alert("Solo se puede aplicar pago a Facturas.");
      if (!["PENDIENTE","VENCIDA","PENDIENTE_PAGO"].includes(String(row.estado_factura || ""))) return alert("La factura no tiene saldo pendiente.");
      document.body.insertAdjacentHTML("beforeend", `
        <div class="modal-backdrop" id="svcModal">
          <div class="modal small">
            <div class="modal-head"><h2>Aplicar Pago / Nota de Crédito</h2><button class="secondary" onclick="closeModal()">Cerrar</button></div>
            <div class="status">Factura ${esc(row.numero_documento)} · Saldo ${esc(row.moneda)} ${Number(row.saldo_pendiente || row.total || 0).toLocaleString("en-US",{minimumFractionDigits:2, maximumFractionDigits:2})}</div>
            <div class="form-grid">
              <label>Tipo de aplicación<select id="colPayTipo" onchange="toggleCollectionPaymentMode()"><option>PAGO</option><option>NOTA_CREDITO</option></select></label>
              <label class="colPayField">Banco / cuenta<select id="colPayBanco"><option value="">Cargando...</option></select></label>
              <label class="colPayField">Fecha de pago<input id="colPayFecha" type="date" value="${new Date().toISOString().slice(0,10)}" /></label>
              <label class="colPayField">Comisión<input id="colPayComision" type="number" step="0.01" value="0" /></label>
              <label class="colPayField">Referencia<input id="colPayReferencia" /></label>
              <label class="colPayField">Monto a aplicar<input id="colPayMonto" type="number" step="0.01" /></label>
              <label class="colNcField hidden wide">Nota de Crédito disponible<select id="colPayNc"><option value="">Cargando...</option></select></label>
            </div>
            <div class="md-actions"><button class="green" onclick="saveCollectionPayment()">Aplicar</button><button class="secondary" onclick="closeModal()">Cancelar</button></div>
            <div id="colPayMsg" class="status hidden"></div>
          </div>
        </div>`);
      await loadCollectionPaymentBanks();
    }
    function toggleCollectionPaymentMode() {
      const nc = valueFrom("colPayTipo") === "NOTA_CREDITO";
      document.querySelectorAll(".colPayField").forEach(el => el.classList.toggle("hidden", nc));
      document.querySelectorAll(".colNcField").forEach(el => el.classList.toggle("hidden", !nc));
      if (nc) loadCollectionCreditNotes().catch(err => alert(err.message));
    }
    async function loadCollectionPaymentBanks() {
      const select = $("colPayBanco");
      if (!select) return;
      try {
        const rows = rowsList(await getJSON("/accounting/bank-accounts"));
        select.innerHTML = rows.map(row => {
          const code = row.account_code || "";
          const name = row.account_name || "";
          return `<option value="${esc(code)}|${esc(name)}">${esc(code)} - ${esc(name)}</option>`;
        }).join("") || '<option value="">Sin bancos disponibles</option>';
      } catch {
        select.innerHTML = '<option value="">Sin bancos disponibles</option>';
      }
    }
    async function loadCollectionCreditNotes() {
      const row = requireCollectionRow();
      const select = $("colPayNc");
      if (!row || !select) return;
      const payload = await getJSON(`/collections/search?cliente=${encodeURIComponent(row.codigo_cliente)}&estado_factura=PENDIENTE_PAGO&page=1&page_size=200`);
      const notes = rowsList(payload).filter(item => item.tipo_documento === "NOTA_CREDITO");
      select.innerHTML = notes.map(item => `<option value="${esc(item.numero_documento)}">${esc(item.numero_documento)} | ${Number(item.total || 0).toLocaleString("en-US",{minimumFractionDigits:2, maximumFractionDigits:2})}</option>`).join("") || '<option value="">Sin notas disponibles</option>';
    }
    async function saveCollectionPayment() {
      const row = requireCollectionRow();
      const msg = $("colPayMsg");
      msg.className = "status";
      msg.textContent = "Aplicando...";
      try {
        if (valueFrom("colPayTipo") === "NOTA_CREDITO") {
          const nc = valueFrom("colPayNc");
          if (!nc) throw new Error("Seleccione una Nota de Crédito.");
          await postJSON("/collections/aplicar-nota-credito", {
            factura_numero:row.numero_documento,
            nota_credito_numero:nc,
            codigo_cliente:row.codigo_cliente,
            nombre_cliente:row.nombre_cliente
          });
        } else {
          const [bankCode, bankName] = valueFrom("colPayBanco").split("|");
          const monto = Number(valueFrom("colPayMonto") || 0);
          if (!bankCode) throw new Error("Seleccione banco / cuenta contable.");
          if (monto <= 0) throw new Error("Monto inválido.");
          await postJSON("/collections/pago", {
            numero_documento:row.numero_documento,
            codigo_cliente:row.codigo_cliente,
            nombre_cliente:row.nombre_cliente,
            banco:valueFrom("colPayBanco"),
            bank_account_code:bankCode,
            bank_account_name:bankName,
            fecha_pago:valueFrom("colPayFecha"),
            comision:Number(valueFrom("colPayComision") || 0),
            referencia:valueFrom("colPayReferencia"),
            monto_pagado:monto,
            tipo_aplicacion:"PAGO"
          });
        }
        closeModal();
        await loadCollections(collectionPage);
      } catch (err) {
        msg.className = "status error";
        msg.textContent = err.message;
      }
    }
    function renderBankWeb(target=orderCashWorkspace()) {
      target.innerHTML = `
        <div class="panel-head">
          <h2>Bank Reconciliation</h2>
          <span class="muted">Pagos, extractos, matching y cierre bancario</span>
        </div>
        <div class="subtabs">
          <button id="bankTabPayments" class="active" onclick="switchBankPane('payments')">Pagos</button>
          <button id="bankTabStatements" onclick="switchBankPane('statements')">Conciliación profesional</button>
          <button id="bankTabPaid" onclick="switchBankPane('paid')">Paid Invoices Report</button>
        </div>
        <div id="bankPane"></div>`;
      switchBankPane("payments");
    }
    function switchBankPane(pane) {
      ["Payments","Statements","Paid"].forEach(name => $("bankTab" + name)?.classList.remove("active"));
      const map = { payments:"Payments", statements:"Statements", paid:"Paid" };
      $("bankTab" + map[pane])?.classList.add("active");
      if (pane === "statements") renderBankStatementsPane();
      else if (pane === "paid") renderPaidInvoicesPane();
      else renderBankPaymentsPane();
    }
    async function loadBankClienteOptions() {
      await ensureFinanceClientes();
      ["bankCliente"].forEach(id => {
        const el = $(id);
        if (!el || el.options.length > 1) return;
        el.innerHTML = '<option value="">Todos</option>' + financeClienteRows.map(row => {
          const name = financeClientName(row);
          const code = financeClientId(row);
          return `<option value="${esc(code)}">${esc(code)} | ${esc(name)}</option>`;
        }).join("");
      });
    }
    async function loadBankAccountOptions() {
      const select = $("bankStatementAccount");
      if (!select || select.options.length > 1) return;
      try {
        const rows = rowsList(await getJSON("/accounting/bank-accounts"));
        select.innerHTML = '<option value="">Todas</option>' + rows.map(row => {
          const code = row.account_code || "";
          const name = row.account_name || "";
          return `<option value="${esc(code)}" data-name="${esc(name)}">${esc(code)} | ${esc(name)}</option>`;
        }).join("");
      } catch {
        select.innerHTML = '<option value="">Todas</option>';
      }
    }
    function renderBankPaymentsPane() {
      $("bankPane").innerHTML = `
        <div class="finance-filter-row compact">
          <label>Cliente<select id="bankCliente" onfocus="loadBankClienteOptions()" onpointerdown="loadBankClienteOptions()"><option value="">Todos</option></select></label>
          <label>Referencia / comprobante<input id="bankReferencia" placeholder="Referencia bancaria" /></label>
          <label>Ver todos<select id="bankVerTodos"><option value="false">No</option><option value="true">Sí</option></select></label>
          <button onclick="loadBankPayments(1)">Buscar</button>
          <button class="secondary" onclick="clearBankPayments()">Limpiar</button>
        </div>
        <div class="finance-toolbar">
          <button class="green" onclick="openManualBankPaymentForm()">Registrar Pago Manual</button>
          <button onclick="viewBankPaymentDetail()">Ver detalle del pago</button>
          <button class="brown" onclick="reverseSelectedBankPayment()">Reversar pago</button>
          <button class="secondary" onclick="downloadBankPaymentsExcel()">Exportar Excel</button>
        </div>
        <div id="bankPaymentsKpis" class="grid kpis hidden"></div>
        <div id="bankPaymentsMsg" class="status hidden"></div>
        <div id="bankPaymentsTable" class="workspace"><div class="status">Use filtros y presione Buscar para consultar pagos bancarios.</div></div>`;
    }
    function bankPaymentParams(page=1) {
      const params = new URLSearchParams({ page:String(page), page_size:"100" });
      const cliente = valueFrom("bankCliente");
      const ref = valueFrom("bankReferencia");
      const verTodos = valueFrom("bankVerTodos") === "true";
      if (cliente) params.set("codigo_cliente", cliente);
      if (ref) params.set("referencia", ref);
      if (verTodos) params.set("ver_todos", "true");
      return params.toString();
    }
    async function loadBankPayments(page=1) {
      const msg = $("bankPaymentsMsg");
      const table = $("bankPaymentsTable");
      selectedBankIndex = null;
      selectedBankIndexes = new Set();
      msg.className = "status";
      msg.textContent = "Consultando pagos bancarios...";
      table.innerHTML = "";
      try {
        const payload = await getJSON(`/bank-reconciliation?${bankPaymentParams(page)}`);
        bankRowsWeb = rowsList(payload);
        renderBankPaymentKpis();
        renderBankPaymentsTable();
        msg.className = "status hidden";
      } catch (err) {
        msg.className = "status error";
        msg.textContent = err.message;
      }
    }
    function clearBankPayments() {
      bankRowsWeb = [];
      selectedBankIndex = null;
      selectedBankIndexes = new Set();
      if ($("bankCliente")) $("bankCliente").value = "";
      if ($("bankReferencia")) $("bankReferencia").value = "";
      if ($("bankVerTodos")) $("bankVerTodos").value = "false";
      $("bankPaymentsKpis")?.classList.add("hidden");
      if ($("bankPaymentsMsg")) $("bankPaymentsMsg").className = "status hidden";
      if ($("bankPaymentsTable")) $("bankPaymentsTable").innerHTML = '<div class="status">Use filtros y presione Buscar para consultar pagos bancarios.</div>';
    }
    function renderBankPaymentKpis() {
      const kpis = $("bankPaymentsKpis");
      if (!kpis) return;
      const total = bankRowsWeb.reduce((sum,row) => sum + Number(row.monto_pagado || 0), 0);
      const applied = bankRowsWeb.filter(row => String(row.estado || "").toUpperCase().includes("APLIC")).length;
      const incoming = bankRowsWeb.filter(row => String(row.id || "").startsWith("incoming_")).length;
      kpis.classList.remove("hidden");
      kpis.innerHTML = [
        ["Pagos", bankRowsWeb.length, "Registros cargados"],
        ["Monto", money(total), "Monto pagado"],
        ["Aplicados", applied, "Estado aplicado"],
        ["Incoming", incoming, "Pagos no cash_app"]
      ].map(([label,value,hint]) => `<div class="card"><span>${label}</span><strong>${value}</strong><small>${hint}</small></div>`).join("");
    }
    function bankFmt(value) {
      return Number(value || 0).toLocaleString("en-US", {minimumFractionDigits:2, maximumFractionDigits:2});
    }
    function renderBankPaymentsTable() {
      const table = $("bankPaymentsTable");
      if (!table) return;
      if (!bankRowsWeb.length) {
        table.innerHTML = '<div class="status">Sin pagos bancarios para esta consulta.</div>';
        return;
      }
      const cols = ["banco","fecha_pago","nombre_cliente","numero_documento","referencia","tipo_aplicacion","monto_pagado","monto_aplicado","saldo","estado"];
      table.innerHTML = `<div class="table-wrap"><table><thead><tr><th class="pick-col"></th>${cols.map(c => `<th>${esc(c.replace(/_/g," "))}</th>`).join("")}</tr></thead><tbody>${bankRowsWeb.map((row, idx) => {
        const selected = selectedBankIndexes.has(idx);
        return `<tr class="${selected ? "service-selected" : ""}" onclick="toggleBankPaymentRow(${idx})"><td class="pick-col"><input class="row-pick" type="checkbox" ${selected ? "checked" : ""} onclick="event.stopPropagation(); toggleBankPaymentRow(${idx}, this.checked)" /></td>${cols.map(c => `<td>${esc(["monto_pagado","monto_aplicado","saldo"].includes(c) ? bankFmt(row[c]) : row[c])}</td>`).join("")}</tr>`;
      }).join("")}</tbody></table></div>`;
    }
    function toggleBankPaymentRow(idx, checked=null) {
      const next = checked === null ? !selectedBankIndexes.has(idx) : checked;
      selectedBankIndex = setIndexSelection(selectedBankIndexes, idx, next);
      renderBankPaymentsTable();
    }
    function selectedBankPayment() {
      if (selectedBankIndex === null) selectedBankIndex = firstFromSet(selectedBankIndexes);
      return selectedBankIndex === null ? null : bankRowsWeb[selectedBankIndex];
    }
    async function openManualBankPaymentForm() {
      await ensureFinanceClientes();
      $("app").insertAdjacentHTML("beforeend", `
        <div class="modal-backdrop" id="svcModal">
          <div class="modal small">
            <div class="modal-head"><h2>Registrar Pago Manual</h2><button class="secondary" onclick="closeModal()">Cerrar</button></div>
            <div class="form-grid">
              <label>Cliente<select id="bankManualCliente">${financeClienteRows.map(row => {
                const code = financeClientId(row);
                const name = financeClientName(row);
                return `<option value="${esc(code)}" data-name="${esc(name)}">${esc(code)} | ${esc(name)}</option>`;
              }).join("")}</select></label>
              <label>Banco<input id="bankManualBanco" /></label>
              <label>Referencia<input id="bankManualReferencia" /></label>
              <label>Fecha pago<input id="bankManualFecha" type="date" value="${new Date().toISOString().slice(0,10)}" /></label>
              <label>Documento<input id="bankManualDocumento" placeholder="Opcional" /></label>
              <label>Monto<input id="bankManualMonto" type="number" step="0.01" /></label>
            </div>
            <div class="md-actions"><button class="green" onclick="submitManualBankPayment()">Registrar pago</button></div>
            <div id="bankManualMsg" class="status hidden"></div>
          </div>
        </div>`);
    }
    async function submitManualBankPayment() {
      const msg = $("bankManualMsg");
      msg.className = "status";
      msg.textContent = "Registrando...";
      try {
        const select = $("bankManualCliente");
        const amount = Number(valueFrom("bankManualMonto") || 0);
        if (!valueFrom("bankManualCliente")) throw new Error("Seleccione cliente.");
        if (!valueFrom("bankManualBanco")) throw new Error("Ingrese banco.");
        if (!valueFrom("bankManualReferencia")) throw new Error("Ingrese referencia.");
        if (!valueFrom("bankManualFecha")) throw new Error("Ingrese fecha de pago.");
        if (amount <= 0) throw new Error("Monto inválido.");
        await postJSON("/incoming-payments", {
          origen:"MANUAL",
          codigo_cliente:valueFrom("bankManualCliente"),
          nombre_cliente:select?.selectedOptions?.[0]?.dataset?.name || "",
          banco:valueFrom("bankManualBanco"),
          numero_referencia:valueFrom("bankManualReferencia"),
          fecha_pago:valueFrom("bankManualFecha"),
          documento:valueFrom("bankManualDocumento") || null,
          monto:amount
        });
        closeModal();
        await loadBankPayments(1);
      } catch (err) {
        msg.className = "status error";
        msg.textContent = err.message;
      }
    }
    function viewBankPaymentDetail() {
      const row = selectedBankPayment();
      if (!row) return alert("Seleccione un pago.");
      $("app").insertAdjacentHTML("beforeend", `
        <div class="modal-backdrop" id="svcModal">
          <div class="modal">
            <div class="modal-head"><h2>Detalle de Pago</h2><button class="secondary" onclick="closeModal()">Cerrar</button></div>
            <div class="table-wrap"><table><tbody>${Object.keys(row).filter(k => !String(k).toLowerCase().includes("hash")).map(k => `<tr><th>${esc(k)}</th><td>${esc(row[k])}</td></tr>`).join("")}</tbody></table></div>
          </div>
        </div>`);
    }
    async function reverseSelectedBankPayment() {
      const row = selectedBankPayment();
      if (!row) return alert("Seleccione un pago.");
      const rawId = String(row.id || "");
      const id = rawId.startsWith("incoming_") ? rawId.replace("incoming_", "") : rawId;
      const reason = prompt("Motivo de reversa", "WRONG_PAYMENT");
      if (!reason) return;
      const comment = prompt("Comentario / soporte de reversa", "");
      if (!comment) return alert("Comentario requerido.");
      if (!confirm(`¿Reversar pago ${rawId}? Esta acción elimina el registro de pago.`)) return;
      try {
        await postJSON(`/bank-reconciliation/${encodeURIComponent(id)}/reverse`, { reason, comment });
        await loadBankPayments(1);
      } catch (err) {
        alert(err.message);
      }
    }
    function downloadBankPaymentsExcel() {
      if (!bankRowsWeb.length) return alert("No hay datos para exportar.");
      const cols = ["id","banco","fecha_pago","codigo_cliente","nombre_cliente","numero_documento","referencia","tipo_aplicacion","monto_pagado","monto_aplicado","saldo","estado"];
      downloadExcelFile(`bank_reconciliation_${new Date().toISOString().slice(0,10)}.xls`, bankRowsWeb, cols, "Bank Reconciliation - pagos");
    }
    function renderPaidInvoicesPane() {
      $("bankPane").innerHTML = `
        <div class="finance-filter-row">
          <label>Año<input id="paidYear" value="${esc($("year")?.value || new Date().getFullYear())}" /></label>
          <label>Mes<select id="paidMonth"><option value="">Todos</option>${Array.from({length:12},(_,i)=>`<option value="${i+1}">${String(i+1).padStart(2,"0")}</option>`).join("")}</select></label>
          <label>Desde<input id="paidFrom" type="date" /></label>
          <label>Hasta<input id="paidTo" type="date" /></label>
          <label>Cliente<input id="paidCliente" placeholder="Cliente o código" /></label>
          <button onclick="loadPaidInvoicesReport()">Buscar</button>
          <button class="secondary" onclick="clearPaidInvoicesReport()">Limpiar</button>
        </div>
        <div class="finance-toolbar"><button class="secondary" onclick="downloadPaidInvoicesExcel()">Exportar Excel</button></div>
        <div id="paidInvoicesKpis" class="grid kpis hidden"></div>
        <div id="paidInvoicesTable" class="workspace"><div class="status">Configure filtros y presione Buscar.</div></div>`;
    }
    let paidInvoiceRows = [];
    function paidInvoiceParams() {
      const params = new URLSearchParams({ page:"1", page_size:"1000" });
      [["paidYear","year"],["paidMonth","month"],["paidFrom","date_from"],["paidTo","date_to"],["paidCliente","cliente"]].forEach(([id,key]) => {
        const value = valueFrom(id);
        if (value) params.set(key, value);
      });
      return params.toString();
    }
    async function loadPaidInvoicesReport() {
      const table = $("paidInvoicesTable");
      selectedPaidInvoiceIndexes = new Set();
      table.innerHTML = '<div class="status">Consultando facturas pagadas...</div>';
      try {
        const payload = await getJSON(`/bank-reconciliation/paid-invoices-report?${paidInvoiceParams()}`);
        paidInvoiceRows = rowsList(payload);
        const summary = payload.summary || {};
        const kpis = $("paidInvoicesKpis");
        kpis.classList.remove("hidden");
        kpis.innerHTML = [
          ["Facturas", summary.total_facturas || 0, "Documentos pagados"],
          ["Clientes", summary.total_clientes || 0, "Clientes únicos"],
          ["Pagado", money(summary.total_pagado || 0), "Monto pagado"],
          ["Comisiones", money(summary.total_comision || 0), "Comisiones"]
        ].map(([label,value,hint]) => `<div class="card"><span>${label}</span><strong>${value}</strong><small>${hint}</small></div>`).join("");
        renderPaidInvoicesTable();
      } catch (err) {
        table.innerHTML = `<div class="status error">${esc(err.message)}</div>`;
      }
    }
    function renderPaidInvoicesTable() {
      const table = $("paidInvoicesTable");
      if (!paidInvoiceRows.length) {
        table.innerHTML = '<div class="status">Sin facturas pagadas para esta consulta.</div>';
        return;
      }
      const cols = ["numero_documento","nombre_cliente","fecha_pago","monto_pagado","comision","banco","referencia","estado_factura","source"];
      table.innerHTML = `<div class="table-wrap"><table><thead><tr><th class="pick-col"></th>${cols.map(c => `<th>${esc(c.replace(/_/g," "))}</th>`).join("")}</tr></thead><tbody>${paidInvoiceRows.map((row, idx) => {
        const selected = selectedPaidInvoiceIndexes.has(idx);
        return `<tr class="${selected ? "service-selected" : ""}" onclick="togglePaidInvoiceRow(${idx})"><td class="pick-col"><input class="row-pick" type="checkbox" ${selected ? "checked" : ""} onclick="event.stopPropagation(); togglePaidInvoiceRow(${idx}, this.checked)" /></td>${cols.map(c => `<td>${esc(["monto_pagado","comision"].includes(c) ? bankFmt(row[c]) : row[c])}</td>`).join("")}</tr>`;
      }).join("")}</tbody></table></div>`;
    }
    function togglePaidInvoiceRow(idx, checked=null) {
      const next = checked === null ? !selectedPaidInvoiceIndexes.has(idx) : checked;
      setIndexSelection(selectedPaidInvoiceIndexes, idx, next);
      renderPaidInvoicesTable();
    }
    function clearPaidInvoicesReport() {
      paidInvoiceRows = [];
      selectedPaidInvoiceIndexes = new Set();
      ["paidYear","paidMonth","paidFrom","paidTo","paidCliente"].forEach(id => { if ($(id)) $(id).value = id === "paidYear" ? ($("year")?.value || "") : ""; });
      $("paidInvoicesKpis")?.classList.add("hidden");
      if ($("paidInvoicesTable")) $("paidInvoicesTable").innerHTML = '<div class="status">Configure filtros y presione Buscar.</div>';
    }
    function downloadPaidInvoicesExcel() {
      if (!paidInvoiceRows.length) return alert("No hay datos para exportar.");
      const cols = ["source","payment_id","numero_documento","codigo_cliente","nombre_cliente","banco","fecha_pago","comision","referencia","monto_pagado","tipo_aplicacion","estado_factura","total_factura","saldo_pendiente"];
      downloadExcelFile(`paid_invoices_${new Date().toISOString().slice(0,10)}.xls`, paidInvoiceRows, cols, "Paid Invoices Report");
    }
    function renderBankStatementsPane() {
      $("bankPane").innerHTML = `
        <div class="finance-filter-row">
          <label>Cuenta contable<select id="bankStatementAccount" onfocus="loadBankAccountOptions()" onpointerdown="loadBankAccountOptions()"><option value="">Todas</option></select></label>
          <label>Moneda<select id="bankStatementCurrency"><option value="">Todas</option><option>CRC</option><option>USD</option></select></label>
          <label>Periodo<input id="bankStatementPeriod" value="${new Date().toISOString().slice(0,7)}" placeholder="YYYY-MM" /></label>
          <label>Status<select id="bankStatementStatus"><option value="">Todos</option><option>OPEN</option><option>MATCHED</option><option>CLOSED</option><option>REOPENED</option></select></label>
          <button onclick="loadBankStatements()">Buscar extractos</button>
          <button class="secondary" onclick="clearBankStatements()">Limpiar</button>
        </div>
        <div class="finance-toolbar">
          <button id="bankBtnLines" onclick="loadBankStatementLines()" disabled>Ver líneas</button>
          <button id="bankBtnMatch" class="green" onclick="autoMatchSelectedStatement()" disabled>Matching automático</button>
          <button id="bankBtnFee" class="brown" onclick="markSelectedBankLineFee()" disabled>Cargo bancario</button>
          <button id="bankBtnClose" onclick="closeSelectedBankStatement()" disabled>Cerrar conciliación</button>
          <button class="secondary" onclick="openBankImportCsv()">Importar CSV</button>
          <button id="bankBtnExportLines" class="secondary" onclick="downloadBankStatementLinesExcel()" disabled>Exportar líneas Excel</button>
        </div>
        <div id="bankStatementMsg" class="status hidden"></div>
        <div id="bankStatementsTable" class="workspace"><div class="status">Presione Buscar extractos para cargar conciliaciones.</div></div>
        <div id="bankStatementLinesTable" class="workspace hidden"></div>`;
      syncBankStatementActions();
    }
    function bankStatementParams() {
      const params = new URLSearchParams();
      const account = valueFrom("bankStatementAccount");
      const currency = valueFrom("bankStatementCurrency");
      const period = valueFrom("bankStatementPeriod");
      const status = valueFrom("bankStatementStatus");
      if (account) params.set("bank_account_code", account);
      if (currency) params.set("currency_code", currency);
      if (period) params.set("period", period);
      if (status) params.set("status", status);
      return params.toString();
    }
    function showBankStatementMsg(message, isError=false) {
      const msg = $("bankStatementMsg");
      if (!msg) return;
      msg.className = isError ? "status error" : "status";
      msg.textContent = message;
    }
    function clearBankStatementMsg() {
      const msg = $("bankStatementMsg");
      if (!msg) return;
      msg.className = "status hidden";
      msg.textContent = "";
    }
    function syncBankStatementActions() {
      const hasStatement = !!(selectedBankStatementId || firstFromSet(selectedBankStatementIds));
      const hasLine = selectedBankLineIndex !== null || firstFromSet(selectedBankLineIndexes) !== null;
      ["bankBtnLines","bankBtnMatch","bankBtnClose"].forEach(id => { if ($(id)) $(id).disabled = !hasStatement; });
      if ($("bankBtnFee")) $("bankBtnFee").disabled = !hasLine;
      if ($("bankBtnExportLines")) $("bankBtnExportLines").disabled = !bankStatementLineRows.length;
    }
    async function loadBankStatements() {
      const msg = $("bankStatementMsg");
      msg.className = "status";
      msg.textContent = "Consultando extractos...";
      selectedBankStatementId = null;
      selectedBankStatementIds = new Set();
      bankStatementLineRows = [];
      selectedBankLineIndex = null;
      selectedBankLineIndexes = new Set();
      try {
        const payload = await getJSON(`/bank-reconciliation/statements?${bankStatementParams()}`);
        bankStatementRows = rowsList(payload);
        renderBankStatementsTable();
        if (!bankStatementRows.length) {
          clearBankStatementMsg();
          $("bankStatementLinesTable").classList.add("hidden");
          $("bankStatementLinesTable").innerHTML = "";
        } else {
          clearBankStatementMsg();
          $("bankStatementLinesTable").classList.remove("hidden");
          $("bankStatementLinesTable").innerHTML = '<div class="status">Seleccione un extracto y presione Ver líneas.</div>';
        }
        syncBankStatementActions();
      } catch (err) {
        msg.className = "status error";
        msg.textContent = err.message;
        syncBankStatementActions();
      }
    }
    function renderBankStatementsTable() {
      const table = $("bankStatementsTable");
      if (!bankStatementRows.length) {
        table.innerHTML = '<div class="status">Sin extractos para esta consulta. Cambie filtros o importe un CSV.</div>';
        return;
      }
      const cols = ["id","bank_name","bank_account_code","currency_code","statement_period","status","line_count","open_count","statement_total","matched_total","open_total"];
      table.innerHTML = `<div class="table-wrap"><table><thead><tr><th class="pick-col"></th>${cols.map(c => `<th>${esc(c.replace(/_/g," "))}</th>`).join("")}</tr></thead><tbody>${bankStatementRows.map(row => {
        const id = Number(row.id);
        const selected = selectedBankStatementIds.has(id);
        return `<tr class="${selected ? "service-selected" : ""}" onclick="toggleBankStatementRow(${id})"><td class="pick-col"><input class="row-pick" type="checkbox" ${selected ? "checked" : ""} onclick="event.stopPropagation(); toggleBankStatementRow(${id}, this.checked)" /></td>${cols.map(c => `<td>${esc(["statement_total","matched_total","open_total"].includes(c) ? bankFmt(row[c]) : row[c])}</td>`).join("")}</tr>`;
      }).join("")}</tbody></table></div>`;
    }
    function toggleBankStatementRow(id, checked=null) {
      const next = checked === null ? !selectedBankStatementIds.has(id) : checked;
      selectedBankStatementId = setIndexSelection(selectedBankStatementIds, id, next);
      clearBankStatementMsg();
      renderBankStatementsTable();
      syncBankStatementActions();
    }
    async function loadBankStatementLines() {
      if (!selectedBankStatementId) selectedBankStatementId = firstFromSet(selectedBankStatementIds);
      if (!selectedBankStatementId) {
        showBankStatementMsg("Seleccione un extracto de la tabla antes de ver líneas.", true);
        syncBankStatementActions();
        return;
      }
      const table = $("bankStatementLinesTable");
      table.classList.remove("hidden");
      table.innerHTML = '<div class="status">Consultando líneas...</div>';
      selectedBankLineIndex = null;
      selectedBankLineIndexes = new Set();
      try {
        const payload = await getJSON(`/bank-reconciliation/statements/${encodeURIComponent(selectedBankStatementId)}/lines`);
        bankStatementLineRows = rowsList(payload);
        renderBankStatementLinesTable();
        clearBankStatementMsg();
        syncBankStatementActions();
      } catch (err) {
        table.innerHTML = `<div class="status error">${esc(err.message)}</div>`;
        showBankStatementMsg(err.message, true);
        syncBankStatementActions();
      }
    }
    function renderBankStatementLinesTable() {
      const table = $("bankStatementLinesTable");
      if (!bankStatementLineRows.length) {
        table.innerHTML = '<div class="status">Sin líneas para este extracto.</div>';
        return;
      }
      const cols = ["id","line_date","reference","description","debit","credit","amount","match_status","matched_source","matched_id","difference"];
      table.innerHTML = `<div class="table-wrap"><table><thead><tr><th class="pick-col"></th>${cols.map(c => `<th>${esc(c.replace(/_/g," "))}</th>`).join("")}</tr></thead><tbody>${bankStatementLineRows.map((row,idx) => {
        const selected = selectedBankLineIndexes.has(idx);
        return `<tr class="${selected ? "service-selected" : ""}" onclick="toggleBankStatementLineRow(${idx})"><td class="pick-col"><input class="row-pick" type="checkbox" ${selected ? "checked" : ""} onclick="event.stopPropagation(); toggleBankStatementLineRow(${idx}, this.checked)" /></td>${cols.map(c => `<td>${esc(["debit","credit","amount","difference"].includes(c) ? bankFmt(row[c]) : row[c])}</td>`).join("")}</tr>`;
      }).join("")}</tbody></table></div>`;
    }
    function toggleBankStatementLineRow(idx, checked=null) {
      const next = checked === null ? !selectedBankLineIndexes.has(idx) : checked;
      selectedBankLineIndex = setIndexSelection(selectedBankLineIndexes, idx, next);
      renderBankStatementLinesTable();
      syncBankStatementActions();
    }
    async function autoMatchSelectedStatement() {
      if (!selectedBankStatementId) selectedBankStatementId = firstFromSet(selectedBankStatementIds);
      if (!selectedBankStatementId) {
        showBankStatementMsg("Seleccione un extracto de la tabla antes de ejecutar matching automático.", true);
        syncBankStatementActions();
        return;
      }
      const tolerance = prompt("Tolerancia de matching", "1.00");
      if (tolerance === null) return;
      try {
        const statementId = selectedBankStatementId;
        const result = await postJSON(`/bank-reconciliation/statements/${encodeURIComponent(selectedBankStatementId)}/auto-match`, { tolerance:Number(tolerance || 0) });
        await loadBankStatements();
        selectedBankStatementId = statementId;
        selectedBankStatementIds = new Set([statementId]);
        renderBankStatementsTable();
        await loadBankStatementLines();
        showBankStatementMsg(`Matching terminado. Matcheadas: ${result.matched || 0}. Diferencias: ${result.differences || 0}.`, false);
        syncBankStatementActions();
      } catch (err) {
        showBankStatementMsg(err.message, true);
        syncBankStatementActions();
      }
    }
    async function markSelectedBankLineFee() {
      if (selectedBankLineIndex === null) selectedBankLineIndex = firstFromSet(selectedBankLineIndexes);
      const row = selectedBankLineIndex === null ? null : bankStatementLineRows[selectedBankLineIndex];
      if (!row) {
        showBankStatementMsg("Seleccione una línea del extracto antes de marcar cargo bancario.", true);
        syncBankStatementActions();
        return;
      }
      const note = prompt("Nota del cargo bancario", "Cargo bancario identificado");
      if (note === null) return;
      try {
        await postJSON(`/bank-reconciliation/lines/${encodeURIComponent(row.id)}/bank-fee`, { note });
        await loadBankStatementLines();
        showBankStatementMsg("Cargo bancario marcado correctamente.", false);
      } catch (err) {
        showBankStatementMsg(err.message, true);
        syncBankStatementActions();
      }
    }
    async function closeSelectedBankStatement() {
      if (!selectedBankStatementId) selectedBankStatementId = firstFromSet(selectedBankStatementIds);
      if (!selectedBankStatementId) {
        showBankStatementMsg("Seleccione un extracto de la tabla antes de cerrar conciliación.", true);
        syncBankStatementActions();
        return;
      }
      const note = prompt("Nota de cierre", "");
      if (note === null) return;
      const force = confirm("Si quedan partidas abiertas, ¿forzar cierre documentado?");
      try {
        await postJSON(`/bank-reconciliation/statements/${encodeURIComponent(selectedBankStatementId)}/close`, { note, force_close:force });
        await loadBankStatements();
        $("bankStatementLinesTable").classList.add("hidden");
        $("bankStatementLinesTable").innerHTML = "";
        showBankStatementMsg("Conciliación cerrada correctamente.", false);
        syncBankStatementActions();
      } catch (err) {
        showBankStatementMsg(err.message, true);
        syncBankStatementActions();
      }
    }
    function clearBankStatements() {
      bankStatementRows = [];
      bankStatementLineRows = [];
      selectedBankStatementId = null;
      selectedBankStatementIds = new Set();
      selectedBankLineIndex = null;
      selectedBankLineIndexes = new Set();
      ["bankStatementAccount","bankStatementCurrency","bankStatementStatus"].forEach(id => { if ($(id)) $(id).value = ""; });
      if ($("bankStatementPeriod")) $("bankStatementPeriod").value = new Date().toISOString().slice(0,7);
      if ($("bankStatementsTable")) $("bankStatementsTable").innerHTML = '<div class="status">Presione Buscar extractos para cargar conciliaciones.</div>';
      if ($("bankStatementLinesTable")) {
        $("bankStatementLinesTable").classList.add("hidden");
        $("bankStatementLinesTable").innerHTML = "";
      }
      if ($("bankStatementMsg")) $("bankStatementMsg").className = "status hidden";
      syncBankStatementActions();
    }
    function downloadBankStatementLinesExcel() {
      if (!bankStatementLineRows.length) return alert("No hay líneas para exportar.");
      const cols = ["id","line_date","reference","description","debit","credit","amount","currency_code","match_status","matched_source","matched_id","matched_entry_id","difference"];
      downloadExcelFile(`bank_statement_lines_${selectedBankStatementId || "all"}_${new Date().toISOString().slice(0,10)}.xls`, bankStatementLineRows, cols, "Bank Statement Lines");
    }
    function parseBankCsv(text) {
      const lines = text.split(/\\r?\\n/).filter(line => line.trim());
      if (lines.length < 2) return [];
      const split = line => line.split(",").map(cell => cell.trim().replace(/^"|"$/g, ""));
      const headers = split(lines[0]).map(h => h.toLowerCase());
      return lines.slice(1).map(line => {
        const values = split(line);
        const row = Object.fromEntries(headers.map((h,i) => [h, values[i] || ""]));
        const pick = (...names) => names.map(n => row[n]).find(v => v !== undefined && v !== "");
        return {
          line_date:String(pick("fecha","date","line_date","fecha pago","fecha_pago") || "").slice(0,10),
          description:pick("descripcion","description","detalle","concepto") || "",
          reference:pick("referencia","reference","comprobante","numero","documento") || "",
          debit:Number(String(pick("debito","debit","retiro","withdrawal") || 0).replace(/,/g,"")) || 0,
          credit:Number(String(pick("credito","credit","deposito","deposit") || 0).replace(/,/g,"")) || 0,
          amount:Number(String(pick("monto","amount","importe") || 0).replace(/,/g,"")) || 0,
          currency_code:valueFrom("bankStatementCurrency") || "CRC"
        };
      }).filter(row => row.line_date);
    }
    function openBankImportCsv() {
      $("app").insertAdjacentHTML("beforeend", `
        <div class="modal-backdrop" id="svcModal">
          <div class="modal small">
            <div class="modal-head"><h2>Importar extracto CSV</h2><button class="secondary" onclick="closeModal()">Cerrar</button></div>
            <div class="form-grid">
              <label>Banco<input id="bankImportName" placeholder="Banco" /></label>
              <label>Periodo<input id="bankImportPeriod" value="${esc(valueFrom("bankStatementPeriod") || new Date().toISOString().slice(0,7))}" /></label>
              <label>Moneda<select id="bankImportCurrency"><option${valueFrom("bankStatementCurrency") === "CRC" ? " selected" : ""}>CRC</option><option${valueFrom("bankStatementCurrency") === "USD" ? " selected" : ""}>USD</option></select></label>
              <label class="wide">CSV<input id="bankImportFile" type="file" accept=".csv,text/csv" /></label>
            </div>
            <div class="md-actions"><button onclick="submitBankImportCsv()">Importar</button></div>
            <div id="bankImportMsg" class="status hidden"></div>
          </div>
        </div>`);
    }
    async function submitBankImportCsv() {
      const msg = $("bankImportMsg");
      msg.className = "status";
      msg.textContent = "Importando...";
      try {
        const file = $("bankImportFile")?.files?.[0];
        if (!file) throw new Error("Seleccione un CSV.");
        const text = await file.text();
        const rows = parseBankCsv(text);
        if (!rows.length) throw new Error("CSV sin líneas válidas.");
        const account = $("bankStatementAccount")?.selectedOptions?.[0];
        const result = await postJSON("/bank-reconciliation/statements/import", {
          bank_name:valueFrom("bankImportName") || account?.dataset?.name || "Banco",
          bank_account_code:valueFrom("bankStatementAccount") || null,
          bank_account_name:account?.dataset?.name || null,
          currency_code:valueFrom("bankImportCurrency") || "CRC",
          statement_period:valueFrom("bankImportPeriod"),
          statement_date:new Date().toISOString().slice(0,10),
          source_filename:file.name,
          rows
        });
        closeModal();
        alert(`Extracto importado. Líneas: ${result.inserted || 0}. Omitidas: ${result.skipped || 0}.`);
        await loadBankStatements();
      } catch (err) {
        msg.className = "status error";
        msg.textContent = err.message;
      }
    }
    function renderDisputesWeb(target=orderCashWorkspace()) {
      target.innerHTML = `
        <div class="panel-head">
          <h2>Disputes</h2>
          <span class="muted">Gestión de disputas de facturación y cobro</span>
        </div>
        <div class="finance-filter-row compact">
          <label>Cliente<select id="disputeCliente" onpointerdown="loadFinanceClientCombos()" onfocus="loadFinanceClientCombos()"><option value="">Todos</option></select></label>
          <label>Status<select id="disputeStatus"><option value="">Todos</option>${DISPUTE_STATUSES.map(s => `<option>${esc(s)}</option>`).join("")}</select></label>
          <button onclick="loadDisputes()">Buscar</button>
          <button class="secondary" onclick="clearDisputes()">Limpiar</button>
        </div>
        <div class="finance-toolbar">
          <button onclick="openSelectedDisputeManagement()">Gestionar Disputa</button>
          <button class="secondary" onclick="openSelectedDisputeHistory()">Ver historial</button>
          <button class="secondary" onclick="downloadDisputesExcel()">Exportar Excel</button>
        </div>
        <div id="disputesKpis" class="grid kpis hidden"></div>
        <div id="disputesMsg" class="status hidden"></div>
        <div id="disputesTable" class="workspace"><div class="status">Seleccione filtros y presione Buscar para consultar Disputes.</div></div>`;
    }
    function disputeParams() {
      const params = new URLSearchParams({ page:"1", page_size:"100" });
      const cliente = valueFrom("disputeCliente");
      if (cliente) params.set("cliente", cliente);
      return params.toString();
    }
    async function loadDisputes() {
      const msg = $("disputesMsg");
      const table = $("disputesTable");
      selectedDisputeIndex = null;
      selectedDisputeIndexes = new Set();
      disputeHistoryRows = [];
      msg.className = "status";
      msg.textContent = "Consultando Disputes...";
      try {
        await loadFinanceClientCombos();
        const [payload, kpis] = await Promise.all([
          getJSON(`/dispute-management?${disputeParams()}`),
          getJSON("/dispute-management/kpis/summary").catch(() => null)
        ]);
        const status = valueFrom("disputeStatus");
        disputeRows = rowsList(payload).filter(row => !status || String(row.status || "New") === status);
        msg.classList.add("hidden");
        renderDisputesKpis(kpis);
        renderDisputesTable();
      } catch (err) {
        disputeRows = [];
        table.innerHTML = "";
        msg.className = "status error";
        msg.textContent = err.message;
      }
    }
    function clearDisputes() {
      ["disputeCliente","disputeStatus"].forEach(id => { if ($(id)) $(id).value = ""; });
      disputeRows = [];
      disputeHistoryRows = [];
      selectedDisputeIndex = null;
      selectedDisputeIndexes = new Set();
      $("disputesKpis")?.classList.add("hidden");
      $("disputesMsg")?.classList.add("hidden");
      if ($("disputesTable")) $("disputesTable").innerHTML = '<div class="status">Seleccione filtros y presione Buscar para consultar Disputes.</div>';
    }
    function renderDisputesKpis(kpis) {
      const host = $("disputesKpis");
      if (!host) return;
      const totals = kpis || {};
      host.classList.remove("hidden");
      host.innerHTML = [
        ["ADO", totals.ADO ?? 0, "Días promedio abiertos"],
        ["DDO", totals.DDO ?? 0, "Días promedio resueltos"],
        ["Incoming", totals.IncomingVolume ?? 0, "Disputas del mes"],
        ["Disputed", Number(totals.DisputedAmount || 0).toLocaleString("en-US", { minimumFractionDigits:2, maximumFractionDigits:2 }), "Monto disputado abierto"]
      ].map(([label,value,hint]) => `<div class="card kpi"><span>${esc(label)}</span><strong>${esc(value)}</strong><small>${esc(hint)}</small></div>`).join("");
    }
    function disputeRow() {
      if (selectedDisputeIndex === null) selectedDisputeIndex = firstFromSet(selectedDisputeIndexes);
      return selectedDisputeIndex === null ? null : disputeRows[selectedDisputeIndex];
    }
    function requireDisputeRow() {
      const row = disputeRow();
      if (!row) alert("Seleccione primero una disputa.");
      return row;
    }
    function disputeStatusBadge(status) {
      const text = status || "New";
      const cls = text === "Resolved" ? "closed" : (text === "Written Off" ? "cancel" : "open");
      return `<span class="badge ${cls}">${esc(text)}</span>`;
    }
    function renderDisputesTable() {
      const table = $("disputesTable");
      const cols = ["dispute_case","numero_documento","codigo_cliente","nombre_cliente","fecha_factura","fecha_vencimiento","monto","status","motivo","comentario","buque_contenedor","operacion","periodo_operacion","descripcion_servicio","created_at"];
      if (!disputeRows.length) {
        table.innerHTML = '<div class="status">Sin disputas para los filtros seleccionados.</div>';
        return;
      }
      table.innerHTML = `
        <div class="table-wrap"><table><thead><tr><th class="pick-col"></th>${cols.map(c => `<th>${esc(c.replace(/_/g," "))}</th>`).join("")}</tr></thead>
        <tbody>${disputeRows.map((row, idx) => {
          const selected = selectedDisputeIndexes.has(idx);
          return `<tr class="${selected ? "service-selected" : ""}" onclick="toggleDisputeRow(${idx})">
            <td class="pick-col"><input class="row-pick" type="checkbox" ${selected ? "checked" : ""} onclick="event.stopPropagation(); toggleDisputeRow(${idx}, this.checked)" /></td>
            ${cols.map(c => `<td>${c === "status" ? disputeStatusBadge(row[c]) : esc(c === "monto" ? Number(row[c] || 0).toLocaleString("en-US", { minimumFractionDigits:2, maximumFractionDigits:2 }) : row[c])}</td>`).join("")}
          </tr>`;
        }).join("")}</tbody></table></div>`;
    }
    function toggleDisputeRow(idx, checked=null) {
      const next = checked === null ? !selectedDisputeIndexes.has(idx) : checked;
      selectedDisputeIndex = setIndexSelection(selectedDisputeIndexes, idx, next);
      renderDisputesTable();
    }
    async function ensureDisputeManagement(row) {
      const info = await postJSON(`/dispute-management/from-dispute/${encodeURIComponent(row.dispute_id)}`, {});
      row.management_id = info.management_id;
      row.status = info.status || row.status || "New";
      return info;
    }
    async function loadDisputeHistory(managementId) {
      disputeHistoryRows = rowsList(await getJSON(`/dispute-management/${encodeURIComponent(managementId)}/history`));
      return disputeHistoryRows;
    }
    function renderDisputeHistoryRows(rows) {
      if (!rows.length) return '<div class="status">Sin historial registrado.</div>';
      return `<div class="table-wrap"><table><thead><tr><th>Fecha</th><th>Usuario</th><th>Comentario</th></tr></thead><tbody>${rows.map(row => `<tr><td>${esc(row.created_at)}</td><td>${esc(row.created_by)}</td><td>${esc(row.comentario)}</td></tr>`).join("")}</tbody></table></div>`;
    }
    async function openSelectedDisputeManagement() {
      const row = requireDisputeRow();
      if (!row) return;
      try {
        const info = await ensureDisputeManagement(row);
        const history = await loadDisputeHistory(info.management_id);
        document.body.insertAdjacentHTML("beforeend", `
          <div class="modal-backdrop" id="svcModal">
            <div class="modal">
              <div class="modal-head"><h2>Dispute Management</h2><button class="secondary" onclick="closeModal()">Cerrar</button></div>
              <div class="status">Dispute ${esc(row.dispute_case || row.dispute_id)} · Management ID ${esc(info.management_id)} · ${esc(row.nombre_cliente || "")} · ${Number(row.monto || 0).toLocaleString("en-US", { minimumFractionDigits:2, maximumFractionDigits:2 })}</div>
              <div class="form-grid">
                <label>Status<select id="disputeMgmtStatus">${DISPUTE_STATUSES.map(s => `<option${s === (info.status || row.status) ? " selected" : ""}>${esc(s)}</option>`).join("")}</select></label>
                <label class="wide">Nuevo comentario<textarea id="disputeMgmtComment"></textarea></label>
              </div>
              <h3>Historial</h3>
              <div id="disputeHistoryTable">${renderDisputeHistoryRows(history)}</div>
              <div class="md-actions"><button class="green" onclick="saveDisputeStatus(${Number(info.management_id)})">Guardar cambios</button><button class="secondary" onclick="closeModal()">Cancelar</button></div>
              <div id="disputeMgmtMsg" class="status hidden"></div>
            </div>
          </div>`);
      } catch (err) {
        alert(err.message);
      }
    }
    async function saveDisputeStatus(managementId) {
      const msg = $("disputeMgmtMsg");
      msg.className = "status";
      msg.textContent = "Guardando status...";
      try {
        await postJSON(`/dispute-management/${encodeURIComponent(managementId)}/status`, {
          status:valueFrom("disputeMgmtStatus"),
          comentario:valueFrom("disputeMgmtComment"),
          user:session?.usuario || "SOM-WEB"
        });
        closeModal();
        await loadDisputes();
      } catch (err) {
        msg.className = "status error";
        msg.textContent = err.message;
      }
    }
    async function openSelectedDisputeHistory() {
      const row = requireDisputeRow();
      if (!row) return;
      try {
        const info = await ensureDisputeManagement(row);
        const history = await loadDisputeHistory(info.management_id);
        document.body.insertAdjacentHTML("beforeend", `
          <div class="modal-backdrop" id="svcModal">
            <div class="modal">
              <div class="modal-head"><h2>Historial de disputa</h2><button class="secondary" onclick="closeModal()">Cerrar</button></div>
              <div class="status">Dispute ${esc(row.dispute_case || row.dispute_id)} · ${esc(row.numero_documento || "")}</div>
              ${renderDisputeHistoryRows(history)}
            </div>
          </div>`);
      } catch (err) {
        alert(err.message);
      }
    }
    function downloadDisputesExcel() {
      if (!disputeRows.length) return alert("No hay datos para exportar.");
      const cols = ["management_id","dispute_id","dispute_case","numero_documento","codigo_cliente","nombre_cliente","fecha_factura","fecha_vencimiento","monto","status","motivo","comentario","buque_contenedor","operacion","periodo_operacion","descripcion_servicio","ultimo_comentario","created_at"];
      downloadExcelFile(`disputes_${new Date().toISOString().slice(0,10)}.xls`, disputeRows, cols, "Disputes - detalle");
    }
    async function ensureFinanceClientes() {
      if (financeClientes.length) return financeClientes;
      const payload = await getJSON("/clientes?page=1&page_size=500").catch(() => ({ data:[] }));
      financeClienteRows = rowsList(payload);
      financeClientes = financeClienteRows.map(c => c.nombrecomercial || c.NombreComercial || c.nombrejuridico || c.NombreJuridico || c.codigo || c.Codigo).filter(Boolean);
      return financeClientes;
    }
    function financeClientName(row) {
      return row?.nombrecomercial || row?.NombreComercial || row?.nombrejuridico || row?.NombreJuridico || row?.cliente || "";
    }
    function financeClientId(row) {
      return row?.codigo || row?.Codigo || row?.codigo_cliente || "";
    }
    function financeClientCode(name) {
      const row = financeClienteRows.find(c => [c.nombrecomercial, c.NombreComercial, c.nombrejuridico, c.NombreJuridico, c.codigo, c.Codigo].filter(Boolean).includes(name));
      return row?.codigo || row?.Codigo || "";
    }
    async function loadFinanceClientCombos() {
      await ensureFinanceClientes();
      ["billableCliente","billingCliente"].forEach(id => {
        const el = $(id);
        if (el && el.tagName === "SELECT" && el.options.length <= 1) {
          el.innerHTML = '<option value="">Todos</option>' + financeClienteRows.map(row => {
            const name = financeClientName(row);
            return `<option value="${esc(name)}">${esc(financeClientId(row))} | ${esc(name)}</option>`;
          }).join("");
          if (!financeClienteRows.length) el.innerHTML = '<option value="">Sin clientes disponibles</option>';
        }
      });
      const credit = $("creditCliente");
      if (credit && credit.options.length <= 1) {
        credit.innerHTML = '<option value="">Todos</option>' + financeClienteRows.map(row => {
          const code = financeClientId(row);
          const name = financeClientName(row);
          return `<option value="${esc(code)}">${esc(code)} | ${esc(name)}</option>`;
        }).join("");
        if (!financeClienteRows.length) credit.innerHTML = '<option value="">Sin clientes disponibles</option>';
      }
      const dispute = $("disputeCliente");
      if (dispute && dispute.options.length <= 1) {
        dispute.innerHTML = '<option value="">Todos</option>' + financeClienteRows.map(row => {
          const code = financeClientId(row);
          const name = financeClientName(row);
          return `<option value="${esc(code)}">${esc(code)} | ${esc(name)}</option>`;
        }).join("");
        if (!financeClienteRows.length) dispute.innerHTML = '<option value="">Sin clientes disponibles</option>';
      }
    }
    async function renderBillingWeb(target=orderCashWorkspace()) {
      target.innerHTML = `
          <div class="panel-head">
            <h2>Invoicing and Billing</h2>
            <span class="muted">Facturación desde servicios y documentos emitidos</span>
          </div>
          <div class="subtabs">
            <button id="billablesTab" onclick="switchBillingPane('billables')">Billing</button>
            <button id="invoicesTab" onclick="switchBillingPane('invoices')">Invoicing</button>
          </div>
          <div id="billingPaneHost" class="billing-pane"></div>
        `;
      renderBillingPane();
      loadFinanceClientCombos().catch(() => null);
    }
    function switchBillingPane(pane) {
      billingPane = pane;
      renderBillingPane();
      loadFinanceClientCombos().catch(() => null);
    }
    function renderBillingPane() {
      const host = $("billingPaneHost");
      if (!host) return;
      $("billablesTab")?.classList.toggle("active", billingPane === "billables");
      $("invoicesTab")?.classList.toggle("active", billingPane === "invoices");
      if (billingPane === "billables") {
        host.innerHTML = `
            <section class="billing-pane">
              <div class="section-head">
                <h3>Billing</h3>
                <span id="billableCount" class="muted">Servicios pendientes</span>
              </div>
              <div class="finance-filter-row compact">
                <label>Cliente<select id="billableCliente"><option value="">Seleccione cliente</option></select></label>
                <button onclick="loadBillables()">Buscar</button>
                <button class="secondary" onclick="clearBillableFilters()">Limpiar</button>
              </div>
              <div class="finance-toolbar">
                <button onclick="openManualInvoiceForm()">Factura Manual</button>
                <button class="secondary" onclick="openXmlInvoiceForm()">Factura XML</button>
                <button class="gray" onclick="openAdvanceInvoiceForm()">Facturación Anticipada</button>
                <button class="brown" onclick="openCreditNoteForm()">Nota Crédito</button>
                <button class="secondary" onclick="viewSelectedBillable()">Ver servicio</button>
              </div>
              <div id="billableMsg" class="status hidden"></div>
              <div id="billableTable" class="workspace"></div>
            </section>`;
        $("billableTable").innerHTML = billableRows.length ? "" : '<div class="status">Ingrese cliente y presione Buscar.</div>';
        if (billableRows.length) renderBillableTable();
        return;
      }
      host.innerHTML = `
            <section class="billing-pane">
              <div class="section-head">
                <h3>Invoicing</h3>
                <span id="billingCount" class="muted">Facturas emitidas</span>
              </div>
              <div class="finance-filter-row">
                <label>Cliente<select id="billingCliente"><option value="">Todos</option></select></label>
                <label>Desde<input id="billingDesde" type="date" /></label>
                <label>Hasta<input id="billingHasta" type="date" /></label>
                <label>Tipo factura<select id="billingTipoFactura"><option value="">Todos</option><option>MANUAL</option><option>ELECTRONICA</option></select></label>
                <label>Documento<select id="billingTipoDocumento"><option value="">Todos</option><option>FACTURA</option><option>NOTA_CREDITO</option></select></label>
                <button onclick="loadBillingRows()">Buscar</button>
                <button class="secondary" onclick="clearBillingFilters()">Limpiar</button>
              </div>
              <div class="finance-toolbar">
                <button onclick="viewSelectedInvoice()">Ver Factura</button>
                <button class="gray" onclick="openBillingEditForm()">Editar</button>
                <button class="brown" onclick="deleteSelectedInvoice()">Eliminar / anular</button>
                <button class="secondary" onclick="downloadBillingExcel()">Exportar Excel</button>
              </div>
              <div id="billingMsg" class="status hidden"></div>
              <div id="billingTable" class="workspace"></div>
            </section>`;
      $("billingTable").innerHTML = billingRows.length ? "" : '<div class="status">Configure filtros y presione Buscar.</div>';
      if (billingRows.length) renderBillingTable();
    }
    function clearBillableFilters() {
      if ($("billableCliente")) $("billableCliente").value = "";
      billableRows = [];
      selectedBillableIndex = null;
      selectedBillableIndexes = new Set();
      if ($("billableCount")) $("billableCount").textContent = "Servicios finalizados pendientes de factura";
      if ($("billableMsg")) $("billableMsg").classList.add("hidden");
      if ($("billableTable")) $("billableTable").innerHTML = '<div class="status">Ingrese cliente y presione Buscar.</div>';
    }
    async function loadBillables() {
      selectedBillableIndex = null;
      selectedBillableIndexes = new Set();
      await loadFinanceClientCombos();
      const cliente = valueFrom("billableCliente");
      const msg = $("billableMsg");
      const table = $("billableTable");
      if (!cliente) {
        billableRows = [];
        $("billableCount").textContent = "Seleccione un cliente";
        table.innerHTML = '<div class="status">Seleccione cliente y presione Buscar.</div>';
        msg.classList.add("hidden");
        return;
      }
      msg.className = "status";
      msg.textContent = "Consultando servicios facturables...";
      try {
        const payload = await getJSON(`/invoicing/facturables?cliente=${encodeURIComponent(cliente)}`);
        billableRows = rowsList(payload);
        $("billableCount").textContent = `${billableRows.length} servicios listos para facturar`;
        msg.classList.add("hidden");
        renderBillableTable();
      } catch (err) {
        msg.className = "status error";
        msg.textContent = err.message;
      }
    }
    function billableRow() {
      if (selectedBillableIndex === null) selectedBillableIndex = firstFromSet(selectedBillableIndexes);
      return selectedBillableIndex === null ? null : billableRows[selectedBillableIndex];
    }
    function toggleBillableRow(idx, checked=null) {
      const next = checked === null ? !selectedBillableIndexes.has(idx) : checked;
      selectedBillableIndex = setIndexSelection(selectedBillableIndexes, idx, next);
      renderBillableTable();
    }
    function requireBillable() {
      const row = billableRow();
      if (!row) alert("Seleccione primero un servicio facturable.");
      return row;
    }
    function renderBillableTable() {
      const cols = ["consec","tipo","buque_contenedor","num_informe","detalle","cliente","pais","puerto","operacion","fecha_inicio","fecha_fin","demoras","duracion"];
      if (!billableRows.length) {
        $("billableTable").innerHTML = '<div class="status">Sin servicios pendientes por facturar para este cliente.</div>';
        return;
      }
      $("billableTable").innerHTML = `<div class="table-wrap"><table><thead><tr><th class="pick-col"></th>${cols.map(c => `<th>${esc(c)}</th>`).join("")}</tr></thead><tbody>${billableRows.map((row, idx) => {
        const selected = selectedBillableIndexes.has(idx);
        return `<tr class="${selected ? "service-selected" : ""}" onclick="toggleBillableRow(${idx})"><td class="pick-col"><input class="row-pick" type="checkbox" ${selected ? "checked" : ""} onclick="event.stopPropagation(); toggleBillableRow(${idx}, this.checked)" /></td>${cols.map(c => `<td>${esc(row[c])}</td>`).join("")}</tr>`;
      }).join("")}</tbody></table></div>`;
    }
    async function viewSelectedBillable() {
      const row = requireBillable();
      if (!row) return;
      const full = await getJSON(`/servicios/${encodeURIComponent(row.consec)}`).catch(() => row);
      document.body.insertAdjacentHTML("beforeend", `
        <div class="modal-backdrop" id="svcModal">
          <div class="modal">
            <div class="modal-head"><h2>Servicio ${esc(full.consec)}</h2><button class="secondary" onclick="closeModal()">Cerrar</button></div>
            <div class="table-wrap"><table><tbody>${Object.keys(full).filter(k => !String(k).toLowerCase().includes("hash")).map(k => `<tr><th>${esc(k)}</th><td>${esc(full[k])}</td></tr>`).join("")}</tbody></table></div>
          </div>
        </div>`);
    }
    function defaultInvoiceDescription(row) {
      return [row?.puerto, row?.pais, row?.operacion, row?.detalle].filter(Boolean).join(" - ");
    }
    async function invoiceTerms(cliente) {
      try {
        const data = await getJSON(`/factura/termino-pago?nombre_cliente=${encodeURIComponent(cliente)}`);
        return data.termino_pago ?? 0;
      } catch {
        return 0;
      }
    }
    async function openManualInvoiceForm() {
      const row = requireBillable();
      if (!row) return;
      const terms = await invoiceTerms(row.cliente);
      const today = new Date().toISOString().slice(0,10);
      document.body.insertAdjacentHTML("beforeend", `
        <div class="modal-backdrop" id="svcModal">
          <div class="modal small">
            <div class="modal-head"><h2>Factura Manual</h2><button class="secondary" onclick="closeModal()">Cerrar</button></div>
            <div class="form-grid">
              <label>Servicio<input value="${esc(row.consec)}" readonly /></label>
              <label>Fecha emisión<input id="inv_fecha" type="date" value="${today}" /></label>
              <label>Moneda<select id="inv_moneda"><option>USD</option><option>CRC</option></select></label>
              <label>Término pago<input id="inv_termino" type="number" value="${esc(terms)}" readonly /></label>
              <label>Total<input id="inv_total" type="number" step="0.01" value="${esc(row.valor_factura || "")}" /></label>
              <label class="wide">Descripción<textarea id="inv_desc">${esc(defaultInvoiceDescription(row))}</textarea></label>
            </div>
            <div class="md-actions"><button class="green" onclick="saveManualInvoice()">Facturar</button><button class="secondary" onclick="closeModal()">Cancelar</button></div>
            <div id="invMsg" class="status hidden"></div>
          </div>
        </div>`);
    }
    async function saveManualInvoice() {
      const row = requireBillable();
      const msg = $("invMsg");
      msg.className = "status";
      msg.textContent = "Creando factura...";
      try {
        const payload = {
          servicio_id:Number(row.consec),
          descripcion:valueFrom("inv_desc"),
          fecha_factura:valueFrom("inv_fecha"),
          moneda:valueFrom("inv_moneda") || "USD",
          termino_pago:Number(valueFrom("inv_termino") || 0),
          total:Number(valueFrom("inv_total") || 0)
        };
        if (!payload.total || payload.total <= 0) throw new Error("Total requerido.");
        const data = await postJSON("/factura/manual", payload);
        await postJSON("/collections/sync-from-invoicing", {}).catch(() => null);
        closeModal();
        await loadBillables();
        await loadBillingRows();
        alert(`Factura manual creada: ${data.numero_factura || data.numero_documento}`);
      } catch (err) {
        msg.className = "status error";
        msg.textContent = err.message;
      }
    }
    function openXmlInvoiceForm() {
      const row = requireBillable();
      if (!row) return;
      document.body.insertAdjacentHTML("beforeend", `
        <div class="modal-backdrop" id="svcModal">
          <div class="modal small">
            <div class="modal-head"><h2>Factura XML</h2><button class="secondary" onclick="closeModal()">Cerrar</button></div>
            <div class="form-grid">
              <label class="wide">XML<input id="xmlFile" type="file" accept=".xml,application/xml,text/xml" /></label>
            </div>
            <div class="md-actions"><button class="green" onclick="saveXmlInvoice()">Registrar XML</button><button class="secondary" onclick="closeModal()">Cancelar</button></div>
            <div id="xmlMsg" class="status hidden"></div>
          </div>
        </div>`);
    }
    async function saveXmlInvoice() {
      const row = requireBillable();
      const file = $("xmlFile")?.files?.[0];
      if (!file) return alert("Seleccione el XML.");
      const msg = $("xmlMsg");
      msg.className = "status";
      msg.textContent = "Registrando XML...";
      try {
        const form = new FormData();
        form.append("servicio_id", row.consec);
        form.append("file", file, file.name);
        const data = await sendForm("/factura/electronica", form);
        await postJSON("/collections/sync-from-invoicing", {}).catch(() => null);
        closeModal();
        await loadBillables();
        await loadBillingRows();
        alert(`Factura XML registrada: ${data.numero_documento}`);
      } catch (err) {
        msg.className = "status error";
        msg.textContent = err.message;
      }
    }
    async function renderInvoicingWeb(target=orderCashWorkspace()) {
      await renderBillingWeb(target);
    }
    function billingParams() {
      const params = new URLSearchParams({ page:"1", page_size:"100" });
      const map = {
        cliente:valueFrom("billingCliente"),
        fecha_desde:valueFrom("billingDesde"),
        fecha_hasta:valueFrom("billingHasta"),
        tipo_factura:valueFrom("billingTipoFactura"),
        tipo_documento:valueFrom("billingTipoDocumento")
      };
      Object.entries(map).forEach(([k,v]) => { if (v) params.set(k, v); });
      return params.toString();
    }
    function clearBillingFilters() {
      ["billingCliente","billingDesde","billingHasta","billingTipoFactura","billingTipoDocumento"].forEach(id => { if ($(id)) $(id).value = ""; });
      billingRows = [];
      selectedBillingIndex = null;
      selectedBillingIndexes = new Set();
      if ($("billingCount")) $("billingCount").textContent = "Facturas emitidas";
      if ($("billingMsg")) $("billingMsg").classList.add("hidden");
      if ($("billingTable")) $("billingTable").innerHTML = '<div class="status">Configure filtros y presione Buscar.</div>';
    }
    async function loadBillingRows() {
      if (!$("billingTable")) return;
      selectedBillingIndex = null;
      selectedBillingIndexes = new Set();
      await loadFinanceClientCombos();
      const msg = $("billingMsg");
      msg.className = "status";
      msg.textContent = "Consultando facturas...";
      try {
        const payload = await getJSON(`/billing/search?${billingParams()}`);
        billingRows = rowsList(payload);
        $("billingCount").textContent = `${payload.total ?? billingRows.length} documentos`;
        msg.classList.add("hidden");
        renderBillingTable();
      } catch (err) {
        msg.className = "status error";
        msg.textContent = err.message;
      }
    }
    function billingRow() {
      if (selectedBillingIndex === null) selectedBillingIndex = firstFromSet(selectedBillingIndexes);
      return selectedBillingIndex === null ? null : billingRows[selectedBillingIndex];
    }
    function toggleBillingRow(idx, checked=null) {
      const next = checked === null ? !selectedBillingIndexes.has(idx) : checked;
      selectedBillingIndex = setIndexSelection(selectedBillingIndexes, idx, next);
      renderBillingTable();
    }
    function requireBillingRow() {
      const row = billingRow();
      if (!row) alert("Seleccione primero una factura.");
      return row;
    }
    function renderBillingTable() {
      const cols = ["id","tipo_factura","tipo_documento","numero_documento","nombre_cliente","fecha_emision","moneda","total","estado"];
      if (!billingRows.length) {
        $("billingTable").innerHTML = '<div class="status">Sin facturas para esta consulta.</div>';
        return;
      }
      $("billingTable").innerHTML = `<div class="table-wrap"><table><thead><tr><th class="pick-col"></th>${cols.map(c => `<th>${esc(c)}</th>`).join("")}</tr></thead><tbody>${billingRows.map((row, idx) => {
        const selected = selectedBillingIndexes.has(idx);
        return `<tr class="${selected ? "service-selected" : ""}" onclick="toggleBillingRow(${idx})"><td class="pick-col"><input class="row-pick" type="checkbox" ${selected ? "checked" : ""} onclick="event.stopPropagation(); toggleBillingRow(${idx}, this.checked)" /></td>${cols.map(c => `<td>${esc(c === "total" ? Number(row[c] || 0).toLocaleString("en-US", {minimumFractionDigits:2, maximumFractionDigits:2}) : row[c])}</td>`).join("")}</tr>`;
      }).join("")}</tbody></table></div>`;
    }
    async function viewSelectedInvoice() {
      const row = requireBillingRow();
      if (!row) return;
      const full = await getJSON(`/billing/${encodeURIComponent(row.numero_documento)}`);
      document.body.insertAdjacentHTML("beforeend", `
        <div class="modal-backdrop" id="svcModal">
          <div class="modal">
            <div class="modal-head"><h2>Factura ${esc(full.numero_documento)}</h2><button class="secondary" onclick="closeModal()">Cerrar</button></div>
            <div class="service-actions">
              <a href="/billing/pdf/${encodeURIComponent(full.numero_documento)}" target="_blank"><button>Ver / descargar PDF</button></a>
              <a href="/billing/word/${encodeURIComponent(full.numero_documento)}" target="_blank"><button class="secondary">Exportar Word</button></a>
            </div>
            <div class="table-wrap"><table><tbody>${Object.keys(full).filter(k => !String(k).toLowerCase().includes("hash")).map(k => `<tr><th>${esc(k)}</th><td>${esc(full[k])}</td></tr>`).join("")}</tbody></table></div>
          </div>
        </div>`);
    }
    async function openBillingEditForm() {
      const row = requireBillingRow();
      if (!row) return;
      const full = await getJSON(`/billing/${encodeURIComponent(row.numero_documento)}`);
      document.body.insertAdjacentHTML("beforeend", `
        <div class="modal-backdrop" id="svcModal">
          <div class="modal small">
            <div class="modal-head"><h2>Editar factura ${esc(full.numero_documento)}</h2><button class="secondary" onclick="closeModal()">Cerrar</button></div>
            <div class="form-grid">
              <label>Número<input id="editInv_numero" value="${esc(full.numero_documento)}" /></label>
              <label>Cliente<input id="editInv_cliente" value="${esc(full.nombre_cliente)}" /></label>
              <label>Fecha emisión<input id="editInv_fecha" type="date" value="${esc(String(full.fecha_emision || "").slice(0,10))}" /></label>
              <label>Moneda<select id="editInv_moneda"><option${full.moneda === "USD" ? " selected" : ""}>USD</option><option${full.moneda === "CRC" ? " selected" : ""}>CRC</option></select></label>
              <label>Total<input id="editInv_total" type="number" step="0.01" value="${esc(full.total)}" /></label>
              <label>Estado<select id="editInv_estado"><option${full.estado === "EMITIDA" ? " selected" : ""}>EMITIDA</option><option${full.estado === "ANULADA" ? " selected" : ""}>ANULADA</option></select></label>
              <label>Término pago<input id="editInv_termino" type="number" value="${esc(full.termino_pago || 0)}" /></label>
              <label>Num informe<input id="editInv_informe" value="${esc(full.num_informe || "")}" /></label>
              <label>Buque / contenedor<input id="editInv_buque" value="${esc(full.buque_contenedor || "")}" /></label>
              <label>Operación<input id="editInv_operacion" value="${esc(full.operacion || "")}" /></label>
              <label class="wide">Descripción<textarea id="editInv_desc">${esc(full.descripcion_servicio || "")}</textarea></label>
            </div>
            <div class="md-actions"><button class="green" onclick="saveBillingEdit(${Number(full.id)})">Guardar</button><button class="secondary" onclick="closeModal()">Cancelar</button></div>
            <div id="editInvMsg" class="status hidden"></div>
          </div>
        </div>`);
    }
    async function saveBillingEdit(id) {
      const msg = $("editInvMsg");
      msg.className = "status";
      msg.textContent = "Guardando...";
      try {
        const payload = {
          numero_documento:valueFrom("editInv_numero"),
          nombre_cliente:valueFrom("editInv_cliente"),
          fecha_emision:valueFrom("editInv_fecha"),
          moneda:valueFrom("editInv_moneda"),
          total:Number(valueFrom("editInv_total") || 0),
          estado:valueFrom("editInv_estado"),
          termino_pago:Number(valueFrom("editInv_termino") || 0),
          num_informe:valueFrom("editInv_informe"),
          buque_contenedor:valueFrom("editInv_buque"),
          operacion:valueFrom("editInv_operacion"),
          descripcion_servicio:valueFrom("editInv_desc")
        };
        if (!payload.numero_documento || !payload.nombre_cliente || payload.total <= 0) throw new Error("Número, cliente y total son requeridos.");
        await sendJSON("PUT", `/billing/${encodeURIComponent(id)}`, payload);
        closeModal();
        await loadBillingRows();
        refreshSummary();
      } catch (err) {
        msg.className = "status error";
        msg.textContent = err.message;
      }
    }
    async function deleteSelectedInvoice() {
      const row = requireBillingRow();
      if (!row) return;
      if (!confirm(`¿Anular factura ${row.numero_documento}?`)) return;
      try {
        await sendJSON("DELETE", `/billing/${encodeURIComponent(row.id)}`, null);
        await loadBillingRows();
        refreshSummary();
      } catch (err) {
        alert(err.message);
      }
    }
    function downloadBillingExcel() {
      if (!billingRows.length) return alert("No hay datos para exportar.");
      const cols = ["id","tipo_factura","tipo_documento","numero_documento","nombre_cliente","fecha_emision","moneda","total","estado"];
      downloadExcelFile(`billing_${new Date().toISOString().slice(0,10)}.xls`, billingRows, cols, "Invoicing - detalle de facturas");
    }
    async function openAdvanceInvoiceForm() {
      const clientes = await ensureFinanceClientes();
      advanceServiceRows = [];
      document.body.insertAdjacentHTML("beforeend", `
        <div class="modal-backdrop" id="svcModal">
          <div class="modal">
            <div class="modal-head"><h2>Facturación Anticipada</h2><button class="secondary" onclick="closeModal()">Cerrar</button></div>
            <div class="form-grid">
              <label>Cliente / código<input id="adv_cliente" list="advClientList" placeholder="Seleccione o escriba cliente" onchange="syncAdvanceClient(); loadAdvanceInvoiceServices()" oninput="syncAdvanceClient()" /></label>
              <label>Nombre en factura<input id="adv_nombre_factura" placeholder="Nombre editable para la factura" /></label>
              <input id="adv_codigo_cliente" type="hidden" />
              <datalist id="advClientList">${clientes.map(c => `<option value="${esc(c)}"></option>`).join("")}</datalist>
              <label>Survey / servicio<select id="adv_service" onchange="applyAdvanceInvoiceService()"><option value="">Seleccione cliente primero</option></select></label>
              <label>Fecha emisión<input value="${new Date().toISOString().slice(0,10)}" readonly /></label>
              <label>Moneda<select id="adv_moneda"><option>USD</option><option>CRC</option></select></label>
              <label>Payment terms<input id="adv_payment_terms" placeholder="CREDIT 10 DAYS" /></label>
              <label>Total<input id="adv_total" type="number" step="0.01" /></label>
              <label>Place<input id="adv_place" placeholder="PUERTO, PAIS" /></label>
              <label>Buque / contenedor<input id="adv_buque" /></label>
              <label>Survey<input id="adv_survey" list="advSurveyList" /></label>
              <label>Num informe<input id="adv_informe" /></label>
              <label>Periodo<input id="adv_periodo" /></label>
              <datalist id="advSurveyList"></datalist>
              <label class="wide">Descripción<textarea id="adv_desc"></textarea></label>
            </div>
            <div class="status">La cuenta bancaria se mantiene fija: BCR Banco de Costa Rica · IBAN CR49015201308000025850 · SWIFT BCRICRSJ.</div>
            <div class="md-actions"><button class="green" onclick="saveAdvanceInvoice()">Facturar</button><button class="secondary" onclick="closeModal()">Cancelar</button></div>
            <div id="advMsg" class="status hidden"></div>
          </div>
        </div>`);
    }
    function syncAdvanceClient() {
      const selected = valueFrom("adv_cliente");
      const code = financeClientCode(selected);
      if ($("adv_codigo_cliente")) $("adv_codigo_cliente").value = code;
      const invoiceName = $("adv_nombre_factura");
      if (invoiceName && (!invoiceName.value || invoiceName.dataset.synced === "1")) {
        invoiceName.value = selected;
        invoiceName.dataset.synced = "1";
      }
      if (invoiceName && !invoiceName.oninput) {
        invoiceName.oninput = () => { invoiceName.dataset.synced = "0"; };
      }
    }
    function advanceTermsDays(text) {
      const match = String(text || "").match(/(\\d+)/);
      return match ? Number(match[1]) : 0;
    }
    function advancePlace(row) {
      return [row?.puerto, row?.pais].filter(Boolean).join(", ");
    }
    function advanceSurvey(row) {
      return row?.operacion || row?.detalle || row?.tipo || "SURVEY";
    }
    function advanceDescription(row, cliente) {
      const first = [row?.num_informe, row?.buque_contenedor, cliente].filter(Boolean).join(" / ");
      return [first, advancePlace(row), "", "SURVEY:", `-${advanceSurvey(row)}`].join("\\n");
    }
    async function loadAdvanceInvoiceServices() {
      const cliente = valueFrom("adv_cliente");
      const svc = $("adv_service");
      const msg = $("advMsg");
      advanceServiceRows = [];
      if (!cliente) {
        svc.innerHTML = '<option value="">Seleccione cliente primero</option>';
        return;
      }
      msg.className = "status";
      msg.textContent = "Consultando servicios del cliente...";
      try {
        const payload = await getJSON(`/invoicing/facturables?cliente=${encodeURIComponent(cliente)}`);
        advanceServiceRows = rowsList(payload);
        svc.innerHTML = '<option value="">Seleccione survey / servicio</option>' + advanceServiceRows.map((row, idx) => {
          const label = [advanceSurvey(row), row.num_informe, row.buque_contenedor, advancePlace(row)].filter(Boolean).join(" | ");
          return `<option value="${idx}">${esc(label)}</option>`;
        }).join("");
        $("advSurveyList").innerHTML = [...new Set(advanceServiceRows.map(advanceSurvey).filter(Boolean))].map(v => `<option value="${esc(v)}"></option>`).join("");
        msg.classList.add("hidden");
        if (!advanceServiceRows.length) {
          svc.innerHTML = '<option value="">Sin servicios finalizados pendientes</option>';
          msg.className = "status";
          msg.textContent = "No hay servicios facturables para este cliente. Puede completar los campos manualmente.";
        }
      } catch (err) {
        svc.innerHTML = '<option value="">No se pudieron cargar servicios</option>';
        msg.className = "status error";
        msg.textContent = err.message;
      }
    }
    function applyAdvanceInvoiceService() {
      const idx = Number(valueFrom("adv_service"));
      const row = Number.isFinite(idx) ? advanceServiceRows[idx] : null;
      if (!row) return;
      const cliente = valueFrom("adv_nombre_factura") || valueFrom("adv_cliente");
      $("adv_place").value = advancePlace(row);
      $("adv_buque").value = row.buque_contenedor || "";
      $("adv_survey").value = advanceSurvey(row);
      $("adv_informe").value = row.num_informe || "";
      $("adv_periodo").value = [row.fecha_inicio, row.fecha_fin].filter(Boolean).join(" a ");
      $("adv_desc").value = advanceDescription(row, cliente);
    }
    async function saveAdvanceInvoice() {
      const cliente = valueFrom("adv_cliente");
      const nombreFactura = valueFrom("adv_nombre_factura") || cliente;
      const codigoCliente = valueFrom("adv_codigo_cliente") || financeClientCode(cliente);
      const msg = $("advMsg");
      msg.className = "status";
      msg.textContent = "Creando factura anticipada...";
      try {
        const paymentTerms = valueFrom("adv_payment_terms") || "DUE UPON RECEIPT";
        const payload = {
          tipo_factura:"MANUAL",
          codigo_cliente:codigoCliente,
          nombre_cliente:nombreFactura,
          descripcion:valueFrom("adv_desc"),
          moneda:valueFrom("adv_moneda") || "USD",
          termino_pago:advanceTermsDays(paymentTerms),
          payment_terms:paymentTerms,
          total:Number(valueFrom("adv_total") || 0),
          buque:valueFrom("adv_buque"),
          operacion:valueFrom("adv_survey"),
          survey:valueFrom("adv_survey"),
          place:valueFrom("adv_place"),
          num_informe:valueFrom("adv_informe"),
          periodo_operacion:valueFrom("adv_periodo")
        };
        if (!payload.codigo_cliente) throw new Error("Seleccione un cliente válido para tomar el código; luego puede corregir el Nombre en factura.");
        if (!payload.nombre_cliente || !payload.descripcion || payload.total <= 0) throw new Error("Nombre en factura, descripción y total son requeridos.");
        const data = await postJSON("/invoicing/anticipada", payload);
        await postJSON("/collections/sync-from-invoicing", {}).catch(() => null);
        closeModal();
        if (financeTab === "billing" && $("billingTable")) await loadBillingRows();
        alert(`Factura anticipada creada: ${data.numero_documento}. Puede exportarla en PDF o Word desde Ver Factura.`);
      } catch (err) {
        msg.className = "status error";
        msg.textContent = err.message;
      }
    }
    async function openCreditNoteForm() {
      const clientes = await ensureFinanceClientes();
      document.body.insertAdjacentHTML("beforeend", `
        <div class="modal-backdrop" id="svcModal">
          <div class="modal small">
            <div class="modal-head"><h2>Nota de Crédito</h2><button class="secondary" onclick="closeModal()">Cerrar</button></div>
            <div class="form-grid">
              <label>Cliente<select id="nc_cliente">${clientes.map(c => `<option value="${esc(c)}">${esc(c)}</option>`).join("")}</select></label>
              <label>Moneda<select id="nc_moneda"><option>USD</option><option>CRC</option></select></label>
              <label>Total<input id="nc_total" type="number" step="0.01" /></label>
              <label>Buque / contenedor<input id="nc_buque" /></label>
              <label>Operación<input id="nc_operacion" /></label>
              <label>Num informe<input id="nc_informe" /></label>
              <label>Periodo<input id="nc_periodo" /></label>
              <label class="wide">Descripción<textarea id="nc_desc"></textarea></label>
            </div>
            <div class="md-actions"><button class="brown" onclick="saveCreditNote()">Crear NC</button><button class="secondary" onclick="closeModal()">Cancelar</button></div>
            <div id="ncMsg" class="status hidden"></div>
          </div>
        </div>`);
    }
    async function saveCreditNote() {
      const cliente = valueFrom("nc_cliente");
      const msg = $("ncMsg");
      msg.className = "status";
      msg.textContent = "Creando nota de crédito...";
      try {
        const payload = {
          tipo_factura:"MANUAL",
          codigo_cliente:financeClientCode(cliente),
          nombre_cliente:cliente,
          descripcion:valueFrom("nc_desc"),
          moneda:valueFrom("nc_moneda") || "USD",
          total:Number(valueFrom("nc_total") || 0),
          buque:valueFrom("nc_buque"),
          operacion:valueFrom("nc_operacion"),
          num_informe:valueFrom("nc_informe"),
          periodo_operacion:valueFrom("nc_periodo")
        };
        if (!payload.codigo_cliente || !payload.nombre_cliente || !payload.descripcion || payload.total <= 0) throw new Error("Cliente, descripción y total son requeridos.");
        const data = await postJSON("/invoicing/nota-credito", payload);
        await postJSON("/collections/sync-from-invoicing", {}).catch(() => null);
        closeModal();
        if (financeTab === "billing" && $("billingTable")) await loadBillingRows();
        alert(`Nota de crédito creada: ${data.numero_documento}`);
      } catch (err) {
        msg.className = "status error";
        msg.textContent = err.message;
      }
    }
    function renderCreditHoldWeb(target=orderCashWorkspace()) {
      target.innerHTML = `
          <div class="panel-head">
            <h2>Credit, Order Hold and Release</h2>
            <span class="muted">Límite, términos crediticios y hold por cliente</span>
          </div>
          <div class="finance-filter-row compact">
            <label>Cliente<select id="creditCliente" onchange="selectCreditByCombo()"><option value="">Todos</option></select></label>
            <button onclick="loadCreditHold()">Buscar</button>
            <button class="secondary" onclick="clearCreditHold()">Limpiar</button>
          </div>
          <div class="service-actions">
            <button onclick="openCreditConfigForm('add')">Agregar límite</button>
            <button class="secondary" onclick="viewSelectedCreditConfig()">Ver</button>
            <button class="gray" onclick="openCreditConfigForm('edit')">Editar</button>
            <button class="brown" onclick="toggleSelectedCreditHold()">Bloquear / liberar</button>
            <button class="dark" onclick="deleteSelectedCreditConfig()">Eliminar</button>
          </div>
          <input id="creditQ" class="hidden" />
          <div id="creditMsg" class="status hidden"></div>
          <div id="creditTable" class="workspace"></div>
        `;
      $("creditTable").innerHTML = '<div class="status">Presione Buscar para consultar crédito.</div>';
      loadFinanceClientCombos().catch(() => null);
    }
    function clearCreditHold() {
      if ($("creditQ")) $("creditQ").value = "";
      if ($("creditCliente")) $("creditCliente").value = "";
      creditRows = [];
      selectedCreditIndex = null;
      selectedCreditIndexes = new Set();
      if ($("creditMsg")) $("creditMsg").classList.add("hidden");
      if ($("creditTable")) $("creditTable").innerHTML = '<div class="status">Presione Buscar para consultar crédito.</div>';
    }
    async function loadCreditHold() {
      const msg = $("creditMsg");
      const table = $("creditTable");
      msg.className = "status";
      msg.textContent = "Consultando credito...";
      await loadFinanceClientCombos();
      const q = valueFrom("creditCliente") || valueFrom("creditQ");
      try {
        const payload = await getJSON(`/som/finance/order-to-cash/credit-hold${q ? `?q=${encodeURIComponent(q)}` : ""}`);
        creditRows = rowsList(payload);
        selectedCreditIndex = null;
        selectedCreditIndexes = new Set();
        msg.classList.add("hidden");
        if (!creditRows.length) {
          table.innerHTML = '<div class="status">Sin clientes para la consulta.</div>';
          return;
        }
        renderCreditTable();
      } catch (err) {
        msg.className = "status error";
        msg.textContent = err.message;
      }
    }
    function creditRow() {
      if (selectedCreditIndex === null) selectedCreditIndex = firstFromSet(selectedCreditIndexes);
      if (selectedCreditIndex !== null) return creditRows[selectedCreditIndex];
      const code = valueFrom("creditCliente");
      if (!code) return null;
      const found = creditRows.find(row => String(row.codigo || row.codigo_cliente || "") === code);
      if (found) return found;
      const option = $("creditCliente")?.selectedOptions?.[0];
      return { codigo:code, cliente:(option?.textContent || "").split("|").slice(1).join("|").trim() };
    }
    function requireCreditRow() {
      const row = creditRow();
      if (!row) alert("Seleccione primero un cliente de Credit.");
      return row;
    }
    function renderCreditTable() {
      const table = $("creditTable");
      if (!creditRows.length) {
        table.innerHTML = '<div class="status">Sin clientes para la consulta.</div>';
        return;
      }
      table.innerHTML = `
        <div class="table-wrap">
          <table>
            <thead><tr>
              <th class="pick-col"></th><th>Código</th><th>Cliente</th><th>Límite</th><th>CxC abierta</th><th>Disponible</th><th>Estado</th><th>Hold</th><th>Decisión</th><th>Acción</th>
            </tr></thead>
            <tbody>${creditRows.map((row, idx) => {
              const decision = String(row.decision || "");
              const badge = decision === "REQUIRES_RELEASE" ? "cancel" : "closed";
              const selected = selectedCreditIndexes.has(idx);
              return `<tr class="${selected ? "service-selected" : ""}" onclick="toggleCreditRow(${idx})">
                <td class="pick-col"><input class="row-pick" type="checkbox" ${selected ? "checked" : ""} onclick="event.stopPropagation(); toggleCreditRow(${idx}, this.checked)" /></td>
                <td>${esc(row.codigo)}</td>
                <td>${esc(row.cliente)}</td>
                <td>${esc(row.moneda)} ${Number(row.limite || 0).toLocaleString("en-US", {minimumFractionDigits:2, maximumFractionDigits:2})}</td>
                <td>${esc(row.moneda)} ${Number(row.cxC_abierta || 0).toLocaleString("en-US", {minimumFractionDigits:2, maximumFractionDigits:2})}</td>
                <td>${esc(row.moneda)} ${Number(row.disponible || 0).toLocaleString("en-US", {minimumFractionDigits:2, maximumFractionDigits:2})}</td>
                <td>${esc(row.estado || "-")}</td>
                <td>${row.hold_manual ? "Si" : "No"}</td>
                <td><span class="badge ${badge}">${esc(decision)}</span></td>
                <td><div class="toolbar"><button class="secondary" onclick="event.stopPropagation(); selectCreditRow(${idx}); viewSelectedCreditConfig()">Ver</button><button onclick="event.stopPropagation(); selectCreditRow(${idx}); openCreditConfigForm('edit')">Editar</button><button class="brown" onclick="event.stopPropagation(); selectCreditRow(${idx}); toggleSelectedCreditHold()">Hold</button><button class="dark" onclick="event.stopPropagation(); selectCreditRow(${idx}); deleteSelectedCreditConfig()">Eliminar</button></div></td>
              </tr>`;
            }).join("")}</tbody>
          </table>
        </div>`;
    }
    function toggleCreditRow(index, checked=null) {
      const next = checked === null ? !selectedCreditIndexes.has(index) : checked;
      selectedCreditIndex = setIndexSelection(selectedCreditIndexes, index, next);
      const row = selectedCreditIndex === null ? null : creditRows[selectedCreditIndex];
      if ($("creditCliente")) $("creditCliente").value = row?.codigo || "";
      renderCreditTable();
    }
    function selectCreditRow(index) {
      selectedCreditIndex = index;
      selectedCreditIndexes = new Set([index]);
      const row = creditRows[index];
      if ($("creditCliente") && row?.codigo) $("creditCliente").value = row.codigo;
      renderCreditTable();
    }
    function selectCreditByCombo() {
      const code = valueFrom("creditCliente");
      selectedCreditIndex = code ? creditRows.findIndex(row => String(row.codigo || row.codigo_cliente || "") === code) : null;
      if (selectedCreditIndex < 0) selectedCreditIndex = null;
      selectedCreditIndexes = selectedCreditIndex === null ? new Set() : new Set([selectedCreditIndex]);
      if (creditRows.length) renderCreditTable();
    }
    async function viewSelectedCreditConfig() {
      const row = requireCreditRow();
      if (!row) return;
      const data = await getJSON(`/cliente-credito/${encodeURIComponent(row.codigo)}`);
      const detail = data.exists ? data.data : { codigo_cliente:row.codigo, nombre_cliente:row.cliente, estado:"Sin límite crediticio" };
      document.body.insertAdjacentHTML("beforeend", `
        <div class="modal-backdrop" id="svcModal">
          <div class="modal">
            <div class="modal-head"><h2>Información crediticia</h2><button class="secondary" onclick="closeModal()">Cerrar</button></div>
            <div class="table-wrap"><table><tbody>${Object.keys(detail).filter(k => !String(k).toLowerCase().includes("hash")).map(k => `<tr><th>${esc(k)}</th><td>${esc(detail[k])}</td></tr>`).join("")}</tbody></table></div>
          </div>
        </div>`);
    }
    async function openCreditConfigForm(mode) {
      const selected = creditRow();
      let row = selected || {};
      let exists = false;
      if (mode === "edit") {
        row = requireCreditRow();
        if (!row) return;
        const data = await getJSON(`/cliente-credito/${encodeURIComponent(row.codigo)}`);
        exists = !!data.exists;
        if (!exists) {
          if (!confirm("Este cliente existe en Master Data pero no tiene límite crediticio. ¿Desea crearlo ahora?")) return;
          mode = "add";
        } else {
          row = { ...row, ...(data.data || {}) };
        }
      }
      const isEdit = mode === "edit";
      document.body.insertAdjacentHTML("beforeend", `
        <div class="modal-backdrop" id="svcModal">
          <div class="modal small">
            <div class="modal-head"><h2>${isEdit ? "Editar crédito" : "Agregar límite crediticio"}</h2><button class="secondary" onclick="closeModal()">Cerrar</button></div>
            <div class="form-grid">
              <label>Código cliente<input id="cred_codigo" value="${esc(row.codigo_cliente || row.codigo || "")}" ${isEdit ? "readonly" : ""} required /></label>
              <label>Nombre<input id="cred_nombre" value="${esc(row.nombre_cliente || row.cliente || "")}" readonly /></label>
              <label>Límite<input id="cred_limite" type="number" step="0.01" value="${esc(row.limite_credito ?? row.limite ?? "")}" required /></label>
              <label>Moneda<select id="cred_moneda"><option>USD</option><option>CRC</option></select></label>
              <label>Término pago<input id="cred_termino" type="number" value="${esc(row.termino_pago ?? 30)}" /></label>
              <label>Estado<select id="cred_estado"><option>ACTIVE</option><option>HOLD</option><option>INACTIVE</option></select></label>
              <label>Hold manual<input id="cred_hold" type="checkbox" ${row.hold_manual ? "checked" : ""} /></label>
              <label class="wide">Observaciones<textarea id="cred_obs">${esc(row.observaciones || row.mensaje || "")}</textarea></label>
            </div>
            <div class="md-actions"><button class="green" onclick="saveCreditConfig('${isEdit ? "edit" : "add"}')">Guardar</button><button class="secondary" onclick="closeModal()">Cancelar</button></div>
            <div id="credMsg" class="status hidden"></div>
          </div>
        </div>`);
      $("cred_moneda").value = row.moneda || "USD";
      $("cred_estado").value = row.estado_credito || row.estado || (row.hold_manual ? "HOLD" : "ACTIVE");
    }
    async function saveCreditConfig(mode) {
      const msg = $("credMsg");
      msg.className = "status";
      msg.textContent = "Guardando crédito...";
      const payload = {
        codigo_cliente:valueFrom("cred_codigo"),
        nombre_cliente:valueFrom("cred_nombre"),
        limite_credito:Number(valueFrom("cred_limite") || 0),
        moneda:valueFrom("cred_moneda") || "USD",
        termino_pago:Number(valueFrom("cred_termino") || 0),
        estado_credito:valueFrom("cred_estado") || "ACTIVE",
        hold_manual:!!($("cred_hold")?.checked),
        observaciones:valueFrom("cred_obs")
      };
      if (!payload.codigo_cliente || payload.limite_credito < 0) {
        msg.className = "status error";
        msg.textContent = "Código cliente y límite válido son requeridos.";
        return;
      }
      try {
        if (mode === "edit") {
          await sendJSON("PUT", `/cliente-credito/${encodeURIComponent(payload.codigo_cliente)}`, payload);
        } else {
          await postJSON("/cliente-credito/", payload);
        }
        closeModal();
        await loadCreditHold();
      } catch (err) {
        msg.className = "status error";
        msg.textContent = err.message;
      }
    }
    async function toggleSelectedCreditHold() {
      const row = requireCreditRow();
      if (!row) return;
      const data = await getJSON(`/cliente-credito/${encodeURIComponent(row.codigo)}`);
      if (!data.exists) return alert("Este cliente aún no tiene configuración crediticia. Primero agregue un límite.");
      const current = data.data || {};
      const nextHold = !current.hold_manual;
      if (!confirm(`${nextHold ? "Bloquear" : "Liberar"} crédito para ${row.cliente}?`)) return;
      await sendJSON("PUT", `/cliente-credito/${encodeURIComponent(row.codigo)}`, {
        ...current,
        hold_manual:nextHold,
        estado_credito:nextHold ? "HOLD" : "ACTIVE"
      });
      await loadCreditHold();
    }
    async function deleteSelectedCreditConfig() {
      const row = requireCreditRow();
      if (!row) return;
      if (!confirm(`¿Eliminar configuración crediticia de ${row.cliente}?`)) return;
      await sendJSON("DELETE", `/cliente-credito/${encodeURIComponent(row.codigo)}`, null);
      await loadCreditHold();
    }
    function renderMasterData() {
      $("content").innerHTML = `
        <div class="card panel">
          <div class="panel-head"><h2>Acciones</h2></div>
          <div class="md-actions">${catalog.master_data_actions.map(a => `<button class="${buttonClass(a)}" onclick="masterAction('${a.key}')">${a.label}</button>`).join("")}</div>
          <div class="filters">
            <select id="mdTipo"><option>Todos</option><option>Empleado</option><option>Surveyor</option><option>Cliente</option><option>Proveedor</option><option>Servicio</option><option>Puerto</option></select>
            <select id="mdContinente"><option>Seleccione continente</option></select>
            <select id="mdPais"><option>Seleccione país</option></select>
            <select id="mdPuerto"><option>Seleccione puerto</option></select>
            <button class="secondary" onclick="loadMasterFilters()">Cargar filtros</button>
            <button onclick="applyMasterFilter()">Buscar</button>
          </div>
          <div class="status master-empty">Seleccione una acción arriba o filtre por tipo para abrir la pantalla correspondiente.</div>
        </div>
        <div id="masterWorkspace" class="card panel workspace hidden"></div>`;
    }
    function buttonClass(action) {
      if (action.key === "export_form") return "green";
      if (action.key === "import_form") return "brown";
      if (action.key === "company_fiscal") return "gray";
      if (action.key === "bank_accounts") return "dark";
      return "";
    }
    function masterAction(key) {
      if (["clientes","surveyores","empleados","proveedores","servicios_md","puertos"].includes(key)) {
        if (key === "puertos") {
          openPortForm(null);
          return;
        }
        openMasterForm(key, null);
        return;
      }
      if (key === "export_form") {
        $("masterWorkspace").classList.remove("hidden");
        $("masterWorkspace").innerHTML = `<div class="panel-head"><h2>Exportar formulario</h2></div>
          <div class="md-actions">
            ${["cliente","proveedor","empleado","surveyor"].map(e => `<a href="/master-data/forms/${e}/xlsx" target="_blank"><button>Excel ${e}</button></a><a href="/master-data/forms/${e}/docx" target="_blank"><button class="secondary">Word ${e}</button></a>`).join("")}
          </div>`;
        return;
      }
      if (key === "company_fiscal") openCompanyFiscalForm();
      if (key === "bank_accounts") openMasterView("bank_accounts");
    }
    async function loadMasterFilters() {
      try {
        const continentes = await getJSON("/cpp/continentes");
        $("mdContinente").innerHTML = "<option>Seleccione continente</option>" + continentes.map(x => `<option>${x}</option>`).join("");
        $("mdContinente").onchange = async () => {
          const cont = $("mdContinente").value;
          const paises = cont.startsWith("Seleccione") ? [] : await getJSON(`/cpp/paises?continente=${encodeURIComponent(cont)}`);
          $("mdPais").innerHTML = "<option>Seleccione país</option>" + paises.map(x => `<option>${x}</option>`).join("");
          $("mdPuerto").innerHTML = "<option>Seleccione puerto</option>";
        };
        $("mdPais").onchange = async () => {
          const cont = $("mdContinente").value;
          const pais = $("mdPais").value;
          const puertos = pais.startsWith("Seleccione") ? [] : await getJSON(`/cpp/puertos?pais=${encodeURIComponent(pais)}${cont && !cont.startsWith("Seleccione") ? `&continente=${encodeURIComponent(cont)}` : ""}`);
          $("mdPuerto").innerHTML = "<option>Seleccione puerto</option>" + puertos.map(x => `<option>${x}</option>`).join("");
        };
      } catch {}
    }
    async function applyMasterFilter() {
      const tipo = $("mdTipo").value;
      const map = { Cliente:"clientes", Proveedor:"proveedores", Empleado:"empleados", Surveyor:"surveyores", Servicio:"servicios_md", Puerto:"puertos" };
      if (tipo === "Puerto") {
        renderPortsMasterView();
        const cont = valueFrom("mdContinente");
        const pais = valueFrom("mdPais");
        const puerto = valueFrom("mdPuerto");
        await loadPortFilterContinents(cont && !cont.startsWith("Seleccione") ? cont : "");
        if (cont && !cont.startsWith("Seleccione")) {
          $("portFilterCont").value = cont;
          await loadPortFilterCountries(pais && !pais.startsWith("Seleccione") ? pais : "");
        }
        if (pais && !pais.startsWith("Seleccione")) {
          $("portFilterPais").value = pais;
          await loadPortFilterPorts(puerto && !puerto.startsWith("Seleccione") ? puerto : "");
        }
        if (puerto && !puerto.startsWith("Seleccione")) $("portFilterPuerto").value = puerto;
        await loadPorts();
        return;
      }
      if (map[tipo]) openMasterView(map[tipo]);
    }
    async function openMasterView(key) {
      selectedMasterView = catalog.master_data_views.find(v => v.key === key);
      const ws = $("masterWorkspace");
      ws.classList.remove("hidden");
      ws.innerHTML = `<div class="panel-head"><h2>${selectedMasterView.label}</h2></div>`;
      if (key === "bank_accounts") {
        openBankAccounts();
        return;
      }
      if (key === "company_fiscal") {
        await openCompanyFiscalForm();
        return;
      }
      if (key === "puertos") {
        renderPortsMasterView();
        return;
      }
      try {
        const payload = await getJSON(selectedMasterView.endpoint);
        const rows = rowsFromPayload(payload);
        currentRows = rows;
        ws.innerHTML = `<div class="panel-head"><h2>${selectedMasterView.label}</h2><div class="toolbar"><button onclick="openMasterForm('${key}', null, 'edit')">Nuevo</button><span class="muted">${rows.length} registros</span></div></div>${renderTable(rows, selectedMasterView.primary, key)}`;
      } catch (err) {
        ws.innerHTML = `<div class="panel-head"><h2>${selectedMasterView.label}</h2></div><div class="status error">No se pudo cargar: ${err.message}</div>`;
      }
    }
    function rowsFromPayload(payload) {
      if (Array.isArray(payload)) return payload;
      if (Array.isArray(payload.data)) return payload.data;
      if (Array.isArray(payload.items)) return payload.items;
      if (payload && typeof payload === "object") return [payload];
      return [];
    }
    function renderTable(rows, preferred, viewKey) {
      if (!rows.length) return '<div class="status">Sin datos para esta pantalla.</div>';
      const keys = (preferred || []).filter(k => Object.prototype.hasOwnProperty.call(rows[0], k));
      const fallback = Object.keys(rows[0]).filter(k => !String(k).toLowerCase().includes("hash")).slice(0, 8);
      const cols = keys.length ? keys : fallback;
      return `<div class="table-wrap"><table><thead><tr>${cols.map(k => `<th>${esc(k)}</th>`).join("")}<th>Acción</th></tr></thead><tbody>${rows.slice(0,100).map((row, i) => `<tr>${cols.map(k => `<td>${esc(row[k])}</td>`).join("")}<td><div class="toolbar"><button class="secondary" onclick="openMasterForm('${viewKey}', ${i}, 'view')">Ver</button><button onclick="openMasterForm('${viewKey}', ${i}, 'edit')">Editar</button><button class="brown" onclick="deleteMasterRecord('${viewKey}', ${i})">Inhabilitar</button></div></td></tr>`).join("")}</tbody></table></div>`;
    }
    function renderPortsMasterView() {
      const ws = $("masterWorkspace");
      ws.classList.remove("hidden");
      ws.innerHTML = `
        <div class="panel-head">
          <h2>Puertos</h2>
          <div class="toolbar"><button onclick="openPortForm(null)">Nuevo</button><span id="portsCount" class="muted">Presione Buscar</span></div>
        </div>
        <div class="finance-filter-row">
          <label>Continente<select id="portFilterCont" onchange="loadPortFilterCountries()"><option value="">Seleccione continente</option></select></label>
          <label>País<select id="portFilterPais" onchange="loadPortFilterPorts()"><option value="">Seleccione país</option></select></label>
          <label>Puerto<select id="portFilterPuerto"><option value="">Seleccione puerto</option></select></label>
          <button class="secondary" onclick="loadPortFilterContinents()">Cargar combos</button>
          <button onclick="loadPorts()">Buscar</button>
          <button class="secondary" onclick="clearPortFilters()">Limpiar</button>
        </div>
        <div id="portsMsg" class="status hidden"></div>
        <div id="portsTable" class="workspace"><div class="status">Cargue combos si desea filtrar, luego presione Buscar.</div></div>`;
    }
    async function loadPortFilterContinents(selected="") {
      const el = $("portFilterCont");
      if (!el) return;
      el.innerHTML = '<option value="">Cargando...</option>';
      try {
        const rows = await getJSON("/cpp/continentes");
        el.innerHTML = options(rows, selected, "Seleccione continente");
      } catch (err) {
        el.innerHTML = '<option value="">Seleccione continente</option>';
        showPortsMsg(err.message, true);
      }
    }
    async function loadPortFilterCountries(selected="") {
      const cont = valueFrom("portFilterCont");
      const pais = $("portFilterPais");
      const puerto = $("portFilterPuerto");
      if (!pais) return;
      pais.innerHTML = '<option value="">Seleccione país</option>';
      if (puerto) puerto.innerHTML = '<option value="">Seleccione puerto</option>';
      if (!cont) return;
      try {
        const rows = await getJSON(`/cpp/paises?continente=${encodeURIComponent(cont)}`);
        pais.innerHTML = options(rows, selected, "Seleccione país");
      } catch (err) {
        showPortsMsg(err.message, true);
      }
    }
    async function loadPortFilterPorts(selected="") {
      const cont = valueFrom("portFilterCont");
      const pais = valueFrom("portFilterPais");
      const puerto = $("portFilterPuerto");
      if (!puerto) return;
      puerto.innerHTML = '<option value="">Seleccione puerto</option>';
      if (!pais) return;
      try {
        const rows = await getJSON(`/cpp/puertos?pais=${encodeURIComponent(pais)}${cont ? `&continente=${encodeURIComponent(cont)}` : ""}`);
        puerto.innerHTML = options(rows, selected, "Seleccione puerto");
      } catch (err) {
        showPortsMsg(err.message, true);
      }
    }
    function portsParams() {
      const params = new URLSearchParams({ page:"1", page_size:"100" });
      [["portFilterCont","continente"],["portFilterPais","pais"],["portFilterPuerto","puerto"]].forEach(([id,key]) => {
        const value = valueFrom(id);
        if (value) params.set(key, value);
      });
      return params.toString();
    }
    function showPortsMsg(message, isError=false) {
      const msg = $("portsMsg");
      if (!msg) return;
      msg.className = isError ? "status error" : "status";
      msg.textContent = message;
    }
    function clearPortsMsg() {
      const msg = $("portsMsg");
      if (!msg) return;
      msg.className = "status hidden";
      msg.textContent = "";
    }
    async function loadPorts() {
      const table = $("portsTable");
      showPortsMsg("Consultando puertos...");
      try {
        const payload = await getJSON(`/cpp/ports?${portsParams()}`);
        portRows = rowsFromPayload(payload);
        currentRows = portRows;
        clearPortsMsg();
        if ($("portsCount")) $("portsCount").textContent = `${portRows.length} registros`;
        renderPortsTable();
      } catch (err) {
        table.innerHTML = "";
        showPortsMsg(err.message, true);
      }
    }
    function renderPortsTable() {
      const table = $("portsTable");
      if (!portRows.length) {
        table.innerHTML = '<div class="status">Sin puertos para los filtros seleccionados.</div>';
        return;
      }
      const cols = ["id","continente","pais","puerto"];
      table.innerHTML = `<div class="table-wrap"><table><thead><tr>${cols.map(c => `<th>${esc(c)}</th>`).join("")}<th>Acción</th></tr></thead><tbody>${portRows.map((row, i) => `<tr>${cols.map(c => `<td>${esc(row[c])}</td>`).join("")}<td><div class="toolbar"><button class="secondary" onclick="openPortForm(${i}, 'view')">Ver</button><button onclick="openPortForm(${i}, 'edit')">Editar</button><button class="brown" onclick="deletePortRecord(${i})">Eliminar</button></div></td></tr>`).join("")}</tbody></table></div>`;
    }
    function clearPortFilters() {
      ["portFilterCont","portFilterPais","portFilterPuerto"].forEach(id => { if ($(id)) $(id).innerHTML = `<option value="">${id === "portFilterCont" ? "Seleccione continente" : id === "portFilterPais" ? "Seleccione país" : "Seleccione puerto"}</option>`; });
      portRows = [];
      currentRows = [];
      if ($("portsCount")) $("portsCount").textContent = "Presione Buscar";
      clearPortsMsg();
      if ($("portsTable")) $("portsTable").innerHTML = '<div class="status">Cargue combos si desea filtrar, luego presione Buscar.</div>';
    }
    function portFormValue(row, key) {
      return esc(row?.[key] ?? "");
    }
    function openPortForm(rowIndex=null, mode="edit") {
      const editing = rowIndex !== null && rowIndex !== undefined;
      const row = editing ? portRows[rowIndex] : {};
      const readonly = mode === "view";
      const ws = $("masterWorkspace");
      ws.classList.remove("hidden");
      ws.innerHTML = `
        <div class="panel-head"><h2>${editing ? (readonly ? "Ver" : "Editar") : "Agregar"} Puerto</h2><span class="muted">El ID se genera automáticamente al guardar</span></div>
        <div class="form-grid">
          ${editing ? `<label>ID<input id="portFormId" value="${portFormValue(row, "id")}" readonly /></label>` : ""}
          <label>Continente<input id="portFormContinente" value="${portFormValue(row, "continente")}" list="portContinentesList" required /></label>
          <label>País<input id="portFormPais" value="${portFormValue(row, "pais")}" list="portPaisesList" required /></label>
          <label>Puerto<input id="portFormPuerto" value="${portFormValue(row, "puerto")}" required /></label>
          <datalist id="portContinentesList"></datalist>
          <datalist id="portPaisesList"></datalist>
        </div>
        <div class="md-actions">
          ${readonly ? "" : `<button class="green" onclick="savePortRecord(${editing ? Number(row.id) : "null"})">Guardar</button>`}
          ${editing && !readonly ? `<button class="brown" onclick="deletePortById(${Number(row.id)})">Eliminar</button>` : ""}
          <button class="secondary" onclick="renderPortsMasterView()">Volver</button>
        </div>
        <div id="portFormMsg" class="status hidden"></div>`;
      if (readonly) ["portFormContinente","portFormPais","portFormPuerto"].forEach(id => { if ($(id)) $(id).disabled = true; });
      loadPortFormDatalists().catch(() => null);
    }
    async function loadPortFormDatalists() {
      const conts = await getJSON("/cpp/continentes").catch(() => []);
      if ($("portContinentesList")) $("portContinentesList").innerHTML = rowsList(conts).map(x => `<option value="${esc(x)}"></option>`).join("");
      const cont = valueFrom("portFormContinente");
      const paises = cont ? await getJSON(`/cpp/paises?continente=${encodeURIComponent(cont)}`).catch(() => []) : [];
      if ($("portPaisesList")) $("portPaisesList").innerHTML = rowsList(paises).map(x => `<option value="${esc(x)}"></option>`).join("");
      const contInput = $("portFormContinente");
      if (contInput) contInput.onchange = loadPortFormDatalists;
    }
    function portPayloadFromForm() {
      return {
        continente:valueFrom("portFormContinente"),
        pais:valueFrom("portFormPais"),
        puerto:valueFrom("portFormPuerto")
      };
    }
    async function savePortRecord(id=null) {
      const msg = $("portFormMsg");
      msg.className = "status";
      msg.textContent = "Guardando...";
      try {
        const payload = portPayloadFromForm();
        if (!payload.continente || !payload.pais || !payload.puerto) throw new Error("Continente, país y puerto son requeridos.");
        await sendJSON(id ? "PUT" : "POST", id ? `/cpp/ports/${encodeURIComponent(id)}` : "/cpp/ports", payload);
        renderPortsMasterView();
        await loadPortFilterContinents(payload.continente);
        $("portFilterCont").value = payload.continente;
        await loadPortFilterCountries(payload.pais);
        $("portFilterPais").value = payload.pais;
        await loadPortFilterPorts(payload.puerto);
        $("portFilterPuerto").value = payload.puerto;
        await loadPorts();
      } catch (err) {
        msg.className = "status error";
        msg.textContent = err.message;
      }
    }
    async function deletePortRecord(rowIndex) {
      const row = portRows[rowIndex];
      if (!row) return;
      await deletePortById(row.id);
    }
    async function deletePortById(id) {
      if (!id) return;
      if (!confirm(`¿Eliminar puerto ${id}?`)) return;
      const msg = $("portFormMsg") || $("portsMsg");
      if (msg) {
        msg.className = "status";
        msg.textContent = "Eliminando...";
      }
      try {
        await sendJSON("DELETE", `/cpp/ports/${encodeURIComponent(id)}`, null);
        renderPortsMasterView();
      } catch (err) {
        if (msg) {
          msg.className = "status error";
          msg.textContent = err.message;
        } else {
          alert(err.message);
        }
      }
    }
    function codePrefix() {
      return selectedCompany().startsWith("MCI") ? "MCI" : "MSL";
    }
    async function nextCode(config) {
      if (!config.ultimo) return "";
      try {
        const data = await getJSON(config.ultimo);
        const next = Number(data.ultimo || 0) + 1;
        return `${codePrefix()}-${String(next).padStart(4, "0")}-${config.suffix}`;
      } catch {
        return "";
      }
    }
    function rowValue(row, key) {
      if (!row) return undefined;
      if (Object.prototype.hasOwnProperty.call(row, key)) return row[key];
      const canonical = value => String(value || "").toLowerCase().replace(/[^a-z0-9]/g, "");
      const lower = canonical(key);
      const found = Object.keys(row).find(k => canonical(k) === lower);
      return found ? row[found] : undefined;
    }
    function normalizeClientePayload(payload) {
      if (payload.FechaDePago === "") payload.FechaDePago = null;
      return payload;
    }
    function normalizePayload(key, payload) {
      if (key === "clientes") return normalizeClientePayload(payload);
      if (key === "company_fiscal") {
        const clone = { ...payload };
        delete clone.company_code;
        return clone;
      }
      return payload;
    }
    function buildMasterPayload(config) {
      const payload = {};
      config.fields.forEach(([key,,type]) => {
        const el = $(`md_${key}`);
        if (!el) return;
        payload[key] = type === "checkbox" ? el.checked : el.value;
      });
      payload.company_code = selectedCompany();
      return normalizePayload(currentMasterKey || "", payload);
    }
    function masterFieldHtml(field, row) {
      const [key, label, type, fallback, required] = field;
      const value = rowValue(row, key);
      const val = value === undefined || value === null ? fallback : value;
      const req = required ? " required" : "";
      const wide = type === "textarea" ? " wide" : "";
      if (type === "textarea") return `<label class="${wide}">${esc(label)}<textarea id="md_${key}"${req}>${esc(val)}</textarea></label>`;
      if (type === "checkbox") {
        const checked = val === true || String(val).toLowerCase() === "true" || String(val).toLowerCase() === "activo" ? " checked" : "";
        return `<label>${esc(label)}<input id="md_${key}" type="checkbox"${checked} /></label>`;
      }
      return `<label>${esc(label)}<input id="md_${key}" type="${type}" value="${esc(val)}"${req} /></label>`;
    }
    let currentMasterKey = "";
    async function openMasterForm(key, rowIndex, mode="edit") {
      if (key === "puertos") {
        if (rowIndex !== null && rowIndex !== undefined && !portRows.length && currentRows.length) {
          portRows = currentRows;
        }
        openPortForm(rowIndex, mode);
        return;
      }
      currentMasterKey = key;
      const config = MASTER_CONFIG[key];
      if (!config) return;
      const editing = rowIndex !== null && rowIndex !== undefined;
      let row = editing ? currentRows[rowIndex] : {};
      const ws = $("masterWorkspace");
      ws.classList.remove("hidden");
      if (editing) {
        ws.innerHTML = `<div class="panel-head"><h2>${mode === "view" ? "Ver" : "Editar"} ${config.title}</h2></div>`;
        const code = rowValue(row, config.codeKey);
        try {
          row = await getJSON(`${config.endpoint}/${encodeURIComponent(code)}`);
        } catch (err) {
          ws.innerHTML = `<div class="panel-head"><h2>${config.title}</h2></div><div class="status error">No se pudo consultar GET: ${err.message}</div>`;
          return;
        }
      }
      const readonly = mode === "view";
      ws.innerHTML = `<div class="panel-head"><h2>${editing ? "Editar" : "Agregar"} ${config.title}</h2></div>
        <div class="form-grid">${config.fields.map(f => masterFieldHtml(f, row)).join("")}</div>
        <div class="md-actions">
          ${readonly ? "" : `<button class="green" onclick="saveMasterRecord('${key}', ${editing ? "true" : "false"})">Guardar</button>`}
          ${editing ? `<button class="brown" onclick="deleteMasterRecord('${key}')">Inhabilitar / eliminar</button>` : ""}
          <button class="secondary" onclick="openMasterView('${key}')">Volver</button>
        </div>
        <div id="masterFormMsg" class="status hidden"></div>`;
      if (!editing && config.ultimo) {
        const code = await nextCode(config);
        const input = $(`md_${config.codeKey}`);
        if (input && code) input.value = code;
      }
      const codeInput = $(`md_${config.codeKey}`);
      if (editing && codeInput) codeInput.readOnly = true;
      if (readonly) config.fields.forEach(([fieldKey]) => {
        const el = $(`md_${fieldKey}`);
        if (el) el.disabled = true;
      });
    }
    async function saveMasterRecord(key, editing) {
      const config = MASTER_CONFIG[key];
      const msg = $("masterFormMsg");
      msg.className = "status";
      msg.textContent = "Guardando...";
      try {
        const payload = buildMasterPayload(config);
        const path = editing ? config.update : config.add;
        const recordId = payload[config.codeKey] || $(`md_${config.codeKey}`)?.value || "";
        const resolvedPath = path
          .replace("{company}", encodeURIComponent(selectedCompany()))
          .replace("{id}", encodeURIComponent(recordId));
        const data = await sendJSON(editing ? "PUT" : "POST", resolvedPath, payload);
        msg.textContent = data.msg || "Guardado correctamente.";
        await openMasterView(key);
      } catch (err) {
        msg.className = "status error";
        msg.textContent = err.message;
      }
    }
    async function deleteMasterRecord(key, rowIndex=null) {
      const config = MASTER_CONFIG[key];
      const code = rowIndex === null ? $(`md_${config.codeKey}`)?.value : rowValue(currentRows[rowIndex], config.codeKey);
      if (!code) return;
      if (!confirm(`¿Inhabilitar/eliminar ${config.title} ${code}?`)) return;
      let msg = $("masterFormMsg");
      if (!msg) {
        const ws = $("masterWorkspace");
        ws.classList.remove("hidden");
        ws.innerHTML = `<div id="masterFormMsg" class="status">Aplicando...</div>`;
        msg = $("masterFormMsg");
      }
      msg.className = "status";
      msg.textContent = "Aplicando...";
      try {
        const data = await sendJSON("DELETE", `${config.endpoint}/${encodeURIComponent(code)}`);
        msg.textContent = data.msg || "Actualizado.";
        await openMasterView(key);
      } catch (err) {
        msg.className = "status error";
        msg.textContent = err.message;
      }
    }
    function bankPayloadFromForm() {
      return {
        bank_name:$("bank_bank_name").value,
        currency:$("bank_currency").value,
        iban:$("bank_iban").value,
        swift_code:$("bank_swift_code").value,
        bank_address:$("bank_bank_address").value,
        uid:$("bank_uid").value,
        beneficiary_name:$("bank_beneficiary_name").value
      };
    }
    function bankForm(row=null) {
      const editing = !!row;
      const val = key => esc(row?.[key] ?? "");
      $("masterWorkspace").innerHTML = `<div class="panel-head"><h2>${editing ? "Editar" : "Agregar"} dato bancario</h2></div>
        <div class="form-grid">
          <label>Banco<input id="bank_bank_name" value="${val("bank_name")}" required /></label>
          <label>Moneda<select id="bank_currency"><option>CRC</option><option>USD</option><option>EUR</option></select></label>
          <label>Cuenta IBAN<input id="bank_iban" value="${val("iban")}" required /></label>
          <label>Swift Code<input id="bank_swift_code" value="${val("swift_code")}" /></label>
          <label>UID<input id="bank_uid" value="${val("uid")}" /></label>
          <label>Beneficiario<input id="bank_beneficiary_name" value="${val("beneficiary_name")}" required /></label>
          <label class="wide">Dirección banco<textarea id="bank_bank_address">${val("bank_address")}</textarea></label>
        </div>
        <div class="md-actions">
          <button class="green" onclick="saveBankAccount(${editing ? row.id : "null"})">Guardar</button>
          ${editing ? `<button class="brown" onclick="deleteBankAccount(${row.id})">Eliminar</button>` : ""}
          <button class="secondary" onclick="loadBankAccounts()">Volver</button>
        </div>
        <div id="bankMsg" class="status hidden"></div>`;
      $("bank_currency").value = row?.currency || "CRC";
    }
    function bankDownloadLink(row, language) {
      const params = new URLSearchParams({
        request_user:session?.usuario || "",
        request_role:session?.rol || "",
        bank_access_token:bankAccessToken,
        company:selectedCompany(),
        company_name:(($("companyTop")?.selectedOptions?.[0] || $("company")?.selectedOptions?.[0])?.textContent || "").split("|").slice(1).join("|").trim(),
        language
      });
      return `/master-data/bank-accounts/${encodeURIComponent(row.id)}/letter-download.pdf?${params.toString()}`;
    }
    async function openBankAccounts() {
      const ws = $("masterWorkspace");
      ws.classList.remove("hidden");
      if (!bankAccessToken) {
        ws.innerHTML = `<div class="panel-head"><h2>Datos bancarios</h2></div>
          <div class="form-grid">
            <label>Código Microsoft Authenticator<input id="bankTotp" inputmode="numeric" autocomplete="one-time-code" placeholder="000000" /></label>
          </div>
          <div class="md-actions"><button onclick="unlockBankAccounts()">Revalidar</button></div>
          <div id="bankMsg" class="status hidden"></div>`;
        return;
      }
      await loadBankAccounts();
    }
    async function unlockBankAccounts() {
      const msg = $("bankMsg");
      msg.className = "status";
      msg.textContent = "Revalidando...";
      try {
        const data = await sendJSON("POST", "/master-data/bank-accounts/unlock", { totp_code:$("bankTotp").value });
        bankAccessToken = data.access_token || "";
        await loadBankAccounts();
      } catch (err) {
        msg.className = "status error";
        msg.textContent = err.message;
      }
    }
    async function loadBankAccounts() {
      const ws = $("masterWorkspace");
      ws.classList.remove("hidden");
      ws.innerHTML = `<div class="panel-head"><h2>Datos bancarios</h2></div>`;
      try {
        const payload = await getJSON("/master-data/bank-accounts", { "X-Bank-Access-Token":bankAccessToken });
        bankRows = rowsFromPayload(payload);
        const cols = ["bank_name","currency","iban","swift_code","uid","beneficiary_name"];
        ws.innerHTML = `<div class="panel-head"><h2>Datos bancarios</h2><div class="toolbar"><button onclick="bankForm()">Nuevo</button><span class="muted">${bankRows.length} registros</span></div></div>
          <div class="table-wrap"><table><thead><tr>${cols.map(c => `<th>${esc(c)}</th>`).join("")}<th>Acción</th></tr></thead><tbody>${bankRows.map((row, i) => `<tr>${cols.map(c => `<td>${esc(row[c])}</td>`).join("")}<td><div class="toolbar"><button class="secondary" onclick="viewBankAccount(${i})">Ver</button><button onclick="bankForm(bankRows[${i}])">Editar</button><a href="${bankDownloadLink(row, "ES")}" target="_blank"><button class="green">PDF ES</button></a><a href="${bankDownloadLink(row, "EN")}" target="_blank"><button class="secondary">PDF EN</button></a><button class="brown" onclick="deleteBankAccount(${row.id})">Eliminar</button></div></td></tr>`).join("")}</tbody></table></div>`;
      } catch (err) {
        bankAccessToken = "";
        ws.innerHTML = `<div class="panel-head"><h2>Datos bancarios</h2></div><div class="status error">${esc(err.message)}</div><div class="md-actions"><button onclick="openBankAccounts()">Revalidar</button></div>`;
      }
    }
    function viewBankAccount(index) {
      bankForm(bankRows[index]);
      ["bank_bank_name","bank_currency","bank_iban","bank_swift_code","bank_bank_address","bank_uid","bank_beneficiary_name"].forEach(id => {
        const el = $(id);
        if (el) el.disabled = true;
      });
      $("bankMsg").className = "status";
      $("bankMsg").textContent = "Vista de solo lectura.";
    }
    async function saveBankAccount(id=null) {
      const msg = $("bankMsg");
      msg.className = "status";
      msg.textContent = "Guardando...";
      try {
        const path = id ? `/master-data/bank-accounts/${encodeURIComponent(id)}` : "/master-data/bank-accounts";
        const data = await sendJSON(id ? "PUT" : "POST", path, bankPayloadFromForm(), { "X-Bank-Access-Token":bankAccessToken });
        msg.textContent = data.id ? "Guardado correctamente." : "Guardado.";
        await loadBankAccounts();
      } catch (err) {
        msg.className = "status error";
        msg.textContent = err.message;
      }
    }
    async function deleteBankAccount(id) {
      if (!confirm(`¿Eliminar dato bancario ${id}?`)) return;
      const ws = $("masterWorkspace");
      ws.innerHTML = `<div id="bankMsg" class="status">Eliminando...</div>`;
      try {
        await sendJSON("DELETE", `/master-data/bank-accounts/${encodeURIComponent(id)}`, null, { "X-Bank-Access-Token":bankAccessToken });
        await loadBankAccounts();
      } catch (err) {
        $("bankMsg").className = "status error";
        $("bankMsg").textContent = err.message;
      }
    }
    async function openCompanyFiscalForm() {
      const ws = $("masterWorkspace");
      ws.classList.remove("hidden");
      ws.innerHTML = `<div class="panel-head"><h2>Datos fiscales</h2></div>`;
      try {
        const row = await getJSON("/companies/current");
        currentRows = [row];
        await openMasterForm("company_fiscal", 0, "edit");
      } catch (err) {
        ws.innerHTML = `<div class="panel-head"><h2>Datos fiscales</h2></div><div class="status error">No se pudo consultar datos fiscales: ${err.message}</div>`;
      }
    }
    function renderServicios() {
      selectedServiceIndex = null;
      $("content").innerHTML = `
        <div class="card panel">
          <div class="panel-head">
            <h2>Servicios</h2>
            <span id="svcCount" class="muted">Presione Buscar</span>
          </div>
          <div class="service-actions">
            <button onclick="openServiceForm()">+ Agregar servicio</button>
            <button class="secondary" onclick="confirmSelectedService()">Generar Consecutivo</button>
            <button onclick="editSelectedService()">Editar servicio</button>
            <button class="green" onclick="closeSelectedService()">Finalizar Servicio</button>
            <button class="secondary" onclick="viewSelectedService()">Ver</button>
            <button class="secondary" onclick="delaySelectedService()">Demoras</button>
            <button class="brown" onclick="cancelSelectedService()">Cancelar</button>
            <button class="dark" onclick="deleteSelectedService()">Eliminar</button>
            <button class="secondary" onclick="exportServicios('csv')">CSV</button>
            <button class="secondary" onclick="exportServicios('pdf')">PDF</button>
            <button class="secondary" onclick="exportServicios('xml')">XML</button>
            <button class="secondary" onclick="exportServicios('excel')">Excel</button>
          </div>
          <div class="filters service-filters">
            <label>Buscar<input id="svcQ" placeholder="Consecutivo, buque, cliente, informe, surveyor..." /></label>
            <label>Año<select id="svcYear"><option value="">Todos</option></select></label>
            <label>Tipo<select id="svcTipo"></select></label>
            <label>Estado<select id="svcEstado"></select></label>
            <label>Cliente<select id="svcCliente"></select></label>
            <button onclick="loadServiceMeta().then(() => loadServicios(1)).catch(err => showServiceMsg(err.message, true))">Buscar</button>
            <button class="secondary" onclick="clearServiceFilters()">Limpiar</button>
            <label>Continente<select id="svcContinente"></select></label>
            <label>País<select id="svcPais"></select></label>
            <label>Puerto<select id="svcPuerto"></select></label>
            <label>Operación<select id="svcOperacion"></select></label>
            <label>Surveyor<select id="svcSurveyor"></select></label>
          </div>
          <div id="svcMsg" class="status hidden"></div>
          <div id="svcTable" class="workspace"></div>
        </div>`;
      for (let y = {year}; y >= {year} - 6; y--) {
        $("svcYear").insertAdjacentHTML("beforeend", `<option value="${y}"${String(y)===$("year").value ? " selected" : ""}>${y}</option>`);
      }
      ["svcTipo","svcEstado","svcCliente","svcContinente","svcPais","svcPuerto","svcOperacion","svcSurveyor"].forEach(id => {
        if ($(id)) $(id).innerHTML = '<option value="">Todos</option>';
      });
      $("svcTable").innerHTML = '<div class="status">Configure filtros y presione Buscar.</div>';
    }
    async function loadServiceMeta() {
      const meta = await getJSON("/servicios/_meta/filtros");
      serviceMeta = meta || {};
      $("svcTipo").innerHTML = options(serviceMeta.tipo, "", "Todos");
      $("svcEstado").innerHTML = options(serviceMeta.status, "", "Todos");
      $("svcCliente").innerHTML = options(serviceMeta.cliente, "", "Todos");
      $("svcOperacion").innerHTML = options(serviceMeta.operacion, "", "Todos");
      $("svcSurveyor").innerHTML = options(serviceMeta.surveyor, "", "Todos");
      const continentes = await getJSON("/cpp/continentes").catch(() => serviceMeta.continente || []);
      $("svcContinente").innerHTML = options(continentes, "", "Todos");
      $("svcPais").innerHTML = options(serviceMeta.pais, "", "Todos");
      $("svcPuerto").innerHTML = options(serviceMeta.puerto, "", "Todos");
      $("svcContinente").onchange = async () => {
        const cont = valueFrom("svcContinente");
        const paises = cont ? await getJSON(`/cpp/paises?continente=${encodeURIComponent(cont)}`).catch(() => serviceMeta.pais || []) : serviceMeta.pais || [];
        $("svcPais").innerHTML = options(paises, "", "Todos");
        $("svcPuerto").innerHTML = options([], "", "Todos");
      };
      $("svcPais").onchange = async () => {
        const pais = valueFrom("svcPais");
        const cont = valueFrom("svcContinente");
        let path = `/cpp/puertos?pais=${encodeURIComponent(pais)}`;
        if (cont) path += `&continente=${encodeURIComponent(cont)}`;
        const puertos = pais ? await getJSON(path).catch(() => serviceMeta.puerto || []) : serviceMeta.puerto || [];
        $("svcPuerto").innerHTML = options(puertos, "", "Todos");
      };
    }
    function serviceQueryParams(page=1) {
      const params = new URLSearchParams({ page:String(page), page_size:"50" });
      const map = {
        svcYear:"year", svcTipo:"tipo", svcEstado:"status", svcCliente:"cliente", svcContinente:"continente",
        svcPais:"pais", svcPuerto:"puerto", svcOperacion:"operacion", svcSurveyor:"surveyor", svcQ:"q"
      };
      Object.entries(map).forEach(([id, key]) => {
        const val = valueFrom(id);
        if (val && !val.toLowerCase().startsWith("seleccione")) params.set(key, val);
      });
      return params.toString();
    }
    async function loadServicios(page=1) {
      servicePage = page;
      showServiceMsg("Cargando servicios...", false);
      try {
        const payload = await getJSON(`/servicios/?${serviceQueryParams(page)}`);
        serviceRows = rowsList(payload).map(row => {
          const clean = { ...row };
          SERVICE_HIDDEN_COLUMNS.forEach(col => delete clean[col]);
          return clean;
        });
        serviceTotal = Number(payload.total || serviceRows.length || 0);
        selectedServiceIndex = null;
        selectedServiceIndexes = new Set();
        $("svcCount").textContent = `${intFmt.format(serviceTotal)} servicios`;
        $("svcMsg").classList.add("hidden");
        renderServiceTable();
      } catch (err) {
        showServiceMsg(`No se pudo consultar GET servicios: ${err.message}`, true);
      }
    }
    function showServiceMsg(text, isError=false) {
      const msg = $("svcMsg");
      if (!msg) return;
      msg.className = isError ? "status error" : "status";
      msg.textContent = text;
    }
    function serviceStatusBadge(status) {
      const value = String(status || "");
      const klass = value.toLowerCase().includes("cancel") ? "cancel" : value.toLowerCase().includes("cerr") || value.toLowerCase().includes("final") ? "closed" : "open";
      return `<span class="badge ${klass}">${esc(value || "Sin estado")}</span>`;
    }
    function serviceCell(row, col) {
      if (col === "estado") return serviceStatusBadge(row[col]);
      const value = row[col];
      if (["honorarios","costo_operativo","costo_tarjetas","valor_factura"].includes(col)) return esc(Number(value || 0).toLocaleString("en-US", { minimumFractionDigits:2, maximumFractionDigits:2 }));
      return esc(value ?? "");
    }
    function renderServiceTable() {
      const target = $("svcTable");
      if (!serviceRows.length) {
        target.innerHTML = '<div class="status">Sin servicios para los filtros seleccionados.</div>';
        return;
      }
      target.innerHTML = `
        <div class="table-wrap">
          <table>
            <thead><tr><th class="pick-col"></th>${visibleServiceColumns().map(c => `<th>${esc(c)}</th>`).join("")}</tr></thead>
            <tbody>${serviceRows.map((row, i) => {
              const missingCosts = String(row.estado || "").toLowerCase().includes("oper") && !Number(row.honorarios || 0) && !Number(row.costo_operativo || 0) && !Number(row.costo_tarjetas || 0);
              const selected = selectedServiceIndexes.has(i);
              return `<tr id="svcRow_${i}" class="${selected ? "service-selected" : missingCosts ? "service-warning" : ""}" onclick="toggleServiceRow(${i})"><td class="pick-col"><input class="row-pick" type="checkbox" ${selected ? "checked" : ""} onclick="event.stopPropagation(); toggleServiceRow(${i}, this.checked)" /></td>${visibleServiceColumns().map(c => `<td>${serviceCell(row, c)}</td>`).join("")}</tr>`;
            }).join("")}</tbody>
          </table>
        </div>
        <div class="pager">
          <button class="secondary" onclick="loadServicios(Math.max(1, servicePage-1))">Anterior</button>
          <span class="muted">Página ${servicePage} · ${serviceRows.length} visibles de ${intFmt.format(serviceTotal)}</span>
          <button class="secondary" onclick="loadServicios(servicePage+1)" ${servicePage*50 >= serviceTotal ? "disabled" : ""}>Siguiente</button>
        </div>`;
    }
    function toggleServiceRow(index, checked=null) {
      const next = checked === null ? !selectedServiceIndexes.has(index) : checked;
      selectedServiceIndex = setIndexSelection(selectedServiceIndexes, index, next);
      renderServiceTable();
    }
    function selectServiceRow(index) {
      selectedServiceIndexes = new Set([index]);
      selectedServiceIndex = index;
      renderServiceTable();
    }
    function clearServiceFilters() {
      ["svcQ","svcYear","svcTipo","svcEstado","svcCliente","svcContinente","svcPais","svcPuerto","svcOperacion","svcSurveyor"].forEach(id => {
        const el = $(id);
        if (el) el.value = "";
      });
      serviceRows = [];
      selectedServiceIndex = null;
      selectedServiceIndexes = new Set();
      serviceTotal = 0;
      $("svcCount").textContent = "Presione Buscar";
      $("svcMsg").classList.add("hidden");
      $("svcTable").innerHTML = '<div class="status">Configure filtros y presione Buscar.</div>';
    }
    async function serviceLookup(kind, term="") {
      const params = new URLSearchParams({ page:"1", page_size:"250" });
      if (term) params.set("q", term);
      const endpoints = {
        clientes:"/clientes",
        operaciones:"/servicios_md",
        surveyores:"/surveyores"
      };
      const data = await getJSON(`${endpoints[kind]}?${params.toString()}`).catch(() => ({ data:[] }));
      return rowsList(data);
    }
    async function ensureServiceCatalogs() {
      const [clientes, operaciones, surveyors] = await Promise.all([
        serviceLookup("clientes"),
        serviceLookup("operaciones"),
        getJSON("/servicios-surveyors/catalogo/lista").catch(() => ({ data:[] }))
      ]);
      serviceMeta.clientesCatalog = clientes;
      serviceMeta.operacionesCatalog = operaciones;
      serviceSurveyorCatalog = rowsList(surveyors).map(row => ({
        ...row,
        full_name:[row.nombre, row.apellidos].filter(Boolean).join(" ") || row.surveyor_nombre || row.nombre_completo || row.nombre || ""
      }));
    }
    function catalogOptionText(row, keys) {
      for (const key of keys) if (row?.[key]) return String(row[key]);
      return "";
    }
    function serviceSelectOptions(rows, selected, keys, placeholder="Seleccione") {
      const values = rowsList(rows).map(r => catalogOptionText(r, keys)).filter(Boolean);
      return options(values, selected || "", placeholder);
    }
    async function loadFormLocation(row={}) {
      const cont = valueFrom("svcForm_continente") || row.continente || "";
      const pais = valueFrom("svcForm_pais") || row.pais || "";
      $("svcForm_continente").innerHTML = options(await getJSON("/cpp/continentes").catch(() => serviceMeta.continente || []), cont, "Seleccione continente");
      $("svcForm_pais").innerHTML = options(cont ? await getJSON(`/cpp/paises?continente=${encodeURIComponent(cont)}`).catch(() => serviceMeta.pais || []) : serviceMeta.pais || [], pais, "Seleccione país");
      let puertoPath = `/cpp/puertos?pais=${encodeURIComponent(pais)}`;
      if (cont) puertoPath += `&continente=${encodeURIComponent(cont)}`;
      $("svcForm_puerto").innerHTML = options(pais ? await getJSON(puertoPath).catch(() => serviceMeta.puerto || []) : serviceMeta.puerto || [], row.puerto || "", "Seleccione puerto");
      $("svcForm_continente").onchange = async () => {
        const selected = valueFrom("svcForm_continente");
        const paises = selected ? await getJSON(`/cpp/paises?continente=${encodeURIComponent(selected)}`).catch(() => []) : [];
        $("svcForm_pais").innerHTML = options(paises, "", "Seleccione país");
        $("svcForm_puerto").innerHTML = options([], "", "Seleccione puerto");
      };
      $("svcForm_pais").onchange = async () => {
        const selectedPais = valueFrom("svcForm_pais");
        const selectedCont = valueFrom("svcForm_continente");
        let path = `/cpp/puertos?pais=${encodeURIComponent(selectedPais)}`;
        if (selectedCont) path += `&continente=${encodeURIComponent(selectedCont)}`;
        const puertos = selectedPais ? await getJSON(path).catch(() => []) : [];
        $("svcForm_puerto").innerHTML = options(puertos, "", "Seleccione puerto");
      };
    }
    function serviceFormValue(id) {
      const el = $("svcForm_" + id);
      return el ? el.value.trim() : "";
    }
    function servicePayload() {
      const surveyors = readSurveyorLines();
      const names = surveyors.map(s => s.surveyor_nombre).filter(Boolean);
      const honorarios = surveyors.reduce((sum, item) => sum + Number(item.honorario || 0), 0);
      return {
        tipo:serviceFormValue("tipo"),
        buque_contenedor:serviceFormValue("buque_contenedor"),
        cliente:serviceFormValue("cliente"),
        contacto:serviceFormValue("contacto"),
        detalle:serviceFormValue("detalle"),
        continente:serviceFormValue("continente"),
        pais:serviceFormValue("pais"),
        puerto:serviceFormValue("puerto"),
        operacion:serviceFormValue("operacion"),
        surveyor:names.length > 1 ? names.join(", ") : (names[0] || serviceFormValue("surveyor")),
        honorarios:String(honorarios || Number(serviceFormValue("honorarios") || 0)),
        costo_operativo:serviceFormValue("costo_operativo") || "0",
        costo_tarjetas:serviceFormValue("costo_tarjetas") || "0",
        fecha_inicio:serviceFormValue("fecha_inicio"),
        hora_inicio:serviceFormValue("hora_inicio"),
        fecha_fin:serviceFormValue("fecha_fin") || null,
        hora_fin:serviceFormValue("hora_fin") || null,
        fecha_factura:serviceFormValue("fecha_factura") || null,
        fecha_vencimiento:serviceFormValue("fecha_vencimiento") || null
      };
    }
    function estimatedServiceAmount(payload) {
      return Number(payload.valor_factura || 0)
        || (Number(payload.honorarios || 0) + Number(payload.costo_operativo || 0) + Number(payload.costo_tarjetas || 0));
    }
    async function applyCreditReleaseIfNeeded(payload) {
      const decision = await postJSON("/cliente-credito/order-to-cash/check", {
        cliente:payload.cliente,
        projected_amount:estimatedServiceAmount(payload),
        currency:"USD"
      });
      const money = value => Number(value || 0).toLocaleString("en-US", {minimumFractionDigits:2, maximumFractionDigits:2});
      const trend = decision.payment_trend || {};
      const alerts = Array.isArray(decision.risk_alerts) ? decision.risk_alerts : [];
      const alertBlock = alerts.length ? `\\nAlertas:\\n${alerts.map(item => `- ${item}`).join("\\n")}\\n` : "";
      const riskText =
        `${decision.message || "Revision crediticia."}\n\n` +
        `Limite: ${decision.currency} ${money(decision.credit_limit)}\n` +
        `CxC pendiente: ${decision.currency} ${money(decision.open_ar)}\n` +
        `CxC vencida: ${decision.currency} ${money(decision.overdue_ar)}\n` +
        `Nueva exposicion: ${decision.currency} ${money(decision.projected_exposure)}\n` +
        `Disponible proyectado: ${decision.currency} ${money(decision.available)}\n` +
        `Exceso: ${decision.currency} ${money(decision.over_amount)}\n` +
        `Payment trend: ${trend.label || trend.trend || "Sin datos"}\n` +
        `Estado credito: ${decision.estado_credito || "-"} | Hold manual: ${decision.hold_manual ? "Si" : "No"}\n` +
        alertBlock;
      if (!decision.requires_release) {
        if (decision.advisory_requires_ack) {
          const ok = confirm(`${riskText}\n¿Desea continuar con el servicio?`);
          if (!ok) throw new Error("Servicio detenido por alerta crediticia.");
        }
        return payload;
      }
      const role = String(session?.rol || "").toLowerCase();
      if (!["admin", "master"].includes(role)) {
        throw new Error(decision.message || "Cliente requiere liberacion crediticia de admin/master.");
      }
      const ok = confirm(`${riskText}\n¿Desea liberar y continuar?`);
      if (!ok) throw new Error("Servicio detenido por control crediticio.");
      const reason = prompt("Justificacion del release crediticio", decision.reason_code || "Release aprobado por admin/master");
      if (!reason || !reason.trim()) throw new Error("Justificacion de release crediticio requerida.");
      return { ...payload, credit_release_approved:true, credit_release_reason:reason };
    }
    function surveyorLineHtml(name="", amount="") {
      return `<div class="surveyor-line">
        <select class="svcSurveyorName">${serviceSelectOptions(serviceSurveyorCatalog, name, ["full_name","nombre_completo","nombre","surveyor_nombre"], "Seleccione surveyor")}</select>
        <input class="svcSurveyorAmount" type="number" step="0.01" value="${esc(amount)}" placeholder="Honorario" />
        <button class="secondary" type="button" onclick="this.closest('.surveyor-line').remove(); updateSurveyorTotals()">-</button>
      </div>`;
    }
    function readSurveyorLines() {
      return [...document.querySelectorAll(".surveyor-line")].map(line => ({
        surveyor_nombre:line.querySelector(".svcSurveyorName")?.value || "",
        honorario:Number(line.querySelector(".svcSurveyorAmount")?.value || 0)
      })).filter(item => item.surveyor_nombre);
    }
    function updateSurveyorTotals() {
      const total = readSurveyorLines().reduce((sum, item) => sum + Number(item.honorario || 0), 0);
      const input = $("svcForm_honorarios");
      if (input) input.value = String(total || "");
    }
    function addSurveyorLine(name="", amount="") {
      $("svcSurveyorLines").insertAdjacentHTML("beforeend", surveyorLineHtml(name, amount));
      document.querySelectorAll(".svcSurveyorAmount").forEach(el => el.oninput = updateSurveyorTotals);
    }
    async function openServiceForm(row=null) {
      await ensureServiceCatalogs();
      const editing = !!row;
      const val = key => esc(row?.[key] ?? "");
      document.body.insertAdjacentHTML("beforeend", `
        <div class="modal-backdrop" id="svcModal">
          <div class="modal">
            <div class="modal-head">
              <h2>${editing ? "Editar servicio " + esc(row.consec) : "Agregar servicio"}</h2>
              <button class="secondary" onclick="closeModal()">Cerrar</button>
            </div>
            <div class="form-grid">
              <label>Tipo<select id="svcForm_tipo"><option>Buque</option><option>Contenedor</option></select></label>
              <label>Buque / contenedor<input id="svcForm_buque_contenedor" value="${val("buque_contenedor")}" required /></label>
              <label>Cliente<select id="svcForm_cliente">${serviceSelectOptions(serviceMeta.clientesCatalog, row?.cliente, ["nombrejuridico","NombreJuridico","nombrecomercial","NombreComercial"], "Seleccione cliente")}</select></label>
              <label>Contacto<input id="svcForm_contacto" value="${val("contacto")}" /></label>
              <label>Continente<select id="svcForm_continente"></select></label>
              <label>País<select id="svcForm_pais"></select></label>
              <label>Puerto<select id="svcForm_puerto"></select></label>
              <label>Operación<select id="svcForm_operacion">${serviceSelectOptions(serviceMeta.operacionesCatalog, row?.operacion, ["nombre","Nombre"], "Seleccione operación")}</select></label>
              <label>Fecha inicio<input id="svcForm_fecha_inicio" type="date" value="${val("fecha_inicio")}" required /></label>
              <label>Hora inicio<input id="svcForm_hora_inicio" type="time" value="${val("hora_inicio")}" required /></label>
              <label>Fecha fin<input id="svcForm_fecha_fin" type="date" value="${val("fecha_fin")}" /></label>
              <label>Hora fin<input id="svcForm_hora_fin" type="time" value="${val("hora_fin")}" /></label>
              <label>Honorarios<input id="svcForm_honorarios" type="number" step="0.01" value="${val("honorarios")}" /></label>
              <label>Costo operativo<input id="svcForm_costo_operativo" type="number" step="0.01" value="${val("costo_operativo")}" /></label>
              <label>Costo tarjetas<input id="svcForm_costo_tarjetas" type="number" step="0.01" value="${val("costo_tarjetas")}" /></label>
              <label>Fecha factura<input id="svcForm_fecha_factura" type="date" value="${val("fecha_factura")}" /></label>
              <label>Fecha vencimiento<input id="svcForm_fecha_vencimiento" type="date" value="${val("fecha_vencimiento")}" /></label>
              <label class="wide">Detalle<textarea id="svcForm_detalle">${val("detalle")}</textarea></label>
              <input id="svcForm_surveyor" type="hidden" value="${val("surveyor")}" />
              <div class="wide surveyors-box">
                <div class="panel-head"><h2>Surveyors</h2><button type="button" onclick="addSurveyorLine()">+ Surveyor</button></div>
                <div id="svcSurveyorLines"></div>
              </div>
            </div>
            <div class="md-actions">
              <button class="green" onclick="saveService(${editing ? Number(row.consec) : "null"})">Guardar</button>
              <button class="secondary" onclick="closeModal()">Cancelar</button>
            </div>
            <div id="svcFormMsg" class="status hidden"></div>
          </div>
        </div>`);
      $("svcForm_tipo").value = row?.tipo || "Buque";
      await loadFormLocation(row || {});
      let savedSurveyors = [];
      if (editing) {
        const loaded = await getJSON(`/servicios-surveyors/${encodeURIComponent(row.consec)}`).catch(() => ({ data:[] }));
        savedSurveyors = rowsList(loaded);
      }
      if (savedSurveyors.length) {
        savedSurveyors.forEach(item => addSurveyorLine(item.surveyor_nombre || item.nombre || "", item.honorario || ""));
      } else {
        addSurveyorLine(row?.surveyor || "", row?.honorarios || "");
      }
      document.querySelectorAll(".svcSurveyorName").forEach(el => el.onchange = updateSurveyorTotals);
    }
    function closeModal() {
      $("svcModal")?.remove();
    }
    async function saveService(consec=null) {
      const msg = $("svcFormMsg");
      msg.className = "status";
      msg.textContent = "Guardando...";
      try {
        const payload = servicePayload();
        const required = ["tipo","buque_contenedor","cliente","continente","pais","puerto","operacion","surveyor","fecha_inicio","hora_inicio"];
        const missing = required.filter(k => !payload[k]);
        if (missing.length) throw new Error("Faltan campos obligatorios: " + missing.join(", "));
        const approvedPayload = await applyCreditReleaseIfNeeded(payload);
        const data = consec
          ? await sendJSON("PUT", `/servicios/editar/${encodeURIComponent(consec)}`, approvedPayload)
          : await postJSON("/servicios/add", approvedPayload);
        const serviceId = consec || data.consec || data.id;
        if (serviceId) await sendJSON(consec ? "PUT" : "POST", `/servicios-surveyors/${encodeURIComponent(serviceId)}`, { surveyors:readSurveyorLines() }).catch(() => null);
        msg.textContent = data.msg || "Servicio guardado.";
        closeModal();
        await loadServiceMeta();
        await loadServicios(servicePage);
        refreshSummary();
      } catch (err) {
        msg.className = "status error";
        msg.textContent = err.message;
      }
    }
    async function editSelectedService() {
      const row = requireService();
      if (!row) return;
      try {
        const full = await getJSON(`/servicios/${encodeURIComponent(row.consec)}`);
        await openServiceForm(full);
      } catch (err) {
        showServiceMsg(`No se pudo consultar GET del servicio: ${err.message}`, true);
      }
    }
    async function viewSelectedService() {
      const row = requireService();
      if (!row) return;
      try {
        const full = await getJSON(`/servicios/${encodeURIComponent(row.consec)}`);
        document.body.insertAdjacentHTML("beforeend", `
          <div class="modal-backdrop" id="svcModal">
            <div class="modal">
              <div class="modal-head"><h2>Servicio ${esc(full.consec)}</h2><button class="secondary" onclick="closeModal()">Cerrar</button></div>
              <div class="table-wrap"><table><tbody>${visibleServiceColumns().map(c => `<tr><th>${esc(c)}</th><td>${serviceCell(full, c)}</td></tr>`).join("")}</tbody></table></div>
            </div>
          </div>`);
      } catch (err) {
        showServiceMsg(`No se pudo abrir servicio: ${err.message}`, true);
      }
    }
    async function confirmSelectedService() {
      const row = requireService();
      if (!row) return;
      const fecha = prompt("Fecha inicio (YYYY-MM-DD)", row.fecha_inicio || new Date().toISOString().slice(0,10));
      if (!fecha) return;
      const hora = prompt("Hora inicio (HH:MM)", String(row.hora_inicio || "08:00").slice(0,5));
      if (!hora) return;
      await serviceAction("PUT", `/servicios/confirmar/${encodeURIComponent(row.consec)}`, { fecha_inicio:fecha, hora_inicio:hora }, "Consecutivo generado.");
    }
    async function closeSelectedService() {
      const row = requireService();
      if (!row) return;
      const fecha = prompt("Fecha fin (YYYY-MM-DD)", row.fecha_fin || new Date().toISOString().slice(0,10));
      if (!fecha) return;
      const hora = prompt("Hora fin (HH:MM)", String(row.hora_fin || "17:00").slice(0,5));
      if (!hora) return;
      await serviceAction("PUT", `/servicios/cerrar/${encodeURIComponent(row.consec)}`, { fecha_fin:fecha, hora_fin:hora }, "Servicio cerrado.");
      await sendJSON("PUT", `/servicios/generar_informe/${encodeURIComponent(row.consec)}`, {}).catch(() => null);
      await loadServicios(servicePage);
    }
    async function delaySelectedService() {
      const row = requireService();
      if (!row) return;
      const total = prompt("Demoras / tiempo total", row.demoras || "");
      if (total === null) return;
      await serviceAction("PUT", `/servicios/demoras/${encodeURIComponent(row.consec)}`, { total }, "Demoras actualizadas.");
    }
    async function cancelSelectedService() {
      const row = requireService();
      if (!row) return;
      const razon = prompt("Razón de cancelación", row.razon_cancelacion || "");
      if (razon === null) return;
      const comentario = prompt("Comentario de cancelación", row.comentario_cancelacion || "") || "";
      await serviceAction("PUT", `/servicios/cancelar/${encodeURIComponent(row.consec)}`, { estado:"Cancelado", razon_cancelacion:razon, comentario_cancelacion:comentario }, "Servicio cancelado.");
    }
    async function deleteSelectedService() {
      const row = requireService();
      if (!row || !confirm(`¿Eliminar servicio ${row.consec}?`)) return;
      await serviceAction("DELETE", `/servicios/${encodeURIComponent(row.consec)}`, null, "Servicio eliminado.");
    }
    async function serviceAction(method, path, payload, okText) {
      showServiceMsg("Procesando...", false);
      try {
        await sendJSON(method, path, payload);
        showServiceMsg(okText, false);
        await loadServicios(servicePage);
        refreshSummary();
      } catch (err) {
        showServiceMsg(err.message, true);
      }
    }
    function exportServicios(kind) {
      if (!serviceRows.length) {
        alert("No hay datos para exportar.");
        return;
      }
      const stamp = new Date().toISOString().slice(0,10);
      const escapeCsv = value => `"${String(value ?? "").replace(/"/g, '""')}"`;
      const cols = visibleServiceColumns();
      const csv = [cols.join(",")].concat(serviceRows.map(row => cols.map(c => escapeCsv(row[c])).join(","))).join("\\n");
      if (kind === "csv") {
        downloadText(`servicios_${stamp}.csv`, csv, "text/csv;charset=utf-8");
        return;
      }
      if (kind === "xml") {
        const xml = `<?xml version="1.0" encoding="UTF-8"?><servicios>${serviceRows.map(row => `<servicio>${cols.map(c => `<${c}>${esc(row[c] ?? "")}</${c}>`).join("")}</servicio>`).join("")}</servicios>`;
        downloadText(`servicios_${stamp}.xml`, xml, "application/xml;charset=utf-8");
        return;
      }
      const tableHtml = `<table border="1"><thead><tr>${cols.map(c => `<th>${esc(c)}</th>`).join("")}</tr></thead><tbody>${serviceRows.map(row => `<tr>${cols.map(c => `<td>${esc(row[c] ?? "")}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
      if (kind === "excel") {
        downloadText(`servicios_${stamp}.xls`, `<html><head><meta charset="utf-8"></head><body>${tableHtml}</body></html>`, "application/vnd.ms-excel;charset=utf-8");
        return;
      }
      const win = window.open("", "_blank");
      win.document.write(`<html><head><title>Servicios ${stamp}</title><style>body{font-family:Arial,sans-serif}table{border-collapse:collapse;width:100%;font-size:10px}th,td{border:1px solid #bbb;padding:4px;text-align:left}th{background:#eef3f8}</style></head><body><h2>Servicios ${esc(selectedCompany())}</h2>${tableHtml}<script>window.print()<\\/script></body></html>`);
      win.document.close();
    }
    function renderComingSoon(mod) {
      $("content").innerHTML = `<div class="card panel"><div class="panel-head"><h2>${mod.title}</h2></div><div class="status">Seleccione una opción del módulo para continuar.</div></div>`;
    }
    $("loginBtn").onclick = login;
    $("totpBtn").onclick = validateTotp;
    $("bioBtn").onclick = unlockWithPasskey;
    $("backLogin").onclick = showLogin;
    $("setupPasskey").onclick = registerDevicePasskey;
    $("logout").onclick = () => { localStorage.removeItem(SESSION_KEY); session=null; showLogin(); };
    $("refresh").onclick = () => {
      refreshSummary();
      if (currentModule === "master_data") renderMasterData();
      if (currentModule === "servicios") renderServicios();
      if (currentModule === "finanzas") renderFinanzas();
    };
    function changeCompany(value) {
      if (!value) return;
      if ($("company")) $("company").value = value;
      if ($("companyTop")) $("companyTop").value = value;
      bankAccessToken = "";
      bankRows = [];
      if (session) {
        session.company = value;
        localStorage.setItem(SESSION_KEY, JSON.stringify(session));
        const saved = JSON.parse(localStorage.getItem(PASSKEY_KEY) || "null");
        if (saved?.session) {
          saved.session.company = value;
          saved.company = value;
          localStorage.setItem(PASSKEY_KEY, JSON.stringify(saved));
        }
        localStorage.setItem(SAVED_LOGIN_KEY, JSON.stringify({ usuario:session.usuario, company:value }));
      }
      setBrand();
      if (currentModule === "dashboard") refreshSummary();
      else resetKpisForManualLoad();
      if (currentModule === "master_data") renderMasterData();
      if (currentModule === "servicios") renderServicios();
      if (currentModule === "finanzas") renderFinanzas();
    }
    $("company").onchange = () => changeCompany($("company").value);
    $("companyTop").onchange = () => changeCompany($("companyTop").value);
    $("year").onchange = () => {
      if (currentModule === "dashboard") refreshSummary();
      else resetKpisForManualLoad();
      if (currentModule === "servicios") renderServicios();
      if (currentModule === "finanzas") renderFinanzas();
    };
    bootSelectors();
    loadCatalog().then(showLogin).catch(showLogin);
  </script>
</body>
</html>"""
    html = html.replace("{year}", str(year)).replace("{asset_version}", _ASSET_VERSION)
    return HTMLResponse(
        html,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
        },
    )


@router.get("/som/logo/{brand}")
def som_web_logo(brand: str) -> FileResponse:
    filenames = ["mci_logo.png"] if brand.lower() in {"mci", "mci-cr"} else ["msl_logo.png", "header.png"]
    path = None
    for filename in filenames:
        for folder in (_ASSETS, _REPO_ASSETS):
            candidate = folder / filename
            if candidate.exists():
                path = candidate
                break
        if path:
            break
    if not path:
        raise HTTPException(status_code=404, detail="Logo no disponible")
    return FileResponse(path)
