/* Containers workspace. No dependency on, or changes to, the desktop client. */
(() => {
  'use strict';
  const base = '/informes/containers';
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const icon = name => `<img alt="" src="/som/queue-icon/${name}.svg" width="20" height="20">`;
  let active;

  async function mount(root, api) {
    active?.destroy();
    let boot, report, revision, dirty = false, busy = false, disposed = false, offset = 0, total = 0;
    let sectionIndex = 0, baseline = {}, formValues = {}, listSequence = 0;
    const controllers = new Set();
    const $ = selector => root.querySelector(selector);
    root.classList.add('som-containers');
    root.innerHTML = `<header class="cw-header"><div class="cw-title">${icon('file-pen-line')}<div><h2>Containers</h2><span>${esc(api.company)}</span></div></div><button type="button" data-action="new">Nuevo informe</button></header>
      <p class="cw-message" role="status" hidden></p><div class="cw-body"></div>`;
    const message = (text = '', error = false) => {
      if (disposed) return;
      const node = $('.cw-message'); node.hidden = !text; node.textContent = text; node.classList.toggle('cw-error', error);
    };
    const fail = error => { if (!disposed && error.name !== 'AbortError') message(error.message || 'No se pudo completar la solicitud', true); };
    async function request(path, method = 'GET', body, binary = false) {
      const controller = new AbortController(); controllers.add(controller);
      const timeout = setTimeout(() => controller.abort(), binary ? 180000 : 60000);
      try {
        const response = await fetch(base + path, {method, headers: api.headers(), signal: controller.signal,
          body: body === undefined ? undefined : JSON.stringify(body)});
        if (!response.ok) {
          let detail;
          try { detail = (await response.json()).detail; } catch (_) { /* A proxy can return HTML. */ }
          throw Error(typeof detail === 'string' ? detail : `No se pudo completar la solicitud (${response.status}). Los cambios locales se conservan.`);
        }
        return binary ? response.blob() : response.json();
      } catch (error) {
        if (error.name === 'AbortError' && !disposed) throw Error('La solicitud tardo demasiado. Verifique el informe antes de repetir el guardado; el borrador se conserva.');
        throw error;
      } finally { clearTimeout(timeout); controllers.delete(controller); }
    }
    function canLeave() {
      if (busy) { message('Espere a que termine la operacion.', true); return false; }
      return !dirty || confirm('Hay cambios sin guardar en Containers. Salir sin guardarlos?');
    }
    function unload(event) { if (dirty || busy) { event.preventDefault(); event.returnValue = ''; } }
    window.addEventListener('beforeunload', unload);
    active = {canLeave, destroy() {
      disposed = true; controllers.forEach(c => c.abort()); window.removeEventListener('beforeunload', unload);
      root.classList.remove('som-containers');
    }};
    const run = fn => async event => { try { await fn(event); } catch (error) { fail(error); } };
    function download(blob, name) {
      const url = URL.createObjectURL(blob), a = document.createElement('a');
      a.href = url; a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(url), 30000);
    }
    function readInputs() {
      root.querySelectorAll('[data-field]').forEach(input => {
        formValues[input.dataset.field] = input.type === 'checkbox' ? input.checked : input.value;
      });
    }
    function formValue(field, value) {
      if (field.type === 'checkbox') return Boolean(value);
      if (field.type === 'datetime-local') {
        const raw = String(value || ''), probe = document.createElement('input');
        probe.type = 'datetime-local'; probe.value = raw.replace(' ', 'T');
        return probe.value || raw;
      }
      return value == null ? '' : String(value);
    }
    function changedFields() {
      readInputs();
      return Object.fromEntries(Object.entries(formValues).filter(([key, value]) => !report?.id || value !== baseline[key]));
    }
    function editor(result) {
      report = result.data; revision = result.version; dirty = false; sectionIndex = 0;
      baseline = Object.fromEntries(boot.sections.flatMap(s => s.fields.map(f => [f.key, formValue(f, report[f.key])])));
      formValues = {...baseline};
      renderEditor();
    }
    function renderEditor() {
      const editable = report.id ? boot.permissions.edit && report.status !== 'Approved' : boot.permissions.create;
      $('.cw-body').innerHTML = `<div class="cw-editor-toolbar"><button type="button" data-action="back">Volver</button><strong>${esc(report.linked_report_number || 'Nuevo informe')}</strong><span class="cw-state">${esc(report.status || 'draft')}</span><span class="cw-spacer"></span>
        <button type="button" data-action="backup" title="Descargar borrador local">Descargar borrador</button>
        ${report.id ? '<label class="cw-export">Documento<select data-export><option value="">Exportar...</option><option value="excel">Excel (.xlsx)</option><option value="pdf">Informe PDF</option><option value="presentation">Portada PDF</option><option value="unified">PDF unificado</option></select></label>' : ''}
        ${editable ? '<button type="button" data-action="save">Guardar borrador</button><button type="button" class="cw-primary" data-action="submit">Enviar a revision</button>' : ''}
        ${report.id && boot.permissions.approve ? '<button type="button" data-action="approve">Aprobar</button><button type="button" data-action="reject">Rechazar</button>' : ''}</div>
        <div class="cw-editor"><nav class="cw-sections" aria-label="Secciones del informe">${boot.sections.map((s,i) => `<button type="button" data-section="${i}" aria-current="${i === sectionIndex ? 'step' : 'false'}"><span>${String(i+1).padStart(2,'0')}</span>${esc(s.title)}</button>`).join('')}</nav>
        <form class="cw-fields" autocomplete="off"><h3>${esc(boot.sections[sectionIndex].title)}</h3><div class="cw-field-grid">${boot.sections[sectionIndex].fields.map(f => {
          const value = formValues[f.key], locked = !editable || f.key === 'linked_report_number';
          const attrs = `data-field="${f.key}" ${locked ? 'disabled' : ''}`;
          if (f.type === 'checkbox') return `<label class="cw-check"><input type="checkbox" ${attrs} ${value ? 'checked' : ''}>${esc(f.label)}</label>`;
          if (f.type === 'textarea') return `<label class="cw-narrative">${esc(f.label)}<textarea rows="7" maxlength="30000" ${attrs}>${esc(value)}</textarea>${editable ? `<button type="button" data-ai="${f.key}">${icon('pencil-line')}Mejorar con PORTIA</button>` : ''}</label>`;
          let type = f.type;
          if (type === 'datetime-local' && value) {
            const probe = document.createElement('input'); probe.type = type; probe.value = value;
            if (!probe.value) type = 'text'; // Preserve legacy free-text dates until explicitly corrected.
          }
          return `<label>${esc(f.label)}<input type="${type}" ${attrs} value="${esc(value)}" ${type === 'datetime-local' ? 'step="60"' : 'maxlength="2000"'}></label>`;
        }).join('')}</div><footer class="cw-section-footer"><button type="button" data-action="previous" ${sectionIndex === 0 ? 'disabled' : ''}>Anterior</button><span>${sectionIndex+1} / ${boot.sections.length}</span><button type="button" data-action="next" ${sectionIndex === boot.sections.length-1 ? 'disabled' : ''}>Siguiente</button></footer></form></div>`;
      $('.cw-fields').onsubmit = event => event.preventDefault();
      root.querySelectorAll('[data-field]').forEach(input => input.oninput = () => { readInputs(); dirty = Object.keys(changedFields()).length > 0; });
      root.querySelectorAll('[data-section]').forEach(button => button.onclick = () => { readInputs(); sectionIndex = Number(button.dataset.section); renderEditor(); });
      const action = (name, fn) => { const button = $(`[data-action="${name}"]`); if (button) button.onclick = run(fn); };
      action('back', () => { if (canLeave()) { dirty = false; showList(); } });
      action('previous', () => { readInputs(); sectionIndex--; renderEditor(); });
      action('next', () => { readInputs(); sectionIndex++; renderEditor(); });
      action('backup', () => { readInputs(); download(new Blob([JSON.stringify({company:api.company,id:report.id,version:revision,fields:formValues},null,2)],{type:'application/json'}),`Container_${report.id || 'borrador'}.json`); });
      action('save', () => save(false)); action('submit', () => save(true));
      action('approve', () => status('Approved')); action('reject', () => status('Rejected'));
      if ($('[data-export]')) $('[data-export]').onchange = run(async event => {
        const kind = event.target.value; event.target.value = ''; if (!kind) return;
        if (dirty) throw Error('Guarde los cambios antes de exportar.');
        await working(async () => download(await request(`/${report.id}/export/${kind}`, 'GET', undefined, true), `Container_${report.id}_${kind}.${kind === 'excel' ? 'xlsx' : 'pdf'}`));
      });
      root.querySelectorAll('[data-ai]').forEach(button => button.onclick = run(async () => {
        readInputs(); const key = button.dataset.ai, original = formValues[key];
        if (!original.trim()) throw Error('Escriba el texto antes de consultar PORTIA.');
        await working(async () => {
          const result = await request('/improve','POST',{text:original,container_no:formValues.report_no,cargo:formValues.goods_description,location:formValues.inspection_place,condition:formValues.goods_condition});
          if (disposed) return;
          const dialog = document.createElement('dialog'); dialog.className = 'cw-ai-dialog';
          dialog.innerHTML = '<h3>Propuesta de PORTIA</h3><textarea rows="14"></textarea><footer><button type="button" data-cancel>Conservar original</button><button type="button" data-apply>Aplicar propuesta</button></footer>';
          root.append(dialog); dialog.querySelector('textarea').value = result.text || '';
          dialog.querySelector('[data-cancel]').onclick = () => dialog.close();
          dialog.querySelector('[data-apply]').onclick = () => { formValues[key] = dialog.querySelector('textarea').value; dirty = true; dialog.close(); renderEditor(); };
          dialog.onclose = () => dialog.remove(); dialog.showModal();
        });
      }));
    }
    async function working(fn) {
      if (busy) return;
      busy = true; message('Procesando...');
      const controls = [...root.querySelectorAll('button,input,select,textarea')].map(el => [el,el.disabled]);
      controls.forEach(([el]) => { el.disabled = true; });
      try { await fn(); message(); } finally { busy = false; controls.forEach(([el,disabled]) => { if(el.isConnected) el.disabled = disabled; }); }
    }
    async function save(submit) {
      const fields = changedFields();
      await working(async () => {
        const result = await request(report.id ? `/${report.id}` : '', report.id ? 'PATCH' : 'POST', {fields,version:revision || null,submit});
        if (!disposed) editor(result);
      });
      message(submit ? 'Informe enviado a revision.' : 'Informe guardado.');
    }
    async function status(value) {
      if (dirty) throw Error('Guarde los cambios antes de cambiar el estado.');
      if (!confirm(`${value === 'Approved' ? 'Aprobar' : 'Rechazar'} este informe?`)) return;
      await working(async () => { const result = await request(`/${report.id}/status`,'POST',{version:revision,status:value}); if(!disposed) editor(result); });
    }
    async function showList() {
      report = null; message();
      $('.cw-body').innerHTML = `<form class="cw-filters"><label>Buscar<input name="q" placeholder="Informe, contenedor, cliente, buque o usuario"></label><label>Estado<select name="status"><option value="">Todos</option><option value="draft">Borrador</option><option>Pending for review</option><option>Approved</option><option>Rejected</option></select></label><button>Buscar</button></form>
        <div class="cw-table-wrap"><table class="cw-table" data-no-excel-filter="true"><thead><tr><th>Informe</th><th>Contenedor</th><th>Cliente</th><th>Buque</th><th>Usuario</th><th>Estado</th><th>Fecha</th><th></th></tr></thead><tbody></tbody></table></div><footer class="cw-pagination"><span></span><button type="button" data-prev>Anterior</button><button type="button" data-next>Siguiente</button></footer>`;
      const load = async () => {
        const sequence = ++listSequence, form = $('.cw-filters');
        const params = new URLSearchParams(new FormData(form)); params.set('offset',offset);
        const result = await request('?' + params);
        if (disposed || sequence !== listSequence || !form.isConnected) return;
        total = result.total;
        $('.cw-table tbody').innerHTML = result.data.map(r => `<tr><td><strong>${esc(r.linked_report_number || '-')}</strong></td><td>${esc(r.report_no)}</td><td>${esc(r.customer)}</td><td>${esc(r.vessel)}</td><td>${esc(r.user)}</td><td><span class="cw-state">${esc(r.status)}</span></td><td>${esc(String(r.created_at || '').slice(0,10).split('-').reverse().join('/'))}</td><td><button type="button" data-open="${Number(r.id)}">Abrir</button></td></tr>`).join('') || '<tr><td colspan="8">Sin informes para estos filtros</td></tr>';
        $('.cw-pagination span').textContent = `${total} informes | Pagina ${Math.floor(offset/50)+1}`;
        $('[data-prev]').disabled = offset === 0; $('[data-next]').disabled = offset + 50 >= total;
        root.querySelectorAll('[data-open]').forEach(button => button.onclick = run(() => working(async () => { const result = await request('/'+button.dataset.open); if(!disposed) editor(result); })));
      };
      $('.cw-filters').onsubmit = run(async event => { event.preventDefault(); offset = 0; await load(); });
      $('[data-prev]').onclick = run(async () => { offset = Math.max(0,offset-50); await load(); });
      $('[data-next]').onclick = run(async () => { offset += 50; await load(); });
      try { await load(); } catch (error) { fail(error); }
    }
    async function newReport() {
      if (!canLeave()) return;
      const dialog = document.createElement('dialog'); dialog.className = 'cw-service-dialog';
      dialog.innerHTML = '<h3>Vincular servicio</h3><form><input aria-label="Buscar servicio" placeholder="Numero, cliente o buque"><button>Buscar</button></form><p role="status"></p><div class="cw-service-results"></div><footer><button type="button" data-more hidden>Ver mas</button><button type="button" data-close>Cancelar</button></footer>';
      root.append(dialog); let start = 0, sequence = 0;
      async function search(append = false) {
        const n = ++sequence;
        try {
          const result = await request(`/services?q=${encodeURIComponent(dialog.querySelector('input').value)}&offset=${start}`);
          if (!dialog.isConnected || n !== sequence) return;
          const target = dialog.querySelector('.cw-service-results'); if (!append) target.replaceChildren();
          for (const s of result.data) {
            const button = document.createElement('button'); button.type = 'button';
            button.innerHTML = `<strong>${esc(s.num_informe)}</strong><span>${esc(s.cliente)}</span><span>${esc(s.buque_contenedor)} | ${esc(s.puerto)}</span>`;
            button.onclick = () => { dialog.close(); editor({data:{linked_report_number:s.num_informe,inspection_place:s.puerto || '',contact_person:s.contacto || '',on_behalf_of:s.cliente || '',status:'draft'}}); dirty = true; };
            target.append(button);
          }
          dialog.querySelector('[role="status"]').textContent = target.childElementCount ? '' : 'Sin servicios disponibles';
          dialog.querySelector('[data-more]').hidden = !result.more;
        } catch(error) { if(dialog.isConnected) dialog.querySelector('[role="status"]').textContent = error.message; }
      }
      dialog.querySelector('form').onsubmit = event => { event.preventDefault(); start=0; search(); };
      dialog.querySelector('[data-more]').onclick = () => { start += 50; search(true); };
      dialog.querySelector('[data-close]').onclick = () => dialog.close();
      dialog.onclose = () => dialog.remove(); dialog.showModal(); await search();
    }
    try {
      boot = await request('/bootstrap'); if (disposed) return;
      $('[data-action="new"]').hidden = !boot.permissions.create;
      $('[data-action="new"]').onclick = run(newReport);
      await showList();
    } catch(error) { fail(error); }
  }
  window.SOMContainers = {mount,canLeave:()=>!active || active.canLeave(),destroy:()=>{active?.destroy();active=null;}};
})();
