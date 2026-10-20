(() => {
  "use strict";
  let current = null;
  const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const dateText = v => /^\d{4}-\d\d-\d\d$/.test(v || "") ? v.split("-").reverse().join("/") : (v || "");
  const statusText = v => ({Draft:"Borrador",Approved:"Aprobado",Rejected:"Rechazado","Pending for review":"Pendiente de revision","Pending review":"Pendiente de revision"}[v] || v || "");
  function canLeave() {
    if (!current) return true;
    if (current.busy) {current.error("Espere a que termine la operacion."); return false;}
    return !current.dirty || confirm("Hay cambios sin guardar. Desea salir y descartarlos?");
  }
  function destroy() {
    if (!current) return;
    current.controller.abort();
    window.removeEventListener("beforeunload", current.unload);
    current = null;
  }
  async function mount(root, options) {
    destroy();
    const s = current = {root, options, controller:new AbortController(), dirty:false, busy:false, kind:"weight", offset:0, q:"", status:"", record:null};
    const $ = sel => root.querySelector(sel);
    const alive = () => current === s;
    s.unload = e => {if (s.dirty || s.busy) {e.preventDefault(); e.returnValue = "";}};
    window.addEventListener("beforeunload", s.unload);
    s.error = message => {if (alive() && $("#cert-error")) $("#cert-error").textContent = message;};
    root.classList.add("som-certificates");
    root.innerHTML = '<div role="status">Cargando certificados...</div><div id="cert-error" role="alert"></div>';
    async function api(path, method="GET", body) {
      const response = await fetch("/informes/certificates" + path, {method, headers:{...options.headers(),"Content-Type":"application/json"}, signal:s.controller.signal, body:body === undefined ? undefined : JSON.stringify(body)});
      const data = await response.json().catch(() => null);
      if (!response.ok) throw new Error(typeof data?.detail === "string" ? data.detail : `No se pudo completar la operacion (${response.status}). Sus cambios siguen en pantalla.`);
      if (!data) throw new Error("El servidor no devolvio una respuesta valida.");
      return data;
    }
    async function run(fn) {
      if (s.busy) return;
      s.busy = true;
      root.setAttribute("aria-busy","true");
      const disabled = [...root.querySelectorAll("button,input,select,textarea")].map(el => [el,el.disabled]);
      disabled.forEach(([el]) => {el.disabled=true;});
      s.error("");
      try {await fn();} catch(e) {if (e.name !== "AbortError") s.error(e.message);}
      finally {s.busy=false; root.removeAttribute("aria-busy"); disabled.forEach(([el,v]) => {if(el.isConnected) el.disabled=v;});}
    }
    function shell(body) {
      const spec = s.boot.types[s.kind];
      root.innerHTML = `<header class="cert-head"><h2>Certificados</h2><span class="cert-meta">${esc(s.boot.company)}</span></header>
        <nav class="cert-types" role="tablist" aria-label="Certificados">${Object.entries(s.boot.types).map(([k,v]) => `<button role="tab" data-kind="${k}" aria-selected="${k===s.kind}">${esc(v.label)}</button>`).join("")}</nav>
        <div id="cert-error" role="alert"></div><h3>${esc(spec.title)}</h3>${body}`;
      root.querySelectorAll("[data-kind]").forEach(b => b.onclick = () => {
        if (s.busy || !canLeave()) return;
        s.kind=b.dataset.kind; s.offset=0; s.q=""; s.status=""; s.dirty=false; s.record=null; run(list);
      });
    }
    async function list() {
      const data = await api(`/${s.kind}?q=${encodeURIComponent(s.q)}&status=${encodeURIComponent(s.status)}&offset=${s.offset}`);
      if (!alive()) return;
      s.record=null;
      shell(`<form class="cert-tools" id="cert-search"><input name="q" aria-label="Buscar certificado" placeholder="Informe, buque o cliente" value="${esc(s.q)}">
        <select name="status" aria-label="Estado"><option value="">Todos los estados</option>${["Draft","Pending for review","Approved","Rejected"].map(x=>`<option value="${x}" ${s.status===x?"selected":""}>${statusText(x)}</option>`).join("")}</select><button>Buscar</button>
        ${s.boot.permissions.create?'<button type="button" class="cert-primary" id="cert-new">Nuevo certificado</button>':""}</form>
        <div class="cert-scroll"><table><thead><tr><th>Informe</th><th>Buque / contenedor</th><th>Cliente</th><th>Fecha</th><th>Estado</th><th></th></tr></thead><tbody>
        ${data.data.map(r=>`<tr><td>${esc(r.report_number)}</td><td>${esc(r.vessel)}</td><td>${esc(r.customer)}</td><td>${esc(dateText(r.date))}</td><td>${esc(statusText(r.status))}</td><td><button data-open="${r.id}">Abrir</button></td></tr>`).join("") || '<tr><td colspan="6">No hay certificados para esta consulta.</td></tr>'}</tbody></table></div>
        <div class="cert-tools"><span class="cert-meta">${data.total} certificados</span><button id="cert-prev" ${s.offset===0?"disabled":""}>Anterior</button><button id="cert-next" ${s.offset+50>=data.total?"disabled":""}>Siguiente</button></div>`);
      $("#cert-search").onsubmit=e=>{e.preventDefault(); const form=new FormData(e.target); s.q=form.get("q"); s.status=form.get("status"); s.offset=0;run(list);};
      if ($("#cert-new")) $("#cert-new").onclick=()=>run(()=>pickService());
      $("#cert-prev").onclick=()=>{s.offset=Math.max(0,s.offset-50);run(list);};
      $("#cert-next").onclick=()=>{s.offset+=50;run(list);};
      root.querySelectorAll("[data-open]").forEach(b=>b.onclick=()=>run(async()=>{const d=await api(`/${s.kind}/${b.dataset.open}`); if(alive()) editor(d);}));
    }
    async function pickService(q="",offset=0) {
      const data=await api(`/services?q=${encodeURIComponent(q)}&offset=${offset}`);
      if(!alive())return;
      shell(`<form id="cert-service-search" class="cert-tools"><input name="q" value="${esc(q)}" placeholder="Informe, buque o cliente" aria-label="Buscar servicio"><button>Buscar servicio</button><button type="button" id="cert-back">Volver</button></form>
        <div class="cert-scroll"><table><thead><tr><th>Informe</th><th>Buque / contenedor</th><th>Cliente</th><th></th></tr></thead><tbody>${data.data.map((r,i)=>`<tr><td>${esc(r.num_informe)}</td><td>${esc(r.buque_contenedor)}</td><td>${esc(r.cliente)}</td><td><button data-service="${i}">Seleccionar</button></td></tr>`).join("") || '<tr><td colspan="4">No hay servicios.</td></tr>'}</tbody></table></div>
        <div class="cert-tools"><button id="cert-prev" ${!offset?"disabled":""}>Anterior</button><button id="cert-next" ${!data.more?"disabled":""}>Siguiente</button></div>`);
      $("#cert-service-search").onsubmit=e=>{e.preventDefault();run(()=>pickService(new FormData(e.target).get("q")));};
      $("#cert-back").onclick=()=>run(list);
      $("#cert-prev").onclick=()=>run(()=>pickService(q,Math.max(0,offset-50)));
      $("#cert-next").onclick=()=>run(()=>pickService(q,offset+50));
      root.querySelectorAll("[data-service]").forEach(b=>b.onclick=()=>{
        const service=data.data[Number(b.dataset.service)], spec=s.boot.types[s.kind];
        const fields={[spec.number]:service.num_informe,port:service.puerto,country:service.pais,customer:service.cliente};
        if(s.kind!=="lashing") fields.vessel=service.buque_contenedor;
        if(s.kind==="weight") Object.assign(fields,{continent:service.continente,operation:service.operacion});
        if(s.kind==="holds")fields.load_port=service.puerto;
        if(["sampling","sealing"].includes(s.kind))fields.certificate_no=service.num_informe;
        editor({data:fields,version:null});s.dirty=true;
      });
    }
    function editor(payload) {
      if(!alive())return;
      s.record=payload;
      const spec=s.boot.types[s.kind], row=payload.data;
      const editable=row.id ? s.boot.permissions.edit && row.status!=="Approved" : s.boot.permissions.create;
      shell(`<div class="cert-tools"><button id="cert-back">Volver</button><strong>${esc(row[spec.number])}</strong><span class="cert-status">${esc(statusText(row.status || "Draft"))}</span></div>
        <form id="cert-form"><div class="cert-editor"><nav class="cert-sections">${spec.sections.map((g,i)=>`<a href="#cert-section-${i}">${esc(g.title)}</a>`).join("")}</nav><div>${spec.sections.map((g,i)=>`<section class="cert-section" id="cert-section-${i}"><h3>${esc(g.title)}</h3><div class="cert-fields">${g.fields.map(f=>{
          const value=f.type==="date"?dateText(row[f.key]):row[f.key];
          return `<label class="${f.type==="textarea"?"cert-wide":""}">${esc(f.label)}${f.type==="textarea"?`<textarea name="${f.key}" maxlength="30000" ${!editable?"disabled":""}>${esc(value)}</textarea>`:`<input type="text" name="${f.key}" value="${esc(value)}" maxlength="2000" ${f.type==="date"?'placeholder="DD/MM/YYYY"':f.type==="time"?'placeholder="HH:MM"':""} ${f.key===spec.number?"readonly":""} ${!editable?"disabled":""}>`}</label>`;
        }).join("")}</div></section>`).join("")}</div></div>
        <footer class="cert-actions">${editable?'<button type="submit" class="cert-primary">Guardar borrador</button><button type="button" id="cert-submit">Enviar a revision</button>':""}
        ${row.id && s.boot.permissions.approve?'<button type="button" id="cert-approve">Aprobar</button><button type="button" id="cert-reject">Rechazar</button>':""}
        ${row.id?`<select id="cert-format" aria-label="Formato de exportacion"><option value="${spec.document}">${spec.document==="word"?"Word":"Excel"}</option><option value="pdf">PDF</option></select><button type="button" id="cert-export">Descargar</button>`:""}
        <span id="cert-save-state" class="cert-meta" role="status"></span></footer></form>`);
      $("#cert-back").onclick=()=>{if(canLeave()){s.dirty=false;run(list);}};
      $("#cert-form").oninput=()=>{s.dirty=true;$("#cert-save-state").textContent="Cambios sin guardar";};
      async function save(submit) {
        // Snapshot before disabling controls; disabled fields are omitted by FormData.
        const fields={};
        for(const f of spec.sections.flatMap(g=>g.fields)) {
          const v=$("#cert-form").elements.namedItem(f.key).value;
          const old=f.type==="date"?dateText(row[f.key]):String(row[f.key]??"");
          if(!row.id || v!==old) fields[f.key]=v;
        }
        await run(async()=>{
          const result=await api(`/${s.kind}${row.id?"/"+row.id:""}`,row.id?"PATCH":"POST",{fields,version:payload.version,submit});
          if(!alive())return;
          s.dirty=false;editor(result);$("#cert-save-state").textContent="Guardado";
        });
      }
      $("#cert-form").onsubmit=e=>{e.preventDefault();if(editable)save(false);};
      if($("#cert-submit"))$("#cert-submit").onclick=()=>save(true);
      for(const [id,status] of [["cert-approve","Approved"],["cert-reject","Rejected"]]) {
        if($("#"+id))$("#"+id).onclick=()=>{
          if(s.dirty){s.error("Guarde los cambios antes de revisar.");return;}
          if(!confirm(`${statusText(status)}: confirmar cambio de estado?`))return;
          run(async()=>{const d=await api(`/${s.kind}/${row.id}/status`,"POST",{version:payload.version,status});if(alive())editor(d);});
        };
      }
      if($("#cert-export"))$("#cert-export").onclick=()=>{
        if(s.dirty){s.error("Guarde los cambios antes de descargar.");return;}
        const format=$("#cert-format").value;
        run(async()=>{
          const response=await fetch(`/informes/certificates/${s.kind}/${row.id}/export/${format}`,{headers:options.headers(),signal:s.controller.signal});
          if(!response.ok){const data=await response.json().catch(()=>null);throw new Error(data?.detail || "No se pudo generar el documento.");}
          const url=URL.createObjectURL(await response.blob());
          const a=document.createElement("a");a.href=url;a.download=`Certificate_${s.kind}_${row.id}.${{word:"docx",excel:"xlsx",pdf:"pdf"}[format]}`;a.click();setTimeout(()=>URL.revokeObjectURL(url),30000);
        });
      };
    }
    await run(async()=>{s.boot=await api("/bootstrap");if(alive())await list();});
  }
  window.SOMCertificates={mount,canLeave,destroy};
})();
