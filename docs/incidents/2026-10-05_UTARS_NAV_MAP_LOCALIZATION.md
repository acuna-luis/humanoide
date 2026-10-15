# utars_nav_map: localización visual perdida y destinos vacíos

**08-10-2026 — INCIDENT-LOGBOOK-20261005-08. VERIFICADO documental.**
[Bitácora unificada de fallos del 5 al 8 de octubre](BITACORA_FALLOS_2026-10-05_A_2026-10-08.md): reportes del operador, causas demostradas, hipótesis, cambios y pendientes; anexo CSV con139 ejecuciones locales fallidas (no139 causas ni todas reportadas en chat). Fuentes especializadas conservadas. Observación actual de copia local: min_correction_m0,01m y max_abs_command_delta0,015rad, ediciones manuales del usuario sin cambio por esta recopilación; no sustituir valores históricos de cada ensayo. Sólo documentación PC, sin consulta/orden al robot ni alteración de parámetros. Fuentes, inventario, before/after y hashes en ../Humanoide-vla-evidence/20261008_FAILURE_LOGBOOK/. Reversión selectiva de esta ficha y dos documentos nuevos. No commit/push.


**06-10-2026 — PC-WIFI-USB-DISCONNECT-20261006. OBSERVADO, sólo lectura.**
KernelPC17:59:28CEST: USB2-1 disconnect y deauth dewlx80afcad40bd6; adaptador
rtw88_8822bu reaparece17:59:30. Asociación17:59:35 falla a17:59:39 con
4WAY_HANDSHAKE_TIMEOUT; NetworkManager restablece conexión/IP42.215 a17:59:44.
Causa de desconexiónUSB (retiradamanual/puerto/hardware/driver) PENDIENTE.
No se culpa a señal débil: lectura actual−28dBm,5GHz5745MHz. Ruta Vision11.3
vía42.2/wlx80afcad40bd6; eno1DOWN/sinIP, conexión actualNOEthernet. Prueba
20pings por destino en~3,8s: Vision0%pérdida,media32,838ms,máx179,732ms;
gateway0%pérdida,media32,061ms,máx177,713ms. Interfaz sinerrores/drops
acumulados desde recreación; no prueba estabilidad prolongada. Corte observado
puede afectar web/vídeo/control; vínculo exacto con aviso rojo PENDIENTE.
No explica por sí solo topictrack_image inexistente y peticiónsinmap_type.
Ante repetición revisar puerto/adaptador/driver antes de control físico; Ethernet
es alternativa cuando se verifiqueenlace/ruta. No se modificó red/USB/powersave,
reinició servicio ni envió movimiento. Evidencia/kernel/ruta/link/pings:
../Humanoide-vla-evidence/20261006_WIFI_LINK_CHECK/. Backup documentalbefore/
after/ ySHA256SUMS, reversiónselectiva. git diff--check correcto; sincommit/push.

**MAP-QUALITY-20261005 — 05-10-2026, Europe/Madrid. OBSERVADO por lectura.**
Consulta del operador sobre cabeza buscando y calidad del mapa. No se ordenó
movimiento, relocalización, carga/guardado de mapas, reinicio ni cambio remoto.

## Resultado actual

Contenedores descubiertos en Vision y Motion mediante docker ps. La última
relocalización de navegación con utars_nav_map falla: FSM_WaitRelocate,
LOCATION_LOST; /vnav/task/command/_action/status conserva status6 del objetivo
iniciado1791214768,676950522. /vnav/vslam/state consultado informa LOCATION_LOST.
Locate3D registra repetidamente Vision pose status is unreliable.
No se envían get_map_name/check_state al endpoint de acciones para evitar
interferir con una eventual tarea del operador; el nombre se toma del diario
de relocalización y se inspecciona ese mapa, sin afirmar un permiso de navegación.

Mapa en /etc/walker/map/utars_nav_map: 139 archivos, mapa visual presente.
source_map/points.pcd declara4443 puntos; localization_map/map.pb595958bytes.
Mapa LiDAR uslam_2d/map.pcd declara12882 puntos. mapping_pose.csv tiene38
registros del05-10: 17:36:42,103–17:37:13,143 CEST. Trayectoria de cámara estimada
abarca3,238m×0,695m XY y recorrido acumulado5,845m en31,041s. Ese rectángulo
no es la extensión del mapa ni una medida de exactitud/cobertura visual.
No es el mapa histórico MESAS2 con13 puntos; evitar reutilizar ese diagnóstico.

En un intento visual del diario recogido hay49 puntos de mapa emparejados, pero
StereoPnPSolver falla: small_error_count17<20; el contador de solver alcanza24
fallos, y relocalization failed, track_state_=LOST. También aparecen candidatos
rechazados por número/área/distribución de correspondencias y homografía.
El mapa no está vacío, pero las coincidencias en esta vista no bastan para una
pose válida. No se deben bajar umbrales para aceptar esos candidatos.
TF de máscara de brazo L_arm_base_link ausente aparece como aviso adicional;
relación causal no demostrada. No se ha comprobado calibración o escena actual.

API de lectura POST /map/get/utars_nav_map devuelve200. umap.target_points=[]
y task.target_points=[]; archivos umap/umap.json y user/task.json coinciden.
Task lleva update_time2026-10-05-23-37-21 (hora nativa), ID
2026-10-05-23-37-21-c8d29d72. El mapa inspeccionado no contiene get1/put1.
Validador versionado scenario1_checks.validate_map_points rechaza exactamente
Require one unique get1. Ese mapa no está listo para el escenario de cajas.
No se restauran coordenadas del mapa anterior sobre un marco nuevo.

