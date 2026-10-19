/* Shared LOGRA workspace. All writes use the isolated version-checked web API. */
(() => {
  'use strict';
  const base = '/informes/logra';
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const key = a => [a.form_slug,a.section,a.item_key].join('|');
  const clone = v => JSON.parse(JSON.stringify(v));
  const date = v => String(v || '').slice(0,10).replace(/^(\d{4})-(\d{2})-(\d{2})$/, '$3/$2/$1');
  const icon = name => `<img alt="" width="20" height="20" src="/som/queue-icon/${name}.svg">`;
  let active;
  async function mount(root, api) {
    active?.destroy();
    root.classList.add('som-logra');
    let boot, current, original, answers = {}, meetings = [], notes = '', seq = 0, dirty = false, busy = false, saving = false, conflict = false, disposed = false;
    let page = 0, group = '', view = 'questions', listOffset = 0, listQuery = '', listKind = 'questionnaire', listRows = [], selected = new Set(), saveTimer, navigation = 0;
    let month = new Date().toISOString().slice(0,7), calendar = false;
    const controllers = new Set();
    const $ = s => root.querySelector(s);
    root.innerHTML = `<header class="lw-header"><div class="lw-title">${icon('file-pen-line')}<div><h2>LOGRA</h2><span>Compartido · MCI y MSL</span></div></div><button data-act="new" type="button">Nuevo cuestionario</button></header><p class="lw-message" role="status" hidden></p><main class="lw-main"></main>`;
    function message(text='', error=false) { if(disposed)return; const n=$('.lw-message'); n.textContent=text;n.hidden=!text;n.classList.toggle('lw-error',error); }
    const fail = error => { if(!disposed) message(error.message || 'No se pudo completar la solicitud',true); };
    const run = fn => async e => { try {await fn(e);} catch(error){fail(error);} };
    function bind(name, fn) { root.querySelectorAll(`[data-act="${name}"]`).forEach(n=>n.onclick=run(fn)); }
    async function request(path, method='GET', body, binary=false) {
      const controller=new AbortController(); controllers.add(controller);
      const timer=setTimeout(()=>controller.abort(),180000), headers=new Headers(api.headers());
      if(body instanceof FormData) headers.delete('Content-Type');
      try {
        const response=await fetch(base+path,{method,headers,signal:controller.signal,body:body===undefined?undefined:body instanceof FormData?body:JSON.stringify(body)});
        if(!response.ok) {
          let detail;try{detail=(await response.json()).detail;}catch(_){}
          const error=Error(typeof detail==='string'?detail:`No se pudo completar la solicitud (${response.status}). El borrador se conserva.`);error.status=response.status;throw error;
        }
        return binary?response.blob():response.json();
      } catch(error) {if(error.name==='AbortError')throw Error('La solicitud tardo demasiado. Verifica el resultado antes de repetirla.');throw error;}
      finally{clearTimeout(timer);controllers.delete(controller);}
    }
    function download(blob,name){const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),30000);}
    function cacheKey(){return `som-logra:${api.user}:${current.report.id}`;}
    function cache(){if(!current)return;try{localStorage.setItem(cacheKey(),JSON.stringify({revision:current.revision,answers,meetings,notes,at:Date.now()}));}catch(_){message('No hay espacio para el respaldo local. Guarda o descarga el borrador.',true);}}
    function changed(){dirty=true;seq++;cache();clearTimeout(saveTimer);if(!conflict&&navigator.onLine)saveTimer=setTimeout(()=>save().catch(fail),2000);}
    function finishBusy(){busy=false;if(dirty&&!conflict&&!disposed){clearTimeout(saveTimer);saveTimer=setTimeout(()=>save().catch(fail),2000);}}
    function canLeave(){if(busy||saving){message('Espera a que termine la operacion.',true);return false;}return !dirty||confirm('Hay cambios pendientes de guardar en LOGRA. Salir conservando el borrador local?');}
    function unload(e){if(dirty||busy||saving){e.preventDefault();e.returnValue='';}}
    function online(){if(dirty&&!conflict)save().catch(fail);}
    window.addEventListener('beforeunload',unload);window.addEventListener('online',online);
    active={canLeave,destroy(){disposed=true;clearTimeout(saveTimer);controllers.forEach(c=>c.abort());window.removeEventListener('beforeunload',unload);window.removeEventListener('online',online);root.classList.remove('som-logra');root.querySelectorAll('dialog').forEach(d=>d.close());}};
    function modal(title,html){const d=document.createElement('dialog');d.className='lw-dialog';d.innerHTML=`<header><h3>${esc(title)}</h3><button type="button" aria-label="Cerrar">×</button></header>${html}`;root.append(d);d.querySelector('header button').onclick=()=>d.close();d.onclose=()=>d.remove();d.showModal();return d;}
    async function list(){
      if(disposed)return;
      clearTimeout(saveTimer);current=null;dirty=false;conflict=false;message();
      const requestNumber=++navigation;
      const result=await request(`?kind=${listKind}&q=${encodeURIComponent(listQuery)}&offset=${listOffset}`);if(disposed||requestNumber!==navigation)return;
      listRows=result.data;selected.clear();
      $('.lw-main').innerHTML=`<nav class="lw-tabs"><button data-act="reports" aria-selected="${listKind==='questionnaire'}">Cuestionarios</button><button data-act="agendas" aria-selected="${listKind==='agenda'}">Agenda</button></nav>
        <form class="lw-toolbar" data-search><label>Buscar<input name="q" value="${esc(listQuery)}" placeholder="Titulo o autor"></label><button type="submit">Buscar</button><button type="button" data-act="reload" aria-label="Recargar" title="Recargar">↻</button>
        ${listKind==='agenda'?'<button type="button" data-act="new-agenda">Nueva agenda</button>':'<label>Idioma IA<select data-language><option>ES</option><option>EN</option></select></label><button type="button" data-act="executive">Reporte ejecutivo IA</button>'}</form>
        <div class="lw-table-wrap"><table><thead><tr><th></th><th>Reporte</th><th>Estado</th><th>Respuestas</th><th>Agenda</th><th>Adjuntos</th><th>Autor</th><th>Actualizado</th><th></th></tr></thead><tbody>${listRows.map(r=>`<tr><td><input type="checkbox" data-select="${r.id}" aria-label="Seleccionar ${esc(r.title)}"></td><td>${esc(r.title)}</td><td><span class="lw-status">${esc(r.status)}</span></td><td>${r.answer_count}</td><td>${r.agenda_count}</td><td>${r.attachment_count}</td><td>${esc(r.created_by)}</td><td>${date(r.updated_at)}</td><td><button data-open="${r.id}">Abrir</button></td></tr>`).join('')||'<tr><td colspan="9">Sin reportes</td></tr>'}</tbody></table></div>
        <footer class="lw-footer"><span>${result.total} reportes</span><div><button data-act="prev-list" ${listOffset===0?'disabled':''} aria-label="Anterior">←</button><span>${Math.floor(listOffset/50)+1} / ${Math.max(1,Math.ceil(result.total/50))}</span><button data-act="next-list" ${listOffset+50>=result.total?'disabled':''} aria-label="Siguiente">→</button></div></footer>`;
      $('[data-search]').onsubmit=run(async e=>{e.preventDefault();listQuery=new FormData(e.target).get('q');listOffset=0;await list();});
      bind('reload',list);bind('reports',()=>{listKind='questionnaire';listOffset=0;return list();});bind('agendas',()=>{listKind='agenda';listOffset=0;return list();});
      bind('prev-list',()=>{listOffset-=50;return list();});bind('next-list',()=>{listOffset+=50;return list();});bind('new-agenda',()=>newReport('agenda'));
      root.querySelectorAll('[data-open]').forEach(n=>n.onclick=run(()=>open(Number(n.dataset.open))));
      root.querySelectorAll('[data-select]').forEach(n=>n.onchange=()=>n.checked?selected.add(Number(n.dataset.select)):selected.delete(Number(n.dataset.select)));
      bind('executive',executive);lockPermissions();
    }
    function lockPermissions(){const n=$('[data-act="new"]');if(n)n.disabled=!boot.permissions.create;const a=$('[data-act="new-agenda"]');if(a)a.disabled=!boot.permissions.create;}
    async function newReport(kind='questionnaire'){
      if(!canLeave()||!boot.permissions.create)return;
      const d=modal(kind==='agenda'?'Nueva agenda':'Nuevo cuestionario',`<form><label>Cuestionario<select name="slug" ${kind==='agenda'?'disabled':''}>${boot.forms.map(f=>`<option value="${esc(f.slug)}">${esc(f.title)}</option>`).join('')}</select></label><footer><button type="submit">Crear</button></footer><p role="status"></p></form>`);
      d.querySelector('form').onsubmit=async e=>{e.preventDefault();if(busy)return;busy=true;const b=d.querySelector('[type="submit"]');b.disabled=true;
        try{const result=await request('','POST',{kind,form_slug:kind==='agenda'?'':d.querySelector('select').value});d.close();adopt(result);render();}
        catch(error){d.querySelector('[role="status"]').textContent=error.message+' Recarga la lista antes de volver a crear para evitar duplicados.';}
        finally{finishBusy();}
      };
    }
    function adopt(result){current=result;original=clone(result);answers=Object.fromEntries(result.answers.map(a=>[key(a),clone(a)]));meetings=clone(result.report.agenda_items||[]);notes=result.report.agenda_notes||'';dirty=false;conflict=false;seq=0;page=0;group='';view=String(result.report.title).trim().toLowerCase()==='ong - agenda'?'agenda':'questions';}
    async function open(id){if(!canLeave())return;clearTimeout(saveTimer);const requestNumber=++navigation;const result=await request('/'+id);if(disposed||requestNumber!==navigation)return;adopt(result);message();
      try{const saved=JSON.parse(localStorage.getItem(cacheKey())||'null');if(saved&&boot.permissions.edit&&confirm('Existe un borrador local de este reporte. Recuperarlo?')){
        answers=saved.answers;meetings=saved.meetings;notes=saved.notes;dirty=true;seq++;conflict=saved.revision!==current.revision;
        current.revision=saved.revision;message(conflict?'El servidor cambio desde ese borrador. Descarga la copia local antes de recargar y combinar.':'Borrador recuperado. Pendiente de guardar.',conflict);
      }}catch(_){}render();
    }
    function groups(){const slugs=current.report.form_slug?[current.report.form_slug]:[...new Set(current.answers.map(a=>a.form_slug))];return boot.forms.filter(f=>slugs.includes(f.slug)).flatMap(f=>['critical_questions','detailed_questions'].map(section=>({id:f.slug+'|'+section,form:f,section,title:section==='critical_questions'?'Criticas':'Detalladas'})));}
    function questions(g){if(!g)return[];const rows=g.form[g.section].map(q=>({form_slug:g.form.slug,section:g.section,item_key:String(q.id||q.number),question_text:q.question,priority:q.priority,block:q.block}));
      const known=new Set(rows.map(key));current.answers.filter(a=>a.form_slug===g.form.slug&&a.section===g.section&&!known.has(key(a))).forEach(a=>rows.push(a));return rows;}
    function render(){if(disposed||!current)return;
      const gs=groups();if(!group&&gs.length)group=gs[0].id;
      $('.lw-main').innerHTML=`<div class="lw-editor-head"><button data-act="back" title="Volver a reportes" aria-label="Volver a reportes">←</button><div><h3>${esc(current.report.title)}</h3><span class="lw-status">${esc(current.report.status)} · v${current.report.version||1}</span></div><div class="lw-actions"><span data-save-state></span><button data-act="backup">Descargar borrador</button><button data-act="history">Historial</button><label>Exportar<select data-export><option value="">Formato</option><option value="docx">Word</option><option value="pdf">PDF</option><option value="xlsx">Excel</option></select></label><button data-act="save" class="lw-primary" ${!boot.permissions.edit?'disabled':''}>Guardar</button></div></div>
        <nav class="lw-tabs"><button data-act="questions" aria-selected="${view==='questions'}">Respuestas</button><button data-act="agenda" aria-selected="${view==='agenda'}">Agenda (${meetings.length})</button></nav><div class="lw-editor"></div>`;
      bind('back',()=>{if(canLeave())return list();});bind('save',()=>save(true));bind('backup',()=>download(new Blob([JSON.stringify({report:current.report,answers:Object.values(answers),agenda_items:meetings,agenda_notes:notes,revision:current.revision},null,2)],{type:'application/json'}),`LOGRA_${current.report.id}_borrador.json`));
      bind('history',history);bind('questions',()=>{view='questions';render();});bind('agenda',()=>{view='agenda';render();});
      $('[data-export]').onchange=run(async e=>{const kind=e.target.value;e.target.value='';if(!kind)return;if(dirty)throw Error('Guarda los cambios antes de exportar la version del servidor.');download(await request(`/${current.report.id}/export/${kind}`,'GET',undefined,true),`LOGRA_${current.report.id}.${kind}`);});
      if(view==='agenda')renderAgenda();else renderQuestions(gs);
      lockPermissions();saveState();
    }
    function saveState(){const n=$('[data-save-state]');if(n)n.textContent=saving?'Guardando...':dirty?conflict?'Conflicto pendiente':'Cambios pendientes':'Guardado';}
    function renderQuestions(gs){const g=gs.find(x=>x.id===group);const all=questions(g);page=Math.min(page,Math.max(0,Math.ceil(all.length/5)-1));
      $('.lw-editor').innerHTML=`<aside class="lw-sidebar">${gs.map(x=>`<button data-group="${esc(x.id)}" aria-current="${x.id===group}"><strong>${esc(x.form.title)}</strong><span>${x.title} · ${questions(x).filter(q=>(answers[key(q)]?.bullets||[]).some(v=>v.trim())).length}/${questions(x).length}</span></button>`).join('')}</aside><section class="lw-questions"><header class="lw-question-toolbar"><span>${all.length} preguntas</span><label>Idioma PORTIA<select data-ai-language><option>ES</option><option>EN</option></select></label></header>
        ${all.slice(page*5,page*5+5).map(q=>{const a=answers[key(q)], bullets=a?.bullets?.length?a.bullets:[''];return `<article class="lw-question" data-question="${esc(key(q))}"><div class="lw-question-meta">${esc(q.item_key)} ${q.priority?`· Prioridad ${esc(q.priority)}`:''} ${esc(q.block||'')}</div><h4>${esc(q.question_text)}</h4>${bullets.map((v,i)=>`<div class="lw-bullet"><textarea rows="3" data-bullet="${i}" aria-label="Respuesta ${esc(q.item_key)} ${i+1}" ${!boot.permissions.edit?'readonly':''}>${esc(v)}</textarea><div>${boot.permissions.edit?`<button data-ai="${i}" title="Mejorar con PORTIA" aria-label="Mejorar con PORTIA">${icon('file-pen-line')}</button><button data-remove-bullet="${i}" title="Quitar respuesta" aria-label="Quitar respuesta">−</button>`:''}</div></div>`).join('')}
        <footer>${boot.permissions.edit?'<button data-add-bullet title="Agregar respuesta" aria-label="Agregar respuesta">+</button><label class="lw-upload">Adjuntar<input type="file" data-upload accept=".pdf,.docx,.doc,.xlsx,.xls,.jpg,.jpeg,.png,.webp,.txt,.csv"></label>':''}<span>${current.attachments.filter(a=>key(a)===key(q)).length}/10 adjuntos</span></footer><div class="lw-attachments">${current.attachments.filter(a=>key(a)===key(q)).map(a=>`<div><button data-attachment="${a.id}">${esc(a.original_filename)}</button>${boot.permissions.edit?`<button data-remove-attachment="${a.id}" title="Quitar adjunto" aria-label="Quitar ${esc(a.original_filename)}">×</button>`:''}</div>`).join('')}</div></article>`;}).join('')||'<p>No hay preguntas asociadas a este reporte.</p>'}
        <footer class="lw-footer"><button data-act="prev-question" ${page===0?'disabled':''} aria-label="Preguntas anteriores">←</button><span>${page+1} / ${Math.max(1,Math.ceil(all.length/5))}</span><button data-act="next-question" ${(page+1)*5>=all.length?'disabled':''} aria-label="Preguntas siguientes">→</button></footer></section>`;
      root.querySelectorAll('[data-group]').forEach(n=>n.onclick=()=>{group=n.dataset.group;page=0;render();});
      bind('prev-question',()=>{page--;render();});bind('next-question',()=>{page++;render();});
      root.querySelectorAll('[data-question]').forEach(card=>{
        const q=all.find(x=>key(x)===card.dataset.question), k=key(q);
        const ensure=()=>answers[k]||(answers[k]={...q,bullets:['']});
        card.querySelectorAll('[data-bullet]').forEach(n=>n.oninput=()=>{ensure().bullets[Number(n.dataset.bullet)]=n.value;changed();saveState();});
        const add=card.querySelector('[data-add-bullet]');if(add)add.onclick=()=>{if(ensure().bullets.length>=20)return message('Maximo 20 respuestas por pregunta.',true);ensure().bullets.push('');changed();render();};
        card.querySelectorAll('[data-remove-bullet]').forEach(n=>n.onclick=()=>{if(!confirm('Quitar esta respuesta?'))return;ensure().bullets.splice(Number(n.dataset.removeBullet),1);changed();render();});
        card.querySelectorAll('[data-ai]').forEach(n=>n.onclick=run(()=>improve(q,Number(n.dataset.ai))));
        const upload=card.querySelector('[data-upload]');if(upload)upload.onchange=run(async()=>{const file=upload.files[0];if(!file)return;if(file.size>20*1024*1024)throw Error('Maximo 20 MB por archivo.');if(dirty)await save(true);if(dirty||saving)throw Error('Espera a que termine el guardado antes de adjuntar.');
          busy=true;try{const data=new FormData();data.set('revision',current.revision);data.set('form_slug',q.form_slug);data.set('section',q.section);data.set('item_key',q.item_key);data.set('file',file);
            const result=await request('/'+current.report.id+'/attachments','POST',data);current.revision=result.revision;current.attachments=result.attachments;current.report=result.report;original=result;render();
          }finally{finishBusy();}
        });
        card.querySelectorAll('[data-attachment]').forEach(n=>n.onclick=run(async()=>{const a=current.attachments.find(x=>String(x.id)===n.dataset.attachment);download(await request('/attachments/'+a.id,'GET',undefined,true),a.original_filename);}));
        card.querySelectorAll('[data-remove-attachment]').forEach(n=>n.onclick=run(async()=>{if(busy||!confirm('Quitar este adjunto del reporte?'))return;if(dirty)await save(true);if(dirty||saving)throw Error('Espera a que termine el guardado.');busy=true;
          try{const result=await request(`/${current.report.id}/attachments/${n.dataset.removeAttachment}`,'DELETE',{revision:current.revision});current.revision=result.revision;current.attachments=result.attachments;current.report=result.report;original=result;render();}finally{finishBusy();}
        }));
      });
    }
    function renderAgenda(){
      const editable=boot.permissions.edit;
      const fields=[['date_iso','Fecha','date'],['start_time','Inicio','time'],['end_time','Fin','time'],['place','Lugar','text'],['person','Persona','text'],['company','Empresa','text'],['phone','Telefono','tel'],['topic','Tema','text']];
      $('.lw-editor').innerHTML=`<section class="lw-agenda"><div class="lw-toolbar"><button data-act="calendar">${calendar?'Lista':'Calendario'}</button>${calendar?`<input type="month" data-month value="${month}" aria-label="Mes">`:''}<button data-act="add-meeting" ${!editable?'disabled':''}>Nueva reunion</button></div><div class="lw-agenda-content"></div><label>Notas generales<textarea data-notes rows="4" ${!editable?'readonly':''}>${esc(notes)}</textarea></label></section>`;
      if(calendar){const [year,m]=month.split('-').map(Number),days=new Date(year,m,0).getDate(),start=(new Date(year,m-1,1).getDay()+6)%7;
        $('.lw-agenda-content').innerHTML=`<div class="lw-calendar">${['Lun','Mar','Mie','Jue','Vie','Sab','Dom'].map(d=>`<strong>${d}</strong>`).join('')}${'<div></div>'.repeat(start)}${Array.from({length:days},(_,i)=>{const day=`${month}-${String(i+1).padStart(2,'0')}`;return `<div><strong>${i+1}</strong>${meetings.map((item,index)=>({item,index})).filter(x=>(x.item.date_iso||'')===day).map(x=>`<button data-meeting="${x.index}">${esc(x.item.start_time)} ${esc(x.item.topic||x.item.person||'Reunion')}</button>`).join('')}</div>`;}).join('')}</div>`;
        $('[data-month]').onchange=e=>{if(e.target.value){month=e.target.value;renderAgenda();}};
      }else $('.lw-agenda-content').innerHTML=`<div class="lw-table-wrap"><table><thead><tr><th>Fecha</th><th>Horario</th><th>Tema</th><th>Persona</th><th>Lugar</th><th>Prioridad</th><th>Estado</th><th></th></tr></thead><tbody>${meetings.map((m,i)=>`<tr><td>${esc(date(m.date_iso)||m.date||m.date_long)}</td><td>${esc(m.start_time)} - ${esc(m.end_time)}</td><td>${esc(m.topic)}</td><td>${esc(m.person)}</td><td>${esc(m.place)}</td><td>${esc(m.priority)}</td><td>${esc(m.status)}</td><td><button data-meeting="${i}">${editable?'Editar':'Ver'}</button></td></tr>`).join('')||'<tr><td colspan="8">Sin reuniones</td></tr>'}</tbody></table></div>`;
      bind('calendar',()=>{calendar=!calendar;renderAgenda();});$('[data-notes]').oninput=e=>{notes=e.target.value;changed();saveState();};
      function edit(index){if(index===null&&meetings.length>=150)return message('Maximo 150 reuniones por agenda.',true);const item=index===null?{}:meetings[index];
        const d=modal(index===null?'Nueva reunion':'Reunion',`<form><div class="lw-meeting-fields">${fields.map(([k,label,type])=>`<label>${label}<input name="${k}" type="${type}" value="${esc(item[k]||'')}" ${['date_iso','start_time','end_time','topic'].includes(k)?'required':''} ${!editable?'readonly':''}></label>`).join('')}<label>Prioridad<select name="priority" ${!editable?'disabled':''}>${['Alta','Media','Baja'].map(v=>`<option ${v===(item.priority||'Media')?'selected':''}>${v}</option>`).join('')}</select></label><label>Estado<select name="status" ${!editable?'disabled':''}>${['Pendiente','En proceso','Completado'].map(v=>`<option ${v===item.status?'selected':''}>${v}</option>`).join('')}</select></label></div><footer>${editable?'<button type="submit">Aplicar</button>':''}${editable&&index!==null?'<button type="button" data-delete-meeting>Eliminar reunion</button>':''}</footer></form>`);
        d.querySelector('form').onsubmit=e=>{e.preventDefault();if(!editable)return;const values=Object.fromEntries(new FormData(e.target));if(values.end_time<=values.start_time){message('La hora final debe ser posterior a la inicial.',true);return;}const updated={...item,...values,date:date(values.date_iso)};if(index===null)meetings.push(updated);else meetings[index]=updated;changed();d.close();render();};
        const del=d.querySelector('[data-delete-meeting]');if(del)del.onclick=()=>{if(confirm('Eliminar esta reunion de la agenda?')){meetings.splice(index,1);changed();d.close();render();}};
      }
      bind('add-meeting',()=>edit(null));root.querySelectorAll('[data-meeting]').forEach(n=>n.onclick=()=>edit(Number(n.dataset.meeting)));
    }
    async function save(manual=false){
      if(!current||!dirty||saving||busy||!boot.permissions.edit)return;
      if(conflict)throw Error('Hay un conflicto pendiente. Descarga el borrador antes de recargar.');
      clearTimeout(saveTimer);const captured=seq, id=current.report.id;
      const before=new Map(original.answers.map(a=>[key(a),a.bullets]));
      const body={revision:current.revision,answers:Object.values(answers).filter(a=>JSON.stringify(a.bullets)!==JSON.stringify(before.get(key(a))||[])).map(a=>({form_slug:a.form_slug,section:a.section,item_key:a.item_key,bullets:a.bullets}))};
      if(JSON.stringify(meetings)!==JSON.stringify(original.report.agenda_items||[]))body.agenda_items=clone(meetings);
      if(notes!==(original.report.agenda_notes||''))body.agenda_notes=notes;
      saving=true;saveState();
      try{const result=await request('/'+id,'PATCH',body);if(disposed)return;current.revision=result.revision;current.report=result.report;original=clone(result);dirty=seq!==captured;
        if(!dirty){localStorage.removeItem(cacheKey());message(manual?'Guardado correctamente.':'');}else cache();
      }catch(error){if(error.status===409)conflict=true;cache();throw error;}
      finally{saving=false;saveState();if(dirty&&!conflict&&seq!==captured&&!disposed)saveTimer=setTimeout(()=>save().catch(fail),2000);}
    }
    async function improve(q,index){if(busy)return;const text=answers[key(q)]?.bullets[index];if(!text?.trim())throw Error('Escribe la respuesta antes de usar PORTIA.');const language=$('[data-ai-language]').value;busy=true;message('PORTIA esta preparando una propuesta...');
      try{const result=await request('/improve','POST',{form_slug:q.form_slug,section:q.section,item_key:q.item_key,text,language});message();const d=modal('Propuesta PORTIA',`<p class="lw-ai-text">${esc(result.text)}</p><footer><button data-apply>Aplicar propuesta</button></footer>`);d.querySelector('[data-apply]').onclick=()=>{if(answers[key(q)]?.bullets[index]!==text){message('La respuesta cambio mientras PORTIA trabajaba. Conserva tu version o copia la propuesta.',true);return;}answers[key(q)].bullets[index]=result.text;changed();d.close();render();};}finally{finishBusy();}
    }
    async function history(){const result=await request('/'+current.report.id+'/history');const id=current.report.id;const d=modal('Historial',`<div class="lw-history">${result.data.map(r=>`<button data-revision="${r.id}">Version ${r.version} · ${esc(r.saved_by)} · ${esc(String(r.created_at).replace('T',' '))}</button>`).join('')||'<p>Sin versiones registradas</p>'}</div><pre data-snapshot></pre>`);d.querySelectorAll('[data-revision]').forEach(n=>n.onclick=run(async()=>{const snapshot=await request(`/${id}/history/${n.dataset.revision}`);d.querySelector('[data-snapshot]').textContent=JSON.stringify(snapshot,null,2);}));}
    async function executive(){if(busy)return;if(!selected.size)throw Error('Selecciona los cuestionarios para el reporte ejecutivo.');busy=true;const language=$('[data-language]').value;message('PORTIA esta preparando el reporte ejecutivo...');try{const result=await request('/executive','POST',{ids:[...selected],language});message();const d=modal('Reporte ejecutivo IA',`<p>${result.answer_count} respuestas consideradas</p><div class="lw-ai-text">${esc(result.text)}</div><footer><button data-ai-export="docx">Word</button><button data-ai-export="pdf">PDF</button></footer>`);d.querySelectorAll('[data-ai-export]').forEach(n=>n.onclick=run(async()=>download(await request('/executive/export','POST',{text:result.text,kind:n.dataset.aiExport},true),`LOGRA_Ejecutivo_${language}.${n.dataset.aiExport}`)));}finally{busy=false;}}
    try{boot=await request('/bootstrap');if(disposed)return;bind('new',()=>newReport());await list();}catch(error){fail(error);}
  }
  window.SOMLogra={mount,canLeave:()=>!active||active.canLeave(),destroy:()=>{active?.destroy();active=null;}};
})();
