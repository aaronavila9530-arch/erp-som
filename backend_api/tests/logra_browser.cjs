const {chromium}=require('C:/Users/aaron/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('fs'),path=require('path'),assert=require('assert');
const root=path.resolve(__dirname,'../..');
const script=fs.readFileSync(path.join(root,'backend_api/assets/logra/logra.js'),'utf8');
const css=fs.readFileSync(path.join(root,'backend_api/assets/logra/logra.css'),'utf8');
const forms=JSON.parse(fs.readFileSync(path.join(root,'backend_api/services/logra_web_catalog.json'),'utf8'));
const shell=fs.readFileSync(path.join(root,'backend_api/routers/som_web.py'),'utf8').match(/<style>([\s\S]*?)<\/style>/)[1];
async function main(){
  const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
  try{
    const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[],writes=[];
    let permissions={view:true,create:true,edit:true},conflict=false;
    let payload={report:{id:1,title:'ONG - '+forms[0].title,form_slug:forms[0].slug,status:'Pending',version:1,created_by:'desktop',agenda_items:[{date_iso:'2026-10-19',start_time:'09:01',end_time:'10:00',topic:'Reunion de operaciones',person:'Persona QA',place:'Puerto',status:'Pendiente',custom:'Preservar'}],agenda_notes:'Notas originales'},answers:[{form_slug:forms[0].slug,section:'critical_questions',item_key:'1',form_title:forms[0].title,question_text:forms[0].critical_questions[0].question,bullets:['Observacion original']}],attachments:[],revision:'r1'};
    page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept());
    await page.route('http://logra.test/**',async route=>{
      const req=route.request(),u=new URL(req.url()),p=u.pathname,method=req.method();const send=data=>route.fulfill({json:data});
      if(p==='/')return route.fulfill({contentType:'text/html; charset=utf-8',body:`<meta charset="utf-8"><style>${shell}\nbody{display:block;margin:0;padding:12px}#content{min-width:0}${css}</style><main id="content"></main><script>${script}</script>`});
      if(p.includes('/queue-icon/'))return route.fulfill({contentType:'image/svg+xml',body:fs.readFileSync(path.join(root,'backend_api/assets/icons/lucide',path.basename(p)),'utf8')});
      if(p.endsWith('/bootstrap'))return send({forms,permissions,scope:'shared'});
      if(p.endsWith('/logra'))return send({data:[{...payload.report,answer_count:payload.answers.length,agenda_count:1,attachment_count:0,updated_at:'2026-10-19'}],total:1});
      if(p.endsWith('/1')&&method==='GET')return send(payload);
      if(p.endsWith('/1')&&method==='PATCH'){
        const body=req.postDataJSON();writes.push(body);
        if(conflict)return route.fulfill({status:409,json:{detail:'Conflicto con cambios de escritorio'}});
        for(const a of body.answers){const i=payload.answers.findIndex(x=>x.form_slug===a.form_slug&&x.section===a.section&&x.item_key===a.item_key);if(i>=0)payload.answers[i]={...payload.answers[i],...a};else payload.answers.push(a);}
        if(body.agenda_items)payload.report.agenda_items=body.agenda_items;
        if(body.agenda_notes!==undefined)payload.report.agenda_notes=body.agenda_notes;
        payload.report.version++;payload.revision='r'+payload.report.version;return send(payload);
      }
      if(p.endsWith('/improve'))return send({text:'Propuesta mejorada de PORTIA'});
      if(p.endsWith('/history'))return send({data:[{id:2,version:1,saved_by:'desktop',created_at:'2026-10-19T08:00'}]});
      if(p.endsWith('/history/2'))return send(payload);
      if(p.endsWith('/executive'))return send({text:'Resumen ejecutivo basado en evidencia de prueba',answer_count:1});
      return route.fulfill({status:404,json:{detail:'Unknown fixture '+p}});
    });
    async function mount(){await page.goto('http://logra.test/');await page.evaluate(()=>SOMLogra.mount(document.getElementById('content'),{user:'qa',headers:()=>({'Content-Type':'application/json'})}));await page.locator('[data-open]').waitFor();}
    await mount();fs.mkdirSync(path.join(root,'tmp/logra-qa'),{recursive:true});
    for(const width of [1440,800,390]){await page.setViewportSize({width,height:1000});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`List overflow ${width}`);await page.screenshot({path:path.join(root,`tmp/logra-qa/list-${width}.png`),fullPage:true});}
    await page.locator('[data-open]').click();await page.locator('[data-bullet]').first().waitFor();
    for(const width of [1440,800,390]){await page.setViewportSize({width,height:1000});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`Editor overflow ${width}`);await page.screenshot({path:path.join(root,`tmp/logra-qa/editor-${width}.png`),fullPage:true});}
    await page.setViewportSize({width:1440,height:1000});
    await page.locator('[data-bullet]').first().fill('Respuesta desde web');
    await page.locator('[data-act=next-question]').click();await page.locator('[data-act=prev-question]').click();assert.equal(await page.locator('[data-bullet]').first().inputValue(),'Respuesta desde web');
    await page.locator('[data-act=save]').click();await page.getByText('Guardado correctamente.',{exact:true}).waitFor();
    assert(!('agenda_items' in writes.at(-1)));assert(!('agenda_notes' in writes.at(-1)));
    await page.locator('[data-ai]').first().click();await page.locator('[data-apply]').click();assert.equal(await page.locator('[data-bullet]').first().inputValue(),'Propuesta mejorada de PORTIA');
    conflict=true;await page.locator('[data-act=save]').click();await page.getByText('Conflicto con cambios de escritorio',{exact:true}).waitFor();assert.equal(await page.locator('[data-bullet]').first().inputValue(),'Propuesta mejorada de PORTIA');
    assert(await page.evaluate(()=>localStorage.getItem('som-logra:qa:1')!==null));
    await page.locator('[data-act=back]').click();await page.locator('[data-open]').click();await page.locator('[data-bullet]').first().waitFor();
    assert.equal(await page.locator('[data-bullet]').first().inputValue(),'Propuesta mejorada de PORTIA');
    // Start a clean fixture to verify agenda preservation independently of conflicts.
    await page.evaluate(()=>{SOMLogra.destroy();localStorage.clear();});conflict=false;await mount();await page.locator('[data-open]').click();await page.locator('[data-act=agenda]').click();await page.locator('[data-meeting]').click();
    await page.locator('dialog input[name=topic]').fill('Reunion ajustada');await page.locator('dialog button[type=submit]').click();await page.locator('[data-act=save]').click();await page.getByText('Guardado correctamente.',{exact:true}).waitFor();
    assert.equal(writes.at(-1).agenda_items[0].custom,'Preservar');assert.equal(writes.at(-1).answers.length,0);
    await page.locator('[data-act=calendar]').click();await page.locator('[data-month]').fill('2026-10');await page.locator('.lw-calendar').waitFor();await page.screenshot({path:path.join(root,'tmp/logra-qa/calendar.png'),fullPage:true});
    await page.locator('[data-act=history]').click();await page.locator('[data-revision]').click();await page.locator('[data-snapshot]').filter({hasText:'Reunion ajustada'}).waitFor();await page.locator('dialog header button').click();
    await page.locator('[data-act=back]').click();await page.locator('[data-select]').check();await page.locator('[data-act=executive]').click();await page.getByText('Resumen ejecutivo basado en evidencia de prueba',{exact:true}).waitFor();await page.locator('dialog header button').click();
    permissions={view:true,edit:false,create:false};await mount();assert(await page.locator('[data-act=new]').isDisabled());await page.locator('[data-open]').click();assert(await page.locator('[data-act=save]').isDisabled());assert.equal(await page.locator('[data-ai]').count(),0);assert(await page.locator('[data-bullet]').first().getAttribute('readonly')!==null);
    assert.deepEqual(errors,[]);console.log('PASS LOGRA: responsive list/editor, partial saves, draft recovery, conflict protection, AI preview, agenda/calendar/history, read-only permissions.');
  }finally{await browser.close();}
}
main().catch(e=>{console.error(e);process.exitCode=1;});
