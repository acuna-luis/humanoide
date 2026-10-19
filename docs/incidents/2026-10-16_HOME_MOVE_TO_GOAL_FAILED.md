# HOME abortado después de PICO — 16-10-2026

Estado: **OBSERVADO en registros del robot**. Diagnóstico exclusivamente de
lectura. Origen de los fallos y recuperación: **PENDIENTES**.

El operador ejecutó `scripts/force_home.sh`: goal
`59860eee-767d-4e0a-8605-6d0540a9d1a5`, resultado `MoveToGoalFailed`,
estado de aplicación `7104050`, estado de acción `6` (abortada).
La aceptación del goal no confirma HOME. El agente no repitió la acción.

## Secuencia comprobada

Horas siguientes nativas de Motion, UTC+08; equivalen a seis horas menos en
Europe/Madrid en esta fecha. La cancelación de PICO termina alrededor de
18:53:08.727. El goal HOME llega a las 18:53:23.932.

Antes del goal, al menos desde 18:53:18 en la ventana conservada, HW ya registra:

- `send a jump command, threshold is 0.087rad` en varios ejes de los brazos
  y la cabeza: diferencias entre consigna y posición superiores a unos 4,98°.
- Ambos motores de cabeza con `err code: 4099` (`0x1003`), estado `12863`.
  No se ha determinado aquí el significado específico del código del fabricante.

HOME utiliza el XML v8 previamente instalado, SHA256
`d9e9462792b41300d352604b53ea2a4890a9382e942321990708f6ded2e26ccb`:
`/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config/cruzr/home.xml`
en `walker-motion.manipulation_robot_app-1`. Coincide con la fuente
`scripts/teleoperation/tasks/cruzr_home_v8_early_roll_CANDIDATE.xml`.
No se ha sustituido ni recargado durante esta revisión.

La primera fase ajusta cada brazo durante 1 s, en paralelo con cabeza,
elevador y cintura durante 3,75 s. No es un HOME completo de un segundo.

| Evento nativo | Observación |
|---|---|
| 18:53:24.840–25.040 | Se inician los primeros ajustes de ambos brazos |
| 18:53:25.853 | Izquierdo `moved failed`; mayor error articular 0,214048 rad ≈ 12,26° |
| 18:53:26.053 | Derecho `moved failed`; mayor error articular 0,499933 rad ≈ 28,64° |
| 18:53:26.136–26.137 | Elevador, cintura y cabeza abortan al fallar el paralelo |

No se alcanzan las fases posteriores de bajada y cierre. El registro HW
durante y después del intento conserva las advertencias de salto, y después
también `Not all EtherCAT slave devices in operational state`.
El fallo no demuestra por sí solo falta de tiempo: ya había discontinuidad de
consignas y fallos de cabeza antes de iniciar HOME. Aumentar tolerancias de
llegada o tiempos no constituye una corrección demostrada para este estado.

## Observación posterior y límites

Captura pasiva de 3 s: cinco mensajes de actuadores completos y ambos paros
observados en `0`. En esos cinco mensajes, velocidad de los veinte ejes `0`,
errores reportados de brazos `0`, y código `4099` en ambos ejes de cabeza.
Persisten diferencias consigna/posición, incluidas las de ambos codos y varios
ejes derechos. `cmd_pos` es la última consigna solicitada sin límites aplicados;
no certifica el setpoint aplicado al servo ni un movimiento futuro.

**Captura no cualificada:** el colector marca error al interpretar el aviso
informativo inicial de ROSA sobre shared memory como JSON. Se conservan las
cinco muestras válidas, pero `usable_capture=false` y el análisis no certifica
salud, reposo continuo ni una trayectoria segura. El aviso shared memory no
queda establecido como causa del HOME fallido.

El operador responde «no» a la consulta sobre contacto, resistencia, objeto
sujeto o movimiento inesperado durante el intento. No aporta una descripción
de la postura final. No se atribuye el fallo a contacto o daño. Tampoco se
ha reconstruido cuándo se originaron la discontinuidad ni los fallos de cabeza,
o su relación con los fallos IK derechos de la sesión anterior.

## Cambios y punto de reanudación

Sólo documentación local. Sin START/STOP, HOME, rearme, modo, reinicio,
calibración, instalación remota ni cambios de protecciones por el agente.
No volver a enviar HOME o rearmar como prueba desde este estado. Preparar
recuperación según postura medida, fallos de cabeza, continuidad de consignas
y condiciones físicas actuales. No elevar el límite de salto para aceptar las
consignas pendientes. La recuperación requiere una intervención autorizada;
no está ejecutada ni validada en este diagnóstico.

Evidencia privada externa:
`/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20261016T105501Z_HOME_MOVE_TO_GOAL_FAILED_READONLY/`.
Incluye inventario, hora Motion, fragmento robot_app y evento HOME,
`installed-home.xml`, `hw-home-window.log` (18:53:18–28), `hw-tail.log`,
captura/metadata/análisis en `after-state/`, `findings.json`, respaldo documental
`before/` y copia final con checksums. Logs privados sin incorporar a Git.

Referencias: [HOME v8](../teleoperation/CRUZR_HOME_V8_CANDIDATA.md),
[recuperación post-PICO](../guides/CRUZR_S2_RECUPERACION_TRAS_CONTACTO_TELEOP.md)
y [dirección derecha comunicada antes de HOME](2026-10-16_PICO_BRAZO_DERECHO_DIRECCION.md).
