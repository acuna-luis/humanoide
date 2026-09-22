# Recomendación UBTECH: CycloneDDS y memoria compartida

**2026-09-22 09:38 CEST — Arranque tras liberar VERIFICADO; lectura de actuadores corregida.**
Operador comunica «todo liberado». Misma instancia CC pasa selfcheck=true/error0,
StartMotion succ y JoystickMode. Paros0/0, cargador0; HOME20D medido, máximo
0,002780rad, brazos0,000959rad, velocidad0, sin faults/consignas latentes fuera
de tolerancia. Preflight técnico y SPS runtime rc0; baterías61,8/62,5%.
COMM-01 cargado en principales desde el arranque anterior; recuperación de
lectura20D VERIFICADA, sin prueba de agarre ni estabilidad bajo carga prolongada.
El primer check rc33 era incompatibilidad QoS: publicador ActuatorState ofrece
BEST_EFFORT/VOLATILE; ROSA echo solicita RELIABLE por defecto. Con tipo explícito
y QoS defecto expira124; con best_effort/volatile recibe datos válidos. Se
actualizan las dos lecturas del ciclo base, conservando el gate20D intacto.
Sin movimiento, cambio de modo, reinicio ni instalación remota por el agente.
Alcance/IK de la caja sigue PENDIENTE; no se ha repetido el ciclo.
Evidencia, scripts de consulta y copias before/after: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260922T073414Z_COMM_AFTER_RELEASE`.

**2026-09-22 09:31 CEST — COMM-01 CARGADO tras encendido manual; check técnico correcto.**
Usuario comunica encendido con paro pulsado. Motion y HW conservan contenedores
y setup SHA5504c791…6748ffe; procesos principales robot_app PID64 y
rosa_control_node PID65 cargan `ROSA_MIDDLE_WARE=cyclone`, `ROSA_USE_SHM=OFF`.
Nuevo arranque07:26:09Z; HOME interno v7 SHA1e6e2fb7…a6f03 conservado.
`cruzr_boot_ready.sh --check` rc0: Motion3/3, seis cámaras2/2 con marcas
crecientes y RELEASE_TECHNICAL_CHECK=passed. Contrato de check: espera inicial
WaitEStopRelease, principal1, servo0, cargador0 e identidad CC estable.
Sin comandos de movimiento, reinicios o apagado desde el agente.
Antes de liberar sigue pendiente la confirmación física de brazos abajo/vacíos,
sin sujeciones que impidan HOME, recorrido libre, ruedas bloqueadas y persona
junto al paro. Se preguntó porque previamente estaban asegurados para apagar.
Salud20D después de StartMotion, fin de arranque y agarre siguen PENDIENTES.
Evidencia y copias antes/después: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260922T072926Z_COMM_BOOT_CHECK`.

