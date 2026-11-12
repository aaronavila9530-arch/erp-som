const {chromium}=require('C:/Users/aaron/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('fs'),path=require('path'),assert=require('assert');
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:768,height:1024},hasTouch:true,isMobile:true});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));page.setDefaultTimeout(20000);
  const assets=path.resolve(__dirname,'../assets/tally');
  await page.route('https://tally.test/**',route=>{const file=new URL(route.request().url()).pathname.slice(1);return route.fulfill(file?{body:fs.readFileSync(path.join(assets,file)),contentType:file.endsWith('.css')?'text/css':'text/javascript'}:{contentType:'text/html',body:'<meta name="viewport" content="width=device-width"><link rel="stylesheet" href="/tabulator.min.css"><link rel="stylesheet" href="/tally.css"><div id="app"></div><script src="/tabulator.min.js"></script><script src="/tally.js"></script>'});});
  await page.goto('https://tally.test/');
  await page.evaluate(async()=>{
   window.remote={revision:1,rows:[{id:crypto.randomUUID(),date:'2026-11-11',ticket:'100',notes:'base'}],drivers:[]};
   window.api={user:'test',company:'MCI',getJSON:async p=>p==='/tally/bootstrap'?{projects:[{id:1,name:'Test',holds:[1]}],drivers:[],companies:['AEGRA'],editable:true,services:[]}:structuredClone(remote),sendJSON:async(m,p,b)=>{
    if(window.offline)throw Error('Sin conexion');
    if(b.revision!==remote.revision)throw Error('Otra persona modifico esta bodega');
    remote={...remote,revision:remote.revision+1,rows:structuredClone(b.rows)};
    if(window.loseResponse){window.loseResponse=false;throw Error('Sin conexion');}
    return {revision:remote.revision};
   }};
   await SOMTally.mount(document.querySelector('#app'),api);
  });
  async function edit(field,value){const c=page.locator(`.tabulator-row [tabulator-field="${field}"]`).first();await c.dblclick();await c.locator('input').fill(value);await c.locator('input').press('Enter');}
  await page.evaluate(()=>{remote.rows[0].notes='other user';remote.revision++;});
  await edit('ticket','101');
  await page.waitForFunction(()=>remote.rows[0].ticket==='101');
  assert.equal(await page.evaluate(()=>remote.rows[0].notes),'other user');
  assert.equal(await page.locator('#tallyResolve').isVisible(),false);
  await page.evaluate(()=>{window.loseResponse=true;});
  await edit('ticket','102');
  await page.waitForFunction(()=>remote.rows[0].ticket==='102');
  await page.waitForFunction(()=>!document.querySelector('#tallyStatus').textContent,{},{timeout:15000});
  assert.equal(await page.locator('#tallyResolve').isVisible(),false);
  await page.evaluate(()=>{remote.rows[0].ticket='theirs';remote.revision++;});
  await edit('ticket','mine');
  await page.locator('#tallyResolve').waitFor({state:'visible'});
  assert.equal(await page.evaluate(()=>remote.rows[0].ticket),'theirs','Do not overwrite conflicting field');
  await page.locator('#tallyResolve').click();
  await page.locator('[data-choice]').selectOption('local');
  await page.locator('#applyChanges').click();
  await page.waitForFunction(()=>remote.rows[0].ticket==='mine');
  const cell=page.locator('.tabulator-row [tabulator-field="ticket"]').first();
  await cell.dblclick();await cell.locator('input').fill('typing not committed');
  assert(await page.evaluate(()=>Object.keys(localStorage).some(k=>k.includes(':backup:')&&localStorage[k].includes('typing not committed'))));
  await cell.locator('input').press('Enter');
  await page.waitForFunction(()=>remote.rows[0].ticket==='typing not committed');
  await page.waitForFunction(()=>!Object.keys(localStorage).some(k=>k.includes(':backup:')));
  await page.evaluate(()=>{window.offline=true;});
  await edit('ticket','offline draft');
  await page.waitForFunction(()=>document.querySelector('#tallyStatus').textContent==='Sin conexion');
  page.on('dialog',dialog=>dialog.accept());
  await page.evaluate(async()=>{SOMTally.destroy();sessionStorage.clear();window.offline=false;remote.rows[0].notes='second remote edit';remote.revision++;await SOMTally.mount(document.querySelector('#app'),api);});
  await page.waitForFunction(()=>remote.rows[0].ticket==='offline draft');
  assert.equal(await page.evaluate(()=>remote.rows[0].notes),'second remote edit');
  await page.waitForFunction(()=>!Object.keys(localStorage).some(k=>k.includes(':backup:')));
  fs.mkdirSync(path.resolve(__dirname,'../../tmp/tally-conflict-qa'),{recursive:true});
  await page.screenshot({path:path.resolve(__dirname,'../../tmp/tally-conflict-qa/tablet.png'),fullPage:true});
  assert.deepEqual(errors,[]);console.log('PASS tablet concurrent fields, lost response, same-cell resolution, persistent active editor');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
