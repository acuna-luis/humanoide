# Ensayos supervisados de retorno HOME con abrazaderas

## 11-09-2026 — caso H03, postura asimétrica: leído y rechazado antes de mover

**VERIFICADO: postura real capturada; CERO órdenes de movimiento.** El usuario
preparó mediante teleoperación una postura de trabajo asimétrica, aportó dos
fotos y autorizó HOME bajo supervisión con E-stop disponible. La autorización
no convirtió esa postura en una referencia PICO válida.

Lecturas nuevas: veinte actuadores habilitados, velocidad0, delta máximo de
consigna0,002362rad; cero publicadores de órdenes, módulo libre y última acción
cancelada (estado5). La evaluación PICO rechaza el estado: error máximo frente
a la referencia más próxima0,842922rad, tolerancia0,02rad. Entre las diferencias:
codos izquierdo−0,725rad/derecho−1,25949rad; muñeca pitch izquierda0,13911rad /
derecha−0,51590rad; cabeza pitch−0,65156rad. Los veinte valores están archivados,
no se reconstruyeron de la foto. Ningún control fue desactivado o ampliado.

Se evaluó **offline**, desde esos ángulos, el candidato del HOME interno
abrir/bajar abierto/cuerpo/cerrar de20s. El estudio de envolventes de abrazaderas
contra robot, con **501 muestras por etapa** y cota nominal entre muestras,
no encontró separaciones nominales negativas en sus pares no locales. El peor
par fue abrazadera derecha–`R_elbow_yaw_link`: cota nominal36,599mm. La cota
correspondiente al error independiente declarado de5° alcanza44,929mm; el resto
es−8,330mm. Por tanto no queda demostrada separación bajo ese escenario.
**No se observó ni se demostró contacto físico** y el signo negativo de la cota
no es una penetración medida. Ese estudio tampoco comprueba todos los pares
del robot, una escena física completa, dinámica o parada.

El modelo completo conserva54rechazos de geometría/margen en esta entrada y
retorna `START_GEOMETRY_REJECTED`. Son avisos del modelo, incluidas interfaces
mecánicas pendientes de interpretar; no54colisiones reales. Se usó escena vacía
sintética sólo para evaluar autocolisiones, no se declaró la escena del taller
medida. No se buscó ni certificó una ruta general a partir de esa entrada
rechazada. `physical_approval=false`, `installable=false`; no se exportó XML.

**Decisión:** no ejecutar HOME directo desde H03 ni ampliar la tolerancia del
script PICO para hacerlo pasar. Se explicó la limitación y se solicitó recuperar
la referencia PICO habitual con torso recto mediante teleoperación, detener el
mando y avisar. Sólo tras medir otra vez esa referencia se podrá usar el perfil
H02 ya probado. Esa colocación/retorno posterior todavía no se han realizado
por el agente al registrar esta entrada. No consta fallo físico del robot.

Evidencia privada: `../Humanoide-vla-evidence/20260911T085902Z_H03-ASYMMETRIC-READONLY/`.
Incluye `reads.json`, JointState/actuadores, evaluación PICO, programa PC
`review_candidate.py`, `clamp-candidate-screen.json`, `full-model-plan.json`,
backup documental y fuentes/hashes. Reproducción del análisis: cargar
`joints.yaml` con `cruzr_pico_to_home_owner_gate.load_sample`, ordenar con
`JOINT_ORDER`, generar `cruzr_internal_home_open_path.waypoints(q)` y evaluar
sus etapas con `review_clamp_trajectory_optimization.assess(...,501)` usando el
snapshot de08-09 `20260908T115359.543954Z_PICO-HOME-CHECK`. Separadamente,
`RobotGeometry` del paquete splint, escena vacía de análisis y
`general_home.planner.plan(...,timeout=20,timing_law='cubic-rest')` reproducen
el rechazo completo. El programa archivado fija los argumentos y fuentes
utilizados; no tiene cliente ROS, publicación, instalación o movimiento.

No hay cambio remoto que restaurar. Reversión documental selectiva desde
`before/`, preservando historial y trabajo ajeno. ANL-01.


## 11-09-2026 — caso H02, PICO con torso recto → HOME, 4×

**VERIFICADO: ejecución terminada, HOME recuperado y captura válida.**
**OBSERVADO por el operador: «resultado ok, suave y sin contacto, libres,
sigamos». H02 cerrado para esta postura y perfil.**

El usuario preparó PICO y confirmó el fin de la teleoperación. Se mantuvieron
las condiciones físicas confirmadas de la sesión supervisada. El preflight
versionado `cruzr_pico_to_home_owner.sh --preflight --speed 4` aprobó estado,
exclusividad, XML exacto y proceso posterior al registro de tareas. Lecturas
auxiliares: ningún objetivo activo (último estado cancelado 5), módulo libre;
paros0/0, cargador0, baterías77,7/75,5 %. El gate articular reconoció
`pico_body_zero`; inmediatamente antes del envío, error máximo0,00316384rad
frente a esa referencia, velocidad0. No se aceptó una postura intermedia.