**22-09 09:17 Europe/Madrid — preparación de apagado para COMM-01.** Usuario
confirma HOME y ambos brazos físicamente asegurados. Nueva lectura ROS2 de20
articulaciones: máximo absoluto 0.002589rad, velocidad0, stamp
1790061405.106022216; compatible con HOME. Esto no sustituye salud de actuadores.
Paros principal0/servo0; se indica pulsar el principal y confirmar para seguir.
Servicio ShutDown y contrato redescubiertos. Sin solicitud de apagado, reinicios
ni movimiento. Activación principal del ajuste OFF pendiente.
Evidencia: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260922T071720Z_COMM_RECOVERY_SHUTDOWN`.

2026-09-22, Europe/Madrid. **COMM-01-NO-SHM — INSTALADO en el entorno de
Motion/HW y clientes SPS. Carga en consultas nuevas VERIFICADA; procesos
principales CARGADOS tras el encendido manual. Fin de arranque y HOME VERIFICADOS; agarre PENDIENTE.**


## Aplicación autorizada del22-09: estado vigente

El usuario pide «hazlo». Se instala sólo la variable `ROSA_USE_SHM=OFF` al final
de `/opt/walker/setup.bash` en Motion192.168.11.2, contenedores:

- `walker-motion.manipulation_robot_app-1` (imagen zs2_motion-v0.2.0).
- `walker-motion.hw-1` (misma imagen).

ROSA_MIDDLE_WARE ya es cyclone, comprobado de nuevo. Son el proceso de
manipulación afectado y su controlador de hardware. Esta intervención **no
elimina Iceoryx globalmente**: RouDi, otros nodos y Vision conservan su estado.
No se cambia CYCLONEDDS_URI, interfaces, watchdogs, prioridades, protecciones,
trayectorias, límites ni binarios. No se modifica el compose. La carga de entorno
afecta a los clientes nuevos que hacen source y al próximo arranque de esos
dos contenedores; no modifica participantes DDS ya creados.

El entrypoint real hace source de ese setup antes de ejecutar la aplicación.
Así se conservan el HOME personalizado y los paquetes dentro de las capas
actuales. Persiste al reiniciar esos contenedores o el host **si uDoke conserva
los contenedores**. Una recreación/actualización exige revisar y reaplicar esta
ficha junto a MOT-01/BOX-01; no se afirma persistencia en una imagen nueva.

Hashes de setup en ambos destinos:

- Anterior: `238e522a314cd13d87d525336d670073c19abdbf4c5cccc0374ad4f4eef17d95`.
- Instalado: `5504c791b93ca9f685f61217afa114c2a35dea4cef68e07e00a93a3df6748ffe`.

### Fuente reproducible, instalación y reversión

[cruzr_no_shm.py](../../scripts/upgrade/cruzr_no_shm.py) requiere Python3 y Docker
en Motion. Comprueba imagen, middleware y hash exacto de ambos originales antes
de escribir; rechaza contenido inesperado. Conserva permisos/propietario, hace
reemplazo atómico con comprobación de concurrencia y deja recibo de cambios
parciales si ocurre un error. Nunca reinicia ni envía órdenes al robot.

En un despliegue nuevo, copiar ese archivo a un directorio privado nuevo en
Motion mediante SSH habitual. Ejecutar allí, sin usar como sustituto de los
gates físicos de activación:

```bash
python3 cruzr_no_shm.py --check
python3 cruzr_no_shm.py --install --backup ./before-install
python3 cruzr_no_shm.py --check
# Reversión selectiva; tampoco recarga procesos:
python3 cruzr_no_shm.py --rollback --backup ./before-rollback
```

Las carpetas de backup deben ser nuevas. Copiar el backup fuera del robot y
verificar SHA256SUMS antes de activar. En esta intervención el instalador y
backup remoto están en `/var/tmp/cruzr-no-shm-20260922T070603Z_CYCLONE_NO_SHM_APPLY`.
Copia externa `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260922T070603Z_CYCLONE_NO_SHM_APPLY/motion-no-shm-backup.tar.gz`,
SHA256 `8997c7193b45fdd050d552952104c4879f33d3ee34698da00b7442ddb7355d76`;
se comprobaron todos los checksums internos tras copiarla. El respaldo incluye
ambos setup originales, nuevos, inventarios privados y recibo. Inventarios y
compose de ambos hosts se conservan privadamente fuera de Git.

### Clientes del escenario y comprobaciones

Paquete frontal nuevo **`a9eaf948512d2eb4`** instalado de forma aditiva en
`/var/tmp/cruzr-front-box/a9eaf948512d2eb4` y, en los contenedores Motion nativo y
ROS2, `/opt/cruzr-front-box/a9eaf948512d2eb4`. Sustituye a `a66aa93932ef9bdb`, que
se conserva. `front_sps_session.py` exporta OFF/cyclone para consultas nativas,
adaptador y proceso del flujo. El parser de descubrimiento admite únicamente
el aviso INFO específico observado de SHM desactivado; conserva rechazo de
grafo vacío, errores, tipos incorrectos y servidores existentes.

Las lecturas JSON de actuadores de `cruzr_blue_workbin_cycle.sh` y de pose en
ambos `force_escenario1*.sh` usan ROSA_LOG_LEVEL=ERROR sólo para esa consulta:
el INFO inicial deja de contaminar JSON. Se verificó ese comportamiento en
una consulta real. Los servicios principales mantienen su nivel de log.
Los gates de salud/frescura/postura no se relajan.

Recrear el paquete: `python3 scripts/box_handling/front_box_integration.py --install`.
Comprobar sólo lectura: el mismo integrador `--check-runtime` (sin percepción ni
caché de caja). **VERIFICADO rc0** en el robot: hashes, descubrimiento SPS con
servidores0 y controlador esperado. Consulta independiente sin override explícito
confirma «Shared memory mode is turned off» y ArmTask servidor1.
Ambos setup comprobados con source devuelven SHM=OFF/cyclone.
PID1 conserva entorno anterior, mismos IDs/StartedAt y RestartCount0: **todavía
no cargado en los procesos principales**. No se ejecutaron adaptadores, tareas,
HOME, navegación, reinicios ni apagado en esta aplicación.

Validación local:61 tests antes del ajuste de lecturas JSON; después24 tests de
middleware/SPS y24 de flujo; sintaxis Bash y parche real de setup/reversión exacta
correctos. Las pruebas no acceden al robot. Prueba física del transporte y salud
20D tras recarga PENDIENTES; no confundir `--check-runtime` con esa validación.

Revertir clientes implica recuperar selectivamente sus fuentes previas del
backup local `project-working-files.tar.gz` y volver a verificar el paquete
anterior. No restaurar todo el árbol ni eliminar cambios ajenos. Revertir sólo
setup no cambia el OFF explícito del supervisor nuevo.

### Activación pendiente y punto de reanudación

No se reinicia con brazos elevados. Se ha solicitado confirmar que personal
formado **ya ha asegurado físicamente ambos brazos**, con abrazaderas vacías y
sin contacto; la confirmación previa sólo era disponibilidad de medios.
Hasta recibir esa confirmación no se da por preparado el apagado. Después,
comprobar paro físico y técnico y seguir el procedimiento excepcional de la
[guía de apagado](UBTECH_SHUTDOWN_PROCEDURE_MISMATCH_V020.md), con confirmación
visual antes de KEY1/chasis. Arranque posterior con paro y comprobación de
HOME instalado/servicios, siguiendo BOOT-01 antes de liberar. No ejecutar el
ciclo de cajas como prueba de comunicación. El alcance/IK sigue sin resolver.

Evidencia, copia del árbol previo con archivos no versionados, receta aplicada,
respuestas y fuentes finales: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260922T070603Z_CYCLONE_NO_SHM_APPLY`. Fecha22-09 Europe/Madrid. El estado
anterior descrito abajo es histórico; no sustituye esta ficha vigente.

