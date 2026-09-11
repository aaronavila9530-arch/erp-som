from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse


router = APIRouter(tags=["SOM Web"])

_ROOT = Path(__file__).resolve().parents[1]
_ASSETS = _ROOT / "assets"


@router.get("/som", response_class=HTMLResponse)
def som_web_home() -> HTMLResponse:
    year = datetime.now().year
    return HTMLResponse(
        f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>SOM Executive Portal</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #102033;
      --muted: #637286;
      --line: #d8e0ea;
      --panel: #ffffff;
      --soft: #f3f6fa;
      --navy: #08345f;
      --blue: #006fb9;
      --cyan: #00a3d7;
      --green: #0f7b53;
      --amber: #b9770e;
      --danger: #ad2f2f;
      --shadow: 0 18px 50px rgba(18, 34, 55, .12);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Inter, Segoe UI, Roboto, Arial, sans-serif;
      color: var(--ink);
      background: linear-gradient(180deg, #f7f9fc 0%, #eef3f8 100%);
    }}
    .shell {{ min-height: 100vh; display: grid; grid-template-columns: 280px 1fr; }}
    aside {{
      background: #071f37;
      color: #fff;
      padding: 24px 20px;
      display: flex;
      flex-direction: column;
      gap: 22px;
    }}
    .brand {{ display: flex; align-items: center; gap: 12px; }}
    .brand img {{ width: 52px; height: 52px; object-fit: contain; background: #fff; border-radius: 8px; padding: 5px; }}
    .brand strong {{ display: block; font-size: 18px; letter-spacing: .02em; }}
    .brand span {{ color: #b9c7d6; font-size: 12px; }}
    nav {{ display: grid; gap: 8px; }}
    nav a {{
      color: #dce8f4;
      text-decoration: none;
      padding: 11px 12px;
      border-radius: 8px;
      border: 1px solid rgba(255,255,255,.08);
    }}
    nav a:hover {{ background: rgba(255,255,255,.08); }}
    .status-pill {{
      margin-top: auto;
      border: 1px solid rgba(255,255,255,.14);
      border-radius: 8px;
      padding: 12px;
      color: #cbd8e6;
      font-size: 13px;
    }}
    main {{ padding: 24px; }}
    header {{
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: flex-start;
      margin-bottom: 18px;
    }}
    h1 {{ margin: 0; font-size: 28px; letter-spacing: 0; }}
    .subtitle {{ margin: 7px 0 0; color: var(--muted); max-width: 780px; line-height: 1.45; }}
    .toolbar {{ display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }}
    select, button {{
      height: 38px;
      border: 1px solid var(--line);
      border-radius: 7px;
      background: #fff;
      padding: 0 11px;
      color: var(--ink);
      font: inherit;
    }}
    button {{
      background: var(--navy);
      color: #fff;
      border-color: var(--navy);
      cursor: pointer;
    }}
    .grid {{ display: grid; gap: 14px; }}
    .kpis {{ grid-template-columns: repeat(4, minmax(0, 1fr)); margin-bottom: 14px; }}
    .card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
    }}
    .kpi {{ padding: 16px; min-height: 112px; }}
    .kpi span {{ display: block; color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .06em; }}
    .kpi strong {{ display: block; font-size: 26px; margin-top: 12px; }}
    .kpi small {{ color: var(--muted); }}
    .layout {{ grid-template-columns: 1.35fr .65fr; align-items: start; }}
    .panel {{ padding: 16px; }}
    .panel-head {{ display: flex; justify-content: space-between; gap: 12px; align-items: center; margin-bottom: 12px; }}
    h2 {{ margin: 0; font-size: 17px; }}
    .hint {{ color: var(--muted); font-size: 13px; }}
    .chart {{ display: grid; gap: 10px; }}
    .bar-row {{ display: grid; grid-template-columns: minmax(110px, 180px) 1fr auto; gap: 10px; align-items: center; font-size: 13px; }}
    .bar-name {{ overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
    .track {{ height: 13px; border-radius: 999px; background: #e8eef5; overflow: hidden; }}
    .fill {{ height: 100%; border-radius: 999px; background: linear-gradient(90deg, var(--blue), var(--cyan)); min-width: 2px; }}
    .modules {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    .module {{ padding: 14px; border-top: 3px solid var(--blue); min-height: 118px; }}
    .module:nth-child(2) {{ border-top-color: var(--green); }}
    .module:nth-child(3) {{ border-top-color: var(--amber); }}
    .module:nth-child(4) {{ border-top-color: var(--cyan); }}
    .module strong {{ display: block; margin-bottom: 8px; }}
    .module p {{ margin: 0; color: var(--muted); line-height: 1.4; font-size: 13px; }}
    .feed {{ display: grid; gap: 8px; }}
    .feed-item {{ padding: 11px; background: var(--soft); border-radius: 7px; display: flex; justify-content: space-between; gap: 10px; }}
    .feed-item span {{ color: var(--muted); font-size: 12px; }}
    .error {{ color: var(--danger); }}
    .ok {{ color: var(--green); }}
    footer {{ margin-top: 18px; color: var(--muted); font-size: 12px; }}
    @media (max-width: 980px) {{
      .shell {{ grid-template-columns: 1fr; }}
      aside {{ position: static; }}
      .kpis, .layout, .modules {{ grid-template-columns: 1fr; }}
      header {{ flex-direction: column; }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <aside>
      <div class="brand">
        <img src="/som/logo/msl" alt="MSL" />
        <div>
          <strong>SOM</strong>
          <span>Survey Operations Management</span>
        </div>
      </div>
      <nav aria-label="Secciones SOM">
        <a href="#resumen">Resumen Ejecutivo</a>
        <a href="#operaciones">Operaciones</a>
        <a href="#finanzas">Finanzas</a>
        <a href="#modulos">Módulos</a>
      </nav>
      <div class="status-pill">
        <div>API Railway</div>
        <strong id="apiStatus">Validando...</strong>
      </div>
    </aside>
    <main>
      <header id="resumen">
        <div>
          <h1>SOM Executive Portal</h1>
          <p class="subtitle">Vista web ligera para monitorear operaciones, facturación, cuentas por cobrar e informes desde el backend productivo de Railway.</p>
        </div>
        <div class="toolbar">
          <select id="year"></select>
          <select id="company">
            <option value="MSL-CR">MSL Marine Surveyors</option>
            <option value="MCI">MSL 2.0 Claims & Risk</option>
          </select>
          <button id="refresh">Actualizar</button>
        </div>
      </header>

      <section class="grid kpis" aria-label="Indicadores principales">
        <div class="card kpi"><span>Servicios</span><strong id="kpiServices">-</strong><small>Año seleccionado</small></div>
        <div class="card kpi"><span>Facturación</span><strong id="kpiRevenue">-</strong><small>USD / moneda base</small></div>
        <div class="card kpi"><span>Cuentas por cobrar</span><strong id="kpiAR">-</strong><small>Saldo pendiente</small></div>
        <div class="card kpi"><span>Informes</span><strong id="kpiReports">-</strong><small>Emitidos o vinculados</small></div>
      </section>

      <section class="grid layout">
        <div class="card panel" id="operaciones">
          <div class="panel-head">
            <div>
              <h2>Revenue Mensual</h2>
              <div class="hint">Arranca desde agosto cuando el dashboard lo permite.</div>
            </div>
            <span id="updatedAt" class="hint"></span>
          </div>
          <div id="revenueChart" class="chart"></div>
        </div>

        <div class="card panel" id="finanzas">
          <div class="panel-head">
            <h2>Alertas Operativas</h2>
            <span class="hint">Live</span>
          </div>
          <div id="feed" class="feed"></div>
        </div>
      </section>

      <section class="card panel" id="modulos" style="margin-top:14px;">
        <div class="panel-head">
          <h2>Módulos SOM</h2>
          <span class="hint">Escritorio, Android y Web conectados al mismo backend</span>
        </div>
        <div class="grid modules">
          <div class="module"><strong>Servicios</strong><p>Registro, edición, facturación, surveyors, puertos, clientes y trazabilidad operativa.</p></div>
          <div class="module"><strong>Finanzas</strong><p>Collections, ITP, Accounting, conciliación bancaria, tarjetas y obligaciones quincenales.</p></div>
          <div class="module"><strong>HHRR</strong><p>Horas, solicitudes, vacaciones, calculadora salarial, red médica y notificaciones.</p></div>
          <div class="module"><strong>Informes</strong><p>Draft, bunker, condition, grain, truck, certificates y exportables Word/PDF/Excel.</p></div>
        </div>
      </section>
      <footer>SOM Web · Railway · Generado desde ERP-SOM API · {year}</footer>
    </main>
  </div>

  <script>
    const currentYear = new Date().getFullYear();
    const yearSelect = document.getElementById("year");
    for (let y = currentYear; y >= currentYear - 4; y--) {{
      const option = document.createElement("option");
      option.value = String(y);
      option.textContent = String(y);
      yearSelect.appendChild(option);
    }}

    const fmtNumber = new Intl.NumberFormat("en-US", {{ maximumFractionDigits: 0 }});
    const fmtMoney = new Intl.NumberFormat("en-US", {{ notation: "compact", maximumFractionDigits: 1 }});

    function setText(id, value) {{
      document.getElementById(id).textContent = value;
    }}

    function money(value) {{
      const n = Number(value || 0);
      return n ? "$" + fmtMoney.format(n) : "$0";
    }}

    async function getJSON(path, company) {{
      const resp = await fetch(path, {{ headers: {{ "X-Company-Code": company }} }});
      if (!resp.ok) throw new Error(path + " -> " + resp.status);
      return resp.json();
    }}

    function drawBars(id, rows, labelKey, valueKey) {{
      const el = document.getElementById(id);
      el.innerHTML = "";
      const cleaned = (rows || []).map(row => ({{
        label: row[labelKey] || row.mes || "Sin dato",
        value: Number(row[valueKey] || row.revenue || row.total || 0)
      }})).filter(row => row.value > 0).slice(0, 8);
      if (!cleaned.length) {{
        el.innerHTML = '<div class="hint">Sin datos para graficar en este periodo.</div>';
        return;
      }}
      const max = Math.max(...cleaned.map(row => row.value));
      cleaned.forEach(row => {{
        const wrap = document.createElement("div");
        wrap.className = "bar-row";
        wrap.innerHTML = `<div class="bar-name" title="${{row.label}}">${{row.label}}</div>
          <div class="track"><div class="fill" style="width:${{Math.max(4, row.value / max * 100)}}%"></div></div>
          <strong>${{money(row.value)}}</strong>`;
        el.appendChild(wrap);
      }});
    }}

    function renderFeed(items) {{
      const feed = document.getElementById("feed");
      feed.innerHTML = "";
      items.forEach(item => {{
        const row = document.createElement("div");
        row.className = "feed-item";
        row.innerHTML = `<div>${{item.title}}</div><span>${{item.value}}</span>`;
        feed.appendChild(row);
      }});
    }}

    async function refresh() {{
      const year = yearSelect.value;
      const company = document.getElementById("company").value;
      setText("apiStatus", "Conectando...");
      document.getElementById("apiStatus").className = "";
      try {{
        const [api, servicios, finanzas, informes] = await Promise.all([
          getJSON("/", company),
          getJSON(`/dashboard/servicios?anio=${{year}}`, company),
          getJSON(`/dashboard-finanzas/resumen?anio=${{year}}`, company),
          getJSON(`/dashboard-informes/resumen?anio=${{year}}`, company)
        ]);
        document.getElementById("apiStatus").textContent = api.status || "Online";
        document.getElementById("apiStatus").className = "ok";
        setText("kpiServices", fmtNumber.format(servicios?.kpis?.total_servicios || 0));
        setText("kpiRevenue", money(finanzas?.kpis?.revenue_total || servicios?.kpis?.total_facturado || 0));
        setText("kpiAR", money(finanzas?.kpis?.ar_total || servicios?.kpis?.total_ar || 0));
        setText("kpiReports", fmtNumber.format(informes?.kpis?.total_informes || 0));
        drawBars("revenueChart", finanzas?.revenue_mensual?.length ? finanzas.revenue_mensual : servicios.revenue_mensual, "mes", "revenue");
        renderFeed([
          {{ title: "API Railway", value: "Online" }},
          {{ title: "A/R pendiente", value: money(finanzas?.kpis?.ar_total || 0) }},
          {{ title: "A/P pendiente", value: money(finanzas?.kpis?.ap_total || 0) }},
          {{ title: "Servicios del periodo", value: fmtNumber.format(servicios?.kpis?.total_servicios || 0) }}
        ]);
        setText("updatedAt", new Date().toLocaleString());
      }} catch (err) {{
        document.getElementById("apiStatus").textContent = "Error";
        document.getElementById("apiStatus").className = "error";
        renderFeed([{{ title: "No se pudo cargar el dashboard", value: err.message }}]);
        drawBars("revenueChart", [], "mes", "revenue");
      }}
    }}

    document.getElementById("refresh").addEventListener("click", refresh);
    document.getElementById("company").addEventListener("change", refresh);
    yearSelect.addEventListener("change", refresh);
    refresh();
  </script>
</body>
</html>"""
    )


@router.get("/som/logo/{brand}")
def som_web_logo(brand: str) -> FileResponse:
    filename = "mci_logo.png" if brand.lower() == "mci" else "header.png"
    path = _ASSETS / filename
    if not path.exists():
        fallback = _ASSETS / "mci_logo.png"
        if not fallback.exists():
            raise HTTPException(status_code=404, detail="Logo no disponible")
        path = fallback
    return FileResponse(path)
