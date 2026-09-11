from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Header, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse
from psycopg2.extras import RealDictCursor

import database
from routers.user_admin import MODULES
from services.tenanting import company_code


router = APIRouter(tags=["SOM Web"])

_ROOT = Path(__file__).resolve().parents[1]
_ASSETS = _ROOT / "assets"
_REPO_ASSETS = _ROOT.parent / "assets"
_ASSET_VERSION = "20260911-msl-logo-full"

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
    {"key": "servicios_md", "label": "Servicios", "endpoint": "/servicios_md/?page=1&page_size=100", "primary": ["codigo", "servicio", "descripcion", "activo"]},
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
    .login-card { width:100%; max-width:520px; padding:48px 56px; display:flex; flex-direction:column; justify-content:center; gap:16px; overflow:hidden; }
    .login-card h1 { margin:0; font-size:30px; color:#003a75; }
    .login-card p { margin:0 0 8px; color:var(--muted); line-height:1.45; }
    .form { display:grid; gap:12px; width:min(100%,420px); min-width:0; }
    .remember { display:flex; gap:8px; align-items:center; color:#334155; font-size:13px; }
    .remember input { width:16px; height:16px; }
    .hero-logo { background:#073659; display:flex; align-items:stretch; justify-content:stretch; padding:0; overflow:hidden; }
    .hero-logo img { width:100%; height:100%; min-height:100vh; object-fit:cover; object-position:center; background:white; border-radius:0; padding:0; box-shadow:none; }
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
    .view-grid { grid-template-columns:repeat(4,minmax(0,1fr)); }
    .view-card { padding:15px; cursor:pointer; min-height:86px; border-top:3px solid var(--blue); }
    .view-card:hover { outline:2px solid rgba(0,93,168,.18); }
    .workspace { margin-top:12px; }
    .table-wrap { overflow:auto; border:1px solid var(--line); border-radius:8px; max-height:520px; }
    table { border-collapse:collapse; width:100%; min-width:850px; font-size:13px; }
    th,td { border-bottom:1px solid #e6edf4; padding:8px 10px; text-align:left; white-space:nowrap; }
    th { background:#f0f4f8; position:sticky; top:0; z-index:1; }
    .bar-row { display:grid; grid-template-columns:130px 1fr auto; gap:9px; align-items:center; font-size:13px; margin-bottom:9px; }
    .track { height:13px; background:#e7eef6; border-radius:999px; overflow:hidden; }
    .fill { height:100%; background:linear-gradient(90deg,var(--blue),#029fcf); min-width:2px; }
    .status { padding:10px 12px; background:var(--soft); border-radius:8px; color:var(--muted); }
    .error { color:var(--red); }
    .hidden { display:none !important; }
    @media(max-width:980px) {
      .login,.app,.kpis,.home-grid,.view-grid { grid-template-columns:1fr; }
      .login-card { max-width:none; padding:34px 24px; }
      .hero-logo { min-height:260px; }
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
          <select id="year"></select>
          <button id="refresh">Actualizar</button>
        </div>
      </header>
      <section class="grid kpis">
        <div class="card kpi"><span>Servicios</span><strong id="kpiServices">-</strong><small>Desde agosto</small></div>
        <div class="card kpi"><span>Facturación</span><strong id="kpiRevenue">-</strong><small>Desde agosto</small></div>
        <div class="card kpi"><span>CxC</span><strong id="kpiAR">-</strong><small>Saldo pendiente</small></div>
        <div class="card kpi"><span>Informes</span><strong id="kpiReports">-</strong><small>Desde agosto</small></div>
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
    let session = JSON.parse(localStorage.getItem("somWebSession") || "null");
    let pendingUser = null;
    let pendingAction = null;
    let catalog = { modules:[], master_data_actions:[], master_data_views:[] };
    let currentModule = "dashboard";
    let selectedMasterView = null;

    const money = value => "$" + moneyFmt.format(Number(value || 0));
    const headers = () => ({
      "Content-Type":"application/json",
      "X-Company-Code": $("company")?.value || session?.company || "MSL-CR",
      "X-User": session?.usuario || "",
      "X-User-Role": session?.rol || ""
    });

    async function getJSON(path) {
      const resp = await fetch(path, { headers:headers() });
      if (!resp.ok) throw new Error(`${path} -> ${resp.status}`);
      return resp.json();
    }
    async function postJSON(path, payload) {
      const resp = await fetch(path, { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(payload) });
      if (!resp.ok) {
        let msg = resp.statusText;
        try { msg = (await resp.json()).detail || msg; } catch {}
        throw new Error(msg);
      }
      return resp.json();
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
      for (let y = {year}; y >= {year} - 4; y--) {
        const option = document.createElement("option");
        option.value = String(y);
        option.textContent = String(y);
        $("year").appendChild(option);
      }
      $("bioBtn").disabled = !window.PublicKeyCredential || !localStorage.getItem("somWebPasskey");
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
        localStorage.setItem("somWebSession", JSON.stringify(session));
        if ($("rememberDevice").checked) await registerDevicePasskey();
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
      return btoa(String.fromCharCode(...new Uint8Array(bytes))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
    }
    async function registerDevicePasskey() {
      if (!window.PublicKeyCredential) return;
      const challenge = crypto.getRandomValues(new Uint8Array(32));
      const userId = crypto.getRandomValues(new Uint8Array(16));
      try {
        const cred = await navigator.credentials.create({
          publicKey: {
            challenge,
            rp: { name:"ERP-SOM Web" },
            user: { id:userId, name:session.usuario, displayName:session.usuario },
            pubKeyCredParams:[{ type:"public-key", alg:-7 }, { type:"public-key", alg:-257 }],
            authenticatorSelection:{ userVerification:"preferred" },
            timeout:60000
          }
        });
        localStorage.setItem("somWebPasskey", JSON.stringify({ id:base64url(cred.rawId), session }));
      } catch {}
    }
    async function unlockWithPasskey() {
      const saved = JSON.parse(localStorage.getItem("somWebPasskey") || "null");
      if (!saved || !window.PublicKeyCredential) return;
      $("loginMsg").textContent = "Validando dispositivo...";
      try {
        await navigator.credentials.get({
          publicKey: {
            challenge:crypto.getRandomValues(new Uint8Array(32)),
            allowCredentials:[{ type:"public-key", id:bytesFromBase64url(saved.id) }],
            userVerification:"preferred",
            timeout:60000
          }
        });
        session = saved.session;
        localStorage.setItem("somWebSession", JSON.stringify(session));
        await loadCatalog();
        showApp();
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
      $("brandLogo").src = ($("company").value || "").startsWith("MCI") ? "/som/logo/mci?v={asset_version}" : "/som/logo/msl?v={asset_version}";
    }
    function selectModule(code) {
      currentModule = code;
      selectedMasterView = null;
      setBrand();
      const mod = catalog.modules.find(m => m.code === code) || catalog.modules[0];
      $("pageTitle").textContent = mod?.title || "SOM";
      $("pageSubtitle").textContent = mod?.subtitle || "";
      renderNav();
      refreshSummary();
      if (code === "dashboard") renderHome();
      else if (code === "master_data") renderMasterData();
      else renderComingSoon(mod);
    }
    async function refreshSummary() {
      try {
        const data = await getJSON(`/som/summary?anio=${$("year").value}`);
        $("kpiServices").textContent = intFmt.format(data.kpis.services || 0);
        $("kpiRevenue").textContent = money(data.kpis.invoiced || 0);
        $("kpiAR").textContent = money(data.kpis.ar || 0);
        $("kpiReports").textContent = intFmt.format(data.kpis.reports || 0);
        if (currentModule === "dashboard") renderHomeChart(data.monthly || []);
      } catch {
        $("kpiServices").textContent = "0";
        $("kpiRevenue").textContent = "$0";
        $("kpiAR").textContent = "$0";
        $("kpiReports").textContent = "0";
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
    function renderMasterData() {
      $("content").innerHTML = `
        <div class="card panel">
          <div class="panel-head"><h2>Acciones</h2><span class="muted">Igual que escritorio</span></div>
          <div class="md-actions">${catalog.master_data_actions.map(a => `<button class="${buttonClass(a)}" onclick="masterAction('${a.key}')">${a.label}</button>`).join("")}</div>
          <div class="filters">
            <select id="mdTipo"><option>Todos</option><option>Empleado</option><option>Surveyor</option><option>Cliente</option><option>Proveedor</option><option>Servicio</option></select>
            <select id="mdContinente"><option>Seleccione continente</option></select>
            <select id="mdPais"><option>Seleccione país</option></select>
            <select id="mdPuerto"><option>Seleccione puerto</option></select>
            <button onclick="applyMasterFilter()">Buscar</button>
          </div>
          <div class="grid view-grid">${catalog.master_data_views.map(v => `<div class="card view-card" onclick="openMasterView('${v.key}')"><h2>${v.label}</h2><p class="muted">Abrir pantalla</p></div>`).join("")}</div>
        </div>
        <div id="masterWorkspace" class="card panel workspace hidden"></div>`;
      loadMasterFilters();
    }
    function buttonClass(action) {
      if (action.key === "export_form") return "green";
      if (action.key === "import_form") return "brown";
      if (action.key === "company_fiscal") return "gray";
      if (action.key === "bank_accounts") return "dark";
      return "";
    }
    function masterAction(key) {
      if (["clientes","surveyores","empleados","proveedores","servicios_md"].includes(key)) {
        const view = catalog.master_data_views.find(v => v.key === key);
        alert(`Pantalla de alta ${view?.label || key}: siguiente etapa web con POST/PUT completo. Por ahora usa escritorio para crear.`);
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
      if (key === "company_fiscal") openMasterView("company_fiscal");
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
          const pais = $("mdPais").value;
          const puertos = pais.startsWith("Seleccione") ? [] : await getJSON(`/cpp/puertos?pais=${encodeURIComponent(pais)}`);
          $("mdPuerto").innerHTML = "<option>Seleccione puerto</option>" + puertos.map(x => `<option>${x}</option>`).join("");
        };
      } catch {}
    }
    function applyMasterFilter() {
      const tipo = $("mdTipo").value;
      const map = { Cliente:"clientes", Proveedor:"proveedores", Empleado:"empleados", Surveyor:"surveyores", Servicio:"servicios_md" };
      if (map[tipo]) openMasterView(map[tipo]);
    }
    async function openMasterView(key) {
      selectedMasterView = catalog.master_data_views.find(v => v.key === key);
      const ws = $("masterWorkspace");
      ws.classList.remove("hidden");
      ws.innerHTML = `<div class="panel-head"><h2>${selectedMasterView.label}</h2><span class="muted">Cargando...</span></div>`;
      if (key === "bank_accounts") {
        ws.innerHTML = `<div class="panel-head"><h2>Datos bancarios</h2><span class="muted">Protegido</span></div><div class="status">Por seguridad, esta pantalla requiere revalidación Authenticator. La versión web completa usará el token protegido del endpoint bancario; usa escritorio mientras cerramos esa pieza.</div>`;
        return;
      }
      try {
        const payload = await getJSON(selectedMasterView.endpoint);
        const rows = rowsFromPayload(payload);
        ws.innerHTML = `<div class="panel-head"><h2>${selectedMasterView.label}</h2><span class="muted">${rows.length} registros</span></div>${renderTable(rows, selectedMasterView.primary)}`;
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
    function renderTable(rows, preferred) {
      if (!rows.length) return '<div class="status">Sin datos para esta pantalla.</div>';
      const keys = (preferred || []).filter(k => Object.prototype.hasOwnProperty.call(rows[0], k));
      const fallback = Object.keys(rows[0]).filter(k => !String(k).toLowerCase().includes("hash")).slice(0, 8);
      const cols = keys.length ? keys : fallback;
      return `<div class="table-wrap"><table><thead><tr>${cols.map(k => `<th>${k}</th>`).join("")}</tr></thead><tbody>${rows.slice(0,100).map(row => `<tr>${cols.map(k => `<td>${row[k] ?? ""}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
    }
    function renderComingSoon(mod) {
      $("content").innerHTML = `<div class="card panel"><div class="panel-head"><h2>${mod.title}</h2><span class="muted">Siguiente etapa</span></div><div class="status">Esta sección queda en navegación web. Primero estamos replicando Master Data de forma quirúrgica; luego seguimos con ${mod.title}.</div></div>`;
    }
    $("loginBtn").onclick = login;
    $("totpBtn").onclick = validateTotp;
    $("bioBtn").onclick = unlockWithPasskey;
    $("backLogin").onclick = showLogin;
    $("logout").onclick = () => { localStorage.removeItem("somWebSession"); session=null; showLogin(); };
    $("refresh").onclick = () => { refreshSummary(); if (currentModule === "master_data") renderMasterData(); };
    $("company").onchange = () => { if (session) { session.company = $("company").value; localStorage.setItem("somWebSession", JSON.stringify(session)); } setBrand(); refreshSummary(); if (currentModule === "master_data") renderMasterData(); };
    $("year").onchange = refreshSummary;
    bootSelectors();
    loadCatalog().then(() => session ? showApp() : showLogin()).catch(showLogin);
  </script>
</body>
</html>"""
    html = html.replace("{year}", str(year)).replace("{asset_version}", _ASSET_VERSION)
    return HTMLResponse(html)


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
