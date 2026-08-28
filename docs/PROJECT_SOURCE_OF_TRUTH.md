# Cruzr S2 — fuente de verdad global del proyecto

**Última actualización:** 28 de agosto de 2026
**Unidad:** Cruzr S2, SN `WAE001UBT60000669`  
**Propósito:** relevo técnico y operativo entre sesiones, personas y agentes

Este documento es el índice vivo del proyecto completo. Conserva el estado
conocido del robot, las modificaciones persistentes, lo que ya funciona, los
bloqueos y el punto de reanudación. No sustituye las guías especializadas ni
certifica el estado físico actual.

`AGENTS.md` obliga a Codex a leer esta fuente al iniciar una sesión desde el
repositorio. Si se modifica aquí una condición material, debe actualizarse
también la fuente especializada enlazada.

## 1. Cómo interpretar el documento

- **VERIFICADO:** demostrado en esta unidad mediante estado, archivos, hashes,
  logs, topics, servicios o una prueba controlada.
- **OBSERVADO:** visto durante una prueba, pero sin causa interna totalmente
  demostrada.
- **INFERENCIA:** explicación compatible con la evidencia que requiere otra
  prueba o confirmación del proveedor.
- **PENDIENTE:** no probado, no resuelto o no contestado por DSA/UBTECH.
- **DESCARTADO:** hipótesis o workaround contradicho por la evidencia.

Una observación histórica no autoriza movimiento. Al retomar, comprobar de
nuevo el estado físico y lógico.

## 2. Relevo vigente

### 2.1 Último estado conocido

| Elemento | Último estado documentado | Confianza |
|---|---|---|
| Postura | el propietario informa robot encendido y en `home`. El check fresco de sólo lectura confirmó Motion disponible, acciones listas y no envió movimiento, pero no pudo certificar la postura 20D porque la muestra de actuadores omitió `2001/2002/2003/3001` | **ESTABLE SEGÚN OPERADOR; HOME LÓGICO NO VERIFICADO** |
| Modo robot | Motion/Vision accesibles, máquina de tareas desbloqueada y sin módulo activo; no se consultó/cambió el modo de trabajo ni se inició cliente físico | **ENCENDIDO; MODO NO INFERIDO** |
| Efector | abrazaderas, `HW_TYPE=cruzr_s2_v1` confirmado por el check fresco | **VERIFICADO POR SOFTWARE; VACÍO DEBE RECONFIRMARSE ANTES DE MOVIMIENTO** |
| Actuadores | `ACTUATORS_OPERATION_ENABLED=1` y acciones `ready`, pero el gate de postura rechazó la muestra incompleta por faltar `2001/2002/2003/3001`; no se envió goal ni se diagnosticó la causa de esas ausencias | **MOVIMIENTO NO AUTORIZADO; COMPLETAR MUESTRA 20D** |
| Teleoperación PC | combinación oficial robot v0.2.0 + controller 4.7.0 + UI 4.1.0, overlay `clamp,0,0` y control bimanual. La sesión 10:25 terminó por protección FT, no por VR. Tras el reinicio el robot quedó en `AutoTaskMode`; no se ha recargado ni reanudado PICO | **BLOQUEADA HASTA NUEVO PREFLIGHT Y CAMBIO DE MODO AUTORIZADO** |
| Servicio PC/PICO | el STOP oficial tras `Ctrl+C` quedó confirmado; PC permaneció encendido durante el power cycle del robot | **STOP VERIFICADO; SIN CLIENTE FÍSICO** |
| VLA | contenedores detenidos, `restart=no`, sin mando físico | **VERIFICADO** |
| Cargador | `disconnected` en el check fresco | **VERIFICADO POR SOFTWARE** |
| Paros, ruedas y zona | ambos paros reportaron `0`; zona, ruedas y persona junto al paro no se verificaron porque sólo se hizo diagnóstico VLA/home de lectura | **RECONFIRMAR FÍSICAMENTE ANTES DE CUALQUIER MOVIMIENTO** |
| Mapa/localización | `test_route_01` se conservó; activación y localización son volátiles | **RECOMPROBAR** |

La rama `main` estaba limpia y sincronizada con `origin/main` en el commit
`4536f8a` antes de crear esta fuente global. El estado Git actual prevalece
sobre esa referencia.

El 28-08 se endureció localmente return-to-home mientras el robot permanecía
completamente apagado. El script no mueve ya sin `--run`, mide los 20 ejes,
trata todo inicio de home como no confirmado hasta observar las posiciones,
bloquea PICO/unknown/fuerza/autocolisión/fault y restringe la tarea vendor a
estados del ciclo de caja. `--force-held-home` quedó retirado y `--fast` ya no
omite gates. Las regresiones locales pasaron; **no existe aún validación física
de la ruta revisada y este cambio no modifica el estado apagado vigente**.

### 2.2 Primeros pasos de la siguiente sesión

Sin mover el robot:

```bash
git status --short --branch

# Elegir sólo los diagnósticos relacionados con la tarea.
./scripts/cruzr_blue_workbin_cycle.sh --check
./scripts/cruzr_blue_workbin_table_transfer.sh --check --fast
./scripts/teleoperation/cruzr_pico_teleop_pc.sh --check
./scripts/vla/run_ubtech_vla_shadow.sh --status
```

El diagnóstico de teleoperación exige que estén presentes los enlaces que
pretende comprobar; no debe interpretarse un fallo por PICO desconectado como
un defecto nuevo del robot. Consulte siempre `--help` antes de usar modos de
movimiento o recuperación.

## 3. Inventario técnico consolidado

### 3.1 Robot y red

| Componente | Valor conocido | Estado |
|---|---|---|
| Modelo | Cruzr S2 | **VERIFICADO** |
| Número de serie | `WAE001UBT60000669` | **VERIFICADO** |
| Software | genérico `v0.2.0` en Motion y Vision | **VERIFICADO** |
| Motion | Ubuntu 22.04, `192.168.11.2` | **VERIFICADO** |
| Vision/web | `192.168.11.3` | **VERIFICADO** |
| PC Ethernet | `eno1`, perfil `cruzr-s2`, `192.168.11.250/24`, autonegociación, 1000 Mb/s full, never-default; Motion/Vision directos | **VERIFICADO; PREFERIDO PC→ROBOT** |
| PC Wi-Fi Internet | `wlo1`, `DSA CORPORATE`, `192.168.40.120/24` | **VERIFICADO; CONSERVAR** |
| PC Wi-Fi robot/PICO y fallback | `wlx80afcad40bd6`, `Cruzr S2-0669`, `192.168.42.215/24`; `.42.0/24` directa y fallback `.11.0/24` vía `.42.2`, never-default, sin DNS y `powersave=disable` | **VERIFICADO; VIGILAR RESET USB REALTEK** |
| PICO Wi-Fi local | `Cruzr S2-0669`, `.211` el 25-08 y `.212` el 26-08 | **VERIFICADO; DHCP, REDESCUBRIR** |
| Efector actual | abrazaderas | **VERIFICADO** |
| `HW_TYPE` | `cruzr_s2_v1` | **VERIFICADO** |
| `TELE_DEVICE` | `pico` | **VERIFICADO** |
| `transmit` | `local` | **VERIFICADO** |
| `MC_SCENE` | vacío en contenedores inspeccionados | **VERIFICADO; DIFERENCIA CON SOP** |

Las credenciales del robot no se versionan. Las rutas Wi-Fi pueden diferir de
las rutas Ethernet; deben descubrirse en cada sesión.

### 3.2 Efectores

- Las abrazaderas son el efector operativo actual. La configuración coherente
  es `HW_TYPE=cruzr_s2_v1`.
- Las manos v4 se instalaron físicamente, se detectaron mediante
  `/mc/left_hand/joint_states` y `/mc/right_hand/joint_states`, y se probaron
  tareas de fábrica. Después se retiraron y se restauraron las abrazaderas.
- Con manos v4 se observó `HW_TYPE=cruzr_s2_v1_sps`. No reutilizar ese valor
  con abrazaderas.
- Las demostraciones de manos son trayectorias fijas, no manipulación autónoma.
  La coreografía de corazón requirió iteración y llegó a dejar un dedo en
  contacto con el torso; no debe ejecutarse desde una postura desconocida.

Guía: [`../scripts/hands/README.md`](../scripts/hands/README.md).

### 3.3 Mapa, estaciones y referencias

- Mapa: `test_route_01`.
- Waypoints conocidos: `START`, `PASO1`, `PASO2`, `PASO 3`, `PASO4`,
  `FINISH`, `MESA2_PRE`.
- La misión mesa 1 → mesa 2 no necesita pasar por `PASO1`; el destino global
  es `MESA2_PRE`, seguido de alineación local.
- AprilTag mesa 1: ID 112, familia `tag36h11`, lado negro medido 75 mm,
  `tag_size=0.075`; uso opcional.
- AprilTag mesa 2: ID 113, familia `tag36h11`, lado negro medido 73,5 mm,
  `tag_size=0.0735`; referencia del depósito.
- El tag 113 se detectó con márgenes de decisión altos y medidas estables. Hay
  referencias separadas para robot vacío y con caja sujeta porque la postura
  de transporte cambia la transformación cámara-tag.
- Activar el mapa no equivale a estar bien localizado. Después de un arranque,
  actualización o movimiento manual hay que validar la pose contra el entorno
  LiDAR antes de navegar.

Guía y valores completos:
[`guides/TRANSFERENCIA_CAJA_ENTRE_MESAS_CON_APRILTAG.md`](guides/TRANSFERENCIA_CAJA_ENTRE_MESAS_CON_APRILTAG.md).

### 3.4 Caja de ensayo y carga

- Contenedor azul de plástico, aproximadamente `600 × 400 × 220–230 mm`.
- Las pruebas descritas se hicieron con la caja vacía o ligera.
- DSA/UBTECH indicó por chat una carga útil máxima bimanual de 20 kg y un rango
  recomendado de 10–15 kg. Es una afirmación del proveedor, no una curva de
  payload validada para cualquier alcance, centro de gravedad o aceleración.
- No extrapolar las pruebas de caja vacía a carga industrial sin commissioning
  mecánico y límites documentados.

## 4. Cambios persistentes realizados en el robot

### 4.1 Actualización v0.2.0

**VERIFICADO:** se aplicó el paquete offline genérico v0.2.0 en Motion y
Vision. Antes se respaldaron configuraciones y mapas. El flujo estándar
`udoke replace` no recibió `upload-confirm` en tres intentos, por lo que se
aplicó el fallback manual incluido en el SOP: preinstalación, sustitución de
configuración, despliegue uDoke y postinstalación.

Se preservaron:

- mapa `test_route_01` y su checksum;
- configuración de abrazaderas `HW_TYPE=cruzr_s2_v1`;
- acceso web, navegación, manipulación y visión.

