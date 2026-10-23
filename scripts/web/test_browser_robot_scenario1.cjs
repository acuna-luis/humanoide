// Disabled-service browser test only. Test server must bind loopback.
const fs=require('fs');
const base='http://127.0.0.1:18777', chrome='http://127.0.0.1:18778';
const out=process.argv[2]; if(!out) throw Error('Specify a NEW output directory');
fs.mkdirSync(out);
(async()=>{
 const target=await(await fetch(chrome+'/json/new?about:blank',{method:'PUT'})).json();
 const ws=new WebSocket(target.webSocketDebuggerUrl);
 await new Promise(r=>ws.addEventListener('open',r,{once:true}));
 let id=0;const pending=new Map(),tests=[];
 ws.addEventListener('message',e=>{const m=JSON.parse(e.data);if(m.id){const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(m.error):p.resolve(m.result)}});
 function call(method,params={}){return new Promise((resolve,reject)=>{const n=++id;pending.set(n,{resolve,reject});ws.send(JSON.stringify({id:n,method,params}))})}
 async function ev(expression){const r=await call('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value}
 function check(name,value){tests.push({name,passed:!!value});if(!value)throw Error(name)}
 await call('Page.enable');await call('Network.enable');
 await call('Emulation.setDeviceMetricsOverride',{width:1280,height:1100,deviceScaleFactor:1,mobile:false});
 await call('Network.setBlockedURLs',{urls:['http://192.168.*','https://*','ws://*','wss://*']});
 await call('Page.navigate',{url:base});
 await ev(`new Promise(r=>{const t=setInterval(()=>{if(document.querySelector('#login')){clearInterval(t);r(true)}},30);setTimeout(()=>{clearInterval(t);r(false)},5000)})`);
 check('login displayed',await ev(`!document.querySelector('#login').hidden`));
 await ev(`document.querySelector('#token').value='offline-test-only';document.querySelector('#login').requestSubmit()`);
 check('login and state loaded',await ev(`new Promise(r=>{const t=setInterval(()=>{if(!document.querySelector('#panel').hidden){clearInterval(t);r(true)}},30);setTimeout(()=>{clearInterval(t);r(false)},5000)})`));
 check('requested actions and heights',await ev(`document.querySelector('#home').textContent==='Ir a HOME' && document.querySelector('#cycle').textContent==='Ejecutar ciclo' && [...document.querySelectorAll('option')].map(x=>x.value).join('|')==='74|90'`));
 await ev(`document.querySelector('#physical').click();document.querySelector('#trial').click()`);
 check('disabled service cannot be armed by checkboxes',await ev(`document.querySelector('#home').disabled && document.querySelector('#cycle').disabled`));
 check('trial and no-PC state visible',await ev(`document.body.textContent.includes('Sin PC externo') && document.body.textContent.includes('pendientes de validación')`));
 let shot=await call('Page.captureScreenshot',{format:'png'});fs.writeFileSync(out+'/desktop.png',Buffer.from(shot.data,'base64'));
 await call('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
 check('mobile fits',await ev(`document.documentElement.scrollWidth<=innerWidth`));
 shot=await call('Page.captureScreenshot',{format:'png'});fs.writeFileSync(out+'/mobile.png',Buffer.from(shot.data,'base64'));
 fs.writeFileSync(out+'/results.json',JSON.stringify(tests,null,2));console.log(JSON.stringify(tests));
 await call('Browser.close');ws.close();
})().catch(e=>{console.error(e);process.exit(1)});
