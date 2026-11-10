# Ensayo offline reproducible del guard de brazo de pelota

Este ejemplo usa **una propuesta y un estado reales pero antiguos** del
frame 2 de la captura del 09-11-2026. Los tiempos y todos los límites son
**sintéticos para la prueba**: no representan relojes actuales, tolerancias,
límites del robot, ni una aprobación de movimiento. No genera órdenes.

Desde la raíz del repositorio, con las evidencias privadas existentes:

```bash
python3 -B - <<'PY'
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, 'scripts/vla')
import ball_arm_preview_guard as guard

root = Path('../Humanoide-vla-evidence/20261109_BALL_SHADOW_ASSESSMENT')
sources = {
    'current_capture/aligned.jsonl': '42d11aa56b69b28cd923b899131ce3fbd6aa1bdc8079cf576934fa45e05aa8f3',
    'current_capture/samples.jsonl': 'fa8297d20c4f2ea33e0339b7a90ce6879e1b2ddb9a98adfc6e98f9ccd715b654',
    'current_observations/manifest.json': '1cc4badef94d7ca6dcfa558209fac74bd0461bb158afcde6445e0d1b989a1512',
    'server/results/result-current/predictions.jsonl': '5a4312d234ba4345f3ffac41f128266a9ed89adc58b34270bb32f8d7785624d5',
}
for name, expected in sources.items():
    h = hashlib.sha256()
    with (root / name).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    if h.hexdigest() != expected:
        raise ValueError('Fuente histórica cambiada: ' + name)

manifest = json.loads((root / 'current_observations/manifest.json').read_text())
pred = json.loads((root / 'server/results/result-current/predictions.jsonl').read_text().splitlines()[0])
obs = next(row for row in manifest['records']
           if row['source_frame'] == pred['source_frame'] and row['image_sha256'] == pred['image_sha256'])
aligned = next(json.loads(line) for line in (root / 'current_capture/aligned.jsonl').open()
               if json.loads(line)['png_file'] == f"rgb/{pred['source_frame']:06d}.png")
line_number = aligned['source_lines']['joints']
with (root / 'current_capture/samples.jsonl').open() as stream:
    raw = next(json.loads(line) for i, line in enumerate(stream, 1) if i == line_number)
if raw['kind'] != 'joints':
    raise ValueError('La referencia no apunta a un estado articular')
message = raw['message']
names = manifest['state_names'][:20]
positions = dict(zip(message['name'], message['position'], strict=True))
velocities = dict(zip(message['name'], message['velocity'], strict=True))
if any(positions[n] != obs['state27'][i] for i, n in enumerate(names)):
    raise ValueError('El estado histórico no coincide con el frame')
if any(abs(pred['prediction'][i] - positions[n] - pred['proposed_minus_observed_rad'][i]) > 1e-12
       for i, n in enumerate(guard.MODEL_ORDER)):
    raise ValueError('Propuesta y diferencias no coinciden con ese estado')

# Sólo demuestra que un límite hipotético de 0,2 rad detecta esta propuesta.
limits = {n: dict(min_position_rad=-10, max_position_rad=10, max_delta_rad=0.2,
                  max_velocity_rad_s=1, max_acceleration_rad_s2=2,
                  stationary_velocity_rad_s=1) for n in guard.MODEL_ORDER}
state = dict(names=names, positions=[positions[n] for n in names],
             velocities=[velocities[n] for n in names], received_monotonic_ns=1_000_000_000)
proposal = dict(names=list(guard.MODEL_ORDER), positions=pred['prediction'][:7],
                received_monotonic_ns=1_000_000_000)
policy = dict(max_state_age_ns=500_000_000, max_proposal_age_ns=500_000_000,
              preview_duration_seconds=4, joint_limits=limits)
result = guard.review(state, proposal, policy, now_ns=1_000_000_000)
print(json.dumps({'historical_frame': pred['source_frame'],
                  'synthetic_policy_and_clock': True,
                  'diagnostic_passed': result['diagnostic_passed'],
                  'reasons': result['reasons'],
                  'physical_control_qualified': result['physical_control_qualified']}, indent=2))
PY
```

Se espera rechazo por cuatro ejes, incluido `R_elbow_yaw_joint`. El umbral
hipotético no es un límite de seguridad; obtener y validar límites reales,
controlador, parada y geometría por separado.