Detalles y reporte al proveedor: [`../upgrade.txt`](../upgrade.txt) y
[`../upgrade_summary.txt`](../upgrade_summary.txt).

### 4.2 Servicios estabilizados tras la actualización

- `main.x86` y `main.orin`: plantillas sin comando que reiniciaban en bucle;
  se dejó su reinicio automático deshabilitado.
- Cliente MQTT cloud: se bloqueaba con `segmentation fault` en el callback de
  batería; se dejó detenido y sin reinicio automático. El MQTT local/upilot
  permaneció estable.
- Netdata Vision: contenedor activo pero health check local de `19999` no
  saludable; pendiente de corrección oficial.
- Frecuencia GPU Vision: el script oficial informó 1,224 GHz frente a objetivo
  1,122 GHz; pendiente de confirmación del proveedor.

Estos cambios son workarounds locales y deben revisarse después de cualquier
actualización oficial.

### 4.3 Guard de arranque v0.2.0

**VERIFICADO:** Vision arrancaba Control Center antes de que Motion ofreciera
servicios x86 funcionales. El self-check fallaba, la cara quedaba roja y la
cabeza baja. Se instaló en Vision un guard reversible que:

- espera versión exacta v0.2.0 y servicios Motion funcionales;
- exige respuestas reales de self-check y muestras de las seis cámaras;
- sólo recupera el patrón `Fault` conocido con paros/cargador seguros;
- reinicia Control Center una vez, exige `StartMotion` y `JoystickMode`;
- devuelve la cabeza a la tarea oficial de home.

Archivos instalados en Vision:

```text
/usr/local/sbin/cruzr-v020-boot-guard
/etc/systemd/system/cruzr-v020-boot-guard.service
/usr/local/share/doc/cruzr-v020-boot-guard.md
```

Guía, comprobación y rollback:
[`guides/CRUZR_V020_BOOT_GUARD.md`](guides/CRUZR_V020_BOOT_GUARD.md).

### 4.4 VLA suministrado

**VERIFICADO:** se instalaron las imágenes, workspaces y
`checkpoint-40000` suministrados. Los dos contenedores se mantienen detenidos
con `restart=no`.

Se añadió un overlay local para:

- usar el perfil S2 correcto de 20 ejes;
- leer `/mc/whole_joint_states` como fuente read-only, porque
  `/mc/sdk/robot_state` no entregaba muestras;
- montar la variante GR00T suministrada y los metadatos de inferencia;
- validar chunks sin importar ni publicar `RobotCommand`.

La inferencia shadow produjo chunks finitos de forma esperada y confirmó cero
publicadores en `/mc/sdk/robot_command`. Desde `home`, los chunks se rechazaron
por diferencias de hasta aproximadamente 1,35 rad en ocho articulaciones. No
se habilitó movimiento VLA.

El 2026-08-28 se ejecutó task 0 otra vez desde una postura/escena viva no
documentada, por lo que el run se clasifica `OOD_RUNTIME_SMOKE`, no prueba
nominal. Generó dos chunks y el validador rechazó ambos por siete saltos del
primer punto; el máximo fue `R_shoulder_yaw_joint=1,339886 rad` frente a
`0,35 rad`. El goal solicitado por 8 s concluyó en `10,063076 s`, al terminar
el ciclo de inferencia en curso. STOP dejó ambos contenedores `exited` y cero
publicadores. Los logs se recuperaron de los contenedores detenidos en
`Humanoide-vla-evidence/20260828T080202_E2.0_recovered/`. Estado:
`PASS_SHADOW_SAFETY_ONLY`; E1.0/E1.3 y la validación de task siguen pendientes.

El 2026-08-28 se implementó y ejecutó E2.2 para PLACE sin utilizar el robot.
`run_vla_offline_place_e2_2.sh` creó un contenedor NVIDIA transitorio en Vision
con red desactivada, sin ROS ni `RobotCommand`, y cargó el checkpoint una sola
vez. El run válido `20260828T112730_E2.2` reprodujo task 1/episodio 465 y task
3/episodio 265 desde frame 0: salidas 10×20 finitas, MAE `0,007283609` y
`0,011394879`, sin violaciones de rango ni de primer salto. El split es el
último 15 % estratificado definido por el proyecto; el dataset sólo declara
`train`, por lo que no prueba generalización ni exclusión del entrenamiento.
`meta/info.json` anuncia `frame_index`, pero los parquets inspeccionados lo
omiten; se usó índice de fila únicamente tras validar task, episodio y la línea
temporal exacta a 120 Hz. Los dos intentos previos fallaron antes de inferencia
y quedaron documentados. La limpieza de JSON root-owned se corrigió y el
residuo temporal se retiró. Hashes de evidencia válidos; estado final
`exited/exited/publishers:0`, sin leer estado ni ordenar movimiento físico.

La evidencia VLA ya no depende de variables exportadas por un bloque anterior.
`new_vla_evidence_run.sh` crea cada run de forma exclusiva y rechaza `/` y
rutas existentes. E1.1/E1.2, los smoke E2.0/E2.1 y las repeticiones E2.3 tienen
wrappers autocontenidos; E2.3 usa sesiones independientes y STOP entre runs.
E2.2 dispone ahora de evaluador y wrapper autocontenidos. Los ejemplos aún no
implementados de E3.2, E4.1, E5.1/E5.2 y VLA-T00…T09 inicializan su directorio
en el mismo bloque. Las herramientas de evidencia son cambios del
PC/repositorio; E2.2 sólo arrancó un contenedor offline transitorio en Vision y
no alteró Motion ni los contenedores VLA persistentes.

El paquete local sí contiene
`codes-S2/motion/s2_vla_scripts/s2_bio_vla/s2_vla_pick_large_teleop_ready.xml`,
hash `f4025124…d8323`. Preposiciona cintura, cabeza y brazos, pero termina
llamando a `clamp_s2_joints_trajectory`, cuya definición/instalación no está
demostrada. El SDK 7.3 confirma B0 `60×40×22 cm` sobre plataforma de **1 m de
altura** y sólo pide mover el robot a una posición adecuada; no proporciona
distancia horizontal.

Se extrajeron de sólo lectura 12 frames —inicio/medio/final de los episodios 0,
1, 90 y 91— con VLC. La referencia visual es un tote rígido gris abierto de
paredes altas y borde gris, con tiras/marcas negras estrechas en algunos frames
y un pequeño elemento con lazo visible dentro, no una caja de cartón cerrada.
Por ello `B0_SAFE` vacía puede servir para canary, pero es OOD si no
reproduce esa apariencia/contenido.

El siguiente bloque de trabajo VLA está planificado al principio de
[`plan_de_trabajo.md`](plan_de_trabajo.md): auditoría offline, contrato temporal,
posturas `VLA-ready`, ejecutor sink, matriz shadow de 4 tasks × 8 perfiles
funcionales (`P14`…`P20`), canary progresivo y comparación del checkpoint
intacto frente a continuación o nuevo DataConfig. Se añadieron tarjetas
`VLA-T00…T10` con fixture, estado inicial, comandos/mensajes PC, PASS/FAIL,
evidencia y recovery: `B0_SAFE` `0,603 × 0,397 × 0,217 m`, plataforma inicial
a 1 m de altura confirmada por SDK y pose medible en `PLATFORM_FRAME`. Los niveles
low/middle y la distancia horizontal no están confirmados, y el plan no
autoriza movimiento. Las tarjetas
físicas permanecen bloqueadas hasta demostrar `VLA_READY`, ejecutor canary y
primitiva de trayectoria. El manual operativo al inicio del plan ordena los
experimentos `E1.0…E8.2`: montaje medido, baseline, primera inferencia, OOD,
ready, perfiles 14–20, canary, cuatro tareas físicas y evolución C1/C2. Para
experimentos 1–3 mantiene plataforma/B0 fuera de la envolvente; el 1 m es
altura de plataforma, no separación. `platform_in_base` sigue sin definirse.

Fuente: [`guides/CRUZR_S2_VLA_SAFE_ENABLEMENT.md`](guides/CRUZR_S2_VLA_SAFE_ENABLEMENT.md).

### 4.5 Teleoperación del robot

Se verificaron `TELE_DEVICE=pico`, `transmit=local`, `signal_server`,
`rtm_receiver` y la tarea
`teleoperation/cruzr_clamp_pico_teleoperation`. No se renombraron topics,
colas o servicios del robot.

`walker28` es exclusivamente el `channel_name` del backend PC. El nombre
`walker28_web` no se encontró en el frontend ni en el sistema inspeccionado.

### 4.6 Tareas auxiliares y scripts

El repositorio contiene XML auxiliares y scripts para brazos, voz, manos,
cajas, navegación, recovery, VLA y teleoperación. Algunos scripts pueden
instalar tareas versionadas en el árbol de manipulación del robot antes de
ejecutarlas; su presencia debe comprobarse mediante los modos `--check` y los
hashes incorporados. No asumir que una tarea local está instalada tras una
actualización.

Los scripts se migraron a los nombres de imágenes/tareas observados en v0.2.0.
La migración se validó sin instalar tareas nuevas ni mover el robot.

## 5. Cambios persistentes en el PC de teleoperación

### 5.1 Paquetes instalados

- XRoboToolkit PC Service `1.0.0.0` para Ubuntu 24.04.
- `ubt-controller` `4.7.0` entregado por UBTECH para el robot v0.2.0 e
  instalado el 26-08; binario oficial sin parches `e88b83b7…`.
- `ubt-remote-control` `4.1.0`.
- ADB y regla udev para PICO.
- Servicio systemd `/etc/systemd/system/ubt-controller.service`.

Instaladores grandes y SOP se mantienen fuera de Git; sus hashes están en la
fuente de teleoperación y en [`../utats/README.md`](../utats/README.md).

### 5.2 Configuración y workarounds PC

- Ruta preferida PC → Motion/Vision por Ethernet `eno1`/`.11.250`, 1 Gb/s;
  Wi-Fi Cruzr conserva PICO, `.42.0/24` y el fallback `.11.0/24` vía `.42.2`.
  Ambas son never-default; Internet continúa exclusivamente por DSA.
- Backend con `transmit=local`, señalización
  `ws://192.168.11.3:4000`, `channel_name=walker28`, dispositivo PICO y
  `enable_foot_switch=1` restaurado por 4.7.0, pendiente de aclaración.
- Los tres parches diagnósticos de 5.3.0 —`GRIPPER→CLAMP`, gatillo izquierdo
  como Y por flanco y timeout heartbeat 300 s— ya no están instalados. 4.7.0
  usa el binario exacto del DEB del proveedor y su watchdog por defecto.
- `arm=clamp` se conserva como variable systemd del PC; `LC_NUMERIC=C` evita
  diferencias locales de separador decimal sin modificar el ejecutable.
- 4.7.0 instala además el cliente oficial `/usr/local/bin/pico_control`
  (`46323392…`), cuya ayuda admite `--arm_type clamp`. No se ejecutó porque
  puede iniciar el flujo de control; el preflight sólo verifica hash y ayuda.
