(function () {
  'use strict';
  const fields = ['number','date','entry','exit','spc','company','ticket','guide','seal','plate','stowage','notes'];
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const plateKey = value => String(value || '').replace(/[\s-]+/g, '').toUpperCase();
  function pasteValue(field,value) {
    value=String(value ?? '').trim();
    if(field==='date') {const m=value.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);if(m)value=`${m[3]}-${m[2].padStart(2,'0')}-${m[1].padStart(2,'0')}`;}
    if(field==='entry'||field==='exit') {const m=value.match(/^(\d{1,2}):(\d{2})(?::\d{2})?\s*(AM|PM)?$/i);if(m){let h=Number(m[1]);if(m[3])h=h%12+(m[3].toUpperCase()==='PM'?12:0);value=`${String(h).padStart(2,'0')}:${m[2]}`;}}
    return value;
  }
  const blank = () => ({id:crypto.randomUUID(), ...Object.fromEntries(fields.map(f => [f,'']))});
  const payloadRows = data => data.filter(row => fields.some(f => row[f] !== '' && row[f] != null))
    .map(row => ({id:row.id, ...Object.fromEntries(fields.map(f => [f, row[f] ?? '']))}));
  let active = null;

  async function mount(root, api) {
    if (active) active.destroy();
    root.innerHTML = '<section class="tally-workspace"><h2>Tally Control</h2><div class="tally-toolbar"><div class="tally-actions"><select aria-label="Proyecto" id="tallyProject"><option value="">Seleccionar proyecto</option></select><button id="tallyNew" class="primary">Nuevo proyecto</button><button id="tallySettings">Bodegas</button></div><div class="tally-actions"><button id="tallyCatalog">Catalogos</button><button id="tallyHistory">Historial</button><button id="tallyExcel">Exportar Excel</button></div></div><div class="tally-actions"><button id="tallyAdd">Agregar 20 filas</button><button id="tallyDelete">Eliminar filas seleccionadas</button><button id="tallySave">Guardar</button><button id="tallyReload">Recargar</button><button id="tallyDraft" hidden>Descargar borrador</button><span id="tallyStatus" class="tally-status" role="status"></span></div><div class="tally-tabs" role="tablist" aria-label="Bodegas"></div><div class="tally-grid"></div><div class="tally-footer"></div></section>';
    const $ = selector => root.querySelector(selector);
    let boot, current, hold, grid, revision=0, generation=0, saved=0, timer, saving=null, destroyed=false, conflict=false, switching=false;
    const drafts = key => `som:tally:${api.user}:${api.company}:${key}`;
    const draftKey = () => drafts(`${current.id}:${hold}`);
    const status = (message, error=false) => { if(destroyed)return; $('#tallyStatus').textContent=message; $('#tallyStatus').classList.toggle('error',error); $('#tallyDraft').hidden=!error; };
    const fail = err => status(err.message || String(err),true);
    const wrap = fn => async (...args) => {try {await fn(...args);} catch(err){fail(err);}};
    const dirty = () => generation !== saved;
    const unload = e => {if(dirty()){e.preventDefault();e.returnValue='';}};
    window.addEventListener('beforeunload',unload);
    const controls = () => {
      if(!boot||destroyed)return;
      for (const id of ['tallySettings','tallyHistory','tallyExcel','tallyReload']) $('#'+id).disabled=!current||switching;
      for (const id of ['tallyAdd','tallyDelete','tallySave']) $('#'+id).disabled=!current || !boot.editable || conflict||switching;
      $('#tallyNew').disabled=!boot.editable||switching; $('#tallySettings').disabled=!current || !boot.editable||switching;
      $('#tallyProject').disabled=switching;$('#tallyCatalog').disabled=switching;
      $('.tally-grid').inert=switching;
    };
    function remember() {
      try {sessionStorage.setItem(draftKey(),JSON.stringify({revision,rows:payloadRows(grid.getData())}));}
      catch {status('Borrador sin respaldo local. Guarde antes de cerrar.',true);}
    }
    function changed() {
      if (!boot.editable || destroyed) return;
      generation++; remember(); status(conflict ? 'Conflicto: descargue su borrador antes de recargar.' : 'Cambios pendientes',conflict);
      clearTimeout(timer); if(!conflict) timer=setTimeout(()=>flush().catch(fail),900);
      $('.tally-footer').textContent=`${payloadRows(grid.getData()).length} registros · Bodega ${hold}`;
    }
    async function flush() {
      clearTimeout(timer);
      if(saving) return saving;
      if(!dirty()) return true;
      if(conflict) return false;
      saving=(async()=>{
        try {
          while(dirty()) {
            const snapshot=generation;
            status('Guardando...');
            const result=await api.sendJSON('PUT',`/tally/projects/${current.id}/sheets/${hold}`,{revision,rows:payloadRows(grid.getData())});
            revision=result.revision; saved=snapshot;
            if(dirty()) remember(); else sessionStorage.removeItem(draftKey());
          }
          status('Guardado'); return true;
        } catch(err) {
          if(/modifico|modificó|sobrescrib|cambio|cambió/i.test(err.message)) conflict=true;
          controls(); fail(err); return false;
        } finally {saving=null;}
      })();
      return saving;
    }
    function driver(plate) {return boot.drivers.find(d=>d.plate===plateKey(plate))?.driver || '';}
    function enrich(row) {return {...row,hold,driver:row.driver || driver(row.plate)};}
    let typingCell=false;
    function temporalEditor(cell,onRendered,success,cancel) {
      const field=cell.getField(),type=field==='date'?'date':'time';
      const editor=document.createElement('input');
      editor.type=typingCell?'text':type;editor.value=cell.getValue()||'';
      let finished=false;
      const commit=()=>{
        if(finished)return;finished=true;
        const value=pasteValue(field,editor.value),check=document.createElement('input');
        check.type=type;check.value=value;
        if(value&&check.value!==value){cancel();status(type==='date'?'Fecha invalida':'Hora invalida',true);return;}
        success(value);
      };
      editor.addEventListener('blur',commit);
      editor.addEventListener('keydown',event=>{
        if(event.key==='Enter'){event.preventDefault();commit();}
        if(event.key==='Escape'){finished=true;cancel();}
      });
      onRendered(()=>{editor.focus();if(editor.type==='text')editor.select();});
      return editor;
    }
    function startTyping(event) {
      if(!grid||!boot?.editable||conflict||switching||event.defaultPrevented||event.isComposing||event.ctrlKey||event.metaKey||event.altKey||event.key.length!==1)return;
      if(event.target.closest('input,textarea,select,[contenteditable="true"]'))return;
      const selected=$('.tabulator-cell.tabulator-range-only-cell-selected');
      const field=selected?.getAttribute('tabulator-field');
      if(!fields.includes(field))return;
      const cell=grid.getRanges()[0]?.getRows().find(row=>row.getElement().contains(selected))?.getCell(field);
      if(!cell)return;
      typingCell=true;
      try {cell.edit();} finally {typingCell=false;}
      const editor=cell.getElement().querySelector('input,textarea');
      if(!editor)return;
      event.preventDefault();event.stopPropagation();
      editor.value=event.key;
      editor.dispatchEvent(new Event('input',{bubbles:true}));
      editor.focus();editor.setSelectionRange?.(editor.value.length,editor.value.length);
    }
    $('.tally-grid').addEventListener('keydown',startTyping,true);
    async function renderGrid(rows) {
      if(grid)grid.destroy();
      const data=rows.map(enrich); for(let i=0;i<20;i++)data.push(enrich(blank()));
      const input=(title,field,width=115,extra={})=>({title,field,width,editor:boot.editable&&!conflict?'input':false,formatter:'plaintext',...extra});
      grid=new Tabulator($('.tally-grid'),{
        data,index:'id',height:'min(62vh,640px)',layout:'fitData',rowHeight:34,
        selectableRange:1,selectableRangeColumns:true,selectableRangeRows:true,
        editTriggerEvent:'dblclick',history:true,clipboard:true,
        clipboardCopyRowRange:'range',clipboardCopyConfig:{columnHeaders:false,rowHeaders:false},
        clipboardPasteParser:function(text){
          if(!boot.editable||conflict)return false;
          const range=grid.getRanges()[0];if(!range)return false;
          const cols=grid.getColumns().map(c=>c.getField()).filter(Boolean);
          const left=cols.indexOf(range.getColumns()[0].getField());
          const parsed=Papa.parse(text,{delimiter:'\t',skipEmptyLines:'greedy'});
          if(parsed.errors.length||parsed.data.length>5000){status('Pegado invalido o mayor a 5000 filas',true);return false;}
          return parsed.data.map(values=>Object.fromEntries(values.map((v,i)=>[cols[left+i],pasteValue(cols[left+i],v)]).filter(([f])=>fields.includes(f))));
        },clipboardPasteAction:boot.editable&&!conflict?function(rows){
          const ranges=grid.getRanges(); if(!ranges.length)return;
          const start=ranges[0].getRows()[0].getPosition()-1;
          const table=grid;
          (async()=>{
            const needed=start+rows.length-table.getRows().length;
            if(needed>0)await table.addData(Array.from({length:needed},()=>enrich(blank())),false);
            const targets=table.getRows().slice(start,start+rows.length);
            for(let i=0;i<rows.length;i++){const clean=rows[i];
              if(Object.hasOwn(clean,'plate')){clean.plate=plateKey(clean.plate);clean.driver=driver(clean.plate);}
              await targets[i].update(clean);
            }
            changed();
          })().catch(fail);return [];
        }:function(){return [];},
        rowHeader:{formatter:'rownum',width:45,frozen:true,headerSort:false,resizable:false},
        columnDefaults:{headerSort:false,resizable:true},
        columns:[input('No.','number',70),{title:'Bodega',field:'hold',width:82,cssClass:'tally-readonly',formatter:'plaintext'},
          input('Fecha','date',120,{editor:boot.editable&&!conflict?temporalEditor:false}),
          input('Entrada','entry',100,{editor:boot.editable&&!conflict?temporalEditor:false}),input('Salida','exit',100,{editor:boot.editable&&!conflict?temporalEditor:false}),
          input('SPC','spc',90),input('Empresa','company',155,{editor:boot.editable&&!conflict?'list':false,editorParams:{values:boot.companies,autocomplete:true,listOnEmpty:true}}),
          input('Ficha','ticket',95),input('Guia Surco','guide',115),input('Guia Sello','seal',105,{editor:boot.editable&&!conflict?'list':false,editorParams:{values:['','Si','No']}}),
          input('Placa','plate',120),{title:'Chofer',field:'driver',width:260,formatter:'plaintext',cssClass:'tally-readonly'},
          input('Consecutivo Estiba','stowage',170),input('Observacion','notes',280)]
      });
      grid.on('cellEdited',cell=>{if(cell.getField()==='plate'){const key=plateKey(cell.getValue());cell.getRow().update({plate:key,driver:driver(key)});} changed();});
      grid.on('historyUndo',()=>changed()); grid.on('historyRedo',()=>changed());
      await new Promise(resolve=>grid.on('tableBuilt',resolve));
      $('.tally-footer').textContent=`${rows.length} registros · Bodega ${hold}`;
    }
    async function openSheet(next, nextProject=current) {
      if(switching)return;
      switching=true;controls();
      try {
      if(!await flush())return;
      const result=await api.getJSON(`/tally/projects/${nextProject.id}/sheets/${next}`);
      if(destroyed)return;
      current=nextProject;$('#tallyProject').value=current.id;
      hold=next; revision=result.revision; generation=saved=0; conflict=false;
      let rows=result.rows;
      try {const draft=JSON.parse(sessionStorage.getItem(draftKey())||'null');if(draft){rows=draft.rows;generation=1;conflict=draft.revision!==revision;}} catch{}
      $('.tally-tabs').innerHTML=current.holds.map(n=>`<button role="tab" aria-selected="${n===hold}" data-hold="${n}">Bodega ${n}</button>`).join('');
      $('.tally-tabs').querySelectorAll('button').forEach(btn=>btn.onclick=wrap(()=>openSheet(Number(btn.dataset.hold))));
      await renderGrid(rows); controls(); status(conflict?'Borrador recuperado con conflicto. Descarguelo antes de recargar.':dirty()?'Borrador recuperado; pendiente de guardar':'Guardado',conflict);
      if(dirty()&&!conflict)await flush();
      } finally {switching=false;controls();if(current)$('#tallyProject').value=current.id;}
    }
    async function refreshBootstrap() {boot=await api.getJSON('/tally/bootstrap');}
    function projectOptions() {$('#tallyProject').innerHTML='<option value="">Seleccionar proyecto</option>'+boot.projects.map(p=>`<option value="${p.id}">${esc(p.name)}</option>`).join(''); if(current)$('#tallyProject').value=current.id;}
    async function chooseProject(id) {
      if(!await flush()){$('#tallyProject').value=current?.id||'';return;}
      if(!id){$('#tallyProject').value=current?.id||'';return;}
      const nextProject=boot.projects.find(p=>p.id===Number(id));
      await openSheet(nextProject.holds[0],nextProject);
    }
    function dialog(title,content) {
      const el=document.createElement('dialog');el.className='tally-dialog';
      el.innerHTML=`<h2>${esc(title)}</h2>${content}<p class="error" role="alert"></p><div class="tally-actions"><button data-close>Cerrar</button></div>`;
      el.querySelector('[data-close]').onclick=()=>el.close();el.addEventListener('close',()=>el.remove());document.body.append(el);el.showModal();return el;
    }
    async function projectDialog(edit=false) {
      if(!await flush())return;
      const p=edit?current:null;
      const d=dialog(edit?'Configurar proyecto':'Nuevo proyecto',`<form><label>Nombre del proyecto<input name="name" maxlength="150" required value="${esc(p?.name)}"></label><label>Buscar servicio<input name="search" type="search"></label><label>Servicio<select name="service"><option value="">Sin vincular</option></select></label><label>Numeros de bodegas<input name="holds" required value="${esc(p?.holds.join(', ')||'1, 3, 5')}" placeholder="1, 3, 5"></label><button class="primary" type="submit">${edit?'Guardar':'Crear proyecto'}</button></form>`);
      const f=d.querySelector('form'); const serviceOptions=items=>{f.elements.service.innerHTML='<option value="">Sin vincular</option>'+items.map(s=>`<option value="${s.consec}">${s.consec} · ${esc(s.buque_contenedor)} · ${esc(s.cliente)}</option>`).join('');if(p?.service_id){if(!items.some(s=>s.consec===p.service_id))f.elements.service.add(new Option(`Servicio ${p.service_id}`,p.service_id));f.elements.service.value=p.service_id;}};
      serviceOptions(boot.services);
      let searchTimer;f.elements.search.oninput=()=>{clearTimeout(searchTimer);searchTimer=setTimeout(async()=>{try{const data=await api.getJSON('/tally/bootstrap?q='+encodeURIComponent(f.elements.search.value));if(d.isConnected)serviceOptions(data.services);}catch(e){d.querySelector('[role=alert]').textContent=e.message;}},350);};
      f.onsubmit=async e=>{e.preventDefault();const btn=f.querySelector('button');btn.disabled=true;try{
        const parts=f.elements.holds.value.split(/[,;\s]+/).filter(Boolean);if(!parts.length||parts.some(x=>!/^\d+$/.test(x)))throw Error('Indique numeros de bodega separados por comas.');
        const body={name:f.elements.name.value,holds:parts.map(Number),service_id:Number(f.elements.service.value)||null,revision:p?.revision||0};
        const result=edit?await api.sendJSON('PUT',`/tally/projects/${p.id}`,body):await api.postJSON('/tally/projects',body);
        await refreshBootstrap();projectOptions();d.close();$('#tallyProject').value=result.id;await chooseProject(result.id);
      }catch(err){d.querySelector('[role=alert]').textContent=err.message;}finally{btn.disabled=false;}};
    }
    async function catalogDialog() {
      if(!await flush())return;
      const d=dialog('Catalogos',`<form id="driverForm"><label>Placa<input name="plate" maxlength="30" required list="tallyPlates"></label><datalist id="tallyPlates">${boot.drivers.map(x=>`<option value="${esc(x.plate)}">${esc(x.driver)}</option>`).join('')}</datalist><label>Chofer<input name="driver" maxlength="150" required></label><button type="submit">Guardar chofer</button></form><hr><form id="companyForm"><label>Empresa<input name="name" maxlength="100" required></label><button type="submit">Agregar empresa</button></form><p>${boot.companies.map(esc).join(', ')||'Sin empresas'}</p><hr><label>Importar catalogo desde Excel<input id="catalogFile" type="file" accept=".xlsx"></label><button id="catalogImport">Importar hoja Choferes</button><p>${boot.drivers.length} placas registradas</p>`);
      const df=d.querySelector('#driverForm');df.elements.plate.oninput=()=>{df.elements.driver.value=driver(df.elements.plate.value);};
      const action=fn=>async e=>{e.preventDefault();try{await fn();await refreshBootstrap();d.close();if(current)await openSheet(hold);}catch(err){d.querySelector('[role=alert]').textContent=err.message;}};
      df.onsubmit=action(()=>api.sendJSON('PUT','/tally/drivers',{plate:df.elements.plate.value,driver:df.elements.driver.value}));
      const cf=d.querySelector('#companyForm');cf.onsubmit=action(()=>api.postJSON('/tally/companies',{name:cf.elements.name.value}));
      d.querySelector('#catalogImport').onclick=action(async()=>{
        const file=d.querySelector('#catalogFile').files[0];if(!file)throw Error('Seleccione el archivo Excel.');
        const form=new FormData();form.append('file',file);const h=api.headers();delete h['Content-Type'];
        const resp=await fetch('/tally/catalog/import',{method:'POST',headers:h,body:form});const data=await resp.json();if(!resp.ok)throw Error(typeof data.detail==='string'?data.detail:'No se pudo importar');
      });
      if(!boot.editable)d.querySelectorAll('input,button[type=submit],#catalogImport').forEach(x=>x.disabled=true);
    }
    function download(blob,name) {const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
    $('#tallyProject').onchange=wrap(e=>chooseProject(e.target.value));
    $('#tallyNew').onclick=wrap(()=>projectDialog());$('#tallySettings').onclick=wrap(()=>projectDialog(true));$('#tallyCatalog').onclick=wrap(catalogDialog);
    $('#tallyAdd').onclick=wrap(async()=>{await grid.addData(Array.from({length:20},()=>enrich(blank())),false);grid.scrollToRow(grid.getRows().at(-1),'bottom',false);});
    $('#tallyDelete').onclick=wrap(async()=>{const rows=[...new Set(grid.getRanges().flatMap(r=>r.getRows()))];if(rows.length&&confirm(`Eliminar ${rows.length} filas?`)){await grid.deleteRow(rows.map(r=>r.getIndex()));changed();}});
    $('#tallySave').onclick=wrap(flush);
    $('#tallyReload').onclick=wrap(async()=>{if(dirty()&&!confirm('Descartar el borrador local y cargar lo guardado?'))return;sessionStorage.removeItem(draftKey());generation=saved=0;conflict=false;await openSheet(hold);});
    $('#tallyDraft').onclick=()=>download(new Blob([JSON.stringify({project:current,hold,revision,rows:payloadRows(grid.getData())},null,2)],{type:'application/json'}),`Tally-${current.id}-bodega-${hold}-borrador.json`);
    $('#tallyExcel').onclick=wrap(async()=>{if(!await flush())return;const resp=await fetch(`/tally/projects/${current.id}/excel`,{headers:api.headers()});if(!resp.ok)throw Error('No se pudo exportar');download(await resp.blob(),`Tally-${current.id}.xlsx`);});
    $('#tallyHistory').onclick=wrap(async()=>{const rows=await api.getJSON(`/tally/projects/${current.id}/history`);dialog('Historial',`<table><thead><tr><th>Fecha</th><th>Usuario</th><th>Bodega</th><th>Version</th></tr></thead><tbody>${rows.map(r=>`<tr><td>${esc(new Date(r.created_at).toLocaleString())}</td><td>${esc(r.performed_by)}</td><td>${r.hold??'Proyecto'}</td><td>${r.revision??'-'}</td></tr>`).join('')}</tbody></table>`);});
    active={destroy(){destroyed=true;clearTimeout(timer);window.removeEventListener('beforeunload',unload);$('.tally-grid').removeEventListener('keydown',startTyping,true);if(grid)grid.destroy();},canLeave(){return !dirty()||confirm('Hay cambios pendientes. El borrador se conservara en esta pestana. Salir?');}};
    try {await refreshBootstrap();if(destroyed)return;projectOptions();controls();if(boot.projects.length){$('#tallyProject').value=boot.projects[0].id;await chooseProject(boot.projects[0].id);}else{$('.tally-footer').textContent='Sin proyectos';}}
    catch(err){fail(err);}
  }
  window.SOMTally={mount,canLeave:()=>!active||active.canLeave(),destroy:()=>{active?.destroy();active=null;},plateKey,payloadRows,pasteValue};
})();
