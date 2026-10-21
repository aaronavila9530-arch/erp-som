const base='https://api-som-fastapi-production-e66d.up.railway.app';
(async()=>{
 for(const path of ['/servicios/?page_size=1000&tipo=TODOS']){
 const r=await fetch(base+path,{headers:{'X-Company-Code':'MCI-CR'}});if(!r.ok)throw Error(r.status);
 const d=await r.json();
 console.log(path, 'TOTAL',d.total,JSON.stringify((d.data||d).map(x=>Object.fromEntries(['consec','cliente','estado','factura','num_informe','buque_contenedor','fecha_inicio'].map(k=>[k,x[k]])))));
 }
})().catch(e=>{console.error(e);process.exitCode=1});