La pose de mapa mediante ROS2 volatile y las articulaciones de cabeza mediante
ROSA no entregaron muestra en7s. /uslam/module_state y umap publicado tampoco.
Esto no demuestra desaparición global de publicadores: hay diferencias conocidas
entre middleware/QoS. No se confirma postura ni parada con esos timeouts.
El movimiento de cabeza descrito por el operador es compatible con búsqueda de
relocalización (INFERENCIA); no se demuestra su cliente exacto o el estado físico.

## Continuación y reproducción

Antes de usarlo para transporte, comprobar correspondencia de posición/orientación
reales con la UI, recuperación estable de localización y poses frescas; comprobar
cobertura visual de zonas/ángulos de aproximación. Si hace falta ampliar o rehacer
cartografía, respaldar el mapa existente y realizar una captura supervisada bajo
nombre nuevo, validar guardado y relocalización antes de reemplazarlo. Después
crear get1/put1 en el marco de ese mapa y comprobar las aproximaciones físicas.
La consulta no autoriza ejecutar esa intervención ni repetir ciclos interrumpidos.

Lecturas reproducibles, tras redescubrir contenedores y sin mandar acciones:

```bash
ssh walker@192.168.11.3 'docker ps --format "{{.Names}}"'
ssh walker@192.168.11.3 'docker exec walker-nav.nav_taskmanager-1 bash -lc "source /opt/walker/setup.bash; export ROS2CLI_DISABLE_DAEMON=1; timeout 7 rosa topic echo --once /vnav/vslam/state"'
ssh walker@192.168.11.3 'docker logs --since 5m --tail 100 walker-nav.nav_taskmanager-1'
```

Comandos completos/respuestas, inventario, hashes de trayectoria, API y resumen:
../Humanoide-vla-evidence/20261005_MAP_QUALITY_READONLY/.
Cambios persistentes sólo en documentación PC; archivos previos exactos before/,
posteriores after/ y manifiesto SHA256. Reversión documental selectiva desde
before/; no existe cambio remoto que restaurar. No commit ni push. Verificación:
consultas anteriores y gate puro sobre API archivada; git diff --check correcto.
Causa de la pérdida, cobertura necesaria y recuperación física PENDIENTES.

## Actualización posterior — cabeza y relocalización del mapa nuevo

**MAP-HEAD-RELOCALIZE-20261005 — OBSERVADO, sólo lectura.** Operador terminó
la nueva cartografía y observa cabeza de lado a lado. Ahora se demuestra el
cliente: walker-nav.vnav_head_processor-1 envía objetivos /mc/head_control
con UUID/pitch/yaw coincidentes con Motion. Dueño del componente: navigation.
No es una tarea de agarre/cabeza enviada por el agente. Las solicitudes rechazadas
por componente ocupado durante una trayectoria no demuestran mando simultáneo
por otra persona; son el bucle periódico del mismo procesador observado.

Navegación acepta relocation_start23:50:21,830 hora nativa, map_type=fusion,
utars_nav_map. Cabeza informa ROTATING_HEAD; realiza solicitudes periódicas de
barrido durante búsqueda. El propio navegador envía stop_rotate23:50:55,640,
cancela UUID27bb5863-a362-43c8-bd84-247e4d4896c6 y envía centro0/0 con UUID
538591e9-f987-4e86-8a48-a72db2cf8885. Motion confirma IsReached23:50:56,433;
el procesador terminaREADY. La línea Head move fail del objetivo cancelado
forma parte de esta cancelación; no prueba por sí sola avería de servo.
No aparecen objetivos de cabeza posteriores en las últimas lecturas acotadas.
Esto documenta el fin técnico del barrido, no telemetría física actual continua.

Relocalización exterior51cf3bf6-e544-4a90-a3c6-9266cf6bef77 termina23:51:04,640,
status4/FSM_Relocating SUCCEEDED, planificadorREADY y transiciónFSM_WaitNavigate.
La consulta VSLAM aún devuelveLOCATION_LOST. Éxito exterior en fusion no demuestra
recuperación visual ni posición física correcta; corresponde verificar mapa/pose
frescos y coherencia con ubicación real antes de navegación con caja. No se ha
publicado una orden de parada, HOME o navegación desde este diagnóstico.

El mapa vuelto a guardar por el operador YA no es la captura anterior4443/38:
source_map/points.pcd declara2471 puntos y mapping_pose.csv56 registros, con
sellos1791215134,586683–1791215301,867837. Un número mayor de poses y menor de
puntos no califica por sí solo calidad o error. Destinos get1/put1 no se revalidan
tras ese guardado en esta intervención; la ausencia previa pertenece a la API
archivada anterior. Conservar separación temporal al interpretar el incidente.

Evidencia/comandos/UUID: ../Humanoide-vla-evidence/20261005_HEAD_AFTER_MAPPING/.
Consultas docker ps/logs, suscripciones de sólo lectura y encabezados de mapa;
ninguna acción cliente, reinicio, configuración o movimiento enviados. Copia
exacta previa de notas before/, posterior after/ y manifiestoSHA256. Reversión
sólo documental selectiva; no hay estado remoto que restaurar. diff-check correcto.
Sin commit/push. Estado físico actual y calidad/calibración visual PENDIENTES.

## NAV-RELOCATE-FAILED-20261006 — fallo previo a get1

