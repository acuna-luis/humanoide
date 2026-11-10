# SmolVLA pelota aro → aro: segunda ronda (10-11-2026)

Continuación de [SMOLVLA_PUENTE_FISICO_20261110.md](SMOLVLA_PUENTE_FISICO_20261110.md)
(documento de entrada vigente). Objetivo del usuario: validar **de una vez** el
método completo (grabar con PICO → dataset → entrenar → probar en el robot con
el puente) con la tarea nueva, aceptando que con pocos datos no se complete.

## 1. Tarea y escena

Dos aros sobre fondo blanco en la mesa; en el primero, una pelota de tenis
comercial; el segundo, vacío. Desde la postura PICO inicial del brazo derecho
el operador aproxima brazo y mano, cierra con el gatillo PICO, lleva la pelota
al segundo aro y la suelta al soltar el gatillo; después vuelve a la postura
PICO. Si falla (aproximación, recogida o dejada) hasta 5 veces, vuelve a la
postura PICO y reintenta. Una persona recoloca la pelota entre intentos (con el
brazo en postura PICO; queda fuera de los segmentos).

Instrucción del modelo: *"Pick up the tennis ball from the first ring with the
right hand, drop it into the empty second ring and return to the start pose."*

## 2. Datos (VERIFICADO)

Grabaciones con `capture_passive_episode.py` (en `../Humanoide-vla-evidence/`):

| Captura | Task | Intentos | Éxitos | Uso |
| --- | --- | --- | --- | --- |
| `20261110T192558Z_EPISODE_7974607c` | `pelota_demo_03x` (300 s) | 9 | 3 | entrenamiento |
| `20261110T191645Z_EPISODE_f0336c79` | `pelota_demo_01x` (120 s) | 3 | 1 | validación apartada |
| `…191407Z…82e9c027`, `…184654Z…11f52d65` | `01c`, `01bien` | — | 0 cierres | descartadas |
| `…191311Z…093d10b2`, `…183121Z…f473ab13` | `01bien`, `01` | — | sin `quality.json` | descartadas |

- Segmentación automática ([`make_ball_place_segments.py`](../../scripts/vla/make_ball_place_segments.py)):
  intento = brazo sale de la postura PICO (>0,05 rad) hasta que vuelve; empieza
  en el primer fotograma con cabeza bajada (pitch ≤ −0,6); éxito = cierre de mano
  mantenido ≥4 s. Los 4 éxitos fueron **confirmados por el operador**. Specs:
  `config/vla/ball_place_segments_20261110.json` (12 segmentos) y
  `…_train_20261110.json` (sólo 03x).
- La cabeza **sigue al visor**: erguida (0/0) en postura PICO, durante los
  intentos pitch −0,65 (cerca del límite −0,785) y yaw ≈ −0,49 (−0,38…−0,71).
  Al ejecutar se fija en (yaw −0,49, pitch −0,65).
- Desviación máxima desde la postura PICO por articulación: hasta 1,18 rad
  (codo roll); envolvente del puente 1,3 rad.
- Conversión `cmd_pos` → articulación con el snapshot histórico de
  transmisiones: |objetivo − medido| mediana 0,9 mrad, p95 6,3 mrad (coherente).
- Dataset LeRobot: 3 episodios, 162 muestras a 2 Hz (~81 s).

## 3. Receta reproducible

