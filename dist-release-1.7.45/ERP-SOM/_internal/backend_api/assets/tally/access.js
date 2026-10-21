(async function(){
  const root=document.querySelector('#tally');
  const token=location.hash.slice(1);
  // The fragment never reaches server access logs or Referer headers.
  if(!/^[A-Za-z0-9_-]{43}$/.test(token)){root.textContent='Enlace invalido. Solicite un enlace nuevo al administrador.';return;}
  const headers=()=>({'Content-Type':'application/json','X-Tally-Token':token});
  const url=path=>path.replace(/^\/tally\//,'/tally-access/api/');
  async function request(path,method='GET',body){
    const response=await fetch(url(path),{method,headers:headers(),cache:'no-store',credentials:'omit',body:body===undefined?undefined:JSON.stringify(body)});
    const data=await response.json();
    if(!response.ok)throw Error(typeof data.detail==='string'?data.detail:'No se pudo guardar. Revise los datos o contacte al administrador.');
    return data;
  }
  await SOMTally.mount(root,{user:'patricia.omier',company:'MCI-CR',headers,url,
    getJSON:path=>request(path),postJSON:(path,body)=>request(path,'POST',body),sendJSON:(method,path,body)=>request(path,method,body)});
})();
