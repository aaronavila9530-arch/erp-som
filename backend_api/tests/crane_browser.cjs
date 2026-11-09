const {chromium}=require('C:/Users/aaron/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('fs'),path=require('path'),assert=require('assert'),cp=require('child_process');
const root=path.resolve(__dirname,'../..'),out=path.join(root,'tmp/crane-qa');fs.mkdirSync(out,{recursive:true});
const spec=JSON.parse(cp.execFileSync('C:/Users/aaron/AppData/Local/Programs/Python/Python311/python.exe',['-c',"import sys,json;sys.path.insert(0,'backend_api');from services.crane_web_fields import SPEC,POINTS,OPTIONS;from services.mci_crane_schema import TITLES,GROUPS,FIELDS,LIMITS;print(json.dumps(dict(msl=SPEC,sections=TITLES,groups=GROUPS,fields=FIELDS,block_limits=LIMITS,crane_points=POINTS,crane_options=OPTIONS)))"],{cwd:root,encoding:'utf8'}));
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
 try{
  const page=await browser.newPage(),errors=[],writes=[];let company='MSL-CR';
  page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept());
  await page.route('http://crane.test/**',route=>{
   const req=route.request(),p=new URL(req.url()).pathname,send=json=>route.fulfill({json});
   if(p==='/')return route.fulfill({contentType:'text/html',body:`<meta charset="utf-8"><style>body{margin:0;font:14px Arial}${fs.readFileSync(path.join(root,'backend_api/assets/certificates/certificates.css'),'utf8')}</style><main></main><script>${fs.readFileSync(path.join(root,'backend_api/assets/certificates/certificates.js'),'utf8')}</script><script>${fs.readFileSync(path.join(root,'backend_api/assets/mci_surveys/editor.js'),'utf8')}</script>`});
   if(p.endsWith('-assist'))return send({text:'QA revised narrative'});
   if(p.endsWith('/bootstrap'))return send(company==='MSL-CR'?{types:{crane:spec.msl},company,permissions:{view:true,create:true,edit:true,approve:true}}:{...spec,ready:true,permissions:{view:true,create:true,edit:true,approve:true}});
   if(p.endsWith('/services'))return send({data:[{consec:1,num_informe:'QA-CRANE',buque_contenedor:'QA VESSEL',cliente:'QA CLIENT',puerto:'Caldera',pais:'Costa Rica'}],more:false});
   const row=company==='MSL-CR'?{id:1,report_number:'QA-CRANE',vessel:'QA VESSEL',client:'QA CLIENT',status:'Draft',crane_access_done:true,crane1_remark_1:'QA remark'}:{id:1,kind:'crane',service_id:1,report_number:'QA-CRANE',vessel:'QA VESSEL',requested_by:'QA CLIENT',status:'Draft',content:{hierarchy_version:2,sections:{remarks:{enabled:true,blocks:[]},crane1:{enabled:true,blocks:[{text:'QA remark'}]}}}};
   if(['POST','PATCH'].includes(req.method())){writes.push(req.postDataJSON());return send({data:{...row,...req.postDataJSON().fields,content:req.postDataJSON().content||row.content},version:'v2'});}
   return send(p.endsWith('/1')?{data:row,version:'v1'}:{data:[{...row,customer:'QA CLIENT'}],total:1,more:false});
  });
  for(company of ['MSL-CR','MCI-CR']){
   await page.goto('http://crane.test/');
   await page.evaluate(company=>(company==='MSL-CR'?SOMCertificates:SOMMCISurveys).mount(document.querySelector('main'),{kind:'crane',company,headers:()=>({})}),company);
   await page.locator('[data-open]').click();
   await page.locator(company==='MSL-CR'?'#cert-form':'#mci-form').waitFor();
   if(company==='MSL-CR'){
    assert.equal(await page.locator('#cert-format option').count(),4);
    assert(await page.locator('[name=client]').evaluate(e=>e.readOnly));
    await page.getByText('Crane Access',{exact:true}).last().click();
    await page.locator('[name=crane_access_done]').uncheck();
    await page.locator('[name=crane_access_status3]').selectOption('Working');
    await page.getByRole('button',{name:'Guardar borrador',exact:true}).click();
    await page.getByText('Guardado',{exact:true}).waitFor();
    assert.strictEqual(writes.at(-1).fields.crane_access_done,false);
    assert.equal(writes.at(-1).fields.crane_access_status3,'Working');
   }else{
    await page.locator('[data-enable=crane_checklist]').check();
    await page.locator('summary').filter({hasText:'Crane Access'}).click();
    await page.locator('[data-check=crane_access][data-check-field=done]').check();
    await page.locator('[data-check=crane_access][data-check-field=status3]').selectOption('Working');
    await page.locator('[name=inspection_time]').fill('08:45');
    await page.locator('[data-enable=enclosure]').check();
    assert.equal(await page.locator('[data-add=enclosure]').count(),0);
    await page.locator('#mci-picture-link').fill('https://example.com/pictures');
    await page.getByRole('button',{name:'Save draft',exact:true}).click();
    await page.getByText('Saved',{exact:true}).waitFor();
    assert.equal(writes.at(-1).content.crane_checks.crane_access.status3,'Working');
    assert.deepEqual(writes.at(-1).content.sections.crane_checklist.blocks,[]);
    for(let i=1;i<10;i++)await page.locator('[data-add=crane1]').click();
    assert(await page.locator('[data-add=crane1]').isDisabled());
    for(let i=9;i>0;i--)await page.locator('[data-remove=crane1]').last().click();
   }
   for(const width of [1440,800,390]){
    await page.setViewportSize({width,height:1000});
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    await page.screenshot({path:path.join(out,`${company}-${width}.png`),fullPage:true});
   }
   // Create must start from a service, never overwrite the report currently reviewed.
   await page.getByRole('button',{name:company==='MSL-CR'?'Crear':'Create',exact:true}).click();
   await page.locator('[data-service]').click();
   assert.equal(await page.locator(company==='MSL-CR'?'[name=client]':'#mci-location').inputValue(),company==='MSL-CR'?'QA CLIENT':'Caldera, Costa Rica');
  }
  assert.deepEqual(errors,[]);console.log('PASS Crane: two companies, create/review, checkbox false, fourth status, limits, enclosure, save and 3 responsive viewports');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