- La instalación 5.3.0 parcheada, configuración, units y backups quedó
  archivada en
  `/home/lacuna/Descargas/ubt-controller-5.3.0-patched-20260826.tar.gz`
  (SHA-256 `c085fc4b…`). El DEB original 5.3.0 se conserva fuera de Git.
- El preflight de teleoperación muestra ahora siete etapas con timestamp y
  timeouts de 5 s para ADB/systemd/journal/WebSocket. La variable
  `CRUZR_TELEOP_DEBUG=1` activa traza Bash con línea y comando; los fallos del
  gate informan el punto exacto antes de solicitar STOP.
- Se mejoró orden de arranque: servicio XR y PICO antes del backend; UI al
  final. Una desconexión/suspensión del visor puede exigir reinicio del
  servicio.
- El lanzador descubre ahora el mismo visor por `ro.serialno` tanto si ADB usa
  el serial USB como si usa un destino `IP:puerto`; `PICO_ADB_TARGET` permite
  fijar el transporte para diagnóstico. No se cambió ninguna ruta de mando.

El binario original permanece respaldado; los hashes original y activo están
en la fuente especializada.

### 5.3 Último estado PC

El 26-08 quedó activo `ubt-controller 4.7.0`, listener 8082 y XR Service 63901;
la UI está inactiva. PICO mantiene el flujo USB `192.168.51.220` →
`192.168.51.42:63901` y `vr_status=1`. El cliente oficial se ejecutó una vez
con timeout y `--arm_type clamp`: Y produjo `Left.b_button=true` y el callback
`tele_operation enable=1`; el grip derecho llegó al backend. Sin embargo, el
backend registró `Arm type is: gripper`. El propietario acepta temporalmente
esa diferencia sólo para cinemática de brazos y prohíbe inferir equivalencia
para mandar el efector. `pico_control` confirmó STOP/`operation_type=1`. El
rearme observado un segundo después no fue espontáneo: un segundo cliente
diagnóstico `wscat --wait 1` permaneció conectado después de enviar STOP y el
backend autoarrancó al detectar cliente + PICO online. El STOP canónico corto
lo dejó después en `operation_type=1`, cliente terminado y articulaciones
inmóviles. No mantener otro WebSocket abierto después de STOP.
La concesión Wi-Fi observada del PICO cambió a `.42.212`, como corresponde a
DHCP. Tras sustituir el cable, Ethernet negocia 1000 Mb/s full y Motion/Vision
responden directamente desde `.11.250` en 0,2–0,9 ms; Wi-Fi Cruzr queda activa
para PICO/fallback y `DSA CORPORATE` mantiene la ruta por defecto de Internet.

El estado 5.3.0 con `vr_status=1`, `enable_control=0` y el backend parcheado
`5083e9f0…` queda como evidencia histórica del 25-08, no como estado activo.

El 27-08 se verificó en Motion que la tarea
`teleoperation/cruzr_clamp_pico_teleoperation` carga `Hand type: clamp`, pero
el YAML vendor activa cuerpo completo con `waist_mode=1` y `leg_mode=2`.
Durante la sesión problemática ambos grips quedaron simultáneamente altos y
el solver registró fallos de alcance repetidos; el torso/elevador compensó en
CoreMode 7. Se instaló de forma reversible un overlay que cambia únicamente
esos dos modos a cero, SHA-256 `4e8d79a4…`, conservando clamp, brazos,
anticolisión y umbrales de fuerza. El backup vendor `5f08b30c…` y el overlay
persisten en Motion bajo `$HOME/.local/share/cruzr-pico-arms-only/`. El overlay
se recargó después y el último baseline conocido quedó
`ARMS_ONLY_LOADED=hand:clamp,waist:0,leg:0`.

El 28-08 se añadió `scripts/teleoperation/probar_pico_full.sh` como lanzador
separado, dejando `probar_pico.sh` sin cambios. Puede preparar el rollback
exacto al YAML vendor y sólo permite START full-body si demuestra hash
`5f08b30c…` más tarea viva `clamp,waist=1,leg=2`; exige Wi-Fi sin Ethernet
sujeto al robot, conserva los gates oficiales y añade STOP ante clicks de
protección, fallos IK, sobreesfuerzo, EtherCAT o pérdida del monitor Motion.
La preparación, recarga de TeleopMode y movimiento son pasos separados. El
cambio quedó validado localmente y con checks de sólo lectura: el full rechazó
correctamente el hash activo `4e8d79a4…` y el original confirmó
`ARMS_ONLY_LOADED=hand:clamp,waist:0,leg:0`. **No se restauró ni cargó el perfil
full, no hubo START ni movimiento**. El primer `--prepare-full` real del
28-08 a las 09:48 superó el preflight Motion, pero abortó antes del rollback:
el comprobador pasivo intentaba asignar temporalmente la constante shell
`readonly BACKEND_LOG`, por lo que Python no recibió la ruta. Se corrigió usando
el nombre de entorno independiente `BACKEND_LOG_PATH`. La reproducción de sólo
lectura devolvió `PASSIVE_OPERATION_TYPE=1` y el check posterior volvió a
demostrar `clamp,waist=0,leg=0`; por tanto no hubo cambio parcial.

Más tarde, tras una sesión PICO, `cruzr_recover_to_home.sh --run --yes`
clasificó correctamente `teleoperated_pose` y lanzó la tarea vendor verificada
`cruzr/open_arm_before_home`. Su primera fase no es una separación cartesiana
condicionada por postura: manda en paralelo ambos brazos a objetivos articulares
intermedios, y también cintura/elevador a cero. Desde la postura cruzada real,
Motion registró primero anticolisión torso–codo/muñeca izquierda durante el
final de teleoperación y, ya en recovery, `Force-X=-370,944 N` en el FT
izquierdo. El brazo derecho y cintura terminaron; el izquierdo falló con
errores articulares grandes y el elevador abortó. La acción acabó
`MoveToGoalFailed`, state `7104050`, `status=6`. Después 4004, 4003 y 4002
registraron `0x1003`/`Operation disabled unexpected:0x123f`; `hw` y
`manipulation_robot_app` reiniciaron. Con el paro accionado, rosa_control espera
`/mc/rosa_control/start`, `/mc/actuator_state` tiene cero publicadores y la
acción de manipulación cero servidores. **DESCARTADO** usar
`open_arm_before_home` como retorno universal desde cualquier postura PICO.
No se liberó el paro, rearmó, reinició, cambió modo ni envió otro movimiento
durante el diagnóstico; el siguiente paso requiere confirmación física fresca
y, si procede, apagado completo controlado, no otra trayectoria.

El operador confirmó después paro accionado, brazo izquierdo apoyado sin
presión apreciable, robot/brazos estables, abrazaderas vacías, cargador fuera,
zona de descenso despejada y persona junto al paro. La solicitud oficial
`/emb/pm_shutdown` con `confirm-to-shutdown` respondió `success=True`; Motion y
Vision pasaron de accesibles a no responder. Tras confirmar físicamente
pantalla y luces apagadas, el operador pulsó `KEY1` y luego apagó el chasis.
Estado final: indicador verde apagado, hosts sin respuesta, robot y brazos
estables. No se liberó el paro, rearmó ningún servo ni se envió otra
trayectoria. Los faults y consignas deben redescubrirse desde cero en el
próximo arranque controlado.

El drop-in de lifecycle de 15 s permanece instalado. Una parada anterior de
5.3.0 agotó el margen y recibió SIGKILL; durante la migración el servicio se
mantuvo enmascarado para impedir que el `postinst` del proveedor arrancara el
backend antes de completar la configuración.

Fuente completa:
[`teleoperation/CRUZR_S2_PICO_TELEOP_SOURCE_OF_TRUTH.md`](teleoperation/CRUZR_S2_PICO_TELEOP_SOURCE_OF_TRUTH.md).

## 6. Capacidades verificadas

### 6.1 Operación y diagnóstico

- Lectura de batería, cargador, paros, sensores y estado de potencia.
- Control web y cambio de modos de trabajo.
- Mando físico para elevador/chasis después de rearme correcto y desbloqueo de
  ruedas.
- TTS en inglés y ASR capaz de transcribir inglés; español funciona peor.
- Cámaras, LiDAR, RGB-D/estéreo y navegación con evitación de obstáculos.

### 6.2 Manipulación tradicional, sin VLA

- Detector especializado `workbin` de UBTECH/DSA para pose 6D de contenedores.
- Centrado visual, agarre bimanual BYD, elevación y depósito mediante tareas
  deterministas.
- Control de separación y fuerzas durante el agarre.
- Transferencia de la caja azul desde mesa 1 a mesa 2 mediante detector,
  navegación, waypoint y AprilTag; un ciclo `--resume-held` completó depósito,
  retroceso de aproximadamente 0,484 m y `home`.
- AprilTag 113 detectado y calibrado para pose vacía y pose con carga.

GR00T/VLA no intervino en esas pruebas. La adaptación procede de detección 6D,
transformaciones, realimentación de fuerza y secuencias programadas.

### 6.3 Manos

Con manos v4 instaladas se verificaron topics y tareas de fábrica para apertura,
cierre, pinzas de dedos, gestos y secuencias. Las manos ya no están instaladas.

### 6.4 VLA

- Checkpoint suministrado cargable en v0.2.0 mediante overlay.
- Inferencia y validación shadow sin publicar a control físico.
- Cuatro IDs documentados: recoger/depositar caja grande en nivel inferior y
  medio.
- No se ha demostrado una ejecución física segura del checkpoint.

Catálogo detallado:
[`guides/CATALOGO_FUNCIONALIDADES_CRUZR_S2.md`](guides/CATALOGO_FUNCIONALIDADES_CRUZR_S2.md).

## 7. Problemas conocidos y decisiones vigentes

### 7.1 PICO/teleoperación — bloqueo P0

La cadena PICO → PC → robot llegó a `Working`, señalización, DataChannel y
recepción de tele-data. El PC no recibe el heartbeat de aplicación esperado.
Con el timeout original esto deshabilitaba la sesión aproximadamente cada
11,1 s; el timeout diagnóstico de 300 s ya superó en runtime ese límite, pero
no corrige ni valida el heartbeat.

