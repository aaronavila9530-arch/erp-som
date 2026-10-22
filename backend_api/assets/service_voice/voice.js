/* Voice prepares a reviewed draft only; the existing Save remains authoritative. */
(() => {
  const norm = s => String(s || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
  const matches = (said, values, person = false) => {
    const unique = [...new Set(values.filter(Boolean))], n = norm(said);
    const canonical = v => norm(v).replace(/\b(and|y)\b/g, ' ').replace(/\boff hire\b/g,'offhire').replace(/\bon hire\b/g,'onhire').replace(/\s+/g,' ').trim();
    const exact = unique.filter(v => canonical(v) === canonical(said));
    if (exact.length) return exact;
    const partial = unique.filter(v => n && (` ${norm(v)} `).includes(` ${n} `));
    if (partial.length || !person) return partial;
    const tokens = norm(said).replace(/v/g,'b').split(' ');
    return tokens.length < 2 ? [] : unique.filter(v => tokens.every(t => norm(v).replace(/v/g,'b').split(' ').includes(t)));
  };
  const labels = {tipo:'Tipo',buque_contenedor:'Buque / contenedor',cliente:'Cliente',contacto:'Contacto',
    continente:'Continente',pais:'Pais',puerto:'Puerto',operacion:'Operacion',detalle:'Detalle',
    fecha_inicio:'Fecha inicio',hora_inicio:'Hora inicio',fecha_fin:'Fecha fin',hora_fin:'Hora fin',
    fecha_factura:'Fecha factura',fecha_vencimiento:'Fecha vencimiento',honorarios:'Honorarios',
    costo_operativo:'Costo operativo',costo_tarjetas:'Costo tarjetas'};
  function mount(host, api) {
    host.innerHTML = `<section class="service-voice"><div class="voice-actions"><button type="button" data-record title="Grabar dictado"><img src="/servicios/voice/assets/mic.svg" width="18" height="18" alt=""> Dictar servicio</button><button type="button" data-stop hidden>Detener</button></div><p>El audio se procesa con OpenAI. SOM no conserva la grabacion. Maximo 2 minutos.</p><div role="status" aria-live="polite" data-status></div></section>`;
    const q = s => host.querySelector(s), status = text => { q('[data-status]').textContent = text; };
    let dead = false, busy = false, recorder, stream, timer, chunks = [], bytes = 0, overflow = false;
    const controller = new AbortController();
    function tracksOff() { stream?.getTracks().forEach(t => t.stop()); stream = null; clearTimeout(timer); }
    function idle() { busy = false; q('[data-record]').disabled = false; q('[data-stop]').hidden = true; }
    function lock() { busy = true; q('[data-record]').disabled = true; }
    async function upload(blob) {
      if (dead) return;
      if (!blob.size || blob.size > 12 * 1024 * 1024) { status('Audio vacio o mayor de 12 MB.'); return; }
      if (!navigator.onLine) { status('Sin conexion. No se envio audio.'); return; }
      lock(); status('Procesando dictado...');
      const baseline = api.snapshot();
      try {
        const response = await api.audio(blob, controller.signal);
        if (dead) return;
        if (!response.text?.trim()) { status('No se reconocio voz.'); return; }
        const draft = response.draft || await api.parse(response.text, controller.signal);
        if (!dead) await applyDraft(draft, baseline);
      } catch (e) { if (!dead) status(e.message); }
      finally { if (!dead) idle(); }
    }
    q('[data-record]').onclick = async () => {
      if (busy || dead) return;
      if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) { status('Este navegador no permite grabar. Complete el formulario manualmente.'); return; }
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
      } catch (e) { tracksOff(); if (!dead) { idle(); status(e.name === 'NotAllowedError' ? 'Permiso de microfono denegado.' : 'No se pudo abrir el microfono.'); } }
    };
    q('[data-stop]').onclick = () => { if (recorder?.state === 'recording') recorder.stop(); };
    async function applyDraft(draft, baseline) {
      const updates = [], pending = [], people = [];
      for (const key of Object.keys(labels)) {
        if (['continente','pais','puerto'].includes(key) || draft[key] == null || draft[key] === '') continue;
        const field = document.getElementById('svcForm_'+key); if (!field) continue;
        const choices = key === 'cliente' && api.clients ? clientMatches(draft[key],api.clients()) : field.tagName === 'SELECT' ? matches(draft[key],[...field.options].map(o=>o.value)) : [String(draft[key])];
        if (choices.length === 1) updates.push(() => {field.value=choices[0];});
        else pending.push(labels[key]+': '+draft[key]);
      }
      if (draft.pais || draft.puerto) {
        const result = await api.locations(draft.pais || '',draft.puerto || '',controller.signal);
        if (dead) return;
        const rows = [...new Map((result.data || []).map(r=>[JSON.stringify(r),r])).values()];
        if (rows.length === 1) updates.push(() => api.location(rows[0]));
        else pending.push('Ubicacion: '+[draft.puerto,draft.pais].filter(Boolean).join(', '));
      } else if (draft.continente) {
        const field=document.getElementById('svcForm_continente');
        const found=field ? matches(draft.continente,[...field.options].map(o=>o.value)) : [];
        if(found.length===1) updates.push(async()=>{field.value=found[0];await field.onchange?.();});
        else pending.push('Continente: '+draft.continente);
      }
      for (const person of draft.surveyors || []) {
        const found=matches(person.nombre,api.surveyors(),true);
        if(found.length===1) people.push({name:found[0],amount:person.honorario});
        else pending.push('Surveyor: '+person.nombre);
      }
      if(dead) return;
      if(api.snapshot() !== baseline) {status('El formulario cambio durante el dictado. No se reemplazaron sus datos; vuelva a dictar.');return;}
      for(const update of updates) {if(dead)return;await update();}
      if(dead)return;
      if(people.length) api.applySurveyors(people);
      status('Revise los campos antes de Guardar.'+(pending.length ? ' Pendientes de seleccionar: '+pending.join('; ')+'.' : '')+' '+(draft.advertencias || []).join(' '));
    }
    return () => { dead=true; controller.abort(); if(recorder?.state==='recording') recorder.stop(); tracksOff(); chunks=[]; };
  }
  function clientMatches(said, rows) {
    const alias = value => norm(value).replace(/\bp\s+(?:and\s+|y\s+)?i\b/g,'pandi');
    const query = alias(said);
    if (!query) return [];
    // Resolve aliases to the actual option value, never to another company's catalog.
    const found = rows.filter(row => [row.value,...row.aliases].some(value => (` ${alias(value)} `).includes(` ${query} `)));
    return [...new Set(found.map(row=>row.value))];
  }
  window.ServiceVoice = {mount,matches,clientMatches};
})();
