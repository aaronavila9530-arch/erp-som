const {chromium}=require('C:/Users/aaron/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('fs'),path=require('path'),assert=require('assert');
const assets=path.resolve(__dirname,'../assets/tally');
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:900}}),errors=[];let saved;
  page.on('pageerror',e=>errors.push(e.message));
  await page.route('https://tally.test/**',route=>{
   const request=route.request(),url=new URL(request.url());
   if(url.pathname.includes('/api/')){
    assert.equal(request.headers()['x-tally-token'],'a'.repeat(43));
    assert.equal(request.headers()['x-user'],undefined);
    if(url.pathname.endsWith('bootstrap'))return route.fulfill({json:{projects:[{id:2,name:'MV LAURA',holds:[1,4]},{id:3,name:'OTHER MCI',holds:[1]}],drivers:[],companies:['AEGRA'],services:[],editable:true,restricted:true}});
    if(request.method()==='PUT'){saved=request.postDataJSON();return route.fulfill({json:{revision:1}});}
    return route.fulfill({json:{revision:0,drivers:[],rows:[]}});
   }
   const file=url.pathname==='/tally-access'?'access.html':path.basename(url.pathname);
   return route.fulfill({contentType:file.endsWith('.html')?'text/html':file.endsWith('.css')?'text/css':'text/javascript',body:fs.readFileSync(path.join(assets,file))});
  });
  await page.goto('https://tally.test/tally-access#'+'a'.repeat(43));
  await page.getByRole('tab',{name:'Bodega 1',exact:true}).waitFor();
  for(const id of ['tallyNew','tallySettings','tallyCatalog','tallyHistory'])assert.equal(await page.locator('#'+id).isVisible(),false);
  const cell=page.locator('.tabulator-row [tabulator-field="spc"]').first();
  await cell.dblclick();await cell.locator('input').fill('123');await cell.locator('input').press('Enter');
  await page.waitForTimeout(600);assert.equal(saved.rows[0].spc,'123');
  await page.locator('#tallyProject').selectOption('3');
  await page.waitForTimeout(200);
  assert.equal(await page.locator('#tallyProject').inputValue(),'3');
  for(const width of [1440,390]){
   await page.setViewportSize({width,height:900});
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
   await page.screenshot({path:path.resolve(__dirname,`../../tmp/tally-qa/patricia-${width}.png`),fullPage:true});
  }
  assert.deepEqual(errors,[]);console.log('PASS direct access, restricted controls, MCI project switching, autosave, desktop/mobile');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