**06-10-2026, Europe/Madrid. OBSERVADO; diagnóstico de sólo lectura.**
Ejecución del operador20261006T121855Z_OPTIMISTIC_SCENARIO1_254841:
mapa utars_nav_map, FSM_WAITRELOCATE ya en ready. Destinos presentes; get1
X1,0599311472187367/Y−0,5603649759784087/yaw0,04843714555150386.
prepare_map solicita relocalización global antes de navigation_start;
objetivo08160e8a-c3a6-4cc3-a57d-1e9010f8098d termina status6, descripción
重定位失败 y `relocation_start failed, change to FSM_WaitRelocate`.
Checkpoint completed=[], fallo navigate_get1, box_state=unknown. No se alcanzó
agarre ni ajuste visual. Los avisos de lease son posteriores al fallo original.
El diario no demuestra parada física actual ni autoriza reiniciar el ciclo.

Lectura posterior: contenedores Vision redescubiertos con docker ps; docker logs
acotados20m/350líneas de nav_taskmanager, vslam y locate3d_task, sin acciones
cliente. Navegación informa fail_module_name=USLAM; locate3d registra
`template_match failed in global relocalization`, ausencia de reflectores
mapa/scan y fallo ICP. VSLAM informa restricciones de pose0<10, fallos de lectura
getFeatures y track_state_=LOST. Estas líneas pertenecen a intentos posteriores
20:20/20:22 hora nativa y observación20:25; no se atribuyen por UUID al intento
121855. Su relación temporal exacta con el fallo comunicado está PENDIENTE.
No se concluye mapa corrupto, avería de cámara ni causa exclusiva de iluminación.

Continuación: comprobar en UI el mapa seleccionado, ubicación/orientación real,
visibilidad del entorno y capacidad de relocalizar en una zona conocida bajo
supervisión antes de transporte. Si no recupera localización, investigar mapa,
sensores/calibración y cambios de escena, respaldando antes cualquier modificación.
No bajar umbrales ni enviar get1 con localización inválida. --check valida estado
sin ordenar relocalización; sólo FSM_WAITNAVIGATE y poses coherentes permiten
considerar recuperada la localización, sin sustituir comprobaciones físicas.
No se enviaron HOME, navegación, relocalización o reinicios desde este diagnóstico.

Cambios persistentes sólo documentación PC; ejecutor y gates conservados.
Evidencia: ../Humanoide-vla-evidence/20261006_RELOCALIZATION_FAILED_READONLY/:
incident.json con SHA256 del diario, respuestas/logs remotos, before/after/ y
SHA256SUMS. Reversión documental selectiva desde before/, preservando trabajo
posterior. Verificación: diario/checkpoint, logs pasivos, git diff --check.
Estado físico, causa raíz y recuperación de localización PENDIENTES; sin commit/push.


## NAV-VSLAM-MAP-DIR-20261006 — mapa visual ausente

**06-10-2026, Europe/Madrid. OBSERVADO por sólo lectura.** Petición revisar
VSLAM_MAP_DIR_ERROR del intento152706_633746. Contenedores Vision redescubiertos;
consultas docker logs/inspect/exec y find/stat/df/cat, sin acciones ROS ni cambios
remotos. VSLAM y navegador arrancaron15:17:30/15:17:29UTC, restart_count0.

Mapa actual `/etc/walker/map/utars_nav_map` visible desde el contenedor VSLAM:
umap, user, uslam_2d, uslam_3d; no directorio vslam/source_map/localization_map.
LiDAR conserva map.pcd/graph.bin/dynamic_map.db y destinos get1/put1 presentes.
version.txt identifica maps_manager current_tag_v1.5.4, guardado20261006_212111
hora nativa. Directorio accesible uid1000ubt, permisos777, disco367GB libres;
no evidencia de falta de espacio o inaccesibilidad de esta raíz. No se escribe
para probar permisos. Estos datos sustituyen el inventario histórico del05-10,
que sí contenía componente visual; no se demuestra quién/cuándo lo retiró.

Logs tras arranque actual: close_auto_update_map informa `Call init_tracker first`
con estadoREADY. Primer save_auto_update_map23:24:41 nativo devuelveMAP_DIR_ERROR;
posteriores enable/close/save también devuelven ese estado. Nav_taskmanager
termina navigation_start SUCCEEDED pero incorpora fallo auxiliar VSLAM.
Diario152706 confirma status4 y descVSLAM_MAP_DIR_ERROR, que el ejecutor rechaza.
Explicación sustentada: guardado visual falla con tracker sin inicializar y sin
componente visual en el mapa actual. Modo efectivo LiDAR/fusion no quedó demostrado
por los logs acotados; no afirmar que se completó localización visual ni llegada
física independiente. En historial anterior mapa utars_nav_map.5 cargó componente
vslam; no reutilizar automáticamente ese mapa/marco para el mapa vigente.

**Continuación:** verificar el tipo de cartografía seleccionado y si la intención
es disponer de mapa visual+LiDAR o LiDAR exclusivo. Si falta componente visual,
respaldar mapa actual y revisar captura/guardado compatible antes de reemplazarlo.
Un mapa LiDAR exclusivo requeriría soporte explícito en escenario y validación
independiente de poses/llegada; no ignorar genéricamente MAP_DIR_ERROR. No copiar
sólo carpetas desde mapas antiguos ni crear directorios vacíos: marcos/archivos
no quedan coherentes por ello. Esta revisión no autoriza modificación/remapeo.

