const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'C:/Users/aaron/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('fs'),path=require('path'),assert=require('assert');
const root=path.resolve(__dirname,'../..');
const js=fs.readFileSync(path.join(root,'backend_api/assets/comercial/comercial.js'),'utf8');
const css=fs.readFileSync(path.join(root,'backend_api/assets/comercial/comercial.css'),'utf8');
const shellCSS=fs.readFileSync(path.join(root,'backend_api/routers/som_web.py'),'utf8').match(/<style>([\s\S]*?)<\/style>/)[1];
const requests=[];
const board=Array.from({length:1205},(_,i)=>({consec:i+1,cliente:'NORDEN',estado:'FINALIZADO',operacion:'Bunker Survey',buque_contenedor:'MV TEST '+i,pais:'Costa Rica',puerto:'Caldera',surveyor:'Test',fecha_inicio:'2026-10-12',duracion:1500}));
let quotes=[{id:1,quotation_number:'Quotation 00001',cliente:'NORDEN',servicio:'Bunker Survey',continente:'America',pais:'Costa Rica',puerto:'Caldera',precio:25000,status:'PENDIENTE',idioma:'ES',validez:15}];
let prices=[{id:1,servicio:'Bunker Survey',cliente:'NORDEN',continente:'America',pais:'Costa Rica',puerto:'Caldera',precio:750,activo:true}];
let role='admin';
async function run(){
 const browser=await chromium.launch({executablePath:process.env.EDGE_PATH||'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
 try {
  const page=await browser.newPage({viewport:{width:1440,height:1000},acceptDownloads:true});
  const errors=[];page.on('pageerror',error=>errors.push(error.message));page.on('dialog',d=>d.accept());
  await page.route('http://commercial.test/**',async route=>{
   const req=route.request(),url=new URL(req.url()),pathname=url.pathname;
   if(pathname==='/'){await route.fulfill({contentType:'text/html',body:`<style>${shellCSS}\nbody{display:block;margin:0;font-family:Arial;padding:12px;background:#f3f6f8}#content{margin-left:220px;min-width:0}@media(max-width:700px){#content{margin-left:0}}${css}</style><div id="content"></div><script>${js}</script>`});return;}
   requests.push({path:pathname,query:url.search,method:req.method(),body:req.postDataJSON(),company:req.headers()['x-company-code']});
   if(pathname.startsWith('/som/queue-icon/')) {await route.fulfill({contentType:'image/svg+xml',body:fs.readFileSync(path.join(root,'backend_api/assets/icons/lucide',path.basename(pathname)))});return;}
   let data={data:[]};
   if(pathname==='/comercial/web/currency')data={currency:'USD',rate:500,rate_date:'2026-10-12'};
   else if(pathname==='/comercial/web/meta')data={permissions:Object.fromEntries(['board','clients','ports','services','quotations','edit','delete','export'].map(k=>[k,role==='admin'||k==='board'])),options:{cliente:['NORDEN'],operacion:['Bunker Survey'],continente:['America'],pais:['Costa Rica'],puerto:['Caldera'],surveyor:['Test'],year:[2025,2026]}};
   else if(pathname==='/comercial/board')data=board;
   else if(pathname==='/comercial/client-view')data={data:[{cliente:'NORDEN',servicios:'Bunker Survey',valor_facturado:25000}],kpis:{clientes:1,facturado:25000}};
   else if(pathname==='/comercial/clientes')data={data:[{nombrejuridico:'NORDEN',correo:'test@example.com',comentarios:'<img src=x onerror=alert(1)>'}]};
   else if(pathname==='/comercial/analytics/puertos')data={data:[{continente:'America',pais:'Costa Rica',puerto:'Caldera',total_operaciones:8,facturacion_neta:25000}]};
   else if(pathname.endsWith('/puertos/kpis'))data={clientes:1,puertos:1,facturacion:25000};
   else if(pathname==='/comercial/ports-coverage')data={data:[{puerto:'Caldera',estado_operativo:'OPERACION_ACTIVA',total_operaciones:8}],kpis:{total_puertos:1,cobertura_pct:100}};
   else if(pathname.endsWith('/by-servicio'))data={data:[{servicio:'Bunker Survey',quarter:'Q2',cantidad_servicios:2,revenue_neto_total:25000}]};
   else if(pathname.endsWith('/servicios/kpis'))data={kpis:{total_servicios:1,revenue_neto_total:25000}};
   else if(pathname.endsWith('/not-offered'))data={data:[{codigo:'C1',servicio:'Draft Survey',costo_base:123}]};
   else if(pathname.endsWith('/costos-surveyor-pareto'))data={data:[{surveyor:'Test',honorarios_total:500,total_servicios:2,acumulado_pct:75,es_pareto_80:true}]};
   else if(pathname==='/comercial/precios/meta')data={clientes:[{nombrejuridico:'NORDEN'}],servicios:[{nombre:'Bunker Survey'}],ubicaciones:[{continente:'America',pais:'Costa Rica',puerto:'Caldera'}]};
   else if(pathname==='/comercial/precios'){
    if(req.method()==='POST'){prices.push({...req.postDataJSON(),id:2,activo:true});data={id:2};}else data={data:prices};
   }else if(pathname==='/comercial/precios/1'){
    if(req.method()==='PUT')prices[0]={...prices[0],...req.postDataJSON()};if(req.method()==='DELETE')prices=prices.filter(r=>r.id!==1);data={status:'OK'};
   }else if(pathname==='/comercial/cotizaciones/next-quotation-number')data={quotation_number:'Quotation 00002'};
   else if(pathname==='/comercial/cotizaciones'){
    if(req.method()==='POST'){quotes.push({...req.postDataJSON(),id:2,quotation_number:'Quotation 00002'});data={id:2};}else data={data:quotes};
   }else if(pathname==='/comercial/cotizaciones/1/detail')data={...quotes[0],texto_exportable:'Texto original'};
   else if(pathname==='/comercial/cotizaciones/1'){
    if(req.method()==='PUT')quotes[0]={...quotes[0],...req.postDataJSON()};data={status:'OK'};
   }else if(pathname==='/comercial/cotizaciones/export-ticket')data={ticket:'fixture-ticket'};
   else if(pathname.includes('/export/')) {await route.fulfill({contentType:'application/octet-stream',body:'fixture export'});return;}
   await route.fulfill({contentType:'application/json',body:JSON.stringify(data)});
  });
  await page.goto('http://commercial.test/');
  async function mount(company='MSL-CR'){await page.evaluate(async company=>{await SOMCommercial.mount(document.getElementById('content'),{company,year:2026,headers:{'Content-Type':'application/json','X-Company-Code':company,'X-User':'test','X-User-Role':'admin'},openService:async()=>{window.serviceOpened=true;}});},company);}
  async function tab(name){await page.getByRole('tab',{name,exact:true}).click();await page.waitForFunction(()=>!document.querySelector('[data-message]').textContent.includes('Cargando'));}
  await mount();assert.equal(await page.getByRole('tab').count(),6);
  await page.getByText('1205 registros',{exact:true}).waitFor();
  assert.equal(await page.locator('[data-kpis] .com-kpi').count(),4);
  assert.equal(await page.locator('[data-overview] section').count(),2);
  await page.locator('[data-rank="NORDEN"]').click();
  assert.equal(await page.locator('[data-search]').inputValue(),'NORDEN');
  await page.locator('[data-search]').fill('');
  fs.mkdirSync(path.join(root,'tmp/comercial-qa'),{recursive:true});
  for(const width of [1440,390,320]){
    await page.setViewportSize({width,height:1000});
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`Board overflow ${width}`);
    await page.screenshot({path:path.join(root,`tmp/comercial-qa/board-${width}.png`),fullPage:true});
  }
  await page.setViewportSize({width:1440,height:1000});
  await page.locator('[data-columns]').selectOption('all');
  assert.equal(await page.locator('thead th').count(),19);
  await page.locator('[data-columns]').selectOption('summary');
  assert.equal(await page.locator('thead th').count(),9);
  await page.getByRole('button',{name:'Buscar',exact:true}).click();await page.getByText('1205 registros',{exact:true}).waitFor();
  assert.equal(await page.locator('tbody tr').count(),50);
  await page.getByRole('button',{name:'Pagina siguiente'.replace('Pagina','Página')}).click();
  await page.locator('[data-search]').fill('MV TEST 1204');assert.equal(await page.locator('tbody tr').count(),1);
  const download=page.waitForEvent('download');await page.locator('[data-export]').selectOption('xlsx');await download;
  assert.equal(requests.findLast(r=>r.path==='/comercial/web/export/xlsx').body.rows.length,1);
  await page.locator('[data-search]').fill('');const allDownload=page.waitForEvent('download');await page.locator('[data-export]').selectOption('csv');await allDownload;
  assert.equal(requests.findLast(r=>r.path==='/comercial/web/export/csv').body.rows.length,1205);
  await tab('Clientes');assert.match(await page.getByRole('status').innerText(), /USD.*TC BCCR.*500.*2026-10-12/);await page.locator('[data-row="0"]').check();await page.locator('[data-action=client-detail]').click();
  await page.locator('dialog').waitFor();assert.equal(await page.locator('dialog img').count(),0);await page.locator('[data-close]').click();
  await tab('Puertos');await page.locator('[data-action=coverage]').click();await page.getByRole('heading',{name:'Cobertura de puertos'}).waitFor();
  await tab('Servicios');await page.locator('select[name=quarter]').selectOption('Q2');await page.getByRole('button',{name:'Buscar',exact:true}).click();
  await page.waitForTimeout(80);assert(requests.findLast(r=>r.path.endsWith('/by-servicio')).query.includes('quarter=Q2'));assert(requests.findLast(r=>r.path.endsWith('/servicios/kpis')).query.includes('quarter=Q2'));
  await page.locator('[data-action=missing]').click();await page.getByRole('heading',{name:'Servicios no ofrecidos'}).waitFor();
  await page.locator('[data-action=back]').click();await page.locator('[data-action=surveyors]').click();await page.getByRole('heading',{name:'Costos por surveyor / Pareto 80-20'}).waitFor();
  await tab('Cotizaciones');await page.locator('[data-row="0"]').check();await page.locator('[data-action=edit-text]').click();
  await page.locator('dialog textarea').fill('Texto actualizado');await page.getByRole('button',{name:'Guardar texto',exact:true}).click();await page.locator('dialog').waitFor({state:'detached'});
  assert.equal(quotes[0].texto_cotizacion,'Texto actualizado');
  await page.locator('[data-action=new-quote]').click();await page.locator('dialog').waitFor();
  for(const [key,value] of Object.entries({cliente:'NORDEN',continente:'America',pais:'Costa Rica',puerto:'Caldera'})){await page.locator(`dialog [name=${key}]`).fill(value);await page.locator(`dialog [name=${key}]`).press('Tab');}
  await page.locator('[data-price]').selectOption('1');await page.locator('[data-action=add-line]').click();
  assert((await page.locator('dialog textarea').inputValue()).includes('750.00'));
  const preview=page.waitForEvent('download');await page.locator('[data-action=preview-pdf]').click();await preview;
  await page.getByRole('button',{name:'Confirmar y guardar'}).click();await page.locator('dialog').waitFor({state:'detached'});
  assert.equal(quotes[1].precio,750);assert.equal(quotes[1].servicio_1,'Bunker Survey');
  await page.locator('[data-row="0"]').check();await page.locator('[data-action=approve]').click();await page.waitForFunction(()=>window.serviceOpened);assert.equal(quotes[0].status,'APROBADO');
  quotes[0].status='PENDIENTE';await tab('Cotizaciones');await page.locator('[data-row="0"]').check();await page.locator('[data-action=cancel]').click();await page.locator('dialog textarea').fill('Cliente no confirma');await page.getByRole('button',{name:'Confirmar cancelación'}).click();await page.locator('dialog').waitFor({state:'detached'});assert.equal(quotes[0].razon_cancelacion,'Cliente no confirma');
  await tab('Precios');await page.locator('[data-row="0"]').check();await page.locator('[data-action=edit-price]').click();await page.locator('dialog [name=precio]').fill('875');await page.getByRole('button',{name:'Guardar precio'}).click();await page.locator('dialog').waitFor({state:'detached'});assert.equal(prices[0].precio,875);
  await page.locator('[data-action=new-price]').click();await page.locator('dialog [name=cliente]').fill('NORDEN');await page.locator('dialog [name=servicio]').fill('Bunker Survey');await page.locator('dialog [name=precio]').fill('900');await page.getByRole('button',{name:'Guardar precio'}).click();await page.locator('dialog').waitFor({state:'detached'});assert.equal(prices[1].precio,900);
  fs.mkdirSync(path.join(root,'tmp/comercial-qa'),{recursive:true});
  for(const width of [1440,1000,390,320]){
    await page.setViewportSize({width,height:900});await tab('Cotizaciones');
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`Overflow ${width}`);
    await page.screenshot({path:path.join(root,`tmp/comercial-qa/quotes-${width}.png`),fullPage:true});
    await page.locator('[data-action=new-quote]').click();await page.locator('dialog').waitFor();
    assert(await page.locator('dialog').evaluate(el=>el.scrollWidth<=el.clientWidth),`Modal overflow ${width}`);
    await page.screenshot({path:path.join(root,`tmp/comercial-qa/form-${width}.png`),fullPage:true});await page.locator('[data-close]').click();
  }
  await mount('MCI-CR');await page.getByRole('button',{name:'Buscar',exact:true}).click();await page.getByText('1205 registros',{exact:true}).waitFor();assert.equal(requests.findLast(r=>r.path==='/comercial/board').company,'MCI-CR');
  role='surveyor';await mount();assert.equal(await page.getByRole('tab').count(),1);assert.equal(await page.locator('[data-export]').count(),0);
  assert.deepEqual(errors,[]);console.log(JSON.stringify({ok:true,requests:requests.length,views:9,widths:[1440,1000,390,320],flows:['pagination','full-export','client-detail','coverage','quarters','missing','pareto','quote-create','quote-text','quote-approve','quote-cancel','price-create','price-edit','company-switch','surveyor-permissions']}));
 }finally{await browser.close();}
}
run().catch(error=>{console.error(error);process.exitCode=1;});
