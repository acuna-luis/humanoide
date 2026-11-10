# SmolVLA pelota — puente físico y estado vigente (10-11-2026)

**Este es el documento de entrada vigente para el piloto SmolVLA de la pelota.**
Sustituye, en cuanto a estado y forma de ejecutar, a
[RELEVO_PORTABLE_SMOLVLA.md](RELEVO_PORTABLE_SMOLVLA.md) y a las secciones de
lease/guardia de [SMOLVLA_NATIVE_ARM_STEP_20261110.md](SMOLVLA_NATIVE_ARM_STEP_20261110.md),
que quedan como historia. Válido para Claude, Codex u otro agente en cualquier
máquina. Leer antes `AGENTS.md`.

## 1. Resumen en una línea

La cadena **grabaciones PICO → dataset LeRobot → entrenamiento SmolVLA en Ada →
inferencia en vivo → acciones en el brazo derecho y la mano v4 físicos** está
**validada físicamente** (10-11-2026). La tarea de la pelota (coger, subir 20 cm,
bajar, soltar) **no** se ha completado: el checkpoint actual no tiene datos
suficientes.

## 2. Qué se quería validar y qué se ha validado

Objetivo del usuario/propietario: demostrar la **metodología** (de vídeos y
grabaciones a una política que se ejecuta en el robot), no que la pelota se
coja.

| Eslabón | Estado | Evidencia |
| --- | --- | --- |
| Grabación teleop PICO (2 tomas, 09-11) | HECHO | [piloto](PELOTA_SMOLVLA_PILOTO_20261109.md) |
| Dataset LeRobot (60 muestras a 2 Hz, 2 tramos de la toma 2) | HECHO | idem |
| Entrenamiento SmolVLA en Ada (1000 pasos, 390 s) | HECHO | idem |
| Inferencia con cámara/estado reales del robot | HECHO | [shadow](../../scripts/vla/SMOLVLA_BALL_LIVE_SHADOW.md) |
| Acciones del modelo → brazo físico, bucle cerrado | **PROBADO FÍSICAMENTE** | §5, run `185347` |
| Acciones del modelo → brazo + mano v4 (intento de agarre) | **PROBADO FÍSICAMENTE** | §5, run `190321` |
| Completar la tarea de la pelota | NO | requiere más datos (§8) |

## 3. Qué falló antes y por qué ya no aplica

Durante el 10-11 Codex construyó una pila de seguridad propia en el PC (lease,
guardia en Motion, latidos, bindings por hash, coordinador/worker; ~27 k líneas
desde el 09-11). **Nunca llegó a enviar una acción del modelo**: cada capa añadía
fallos propios (reloj del lease, contención de lock, `fsync`, ACK caducado) y
cada cambio invalidaba los bindings. En el incidente 731084 un objetivo fijo de
muñeca fue aceptado por Motion y alcanzado (+0,009875 de +0,01 rad) y la
cancelación la provocó la propia guardia del PC (`guard_lost_during_trial`).
Interpretación (INFERENCIA): la ruta del robot funcionaba; fallaba la capa del PC.

Decisión del propietario (10-11-2026, en sesión con Claude): sustituir esa pila,
para este piloto, por un puente simple. El gate `model_wrist_dispatch_not_enabled`
y los scripts `pico_wrist_*`, `arm_native_lease_bridge.py`, etc. quedan
**congelados como historia**: no borrar, no es necesario repararlos para usar
el puente. La marca `/var/tmp/cruzr-pico-v4-wrist-control/PENDING_OR_UNRESOLVED.json`
en el host de Motion pertenece sólo a esos scripts; Motion no la lee y no
bloquea el puente. Se conserva como evidencia de 731084.

## 4. El puente

[`scripts/vla/smolvla_physical_bridge.py`](../../scripts/vla/smolvla_physical_bridge.py)
(~350 líneas, `--help`). Reutiliza piezas ya validadas:

```
run_ball_live_shadow.py  (Vision: imagen RGB + estado → Ada: SmolVLA → predicción 8D)
        │  stdout JSONL: prediction[0:7] = objetivos absolutos brazo derecho,
        │                prediction[7]   = escalar de mano (≈ prob. cerrar)
        ▼
plan_step(): obs = predicción − delta; delta recortado por articulación;
             envolvente alrededor de la postura inicial; límites URDF con margen;
             aborto si |obs − último objetivo| > jump-abort
HandGate:    abrir en el paso 0; cerrar si escalar ≥ umbral N pasos seguidos y
             max|delta modelo| < grasp-near; una vez cerrada sólo abre si el
             escalar < umbral N pasos seguidos
        ▼
Motion (SSH walker@192.168.11.2) → docker exec walker-motion.manipulation_robot_app-1
  ejecutor Python persistente: escribe config/diagnostics/svla_<run>/step_NNN.xml
  (MetaMove type="arm" location="right" + opcional type="effector") y ejecuta
  `rosa action send_goal /mc/manipulation/action mc_task_msgs/action/ArmTask`
  (misma vía que scripts/cruzr_blue_workbin_cycle.sh); éxito = 'SUCCEED' y status=4
        ▼
siguiente predicción sólo si llegó ≥ settle-s después de terminar el paso
```

