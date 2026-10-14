const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = fs.readFileSync('backend_api/routers/som_web.py', 'utf8');
function extract(name, next) {
  const start = source.indexOf(`    async function ${name}(`);
  return source.slice(start, source.indexOf(`    ${next}`, start + 1));
}
const select = {innerHTML:'', dataset:{}};
const ctx = vm.createContext({
  company:'MSL-CR', select, financeClientes:[], financeClienteRows:[],
  collectionClientes:[], collectionClientesLoaded:false,
  selectedCompany:()=>ctx.company, $:()=>select, rowsList:p=>p.data,
  esc:s=>s, alert:e=>{throw Error(e)},
});
vm.runInContext(extract('ensureFinanceClientes', 'function financeClientName'),ctx);
vm.runInContext(extract('loadCollectionsClientes', 'function collectionParams'),ctx);
const row = (name)=>({codigo:name,nombrejuridico:name});
(async()=>{
  ctx.getJSON = async (path, headers)=>{
    assert.equal(headers['X-Company-Code'],ctx.company);
    return {total:501,data:path.includes('page=1&')?Array.from({length:500},(_,i)=>row('MSL'+i)):[row('LAST')]};
  };
  assert.equal((await ctx.ensureFinanceClientes()).length,501);
  ctx.company='MCI-CR';
  ctx.getJSON=async path=>path.startsWith('/clientes')
    ? {total:1,data:[row('TECH MARINE SURVEY UK LTD')]}
    : {total:1,data:[{nombre_cliente:'HISTORICAL CLIENT'}]};
  await ctx.loadCollectionsClientes();
  assert(select.innerHTML.includes('TECH MARINE SURVEY UK LTD'));
  assert(select.innerHTML.includes('HISTORICAL CLIENT'));
  assert(!select.innerHTML.includes('MSL0'));
  assert.equal(ctx.financeClienteRows.length,1);
  // A later Master Data update must be visible without logging out.
  ctx.getJSON=async()=>({total:2,data:[row('TECH MARINE SURVEY UK LTD'),row('NEW')]});
  assert.equal((await ctx.ensureFinanceClientes()).length,2);
  ctx.getJSON=async()=>{throw Error('offline')};
  await assert.rejects(ctx.ensureFinanceClientes(),/offline/);
  ctx.getJSON=async()=>{ctx.company='MSL-CR';return {total:1,data:[row('WRONG TENANT')]}};
  await assert.rejects(ctx.ensureFinanceClientes(),/empresa/);
  assert(!ctx.financeClientes.includes('WRONG TENANT'));
  console.log('PASS: pagination, company switching, Master Data freshness, Collections union, errors and stale responses');
})().catch(e=>{console.error(e);process.exitCode=1});
