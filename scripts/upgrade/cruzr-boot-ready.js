/* Initial boot aid. The vendor page, commands and error indications remain active. */
(function (root) {
  'use strict';
  function leaseRemaining(data, serverDate, now) {
    const serverTime = Date.parse(serverDate);
    if (!data || data.schema !== 'cruzr-boot-ready-v1' || data.ready !== true ||
        data.expression !== 'inspection' || !/^[a-f0-9]{32}$/.test(data.sequence) ||
        !Number.isFinite(data.expires_at_ms) || !Number.isFinite(serverTime)) return 0;
    // Use the HTTP server's clock: the face browser need not share Vision's clock.
    const remaining = data.expires_at_ms - serverTime - 1000;
    return remaining > 0 && remaining <= 12000 ? now + remaining : 0;
  }
  function neutralSource(src, base) {
    try { return new URL(src, base).pathname === '/expression/breath.mp4'; }
    catch (_) { return false; }
  }
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = {leaseRemaining, neutralSource};
    return;
  }
  if (root.__cruzrBootVisual) return;
  root.__cruzrBootVisual = true;
  const video = document.createElement('video');
  video.id = 'cruzr-boot-inspection';
  video.src = 'http://127.0.0.1:5000/expression/inspection.mp4';
  video.muted = true;
  video.loop = true;
  video.playsInline = true;
  video.setAttribute('aria-label', 'Initial boot: ready to release the emergency stop');
  video.style.cssText = 'display:none;position:fixed;inset:0;width:100%;height:100%;' +
    'object-fit:contain;background:black;z-index:10000;pointer-events:none';
  document.body.appendChild(video);
  let deadline = 0, sequence = '', failed = false, active = false, inFlight = false;
  const hide = () => { video.style.display = 'none'; video.pause(); active = false; };
  const render = () => {
    const native = document.querySelector('#root video.dynamic-media');
    // Every vendor expression other than breath has immediate priority, including
    // warning-red/yellow/orange, shutdown and blank. Never force a white face.
    const neutral = native && !native.error && neutralSource(native.getAttribute('src'), location.href);
    if (failed || performance.now() >= deadline || !neutral) { hide(); return; }
    if (!active) {
      active = true;
      video.style.display = 'block';
      video.play().catch(() => { failed = true; hide(); });
    }
  };
  video.addEventListener('error', () => { failed = true; hide(); });
  new MutationObserver(render).observe(document.getElementById('root'),
    {subtree: true, childList: true, attributes: true, attributeFilter: ['src']});
  async function poll() {
    if (inFlight) return;
    inFlight = true;
    const abort = new AbortController();
    const timeout = setTimeout(() => abort.abort(), 1000);
    try {
      const response = await fetch('/cruzr-boot-ready.json',
        {cache: 'no-store', signal: abort.signal});
      if (!response.ok) throw new Error('status unavailable');
      const data = await response.json();
      const candidate = leaseRemaining(data, response.headers.get('Date'), performance.now());
      if (!candidate) { deadline = 0; sequence = ''; }
      else if (data.sequence !== sequence) { deadline = candidate; sequence = data.sequence; }
      // Re-reading an old heartbeat cannot prolong its lifetime.
    } catch (_) { deadline = 0; }
    finally { clearTimeout(timeout); inFlight = false; render(); }
  }
  root.addEventListener('pagehide', hide);
  setInterval(render, 100);
  setInterval(poll, 500);
  poll();
})(globalThis);