```bash
E=../Humanoide-vla-evidence; P=$E/20261110_VLA_BALL_PLACE_PREP
TASK="Pick up the tennis ball from the first ring with the right hand, drop it into the empty second ring and return to the start pose."
python3 -B scripts/vla/make_ball_place_segments.py \
  --capture $E/20261110T192558Z_EPISODE_7974607c:inspection_train \
  --output config/vla/ball_place_segments_train_20261110.json
python3 -B scripts/vla/prepare_ball_observations.py --segments config/vla/ball_place_segments_train_20261110.json \
  --output $P/observations_train --task "$TASK"
python3 -B scripts/vla/prepare_ball_candidate_targets.py --observations $P/observations_train \
  --hardware-snapshot $E/20260914_ARM_MAPPING_LIMITS/hardware-configs.json --output $P/candidate_targets_train
bash scripts/vla/smolvla_ball_server/stage_data.sh --copy --candidates $P/candidate_targets_train \
  --host luisacuna@192.168.1.43 --port 2649 \
  --remote-dir /home/luisacuna/cruzr-smolvla-ball-20261109/input-staged-place-20261110
# En Ada (/home/luisacuna/cruzr-smolvla-ball-20261109):
bash input-staged-place-20261110/tools/convert_on_server.sh --run \
  --staging $PWD/input-staged-place-20261110 --output $PWD/dataset-place-20261110
nohup bash training-runner/run_offline.sh dataset-place-20261110/lerobot-experiment \
  cruzr-smolvla-ball-public-models-20261109 place-3000step 3000 8 8 > train-place-3000step.log 2>&1 &
```

`stage_data` sólo admite segmentos `candidate_success` de `inspection_train`:
la validación se evalúa aparte con
[`eval_heldout_with_shadow.py`](../../scripts/vla/eval_heldout_with_shadow.py)
sobre `$P/candidate_targets/pelota_demo_01x_a00_73_194`.

## 4. Bloqueos encontrados y corregidos antes del robot

Para no repetir el patrón del 10-11 (fallos descubiertos con el robot delante),
se revisó toda la cadena con un modelo distinto del piloto:

1. **Instrucción fija** en `prepare_ball_observations.py` → `--task`.
2. **Hashes del piloto fijados** en el servidor del shadow
   (`shadow_live_inference.py` importaba `TRAIN_MANIFEST_SHA`/`CHECKPOINT_FILES`)
   → `--pins-b64` / 7.º argumento de `shadow_live_inference.sh` /
   `--pins-file` en `run_ball_live_shadow.py` y en el puente. Sigue siendo una
   verificación fijada: los hashes los aporta el PC.
3. **Hash del modelo fijado en el PC** (`MODEL_SHA256` en `run_ball_live_shadow.py`)
   → se toma de `--pins-file`.
4. **Instrucción fija en el adaptador en vivo** (`live_ball_observation_adapter.py`
   importaba `TASK` del piloto; el servidor rechaza tareas distintas) → el
   servidor anuncia la tarea del dataset en `ready` y se pasa al adaptador
   (`CRUZR_SVLA_TASK`).
5. `stage_data` rechaza segmentos de validación → conjunto sólo de entrenamiento.

Sin `--pins-file` todo se comporta como con el piloto. Scripts del servidor
actualizados en Ada en `live-shadow-20261110-place/` (5 archivos con SHA256
idénticos al repositorio); la carpeta del piloto no se tocó.

## 5. Puente: novedades

- `--train/--checkpoint/--runner/--pins-file`: elegir modelo.
- `--head-pose YAW,PITCH` y `--start-pose pico`: antes de la política, un XML
  `Parallel` con `MetaMove type="head" location="single" joint_angles="yaw; pitch"`
  (formato del probe de cabeza del 10-11), brazo a la postura PICO y mano
  abierta. Rechaza si el brazo está a >0,6 rad de la postura PICO.
- `--chunk-steps K --action-duration-s 0.5`: ejecuta las K primeras acciones del
  bloque de 8 que predice el modelo (el servidor ahora devuelve `chunk`), como
  `Sequence` de `MetaMove` a la cadencia del dataset (2 Hz), recortando cada una
  respecto a la anterior (≤0,10 rad por acción).
- Tests: `scripts/vla/test_smolvla_physical_bridge.py` (6).

## 6. Entrenamiento y evaluación offline (VERIFICADO)

