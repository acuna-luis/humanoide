// Browser integration checks using local Chrome CDP; no external dependencies.
const fs = require('fs');
const base = process.env.SCENARIO1_PREVIEW_URL || 'http://127.0.0.1:18774';
const chrome = process.env.SCENARIO1_CHROME_URL || 'http://127.0.0.1:18775';
for (const address of [base, chrome]) {
 const u = new URL(address);
 if (u.protocol !== 'http:' || !['127.0.0.1', 'localhost', '[::1]'].includes(u.hostname)) throw new Error('Tests require loopback-only URLs');
}
const out = process.argv[2];
if (!out) throw new Error('Usage: node --experimental-websocket scripts/web/test_browser_scenario1.cjs NEW_OUTPUT_DIRECTORY');
fs.mkdirSync(out, {recursive:false});
(async () => {
 const target = await (await fetch(chrome+'/json/new?about:blank', {method:'PUT'})).json();
 const ws = new WebSocket(target.webSocketDebuggerUrl);
 await new Promise(resolve => ws.addEventListener('open', resolve, {once:true}));
 let serial=0; const waiting=new Map(), failures=[], connections=[];
 ws.addEventListener('message', e => { const m=JSON.parse(e.data); if(m.id){const w=waiting.get(m.id);waiting.delete(m.id);m.error?w.reject(m.error):w.resolve(m.result);} else if(m.method==='Network.loadingFailed')failures.push(m.params);else if(m.method==='Network.webSocketCreated')connections.push(m.params.url); });
 function call(method,params={}) {return new Promise((resolve,reject)=>{const id=++serial;waiting.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params}));});}
 async function evaluate(expression) {const r=await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw new Error(JSON.stringify(r.exceptionDetails));return r.result.value;}
 await call('Page.enable');await call('Runtime.enable');await call('Network.enable');
 // Defense in depth alongside the preview response's CSP: never contact robots.
 await call('Network.setBlockedURLs',{urls:['http://192.168.*','https://*','ws://*','wss://*','http://127.0.0.1:5000/*','http://127.0.0.1:8100/*']});
 await call('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
 await call('Page.navigate',{url:base});
 await evaluate(`new Promise(resolve=>{const t=setInterval(()=>{if(document.querySelector('#sc1-host .sc1-launch') && document.querySelector('#root')?.children.length){clearInterval(t);resolve(true)}},100);setTimeout(()=>{clearInterval(t);resolve(false)},10000)})`);
 let tests=[];function check(name,pass){tests.push({name,passed:!!pass});if(!pass)throw new Error(name);}
 check('vendor React page mounted',await evaluate(`!!document.querySelector('#root')?.children.length`));
 check('two requested action labels present',await evaluate(`Array.from(document.querySelectorAll('#sc1-host [data-action] strong')).map(x=>x.textContent).join('|')==='Ir a HOME|Ejecutar ciclo'`));
 await evaluate(`document.querySelector('.sc1-launch').click()`);
 check('dialog opens',await evaluate(`document.querySelector('.sc1-dialog').open`));
 let screenshot=await call('Page.captureScreenshot',{format:'png'});fs.writeFileSync(out+'/desktop.png',Buffer.from(screenshot.data,'base64'));
 await evaluate(`document.querySelector('[data-action=home]').click()`);
 check('confirmation required',await evaluate(`document.querySelector('.sc1-confirm-go').disabled`));
 await evaluate(`document.querySelector('.sc1-confirm input').click();document.querySelector('.sc1-confirm-go').click()`);
 check('concurrent action disabled',await evaluate(`document.querySelector('[data-action=cycle]').disabled`));
 await evaluate(`new Promise(r=>setTimeout(r,1300))`);
 check('HOME explicitly simulated',await evaluate(`document.querySelector('.sc1-status').textContent.includes('HOME real NO verificado')`));
 await evaluate(`document.querySelector('select[aria-label="Altura de mesa"]').value='90';document.querySelector('[data-action=cycle]').click();document.querySelector('.sc1-confirm input').click();document.querySelector('.sc1-confirm-go').click()`);
 await evaluate(`new Promise(r=>setTimeout(r,3300))`);
 check('cycle explicitly simulated',await evaluate(`document.querySelector('.sc1-status').textContent.includes('Depósito y HOME reales NO verificados')`));
 await evaluate(`document.querySelector('[data-action=cycle]').click();document.querySelector('.sc1-confirm input').click();document.querySelector('.sc1-confirm-go').click();document.querySelector('.sc1-cancel').click()`);
 check('cancel only simulation',await evaluate(`document.querySelector('.sc1-status').textContent.includes('Simulación cancelada')`));
 await call('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
 await evaluate(`new Promise(r=>setTimeout(r,500))`);
 check('mobile panel fits viewport',await evaluate(`document.querySelector('.sc1-dialog').getBoundingClientRect().width<=innerWidth && document.querySelector('.sc1-dialog').getBoundingClientRect().left>=0`));
 screenshot=await call('Page.captureScreenshot',{format:'png'});fs.writeFileSync(out+'/mobile.png',Buffer.from(screenshot.data,'base64'));
 await evaluate(`document.querySelector('.sc1-close').click();document.querySelector('#sc1-host').remove();const s=document.createElement('script');s.src='/_scenario1/controls.js?disabled';document.body.appendChild(s)`);
 await evaluate(`new Promise(r=>setTimeout(r,400))`);
 check('production default disabled without integration',await evaluate(`Array.from(document.querySelectorAll('#sc1-host [data-action]')).every(x=>x.disabled)`));
 fs.writeFileSync(out+'/browser-results.json',JSON.stringify({tests,failedRequests:failures.map(x=>({blockedReason:x.blockedReason,error:x.errorText})),websocketAttempts:connections,robotRequestsPermitted:false},null,2));
 console.log(JSON.stringify(tests));ws.close();
})().catch(e=>{console.error(e);process.exit(1)});
