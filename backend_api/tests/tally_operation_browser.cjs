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
   const projects=[{id:1,name:'MV LAURA',holds:[1,4],revision:0},{id:2,name:'OTHER OPERATION',holds:[1],revision:0}];
   await SOMTally.mount(document.querySelector('#app'),{user:'test',company:'TEST',headers:()=>({}),
    getJSON:async p=>p==='/tally/bootstrap'?{projects,drivers:[],companies:['AEGRA','MANEJOS'],services:[],editable:true}:{revision:0,drivers:[{plate:'123',driver:p.includes('/1/sheets')?'LAURA DRIVER':'OTHER DRIVER'}],rows:[80,79,78,81,77].map(n=>({id:crypto.randomUUID(),stowage:String(n),plate:'123',date:'2026-10-16'}))},
    sendJSON:async(method,path,body)=>{window.saveAttempts=(window.saveAttempts||0)+1;if(window.failNextSave){window.failNextSave=false;throw Error('Sin conexion');}window.savedRows=body.rows;return {revision:1};},postJSON:async()=>({})});
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
  assert.equal(await page.locator('#tallySave').count(),0);
  assert.equal(await page.locator('#tallyStatus').innerText(),'');
  await page.evaluate(()=>{window.failNextSave=true;});
  await entry.dblclick();await entry.locator('input').fill('09:02');await entry.locator('input').press('Enter');
  await page.getByText('Sin conexion',{exact:true}).waitFor();
  await page.waitForFunction(()=>window.savedRows?.[0]?.entry==='09:02');
  assert.equal(await page.locator('#tallyStatus').innerText(),'');
  await entry.dblclick();await entry.locator('input').fill('09:01');await entry.locator('input').press('Enter');
  await entry.dblclick();await entry.locator('input').fill('25:90');await entry.locator('input').press('Enter');
  assert.equal(await entry.innerText(),'09:01');
  assert.equal(await page.evaluate(()=>SOMTally.pasteValue('entry','09:01:00')),'09:01');
  for(const [field,letter,expected] of [['company','A','AEGRA'],['company','M','MANEJOS'],['seal','S','Si'],['seal','N','No']]){
   const cell=page.locator(`.tabulator-row .tabulator-cell[tabulator-field="${field}"]`).first();
   await cell.dblclick();await cell.locator('input').fill(letter);await cell.locator('input').press('Enter');
   assert.equal(await cell.innerText(),expected);
  }
  const dates=page.locator('.tabulator-row .tabulator-cell[tabulator-field="date"]');
  await dates.first().dblclick();
  assert.equal(await dates.first().locator('input').getAttribute('type'),'text');
  assert.equal(await dates.first().locator('input').inputValue(),'16/10/2026');
  await dates.first().locator('input').fill('17/10/2026');await dates.first().locator('input').press('Enter');
  await dates.first().dblclick();await dates.first().locator('input').fill('31/02/2026');await dates.first().locator('input').press('Enter');
  assert.equal(await dates.first().innerText(),'17/10/2026');
  const first=await dates.first().boundingBox(),third=await dates.nth(2).boundingBox();
  await page.mouse.move(first.x+20,first.y+15);await page.mouse.down();await page.mouse.move(third.x+20,third.y+15,{steps:8});await page.mouse.up();
  await page.keyboard.press('Control+d');
  await page.waitForFunction(()=>window.savedRows?.slice(0,3).every(r=>r.date==='2026-10-17'));
  assert.equal(await dates.nth(2).innerText(),'17/10/2026');
  await page.context().grantPermissions(['clipboard-read','clipboard-write']);
  await dates.first().click();await page.keyboard.press('Control+c');
  assert((await page.evaluate(()=>navigator.clipboard.readText())).includes('2026'));
  const fourth=await dates.nth(3).boundingBox(),fifth=await dates.nth(4).boundingBox();
  await page.mouse.move(fourth.x+20,fourth.y+15);await page.mouse.down();await page.mouse.move(fifth.x+20,fifth.y+15,{steps:8});await page.mouse.up();
  await page.keyboard.press('Control+v');
  await page.waitForFunction(()=>window.savedRows?.slice(0,5).every(r=>r.date==='2026-10-17'));
  assert.equal(await dates.nth(4).innerText(),'17/10/2026');
  assert.equal(await page.evaluate(()=>SOMTally.pasteValue('date','16/10/2026')),'2026-10-16');
  assert.equal(await page.evaluate(()=>SOMTally.payloadRows([{id:'test',date:'2026-10-16'}])[0].date),'2026-10-16');
  const holder=page.locator('.tabulator-tableholder');
  await holder.evaluate(el=>{el.scrollTop=6400;el.scrollLeft=240;});
  await page.waitForTimeout(150);
  const scrollA=await holder.evaluate(el=>({top:el.scrollTop,left:el.scrollLeft}));
  await page.getByRole('tab',{name:'Bodega 4',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('[data-hold="4"][aria-selected="true"]')&&!document.querySelector('#tallyReload').disabled);
  assert.equal(await holder.evaluate(el=>el.scrollTop),0);
  await holder.evaluate(el=>{el.scrollTop=3200;el.scrollLeft=120;});
  await page.waitForTimeout(150);
  const scrollB=await holder.evaluate(el=>({top:el.scrollTop,left:el.scrollLeft}));
  await page.getByRole('tab',{name:'Bodega 1',exact:true}).click();
  await page.waitForFunction(()=>!document.querySelector('#tallyReload').disabled&&document.querySelector('.tabulator-tableholder').scrollTop===6400);
  assert.deepEqual(await holder.evaluate(el=>({top:el.scrollTop,left:el.scrollLeft})),scrollA);
  await page.getByRole('tab',{name:'Bodega 4',exact:true}).click();
  await page.waitForFunction(()=>!document.querySelector('#tallyReload').disabled&&document.querySelector('.tabulator-tableholder').scrollTop===3200);
  assert.deepEqual(await holder.evaluate(el=>({top:el.scrollTop,left:el.scrollLeft})),scrollB);
  await page.locator('#tallyProject').selectOption('2');
  await page.getByText('OTHER DRIVER',{exact:true}).first().waitFor();
  assert.equal(await page.getByText('LAURA DRIVER',{exact:true}).count(),0);
  page.on('dialog',dialog=>dialog.accept());
  const row=page.locator('.tabulator-row').first();
  await row.locator('[tabulator-field="date"]').click({button:'right'});
  await page.getByText('Eliminar fila(s)',{exact:true}).click();
  await page.waitForFunction(()=>window.savedRows?.length===4);
  await page.locator('.tabulator-row').first().locator('.tabulator-row-header').click();
  await page.keyboard.press('Delete');
  await page.waitForFunction(()=>window.savedRows?.length===3);
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
