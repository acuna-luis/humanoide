/* Additive review controls. No ROS, WebSocket, fetch or physical command. */
(function () {
  'use strict';
  const preview = document.currentScript?.dataset.mode === 'preview';
  function mount() {
    if (document.getElementById('sc1-host')) return;
    const host = document.createElement('section');
    host.id = 'sc1-host'; host.setAttribute('data-cruzr-notr', '');
    host.innerHTML = `
      <aside class="sc1-banner" role="status">VISTA PREVIA LOCAL · Sin conexión al robot · Los botones sólo simulan</aside>
      <button class="sc1-launch" type="button" aria-haspopup="dialog">Operación de cajas</button>
      <dialog class="sc1-dialog" aria-labelledby="sc1-title">
        <header><div><p class="sc1-eyebrow">CRUZR S2 · DEMO DE CAJAS</p><h2 id="sc1-title">Operación de cajas</h2></div>
          <button class="sc1-close" type="button" aria-label="Cerrar panel">×</button></header>
        <p class="sc1-mode"></p>
        <label class="sc1-height">Mesa de depósito <select aria-label="Altura de mesa"><option value="74">74 cm</option><option value="90">90 cm</option></select></label>
        <div class="sc1-actions">
          <button type="button" data-action="home"><strong>Ir a HOME</strong><span>Recuperar postura; no desplaza la base</span></button>
          <button type="button" data-action="cycle"><strong>Ejecutar ciclo</strong><span>Recoger → depositar → HOME</span></button>
        </div>
        <section class="sc1-confirm" hidden>
          <h3></h3><p></p>
          <label><input type="checkbox"> <span></span></label>
          <div><button type="button" class="sc1-confirm-go" disabled></button><button type="button" class="sc1-back">Volver</button></div>
        </section>
        <p class="sc1-status" role="status" aria-live="polite">Sin operación iniciada.</p>
        <progress aria-label="Progreso simulado" value="0" max="100" hidden></progress>
        <button class="sc1-cancel" type="button" hidden>Cancelar simulación</button>
        <p class="sc1-note">El control real requiere el servicio de ejecución y comprobaciones del robot.</p>
      </dialog>`;
    document.body.appendChild(host);
    const q = s => host.querySelector(s);
    const dialog = q('dialog'), launcher = q('.sc1-launch'), status = q('.sc1-status');
    const actions = Array.from(host.querySelectorAll('[data-action]'));
    const confirm = q('.sc1-confirm'), checkbox = q('input'), go = q('.sc1-confirm-go');
    let selected = null, running = false, timer = null;
    q('.sc1-banner').hidden = !preview;
    q('.sc1-mode').textContent = preview ? 'Simulación: ningún clic envía órdenes al robot.' : 'Integración pendiente: controles reales deshabilitados.';
    function controls() { actions.forEach(b => b.disabled = !preview || running); q('select').disabled = running || !preview; }
    function resetConfirmation() { confirm.hidden = true; checkbox.checked = false; go.disabled = true; selected = null; }
    function cancel() {
      if (!running) return;
      clearTimeout(timer); running = false; q('progress').hidden = true; q('.sc1-cancel').hidden = true;
      status.textContent = 'Simulación cancelada. No se ha enviado ninguna orden al robot.'; controls();
    }
    q('.sc1-cancel').addEventListener('click', cancel);
    launcher.addEventListener('click', () => dialog.showModal());
    q('.sc1-close').addEventListener('click', () => { if (!running) { resetConfirmation(); dialog.close(); } });
    dialog.addEventListener('cancel', event => { if (running) event.preventDefault(); else resetConfirmation(); });
    actions.forEach(button => button.addEventListener('click', () => {
      if (!preview || running) return;
      selected = button.dataset.action; checkbox.checked = false; go.disabled = true; confirm.hidden = false;
      q('.sc1-confirm h3').textContent = selected === 'home' ? 'Vista previa de HOME' : `Vista previa del ciclo · mesa ${q('select').value} cm`;
      q('.sc1-confirm p').textContent = selected === 'home' ? 'En el robot: sólo con útiles vacíos y recorrido de HOME libre. No es un retorno del chasis a get1.' : 'En el robot: comprobar montaje, postura, caja, mesa, recorrido y disponibilidad del control antes del ciclo.';
      q('.sc1-confirm label span').textContent = 'Entiendo que esta prueba es una simulación sin movimiento.';
      go.textContent = selected === 'home' ? 'Simular HOME' : 'Simular ciclo'; checkbox.focus();
    }));
    checkbox.addEventListener('change', () => { go.disabled = !checkbox.checked || running; });
    q('.sc1-back').addEventListener('click', resetConfirmation);
    go.addEventListener('click', () => {
      if (!preview || running || !selected || !checkbox.checked) return;
      const action = selected;
      const steps = action === 'home' ? ['Simulación · comprobaciones previas', 'Simulación · recuperación HOME', 'Vista previa terminada. HOME real NO verificado.'] :
        ['Simulación · comprobaciones previas', 'Simulación · ir a get1', 'Simulación · recoger caja', 'Simulación · ir a put1', `Simulación · depositar en mesa de ${q('select').value} cm`, 'Simulación · HOME', 'Vista previa terminada. Depósito y HOME reales NO verificados.'];
      running = true; resetConfirmation(); controls(); q('progress').hidden = false; q('.sc1-cancel').hidden = false;
      let step = 0;
      function tick() {
        status.textContent = steps[step]; q('progress').value = (step + 1) / steps.length * 100;
        if (++step < steps.length) timer = setTimeout(tick, 500);
        else { running = false; q('.sc1-cancel').hidden = true; controls(); }
      }
      tick();
    });
    controls();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount, {once:true}); else mount();
})();