- Orden de articulaciones (modelo = URDF = MetaMove): `R_shoulder_pitch,
  R_shoulder_roll, R_shoulder_yaw, R_elbow_roll, R_elbow_yaw, R_wrist_pitch,
  R_wrist_roll`. Comprobado: el seguimiento físico coincide (≤3,4 mrad).
- Límites URDF (`cruzr_s2_v1.urdf` en Motion) están embebidos en el script.
- Dedos v4 (orden `thumb_swing, thumb_mcp, thumb_pip, index, middle, ring,
  little`): abierta `[0.8,0,0,0,0,0,0]`; cerrada `[1.824,0.737,1.018,1.638,0.853,0.76,0.234]`
  (posición medida sujetando la pelota en la toma 2, tramo 935–1008).
- Preflight de sólo lectura: paros `/emb/estop_key_state` y
  `/emb/servo_estop_key_state` = 0, baterías ≥30 %, cargador
  `/emb/chrg_input_status` = 0 (o `--allow-charger`), sin metas activas.
- Ctrl-C / error → `ros2 service call /mc/manipulation/action/_action/cancel_goal
  action_msgs/srv/CancelGoal '{}'` (cancela todas las metas). **No ejercitado
  físicamente todavía.** La protección real es la persona en el paro físico.
- Cada paso dura ~2,1 s de extremo a extremo (1 s de movimiento + overhead ROSA).
- Registro JSONL por ejecución en
  `../Humanoide-vla-evidence/SMOLVLA_PHYSICAL_BRIDGE/run-<fecha>/bridge.jsonl`
  (evidencia privada, **fuera de Git**).
- `run_ball_live_shadow.py` admite ahora `--seconds` hasta 240 (antes 60); el
  colector de Vision admite 1800 y el contenedor de Ada corta a 300 s. Con
  240 s caben ~50–60 pasos.

### Comandos

Desde la raíz del repositorio:

```bash
# Sin movimiento: inferencia en vivo + plan de pasos
python3 -B scripts/vla/smolvla_physical_bridge.py --dry-run --hand --max-steps 6 --seconds 30 --settle-s 0

# Prueba corta de brazo (lo usado en el primer run)
python3 -B scripts/vla/smolvla_physical_bridge.py --max-steps 3 --seconds 60

# Intento de agarre (lo usado en el segundo run)
python3 -B scripts/vla/smolvla_physical_bridge.py --hand --max-steps 50 --seconds 240 \
  --envelope-rad 1.3 --max-step-rad 0.08 --jump-abort-rad 0.06

# Interactivo (Enter antes de cada paso); sólo desde una terminal real
python3 -B scripts/vla/smolvla_physical_bridge.py --step --max-steps 5
```

Topes duros del script: duración ≥1 s, paso ≤0,15 rad, envolvente ≤1,5 rad,
`--seconds` 1–240, `--fps` 0,5–2.

## 5. Ejecuciones físicas (10-11-2026, Europe/Madrid)

Todas con autorización expresa del propietario en el momento, persona en el
paro, zona despejada, sin otros clientes de control y cargador desconectado.

| Run | Qué | Resultado |
| --- | --- | --- |
| `run-20261110T184950` | dry-run, 5 pasos | sin metas |
| `run-20261110T185313` | abortado por `--seconds 90` (fuera de rango del shadow) | sin metas; dejó dir. vacío en Motion |
| `run-20261110T185347` | brazo, 3 pasos, 0,05 rad | 3/3 SUCCEED, seguimiento ≤2,4 mrad |
| `run-20261110T190127` | dry-run con mano, 6 pasos | sin metas |
| `run-20261110T190321` | brazo + mano, 50 pasos, 0,08 rad, envolvente 1,3 | 50/50 SUCCEED, sin aborto, seguimiento ≤3,4 mrad |

Comportamiento del modelo en `190321`: pasos 0–11 aproximación a la zona de
agarre de las demostraciones (hombro pitch −0,37 / codo yaw −1,79 frente a
−0,43 / −1,83 en la demo; codo roll y hombro yaw aún a 0,3–0,4 rad); después
oscila con deltas pequeños. Escalar de mano 0,53–0,97 casi siempre (pide
cerrar). Mano: abrir 0, cerrar 12, abrir 16, cerrar 24, abrir 33, cerrar 35; las
aperturas 16/33 eran un defecto de `HandGate` ya corregido. No hubo elevación,
bajada ni suelta. **Si sujetó la pelota no está confirmado** (pendiente de la
observación del operador); índice y pulgar pip quedaron 0,04–0,07 rad por
debajo de la consigna.

