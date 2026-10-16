const {chromium}=require('C:/Users/aaron/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('fs'),path=require('path'),assert=require('assert');
const root=path.resolve(__dirname,'../..');
const js=fs.readFileSync(path.join(root,'backend_api/assets/admin/admin.js'),'utf8');
const css=fs.readFileSync(path.join(root,'backend_api/assets/admin/admin.css'),'utf8');
const shell=fs.readFileSync(path.join(root,'backend_api/routers/som_web.py'),'utf8').match(/<style>([\s\S]*?)<\/style>/)[1];
async function run(){
 const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept());
  await page.route('http://admin.test/',r=>r.fulfill({contentType:'text/html',body:`<style>${shell}\nbody{display:block;padding:12px;margin:0}#content{min-width:0}${css}</style><main id="content"></main><script>${js}</script>`}));
  await page.goto('http://admin.test/');
  await page.evaluate(()=>{
   window.calls=[];
   const modules=['dashboard','master_data','servicios','finanzas','hhrre','comercial','informes','portia','qa_som','admin_users'].map(code=>({code,label:code}));
   SOMAdmin.mount(document.getElementById('content'),{request:async(path,method='GET',payload)=>{
    calls.push({path,method,payload:payload?JSON.parse(JSON.stringify(payload)):null});
    if(method!=='GET')return {status:'OK'};
    if(path.endsWith('/meta'))return {modules,actions:[{code:'view',label:'Ver'},{code:'edit',label:'Editar'}],module_actions:{},roles:['user','admin'],password_rules:['Minimo 12 caracteres']};
    if(path.endsWith('/people'))return {people:[{source_type:'empleado',source_id:'1',label:'Ana Test',nombre:'Ana',apellido:'Test'}]};
    if(path.endsWith('/permissions'))return {source:'inherited',permissions:{},inherited_permissions:{dashboard:['view']}};
    if(path.includes('/audit'))return {data:[{created_at:'2026-10-15',actor_usuario:'admin',target_usuario:'test',action:'CREATE_USER'}],has_more:!path.endsWith('100')};
    return {users:[{usuario:'test',rol:'user',activo:true}]};
   }});
  });
  assert.equal(await page.evaluate(()=>calls.length),0);
  await page.locator('[data-authorize]').click();await page.locator('[data-create]').waitFor();
  assert.equal(await page.locator('fieldset').count(),10);
  fs.mkdirSync(path.join(root,'tmp/admin-qa'),{recursive:true});
  for(const width of [1440,390,320]){
   await page.setViewportSize({width,height:1000});
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`overflow ${width}`);
   await page.screenshot({path:path.join(root,`tmp/admin-qa/create-${width}.png`),fullPage:true});
  }
  await page.locator('[name=person]').selectOption('0');
  assert.equal(await page.locator('[name=usuario]').inputValue(),'ana.test');
  await page.locator('[name=password]').fill('StrongPassword123!');
  await page.locator('[type=submit]').click();
  await page.getByText('Usuario ana.test creado correctamente.',{exact:true}).waitFor();
  assert.equal(await page.locator('[name=password]').inputValue(),'');
  assert.equal(await page.evaluate(()=>calls.find(c=>c.method==='POST').payload.source_id),'1');
  await page.locator('[data-tab=permissions]').click();
  await page.locator('[data-user]').selectOption('test');
  await page.locator('[data-permission]:checked').waitFor();
  await page.locator('[data-permission]:checked').uncheck();
  await page.locator('[data-save]').click();
  await page.getByText('No se guardo: una matriz vacia reactivaria los permisos heredados.',{exact:true}).waitFor();
  assert.equal(await page.evaluate(()=>calls.filter(c=>c.method==='PUT').length),0);
  await page.locator('[data-module=dashboard][data-permission=view]').check();
  await page.locator('[data-save]').click();
  await page.getByText('Permisos guardados. El usuario debe volver a iniciar sesion.',{exact:true}).waitFor();
  assert.equal(await page.evaluate(()=>calls.filter(c=>c.method==='PUT').length),1);
  await page.locator('[data-tab=audit]').click();await page.getByText('CREATE_USER',{exact:true}).waitFor();
  await page.locator('[data-next]').click();await page.getByText('Pagina 2',{exact:true}).waitFor();
  assert(await page.locator('[data-next]').isDisabled());
  assert.deepEqual(errors,[]);console.log('PASS: responsive layouts, create, inherited permissions, empty-save guard, save, audit pagination; no real data modified.');
 }finally{await browser.close();}
}
run().catch(e=>{console.error(e);process.exitCode=1;});