Se envió una sola acción supervisada, después de armar la captura y repetir
la lectura de postura y salud. La autorización fue la sesión de pruebas en
el chat; no se rellenó ni simuló la frase de confirmación de terminal del
script propietario. El ejecutor versionado y sus confirmaciones siguen intactos.
No se añadieron opciones para omitir controles ni un ejecutor general.

```text
HOST=192.168.11.2
CONTAINER=walker-motion.manipulation_robot_app-1
XML=/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config/cruzr/pico_to_home_open_v2_4x.xml
SHA256=6dd482a70e8ec55e02f125eb442b483a12a7c591959e72965214fcc9e02027dc
TASK=cruzr/pico_to_home_open_v2_4x
GOAL=8c82d2bb-cea4-4c89-b195-1333b3d9f1a0
```

| Observación | Resultado |
|---|---|
| Perfil | 4×, 20 s nominales; abrir2,5s / bajar abierto10s / cuerpo3,75s / cerrar3,75s |
| Motion | `SUCCEED`, `status=4`; un objetivo, sin reintento |
| Captura | 2.103 muestras, completa, análisis sin incidencias |
| Velocidad máxima observada | 0,243997 rad/s |
| Error máximo frente a consigna solicitada | 0,00756892 rad; no es error frente a consigna final del servo |
| Hueco máximo de recepción | 31,702 ms |
| Fallos / muestras deshabilitadas | 0 / 0 en los veinte ejes |
| HOME final independiente | Máximo0,00297209rad, velocidad0 |
| Paros | 0/0; sin transición, frenado no medido |
| Observación del operador | Suave, sin contacto, abrazaderas libres |

Alcance: retorno de la referencia PICO con torso recto, con estas abrazaderas
vacías y este XML/velocidad. No acredita PICO con torso flexionado, posiciones
asimétricas, carga, otros obstáculos, velocidades o condiciones de parada.

Reproducción con operador en terminal: preparar esa referencia y repetir el
preflight anterior; armar la captura pasiva antes del movimiento; ejecutar
`./scripts/teleoperation/cruzr_pico_to_home_owner.sh --run --speed 4` y contestar
personalmente su confirmación. El script repite preflight y postura antes de
mandar el objetivo. Si la captura termina antes de acabar el ensayo, conservarla
como incompleta, sin afirmar validación del seguimiento. Nunca reintentar tras
fallo ni recargar/reiniciar para forzar un preflight desde brazos elevados.

El despacho de esta sesión utilizó el mismo tipo, endpoint y argumentos que el
ejecutor: `/mc/manipulation/action`, `mc_task_msgs/action/ArmTask`,
`{"task_name":"cruzr/pico_to_home_open_v2_4x","yaml_args":"{}"}`.
Los lectores y clientes con timeout no paran el robot.

Evidencia, programa exacto de la sesión, preflight, fuentes, resultados,
confirmación y backups documentales:
`../Humanoide-vla-evidence/20260911T084247Z_H02-PICO-SUPERVISED/`.
Sin instalación, recarga, reinicio, cambio de modo o desactivación de protección.
No hay configuración remota que revertir. Estado final: HOME medido, usuario
confirma contacto libre. Registro ANL-01/MOT-02.


## 11-09-2026 — caso H01, desde HOME con brazos bajos

**VERIFICADO por telemetría: una ejecución terminada y HOME recuperado.**
**OBSERVADO por el operador: «suave sin contacto». H01 cerrado para el caso ensayado.**
Este caso no aprueba un retorno desde cualquier posición, velocidades mayores
ni una distancia de parada. La petición del usuario autorizó ensayos físicos
supervisados; no se modificaron las restricciones del planificador general.

El usuario confirmó en esta sesión HOME, paro liberado, abrazaderas vacías,
robot estable y sin contacto, zona completa libre, cargador desconectado,
ruedas bloqueadas, mandos/PICO/UI inactivos y persona junto al E-stop.

### Preparación y trayectoria exacta

Se descubrieron Motion y ROS, se verificó el preflight canónico
`scripts/cruzr_blue_workbin_cycle.sh --check`, ambos paros 0, cargador 0,
baterías 79,6/77,5 %, actuadores habilitados e inmóviles y ausencia de
publicadores en `/mc/sdk/robot_command`. La acción anterior tenía estado 4,
el módulo estaba desbloqueado y el último cambio de estado de Control Center
registrado era AutoTaskMode. Las lecturas finales previas al comando repitieron
paros, cargador, ausencia de acción activa/publicadores y HOME medido.

Destino: Motion `192.168.11.2`, contenedor
`walker-motion.manipulation_robot_app-1`, v0.2.0. Se leyó y comparó el contenido
de `/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config/cruzr/home.xml`:

```text
SHA256=05174d2b4cf003b9b1c5274cd445b0d4faefe4276c5fbe8e59e68e6b64ee8cbe
SOURCE=scripts/teleoperation/tasks/cruzr_internal_home_open_v3_20s.xml
TASK=cruzr/home
START=HOME, veinte posiciones absolutas menores de 0,005 rad
```

Secuencia instalada, sin modificar: abrir hombros lateralmente −0,4 rad en
2,5 s; brazos bajos con apertura −0,6 rad en 10 s; cuerpo a cero conservando
apertura en 3,75 s; cerrar los brazos bajos en 3,75 s. Desde esta postura no
se necesita elevar los brazos ni desplazar la base. Duración nominal: 20 s.
El operador recibió antes del envío la descripción y la indicación de actuar
sobre el paro ante aproximación inesperada, contacto o tirón.

### Resultado registrado

| Observación | Resultado |
|---|---|
| Baseline pasivo | 346 muestras; HOME máx. 0,00278034 rad; velocidad 0 |
| Órdenes de movimiento | Una; sin reintento |
| Objetivo aceptado | `8c557150-dbbe-4ed7-9f20-0034ef0b0323` |
| Resultado Motion | `SUCCEED`, `status=4` |
| Captura durante ensayo | 2.103 muestras, completa; análisis sin incidencias |
| Velocidad máxima observada | 0,247139 rad/s, hombro derecho roll |
| Error máximo frente a consigna solicitada | 0,00775288 rad; no es la consigna final aplicada al servo |
| Apertura observada, recorrido angular | 0,596910 rad izquierda; 0,597294 rad derecha |
| Hueco máximo entre recepciones | 27,831 ms |
| Fallos / muestras deshabilitadas | 0 / 0 en los veinte ejes |
| HOME final, lectura independiente | Máximo 0,00278034 rad; velocidad 0 |
| Paros observados | 0/0, sin transición: no se midió frenado |
| Inspección física final | Operador confirma «suave sin contacto»; caso H01 cerrado |

Primera preparación abortada antes de enviar movimiento: el lector auxiliar
rechazó el separador YAML final `---` de ROS 2. Se archivó esa preparación con
`movement_commands=0`; se corrigió el lector para exigir un único documento
no vacío y se repitieron las lecturas. No fue un fallo de Motion ni un reintento
de trayectoria. Una consulta auxiliar usó `rg`, ausente en Vision; se repitió
con `grep` y se conservan ambas evidencias.

### Reproducción y límites

La receta de captura/análisis está en
[captura HOME](CRUZR_HOME_CAPTURA_Y_PROGRESO_INDEPENDIENTE.md).
Para repetir H01 se deben comprobar de nuevo la preparación física, el
preflight, el hash anterior, la exclusividad y HOME fresco. Arrancar una captura
de 45 s y verificar que recibe actuadores y ambos paros **antes** del envío.
Con esas condiciones, dentro del contenedor Motion descubierto, el despacho
utilizado fue exactamente:

```bash
source /opt/walker/setup.bash
export ROS2CLI_DISABLE_DAEMON=1
timeout 90 rosa action send_goal /mc/manipulation/action mc_task_msgs/action/ArmTask \
  '{"task_name":"cruzr/home","yaml_args":"{}"}'
```

Esta llamada mueve incluso partiendo de HOME; no es una consulta ni un
comando de recuperación general. El `timeout` termina el cliente y **no frena
Motion**. Ante resultado fallido/interrupción, no reintentar ni rearmar.
Tras éxito, exigir una lectura nueva HOME y conservar la captura completa;
registrar aparte lo observado físicamente por el operador.

No se instalaron XML, paquetes o servicios, ni se recargó, reinició, cambió
modo, liberó paro o desactivó protección. No se amplió el ejecutor PICO ni se
creó un ejecutor desde posturas arbitrarias. No hay cambio persistente remoto
que restaurar; el robot quedó en HOME medido. No repetir movimientos para
"revertir" el ensayo.

Evidencia privada y fuentes exactas de la intervención:
`../Humanoide-vla-evidence/20260911T082510Z_SUPERVISED-HOME-PREPARATION/`.
Incluye lecturas, preparación fallida, `trial_once.py`, comando SSH sin
credenciales, resultado de acción, baseline, captura/análisis y backups de
documentos en `before/`. Los tiempos PC se registraron en UTC; los relojes del
robot no se consideran sincronizados.

### Punto de reanudación

H01 y H02 cerrados, H03 capturado pero sin retorno directo aprobado ni ejecutado.
El usuario indicó después que la teleoperación no está disponible: **queda
retirada la petición de regresar a PICO mediante teleoperación**. Se creó y probó
un preparador desde JointState real, sin PICO, que conserva la asimetría y para
ante rechazo del modelo. Todavía no existe aquí un ejecutor general habilitado.
[Script, pruebas y resultado actual](CRUZR_RECUPERACION_SIN_TELEOPERACION.md).
No usar el HOME interno, un reinicio o límites ampliados para saltar ese rechazo.
La configuración PICO instalada conserva `waist_mode: 0`, `leg_mode: 0`.