En el gate del 25 de agosto se verificó además el workaround de entrada:
gatillo izquierdo → `b_button=true` → `enable=1` → Motion `CoreMode 7`. El
Y del proveedor funciona como conmutador con repetición, no como *deadman*:
con el gatillo crudo estable en `1.0`, `enable` alternó aproximadamente cada
0,51 segundos. A las 12:27 una sola pulsación de 0,567 s volvió a alternar
`enable 0→1→0`; no fue un fallo de heartbeat. El backend activo publica ahora
sólo el flanco ascendente. Tras detectar que el primer gate reutilizaba
muestras antiguas, los scripts exigen ahora muestras Left/Right nuevas después
de START mientras `enable_control=0`, neutralidad antes de mostrar
`TOQUE AHORA` y liberación posterior del gatillo. Su test aislado pasó; el E2E
físico queda pendiente.
Los STOP automáticos dejaron el PC en `operation_type=1`, `enable_control=0`.
El operador confirmó cero movimiento físico en los intentos informados. El gate
local de 60 segundos se ejecutó el 25 de agosto: START fue a las 09:53:46.142,
el toque habilitó a las 09:53:49.845 y el watchdog cerró a las 09:53:56.718 por
`No heartbeat for 10 seconds`. No hubo movimiento físico y sí se oyó una voz
del robot. Esto confirma el bloqueo P0 de heartbeat.

En la ventana de las 10:38 con el timeout de 300 s, el DataChannel abrió antes
de habilitar y `enable_control=1` se sostuvo durante unos 46,1 s sin disparar
el watchdog anterior. Motion entró en `CoreMode 7`, habilitó la protección de
fuerza de ambos brazos y arrancó ambos chequeos de fuerza. El operador movió
los mandos, pero observó cero movimiento del robot. El log PC contiene 4.530
muestras por mando durante ese minuto y ninguna activación de
`squeeze`/grip (`false`, valor `0.0`). Según el SOP, mover el mando sólo hace
seguir al brazo mientras se mantiene el grip correspondiente; por ello este
resultado es el esperado para el gate sin maniobra y no valida ni refuta aún
el seguimiento físico. Tres pulsaciones nuevas al final produjeron
`enable=0→1→0` a intervalos de 0,5 s; el lanzador detectó la pérdida y envió
STOP. El robot quedó `CoreMode 0`/`NotTele` y el PC en
`operation_type=1`, `enable_control=0`. A las 10:43 el stream XR volvió a
`vr_status=0`, aunque TCP/ADB reverse seguían presentes.

A las 10:50–10:51 se restauró de nuevo el stream reiniciando sólo
XRoboToolkit y conservando ADB reverse. El propietario autorizó después una
prueba física real inmediata. `probar_pico.sh` sin argumentos ejecuta ahora
una micromaniobra del brazo derecho; `--move-left-arm` permite la segunda
prueba y `--gate-only` conserva el diagnóstico sin movimiento. Cada modo
físico exige un preflight fresco de paros, batería, cargador, efector, tarea
PICO y velocidad articular, mantiene 60 s sin grips, admite un solo grip y un
gesto de 2–3 cm durante un máximo de 5 s, y envía STOP al soltar o fallar. El
preflight sólo lectura pasó con baterías 77,2/77,8 %, ambos paros a cero,
cargador desconectado, robot inmóvil y tarea Cruzr/PICO correcta. No se envió
START durante la implementación ni la validación seca.

A las 11:53 el transporte XR se migró a la WLAN local `Cruzr S2-0669` sin
alterar `DSA CORPORATE`: PC `192.168.42.215`, PICO `192.168.42.211`. Tras
seleccionar `Head + Controllers` y `Send data`, XRoboToolkit abrió TCP directo
hacia el listener PC `63901`. Se borró el reverse, el flujo siguió establecido
y el preflight canónico terminó correctamente con el backend en STOP. ADB TCP
se usó sólo para administración inalámbrica; no transporta el stream XR
directo. No hubo movimiento físico.

La reinspección de los artefactos instalados descarta que el heartbeat deba
producirlo la UI PC: el source map de `ubt-remote-control 4.1.0` sólo envía
START/STOP. El bytecode de `Publisher.callback` en `ubt_controller 5.3.0`
declara que procesa mensajes inversos del robot por RTM y sólo ante
`type=heartbeat` actualiza `last_heartbeat_time`. **DESCARTADO** desactivar o
puentear este watchdog en el PC: eliminaría la detección de pérdida robot→PC.
El propietario autorizó después una excepción limitada: ampliar el timeout a
300 s para diagnóstico, conservando el STOP. Esto no resuelve ni valida el
heartbeat y una ventana local de 60 s ya no puede declararse gate de heartbeat.
Si el robot debe permanecer inmutable, UBTECH debe suministrar un backend PC
compatible con la v0.2.0 genérica o el componente oficial que complete ese
heartbeat, conservando la parada por pérdida de enlace.

La coordinación del flanco ya no debe realizarse por chat. El modo local
`cruzr_pico_teleop_pc.sh --gate-local` exige terminal interactivo, emite la
señal `TOQUE AHORA` sólo después de armar, monitoriza el gate y envía STOP al
terminar o ante cualquier fallo. `--run` es únicamente un alias compatible.
El lanzador humano `scripts/teleoperation/probar_pico.sh` presenta esas órdenes
en el terminal y delega el flujo al controlador canónico. Por defecto ejecuta
la prueba física mínima del brazo derecho; `--move-left-arm` selecciona el
izquierdo y `--gate-only` conserva el gate sin maniobra. Tras observar que
`Ctrl+C` durante un `read` enviaba STOP pero permitía continuar, el handler se
corrigió para terminar definitivamente con código 130 (143 para `TERM`)
después del STOP.

El SOP exige `utars-udoke-config-v0.2.0-dac-beta.2.tar.gz`, pero sólo está
demostrada la build genérica v0.2.0. Además, `MC_SCENE` está vacío y no se
encontró `pico_control`, aunque ambos aparecen en el SDK/SOP.

Decisiones:

- no eliminar el watchdog ni fabricar heartbeat; el timeout temporal autorizado
  es 300 s y debe tratarse como workaround diagnóstico;
- no declarar lista la teleoperación por ver sólo `Working`, `TeleopMode` o un
  topic existente;
- no ejecutar a la vez el cliente PC y un supuesto cliente PICO directo;
- exigir un gate monitorizado de 60 s antes de cualquier movimiento mínimo;
- pedir a DSA paquete DAC exacto, hashes, matriz de versiones, componente de
  heartbeat y procedimiento directo.

Fuente viva obligatoria:
[`teleoperation/CRUZR_S2_PICO_TELEOP_SOURCE_OF_TRUTH.md`](teleoperation/CRUZR_S2_PICO_TELEOP_SOURCE_OF_TRUTH.md).

### 7.2 Navegación transportando caja

La caja puede aparecer ante las cámaras RGB-D/estéreo como obstáculo propio y
bloquear el costmap dinámico. Se creó un perfil temporal de percepción de
carga que redirige únicamente tres entradas de nube de puntos; mantiene LiDAR,
odom, mapa, bumpers y paros. El último preflight registró
`CARGO_PERCEPTION_PROFILE=disabled`, es decir, restaurado.

Nunca desactivar toda la evitación ni dejar el perfil activo después del
transporte.

### 7.3 Depósito y AprilTag

- Una tolerancia demasiado estricta causaba múltiples correcciones aunque la
  caja ya estuviera razonablemente sobre la mesa.
- El perfil `--fluid` acepta hasta 50 mm en la estación validada, con límites
  duros y menos muestras/iteraciones.
- Una lectura vertical no se corrige con el chasis. La postura de cabeza y
  brazos debe coincidir con la calibración.
- La aproximación autónoma se interrumpe si la orientación o la detección es
  inestable; no debe abrir las abrazaderas al fallar.

### 7.4 Arranque y apagado

- La carrera de arranque v0.2.0 está mitigada mediante boot guard local.
- El manual oficial exige un `Servo Control Button` no identificable en esta
  revisión física.
- La máquina de estados v0.2.0 pide pulsar el paro rojo después de aceptar un
  apagado, aunque el manual no lo incluye como apagado normal.
- Usar `KEY1` aisladamente produjo un corte compatible con apagado abrupto y
  corrupción de logs Docker. No debe usarse como sustituto del apagado lógico.
- El procedimiento definitivo aplicable a este número de serie sigue
  pendiente de DSA.

Fuente:
[`support/UBTECH_SHUTDOWN_PROCEDURE_MISMATCH_V020.md`](support/UBTECH_SHUTDOWN_PROCEDURE_MISMATCH_V020.md).

### 7.5 Baterías/BMS

Históricamente se observó gran diferencia de SOC y truncamiento del segundo
número de serie. Tras la actualización se registraron SOC equilibrados y
números completos, pero la respuesta técnica del proveedor sobre el fallo
histórico sigue pendiente. La UI también llegó a mostrar “fault” sin error de
powerboard. No borrar alarmas ni asumir que son falsas sin comprobar BMS.

### 7.6 Voz

ASR transcribió frases inglesas cuando `run_record`/chatting estaban en el
estado adecuado. Los topics no siempre emitían; se llegó a recuperar texto del
log del motor ASR. El español se reconocía peor. No existe una lista completa
confirmada de órdenes industriales por voz.

### 7.7 Soporte documental y proveedor

Siguen abiertos, entre otros: build DAC exacta, heartbeat, apagado actualizado,
corrección oficial del boot race, cliente MQTT, Netdata, GPU, documentación de
payload, pipeline teleoperación → LeRobot, certificado de conformidad y reporte
de inspección de fábrica.

Seguimiento:
[`support/UBTECH_SUPPORT_TRACKER.md`](support/UBTECH_SUPPORT_TRACKER.md) y
[`support/UBTECH_OPEN_QUESTIONS.md`](support/UBTECH_OPEN_QUESTIONS.md).

## 8. Matriz de reanudación por tarea

### 8.1 Diagnóstico o recuperación de postura

1. Confirmar visualmente efector, carga y obstáculos.
2. Ejecutar `./scripts/cruzr_recover_to_home.sh --check`.
3. Leer `RECOVERY_ROUTE`: `already-home` no envía objetivos;
   `known-workbin` es la única ruta automática candidata.
4. No enviar `home` con una carga o contacto dentro de la trayectoria.
5. Tras PICO no usar `cruzr/home` ni `open_arm_before_home`: el script canónico
   bloquea toda postura no-home de PICO. Volver a home dentro de la propia
   sesión PICO antes de STOP o usar el procedimiento de recuperación por
   fault/apagado; no adivinar una trayectoria desde una postura cruzada.

### 8.2 Caja mesa 1 → mesa 2

1. Leer la guía AprilTag completa.
2. Ejecutar `--check --fast` o preparar `--check --fluid`.
3. Primera puesta en servicio: `--stage-held`; inspeccionar en `MESA2_PRE`.
4. Con caja ya sujeta, usar el modo de reanudación apropiado; no reiniciar el
   ciclo completo.
5. Confirmar visualmente tag, mesa y estabilidad antes del depósito.

Script canónico:
`scripts/cruzr_blue_workbin_table_transfer.sh`.

### 8.3 PICO