Cambios persistentes sólo esta documentación PC; sin mapa recargado, reinicios,
configuración, movimiento ni relajación del ejecutor. Evidencia/comandos/resultados:
../Humanoide-vla-evidence/20261006_VSLAM_MAP_DIR_READONLY/ con before/after/,
map-files.json, map-container.json, logs e inspect archivados y SHA256SUMS.
Reversión documental selectiva desde before/ conservando cambios posteriores.
Verificación: lecturas reales anteriores y git diff --check; causa de cambio de
mapa, modo efectivo, reparación y validación física PENDIENTES. Sin commit/push.


## MAP-VISUAL-RECOVERY-CANDIDATE-20261006 — new6 persistido

**06-10-2026, Europe/Madrid. OBSERVADO / integridad VERIFICADA por lectura.**
Usuario pide localizar archivos y evaluar recuperación. Inventario Vision tras
redescubrir contenedores: `/etc/walker/map/new6/vslam/` conserva source_map y
localization_map con map.pb, features_des_0.pb y mixvpr_descriptor.h5, calibración,
trayectoria/imagen, landmarks y versiónv2.1.0. 492 archivos y141 filas de
mapping_pose.csv. Archivos principales guardados06-10,20:51:49–20:51:50 hora
nativa; ruta candidata tiene únicamente vslam, sin umap/LiDAR/tareas.

Se calcularon SHA256 reales por lectura en ambas carpetas: los seis archivos
(features_des_0.pb/map.pb/mixvpr_descriptor.h5) coinciden con map_hash.txt de
su carpeta. Source map.pb aae0ae7029b9d3f1bd13df59ee1aaa411ff1d6e9498a297a93ee2064c0e2d101;
localization map.pb ef4c5a9c3e986dfea6baa62e100220d3499b9963da7caf7e4bf0463cb08b5e5a.
Esto prueba conservación de esos archivos, no relocalización física/compatibilidad.
La hipótesis anterior de estado sólo en memoria queda sin confirmar; existe
captura visual persistida bajo OTRO nombre. Su identidad con el último mapa
LiDAR y la causa de separación de nombres siguen PENDIENTES.

`utars_nav_map` vigente conserva LiDAR/umap/get1/put1 pero no vslam.
`utars_nav_map.5/vslam/` ahora sólo contiene localization_and_updateRig.txt;
no es copia completa. Logs históricos archivados muestran carga de map.pb desde
utars_nav_map.5 a21:17, antes del reinicio15:17UTC; no se demuestra causa de su
posterior desaparición. Otras carpetas mapatest/mapanuevo/utars_nav_map_old y
old2/old3 contienen mapas visuales anteriores, de fechas/marcos distintos.
No se restauran ni se mezclan por compartir lugar/nombre parecido.

Búsqueda acotada de map.pb/mapping_pose.csv en /etc/walker,/home,/tmp,/var/tmp:
encuentra candidatas anteriores; retorna1 por rutas no accesibles, no es búsqueda
exhaustiva. Consulta de logs docker12h agotó18s; grep de archivos map_manager
no aportó líneas de renombrado/copia. Ruta exacta del guardado/conversión y
correspondencia de marcos no quedaron demostradas. No atribuirlo a pérdida de
disco, permisos o fallo de guardado sin datos adicionales.

**Recuperación:** hay datos visuales íntegros candidatos, por lo que no debe
asumirse necesario remapear desde cero. Recuperación operativa PENDIENTE:
respaldar externamente mapa vigente y new6, determinar correspondencia visual–
LiDAR/calibración y reconstruir/cargar mediante receta compatible conservando
originales; verificar relocalización estable, marco y destinos después de
arranque. Si los marcos difieren, recrear destinos tras validar el mapa conjunto.
No copiar simplemente vslam sobre utars_nav_map ni renombrar sin validación.
Esta petición sólo autoriza diagnóstico; no se efectuó restauración/carga.

Evidencia/comandos/respuestas/hashes y limitaciones:
../Humanoide-vla-evidence/20261006_MAP_RECOVERY_SEARCH/ (candidate-files.json,
candidate-metadata.json, candidate-integrity.json e inventarios/logs). before/
after/ para documentación PC y SHA256SUMS; rollback documental selectivo desde
before/ conservando cambios posteriores. Sin copia de paquetes/mapas binarios a
Git, sin modificaciones remotas, acciones de control, reinicios o movimiento.
Verificación de documentación git diff --check; relocalización y recuperación
física PENDIENTES. No commit/push.


## MAP-RECREATED-CHECK-20261006 — guardado LiDAR, escenario pendiente

**06-10-2026, Europe/Madrid. OBSERVADO por lectura.** Usuario comunica borrar y
crear utars_nav_map; agente no realiza esa modificación. Consulta tras descubrir
contenedores: nuevo version.txt20261006_233914 hora nativa, taskID
2026-10-06-23-39-14-9dc8fcba. LiDAR map.pcd131834bytes y graph.bin1106786bytes,
umap creado608×800. Mapping2D registra guardado umap/task/graph correcto
(node13/edge15); navegador FSM_Mapping SUCCEEDED a23:39:14,747.

No get1/put1: umap.target_points=[] y task.target_points=[]. No componente
vslam/map.pb ni mapping_pose.csv en este nuevo mapa. Logs VSLAM acotados12min
no muestran captura/guardado de esta nueva creación. mapping_start23:38:20
informa clave map_type ausente, seguido mapping_mode leído; modo efectivo no
se deduce sólo de esa advertencia. No se afirma integridad/calidad visual.
Tras guardar, FSM_WAITSETMAP; últimas respuestas get_map_name del navegador
a23:39:28 devuelven nombre vacío. Son registros pasivos, no estado permanente.
No se envía get_map_name/check_state para evitar preemptar tareas actuales.

