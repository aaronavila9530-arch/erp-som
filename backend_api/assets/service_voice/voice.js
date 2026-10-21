/* Voice prepares a reviewed draft only; the existing Save remains authoritative. */
(() => {
  const norm = s => String(s || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
  const matches = (said, values) => {
    const unique = [...new Set(values.filter(Boolean))], n = norm(said);
    const exact = unique.filter(v => norm(v) === n);
    return exact.length ? exact : unique.filter(v => n && (` ${norm(v)} `).includes(` ${n} `));
  };
  const labels = {tipo:'Tipo',buque_contenedor:'Buque / contenedor',cliente:'Cliente',contacto:'Contacto',
    continente:'Continente',pais:'Pais',puerto:'Puerto',operacion:'Operacion',detalle:'Detalle',
    fecha_inicio:'Fecha inicio',hora_inicio:'Hora inicio',fecha_fin:'Fecha fin',hora_fin:'Hora fin',
    fecha_factura:'Fecha factura',fecha_vencimiento:'Fecha vencimiento',honorarios:'Honorarios',
    costo_operativo:'Costo operativo',costo_tarjetas:'Costo tarjetas'};
  function mount(host, api) {
    host.innerHTML = `<section class="service-voice"><div class="voice-actions"><button type="button" data-record title="Grabar dictado" aria-label="Grabar dictado"><img src="/servicios/voice/assets/mic.svg" width="18" height="18" alt=""> Dictar servicio</button><button type="button" data-stop hidden>Detener</button><label>Audio<input type="file" data-audio accept="audio/*"></label><button type="button" data-edit>Texto</button></div><p>El audio y su transcripcion se procesan con OpenAI. SOM no conserva la grabacion. Grabacion: maximo 2 minutos. Archivo: maximo 12 MB.</p><div data-editor hidden><label>Transcripcion<textarea data-text maxlength="6000" rows="3"></textarea></label><button type="button" data-parse>Preparar campos</button><div data-preview></div></div><div role="status" aria-live="polite" data-status></div></section>`;
    const q = s => host.querySelector(s), status = text => { q('[data-status]').textContent = text; };
    let dead = false, busy = false, recorder, stream, timer, chunks = [], bytes = 0, overflow = false;
    const controller = new AbortController();
    function tracksOff() { stream?.getTracks().forEach(t => t.stop()); stream = null; clearTimeout(timer); }
    function idle() { busy = false; q('[data-record]').disabled = false; q('[data-audio]').disabled = false; q('[data-parse]').disabled = false; q('[data-text]').disabled = false; q('[data-stop]').hidden = true; }
    function lock() { busy = true; q('[data-record]').disabled = true; q('[data-audio]').disabled = true; q('[data-parse]').disabled = true; q('[data-text]').disabled = true; }
    function invalidate() { q('[data-preview]').replaceChildren(); }
    q('[data-text]').oninput = invalidate;
    q('[data-edit]').onclick = () => { q('[data-editor]').hidden=false; };
    async function upload(blob) {
      if (dead) return;
      if (!blob.size || blob.size > 12 * 1024 * 1024) { status('Audio vacio o mayor de 12 MB.'); return; }
      if (!navigator.onLine) { status('Sin conexion. No se envio audio.'); return; }
      lock(); invalidate(); status('Transcribiendo...');
      try {
        const response = await api.audio(blob, controller.signal);
        if (dead) return;
        q('[data-editor]').hidden = false; q('[data-text]').value = response.text || '';
        status(response.text?.trim() ? 'Transcripcion lista para revisar.' : 'No se reconocio voz.');
      } catch (e) { if (!dead) status(e.message); }
      finally { if (!dead) idle(); }
    }
    q('[data-record]').onclick = async () => {
      if (busy || dead) return;
      if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) { status('Este navegador no permite grabar. Puede adjuntar un audio o escribir la transcripcion.'); q('[data-editor]').hidden = false; return; }
      if (!navigator.onLine) { status('Necesita conexion para procesar el dictado.'); return; }
      lock(); status('Solicitando microfono...');
      try {
        stream = await navigator.mediaDevices.getUserMedia({audio:true});
        if (dead) { tracksOff(); return; }
        const mime = ['audio/webm;codecs=opus','audio/mp4','audio/ogg;codecs=opus'].find(t => MediaRecorder.isTypeSupported(t));
        recorder = new MediaRecorder(stream, mime ? {mimeType:mime} : undefined);
        chunks = []; bytes = 0; overflow = false;
        recorder.ondataavailable = e => { bytes += e.data.size; if (bytes <= 12*1024*1024) chunks.push(e.data); else { overflow = true; if (recorder.state === 'recording') recorder.stop(); } };
        recorder.onstop = async () => { tracksOff(); if (dead) return; idle(); if (overflow) { status('Audio demasiado grande; vuelva a grabar.'); return; } const blob = new Blob(chunks,{type:recorder.mimeType}); chunks=[]; await upload(blob); };
        recorder.onerror = () => { tracksOff(); if (!dead) { idle(); status('La grabacion se interrumpio. Vuelva a intentarlo.'); } };
        recorder.start(1000); q('[data-stop]').hidden = false; status('Grabando...');
        timer = setTimeout(() => { if (recorder.state === 'recording') recorder.stop(); },120000);
      } catch (e) { tracksOff(); if (!dead) { idle(); status(e.name === 'NotAllowedError' ? 'Permiso de microfono denegado. Puede adjuntar audio o escribir.' : 'No se pudo abrir el microfono.'); q('[data-editor]').hidden = false; } }
    };
    q('[data-stop]').onclick = () => { if (recorder?.state === 'recording') recorder.stop(); };
    q('[data-audio]').onchange = async e => { const file = e.target.files[0]; if (file) await upload(file); e.target.value = ''; };
    q('[data-parse]').onclick = async () => {
      if (busy) return;
      const text = q('[data-text]').value.trim(); if (text.length < 3) { status('Escriba o grabe el dictado.'); return; }
      lock(); invalidate(); status('Preparando borrador...');
      const baseline = api.snapshot();
      try { const draft = await api.parse(text,controller.signal); if (!dead) await preview(draft,baseline); }
      catch(e) { if (!dead) status(e.message); }
      finally { if (!dead) idle(); }
    };
    async function preview(draft,baseline) {
      const panel = q('[data-preview]'), entries = [];
      function entry(key, said, choices, apply) {
        const row = document.createElement('label'); row.className = 'voice-row';
        const check = document.createElement('input'); check.type = 'checkbox'; check.checked = choices == null || choices.length === 1;
        const name = document.createElement('span'); name.textContent = (labels[key] || key) + ': ' + said;
        let control;
        if (choices != null) {
          control = document.createElement('select'); control.add(new Option('Seleccione...', ''));
          choices.forEach(v => control.add(new Option(v,v)));
          if (choices.length === 1) control.value = choices[0];
          control.onchange = () => { check.checked = !!control.value; };
          if (!choices.length) { check.checked = false; check.disabled = true; name.textContent += ' (sin coincidencia; completar manualmente)'; }
        } else { control = document.createElement('input'); control.value = String(said); control.readOnly = true; }
        row.append(check,name,control); panel.append(row); entries.push({check,control,apply});
      }
      for (const [key,label] of Object.entries(labels)) {
        if (['continente','pais','puerto'].includes(key) || draft[key] == null || draft[key] === '') continue;
        const field = document.getElementById('svcForm_'+key); if (!field) continue;
        const choices = field.tagName === 'SELECT' ? matches(draft[key],[...field.options].map(o=>o.value)) : null;
        entry(key,draft[key],choices, value => { field.value = value; });
      }
      if (draft.pais || draft.puerto) {
        const locations = await api.locations(draft.pais || '',draft.puerto || '',controller.signal);
        if (dead) return;
        const rows = locations.data || [], values = rows.map(r => [r.continente,r.pais,r.puerto].join(' / '));
        entry('Ubicacion',[draft.pais,draft.puerto].filter(Boolean).join(' / '),[...new Set(values)],async value => {
          const location = rows[values.indexOf(value)]; if (location) await api.location(location);
        });
      } else if (draft.continente) {
        entry('continente',draft.continente,null, async value => { const field=document.getElementById('svcForm_continente'); const found=matches(value,[...field.options].map(o=>o.value)); if(found.length===1) {field.value=found[0];await field.onchange();} });
      }
      const people = [];
      for (const person of draft.surveyors || []) {
        entry('Surveyor',person.nombre,matches(person.nombre,api.surveyors()),value => {people.push({name:value,amount:person.honorario});});
      }
      const warnings = document.createElement('p'); warnings.textContent = (draft.advertencias || []).join(' '); panel.append(warnings);
      const button = document.createElement('button'); button.type='button'; button.textContent='Aplicar campos seleccionados'; panel.append(button);
      button.onclick = async () => {
        if (busy || dead) return;
        if (api.snapshot() !== baseline && !confirm('El formulario cambio desde el dictado. ¿Aplicar los campos seleccionados sobre los valores actuales?')) return;
        lock(); button.disabled = true; people.length=0;
        try {
          for (const e of entries) { if (e.check.checked && e.control.value) await e.apply(e.control.value); }
          if (people.length) api.applySurveyors(people);
          invalidate(); status('Campos aplicados. Revise el formulario antes de Guardar.');
        } catch(e) { status('Aplicacion incompleta: '+e.message+' Revise el formulario.'); button.disabled=false; }
        finally { idle(); }
      };
      status('Borrador listo. Las coincidencias ambiguas requieren seleccion.');
    }
    return () => { dead=true; controller.abort(); if(recorder?.state==='recording') recorder.stop(); tracksOff(); chunks=[]; };
  }
  window.ServiceVoice = {mount,matches};
})();
