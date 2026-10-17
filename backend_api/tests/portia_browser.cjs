const {chromium}=require('C:/Users/aaron/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('fs'),path=require('path'),assert=require('assert');
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  const assets=path.resolve(__dirname,'../assets');
  await page.route('https://portia.test/**',route=>{
   const p=new URL(route.request().url()).pathname;
   if(p==='/')return route.fulfill({contentType:'text/html; charset=utf-8',body:'<meta charset="utf-8"><meta name="viewport" content="width=device-width"><style>body{margin:0;font-family:Arial}</style><link rel="stylesheet" href="/portia.css"><main></main><script src="/portia.js"></script>'});
   const file=p.endsWith('.svg')?path.join(assets,'icons/lucide/file-pen-line.svg'):path.join(assets,'portia',path.basename(p));
   return route.fulfill({contentType:p.endsWith('.css')?'text/css':p.endsWith('.svg')?'image/svg+xml':'text/javascript',body:fs.readFileSync(file)});
  });
  await page.goto('https://portia.test/');
  await page.evaluate(()=>{
   window.requests=[];
   const evidence={start:'2026-10-01',end:'2026-10-16',previous_start:'2026-09-15',previous_end:'2026-09-30',generated_at:'2026-10-16T10:00:00-06:00',warnings:[],sections:{expenses:{name:'Obligaciones por beneficiario',source:'payment_obligations',basis:'Obligaciones, no gasto contable.',count:1,totals:[{currency:'USD',amount:1500,previous:1000,change:500}],groups:[{label:'Proveedor <img src=x onerror=alert(1)>',currency:'USD',amount:1500,change:500}],details:[{id:12,date:'2026-10-10',label:'Proveedor',reference:'123',currency:'USD',amount:1500,status:'PENDING'}]}}};
   SOMPortia.mount(document.querySelector('main'),{company:'MCI-CR',get:async()=>({data:evidence}),post:async(path,payload)=>{requests.push(payload);return {answer:'1. Gastos\nAumento de USD 500.\n2. Quincena\nRevise los pendientes.\n3. Ventas\nFalta fuente.',context:evidence,mode:'local',warning:'Respuesta local de prueba.'};}});
  });
  await page.getByText('Obligaciones por beneficiario',{exact:false}).first().waitFor();
  assert.equal(await page.locator('#pEvidence img').count(),0);
  await page.locator('#pQuestion').fill('Por que tengo gastos, quincena alta y donde vendi mas?');
  await page.getByRole('button',{name:'Consultar',exact:true}).click();
  await page.getByText('1. Gastos',{exact:false}).waitFor();
  await page.locator('#pQuestion').fill('Desglosa lo anterior');await page.getByRole('button',{name:'Consultar',exact:true}).click();
  await page.waitForFunction(()=>requests.length===2);
  assert.equal(await page.evaluate(()=>requests[1].history.length),2);
  for(const width of [1440,390]){
   await page.setViewportSize({width,height:1000});
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`overflow ${width}`);
   fs.mkdirSync(path.resolve(__dirname,'../../tmp/portia-qa'),{recursive:true});
   await page.screenshot({path:path.resolve(__dirname,`../../tmp/portia-qa/portia-${width}.png`),fullPage:true});
  }
  await page.getByLabel('General',{exact:true}).check();
  assert.equal(await page.locator('.portia-message').count(),0);
  assert.equal(await page.locator('#pEvidence').innerText(),'Sin datos ERP en este alcance.');
  assert.deepEqual(errors,[]);console.log('PASS multi-question, follow-up, scope reset, escaping, desktop/mobile');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
