const {chromium}=require('C:/Users/aaron/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('fs'),path=require('path'),assert=require('assert');
const root=path.resolve(__dirname,'../..'),assets=path.join(root,'backend_api/assets/tally');
async function run(){
 const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];
  page.setDefaultTimeout(15000);
  page.on('pageerror',e=>errors.push(e.message));
  await page.route('https://tally.test/**',async route=>{
   const url=new URL(route.request().url());
   if(url.pathname==='/')return route.fulfill({contentType:'text/html',body:`<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width"><style>body{margin:12px;font-family:Arial}*{box-sizing:border-box}</style><link rel="stylesheet" href="/tabulator.min.css"><link rel="stylesheet" href="/tally.css"><main id="app"></main><script src="/tabulator.min.js"></script><script src="/papaparse.min.js"></script><script src="/tally.js"></script>`});
   return route.fulfill({contentType:url.pathname.endsWith('.css')?'text/css':'text/javascript',body:fs.readFileSync(path.join(assets,path.basename(url.pathname)))});
  });
  await page.goto('https://tally.test/');
  await page.evaluate(async()=>{
   const projects=[{id:1,name:'MV LAURA',holds:[1],revision:0},{id:2,name:'OTHER OPERATION',holds:[1],revision:0}];
   await SOMTally.mount(document.querySelector('#app'),{user:'test',company:'TEST',headers:()=>({}),
    getJSON:async p=>p==='/tally/bootstrap'?{projects,drivers:[],companies:['AEGRA','MANEJOS'],services:[],editable:true}:{revision:0,drivers:[{plate:'123',driver:p.includes('/1/sheets')?'LAURA DRIVER':'OTHER DRIVER'}],rows:[80,79,78,81,77].map(n=>({id:crypto.randomUUID(),stowage:String(n),plate:'123',date:'2026-10-16'}))},
    sendJSON:async(method,path,body)=>{window.savedRows=body.rows;return {revision:1};},postJSON:async()=>({})});
  });
  assert.deepEqual(await page.evaluate(()=>SOMTally.metrics([80,79,78,81,77].map(n=>({id:String(n),stowage:String(n)})))),{count:5,max:81,missing:76,duplicates:0,invalid:0});
  assert.deepEqual(await page.evaluate(()=>SOMTally.metrics([{stowage:'1'},{stowage:'1'},{stowage:'3'},{plate:'123'},{}])),{count:4,max:3,missing:1,duplicates:1,invalid:1});
  assert.equal(await page.evaluate(()=>SOMTally.metrics([{stowage:'con secutivo #12'}]).max),12);
  await page.getByText('LAURA DRIVER',{exact:true}).first().waitFor();
  await page.getByText('16/10/2026',{exact:true}).first().waitFor();
  const entry=page.locator('.tabulator-row .tabulator-cell[tabulator-field="entry"]').first();
  await entry.dblclick();await entry.locator('input').fill('09:01');await entry.locator('input').press('Enter');
  await page.waitForFunction(()=>window.savedRows?.[0]?.entry==='09:01');
  assert.equal(await entry.innerText(),'09:01');
  await entry.dblclick();await entry.locator('input').fill('25:90');await entry.locator('input').press('Enter');
  assert.equal(await entry.innerText(),'09:01');
  assert.equal(await page.evaluate(()=>SOMTally.pasteValue('entry','09:01:00')),'09:01');
  for(const [field,letter,expected] of [['company','A','AEGRA'],['company','M','MANEJOS'],['seal','S','Si'],['seal','N','No']]){
   const cell=page.locator(`.tabulator-row .tabulator-cell[tabulator-field="${field}"]`).first();
   await cell.dblclick();await cell.locator('input').fill(letter);await cell.locator('input').press('Enter');
   assert.equal(await cell.innerText(),expected);
  }
  const dates=page.locator('.tabulator-row .tabulator-cell[tabulator-field="date"]');
  await dates.first().dblclick();await dates.first().locator('input').fill('2026-10-17');await dates.first().locator('input').press('Enter');
  const first=await dates.first().boundingBox(),third=await dates.nth(2).boundingBox();
  await page.mouse.move(first.x+20,first.y+15);await page.mouse.down();await page.mouse.move(third.x+20,third.y+15,{steps:8});await page.mouse.up();
  await page.keyboard.press('Control+d');
  await page.waitForFunction(()=>window.savedRows?.slice(0,3).every(r=>r.date==='2026-10-17'));
  assert.equal(await dates.nth(2).innerText(),'17/10/2026');
  assert.equal(await page.evaluate(()=>SOMTally.pasteValue('date','16/10/2026')),'2026-10-16');
  assert.equal(await page.evaluate(()=>SOMTally.payloadRows([{id:'test',date:'2026-10-16'}])[0].date),'2026-10-16');
  await page.locator('#tallyProject').selectOption('2');
  await page.getByText('OTHER DRIVER',{exact:true}).first().waitFor();
  assert.equal(await page.getByText('LAURA DRIVER',{exact:true}).count(),0);
  fs.mkdirSync(path.join(root,'tmp/tally-qa'),{recursive:true});
  for(const width of [1440,390]){
   await page.setViewportSize({width,height:1000});
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`overflow ${width}`);
   await page.screenshot({path:path.join(root,`tmp/tally-qa/tally-${width}.png`),fullPage:true});
  }
  assert.deepEqual(errors,[]);console.log('PASS metrics unordered/duplicates/blanks, project driver isolation, desktop/mobile');
 }finally{await browser.close();}
}
run().catch(e=>{console.error(e);process.exitCode=1;});
