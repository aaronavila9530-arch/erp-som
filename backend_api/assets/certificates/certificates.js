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
    const s = current = {root, options, controller:new AbortController(), dirty:false, busy:false, mode:"review", kind:options.kind || "weight", offset:0, q:"", status:"", record:null};
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
      root.innerHTML = `<header class="cert-head"><h2>${options.kind ? esc(spec.title) : 'Certificados'}</h2><span class="cert-meta">${esc(s.boot.company)}</span></header>
        <nav class="cert-workflows" aria-label="Flujo de informes">${s.boot.permissions.create?`<button type="button" data-mode="create" aria-pressed="${s.mode==='create'}">Crear</button>`:''}<button type="button" data-mode="review" aria-pressed="${s.mode==='review'}">Revisar</button></nav>
        <nav class="cert-types" role="tablist" aria-label="Certificados">${Object.entries(s.boot.types).map(([k,v]) => `<button role="tab" data-kind="${k}" aria-selected="${k===s.kind}">${esc(v.label)}</button>`).join("")}</nav>
        <div id="cert-error" role="alert"></div><h3>${esc(spec.title)}</h3>${body}`;
      if(options.kind) {$(".cert-types").hidden=true;root.querySelector('h3').hidden=true;}
      root.querySelectorAll('[data-mode]').forEach(b=>b.onclick=()=>{
        if(s.busy || s.mode===b.dataset.mode || !canLeave())return;
        s.mode=b.dataset.mode;s.dirty=false;s.offset=0;s.status='';
        run(s.mode==='create'?pickService:list);
      });
      root.querySelectorAll("[data-kind]").forEach(b => b.onclick = () => {
        if (s.busy || !canLeave()) return;
        s.kind=b.dataset.kind; s.offset=0; s.q=""; s.status=""; s.dirty=false; s.record=null; run(s.mode==='create'?pickService:list);
      });
    }
    async function list() {
      s.mode='review';
      const data = await api(`/${s.kind}?q=${encodeURIComponent(s.q)}&status=${encodeURIComponent(s.status)}&offset=${s.offset}`);
      if (!alive()) return;
      s.record=null;
      shell(`<form class="cert-tools" id="cert-search"><input name="q" aria-label="Buscar certificado" placeholder="Informe, buque o cliente" value="${esc(s.q)}">
        <select name="status" aria-label="Estado"><option value="">Todos los estados</option>${["Draft","Pending for review","Approved","Rejected"].map(x=>`<option value="${x}" ${s.status===x?"selected":""}>${statusText(x)}</option>`).join("")}</select><button>Buscar</button>
        ${s.mode==='edit' && s.boot.permissions.create?'<button type="button" class="cert-primary" id="cert-new">Nuevo informe</button>':""}</form>
        <div class="cert-scroll"><table><thead><tr><th>Informe</th><th>Buque / contenedor</th><th>Cliente</th><th>Fecha</th><th>Estado</th><th></th></tr></thead><tbody>
        ${data.data.map(r=>`<tr><td>${esc(r.report_number)}</td><td>${esc(r.vessel)}</td><td>${esc(r.customer)}</td><td>${esc(dateText(r.date))}</td><td>${esc(statusText(r.status))}</td><td><button data-open="${r.id}">Abrir</button></td></tr>`).join("") || '<tr><td colspan="6">No hay certificados para esta consulta.</td></tr>'}</tbody></table></div>
        <div class="cert-tools"><span class="cert-meta">${data.total} certificados</span><button id="cert-prev" ${s.offset===0?"disabled":""}>Anterior</button><button id="cert-next" ${s.offset+50>=data.total?"disabled":""}>Siguiente</button></div>`);
      $("#cert-search").onsubmit=e=>{e.preventDefault(); const form=new FormData(e.target); s.q=form.get("q"); s.status=form.get("status"); s.offset=0;run(list);};
      if ($("#cert-new")) $("#cert-new").onclick=()=>run(()=>pickService());
      $("#cert-prev").onclick=()=>{s.offset=Math.max(0,s.offset-50);run(list);};
      $("#cert-next").onclick=()=>{s.offset+=50;run(list);};
      root.querySelectorAll("[data-open]").forEach(b=>{b.textContent='Revisar informe';b.onclick=()=>run(async()=>{const d=await api(`/${s.kind}/${b.dataset.open}`); if(alive()) editor(d);});});
    }
    async function pickService(q="",offset=0) {
      s.mode='create';
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
        if(s.kind==="grain") {
          for(const key of Object.keys(fields)) delete fields[key];
          Object.assign(fields,{cert_no:service.num_informe,vessel_name:service.buque_contenedor,requested_by:service.cliente});
        }
        if(['condition','cargo_condition'].includes(s.kind)) {
          for(const key of Object.keys(fields))delete fields[key];
          Object.assign(fields,{report_number:service.num_informe,vessel:service.buque_contenedor,
            requested_by:service.cliente,continent:service.continente,country:service.pais,port:service.puerto,
            service_start_date:String(service.fecha_inicio||'').slice(0,10),operation:service.operacion});
        }
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
      if(row.id)s.mode='review';
      const editable=row.id ? s.boot.permissions.edit && row.status!=="Approved" : s.boot.permissions.create;
      shell(`<div class="cert-tools"><button id="cert-back">Volver</button><strong>${esc(row[spec.number])}</strong><span class="cert-status">${esc(statusText(row.status || "Draft"))}</span></div>
        <form id="cert-form"><div class="cert-editor"><nav class="cert-sections">${spec.sections.map((g,i)=>`<a href="#cert-section-${i}">${esc(g.title)}</a>`).join("")}</nav><div>${spec.sections.map((g,i)=>`<details class="cert-section" id="cert-section-${i}" ${s.kind!=="grain" || i<3 ? "open" : ""}><summary>${esc(g.title)}</summary><div class="cert-fields">${g.fields.map(f=>{
          const value=f.type==="date"?dateText(row[f.key]):row[f.key];
          return `<label class="${f.type==="textarea"?"cert-wide":""}">${esc(f.label)}${f.type==="textarea"?`<textarea name="${f.key}" maxlength="30000" ${!editable?"disabled":""}>${esc(value)}</textarea>`:`<input type="text" name="${f.key}" value="${esc(value)}" maxlength="2000" ${f.type==="date"?'placeholder="DD/MM/YYYY"':f.type==="time"?'placeholder="HH:MM"':f.type==="datetime"?'placeholder="DD/MM/YYYY HH:MM"':""} ${f.key===spec.number?"readonly":""} ${!editable?"disabled":""}>`}</label>`;
        }).join("")}</div></details>`).join("")}</div></div>
        <footer class="cert-actions"><div class="cert-action-group"><span class="cert-action-label">Edicion</span>${editable?'<button type="submit" class="cert-primary">Guardar borrador</button><button type="button" id="cert-submit">Enviar a revision</button>':""}
        </div><div class="cert-action-group"><span class="cert-action-label">Revision</span>${row.id && s.boot.permissions.approve?'<button type="button" id="cert-approve">Aprobar</button><button type="button" id="cert-reject">Rechazar</button>':""}
        </div><div class="cert-action-group"><span class="cert-action-label">Exportacion</span>${row.id?`<select id="cert-format" aria-label="Formato de exportacion"><option value="${spec.document}">${spec.document==="word"?"Word":"Excel"}</option><option value="pdf">Informe PDF</option>${s.kind==="grain"?'<option value="presentation">Presentacion PDF</option><option value="complete">Presentacion + informe PDF</option>':""}</select><button type="button" id="cert-export">Descargar</button>`:""}
        </div><span id="cert-save-state" class="cert-meta" role="status"></span></footer></form>`);
      $("#cert-form").prepend($(".cert-actions"));
      const groups=root.querySelectorAll('.cert-action-group');
      groups[0].hidden=!editable;
      groups[1].hidden=s.mode!=='review';
      groups[2].hidden=s.mode!=='review';
      root.querySelectorAll(".cert-sections a").forEach(a=>a.onclick=()=>{const section=$(a.getAttribute("href"));if(section)section.open=true;});
      spec.sections.forEach((group,index)=>{
        if(!group.repeatable)return;
        const section=$('#cert-section-'+index),inputs=group.fields.map(f=>$("#cert-form").elements.namedItem(f.key));
        let count=Math.max(1,...inputs.map((input,i)=>input.value.trim()?i+1:0));
        const tools=document.createElement('div');tools.className='cert-tools';
        tools.innerHTML='<button type="button" title="Agregar texto" aria-label="Agregar texto">+</button><button type="button" title="Eliminar ultimo texto" aria-label="Eliminar ultimo texto">−</button>';
        const [add,remove]=tools.children;
        function refresh(){inputs.forEach((input,i)=>input.parentElement.hidden=i>=count);add.disabled=!editable||count===inputs.length;remove.disabled=!editable||count===1;}
        const mark=()=>{s.dirty=true;$('#cert-save-state').textContent='Cambios sin guardar';};
        add.onclick=()=>{if(count<inputs.length){count++;refresh();inputs[count-1].focus();}};
        remove.onclick=()=>{if(count<=1)return;const input=inputs[count-1];if(input.value.trim()&&!confirm('Eliminar este texto?'))return;input.value='';count--;mark();refresh();};
        section.append(tools);refresh();
      });
      if(s.kind==="grain" && editable) {
        const conclusion=$('[name="conclusion"]');
        const tools=document.createElement('div'); tools.className='cert-tools';
        tools.innerHTML='<select aria-label="Idioma de propuesta IA"><option value="ES">Español</option><option value="EN">English</option></select><button type="button">Proponer redaccion con IA</button><div class="cert-ai-result" hidden></div>';
        conclusion.parentElement.after(tools);
        tools.querySelector('button').onclick=()=>{
          if(!conclusion.value.trim()){s.error('Escriba una conclusion antes de solicitar una propuesta.');return;}
          const text=conclusion.value,language=tools.querySelector('select').value;
          run(async()=>{
            const result=await api('/grain-assist','POST',{text,language});
            if(!alive())return;
            const panel=tools.querySelector('.cert-ai-result');panel.hidden=false;
            panel.innerHTML='<label>Propuesta IA<textarea readonly></textarea></label><button type="button" data-accept>Aceptar propuesta</button><button type="button" data-discard>Descartar</button>';
            panel.querySelector('textarea').value=result.text;
            panel.querySelector('[data-accept]').onclick=()=>{
              conclusion.value=result.text;conclusion.dispatchEvent(new Event('input',{bubbles:true}));panel.hidden=true;
            };
            panel.querySelector('[data-discard]').onclick=()=>{panel.hidden=true;};
          });
        };
      }
      $("#cert-back").onclick=()=>{if(canLeave()){s.dirty=false;run(list);}};
      $("#cert-form").oninput=e=>{
        if(!e.target.matches("input[name], textarea[name]"))return;
        s.dirty=true;$("#cert-save-state").textContent="Cambios sin guardar";
      };
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
          const a=document.createElement("a");a.href=url;a.download=`${s.kind}_${row.id}_${format}.${{word:"docx",excel:"xlsx",pdf:"pdf",presentation:"pdf",complete:"pdf"}[format]}`;a.click();setTimeout(()=>URL.revokeObjectURL(url),30000);
        });
      };
    }
    await run(async()=>{
      s.boot=await api("/bootstrap");
      s.boot.types=Object.fromEntries(Object.entries(s.boot.types).filter(([k])=>options.kind ? k===options.kind : !['grain','condition','cargo_condition'].includes(k)));
      if(alive())await list();
    });
  }
  window.SOMCertificates={mount,canLeave,destroy};
})();