**Continuación:** seleccionar mapa nuevo y establecer get1/put1 en su marco;
verificar si se quiere cartografía visual+LiDAR y corregir captura/guardado antes
de transporte. Persiste ausencia visual asociada al fallo previoMAP_DIR_ERROR;
no ejecutar ciclo esperando que el mapa actual lo resuelva. Relocalización,
pose estable y correspondencia con escena real pendientes. No trasladar destinos
antiguos sin validación. Mapa LiDAR guardado no equivale a escenario listo.

Corrección del candidato anterior: operador aclara que new6 era OTRO mapa.
DESCARTADO como recuperación confirmada de utars_nav_map aunque sus archivos
sean íntegros; no mezclarlo ni restaurarlo sobre este mapa. Hipótesis de datos
sólo en memoria y causa de ausencia del mapa visual original no confirmadas.

Cambios persistentes del agente sólo documentación PC; sin acciones cliente,
carga/relocalización, configuración, reinicios o movimiento. Evidencia y recetas
de consultas archivadas: ../Humanoide-vla-evidence/20261006_RECREATED_MAP_CHECK/
(files.json e inventario/docker logs), before/after/ ySHA256SUMS. Reversión
documental selectiva conservando cambios ajenos. Comprobación git diff --check;
creación de destinos/captura visual/validación física PENDIENTES. Sin commit/push.


**06-10-2026 — MAP-VISUAL-BRANCH-DIAG. OBSERVADO / INFERENCIA indicada.**
Leído mapping.xml instalado en nav_taskmanager, sin acciones: mapping normal
elige por map_type. fusion inicia start_vslam_mapping y guarda VSLAM save_map
junto con LiDAR; uslam inicia/guarda sólo Mapping2D. Logs del nuevo mapa:
mapping_mode normal, petición sin map_type, guardado LiDAR correcto y ninguna
orden de captura/guardado VSLAM en ventana consultada. Evidencia compatible con
rama uslam (INFERENCIA); valor efectivo/herencia/configuración UI PENDIENTES.
No se demuestra fallo de escritura visual: no se solicitó su guardado en la
secuencia registrada. Evidencia XML: ../Humanoide-vla-evidence/20261006_MAPPING_VISUAL_BRANCH_DIAG/;
logs en20261006_RECREATED_MAP_CHECK. Revisión sólo lectura, sin modificar modo,
árbol o mapa. Respaldos/documentación before/after/; reversión selectiva.


## MAP-WEB-MODE-20261006 — UI omite map_type

**06-10-2026, Europe/Madrid. VERIFICADO por lectura de fuentes desplegadas.**
Operador usa http://192.168.11.3/map/mapManager. Nginx sirve aplicaciónmain.
Bundles async1348.3578c594.js y4370.173fbc6e.js contienen el inicio normal de
mapeo vía ROSLIB a nav_task_manager: command=mapping_start, arg_json con
map_name y mapping_mode=normal, SIN map_type. Extensión también omite ese campo.
No se pasa por el controlador HTTP de web-backend para esa orden: JS usa acción
ROS mediante WebSocket. No se prueba caché del navegador ni cliente cargado por
el operador; fuentes actuales desplegadas coinciden con campo ausente del log.

Esto explica por qué usar la misma página no garantiza modofusion: UI delega
map_type al navegador. mapping.xml decide captura/guardado visual por ese
valor, y la secuencia observada sólo grabó LiDAR. Valor efectivo/default y
por qué difiere de antes del reinicio siguen PENDIENTES: búsqueda acotada de
map_type en yaml/json de configuración no devuelve resultado, sin deducir
default inexistente. No se afirma que cambió software o que UI borró archivos.
La hipótesis concreta de uso previo de estadofusion en memoria no se demuestra.

Evidencia/fuentes exactas/respuestas:
../Humanoide-vla-evidence/20261006_MAP_WEB_MODE_READONLY/ (lazy-mapping-code.json,
frontend-paths.json, configuración consultada). Consultas de sólo lectura por
SSH/docker exec; no modo cambiado, acción ROS, recarga, mapeo o movimiento.
Fallos iniciales de execbash (contenedores sinbash) resueltos usandosh;
no son fallos del robot. Documentación PC respaldada before/after/ ySHA256SUMS;
reversión selectiva preservando cambios posteriores. git diff --check correcto.
Corrección de petición explícitafusion requiere intervención separada con backup
y validación compatible; no se altera UI/SDK ni se envía ahora ese comando.


## MAP-TYPE-INHERITED-USLAM-20261006 — origen del cambio de captura

**06-10-2026, Europe/Madrid. OBSERVADO por lectura; enlace causal INFERENCIA
sustentada.** Continuación autorizada: comprobar valor omitido y peticiónfusion,
sin iniciar captura. Logs de nav_taskmanager desde arranque actual: a23:21:51,
23:22:17 y23:22:39 nativos fsm_set_map informa `No vslam map, use uslam mode
while set map.`, campo map_type ausente y `Last use map_type: uslam`.
Relocalización también informa uslam. Web posterior inicia normal23:38:20
sin map_type; captura/guardado registrados sólo Mapping2D. Evidencia del modo
previo uslam VERIFICADA; herencia efectiva durante nueva captura INFERENCIA
coherente con árbol, petición y ejecución, no lectura interna de blackboard.
No es prueba de cambio de firmware/UI ni fallo de escritura visual.