## Mensaje del proveedor y alcance

El usuario aporta un mensaje de 邹烨龙 en respuesta al archivo
`20260918_UBTECH_SELFCHECK_LOGS_WAE001UBT60000669.zip`:

> 分析日志，原因是使用了iceoryx通信中间件，不建议这样使用，因为iceoryx只有共享内存，不支持UDP，如果对端不是iceoryx，就会出问题，可以切换为cyclonedds

Traducción: «Al analizar los registros, la causa es el uso del middleware
Iceoryx. No recomendamos usarlo así: Iceoryx sólo tiene memoria compartida,
no admite UDP; si el otro extremo no usa Iceoryx, puede haber problemas.
Se puede cambiar a CycloneDDS».

**Afirmación de proveedor**, referida al paquete del18-09. Es una pista para
investigar los fallos del22-09; no demuestra por sí sola que ambos incidentes
tengan exactamente la misma causa. Tampoco prueba que baste cambiar una
variable en el ejecutor PC ni que el proveedor haya revisado el adaptador SPS.

## Configuración realmente leída

| Proceso/contenedor | Middleware | Memoria compartida |
| --- | --- | --- |
| Motion, `walker-motion.manipulation_robot_app-1`, PID65 | `ROSA_MIDDLE_WARE=cyclone` en entorno del proceso | `ROSA_USE_SHM` ausente; trazas de ejecución pasan por CycloneDDS→Iceoryx. |
| Motion, `walker-ros.ros2-1` | `RMW_IMPLEMENTATION=rmw_cyclonedds_cpp` | No es el proceso nativo de manipulación. |
| Vision, `walker-system.self_check_service-1`, PID71 | `ROSA_MIDDLE_WARE=cyclone` | `ROSA_USE_SHM=OFF` ya presente antes de esta intervención. No es una lectura del antiguo self_check_monitor. |
| Vision, `walker-ros.ros2-1` | `RMW_IMPLEMENTATION=rmw_cyclonedds_cpp` | No demuestra el transporte de todos los nodos ROSA. |

