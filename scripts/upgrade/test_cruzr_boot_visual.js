'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const {leaseRemaining, neutralSource} = require('./cruzr-boot-ready.js');
const date = 'Thu, 10 Sep 2026 10:00:00 GMT';
const payload = {schema:'cruzr-boot-ready-v1', ready:true, expression:'inspection',
  sequence:'a'.repeat(32), expires_at_ms:Date.parse(date)+12000};
assert.equal(leaseRemaining(payload, date, 100), 11100);
for (const bad of [null, {...payload, ready:false}, {...payload, sequence:'old'},
  {...payload, expires_at_ms:Date.parse(date)-1},
  {...payload, expires_at_ms:Date.parse(date)+60000}]) {
  assert.equal(leaseRemaining(bad, date, 100), 0);
}
assert.equal(leaseRemaining(payload, null, 100), 0);
assert(neutralSource('http://127.0.0.1:5000/expression/breath.mp4?v=1', 'http://face/'));
for (const name of ['warning-red', 'warning-yellow', 'warning-orange', 'inspection', 'blank']) {
  assert(!neutralSource('/expression/'+name+'.mp4', 'http://face/'));
}

(async function () {
  let now=100, mutation, failFetch=false, nativeSource='/expression/breath.mp4';
  const intervals={}, mediaListeners={};
  const video={style:{}, setAttribute(){}, pause(){}, play(){return Promise.resolve();},
    addEventListener(name, fn){mediaListeners[name]=fn;}};
  let bodyChildren=0;
  const native={getAttribute(){return nativeSource;}};
  const document={createElement(){return video;}, body:{appendChild(){bodyChildren++;}},
    querySelector(){return native;}, getElementById(){return {};}};
  const context={URL, Date, Number, performance:{now:()=>now}, document,
    location:{href:'http://face/'}, addEventListener(){},
    MutationObserver:class {constructor(fn){mutation=fn;} observe(){}},
    setTimeout(){return 1;}, clearTimeout(){}, AbortController,
    setInterval(fn, delay){intervals[delay]=fn;},
    fetch:async()=>{
      if(failFetch) throw new Error('offline');
      return {ok:true, json:async()=>payload, headers:{get:()=>date}};
    }};
  vm.createContext(context);
  const source=fs.readFileSync(require.resolve('./cruzr-boot-ready.js'),'utf8');
  vm.runInContext(source, context);
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(video.style.display,'block');
  // Vendor warning wins immediately; its native DOM is never changed.
  nativeSource='/expression/warning-red.mp4'; mutation();
  assert.equal(video.style.display,'none');
  nativeSource='/expression/breath.mp4'; mutation();
  assert.equal(video.style.display,'block');
  // An unchanged JSON heartbeat cannot renew the browser deadline.
  now=12000; await intervals[500](); intervals[100]();
  assert.equal(video.style.display,'none');
  payload.sequence='b'.repeat(32); await intervals[500]();
  assert.equal(video.style.display,'block');
  failFetch=true; await intervals[500]();
  assert.equal(video.style.display,'none');
  failFetch=false; payload.sequence='c'.repeat(32); await intervals[500]();
  mediaListeners.error();
  assert.equal(video.style.display,'none');
  payload.sequence='d'.repeat(32); await intervals[500]();
  assert.equal(video.style.display,'none');
  vm.runInContext(source, context);
  assert.equal(bodyChildren,1);
  console.log('PASS: lease expiry, stale heartbeat, warning priority, fetch/media failure, singleton');
})().catch(error=>{console.error(error);process.exitCode=1;});
