(() => {
  let active;
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const fields={imo:'IMO',length_and_tonnage:'Length overall and tonnage',cargo:'Cargo',period_start:'Period investigated - from',period_end:'Period investigated - to',issue_date:'Date of issue',report_status:'Report status',master:'Master',chief_officer:'Chief officer',surveyor:'Surveyor / signatory'};
  const defaultGroups={instructions:['work','limitations','chronology','representatives'],findings:['visual','provided','missing'],conclusion:[],enclosure:[]};
  function canLeave(){return !active || (!active.busy && (!active.dirty || confirm('There are unsaved changes. Discard them?')));}
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
      catch(e){if(expired)throw Error('The request timed out. Your text is still here. Check the report before saving again.');throw e;}
      finally{clearTimeout(timer);s.abort.signal.removeEventListener('abort',cancel);}
    }
    async function request(path,method='GET',body){
      const r=await fetchBounded(path,{method,headers:{...opts.headers(),'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});
      const d=await r.json().catch(()=>null);if(!r.ok)throw Error(typeof d?.detail==='string'?d.detail:'The request could not be completed. Check the fields.');return d;
    }
    async function run(fn){if(s.busy)return;s.busy=true;root.inert=true;try{await fn();}catch(e){if(live()&&e.name!=='AbortError')$('#mci-error').textContent=e.message;}finally{s.busy=false;root.inert=false;}}
    function shell(mode,body){
      if(!live())return;
      root.innerHTML=`<header class="cert-head"><h2>${esc({vessel:'Vessel Survey',condition:'Vessel Condition Survey',cargo:'Cargo Condition Survey'}[opts.kind])}</h2><span>MCI-CR</span></header><nav class="cert-workflows">${s.boot?.permissions.create?`<button data-create aria-pressed="${mode==='create'}">Create</button>`:''}<button data-review aria-pressed="${mode==='review'}">Review</button></nav><p id="mci-error" role="alert"></p>${body}`;
      if(s.boot && !s.boot.ready){root.querySelectorAll('nav button').forEach(b=>b.disabled=true);return;}
      if($('[data-create]'))$('[data-create]').onclick=()=>{if(canLeave()){s.dirty=false;run(()=>services());}};
      $('[data-review]').onclick=()=>{if(canLeave()){s.dirty=false;run(list);}};
    }
    async function list(){
      const d=await request(`/informes/mci-surveys?kind=${opts.kind}&q=${encodeURIComponent(s.q)}&offset=${s.offset}`);if(!live())return;
      shell('review',`<form class="cert-tools" id="mci-search"><input name="q" aria-label="Search reports" placeholder="Report, vessel or client" value="${esc(s.q)}"><button>Search</button></form><div class="cert-scroll"><table><thead><tr><th>Report</th><th>Vessel</th><th>Client</th><th>Status</th><th></th></tr></thead><tbody>${d.data.map(r=>`<tr><td>${esc(r.report_number)}</td><td>${esc(r.vessel)}</td><td>${esc(r.requested_by)}</td><td>${esc(r.status)}</td><td><button data-open="${r.id}">Review report</button></td></tr>`).join('')||'<tr><td colspan="5">No reports</td></tr>'}</tbody></table></div><button data-prev ${!s.offset?'disabled':''}>Previous</button><button data-next ${!d.more?'disabled':''}>Next</button>`);
      $('#mci-search').onsubmit=e=>{e.preventDefault();s.q=new FormData(e.target).get('q');s.offset=0;run(list);};
      $('[data-prev]').onclick=()=>{s.offset=Math.max(0,s.offset-50);run(list);};$('[data-next]').onclick=()=>{s.offset+=50;run(list);};
      root.querySelectorAll('[data-open]').forEach(b=>b.onclick=()=>run(async()=>editor(await request('/informes/mci-surveys/'+b.dataset.open))));
    }
    async function services(q='',offset=0){
      const d=await request(`/informes/certificates/services?q=${encodeURIComponent(q)}&offset=${offset}`);if(!live())return;
      shell('create',`<form class="cert-tools" id="mci-service-search"><input name="q" placeholder="Search services" aria-label="Search services" value="${esc(q)}"><button>Search</button></form><div class="cert-scroll"><table><tbody>${d.data.map((r,i)=>`<tr><td>${esc(r.num_informe)}</td><td>${esc(r.buque_contenedor)}</td><td>${esc(r.cliente)}</td><td><button data-service="${i}">Create report</button></td></tr>`).join('')||'<tr><td>No services</td></tr>'}</tbody></table></div><button data-prev ${!offset?'disabled':''}>Previous</button><button data-next ${!d.more?'disabled':''}>Next</button>`);
      $('#mci-service-search').onsubmit=e=>{e.preventDefault();run(()=>services(new FormData(e.target).get('q')));};
      $('[data-prev]').onclick=()=>run(()=>services(q,Math.max(0,offset-50)));$('[data-next]').onclick=()=>run(()=>services(q,offset+50));
      root.querySelectorAll('[data-service]').forEach(b=>b.onclick=()=>{const v=d.data[+b.dataset.service];editor({data:{service_id:v.consec,kind:opts.kind,report_number:v.num_informe,vessel:v.buque_contenedor,requested_by:v.cliente,location:[v.puerto,v.pais].map(x=>String(x||'').trim()).filter(Boolean).join(', '),content:{hierarchy_version:2,report_status:'Draft',sections:{}}}});s.dirty=true;});
    }
    function editor(payload){
      if(!live())return;const row=payload.data,c=structuredClone(row.content),editable=row.id?s.boot.permissions.edit&&row.status!=='Approved':s.boot.permissions.create;
      c.sections ||= {};
      const groups=s.boot.groups||defaultGroups,parents=Object.fromEntries(Object.entries(groups).flatMap(([parent,children])=>children.map(k=>[k,parent])));
      if((c.hierarchy_version||1)===1){for(const [parent,children] of Object.entries(groups)){if(children.some(k=>c.sections[k]?.enabled))(c.sections[parent]||={enabled:false,blocks:[]}).enabled=true;}}
      c.hierarchy_version=2;
      shell(row.id?'review':'create',`<p><strong>${esc(row.report_number)}</strong> · ${esc(row.vessel)} · ${esc(row.requested_by)}</p><form id="mci-form" lang="en"><div class="cert-tools">${editable?'<button type="submit">Save draft</button><button type="button" data-submit>Submit for review</button>':''}${row.id?'<button type="button" data-export="word">Word</button><button type="button" data-export="pdf">PDF</button>':''}${row.id&&s.boot.permissions.approve?'<button type="button" data-status="Approved">Approve</button><button type="button" data-status="Rejected">Reject</button>':''}<span id="mci-save-state" role="status"></span></div><fieldset ${!editable?'disabled':''}><div class="cert-fields"><label>Location<input id="mci-location" readonly value="${esc(row.location||'')}" placeholder="Not set in the linked service"></label>${Object.entries(fields).map(([k,label])=>`<label>${label}<input name="${k}" type="${k==='issue_date'?'date':k.startsWith('period_')?'datetime-local':'text'}" value="${esc(c[k]||'')}" maxlength="${k==='cargo'?3000:1000}"></label>`).join('')}</div><div id="mci-sections"></div></fieldset></form>`);
      const mark=()=>{s.dirty=true;$('#mci-save-state').textContent='Unsaved changes';};
      function sections(){
        if(c.sections.enclosure?.enabled){
          const enclosure=c.sections.enclosure;
          enclosure.blocks=[{text:enclosure.blocks.map(b=>b.text).filter(Boolean).join('\n')}];
        }
        const option=(k,child=false)=>`<label class="mci-section-option ${child?'mci-child-option':'mci-parent-option'}"><input type="checkbox" data-enable="${k}" ${c.sections[k]?.enabled?'checked':''} ${child&&!c.sections[parents[k]]?.enabled?'disabled':''}><span>${esc(s.boot.sections[k])}</span></label>`;
        const textEditor=(k,label)=>{const sec=c.sections[k]||{blocks:[]};return `<section class="mci-text-section"><header><h3>${esc(label)}</h3><button type="button" data-add="${k}" title="Add text" aria-label="Add text to ${esc(label)}" ${sec.blocks.length>=100?'disabled':''}>+</button></header>${sec.blocks.map((b,i)=>`<div class="mci-text-block"><label>Text ${i+1}<textarea data-block="${k}" data-index="${i}" maxlength="30000">${esc(b.text)}</textarea></label><button type="button" data-remove="${k}" data-index="${i}" title="Remove text" aria-label="Remove text ${i+1}">&#8722;</button></div>`).join('')}</section>`;};
        $('#mci-sections').innerHTML=`<h3>Report sections</h3><div class="mci-section-options mci-hierarchy">${Object.entries(groups).map(([parent,children])=>`<div class="mci-section-group">${option(parent)}<div class="mci-subsections">${children.map(k=>option(k,true)).join('')}</div></div>`).join('')}</div><div class="mci-section-editors">${Object.entries(groups).filter(([parent])=>c.sections[parent]?.enabled).map(([parent,children])=>`<div class="mci-editor-group"><h3 class="mci-group-title">${esc(s.boot.sections[parent])}</h3>${children.length?(c.sections[parent]?.blocks.length?textEditor(parent,'Section introduction'):'')+children.filter(k=>c.sections[k]?.enabled).map(k=>textEditor(k,s.boot.sections[k])).join(''):textEditor(parent,s.boot.sections[parent])}</div>`).join('')}</div>`;
        root.querySelectorAll('[data-enable]').forEach(b=>b.onchange=()=>{const key=b.dataset.enable,sec=c.sections[key] ||= {enabled:false,blocks:[]};sec.enabled=b.checked;if(sec.enabled&&!sec.blocks.length&&!(groups[key]?.length))sec.blocks.push({text:''});mark();sections();root.querySelector(`[data-enable="${key}"]`)?.focus({preventScroll:true});});
        const enclosureEditor=root.querySelector('[data-add="enclosure"]')?.closest('.mci-text-section');
        if(enclosureEditor)enclosureEditor.innerHTML=`<label for="mci-picture-link">Picture link</label><textarea id="mci-picture-link" data-block="enclosure" data-index="0" rows="2" maxlength="30000" placeholder="https://">${esc(c.sections.enclosure.blocks[0].text)}</textarea>`;
        root.querySelectorAll('[data-block]').forEach(t=>t.oninput=()=>{c.sections[t.dataset.block].blocks[+t.dataset.index].text=t.value;mark();});
        root.querySelectorAll('[data-add]').forEach(b=>b.onclick=()=>{c.sections[b.dataset.add].blocks.push({text:''});mark();sections();});
        root.querySelectorAll('[data-remove]').forEach(b=>b.onclick=()=>{const a=c.sections[b.dataset.remove].blocks,i=+b.dataset.index;if(a[i].text.trim()&&!confirm('Remove this text?'))return;a.splice(i,1);mark();sections();});
      }
      sections();root.querySelectorAll('#mci-form input[name]').forEach(el=>el.oninput=()=>{c[el.name]=el.value||(['issue_date','period_start','period_end'].includes(el.name)?null:'');mark();});
      async function save(submit){if(!editable)return;await run(async()=>{const d=await request('/informes/mci-surveys'+(row.id?'/'+row.id:''),row.id?'PATCH':'POST',{kind:opts.kind,service_id:row.service_id,content:c,version:payload.version,submit});if(live()){s.dirty=false;editor(d);$('#mci-save-state').textContent='Saved';}});}
      $('#mci-form').onsubmit=e=>{e.preventDefault();save(false);};if($('[data-submit]'))$('[data-submit]').onclick=()=>save(true);
      root.querySelectorAll('[data-status]').forEach(b=>b.onclick=()=>{if(s.dirty){$('#mci-error').textContent='Save changes before reviewing.';return;}if(!confirm('Confirm status change?'))return;run(async()=>editor(await request(`/informes/mci-surveys/${row.id}/status`,'POST',{version:payload.version,status:b.dataset.status})));});
      root.querySelectorAll('[data-export]').forEach(b=>b.onclick=()=>{if(s.dirty){$('#mci-error').textContent='Save changes before downloading.';return;}run(async()=>{const r=await fetch(`/informes/mci-surveys/${row.id}/export/${b.dataset.export}`,{headers:opts.headers(),signal:s.abort.signal});if(!r.ok)throw Error('The document could not be generated. The saved report has not changed.');const url=URL.createObjectURL(await r.blob()),a=document.createElement('a');a.href=url;a.download=`Survey_${row.id}.${b.dataset.export==='word'?'docx':'pdf'}`;a.click();setTimeout(()=>URL.revokeObjectURL(url),30000);});});
    }
    shell('review','');await run(async()=>{s.boot=await request('/informes/mci-surveys/bootstrap');if(!s.boot.ready){shell('review','<p>This module is not enabled yet.</p>');return;}await list();});
  }
  window.SOMMCISurveys={mount,canLeave,destroy};
})();