El entorno Cyclone nativo conserva `<Discovery><MaxAutoParticipantIndex>100`
en CYCLONEDDS_URI; interfaces Motion `enp4s0;lo`, Vision `rgmii0;lo`.
Se consultaron también contenedores y rutas de montaje, sin recrearlos.
La biblioteca `libcyclone_transport.so` incluye un fragmento XML
`<SharedMemory><Enable>true</Enable></SharedMemory>`; que exista el texto no
significa que todos los procesos lo activen. El aborto observado del22-09 sí
recorre `libddsc → iceoryx_binding_c → iceoryx_posh`.

Copia local de `librosa_interfaces.so` contiene el parser de `ROSA_USE_SHM`:
valores admitidos OFF/ON/0/1/TRUE/FALSE, valor no admitido vuelve a ON.
El binding ContextOptions expone `use_shm_` y ShmMode_ON/OFF. Análisis local
estático, sin parchear bibliotecas ni SDK original. Hashes:

- `libcyclone_transport.so`: `faca9411a03acfbf0d99e0041853501f7fc938324733973d1be7423a4b2ed033`.
- `librosa_core.so`: `cab2df6a11b2b9fd15f43845c1b267659b057a095ef1bcb610cfeb2b921bb271`.
- `librosa_interfaces.so`: `9962d4bcc66a611840600e0999e7097c299c5b2c88dea3fd1f4cc302e9f346c9`.

## Prueba acotada sin movimiento

Sólo para el proceso de consulta recién creado se estableció
`ROSA_USE_SHM=OFF` mediante `docker exec -e`. ROSA confirmó:

```text
Shared memory mode is turned off.
Action: mc_task_msgs/action/ArmTask
Action client count: 1
Action server count: 1
```

Consulta `rosa action info --no-daemon /mc/manipulation/action`, rc0.
Prueba posterior `rosa topic echo --once --print-compact --no-daemon
/mc/actuator_state`, con la misma variable, agotó10s (rc124) sin datos, aunque
confirmó SHM desactivado. **Descubrimiento correcto no equivale a estado de
actuadores recuperado ni a una prueba de la acción de movimiento.**

El ajuste concreto identificado para un proceso ROSA nuevo es:

```bash
ROSA_MIDDLE_WARE=cyclone
ROSA_USE_SHM=OFF
```

No basta exportarlo en el PC: debe llegar al entorno del proceso ROSA que se
pretenda cambiar. No modifica el entorno ni los participantes de un robot_app
ya arrancado. No se aplicó a Motion, HW, clientes de control o adaptador SPS
persistentes; no se afirma solución global probada. Reproducir únicamente la
consulta de lectura con la receta de abajo; no reutilizarla para enviar HOME.

```bash
# En Motion, lectura del grafo; no envía objetivos:
docker exec -e ROSA_USE_SHM=OFF walker-motion.manipulation_robot_app-1 bash -lc \
  'source /opt/walker/setup.bash; export ROS2CLI_DISABLE_DAEMON=1; timeout -k 2 8 rosa action info --no-daemon /mc/manipulation/action'
```

Reversión del ensayo: al salir el proceso desaparece su override de entorno;
no hay archivo ni servicio que restaurar. Los logs de diagnóstico normales del
proveedor pueden registrar el proceso. Se finalizaron explícitamente dos
subprocesos de lectura propios que sobrevivieron a consultas previas con
Iceoryx (PID2533 y2609, `__rosa_list_function topic type /mc/actuator_state
--no-daemon`), verificando comando exacto antes de señalizar: SIGTERM no terminó,
SIGKILL los dejó Z, pendientes de recolección por su padre. No se señalizaron
robot_app, HW, RouDi ni otros servicios. No repetir pruebas que dejen consultas
colgadas; verificar el tipo antes de suscribirse en siguientes diagnósticos.

## Recuperación preparada, no ejecutada

Nueva lectura antes del ensayo: RouDi aún avisa de runtimes retirados del
PID65 y actuator_state nativo falla rc124. JointStates nuevo
stamp1790060009.478018308, velocidades0, postura preparatoria fuera de HOME.
No habilita una trayectoria automática. El recuperador versionado exige
actuator_state20D y una ruta reconocida; no se puentearon sus requisitos.

