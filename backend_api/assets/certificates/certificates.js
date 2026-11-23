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
    root.classList.toggle('som-crane',options.kind==='crane');
    root.classList.toggle('som-bunker',options.kind==='bunker');
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
      const data=await api(`/services?q=${encodeURIComponent(q)}&offset=${offset}&kind=${encodeURIComponent(s.kind)}`);
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
        if(s.kind==='crane'){fields.client=service.cliente;delete fields.customer;}
        if(s.kind==='bunker'){fields.client=service.cliente;fields.ship_name=service.buque_contenedor;fields.certificate='ON_HIRE';delete fields.customer;}
        if(!['lashing','bunker'].includes(s.kind)) fields.vessel=service.buque_contenedor;
        if(s.kind==='logistics') {
          delete fields.vessel;
          fields.vessel_name=service.buque_contenedor;
        }
        if(s.kind==="grain") {
          for(const key of Object.keys(fields)) delete fields[key];
          Object.assign(fields,{cert_no:service.num_informe,vessel_name:service.buque_contenedor,requested_by:service.cliente});
        }
        if(['condition','cargo_condition','port_captancy'].includes(s.kind)) {
          for(const key of Object.keys(fields))delete fields[key];
          Object.assign(fields,{report_number:service.num_informe,vessel:service.buque_contenedor,
            requested_by:service.cliente,continent:service.continente,country:service.pais,port:service.puerto,
            service_start_date:String(service.fecha_inicio||'').slice(0,10),operation:service.operacion});
          if(s.kind==='port_captancy')delete fields.service_start_date;
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
        <form id="cert-form"><div class="cert-editor"><nav class="cert-sections">${spec.sections.map((g,i)=>`<a href="#cert-section-${i}">${esc(g.title)}</a>`).join("")}</nav><div>${spec.sections.map((g,i)=>`<details class="cert-section" id="cert-section-${i}" ${!['grain','crane','bunker'].includes(s.kind) || i<3 ? "open" : ""}><summary>${esc(g.title)}</summary><div class="cert-fields">${g.fields.map(f=>{
          const value=f.type==="date"?dateText(row[f.key]):row[f.key];
          if(f.type==='checkbox')return `<label class="mci-section-option"><input type="checkbox" name="${f.key}" ${value?'checked':''} ${!editable?'disabled':''}><span>${esc(f.label)}</span></label>`;
          if(f.type==='select')return `<label>${esc(f.label)}<select name="${f.key}" ${!editable?'disabled':''}>${f.options.map(v=>`<option value="${esc(v)}" ${v===(value||'')?'selected':''}>${esc(v||'Not specified')}</option>`).join('')}</select></label>`;
          return `<label class="${f.type==="textarea"?"cert-wide":""}">${esc(f.label)}${f.type==="textarea"?`<textarea name="${f.key}" maxlength="30000" ${!editable?"disabled":""}>${esc(value)}</textarea>`:`<input type="text" name="${f.key}" value="${esc(value)}" maxlength="2000" ${f.type==="date"?'placeholder="DD/MM/YYYY"':f.type==="time"?'placeholder="HH:MM"':f.type==="datetime"?'placeholder="DD/MM/YYYY HH:MM"':""} ${f.key===spec.number?"readonly":""} ${!editable?"disabled":""}>`}</label>`;
        }).join("")}</div></details>`).join("")}</div></div>
        <footer class="cert-actions"><div class="cert-action-group"><span class="cert-action-label">Edicion</span>${editable?'<button type="submit" class="cert-primary">Guardar borrador</button><button type="button" id="cert-submit">Enviar a revision</button>':""}
        </div><div class="cert-action-group"><span class="cert-action-label">Revision</span>${row.id && s.boot.permissions.approve?'<button type="button" id="cert-approve">Aprobar</button><button type="button" id="cert-reject">Rechazar</button>':""}
        </div><div class="cert-action-group"><span class="cert-action-label">Exportacion</span>${row.id?`<select id="cert-format" aria-label="Formato de exportacion"><option value="${spec.document}">${spec.document==="word"?"Word":"Excel"}</option><option value="pdf">Informe PDF</option>${['grain','logistics'].includes(s.kind)?'<option value="presentation">Presentacion PDF</option><option value="complete">Presentacion + informe PDF</option>':""}</select><button type="button" id="cert-export">Descargar</button>`:""}
        </div><span id="cert-save-state" class="cert-meta" role="status"></span></footer></form>`);
      $("#cert-form").prepend($(".cert-actions"));
      if(s.kind==='bunker'){
        const form=$('#cert-form');
        spec.sections.forEach((group,index)=>{$('#cert-section-'+index).open=index===0||!!(group.tank_fuel&&group.fields.some(f=>row[f.key]!=null&&String(row[f.key]).trim()));});
        for(const key of ['client','ship_name','port','country','trim','log_at_survey_vlsfo','log_at_survey_lsmgo'])form.elements.namedItem(key).readOnly=true;
        if(row.id)form.elements.namedItem('certificate').disabled=true;
        const totals=document.createElement('output');totals.className='cert-tools';totals.setAttribute('aria-live','polite');form.prepend(totals);
        let revision=0,timer;
        const refresh=()=>{
          clearTimeout(timer);const rev=++revision;totals.textContent='Calculando...';
          timer=setTimeout(async()=>{
            if(!alive()||!form.isConnected)return;
            const fields=Object.fromEntries(spec.sections.flatMap(g=>g.fields).map(f=>[f.key,form.elements.namedItem(f.key).value]));
            try{
              const result=await api('/bunker/calculate','POST',{fields});
              if(!alive()||!form.isConnected||revision!==rev)return;
              for(const [key,value] of Object.entries(result.fields))if(form.elements.namedItem(key)&&(key==='trim'||key==='log_at_survey_vlsfo'||key==='log_at_survey_lsmgo'||key.endsWith('_temp_f')||key.endsWith('_weight_mt')))form.elements.namedItem(key).value=value??'';
              totals.textContent=result.valid&&result.tanks.length?`VLSFO: ${result.totals.vlsfo} MT | MGO: ${result.totals.mgo} MT | Total: ${result.total_mt} MT`:(result.errors.join(' | ')||'Sin mediciones');
              if(result.valid&&result.tanks.length)for(const fuel of ['vlsfo','mgo'])if(result.dlosp[fuel]!==null)totals.textContent+=` | DLOSP ${fuel.toUpperCase()}: ${result.dlosp[fuel]} MT`;
            }catch(error){if(error.name!=='AbortError'&&alive()&&revision===rev)totals.textContent=error.message;}
          },350);
        };
        for(const f of spec.sections.flatMap(g=>g.fields))if(f.readonly)form.elements.namedItem(f.key).readOnly=true;
        spec.sections.forEach((g,index)=>{
          if(!g.tank_fuel&&!g.figure_rows)return;
          const section=$('#cert-section-'+index),labels=[...section.querySelectorAll('.cert-fields>label')];
          const size=g.row_size,limit=g.fields.length/size,minimum=g.figure_rows?3:1;
          const tankRows=[];
          for(let i=0;i<limit;i++){
            const fieldset=document.createElement('fieldset');fieldset.className='cert-bunker-tank';
            const legend=document.createElement('legend');legend.textContent=g.figure_rows?({1:'Generator until DLOSP',2:'Departure M.E. to sea buoy'}[i]||`Figure ${i+1}`):`${g.tank_fuel.toUpperCase()} ${i+1}`;fieldset.append(legend);
            labels.slice(i*size,(i+1)*size).forEach(label=>fieldset.append(label));section.querySelector('.cert-fields').append(fieldset);tankRows.push(fieldset);
          }
          let count=Math.max(minimum,...g.fields.map((f,i)=>row[f.key]!=null&&String(row[f.key]).trim()?Math.floor(i/size)+1:0));
          const tools=document.createElement('div');tools.className='cert-tools';
          tools.innerHTML='<button type="button" title="Agregar tanque" aria-label="Agregar tanque">+</button><button type="button" title="Eliminar ultimo tanque" aria-label="Eliminar ultimo tanque">−</button>';
          const [add,remove]=tools.children;
          if(g.figure_rows){add.title='Agregar fila';remove.title='Eliminar ultima fila';add.setAttribute('aria-label',add.title);remove.setAttribute('aria-label',remove.title);}
          const show=()=>{tankRows.forEach((l,i)=>l.hidden=i>=count);add.disabled=!editable||count===limit;remove.disabled=!editable||count===minimum;};
          add.onclick=()=>{count++;show();labels[(count-1)*size].querySelector('input').focus();};
          remove.onclick=()=>{if(!confirm('Eliminar la ultima fila y sus datos?'))return;g.fields.slice((count-1)*size,count*size).forEach(f=>form.elements.namedItem(f.key).value='');count--;s.dirty=true;show();refresh();};
          section.append(tools);show();
        });
        form.addEventListener('input',refresh);refresh();
        if(row.id){
          const format=$('#cert-format');format.add(new Option('Presentacion PDF','presentation'));format.add(new Option('Only: presentacion + informe PDF','complete'));
          if(s.boot.company==='MCI-CR')format.add(new Option('Excel de calculos','excel'));
          else format.add(new Option('Word','word'));
          const language=document.createElement('select');language.id='bunker-language';language.setAttribute('aria-label','Idioma del informe');
          language.innerHTML='<option value="EN">English</option><option value="ES">Español</option>';language.hidden=s.boot.company!=='MCI-CR';format.before(language);
          window.SOMPortAttachments(form,{url:`/informes/certificates/bunker/${row.id}/bundle`,getLanguage:()=>language.value,filename:'Bunker_Condition.pdf',headers:options.headers,run,dirty:()=>s.dirty,signal:s.controller.signal});
        }
      }
      if(s.kind==='crane'){
        for(const key of ['client','vessel','port','country'])$(`[name="${key}"]`).readOnly=true;
        const link=$('[name="link_picture"]');link.inputMode='url';link.placeholder='https://';
        if(row.id){
          $('#cert-format').add(new Option('Presentacion PDF','presentation'));
          $('#cert-format').add(new Option('Presentacion + informe PDF','complete'));
          window.SOMPortAttachments($('#cert-form'),{url:`/informes/certificates/crane/${row.id}/bundle`,filename:'Crane_Inspection_complete.pdf',headers:options.headers,run,dirty:()=>s.dirty,signal:s.controller.signal});
        }
        if(editable)root.querySelectorAll('textarea[name]').forEach(input=>window.SOMLogisticsAssist(input,{request:body=>api('/crane-assist','POST',body),run,alive,mark:()=>input.dispatchEvent(new Event('input',{bubbles:true}))}));
      }
      if(s.kind==='port_captancy'&&row.id)window.SOMPortAttachments($('#cert-form'),{
        url:`/informes/certificates/port_captancy/${row.id}/bundle`,headers:options.headers,run,
        dirty:()=>s.dirty,signal:s.controller.signal
      });
      if(s.kind==='port_captancy' && row.id){
        $('#cert-format').add(new Option('Presentacion PDF','presentation'));
        $('#cert-format').add(new Option('Presentacion + informe PDF','complete'));
      }
      if(s.kind==='logistics')for(const key of ['customer','vessel_name','port','country'])$(`[name="${key}"]`).readOnly=true;
      if(s.kind==='port_captancy')for(const key of ['requested_by','vessel','continent','port','country','operation'])$(`[name="${key}"]`).readOnly=true;
      if(s.kind==='port_captancy' && editable)root.querySelectorAll('textarea[name]').forEach(input=>window.SOMLogisticsAssist(input,{
        request:body=>api('/port-captancy-assist','POST',body),run,alive,mark:()=>input.dispatchEvent(new Event('input',{bubbles:true}))
      }));
      if(s.kind==='logistics' && editable)root.querySelectorAll('textarea[name]').forEach(input=>window.SOMLogisticsAssist(input,{
        request:body=>api('/logistics-assist','POST',body),run,alive,mark:()=>input.dispatchEvent(new Event('input',{bubbles:true}))
      }));
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
        if(!e.target.matches("input[name], textarea[name], select[name]"))return;
        s.dirty=true;$("#cert-save-state").textContent="Cambios sin guardar";
      };
      async function save(submit) {
        // Snapshot before disabling controls; disabled fields are omitted by FormData.
        const fields={};
        for(const f of spec.sections.flatMap(g=>g.fields)) {
          const input=$("#cert-form").elements.namedItem(f.key);
          const v=f.type==='checkbox'?input.checked:input.value;
          const old=f.type==='checkbox'?!!row[f.key]:f.type==="date"?dateText(row[f.key]):String(row[f.key]??"");
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
          const response=await fetch(`/informes/certificates/${s.kind}/${row.id}/export/${format}${s.kind==='bunker'?'?language='+$('#bunker-language').value:''}`,{headers:options.headers(),signal:s.controller.signal});
          if(!response.ok){const data=await response.json().catch(()=>null);throw new Error(data?.detail || "No se pudo generar el documento.");}
          const url=URL.createObjectURL(await response.blob());
          const a=document.createElement("a");a.href=url;a.download=`${s.kind}_${row.id}_${format}.${{word:"docx",excel:"xlsx",pdf:"pdf",presentation:"pdf",complete:"pdf"}[format]}`;a.click();setTimeout(()=>URL.revokeObjectURL(url),30000);
        });
      };
    }
    await run(async()=>{
      s.boot=await api("/bootstrap");
      s.boot.types=Object.fromEntries(Object.entries(s.boot.types).filter(([k])=>options.kind ? k===options.kind : !['grain','condition','cargo_condition','logistics','port_captancy','crane','bunker'].includes(k)));
      if(alive())await list();
    });
  }
  window.SOMCertificates={mount,canLeave,destroy};
})();

window.SOMPortAttachments=(form,options)=>{
  const box=document.createElement('details');box.className='cert-section';
  box.innerHTML='<summary>PDF annexes</summary><div class="cert-tools"><input type="file" accept="application/pdf,.pdf" multiple aria-label="PDF annexes"><button type="button" disabled>Download report with annexes</button></div><ol></ol>';
  form.append(box);let files=[];
  const input=box.querySelector('input'),download=box.querySelector('button'),list=box.querySelector('ol');
  function show(){
    list.replaceChildren();download.disabled=!files.length;
    files.forEach((file,i)=>{const li=document.createElement('li'),name=document.createElement('span');name.textContent=file.name;name.style.overflowWrap='anywhere';li.append(name);
      for(const [label,symbol,action,disabled] of [
        ['Move up','\u2191',()=>{[files[i-1],files[i]]=[files[i],files[i-1]];show();},i===0],
        ['Move down','\u2193',()=>{[files[i+1],files[i]]=[files[i],files[i+1]];show();},i===files.length-1],
        ['Remove','\u2212',()=>{files.splice(i,1);show();},false]]){
        const b=document.createElement('button');b.type='button';b.textContent=symbol;b.title=label;b.setAttribute('aria-label',label);b.disabled=disabled;b.onclick=action;li.append(b);
      }list.append(li);
    });
  }
  input.onchange=()=>{files.push(...input.files);input.value='';show();};
  download.onclick=()=>options.run(async()=>{
    if(options.dirty())throw Error('Save changes before downloading.');
    if(files.length>10||files.some(f=>f.size>20*1024*1024)||files.reduce((n,f)=>n+f.size,0)>40*1024*1024)throw Error('Maximum 10 PDFs, 20 MB per file, 40 MB total.');
    const body=new FormData();files.forEach(file=>body.append('files',file));
    const headers={...options.headers()};for(const k of Object.keys(headers))if(k.toLowerCase()==='content-type')delete headers[k];
    const requestUrl=options.getLanguage?`${options.url}?language=${encodeURIComponent(options.getLanguage())}`:options.url;
    const response=await fetch(requestUrl,{method:'POST',headers,body,signal:options.signal});
    if(!response.ok){const data=await response.json().catch(()=>null);throw Error(data?.detail||'Could not assemble PDF.');}
    const url=URL.createObjectURL(await response.blob()),a=document.createElement('a');a.href=url;a.download=options.filename||'Port_Captancy_complete.pdf';a.click();setTimeout(()=>URL.revokeObjectURL(url),30000);
  });
};

window.SOMLogisticsAssist=(input,options)=>{
  const tools=document.createElement('div');tools.className='cert-tools';
  tools.innerHTML='<select aria-label="PORTIA language"><option value="EN">English</option><option value="ES">Espa\u00f1ol</option></select><button type="button">PORTIA</button><div class="cert-ai-result" hidden></div>';
  input.after(tools);
  if(options.getLanguage)tools.querySelector('select').value=options.getLanguage();
  tools.querySelector('select').onchange=()=>options.onLanguageChange?.(tools.querySelector('select').value);
  tools.querySelector('button').onclick=()=>options.run(async()=>{
    const original=input.value;
    if(!original.trim()||original.length>6000)throw Error('PORTIA requires between 1 and 6000 characters.');
    const language=tools.querySelector('select').value;
    const result=await options.request({text:original,language});
    if(!options.alive()||!input.isConnected)return;
    const panel=tools.querySelector('div');panel.hidden=false;
    panel.innerHTML='<label>PORTIA proposal<textarea readonly></textarea></label><button type="button" data-accept>Accept</button><button type="button" data-discard>Discard</button>';
    panel.querySelector('textarea').value=result.text;
    panel.querySelector('[data-accept]').onclick=()=>{
      if(input.value!==original&&!confirm('The original text changed. Replace it with this proposal?'))return;
      input.value=result.text;options.onLanguageChange?.(language);options.mark();panel.hidden=true;
    };
    panel.querySelector('[data-discard]').onclick=()=>panel.hidden=true;
  });
};
