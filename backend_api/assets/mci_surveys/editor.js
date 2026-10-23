(() => {
  let active;
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const fields={title:'Titulo',location:'Lugar',imo:'IMO',length_and_tonnage:'Eslora y tonelaje',cargo:'Carga',period_start:'Inicio del periodo',period_end:'Fin del periodo',issue_date:'Fecha de emision',report_status:'Estado impreso',master:'Capitan',chief_officer:'Primer oficial',surveyor:'Surveyor / firmante'};
  function canLeave(){return !active || (!active.busy && (!active.dirty || confirm('Hay cambios sin guardar. Descartarlos?')));}
  function destroy(){if(active){active.abort.abort();window.removeEventListener('beforeunload',active.unload);active=null;}}
  async function mount(root,opts){
    destroy(); const s=active={dirty:false,busy:false,abort:new AbortController(),offset:0,q:''};
    s.unload=e=>{if(s.dirty||s.busy){e.preventDefault();e.returnValue='';}};window.addEventListener('beforeunload',s.unload);
    const $=q=>root.querySelector(q),live=()=>active===s;
    root.classList.add('som-certificates');
    async function fetchBounded(path,options={},timeout=45000){
      const controller=new AbortController();let expired=false;
      const cancel=()=>controller.abort();s.abort.signal.addEventListener('abort',cancel,{once:true});
      const timer=setTimeout(()=>{expired=true;controller.abort();},timeout);
      try{return await fetch(path,{...options,signal:controller.signal});}
      catch(e){if(expired)throw Error('La solicitud tardo demasiado. Su texto sigue aqui. Compruebe el informe antes de volver a guardar.');throw e;}
      finally{clearTimeout(timer);s.abort.signal.removeEventListener('abort',cancel);}
    }
    async function request(path,method='GET',body){
      const r=await fetchBounded(path,{method,headers:{...opts.headers(),'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});
      const d=await r.json().catch(()=>null);if(!r.ok)throw Error(typeof d?.detail==='string'?d.detail:'No se pudo completar la solicitud. Revise los campos.');return d;
    }
    async function run(fn){if(s.busy)return;s.busy=true;root.inert=true;try{await fn();}catch(e){if(live()&&e.name!=='AbortError')$('#mci-error').textContent=e.message;}finally{s.busy=false;root.inert=false;}}
    function shell(mode,body){
      if(!live())return;
      root.innerHTML=`<header class="cert-head"><h2>${esc({vessel:'Vessel Survey',condition:'Vessel Condition Survey',cargo:'Cargo Condition Survey'}[opts.kind])}</h2><span>MCI-CR</span></header><nav class="cert-workflows">${s.boot?.permissions.create?`<button data-create aria-pressed="${mode==='create'}">Crear</button>`:''}<button data-review aria-pressed="${mode==='review'}">Revisar</button></nav><p id="mci-error" role="alert"></p>${body}`;
      if(s.boot && !s.boot.ready){root.querySelectorAll('nav button').forEach(b=>b.disabled=true);return;}
      if($('[data-create]'))$('[data-create]').onclick=()=>{if(canLeave()){s.dirty=false;run(()=>services());}};
      $('[data-review]').onclick=()=>{if(canLeave()){s.dirty=false;run(list);}};
    }
    async function list(){
      const d=await request(`/informes/mci-surveys?kind=${opts.kind}&q=${encodeURIComponent(s.q)}&offset=${s.offset}`);if(!live())return;
      shell('review',`<form class="cert-tools" id="mci-search"><input name="q" aria-label="Buscar informe" placeholder="Informe, buque o cliente" value="${esc(s.q)}"><button>Buscar</button></form><div class="cert-scroll"><table><thead><tr><th>Informe</th><th>Buque</th><th>Cliente</th><th>Estado</th><th></th></tr></thead><tbody>${d.data.map(r=>`<tr><td>${esc(r.report_number)}</td><td>${esc(r.vessel)}</td><td>${esc(r.requested_by)}</td><td>${esc(r.status)}</td><td><button data-open="${r.id}">Revisar informe</button></td></tr>`).join('')||'<tr><td colspan="5">Sin informes</td></tr>'}</tbody></table></div><button data-prev ${!s.offset?'disabled':''}>Anterior</button><button data-next ${!d.more?'disabled':''}>Siguiente</button>`);
      $('#mci-search').onsubmit=e=>{e.preventDefault();s.q=new FormData(e.target).get('q');s.offset=0;run(list);};
      $('[data-prev]').onclick=()=>{s.offset=Math.max(0,s.offset-50);run(list);};$('[data-next]').onclick=()=>{s.offset+=50;run(list);};
      root.querySelectorAll('[data-open]').forEach(b=>b.onclick=()=>run(async()=>editor(await request('/informes/mci-surveys/'+b.dataset.open))));
    }
    async function services(q='',offset=0){
      const d=await request(`/informes/certificates/services?q=${encodeURIComponent(q)}&offset=${offset}`);if(!live())return;
      shell('create',`<form class="cert-tools" id="mci-service-search"><input name="q" placeholder="Buscar servicio" aria-label="Buscar servicio" value="${esc(q)}"><button>Buscar</button></form><div class="cert-scroll"><table><tbody>${d.data.map((r,i)=>`<tr><td>${esc(r.num_informe)}</td><td>${esc(r.buque_contenedor)}</td><td>${esc(r.cliente)}</td><td><button data-service="${i}">Crear informe</button></td></tr>`).join('')||'<tr><td>Sin servicios</td></tr>'}</tbody></table></div><button data-prev ${!offset?'disabled':''}>Anterior</button><button data-next ${!d.more?'disabled':''}>Siguiente</button>`);
      $('#mci-service-search').onsubmit=e=>{e.preventDefault();run(()=>services(new FormData(e.target).get('q')));};
      $('[data-prev]').onclick=()=>run(()=>services(q,Math.max(0,offset-50)));$('[data-next]').onclick=()=>run(()=>services(q,offset+50));
      root.querySelectorAll('[data-service]').forEach(b=>b.onclick=()=>{const v=d.data[+b.dataset.service];editor({data:{service_id:v.consec,kind:opts.kind,report_number:v.num_informe,vessel:v.buque_contenedor,requested_by:v.cliente,content:{sections:{}}}});s.dirty=true;});
    }
    function editor(payload){
      if(!live())return;const row=payload.data,c=structuredClone(row.content),editable=row.id?s.boot.permissions.edit&&row.status!=='Approved':s.boot.permissions.create;
      c.sections ||= {};
      shell(row.id?'review':'create',`<p><strong>${esc(row.report_number)}</strong> · ${esc(row.vessel)} · ${esc(row.requested_by)}</p><form id="mci-form"><div class="cert-tools">${editable?'<button type="submit">Guardar borrador</button><button type="button" data-submit>Enviar a revision</button>':''}${row.id?'<button type="button" data-export="word">Word</button><button type="button" data-export="pdf">PDF</button>':''}${row.id&&s.boot.permissions.approve?'<button type="button" data-status="Approved">Aprobar</button><button type="button" data-status="Rejected">Rechazar</button>':''}<span id="mci-save-state" role="status"></span></div><fieldset ${!editable?'disabled':''}><div class="cert-fields">${Object.entries(fields).map(([k,label])=>`<label>${label}<input name="${k}" type="${k==='issue_date'?'date':k.startsWith('period_')?'datetime-local':'text'}" value="${esc(c[k]||'')}" maxlength="${k==='cargo'?3000:1000}"></label>`).join('')}</div><div id="mci-sections"></div></fieldset></form>`);
      const mark=()=>{s.dirty=true;$('#mci-save-state').textContent='Cambios sin guardar';};
      function sections(){
        const entries=Object.entries(s.boot.sections);
        $('#mci-sections').innerHTML=`<h3>Secciones del informe</h3><div class="mci-section-options">${entries.map(([k,label])=>`<label class="mci-section-option"><input type="checkbox" data-enable="${k}" ${c.sections[k]?.enabled?'checked':''}><span>${esc(label)}</span></label>`).join('')}</div><div class="mci-section-editors">${entries.filter(([k])=>c.sections[k]?.enabled).map(([k,label])=>{const sec=c.sections[k];return `<section class="mci-text-section"><header><h3>${esc(label)}</h3><button type="button" data-add="${k}" title="Agregar texto" aria-label="Agregar texto a ${esc(label)}" ${sec.blocks.length>=100?'disabled':''}>+</button></header>${sec.blocks.map((b,i)=>`<div class="mci-text-block"><label>Texto ${i+1}<textarea data-block="${k}" data-index="${i}" maxlength="30000">${esc(b.text)}</textarea></label><button type="button" data-remove="${k}" data-index="${i}" title="Eliminar texto" aria-label="Eliminar texto ${i+1}">&#8722;</button></div>`).join('')}</section>`;}).join('')}</div>`;
        root.querySelectorAll('[data-enable]').forEach(b=>b.onchange=()=>{const sec=c.sections[b.dataset.enable] ||= {enabled:false,blocks:[]};sec.enabled=b.checked;if(sec.enabled&&!sec.blocks.length)sec.blocks.push({text:''});mark();sections();});
        root.querySelectorAll('[data-block]').forEach(t=>t.oninput=()=>{c.sections[t.dataset.block].blocks[+t.dataset.index].text=t.value;mark();});
        root.querySelectorAll('[data-add]').forEach(b=>b.onclick=()=>{c.sections[b.dataset.add].blocks.push({text:''});mark();sections();});
        root.querySelectorAll('[data-remove]').forEach(b=>b.onclick=()=>{const a=c.sections[b.dataset.remove].blocks,i=+b.dataset.index;if(a[i].text.trim()&&!confirm('Eliminar este texto?'))return;a.splice(i,1);mark();sections();});
      }
      sections();root.querySelectorAll('#mci-form input[name]').forEach(el=>el.oninput=()=>{c[el.name]=el.value||(['issue_date','period_start','period_end'].includes(el.name)?null:'');mark();});
      async function save(submit){if(!editable)return;await run(async()=>{const d=await request('/informes/mci-surveys'+(row.id?'/'+row.id:''),row.id?'PATCH':'POST',{kind:opts.kind,service_id:row.service_id,content:c,version:payload.version,submit});if(live()){s.dirty=false;editor(d);$('#mci-save-state').textContent='Guardado';}});}
      $('#mci-form').onsubmit=e=>{e.preventDefault();save(false);};if($('[data-submit]'))$('[data-submit]').onclick=()=>save(true);
      root.querySelectorAll('[data-status]').forEach(b=>b.onclick=()=>{if(s.dirty){$('#mci-error').textContent='Guarde los cambios antes de revisar.';return;}if(!confirm('Confirmar cambio de estado?'))return;run(async()=>editor(await request(`/informes/mci-surveys/${row.id}/status`,'POST',{version:payload.version,status:b.dataset.status})));});
      root.querySelectorAll('[data-export]').forEach(b=>b.onclick=()=>{if(s.dirty){$('#mci-error').textContent='Guarde los cambios antes de descargar.';return;}run(async()=>{const r=await fetch(`/informes/mci-surveys/${row.id}/export/${b.dataset.export}`,{headers:opts.headers(),signal:s.abort.signal});if(!r.ok)throw Error('No se pudo generar el documento. El informe guardado no ha cambiado.');const url=URL.createObjectURL(await r.blob()),a=document.createElement('a');a.href=url;a.download=`Survey_${row.id}.${b.dataset.export==='word'?'docx':'pdf'}`;a.click();setTimeout(()=>URL.revokeObjectURL(url),30000);});});
    }
    shell('review','');await run(async()=>{s.boot=await request('/informes/mci-surveys/bootstrap');if(!s.boot.ready){shell('review','<p>Este modulo esta pendiente de habilitacion.</p>');return;}await list();});
  }
  window.SOMMCISurveys={mount,canLeave,destroy};
})();
