from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

from routers.user_admin import MODULES, MODULE_ACTIONS_BY_MODULE


router = APIRouter(tags=["SOM Web"])

_ROOT = Path(__file__).resolve().parents[1]
_ASSETS = _ROOT / "assets"


DESKTOP_AUDIT = [
    {
        "code": "dashboard",
        "title": "Inicio",
        "subtitle": "Indicadores desde agosto en adelante, estado operativo y accesos rápidos.",
        "views": ["Servicios", "Finanzas", "Comercial", "Informes"],
    },
    {
        "code": "master_data",
        "title": "Master Data",
        "subtitle": "Clientes, proveedores, empleados, surveyors, servicios, datos fiscales y datos bancarios protegidos.",
        "views": ["Clientes", "Proveedores", "Empleados", "Surveyors", "Servicios", "Tarjeta fiscal", "Datos bancarios"],
    },
    {
        "code": "servicios",
        "title": "Servicios",
        "subtitle": "Crear, editar, asignar surveyors, finalizar, cancelar, demoras, facturación e informes.",
        "views": ["Lista de servicios", "Detalle", "Editar", "Surveyors", "Demoras", "Generar informe"],
    },
    {
        "code": "finanzas",
        "title": "Finanzas",
        "subtitle": "Order to Cash, Invoice to Pay, Accounting, bancos, tarjetas, fiscal y reportes.",
        "views": [
            "Invoicing & Billing",
            "Collections",
            "Credit",
            "Disputes",
            "Bank Reconciliation",
            "Invoice To Pay",
            "Obligaciones quincenales",
            "Accounting",
            "Centro fiscal",
            "Tarjetas corporativas",
        ],
    },
    {
        "code": "hhrre",
        "title": "HHRR",
        "subtitle": "Registro de horas, solicitudes, vacaciones, payroll, colillas, red médica y calculadora salarial.",
        "views": ["Horas", "Solicitudes", "Aprobaciones", "Payroll", "Colillas", "Empleados", "Red médica", "Calculadora salarial"],
    },
    {
        "code": "comercial",
        "title": "Comercial",
        "subtitle": "Cotizaciones, precios, analítica, cobertura de puertos y exportables Word/PDF.",
        "views": ["Cotizaciones", "Precios", "Clientes", "Puertos", "Servicios no ofrecidos", "Analítica"],
    },
    {
        "code": "informes",
        "title": "Informes",
        "subtitle": "Draft Survey, bunker, condición, crane, grain, truck, certificados y aprobaciones.",
        "views": ["Draft Survey", "Bunker", "Cargo condition", "Crane", "Grain", "Truck", "Certificates", "Status"],
    },
    {
        "code": "portia",
        "title": "PORTIA",
        "subtitle": "Asistente operativo, contable y documental conectado al contexto SOM.",
        "views": ["Q&A", "Finanzas", "Informes", "Operaciones"],
    },
    {
        "code": "qa_som",
        "title": "Q&A SOM",
        "subtitle": "Base de conocimiento por módulo y preguntas frecuentes del ERP.",
        "views": ["Master Data", "Servicios", "Finanzas", "Comercial", "Informes", "HHRR"],
    },
    {
        "code": "admin_users",
        "title": "Admin",
        "subtitle": "Usuarios, roles, permisos por módulo, auditoría y control de acceso.",
        "views": ["Crear usuario", "Permisos", "Roles", "Auditoría"],
    },
]


