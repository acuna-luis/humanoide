'use strict';
const q = s => document.querySelector(s);
let csrf = '', busy = true, enabled = false, pending = null, sending = false;
function controls() {
  q('#home').disabled = sending || busy || !enabled || !q('#physical').checked;
  q('#cycle').disabled = q('#home').disabled || !q('#trial').checked;
  q('#height').disabled = sending || busy;
}
async function request(path, data) {
  const response = await fetch(path, {credentials:'same-origin', ...(data ? {
    method:'POST', headers:{'Content-Type':'application/json','X-CSRF-Token':csrf}, body:JSON.stringify(data)
  } : {})});
  const value = await response.json();
  if (!response.ok) throw new Error(value.error || response.status);
  return value;
}
async function refresh() {
  try {
    const value = await request('/api/status');
    csrf = value.csrf; enabled = value.enabled;
    busy = value.blocked || ['accepted','checking','running'].includes(value.job?.status);
    q('#login').hidden = true; q('#panel').hidden = false;
    const job = value.job;
    q('#status').textContent = (enabled ? 'Servicio habilitado' : 'Servicio instalado, aún deshabilitado') +
      (value.blocked ? '\nBloqueado: requiere revisión física y reconciliación administrativa.' : '') +
      (job ? `\nTrabajo ${job.id}\n${job.action}: ${job.status}\n${job.reason || ''}` : '\nSin trabajo iniciado.');
  } catch (error) { busy = true; enabled = false; q('#status').textContent = error.message; }
  controls();
}
q('#login').addEventListener('submit', async event => {
  event.preventDefault();
  try { await request('/api/login', {token:q('#token').value}); q('#token').value = ''; await refresh(); }
  catch (error) { q('#status').textContent = error.message; }
});
for (const action of ['home','cycle']) q('#'+action).addEventListener('click', async () => {
  if (sending || busy || !enabled || !q('#physical').checked) return;
  const intent = {action, height:q('#height').value, physical_confirmed:true, trial_authorized:q('#trial').checked};
  // If HTTP acknowledgement was lost, retry only this identical idempotent request.
  if (!pending || JSON.stringify(pending.intent) !== JSON.stringify(intent)) {
    if (pending) { q('#status').textContent = 'Resultado HTTP incierto: recargue el estado antes de otra petición.'; return; }
    pending = {intent, key:Array.from(crypto.getRandomValues(new Uint8Array(16)), x=>x.toString(16).padStart(2,'0')).join('')};
  }
  sending = true; controls();
  try {
    await request('/api/jobs', {...intent, key:pending.key});
    pending = null; q('#physical').checked = false; q('#trial').checked = false;
    await refresh();
  } catch (error) { q('#status').textContent = error.message; busy = true; }
  finally { sending = false; controls(); }
});
q('#physical').addEventListener('change', controls);
q('#trial').addEventListener('change', controls);
refresh(); setInterval(refresh, 2000);
