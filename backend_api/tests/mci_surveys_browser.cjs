const {chromium}=require('C:/Users/aaron/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('fs'),path=require('path'),assert=require('assert');
const root=path.resolve(__dirname,'../..'),js=fs.readFileSync(path.join(root,'backend_api/assets/mci_surveys/editor.js'),'utf8'),css=fs.readFileSync(path.join(root,'backend_api/assets/certificates/certificates.css'),'utf8');
const sections={instructions:'INSTRUCTIONS, SCOPE AND METHODOLOGY',work:'Work performed',limitations:'Main limitations of this report',chronology:'Time and place of arrival and chronology of events',representatives:'Representatives',findings:'SURVEY FINDINGS',visual:'Visual inspection',provided:'Documentation provided',missing:'Documentation not provided',conclusion:'CONCLUSION',enclosure:'ENCLOSURE'};
async function main(){
 const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
 try{
  const page=await browser.newPage(),errors=[],writes=[];let conflict=false;
  let row={id:1,kind:'vessel',service_id:3,company_code:'MCI-CR',report_number:'QA-1',vessel:'MV QA',requested_by:'QA CLIENT',status:'Draft',content:{sections:{}}};
  page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept());
  await page.route('http://mci.test/**',route=>{
   const r=route.request(),p=new URL(r.url()).pathname,send=d=>route.fulfill({json:d});
   if(p==='/')return route.fulfill({contentType:'text/html; charset=utf-8',body:`<meta charset="utf-8"><style>body{margin:0;font:14px Arial}input{width:100%;min-height:40px}label{justify-content:space-between}${css}</style><main id="root"></main><script>${js}</script>`});
   if(p.endsWith('/bootstrap'))return send({ready:true,permissions:{create:true,edit:true,approve:true},sections});
   if(p.endsWith('/services'))return send({data:[{consec:3,num_informe:'QA-1',buque_contenedor:'MV QA',cliente:'QA CLIENT',puerto:'Caldera',pais:'Costa Rica'}],more:false});
   if(r.method()==='GET')return send(p.endsWith('/1')?{data:row,version:'v1'}:{data:[row],more:false});
   const body=r.postDataJSON();writes.push(body);
   if(conflict)return route.fulfill({status:409,json:{detail:'Conflicto de version'}});
   row={...row,content:body.content||row.content,status:body.status||'Draft'};return send({data:row,version:'v2'});
  });
  await page.goto('http://mci.test/');await page.evaluate(()=>SOMMCISurveys.mount(document.querySelector('main'),{kind:'vessel',headers:()=>({})}));
  await page.locator('[data-create]').click();await page.locator('[data-service]').waitFor();assert.equal(await page.locator('[data-open]').count(),0);
  await page.locator('[data-service]').click();
  assert.equal(await page.locator('[name=title]').count(),0);
  assert.equal(await page.locator('#mci-location').inputValue(),'Caldera, Costa Rica');
  assert(await page.locator('#mci-location').evaluate(e=>e.readOnly));
  assert(await page.locator('[data-enable=work]').isDisabled());
  await page.locator('[data-enable=instructions]').check();
  await page.locator('[data-enable=work]').check();await page.locator('[data-block=work]').fill('Preserved text');
  await page.locator('[data-enable=instructions]').uncheck();
  assert.equal(await page.locator('[data-block=work]').count(),0);
  assert(await page.locator('[data-enable=work]').isChecked());
  await page.locator('[data-enable=instructions]').check();
  assert.equal(await page.locator('[data-block=work]').inputValue(),'Preserved text');
  await page.locator('[data-enable=work]').uncheck();await page.locator('[data-enable=work]').check();assert.equal(await page.locator('[data-block=work]').inputValue(),'Preserved text');
  await page.locator('[data-add=work]').click();assert.equal(await page.locator('[data-block=work]').count(),2);await page.locator('[data-remove=work]').last().click();
  const dir=fs.mkdtempSync(path.join(require('os').tmpdir(),'mci-web-'));
  for(const width of [1440,800,390]){
   await page.setViewportSize({width,height:1000});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
   const metrics=await page.evaluate(()=>({height:document.querySelector('.mci-section-options').getBoundingClientRect().height,items:[...document.querySelectorAll('.mci-section-option')].map(l=>{const a=l.querySelector('input').getBoundingClientRect(),b=l.querySelector('span').getBoundingClientRect();return {width:a.width,gap:b.left-a.right};})}));
   assert(metrics.height<(width===390?750:420));
   assert(metrics.items.every(m=>m.width===18&&m.gap>=8&&m.gap<=12));
   assert.equal(await page.locator('.mci-text-section').count(),1);
   await page.screenshot({path:path.join(dir,`${width}.png`),fullPage:true});
  }
  conflict=true;await page.locator('button[type=submit]').click();await page.getByText('Conflicto de version').waitFor();assert.equal(await page.locator('[data-block=work]').inputValue(),'Preserved text');
  conflict=false;await page.locator('button[type=submit]').click();await page.getByText('Saved',{exact:true}).waitFor();
  assert.equal(writes.at(-1).content.hierarchy_version,2);
  assert.equal(writes.at(-1).service_id,3);assert(!('company_code' in writes.at(-1)));assert(!('vessel' in writes.at(-1)));assert.equal(writes.at(-1).content.sections.work.blocks[0].text,'Preserved text');
  assert.deepEqual(errors,[]);console.log('PASS MCI create/review, optional sections, add/remove, retained disabled text, identity, conflicts, 3 viewports. Screenshots:',dir);
 }finally{await browser.close();}
}
main().catch(e=>{console.error(e);process.exitCode=1;});