@router.get("/som/catalog")
def som_web_catalog():
    module_labels = {item["code"]: item["label"] for item in MODULES}
    return {
        "modules": [
            {
                **item,
                "label": module_labels.get(item["code"], item["title"]),
                "actions": MODULE_ACTIONS_BY_MODULE.get(item["code"], []),
            }
            for item in DESKTOP_AUDIT
        ],
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }


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
    :root {{
      color-scheme: light;
      --ink:#122033; --muted:#66758a; --line:#d7e0ea; --soft:#f4f7fb;
      --panel:#fff; --nav:#071f37; --blue:#005da8; --cyan:#029fcf;
      --green:#087a52; --amber:#ad6b00; --red:#b42318;
      --shadow:0 18px 48px rgba(15,31,53,.12);
    }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font-family:Inter,Segoe UI,Roboto,Arial,sans-serif; color:var(--ink); background:#eef3f8; }}
    button, input, select {{ font:inherit; }}
    button {{ border:0; background:var(--blue); color:white; border-radius:7px; height:38px; padding:0 13px; cursor:pointer; }}
    button.secondary {{ background:white; color:var(--ink); border:1px solid var(--line); }}
    button.ghost {{ background:transparent; color:#dce8f4; border:1px solid rgba(255,255,255,.18); }}
    input, select {{ height:38px; border:1px solid var(--line); border-radius:7px; padding:0 11px; background:white; color:var(--ink); }}
    .login {{ min-height:100vh; display:grid; grid-template-columns:minmax(380px,520px) 1fr; background:white; }}
    .login-card {{ padding:54px 64px; display:flex; flex-direction:column; justify-content:center; gap:16px; }}
    .login-card h1 {{ margin:0; font-size:30px; color:#003a75; }}
    .login-card p {{ margin:0 0 8px; color:var(--muted); line-height:1.45; }}
    .form {{ display:grid; gap:12px; max-width:390px; }}
    .hero {{ background:linear-gradient(135deg,#071f37,#0a4f82); color:white; padding:54px; display:flex; flex-direction:column; justify-content:space-between; }}
    .hero img {{ width:130px; background:white; border-radius:8px; padding:8px; }}
    .hero h2 {{ font-size:42px; max-width:680px; margin:0; line-height:1.05; }}
    .qr {{ max-width:220px; border:1px solid var(--line); border-radius:8px; padding:8px; background:white; }}
    .app {{ min-height:100vh; display:grid; grid-template-columns:292px 1fr; }}
    aside {{ background:var(--nav); color:white; padding:20px 16px; display:flex; flex-direction:column; gap:16px; }}
    .brand {{ display:flex; gap:12px; align-items:center; padding:6px; }}
    .brand img {{ width:50px; height:50px; object-fit:contain; background:white; border-radius:8px; padding:5px; }}
    .brand strong {{ display:block; font-size:18px; }}
    .brand span {{ color:#b9c7d6; font-size:12px; }}
    .nav {{ display:grid; gap:7px; overflow:auto; }}
    .nav button {{ text-align:left; justify-content:flex-start; background:transparent; color:#dce8f4; border:1px solid rgba(255,255,255,.09); }}
    .nav button.active, .nav button:hover {{ background:rgba(255,255,255,.1); }}
    .side-foot {{ margin-top:auto; color:#cbd8e6; font-size:12px; display:grid; gap:8px; }}
    main {{ padding:20px; min-width:0; }}
    header {{ display:flex; justify-content:space-between; gap:16px; align-items:flex-start; margin-bottom:14px; }}
    h1 {{ margin:0; font-size:25px; letter-spacing:0; }}
    h2 {{ margin:0; font-size:17px; }}
    .muted {{ color:var(--muted); }}
    .toolbar {{ display:flex; gap:8px; align-items:center; flex-wrap:wrap; justify-content:flex-end; }}
    .grid {{ display:grid; gap:12px; }}
    .kpis {{ grid-template-columns:repeat(4,minmax(0,1fr)); }}
    .card {{ background:var(--panel); border:1px solid var(--line); border-radius:8px; box-shadow:var(--shadow); }}
    .kpi {{ padding:14px; min-height:96px; }}
    .kpi span {{ display:block; color:var(--muted); font-size:12px; text-transform:uppercase; }}
    .kpi strong {{ display:block; font-size:24px; margin-top:10px; }}
    .layout {{ grid-template-columns:1.25fr .75fr; align-items:start; margin-top:12px; }}
    .panel {{ padding:14px; }}
    .panel-head {{ display:flex; justify-content:space-between; gap:12px; align-items:center; margin-bottom:12px; }}
    .modules {{ grid-template-columns:repeat(2,minmax(0,1fr)); }}
    .module-card {{ padding:14px; cursor:pointer; border-top:3px solid var(--blue); }}
    .module-card:hover {{ outline:2px solid rgba(0,93,168,.2); }}
    .chips {{ display:flex; flex-wrap:wrap; gap:6px; margin-top:10px; }}
    .chip {{ background:#edf4fb; color:#17466e; border:1px solid #cbdff1; border-radius:999px; padding:5px 9px; font-size:12px; }}
    .table-wrap {{ overflow:auto; border:1px solid var(--line); border-radius:8px; max-height:440px; }}
    table {{ border-collapse:collapse; width:100%; min-width:850px; font-size:13px; }}
    th,td {{ border-bottom:1px solid #e6edf4; padding:8px 10px; text-align:left; white-space:nowrap; }}
    th {{ background:#f0f4f8; position:sticky; top:0; z-index:1; }}
    .bar-row {{ display:grid; grid-template-columns:150px 1fr auto; gap:9px; align-items:center; font-size:13px; margin-bottom:9px; }}
    .track {{ height:13px; background:#e7eef6; border-radius:999px; overflow:hidden; }}
    .fill {{ height:100%; background:linear-gradient(90deg,var(--blue),var(--cyan)); min-width:2px; }}
    .status {{ padding:10px 12px; background:var(--soft); border-radius:8px; margin-top:10px; color:var(--muted); }}
    .error {{ color:var(--red); }}
    .hidden {{ display:none !important; }}
    @media(max-width:980px) {{
      .login, .app, .layout, .kpis, .modules {{ grid-template-columns:1fr; }}
      aside {{ min-height:auto; }}
      header {{ flex-direction:column; }}
      .hero {{ display:none; }}
    }}
  </style>
</head>
<body>
  <section id="loginView" class="login">
    <div class="login-card">
      <h1>ERP-SOM Web</h1>
      <p>Ingresa con el mismo usuario, contraseña y Microsoft Authenticator que usas en SOM escritorio.</p>
      <div id="loginForm" class="form">
        <input id="user" autocomplete="username" placeholder="Usuario" />
        <input id="pass" autocomplete="current-password" placeholder="Contraseña" type="password" />
        <select id="loginCompany"></select>
        <button id="loginBtn">Ingresar</button>
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
    <div class="hero">
      <img src="/som/logo/msl" alt="SOM" />
      <h2>SOM completo en web, conectado a Railway y alineado con escritorio.</h2>
      <p>Servicios, Finanzas, Accounting, ITP, HHRR, Comercial, Informes, PORTIA, Q&A y Admin.</p>
    </div>
  </section>

  <section id="appView" class="app hidden">
    <aside>
      <div class="brand">
        <img id="brandLogo" src="/som/logo/msl" alt="Logo" />
        <div><strong>SOM Web</strong><span id="sessionText">Sesión activa</span></div>
      </div>
      <div class="nav" id="moduleNav"></div>
      <div class="side-foot">
        <select id="company"></select>
        <button id="logout" class="ghost">Cerrar sesión</button>
      </div>
    </aside>
    <main>
      <header>
        <div>
          <h1 id="pageTitle">Inicio</h1>
          <div id="pageSubtitle" class="muted">Dashboard operativo</div>
        </div>
        <div class="toolbar">
          <select id="year"></select>
          <button id="refresh">Actualizar</button>
        </div>
      </header>

      <section class="grid kpis">
        <div class="card kpi"><span>Servicios</span><strong id="kpiServices">-</strong><small>Año seleccionado</small></div>
        <div class="card kpi"><span>Facturación</span><strong id="kpiRevenue">-</strong><small>Revenue</small></div>
        <div class="card kpi"><span>CxC</span><strong id="kpiAR">-</strong><small>Saldo pendiente</small></div>
        <div class="card kpi"><span>Informes</span><strong id="kpiReports">-</strong><small>Emitidos/vinculados</small></div>
      </section>

      <section class="grid layout">
        <div class="card panel">
          <div class="panel-head">
            <h2 id="primaryTitle">Módulos auditados</h2>
            <span id="updatedAt" class="muted"></span>
          </div>
          <div id="primary"></div>
        </div>
        <div class="card panel">
          <div class="panel-head">
            <h2>Acciones / Permisos</h2>
            <span id="roleBadge" class="muted"></span>
          </div>
          <div id="actions"></div>
        </div>
      </section>

      <section class="card panel" style="margin-top:12px;">
        <div class="panel-head">
          <h2 id="tableTitle">Datos conectados</h2>
          <span id="tableStatus" class="muted"></span>
        </div>
        <div id="dataTable"></div>
      </section>
    </main>
  </section>

  <script>
    const DEFAULT_COMPANIES = [
      {{ company_code:"MSL-CR", company_name:"MSL MARINE SURVEYORS AND LOGISTICS GROUP SRL" }},
      {{ company_code:"MCI-CR", company_name:"MSL MARINE CLAIMS RISK & INTELLIGENCE" }}
    ];
    const endpoints = {{
      dashboard:"/dashboard/servicios",
      master_data:"/clientes",
      servicios:"/servicios/",
      finanzas:"/collections/search",
      hhrre:"/hr/events/",
      comercial:"/comercial/cotizaciones",
      informes:"/status-informes",
      portia:"/portia/context",
      qa_som:"/portia/qa",
      admin_users:"/admin/users/users"
    }};
    const moneyFmt = new Intl.NumberFormat("en-US", {{ notation:"compact", maximumFractionDigits:1 }});
    const intFmt = new Intl.NumberFormat("en-US", {{ maximumFractionDigits:0 }});
    let catalog = [];
    let session = JSON.parse(localStorage.getItem("somWebSession") || "null");
    let pendingUser = null;
    let pendingAction = null;
    let currentModule = "dashboard";

    const $ = id => document.getElementById(id);
    const apiHeaders = () => ({{
      "Content-Type":"application/json",
      "X-Company-Code": $("company")?.value || session?.company || "MSL-CR",
      "X-User": session?.usuario || "",
      "X-User-Role": session?.rol || ""
    }});
    const canView = code => {{
      if (!session) return false;
      const role = String(session.rol || "").toLowerCase();
      if (["admin","master"].includes(role)) return true;
      const perms = session.permissions || {{}};
      return (session.modules || []).includes(code) || (perms[code] || []).length > 0;
    }};
    const money = value => "$" + moneyFmt.format(Number(value || 0));

    async function getJSON(path) {{
      const resp = await fetch(path, {{ headers: apiHeaders() }});
      if (!resp.ok) throw new Error(`${{path}} -> ${{resp.status}}`);
      return resp.json();
    }}
    async function postJSON(path, payload) {{
      const resp = await fetch(path, {{ method:"POST", headers:{{"Content-Type":"application/json"}}, body:JSON.stringify(payload) }});
      if (!resp.ok) {{
        let msg = resp.statusText;
        try {{ msg = (await resp.json()).detail || msg; }} catch {{}}
        throw new Error(msg);
      }}
      return resp.json();
    }}

    function fillCompanySelect(select) {{
      select.innerHTML = "";
      DEFAULT_COMPANIES.forEach(c => {{
        const option = document.createElement("option");
        option.value = c.company_code;
        option.textContent = `${{c.company_code}} | ${{c.company_name}}`;
        select.appendChild(option);
      }});
    }}
    function bootSelectors() {{
      fillCompanySelect($("loginCompany"));
      fillCompanySelect($("company"));
      for (let y = {year}; y >= {year} - 4; y--) {{
        const option = document.createElement("option");
        option.value = String(y);
        option.textContent = String(y);
        $("year").appendChild(option);
      }}
    }}

    async function loadCatalog() {{
      const data = await getJSON("/som/catalog").catch(() => ({{ modules: [] }}));
      catalog = data.modules || [];
    }}

    function showLogin() {{
      $("loginView").classList.remove("hidden");
      $("appView").classList.add("hidden");
      $("loginForm").classList.remove("hidden");
      $("totpForm").classList.add("hidden");
    }}
    function showApp() {{
      $("loginView").classList.add("hidden");
      $("appView").classList.remove("hidden");
      $("sessionText").textContent = `${{session.usuario}} · ${{session.rol}}`;
      $("roleBadge").textContent = session.rol || "";
      $("company").value = session.company || "MSL-CR";
      renderNav();
      selectModule(currentModule);
    }}

    async function login() {{
      $("loginMsg").textContent = "Validando...";
      try {{
        const data = await postJSON("/auth/mobile/login", {{ usuario:$("user").value, password:$("pass").value }});
        pendingUser = data.usuario || $("user").value;
        pendingAction = data.action;
        if (data.action === "ENROLL_TOTP" && data.qr_base64) {{
          $("qr").src = "data:image/png;base64," + data.qr_base64;
          $("qr").classList.remove("hidden");
        }} else {{
          $("qr").classList.add("hidden");
        }}
        $("loginForm").classList.add("hidden");
        $("totpForm").classList.remove("hidden");
        $("totpMsg").textContent = data.action === "ENROLL_TOTP" ? "Escanea el QR y valida el primer código." : "Ingresa tu código Authenticator.";
      }} catch (err) {{
        $("loginMsg").innerHTML = `<span class="error">${{err.message}}</span>`;
      }}
    }}
    async function validateTotp() {{
      $("totpMsg").textContent = "Validando código...";
      try {{
        const path = pendingAction === "ENROLL_TOTP" ? "/auth/mobile/totp/confirm" : "/auth/mobile/totp/verify";
        const data = await postJSON(path, {{ usuario:pendingUser, codigo:$("code").value }});
        session = {{ ...data, company:$("loginCompany").value }};
        localStorage.setItem("somWebSession", JSON.stringify(session));
        await loadCatalog();
        showApp();
      }} catch (err) {{
        $("totpMsg").innerHTML = `<span class="error">${{err.message}}</span>`;
      }}
    }}

    function renderNav() {{
      $("moduleNav").innerHTML = "";
      catalog.filter(m => canView(m.code)).forEach(mod => {{
        const btn = document.createElement("button");
        btn.textContent = mod.title;
        btn.className = mod.code === currentModule ? "active" : "";
        btn.onclick = () => selectModule(mod.code);
        $("moduleNav").appendChild(btn);
      }});
    }}

    function selectModule(code) {{
      currentModule = code;
      const mod = catalog.find(m => m.code === code) || catalog[0];
      if (!mod) return;
      $("brandLogo").src = ($("company").value || "").startsWith("MCI") ? "/som/logo/mci" : "/som/logo/msl";
      $("pageTitle").textContent = mod.title;
      $("pageSubtitle").textContent = mod.subtitle;
      $("primaryTitle").textContent = mod.title + " web";
      renderNav();
      renderModule(mod);
      refresh();
    }}

    function renderModule(mod) {{
      $("primary").innerHTML = `<div class="grid modules">${
        (mod.views || []).map(v => `<div class="card module-card"><strong>${{v}}</strong><div class="muted">Disponible desde SOM web conectado al backend Railway.</div></div>`).join("")
      }</div>`;
      const allowed = new Set((session.permissions || {{}})[mod.code] || []);
      const role = String(session.rol || "").toLowerCase();
      $("actions").innerHTML = `<div class="chips">${
        (mod.actions || []).map(a => {{
          const ok = ["admin","master"].includes(role) || allowed.has(a.code) || allowed.has("admin");
          return `<span class="chip" title="${{a.code}}">${{ok ? "✓" : "•"}} ${{a.label}}</span>`;
        }}).join("")
      }</div><div class="status">Auditoría escritorio: ${(mod.views || []).length} vistas y ${(mod.actions || []).length} acciones mapeadas.</div>`;
    }}

    function rowsFromPayload(payload) {{
      if (Array.isArray(payload)) return payload;
      if (Array.isArray(payload.data)) return payload.data;
      if (Array.isArray(payload.items)) return payload.items;
      if (Array.isArray(payload.rows)) return payload.rows;
      if (Array.isArray(payload.results)) return payload.results;
      return [];
    }}
    function renderTable(rows) {{
      if (!rows.length) {{
        $("dataTable").innerHTML = '<div class="status">Sin datos para esta consulta o el endpoint requiere filtros adicionales.</div>';
        return;
      }}
      const keys = Object.keys(rows[0]).filter(k => !String(k).toLowerCase().includes("hash")).slice(0, 10);
      $("dataTable").innerHTML = `<div class="table-wrap"><table><thead><tr>${keys.map(k=>`<th>${k}</th>`).join("")}</tr></thead><tbody>${
        rows.slice(0,80).map(row => `<tr>${keys.map(k=>`<td>${row[k] ?? ""}</td>`).join("")}</tr>`).join("")
      }</tbody></table></div>`;
    }}
    function drawBars(rows) {{
      const cleaned = (rows || []).filter(r => Number(r.revenue || r.total || r.total_facturado || 0) > 0).slice(0, 8);
      if (!cleaned.length) return false;
      const max = Math.max(...cleaned.map(r => Number(r.revenue || r.total || r.total_facturado || 0)));
      $("primary").innerHTML = cleaned.map(r => {{
        const label = r.mes || r.month || r.periodo || "Periodo";
        const value = Number(r.revenue || r.total || r.total_facturado || 0);
        return `<div class="bar-row"><div>${{label}}</div><div class="track"><div class="fill" style="width:${{Math.max(4,value/max*100)}}%"></div></div><strong>${{money(value)}}</strong></div>`;
      }}).join("");
      return true;
    }}

    async function refresh() {{
      $("updatedAt").textContent = "Actualizando...";
      const company = $("company").value;
      if (session) {{
        session.company = company;
        localStorage.setItem("somWebSession", JSON.stringify(session));
      }}
      $("brandLogo").src = company.startsWith("MCI") ? "/som/logo/mci" : "/som/logo/msl";
      try {{
        const year = $("year").value;
        const [servicios, finanzas, informes] = await Promise.allSettled([
          getJSON(`/dashboard/servicios?anio=${{year}}`),
          getJSON(`/dashboard-finanzas/resumen?anio=${{year}}`),
          getJSON(`/dashboard-informes/resumen?anio=${{year}}`)
        ]);
        const s = servicios.value || {{}}, f = finanzas.value || {{}}, i = informes.value || {{}};
        $("kpiServices").textContent = intFmt.format(s?.kpis?.total_servicios || 0);
        $("kpiRevenue").textContent = money(f?.kpis?.revenue_total || s?.kpis?.total_facturado || 0);
        $("kpiAR").textContent = money(f?.kpis?.ar_total || 0);
        $("kpiReports").textContent = intFmt.format(i?.kpis?.total_informes || 0);
        if (currentModule === "dashboard") drawBars(f?.revenue_mensual || s?.revenue_mensual || []);
      }} catch (err) {{}}
      await loadModuleData();
      $("updatedAt").textContent = new Date().toLocaleString();
    }}

    async function loadModuleData() {{
      const endpoint = endpoints[currentModule];
      $("tableTitle").textContent = "Datos conectados · " + currentModule;
      $("tableStatus").textContent = endpoint || "";
      if (!endpoint) return renderTable([]);
      try {{
        let path = endpoint;
        const sep = path.includes("?") ? "&" : "?";
        if (currentModule === "dashboard") path = `/dashboard/servicios?anio=${{$("year").value}}`;
        else if (currentModule === "finanzas") path = `/collections/search?estado=ALL`;
        else if (currentModule === "servicios") path = `/servicios/`;
        else if (currentModule === "hhrre") path = `/hr/events/`;
        else if (currentModule === "master_data") path = `/clientes`;
        const payload = await getJSON(path);
        renderTable(rowsFromPayload(payload));
      }} catch (err) {{
        $("dataTable").innerHTML = `<div class="status error">No se pudo cargar: ${{err.message}}</div>`;
      }}
    }}

    $("loginBtn").onclick = login;
    $("totpBtn").onclick = validateTotp;
    $("backLogin").onclick = showLogin;
    $("logout").onclick = () => {{ localStorage.removeItem("somWebSession"); session=null; showLogin(); }};
    $("refresh").onclick = refresh;
    $("company").onchange = () => selectModule(currentModule);
    $("year").onchange = refresh;
    bootSelectors();
    loadCatalog().then(() => session ? showApp() : showLogin()).catch(showLogin);
  </script>
</body>
</html>"""
    html = html.replace("{{", "{").replace("}}", "}").replace("{year}", str(year))
    return HTMLResponse(html)


@router.get("/som/logo/{brand}")
def som_web_logo(brand: str) -> FileResponse:
    filename = "mci_logo.png" if brand.lower() in {"mci", "mci-cr"} else "header.png"
    path = _ASSETS / filename
    if not path.exists():
        fallback = _ASSETS / "mci_logo.png"
        if not fallback.exists():
            raise HTTPException(status_code=404, detail="Logo no disponible")
        path = fallback
    return FileResponse(path)
