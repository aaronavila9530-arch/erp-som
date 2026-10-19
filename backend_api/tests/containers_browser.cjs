const {chromium} = require('C:/Users/aaron/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs = require('fs'), path = require('path'), assert = require('assert'), cp = require('child_process');
const root = path.resolve(__dirname,'../..');
const sections = JSON.parse(cp.execFileSync('python',['-c','import json; from backend_api.services.container_web_fields import SECTIONS; print(json.dumps(SECTIONS))'],{cwd:root,encoding:'utf8'}));
const script = fs.readFileSync(path.join(root,'backend_api/assets/containers/containers.js'),'utf8');
const css = fs.readFileSync(path.join(root,'backend_api/assets/containers/containers.css'),'utf8');
const somSource = fs.readFileSync(path.join(root,'backend_api/routers/som_web.py'),'utf8');
const shell = somSource.match(/<style>([\s\S]*?)<\/style>/)[1];
async function run() {
  const browser = await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
  try {
    const page = await browser.newPage({viewport:{width:1440,height:1000}}), errors=[], writes=[];
    let permissions = {view:true,create:true,edit:true,approve:true}, conflict=false;
    let report = {id:1,linked_report_number:'QA-001',report_no:'MSLU1234567',vessel:'QA VESSEL',user:'surveyor',status:'Pending for review',customer:'QA Client',created_at:'2026-10-19',remarks:'Original narrative',contact_datetime:'October 19, 2026 at 09:01',init_to:'2026-10-19 09:01:00'};
    page.on('pageerror', e=>errors.push(e.message)); page.on('dialog',d=>d.accept());
    await page.route('http://containers.test/**',async route=>{
      const req=route.request(), url=new URL(req.url()), p=url.pathname, method=req.method();
      const send = data=>route.fulfill({json:data});
      if(p==='/')return route.fulfill({contentType:'text/html',body:`<style>${shell}\nbody{display:block;padding:12px;margin:0}#content{min-width:0}${css}</style><main id="content"></main><script>${script}</script>`});
      if(p.includes('/queue-icon/'))return route.fulfill({contentType:'image/svg+xml',body:fs.readFileSync(path.join(root,'backend_api/assets/icons/lucide',path.basename(p)),'utf8')});
      if(p.endsWith('/bootstrap'))return send({sections,permissions,company:'MCI-CR'});
      if(p.endsWith('/services'))return send({data:[{num_informe:'QA-NEW',cliente:'QA Client',puerto:'Caldera',buque_contenedor:'QA VESSEL'}],more:false});
      if(p.endsWith('/improve'))return send({text:'Improved narrative for review'});
      if(p.endsWith('/containers') && method==='GET')return send({data:[report],total:1});
      if(p.endsWith('/1') && method==='GET')return send({data:report,version:'v1'});
      if(method!=='GET'){
        const body=req.postDataJSON(); writes.push({method,body});
        if(conflict)return route.fulfill({status:409,json:{detail:'El informe cambio en escritorio. Conserve el borrador.'}});
        report={...report,...body.fields,status:body.submit?'Pending for review':body.status||report.status};
        return send({data:report,version:'v2'});
      }
      return route.fulfill({status:404,json:{detail:'Fixture missing: '+p}});
    });
    async function mount(){await page.goto('http://containers.test/');await page.evaluate(()=>SOMContainers.mount(document.getElementById('content'),{company:'MCI-CR',headers:()=>({'Content-Type':'application/json','X-User':'qa','X-Role':'admin'})}));}
    await mount(); await page.locator('[data-open]').waitFor();
    fs.mkdirSync(path.join(root,'tmp/containers-qa'),{recursive:true});
    for(const width of [1440,800,390]){
      await page.setViewportSize({width,height:1000});
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`list overflow ${width}`);
      await page.screenshot({path:path.join(root,`tmp/containers-qa/list-${width}.png`),fullPage:true});
    }
    await page.locator('[data-open]').click(); await page.locator('[data-field=report_no]').waitFor();
    assert.equal(await page.locator('[data-field=report_no]').inputValue(),'MSLU1234567');
    assert(await page.locator('[data-field=linked_report_number]').isDisabled());
    for(const width of [1440,800,390]){
      await page.setViewportSize({width,height:1000});
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`editor overflow ${width}`);
      await page.screenshot({path:path.join(root,`tmp/containers-qa/editor-${width}.png`),fullPage:true});
    }
    await page.setViewportSize({width:1440,height:1000});
    await page.locator('[data-section="1"]').click();
    assert.equal(await page.locator('[data-field=contact_datetime]').inputValue(),'October 19, 2026 at 09:01');
    await page.locator('[data-section="0"]').click();
    await page.locator('[data-field=report_no]').fill('MSLU7654321');
    await page.locator('[data-section="4"]').click();
    await page.locator('[data-field=remarks]').fill('Draft from web');
    await page.locator('[data-ai=remarks]').click(); await page.locator('dialog').waitFor();
    await page.locator('[data-cancel]').click();
    assert.equal(await page.locator('[data-field=remarks]').inputValue(),'Draft from web');
    await page.locator('[data-ai=remarks]').click(); await page.locator('[data-apply]').click();
    assert.equal(await page.locator('[data-field=remarks]').inputValue(),'Improved narrative for review');
    conflict=true;
    await page.locator('[data-action=save]').click();
    await page.getByText('El informe cambio en escritorio. Conserve el borrador.',{exact:true}).waitFor();
    assert.equal(await page.locator('[data-field=remarks]').inputValue(),'Improved narrative for review');
    assert.equal(writes.at(-1).body.fields.report_no,'MSLU7654321');
    assert(!('vessel' in writes.at(-1).body.fields));
    assert(!('contact_datetime' in writes.at(-1).body.fields));
    assert(!('init_to' in writes.at(-1).body.fields));
    conflict=false;
    await page.locator('[data-action=save]').click(); await page.getByText('Informe guardado.',{exact:true}).waitFor();
    await page.locator('[data-action=approve]').click();
    await page.getByText('Approved',{exact:true}).waitFor();
    assert(await page.locator('[data-field=report_no]').isDisabled());
    assert.equal(await page.locator('[data-action=save]').count(),0);
    permissions={view:true,create:false,edit:false,approve:false}; await mount();
    assert(await page.locator('[data-action=new]').isHidden());
    await page.locator('[data-open]').click(); await page.locator('[data-field=report_no]').waitFor();
    assert(await page.locator('[data-field=report_no]').isDisabled());
    assert.equal(await page.locator('[data-action=approve]').count(),0);
    // Exercise the actual shell's tab wiring separately from the grid regression suite.
    const integration = somSource.slice(somSource.indexOf('    let informesView ='),somSource.indexOf('    async function refreshSummary()'));
    await page.evaluate(()=>{
      SOMContainers.destroy();
      window.$=id=>document.getElementById(id); window.headers=()=>({'Content-Type':'application/json'});
      window.selectedCompany=()=> 'MCI-CR'; window.session={usuario:'qa',rol:'admin'};
      window.SOMTally={destroy(){},canLeave(){return true;},mount(root){root.innerHTML='<p>Tally fixture</p>';}};
    });
    await page.addScriptTag({content:integration+'\nrenderInformesTally();'});
    await page.getByText('Tally fixture',{exact:true}).waitFor();
    await page.locator('[data-report-view=containers]').click(); await page.locator('[data-open]').waitFor();
    await page.locator('[data-report-view=tally]').click(); await page.getByText('Tally fixture',{exact:true}).waitFor();
    assert.deepEqual(errors,[]);
    console.log('PASS: desktop/tablet/mobile, edit across sections, AI preview, conflict preservation, partial PATCH, approval/read-only roles; no production writes.');
  } finally { await browser.close(); }
}
run().catch(error=>{console.error(error);process.exitCode=1;});
