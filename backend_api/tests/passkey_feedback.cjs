const cp=require('child_process'),vm=require('vm'),assert=require('assert');
const source=`import ast,json
t=ast.parse(open('backend_api/routers/som_web.py',encoding='utf-8-sig').read())
f=next(n for n in t.body if isinstance(n,ast.FunctionDef) and n.name=='som_web_home')
a=next(n for n in f.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='html' for x in n.targets))
print(json.dumps(ast.literal_eval(a.value)))`;
const html=JSON.parse(cp.execFileSync('python',['-c',source],{encoding:'utf8'}));
const code=html.slice(html.indexOf('    function bytesFromBase64url'),html.indexOf('    function renderNav'));
function setup(saved,get){
 const elements={};const el=id=>elements[id]??={value:'',textContent:'',disabled:false,classList:{add(){},remove(){}}};
 const context={window:{isSecureContext:true,PublicKeyCredential:function(){}},navigator:{credentials:{get,create:async()=>({rawId:new Uint8Array([1,2]).buffer})}},
  $:el,readLocalJson:()=>saved,PASSKEY_KEY:'key',session:{usuario:'qa',company:'MCI-CR'},crypto:require('crypto').webcrypto,Uint8Array,
  btoa:s=>Buffer.from(s,'binary').toString('base64'),atob:s=>Buffer.from(s,'base64').toString('binary'),localStorage:{setItem(){}},alert(){}};
 vm.createContext(context);vm.runInContext(code,context);return {context,el};
}
(async()=>{
 let calls=0;let f=setup(null,async()=>{calls++});await f.context.unlockWithPasskey();assert(f.el('loginMsg').textContent.includes('no tiene configurado'));assert.equal(calls,0);
 f=setup(null,async()=>{});f.context.window.isSecureContext=false;await f.context.unlockWithPasskey();assert(f.el('loginMsg').textContent.includes('HTTPS'));
 const saved={id:'AQI',usuario:'qa',company:'MCI-CR'};
 f=setup(saved,async()=>{throw Object.assign(new Error(),{name:'NotAllowedError'})});await f.context.unlockWithPasskey();assert(f.el('loginMsg').textContent.includes('cancelada'));assert.equal(f.el('bioBtn').disabled,false);
 f=setup(saved,async()=>({rawId:new Uint8Array([1,2]).buffer}));await f.context.unlockWithPasskey();assert.equal(f.context.pendingUser,'qa');assert.equal(f.context.pendingAction,'VERIFY_TOTP');assert(f.el('totpMsg').textContent.includes('Authenticator'));
 f=setup(saved,async()=>({rawId:new Uint8Array([3,4]).buffer}));await f.context.unlockWithPasskey();assert.equal(f.context.pendingUser,undefined);
 let release;calls=0;f=setup(saved,()=>{calls++;return new Promise(r=>release=r)});const pending=f.context.unlockWithPasskey();await f.context.unlockWithPasskey();assert.equal(calls,1);release({rawId:new Uint8Array([1,2]).buffer});await pending;
 assert(!html.includes('disabled = !window.PublicKeyCredential || !localStorage.getItem(PASSKEY_KEY)'));
 console.log('PASS: missing setup, insecure context, cancel, correct credential, mismatch, double tap, TOTP retained.');
})().catch(e=>{console.error(e);process.exit(1)});
