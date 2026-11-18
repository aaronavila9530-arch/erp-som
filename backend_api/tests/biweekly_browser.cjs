const {chromium}=require('C:/Users/aaron/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('fs'),cp=require('child_process'),assert=require('assert');
const html=cp.execFileSync('python',['-X','utf8','-c',"import ast; t=ast.parse(open('backend_api/routers/som_web.py',encoding='utf8').read()); f=next(n for n in t.body if isinstance(n,ast.FunctionDef) and n.name=='som_web_home'); print(next(n.value.value for n in f.body if isinstance(n,ast.Assign) and isinstance(n.value,ast.Constant) and isinstance(n.value.value,str)))"],{encoding:'utf8'});
const code=html.slice(html.indexOf('    function itpBiOptions'),html.indexOf('    async function saveItpBiweeklyDraft'));
(async()=>{const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});try{
 const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.setContent('<div id="itpBiTable"></div><span id="itpBiSelectionCount"></span>');
 await page.addScriptTag({content:`
 const $=id=>document.getElementById(id), esc=x=>String(x??'').replace(/"/g,'&quot;');
 let itpBiweeklyRows=[{name:'A',amount:10},{name:'B',amount:20}],itpBiweeklyChecked=new Set(),itpBiweeklySuppressed=new Set(),selectedItpBiweeklyIndex=null;
 const ITP_BI_CATEGORIES=['Otros'],ITP_BI_PAYMENT_METHODS=['BANK'],ITP_BI_BANK_ACCOUNTS=['1'];
 const selectedCompany=()=> 'MSL-CR',normalizeItpBiPaymentRow=r=>r,itpBiStatus=()=> 'Pendiente',itpBiPaymentLabel=()=> 'Banco',itpBiReady=()=>false,itpBiRowKey=r=>r.name,valueFrom=id=>id==='itpBiPeriod'?'2026-11':'2',previousBusinessDayCR=x=>x;
 ${code}
 renderItpBiweeklyTable();`});
 await page.locator('[data-bi-check="0"]').check();await page.locator('[data-bi-check="1"]').check();
 assert.equal(await page.evaluate(()=>itpBiweeklyChecked.size),2);
 await page.evaluate(()=>deleteCheckedItpBiweeklyLines());assert.equal(await page.locator('tbody tr').count(),0);
 await page.evaluate(()=>addItpBiweeklyLine());assert.equal(await page.locator('[data-field="name"]').evaluate(e=>e===document.activeElement),true);
 await page.locator('[data-field="name"]').evaluate(e=>{const d=new DataTransfer();d.setData('text/plain','American Data\t100\tUSD\nPrime Properties\t200\tUSD');e.dispatchEvent(new ClipboardEvent('paste',{clipboardData:d,bubbles:true,cancelable:true}));});
 assert.deepEqual(await page.evaluate(()=>itpBiweeklyRows.map(r=>[r.name,r.amount])),[['American Data',100],['Prime Properties',200]]);
 assert.deepEqual(errors,[]);console.log('PASS: multiseleccion, eliminar varias, agregar con foco y pegar dos filas.');
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exit(1)});
