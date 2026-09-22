# get1 guardado y ejecutor get1 → put1 → HOME

**22-09-2026 — BOX-01-ORIGINAL-SCRIPT: variante local con tareas anteriores.**
Creado por petición explícita [force_excenario1.original.sh](../../scripts/force_excenario1.original.sh)
(nombre exacto solicitado, excenario). Deriva del force_escenario1.sh de HEAD
identificado en manifest de evidencia. Secuencia get1→vision/enable_transport_vision_switch
→Singapore/separate_right_cruzr→cruzr/mobot_back_20→put1→wrc_cruzr/put_cruzr_wrc_low
→cruzr/originalhome. No usa ni inicia SPS; la selección original puede elegir
una lateral. Ejecuta navegación a get1, no un agarre en posición actual.
Conserva validación de resultados, aborto, mapa/localización y llegada; añade
preflight técnico existente y aviso físico del ejecutor actual. Mantiene el
ajuste ROSA_LOG_LEVEL=ERROR en lectura JSON de pose. Reutiliza el helper SSH
existente sin duplicar credenciales. No cambia middleware ni tareas instaladas.

Destino PC: scripts/force_excenario1.original.sh, ejecutable, SHA256 `5870865587e6b301d8c90fc2b2e3ce8024066921e5f0f41b32ab71586b95342b`.
Aplicación: archivo aditivo; dependencias scripts/cruzr_recover_to_home.sh,
scripts/cruzr_blue_workbin_cycle.sh, SSH/Docker/ROSA y tareas originales del robot.
Validación local: bash -n, --help; pruebas offline de ciclo, fallo de agarre y
--check registradas en evidencia. No ejecución, instalación ni movimiento en
robot; compatibilidad/agarre físico PENDIENTES. Uso diagnóstico:
`./scripts/force_excenario1.original.sh --check`; ciclo sólo tras comprobar
estado físico y recorrido. No reanudar el ciclo con caja sujeta.
Reversión: retirar sólo este archivo nuevo y revertir selectivamente estas notas;
los dos scripts actuales permanecen intactos. Evidencia/manifest y backups:
`/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260922T095947Z_ORIGINAL_SCRIPT`. Sin commit/push.

**22-09-2026 11:31 CEST — Repetido fallo de recogida baja, sin cambio de selector.**
Goale2b1c122… entrega caja frontal correcta a Motion; X0,802563/Y0,115734/
Z0,178277m. ExcesoX2,563mm y cinco fallosIK011 seguidos de agotamiento de
búsqueda. Misma clase de fallo del intento52efbb3b…; llegada get1 correcta
no valida recogida. Diagnóstico del agente sólo lectura/replay; ninguna
trayectoria nueva ni modificación de límites. No repetir ciclo como solución.
[Repetición y siguiente trabajo](../incidents/2026-09-22_CAJA_FRONTAL_COTA_BAJA.md).

**22-09-2026 11:22 CEST — Nueva recogida baja rechazada; selección correcta.**
Goal52efbb3b… devuelve ClampBoxOutOfReach. Sesión/TF/imagen y Motion confirman
candidata3 frontal, no laterales. Pose nueva base_link≈[0,8006;0,1181;0,1671]m;
Motion≈[0,8039;0,1192;0,1741]m. Distinta de la caja aZ≈0,794m de la prueba
perceptiva anterior. Excede X3,92mm y falla IK011/búsqueda de postura; no basta
quitar el límite ni interpretar llegada get1 como alcance de agarre. Preparó
cabeza/brazos; no asumir HOME. Agente sólo diagnóstico, sin nuevas trayectorias
ni cambios de controles; recoger a esta cota sigue pendiente de validación.
[Informe y evidencia](../incidents/2026-09-22_CAJA_FRONTAL_COTA_BAJA.md).

**22-09-2026 10:58 CEST — Corregido empate entre caja frontal y soporte.**
El nuevo fallo38371422…/NoneException procedía del selector: dos detecciones de
la misma pila tenían ángulo casi igual. Operador confirma la caja abierta
superior de la pila frontal. Selector ahora agrupa columnas coherentes de
workbin22cm y elige la superior dentro de la pila frontal, sin priorizar la
altura de pilas laterales ni ampliar controles físicos. Paquete
`74f5507e44addd71` instalado de forma aditiva; percepción directa y recepción
nativa SUCCEED verificadas, sin trayectoria. Pose nueva X≈0,780/Y≈0,134/Z≈0,794m;
no reutilizar la pose baja del fallo anterior. Usuario confirma inmóvil y sin
contacto; tras preparación del ensayo no asumir HOME. Agarre aún PENDIENTE.
[Causa, fuentes, pruebas, instalación y reversión](../incidents/2026-09-22_FRONTAL_PILA_AMBIGUA.md).

