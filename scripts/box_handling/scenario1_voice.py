"""Best-effort PC-side speech; never used for control or recovery decisions."""
import json
from pathlib import Path
import queue
import shutil
import subprocess
import threading
import time

TEXT = {
 'position_retry': ('Error al posicionarse. Voy a medir y ajustar de nuevo.', 'Positioning error. Measuring and adjusting again.'),
 'position_adjust': ('La caja está fuera de rango. Ajustando la posición.', 'The box is out of range. Adjusting position.'),
 'position_ready': ('Posición corregida. Continuando la recogida.', 'Position corrected. Continuing pickup.'),
 'home_start': ('Recogida no iniciada. Condiciones comprobadas. Recuperando HOME.', 'Pickup has not started. Conditions checked. Recovering home posture.'),
 'home_recovered': ('HOME comprobado. Ciclo detenido. Revise el montaje antes de reintentar.', 'Home posture verified. Cycle stopped. Check the setup before retrying.'),
 'home_blocked': ('Recuperación automática bloqueada. Se necesita revisión del operador.', 'Automatic recovery blocked. Operator inspection required.'),
}


def message(event):
    code = event.get('code') if event.get('event') == 'recovery' else None
    if code in TEXT:
        return code, TEXT[code]
    if event.get('event') == 'get1_correction' and event.get('phase') == 'start':
        return 'get1-adjust-'+str(event.get('attempt')), TEXT['position_adjust']
    if event.get('event') == 'box_alignment' and event.get('phase') == 'in_flight':
        return 'adjust-'+str(event.get('attempt')), TEXT['position_adjust']
    if event.get('event') == 'error':
        reason = str(event.get('reason', ''))
        if any(k in reason for k in ('Correction', 'ALIGNMENT', 'ARRIVAL', 'CORRECTION')):
            return 'position-error', ('Error al posicionarse. '+('' if not reason else reason[:150]),
                                      'Positioning failed. '+reason[:150])
        return 'cycle-error', ('Ciclo interrumpido. Se necesita revisión del operador.',
                               'Cycle interrupted. Operator inspection required.')
    return None


class Voice:
    def __init__(self, mode, evidence, robot_script):
        self.mode, self.evidence = mode, Path(evidence)
        self.script = str(robot_script)
        self.engine = (shutil.which('espeak-ng') or shutil.which('espeak')) if mode == 'pc' else None
        self.jobs = queue.Queue(maxsize=8)
        self.seen = set()
        self.closed = False
        self.thread = threading.Thread(target=self.work, daemon=True)
        self.thread.start()

    def record(self, **values):
        try:
            with (self.evidence/'voice.jsonl').open('a') as f:
                f.write(json.dumps(dict(time_ns=time.time_ns(), mode=self.mode, **values))+'\n')
        except OSError:
            pass  # Speech diagnostics cannot affect the control reader.

    def feed(self, event):
        item = message(event)
        if event.get('event') == 'error' and 'home_recovered' in self.seen:
            return
        if self.closed or not item or item[0] in self.seen:
            return
        self.seen.add(item[0])
        try:
            self.jobs.put_nowait(item)
        except queue.Full:
            self.record(status='dropped_queue_full', code=item[0])

    def work(self):
        while True:
            item = self.jobs.get()
            if item is None:
                return
            code, texts = item
            if self.mode == 'pc' and not self.engine:
                self.record(status='unavailable', code=code, reason='Install espeak-ng or select robot-en')
                continue
            command = ([self.engine, '-v', 'es', '-s', '165', texts[0]] if self.mode == 'pc' else
                       ['bash', self.script, texts[1]])
            try:
                result = subprocess.run(command, capture_output=True, text=True, timeout=12,
                                        start_new_session=True)
                self.record(code=code, status='completed' if result.returncode == 0 else 'failed',
                            returncode=result.returncode)
            except (OSError, subprocess.TimeoutExpired) as exc:
                self.record(code=code, status='failed', reason=type(exc).__name__)

    def close(self):
        self.closed = True
        try:
            self.jobs.put_nowait(None)
        except queue.Full:
            pass
        # No join: stopping/cancelling robot control must never wait for speech.
