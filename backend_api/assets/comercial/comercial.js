/* Commercial desktop parity, using the same API and quotation exporters. */
(() => {
  'use strict';
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const number = value => new Intl.NumberFormat('es-CR', {maximumFractionDigits:2}).format(Number(value || 0));
  const labels = {
    consec:'Consecutivo', tipo:'Tipo', estado:'Estado', num_informe:'Informe', buque_contenedor:'Buque / contenedor', cliente:'Cliente',
    operacion:'Operaci\u00f3n', detalle:'Detalle', surveyor:'Surveyor', continente:'Continente', pais:'Pa\u00eds', puerto:'Puerto',
    fecha_inicio:'Fecha inicio', hora_inicio:'Hora inicio', fecha_fin:'Fecha fin', hora_fin:'Hora fin', demoras:'Demoras', duracion:'Duraci\u00f3n',
    year:'A\u00f1o', year_from:'A\u00f1o desde', year_to:'A\u00f1o hasta', quarter:'Trimestre', quarter_from:'Trimestre desde', quarter_to:'Trimestre hasta',
    servicios:'Servicios', servicio:'Servicio', factura:'Factura', valor_facturado:'Facturado', costo_operativo:'Costo operativo', costo_tarjetas:'Costo tarjetas',
    honorarios:'Honorarios', iva:'IVA', comision_bancaria:'Comisi\u00f3n bancaria', margen_bruto:'Margen bruto', margen_neto:'Margen neto',
    total_operaciones:'Operaciones', frecuencia:'Frecuencia', facturacion_neta:'Facturaci\u00f3n neta', ticket_promedio:'Ticket promedio', is_pareto_80:'Pareto 80%',
    cantidad_servicios:'Cantidad', revenue_bruto_total:'Ingreso bruto', revenue_neto_total:'Ingreso neto', costo_total:'Costo total', margen_neto_pct:'Margen neto %',
    id:'ID', quotation_number:'Cotizaci\u00f3n', precio:'Precio', idioma:'Idioma', validez:'Validez (d\u00edas)', status:'Estado', created_at:'Creada', activo:'Activo',
    total_facturado:'Facturado', estado_operativo:'Estado operativo', min_ops:'Umbral m\u00ednimo', codigo:'C\u00f3digo', codigoprod:'C\u00f3digo producto', costo_base:'Costo base',
    total_servicios:'Servicios', honorarios_total:'Honorarios', acumulado_pct:'Acumulado %', es_pareto_80:'Pareto 80%', clientes:'Clientes', paises:'Pa\u00edses', puertos:'Puertos',
    facturado:'Facturado', costos:'Costos', rentabilidad_monto:'Rentabilidad', rentabilidad_pct:'Rentabilidad %', facturacion:'Facturaci\u00f3n', rentabilidad:'Rentabilidad',
    costos_totales:'Costos', margen_bruto_total:'Margen bruto', margen_neto_total:'Margen neto', total_puertos:'Puertos', con_operacion:'Con operaci\u00f3n',
    sin_operacion:'Sin operaci\u00f3n', operacion_minima:'Operaci\u00f3n m\u00ednima', operacion_activa:'Operaci\u00f3n activa', cobertura_pct:'Cobertura %',
    pendientes:'Pendientes', aprobadas:'Aprobadas', canceladas:'Canceladas', nombrejuridico:'Nombre jur\u00eddico', nombrecomercial:'Nombre comercial',
    telefono:'Tel\u00e9fono', cedulajuridicavat:'Identificaci\u00f3n fiscal', actividad_economica:'Actividad econ\u00f3mica', creado_en:'Creado', provincia:'Provincia',
    canton:'Cant\u00f3n', distrito:'Distrito', direccionexacta:'Direcci\u00f3n', prefijo:'Prefijo', correo:'Correo', contacto_principal:'Contacto principal',
    contacto_secundario:'Contacto secundario', fecha_pago:'T\u00e9rminos de pago', comentarios:'Comentarios'
  };
  const views = {
    board:{title:'Pizarra operativa', tab:'Pizarra', permission:'board', path:'/comercial/board', filters:['cliente','pais','puerto','surveyor','year'], columns:'consec tipo estado num_informe buque_contenedor cliente operacion detalle surveyor continente pais puerto fecha_inicio hora_inicio fecha_fin hora_fin demoras duracion'},
    clients:{title:'Anal\u00edtica de clientes', tab:'Clientes', permission:'clients', path:'/comercial/client-view', filters:['year_from','year_to','cliente','servicio'], columns:'cliente servicios buque_contenedor fecha_inicio fecha_fin factura valor_facturado costo_operativo costo_tarjetas honorarios iva comision_bancaria margen_bruto margen_neto'},
    ports:{title:'Anal\u00edtica de puertos', tab:'Puertos', permission:'ports', path:'/comercial/analytics/puertos', filters:['year_from','year_to','cliente','continente','pais','puerto'], columns:'continente pais puerto total_operaciones frecuencia facturacion_neta ticket_promedio margen_bruto margen_neto is_pareto_80'},
    services:{title:'Anal\u00edtica de servicios', tab:'Servicios', permission:'services', path:'/comercial/analytics/servicios/by-servicio', filters:['year_from','year_to','quarter','continente','pais','puerto','servicio'], columns:'servicio quarter cantidad_servicios revenue_bruto_total revenue_neto_total costo_total margen_neto margen_neto_pct'},
    quotes:{title:'Cotizaciones', tab:'Cotizaciones', permission:'quotations', path:'/comercial/cotizaciones', filters:['cliente','servicio','continente','pais','puerto','status'], columns:'id quotation_number cliente servicio continente pais puerto precio idioma validez status created_at'},
    prices:{title:'Precios por servicio', tab:'Precios', permission:'quotations', path:'/comercial/precios', filters:['cliente','servicio','continente','pais','puerto','activo'], columns:'id servicio cliente continente pais puerto precio activo'},
    coverage:{title:'Cobertura de puertos', parent:'ports', permission:'ports', path:'/comercial/ports-coverage', filters:['year_from','year_to','cliente','min_ops','continente','pais','puerto','estado_operativo'], columns:'continente pais puerto total_operaciones total_facturado estado_operativo'},
    missing:{title:'Servicios no ofrecidos', parent:'services', permission:'services', path:'/comercial/analytics/servicios/not-offered', filters:['year_from','year_to','quarter_from','quarter_to','continente','pais','puerto'], columns:'codigo codigoprod servicio costo_base'},
    surveyors:{title:'Costos por surveyor / Pareto 80-20', parent:'services', permission:'services', path:'/comercial/analytics/servicios/costos-surveyor-pareto', filters:['year_from','year_to','quarter','surveyor','continente','pais','puerto','servicio'], columns:'surveyor continente pais puerto total_servicios honorarios_total acumulado_pct es_pareto_80'}
  };
  const moneyKeys = new Set('precio costo_base valor_facturado costo_operativo costo_tarjetas honorarios iva comision_bancaria margen_bruto margen_neto facturacion_neta ticket_promedio revenue_bruto_total revenue_neto_total costo_total total_facturado honorarios_total'.split(' '));
  let instance;
  class Workspace {
    constructor(root, config) {
      this.root=root; this.config=config; this.controller=new AbortController(); this.view='board'; this.rows=[]; this.filtered=[];
      this.page=0; this.selected=null; this.sort=null; this.order=1; this.filters={}; this.permissions={}; this.options={}; this.sequence=0;
      this.dirty=false; this.disposed=false; this.dialog=null;
    }
    async request(path, method='GET', body, binary=false) {
      const response=await fetch(path,{method, headers:this.config.headers, signal:this.controller.signal, ...(body===undefined?{}:{body:JSON.stringify(body)})});
      if(!response.ok) {
        let detail; try { detail=(await response.json()).detail; } catch (_) {}
        throw new Error(typeof detail==='string'?detail:`No se pudo completar la solicitud (${response.status}).`);
      }
      return binary?response.blob():response.json();
    }
    async start() {
      this.root.innerHTML='<section class="commercial"><p role="status">Cargando Comercial...</p></section>';
      try { const meta=await this.request('/comercial/web/meta'); if(this.disposed)return; this.permissions=meta.permissions; this.options=meta.options; this.render(); }
      catch(error) { if(!this.disposed) this.root.innerHTML=`<section class="commercial"><p role="alert">${esc(error.message)}</p><button data-retry>Reintentar</button></section>`;
        this.root.querySelector('[data-retry]')?.addEventListener('click',()=>this.start()); }
    }
    canLeave() { return !this.dirty || confirm('Hay cambios sin guardar. \u00bfDesea descartarlos?'); }
    destroy() { this.disposed=true; this.controller.abort(); this.dialog?.remove(); }
    message(text,error=false) { const node=this.root.querySelector('[data-message]'); if(node){node.textContent=text;node.classList.toggle('error',error);} }
    async go(view) {
      if(!this.canLeave() || !this.permissions[views[view].permission]) return;
      this.closeDialog(true); this.view=view; this.filters={}; this.rows=[]; this.page=0; this.selected=null; this.sort=null; this.sequence++;
      this.render(); if(view!=='board') await this.search();
    }
    field(key, value='', options=null, required=false) {
      const title=labels[key]||key;
      const values=options ?? this.options[key==='servicio'?'operacion':key] ?? [];
      let input;
      if(['status','activo','estado_operativo','quarter','quarter_from','quarter_to','idioma'].includes(key)) {
        const choices=options ?? ({status:['PENDIENTE','APROBADO','CANCELADO'],activo:['true','false'],estado_operativo:['SIN_OPERACION','OPERACION_MINIMA','OPERACION_ACTIVA'],idioma:['ES','EN']}[key]||['Q1','Q2','Q3','Q4']);
        input=`<select name="${key}" ${required?'required':''}><option value="">Todos</option>${choices.map(v=>`<option value="${esc(v)}" ${String(v)===String(value)?'selected':''}>${esc(v==='true'?'S\u00ed':v==='false'?'No':v)}</option>`).join('')}</select>`;
      } else if(['year','year_from','year_to','min_ops','validez','precio'].includes(key)) {
        input=`<input name="${key}" type="number" step="${key==='precio'?'0.01':'1'}" min="${key.startsWith('year')?1900:0}" ${key.startsWith('year')?'max="2200"':''} value="${esc(value)}" ${required?'required':''}>`;
      } else {
        const id=`com-list-${this.dialog?'dialog':'filter'}-${key}`;
        input=`<input name="${key}" list="${id}" value="${esc(value)}" autocomplete="off" ${required?'required':''}><datalist id="${id}">${values.map(v=>`<option value="${esc(v)}"></option>`).join('')}</datalist>`;
      }
      return `<label>${esc(title)}${input}</label>`;
    }
    button(action,text,secondary=true,icon='') {
      return `<button type="button" data-action="${action}" class="${secondary?'secondary':''}">${icon?`<span class="com-icon" aria-hidden="true" style="--com-icon:url('/som/queue-icon/${icon}.svg')"></span>`:''}${text}</button>`;
    }
    render() {
      const v=views[this.view], ranged=v.filters.includes('year_from');
      const year=this.config.year||new Date().getFullYear();
      if(ranged && !Object.keys(this.filters).length) this.filters={year_from:year,year_to:year};
      if(this.view==='coverage' && !this.filters.min_ops) this.filters.min_ops=3;
      let actions='';
      if(this.view==='clients') actions+=this.button('client-detail','Ver cliente','secondary','receipt-text');
      if(this.view==='ports') actions+=this.button('coverage','Cobertura de puertos');
      if(this.view==='services') actions+=this.button('missing','No ofrecidos')+this.button('surveyors','Costos por surveyor');
      if(this.view==='quotes') {
        if(this.permissions.edit) actions+=this.button('new-quote','Nueva cotizaci\u00f3n',false,'file-pen-line')+this.button('approve','Aprobar',true,'badge-check')+this.button('cancel','Cancelar')+this.button('edit-text','Editar texto',true,'pencil-line');
        actions+=this.button('quote-word','Word')+this.button('quote-pdf','PDF');
        if(this.permissions.delete) actions+=this.button('delete','Eliminar');
      }
      if(this.view==='prices') {
        if(this.permissions.edit) actions+=this.button('new-price','Agregar precio',false,'file-pen-line')+this.button('edit-price','Editar precio',true,'pencil-line');
        if(this.permissions.edit) actions+=this.button('delete','Eliminar precio');
      }
      if(this.permissions.export) actions+=`<label>Exportar<select data-export><option value="">Formato...</option><option value="xlsx">Excel</option><option value="csv">CSV</option><option value="pdf">PDF</option></select></label>`;
      this.root.innerHTML=`<section class="commercial"><div class="com-top"><h2>${esc(v.title)}</h2><span class="com-company">${esc(this.config.company)}</span></div>
        <nav class="com-tabs" role="tablist" aria-label="Comercial">${Object.entries(views).filter(([,x])=>!x.parent && this.permissions[x.permission]).map(([key,x])=>`<button role="tab" aria-selected="${key===(v.parent||this.view)}" data-view="${key}">${esc(x.tab)}</button>`).join('')}</nav>
        ${v.parent?`<div class="com-actions">${this.button('back','&larr; '+views[v.parent].tab)}</div>`:''}
        <form data-filters><div class="com-filters">${ranged?`<label>Per\u00edodo<select name="year_mode"><option value="exact">A\u00f1o exacto</option><option value="range">Rango de a\u00f1os</option></select></label>`:''}${v.filters.map(key=>this.field(key,this.filters[key]??'')).join('')}</div>
        ${this.view==='board'?`<div class="com-checks">${['Confirmado','En operaci\u00f3n','FINALIZADO','Cancelado'].map((value,i)=>`<label><input type="checkbox" name="estados" value="${value}" ${i<2?'checked':''}>${esc(value)}</label>`).join('')}</div>`:''}
        <div class="com-actions"><button type="submit">Buscar</button>${this.button('clear','Limpiar')}</div></form>
        <div data-message class="com-message" role="status" aria-live="polite">${this.view==='board'?'Seleccione los filtros y busque.':''}</div><div data-kpis class="com-kpis" hidden></div>
        <div class="com-actions">${actions}<label>Buscar en resultados<input type="search" data-search></label></div><div data-table></div></section>`;
      this.root.querySelectorAll('[data-view]').forEach(button=>button.onclick=()=>this.go(button.dataset.view));
      this.root.querySelector('[data-filters]').onsubmit=event=>{event.preventDefault();this.search();};
      this.root.querySelectorAll('[data-action]').forEach(button=>button.onclick=()=>this.action(button.dataset.action));
      this.root.querySelector('[data-search]').oninput=()=>{this.page=0;this.table();};
      const exports=this.root.querySelector('[data-export]'); if(exports) exports.onchange=()=>{const fmt=exports.value;exports.value='';if(fmt)this.export(fmt);};
      if(ranged) {
        const form=this.root.querySelector('[data-filters]');
        const sync=()=>{form.elements.year_to.disabled=form.elements.year_mode.value==='exact';if(form.elements.year_to.disabled)form.elements.year_to.value=form.elements.year_from.value;};
        form.elements.year_mode.onchange=sync;form.elements.year_from.oninput=sync;sync();
      }
      this.table();
    }
    readFilters() {
      const form=this.root.querySelector('[data-filters]'), data=new FormData(form), result={};
      for(const [key,value] of data) if(String(value).trim() && !['estados','year_mode'].includes(key)) result[key]=String(value).trim();
      if(data.has('year_mode')) {
        result.year_from=result.year_from||result.year_to||String(this.config.year||new Date().getFullYear());
        result.year_to=data.get('year_mode')==='exact'?result.year_from:(result.year_to||result.year_from);
        if(Number(result.year_from)>Number(result.year_to)) throw new Error('El a\u00f1o desde no puede ser mayor al a\u00f1o hasta.');
      }
      if(result.quarter_from && result.quarter_to && result.quarter_from>result.quarter_to) throw new Error('El rango de trimestres est\u00e1 invertido.');
      if(this.view==='board') result.estados=data.getAll('estados');
      return result;
    }
    url(path,filters) {
      const query=new URLSearchParams();
      for(const [key,value] of Object.entries(filters)) (Array.isArray(value)?value:[value]).forEach(v=>{if(v!=='' && v!=null)query.append(key,v);});
      return `${path}?${query}`;
    }
    async search() {
      const seq=++this.sequence, view=this.view, definition=views[view];
      try {
        this.filters=this.readFilters(); const query={...this.filters};
        if(view==='ports' && query.cliente){query.clientes=query.cliente;delete query.cliente;}
        if(view==='surveyors' && query.servicio){query.operacion=query.servicio;delete query.servicio;}
        this.message('Cargando...'); this.selected=null;
        const data=await this.request(this.url(definition.path,query));
        if(seq!==this.sequence || this.disposed) return;
        let rows=Array.isArray(data)?data:(data.data||[]);
        if(['prices','coverage','services'].includes(view)) rows=rows.filter(row=>definition.filters.every(key=>!(key in row) || !this.filters[key] || String(row[key])===String(this.filters[key])));
        let kpis=data.kpis;
        if(view==='ports') kpis=await this.request(this.url('/comercial/analytics/puertos/kpis',query));
        if(view==='services') kpis=(await this.request(this.url('/comercial/analytics/servicios/kpis',{...query,operacion:query.servicio}))).kpis;
        if(seq!==this.sequence || this.disposed) return;
        this.rows=rows; this.page=0;
        if(view==='quotes') kpis={clientes:new Set(rows.map(r=>r.cliente)).size,servicios:new Set(rows.map(r=>r.servicio)).size,paises:new Set(rows.map(r=>r.pais)).size,puertos:new Set(rows.map(r=>r.puerto)).size,pendientes:rows.filter(r=>r.status==='PENDIENTE').length,aprobadas:rows.filter(r=>r.status==='APROBADO').length,canceladas:rows.filter(r=>r.status==='CANCELADO').length};
        this.kpis(kpis||{}); this.table(); this.message(`${rows.length} registros`);
        for(const key of definition.filters) {
          const optionKey=key==='servicio'?'operacion':key;
          this.options[optionKey]=[...new Set([...(this.options[optionKey]||[]),...rows.map(r=>r[key]).filter(v=>v!=null)])].sort();
          const list=this.root.querySelector(`#com-list-filter-${key}`);
          if(list)list.innerHTML=this.options[optionKey].map(v=>`<option value="${esc(v)}"></option>`).join('');
        }
      } catch(error) { if(seq===this.sequence && !this.disposed){this.rows=[];this.kpis({});this.table();this.message(error.message,true);} }
    }
    kpis(values) {
      const node=this.root.querySelector('[data-kpis]');
      const entries=Object.entries(values).filter(([,value])=>value!==null && Number.isFinite(Number(value)));
      node.hidden=!entries.length;
      node.innerHTML=entries.map(([key,value])=>`<div class="com-kpi"><small>${esc(labels[key]||key.replaceAll('_',' '))}</small><strong>${number(value)}${key.endsWith('_pct')?'%':''}</strong></div>`).join('');
    }
    cell(key,value) {
      if(value==null)return '';
      if(typeof value==='boolean')return value?'S\u00ed':'No';
      if(key==='duracion'){const n=Math.max(0,Number(value)||0);return `${Math.floor(n/1440)}D ${Math.floor(n%1440/60)}H ${Math.floor(n%60)}M`;}
      if(moneyKeys.has(key))return number(value);
      if(key.endsWith('_pct'))return number(value)+'%';
      if(['estado','status','estado_operativo'].includes(key))return `<span class="com-status ${esc(String(value).toUpperCase())}">${esc(value)}</span>`;
      return esc(value);
    }
    table() {
      const node=this.root.querySelector('[data-table]'); if(!node)return;
      const cols=views[this.view].columns.split(' '), query=(this.root.querySelector('[data-search]')?.value||'').toLocaleLowerCase();
      this.filtered=this.rows.filter(row=>!query || cols.some(key=>String(row[key]??'').toLocaleLowerCase().includes(query)));
      if(this.sort)this.filtered.sort((a,b)=>{const x=a[this.sort],y=b[this.sort];return this.order*(typeof x==='number' && typeof y==='number'?x-y:String(x??'').localeCompare(String(y??''),'es',{numeric:true}));});
      const pages=Math.max(1,Math.ceil(this.filtered.length/50));this.page=Math.min(this.page,pages-1);
      const slice=this.filtered.slice(this.page*50,(this.page+1)*50);
      node.innerHTML=`<div class="com-table-wrap"><table data-excel-enhanced="1"><thead><tr><th>Seleccionar</th>${cols.map(key=>`<th><button type="button" data-sort="${key}">${esc(labels[key]||key)}${this.sort===key?(this.order===1?' \u2191':' \u2193'):''}</button></th>`).join('')}</tr></thead><tbody>${slice.map((row,index)=>`<tr aria-selected="${this.selected===row}"><td><input type="radio" name="com-row" data-row="${index}" aria-label="Seleccionar registro ${this.page*50+index+1}" ${this.selected===row?'checked':''}></td>${cols.map(key=>`<td class="${['cliente','servicio','servicios','detalle','buque_contenedor'].includes(key)?'com-text':''}">${this.cell(key,row[key])}</td>`).join('')}</tr>`).join('')||`<tr><td colspan="${cols.length+1}">Sin registros</td></tr>`}</tbody></table></div>
        <div class="com-pager"><span>${this.filtered.length} registros \u00b7 P\u00e1gina ${this.page+1} de ${pages}</span><button data-prev aria-label="P\u00e1gina anterior" ${this.page===0?'disabled':''}>&larr;</button><button data-next aria-label="P\u00e1gina siguiente" ${this.page+1>=pages?'disabled':''}>&rarr;</button></div>`;
      node.querySelectorAll('[data-sort]').forEach(button=>button.onclick=()=>{this.order=this.sort===button.dataset.sort?-this.order:1;this.sort=button.dataset.sort;this.table();});
      node.querySelectorAll('[data-row]').forEach(input=>input.onchange=()=>{this.selected=slice[Number(input.dataset.row)];this.table();});
      node.querySelector('[data-prev]').onclick=()=>{this.page--;this.table();};node.querySelector('[data-next]').onclick=()=>{this.page++;this.table();};
    }
    selectedRow() { if(!this.selected)throw new Error('Seleccione un registro.');return this.selected; }
    async download(path,name,method='GET',body) {
      const blob=await this.request(path,method,body,true);if(this.disposed)return;
      const url=URL.createObjectURL(blob), link=document.createElement('a');link.href=url;link.download=name;document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
    }
    async export(format) {
      try {if(!this.filtered.length)throw new Error('No hay registros para exportar.');
        const columns=views[this.view].columns.split(' ');
        await this.download(`/comercial/web/export/${format}`,`${this.view}.${format}`,'POST',{title:views[this.view].title,columns,labels:columns.map(key=>labels[key]||key),rows:this.filtered});
      }catch(error){this.message(error.message,true);}
    }
    async action(action) {
      try {
        if(action==='clear'){this.filters={};this.rows=[];this.selected=null;this.sequence++;this.render();return;}
        if(action==='back'){await this.go(views[this.view].parent);return;}
        if(['coverage','missing','surveyors'].includes(action)){const filters={...this.filters};await this.go(action);const form=this.root.querySelector('[data-filters]');for(const [key,value] of Object.entries(filters))if(form.elements[key]){form.elements[key].value=value;if(key==='year_to' && filters.year_from!==value){form.elements.year_mode.value='range';form.elements.year_to.disabled=false;}}await this.search();return;}
        if(action==='client-detail'){await this.clientDetail();return;}
        if(action==='new-quote'){await this.quoteForm();return;}
        if(action==='new-price' || action==='edit-price'){await this.priceForm(action==='edit-price'?this.selectedRow():null);return;}
        if(action==='edit-text'){await this.editText();return;}
        const row=this.selectedRow();
        if(action.startsWith('quote-')) {const fmt=action.slice(6);await this.download(`/comercial/cotizaciones/${row.id}/export/${fmt}`,`${row.quotation_number||row.id}.${fmt==='word'?'docx':'pdf'}`);return;}
        if(action==='delete') {
          if(!confirm(`\u00bfEliminar ${row.quotation_number||row.servicio||row.id}?`))return;
          await this.request(`${views[this.view].path}/${row.id}`,'DELETE');await this.search();this.message('Registro eliminado.');return;
        }
        if(['approve','cancel'].includes(action)) {
          if(row.status!=='PENDIENTE')throw new Error('Solo se pueden aprobar o cancelar cotizaciones pendientes.');
          if(action==='cancel'){this.cancelQuote(row);return;}
          if(!confirm(`\u00bfAprobar la cotizaci\u00f3n ${row.quotation_number}?`))return;
          await this.request(`/comercial/cotizaciones/${row.id}`,'PUT',{status:'APROBADO'});await this.search();
          this.message('Cotizaci\u00f3n aprobada.');await this.config.openService();
        }
      } catch(error) {if(!this.disposed)this.message(error.message,true);}
    }
    modal(title,html) {
      this.closeDialog(true);this.dialog=document.createElement('dialog');this.dialog.className='com-dialog';
      this.dialog.innerHTML=`<div class="com-top"><h2>${esc(title)}</h2><button class="secondary" type="button" data-close aria-label="Cerrar">\u00d7</button></div>${html}<p data-error role="alert" class="com-message error"></p>`;
      document.body.append(this.dialog);this.dialog.showModal();
      this.dialog.querySelector('[data-close]').onclick=()=>this.closeDialog();
      this.dialog.oncancel=event=>{event.preventDefault();this.closeDialog();};
      this.dialog.oninput=()=>{this.dirty=true;};return this.dialog;
    }
    closeDialog(force=false) {if(!force && !this.canLeave())return false;this.dialog?.remove();this.dialog=null;this.dirty=false;return true;}
    bindSave(dialog,handler) {
      dialog.querySelector('form').onsubmit=async event=>{
        event.preventDefault();const button=event.submitter;button.disabled=true;
        try {await handler(new FormData(event.target));if(this.disposed)return;this.closeDialog(true);await this.search();this.message('Guardado correctamente.');}
        catch(error){if(dialog.isConnected)dialog.querySelector('[data-error]').textContent=error.message;}
        finally{button.disabled=false;}
      };
    }
    async clientDetail() {
      const row=this.selectedRow(), response=await this.request(this.url('/comercial/clientes',{nombre:row.cliente}));
      const clients=response.data||[];if(!clients.length)throw new Error('No se encontr\u00f3 la ficha del cliente.');
      this.modal('Detalle del cliente',clients.map(client=>`<dl class="com-detail">${Object.entries(client).map(([key,value])=>`<div><dt>${esc(labels[key]||key)}</dt><dd>${esc(value??'')}</dd></div>`).join('')}</dl>`).join('<hr>'));
    }
    cancelQuote(row) {
      const dialog=this.modal('Cancelar '+row.quotation_number,'<form><label>Raz\u00f3n de cancelaci\u00f3n<textarea name="reason" required></textarea></label><div class="com-actions"><button type="submit">Confirmar cancelaci\u00f3n</button></div></form>');
      this.bindSave(dialog,async data=>{const reason=data.get('reason').trim();if(!reason)throw new Error('Indique la raz\u00f3n de cancelaci\u00f3n.');await this.request(`/comercial/cotizaciones/${row.id}`,'PUT',{status:'CANCELADO',razon_cancelacion:reason});});
    }
    async editText() {
      const row=this.selectedRow(), data=await this.request(`/comercial/cotizaciones/${row.id}/detail`);
      const dialog=this.modal('Texto / '+(row.quotation_number||row.id),`<form><label>Texto de la cotizaci\u00f3n<textarea name="text" required>${esc(data.texto_cotizacion||data.texto_exportable||'')}</textarea></label><div class="com-actions"><button type="submit">Guardar texto</button></div></form>`);
      this.bindSave(dialog,async values=>{const text=values.get('text').trim();if(!text)throw new Error('El texto no puede quedar vac\u00edo.');await this.request(`/comercial/cotizaciones/${row.id}`,'PUT',{texto_cotizacion:text});});
    }
    cascade(form,locations) {
      const keys=['continente','pais','puerto'];
      const update=start=>{for(let i=start;i<keys.length;i++){const key=keys[i], rows=locations.filter(row=>keys.slice(0,i).every(parent=>!form.elements[parent].value||row[parent]===form.elements[parent].value));const list=form.querySelector(`#com-list-dialog-${key}`);if(list)list.innerHTML=[...new Set(rows.map(r=>r[key]).filter(Boolean))].sort().map(value=>`<option value="${esc(value)}"></option>`).join('');}};
      keys.forEach((key,index)=>form.elements[key].addEventListener('change',()=>{keys.slice(index+1).forEach(k=>form.elements[k].value='');update(index+1);}));update(0);
    }
    async priceForm(row) {
      const meta=await this.request('/comercial/precios/meta');
      const dialog=this.modal(row?'Editar precio':'Agregar precio','');
      dialog.querySelector('[data-error]').insertAdjacentHTML('beforebegin',`<form><div class="com-form-grid">${this.field('cliente',row?.cliente,meta.clientes.map(r=>r.nombrejuridico),true)}${this.field('servicio',row?.servicio,meta.servicios.map(r=>r.nombre),true)}${['continente','pais','puerto'].map(key=>this.field(key,row?.[key])).join('')}${this.field('precio',row?.precio,[],true)}${row?`<label class="com-check"><input type="checkbox" name="activo" ${row.activo?'checked':''}>Activo</label>`:''}</div><div class="com-actions"><button type="submit">Guardar precio</button></div></form>`);
      this.cascade(dialog.querySelector('form'),meta.ubicaciones);
      this.bindSave(dialog,async data=>{
        const payload=Object.fromEntries(data);payload.precio=Number(payload.precio);if(row)payload.activo=data.has('activo');
        if(!meta.clientes.some(r=>r.nombrejuridico===payload.cliente)||!meta.servicios.some(r=>r.nombre===payload.servicio))throw new Error('Seleccione un cliente y servicio del cat\u00e1logo.');
        await this.request('/comercial/precios'+(row?'/'+row.id:''),row?'PUT':'POST',payload);
      });
    }
    async quoteForm() {
      const prices=(await this.request('/comercial/precios')).data.filter(row=>row.activo!==false);
      const next=await this.request('/comercial/cotizaciones/next-quotation-number');
      const quoteNumber=next.quotation_number||'';
      const dialog=this.modal('Nueva cotizaci\u00f3n '+quoteNumber,'');
      const clients=[...new Set(prices.map(r=>r.cliente))].sort();
      dialog.querySelector('[data-error]').insertAdjacentHTML('beforebegin',`<form><div class="com-form-grid">${this.field('cliente','',clients,true)}${['continente','pais','puerto'].map(key=>this.field(key,'',[])).join('')}${this.field('idioma','ES',['ES','EN'],true)}${this.field('validez',15,[],true)}</div><div class="com-actions"><label>Servicio<select data-price><option value="">Seleccione...</option></select></label>${this.button('add-line','Agregar servicio')}</div><div class="com-lines" data-lines></div><p data-total>Total: 0</p><label>Texto de la cotizaci\u00f3n<textarea name="texto" required></textarea></label><div class="com-actions">${this.button('reset-text','Generar texto')}${this.button('preview-word','Word')}${this.button('preview-pdf','PDF')}<button type="submit">Confirmar y guardar</button></div></form>`);
      const form=dialog.querySelector('form'), lines=[];
      const text=()=>{
        const en=form.elements.idioma.value==='EN';
        const until=new Date();until.setDate(until.getDate()+Number(form.elements.validez.value||0));
        const valid=until.toLocaleDateString(en?'en-US':'es-CR',{year:'numeric',month:'long',day:'numeric'});
        const company=this.config.companyName||this.config.company.split('-')[0];
        const client=form.elements.cliente.value||(en?'Client':'cliente');
        const services=lines.map(row=>`- ${row.servicio}: USD ${Number(row.precio).toFixed(2)}`).join('\n');
        const total=lines.reduce((sum,r)=>sum+Number(r.precio),0).toFixed(2);
        form.elements.texto.value=en?
          `Dear ${client},\n\nWe are pleased to submit our quotation for the following services:\n\n${services}\n\nTotal amount: USD ${total}\n\nThis quotation is valid until ${valid}.\nPayment terms: 30 days from invoice date.\n\nSincerely,\n${company}`:
          `Estimado ${client},\n\nPor medio de la presente compartimos la cotizaci\u00f3n para los siguientes servicios:\n\n${services}\n\nMonto total: USD ${total}\n\nEsta cotizaci\u00f3n tiene una validez hasta el ${valid}.\nT\u00e9rminos de pago: 30 d\u00edas fecha factura.\n\nAtentamente,\n${company}`;
      };
      const renderLines=()=>{
        dialog.querySelector('[data-lines]').innerHTML=lines.map((row,index)=>`<div class="com-line"><span>${esc(row.servicio)}</span><span>USD ${number(row.precio)}</span><button type="button" class="secondary" data-remove="${index}" aria-label="Quitar servicio">\u00d7</button></div>`).join('');
        dialog.querySelectorAll('[data-remove]').forEach(button=>button.onclick=()=>{lines.splice(Number(button.dataset.remove),1);renderLines();this.dirty=true;});
        dialog.querySelector('[data-total]').textContent='Total: USD '+number(lines.reduce((sum,row)=>sum+Number(row.precio),0));text();
      };
      const keys=['cliente','continente','pais','puerto'];
      const update=()=>{
        keys.slice(1).forEach((key,index)=>{const rows=prices.filter(row=>keys.slice(0,index+1).every(k=>!form.elements[k].value||row[k]===form.elements[k].value));dialog.querySelector(`#com-list-dialog-${key}`).innerHTML=[...new Set(rows.map(r=>r[key]).filter(Boolean))].map(value=>`<option value="${esc(value)}"></option>`).join('');});
        const rows=prices.filter(row=>form.elements.cliente.value && keys.every(key=>!form.elements[key].value || row[key]===form.elements[key].value));
        dialog.querySelector('[data-price]').innerHTML='<option value="">Seleccione...</option>'+rows.map(row=>`<option value="${row.id}">${esc(row.servicio)} / USD ${number(row.precio)}</option>`).join('');
      };
      keys.forEach((key,index)=>form.elements[key].onchange=()=>{keys.slice(index+1).forEach(k=>form.elements[k].value='');lines.length=0;update();renderLines();});
      form.elements.idioma.onchange=text;form.elements.validez.onchange=text;
      dialog.querySelector('[data-action=add-line]').onclick=()=>{
        const row=prices.find(r=>String(r.id)===dialog.querySelector('[data-price]').value);if(!row)return;
        if(lines.length>=4){dialog.querySelector('[data-error]').textContent='La cotizaci\u00f3n admite hasta cuatro servicios.';return;}
        if(lines.some(r=>r.id===row.id))return;lines.push(row);renderLines();this.dirty=true;
      };
      dialog.querySelector('[data-action=reset-text]').onclick=()=>{if(confirm('\u00bfReemplazar el texto con los datos actuales?'))text();};
      for(const fmt of ['word','pdf'])dialog.querySelector(`[data-action=preview-${fmt}]`).onclick=async()=>{
        try {
          const ticket=await this.request('/comercial/cotizaciones/export-ticket','POST',{quotation_number:quoteNumber,cliente:form.elements.cliente.value,servicio:lines.map(r=>r.servicio).join(', '),idioma:form.elements.idioma.value,texto:form.elements.texto.value});
          await this.download(this.url(`/comercial/cotizaciones/export/${fmt}`,{ticket:ticket.ticket,request_user:this.config.headers['X-User'],request_role:this.config.headers['X-User-Role']}),`cotizacion.${fmt==='word'?'docx':'pdf'}`);
        }catch(error){dialog.querySelector('[data-error]').textContent=error.message;}
      };
      this.bindSave(dialog,async data=>{
        if(!lines.length)throw new Error('Agregue al menos un servicio.');
        const payload={cliente:data.get('cliente'),continente:data.get('continente'),pais:data.get('pais'),puerto:data.get('puerto'),idioma:data.get('idioma'),validez:Number(data.get('validez')),status:'PENDIENTE',servicio:lines.map(r=>r.servicio).join(', '),precio:lines.reduce((sum,r)=>sum+Number(r.precio),0),texto_cotizacion:data.get('texto')};
        lines.forEach((row,index)=>{payload[`servicio_${index+1}`]=row.servicio;payload[`precio_${index+1}`]=Number(row.precio);});
        await this.request('/comercial/cotizaciones','POST',payload);
      });update();text();
    }
  }
  window.SOMCommercial={mount(root,config){instance?.destroy();instance=new Workspace(root,config);return instance.start();},canLeave(){return instance?.canLeave()??true;},destroy(){instance?.destroy();instance=null;}};
  window.addEventListener('beforeunload',event=>{if(instance?.dirty){event.preventDefault();event.returnValue='';}});
})();
