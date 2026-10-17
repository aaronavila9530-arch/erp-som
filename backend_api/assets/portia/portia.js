(function(){
 'use strict';let active;
 const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const money=v=>Number(v||0).toLocaleString('es-CR',{minimumFractionDigits:2,maximumFractionDigits:2});
 function mount(root,api){
  active?.destroy();let dead=false,busy=false,evidence=null,conversation=[],revision=0;
  const today=new Intl.DateTimeFormat('en-CA',{timeZone:'America/Costa_Rica',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
  root.innerHTML=`<section class="portia-workspace"><div class="portia-top"><div><img src="/som/queue-icon/file-pen-line.svg" alt=""><strong>PORTIA</strong><span>${esc(api.company)}</span></div><button id="pNew">Nueva consulta</button></div>
   <div class="portia-filters"><fieldset id="pScopes"><legend>Alcance</legend><label><input type="radio" name="pScope" value="erp" checked> Datos SOM</label><label><input type="radio" name="pScope" value="qa"> Manual SOM</label><label><input type="radio" name="pScope" value="general_chat"> General</label></fieldset>
   <label>Desde<input id="pStart" type="date" value="${today.slice(0,8)}01"></label><label>Hasta<input id="pEnd" type="date" value="${today}"></label><button id="pRefresh">Actualizar datos</button></div>
   <div id="pNotice" role="status"></div><div class="portia-layout"><div class="portia-conversation"><div id="pMessages" role="log" aria-live="polite"><div class="portia-empty"><h2>Consulta ejecutiva</h2><div class="portia-prompts"><button data-prompt="Explica mis obligaciones y gastos del periodo. ¿Qué beneficiarios concentran el importe y qué cambió respecto al periodo anterior?">Gastos y variaciones</button><button data-half="1" data-prompt="¿Por qué es alta esta quincena? Desglosa las categorías, beneficiarios y pendientes; separa pagos aplicados de borradores.">Primera quincena</button><button data-half="2" data-prompt="¿Por qué es alta esta quincena? Desglosa las categorías, beneficiarios y pendientes; separa pagos aplicados de borradores.">Segunda quincena</button><button data-prompt="¿A qué clientes he facturado más y dónde tengo más actividad? Compara con el periodo anterior y distingue ventas de cantidad de servicios.">Ventas y actividad</button></div></div></div>
   <form id="pForm"><label for="pQuestion">Pregunta a PORTIA</label><textarea id="pQuestion" rows="3" maxlength="4000" placeholder="¿Por qué subieron los gastos? ¿Qué compone la quincena? ¿A qué cliente vendimos más?" required></textarea><div class="portia-compose-actions"><span id="pMode">Solo consulta</span><button type="submit" id="pSend">Consultar</button></div></form></div>
   <aside class="portia-evidence"><div class="portia-evidence-title"><h2>Evidencia</h2><button id="pExport" disabled>Descargar CSV</button></div><div id="pEvidence"></div></aside></div></section>`;
  const $=s=>root.querySelector(s),scope=()=>$('input[name=pScope]:checked').value;
  function notice(text,error=false){if(dead)return;$('#pNotice').textContent=text;$('#pNotice').className=error?'portia-error':'portia-notice';}
  function renderEvidence(){
   if(dead)return;
   $('#pExport').disabled=!evidence||!Object.keys(evidence.sections||{}).length;
   if(!evidence){$('#pEvidence').textContent=scope()==='erp'?'Sin datos cargados.':'Sin datos ERP en este alcance.';return;}
   $('#pEvidence').innerHTML=`<p class="portia-period">${esc(evidence.start)} al ${esc(evidence.end)}<br>Comparación: ${esc(evidence.previous_start)} al ${esc(evidence.previous_end)}</p>`+
    (evidence.warnings||[]).map(w=>`<p class="portia-warning">${esc(w)}</p>`).join('')+
    Object.values(evidence.sections||{}).map(s=>`<details class="portia-source" open><summary>${esc(s.name)} <span>${s.count} registros</span></summary><p>${esc(s.basis)}</p>
     <div class="portia-totals">${s.totals.map(t=>`<div><small>${esc(t.currency)}</small><strong>${money(t.amount)}</strong><span class="${t.change>0?'portia-up':'portia-down'}">${t.change>0?'+':''}${money(t.change)} vs anterior</span></div>`).join('')||'<span>Sin registros en este periodo</span>'}</div>
     <div class="portia-table-wrap"><table><thead><tr><th>Concepto</th><th>Moneda</th><th>Importe</th><th>Variación</th></tr></thead><tbody>${s.groups.map(g=>`<tr><td>${esc(g.label)}</td><td>${esc(g.currency)}</td><td>${money(g.amount)}</td><td>${money(g.change)}</td></tr>`).join('')}</tbody></table></div>
     <details><summary>Ver registros (${s.details.length} de ${s.count})</summary><div class="portia-table-wrap"><table><thead><tr><th>ID / referencia</th><th>Fecha</th><th>Beneficiario / cliente</th><th>Estado</th><th>Importe</th></tr></thead><tbody>${s.details.map(r=>`<tr><td>${esc(r.id)} · ${esc(r.reference)}</td><td>${esc(r.date)}</td><td>${esc(r.label)}</td><td>${esc(r.status)}</td><td>${esc(r.currency)} ${money(r.amount)}</td></tr>`).join('')}</tbody></table></div></details><small>Fuente: ${esc(s.source)} · ${esc(evidence.generated_at)}</small></details>`).join('');
  }
  function reset(){revision++;conversation=[];$('#pMessages').replaceChildren();evidence=null;renderEvidence();notice('');}
  function message(role,text){$('.portia-empty')?.remove();const article=document.createElement('article');article.className='portia-message '+role;const label=document.createElement('strong');label.textContent=role==='user'?'Tú':'PORTIA';const body=document.createElement('div');body.className='portia-answer';body.textContent=text;article.append(label,body);$('#pMessages').append(article);article.scrollIntoView({block:'nearest'});return article;}
  function lock(value){busy=value;$('#pSend').disabled=value;$('#pSend').textContent=value?'Consultando…':'Consultar';for(const element of root.querySelectorAll('.portia-filters input,.portia-filters button,#pNew,.portia-prompts button'))element.disabled=value;}
  async function refresh(){
   if(scope()!=='erp'){evidence=null;renderEvidence();return;}
   const ticket=revision;notice('Consultando fuentes…');
   try{const data=await api.get(`/portia/context?start=${$('#pStart').value}&end=${$('#pEnd').value}`);if(dead||ticket!==revision)return;evidence=data.data;renderEvidence();notice('');}
   catch(e){if(!dead&&ticket===revision)notice(e.message,true);}
  }
  $('#pForm').onsubmit=async event=>{
   event.preventDefault();if(busy)return;const question=$('#pQuestion').value.trim();if(!question)return;
   const ticket=revision;lock(true);notice('');message('user',question);
   try{
    const result=await api.post('/portia/ask',{question,scope:scope(),start:$('#pStart').value,end:$('#pEnd').value,history:conversation.slice(-8)});
    if(dead||ticket!==revision)return;
    conversation.push({role:'user',content:question},{role:'assistant',content:result.answer.slice(0,12000)});
    const article=message('assistant',result.answer);const copy=document.createElement('button');copy.textContent='Copiar respuesta';copy.onclick=()=>navigator.clipboard.writeText(result.answer).catch(()=>notice('No se pudo copiar.',true));article.append(copy);
    evidence=scope()==='erp'?result.context:null;renderEvidence();$('#pQuestion').value='';
    $('#pMode').textContent=result.mode==='openai'?'IA · fuentes del alcance seleccionado':'Análisis local · sin IA generativa';
    if(result.warning)notice(result.warning,true);
   }catch(e){if(!dead&&ticket===revision){message('assistant','No se pudo completar la consulta. Puedes reenviarla; el texto permanece abajo.');notice(e.message,true);}}
   finally{if(!dead){lock(false);$('#pQuestion').focus();}}
  };
  $('#pNew').onclick=()=>{reset();refresh();};$('#pRefresh').onclick=()=>{reset();refresh();};
  for(const input of root.querySelectorAll('.portia-filters input'))input.onchange=()=>{reset();refresh();};
  for(const button of root.querySelectorAll('[data-prompt]'))button.onclick=()=>{
   if(button.dataset.half){const half=Number(button.dataset.half),month=$('#pStart').value.slice(0,7),[y,m]=month.split('-').map(Number);$('#pStart').value=month+(half===1?'-01':'-16');$('#pEnd').value=month+'-'+(half===1?'15':String(new Date(y,m,0).getDate()));reset();refresh();}
   $('#pQuestion').value=button.dataset.prompt;$('#pQuestion').focus();
  };
  $('#pExport').onclick=()=>{
   const safe=value=>'"'+String(value??'').replace(/^[=+@-]/,"'$&").replace(/"/g,'""')+'"';
   const rows=[['Fuente','ID','Fecha','Nombre','Referencia','Moneda','Importe']];
   for(const section of Object.values(evidence.sections))for(const r of section.details)rows.push([section.source,r.id,r.date,r.label,r.reference,r.currency,r.amount]);
   const url=URL.createObjectURL(new Blob(['\uFEFF'+rows.map(r=>r.map(safe).join(',')).join('\r\n')],{type:'text/csv;charset=utf-8'}));
   const a=document.createElement('a');a.href=url;a.download=`PORTIA-${api.company}-${evidence.start}-${evidence.end}-detalle-visible.csv`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  };
  active={destroy(){dead=true;revision++;}};refresh();
 }
 window.SOMPortia={mount,destroy(){active?.destroy();active=null;}};
})();