La misma UI no fija tipo: seleccionar un mapa sin componentevisual puede
cambiar el estado del navegador a uslam; siguiente inicio omite tipo y no exige
fusion. El reinicio previo perdió estado tracker visual, pero no se identifica
con estas consultas cómo/quién produjo originalmente el mapa sin vslam.
No atribuir toda la cadena a borrado automático ni a error del operador.

**Petición explícita revisable (NO ENVIADA):** acción de navegación existente,
command=mapping_start, arg_json con map_name nuevo, mapping_mode=normal,
map_type=fusion. Ejemplo versionado de datos:

```json
{
  "map_name": "utars_nav_map_fusion_review",
  "mapping_mode": "normal",
  "map_type": "fusion"
}
```

mapping.xml desplegado confirma ramasfusion que llaman start_vslam_mapping
al inicio y VSLAMsave_map al guardar, junto con Mapping2D. No basta añadir
fusion al guardado después de capturar sólo LiDAR: debe activarse desdeinicio.
Usar nombre nuevo/backup antes de modificar para preservar mapaactual; pruebas
requieren condiciones físicas actuales, control exclusivo/persona juntoparo.
No se publica esta petición, no se cambia UI ni estado, no se inicia mapeo.
Integración de inicio explícito en UI/script y prueba física PENDIENTES.

Consultas: docker exec find/rosa--help y dockerlogs filtrados acotados2h;
ROSAhelp no ofrece param (no se intenta modificar estado ni daemon). Sin valor
hallado en YAML/JSON; dato definitivo obtenido del diario del propio navegador.
Evidencia: ../Humanoide-vla-evidence/20261006_MAP_TYPE_DEFAULT_READONLY/
(nav-startup.json, explicit-fusion-request.json ilustrativo, before/after/,
SHA256SUMS). Cambios persistentes sólo documentaciónPC. Reversión selectiva
before/ preservando modificaciones posteriores; git diff--check correcto.
Sin arranque/carga/relocalización, reinicios, movimiento, commit/push.


## MAP-FUSION-CONFIG-AUDIT-20261006 — configuración desplegada revisada

**06-10-2026, Europe/Madrid. OBSERVADO, sólo lectura.** Usuario pide verificar
configuraciones para uso de fusion desde web. Docker inspect de nav_taskmanager,
web y web-backend: sin variablesMAP_TYPE/fusion/uslam/vslam; nav arranca `rosa run
nav_taskmanager nav_taskmanager_node -- -p nav_commonwalker_config_utars`.
Paquetes de configuración instalados contienen árbolesXML y bag_recorder.yaml;
no parámetro map_type encontrado en YAML/JSON consultados. Búsqueda posterior
145 archivos de configuración legibles en /etc/walker (excluye bag/map/log y
modelos; extensionesyaml/yml/json/toml/ini/conf) tampoco devuelve map_type o
default_map_type. Es búsqueda delimitada, no demostración de inexistencia de
cualquier opción interna del binario o ajustes no enumerados.

Assets main/utars revisados no contienen literalesfusion/map_type; inicio normal
ya observado usa ROSLIB sin dicho campo. No se demuestra selectorfusion o
variable de entorno admitida para la web. BackendHTTP no interviene en ese
inicioROS directo. mecanismoVERIFICADO: navegador registra fallbackuslam al
cargar mapa sin visual; mapping.xml usa map_type para elegir captura/guardado.
Alternativa concreta sustentada: peticiónmapping_start explícitafusion desde
inicio. No crear parámetro inventado ni modificar XML para forzar ramasglobales.

Esta verificación NO modifica web/navegador/robot. Ajuste para que el botón
envíefusion requiere cambio revisable separado, respaldo y validación de captura,
guardado y arranque; ningún mapeo/prueba física ejecutado. No se publica acciónROS,
se cambia estado, reinicia o instala. Evidencia/configuraciones/comandos:
../Humanoide-vla-evidence/20261006_FUSION_CONFIG_AUDIT/ (container-config.json,
web-fusion-config.json, navigation-config-paths.json, persistent-config-audit.json),
backup documentaciónbefore/after/ y SHA256SUMS. Primer intento buscó directorios
config convencionales inexistentes (0archivos); corregido con inventario real y
145archivos. Rollback documental selectivo. git diff --check correcto;
implementación en web/ensayo físico PENDIENTES. Sin commit/push.


## MAP-WEB-EXPLICIT-FUSION-20261006 — inicio normal con tipo explícito

**06-10-2026,17:57 Europe/Madrid. INSTALADO y servidoHTTP VERIFICADO;
navegador del operador/captura/guardado físico PENDIENTES.** Usuario autoriza
cambiar la web; pide cerrar/documentar si requiere más de4min antes de apagar.
Intervención terminada sin órdenesROS, movimiento, carga, mapeo ni reinicios.

**Objetivo/destino exacto:** Vision192.168.11.3, contenedorwalker-web.web-1,
/usr/share/nginx/html/main/static/js/async/1348.3578c594.js y4370.173fbc6e.js.
En cada archivo, único literal `mapping_mode:"normal"` pasa a
`mapping_mode:"normal",map_type:"fusion"`. Son las dos implementaciones de
inicio normal desplegadas. Conserva nombre, comando y resto del bundle.
No modifica extensión/mapping_consistency, tareas/navegación/grasp o XML vendor.
El botón normal deja de depender del modo heredado del navegador.

