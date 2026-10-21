const {chromium}=require('C:/Users/aaron/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('fs'),path=require('path'),assert=require('assert');
const root=path.resolve(__dirname,'../..');
const script=fs.readFileSync(path.join(root,'backend_api/assets/service_voice/voice.js'),'utf8');
const css=fs.readFileSync(path.join(root,'backend_api/assets/service_voice/voice.css'),'utf8');
const shell=fs.readFileSync(path.join(root,'backend_api/routers/som_web.py'),'utf8').match(/<style>([\s\S]*?)<\/style>/)[1];
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
 try {
  for(const width of [1280,390]) {
   const page=await browser.newPage({viewport:{width,height:1000}}),errors=[];
   page.on('pageerror',e=>errors.push(e.message));
   await page.route('http://voice.test/**',route=>{
    if(route.request().url().endsWith('mic.svg'))return route.fulfill({contentType:'image/svg+xml',body:fs.readFileSync(path.join(root,'backend_api/assets/service_voice/mic.svg'),'utf8')});
    return route.fulfill({contentType:'text/html',body:`<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><style>${shell}${css}body{display:block;padding:12px;margin:0}main{max-width:900px;margin:auto}</style><main><h2>Agregar servicio</h2><div id="voice"></div><label>Buque<input id="svcForm_buque_contenedor" value=""></label><label>Cliente<select id="svcForm_cliente"><option></option><option>Pandi Costa Rica</option><option>Pandi Panama</option></select></label><label>Operacion<select id="svcForm_operacion"><option></option><option>Draft Survey Initial</option><option>Draft Survey Final</option></select></label><label>Fecha<input type="date" id="svcForm_fecha_inicio"></label><label>Hora<input type="time" id="svcForm_hora_inicio"></label><button id="save">Guardar</button></main><script>${script}</script>`});
   });
   await page.goto('http://voice.test');
   await page.evaluate(()=>{
    window.saved=0;document.querySelector('#save').onclick=()=>window.saved++;
    window.dispose=ServiceVoice.mount(document.querySelector('#voice'),{
     snapshot:()=>document.querySelector('#svcForm_buque_contenedor').value,
     audio:async()=>({text:'Buque MV prueba, Cliente Pandi, servicio Draft Survey'}),
     parse:async()=>({buque_contenedor:'MV prueba',cliente:'Pandi',operacion:'Draft Survey',fecha_inicio:'2026-10-24',hora_inicio:'10:00',surveyors:[{nombre:'Erick Garay'}],advertencias:[]}),
     surveyors:()=>['Erick Garay'],applySurveyors:people=>window.people=people,
     locations:async()=>({data:[]})
    });
   });
   await page.locator('[data-audio]').setInputFiles({name:'test.webm',mimeType:'audio/webm',buffer:Buffer.alloc(200)});
   await page.locator('[data-text]').waitFor({state:'visible'});
   await page.locator('[data-parse]').click();
   await page.getByRole('button',{name:'Aplicar campos seleccionados'}).waitFor();
   assert.equal(await page.locator('#svcForm_buque_contenedor').inputValue(),'');
   assert.equal(await page.locator('.voice-row').filter({hasText:'Cliente:'}).locator('select').inputValue(),'');
   assert.equal(await page.locator('.voice-row').filter({hasText:'Operacion:'}).locator('select').inputValue(),'');
   fs.mkdirSync(path.join(root,'tmp/voice-qa'),{recursive:true});
   await page.screenshot({path:path.join(root,`tmp/voice-qa/preview-${width}.png`),fullPage:true});
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
   await page.locator('.voice-row').filter({hasText:'Cliente:'}).locator('select').selectOption('Pandi Costa Rica');
   await page.locator('.voice-row').filter({hasText:'Operacion:'}).locator('select').selectOption('Draft Survey Initial');
   await page.getByRole('button',{name:'Aplicar campos seleccionados'}).click();
   assert.equal(await page.locator('#svcForm_buque_contenedor').inputValue(),'MV prueba');
   assert.equal(await page.locator('#svcForm_fecha_inicio').inputValue(),'2026-10-24');
   assert.equal(await page.locator('#svcForm_hora_inicio').inputValue(),'10:00');
   assert.equal(await page.evaluate(()=>window.saved),0);
   assert.equal(await page.evaluate(()=>window.people[0].name),'Erick Garay');
   await page.evaluate(()=>{window.dispose();});
   await page.evaluate(()=>{
    window.stopped=0;window.uploads=0;
    Object.defineProperty(navigator,'mediaDevices',{configurable:true,value:{getUserMedia:async()=>({getTracks:()=>[{stop:()=>window.stopped++}]})}});
    window.MediaRecorder=class {
     static isTypeSupported(){return true}
     constructor(){this.state='inactive';this.mimeType='audio/webm'}
     start(){this.state='recording'}
     stop(){this.state='inactive';this.ondataavailable({data:new Blob(['x'.repeat(200)])});this.onstop()}
    };
    window.dispose=ServiceVoice.mount(document.querySelector('#voice'),{audio:async()=>{window.uploads++;return {text:'Buque QA'};}});
   });
   await page.locator('[data-record]').click();
   await page.locator('[data-stop]').waitFor({state:'visible'});
   await page.evaluate(()=>window.dispose());
   assert.equal(await page.evaluate(()=>window.stopped),1);
   assert.equal(await page.evaluate(()=>window.uploads),0);
   await page.evaluate(()=>{
    navigator.mediaDevices.getUserMedia=async()=>{throw Object.assign(new Error(),{name:'NotAllowedError'})};
    window.dispose=ServiceVoice.mount(document.querySelector('#voice'),{});
   });
   await page.locator('[data-record]').click();
   await page.getByText('Permiso de microfono denegado.',{exact:false}).waitFor();
   await page.evaluate(()=>window.dispose());
   assert.deepEqual(errors,[]);
   await page.close();
  }
  console.log('PASS: desktop/mobile review, ambiguity, date/time, explicit apply, no automatic saves or overflow.');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
