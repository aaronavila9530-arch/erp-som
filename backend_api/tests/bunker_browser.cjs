const {chromium}=require('C:/Users/aaron/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('fs'),path=require('path'),assert=require('assert'),cp=require('child_process');
const root=path.resolve(__dirname,'../..'),out=path.join(root,'tmp/bunker-qa');fs.mkdirSync(out,{recursive:true});
const spec=JSON.parse(cp.execFileSync('python',['-c',"import sys,json;sys.path.insert(0,'backend_api');from services.bunker_web_fields import SPEC;print(json.dumps(SPEC))"],{cwd:root,encoding:'utf8'}));
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
 try{
  const page=await browser.newPage(),errors=[],writes=[];let company='MSL-CR',conflict=false;
  page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept());
  await page.route('http://bunker.test/**',route=>{
   const req=route.request(),p=new URL(req.url()).pathname,send=json=>route.fulfill({json});
   if(p==='/')return route.fulfill({contentType:'text/html',body:`<meta charset="utf-8"><style>body{margin:0;font:14px Arial}${fs.readFileSync(path.join(root,'backend_api/assets/certificates/certificates.css'),'utf8')}</style><main></main><script>${fs.readFileSync(path.join(root,'backend_api/assets/certificates/certificates.js'),'utf8')}</script>`});
   if(p.endsWith('/bootstrap'))return send({types:{bunker:{...spec,document:company==='MCI-CR'?'word':'excel'}},company,permissions:{view:true,create:true,edit:true,approve:true}});
   if(p.endsWith('/services'))return send({data:[{consec:1,num_informe:'QA-BUNKER',buque_contenedor:'QA VESSEL',cliente:'QA CLIENT',puerto:'Caldera',pais:'Costa Rica'}],more:false});
   if(p.endsWith('/calculate')){
    const result=cp.execFileSync('python',['-c',"import sys,json;sys.path.insert(0,'backend_api');from services.bunker_web_fields import normalize;print(json.dumps(normalize(json.load(sys.stdin)['fields'])[1]))"],{cwd:root,encoding:'utf8',input:req.postData()});
    return send(JSON.parse(result));
   }
   const row={id:1,bunker_cert_no:'QA-BUNKER',ship_name:'QA VESSEL',client:'QA CLIENT',certificate:'OFF_HIRE',status:'Draft',
    vlsfo_tank_1_name:'T1',vlsfo_tank_1_volume_m3:'100',vlsfo_tank_1_temp_c:'30',vlsfo_tank_1_density_15c:'.95'};
   if(['POST','PATCH'].includes(req.method())){
    writes.push(req.postDataJSON());
    if(conflict)return route.fulfill({status:409,json:{detail:'Changed elsewhere - keep draft'}});
    return send({data:{...row,...req.postDataJSON().fields},version:'v2'});
   }
   return send(p.endsWith('/1')?{data:row,version:'v1'}:{data:[{...row,report_number:'QA-BUNKER',vessel:'QA VESSEL',customer:'QA CLIENT'}],total:1});
  });
  for(company of ['MSL-CR','MCI-CR']){
   await page.goto('http://bunker.test/');
   await page.evaluate(company=>SOMCertificates.mount(document.querySelector('main'),{kind:'bunker',company,headers:()=>({})}),company);
   await page.locator('[data-open]').click();await page.locator('#cert-form').waitFor();
   await page.waitForFunction(()=>document.querySelector('output')?.textContent.includes('94.06'));
   assert(await page.locator('[name=client]').evaluate(e=>e.readOnly));
   assert(await page.locator('[name=vlsfo_tank_1_weight_mt]').evaluate(e=>e.readOnly));
   assert(await page.locator('[name=log_at_survey_vlsfo]').evaluate(e=>e.readOnly));
   const formats=await page.locator('#cert-format option').evaluateAll(options=>options.map(o=>o.value));
   for(const value of ['word','excel','pdf','presentation','complete'])assert(formats.includes(value),`${company} missing ${value}`);
   await page.getByText('VLSFO tanks',{exact:true}).last().evaluate(e=>e.parentElement.open=true);
   await page.locator('[name=vlsfo_tank_1_volume_m3]').fill('1.25');
   await page.locator('[name=vlsfo_tank_1_temp_c]').fill('15');
   await page.locator('[name=vlsfo_tank_1_density_15c]').fill('.9');
   await page.waitForFunction(()=>document.querySelector('[name=vlsfo_tank_1_weight_mt]').value==='1.13');
   assert.equal(await page.locator('[name=vlsfo_tank_1_volume_m3]').inputValue(),'1.25');
   await page.getByRole('button',{name:'Agregar tanque',exact:true}).first().click();
   await page.locator('[name=vlsfo_tank_2_name]').fill('SECOND');
   await page.getByRole('button',{name:'Eliminar ultimo tanque',exact:true}).first().click();
   assert.equal(await page.locator('[name=vlsfo_tank_2_name]').inputValue(),'');
   await page.getByRole('button',{name:'Guardar borrador',exact:true}).click();
   await page.getByText('Guardado',{exact:true}).waitFor();
   assert.equal(writes.at(-1).fields.vlsfo_tank_1_volume_m3,'1.25');
   for(const width of [1440,800,390]){
    await page.setViewportSize({width,height:1000});
    await page.getByText('VLSFO tanks',{exact:true}).last().evaluate(e=>e.parentElement.open=true);
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    await page.screenshot({path:path.join(out,`${company}-${width}.png`),fullPage:true});
   }
   conflict=true;
   await page.locator('[name=vlsfo_tank_1_volume_m3]').fill('123');
   await page.getByRole('button',{name:'Guardar borrador',exact:true}).click();
   await page.getByText('Changed elsewhere - keep draft',{exact:true}).waitFor();
   assert.equal(await page.locator('[name=vlsfo_tank_1_volume_m3]').inputValue(),'123');
   conflict=false;
   await page.getByRole('button',{name:'Crear',exact:true}).click();
   await page.locator('[data-service]').click();
   assert.equal(await page.locator('[name=client]').inputValue(),'QA CLIENT');
   assert.equal(await page.locator('[name=ship_name]').inputValue(),'QA VESSEL');
  }
  assert.deepEqual(errors,[]);console.log('PASS Bunker: two companies, authoritative calculation, decimal rounding, add/remove, save, conflict retention, 3 responsive viewports');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