Se redescubrió en Vision `/emb/pm_shutdown`, tipo `emb_task_msgs/srv/ShutDown`,
contrato `deadline_sec=15`, `confirm_str=confirm-to-shutdown`.
**No se llamó al servicio.** Operador confirma disponer de personal/medios
para asegurar brazos; eso no equivale a confirmar que ya estén asegurados ni
a autorizar/aplicar un apagado. La propuesta de apagado queda sin ejecutar
mientras se define el cambio de comunicación a partir del mensaje UBTECH.
Procedimiento excepcional con brazos fuera de HOME:
[apagado de esta unidad](UBTECH_SHUTDOWN_PROCEDURE_MISMATCH_V020.md).

Siguiente: delimitar con los entornos/binarios de cada proceso qué servicios
requieren OFF, preparar aplicación y reversión selectivas, recuperar los
participantes afectados en condiciones físicas verificadas y comprobar salud
20D/consignas antes de HOME o agarre. No reiniciar componentes para probar desde
brazos elevados. No desactivar watchdogs ni borrar /dev/shm. El fallo de
alcance/IK de la caja requiere validación separada, incluso si se resuelve IPC.

## Estado y evidencia

Sólo cambios documentales PC y copias de lectura fuera de Git. Sin paquetes
instalados, configuración persistente remota, reinicios, apagado ni movimiento.
Efectos temporales: consultas con override OFF y cierre de dos consultas propias.
Aplicación persistente/carga en producción/prueba física: PENDIENTES.
Backup documental, scripts de consulta, respuestas completas, bibliotecas,
ensamblador, procedencia del mensaje y SHA256SUMS:
`/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260922T065357Z_FRONT_SPS_RECOVERY_CHECK`.
La receta anterior reproduce el único ensayo admisible aquí; los colectores
archivados conservan la trazabilidad, sin depender del historial del chat.
Reversión documental selectiva con before/. Sin commit ni push.


## Corrección de la lectura20D tras liberar — 2026-09-22 09:38 CEST

Cambio PC en [cruzr_blue_workbin_cycle.sh](../../scripts/cruzr_blue_workbin_cycle.sh):
las dos consultas de `/mc/actuator_state` solicitan ahora
`--qos-reliability best_effort --qos-durability volatile` y tipo explícito
`mc_state_msgs/msg/ActuatorState`. No se cambia el publicador, los valores de
telemetría ni las condiciones del gate; se corrige la compatibilidad de entrega.
La guía `rosa topic echo --help` instalada confirma RELIABLE como valor por
defecto. Grafo real ofrece1 publicador BEST_EFFORT/VOLATILE. Comparación
acotada con tipo explícito: defecto rc124 sin muestra; best_effort rc0.
ROS2 también recibió muestra20D válida; ambas pasan el clasificador existente.
`/nav/robot_pose` ofrece RELIABLE en ambos publicadores y no requiere este cambio.

Aplicación: basta usar el archivo PC actualizado, que envía su consulta por SSH.
No requiere instalar ni recargar nada en robot. Reproducir la verificación con
`bash scripts/cruzr_blue_workbin_cycle.sh --check` (rc0 en esta intervención)
y `python3 scripts/box_handling/front_box_integration.py --check-runtime`
(rc0, sin adaptadores ni tarea perceptiva). Cinco tests del gate20D, sintaxis
Bash y diff correctos. Copia previa/final y checksums en el directorio de
evidencia de esta sección. Reversión selectiva de las dos consultas desde
`before/scripts/cruzr_blue_workbin_cycle.sh`; no restaura servicios ni hace
movimientos y volvería a provocar el timeout con esta configuración.

Control Center terminó el arranque a07:32:08Z (log15:32:08 UTC+8).
Snapshot actual identifica PID1005, logcc_main.20260922_152709.1005.log y
estadoJoystickMode. Lectura ROS2 ActuatorState stamp1790062487.316727708;
nativa stamp1790062512.096720027. Estado habilitado/sin fallos20D, HOME e
inmovilidad verificados; preflight completo posterior vuelve a pasar.
Consulta de RouDi últimos2min no devolvió advertencias: observación acotada,
no prueba de ausencia futura de fallos ni calificación de agarre/carga.
No se enviaron tareas, HOME, navegación, cambios de controlador o reinicios.