**Fuente reproducible/versionado:**
[scripts/patch_web_map_fusion.py](../../scripts/patch_web_map_fusion.py),
[test](../../scripts/test_patch_web_map_fusion.py). Script Python3 ejecutado en
hostVision, usa docker exec y contenedor descubierto. Pinea SHA256 originales,
comprueba ambos antes de mutar, respalda original/nuevo+manifest, sustituye
archivos atómicamente conservando permisos, comprueba bytes y revierte en fallo
sin sobrescribir cambios ajenos. Rechaza versiones desconocidas/backups ya
existentes; no aplicar ciegamente tras actualización.

Hashes anterior→nuevo:
-1348:21fcdd17089da3caf9c403f515930086c83337c1c423055bd4bc61dbe9480490
→55b1f38a5d73749ea0bea9110f4a045b6aa11d2b833a6d2ecb8f9dc4df993a52.
-4370:701589ec445cf5c3279c0ef7f2c01c276851466072c47b08411e5d8236f42fb2
→f00085d6e20ef2e0b67e330a0295016d2ccaaf839ad4c28f7d2d612e819a75fe.

**Aplicación realizada:** check y apply remotosrc0. Backup persistentehost:
/etc/walker/customizations/web-map-explicit-fusion-20261006/ conbefore/,after/,
manifest.json yapply.py (misma fuente del repo). Fuentes y backup externo PC:
../Humanoide-vla-evidence/20261006_WEB_EXPLICIT_FUSION/. No depender dehistorial/
tmp para reconstruir. Para futura aplicación sobre originales compatibles,
transferir scriptversionado aVision y ejecutar (nueva ruta backup inexistente):

```bash
python3 /ruta/patch_web_map_fusion.py check --backup-dir /etc/walker/customizations/web-map-fusion-NUEVA-FECHA
python3 /ruta/patch_web_map_fusion.py apply --backup-dir /etc/walker/customizations/web-map-fusion-NUEVA-FECHA
```

**Verificación:**2tests offline pasan; ambos bundles completos modificados pasan
`node --check`. Patch remoto lee/checks hashes y confirma escritura exacta.
HTTP GET192.168.11.3/static/js/async/{archivo}: ambos hashes iguales al esperado
yuna peticiónnormalfusion en cada uno. Nginx sirve inmediatamente; sinreload/
restart. git diff--check correcto. Estos checks no demuestran que navegador del
operador descargó código nuevo ni que el mapa visual se haya capturado.

**Activación/punto de reanudación mañana:** recarga forzadaCtrl+Shift+R enweb
antes del próximo inicio. Con condicionesfísicas y control exclusivo comprobados,
crear mapa bajo nombre nuevo desdeinicio normal, recorrer yguardar; confirmar
órdenesVSLAMstart_mapping/save_map y archivosvisual+LiDAR del mismo mapa.
Seleccionar/relocalizar y validar tras siguiente arranque; comprobar destinos
actuales antes del escenario. No se prueba hoy ni se regenera automáticamente
utars_nav_map. La modificación no añade datosvisual a mapas ya grabados.

**Reversión concreta (sólo archivosweb):** enhostVision:

```bash
python3 /etc/walker/customizations/web-map-explicit-fusion-20261006/apply.py restore --backup-dir /etc/walker/customizations/web-map-explicit-fusion-20261006
```

Script exige hashes del cambio instalado antes derestaurar y del respaldooriginal;
no restaura mapa/estado decontrol. Después recarga forzada navegador. Código
webmodificado está en capa escribible del contenedor: persiste al reinicio normal,
pero recrearlo/actualizar la imagen puede retirarlo. Tras actualización seguir
CRUZR_REAPLICAR_CAMBIOS_TRAS_ACTUALIZACION, comprobar compatibilidad yreaplicar
selectivamente. Ficha conserva criterio instalado/servido y pruebas pendientes.

Evidencia before/after, check.json/apply.json, http-verification.json,
remote-recipe.json, tests.log ySHA256SUMS externos. Documentaciónanterior exacta
respaldada antes del cambio; no commit/push. Ningún mapa/cámara/firmware/mode/
watchdog/localización/paros/límites cambiado por el agente.


**06-10-2026 — MAP-CAMERA-VIEW-DIAG. OBSERVADO, sólo lectura.**
Tras parcheweb, operador muestra track_image vacío/diálogo guardado.
Inicio registrado23:57:47 nativo sigue sin map_type; sin start_mappingVSLAM en
ventana8min. Streaming a23:58:07–09 informa topic/vnav/vslam/track_image not
exists. InventarioROSA actual contiene topicsstereo_left/right image/raw y
stereocolor/depth pero no track_image; presencia no demuestra imágenes frescas.
HTTP actual todavía sirve ambosbundles fusion (1 peticiónnormal cada uno).
Cliente en caché/anterior compatible (INFERENCIA), sin comprobarDevTools real.
No se confirma avería de cámara ni captura visual. Esperar fin/resultado guardado
sin recargar durante operación; despuésrecarga forzada y verificar nuevoinicio
fusion antes de recorrer/guardar nueva captura. No se envía parada/reinicio/
ROScontrol ni se modifica web en esta consulta.
Evidencia: ../Humanoide-vla-evidence/20261006_MAPPING_CAMERA_READONLY/;
backupsdocumentales before/after/ ySHA256SUMS, rollbackselectivo. Validación
documental diff--check; captura/guardado fusión permanecenPENDIENTES.