1. Leer la fuente PICO completa, incluida la checklist P0.
2. Comprobar que no hay otro cliente ni servicio reactivado.
3. Recuperar ADB/red/`Working`; verificar tracking y backend por separado.
4. Ejecutar `./scripts/teleoperation/probar_pico.sh --check` con el visor en
   Head + Controllers / Send data / Working; debe terminar 7/7 con
   `PICO_TRACKING_OK=vr_status:1`.
5. Ejecutar `./scripts/teleoperation/probar_pico.sh --check-arms-only`; debe
   demostrar el hash esperado y `hand:clamp,waist:0,leg:0`. Si informa
   `waist:1,leg:2`, no mover: salir de TeleopMode y volver a entrar sólo con
   preflight físico fresco para recargar la tarea.
6. Para brazos use únicamente `./scripts/teleoperation/probar_pico.sh
   --teleoperate`: integra `pico_control` oficial, cámara, preflight físico,
   muestras neutras, Y, gate arms-only, ventana de 300 s y STOP. Permite uno o
   ambos brazos; con ambos use recorridos pequeños y suelte ante resistencia,
   retraso o movimiento del torso. `PICO_ALLOW_BIMANUAL=0` restaura el rechazo
   de solapamiento. No autoriza chasis, elevador, joysticks, botones adicionales
   ni gatillos de efector.
7. No usar todavía `--gate-only`, `--move-*-arm` ni `--all-controls`: 4.7.0 no
   publica el campo `enable_control` usado por los gates de 5.3.0. Los scripts
   solicitan STOP y bloquean START en esos modos legados.
8. Repetir siempre el preflight físico fresco y verificar cámara PICO antes de
   cualquier movimiento. La captura de un episodio piloto
   sigue pendiente de exportación y auditoría.

### 8.4 VLA suministrado

1. Mantener contenedores detenidos salvo diagnóstico solicitado.
2. Usar `--status` y shadow, nunca un ejecutor físico implícito.
3. Registrar la postura oficial ready y repetir shadow desde ella.
4. Resolver task-ID, primitiva de trayectoria, límites y deadman antes de
   publicar a control.

### 8.5 Nuevo dataset/checkpoint

1. No iniciar una campaña grande hasta exportar y auditar un episodio piloto.
2. Capturar misión, fases, observaciones sincronizadas, acciones, estado,
   fuerza, cámaras, transformaciones, mapa/waypoints, AprilTags y resultado.
3. Separar navegación global, alineación local, pick, transporte y place.
4. Mantener variantes de caja/pose/iluminación y negativos/recovery en splits
   por escenario, no por frames.

Fuente:
[`vla/CRUZR_S2_VLA_TELEOP_DATA_GUIDE.md`](vla/CRUZR_S2_VLA_TELEOP_DATA_GUIDE.md).

### 8.6 Manos

Las manos no están instaladas. Para retomarlas: SOP físico, `HW_TYPE` correcto,
homing, `check_hands.sh`, ensayo `--check` y luego demostración vacía. No usar
scripts de manos con abrazaderas.

## 9. Qué no debe darse por hecho

- Que la postura o el modo descritos aquí siguen vigentes.
- Que mapa cargado significa localización correcta.
- Que `Working` del PICO significa teleoperación autorizada.
- Que un topic DDS anunciado está publicando muestras frescas.
- Que `status=6` con `RUNNING` es éxito; en acciones ROS 2, el éxito observado
  ha sido `status=4` con `SUCCEED`.
- Que una tarea de manos, caja o VLA sigue instalada después de actualizar.
- Que `KEY1` es el botón de apagado lógico.
- Que una caja ligera valida la carga nominal.
- Que un detector workbin generaliza a botellas u otras clases.
- Que una reproducción `.motion` es una política adaptativa.

## 10. Estructura y fuentes canónicas

| Tema | Fuente canónica |
|---|---|
| Contexto global | este documento |
| Teleoperación PICO/PC/robot | [`teleoperation/CRUZR_S2_PICO_TELEOP_SOURCE_OF_TRUTH.md`](teleoperation/CRUZR_S2_PICO_TELEOP_SOURCE_OF_TRUTH.md) |
| Handoff histórico PICO | [`teleoperation/CRUZR_S2_PICO_TELEOP_HANDOFF_2026-08-24.md`](teleoperation/CRUZR_S2_PICO_TELEOP_HANDOFF_2026-08-24.md) |
| Captura y entrenamiento VLA | [`vla/CRUZR_S2_VLA_TELEOP_DATA_GUIDE.md`](vla/CRUZR_S2_VLA_TELEOP_DATA_GUIDE.md) |
| VLA instalado y shadow | [`guides/CRUZR_S2_VLA_SAFE_ENABLEMENT.md`](guides/CRUZR_S2_VLA_SAFE_ENABLEMENT.md) |
| Cajas y AprilTags | [`guides/TRANSFERENCIA_CAJA_ENTRE_MESAS_CON_APRILTAG.md`](guides/TRANSFERENCIA_CAJA_ENTRE_MESAS_CON_APRILTAG.md) |
| Plan pick → transporte → volcado → depósito multialtura | [`plan_de_trabajo.md`](plan_de_trabajo.md) |
| Contacto/fault y recuperación post-teleop | [`guides/CRUZR_S2_RECUPERACION_TRAS_CONTACTO_TELEOP.md`](guides/CRUZR_S2_RECUPERACION_TRAS_CONTACTO_TELEOP.md) |
| Capacidades y ejemplos | [`guides/CATALOGO_FUNCIONALIDADES_CRUZR_S2.md`](guides/CATALOGO_FUNCIONALIDADES_CRUZR_S2.md) |
| Manos | [`../scripts/hands/README.md`](../scripts/hands/README.md) |
| Boot guard | [`guides/CRUZR_V020_BOOT_GUARD.md`](guides/CRUZR_V020_BOOT_GUARD.md) |
| Apagado | [`support/UBTECH_SHUTDOWN_PROCEDURE_MISMATCH_V020.md`](support/UBTECH_SHUTDOWN_PROCEDURE_MISMATCH_V020.md) |
| Soporte | [`support/UBTECH_SUPPORT_TRACKER.md`](support/UBTECH_SUPPORT_TRACKER.md) |
| SDK original | [`../Cruzr S2-20260803T070710Z-1-003/Cruzr S2/SDK/`](<../Cruzr S2-20260803T070710Z-1-003/Cruzr S2/SDK/>) |

## 11. Protocolo de actualización de esta fuente

Después de cada intervención material, añadir o corregir:

1. fecha y evidencia;
2. estado físico/lógico final **sin asumir que persistirá**;
3. cambio persistente en robot, PC o repositorio;
4. verificación realizada y resultado;
5. rollback disponible;
6. bloqueo o riesgo nuevo;
7. siguiente comando de sólo lectura y documento a consultar.

No copie logs completos aquí. Resuma y enlace la fuente detallada. Si la
evidencia contradice este documento, prevalece la evidencia actual y debe
actualizarse este archivo antes de cerrar la sesión.

## 12. Historial global

