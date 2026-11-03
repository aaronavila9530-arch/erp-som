const {chromium}=require('C:/Users/aaron/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('fs'),path=require('path'),assert=require('assert'),cp=require('child_process');
const root=path.resolve(__dirname,'../..'),out=path.join(root,'tmp/port-captancy-qa');fs.mkdirSync(out,{recursive:true});
const python='C:/Users/aaron/AppData/Local/Programs/Python/Python311/python.exe';
const spec=JSON.parse(cp.execFileSync(python,['-c',"import sys,json;sys.path.insert(0,'backend_api');from services.port_captancy_web_fields import SPEC;from services.mci_port_captancy_schema import TITLES,GROUPS,FIELDS;print(json.dumps(dict(msl=SPEC,titles=TITLES,groups=GROUPS,fields=FIELDS)))"],{cwd:root,encoding:'utf8'}));
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
 try{
  const page=await browser.newPage(),errors=[],writes=[];let company='MSL-CR';
  page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept());
  await page.route('http://port.test/**',route=>{
   const req=route.request(),p=new URL(req.url()).pathname,send=json=>route.fulfill({json});
   if(p==='/')return route.fulfill({contentType:'text/html',body:`<meta charset="utf-8"><style>body{margin:0;font:14px Arial}${fs.readFileSync(path.join(root,'backend_api/assets/certificates/certificates.css'),'utf8')}</style><main></main><script>${fs.readFileSync(path.join(root,'backend_api/assets/certificates/certificates.js'),'utf8')}</script><script>${fs.readFileSync(path.join(root,'backend_api/assets/mci_surveys/editor.js'),'utf8')}</script>`});
   if(p.endsWith('-assist'))return send({text:'QA revised narrative'});
   if(p.endsWith('/bootstrap'))return send(company==='MSL-CR'?{types:{port_captancy:spec.msl},company,permissions:{view:true,create:true,edit:true,approve:true}}:{ready:true,sections:spec.titles,groups:spec.groups,fields:spec.fields,max_blocks:15,permissions:{view:true,create:true,edit:true,approve:true}});
   if(p.endsWith('/services'))return send({data:[{consec:1,num_informe:'QA-PC',buque_contenedor:'QA VESSEL',cliente:'QA CLIENT',puerto:'Caldera',pais:'Costa Rica',operacion:'Steel',continente:'America'}],more:false});
   const row=company==='MSL-CR'?{id:1,report_number:'QA-PC',vessel:'QA VESSEL',requested_by:'QA CLIENT',status:'Draft',operation_summary_1:'QA operation',ts_date_0:'2026-11-02'}:{id:1,kind:'port_captancy',service_id:1,report_number:'QA-PC',vessel:'QA VESSEL',requested_by:'QA CLIENT',status:'Draft',content:{hierarchy_version:2,sections:{operation_summary:{enabled:true,blocks:[{text:'QA operation'}]}}}};
   if(['POST','PATCH'].includes(req.method())){writes.push(req.postDataJSON());return send({data:{...row,...req.postDataJSON().fields,content:req.postDataJSON().content||row.content},version:'v2'});}
   return send(p.endsWith('/1')?{data:row,version:'v1'}:{data:[{...row,customer:'QA CLIENT'}],total:1,more:false});
  });
  for(company of ['MSL-CR','MCI-CR']){
   await page.goto('http://port.test/');
   await page.evaluate(company=>(company==='MSL-CR'?SOMCertificates:SOMMCISurveys).mount(document.querySelector('main'),{kind:'port_captancy',company,headers:()=>({})}),company);
   assert.equal(await page.locator('textarea').count(),0);
   await page.locator('[data-open]').click();
   if(company==='MSL-CR'){
    assert.equal(await page.locator('#cert-format option').count(),4);
    assert(await page.locator('[name=vessel]').evaluate(e=>e.readOnly));
    await page.locator('[name=ts_hour_0]').fill('08');await page.locator('[name=ts_min_0]').fill('15');
    await page.locator('[name=operation_summary_1]').fill('QA edited');
    await page.getByRole('button',{name:'Guardar borrador',exact:true}).click();
    assert.equal(writes.at(-1).fields.ts_hour_0,'08');
    assert.equal(writes.at(-1).fields.operation_summary_1,'QA edited');
   }else{
    assert.equal(await page.locator('[name=ts_date_0]').getAttribute('type'),'date');
    assert.equal(await page.locator('[name=ts_time_0]').getAttribute('type'),'time');
    await page.locator('summary').filter({hasText:'Extract time sheet'}).click();
    await page.locator('[name=ts_date_0]').fill('2026-11-02');await page.locator('[name=ts_time_0]').fill('08:15');
    await page.locator('[data-enable=enclosure]').check();
    assert.equal(await page.locator('[data-add=enclosure]').count(),0);
    await page.locator('#mci-picture-link').fill('https://example.com/pictures');
    await page.getByRole('button',{name:'Save draft',exact:true}).click();
    assert.equal(writes.at(-1).content.ts_time_0,'08:15');
    for(let i=1;i<15;i++)await page.locator('[data-add=operation_summary]').click();
    assert(await page.locator('[data-add=operation_summary]').isDisabled());
    for(let i=14;i>0;i--)await page.locator('[data-remove=operation_summary]').last().click();
   }
   const input=company==='MSL-CR'?page.locator('[name=operation_summary_1]'):page.locator('[data-block=operation_summary]');
   await input.locator('..').getByRole('button',{name:'PORTIA',exact:true}).click();
   await page.getByRole('button',{name:'Accept',exact:true}).click();
   assert.equal(await input.inputValue(),'QA revised narrative');
   await page.locator('summary').filter({hasText:'PDF annexes'}).click();
   await page.locator('input[type=file]').setInputFiles([
    {name:'first.pdf',mimeType:'application/pdf',buffer:Buffer.from('%PDF-1.4 QA')},
    {name:'second.pdf',mimeType:'application/pdf',buffer:Buffer.from('%PDF-1.4 QA')}
   ]);
   await page.getByRole('button',{name:'Move up',exact:true}).nth(1).click();
   assert.equal(await page.locator('ol li span').first().textContent(),'second.pdf');
   await page.getByRole('button',{name:'Remove',exact:true}).first().click();
   assert.equal(await page.locator('ol li span').first().textContent(),'first.pdf');
   for(const width of [1440,800,390]){
    await page.setViewportSize({width,height:1000});
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    await page.screenshot({path:path.join(out,`${company}-${width}.png`),fullPage:true});
   }
  }
  assert.deepEqual(errors,[]);console.log('PASS: MSL/MCI forms, times, blocks, enclosure, save, PORTIA and responsive views');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
