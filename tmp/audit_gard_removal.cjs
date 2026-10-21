const base='https://api-som-fastapi-production-e66d.up.railway.app';
(async()=>{
for(const path of ['/billing/00100001090000000001','/collections/search?cliente=Gard&page_size=100','/servicios/505']){
const r=await fetch(base+path,{headers:{'X-Company-Code':'MCI-CR'}});
console.log(path,r.status,await r.text());
}
})().catch(e=>{console.error(e);process.exitCode=1});
