# get1 guardado y ejecutor get1 → put1 → HOME

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
