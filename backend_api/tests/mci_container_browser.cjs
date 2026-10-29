const {chromium}=require('C:/Users/aaron/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('fs'),path=require('path'),assert=require('assert');
const root=path.resolve(__dirname,'../..');
const js=fs.readFileSync(path.join(root,'backend_api/assets/mci_surveys/editor.js'),'utf8');
const css=fs.readFileSync(path.join(root,'backend_api/assets/certificates/certificates.css'),'utf8');
const sections={introduction:'INTRODUCTION',purpose:'Purpose',instructions:'Instructions',representatives:'Representatives',particulars:'PARTICULARS',timesheet:'EXTRACT TIME SHEET',damage:'DETAILS OF DAMAGE / SHORTAGE (IF ANY) OR INSPECTION CAUSE',remarks:'REMARKS',conclusion:'CONCLUSION',enclosure:'SURVEY LINK PICTURES',attachments:'ENCLOSURES'};
const groups={introduction:['purpose','instructions','representatives'],particulars:[],timesheet:[],damage:[],remarks:[],conclusion:[],enclosure:[],attachments:[]};
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
 try{
  const page=await browser.newPage(),errors=[],writes=[];
  page.on('pageerror',e=>errors.push(e.message));
  const row={id:44,kind:'container',service_id:538,report_number:'QA-2253',vessel:'HAMU-QA',requested_by:'QA CLIENT',status:'Draft',source_filename:'Original.docx',content:{hierarchy_version:2,cargo:'Tuna',sections:{}}};
  await page.route('http://container.test/**',route=>{
   const req=route.request(),p=new URL(req.url()).pathname,send=x=>route.fulfill({json:x});
   if(p==='/')return route.fulfill({contentType:'text/html',body:`<meta charset="utf-8"><style>body{margin:0;font:14px Arial}${css}</style><main></main><script>${js}</script>`});
   if(p.endsWith('bootstrap'))return send({ready:true,permissions:{view:true,create:true,edit:true,approve:true},sections,groups,fields:{cargo:'Cargo',quantity:'Quantity',shipper:'Shipper'}});
   if(req.method()==='PATCH'){writes.push(req.postDataJSON());Object.assign(row,{content:req.postDataJSON().content});return send({data:row,version:'v2'});}
   return send(p.endsWith('/44')?{data:row,version:'v1'}:{data:[row],more:false});
  });
  await page.goto('http://container.test/');
  await page.evaluate(()=>SOMMCISurveys.mount(document.querySelector('main'),{kind:'container',headers:()=>({'X-Company-Code':'MCI-CR'})}));
  await page.locator('[data-open]').click();
  await page.getByRole('heading',{name:'Container Survey Report',exact:true}).waitFor();
  assert.equal(await page.locator('[name=imo]').count(),0);
  assert.equal(await page.getByRole('button',{name:'Original Word',exact:true}).count(),1);
  assert(await page.locator('[data-enable=purpose]').isDisabled());
  await page.locator('[data-enable=introduction]').check();
  await page.locator('[data-enable=purpose]').check();
  await page.locator('[data-block=purpose]').fill('QA purpose');
  await page.locator('[data-enable=damage]').check();
  await page.locator('[data-block=damage]').fill('QA damage');
  await page.locator('[data-add=damage]').click();
  assert.equal(await page.locator('[data-block=damage]').count(),2);
  await page.locator('[data-enable=enclosure]').check();
  assert.equal(await page.locator('[data-add=enclosure]').count(),0);
  await page.locator('#mci-picture-link').fill('https://example.com/photos');
  for(const width of [1440,800,390]){
   await page.setViewportSize({width,height:1000});
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
   await page.screenshot({path:path.join(root,`tmp/figal-container/editor-${width}.png`),fullPage:true});
  }
  await page.getByRole('button',{name:'Save draft',exact:true}).click();
  await page.getByText('Saved',{exact:true}).waitFor();
  assert.equal(writes[0].kind,'container');assert.equal(writes[0].content.sections.purpose.blocks[0].text,'QA purpose');
  assert.deepEqual(errors,[]);
  console.log('PASS container metadata, section hierarchy, blocks, original, save, 3 viewports');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
