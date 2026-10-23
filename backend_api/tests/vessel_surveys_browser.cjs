const {chromium}=require('C:/Users/aaron/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('fs'),path=require('path'),assert=require('assert'),cp=require('child_process');
const root=path.resolve(__dirname,'../..');
const types=JSON.parse(cp.execFileSync('python',['-c',"import sys,json;sys.path.insert(0,'backend_api');from services.vessel_web_fields import VESSEL_TYPES;print(json.dumps(VESSEL_TYPES))"],{cwd:root,encoding:'utf8'}));
async function main(){
 const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
 try{
  const page=await browser.newPage(),errors=[];
  page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept());
  await page.route('http://vessel.test/**',route=>{
   const p=new URL(route.request().url()).pathname;
   if(p==='/')return route.fulfill({contentType:'text/html; charset=utf-8',body:`<meta charset="utf-8"><style>body{margin:0}${fs.readFileSync(path.join(root,'backend_api/assets/certificates/certificates.css'),'utf8')}</style><main></main><script>${fs.readFileSync(path.join(root,'backend_api/assets/certificates/certificates.js'),'utf8')}</script>`});
   if(p.endsWith('/bootstrap'))return route.fulfill({json:{types,company:'MSL-CR',permissions:{view:true,create:true,edit:true,approve:true}}});
   const row={id:1,report_number:'QA-1',vessel:'QA VESSEL',status:'Draft',narrative_3:'Existing third paragraph'};
   return route.fulfill({json:p.endsWith('/1')?{data:row,version:'v1'}:{data:[row],total:1}});
  });
  for(const kind of Object.keys(types)){
   await page.goto('http://vessel.test/');
   await page.evaluate(kind=>SOMCertificates.mount(document.querySelector('main'),{kind,company:'MSL-CR',headers:()=>({})}),kind);
   await page.locator('[data-open]').click();
   await page.locator('#cert-form').waitFor();
   assert(await page.locator('[name=narrative_3]').isVisible());
   assert(!(await page.locator('[name=narrative_4]').isVisible()));
   const section=page.locator('details').filter({has:page.locator('[name=narrative_1]')});
   await section.getByRole('button',{name:'Agregar texto',exact:true}).click();
   assert(await page.locator('[name=narrative_4]').isVisible());
   await page.locator('[name=narrative_4]').fill('New text');
   await section.getByRole('button',{name:'Eliminar ultimo texto',exact:true}).click();
   assert.equal(await page.locator('[name=narrative_4]').inputValue(),'');
   for(const width of [1440,800,390]){await page.setViewportSize({width,height:1000});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));}
  }
  assert.deepEqual(errors,[]);console.log('PASS both MSL survey forms: retained paragraphs, add/remove, responsive widths.');
 }finally{await browser.close();}
}
main().catch(e=>{console.error(e);process.exitCode=1;});
