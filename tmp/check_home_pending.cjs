const fs = require('fs');
const vm = require('vm');
const {execFileSync} = require('child_process');
const {chromium} = require('C:/Users/aaron/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const assert = require('assert/strict');
const html = execFileSync('python', ['-c', `import ast,pathlib
t=ast.parse(pathlib.Path('backend_api/routers/som_web.py').read_text(encoding='utf-8'))
f=next(n for n in t.body if isinstance(n,ast.FunctionDef) and n.name=='som_web_home')
h=next(n.value.value for n in f.body if isinstance(n,ast.Assign) and isinstance(n.value,ast.Constant) and isinstance(n.value.value,str) and '<!doctype' in n.value.value)
import sys;sys.stdout.buffer.write(h.encode('utf-8'))`], {encoding:'utf8'});
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m=>m[1]);
scripts.forEach(script=>new vm.Script(script));
const script = scripts.find(s=>s.includes('let homePending ='));
const functions = script.slice(script.indexOf('    let homePending ='), script.indexOf('    function renderHome()'));
const style = html.match(/<style>([\s\S]*?)<\/style>/)[1];
(async()=>{
  const browser = await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
  try {
    const page = await browser.newPage();
    const loadedIcons = new Set();
    await page.route('http://som.test/som/queue-icon/*', async route=>{
      const name = new URL(route.request().url()).pathname.split('/').pop();
      await route.fulfill({contentType:'image/svg+xml',body:fs.readFileSync(`backend_api/assets/icons/lucide/${name}`)});
      loadedIcons.add(name);
    });
    const errors=[];page.on('pageerror',e=>errors.push(e.message));
    await page.setContent(`<base href="http://som.test/"><style>${style}</style><main style="padding:16px"><div id="homePendingTables" class="home-queue-section"></div></main>`);
    await page.addScriptTag({content:`const $=id=>document.getElementById(id); const intFmt=new Intl.NumberFormat('es'); const esc=v=>String(v??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;'); const selectedCompany=()=> 'MSL-CR'; const closeModal=()=> $('svcModal')?.remove(); const downloadExcelFile=(name,rows)=>window.exportedRows=rows; ${functions}`});
    await page.evaluate(()=>{
      const rows=Array.from({length:1205},(_,i)=>({consec:i+1,cliente:i===1204?'ULTIMO CLIENTE':'NORDEN',buque_contenedor:'MV DEMO',operacion:'Bunker Survey',fecha_fin:'2024-01-01',num_informe:`REP-${i+1}`}));
      renderHomePending({company:'MSL-CR',queues:{billing:{count:rows.length,rows},missing:{count:rows.length,rows},approval:{count:1,rows:[{...rows[0],tipo_informe:'Bunker Survey',numero:'REP-1',estado_informe:'Pending for review'}]},rework:{count:0,rows:[]},unlinked:{count:0,rows:[]}}});
    });
    for(const width of [1440,1100,1001,800,390,320]) {
      await page.setViewportSize({width,height:900});
      await page.locator('main').evaluate((el, width)=>el.style.marginLeft=width>1000?'260px':'0',width);
      await page.screenshot({path:`tmp/home_pending_${width}.png`,fullPage:true});
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
      assert(await page.locator('.home-queue-metric').evaluateAll(buttons=>buttons.every(button=>{
        const number=button.querySelector('.home-queue-value').getBoundingClientRect();
        const label=button.querySelector('.home-queue-label').getBoundingClientRect();
        const icon=button.querySelector('.home-queue-icon').getBoundingClientRect();
        return (number.bottom<=label.top || number.right<=label.left) && icon.right<=number.left;
      })));
    }
    assert.equal(loadedIcons.size,5);
    await page.setViewportSize({width:390,height:900});
    await page.getByRole('button',{name:'Servicios pendientes de facturación',exact:true}).click();
    assert.equal(await page.locator('#homePendingRows tbody tr').count(),100);
    await page.locator('#homePendingSearch').fill('ULTIMO CLIENTE');
    assert.equal(await page.locator('#homePendingRows tbody tr').count(),1);
    assert((await page.locator('#homePendingRows').innerText()).includes('1205'));
    await page.getByRole('button',{name:'Exportar Excel',exact:true}).click();
    assert.equal(await page.evaluate(()=>window.exportedRows.length),1);
    await page.locator('#homePendingSearch').fill('');
    await page.getByRole('button',{name:'Exportar Excel',exact:true}).click();
    assert.equal(await page.evaluate(()=>window.exportedRows.length),1205);
    await page.getByRole('button',{name:'Página siguiente',exact:true}).click();
    assert.equal(await page.locator('#homePendingPageLabel').innerText(),'2 / 13');
    await page.screenshot({path:'tmp/home_pending_modal_mobile.png'});
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    await page.getByRole('button',{name:'Cerrar',exact:true}).click();
    await page.getByRole('button',{name:'Informes pendientes de aprobación',exact:true}).click();
    await page.locator('#homePendingType').selectOption('Bunker Survey');
    assert.equal(await page.locator('#homePendingRows tbody tr').count(),1);
    await page.setViewportSize({width:1440,height:900});
    await page.screenshot({path:'tmp/home_pending_modal_desktop.png'});
    await page.getByRole('button',{name:'Cerrar',exact:true}).click();
    await page.evaluate(()=>{
      const rows=[{id:1,payee_name:'Proveedor',quincena:'2026-10 Q1',mes:'2026-10',currency:'CRC',balance:1000},{id:2,payee_name:'Surveyor',quincena:'2026-10 Q2',mes:'2026-10',currency:'USD',balance:50}];
      renderHomePending({company:'MSL-CR',queues:{payable_half:{count:2,rows,summary:[]},payable_month:{count:1,rows,summary:[]},payable_invoices:{count:2,rows},receivable_invoices:{count:0,rows:[]}}});
    });
    for(const width of [1440,390]) {
      await page.setViewportSize({width,height:900});
      await page.locator('main').evaluate(el=>el.style.marginLeft='0');
      await page.screenshot({path:`tmp/home_payables_${width}.png`,fullPage:true});
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    }
    await page.getByRole('button',{name:'Obligaciones por quincena',exact:true}).click();
    await page.locator('#homePaymentPeriod').selectOption('2026-10 Q2');
    assert.equal(await page.locator('#homePendingRows tbody tr').count(),1);
    assert((await page.locator('#homePendingRows').innerText()).includes('USD'));
    assert(!(await page.locator('#homePendingRows').innerText()).includes('CRC'));
    assert.deepEqual(errors,[]);
    console.log('PASS: JS syntax, desktop/mobile layout, drilldown, search, type filter, pagination and complete Excel export.');
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