| Fecha | Hito | Resultado |
|---|---|---|
| 2026-08-28 | E2.3 piloto reducido de repetibilidad P20 | se ejecutaron dos runs independientes task 0 y dos task 2, con STOP entre ellos. Task 0: 4 chunks, todos rechazados por 7 discontinuidades, duración 10,006055–10,039981 s y máximo `R_shoulder_yaw_joint` 1,361919–1,367893 rad. Task 2: 4 chunks, todos rechazados por 7 discontinuidades, duración 10,005578–10,006689 s y máximo 1,372170–1,379845 rad en el mismo eje. Ambos manifests validan; cada run y los finales quedaron `exited/exited`, `publishers:0`, sin movimiento. Estado `PASS_PILOT_2X2_SHADOW_ONLY`: rechazo/runtime reproducibles, no éxito de PICK |
| 2026-08-28 | E1.0/E1.3 reducidos y E2.1 task 2 completado en shadow | por decisión del propietario, E1.0 cerró con medidas `1,80 × 0,80 × 1,00 m`, cuatro esquinas a 1 m, rigidez/estabilidad y separación >1,5 m; fotos/marcas se difieren a E4. E1.3 reutiliza B0 `0,603 × 0,397 × 0,217 m` y difiere masa/colocación a E4/E6, sólo para liberar shadow. E2.1 `20260828T105547_E2.1` produjo dos chunks task 2 en 10,065 s; ambos fueron rechazados por siete saltos iniciales, máximo `R_shoulder_yaw_joint=1,376502 rad` frente a 0,35. Inferencia/control terminaron `exited`, publicadores `0`, hashes válidos y ningún movimiento. Estado `PASS_SHADOW_SAFETY_ONLY`, no PICK validado |
| 2026-08-28 | reanudación VLA en E1.0 con robot encendido | el propietario informó `home`; el diagnóstico fresco confirmó Motion/Vision accesibles, `HW_TYPE=cruzr_s2_v1`, baterías 70,0/77,7 %, paros 0/0, cargador fuera, acciones listas y máquina de tareas libre. El gate de home no certificó los 20 ejes porque faltaron `2001/2002/2003/3001`, por lo que no se autorizó movimiento. VLA permaneció `exited/exited` con `publishers:0`. Se abrió `Humanoide-vla-evidence/20260828T104622_E1.0/actual_result.yaml`; E1.0 queda pendiente de cuatro alturas, ancho/fondo, estabilidad y fotografías reales de `MESA_T1` a más de 1,5 m del robot |
| 2026-08-28 | return-to-home condicionado por muestra 20D y estado | `cruzr_recover_to_home.sh` pasa a `--check` por omisión, exige 20 ejes presentes, error cero, Operation Enabled, velocidad ≤0,02 rad/s, delta consigna ≤0,01 rad y usa `<0,02 rad` para declarar home sin enviar goals. Un inicio de tarea home ya no prueba éxito. Posturas PICO/unknown/caja posiblemente sujeta/intento no confirmado y eventos posteriores de fuerza, autocolisión, `MoveToGoalFailed`, fault o SAFEOP quedan bloqueados. La primitiva vendor sólo puede ejecutarse internamente desde estados reconocidos del ciclo de caja, con gates antes/después; `cycle.sh --home` delega al recovery, `--force-held-home` se retiró y `--fast` no omite auditorías. `--self-test`, `bash -n`, compilación Python y diff aprobaron localmente con el robot apagado; ruta física revisada pendiente de validación controlada |
| 2026-08-28 | `open_arm_before_home` falla desde postura PICO cruzada; apagado controlado completado | el goal `54f7beb2…` inició ambos brazos, cintura y elevador en paralelo. El FT izquierdo llegó a `Force-X=-370,944 N`; el brazo izquierdo no alcanzó el objetivo y el elevador abortó, terminando `MoveToGoalFailed`/`7104050`/`status=6`. El final previo de PICO ya mostraba autocolisión torso–codo/muñeca izquierda a 17–25 mm. Después 4004/4003/4002 registraron `0x1003` y `0x123f`; `hw`/manipulation reiniciaron y quedaron sin publisher de actuadores ni servidor de acción. Con confirmación física completa y paro mantenido, `/emb/pm_shutdown` respondió `success=True`; Motion/Vision cayeron, pantalla/luces se confirmaron apagadas, y sólo entonces se pulsó `KEY1` y apagó el chasis. Indicador verde apagado, robot/brazos estables. Se descarta esa tarea como home universal desde postura PICO; faults/consignas pendientes de redescubrir antes de cualquier movimiento |
| 2026-08-28 | corregido aborto de `--prepare-full` antes del rollback | el primer intento superó el preflight Motion, pero la asignación de entorno `BACKEND_LOG=…` chocó con la constante shell de sólo lectura y dejó a Python sin ruta. Se cambió únicamente el nombre exportado a `BACKEND_LOG_PATH`. `bash -n` y `git diff --check` aprobaron; el mismo parser pasivo obtuvo `operation_type=1` y `--check-arms-only` confirmó hash `4e8d79a4…`, `clamp/waist=0/leg=0`. El perfil full no fue restaurado, no se recargó modo, no hubo START ni movimiento |
| 2026-08-28 | lanzador PICO full-body separado, aún no activado | se creó `probar_pico_full.sh` sin modificar `probar_pico.sh`. El nuevo flujo exige el YAML vendor exacto y la tarea viva `clamp/waist=1/leg=2`, separa restauración, recarga y START, requiere Wi-Fi sin Ethernet sujeto y conserva preflight/Y/STOP. Añade monitor de log Motion y aborta ante IK, fuerza, EtherCAT, pérdida del monitor o click que conmute protección. El gestor de perfil comprueba STOP mediante log pasivo, sin abrir el WebSocket que podía autoarrancar 4.7.0. Sintaxis, ayudas, diff y bloqueos no-TTY aprobados; `shellcheck` no disponible. Checks reales: full rechazó el hash arms-only activo y el original confirmó `clamp/0/0`. No se cambió configuración robot/PC, no se recargó TeleopMode y no hubo movimiento; el baseline sigue arms-only |
| 2026-08-28 | disciplina de evidencia VLA endurecida para todos los ejercicios | se añadió un creador exclusivo de runs que rechaza raíz/rutas existentes, wrapper completo E1.1, protección de no sobrescritura y hashes relativos en E1.2, y wrapper E2.3 con sub-runs/STOP independientes. E2.0/E2.1 usan el mismo creador. Todos los bloques actuales/futuros del plan que escriben evidencia inicializan su ruta localmente; se eliminaron dependencias de `$VLA_RUN_ID`/`$VLA_EVIDENCE_ROOT` heredadas. Validación local solamente: no se inició inferencia, no se cambió el robot y no hubo movimiento |
| 2026-08-28 | E2.0 task 0 ejecutado fuera de secuencia y recuperado | el bloque manual sí ejecutó check, inferencia shadow y STOP, pero `$VLA_RUN_DIR` estaba vacío y todos los `tee` fallaron contra `/`. La evidencia persistente se recuperó en modo read-only desde los contenedores detenidos: dos chunks, ambos rechazados por `first_point_delta_violations:7`, máximo `R_shoulder_yaw_joint=1,339886 rad` frente a 0,35; duración real `10,063076 s` ante 8 s solicitados. Estado final verificado: inferencia/control `exited`, publicadores `0`, ningún movimiento. Se añadieron `--export-evidence` y `run_vla_shadow_smoke.sh` para evidencia autocontenida y STOP en fallo. Clasificación `PASS_SHADOW_SAFETY_ONLY`; escena/postura no documentadas y E1.0/E1.3 pendientes, por lo que E2.1 no está autorizado |
| 2026-08-27 | referencia visual del dataset VLA identificada | se validó en `/tmp`, sin alterar el dataset, el muestreo automatizado de 12 frames —inicio/medio/final de episodios 0/1/90/91— mediante VLC. Muestran un tote rígido gris abierto de paredes altas y borde gris, con tiras/marcas negras estrechas en algunos frames y un pequeño elemento con lazo visible dentro. El seek puede elegir frames adyacentes entre runs, por lo que sus hashes son de integridad por run, no canónicos. El plan distingue `B0_SAFE` vacía de la referencia: cartón u otro tote es OOD aunque mida 60×40×22 cm. No hubo inferencia ni movimiento |
| 2026-08-27 | mesa candidata disponible para fixture VLA | el propietario declara disponible `MESA_T1`, nominalmente `1,85 × 0,80 × 1,00 m` (ancho × fondo × altura). Se registró como `PENDIENTE`: E1.0 debe medir tablero/cuatro esquinas y comprobar nivelación, rigidez, estabilidad, patas y travesaños. No determina la separación horizontal ni autoriza acercarla al robot |
| 2026-08-27 | inventario mínimo de superficies VLA definido | para tasks 0–3 se reutilizará `MESA_T1` a 1 m y sólo se considerará una plataforma regulable rígida después de que E4.2 resuelva las alturas low/middle; no se requieren compartimientos ni dos repisas simultáneas. `RECEPTOR_VOLCADO` y `MESA_DESTINO_VACIA` corresponden a la misión ampliada y quedan pendientes de nueva primitiva/dataset, no del checkpoint actual. No se adquirió ni movió mobiliario |
| 2026-08-27 | primer intento E1.1 técnicamente correcto pero sin evidencia | `install --check/--verify` y `shadow --check/--status/--stop` observaron hosts correctos, paquete S2/checkpoint, instalación deshabilitada, contenedores `exited`, cero publishers y sesión detenida. `VLA_RUN_DIR` estaba vacío y los cinco `tee` intentaron escribir bajo `/`, fallando por permisos; no quedaron logs. El plan inicializa/valida ahora el directorio y exige cinco logs no vacíos más hashes. Estado `INCOMPLETE_EVIDENCE_EMPTY_VLA_RUN_DIR`; repetir E1.1, sin inferencia ni movimiento |
| 2026-08-27 | E1.1 baseline PC/VLA aprobado con evidencia | run `20260827T141244_E1.1`: cinco logs no vacíos validados contra `logs.sha256`; Vision/Motion y paquete `codes-S2`/`checkpoint-40000`/abrazaderas correctos; instalación deshabilitada; inferencia/control `exited`; `verify_installation` exige `restart=no`; publicadores de movimiento `0`; STOP confirmado. Se creó `actual_result.yaml` con `PASS`. Sólo queda habilitado E1.2 de lectura; no hubo inferencia ni movimiento |
| 2026-08-27 | primer intento manual E1.2 sin directorio de evidencia | `VLA_RUN_DIR` había sido definido dentro del subshell E1.1 y dejó de existir al volver al prompt. Las redirecciones intentaron escribir tres ficheros bajo `/` y fueron rechazadas por permisos; fuentes y robot no cambiaron. Se añadió `audit_vla_experiment_e1_2.sh`, wrapper local de sólo lectura que crea/valida su directorio, comprueba XML/tasks, extrae 12 frames y deja revisión visual pendiente |
| 2026-08-27 | E1.2 auditoría local de artefactos aprobada | run `20260827T141837_E1.2`: XML S2 hash `f4025124…d8323`, preposiciones y llamada pendiente `clamp_s2_joints_trajectory`; catálogo exacto tasks 0–3; doce frames y hoja de contacto inspeccionados. Referencia: tote gris abierto de paredes altas/borde gris, tiras negras estrechas en algunos frames y pequeño elemento con lazo dentro, no cartón. Alturas low/middle, task ready instalado, trayectoria interna y pose horizontal siguen `UNRESOLVED`. Estado `PASS`, sin conexión al robot, inferencia ni movimiento |
| 2026-08-27 | repetición E1.2 del operador aprobada | run `20260827T142214_E1.2`: todos los ficheros validan contra sus hashes. Varios PNG difieren bit a bit del run anterior porque el seek temporal de VLC seleccionó frames adyacentes; la hoja de contacto revisada mantiene el mismo tote/escenario/semántica. El extractor documenta ahora que los hashes PNG prueban integridad por run, no identidad canónica. Estado `PASS`, sin conexión al robot ni inferencia |
| 2026-08-27 | corregida la interpretación geométrica del demo VLA | la sección 7.3 del SDK dice que B0 `60×40×22 cm` debe estar sobre una plataforma de **1 m de altura**; no dice que exista 1 m horizontal robot–plataforma. El plan retiró esa separación inventada y dejó `D_BUMPER_PLATFORM/platform_in_base=UNRESOLVED`. También separó las alturas 55/70/85/100/115 del árbol alternativo no-S2. Se localizó el XML S2 ready, hash `f4025124…d8323`, que aún depende de `clamp_s2_joints_trajectory`. E4 debe derivar pose horizontal/alturas con XML, FK, cámara y frames antes de movimiento. Sólo hubo lectura y documentación |
| 2026-08-27 | manual secuencial E1.0→E8.2 añadido al plan VLA | el inicio de `docs/plan_de_trabajo.md` define plataforma S2 a 1 m de altura fuera de la envolvente, pose de B0, tolerancias, orden literal de comandos, salida esperada, PASS/FAIL/BLOCKED, artefactos y formulario `actual_result.yaml`. E2 es smoke shadow OOD; E4 calcula la pose horizontal y el mapeo low/middle antes de manipular. Los experimentos físicos E4/E6/E7 continúan bloqueados; no se inició inferencia ni movimiento |
| 2026-08-27 | escenarios y runbook PC completos para validación VLA | se definieron en `docs/plan_de_trabajo.md` B0, plataforma S2 de 1 m, estados `NO_BOX/SUPPORTED/HELD`, manifiesto de evidencia y tarjetas `VLA-T00…T10`. Cada tarjeta especifica escenario, comandos o mensajes PC, PASS/FAIL, evidencia y recovery; se separan scripts existentes de herramientas aún por implementar. La revisión de `cruzr_blue_workbin_cycle.sh --help` fijó el lado de 600 mm paralelo a hombros. Es planificación documental: no se inició inferencia ni hubo movimiento; los canaries físicos siguen bloqueados por falta de ready/fixture, ejecutor y primitiva demostrados |
| 2026-08-27 | campaña VLA 14→20 priorizada | se amplió el inicio de `docs/plan_de_trabajo.md` con una campaña por gates para caracterizar exhaustivamente por grupos los 20 outputs del checkpoint: A=14 brazos, H=2 cabeza, L=3 elevador y W=1 cintura. Cubre ocho perfiles funcionales —incluidas dos combinaciones distintas de 17D—, los cuatro task IDs, 32 celdas shadow, postura baja/media, contrato temporal, end flag, OOD, ejecutor sink, canary sin caja, tareas físicas con caja vacía y decisión C0/C1/C2. Es planificación documental; no se inició VLA, no se creó publicador y no hubo movimiento |
| 2026-08-27 | plan de trabajo multialtura y multitamaño | se documentó en `docs/plan_de_trabajo.md` una misión por estados para recoger una caja a baja altura, transportarla, volcar contenido ligero en un receptor, devolverla erguida y depositarla vacía a otra altura. Incluye una caja manipulada por ensayo, perfiles de cajas/estaciones, variación OFAT de posición/orientación/altura, comparación de detector/tag/RGB-D, control determinista, replay, PICO y VLA, gates de captura 20D y recuperación por fase. Es planificación documental: no se enviaron comandos ni se autorizó movimiento |
| 2026-08-27 | arranque controlado después del trip FT restaura Motion sin mover | se encendió chasis, `KEY1` y botón trasero con el paro accionado; Control Center esperó `WaitEStopRelease`. Tras confirmación física se liberó y no hubo movimiento inesperado. La primera consulta `docker info` activó `docker.service` mediante `docker.socket`; se registró explícitamente y no envió comandos al robot. Motion inició `hw`/`manipulation_robot_app`, readiness x86 3/3 y cámaras 2/2; self-check global `passed=true` y `StartMotion` exitoso. Control Center quedó en `AutoTaskMode`. `cruzr_blue_workbin_cycle.sh --check` aprobó: actuadores Operation Enabled, errores/deltas/velocidades dentro de gates, paros 0/0, cargador fuera, baterías 51,5/63,4 % y acciones listas. `cruzr_recover_to_home.sh --check` repitió la salud pero bloqueó correctamente `home` porque el nuevo log no clasifica la postura. El boot guard terminó `failed` por `CONTROL_STATE=unknown`, aunque no ejecutó recuperación (`RECOVERY_ELIGIBLE=0`) y registró seguridad `0 0 0`; no invalida el preflight de Motion, pero debe corregirse para reconocer `AutoTaskMode` |
| 2026-08-27 | teleoperación interrumpida al sujetar una caja; protección FT, caída de Motion y apagado completo | el stream PICO/PC continuó a 90 Hz, Y/enable permaneció activo y el script sólo terminó al `Ctrl+C` del operador. Motion registró en la muñeca izquierda `Force-X=-305,6…-307,0 N` frente al umbral de 120 N, declaró `Excessive force` y detuvo la tarea a las 16:25:59. La causa física exacta —compresión de la caja/contacto externo o transitorio/bias FT— queda pendiente, pero **no fue apretar fuerte el grip del PICO**, que es un clutch booleano. Después se observaron servo 5003 `0x1001/0x2007`, saltos de consigna en ambos hombros y EtherCAT SAFEOP ERROR; los checks terminaron `exit 25` sin servidor de manipulación. Con caja retirada y robot estable, el propietario autorizó apagado completo. `/emb/pm_shutdown` respondió `success=True`; Control Center transitó `TeleopMode→WaitShutdownReady→Shutdown→Term`. Motion y Vision dejaron de responder, el operador confirmó pantalla/luces apagadas, pulsó después `KEY1` y finalmente apagó el chasis; indicador verde apagado y robot estable. No se ha arrancado ni demostrado recuperación |
| 2026-08-27 | carrera de auto-START de WebSocket 4.7.0 eliminada del preflight | el intento 10:12 encontró `operation_type=2` antes de la confirmación. Los logs demuestran que las consultas locales breves de las 10:12:28.592 y 10:12:48.961 coincidieron con `Broadcasting publisher states`; 4.7.0 ejecutó `device detected online, starting remote operation` y arrancó el publisher sin un mensaje `collect operation_type=2`. El preflight detectó el segundo caso y su cleanup lo dejó en STOP a las 10:12:54.828. Se sustituyeron la espera, CHECK 7/7 y la verificación final por reconstrucción pasiva desde transiciones `Pico connect state` y eventos `Pico publisher start/stop`, limitada al arranque vigente del servicio. El WebSocket queda reservado para el cliente oficial después de la confirmación o un STOP de emergencia. `--check` real a las 10:17 abrió **0** clientes WebSocket y produjo **0** START; bloqueó únicamente por `vr_status=0`. Sintaxis, shellcheck y diff correctos; no hubo movimiento |
| 2026-08-27 | primer intento izquierdo tras habilitar bimanual: STOP por segundo Y | arms-only y preflight aprobaron; Y produjo `enable=1` a las 10:07:06.050. Al intentar mover el brazo izquierdo, el grip permanecía activo (`squeeze=1.0`) y XR publicó otro intervalo independiente `Left.b_button=true` desde 10:07:12.312; 5 ms después el backend vendor conmutó `enable=0`. El derecho siguió neutro, no hubo fallo IK y la velocidad articular final fue cero. El script identificó la deshabilitación y confirmó STOP. Es un segundo evento Y en la entrada XR, no una limitación bimanual ni un fallo del brazo. No se modificó software: en la siguiente prueba mantener ambos grips neutros hasta `ENABLE_OFICIAL_CONFIRMADO=1` y después mantener el pulgar izquierdo alejado de Y; no ocultar este STOP sin definir antes otra parada desde el visor |
| 2026-08-27 | control bimanual habilitado por el propietario | tras confirmar el operador que el torso permaneció quieto y verificar cero fallos IK en la sesión arms-only, `--teleoperate` permite por defecto ambos grips/brazos. El gate de `clamp,waist=0,leg=0`, enlaces, tracking, watchdog, STOP y demás seguridades permanece. Se registran `BIMANUAL_GRIPS_ACTIVE=1/0`; `PICO_ALLOW_BIMANUAL=0` ofrece rollback operativo inmediato al criterio de un brazo. Cambio de código sin START ni movimiento |
| 2026-08-27 | primer START con arms-only y STOP por solapamiento mínimo de grips | preflight aprobado y sesión oficial activa durante 29 s con Motion `clamp,waist=0,leg=0`. El guard local detectó ambos grips sólo entre 09:59:26.872 y .917 (~45 ms, cinco frames derechos) y solicitó STOP. En la ventana Motion hubo cero `CalcS2*…failed`; los dos mensajes `ik_restart_time_` eran estado, no fallo. Estado final: `operation_type=1`, UI/cámara paradas y velocidad articular cero. No se ha demostrado que el robot prohíba control bimanual; el bloqueo actual es intencionalmente conservador |
| 2026-08-27 | perfil arms-only recargado y demostrado sin movimiento | con preflight físico/lógico fresco se cambió Control Center `teleop→auto_task→teleop` usando el mismo RPC de la web. En el estado intermedio hubo cero acciones y velocidad articular máxima 0. El último arranque Motion y el gate canónico demuestran ahora hash `4e8d79a4…`, `hand=clamp,waist=0,leg=0`; preflight final: paros 0/0, baterías 58,0/69,0 %, cargador fuera, única acción PICO y joints inmóviles. PC quedó STOP, UI inactiva, sin `pico_control`; prueba física de un brazo pendiente |
| 2026-08-27 | causa de oscilación aislada y perfil PICO arms-only instalado | Motion confirmó que la tarea real era clamp, pero su configuración vendor activaba cintura y elevador (`waist_mode=1`, `leg_mode=2`) en CoreMode 7. Ambos grips estuvieron simultáneamente activos casi toda la sesión y los logs mostraron fallos IK repetidos de alcance, especialmente en el brazo derecho; ésa es la causa comprobada del movimiento compensatorio del torso. Se instaló sin reinicio ni movimiento un overlay reversible que cambia sólo ambos modos a cero (`4e8d79a4…`; vendor `5f08b30c…`). La tarea viva sigue con 1/2: `--check-arms-only` falla de forma esperada y `--teleoperate` no puede enviar START hasta recargar TeleopMode y demostrar `clamp,0,0`. También se añadió STOP si ambos grips quedan apretados |
| 2026-08-27 | movimiento pronunciado del torso con controller 4.7.0 | en una sesión oficial, `pico_control` solicitó `clamp`, el backend PC etiquetó `gripper`, ambos grips estuvieron activos casi continuamente y el operador observó oscilación grande del torso. STOP quedó confirmado (`operation_type=1`, `enable=0`). El diagnóstico posterior verificó Motion `clamp` con cintura/elevador 1/2 y fallos IK: véase la entrada arms-only precedente. En un hallazgo separado, ADB TCP 5555 cerró al retirar USB aunque XR/63901 siguió activo; el preflight bloqueó antes de START |
| 2026-08-27 | recuperación tras PICO, fault 4003 y consignas latentes | la recuperación normal bloqueó `unknown`; después apareció `L_shoulder_yaw_motor` 4003 en FAULT `0x1001/0x0238`. Una tarea temporal sólo para el brazo derecho fue aceptada pero terminó `MoveToGoalFailed/status=6`, sin cambiar posiciones; dejó consignas derechas latentes de hasta 0,1043 rad. El preflight impidió correctamente llamar al rearmado 4003. Se añadió un gate para error/status y `abs(cmd_pos-position)>0,01`. El operador hizo un apagado completo, retiró la caja y usó `KEY1`; los brazos descendieron sin trayectoria. En el arranque siguiente, el boot guard quedó `failed` por `CONTROL_STATE=unknown` mientras el paro estaba accionado, pero tras liberarlo Motion inicializó correctamente: todos los ejes quedaron sin fault, `0x1237`, inmóviles, con posición/consigna dentro de ±0,003 rad de cero. **Home articular alcanzado sin enviar una trayectoria adicional ni llamar al rearmado.** `KEY1` aislado sigue sin ser un procedimiento aprobado y no debe reutilizarse como recuperación |
| 2026-08-27 | auditoría local del contrato de datos 20D suministrado | **VERIFICADO** en metadatos/configuración: estado 32D = 20 posiciones + 12 fuerza/par, acción 20D y horizonte de 10 filas. **OBSERVADO** en episodios 000000/000088/000499: `action[t]` está casi alineada con las 20 posiciones simultáneas (MAE ≈`9e-5`–`1.1e-4` rad; un frame de desfase empeora ≈20x). Parquet y MP4 exportan una timeline de 120 Hz, H.264 `960x576`, con igual número de filas/frames en las muestras. **PENDIENTE UBTECH/DSA**: origen exacto de la acción previa al actuador, reloj maestro y cadencia física real. Se documentó una vía de recolector pasivo y piloto, sin declararla contrato oficial. Sólo lectura: no se cambió PC/robot ni hubo movimiento |
| 2026-08-26 | PICO migrado de USB a Wi-Fi Cruzr | con STOP confirmado se habilitó ADB TCP y se retiró USB. PICO quedó `192.168.42.212:5555`, PC robot-Wi-Fi `.215`; tras reiniciar sólo XRoboToolkit y reactivar Head + Controllers / Working, Unity conectó directamente a `.215:63901`, `vr_status=1` y `probar_pico.sh --check` pasó 7/7. Motion/Vision siguen por Ethernet y DSA conserva Internet. Un socket `.51` obsoleto siguió visible temporalmente en el kernel, pero el preflight seleccionó y demostró el flujo Wi-Fi `.212→.215` |
| 2026-08-26 | destino de cámara PICO corregido | la primera ejecución de `--teleoperate` abrió correctamente el stream Vision pero el relay esperaba el listener en la concesión histórica `.42.211`; el PICO actual era `.42.212`, por lo que no podía llegar el keyframe y no se envió START. Se eliminó la IP predeterminada fija: el lanzador y el script de cámara descubren ahora `wlan0` por el serial ADB y usan USB sólo como fallback. Validado `.42.212` por `wlx80afcad40bd6`; sin relay residual ni movimiento |
| 2026-08-26 | primer gate oficial 4.7.0 y nuevo `--teleoperate` | `pico_control --arm_type clamp` abrió P2P, Y izquierdo produjo `Left.b_button`/`enable=1` y el grip derecho llegó al backend. El cliente oficial confirmó STOP. Un rearme posterior fue causado por un segundo `wscat --wait 1`, no por el STOP oficial; ese patrón quedó prohibido. El propietario acepta temporalmente la selección interna `gripper` sólo para cinemática de brazos. Se añadió `probar_pico.sh --teleoperate`: preflight, cámara principal, neutralidad fresca, Y, ventana inicialmente de 120 s y elevada por el propietario a 300 s, monitor de enlaces/heartbeat y STOP. Sintaxis, diff y rechazo no-TTY/duración inválida verificados; la cancelación final quedó STOP y no movió. El resultado físico del primer grip sigue pendiente de confirmación del operador |
| 2026-08-26 | cable Ethernet sustituido y enlace directo restaurado | `eno1` pasó de 10 a 1000 Mb/s full con autonegociación; se activó el perfil persistente `cruzr-s2`/`192.168.11.250`, never-default, y Motion `.2`/Vision `.3` respondieron sin pérdida en 0,2–0,9 ms. La ruta a `.11.0/24` usa Ethernet, PICO/Wi-Fi Cruzr permanecen activos y la ruta por defecto/Internet sigue por `DSA CORPORATE`. `probar_pico.sh --check` reconoció Ethernet y llegó a CHECK 5/7; falló únicamente porque el PICO aún no transmite TCP 63901. Sin START ni movimiento |
| 2026-08-26 | migración solicitada por UBTECH a controller 4.7.0 para robot v0.2.0 | se respaldó 5.3.0 parcheado (`c085fc4b…`), verificó el DEB 4.7.0 (`4f2b728b…`), purgó 5.3.0 e instaló 4.7.0 conservando el servicio parado durante los scripts del proveedor. El binario instalado coincide con el DEB (`e88b83b7…`), UI 4.1.0 permanece inactiva y el backend está STOP (`operation_type=1`); 4.7.0 no expone `enable_control`, por lo que los scripts validan el baseline pero bloquean todo START hasta observar el Y/enable oficial. XRoboToolkit está abierto por ADB, aunque el visor aún no envía TCP 63901 (`vr_status=0`). No hubo movimiento. Ethernet `eno1` negoció 10 Mb/s pero no resolvió ARP hacia `.2/.3`; el perfil quedó inactivo y Wi-Fi Cruzr sigue llevando Motion/Vision, mientras DSA conserva Internet. En la reunión UBTECH afirmó que 4.7.0 sí recopila datos del robot, contradiciendo/precisando la etiqueta china `只支持遥操作`; formatos, modalidades y exportación continúan PENDIENTES |
| 2026-08-25 | cámara principal Cruzr integrada en XRoboToolkit | `cruzr_pico_camera.sh` abre mediante `/streaming/start` la estéreo izquierda de cabeza, mantiene el heartbeat exclusivo de vídeo, convierte SRS HTTP-FLV/AVCC a H.264 Annex-B con longitud TCP y lo envía al listener 12345 del PICO; las pruebas físicas esperan `PICO_CAMERA_LIVE_BEFORE_START=1`. Fuente real validada (64 frames/3 keyframes en muestra y 36 unidades contra PICO simulado), cierre sin streams ni heartbeat residuales. No hubo START ni movimiento; la visualización en el PICO real queda PENDIENTE porque `.42.211` está fuera de línea |
| 2026-08-25 | reset USB Wi-Fi durante gate PICO | a las 12:59:43 desapareció del kernel el Realtek `0bda:b812`/`wlx80afcad40bd6`; el trigger nunca llegó (758 muestras a cero), `vr_status` cayó y nunca hubo `enable=1`; STOP final, sin movimiento. USB autosuspend ya estaba desactivado, pero Wi-Fi powersave estaba activo y existían errores LPS/tx report. Se fijó `powersave=disable` sólo para `Cruzr S2-0669 1`, se reconectó con STOP, se verificó `Power save: off`, DSA intacta y `--check` 7/7. Los bucles armados abortan ahora inmediatamente ante pérdida de interfaz/carrier/IP/ruta o tracking |
| 2026-08-25 | falso positivo de neutralidad corregido | el intento de las 12:53 abortó antes de START al reutilizar las últimas muestras del log, que eran de las 12:31:26 con ambos grips altos. Ahora START queda aún con `enable=0`, se exigen estados nuevos de ambos mandos pertenecientes a esa ejecución, se valida neutralidad y sólo después aparece `TOQUE AHORA`; ausencia o entrada activa envía STOP. Sin movimiento; final STOP/UI inactiva |
| 2026-08-25 | fallo de gatillo de nivel y corrección a flanco | `--all-controls` habilitó con una sola pulsación, pero sus 0,567 s altos repitieron Y y causaron `enable 0→1→0`; STOP automático, sin trip de heartbeat. Backend cambiado a pulso sólo en flanco ascendente, con gates de mandos neutros/liberación; activo `5083e9f0…`, rollback de nivel/300 s `40b440f4…`. A las 12:44 `--check` recuperó PICO/stream y pasó 7/7; final `vr_status=1`, `operation_type=1`, `enable_control=0`, UI inactiva; E2E físico pendiente |
| 2026-08-25 | Wi-Fi Cruzr canónica para todos los dispositivos del robot; DSA sólo Internet | toda `.11.0/24` se enruta vía `.42.2` y `.42.0/24` es directa por `wlx80afcad40bd6`; perfil Cruzr `never-default`/sin DNS. Motion, Vision, PICO y servicios robot usan `Cruzr S2-0669`; sólo Internet usa `wlo1`. Scripts dejaron de exigir `eno1`; `--check-motion-ready` pasó sin START/movimiento |
| 2026-08-25 | `--all-controls` abortó antes de START por Ethernet caído | `eno1` quedó `NO-CARRIER`/sin `192.168.11.250`; Motion/Vision no eran accesibles y no se armó teleoperación. El preflight ahora recomprueba portadora, IP, ruta, ping y SSH justo antes de los gates físicos para fallar inmediatamente y con causa concreta; ambas Wi-Fi permanecieron conectadas |
| 2026-08-25 | ventana integral PICO autorizada, aún no ejecutada | `probar_pico.sh --all-controls` permite 120 s activos tras 60 s neutros (configurable 120–180 s), cubre controles documentados y siempre solicita STOP; resumen sólo acredita entradas, no efectos finales. Tras una caída WLAN quedaron dos sockets y `vr_status=0` pese a Working; reiniciar sólo XRoboToolkit y reseleccionar Head+Controllers/Send data recuperó el enlace. El `--check` final terminó 7/7 con `vr_status=1`, clamp/300 s y backend desarmado; no hubo START ni movimiento durante el cambio |
| 2026-08-25 | PICO por Wi-Fi local sin túnel XR | `DSA CORPORATE` se conservó en `wlo1`; adaptador secundario y PICO se asociaron a `Cruzr S2-0669` (`.215`/`.211`); XR abrió TCP directo 63901, reverse vacío, `--check` OK y backend STOP; ADB por Wi-Fi soportado por discovery de serial |
| 2026-08-25 | movimiento PICO y retorno a home | el brazo se movió; STOP desarmó el PC pero TeleopMode persistió hasta seleccionar `auto_task`; home directo terminó, aunque las abrazaderas bajas pasaron casi rozando. `--home` queda cambiado a la tarea oficial `cruzr/open_arm_before_home` (apertura previa); hash y preflight sin movimiento verificados, prueba física de la corrección pendiente |
| 2026-08-25 | modo físico real PICO autorizado | `probar_pico.sh` por defecto prueba sólo brazo derecho: preflight Motion+PC, estabilidad 60 s, grip exclusivo, gesto 2–3 cm/5 s máximo y STOP al soltar/fallar; XR restaurado a `vr_status=1`; en ese preflight aún no se había ejecutado START físico |
| 2026-08-25 | ventana PICO 300 s / gate sin maniobra | DataChannel abrió antes de enable; `CoreMode 7` y protección de fuerza activos ~46 s sin trip de 10 s; cero movimiento con ambos grips siempre libres; tres pulsaciones finales alternaron `0→1→0` y provocaron STOP seguro; a las 10:43 `vr_status=0` |
| 2026-08-25 | debug lanzador PICO | añadidos progreso 1/7, timestamps, timeouts de 5 s y traza opcional; flujo normal y fallo ADB simulado verificados; backend permaneció STOP |
| 2026-08-25 | reconexión XR | restaurado ADB reverse 63901 y reiniciada sólo la app; TCP y `vr_status=1`; backend activo pero STOP (`operation_type=1`, `enable_control=0`); `--check` completo OK |
| 2026-08-25 | timeout PICO 300 s | propietario autorizó 10→300 s; binario PC `40b440…` instalado con STOP conservado y backup `0f0d3414…`; backend/UI/XR quedaron detenidos; sin runtime ni movimiento |
| 2026-08-25 | gate PICO/conmutador | gatillo y `CoreMode 7` verificados; toque único correcto habilitó, pero el gate falló por heartbeat a los 10,576 s desde START; STOP dejó `operation_type=1`, `enable_control=0`; en el último intento no hubo movimiento y sí voz |
| 2026-08-10/11 | diagnóstico inicial BMS | se observó desequilibrio SOC y SN truncado; pendiente proveedor |
| 2026-08-14 | AprilTag mesa 2 | tag 113 y referencias empty/held calibrados |
| 2026-08-17 | manos v4 | detección y demos de fábrica; luego se restauraron abrazaderas |
| 2026-08-20/21 | upgrade v0.2.0 | sistema actualizado, mapa y `HW_TYPE` preservados |
| 2026-08-21 | boot guard | recuperación controlada del race Vision→Motion validada |
| 2026-08-21 | VLA shadow | inferencia funcional; chunks rechazados desde `home`; cero mando físico |
| 2026-08-21 | apagado | discrepancia manual/hardware/software documentada |
| 2026-08-24/25 | PICO | cadena hasta DataChannel validada; heartbeat sigue bloqueando sesión estable |
| 2026-08-25 | relevo global | `AGENTS.md` y esta fuente hacen el contexto descubrible automáticamente |
