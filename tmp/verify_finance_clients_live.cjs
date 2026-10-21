const vm = require('node:vm');
const assert = require('node:assert/strict');
const base='https://api-som-fastapi-production-e66d.up.railway.app';
(async()=>{
  const version=await (await fetch(base+'/som/web-version')).json();
  console.log(version);
  if(version.asset_version!=='20261014-finance-client-catalog-v7') process.exit(2);
  const html=await (await fetch(base+'/som')).text();
  const select={innerHTML:'',dataset:{}};
  const ctx=vm.createContext({company:'MSL-CR',financeClientes:[],financeClienteRows:[],
    collectionClientes:[],collectionClientesLoaded:false,rowsList:p=>p.data,
    selectedCompany:()=>ctx.company,$:()=>select,esc:s=>s,alert:e=>{throw Error(e)},
    getJSON:async(path,headers)=>{const r=await fetch(base+path,{headers});assert(r.ok,`${path}: ${r.status}`);return r.json();}});
  for(const [name,next] of [['ensureFinanceClientes','function financeClientName'],['loadCollectionsClientes','function collectionParams']]){
    const start=html.indexOf(`    async function ${name}(`);
    assert(start>=0);
    vm.runInContext(html.slice(start,html.indexOf(`    ${next}`,start+1)),ctx);
  }
  const msl=await ctx.ensureFinanceClientes();
  console.log('MSL catalog',msl.length);
  ctx.company='MCI-CR';
  await ctx.loadCollectionsClientes();
  assert(ctx.financeClienteRows.some(r=>r.codigo==='MCI-0034-C'&&r.nombrejuridico==='TECH MARINE SURVEY UK LTD'));
  assert(select.innerHTML.includes('TECH MARINE SURVEY UK LTD'));
  console.log('PASS published functions + live MCI Master Data/Collections, TECH MARINE visible; MCI catalog',ctx.financeClienteRows.length);
})().catch(e=>{console.error(e);process.exitCode=1});
