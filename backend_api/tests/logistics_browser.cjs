const {chromium}=require('C:/Users/aaron/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('fs'),path=require('path'),assert=require('assert'),cp=require('child_process');
const root=path.resolve(__dirname,'../..'),out=path.join(root,'tmp/logistics-qa');fs.mkdirSync(out,{recursive:true});
const spec=JSON.parse(cp.execFileSync('py',['-3.11','-c',"import sys,json;sys.path.insert(0,'backend_api');from services.logistics_web_fields import SPEC;from services.mci_logistics_schema import TITLES,GROUPS,FIELDS;print(json.dumps(dict(msl=SPEC,titles=TITLES,groups=GROUPS,fields=FIELDS)))"],{cwd:root,encoding:'utf8'}));
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
 try{
  const page=await browser.newPage(),errors=[],writes=[];
  page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept());
  let company='MSL-CR';
  await page.route('http://logistics.test/**',route=>{
   const req=route.request(),p=new URL(req.url()).pathname,send=json=>route.fulfill({json});
   if(p==='/')return route.fulfill({contentType:'text/html',body:`<meta charset="utf-8"><style>body{margin:0;font:14px Arial}${fs.readFileSync(path.join(root,'backend_api/assets/certificates/certificates.css'),'utf8')}</style><main></main><script>${fs.readFileSync(path.join(root,'backend_api/assets/certificates/certificates.js'),'utf8')}</script><script>${fs.readFileSync(path.join(root,'backend_api/assets/mci_surveys/editor.js'),'utf8')}</script>`});
   if(p.endsWith('/logistics-assist'))return send({text:'QA improved logistics narrative'});
   if(p.endsWith('/bootstrap'))return send(company==='MSL-CR'?{types:{logistics:spec.msl},company,permissions:{view:true,create:true,edit:true,approve:true}}:{ready:true,sections:spec.titles,groups:spec.groups,fields:spec.fields,permissions:{view:true,create:true,edit:true,approve:true}});
   const service={consec:123,num_informe:'QA-123',buque_contenedor:'QA VESSEL',cliente:'QA CLIENT',puerto:'Caldera',pais:'Costa Rica'};
   if(p.endsWith('/services'))return send({data:[service],more:false});
   const row=company==='MSL-CR'?{id:1,cert_no:'QA-123',vessel_name:'QA VESSEL',status:'Draft',process_text:'QA process'}:{id:1,kind:'logistics',service_id:123,report_number:'QA-123',vessel:'QA VESSEL',requested_by:'QA CLIENT',status:'Draft',content:{hierarchy_version:2,sections:{process:{enabled:true,blocks:[{text:'QA process'}]}}}};
   if(['POST','PATCH'].includes(req.method())){writes.push(req.postDataJSON());return send({data:{...row,...req.postDataJSON().fields,content:req.postDataJSON().content||row.content},version:'v2'});}
   return send(p.endsWith('/1')?{data:row,version:'v1'}:{data:[{...row,report_number:'QA-123',vessel:'QA VESSEL',customer:'QA CLIENT'}],total:1,more:false});
  });
  for(company of ['MSL-CR','MCI-CR']){
   await page.goto('http://logistics.test/');
   await page.evaluate(company=>(company==='MSL-CR'?SOMCertificates:SOMMCISurveys).mount(document.querySelector('main'),{kind:'logistics',company,headers:()=>({})}),company);
   await page.locator('[data-open]').click();
   if(company==='MSL-CR'){
    assert.equal(await page.locator('#cert-format option').count(),4);
    await page.locator('[name=process_text]').fill('QA edited process');
    await page.getByRole('button',{name:'Guardar borrador',exact:true}).click();
    assert.equal(writes.at(-1).fields.process_text,'QA edited process');
   }else{
    assert.equal(await page.locator('[name=inspection_date]').getAttribute('type'),'date');
    await page.locator('[data-enable=findings]').check();
    await page.locator('[data-enable=documentary]').check();
    await page.locator('[data-block=documentary]').fill('QA documents');
    await page.locator('[data-add=documentary]').click();
    assert.equal(await page.locator('[data-block=documentary]').count(),2);
    await page.getByRole('button',{name:'Save draft',exact:true}).click();
    assert.equal(writes.at(-1).kind,'logistics');
    assert.equal(writes.at(-1).content.sections.documentary.blocks[0].text,'QA documents');
   }
   const input=company==='MSL-CR'?page.locator('[name=process_text]'):page.locator('[data-block=process]');
   await input.locator('..').getByRole('button',{name:'PORTIA',exact:true}).click();
   await page.getByRole('button',{name:'Accept',exact:true}).click();
   assert.equal(await input.inputValue(),'QA improved logistics narrative');
   for(const width of [1440,800,390]){
    await page.setViewportSize({width,height:1000});
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    await page.screenshot({path:path.join(out,`${company}-${width}.png`),fullPage:true});
   }
  }
  assert.deepEqual(errors,[]);console.log('PASS MSL/MCI Logistics: metadata, exports, hierarchy, save, PORTIA acceptance, responsive widths');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