Fichas con hashes y reversión:
[`SMOLVLA-PHYSICAL-BRIDGE-20261110`](../SYSTEM_CUSTOMIZATIONS.md#smolvla-physical-bridge-20261110),
[`SMOLVLA-PHYSICAL-GRASP-20261110`](../SYSTEM_CUSTOMIZATIONS.md#smolvla-physical-grasp-20261110).

## 6. Estado del robot al cerrar la sesión (~19:10, 10-11-2026)

Último estado **leído**; no presuponer que sigue así.

- Brazo derecho quieto en `[-0.371,-0.154,+1.387,-1.030,-1.790,-0.099,+0.065]`
  (no está en HOME ni en la postura PICO previa).
- Mano derecha v4 **cerrada** `[1.824,0.739,0.980,1.570,0.853,0.760,0.234]`,
  posiblemente con la pelota. No se envió apertura ni HOME.
- Paros 0/0, cargador 0, baterías ~53/54 %, sin metas activas.
- `HW_TYPE=cruzr_s2_v1_sps`; mano v4 montada.
- En Motion, contenedor `walker-motion.manipulation_robot_app-1`, carpeta
  `/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config/diagnostics/`:
  `svla_20261110T185313/` (vacío), `svla_20261110T185347/` (3 XML),
  `svla_20261110T190321/` (50 XML), además de `pico_v4_wrist_d4c704e6ab369d25.xml`
  de 731084. Se pierden al recrear el contenedor; borrables con
  `docker exec … rm -r …/diagnostics/svla_*`.

Antes de cualquier movimiento: decidir con el operador si la mano sujeta la
pelota, abrirla o no, y cómo llevar el brazo a una postura segura **con un paso
revisado** (HOME sólo si la trayectoria está despejada; ver `AGENTS.md`).

## 7. Requisitos para usarlo en otra máquina

Lo versionado en Git no basta. Hace falta, por canal privado:

1. **Red al robot:** PC en `192.168.11.0/24` (Ethernet directa `eno1`
   `192.168.11.250/24` en el PC original). Motion `192.168.11.2`, Vision `.3`.
2. **Contraseña SSH del robot** en `.secrets/cruzr_ssh_password` (archivo 0600,
   una línea) o variable `CRUZR_SSH_PASSWORD`; la lee
   `scripts/lib/cruzr_ssh_askpass.py`. `~/.ssh/known_hosts` con las host keys de
   Motion y Vision (el puente usa `StrictHostKeyChecking=yes`).
3. **Ada** (`luisacuna@192.168.1.43`, puerto 2649): acceso SSH por clave, Docker
   con GPU, volumen `cruzr-smolvla-ball-public-models-20261109`, dataset
   `/home/luisacuna/cruzr-smolvla-ball-20261109/dataset-v2/lerobot-experiment`,
   checkpoint `…/pilot-1000step/run/checkpoints/001000/pretrained_model` y runner
   `…/live-shadow-20261109-2144/shadow_live_inference.sh`. Rutas fijadas en el
   diccionario `ADA` del puente.
4. Python 3 con `pyyaml` en el PC.
5. Opcional: `../Humanoide-vla-evidence/` (al lado de la raíz del repo) para
   grabaciones, registros y evidencia; el puente la crea si no existe.

Comprobación mínima en la máquina nueva: `--dry-run` (no mueve nada).

**Seguridad de Git:** la contraseña SSH del robot aparece en claro en varios
scripts ya publicados en `origin/main` (anteriores a esta sesión). Rotarla y
sanear el historial es una tarea pendiente separada; no añadir más secretos.

## 8. Siguientes pasos recomendados

1. Registrar la observación del operador sobre el run `190321` (¿tocó/sujetó la
   pelota?).
2. Probar Ctrl-C durante un paso para ejercitar `cancel_goal`.
3. **Más datos** (lo que más influye para completar la tarea): 10–20
   demostraciones PICO completas (aproximar, cerrar, subir, bajar, abrir) desde
   la misma postura inicial que se usará en ejecución; convertir con
   `prepare_ball_observations.py` → `prepare_ball_candidate_targets.py` →
   `convert_ball_candidates_to_lerobot.py`, entrenar en Ada con
   `smolvla_ball_server/run_offline.sh` (≈7 min/1000 pasos) y cambiar
   `checkpoint` en `ADA` del puente. Ver [guía de datos](CRUZR_S2_VLA_TELEOP_DATA_GUIDE.md)
   y [piloto](PELOTA_SMOLVLA_PILOTO_20261109.md).
4. Con una política en distribución se puede subir `--max-step-rad` (≤0,15) y
   bajar la duración de los pasos, siempre con persona en el paro.

## 9. Lecciones para el próximo agente

- El usuario quiere resultados físicos con comprobaciones mínimas justificadas.
  Prefiera reutilizar rutas ya validadas (MetaMove + `rosa action send_goal`)
  antes que construir capas nuevas.
- La seguridad de este puente es: pasos pequeños y lentos, envolvente, límites
  URDF, aborto por desviación, preflight de sólo lectura y persona en el paro.
  No sustituye la recomprobación física ni la autorización actual del usuario
  antes de mover.
- Documente al terminar cada fase, no en cada paso.
