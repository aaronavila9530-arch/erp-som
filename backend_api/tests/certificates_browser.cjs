const {chromium}=require('C:/Users/aaron/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('fs'),path=require('path'),assert=require('assert'),cp=require('child_process');
const root=path.resolve(__dirname,'../..');
const types=JSON.parse(cp.execFileSync('python',['-c','import json;from backend_api.services.certificate_web_fields import TYPES;print(json.dumps(TYPES))'],{cwd:root,encoding:'utf8'}));
const js=fs.readFileSync(path.join(root,'backend_api/assets/certificates/certificates.js'),'utf8');
const css=fs.readFileSync(path.join(root,'backend_api/assets/certificates/certificates.css'),'utf8');
async function main(){
  const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
  try{
    const page=await browser.newPage({viewport:{width:1440,height:1000}});
    const errors=[],writes=[];let conflict=false,permissions={view:true,create:true,edit:true,approve:true};
    const records=Object.fromEntries(Object.keys(types).map(k=>[k,{id:1,report_number:'QA-001',report_no:'QA-001',vessel:'QA VESSEL',flat_rack_container:'QA CONTAINER',status:'Pending for review',date:'2026-10-20',remarks:'Original',legacy:'Preserved'}]));
    page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept());
    await page.route('http://certificates.test/**',async route=>{
      const req=route.request(),url=new URL(req.url()),parts=url.pathname.split('/'),kind=parts[3];
      const send=data=>route.fulfill({json:data});
      if(url.pathname==='/')return route.fulfill({contentType:'text/html',body:`<style>body{margin:0;font:14px Arial} ${css}</style><main id="app"></main><script>${js}</script>`});
      if(kind==='bootstrap')return send({types,permissions,company:'MCI-CR'});
      if(kind==='grain-assist')return send({text:'Propuesta QA revisada'});
      if(kind==='services')return send({data:[{num_informe:'QA-NEW',buque_contenedor:'QA NEW VESSEL',cliente:'QA CLIENT',puerto:'Caldera',pais:'Costa Rica'}],more:false});
      if(req.method()==='GET'){
        if(parts.length===4)return send({data:[{...records[kind],customer:'QA CLIENT'}],total:1});
        return send({data:records[kind],version:'v1'});
      }
      const body=req.postDataJSON();writes.push({kind,body,method:req.method()});
      if(conflict)return route.fulfill({status:409,json:{detail:'Conflicto: otro usuario modifico el certificado.'}});
      records[kind]={...records[kind],...body.fields,status:body.status||(body.submit?'Pending for review':'Draft')};
      return send({data:records[kind],version:'v2'});
    });
    async function mount(){
      await page.goto('http://certificates.test/');
      await page.evaluate(()=>SOMCertificates.mount(document.getElementById('app'),{headers:()=>({'X-Company-Code':'MCI-CR'})}));
      await page.locator('[data-open]').waitFor();
    }
    await mount();
    const qaDir=fs.mkdtempSync(path.join(require('os').tmpdir(),'som-reports-'));
    for(const kind of Object.keys(types)){
      await page.locator(`[data-kind=${kind}]`).click();
      await page.locator('[data-open]').click();
      await page.locator('#cert-form').waitFor();
      assert.equal(await page.locator('#cert-format').isVisible(),false);
      assert.equal(await page.locator('#cert-approve').isVisible(),false);
      assert.equal(await page.evaluate(()=>SOMCertificates.canLeave()),true);
      assert.equal(await page.locator('#cert-save-state').textContent(),'');
      const fieldCount=types[kind].sections.flatMap(x=>x.fields).length;
      assert.equal(await page.locator('#cert-form [name]').count(),fieldCount);
      assert.equal(await page.locator('[name=date]').inputValue(),'20/10/2026');
      for(const width of [1440,800,390]){
        await page.setViewportSize({width,height:1000});
        assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`${kind} overflow ${width}`);
        await page.screenshot({path:path.join(qaDir,`${kind}-${width}.png`),fullPage:true});
      }
      await page.setViewportSize({width:1440,height:1000});
      const key=kind==='lashing'?'ratchet_quantity':kind==='sampling'?'hold_10_seal':'remarks';
      await page.locator(`[name=${key}]`).fill('00013');
      conflict=true;
      await page.locator('button[type=submit]').click();
      await page.getByText('Conflicto: otro usuario modifico el certificado.',{exact:true}).waitFor();
      assert.equal(await page.locator(`[name=${key}]`).inputValue(),'00013');
      assert.deepEqual(writes.at(-1).body.fields,{[key]:'00013'});
      conflict=false;
      await page.locator('#cert-submit').click();
      await page.getByText('Guardado',{exact:true}).waitFor();
      assert.equal(writes.at(-1).body.submit,true);
      await page.locator('[data-mode=review]').click();
      assert.equal(await page.locator('#cert-new').count(),0);
      await page.locator('[data-open]').click();
      assert(await page.locator(`[name=${key}]`).isDisabled());
      assert.equal(await page.locator('#cert-submit').count(),0);
      await page.locator('#cert-format').selectOption('pdf');
      await page.locator('#cert-approve').click();
      await page.getByText('Aprobado',{exact:true}).waitFor();
      assert(await page.locator(`[name=${key}]`).isDisabled());
      await page.locator('#cert-reject').click();
      await page.getByText('Rechazado',{exact:true}).waitFor();
      await page.locator('#cert-back').click();
      await page.locator('[data-mode=edit]').click();
      await page.locator('#cert-new').click();
      await page.locator('[data-service]').click();
      assert.equal(await page.locator(`[name=${types[kind].number}]`).inputValue(),'QA-NEW');
      await page.locator('button[type=submit]').click();
      await page.getByText('Guardado',{exact:true}).waitFor();
      assert.equal(writes.at(-1).method,'POST');
      assert.equal(writes.at(-1).body.fields[types[kind].number],'QA-NEW');
      await page.locator('#cert-back').click();
    }
    types.grain=JSON.parse(cp.execFileSync('python',['-c','import json;from backend_api.services.grain_web_fields import SPEC;print(json.dumps(SPEC))'],{cwd:root,encoding:'utf8'}));
    records.grain={id:9,cert_no:'QA-GRAIN',vessel_name:'QA GRAIN VESSEL',status:'Draft',place_date:'2026-10-22',sample10_centro:'001'};
    await page.goto('http://certificates.test/');
    await page.evaluate(()=>SOMCertificates.mount(document.getElementById('app'),{kind:'grain',headers:()=>({'X-Company-Code':'MCI-CR'})}));
    await page.locator('[data-open]').click();
    await page.locator('#cert-form').waitFor();
    assert.equal(await page.locator('#cert-form [name]').count(),112);
    assert.equal(await page.locator('[name=place_date]').inputValue(),'22/10/2026');
    for(const width of [1440,800,390]) {
      await page.setViewportSize({width,height:1000});
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`grain overflow ${width}`);
      await page.screenshot({path:path.join(qaDir,`grain-${width}.png`),fullPage:true});
    }
    await page.locator('.cert-sections a').filter({hasText:'Puntos de muestreo'}).click();
    await page.locator('[name=sample10_centro]').fill('002');
    await page.locator('button[type=submit]').click();
    await page.getByText('Guardado',{exact:true}).waitFor();
    assert.deepEqual(writes.at(-1).body.fields,{sample10_centro:'002'});
    assert.equal(await page.locator('#cert-format option').count(),4);
    await page.locator('.cert-sections a').filter({hasText:'Supervision y conclusion'}).click();
    await page.locator('[name=conclusion]').fill('Original QA');
    await page.getByRole('button',{name:'Proponer redaccion con IA'}).click();
    await page.locator('[data-accept]').waitFor();
    assert.equal(await page.locator('[name=conclusion]').inputValue(),'Original QA');
    await page.locator('[data-accept]').click();
    assert.equal(await page.locator('[name=conclusion]').inputValue(),'Propuesta QA revisada');
    await page.locator('#cert-back').click();
    await page.locator('#cert-new').click();
    await page.locator('[data-service]').click();
    assert.equal(await page.locator('[name=vessel_name]').inputValue(),'QA NEW VESSEL');
    assert.equal(await page.locator('[name=requested_by]').inputValue(),'QA CLIENT');
    permissions={view:true,create:false,edit:false,approve:false};await mount();
    assert.equal(await page.locator('#cert-new').count(),0);
    await page.locator('[data-open]').click();
    assert(await page.locator('[name=date]').isDisabled());
    assert.equal(await page.locator('#cert-approve').count(),0);
    const somSource=fs.readFileSync(path.join(root,'backend_api/routers/som_web.py'),'utf8');
    const integration=somSource.slice(somSource.indexOf('    let informesView ='),somSource.indexOf('    async function refreshSummary()'));
    await page.evaluate(()=>{
      SOMCertificates.destroy();document.getElementById('app').id='content';
      window.$=id=>document.getElementById(id);window.headers=()=>({'Content-Type':'application/json'});
      window.selectedCompany=()=> 'MCI-CR';window.session={usuario:'qa'};
      window.SOMTally={destroy(){},canLeave(){return true;},mount(root){root.innerHTML='<p>Tally fixture</p>';}};
      window.SOMContainers={destroy(){},canLeave(){return true;},mount(){}};
      window.SOMLogra={destroy(){},canLeave(){return true;},mount(){}};
    });
    await page.addScriptTag({content:integration+'\nrenderInformesTally();'});
    await page.getByText('Tally fixture',{exact:true}).waitFor();
    await page.locator('#reportCategory').selectOption('certificates');
    await page.locator('[data-open]').waitFor();
    await page.locator('#reportCategory').selectOption('tally');
    await page.getByText('Tally fixture',{exact:true}).waitFor();
    assert.deepEqual(errors,[]);
    console.log('Screenshots:',qaDir);
    console.log('PASS: 5 certificates + grain (112 fields), 3 viewports, conflicts, partial PATCH, approval/rejection, creation/service link, AI explicit acceptance, read-only permissions.');
  }finally{await browser.close();}
}
main().catch(e=>{console.error(e);process.exitCode=1;});