**22-09-2026 10:10 CEST — Se retoma el agarre por indicación del operador.**
Selección frontal consumida por Motion verificada; el rechazo previo al agarre
combina pose X0,803542m e IK fallida para la trayectoria de separación. No hay
prueba de contacto lateral en ese rechazo. Revisar postura/trayectoria de la
caja baja, sin anular controles ni cambiar a ciegas de tarea.
El diagnóstico estático de navegación explica la primera salida−0,04m/s por
inicialización `odom_vx−0,05`; su perfil candidato permanece sólo en PC,
SIN instalar/activar/probar. No hubo nuevos movimientos ni cambios remotos.
[Agarre](../incidents/2026-09-22_FRONTAL_SPS_ALCANCE_ICEORYX.md#revision-centrada-en-el-agarre-22-09-2026); [navegación](ARC_PRECISE_ARRANQUE_20260922.md).

**2026-09-22 09:55 CEST — Ensayo5cm interrumpido por retroceso; robot detenido en HOME.**
Operador confirmó espacio frontal/apoyos libres, ruedas en navegación y persona
junto al paro. Se cargó utars_nav_map y relocalizó: NAVIGATION_READY; durante
esta preparación la cabeza volvió cerca de HOME, observado antes de navegar.
Un único objetivo5cm al frente (27028c333b0c450ea296ff577d3c38bc) generó retroceso.
El monitor solicitó navigation_stop al medir−5,11mm; petición aceptada status4.
Postlectura: desplazamiento−7,503mm, velocidad0, HOME20D sin faults, máximo
0,000959rad. No avance5cm, agarre, reintento ni segundo movimiento de cabeza.
Log del proveedor: MPPI tolerancia0,3m→ArcPreciseController, allow_backward=true;
objetivo delante5cm, x_tilt−0,05 y salida x−0,04m/s. Causa completa/contrato del
controlador PENDIENTE; no invertir signos ni forzar parámetros a ciegas.
Herramienta nueva front_nudge.py queda bloqueada para --run; --check sólo lectura.
Evidencia: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260922T073932Z_FRONT_REACH_RECHECK`.

**2026-09-22 09:46 CEST — Caja frontal confirmada; cabeza preparada, sin agarre.**
Tras «adelante» y condiciones físicas confirmadas en el arranque, se ejecuta
únicamente `--prepare-vision --yes`: cabeza0/−0,43rad en2s,
goalc68f5d5e-45b9-4ff6-9ac7-a3c9d01ac807 SUCCEED/status4. Preflight correcto.
Postlectura20D sana, inmóvil; pitch−0,430473rad y brazos próximos a HOME.
Dos detecciones con TF exacta eligen índice1, la caja frontal baja, frente a
la lateral alta: X0,800744/0,798246m; Y0,105542/0,106856m;
Z0,383803/0,382768m. Selección correcta y estable≈3mm; X en el borde0,8m
del proveedor. Esto no valida IK ni espacio entre cajas.
Mapa vacío/FSM_WAITSETMAP tras encendido; no hay pose de navegación actual.
Propuesta de ensayo: avance recto5cm y nueva medición, conservando límites;
requiere preparar localización/control y confirmar espacio de chasis/apoyos y
ruedas en navegación. Confirmación solicitada y PENDIENTE. Sin avance ni agarre.
Cabeza queda bajada; no HOME automático.
Evidencia: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260922T073932Z_FRONT_REACH_RECHECK`.

**22-09 — Ensayo frontal FALLIDO; diagnóstico de lectura VERIFICADO.** MetaClamp
sí recibió la caja frontal elegida, pero rechazó alcance/IK (X0,803542m).
RouDi retiró runtimes por heartbeat y abortaron cliente ROSA/adaptador; comunicación
sigue degradada. Robot inmóvil en postura preparatoria, **fuera de HOME**;
actuator_state sin muestra. No repetir ciclo ni reiniciar a ciegas. Usuario
confirma recogidas previas sin laterales y caja sobre otras dos; no pedir nuevas
medidas. Sin cambios remotos del agente. [Informe y reanudación](../incidents/2026-09-22_FRONTAL_SPS_ALCANCE_ICEORYX.md).

**21-09 — VIGENTE: selección frontal SPS instalada y recepción nativa comprobada.** Ambos ejecutores llaman ahora a `local_front_box/separate_right_cruzr`; tres consultas MetaLook SUCCEED seleccionan la caja baja frontal entre dos candidatas y Motion registra la misma pose. `--check-sps` prueba esa interfaz sin trayectoria, actualizando caché `box/0`; usar con abrazaderas vacías. Ciclo habilitado tras confirmación física/preflight, sin ejecutar agarre por el agente.49 tests verificados; recogida y ciclo físicos PENDIENTES. [Instalación, evidencia, uso y reversión](INTEGRACION_CAJA_FRONTAL_SPS.md).

**21-09 — HISTÓRICO, decompilación previa a instalación SPS:** Copias locales de MetaClamp/percepción analizadas; `special_box_name` activa detección y selección SPS. Corrige la conclusión de que necesariamente faltan fuentes. Hay que conservar la pose original y la referencia de historial `box/0`; adaptador e integración aún PENDIENTES. Sin cambios ni movimiento en robot; run conserva rc78. [Hallazgos, reproducción y límites](DECOMPILACION_SELECCION_CAJA.md).

2026-09-16, Europe/Madrid. Estado por apartado; no constituye ensayo del ciclo completo.

## MAP-GET1 — Guardado de posición y orientación

**VERIFICADO, 12:09 CEST:** `get1` persistido en `utars_nav_map`, con la base en
la posición indicada por el operador. Pose nueva de `/nav/robot_pose`, marco
`map`, validada con dos mensajes nuevos y reloj del robot.

- X: `0.543184372094` m; Y: `-1.77098915045` m.
- Yaw: `-1.53310485885` rad = **−87,8404379631°**.
- Modo `logo_nav`, tipo `hand_marker`, metadato `work-point`.
- Valores auxiliares del editor UBTECH: velocidades 0,3 m/s, 0,05 m/s lateral
  y 0,3 rad/s; no se ejecutó navegación para probarlos.
- Fuente reproducible: [perfil JSON](../../config/box_handling/utars_nav_map_get1.json).

Inicialmente `FSM_WAITRELOCATE` y sin pose. El usuario completó localización
mediante web; después se verificó `FSM_WAITNAVIGATE`. El agente no relocalizó,
reinició ni envió navegación/manipulación. Conexión de lectura/escritura del
mapa por Vision Wi-Fi `192.168.42.2`; `.11.3` no respondió directamente desde PC.

**Destino exacto:** Vision, `walker-system.sys_map_http_manager-1`, API local
`http://127.0.0.1:30023`; persistencia comprobada en
`/etc/walker/map/utars_nav_map/umap/umap.json` y metadatos API de
`/etc/walker/map/utars_nav_map/user/task.json`.
API original del editor: POST `/map/get/utars_nav_map` con `{}`; POST
`/map/save/utars_nav_map` con `map_name`, `umap` y `task`, estos últimos
**cadenas JSON serializadas**, no objetos. Primer envío con objetos fue
rechazado con code500/type_error; antes del segundo se verificó que el mapa
seguía idéntico al respaldo. Segundo envío code200; lectura API y archivo
confirman coordenadas/orientación. Cuadrícula, líneas y marcadores conservados.

SHA256 del umap persistido:
`44c31c4b6ca44078476e727ddcf33c66d35cfb35d7bc18db884df5c31ac45835`.
SHA256 canónico de `map_data` (JSON sort_keys, separadores coma/dos puntos):
`249a2b6b02496d67ac5a2c0bee0e44f1406d42fc593db018aa68994aeef16ec5`.

**Respaldo externo y evidencia:** `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260916T095254Z_SAVE_GET1`:
`before-map.json`, `after-map.json`, resultados de lectura/guardado y receta
exacta `save-remote-serialized.py`. SHA256 del respaldo `before-map.json`:
`5a97581c144d2b9b0c0327bf01ecd21596087aa9227fa435a036b3fe5ee5849d`.
Ese respaldo de API no sustituye una exportación completa del mapa 3D.

**Recrear después de actualización:** recuperar primero el mismo mapa original;
comparar su `map_data` con el hash anterior. En el editor guardar `get1` con X/Y
y orientación indicadas, modo `logo_nav`, y metadato `work-point`. Si se utiliza
API, consultar el mapa completo, respaldarlo, añadir/sustituir únicamente el
`target_point` del perfil en `umap.target_points` y `task_point` en
`task.target_points`, conservando el resto. Enviar con las dos cadenas JSON y
releer. No copiar estas coordenadas a un mapa reconstruido con otro origen.
No requiere reinicio. **Cargado en el planificador y navegación física: PENDIENTE**;
no se mandó un objetivo para comprobarlo.

**Reversión:** desde el editor eliminar sólo `get1` de este mapa, o mediante la
misma API retirar únicamente su entrada y metadato, conservando otros cambios
posteriores. El respaldo completo sólo es apto si nadie ha cambiado el mapa
después. `put1` todavía no existe en la última lectura.

## BOX-01-EXEC — Extensión solicitada del ejecutor

**IMPLEMENTADO Y PROBADO OFFLINE; NO EJECUTADO EN ROBOT.** Archivo PC:
[scripts/force_separate_right_cruzr.sh](../../scripts/force_separate_right_cruzr.sh).
SHA256: `62ce6a30e172aede79cf08410f80d8f1d9e255b8f3435d7e260a84ca339f2546`.

Orden ahora, en una sola invocación:

1. Consultar mapa activo `utars_nav_map`, navegación localizada y `put1` único
   con coordenadas/orientación finitas y modo `logo_nav`.
2. `vision/enable_transport_vision_switch`.
3. `Singapore/separate_right_cruzr`.
4. `cruzr/mobot_back_20`.
5. `/vnav/task/command`, `navigation_start`, `target_point` con
   `map_name=utars_nav_map`, `mode=logo_nav`, `id=put1`.
6. `wrc_cruzr/put_cruzr_wrc_low` (incluye apertura).
7. `cruzr/home`.

Cada etapa exige un único resultado final exitoso; Motion exige
SUCCEED/1101001/status4. Una respuesta de navegación con error interno, aunque
status4, no permite depósito. Fallo o timeout detiene la secuencia sin reintentos,
sin apertura ni HOME de recuperación. Si navegación estaba activa, se solicita
`navigation_stop`; no se confunde timeout o solicitud de parada con parada física
verificada. Timeouts de cliente: visión20s, separación45s, retroceso30s,
navegación180s, depósito120s, HOME60s. La pérdida completa de conexión puede
impedir solicitar parada. No usar el ejecutor desde cero con una caja ya sujeta.

Uso desde raíz del repositorio, después de registrar el destino real `put1`:

```bash
./scripts/force_separate_right_cruzr.sh --check
./scripts/force_separate_right_cruzr.sh
```

Añadir `--wifi` a ambos si se accede por Vision como salto SSH a Motion.
Se corrige el comportamiento anterior de `--wifi`, que intentaba ejecutar el
contenedor de Motion directamente en Vision. Esta ruta de salto está preparada,
pero no se ha probado en vivo en esta modificación.

`--check` sólo consulta mapa/localización/destino; no mueve y no cualifica la
geometría del depósito, postura o carga. La posición guardada de `put1` no cambia
la altura/pendiente del XML/YAML del proveedor. El depósito hacia la estantería
local sigue sin ensayo comunicado. El ciclo completo requiere zona libre para
el retroceso y navegación, ruedas sin bloqueos físicos, control exclusivo y
supervisión junto al paro; confirmar condiciones actuales antes de ejecutar.

**Activación/dependencias:** guardar archivo PC; Bash, SSH y herramientas ya
usadas, Python3 estándar y ROSA dentro del contenedor Motion. API de mapas en
Vision puerto30023. Sin instalación, recarga ni modificación de XML del robot.
**Reversión:** restaurar sólo el ejecutor respaldado en `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260916T103024Z_GET1_PUT1_EXECUTOR/before/`;
no afecta al `get1` guardado. **Verificación:** sintaxis Bash y pruebas offline
[scripts/test_force_separate_right_flow.py](../../scripts/test_force_separate_right_flow.py),
que sustituyen ROSA por simulación y API por servidor local, sin SSH al robot.

## Incidente posterior

**2026-09-16 — Incidente posterior: separación abortó con Iceoryx, salida137.**
Tras navegar a get1, visión detectó la caja; RouDi retiró aplicaciones por
heartbeats ausentes ~1,5s y Motion abortó con CHUNK_LOCKING_ERROR/SIGABRT.
Docker reinició manipulación e IMU; no fue timeout45s. Operador confirma caja
apoyada, robot inmóvil, sin pulsar paro; JointStates posterior con velocidades0.
X_BaseBox0,810808m excede por10,808mm el límite0,8m, hallazgo distinto sin vínculo
causal demostrado con el crash. Sólo diagnóstico; no se reinició ni movió nada.
[Informe y continuación](../incidents/2026-09-16_SEPARATE_RIGHT_137_ICEORYX.md).

2026-09-16, actualización posterior: dos intentos get1 devolvieron
ClampBoxOutOfReach7101100; X ligeramente fuera de0.8m y fallo IK101 conjunto.
Pose posterior próxima a get1 (7,84mm); HOME intermedio no resolvió alcance.
put1 ya existe. No hubo cambios remotos; diagnóstico adicional en
`docs/incidents/2026-09-16_SEPARATE_RIGHT_137_ICEORYX.md`.

## Depósito posterior: altura incompatible

**2026-09-16 — VERIFICADO: depósito WRC original no adaptado a superficie de 100 cm.**
YAML instalado y trayectoria registrada ordenan Z de manos ≈1,10→0,65→0,45 m;
`1.2` corresponde al torso, no a la estantería. Los 90 cm del documento son
horizontales desde rueda derecha a parte inferior del mueble, no altura ni la
misma referencia física que los 59 cm de recogida. No corregirlo acercando el
mueble. Usuario comunica reinicio; HOME posterior no medido por el agente.
Diagnóstico sin movimientos ni cambios remotos; variante de depósito pendiente.
[Análisis y referencias](DEPOSITO_WRC_ALTURA_100CM.md).

## 2026-09-16 — BOX-01-AUTO-MAP: preparación automática del mapa

IMPLEMENTADO EN PC; prueba con robot pendiente. Por petición del usuario,
`scripts/force_separate_right_cruzr.sh` conserva navegación a get1 y añade:
consulta de mapa/estado, validación de get1 y put1 guardados (orientación finita,
modo logo_nav), map_set a utars_nav_map si es otro, relocation_start global
si cambió el mapa o está FSM_WAITRELOCATE, y nueva consulta que exige mapa
correcto y FSM_WAITNAVIGATE antes de navegar/agarrar. Si ya está listo, no carga
ni relocaliza. Estados ocupados/desconocidos se rechazan; no se interrumpe una
navegación ajena. Acciones de preparación limitadas a90s, una vez, sin reintento.
Timeout o fallo no permite seguir; no se afirma que un timeout detenga el servicio.
`--check` permanece sólo lectura: informa preparación pendiente con salida55.

Uso normal, desde scripts: `./force_separate_right_cruzr.sh` (inicia el ciclo
completo). No requiere instalar XML ni reiniciar el robot; el script envía la
preparación al ejecutarse. Conserva depósito y HOME existentes sin cambiar alturas.
Mapa fijo del escenario1: utars_nav_map, coherente con Navigation/navigation.xml
del proveedor; no usa coordenadas manuales para fingir localización.
No se ha ejecutado el ciclo ni cambiado mapas/estado remoto en esta intervención.

Reversión: restaurar únicamente el script respaldado en /home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260916T122654Z_AUTO_MAP,
conservando cambios posteriores. No revierte modificaciones de mapas de futuras
ejecuciones. Tests offline simulan ROSA/API; validación física pendiente.

HOME-BODY-FIRST-04: usuario comunica «funciona» tras el reinicio/liberación;
se registra éxito observado por operador, sin inferir validación desde cualquier
postura ni nueva telemetría del agente.

Verificación BOX-01-AUTO-MAP: 14 tests offline y bash -n correctos. SHA256 ejecutor: `94ec4bc7747d2fee1a46028bd942bf5ad3be2b56b00dbb86a5fae7001cbd34be`.

2026-09-16 12:37 UTC — Diagnóstico sólo lectura del anillo rojo durante ciclo:
Control Center alterna logo/warning-red asociado a02039005, catálogo instalado
«pocas características coincidentes durante localización». También aparecieron
02039001/02039002, resueltos después; no se asigna significado sin catálogo.
Última transición capturada20:35:52 del reloj del log: solve02039005 y retorno
warning-red→logo. Es aviso intermitente de localización; no prueba causa visual
específica ni fallo de HOME. Motion registra éxito del árbol HOME a20:36:33.
No se interrumpió el flujo, cambió expresión, borró fallos ni reinició nada.
Evidencia: /home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260916T123727Z_RED_RUNNING.

## 2026-09-17 — Escenario1: puntos mapping_marker

Consulta viva confirma get1 y put1 tipo mapping_marker, mode vacío. El bloqueo
«get1 debe tener modo logo_nav» era una restricción del ejecutor, no fallo de
localización: FSM_WAITNAVIGATE en el log del operador. Corrección PC en
scripts/force_escenario1.sh: acepta logo_nav por ID, o mapping_marker/mode vacío
mediante free_nav con point_x/point_y/point_yaw guardados, siguiendo el contrato
ya implementado en cruzr_blue_workbin_map_route.sh. Ambos puntos se validan antes
de mover; otros tipos, duplicados y coordenadas no finitas siguen rechazados.
Velocidad free_nav: x0,18m/s, y0,01m/s, yaw0,20rad/s. Sin cambios a mapa ni puntos.
Preserva resultado final estricto y parada de navegación ante fallo.
No se ejecuta ciclo físico en esta revisión. Respaldo ejecutor/tests: /home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260917T085737Z_SCENARIO1_MARKERS.
Reversión selectiva desde ese respaldo; no modifica estado del robot.

Verificación 17-09: 17 tests offline y sintaxis Bash pasan; --check vivo rc0, utars_nav_map/FSM_WAITNAVIGATE y get1/put1 disponibles. Cero navegación o manipulación.

## 2026-09-17 — get1: FINISH del planificador y pose obsoleta

Operador confirma robot inmóvil tras fallo. Consultas sólo lectura: planificador
registró FINISH; después close_auto_update_map/save_auto_update_map devolvieron
LOCATION_LOST y ese estado pasó al resultado exterior, pese a SUCCEEDED.
Árbol instalado envuelve esas acciones VSLAM en ForceSuccess. Corrección del
diagnóstico inicial: la respuesta por sí sola no demuestra pérdida durante el
movimiento ni llegada. No se acepta el error como éxito automáticamente.
/vnav/vslam/state actual informa LOCATION_LOST. /nav/robot_pose entrega stamp
1789634982.607435, pose x1.3680026093,y1.3859004378,yaw≈0.0346456: próxima a put1,
no a get1. Reloj Vision posterior1789635706, muestra >10min antigua; no usarla
para verificar llegada. /uslam/module_state sin muestra en lectura nativa acotada.
No se relocalizó, reinició, navegó ni agarró desde el agente; causa raíz de la
pose obsoleta pendiente. Evidencia externa: /home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260917T090056Z_LOCATION_LOST.

## 17-09 — Recuperación de localización y corrección del diagnóstico

Usuario autoriza recuperar localización con robot confirmado inmóvil. Se envió
una sola relocation_start global para utars_nav_map: goal
ccd4e4bb-1e67-4914-81e5-e6f6ce38724f, NAVIGATION_READY/status4. No navegación,
agarre, HOME, reinicio ni cambios de archivos remotos. Estado volátil de
localización modificado; no hay reversión automática a una pose antigua.

Dos publicadores TRANSIENT_LOCAL en /nav/robot_pose. Consulta ROS2 por defecto
recibía muestra retenida antigua cercana a put1. Consulta ROSA nativa y ROS2 con
--qos-durability volatile reciben poses nuevas coincidentes: x0.095318657,
y0.666315422; stamps1789635912.933→1789635942.574→1789635945.434.
Posición actual a≈8,08mm de get1, orientación≈0,39° de diferencia.
Esto corrige la inferencia anterior de localización totalmente congelada;
no demuestra que antes de relocalizar no hubiera ya una fuente válida.
VSLAM auxiliar sigue LOCATION_LOST y la navegación2D había registrado FINISH.
No aceptar ese resultado contradictorio sin verificar llegada con pose fresca.
El script conserva rechazo estricto; ajustar interpretación/validación de llegada
es pendiente separado, no se repitió el ciclo. Evidencia: /home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260917T090350Z_RELOCALIZE.
Receta ejecutada y respuesta completas en relocation.json; consultas de fuentes
nativa/volátil en native_pose*.json y pose_volatile.json.

## 17-09 — BOX-01-ARRIVAL: éxito condicionado a llegada medida

Modificado force_escenario1.sh a petición del usuario. VSLAM_LOCATION_LOST sólo
pasa el filtro inicial si status4 y dmsg empieza navigation_start SUCCEEDED;
no concede continuación por sí solo. Después de toda navegación, incluso con
resultado normal, se releen mapa/WAITNAVIGATE y dos poses ROSA nuevas mediante
QoS volatile. Se exige marco map, tiempos posteriores al inicio de lectura
(tolerancia0,1s), edad≤2s, avance temporal, cuaternión válido, coordenadas finitas,
error≤0,05m y yaw≤3°. Las dos muestras deben cumplir. Si no, aborta y solicita
navigation_stop, sin agarre/depósito/HOME ni reintento. Nunca acepta otros errores.
No certifica despeje físico ni exactitud absoluta de la localización.

Se conservan coordenadas esperadas también para logo_nav; no se envía ese
metadato interno al servidor. Ambos destinos usan idéntica comprobación.
19 tests offline pasan, incluidos aviso auxiliar con llegada válida, posición
antigua, posición incorrecta y orientación incorrecta; Bash sintaxis correcta.
Ensayo de lectura del verificador real en get1: dos muestras nuevas, error8mm,
yaw0,388°, LLEGADA_VERIFICADA=get1. No se envió navegación/manipulación ni se
cambió el mapa. Ejecución del ciclo corregido aún pendiente del operador.

Cambio PC; no requiere instalar ni recargar robot. Respaldo, prueba viva y
reversión selectiva del script/tests: /home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260917T091003Z_ARRIVAL_CHECK. SHA256 ejecutor: 9a212c3b26c750d86cec3a9af9c34d2d55d24677d3d07e2c4ea9366ebaf6bb46.

## 2026-09-17 — BOX-01-WAITSETMAP: carga inicial después del encendido

**OBSERVADO en salida aportada por el operador:** mapa activo vacío y
FSM_WAITSETMAP; el preflight abortó con54 antes de cargar el mapa. No es
prueba de navegación ocupada ni del fallo anterior ClampBoxOutOfReach.
**IMPLEMENTADO en PC:** se admite explícitamente FSM_WAITSETMAP para preparar
el mapa. En ejecución normal se llama map_set a utars_nav_map también cuando
el nombre ya coincide pero el FSM espera carga; después relocalización global
y comprobación independiente de mapa/FSM antes de navegar. Estados ocupados o
desconocidos siguen rechazados. --check permanece de lectura y devuelve55 si
requiere preparación. Se conserva HOME comentado por el operador.

Destino/fuente reproducible: scripts/force_escenario1.sh en el PC; se transmite
por SSH al ejecutarlo, sin instalación remota. SHA256: `6e72819ba953a2556691971c93b673de9c43fc9e0482615f8210960608ba5236`.
Depende de los endpoints ROSA y API de mapas existentes y de get1/put1 válidos.
Backup anterior, incluidos cambios pendientes y SHA256SUMS: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260917T104341Z_WAITSETMAP_FIX`.
Reversión: retirar únicamente FSM_WAITSETMAP de la admisión y de la condición
map_set, conservando los demás cambios del operador. Tests asociados en
scripts/test_force_separate_right_flow.py; ejecutar `bash -n scripts/force_escenario1.sh`
y `python3 -m unittest scripts/test_force_separate_right_flow.py`.
No se ha conectado al robot ni enviado mapa, localización o movimiento durante
esta corrección. Instalación/carga/prueba física remota: PENDIENTES; siguiente
paso, verificar la preparación en la próxima ejecución supervisada.

Validación local: sintaxis Bash correcta y 23 pruebas offline superadas (43,718s), incluidas carga inicial, --check sin escrituras, fallo de carga y estado desconocido. No constituye ensayo físico.

## 2026-09-21 — BOX-01: varias cajas y selección fuera de alcance

**VERIFICADO en logs leídos a las 10:40 UTC / 12:40 Europe/Madrid.** Goal
`58946ad3-889d-419e-baf6-fa9097d32173` enlazado en Motion con el intento
18:35:03–18:35:09 del log vendor (UTC+8). Visión devuelve tres poses;
Motion consume la que coincide con `best.pose[0]`: cámara
[-0.699946,0.470781,0.913464]m. No se demuestra que siempre elija índice0.
La transformación registrada por Motion da X_BaseBox
[0.804895,0.723056,0.706858]m; orientación RPY aproximada
[0.0469,-0.0402,-1.6648]rad. Límites vigentes X[0.4,0.8],
Y[-0.4,0.4], Z[0,1.5]m: exceso X4.895mm y Y323.056mm.
Después falla CheckIkSolved y devuelve ClampBoxOutOfReach. No hay evidencia
de un rechazo por colisión para este intento. La otra candidata best.pose[1]
está mucho más centrada horizontalmente en cámara (-0.0743363m), pero su
identidad física y alcanzabilidad NO están confirmadas.

**INFERENCIA:** selección de una caja lateral distinta de la deseada, compatible
con varias cajas visibles; confirmar sobre imagen anotada. No concluir que el
robot no puede trabajar con cajas contiguas, ni desactivar límites/anticolisión.
Comparación en la misma instancia: separate_right y separate_bodyback anteriores
18:26 terminaron SUCCESS, con X_BaseBox[0.7876,0.1016,0.5997]m para la primera.
Esto es éxito reportado por software, no nueva confirmación física del operador.

Propuesta: contrastar imagen/selección; comparar detección con una sola caja
visible conservando posición de objetivo/base, sin ejecutar agarre de prueba.
Para solución permanente investigar selector/ROI soportado por proveedor y
rechazar ambigüedad antes de la acción. No suponer que una lectura previa obliga
al MetaClamp a usar esa misma pose: la tarea solicita su propia detección.
No se ha llamado visión, movimiento, HOME, mapa, cambio de modo ni reinicio;
sólo docker ps/logs y lectura del YAML. Scripts del usuario conservados.
**PENDIENTE:** identificación visual de la caja seleccionada, mecanismo soportado
de selección y validación física. Evidencia privada y copias previas: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260921T104034Z_SEPARATE_NEIGHBOR_DIAG`.
Reproducción: en Motion, `docker logs --tail 5000 walker-motion.manipulation_robot_app-1`;
en Vision, `docker logs --tail 1800 walker-box_pose_estimation.box_pose_estimation-1`.
Los logs rotan: usar la captura y su SHA256SUMS para este intento concreto.

## 2026-09-21 — BOX-01-SELECT: identificación visual y consulta perceptiva

**VERIFICADO:** recuperadas las imágenes originales del fallo, timestamp
1789986907.692817000, coincidente con best-stamp del detector. En
`failed_grasp.jpg` la etiqueta XYZ(-0.700,0.471,0.913) identifica la caja
superior de la pila a la izquierda de la imagen: coincide con best.pose[0]
y X_CameraBox consumido por Motion. La candidata1 está en la caja baja a la
derecha, aproximadamente centrada. Objetivo deseado: PENDIENTE de confirmar
por el operador. No se ha probado alcanzabilidad de esa otra caja.

Usuario confirma robot en HOME frente a las cajas en get1. Lectura articular:
brazos próximos a cero, cabeza pitch−0.002876rad; la cámara horizontal sólo
muestra parcialmente cajas abajo. Esto no implica que la base haya cambiado.
Una consulta perceptiva transport/head/grasp (0.603,0.397,0.22), goal
 e37eaa4b-31ea-44c4-85cc-22652601f5ff, devuelve status4 pero ok=False,
cero poses: NO es detección exitosa. No hubo orden de movimiento ni cambio de
cabeza. Captura pasiva finalizada; segment tiene stamp0 y no demuestra
sincronización exacta; RGB tiene timestamp propio.

La consulta activa el procesamiento perceptivo temporal y el proveedor guarda
automáticamente imágenes en Vision
/etc/walker/bag/vision/pose_6d_head_front/2026-09-21/18-45/.
No se cambió configuración, servicio, mapa ni protección; no requiere
restauración de postura. No se borraron las imágenes generadas.
Origen de imágenes del fallo: mismo directorio, subcarpeta18-35,
1789986907.692817000_action_grasp.jpg y _seg.jpg.

Contrato instalado: trans_inputs tiene camera_name,task_stage,box_size,target_pose;
no select_id. select_id pertenece a sps_inputs, ruta diferente, no asumir
intercambiabilidad. Proceso carga pose_6d_estimation_640_400_byd.json; contiene
grasp_params.target_height=-1 (nombre real grasp_params) y depth_roi640×400
completa. No demostrado que depth_roi filtre selección ni que target_pose elija
caja en grasp. No se modifican por inferencia ni se publica una pose artificial.
PENDIENTE: confirmar objetivo y semántica soportada para selección en MetaClamp;
comparación con una sola caja visible aún no realizada.

Evidencia/capturas/config/contrato y backups: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260921T104532Z_BOX_SELECTION_CAPTURE`; SHA256SUMS.
Cambios locales: registro documental. Estado remoto: consulta perceptiva
terminada, sin publicación de movimiento, instalación ni reinicio.

### Confirmación del objetivo y preparación pendiente, 21-09

**CONFIRMADO por el operador:** objetivo = caja baja a la derecha en la imagen,
no superior de pila izquierda. Robot en HOME frente a las cajas en get1.
Biblioteca instalada de percepción contiene select_by_height/select_by_xyzCam/
select_by_xyzBox; ejemplos YAML de vision_aligned usan transport_type e id.
No se ha demostrado cómo aplicarlo a separate_box/transformación VISION de
Singapore/separate_right_cruzr; no modificar task_type ni copiar un selector
SPS por analogía. Inspección parcial del binario no constituye contrato validado.
Estimación offline usando X_WCamera redondeado del fallo y best.pose[1]:
XYZ≈[0.80016,0.09934,0.39364]m en W de Motion. No es medida nueva ni certifica
alcance; podría requerir ajustar geometría además de selección.

Preflight versionado `cruzr_blue_workbin_cycle.sh --check`: rc0,
20 actuadores habilitados, velocidad0, delta consigna máximo0.002876rad,
baterías82.6/81.7%, paros0/0, cargador desconectado, acciones disponibles.
HOME interno redescubierto body-first-v7-13s, hash
1e6e2fb7ddc598dc3793d093c283c82063507df0e53b70a18e161cab883a6f03;
no se ha ejecutado HOME ni cambiado la instalación en esta consulta.

Acción concreta preparada: `cruzr_blue_workbin_cycle.sh --prepare-vision`,
XML instalado cruzr/move_head_lower sólo MetaMove head0/−0.43rad en2s.
Requiere autorización de este movimiento y recorrido de cabeza libre,
sin otros mandos y supervisión junto al paro conforme a AGENTS.md.
Después consulta perceptiva, sin brazos/chasis/agarre. Todavía NO ejecutada.
No se ha desplegado filtro/ROI ni cambiado límites. Confirmar selección en
imagen fresca y validar semántica del selector antes de integración física.

## 2026-09-21 12:55 Europe/Madrid — BOX-01-SELECT: cabeza y detección real

**AUTORIZADO y VERIFICADO.** Operador confirma movimiento de cabeza y condiciones
presenciales. `scripts/cruzr_blue_workbin_cycle.sh --prepare-vision --yes`
repite preflight y termina0. 20 actuadores habilitados, velocidad0,
baterías82.3/81.5%, paros0/0 y cargador desconectado. Tarea
cruzr/move_head_lower, goal98529484-9024-4063-b073-2f59010c3ac9,
SUCCEED1101001/status4. Lectura posterior pitch−0.430473rad, yaw0.000096rad,
todas las velocidades medidas0. No se ordenaron brazos/chasis/agarre/HOME.
Cabeza queda bajada; NO se ha restaurado automáticamente a HOME.

Consulta transport/head/grasp, goal4b83c549-2b31-4325-b85f-a97602ff3fcf,
status4/okTrue/workbin/tres poses, stamp1789988110.746375. Candidata1 (índice
cero-based1) corresponde a caja baja derecha confirmada por operador:
XYZ cámara[-0.074134648,0.749307678,1.053508175]m,
Quaternion XYZW[0.851942738,-0.004945094,-0.012608065,0.523459792].
La primera sigue siendo superior izquierda, cámara[-0.693574,0.472225,0.915839].
Imagen segment.png coincide visualmente con esa disposición; su header tiene
stamp0, por lo que no se certifica sincronización exacta con el resultado.

**DESCARTADA para uso directo:** llamada perceptiva task_stage=select_by_xyzCam
con target_pose=candidata1 fresca. Goal4f371d45-b7ef-468f-8fd6-34b88b3b7c4a
aceptado, cliente timeout15s/rc124. Log Vision explícito:
`Warning: receive incorrect 'task_stage'`. No llamar esta etapa en el script.
Su presencia en las bibliotecas Motion no prueba soporte del servidor instalado.
No hubo orden mecánica en esta prueba. Se pidió cancelar SÓLO ese UUID mediante
/cv/task/transport_action/_action/cancel_goal: return_code1, goals_canceling[].
Cancelación rechazada, cierre del goal NO demostrado; consulta de status agotó6s.
No se reinicia Vision ni se reintenta para ocultarlo. No afirmar detección parada
por el timeout. Próxima intervención: verificar estado del servidor antes de
nuevas consultas/agarre. No se modificaron configuración persistente ni límites.

Efectos: cabeza bajada mediante tarea existente; procesamiento perceptivo y
archivos de diagnóstico automáticos del proveedor. Receta de movimiento:
--prepare-vision tras --check/autorización presencial. La medición válida es
transport/head/grasp con box_size0.603,0.397,0.22; no usar select_by_xyzCam.
Reversión física no automática: evaluar recorrido y autorizar recuperación de
cabeza cuando corresponda. Copias previas, imágenes, resultado completo y hashes:
`/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260921T105542Z_BOX_SELECTION_CAPTURE`. PENDIENTE: selección soportada dentro de MetaClamp y alcance de objetivo;
no se ha corregido ni probado el agarre entre múltiples cajas.

## 2026-09-21 13:03 Europe/Madrid — BOX-01-SELECT: pila apartada, objetivo primero

Operador confirma haber apartado la pila manteniendo robot/caja objetivo.
**VERIFICADO:** imagen nueva muestra pila aún visible a la izquierda pero más
alejada; en dos consultas transport/head/grasp consecutivas la primera pose
corresponde ahora a la caja baja derecha deseada. Devuelve5 y6 candidatos,
respectivamente; NO afirmar caja única detectada ni orden garantizado siempre.
Goals c1c845db-484e-4368-bacf-3f67fab1aab3 y
4d75e3e6-af25-42ca-a5b2-a8334abc649c: ambos status4/okTrue/workbin.
Primera pose cámara[-0.071954291,0.746086016,1.051233996]m;
segunda[-0.072050732,0.746880034,1.051008088]m, variación0.831mm.
Servidor presente1 y solicitudes grasp completas: funcionamiento de detección
normal recuperado/verificado sin reinicio. El cierre del goal inválido anterior
no se ha demostrado; no confundir con bloqueo actual de todas las consultas.

TF leído para RGB posterior (~10s), con postura inmóvil, sitúa la primera pose
en base_link[0.799790780,0.099928312,0.388816784]m; en base_footprint sólo
cambia Z a0.518816784m. Cabeza−0.430473rad; todas las velocidades0.
**INFERENCIA LIMITADA:** X alrededor de0.800m, junto al máximo0.8m del YAML;
el margen nominal0.21mm no es robusto y no debe interpretarse como certificado.
TF base_link no está demostrado idéntico al marco/calibración interno de Motion;
no llamar a este cálculo X_BaseBox medido ni atribuir Z a altura de apoyo.
Selección favorable no demuestra IK ni trayectoria válida para la caja baja.

No se ejecutaron movimiento, agarre, HOME, reinicios ni cambios de configuración.
Cabeza conserva postura bajada de la acción autorizada anterior. Consultas
perceptivas generan evidencia automática vendor. Punto de reanudación:
conservar nueva disposición, renovar detección antes de actuar; preparar ajuste
pequeño de aproximación para dar margen, condicionado a apoyo/espacio/estado físico,
y verificar de nuevo alcance/IK. No repetir el ciclo completo por este resultado.
Evidencia con imágenes, respuestas, TF y copias previas: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260921T110304Z_BOX_SELECTION_CAPTURE`; SHA256SUMS.
Receta de percepción: /cv/task/transport_action VisionActionTask,
transport/head/grasp, box_size0.603/0.397/0.22; ninguna llamada de movimiento.

## 2026-09-21 — BOX-01-FRONT: selección frontal solicitada

Operador aclara requisito: caja frontal aunque sea más baja que las laterales;
apartar la pila fue diagnóstico, no solución definitiva. Selector offline y
8 tests añadidos, sin ROS/movimiento. Rama nativa inspeccionada pasa índice0;
para cumplir requisito falta conectar la selección a la detección que realmente
consume MetaClamp, no basta modificar el wrapper o elegir índice1 fijo.
Fuente/receta/criterio/límites: [selección frontal](SELECCION_CAJA_FRONTAL.md).
Instalado/cargado/probado físicamente: NO; pruebas locales:8 correctas y
replay aproximado elige caja baja derecha. No modifica prioridades en robot.
Destino local scripts/box_handling/select_front_box.py y test asociado;
stdlib Python, sin dependencias nuevas. Reversión: retirar esos archivos y sus
referencias documentales; no requiere rollback remoto. Scripts originales intactos.
Backup documental, binarios leídos, hashes y replay: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260921T110500Z_FRONT_BOX_SELECTION`.
PENDIENTE: enlace nativo/adaptador por tarea, frescura/TF, alcance/IK y ensayo.


## Reanudación frontal tras OFF — 2026-09-22 09:46 CEST

COMM-01 y recuperación ya verificadas; esta intervención continúa el alcance.
Desde HOME la consulta perceptiva terminó sin resultado válido (status4/oktrue
no confirmado por validador), no se interpreta como pérdida global de visión.
Tarea existente de cabeza leída y hash
`f3a73626f97b471d4a0a03c98c24de32243651116c497328e69b5ddc57ea46c1` comprobado.
`front_box_integration.py --check-runtime` rc0 antes del movimiento.

Receta ejecutada, sin editar archivos del robot ni instalar tareas:

```bash
# Requiere autorización y condiciones físicas actuales:
bash scripts/cruzr_blue_workbin_cycle.sh --prepare-vision --yes
# Dos consultas posteriores, secuenciales; no hacen trayectorias:
./scripts/force_escenario1.sh --check-front
./scripts/force_escenario1.sh --check-front
```

Sólo el primer comando mueve: cabeza, no brazos/chasis. Usa preflight completo
sin --fast; baterías61,3/62%, paros0/0, cargador desconectado, acción libre.
Postura final leída por ActuatorState: pitch−0,430473rad, yaw−0,000479rad;
velocidad0, delta consigna máximo0,000959rad; MEASURED_HOME=0 debido a cabeza.
No se devuelve automáticamente a HOME junto a las cajas. Reversión física
requiere su propia comprobación de recorrido; no se ha ejecutado.

Consultas de visión posteriores:8b70aa1b9d0d4667a757c9177e5a1fa0 y
4c7179c3a2be4d37a414748546a5eb1e, resultado válido, índice1 en ambas.
Primera captura stamp1790062872.809780000; imagen `_action_grasp.jpg` leída
de Vision y conservada como `current-grasp.jpg`, procedencia en image-paths.json.
Coincide etiqueta frontal cámara≈[−0,077;0,750;1,054] y caja baja de la derecha.
Poses base_link y TF exactas completas en ambos JSON. Diferencia entre muestras
3.007mm. Son estimaciones TF; Motion
usa su cinemática propia y no debe equipararse el último milímetro al umbral.

No enviar de nuevo el mismo agarre esperando que SHM arregle alcance: fallo
anterior también incluía IK. Desplazar idealmente el chasis5cm al frente daría
X≈0,748–0,751m y dejaría Z igual; **hipótesis geométrica, no IK ni trayectoria
aprobadas**. Primero comprobar espacio físico y ruedas, preparar localización
y ejecución acotada con parada/lectura, y volver a medir. No alterar get1 guardado
ni ampliar límites para ocultar el problema. No se han cambiado mapa, modo,
controladores o parámetros, ni enviado avance, retirada o agarre.

Evidencia/backups/recetas de consulta/hashes: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260922T073932Z_FRONT_REACH_RECHECK`.
El intento local de `probe_front_box.py --help` carecía de rclpy en PC; las
consultas reales usaron el wrapper que lo ejecuta en ROS2 del robot. Sin
instalaciones PC ni remotas por ese intento. Cambios locales sólo documentales.


## Ensayo supervisado de objetivo frontal5cm — 2026-09-22 09:55 CEST

Autorización: operador responde «Sí, espacio libre y ruedas en modo navegación»
a la propuesta de avance5cm, incluyendo apoyos y persona junto al paro.
No requiere ni ejecuta agarre. Se conserva el objetivo del usuario de recoger
la caja frontal baja entre laterales; este ensayo no ha resuelto el alcance.

Fuentes nuevas PC, sin instalación permanente en robot:

- [prepare_front_map.py](../../scripts/box_handling/prepare_front_map.py): ejecutado
  por stdin en ROS2 de Motion, comandosget_map_name/check_state, map_set y
  relocation_start global sobre utars_nav_map. No edita get1/put1 ni publica
  velocidad. La localización nativa puede mover la cabeza: se observó su retorno
  desde−0,43 a≈0 antes de la navegación; no calificar la preparación como
  completamente inmóvil. Goalmap8861504c7a5d4328952116c58f0db9e5;
  relocalización27e937a4cbb9448784087abe4a9145d9, ambosstatus4.
- [front_nudge.py](../../scripts/box_handling/front_nudge.py): --check rc0;
  objetivo desde pose fresca, avance geométrico0,05m/rumbo conservado, velocidad
  solicitada0,03m/s y0,05rad/s. Observa mapa, odometría, salud20D, postura, paros
  y cargador. Solicita parada por desvío, retroceso, pérdida de datos o error.
  No publica cmd_vel ni modifica tolerancias/anticolisión del proveedor.
- [test_front_nudge.py](../../scripts/box_handling/test_front_nudge.py): tres
  pruebas offline de transformación del objetivo, rechazo de desvíos/valores
  inválidos y bloqueo de repetición tras el resultado real. Sintaxis/diff pasan.

`--run` se ejecutó UNA vez tras check y preflight completo (baterías59,7/60,8%,
paros0/0, cargador desconectado, acción libre). Objetivo exacto:
X0,0422561000196/Y0,650751397548/yaw−3,08746363803rad en mapa; pose inicial
X≈0,092183/Y≈0,653457 con ese rumbo. Odom inicial≈(0,0,0).
Distancia frontal solicitada5cm, no desplazamiento realizado.

Navigation_start goal27028c333b0c450ea296ff577d3c38bc aceptado.
Al medir avance−0,005110m, lateral0,000002m, yaw−0,000092rad, el monitor aborta
y envía navigation_stop goale2399f82497047bd8256951862757aed. Resultado
status4/dmsg navigation_stop SUCCEEDED; desc auxiliarVSLAM_LOCATION_LOST.
El log del planificador confirma CANCEL1214108. Después se midió odom
stamp1790063495.648669691: X−0,007503082738m, Y0,000000948m, yaw≈0,000462rad,
twist0. Muestra20D habilitada/sin faults, máxima posición y delta0,000959rad,
velocidad0, MEASURED_HOME=1. La respuesta del stop por sí sola no se tomó como
prueba de inmovilidad; se hizo lectura independiente.

Causa acotada al registro: MPPI declaró alcanzado el destino con5cm restantes
porque level1 tiene tolerancia0,3m; después pasó a ArcPreciseController con
allow_backward=true. Éste registra pose−176,9°, objetivo frontal5cm y
x_tilt−0,05, e inicia salida x−0,04m/s. La distancia al objetivo sube
0,050→0,054m antes de cancelar. No fue un problema del selector de cajas.
No se ha demostrado si es un defecto, una convención o una fase del algoritmo;
no afirmar una reparación cambiando el signo o inventando un parámetro.
La velocidad solicitada no demuestra un techo efectivo en este controlador.

**Estado vigente del helper:** RUN_QUALIFIED=False, --run rechaza antes de
importar ROS/conectar. Sólo --check utilizable para lectura. La versión exacta
ejecutada se conserva en evidencia como nudge-executed.py y su checksum; no
reusarla para otro ensayo. Punto de reanudación: revisar contrato de navegación
precisa/admitir un método de aproximación adecuado, volver a medir la caja y
validar IK; ningún reintento autorizado implícitamente por este informe.

Reproducción de lectura, desde PC con SSH habitual y entorno ROS del contenedor:

```bash
# Lectura únicamente; no instala el helper:
ssh walker@192.168.11.2 \
  'docker exec -i walker-ros.ros2-1 bash -lc "source /opt/ros/humble/setup.bash; export ROS2CLI_DISABLE_DAEMON=1; timeout 50 python3 - --check"' \
  < scripts/box_handling/front_nudge.py
```

La preparación del mapa se transmite de igual forma usando prepare_front_map.py
sin --check, pero **cambia estado de navegación y puede mover la cabeza**; no
ejecutarla como consulta ni por rutina ahora que el mapa está localizado.
No se guardaron cambios de waypoints, configuración, límites ni SDK.
El cambio de estado persistente en ejecución es mapa cargado/localizado y pose
desplazada7,5mm atrás; no hay rollback físico automático. Documentación/fuentes
PC se revierten selectivamente desde before/ (fuentes nuevas identificadas),
sin sobrescribir otros cambios. Mapaypostura se conservan hasta una operación
autorizada posterior; no restaurar a ciegas el estado sin mapa.

Evidencia completa y SHA256SUMS: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260922T073932Z_FRONT_REACH_RECHECK`.
Incluye confirmación presencial, before/after, respuestas map/localización,
versión ejecutada, plan y progreso del objetivo, stop, lecturas posteriores
y logsfreepnc. No se mandó nueva detección ni cabeza tras el fallo del avance.