**06-10-2026 — MAP-LIVE-CAPTURE-CHECK-20261006. OBSERVADO por lectura.**
Operador dice grabaciónactiva. Nav a00:04:55nativo (06-10,18:04:55CEST) acepta
mapping_startutars_nav_map/normal con map_typeausente; Mapping2DMAPPING_NORMAL
continuado. VSLAM no registra inicio visual enventana3min; suscripciónROSA
posterior de sólolectura devuelveMAP_DIR_ERROR. No se confirma mapa visual en
captura; fase observada sóloLiDAR. Parche servido no demuestra uso encliente;
caché/cliente/otra petición sonposibilidades sinverificar. No detener/reiniciar,
recargar página enoperación o arrancarVSLAM deforma tardía desdeestediagnóstico.
Tras guardar/terminar acción, comprobar cliente actualizado y próximo inicio
fusion antes de recorrido. Evidencia: ../Humanoide-vla-evidence/20261006_LIVE_MAPPING_CAPTURE_CHECK/;
backupsdocumentales before/after ySHA256SUMS, reversiónselectiva. Sin comandos
control/configuración/movimiento. diff--check correcto; captura fusionPENDIENTE.


## MAP-FUSION-SAVE-VERIFIED-20261007 — captura visual persistida

**07-10-2026, Europe/Madrid. Guardado/integridad/carga VERIFICADOS por lectura;
relocalización/calidad física y próximo arranque PENDIENTES.** Usuario comunica
nueva grabación. ContenedoresVision redescubiertos; no accionescliente/map_set/
relocation_start, reinicios ni movimiento enviados por agente.

utars_nav_map nuevo version20261007_182902 ytaskID
2026-10-07-18-29-02-dd6b228a (hora nativa). Guardado conjunto: uslam_2d/map.pcd
257932bytes, graph.bin2771476bytes, umap/user; AHORA existevslam/source_map y
localization_map con map.pb/descriptores/calibración. Source map.pb1088443bytes,
localization map.pb922858bytes.285archivos visuales,90filas deposes; primera/
última captura1791368852,129722–1791368932,850299 (~80,721s entre filasextremas,
no duración total de sesión). Cada parte verifica exactamenteSHA256 de
features_des_0.pb,map.pb,mixvpr_descriptor.h5 contra su map_hash.txt (6/6).
Source map.pb3c37cee95bc5b741e91f20daa5f0ace425bbb732d4e05870e67b2632a68997d9;
localizationmap.pbd83ebd9c63c4fe2a90568f90b75c50feea24a9883faf07ad955c3eba9f78abb4.

VSLAM recibe save_map mientrasMAPPING_RUNNING a18:29:02,306nativo; guarda a
/etc/walker/map/utars_nav_map/vslam y terminaSAVE_MAP_SUCCEED18:29:03,380.
Navegador confirmaFSM_MappingSUCCEEDED. Posterior selección por operador:
Last use map_type:fusion y set_mapVSLAMSUCCEEDED/LOAD_MAP_FINISHED18:29:28.
Advertencia update_vslam ausente no impide esta carga; no crearfragmento vacío.
Después navegadorFSM_WAITRELOCATE; lecturaROSA posteriorVSLAM=LOAD_MAP_FINISHED.
Carga correcta no equivale a localización estable, precisión/alcance de cajas
ni recuperación tras próximo apagado. No se ensaya ni ordena relocalización.

user/task y umap conservan destinos vacíos; operador ya sabe que falta get1/put1.
No se da por listo escenario ni se reutilizan coordenadas anteriores.
La captura/prueba de guardado conjunto sí demuestra que ya se ejecutó componente
visual, quefaltaba en intentos del06-10. No se afirma calidadpor conteo deposes.
Próxima comprobación: relocalización supervisada y correspondencia pose-real;
verificar persistencia/carga tras siguiente arranque ydestinos delmarco actual.

Evidencia/recetas deconsultas: ../Humanoide-vla-evidence/20261007_NEW_MAP_SAVE_CHECK/
(inventario, map-files.json, visual-integrity.json, logs yvslam-state.json).
Agente sólo modifica documentaciónPC, respaldada before/after ySHA256SUMS;
rollbackdocumental selectivo preservando cambios posteriores. Sin configuración
remota persistente o archivosdemapa modificados. git diff --check correcto;
sin commit/push. Clientewebcargado y causa exacta de cambio de peticiónno se
inspeccionan, aunque ejecuciónvisual yguardado presentes quedan demostrados.


**07-10-2026 — HEALTH-SAFETY-STALE-DIAG. OBSERVADO offline.**
Intento104340_885613 falla enhealth inicial5,70935s antes deready/arm/etapa1.
Collector.complete rechaza edadrecibo de cualquiera estop/servo/charger/battery
>2s (o edadnegativa por reloj). Actuatormuestras habían pasado su comprobación;
error no informa canal/edadconcreta, por loque no atribuirlo a Wi-Fi, batería,
paroactivado o mapa. Iniciohealthworker/session_ready confirmado, request1
termina78 porobsolescencia; no navigation/grasp enviado porestaejecución.
Estadofísicoactual no comprobado. Sólo lectura local, sin cambioejecutor/límites,
consultasremotas o movimiento. Evidencia/backupsdocumentales selectivos:
../Humanoide-vla-evidence/20261007_SAFETY_SAMPLES_STALE_DIAG/.