- Ada, `place-3000step`: desde `smolvla_base`, 3.000 pasos, batch 8, chunk 8,
  1951 s (32,5 min); pérdida final 0,05–0,09. Checkpoint
  `place-3000step/run/checkpoints/003000/pretrained_model`, `model.safetensors`
  SHA256 `7ae6fcbc025e2909f9e72c7c1d0c171b2f33eaa38a054c5dffe30e4228eb2f1b`;
  hashes esperados en [`config/vla/smolvla_place_3000step_pins.json`](../../config/vla/smolvla_place_3000step_pins.json)
  (dataset manifest `32ffa717…7c3d`).
- **Hallazgo de pipeline (heredado del piloto):** la acción del dataset es la
  consigna de motor simultánea a la observación (≈ estado medido, 0,9 mrad), así
  que `chunk[0]` significa "quedarse"; el movimiento está en `chunk[1..7]`
  (+0,5 s cada uno). Ejecutar sólo `chunk[0]` (lo que hacía el puente con
  `--chunk-steps 1`) no reproduce la política; el movimiento de los ensayos del
  10-11 por la tarde venía de predicciones fuera de distribución. El puente
  ejecuta ahora `chunk[offset:offset+K]` con `--chunk-offset 1` por defecto.
- Evaluación con el servidor del shadow (cadena completa con pins y tarea),
  comparando `chunk[h]` con el objetivo grabado h·0,5 s después frente a "no
  moverse":

| Datos | 0,5 s | 1,0 s | 1,5 s | 2,0 s | Mano |
| --- | --- | --- | --- | --- | --- |
| Entrenamiento (03x a00) modelo / quieto (rad) | 0,015 / 0,023 | 0,018 / 0,040 | 0,019 / 0,051 | 0,017 / 0,059 | 98,8 % |
| Apartado (01x a00) modelo / quieto (rad) | 0,140 / 0,019 | 0,169 / 0,032 | 0,185 / 0,041 | 0,185 / 0,049 | 64,8 % (trivial 65,6 %) |

  Interpretación: la cadena funciona (aprende y reproduce las demostraciones de
  entrenamiento); con 3 demostraciones **no generaliza** a otra grabación. En el
  robot cabe esperar, como mucho, una trayectoria memorizada si arranca desde la
  postura y escena de las demos. Para generalizar hacen falta muchas más
  demostraciones (§8 del documento de entrada).
- Velocidad de las demos: máximo |Δ| por 0,5 s (peor articulación) mediana
  0,049, p90 0,207, p99 0,578 rad. Con 0,10 rad por acción el robot va a la
  velocidad del operador la mayor parte del tiempo y a la mitad en tramos rápidos.
- Evidencia: `../Humanoide-vla-evidence/20261110_VLA_BALL_PLACE_PREP/`
  (`heldout_eval_place_3000step_horizons.json`, `train_eval_place_3000step_horizons.json`).

## 7. Prueba física

PENDIENTE. Al intentar el dry-run (20:3x) el enlace Ethernet `eno1` estaba DOWN
y Motion/Vision no respondían (cable o robot apagado); no se envió nada.
Comando previsto (tras preflight y confirmación física del operador):

```bash
R=/home/luisacuna/cruzr-smolvla-ball-20261109
python3 -B scripts/vla/smolvla_physical_bridge.py --hand --max-steps 60 --seconds 240 \
  --train $R/dataset-place-20261110/lerobot-experiment \
  --checkpoint $R/place-3000step/run/checkpoints/003000/pretrained_model \
  --runner $R/live-shadow-20261110-place/shadow_live_inference.sh \
  --pins-file config/vla/smolvla_place_3000step_pins.json \
  --chunk-steps 4 --chunk-offset 1 --action-duration-s 0.5 --max-step-rad 0.10 \
  --envelope-rad 1.3 --jump-abort-rad 0.08 --fps 2 --settle-s 1.0 \
  --hand-confirm 1 --grasp-near-rad 0.2 --head-pose=-0.49,-0.65 --start-pose pico
```
