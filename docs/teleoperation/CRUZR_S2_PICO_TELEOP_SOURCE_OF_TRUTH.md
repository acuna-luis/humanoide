# Cruzr S2 + PICO: fuente de verdad de teleoperación

**16-10-2026 — PICO-CAMERA-USB-20261016: vídeo en preparación, control en STOP.**
Operador pide cámara tras abortar --teleoperate por valor no admitido de
PICO_TELEOP_CAMERA; main es la fuente frontal estéreo izquierda. Check pasivo
PC7/7 confirma vr_status1/STOP y ruta Motion/Vision por eno1/.11.250. Sin START.
UI real XRoboToolkit1.1.1: Remote Vision → ZEDMINI → Listen → IP del PC,
no Camera/Request PC camera data. Confirmado en captura del visor, APK local y
fuentes oficiales tagv1.1.1/commit9f775b535d781618bd2bb7ef8d6c414c0531387c.
Tras confirmar el operador, PICO escucha12345. No tiene usb0 actualmente;
se crea exclusivamente adb forward --no-rebind tcp12345→tcp12345 para vídeoUSB,
con puertoPC y lista previa libres. ReverseXR63901 conservado.
La cámara mono requiere duplicar su imagen completa en dos mitades para el
perfil ZEDMINI2560×720; adaptación PC GStreamer preparada/en validación, sin
instalar paquetes. No representa profundidad estéreo. FuenteSRS/discovery ROS
verificados; todavía sin stream ni imagen en este punto.
Evidencia `../Humanoide-vla-evidence/20261016T084628Z_PICO_CAMERA_USB/`,
inventario antes/recibo de forward/captura/listeners y copias de fuentes previas.
Rollback: cerrar sólo vídeo, verificar heartbeat/SRS sin residuos y quitar sólo
forward12345 creado; conservar reverse63901 y configuración de control.

**16-10-2026 — PICO-XR-USB-20261016: USB y seguimiento VERIFICADOS.**
Tras migración a v4 y HOME, operador solicita configurar gafas. PICO físico
PA94Y0MGKB070822G por USB, Awake y XRoboToolkit abierto. Backend STOP confirmado
pasivamente, sin pico_control; servicio XR escucha63901. Reverse antes vacío;
se ejecuta `bash scripts/teleoperation/configure_pico_xr_usb.sh --configure` y
`--check` confirma mapping tcp63901→63901. Antes del cambio existía socket
192.168.224.184→192.168.224.6:63901 por red compartida USB; no llamarlo Wi-Fi
ni dar por demostrado que el flujo usa ahora loopback. PC→Motion por
Ethernet eno1, 192.168.11.250; red del robot conservada. Check v4 cámaraoff pasa
PC/red/identidad y bloquea por vr_status0. Se pide al operador conectar a
127.0.0.1 y activar Head+Controllers/Senddata, sin Hands/Y/grips/gatillos.
Actualización 10:34 Europe/Madrid: operador confirma Connected/Working y Send
data. Check pasivo PC completo7/7, rc0, identidad correcta, vr_status1 y
operation_type1 (STOP). Coexisten TCP loopback por ADB y socket previo de
redUSB .224.184→.224.6; no atribuir el stream exclusivamente a uno.
Transporte USB disponible y seguimiento demostrado. Comprobación sólo de PC/XR;
no certifica que la tarea TeleopMode v4 esté cargada. Mantener visor despierto
y puesto; la suspensión puede parar el seguimiento.
Sin START, cambio de modo o movimiento enviado. Túnel transitorio; reversión:
`bash scripts/teleoperation/configure_pico_xr_usb.sh --remove` con backend STOP,
y restaurar IP de la app sólo si se quiere volver al transporte anterior.
Evidencia privada `../Humanoide-vla-evidence/20261016T083300Z_PICO_USB_CONFIG/`
(inventario before/after, receta/hash y copias documentales previas).

**16-10-2026 — SWITCH-EFFECTOR-RESTORE-20261016: restauración CORREGIDA y cambio a v4 VERIFICADO.**
La sesión `EFFECTOR-20261016T081258Z-1bddf143` instaló SPS y recreó los nueve
servicios Motion y CC; falló antes de arrancarlos al restaurar historiales sobre
bind mounts de CC. Respaldos externos e internos íntegros. Lectura fresca:
contenedores creados/detenidos, principal pulsado, servos liberado, cargador fuera,
baterías 88,3/89,2%. Sin HOME ni START PICO enviados.
Corrección local: excluir montajes también en respaldos antiguos y omitir copia
vacía; reanudar la misma sesión mediante `--resume-from`, sin repetir recreación.
[Receta y límites](../guides/CAMBIO_EFECTOR_ABRAZADERAS_MANOS_V4.md). Reanudación ejecutada: Motion restaurado verificado, Vision sin copia sobre
montajes (restauración efectiva vacía), servicios arrancados bajo paro. Tras
confirmación del operador y liberación manual, HOME20D medido en dos muestras
avanzantes, velocidad0, sin fallos, delta máximo0,002876rad y estados válidos
avanzantes de siete ejes por mano. dexterous_hand_controller running.
Resultado PERFIL_Y_HOME_VERIFICADOS=v4; sesión cerrada en ambos hosts tras
comprobar archivos. No reinicio físico ni HOME adicional. Siguiente paso:
entrada controlada a PICO v4 con sus gates actuales; no se inició teleoperación.
Evidencia privada: sesión original, `recovery/` y
`EFFECTOR-20261016T082431Z-0cf31f55`. No borrar `active.json`.

**16-10-2026 — PICO-V4-GATE-20261016: bloqueo por tarea clamp, diagnóstico VERIFICADO.**
Operador confirma reinstalación de manos v4 ante pregunta de montaje con robot
apagado. Lectura nueva: hw/app/CC siguen HW_TYPE=cruzr_s2_v1 y restart0.
CC entra TeleopMode y el último arranque de tarea es cruzr_clamp_pico_teleoperation,
Hand type clamp, waist0/leg0. YAML v4 conserva SHA esperado01a5ca8…; no es
corrupción del archivo. Faltan topics MC de estados de manos bajo este perfil.
El mensaje genérico del lanzador es anterior a START; en este caso no encontró
la tarea v4 requerida. Repetir el mismo --teleoperate no cambia el perfil nativo.
Muestra20D: reposo0, sinfallos, delta0,003230rad, maxposición1,568783rad,
MEASURED_HOME0: postura inicial PICO/clamp. No inferir HOME del chequeo de arranque
anterior. No enviar HOME, reiniciar ni cambiar modos para probar desde ahí.
Migración SPS y posterior entrada controlada a Teleop v4 pendientes. La guía del
selector contempla --secured-recovery con brazos asegurados, paros/cargador y
verificación; no se ejecutó en esta intervención. El selector termina en HOME,
no activa por sí mismo TeleopMode ni STARTPICO.
Evidencia privada `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20261016T081039Z_PICO_V4_GATE_READONLY`: perfiles/instancias, logs actuales, último bloque de
tarea, hashYAML, inventario y muestra/clasificación. Solo lectura, cero cambios
remotos/movimientos; copias documentales before-docs y SHA256SUMS en evidencia.


**15-10-2026 — SWITCH-EFFECTOR-20261015. Entrada bidireccional preparada.**
`bash scripts/hands/cambiar_efector.sh --to clamp|v4 --check|--apply|--verify`.
Unifica fuentes persistentes, respaldo/recreación conservando personalizaciones,
espera de paro y verificación de HOME/manos; no inicia PICO ni cambia su conexión.
Usar después probar_pico.sh para clamp o probar_pico_v4.sh para manos instaladas.
29 pruebas offline pasan y --check se consulta en ambos sentidos. No se ejecutó
--apply nuevo; validación física integral pendiente. Lectura de verificación
observa postura fuera de HOME y no la certifica, sin correcciones del agente.
[Procedimiento y límites](../guides/CAMBIO_EFECTOR_ABRAZADERAS_MANOS_V4.md).


**15-10-2026 — BOOT-CC-SPS-20261015 / selector CC:** HW_TYPE SPS instalado y
sólo CC recreado con mismaimagen/orden/montajes. Guard de arranque actualizado
para reconocer identificadorSPS conservando gates yvoz;18tests pasan.
Principal1 ybrazos asegurados confirmados; Motion no reiniciado, sinHOME/START.
Consignas latentes siguen pendientes: apagado supervisado en preparación,
paro mantenido. Detalle/rollback/evidencia en PICO_MANOS_V4_20261015.


**Ampliación 15-10 — postura PICO incompleta:** logs HW confirman rechazo
`send a jump command` (>0,087rad) en cuatro ejes, no contacto según operador.
Cancelación a auto_task deja consignas latentes~1,57rad; HOME/reset/rearme
bloqueados por guía de recuperación. Sin nuevos movimientos/restart.
Selector CC preparado offline en prepare_pico_v4_cc_env.py (sólo CC, no global),
NO instalado. Recuperación documentada y corrección/ensayo todavía pendientes.
Detalle/evidencia en PICO_MANOS_V4_20261015 y20261015_PICO_V4_PROFILE.


**15-10-2026 — PICO-V4-CC-SELECTION-20261015: PICO aún NO habilitado.**
CC con HW_TYPE antiguo seleccionó tarea clamp al entrar en teleop; Motion síSPS.
Inicialización de brazos incompleta/asimétrica, medida/consigna difieren~1,57rad.
Se cancela pasando a auto_task; velocidad medida0/sinfallos, consigna antigua aún
no coincide. Sin START PC ni HOME; no declarar postura lista ni teleop v4 probada.
Selector CC, recuperación a HOME y ensayo v4 pendientes. Detalle en ficha PICO v4.
Evidencia20261015_PICO_V4_PROFILE fueraGit; no restart/cambioenvCC en esta fase.


**15-10-2026 — PICO-V4-PROFILE-20261015: SPS CARGADO; HOME y estados v4 VERIFICADOS.**
[Estado, receta, respaldos y reversión de manos v4](PICO_MANOS_V4_20261015.md).
YAML v4 sólo brazos instalado, no cargado; HW_TYPE SPS aplicado y Motion recreado.
Selector PC y comprobación de siete articulaciones preparados,19 tests pasan.
HOME medido antes del paro; operador confirma paro principal pulsado para migración.
Respaldos Motion/Vision externos y hashes verificados. Ethernet eno1 confirmado.
Mismas imágenes,3+59 archivos restaurados/verificados; operador libera paro.
CC termina StartMotion y JoystickMode; HOME20D máximo0,002493rad/velocidad0/sinfallos.
Ambos controladores v4 cargados; estados frescos7ejes/mano pasan checker ROS2.
Sin START PICO: tarea TeleopMode v4, ensayo de gatillos y replay aún pendientes.
No se requiere otro reinicio; seguimiento posterior sólo lectura.
Evidencia privada ../Humanoide-vla-evidence/20261015_PICO_V4_PROFILE/.


**15-10-2026 — HANDS-V4-BUS-IDENTITY-20261015: INSTALADO y CARGADO; arranque verificado.**
Actualiza el estado offline anterior. Operador confirma manos vacías, trayectoria
libre, otros mandos detenidos y persona junto al paro. Aclara finalmente paro
principal liberado. Antes de recarga: lecturas nuevas principal0/servo0,
cargador0 (antes se observó carga2; no se omitió el bloqueo), baterías84,1/71,7%.
Las consultas iniciales de paros con timeout corto expiraron; tipo UInt8 explícito,
RELIABLE/VOLATILE y timeout10 recibieron0/0. No se fingieron estados.

Aplicación reproducible desde PC, sin activar por este instalador:
`python scripts/hands/install_v4_bus_profile.py --check --evidence /RUTA`
y `--install` en lugar de `--check`. Instalador verifica hash original y PID1
esperando arranque, conserva propietario/permisos y sustituye atómicamente.
Acepta un perfil ya corregido como comprobación sin cambio. Destino Motion,
walker-motion.hw-1, /opt/walker/ubt_ethercat_master/bin/eni_cruzr_kw_unified_noimu.xml.
Original SHA1b0c9323a7dc1fa627aa4bfddae216374cea2f68157b7a0e8739176f42843d1d;
instalado SHA678c7d6bae1608709400383d85c6e0e5edae7032b365d11977cb56bc984250e8.
Backup remoto: /etc/walker/customizations/hands-v4-bus-20261015/
eni_cruzr_kw_unified_noimu.xml.before y receipt.json. Original externo también
en evidencia. Sólo dos valores XML cambiados, todas las comprobaciones conservadas.

Activación autorizada: un único `docker restart --time 5
walker-system.control_center-1` en Vision (rc0); no restart de hw, no start ROS
forzado ni HOME adicional. Guard pasa y CC recorre Recover/SelfCheck/StartMotion.
El maestro selecciona automáticamente el ENI corregido y actualiza por sí mismo
/opt/walker/ubt_ethercat_master/share/ubt_ethercat_master/config/dynamic_config.yaml:
last_eni pasa de eni_cruzr_kw_noimu.xml a eni_cruzr_kw_unified_noimu.xml.
Este cambio persistente es efecto del arranque; no restaurar el valor antiguo
como configuración vigente de manos. Tiempos PC/robot difieren alrededor de52s;
no comparar sus marcas directamente. Logs Docker del nuevo ciclo:
07:51:52Z selecciona perfil; versión4 obtenida de ambas manos;
07:51:56Z maestro SAFEOP→OP. No repite el fallo de selección/IMU observado antes.

Controladores manipulation, fuerza/par y estados en running, servicio responde.
Muestras nuevas /ecat/left_hand/state y right_hand/state: palm_connect=True,
servo_cnt=7, velocidades0 y servo_status publicados0 (no se interpreta ese0
como diagnóstico universal). Dos errores de SDO en direcciones antiguas18001/2
y objeto2004:7 ausente en8001 aparecen durante inicialización; no impidieron
OP/HOME/telemetría. Causa/impacto de esos avisos aún PENDIENTES, no borrados.
/mc/left_hand/joint_states y /mc/right_hand/joint_states aún no figuran en el
listado tras carga; el checker actual depende de ellos y no queda certificado
CHECK_OK. No forzar su gate; adaptación del control v4 es fase siguiente.

CC registra LimbMotion/StartMotion succ y JoystickMode. Muestra posterior de22
actuadores:20 ejes de cuerpo cerca de HOME, máximo0,00278034rad,
velocidad máxima0 y error_code0; dedos no incluidos en HOME20D.
Paso1 resuelto para inicialización del bus y recepción de estados v4; teleoperación,
movimientos de dedos, grabación/replay v4 y arranque en frío posterior PENDIENTES.
No se envió START PICO ni tarea de demostración de manos.

Reversión: sólo con control detenido/esperando, estado físico preparado y sin
otros mandos, comprobar hash instalado, comprobar SHA original del .before y
restaurar únicamente ese XML conservando permisos. Recargar mediante arranque
supervisado; no copiar dynamic_config antiguo sobre la selección actual ni
retirar sensores para sortear el fallo. Antes de recrear contenedor/actualizar,
conservar copia externa y reaplicar selectivamente según ficha. Persistencia en
recreación Docker no verificada. No se ejecutó rollback.

Fuentes/scripts, recetas, metadata, validación offline, install.json, postcheck,
logs antes/después, estados de manos y body-final-classification.json en
../Humanoide-vla-evidence/20261015_HANDS_V4_BUS_DIAG/.
Documentación before-install-docs/ y after/, SHA256SUMS. No commit/push.


**15-10-2026 — HANDS-V4-BUS-IDENTITY-20261015. VERIFICADO offline; no instalado.**
Ampliación/corrección del diagnóstico HANDS-V4-PREFLIGHT: no atribuir el fallo a
una IMU averiada. `dynamic_config.yaml` recuerda `eni_cruzr_kw_noimu.xml`, perfil
sin IMU EtherCAT que ya se utilizaba con abrazaderas. El escaneo del arranque
fallido contiene 27 dispositivos, incluidos ambos sensores Kunwei y dos
`hand unified`. El candidato vendor `eni_cruzr_kw_unified_noimu.xml` coincide
en número, orden de vendor/product y tipos salvo el puente 18000: vendor ENI
0xffffffff frente a vendor físico 0xe0000002. Su InitCmd también exige literalmente
ffffffff. La comparación no prueba por sí sola el algoritmo interno de selección
ni la causa única del fallo; el mensaje de IMU es insuficiente para diagnosticar
hardware y la activación del derivado sigue PENDIENTE.

Receta reproducible exclusivamente offline:
`python scripts/hands/prepare_v4_bus_profile.py --input ORIGINAL --output DERIVADO`.
Sólo acepta SHA256 original
1b0c9323a7dc1fa627aa4bfddae216374cea2f68157b7a0e8739176f42843d1d.
Cambia sólo VendorId del puente a 3758096386 y Validate/Data de su check vendor
a 020000e0 (mismo valor y comprobación que el perfil anterior de esta unidad).
No suprime comprobaciones, no altera PDO, sensores, límites ni watchdogs.
SHA256 derivado: 678c7d6bae1608709400383d85c6e0e5edae7032b365d11977cb56bc984250e8.
Verificación: exactamente dos hojas XML distintas, 27 identidades vendor/product
coinciden con el escaneo, fuentes alteradas rechazadas. Direcciones físicas
actuales de manos 18001/18002 difieren de las direcciones de configuración
8001/8002; su asignación por maestro aún no verificada. No inferir publicación
fresca ni manos operativas de este ensayo offline.

Destino previsto, NO aplicado: Motion, contenedor walker-motion.hw-1,
/opt/walker/ubt_ethercat_master/bin/eni_cruzr_kw_unified_noimu.xml.
Antes de aplicar: copia externa original ya conservada; respaldo remoto y
comprobación hash inmediata. No modificar dynamic_config ni forzar start como
supuesto arreglo. Cargar mediante secuencia de arranque revisada sólo después
de confirmar estado físico, paros, zona y exclusión de otros mandos: puede
iniciar homing. Después verificar bus, controladores y estados frescos de manos.
Reversión prevista: restaurar exactamente el XML original respaldado y verificar
su SHA; cualquier recarga vuelve a requerir comprobar estado físico.

Evidencia: ../Humanoide-vla-evidence/20261015_HANDS_V4_BUS_DIAG/ (logs,
inventario, perfiles originales/derivado y offline-validation.json).
Cambios de esta intervención sólo en PC: receta y documentación; robot sólo
consultado. Backup documental before/, estado after/ y SHA256SUMS en evidencia.
Revertir sólo esta ficha y la receta si se descarta; conservar cambios ajenos.
Pendientes: instalación, carga, validación física y adaptación PICO v4.
No commit/push.


**15-10-2026 — HANDS-V4-PREFLIGHT-20261015. OBSERVADO; activación PENDIENTE.**
Operador informa instalación de manos v4 con el robot apagado. Diagnóstico sólo
lectura: el escaneo EtherCAT reconoce dispositivos 18001 y 18002 como
`hand unified`, pero el intento de inicialización de las 07:34:45–50 UTC falla
por dispositivo 10000 no encontrado (mensaje vendor: IMU de movimiento, primer
dispositivo del puerto 2 del switch de cintura). No demuestra avería de IMU ni
modelo v4 por sí solo. El contenedor hw se reinicia una vez; la instancia actual
queda esperando `/mc/rosa_control/start`, sin proceso EtherCAT en `ps`.
La aplicación espera ListControllers y la consulta de ese servicio agota timeout;
los topics `/mc/left_hand/joint_states` y `/mc/right_hand/joint_states` faltan.
Los topics `/ecat/*_hand/state` por sí solos no prueban publicación fresca.
`check_hands.sh --model auto` rechaza correctamente la detección.

Existe tarea instalada `teleoperation/cruzr_v4_pico_teleoperation` y YAML
`cruzr_v4_pico_tele.yaml` con hand_type=v4, waist_mode=1 y leg_mode=2.
El lanzador PC actual sigue fijado a clamp y bloquea gatillos; no reutilizarlo
para v4 sin adaptación deliberada de tarea, cliente, controles y validaciones.
Para grabar/reproducir manos se requiere el perfil `utars_with_v4_hand`;
el inspector local de motion actual sólo admite Utars de abrazaderas.
Primero resolver arranque/topología, después configurar y comprobar v4 con
cintura/elevador bloqueados si se mantiene alcance sólo brazos. No sustituir ENI
por una variante noimu ni cambiar HW_TYPE como supuesto arreglo.

Evidencia privada: `../Humanoide-vla-evidence/20261015_HANDS_V4_PREFLIGHT/`
(metadata de tarea/YAML, listado de servicios/topics, logs, StartedAt/reinicios,
procesos y respuesta de controladores). Rutas remotas consultadas:
Motion, contenedores `walker-motion.hw-1` y
`walker-motion.manipulation_robot_app-1`; `/opt/walker/`.
No movimiento, HOME, reinicio, START ni modificación de robot/PC de control.
Cambios únicamente documentales PC en esta ficha y fuentes especializadas;
respaldo selectivo before/, copia after/ y SHA256SUMS en evidencia.
Reversión: retirar sólo el bloque HANDS-V4-PREFLIGHT-20261015; conservar cambios
anteriores del usuario. Configuración instalada v4 observada, carga y prueba
física PENDIENTES. Reanudar con diagnóstico del fallo de inicialización del bus.
No commit/push.


**14-10-2026 — PICO-REPLAY-WORKFLOW-20261014. VERIFICADO técnico y confirmado por operador.**
La reproducción corregida de la copia lenta terminó con is_finished=true y bag played successfully; operador confirma funcionamiento perfecto. No HOME enviado. Procedimiento reutilizable [grabación/reproducción PICO](PICO_GRABAR_REPRODUCIR_PROCEDIMIENTO.md) e inspector local scripts/teleoperation/inspect_pico_motion.py para no repetir investigación del SDK en cada toma. Reutilizar orden articular por nombres, evitar --loop1 en build conocida, leer nombre real con timestamp y preparar derivados sólo cuando necesarios. Mantener confirmación física y preflight fresco; no reutilizar salud/postura histórica. Cuatro pruebas del inspector pasan y grabación real validada estructuralmente. Read-only local en esta intervención, sin otro replay ni configuración robot. Nueva guía, inspector/tests y enlaces PC. Before/after, hashes y validación ../Humanoide-vla-evidence/20261014_PICO_REPLAY_WORKFLOW/. Reversión selectiva documental/herramienta, sin modificar SDK ni motion; no commit/push.


**06-10-2026 — NET-ETHERNET-MAPPING-LINK-20261006. VERIFICADO por lectura.**
Tras conexión del operador, eno1UP/carrier1/IP192.168.11.250/24/perfilcruzr-s2.
RutaVision192.168.11.3 directaeno1, ya NOvíaWi-Fi.5pings forzadoseno1:
0%pérdida,media0,962ms,máx1,635ms. Enlace web/mapeoEthernet comprobado;
no prueba capturaVSLAM ni seguridadfísica. Antesde nueva captura recargarweb
Ctrl+Shift+R para peticiónfusion; no recargar duranteguardadoactivo. Sin cambio
red/mapa o movimiento delagente. Evidencia/backups documentales selectivos:
../Humanoide-vla-evidence/20261006_ETHERNET_MAPPING_LINK_CHECK/.

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

## TELEOP-PREFLIGHT-SIGPIPE-20261006 — selección de log Motion

**06-10-2026, Europe/Madrid. VERIFICADO offline; instalado PC; comprobación
remota PENDIENTE.** Operador informa preflight13:08:58 rc141, sin START y STOP
confirmado por la herramienta. No se consultó ni movió el robot por el agente.
141 corresponde a128+SIGPIPE13. Causa concreta del intento físico INFERENCIA:
la tubería de inventario `find | sort -nr | head -n1 | cut` puede cerrar la
entrada de `head` antes de terminar `sort`; `pipefail` propaga141 y aborta antes
de las consultas de paros/batería. Reproducido con100000 rutas sintéticas usando
la misma tubería: revisión anterior141, nueva0 y mismo log más reciente.
No se atribuye el error a Ethernet, PICO o un paro físico sin evidencia.

**Cambio y destino:** PC, `scripts/teleoperation/cruzr_pico_teleop_pc.sh`, función
`check_robot_teleop_safety`, heredoc remoto leído por SSH: sustituir `head -n1`
por `sed -n '1p'`, que consume toda la salida. Se conservan ordenación, selección,
propagación de errores y todos los gates. No se instala archivo persistente en
Motion; la próxima consulta transmite el fragmento actualizado. Dependencias:
mismas herramientas shell/find/sort/sed/cut y SSH existentes. No reinicios ni
cambios de modo, red, cámara, firmware o robot.

**Verificación:** `python3 -m unittest
scripts.teleoperation.test_pico_motion_preflight_diagnostics -v`:7 pruebas
correctas. Nueva regresión de inventario voluminoso y error real de `find`
continúa bloqueando; gates31–38, tarea incorrecta, timeout/SSH y éxito conservados.
`bash -n` y `git diff --check` correctos. Ensayo físico no realizado.

**Aplicación y reanudación:** usar las fuentes locales actuales; ejecutar primero
la consulta sin movimiento:

```bash
PICO_TELEOP_CAMERA=off CRUZR_IFACE=eno1 CRUZR_PC_IP=192.168.11.250 \
  ./scripts/teleoperation/probar_pico.sh --check-motion-ready
```

Sólo si pasa y se comprueban de nuevo las condiciones físicas/exclusividad,
el operador puede repetir `--teleoperate` con las mismas variables y la
confirmación presencial. Este cambio no demuestra que el estado físico sea apto.

**Respaldo/reversión/evidencia:**
`../Humanoide-vla-evidence/20261006_PICO_PREFLIGHT_SIGPIPE/`: before/, baseline.json
con HEAD/hash de fuentes y cambios previos, tests.log, checks.json, after/ y
SHA256SUMS. Revertir selectivamente script/tests desde before/ conservando cambios
posteriores ajenos; no restaurar todo el checkout. Estado instalado PC, carga
transitoria remota y prueba física PENDIENTES. Fuente reproducible: script y
`test_pico_motion_preflight_diagnostics.py`; no commit/push.

## TELEOP-PREFLIGHT-DIAG-20261006 — diagnóstico previo a START

06-10-2026, Europe/Madrid. **OBSERVADO** estado técnico; **VERIFICADO offline**
diagnóstico; ensayo físico de esta revisión **PENDIENTE**.

11:30:19, --check con PICO_TELEOP_CAMERA=off/CRUZR_IFACE=eno1/
CRUZR_PC_IP=192.168.11.250 pasa7/7 rc0. ADB ausente: el modo off ya soportado
exige peer XR, serialPA94Y0MGKB070822G en el backend y vr_status1; no omite
identidad/tracking. Gafas42.211→PC42.215:63901. No cámara ni START lanzados.
Evidencia: ../Humanoide-vla-evidence/20261006T093019Z_PICO_ETHERNET_CAMERA_OFF_CHECK/.

El operador aporta intento11:31:05 que aborta en preflight Motion antes de START
con mensaje genérico y cierre STOP confirmado. Causa precisa **PENDIENTE**:
el registro aportado no contiene código de salida ni requisito fallido.
No se atribuye ese intento a HOME, movimiento, paros, cable o falta de muestras.
Consulta instrumentada posterior del mismo cuerpo remoto devuelve26 y
ACTIVE_TASK_ERROR=cruzr/home; después el registro Motion muestra otra activación
PICO. No hubo cambio de modo del agente. A11:34:56 el --check-reload-ready
versionado devuelve0: paros0/0, baterías66,4/70,7%, cargador desconectado,
velocidades inmóviles, una acción y tarea teleoperation/cruzr_clamp_pico_teleoperation.
Esta consulta posterior no reconstruye el fallo original ni certifica estado físico.

**Cambio local:** [cruzr_pico_teleop_pc.sh](../../scripts/teleoperation/cruzr_pico_teleop_pc.sh)
conserva el rc de SSH/preflight e informa MOTION_PREFLIGHT_FAILED con requisito.
Códigos21..26: contenedores/hardware/dispositivo/transporte/log/tarea;
31..38: paros, dos baterías/mínimo30%, cargador, módulos, una acción y velocidad
articular≤0,02rad/s.124: timeout; otros: error de consulta. `topic_once()` conserva
rc y añade MOTION_TOPIC_READ_FAILED con nombre del canal; acción usa el mismo
lector y los mismos argumentos ROS/QoS que antes. Sin cambios de criterio,
velocidad, umbrales, cola de control, postura, timeout o autorización de START.
Los mensajes significan falta de confirmación, no diagnóstico físico categórico.
[Tests](../../scripts/teleoperation/test_pico_motion_preflight_diagnostics.py):
5 pruebas offline ejecutan fragmentos reales con dobles SSH/ROS; preservan todos
los rechazos31..38, tarea26, timeout124, errorSSH255 y aceptación con datos sanos.
Sin tráfico/movimiento en esos tests. `bash -n` y `git diff --check` correctos.

**Estado posterior:** a11:41:59 --check-motion-ready de la revisión nueva se
bloquea en la ruta, antes de los gates Motion: selecciona wlx80afcad40bd6,
no eno1. Lectura final: eno1DOWN, sinIPv4, carrier0, Link detected:no;
Motion/Vision vía192.168.42.2 con origen192.168.42.215. La causa física de la
pérdida de portadora no está identificada. No se cambió red ni se relajó el
requisito Ethernet. Rutas verificadas previamente por eno1 quedan históricas.
Recuperar enlace físico y comprobar la ruta antes de repetir:

```bash
ip route get 192.168.11.2
ip route get 192.168.11.3
PICO_TELEOP_CAMERA=off CRUZR_IFACE=eno1 CRUZR_PC_IP=192.168.11.250 \
  ./scripts/teleoperation/probar_pico.sh --check-motion-ready
```

Ambas rutas deben mostrar deveno1/src192.168.11.250. --check-motion-ready no
inicia control; --teleoperate permanece para operador local con preflight y
confirmación física actuales. No se ejecutó ventana de movimiento por el agente.
La captura del transporte RTM/WebRTC real sigue PENDIENTE; ruta válida no basta.

**Destino/activación/reversión:** PC, script y test anteriores. Revisión instalada
localmente, aplicada al próximo lanzamiento; gate físico con nuevo diagnóstico
no alcanzado en la última consulta por fallo de ruta. Sin instalación o cambio
persistente remoto. Reversión selectiva desde before/, conservando trabajo ajeno;
retirar el nuevo test si se revierte. No restaurar estados físicos o rutas por
copiar un respaldo documental.

**Evidencia:** ../Humanoide-vla-evidence/20261006T093305Z_PICO_MOTION_PREFLIGHT_READONLY/ contiene before/, consultas
pasivas/contendores, script diagnóstico transitorio, tarea/acción, resumen,
check-motion-ready.log y rc, final_network.json, tests.log/tests.json, source
hashes, after/ y SHA256SUMS. Sigue pendiente reconstruir el requisito exacto del
intento11:31 y verificar enlace/tráfico/sesión física tras reconexión.

**2026-09-11 — Recuperación sin teleoperación: preparación integrada; ejecución NO resuelta.**
El usuario indicó teleoperación no disponible: se retira la petición de volver
manualmente a PICO como siguiente paso. Nuevo `cruzr_prepare_recovery.py` lee
estado actual, salud/control y planifica sin sustituir los brazos asimétricos.
Corregido el primer prototipo: posiciones motor y JointState usan signos
distintos; sólo se planifica con dos JointState canónicos nuevos. El falso
START_OUTSIDE_LIMITS inicial queda DESCARTADO como diagnóstico físico.
Prueba corregida:101muestras válidas, paros0/0 y control libre; el modelo devuelve
START_GEOMETRY_REJECTED/54avisos, no54contactos reales. Diez pruebas pasan.
El script es sólo preparación, sin --run ni instalación/publicación/reinicio;
HOME desde H03 sigue sin ejecutarse ni aprobarse. No se reduce margen ni se
cambian tolerancias/protecciones. ANL-01; fuentes/backups/evidencia:
`../Humanoide-vla-evidence/20260911T092355Z_RECOVERY-FROM-CURRENT/`.
[Uso, resultado y límites](CRUZR_RECUPERACION_SIN_TELEOPERACION.md).

**2026-09-11 — H03 asimétrico capturado; no se ejecutó retorno.**
Usuario autorizó ensayo supervisado. Telemetría sana/inmóvil, control libre;
la postura no coincide con PICO (error0,842922rad frente a tolerancia0,02rad).
Candidato HOME interno estudiado sólo offline: cota nominal mínima36,599mm
abrazadera derecha–codo; descontando el escenario declarado5° queda−8,330mm,
sin demostrar separación ni contacto real. Modelo completo rechaza la entrada
con54avisos; no son54colisiones físicas. Cero órdenes, instalaciones, recargas,
reinicios, cambios de modo o protecciones. No se amplió la tolerancia PICO.
Para volver por el perfil H02 se pidió al operador preparar PICO con torso recto
y detener teleoperación; esa nueva postura y retorno todavía PENDIENTES.
ANL-01; evidencia `../Humanoide-vla-evidence/20260911T085902Z_H03-ASYMMETRIC-READONLY/`.
[Detalle y reanudación](CRUZR_HOME_ENSAYOS_SUPERVISADOS.md).

**2026-09-11 — H02 PICO con torso recto → HOME 4×, ensayo cerrado.**
Preflight exacto y referencia `pico_body_zero` reconocida; una acción supervisada
`cruzr/pico_to_home_open_v2_4x`, XML SHA `6dd482a7…`, 20s nominales.
Motion SUCCEED/4, 2.103 muestras válidas, cero fallos/deshabilitados; velocidad
máxima observada0,243997rad/s y HOME final0,00297209rad máximo, velocidad0.
El operador confirma «resultado ok, suave y sin contacto, libres, sigamos».
Se valida este caso observado; no retorno general, cuerpo flexionado, carga,
posturas asimétricas ni frenado. No se instaló, recargó, reinició o cambió modo
ni protección. Próximo paso: captura de una postura asimétrica habitual, sin
mandar un retorno hasta revisarla. Ejecutores intactos; confirmación por chat
para esta acción supervisada, sin simular la confirmación de terminal.
ANL-01/MOT-02; evidencia `../Humanoide-vla-evidence/20260911T084247Z_H02-PICO-SUPERVISED/`.
[Resultados y receta](CRUZR_HOME_ENSAYOS_SUPERVISADOS.md).

**2026-09-11 — Ensayo H01 desde HOME ejecutado bajo supervisión.**
Con preparación física confirmada y preflight aprobado se envió una sola
acción `cruzr/home`, XML instalado open_v3_20s SHA `05174d2b…`, desde HOME
medido: apertura lateral de brazos bajos y cierre. Motion `SUCCEED/status=4`;
2.103 muestras válidas, sin fallos de servo ni deshabilitados, velocidad máxima
observada 0,247139 rad/s. Lectura final HOME máximo 0,00278034 rad y velocidad0.
Paros0/0 sin transición: no se midió frenado. El operador confirmó después «suave sin contacto»: H01 cerrado para el caso
ensayado. No se aprueba retorno general ni nuevas velocidades.
Sin instalación, recarga, reinicio, modo o protección modificados. La primera
preparación abortó por formato YAML antes del envío y se conservó; después de
corregir el lector se repitieron los controles, sin reintentar movimiento.
ANL-01; evidencia `../Humanoide-vla-evidence/20260911T082510Z_SUPERVISED-HOME-PREPARATION/`.
[Caso, receta y alcance](CRUZR_HOME_ENSAYOS_SUPERVISADOS.md).

**2026-09-11 — Cierre de interfaces HOME todavía no demostrado.**
Corregida la localización de testigos del auditor: `contact.pos` de FCL puede
quedar fuera de la intersección. Ahora se reconstruyen y comprueban contra ambos
triángulos del CAD. Barrido URDF: 8 parejas con contacto fuera de las zonas
iniciales; barrido ±0,5 rad: 4. No son contactos físicos; la ausencia de otros
testigos no autoriza excluir parejas. Los preliminares 13/9 quedan descartados.
El bucle nativo de grupos se trazó con entradas sintéticas/distancia sustituida;
no permite deducir una matriz de excepciones de links. 64 pruebas pasan sin
omitidas. Siguen 54 rechazos por referencia y falta el modelo mecánico de las
interfaces y su dominio. No aprobado retorno general ni mayor velocidad.
Consultas/copias remotas de lectura; cambios sólo en auditores/documentos PC.
Sin mover, instalar, recargar, reiniciar ni cambiar modos; PICO/HOME operativo
intacto. [Resultados y reproducción](CRUZR_HOME_GEOMETRIA_Y_MOTION.md#resultado-de-la-revisión-de-interfaces-11-09-2026).
ANL-01; `../Humanoide-vla-evidence/20260911T075508Z_HOME-INTERFACE-CLOSURE/`.

**2026-09-11 — Refinamiento del elevador integrado en el análisis HOME.**
Cinco componentes abiertos se reconocen como paredes prismáticas completas y se
encierran individualmente, conservando los otros sólidos. Las envolventes generales
bajan de11a10. Se mantienen982pares y margen2mm;52pruebas pasan. Auditor nuevo
registra superficies originales y testigos alrededor de ejes, sin autorizar
excepciones. Las tres referencias conservan54avisos; en HOME10son cruces del CAD,
24volumen/contención y20holguras inferiores al margen. No equivalen a contacto
físico ni validan HOME desde cualquier postura. Sólo cambios PC, sin conexión,
movimientos, instalación o recarga remotos; perfiles PICO/HOME20s intactos.
[Resultados y reproducción](CRUZR_HOME_GEOMETRIA_Y_MOTION.md#refinamiento-del-elevador-y-diagnóstico-de-interfaces-11-09-2026).
ANL-01; evidencia/backups:
`../Humanoide-vla-evidence/20260911T073642Z_HOME-INTERFACE-REFINEMENT/`.

**2026-09-11 — Unión muñeca+abrazadera: cobertura CAD local VERIFICADA.**
La unión nativa examinada conserva puntos hasta8,64mm fuera en ambos lados.
Complemento convexo local generado sin recortar CAD: cobertura completa de
frontera/volumen certificada. Ocho pruebas pasan, incluyendo FK/colocación
emuladas del binario con hash fijado; visor 3D comprobado para ambos brazos.
La selección/anclaje se contrastan con archivos y código, no con el modelo
calibrado activo ni con medición física. No se integra todavía en el planificador,
instala en Motion, cambia pares/márgenes/XML o envía movimiento. Complemento
amplio: no acredita menor tiempo. HOME general sigue pendiente; rutas20s intactas.
[Receta, prueba y límites](CRUZR_HOME_GEOMETRIA_Y_MOTION.md#unión-muñeca-y-abrazadera-11-09-2026).
ANL-01; evidencia/backup/fuentes:
`../Humanoide-vla-evidence/20260911T070352Z_WRIST-CLAMP-UNION/`.

**2026-09-11 — Auditoría de geometría nativa VERIFICADA offline.**
Se extrajeron defaults de brazos/cabeza/pierna y abrazaderas S2 con hashes fijos,
sin cargar ni ejecutar código nativo en el host. Cinco pruebas pasan. Comparación
de S2Clamp aislada con CAD bajo marcos archivados/anclaje supuesto: exceso máximo
44,396mm L/44,395mm R. Falta comprobar unión con muñeca y anclaje/selección runtime;
no se atribuye ese exceso al modelo activo completo. `s2_leg` no es nuestro
elevador. Se conservan todas las comprobaciones y los perfiles operativos20s;
sin comandos, recargas ni cambios remotos. HOME general PENDIENTE.
[Receta y detalle](CRUZR_HOME_GEOMETRIA_Y_MOTION.md#extracción-de-las-formas-nativas-11-09-2026).
ANL-01, evidencia/backup:
`../Humanoide-vla-evidence/20260911T063949Z_NATIVE-COLLISION-INTERFACES/`.

**2026-09-11 — Arranque completado hasta HOME medido, sin comandos del agente.**
Usuario confirmó condiciones físicas previas y se indicó liberar tras readiness.
Lectura principal0; CC selfcheck aprobado, StartMotion succ, AutoTaskMode;
servidor1 y HOME20D sano, velocidad0, máximo0,003068rad. Confirmación física
posterior del recorrido/contacto PENDIENTE al registrar. Corrección PC del lector
pasivo: salida ROSA por defecto es JSON multilínea; `--print-compact` es texto de
campos y se rechaza. Cierre de objeto en curso con máximo0,5s adicionales,
rechazo de stream truncado/estancado. 15 pruebas pasan y captura en HOME:
252 muestras, paros0/0, sin errores de análisis. La traza inicial de movimiento
falló y no se usa para acreditar seguimiento/frenado. Sin cambios en trayectorias,
instalaciones remotas o HOME general habilitado. Registro ANL-01;
evidencia/backup `../Humanoide-vla-evidence/20260911T062619Z_BOOT-AFTER-CONFIRMATION/`.

**2026-09-11 — HOME general: comprobación de desfases y captura de datos
VERIFICADAS; ensayo físico PENDIENTE.** El validador comprueba ahora también
progreso independiente de cada eje dentro de sus intervalos de etapa, con los
márgenes declarados. Captura pasiva PC de actuadores/paros con timeout remoto
por lector; análisis estricto de veinte articulaciones y recorrido muestreado
tras paro. No es watchdog ni demuestra distancia máxima de parada. `cmd_pos`
es consigna solicitada sin límites, no consigna final de servo.
90 pruebas offline pasan; modelo completo conserva 54 conflictos por referencia
y once envolventes. Lectura bajo paro: principal `1`, servo `0`, sin actuadores;
Control Center de este arranque llegó a `WaitEStopRelease`. Usuario mantiene
E-stop; postura física actual no quedó confirmada. No hubo movimiento, cambios
de modo, reinicios, recargas o instalaciones remotas. JSON/MetaClamp nativo no
se usó: su perfil deshabilita autocolisión/anomalías. Ejecutor/supervisor general
y HOME interno por dominio siguen pendientes; PICO/HOME operativos de 20 s
intactos. [Resultado y comandos](CRUZR_HOME_CAPTURA_Y_PROGRESO_INDEPENDIENTE.md),
registro ANL-01. Backup/evidencia:
`../Humanoide-vla-evidence/20260911T054510Z_GENERAL-HOME-COMPLETION/`.

**2026-09-10 — Refinamiento HOME general y auditoría de Motion (VERIFICADO offline;
prueba física PENDIENTE).** Siete mallas recuperadas sin recortar superficies;
once envolventes restantes. Los 54 pares rechazados por referencia se desglosan
en 30 invariantes con base/ruedas fijas y 24 móviles, sin ignorarlos. Visor 3D
autónomo para comparar originales y sólidos del cálculo. Rutina numérica cúbica
de Motion contrastada en 1.312 casos mediante emulación aislada; error máximo
2,67e-15 rad. `--timing-law cubic-rest` es una opción de análisis, sin `--run`.
Auditoría de marcos CAD/runtime y límites configurados, sin cambiar el robot.
75 pruebas pasan: 37 del paquete y 38 regresiones. PC: `unicorn==2.1.4` en venv.
Lecturas Wi-Fi: paro principal `1`, sin muestra articular dentro del timeout;
después SSH agotó el tiempo de conexión. No se liberó ni rearmó el paro, ni se
enviaron comandos de movimiento, recargas o instalaciones. PICO/HOME 20 s intactos.
[Resultados y reanudación](CRUZR_HOME_GEOMETRIA_Y_MOTION.md), registro ANL-01.
Evidencia/backup: `../Humanoide-vla-evidence/20260910T142312Z_HOME-GEOMETRY-MOTION-QUALIFICATION/`.
Pendiente: interfaces físicas y once envolventes, estado fresco, contrato completo
del adaptador, seguimiento/parada/estabilidad y HOME de arranque. No hay permiso
físico general derivado de estas pruebas.

**2026-09-10 — Implementado el planificador general, únicamente offline.**
`cruzr_plan_home.py --plan` recibe estado20D y escena archivados; no requiere
una referencia PICO ni simetría. Comprueba robot completo/escena, prueba caminos
cortos, busca alternativas y verifica cada segmento con cotas continuas.
28 pruebas pasan. El auditor del modelo suministrado informa54pares con conflicto
de malla/margen en HOME y ambas referencias PICO; no son54contactos reales.
Conserva todas las piezas y omite sólo ocho pares internos de uniones fijas.
PENDIENTE: correspondencia física del modelo, contrato Motion de curva/sincronía,
parada/dinámica/estabilidad, lecturas vivas y HOME interno. El resultado siempre
declara `physical_approval=false` e `installable=false`; no tiene `--run`.
No modifica ni amplía el ejecutor PICO vigente ni sus perfiles de20s. No se
conectó ni movió el robot. PC: entorno `.venv/general-home` con versiones fijadas.
[Comandos y formatos](../../scripts/teleoperation/general_home/README.md),
[diseño y estado](CRUZR_HOME_DESDE_POSTURA_GENERAL.md), registro ANL-01.
Backup/informes/hashes:
`../Humanoide-vla-evidence/20260910T134348Z_GENERAL-HOME-IMPLEMENTATION/`.

**2026-09-10 — Revisión de HOME desde posturas generales con abrazaderas.**
VERIFICADO offline: el modelo completo y 4.000 posturas sintéticas muestran
que la apertura fija puede exceder límites o empeorar separación de envolventes.
No se infieren contactos reales ni se habilitan nuevas posturas en el ejecutor.
Se propone planificar ambos brazos desde sus veinte estados medidos, incluir
escena y todos los pares del robot, validar la curva final y resolver también
el HOME interno del arranque. Muñeca final/sensor/abrazadera forman un conjunto
rígido; el par con wrist_pitch sigue siendo móvil. Implementación general
PENDIENTE; perfiles operativos20s intactos, sin conexión ni movimiento.
[Diseño, evidencia y alcance](CRUZR_HOME_DESDE_POSTURA_GENERAL.md).
Backup/estudio: `../Humanoide-vla-evidence/20260910T124156Z_GENERAL-HOME-3D-REVIEW/`.

**2026-09-10 — Contraseña del ejecutor separada del código (VERIFICADO offline).**
PICO→HOME y los dos comprobadores SSH que utiliza leen ahora la credencial del
entorno o de `.secrets/cruzr_ssh_password`, privado e ignorado en Git. Se conserva
el valor local existente; no se modificó el robot ni se cambiaron trayectorias.
Ocho pruebas de autenticación local pasan. En otro PC hay que proporcionar la
credencial: [configuración y respaldo PC-03](../SYSTEM_CUSTOMIZATIONS.md#pc-03--credencial-ssh-privada-del-pc).
Evidencia: `../Humanoide-vla-evidence/20260910T122441Z_COMMIT-CLEANUP/`.

**2026-09-10 — Plan HOME adaptativo y salida sin acción si HOME ya está medido.**
VERIFICADO local: nuevo planificador abre sólo lo que falta por cada hombro
(mínimo candidato−0,50rad), conserva brazos ya abiertos/asimetría de roll,
baja antes de cerrar y ajusta tiempos según desplazamiento. Rechaza formas
distintas de PICO/brazos abajo y cuerpo fuera de referencias. Ocho pruebas pasan;
auditoría siete casos con cotas nominales positivas. PICO cuerpo cero15,417s,
flexionado18,544s, más comprobaciones/correcciones reales cuando correspondan.
PENDIENTE: no está activado en Motion; error5°/parada/interpolación no cerrados,
sin adaptar el HOME automático del arranque a lecturas actuales. XML vigente20s.
APLICADO en PC: el ejecutor sale `ALREADY_HOME_MEASURED` sin acción si dos lecturas
nuevas de JointState/actuadores sanos prueban HOME estricto e inmovilidad;22pruebas
del ejecutor pasan. No permite ejecutar desde una postura PICO distinta.
Consulta viva no produjo JointState utilizable; preflight abortó por paro,
confirmado después principal1/servo0. Cero movimiento, reinicio o instalación.
[Estado y detalles](CRUZR_HOME_ADAPTATIVO.md).
Evidencia/rollback: `../Humanoide-vla-evidence/20260910T120838Z_ADAPTIVE-HOME/`.

**2026-09-10 — PICO 4× vuelve a pasar el preflight (VERIFICADO, cero movimientos).**
El bloqueo `HASH_ERROR=…/cruzr/home.xml:05174d2b…8cbe` era un contrato local
desactualizado tras instalar HOME abierto; no un fallo demostrado de arranque.
El comprobador canónico reconoce el overlay exacto y exige su biblioteca MetaMove
exacta; los otros hashes y controles físicos permanecen. E6.0G informa errores
de hash sin aconsejar reinicios. Seis regresiones nuevas y cinco previas pasan.
Consulta real completa: `PICO_HOME_PREFLIGHT_OK`, `MOVEMENT_COMMANDS=0`, perfil4×
SHA6dd482a7…27dc, acciones1 y postura `pico_body_zero` inmóvil/error0,002972rad.
No hubo instalación ni recarga. Reanudar con el mismo `--run` bajo la comprobación
presencial de su terminal; sigue pendiente el ensayo físico, no cubierto por
el éxito del preflight. [Detalle](CRUZR_HOME_INTERNO_APERTURA.md#compatibilidad-del-preflight-canónico).
Backup/log/fuentes: `../Humanoide-vla-evidence/20260910T114627Z_HOME-PREFLIGHT-CONTRACT/`.

**2026-09-10 — Optimización PICO/HOME comparada offline (VERIFICADO numérico; sin activar).**
El comparador nuevo conserva envolventes y errores archivados. La candidata
prioritaria omite la etapa3 de3,75s únicamente con objetivos del cuerpo
exactamente iguales: PICO body_zero20→16,25s, body_flexed permanece20s.
La igualdad nominal debe contrastarse con estado/asentamiento físicos; no basta
la tolerancia0,02rad del gate. Reducir apertura a−0,45rad alcanza14,946s desde
body_zero pero pierde unos35mm de cota nominal respecto al torso. No se instaló.
Ocho pruebas pasan. Modelos de brazos concuerdan en744estados, pero cabeza
difiere4,6mm. Hipótesis quintic, error5° y parada no permiten certificar una
aceleración física sólo con este cálculo. [Informe y alcance](../reports/2026-09-10_OPTIMIZACION_TRAYECTORIAS_ABRAZADERAS.md).
Se conservan XML/ejecutor/generadores vigentes; evidencia y hashes en
`../Humanoide-vla-evidence/20260910T113554Z_CLAMP-TRAJECTORY-OPTIMIZATION/`.

**2026-09-10 — Descripciones 3D recibidas (VERIFICADO local, sin instalación).**
La variante base tiene pinzas con dedos; `splint`, abrazaderas rígidas. Sus
mallas y uniones de abrazadera coinciden con la captura runtime del 08-09,
pero el árbol completo difiere y debe contrastarse antes de sustituirlo.
Los auditores PICO/HOME siguen leyendo su snapshot, no estas carpetas.
[Informe, utilidad y hashes](../reports/2026-09-10_MODELOS_CRUZR_S2_DESCRIPTION.md).
Sin modificaciones a modelos, ejecutores ni robot; evidencia y documentos
anteriores en `../Humanoide-vla-evidence/20260910T112000Z_DESCRIPTION-REVIEW/`.

**2026-09-10 — Chequeo previo a primera liberación del HOME nuevo (VERIFICADO técnico).**
`cruzr_boot_ready.sh --check` terminó con RELEASE_TECHNICAL_CHECK=passed:
CC en primera espera de liberación, tres respuestas Motion y seis cámaras con
marcas de tiempo avanzando. Principal pulsado, servo liberado, cargador
desconectado y HOME open-v3-20s/hash de MetaMove esperados. Baterías 70,8/68,3 %.
Consulta VLA de sólo lectura: inferencia/control detenidos y publicadores del
SDK cero. No se envió movimiento ni se reinició ningún servicio.
**PENDIENTE:** confirmación actual del espacio de apertura lateral, sujeciones
retiradas y supervisión junto al paro, seguida de ensayo físico del HOME nuevo.
La comprobación técnica no constituye validación física de la trayectoria.
Evidencia: ../Humanoide-vla-evidence/20260910T101530Z_INTERNAL-HOME-FIRST-RELEASE/.

**2026-09-10 — HOME interno sustituido por apertura relativa; 20 s instalados.**
Usuario confirma brazos abajo/vacíos/libres y solicita corregir `cruzr/home`.
Se reemplazó su XML por home_open_v3_20s: abrir ambos hombros −0,4 rad relativos
conservando los otros ángulos; bajar abiertos a roll−0,6; cuerpo HOME; cerrar
sólo con brazos abajo. Evita que copiar PICO abra elevando brazos desde abajo.
No cambia task_list, primitivas, límites ni el ejecutor PICO. Principal1/servo0/
cargador0 y hash de MetaMove comprobados antes/después de instalación y recarga.
XML nuevo SHA05174d2b…8cbe; original50d819d6…ed88 respaldado en
/etc/walker/trajectory-overlays/20260910T100528.529307Z_home_open_v3/.
Sólo manipulación reiniciada (StartedAt10:06:09Z); CC/hw no reiniciados, cero
objetivos enviados. Manipulación espera ListControllers bajo paro: no afirmar
validación física ni ejecución del árbol. Se conservó E-stop pulsado.
Barrido4referencias×4etapas×501muestras: mínimo69,79mm fuera de uniones locales,
cota condicional7,929mm. No cubre escena/seguimiento/parada ni posturas arbitrarias.
7 pruebas nuevas y20 previas correctas. Seis segundos: borrador local, sin
instalar; aceleración quintic estimada11,11× frente a20s. Tiempo instalado20s,
primera prueba física pendiente. No repetir reload/cambiar modo para probar.
Evidencia: ../Humanoide-vla-evidence/20260910T095255Z_HOME-ROUTE-REVIEW/ y
20260910T100548.301769Z / 20260910T100621.887349Z_INTERNAL-HOME-CHANGE.
[Detalle, limitaciones y reversión](CRUZR_HOME_INTERNO_APERTURA.md).

**2026-09-10 — Incidente tras instalar 4×: HOME interno por cambio a auto (VERIFICADO).**
El perfil 4× quedó instalado con XML/hash exacto, pero la recarga dejó acciones0
sin estados articulares. Liberar el paro no recuperó por sí solo Motion.
A09:38:19Z CC recibió `workMode:auto_task` desde TeleopMode y ejecutó StartMotion;
a09:38:33Z Motion inició `cruzr/home`, ordenando todos los ejes de ambos brazos
a cero en6s. Operador pulsó E-stop a09:38:37Z al ver acercamiento al cuerpo.
Los intentos del script 4× se detuvieron en preflight; no enviaron esa ruta.
La nueva trayectoria no sustituye el HOME interno del fabricante. No usar
cambio a auto/StartMotion/reinicio para recuperar desde brazos elevados.
Nuevo encendido: principal1 y CC WaitEStopRelease comprobados. Voz autónoma
completó su chequeo y TTS Success/status4 a09:45:27Z, primera ejecución en
encendido completo registrada; no confirma por sí misma postura ni audición.
Pendientes respuesta física (brazos abajo/elevados, carga, contacto), liberación
supervisada y ensayo 4×. Mantener E-stop mientras se verifica la postura.
Sólo lectura remota y documentación local; cero reinicios/objetivos/cambios
remotos del agente. Evidencia: ../Humanoide-vla-evidence/20260910T094443Z_RELEASE-AFTER-RELOAD/.
[Secuencia y diagnóstico](../incidents/2026-09-10_HOME_INTERNO_TRAS_RELOAD_4X.md).

**2026-09-10 — PICO→HOME: 4× por defecto; perfiles rápidos verificados sólo en PC.**
**OBSERVADO por el operador:** open_v2 original funciona bien, pero es lenta.
**VERIFICADO local:** el ejecutor acepta `--speed 1|3|4` en todos sus modos;
por petición expresa, omitirlo selecciona 4×. Tiempos de movimiento nominales:
80 / 26,666 / 20 s, más preflight y verificación. Se conservan objetivos,
apertura de hombros, orden de las cuatro etapas y protecciones. Cada velocidad
exige su XML/hash y tarea independientes; si falta, no envía acción ni cambia
a otro perfil. El XML original mantiene hash6b8309f3…6999; 3×f66e53b2…8da y
4×6dd482a7…7dc. Veinte pruebas y bash -n correctos; ShellCheck no está instalado. Sin argumentos
sigue siendo --check local, sin movimiento. Timeout120s y TimeRatio1 intactos.
**PENDIENTE:** instalar/cargar y ensayar 3×/4× en robot; no hubo conexión,
escritura remota ni movimiento en esta modificación. El éxito comunicado de
1× no certifica seguimiento/parada a 4× ni acredita el estado físico actual.
Preparar instalación con brazos abajo/vacíos y E-stop conforme a la guía;
no reiniciar desde PICO para forzar la carga. Reversión: `--speed 1`, sin
restaurar la tarea directa retirada. Evidencia/backup antes y después:
`../Humanoide-vla-evidence/20260910T091420Z_PICO-HOME-SPEED/`.
[Perfiles, carga y límites de la verificación](CRUZR_PICO_HOME_OPEN_V2.md).

**2026-09-10 — Apagado completo y brazos abajo confirmados durante la recuperación:**
Tras confirmar paro pulsado y brazos asegurados, solicitud única de apagado
aceptada y pantalla/luces superiores apagadas confirmadas por el usuario.
Después de KEY1 y chasis, el usuario confirmó «apagado y brazos abajo».
Nuevo arranque con E-stop pulsado indicado; confirmación y readiness pendientes.
No activar PICO antes de recuperar Motion; ensayo open_v2 pendiente.
[Detalle](../incidents/2026-09-10_PICO_RECARGA_SIN_MOTION.md).

**2026-09-10 — open_v2 instalada; Motion no disponible tras paro (VERIFICADO):**
XML remoto exacto6b8309f3…6999 y una entrada en task_list. hw se reinició al
accionar E-stop y espera su servicio de arranque; manipulación recargada espera
ListControllers. Acción0, actuadores sin muestra; no basta liberar el paro.
Operador confirma postura PICO estable/sin contacto y abrazaderas vacías.
No arrancar HOME interno desde esta postura para intentar recuperar el servidor.
Wrapper corregido: errores de auditor/grep ya no se ocultan en sustituciones
Bash; fechas y servidor se informan separados; se retira la indicación de
liberar tras --reload. Instalación/recarga se preparan con brazos abajo/vacíos.
17 pruebas locales pasan; preflight vivo se detiene antes de runtime, sin mover.
Ensayo open_v2 y recuperación física pendientes; sin cambios remotos del agente.
[Diagnóstico, cambios y punto de reanudación](../incidents/2026-09-10_PICO_RECARGA_SIN_MOTION.md).

**2026-09-09 — Corrección local PICO→HOME open_v2 (VERIFICADO offline; NO instalada/ejecutada):**
Se retira del wrapper la tarea directa `cruzr/pico_to_home_owner` tras contacto
comunicado por el operador. Nueva tarea independiente `cruzr/pico_to_home_open_v2`:
abrir hombros roll a −0,60 rad (10 s), bajar otros ejes de brazo manteniendo
apertura (40 s), llevar cuerpo a cero manteniendo brazos abiertos (15 s), cerrar
hombros de brazos ya bajados (15 s). XML/hash nuevos; si sólo existe el antiguo,
--run no envía acción. Instalación/recarga pendientes bajo condiciones existentes.
Doce pruebas y sintaxis correctas; mapeo MetaMove verificado, espera aumentada
120 s para 80 s nominales, nueva lectura articular después de confirmación,
conservación de stdout/stderr y código remoto incluso cuando falla una acción.
Barrido de envolventes, dos variantes/501 muestras por etapa: mínimo fuera de
uniones locales 69,79 mm; menor cota entre muestras 7,95 mm condicionada a la
interpolación común monótona. Todos los pares locales siguen informados, sin
nuevas exenciones. No certifica registro físico, desviaciones, frenado ni escena;
no sustituye ensayo real. Límites de postura/velocidad y protecciones intactos.
Cambios sólo en PC; cero consultas o escrituras al robot durante esta revisión.
Detalle: docs/teleoperation/CRUZR_PICO_HOME_OPEN_V2.md.
Evidencia/backup previo: /home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260909T124028Z_PICO-HOME-OPEN-REVISION.
No restaurar la versión retirada para ejecutar; rollback operativo = suspender
ruta y retirar únicamente la nueva tarea bajo E-stop, conservando otros cambios.
Punto siguiente: instalación, recarga y ensayo supervisado pendientes después
de resolver contacto/apagado. No asumir postura actual ni apagado completado.


**2026-09-09 — CONTACTO REAL durante PICO→HOME body-zero (OBSERVADO por operador):**
El usuario informa contacto al ejecutar owner --run tras aprobar pico_body_zero
(error inicial 0,002684466 rad); resultado ACTION_FAILED_NO_RETRY. Esta evidencia
invalida reutilizar el recorrido como libre de contacto: reconocimiento de postura
y pruebas nominales NO demostraban seguridad del barrido. Se suspende su uso,
incluida cualquier repetición desde la postura posterior al contacto. No enviar
HOME, rearmar ni cambiar de modo para recuperar. Usuario solicita instrucciones
para apagado con E-stop presionado; estado de caja/apoyo de brazos aún pendiente.
Mantener paro; apagado lógico antes de KEY1 y chasis conforme informe de esta
unidad. Apagado no garantiza relajación controlada ni liberación de frenos.
Ningún movimiento, rearme o apagado enviado por el agente en este diagnóstico.
Evidencia: ../Humanoide-vla-evidence/20260909T142542_PICO-HOME-OWNER-RUN/.


**2026-09-09 — Nuevo bloqueo con caja durante PICO (OBSERVADO, recuperación pendiente):**
Usuario informa caja sujeta y brazos asimétricos; considera segura la suelta.
Consulta pasiva: Motion registra protección de fuerza izquierda 20:20:34.504
(hora del log) y derecha 20:20:38.404, separadas 3,900 s. Cancelación de tarea
PICO a 20:23:17 y nuevo inicio de tarea observado a 20:23:53; no asumir control
inactivo persistente. En muestra inicial ambos paros 0, writers RobotCommand 0;
gate de actuadores rechaza consigna latente, delta máximo 0,010203 rad.
La secuencia de disparos puede explicar la asimetría, no demuestra por sí sola
la causa mecánica del esfuerzo. No ejecutar HOME ni apertura workbin desde esta
postura: apertura existente limitada al agarre frontal workbin. No se enviaron
servicios, movimientos, cancelaciones ni rearme. Pendiente estado físico de
apoyo de caja y cese confirmado de otros mandos antes de preparar liberación.
Evidencia: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260909T122324Z_TELEOP-BOX-BLOCK`. Sustituye como estado operativo al preflight PICO
body-zero previo; no reutilizar aquella postura ni su aprobación de extremos.


**2026-09-09 — Corregido PICO→HOME con cuerpo a cero (VERIFICADO local y preflight vivo):**
El gate reconoce dos referencias completas y discretas: `pico_body_flexed`
(original) y `pico_body_zero` (los mismos 14 ejes de brazos; cabeza, elevador y
cintura a cero). Selecciona la referencia más próxima y exige que TODOS los
ejes cumplan 0,02 rad y velocidad máxima 0,01 rad/s. No mezcla referencias ni
acepta posturas intermedias; HOME sigue exigiendo veinte ceros. El informe
incluye referencia, valores esperados/medidos y cada articulación discrepante.
XML/hash, tiempos 19,617+6,254 s, protecciones y confirmación local intactos;
no requiere instalar ni recargar. Ocho tests pasan, incluidos rechazos en cada
uno de los veinte ejes de ambas variantes, mezcla, datos inválidos y secuencia
XML. `--preflight` vivo finalizó 0: `matched_reference=pico_body_zero`, error
máximo 0,00278034 rad, velocidad cero, sano/control exclusivo, `MOVEMENT_COMMANDS=0`.
Revisión geométrica archivada, 101 muestras por segmento y variante: menor
separación OBB fuera de uniones locales 3,473 mm frente a lifter_pitch_2_link
(antes 25,056 mm). Las 15 consultas de superficies STL cerca de ese mínimo,
con hipótesis axial 0/20/40 mm, dieron mínimo 19.303 mm. Son distancias
nominales muestreadas, no cota global ni certificación física; las uniones locales
siguen en el informe y no se crean exenciones. Interpolador, errores dinámicos,
parada y escena conservan las limitaciones ya declaradas al operador.
Cambios persistentes sólo locales: gate, tests, ayuda y etiqueta del wrapper.
Backup/rollback: restaurar esos tres archivos desde `before/` de la evidencia
con el ejecutor detenido, preservando otros cambios. Sin reinicios ni movimiento.
Evidencia: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260909T121801Z_PICO-HOME-BODY-ZERO`. Próximo paso: `--run` por operador presente,
con confirmación literal existente; ejecución física de esta variante pendiente.


**2026-09-09 — Diagnóstico de rechazo del ejecutor PICO→HOME (VERIFICADO en captura):**
El intento del operador `20260909T141428_PICO-HOME-OWNER-RUN` no envió
movimiento: el gate exige una única referencia PICO20D con elevador
[0,299989118; −0,500269484; 0,199609250] rad. La captura guardada muestra
[−0,000191748; −0,000191748; −0,000383495] rad, prácticamente HOME corporal.
Los 14 ejes de brazos sí coinciden con PICO (error máximo 0,002013350 rad).
Por tanto `postura_no_coincide_con_pico` no significa que el usuario no esté
en modo PICO: significa que no coincide la postura corporal específica del
recorrido revisado. Error máximo elevador 2 = 0,500077737 rad (28,65°),
tolerancia 0,02 rad. Inferencia: variante de brazos PICO con cuerpo a cero,
compatible con el overlay de control sólo de brazos; no demuestra modo vivo.
No se alteraron referencias, tolerancias, tareas ni robot durante el diagnóstico.
Pendiente adaptar y revisar explícitamente esa variante antes de ejecutarla;
no ensanchar la tolerancia ni llevar el torso a la referencia antigua para pasar.
Evidencia: `../Humanoide-vla-evidence/20260909T141428_PICO-HOME-OWNER-RUN/before-joints.yaml`
y `scripts/teleoperation/cruzr_pico_to_home_owner_gate.py`.


**2026-09-08 — ejecutor específico de salida PICO→HOME:** por autorización
expresa del propietario se creó `scripts/teleoperation/cruzr_pico_to_home_owner.sh`.
Sólo admite la referencia PICO20D revisada (tolerancia 0,02 rad e inmovilidad),
mueve brazos a cero antes de los seis ejes corporales, exige instalación/recarga
bajo E-stop y confirmación humana literal para `--run`, conserva las protecciones
y no reintenta. Interpolador y parada siguen no certificados y quedan aceptados
en la confirmación del operador. Validación local correcta; no instalado ni
ejecutado sobre el robot al registrar esta entrada.

**08-09, diagnóstico adicional localización02039005:** get_map_name de consulta
termina SUCCESS/status4 y devuelve mapanuevo (no asumir test_route_01 histórico).
Locate3d informa LocateRunning y publica pose, con avisos repetidos de estado
estimado anterior al último tiempo. VSLAM sigue extrayendo características,
pero advierte TF L_arm_base_link inexistente al calcular máscara de brazo.
No demuestra que ese TF ni los avisos temporales causen02039005; tampoco que
el mapa corresponda a escena actual. Preguntado al operador sobre mapanuevo.
Sin navegación, cambio de mapa, pose inicial, reinicios ni cambio de umbrales.
Resolución pendiente: confirmar mapa/escena, visibilidad y calibración/TF antes
de relocalizar o remapear; no ocultar el aviso. Evidencia: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260908T091128Z_LOCALIZATION-WARNING/`.

**08-09, anillo rojo explicado por localización:** log CC correlaciona
occur02039005 con logo→warning-red; varias resoluciones temporales y nueva
aparición persistente en última transición. Catálogo instalado define02039005
como cantidad baja de características coincidentes durante localización,
sistema navegación/localización; solución vendor pendiente. No atribuir al
vr_status0 ni al watchdog FT anterior. Consulta actual CC JoystickMode,
paros0/0, actuadores sin errores y velocidad0, hw sin nuevo reinicio. Posibles
causas visuales/mapa aún no investigadas. Sin movimientos/cambios de modo,
sin ocultar aviso ni reiniciar. Evidencia: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260908T090540Z_RED-FACE/`.

**08-09, vr_status0 durante sesión PICO:** lectura pasiva PC muestra transición
1→0 a10:52:58, seguida de Pico publisher stop y operation_type1. Tracking vuelve
1 a10:52:59 y0 a10:54:15. Dos TCP establecidos desde PICO42.211 a PC42.215:63901;
ADB sin dispositivos. Esto no demuestra pérdida Wi-Fi ni sensor averiado.
Lanzador --teleoperate todavía presente (PID distinto entre consultas); no
inferir sesión finalizada sólo por STOP del publisher. Antes de reactivar
Working cerrar lanzador con Ctrl+C para evitar reanudación al volver tracking.
No se abrió WebSocket, reconectó ADB, reinició app/servicio ni envió movimiento.
Pendiente comprobar dentro del visor Head+Controllers/Send data/Working y
repetir --check con lanzador detenido. Evidencia: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260908T085738Z_VR-STATUS-ZERO/`.

**08-09, recuperación operativa y HOME verificados:** [resultado](../incidents/2026-09-08_HOME_TRAS_RECUPERAR_CONTROL_CENTER.md).
Tras reinicio único de CC y liberación supervisada, self-check/StartMotion
correctos y JoystickMode. HOME20D máximo0,003068 rad, velocidad0, actuadores
sanos; servidor1, VLA detenido/writers0. Confirmación visual posterior pendiente.
Sustituye Fault como estado vigente; causa watchdog6002/SIGSEGV sigue abierta,
sin otro restart de hw ni HOME publicado por agente. Sin monitor persistente.

**08-09, recuperación solicitada tras disparo FT:** el operador confirma caja
retirada, abrazaderas vacías, estabilidad/sin contacto, zona libre y otros mandos
detenidos. El --check de recuperación rechaza ACTION_BUSY (rc27). Se canceló
únicamente la tarea PICO `ac314729-ec21-4ea5-9439-4d4d8f179824` por CancelGoal;
respuesta aceptada y status final 5 (CANCELED). ROSA falló en conversión local
del UUID antes de llamar; la llamada ROS2 estándar sí fue aceptada.
Muestra posterior sana e inmóvil, delta máximo 0,001900 rad, NO HOME.
No se envió trayectoria ni rearme. Recuperación HOME pendiente: postura PICO
tras fuerza no cubierta por READY→HOME ni por el ciclo de caja del wrapper.
No hubo cambio persistente de configuración ni reinicio; sin monitor activo.

**08-09, nueva detención PICO con caja vacía:** [diagnóstico](../incidents/2026-09-08_PARADA_PICO_CAJA_VACIA.md).
Protección de fuerza izquierda y derecha activadas con 0,200 s de separación.
Operador dice caja soltada y ningún paro; lecturas paros 0/0, actuadores sanos
inmóviles, delta 0,001900 rad. Postura teleoperada NO HOME sustituye estado
anterior. Causa mecánica/estado físico y recuperación específica pendientes.
Sólo lectura; no rearme, HOME, reinicio ni modificación de protecciones.

**Última actualización:** 28 de agosto de 2026<br>
**Estado del documento:** operativo y en evolución<br>
**Plataforma:** Cruzr S2 con abrazaderas, PICO 4 Ultra Enterprise y PC Ubuntu<br>
**Responsable de actualización:** registrar aquí cada cambio antes de reanudar una prueba física

Este documento conserva el estado real de la integración de teleoperación. Su
objetivo es que el trabajo pueda detenerse y reanudarse sin repetir pruebas,
perder hallazgos ni confundir una capa que funciona con el sistema completo.
Es la fuente de verdad para la conexión **PICO → PC → robot**. La guía de
captura, dataset y VLA sigue estando en
[`../vla/CRUZR_S2_VLA_TELEOP_DATA_GUIDE.md`](../vla/CRUZR_S2_VLA_TELEOP_DATA_GUIDE.md).

> **Relevo vigente (27-08-2026):** el PC conserva el baseline oficial robot
> v0.2.0 + controller 4.7.0 + UI 4.1.0 y está en STOP. **Motion no está listo
> para mover:** durante la sesión 10:25, al manipular una caja, la muñeca
> izquierda midió aproximadamente 306 N en X frente al límite de 120 N y la
> protección FT detuvo la tarea. PICO y PC siguieron enviando datos a 90 Hz,
> por lo que no fue una desconexión XR, un segundo Y ni el watchdog. Después
> fallaron el servo 5003 y EtherCAT; `hw` y `manipulation_robot_app` reiniciaron
> una vez, pero a las 10:30 PC aún faltaba `ListControllers` y
> `rosa_control_node` esperaba `/mc/rosa_control/start`. Con caja retirada y
> robot estable se completó después el apagado lógico y físico. El arranque
> controlado posterior restauró EtherCAT, controladores y servidor de acciones;
> el preflight versionado aprobó sin mover. Control Center quedó en
> `AutoTaskMode` y la postura continúa sin clasificación histórica, por lo que
> `home` y teleoperación siguen bloqueados hasta una nueva decisión física.
> Antes de este incidente, la oscilación grande del
> torso ya no se atribuye principalmente a la etiqueta PC `gripper`: Motion
> confirmó `Hand type: clamp`, pero la tarea vendor PICO activaba control de
> cuerpo completo (`waist_mode=1`, `leg_mode=2`, CoreMode 7). Ambos grips
> estuvieron activos casi toda la sesión y hubo fallos IK de alcance repetidos,
> sobre todo del brazo derecho. Se instaló sin reinicio ni movimiento un overlay
> reversible que cambia sólo cintura/elevador a cero (`4e8d79a4…`; vendor
> `5f08b30c…`). Tras un preflight fresco se completó el ciclo Control Center
> `teleop→auto_task→teleop`: la tarea viva demuestra ahora
> `ARMS_ONLY_LOADED=hand:clamp,waist:0,leg:0`, inmovilidad y PC en STOP. No se
> inició `pico_control` ni hubo movimiento. En una sesión posterior el operador
> confirmó torso quieto, Motion no registró fallos IK y el STOP se debió sólo a
> 45 ms de solapamiento de grips. Por autorización del propietario,
> `--teleoperate` permite ahora uno o ambos brazos, manteniendo todos los gates;
> `PICO_ALLOW_BIMANUAL=0` restaura el criterio estricto. La primera prueba
> bimanual no falló por IK: al iniciar el brazo izquierdo XR publicó un segundo
> Y (`Left.b_button=true`), el protocolo vendor conmutó `enable` a cero y el
> monitor confirmó STOP. No se ha ocultado ese camino de parada. Se corrigió
> además una carrera de 4.7.0: una conexión WebSocket de sólo lectura podía
> autoarrancar el publisher al coincidir con su broadcast periódico. Los gates
> previos y la verificación final leen ahora logs pasivos, sin conectarse. Para el
> historial anterior, véase
> [`CRUZR_S2_PICO_TELEOP_HANDOFF_2026-08-24.md`](CRUZR_S2_PICO_TELEOP_HANDOFF_2026-08-24.md).

## 1. Convenciones de evidencia

Cada afirmación importante usa una de estas categorías:

- **VERIFICADO:** comprobado directamente mediante archivos, procesos, red,
  topics, logs o hashes.
- **OBSERVADO:** visto durante una prueba, aunque no se conozca aún toda la
  causa interna.
- **INFERENCIA:** explicación que encaja con la evidencia, pero requiere
  confirmación del proveedor o una prueba adicional.
- **PENDIENTE:** no probado o no documentado por DSA.
- **DESCARTADO:** una hipótesis o workaround que la evidencia ya contradice.

Una pantalla verde `Working`, un proceso activo o un topic existente sólo
certifican su propia capa. No equivalen a “teleoperación lista para mover”.

## 2. Resumen ejecutivo del estado actual

| Capa | Estado | Evidencia resumida |
|---|---|---|
| PICO físico y red | **VERIFICADO EN WLAN LOCAL** | PICO `.42.212` y PC `.42.215` en `Cruzr S2-0669` el 26-08; DHCP, redescubrir |
| Aplicación XR del PICO | **FUNCIONÓ DURANTE LA SESIÓN; ESTADO ACTUAL NO RECOMPROBADO** | PICO `.42.211` entregó tracking y mandos hasta el STOP de las 10:26. ADB Wi-Fi no persiste sin USB, pero no causó la detención |
| Servicio XR del PC | **FUNCIONÓ DURANTE LA SESIÓN** | `RoboticsServiceProcess` recibió a 90 Hz; el estado actual es secundario mientras Motion siga sin controladores |
| Backend UBT del PC | **4.7.0 OFICIAL, ACTIVO Y STOP** | SHA-256 `e88b83b7…`; la sesión 10:25–10:26 terminó con STOP oficial tras `Ctrl+C`. Preflight y verificación final no abren un WebSocket susceptible de auto-START |
| Cliente oficial PICO del PC | **INSTALADO; DETENIDO** | `/usr/local/bin/pico_control` SHA-256 `46323392…`; el transporte entregó 5.931 muestras por mando y 5.931 poses a 90 Hz durante la última sesión, hasta el STOP |
| Ethernet PC ↔ Motion/Vision | **VERIFICADO Y PREFERIDO** | `eno1`, `.11.250`, 1000 Mb/s full/autoneg; ping directo `.2/.3` sin pérdida y 0,2–0,9 ms |
| Wi-Fi PC ↔ PICO/fallback robot | **VERIFICADO** | `Cruzr S2-0669`, PC `.42.215`, gateway `.42.2`, fallback `.11.0/24` y powersave desactivado |
| Configuración de efector | **VERIFICADO EN ROBOT Y PC** | `HW_TYPE=cruzr_s2_v1`; backend PC fijado a `arm=clamp` |
| Configuración PICO del robot | **VERIFICADO** | `TELE_DEVICE=pico`, `transmit=local` |
| Tarea Cruzr/PICO correcta | **VERIFICADO** | `teleoperation/cruzr_clamp_pico_teleoperation` |
| Modo robot/web | **ROBOT RECUPERADO EN `AutoTaskMode`; PC STOP** | self-check y `StartMotion` exitosos; sin cliente PICO ni tarea de movimiento enviada |
| Señalización y DataChannel | **VERIFICADO** | DataChannel llegó a estado abierto durante diagnóstico |
| Flujo XR hacia el robot | **VERIFICADO** | El robot registró recepción de tele-data y habilitación temporal |
| Botón de habilitación | **VERIFICADO COMO CONMUTADOR EN 4.7.0** | Y físico izquierdo → `Left.b_button=true` → callback `tele_operation {enable:1/0}`. Un segundo pulso XR a las 10:07:12 deshabilitó la sesión; no se usó el workaround del gatillo |
| Heartbeat de aplicación robot → PC | **4.7.0 VENDOR SIN MODIFICAR; PENDIENTE** | el fallo y timeout 300 s corresponden al 5.3.0 histórico; aún no hay sesión 4.7.0 para caracterizarlo |
| Teleoperación sostenida | **BLOQUEADA TRAS RECUPERACIÓN** | Motion está sano, pero Control Center está en `AutoTaskMode` y la postura es `unknown`; no se ha recargado la tarea PICO ni repetido un preflight de teleoperación |
| Movimiento físico mediante PICO | **NO REANUDAR** | `Force-X` izquierda llegó a `-305,6…-307,0 N` con límite de 120 N y Motion detuvo la tarea. La causa física exacta requiere distinguir caja comprimida/contacto de un transitorio o bias FT |
| Grabación de episodios con `B` | **AFIRMADA POR UBTECH; PENDIENTE DE AUDITORÍA** | en la reunión del 26-08 UBTECH respondió que 4.7.0 recopila datos de este robot; falta saber modalidades, almacenamiento y exportar un episodio |
| PICO directo al robot sin PC | **NO IMPLEMENTADO EN EL MATERIAL INSPECCIONADO** | la web viva sólo cambia el modo; no contiene discovery, tracking ni transporte PICO |

### 2.1 Compatibilidad y captura según UBTECH (26-08)

La matriz china recibida distingue:

- `支持遥操作，配合数采平台一起可支持数据采集`: robot
  `v0.2.0-dac-beta.3` + controller 5.3.0 + UI 4.1.0 soporta teleoperación y,
  junto con la plataforma de adquisición, recopilación de datos;
- `只支持遥操作`: robot `v0.2.0` + controller 4.7.0 + UI 4.1.0 “sólo soporta
  teleoperación”.

Sin embargo, en la reunión técnica del 26-08 UBTECH explicó que 5.3.0 estaba
destinado a un centro experto de adquisición y respondió “Yes, exactly” a la
pregunta directa de si 4.7.0 permitiría recopilar datos de **nuestro robot**.
Esto es una afirmación del proveedor, no una verificación local. Una
interpretación posible es que 4.7.0 grabe episodios de un robot pero no aporte
la plataforma central de adquisición de 5.3.0; todavía falta que UBTECH defina
qué significa exactamente “collect data”, qué modalidades incluye, dónde se
almacena y cómo se exporta. No se declarará captura funcional hasta grabar y
auditar un episodio piloto.

El estado activo del 26 de agosto prevalece sobre la siguiente cronología del
24/25: 4.7.0 reemplazó a 5.3.0 y no hereda ninguna validación de heartbeat,
enable o captura del backend anterior.

Estado histórico consolidado tras las sesiones del 24 y 25 de agosto:

- PICO, PC Service, backend, señalización y DataChannel llegaron a enlazarse;
- no se obtuvo una teleoperación física sostenida por el fallo de heartbeat;
- por autorización explícita del propietario se instaló en el PC un timeout
  temporal de 300 s, conservando la misma ruta STOP; sostuvo enable unos
  46,1 s sin el trip anterior, pero no se validó su vencimiento;
- la primera recuperación usó `127.0.0.1:63901` y ADB reverse; después PC y
  PICO se asociaron a `Cruzr S2-0669` y XRoboToolkit descubrió
  `192.168.42.215`, abrió TCP directo y permitió retirar el reverse;
- el selector web `遥操模式` se verificó, pero no crea la conexión PICO;
- la prueba mínima produjo movimiento físico; después el STOP del PC no sacó
  por sí solo al robot de `TeleopMode`, por lo que se seleccionó `auto_task`;
- `cruzr/home` terminó, pero la vuelta directa casi hizo rozar las abrazaderas
  bajas; el flujo queda corregido para usar `cruzr/open_arm_before_home` y su
  apertura previa, aún pendiente de validación física;
- la web se devolvió manualmente a `JoystickMode`;
- el cliente de teleoperación del PC se detuvo por completo para evitar dos
  clientes sobre el mismo canal;
- el robot conserva `HW_TYPE=cruzr_s2_v1`, `TELE_DEVICE=pico` y
  `transmit=local`;
- no se renombraron topics, colas, `walker28` ni servicios de teleoperación;
  el perfil independiente de tránsito con caja sí redirige temporalmente tres
  entradas de nube de puntos del costmap y después restaura el original;
- los scripts locales se migraron a las imágenes y hashes de v0.2.0 sin
  instalar tareas nuevas ni mover el robot durante esa migración.

## 3. Arquitectura que se ha verificado

```text
PICO 4 Ultra Enterprise
  Android 14 / XRoboToolkit-PICO 1.1.1
  Wi-Fi Cruzr S2-0669: 192.168.42.212/24 en la sesión del 26-08 (DHCP)
                 │
                 │ TCP directo por Wi-Fi local a 192.168.42.215:63901
                 ▼
PC Ubuntu 24.04.4 LTS
  wlo1 / DSA CORPORATE: 192.168.40.120 (Internet; conservar)
  eno1 / cruzr-s2: 192.168.11.250 (Motion/Vision; 1 Gb/s; preferido)
  wlx80afcad40bd6 / Cruzr S2-0669: 192.168.42.215 (PICO + fallback)
  fallback 192.168.11.0/24 vía 192.168.42.2 (persistente)
  perfil Cruzr: never-default + sin DNS (Internet nunca sale por aquí)
  ├─ RoboticsServiceProcess 1.0.0.0  (TCP 63901)
  ├─ ubt_controller 4.7.0             (WebSocket local TCP 8082; vendor)
  └─ ubt-remote-control 4.1.0          (UI; no está abierta ahora)
                 │
                 │ señalización local ws://192.168.11.3:4000
                 │ + DataChannel
                 ▼
Cruzr S2 v0.2.0
  ├─ Vision 192.168.11.3: señalización/web/percepción
  └─ Motion 192.168.11.2: rtm_receiver + control/manipulación
       └─ teleoperation/cruzr_clamp_pico_teleoperation
```

La señalización y el DataChannel no son el mismo canal. Tampoco debe
confundirse el heartbeat de señalización con el heartbeat de seguridad de la
aplicación de teleoperación; esta distinción explica el bloqueo actual.

**Política de rutas canónica desde el 26-08-2026:** PC → Motion/Vision usa
preferentemente Ethernet directa `eno1`/`192.168.11.250`; el perfil
`cruzr-s2` tiene autonegociación y `ipv4.never-default=yes`. PICO y la subred
AP `192.168.42.0/24` permanecen en `Cruzr S2-0669`; ese perfil conserva como
fallback la ruta `.11.0/24` vía `.42.2`, never-default y sin DNS. Sólo destinos
externos/Internet usan `wlo1`/`DSA CORPORATE`. Ninguna de las redes del robot
puede convertirse en ruta por defecto.

### 3.1 Qué hace realmente la web viva del robot

Se inspeccionaron, sin modificarlos, los recursos JavaScript servidos por el
propio robot en `http://192.168.11.3`. El selector superior ofrece estos modos:

| Etiqueta | Valor interno |
|---|---|
| 遥控模式 | `joystick` |
| 开发者模式 | `develop` |
| 示教模式 | `teach` |
| 遥操模式 | `teleop` |
| 维修模式 | `maintain` |
| 自动任务模式 | `auto_task` |

Al elegir uno, la web invoca `work_mode.switch` con el campo `workMode`. Ese
componente no descubre el PICO, no lee cabeza/controladores, no abre el canal
XR y no ejecuta la tarea de manipulación. Por tanto:

```text
seleccionar 遥操模式 = prerrequisito de estado del robot
seleccionar 遥操模式 ≠ conectar PICO ni iniciar una sesión completa
```

La ruta `/vr` de esa misma web reproduce la cámara del robot mediante un flujo
WebRTC (`.../live/rtmpstream/head_front_rgbd`). Es un visor de vídeo del robot,
no un cliente de entrada PICO. La presencia de librerías WebRTC/DataChannel en
el frontend tampoco demuestra teleoperación directa.

No se encontraron en el frontend vivo ni en el subfrontend `/utars/`
implementaciones o referencias operativas a `pico_control`,
`cruzr_clamp_pico_teleoperation`, `walker28_web`, tracking PICO o conexión
directa al visor. Esto no prueba que DSA no disponga de otro APK o módulo; sí
prueba que **no está expuesto por la web actualmente instalada**.

### 3.2 Web del robot y HMI del PC no son la misma interfaz

La frase del SDK “pulsar iniciar teleoperación en la web” es ambigua. La web
viva del robot sólo contiene el cambio de `workMode`, mientras la HMI Electron
del PC (`ubt-remote-control`) contiene el control de sesión asociado al backend
5.3.0. Hasta que DSA identifique otra página o APK, no debe interpretarse el
selector de `192.168.11.3` como sustituto del PC.

### 3.3 Cámara principal dentro de XRoboToolkit

**VERIFICADO en Vision/PC; PENDIENTE en la pantalla del PICO real.** El APK
vendor `XRoboToolkit-PICO-1.1.1` contiene una vista `RemoteCameraWindow`. Al
activar `Camera` → `Request PC camera data`, su `MediaDecoder` abre por defecto
un servidor TCP en el puerto `12345`. El protocolo observado en el APK es:

```text
uint32 big-endian: longitud de la unidad H.264
bytes:             unidad H.264 Annex-B
```

En el robot, la fuente frontal usada ya por la teleoperación es
`/sensor/camera/stereo_left/image/raw` (`shm_msgs/msg/Image6m`). El servicio
Vision `/streaming/start` aceptó esa fuente a `640×400@12`, devolvió
`webrtc://192.168.11.3:1985/sensor/camera/stereo_left/image` y el heartbeat
`/sensor/camera/stereo_left/image/heartbeat`. SRS tiene `http_remux` activo y
entregó el mismo flujo como
`http://192.168.11.3:8080/sensor/camera/stereo_left/image.flv`.

El puente versionado conserva el H.264 del robot: demultiplexa FLV, convierte
las longitudes AVCC a start codes Annex-B, repite SPS/PPS en keyframes y hace
la única conexión al listener del visor. No decodifica/re-encodea vídeo y no
usa ningún canal de control del robot. También mantiene el heartbeat exclusivo
de `/streaming/start` y, al salir, termina publicadores y llama
`/streaming/stop`.

```bash
# Sólo lectura: valida Vision, SRS, ruta y topic.
./scripts/teleoperation/cruzr_pico_camera.sh --check

# Sólo vídeo; no envía START de teleoperación.
./scripts/teleoperation/cruzr_pico_camera.sh --run --camera main
```

Las pruebas de `cruzr_pico_teleop_pc.sh` arrancan este puente antes del
preflight Motion final y no envían START hasta observar
`PICO_CAMERA_LIVE_BEFORE_START=1` tras un keyframe real. La fuente es
configurable con `PICO_TELEOP_CAMERA=main|stereo-right|waist|chassis`; `off`
es una desactivación explícita sólo de vídeo. No se hace un connect de sondeo
a `12345`, porque el decodificador del APK acepta una única sesión y un probe
vacío la consumiría. Durante una sesión, el relay refresca un liveness cada
segundo; proceso ausente o más de cinco segundos sin frames solicita primero
STOP de control y después limpia la cámara.

Evidencia de banco del 25-08-2026: el stream real produjo una muestra FLV de
1.367.328 bytes, 64 frames y 3 keyframes; un receptor PICO simulado recibió 36
unidades con SPS/PPS y el archivo de readiness. Tres ciclos de cierre dejaron
`SRS_STREAMS=0` y cero publicadores de heartbeat. No hubo START ni movimiento.
La prueba visual real sigue pendiente: en el cierre de esta intervención
`192.168.42.211` no respondía, ADB no tenía dispositivos y no se pudo confirmar
la textura en el headset.

El cambio persistente está limitado a los scripts del repositorio; no se
modificaron servicios, contenedores ni configuración del robot/PC. El rollback
operativo inmediato es `PICO_TELEOP_CAMERA=off` para recuperar el flujo previo;
el rollback de código consiste en retirar la llamada previa a START y los dos
scripts nuevos. Los streams temporales ya fueron cerrados.

## 4. Inventario y versiones

### 4.1 Robot

| Elemento | Valor | Estado |
|---|---|---|
| Modelo | Cruzr S2 | **VERIFICADO** |
| Efector actual | abrazaderas laterales | **VERIFICADO** |
| Host Motion | Ubuntu 22.04, `192.168.11.2` | **VERIFICADO** |
| Host Vision | `192.168.11.3` | **VERIFICADO** |
| Versión corta | `v0.2.0` | **VERIFICADO** en Motion y Vision |
| Imagen de integración Motion | `zs2_motion-v0.2.0` | **VERIFICADO** |
| `HW_TYPE` | `cruzr_s2_v1` | **VERIFICADO** |
| `TELE_DEVICE` | `pico` | **VERIFICADO** |
| `transmit` | `local` | **VERIFICADO** |
| `MC_SCENE` | vacío en contenedores inspeccionados | **VERIFICADO; difiere del `DAC` indicado por el SDK** |
| Canal configurado en el PC | `walker28` | **VERIFICADO**, no modificar sin DSA |
| Build exacta DAC | `v0.2.0-dac-beta.2` | **NO DEMOSTRADA** |
| Ejecutable `pico_control` | no encontrado en hosts/contenedores relevantes | **PENDIENTE DSA** |

El SOP entregado exige específicamente:

```text
utars-udoke-config-v0.2.0-dac-beta.2.tar.gz
```

El robot fue actualizado con el paquete genérico `v0.2.0`. El archivo de
versión sólo contiene `SOFT_VERSION=v0.2.0`, y las imágenes activas tampoco
incluyen `dac-beta.2` en el tag. Por tanto, **el nombre corto no demuestra
equivalencia con la build de adquisición de datos**.

Paquetes de actualización ya inspeccionados:

| Paquete | SHA-256 | Conclusión |
|---|---|---|
| archivo offline completo `v0.2.0_offline-001` | `d66372c9f233580a6ebfa7d3ec5f11045fc2bedf61c12562eb2bf4b3c05445d9` | genérico v0.2.0 |
| configuración `utars-udoke-config-v0.2.0.tar.gz` | `0f3d5a988eebb3b4aaacdbaa776c44708b3544afe522edba475fa09a7639aa3b` | genérica v0.2.0 |
| `utars-udoke-config-v0.2.0-dac-beta.2.tar.gz` | no disponible localmente | **PENDIENTE DSA** |

El SOP indica un tamaño aproximado de 39,38 MB para el paquete online DAC y
un `CR_BASE_URL` de `acr.rd.ubtrobot.com/glcr` para ese flujo. El robot tiene
actualmente `CR_BASE_URL=glcr.rd.ubtrobot.com`. No se cambiará el registry ni
se ejecutará una actualización online sin paquete, backup y aprobación.

La sección 7.1 del SDK recibido indica para v0.2.0 `MC_SCENE=DAC`,
`TELE_DEVICE=pico`, el arranque de `signal_server` en Vision, `rtm_receiver` en
Motion y la tarea `teleoperation/cruzr_clamp_pico_teleoperation`. También
menciona el comando `pico_control --arm_type clamp/hand/gripper`. En el robot
real están activos `signal_server` y `rtm_receiver`, pero `MC_SCENE` aparece
vacío y `pico_control` no se encontró **en el robot**. El DEB PC 4.7.0 sí
instala `/usr/local/bin/pico_control`; son alcances distintos y no debe
copiarse ese binario al robot. `MC_SCENE` sigue pendiente con UBTECH.

### 4.2 PC de teleoperación

| Elemento | Valor | Estado |
|---|---|---|
| Sistema | Ubuntu 24.04.4 LTS, amd64 | **VERIFICADO** |
| Ethernet al robot | perfil `cruzr-s2`, `192.168.11.250/24` | **VERIFICADO 26-08:** 1000 Mb/s full/autoneg; `.2/.3` directos, 0 % pérdida |
| Interfaz USB PICO | `192.168.67.183/24` en una sesión; subred variable | **HISTÓRICAMENTE VERIFICADO** |
| ADB | `1:34.0.4-1build3` | **VERIFICADO** |
| XRoboToolkit PC Service | `roboticsservice 1.0.0.0` para Ubuntu 24.04 | **VERIFICADO** |
| Backend | `ubt-controller 4.7.0` | **VERIFICADO; OFICIAL PARA ROBOT v0.2.0** |
| Cliente PICO | `/usr/local/bin/pico_control`, `46323392…` | **VERIFICADO Y EJECUTADO; ayuda admite `--arm_type clamp`; nueva ejecución sujeta al gate arms-only** |
| UI | `ubt-remote-control 4.1.0` | **VERIFICADO** |
| Servicio | `/etc/systemd/system/ubt-controller.service` | instalado, habilitado y **activo**; UI inactiva |
| Backend local | TCP 8082 | listener activo; operación STOP |
| Servicio XR | TCP 63901 | proceso/listener activos; PICO/stream offline en el snapshot del 26-08 |

La instalación conserva
`XRoboToolkit_PC_Service_1.0.0_ubuntu_24.04_amd64.deb`. UBTECH entregó el
26-08 `ubt_controller_4.7.0_ubuntu22.04_amd64.deb` e indicó instalarlo para la
combinación robot v0.2.0 + UI 4.1.0. Su nombre menciona Ubuntu 22.04 aunque el
PC usa 24.04; la instalación y el arranque se verificaron, pero falta la
confirmación formal de soporte del host 24.04.

El ejecutable activo es el binario vendor sin modificaciones:

```text
e88b83b7936a13f5fb71b99416e0d6bcc844b9361524ef709f87fd04ed449d16
```

El siguiente bloque describe **sólo el 5.3.0 histórico y su rollback**; no es
la instalación activa.

El binario original entregado se conserva como backup con este SHA-256:

```text
3a094a007842d859ce95974d74fddf74714e1a49a9a75ca32e82fd6ce7b789fa
```

El ejecutable activo fue reconstruido de forma reproducible a partir de ese
backup, modificando tres objetos de código en dos módulos Python embebidos;
SHA-256 activo al
cierre:

```text
5083e9f0bef9142bfa6ad1b849c767cb9e5ab22e2edd99b981d6061decd7aec2
```

Los cambios son `GRIPPER → CLAMP` en la selección del efector, el mapeo del
flanco ascendente del gatillo izquierdo al booleano que el proveedor asigna a
Y, y el operando del comparador del heartbeat, fijado temporalmente en 300 s.
No se modifica el
robot, no se fuerza `enable_control` y no se fabrica heartbeat; el watchdog y
su ruta STOP siguen presentes. La versión anterior de 10 s está respaldada en
`/opt/ubt/ubt_controller/ubt_controller.clamp-trigger-heartbeat-10s-0f0d3414.bak`
con SHA-256
`0f0d341424f30042cc9189ff215d09007de91f443e4b9b0debaeffa81cda28eb`.
La variante anterior de nivel/300 s está respaldada en
`/opt/ubt/ubt_controller/ubt_controller.clamp-trigger-level-heartbeat-300s-40b440f4.bak`
con SHA-256
`40b440f4a991160e07aeabd168b212854fad2d7b4efbe6bb4874520b48038b4c`.
El activo quedó modo `0755`, propietario `lacuna:lacuna`; el directorio ya era
escribible por ese usuario antes del cambio. El backup de 10 s conserva
`root:root`.
Véase la sección 8.

### 4.3 PICO

| Elemento | Valor | Estado |
|---|---|---|
| Modelo reportado por ADB | `A9210` | **VERIFICADO** |
| Familia comercial | PICO 4 Ultra Enterprise | **VERIFICADO por hardware/proveedor** |
| Android | 14 | **VERIFICADO** |
| Aplicación | `com.xrobotoolkit.client` | **VERIFICADO** |
| XRoboToolkit | 1.1.1 | **VERIFICADO** |
| IP Wi-Fi local observada | `192.168.42.211/24` en `Cruzr S2-0669` | **VERIFICADO POR DHCP**, no fijar en scripts |
| IP USB compartida | varias subredes `192.168.67.x` y `192.168.106.x` | **HISTÓRICO**, no fijar en scripts |
| Estado de aplicación | llegó a `Working` en varias sesiones; estado físico actual no asumido | **OBSERVADO** |
| Modo de envío | `Head + Controllers` | **OBSERVADO antes del reinicio** |
| Controladores | poses enviadas; neutros antes de pruebas | **OBSERVADO** |
| `QuestTool_v3.5.3.apk` | recibido, no identificado como componente activo | **NO UTILIZADO** |

`Working` significa que el PICO está unido al servicio XR del PC. No confirma
heartbeat del robot, tarea de manipulación activa ni autorización para mover.

Después de reiniciar el visor, el USB volvió como MTP/ADB o
MTP/accessory/ADB, sin recrear la interfaz Ethernet USB anterior. El PICO no
tenía una Wi-Fi asociada y XRoboToolkit quedó sin ruta hacia el PC. Los intentos
de forzar RNDIS mediante `svc usb setFunctions` no produjeron una interfaz de
red y no deben usarse como procedimiento de reconexión.

**VERIFICADO después:** `wlo1` permanece en `DSA CORPORATE` para Internet y el
adaptador secundario `wlx80afcad40bd6` usa `Cruzr S2-0669`. Al asociar PICO a
esa misma WLAN, XRoboToolkit recibió por discovery la IP PC
`192.168.42.215` y conectó directamente a TCP 63901 desde `192.168.42.211`.
No requiere red USB ni reverse; ambas IP son concesiones observadas, no una
configuración estática garantizada.

### 4.4 Hashes de los instaladores recibidos

Los binarios grandes se mantienen fuera de Git; estos hashes permiten volver
a identificar exactamente el material utilizado.

| Archivo | SHA-256 |
|---|---|
| `XRoboToolkit-PICO-1.1.1.apk` | `6b2bb282405673d24abcb1980e3478b8f1052e90f7207b1f24cc56a59f8d8261` |
| `XRoboToolkit_PC_Service_1.0.0_ubuntu_24.04_amd64.deb` | `bce661f0be0b8a246ceecb2e5f1675a81c26b834648dc7fdf23f8c0bfe2a5d19` |
| `ubt_controller_4.7.0_ubuntu22.04_amd64.deb` | `4f2b728b689175867ff345bec3e30f319fe7d8567d9e08985aa48a2b67bad61c` |
| `ubt_controller_5.3.0_ubuntu22.04_amd64.deb` | `18300c8e16c5cfc9e88214ddce772d8be6b1d03129e953b9d1cb3ae2d2d34144` |
| `ubt-remote-control_4.1.0_amd64.deb` | `2663545f83fa00946443a60f493e4f3db2b14a7e12b6980b5cdece76f2f5d279` |
| SOP UTARS/PICO recibido | `2b786be5391cd93feb3750e4e2786377b1a0799537310d527bca9ce75d22a258` |

## 5. Configuración activa conocida

### 5.1 Backend del PC

Archivo: `/opt/ubt/ubt_controller/config/config.json`.

```json
{
  "transmit": "local",
  "signal_server_url": "ws://192.168.11.3:4000",
  "channel_name": "walker28",
  "push_rate": 90,
  "control_device": "pico",
  "foot_switch_path": "/dev/input/by-id/usb-PCsensor_FootSwitch-event-kbd",
  "enable_foot_switch": 1,
  "send_joint_name": 0,
  "enable_adb_reverse": 1
}
```

Observaciones:

- `push_rate=90` es la tasa configurada del flujo XR, no una garantía de 90 FPS
  del dataset final.
- `enable_foot_switch=1` fue restaurado por el paquete 4.7.0. El visor informa
  `foot_switch_status=0`; debe aclararse si el pedal es obligatorio o si esta
  opción puede desactivarse oficialmente antes de una prueba física.
- `enable_adb_reverse=1` está configurado, pero el flujo vigente previsto es
  TCP directo por Wi-Fi Cruzr. En el snapshot actual no existe ni peer 63901
  ni reverse; el visor debe reactivar Send data/Working.
- No se deben versionar certificados, tokens, contraseñas ni identificadores
  privados presentes en paquetes cerrados.

### 5.2 Tarea correcta del robot

La tarea específica de este robot y efector es:

```text
teleoperation/cruzr_clamp_pico_teleoperation
```

Usa el meta-task:

```text
meta_teleoperation/cruzr_clamp_pico_tele.yaml
```

Valores relevantes verificados:

| Campo | Valor |
|---|---|
| `robot_type` | `cruzr` |
| `hand_type` | `clamp` |
| `frequency` | `500` |
| `init_time` | `12.0` s |
| `collision_detection` | `true` |
| `web_comm_service` | `true` |
| `head_tracking` | `true` |
| `waist_tracking` | `false` |
| `tele_device` | `7` (`kPico`) |
| modo de brazos | mapeo de efector (`limb_mode=2`) |
| protección de fuerza configurada | 120 N por eje en cada brazo |

La presencia de `collision_detection=true` y umbrales de 120 N no equivale a
seguridad funcional certificada. DSA debe confirmar unidades, significado,
tiempo de reacción y límites adecuados para este efector.

También existen tareas `s2_*`, pero **no son la elección correcta para Cruzr**.
Aunque el SOP sea compartido con Walker S2, el robot contiene una variante
específica `cruzr_clamp_pico_teleoperation` con parámetros geométricos Cruzr.

### 5.3 Interfaces ROS observadas

| Topic | Tipo | Publicador/suscriptor presentes |
|---|---|---|
| `/pico_vr/hand_data` | `sensor_msgs/msg/JointState` | sí |
| `/pico_vr/joy_data` | `quest_msgs/msg/Joysticks` | sí |
| `/pico_vr/pose_data` | `sensor_msgs/msg/JointState` | sí |
| `/pico_vr/tele_data` | `sensor_msgs/msg/JointState` | 1 / 1 |
| `/mc/teleoperation/enable` | `std_msgs/msg/Bool` | 1 / 1 |
| `/mc/teleoperation/mode_status` | `sensor_msgs/msg/JointState` | 1 / 1 |
| `/teleop/enable` | `std_msgs/msg/Bool` | 1 / 1 |

La existencia de endpoints DDS no demuestra que estén publicando muestras
válidas en este instante. En el último snapshot, los `echo --once` no
recibieron muestra durante cinco segundos.

### 5.4 Controles documentados y nivel de validación

| Control PICO | Función indicada por SOP | Validación actual |
|---|---|---|
| `Y` | iniciar/detener teleoperación | contacto capacitivo observado; clic mecánico `key.b_y` no fiable |
| `X` | alternar modo en sitio/móvil | clic aislado no reproducible; no está reasignado en el backend activo |
| `A` | reset del tren superior en modo en sitio | pulsado; no corrige el enlace; efecto físico no caracterizado |
| `B` | iniciar/detener captura de episodio | **PENDIENTE** |
| grip izquierdo/derecho | seguimiento de ese brazo y cintura | **PENDIENTE**, no usar antes del gate |
| gatillo izquierdo | cierre/apertura de mano activa según SOP | con abrazaderas pasivas se mapea a un solo flanco de Y; comportamiento aislado verificado, E2E físico pendiente |
| gatillo derecho | cierre/apertura de mano activa según SOP | sin cambios; no usar con abrazaderas para habilitar |
| joysticks en sitio | cintura y elevador | **PENDIENTE** |
| joysticks en modo móvil | traslación y giro del chasis | **PENDIENTE** |
| clics de joystick | alternar protección de fuerza por brazo | **NO PROBAR** hasta confirmar estado/indicación |

La UI PICO no muestra por sí sola toda la cadena de armado. Mientras no se
conozca el heartbeat, ningún cambio de color o estado del visor debe sustituir
la lectura del backend y del robot.

### 5.5 Estado interno y semántica observada en v0.2.0

La última recuperación dejó evidencia de un cierre limpio de la tarea:

- `teleoperation/cruzr_clamp_pico_teleoperation` fue destruida antes de
  ejecutar `cruzr/home`;
- `/sys/state/module_lock_info` devolvió `locked=false` y `module_name` vacío;
- `cruzr/home` terminó con `SUCCEED/status=4`;
- la última muestra conocida del status de acción era terminal, no activa.

En v0.2.0 hay dos diferencias importantes respecto a scripts antiguos:

1. `/sys/task/remote_command` puede anunciar un cliente pero ningún servidor y
   no ofrecer `DO_RESET=9`. Si la máquina de tareas está libre, no hace falta
   enviar ese reset; si está bloqueada y `DO_RESET` no existe, se debe parar y
   diagnosticar, no enviar una orden inventada.
2. `/mc/manipulation/action` conserva un cliente persistente incluso en reposo.
   `Action client count: 1` ya no significa que haya una tarea ejecutándose.
   Para decidir si está ocupado se consultan estados activos de action status
   (`1`, `2` o `3`), además del lock y del resultado de la tarea.

El último log de la tarea PICO confirmó los parámetros reales: abrazaderas,
`PicoVRJoystick`, frecuencia 500 Hz, inicialización 12 s, detección de
colisiones activa, seguimiento de cabeza activo, cintura desactivada y
`TimeRatio=0.5`. Son evidencia de configuración, no de una sesión PICO válida.

## 6. Qué se ha probado extremo a extremo

### 6.1 Enlace PICO → PC

**VERIFICADO:**

1. El PICO aparece como dispositivo ADB autorizado.
2. XRoboToolkit entra en `Working` y envía `Head + Controller`.
3. Históricamente apareció red IP USB en subredes variables; la sesión actual
   usa la WLAN `Cruzr S2-0669` con DHCP.
4. Se establece TCP directo desde el PICO hacia
   `192.168.42.215:63901` (`RoboticsServiceProcess`).
5. El servicio detecta el dispositivo y `ubt_controller` consume el SDK.
6. En una prueba diagnóstica se observaron datos PICO próximos a la tasa
   configurada de 90 Hz.

**REGRESIÓN HISTÓRICA Y RECUPERACIÓN ACTUAL:** después de reiniciar el PICO,
ADB volvió pero no reapareció la interfaz de red USB. El 25 de agosto a las
10:29 se verificó que XRoboToolkit intenta `127.0.0.1:63901`; se restauró
`adb reverse tcp:63901 tcp:63901`, se reinició sólo la app y reaparecieron TCP
establecido y `vr_status=1`. No se forzó RNDIS.

### 6.2 PC → robot

**VERIFICADO:**

1. El backend local acepta un cliente WebSocket en TCP 8082.
2. Al iniciar recopilación desde un cliente diagnóstico, el PC establece
   señalización y abre el DataChannel con el robot.
3. El log de transporte confirma repetidamente `datachannel is open`.
4. El robot recibe tele-data y registra habilitación temporal de
   teleoperación.
5. El robot devuelve eventos `tele_operation` al PC; se observaron estados
   `enable=1` y posteriormente `enable=0`.

La prueba diagnóstica utilizó el protocolo local descubierto en el paquete:

```json
{"type":"collect","content":{"operation_type":2,"enable_hand_pose":0}}
```

`operation_type=2` inicia y `operation_type=1` detiene. Esta interfaz se usó
solamente para aislar capas; **no es el procedimiento normal de operación**.
El cliente diagnóstico fue cerrado y se envió STOP. No debe quedar conectado
en paralelo con la interfaz oficial.

### 6.3 Robot → PC: punto de fallo

**FALLA REPRODUCIDA:** el backend espera recibir periódicamente:

```json
{"type":"heartbeat"}
```

No se observó ningún mensaje de ese tipo. El watchdog del controlador compara
la hora actual con `last_heartbeat_time`; si transcurren más de 10 segundos,
registra:

```text
No heartbeat for 10 seconds, stoping operation
```

y envía STOP. El callback posterior muestra:

```json
{"content":{"enable":0},"type":"tele_operation"}
```

Ese valor de 10 s describe el binario vendor y las reproducciones históricas.
El ejecutable actualmente instalado conserva el mismo bloque pero compara con
300 s por la autorización diagnóstica registrada en 8.10; todavía no se ha
ejecutado ni validado en runtime.

El watchdog puede seguir emitiendo STOP de forma periódica mientras no haya
heartbeat. En el binario histórico, si START ocurría cuando el temporizador ya
estaba vencido, la parada podía aparecer antes de diez segundos desde la
pulsación de `Y`; los diez segundos se medían desde el último heartbeat válido,
no necesariamente desde el último START. La misma semántica se conserva con el
umbral temporal de 300 s.

La reproducción inicial se hizo sin haber confirmado el selector web
obligatorio `遥操模式`. Después se repitió la cadena con modo remoto,
`vr_status=1` y `arm=clamp`; el robot siguió devolviendo `enable=0` y no se
observó el heartbeat esperado. En la sesión analizada, estos callbacks
aparecieron aproximadamente cada 11,1 segundos, mientras el watchdog del PC
vence a los 10 segundos. Esto confirma una incompatibilidad temporal o de
protocolo pendiente de DSA; no demuestra por sí solo cuál componente tiene la
versión incorrecta.

**REVALIDADO el 25 de agosto sobre los binarios instalados:** el bytecode de
`Publisher.callback` documenta el flujo «robot SDK → RTM → Sender → callback».
La rama `type=heartbeat` llama a `update_last_heartbeat_time`; START sólo
inicializa esa misma marca una vez. El source map de la UI PC 4.1.0 no contiene
un emisor de heartbeat y sus únicos mensajes operativos son START/STOP. Por
tanto, mantener abierto el WebSocket de la UI o del lanzador no proporciona el
heartbeat que falta.

### 6.4 Los dos “heartbeats” no son equivalentes

El robot registra cada diez segundos:

```text
AnswerSession: sent heartbeat
```

El análisis de `libwebrtc_sdk.so` confirma que esa rutina envía al servidor de
señalización un mensaje equivalente a:

```json
{"event":"ping","server_id":"..."}
```

Su función es mantener registrada la sesión de señalización. **No es** el
heartbeat JSON de la aplicación que espera `ubt-controller` por el callback
del DataChannel.

El ejecutable `rtm_receiver` y la biblioteca `librtm_sdk.so` inspeccionados no
mostraron una rutina evidente que publique el heartbeat de aplicación. Esto es
coherente con que la build genérica `v0.2.0` carezca de una pieza incluida en
`v0.2.0-dac-beta.2`.

### 6.5 Resultado de las pruebas de botones

- Android/Stationservice reporta por separado contacto capacitivo y clic.
- En una prueba aislada anterior, X mantenido llegó a producir
  `key.a_x=1`, pero el resultado no fue reproducible.
- Al pulsar Y durante dos segundos apareció contacto `touch.b_y=1`, pero
  `key.b_y` permaneció en cero. Por tanto se estaba tocando el botón correcto,
  pero su clic no llegó a la aplicación.
- En las pruebas posteriores, Stationservice mantuvo `key.a_x=0` también al
  pulsar X. Una escucha directa de `get_X_button()`, `get_Y_button()`,
  `get_A_button()` y `get_B_button()` en el SDK del PC terminó con
  `BUTTONS_SEEN=NONE`, mientras el tracking de poses seguía disponible.
- Durante esa misma ventana Android registró una transición temporal a
  `HandTrackingActive` y después a `ControllerActive`. Esto sitúa el fallo
  actual antes del backend del robot: estado/modo de entrada de XRoboToolkit,
  controlador PICO o transporte de botones PICO → XRoboToolkit PC Service.
- El backend vendor usa `get_Y_button()` para `left_joystick.b_button`, y ese
  campo llama a `enable_operation_switch()`.
- Se sustituyó el workaround X/Y por un mapping del gatillo izquierdo al
  booleano Y, manteniendo intacto el mando derecho. Una prueba de ocho segundos
  no observó `b_button=true`; el robot permaneció con `enable=0`.
- Dos escuchas directas posteriores del SDK devolvieron pico de gatillo
  izquierdo `0.000` y ningún botón. Una primera prueba pudo haberse hecho sin
  accionar correctamente el gatillo; la repetición explícita también quedó en
  cero.
- Aún no se ha obtenido una teleoperación física continua y validada.

## 7. Diagnóstico de causa

### 7.1 Hechos que descartan un fallo básico de conexión

No encaja con un fallo simple de USB, ADB, PICO, Ethernet o DataChannel porque:

- ADB ve el visor;
- el PICO mantiene TCP con el servicio XR;
- el PC recibe datos XR;
- el DataChannel se abre;
- el robot recibe tele-data;
- el robot devuelve mensajes `tele_operation`;
- el watchdog específico de heartbeat es quien ordena STOP.

### 7.2 Causas compatibles con la evidencia

La respuesta posterior de DSA añadió un prerrequisito que no estaba reflejado
en las pruebas iniciales: seleccionar `遥操模式` en la web del robot. Ese modo
se seleccionó y Control Center confirmó `TeleopMode`; no resolvió por sí solo
la habilitación ni el heartbeat.

La segunda causa posible sigue siendo una incompatibilidad entre el robot
genérico `v0.2.0` y el conjunto de PC exigido para adquisición de datos. El SOP
define una matriz exacta:

| Componente | Versión exigida por SOP |
|---|---|
| Robot | `utars-udoke-config-v0.2.0-dac-beta.2.tar.gz` |
| Backend PC | `ubt_controller_5.3.0_ubuntu22.04_amd64` |
| UI PC | `ubt-remote-control_4.1.0_amd64` |

Los dos componentes del PC coinciden. La build exacta del robot no está
instalada o, como mínimo, no puede demostrarse con el material actual. La
ausencia del heartbeat de aplicación es consistente con esa diferencia, pero
no demuestra por sí sola la build causante. También existe un desfase
observado entre callbacks del robot (~11,1 s) y el watchdog del PC (10 s) que
DSA debe explicar.

### 7.3 Qué debe confirmar DSA

DSA debe proporcionar una de estas dos respuestas verificables:

1. el archivo exacto `utars-udoke-config-v0.2.0-dac-beta.2.tar.gz`, su hash y
   procedimiento de actualización/rollback; o
2. una declaración de que el paquete genérico instalado contiene exactamente
   los mismos componentes DAC, acompañada por versiones/hashes y una corrección
   concreta para el heartbeat que falta.

Hasta entonces no se considerará resuelto.

## 8. Workarounds y cambios locales aplicados

Todos son reversibles. El binario original de `ubt_controller` permanece
respaldado; los dos cambios de bytecode del PC se generan mediante un script
versionado y validan estructura, runtime y orden de lecturas antes de instalar.

### 8.1 Regla udev para PICO

Se instaló y versionó
[`../../config/udev/51-pico-ubt.rules`](../../config/udev/51-pico-ubt.rules)
para dar acceso al vendor USB `2d40` mediante `plugdev`/`uaccess`. El usuario
operador pertenece a `plugdev`.

**Resultado:** ADB funciona sin ejecutar un daemon ADB como root.

### 8.2 Locale numérico neutral

Se añadieron `LANG=C.UTF-8`, `LC_ALL=C.UTF-8` y `LC_NUMERIC=C` a la unidad
systemd y al wrapper `run.sh`.

**Motivo:** XRoboToolkit serializa arrays como texto separado por comas. Un
locale español también usa coma decimal y puede corromper la separación de
coordenadas.

**Resultado:** el servicio XR entrega poses interpretables. Esto corrige el
formato local, pero no el heartbeat robot → PC.

### 8.3 Espera de conexión PICO antes del backend

El wrapper espera hasta 60 segundos a que exista una conexión establecida en
TCP 63901 antes de lanzar `ubt_controller`.

**Motivo:** el SDK XR enumera dispositivos existentes al inicializarse. Si el
backend arranca antes de que el PICO conecte, el proceso puede quedar vivo sin
publicar poses después de una reconexión.

**Resultado:** tras el reinicio más reciente, el wrapper detectó el stream a
los 21 segundos y después arrancó el controlador.

**Limitación:** si el PICO se desconecta o duerme después, puede ser necesario
reiniciar `ubt-controller.service` una vez restablecido `Working`.

### 8.4 Operación sin pedal

Se cambió únicamente:

```json
"enable_foot_switch": 0
```

**Motivo:** no hay pedal físico conectado. El paquete contempla el flag.

**Resultado:** el backend no espera el dispositivo de pedal. Aún falta que DSA
confirme el comportamiento oficial de deadman sin pedal y la relación exacta
entre `Y`, grips y habilitación.

### 8.5 IP Ethernet del PC

Se configuró `192.168.11.250/24`, que es la IP indicada por el SOP. Sustituye
la dirección de diagnóstico anterior `192.168.11.99`.

**Resultado:** acceso correcto a Motion `.2` y Vision `.3` sin usar la ruta por
defecto del PC.

### 8.6 Cliente WebSocket diagnóstico

Se usó temporalmente un cliente local para separar UI, backend, señalización y
robot.

**Resultado:** demostró que el transporte XR/DataChannel llega al robot y que
la parada procede del watchdog de heartbeat.

**Estado final:** cerrado; STOP enviado; no debe ejecutarse junto a la UI
oficial ni convertirse en una herramienta de producción.

### 8.7 Perfil de abrazaderas en el backend del PC

Se instaló el drop-in versionado
[`../../config/systemd/system/ubt-controller.service.d/20-cruzr-clamp.conf`](../../config/systemd/system/ubt-controller.service.d/20-cruzr-clamp.conf),
que fija:

```ini
Environment=arm=clamp
```

**Motivo:** la interfaz recibió del canal del robot la etiqueta genérica
`gripper` y el backend cargó `ubt_gripper.json`, aunque el hardware real son
abrazaderas laterales. El controlador distingue explícitamente `clamp` de
`gripper`.

**Resultado:** el valor por defecto del backend coincide ahora con el efector
físico. El lanzador exige además `arm_type=clamp` y aborta si el log vuelve a
seleccionar `gripper`.

### 8.8 UI bajo demanda y preflight del PC

Se añadió la unidad de usuario bajo demanda
[`../../config/systemd/user/ubt-remote-control.service`](../../config/systemd/user/ubt-remote-control.service)
y el lanzador
[`../../scripts/teleoperation/cruzr_pico_teleop_pc.sh`](../../scripts/teleoperation/cruzr_pico_teleop_pc.sh).

La UI no se habilita al arrancar Ubuntu. El lanzador comprueba ADB, rutas,
Motion/Vision, TCP 63901, WebSocket 8082, `vr_status`, estado de operación y
`arm=clamp`; exige una confirmación física antes de publicar y detiene/cierra
si aparece el watchdog.

La inspección del source map de `ubt-remote-control 4.1.0` mostró dos detalles:

- la UI no genera el heartbeat de aplicación; éste debe llegar desde el lado
  del robot;
- usa `reconnectLimit: -1` como si significara infinito, pero la versión
  incluida de la librería no reconecta con ese valor. Por eso el orden seguro
  es backend + PICO primero y UI después.

**MEJORADO el 25 de agosto a las 10:35:** `check_pc` era silencioso hasta
terminar, por lo que una consulta lenta parecía un cuelgue. Ahora imprime siete
etapas con timestamp antes de ejecutarlas, limita ADB, systemd, journal y
WebSocket a 5 s y termina con `CHECK COMPLETADO`. El gate muestra además cuándo
envía START y cuándo espera `arm=clamp`; un fallo Bash inesperado informa
línea/comando antes de solicitar STOP. Para traza completa sin cambiar la
operación se puede usar:

```bash
CRUZR_TELEOP_DEBUG=1 \
  ./scripts/teleoperation/cruzr_pico_teleop_pc.sh --check
```

Se verificó el flujo normal completo y un fallo ADB simulado; ambos dejaron
`operation_type=1`, `enable_control=0`, `vr_status=1`. No se ejecutó el gate.

### 8.9 Recuperación de socket XR del PICO

Después de reiniciar `RoboticsServiceProcess`, XRoboToolkit puede conservar una
pantalla activa con un socket ya muerto. Se reprodujo que reiniciar sólo la app
`com.xrobotoolkit.client` por ADB recupera TCP 63901. Ese reinicio desarma el
envío: hay que volver a seleccionar `Head + Controllers`, pulsar `Send data` y
verificar `Working`; TCP establecido por sí solo no equivale a `vr_status=1`.

**REVALIDADO el 25 de agosto a las 10:29:** el servicio estaba activo y
escuchaba 63901, pero no había red USB ni entrada en `adb reverse --list`.
XRoboToolkit registraba fallos repetidos contra `127.0.0.1:63901`. Tras crear
el reverse, la app conservó el socket fallido; `am force-stop` seguido de un
nuevo lanzamiento produjo TCP establecido, `ControllerActive` y
`vr_status=1`. El backend permaneció en `operation_type=1`,
`enable_control=0`; no se envió `collect`/START ni hubo prueba física. El
`--check` canónico pasó red, ADB, stream, tracking, clamp, hash `40b440…` y
watchdog configurado a 300 s.

**REVALIDADO el 25 de agosto a las 11:53:** PC y PICO quedaron en
`Cruzr S2-0669` con `192.168.42.215` y `192.168.42.211`, respectivamente,
sin desconectar `wlo1` de `DSA CORPORATE`. Tras `Head + Controllers` y
`Send data`, el log Unity confirmó conexión a `192.168.42.215:63901` y `ss`
mostró el peer directo. Se eliminó `adb reverse --remove-all`; TCP,
`vr_status=1` y STOP permanecieron. El lanzador identifica ahora el visor por
`ro.serialno` con serial USB o destino ADB `IP:puerto`. `bash -n` y `--check`
pasaron; `shellcheck` no está instalado. No se envió START ni hubo movimiento.

**REVALIDADO el 25 de agosto a las 12:16:** una caída transitoria de la WLAN y
la recuperación ADB dejaron dos sockets XR simultáneos. Aunque la app estaba
visible en `Working` y el tracking PICO local mostraba cabeza y controladores,
el backend registró `device missing` a las 12:13:21 y devolvió `vr_status=0`.
Se reinició únicamente `com.xrobotoolkit.client`; después de volver a elegir
`Head + Controllers` y `Send data`, `vr_status` cambió `0→1` manteniendo
`operation_type=1`, `enable_control=0`. El `--check` canónico volvió a pasar
7/7 por TCP directo `.211→.215:63901`. No hubo START ni movimiento.

### 8.10 Corrección del efector y workaround de entrada

El script
[`../../scripts/teleoperation/patch_ubt_controller_clamp.py`](../../scripts/teleoperation/patch_ubt_controller_clamp.py)
reconstruye el archivo PYZ de PyInstaller con Python 3.10 y aplica:

1. `WebsocketServer.collect`: cambia la selección automática
   `ARM_TYPE.GRIPPER` por `ARM_TYPE.CLAMP`.
2. Con `--pico-enable-left-trigger`, `PicoPublisher.publish_joysticks`:
   conserva el empaquetado de ambos mandos, lee una vez el gatillo izquierdo
   y publica `left_joystick.b_button=true` sólo durante su flanco ascendente.
   Mantenerlo apretado ya no repite el conmutador Y del proveedor.
3. Con `--heartbeat-timeout-seconds 300`,
   `WebsocketServer._broadcast_publisher_states`: sustituye únicamente el
   operando `release_timeout` de la comparación de heartbeat por el literal
   `300`; no toca las demás aplicaciones de `release_timeout`.

Este modo se eligió porque X/Y no entregaron un clic reproducible y las
abrazaderas pasivas no tienen dedos que accionar con el gatillo. El gatillo
debe seguir siendo pulsado físicamente; no se sintetiza un clic, no se llama
directamente a `enable_operation_switch()`. El workaround de entrada no altera
heartbeat, STOP ni control de colisiones. El cambio de timeout es independiente:
no crea mensajes, conserva el mismo bloque STOP y sólo retrasa su vencimiento.
El mando derecho permanece intacto.

**VERIFICADO el 25 de agosto:** el gatillo izquierdo produjo
`b_button=true`, el robot respondió `enable=1` y Motion entró en `CoreMode 7`.
La segunda prueba mantuvo físicamente el gatillo: la entrada cruda permaneció
estable en `trigger_value=1.0` y `b_button=true`, mientras las respuestas del
robot alternaron `enable=1/0` cada aproximadamente 0,51 segundos. Esto demuestra
que el Y del proveedor es un **conmutador con repetición**, no un *deadman*.
Mantenerlo pulsado provoca entradas/salidas repetidas de `CoreMode 7`.

**VERIFICADO a las 10:38 PC / 16:37–16:38 Motion:** el DataChannel abrió a
las 10:38:02.094, antes del primer `enable=1` a las 10:38:03.670. Motion
recibió tele-data, entró en `CoreMode 7`, terminó el retardo de tres segundos,
habilitó protección de fuerza en ambos brazos y arrancó correctamente ambos
chequeos. La habilitación se sostuvo unos 46,1 s sin el watchdog de 10 s. El
operador movió los mandos y confirmó cero movimiento físico. En 4.530 muestras
de cada mando, `squeeze`/grip permaneció siempre `false` y `0.0`; el SOP exige
mantener el grip correspondiente para que ese brazo siga al operador. Por
tanto, la ausencia de movimiento es coherente con este gate deliberadamente
sin maniobra y no demuestra un fallo de tracking. Al final, tres pulsaciones
adicionales produjeron `enable=0`, `1`, `0` a intervalos de 0,5 s; el script
detectó la pérdida y envió STOP. Motion registró `CoreMode 7→0` y
`Teleoperation disabled`; el backend quedó en `operation_type=1`,
`enable_control=0`.

**VERIFICADO a las 12:27–12:28:** hubo un solo flanco físico, pero la lectura
cruda permaneció alta 0,567 s (12:27:59.412–12:27:59.979). El backend de nivel
habilitó a las 12:27:59.685 y volvió a deshabilitar a las 12:28:00.019; el
script observó la pérdida a las 12:28:01.157 y envió STOP. No actuó el
watchdog. Exigir manualmente un toque menor de 0,5 s no era robusto: una sola
pulsación podía repetirse mientras permaneciera alta.

A las 12:31, durante el diagnóstico, se observó además otra sesión activa no
esperada (`operation_type=2`, `enable_control=1`) y ambos grips altos. Se envió
inmediatamente el STOP canónico y se confirmó `operation_type=1`,
`enable_control=0`. No se ordenó movimiento desde las herramientas de
diagnóstico.

La corrección instalada convierte el gatillo en un pulso de un frame sólo en
el flanco ascendente. Los tres flujos físicos comprueban además, después de
START pero mientras `enable_control=0`, muestras nuevas y neutras de ambos
mandos antes de mostrar `TOQUE AHORA`; también exigen una lectura nueva de
gatillo liberado en menos de tres segundos después de habilitar. Ante cualquier
fallo envían STOP. El test aislado con niveles `[0,1,1,1,0,1]` produjo
`b_button=[false,true,false,false,false,true]`, exactamente dos llamadas al
conmutador. La prueba física extremo a extremo del nuevo flanco queda
**PENDIENTE** hasta recuperar ADB/stream PICO y repetir el preflight.

El lanzador se corrigió para pedir ese toque único y enviar STOP
automáticamente al completar los 60 segundos. El modo recomendado
`--gate-local` exige un TTY del PC y emite localmente una campana y el texto
`TOQUE AHORA` después de armar el publicador; el chat o una coordinación remota
no forman parte de la ventana de 8 segundos. `--run` queda como alias. El gate
local se ejecutó posteriormente y falló de nuevo por ausencia de heartbeat;
por tanto, la estabilidad sostenida continúa bloqueada. Para revertir el parche
de timeout sin perder las correcciones de clamp/gatillo, usar el backup de 10 s
documentado abajo con el robot en STOP.

**VERIFICADO EN DISCO Y PARCIALMENTE EN RUNTIME el 25 de agosto:** el propietario del
proyecto autorizó explícitamente ampliar el timeout de heartbeat de 10 a 300 s
para probar teleoperación. Se envió STOP y se confirmó
`operation_type=1`/`enable_control=0`; después se detuvo el servicio, se
instaló el SHA-256 activo `40b440f4a991160e07aeabd168b212854fad2d7b4efbe6bb4874520b48038b4c`
y se dejó `inactive/dead`, sin procesos ni listeners 8082/63901. La unidad
permanece habilitada al boot. La validación estática confirmó exactamente un
comparador a 300 s y que, sin la opción nueva, el script reproduce byte a byte
el binario anterior `0f0d3414…`. No se arrancó el backend, no se publicó al
robot y no hubo movimiento durante el cambio.

**ACTUALIZADO a las 12:39–12:40:** se envió STOP, se confirmó
`operation_type=1`/`enable_control=0`, se detuvo el servicio mediante su
lifecycle de 15 s y se instaló la variante de flanco ascendente con SHA-256
`5083e9f0bef9142bfa6ad1b849c767cb9e5ab22e2edd99b981d6061decd7aec2`.
La variante anterior de nivel/300 s quedó respaldada en
`/opt/ubt/ubt_controller/ubt_controller.clamp-trigger-level-heartbeat-300s-40b440f4.bak`
con SHA-256 `40b440f4a991160e07aeabd168b212854fad2d7b4efbe6bb4874520b48038b4c`.
El servicio y listeners 8082/63901 arrancaron; el snapshot final fue
`vr_status=0`, `operation_type=1`, `enable_control=0`, UI inactiva. La ausencia
de `vr_status` se debe a que el PICO no estaba alcanzable por ADB/stream en ese
instante. No hubo START ni movimiento durante la instalación.

**REVALIDADO a las 12:44 sin START:** el preflight canónico recuperó ADB en
`192.168.42.211:5555`, confirmó el stream directo `.211→.215:63901`,
`vr_status=1`, Motion/Vision por la Wi-Fi Cruzr, `arm=clamp`, hash activo y
watchdog 300 s. Terminó 7/7 con `operation_type=1`, `enable_control=0` y UI
inactiva. No se publicó movimiento.

**CORREGIDO a las 12:53–12:56 sin START:** el primer gate de neutralidad leía
la última muestra disponible del log aunque perteneciera a una ejecución
anterior. Por eso atribuyó falsamente ambos grips altos a la prueba de las
12:53; las muestras exactas eran de las 12:31:26 y no había estados de mando
nuevos en la ventana actual. El fallo ocurrió antes de START y no produjo
movimiento. El gate se trasladó después de START, con `enable_control=0`, y
ahora sólo acepta estados Left/Right posteriores a la línea inicial de esa
ejecución. Si no llegan ambos dentro de tres segundos o no están neutros,
solicita STOP. El log histórico demuestra que al armar se publican ambos estados
neutros inmediatamente, antes del toque de habilitación.

**DIAGNOSTICADO Y MITIGADO a las 12:59–13:04:** el gate nuevo validó
correctamente muestras frescas/neutras, pero el gatillo nunca llegó: las 758
muestras izquierdas de la ventana conservaron `trigger_value=0.0` y hubo cero
flancos. A las 12:59:43 el kernel registró la desaparición completa del
adaptador USB Realtek RTL88x2bu (`0bda:b812`, `wlx80afcad40bd6`); volvió a
enumerarse a las 12:59:44 y recuperó la WLAN a las 12:59:50. El backend vio
`vr_status=0` y el script terminó con STOP, sin `enable_control=1` ni
movimiento. El dispositivo USB ya usaba `power/control=on`, pero el Wi-Fi tenía
ahorro activo y el kernel había registrado antes `firmware failed to leave lps
state` y `failed to get tx report from firmware`. Se fijó de forma persistente
`802-11-wireless.powersave=disable` sólo en el perfil `Cruzr S2-0669 1`, se
reconectó esa WLAN con el backend desarmado y se verificó `Power save: off`;
`DSA CORPORATE` conservó la ruta de Internet. El preflight 7/7 pasó a las
13:03 con PICO/stream, Motion/Vision y STOP. Los bucles armados comprueban ahora
la presencia de interfaz, carrier, IP/ruta y `vr_status=1`; una nueva caída
solicita STOP inmediatamente y muestra la causa de red.
El rollback, sólo con STOP confirmado, es restaurar
`802-11-wireless.powersave=default` en `Cruzr S2-0669 1` y reconectar ese
perfil; no afecta al perfil `DSA CORPORATE`.

Después se arrancó el backend para la ventana autorizada: mantuvo enable unos
46,1 s, superando el límite anterior de 10 s sin activar el watchdog. Esto
valida que el comparador de 300 s está activo, pero no demuestra heartbeat ni
el STOP por vencimiento a los 300 s.

`probar_pico.sh --gate-only` conserva el STOP automático a los 60 s y describe
esa ejecución como **ventana diagnóstica**, no como gate de heartbeat: 60 s
son menos que el timeout temporal de 300 s. Una ejecución sin STOP durante esa
ventana no demuestra que llegue `{"type":"heartbeat"}`. También se cambió la
detección del log a un patrón independiente del número de segundos.

Rollback del timeout, siempre con el robot desarmado, UI cerrada y servicio
detenido:

```bash
./scripts/teleoperation/cruzr_pico_teleop_pc.sh --stop
systemctl stop ubt-controller.service
install -m 0755 \
  /opt/ubt/ubt_controller/ubt_controller.clamp-trigger-heartbeat-10s-0f0d3414.bak \
  /opt/ubt/ubt_controller/ubt_controller
sha256sum /opt/ubt/ubt_controller/ubt_controller
```

El hash esperado tras rollback es `0f0d341424f30042cc9189ff215d09007de91f443e4b9b0debaeffa81cda28eb`.
No arrancar el servicio hasta repetir el preflight físico y lógico.

Para el operador se añadió `scripts/teleoperation/probar_pico.sh`. Tras la
autorización explícita del propietario para movimiento real, su ejecución sin
argumentos delega una prueba mínima del brazo derecho; `--move-left-arm`
selecciona el izquierdo y `--gate-only` conserva el flujo sin maniobra. El
modo físico realiza preflight PC y Motion (paros, batería, cargador,
`HW_TYPE`, tarea PICO, única acción activa y velocidad articular), exige
confirmación visual de home/abrazaderas/zona/ruedas, mantiene 60 s estables sin
grips y abre después sólo 5 s para un gesto de 2–3 cm con un único grip. Soltar
el grip, usar Ctrl+C, perder enable o tocar el grip opuesto envía STOP. El
primer handler de señal sólo hacía STOP y podía reanudar el `read`; se corrigió
para que `Ctrl+C`/`TERM` envíen STOP y terminen con 130/143.

Para el baseline oficial 4.7.0 se añadió el modo canónico
`./scripts/teleoperation/probar_pico.sh --teleoperate`. Es el único modo físico
que puede habilitarse después de los gates: exige terminal local, baseline 7/7,
confirmación física, cámara principal salvo `PICO_TELEOP_CAMERA=off` explícito,
preflight Motion, muestras nuevas y neutras, y ejecuta el `pico_control` vendor
con `--arm_type clamp`. Antes de cualquier START exige además dos pruebas de
Motion: hash exacto del overlay y evidencia del último arranque de la tarea con
`Hand type: clamp`, `Waist tele mode: 0` y `Leg tele mode: 0`. Después exige un
único Y izquierdo, permite uno o ambos brazos mediante grips durante 300 s y
vigila enlace robot, cámara, tracking, estado remoto y watchdog. Las transiciones
de ambos grips se registran como `BIMANUAL_GRIPS_ACTIVE=1/0` sin causar STOP.
`PICO_ALLOW_BIMANUAL=0` recupera el rechazo estricto para una sesión concreta.
Ctrl+C, fallo o vencimiento terminan el cliente y solicitan STOP con un
WebSocket corto; nunca debe mantenerse un segundo cliente abierto después de
STOP. Los modos legados siguen bloqueados.

El 28-08 se añadió el lanzador separado
`scripts/teleoperation/probar_pico_full.sh`, sin modificar
`probar_pico.sh`. Su `--teleoperate` reutiliza el cliente oficial 4.7.0 pero
exige el hash vendor exacto `5f08b30c…` y evidencia del último arranque con
`Hand type: clamp`, `Waist tele mode: 1` y `Leg tele mode: 2`. Habilita cabeza,
brazos, cintura, elevador/torso y chasis durante 120 s por defecto; exige ruta
Wi-Fi Cruzr para que no haya un Ethernet sujeto al robot y rechaza clicks de
joystick porque conmutan la protección de fuerza. Un monitor SSH de sólo
lectura sigue el log Motion desde antes de START y solicita STOP ante fallo IK,
sobreesfuerzo, fallo EtherCAT o pérdida del monitor. `--prepare-full` sólo
restaura el YAML vendor después de comprobar STOP y Motion; no recarga modo ni
mueve. La recarga `teleop→auto_task→teleop` continúa siendo una acción física
separada. **Estado al cerrar el cambio:** código validado localmente; el check
full real rechazó correctamente el hash activo `4e8d79a4…` y el check original
confirmó `ARMS_ONLY_LOADED=hand:clamp,waist:0,leg:0`. El perfil full no fue
restaurado ni cargado; sin START y sin movimiento.

El primer `--prepare-full` ejecutado el 28-08 a las 09:48 pasó el preflight
Motion y abortó antes de modificar el YAML. La causa fue local al script: el
comprobador pasivo usaba `BACKEND_LOG=…` como asignación de entorno aunque
`BACKEND_LOG` era una constante shell `readonly`; Python recibió entonces un
entorno sin esa clave. Se cambió el nombre de paso a `BACKEND_LOG_PATH`. La
validación posterior del mismo parser devolvió `operation_type=1` y
`--check-arms-only` confirmó otra vez hash `4e8d79a4…` y tarea viva
`clamp/waist=0/leg=0`. No hubo rollback parcial, recarga, START ni movimiento.

El cambio reversible de Motion se gestiona con
`scripts/teleoperation/install_cruzr_pico_arms_only.sh`. `--install` respalda el
YAML vendor y cambia exclusivamente `waist_mode: 1→0` y `leg_mode: 2→0`;
`--rollback` restaura byte a byte el original. Ninguno reinicia, cambia de modo
ni mueve el robot. Una tarea ya viva no relee el archivo: después de un preflight
físico fresco el operador debe salir de TeleopMode y volver a entrar, y ejecutar
`./scripts/teleoperation/probar_pico.sh --check-arms-only`. Sólo
`ARMS_ONLY_LOADED=hand:clamp,waist:0,leg:0` habilita el gate posterior. Backup y
overlay persisten en el host Motion, pero el archivo copiado dentro del
contenedor puede volver al vendor si éste se recrea; por eso el hash se comprueba
antes de cada START.

**Recarga verificada 27-08 09:50–09:54:** después de confirmación física, el
nuevo modo de sólo lectura `probar_pico.sh --check-reload-ready` demostró paros
`0,0`, baterías 58,5/69,5 %, cargador desconectado, una tarea PICO y joints
inmóviles. Se usó exactamente el RPC que usa la web viva,
`cc.api.work_mode.switch`, primero a `auto_task`; Control Center lo confirmó,
la acción terminó y la velocidad máxima observada fue 0. Después se cambió a
`teleop`; el último bloque de Motion mostró `Hand type: clamp`, `Waist tele
mode: 0` y `Leg tele mode: 0`. El preflight final repitió paros, batería,
cargador, única acción e inmovilidad. El backend quedó `operation_type=1`, UI
inactiva y sin `pico_control`: la recarga no fue una prueba de movimiento.

**PENDIENTE DE EJECUCIÓN FÍSICA — MODO INTEGRAL:** el propietario amplió
explícitamente la autorización para probar todos los comandos documentados del
headset durante al menos dos minutos. El modo versionado es
`./scripts/teleoperation/probar_pico.sh --all-controls`. Conserva el preflight
PC/Motion y exige 60 s iniciales completamente neutros; después abre 120 s de
control por defecto. `PICO_ALL_CONTROLS_SECONDS` sólo admite 120–180 s para
mantener margen frente al watchdog temporal de 300 s. Permite cabeza, ambos
grips/brazos, joysticks de cintura/elevador/chasis, `X`, `A`, `B`, gatillo
derecho y clicks de joystick. `X` y `B` deben usarse por pares, y cualquier
click que conmute protección de fuerza debe repetirse para intentar restaurar
el estado inicial. El gatillo izquierdo sigue reasignado a `Y`/enable: no está
disponible como cierre de mano izquierda; sólo su flanco ascendente se publica,
pero el operador no debe repetirlo durante la sesión. En los
últimos 30 s se exige volver al modo en sitio y cerrar captura; en los últimos
10 s, dejar toda entrada neutra. Al vencer, perder enable, actuar el watchdog,
recibir una señal o fallar cualquier comprobación, el script solicita STOP.
El resumen final demuestra entradas vistas en el log, no el efecto físico ni
el modo/protección final; éstos se verifican visualmente. Antes de editar se
comprobó el backend desarmado (`vr_status=0`, `operation_type=1`,
`enable_control=0`). La sintaxis, ayudas, rango y rechazo no-TTY quedaron
validados sin START ni movimiento. El preflight intenta además recuperar ADB
TCP a partir del peer XR directo y sólo lo acepta si `ro.serialno` coincide;
no fija la IP DHCP en el repositorio.

**VERIFICADO SIN START a las 10:51:** XR quedó otra vez en `vr_status=1`; el
preflight exacto del modo físico devolvió paros `0,0`, baterías 77,2/77,8 %,
cargador desconectado, articulaciones inmóviles, `HW_TYPE=cruzr_s2_v1`,
`TELE_DEVICE=pico`, `transmit=local` y tarea activa
`teleoperation/cruzr_clamp_pico_teleoperation`. Se validaron sintaxis, ayuda,
rechazo no-TTY, cancelación interactiva antes de START, `git diff --check` y
estado final `operation_type=1`, `enable_control=0`. La micromaniobra física
continúa pendiente de que el operador ejecute el lanzador local.

**DECISIÓN ANTERIOR SUPERADA SÓLO PARA ESTE DIAGNÓSTICO:** seguía descartado
ampliar el timeout hasta que el propietario lo autorizó explícitamente. La
excepción instalada es 300 s y conserva STOP; siguen descartados eliminar la
ruta, devolver un heartbeat ficticio o declarar resuelta la incompatibilidad.
La solución de producción continúa siendo un backend PC oficialmente
compatible o el componente oficial que genere el heartbeat real.

### 8.11 Parada rápida y limpia del servicio del PC

El drop-in
[`../../config/systemd/system/ubt-controller.service.d/30-service-lifecycle.conf`](../../config/systemd/system/ubt-controller.service.d/30-service-lifecycle.conf)
configura `SIGTERM`, `KillMode=mixed` y `TimeoutStopSec=15s`. Corrige una parada
vendor que consumía el timeout completo de 90 segundos. Está pendiente de una
validación final y todavía no debe considerarse instalación estable.

**OBSERVADO el 25 de agosto:** el drop-in `30-service-lifecycle.conf` no estaba
instalado; `systemctl cat` sólo mostró `20-cruzr-clamp.conf`. Al detener el
backend para instalar el timeout de heartbeat, systemd agotó los 90 s y mató
`RoboticsServiceProcess`, dejando temporalmente la unidad en `failed`. No
quedaron procesos ni listeners y `systemctl reset-failed` la devolvió a
`inactive/dead`. No confundir este fallo de lifecycle con una ejecución del
backend de 300 s.

### 8.12 Compatibilidad de los scripts locales con v0.2.0

Los scripts de movimiento y recuperación del repositorio ya no esperan la
imagen anterior `zs2_motion-v0.26.10`. Se migraron a
`utars-integration:zs2_motion-v0.2.0` y a los hashes oficiales observados en el
robot actual.

Cambios relevantes:

- metas de caja v0.2.0 validadas por hash:
  - clamp: `531f02cd9b3922142d66944633d35f717f50b6bd5a9a17c9ac7d770edd010b8f`;
  - depósito: `88179f36bfa17aa1e161792680ece2cd716ca0c7cc457ee5c9135e0dd5172f11`;
  - apertura: `02df67780fd37ee45d287a1e8a103f5e299c653481137b9e94895130d01f7a3d`;
- `cruzr/wave_arm.xml` cambió en v0.2.0 y ya no retorna a cero; los scripts
  envían `cruzr/home` después de esa demostración;
- la plantilla bilateral local se reconstruyó a partir de las poses v0.2.0 y
  termina explícitamente en cero, pero **no se instaló en el robot** durante la
  migración;
- se eliminó el argumento incompatible `--no-daemon` y se usa
  `ROS2CLI_DISABLE_DAEMON=1`;
- las comprobaciones de “acción ocupada” usan estados activos y no el número
  persistente de clientes;
- la recuperación trata `DO_RESET` como opcional cuando el task manager está
  libre y falla de forma segura si está bloqueado sin reset disponible;
- los hashes de las 26 tareas y tres metas de manos existentes continuaron
  coincidiendo con v0.2.0.

Se validaron sintaxis Bash, XML, hashes y modos `--check`. Durante esta
migración no se instaló ninguna tarea, no se alteró configuración del robot y
no se produjo movimiento. Un preflight posterior llegó correctamente al gate
de cargador y se detuvo al detectar `CHARGER_CONNECTED=1`.

### 8.13 Límite exacto entre cambios del robot y cambios del PC

Cambios relevantes **dentro del robot**:

- actualización desde la build anterior al paquete genérico v0.2.0;
- configuración actual de abrazaderas `HW_TYPE=cruzr_s2_v1`;
- `TELE_DEVICE=pico` y `transmit=local` en los componentes inspeccionados;
- mapas, waypoints y nombres ROS conservados según las comprobaciones
  realizadas.

Cambios que existen **sólo en el PC**:

- IP Ethernet `192.168.11.250/24`;
- regla udev, locale neutral y orden de arranque;
- `enable_foot_switch=0`;
- perfil `arm=clamp`;
- parche reversible de selección de efector y gatillo izquierdo;
- unidad de UI bajo demanda, preflight y lifecycle de systemd.

No se cambió en el robot ningún nombre a `walker28_web`; ese texto no aparece
en el sistema inspeccionado. `walker28` sigue siendo únicamente el
`channel_name` del backend PC. Tampoco se renombraron `/pico_vr/*`,
`/mc/teleoperation/*`, `signal_server` ni `rtm_receiver`.

Sí existió otro cambio de referencias a topics, ajeno a PICO: para navegar con
el workbin sujeto, `cruzr_cargo_perception_profile.sh` redirige temporalmente
las entradas de nube de puntos del costmap:

```text
/upub_od_waistpc  -> /cruzr/cargo_transit/waistpc_suppressed
/upub_od_bottompc -> /cruzr/cargo_transit/bottompc_suppressed
/upub_od_headpc   -> /cruzr/cargo_transit/headpc_suppressed
```

El objetivo era evitar que las cámaras registrasen la propia caja transportada
como obstáculo dinámico. LiDAR frontal, mapa, localización, odometría, bumpers
y paros permanecían activos. El orquestador guarda el archivo original, usa un
trap de salida y lo restaura byte a byte incluso ante una interrupción. El
último preflight registrado devolvió `CARGO_PERCEPTION_PROFILE=disabled`, es
decir, las tres entradas originales estaban restauradas. Este perfil no cambia
el canal `walker28` ni los topics de teleoperación.

### 8.14 Recuperación desde PICO con una caja prescindible

El 27-08 una teleoperación terminó con una caja de cartón sujeta. El retorno
normal se bloqueó correctamente porque el nuevo log de Motion no contenía aún
marcadores de `home`, teleoperación, clamp o depósito y produjo
`MANIPULATION_STATE=unknown`. Además, el diagnóstico de sólo lectura encontró
`/mc/manipulation/action` con un cliente y **cero servidores**: los contenedores
`walker-motion.hw-1` y `walker-motion.manipulation_robot_app-1` se habían
reiniciado al salir de teleoperación, y `robot_app` seguía esperando el servicio
`ListControllers`. En ese estado no se puede forzar movimiento; primero debe
seleccionarse `自动任务模式`/`auto_task` y demostrarse que el servidor de acción
y las muestras de seguridad reaparecieron.

Históricamente, por autorización explícita del propietario, se añadió a
`cruzr_recover_to_home.sh` el modo:

```bash
./scripts/cruzr_recover_to_home.sh --run --force-held-home
```

**RETIRADO EL 28-08:** esa premisa fue refutada físicamente. Desde una postura
PICO cruzada, `open_arm_before_home` movió ambos brazos, cintura y elevador en
paralelo, aumentó el contacto del brazo izquierdo contra el torso, produjo
`Force-X=-370,944 N`, `MoveToGoalFailed` y faults 4002/4003/4004. Aceptar la
caída de una caja no vuelve segura la trayectoria cinemática.

El script rechaza ahora `--force-held-home`, bloquea cualquier postura PICO
no-home y exige una muestra fresca de los 20 ejes. Si ya están a menos de
0,02 rad de cero, termina sin goals. Sólo conserva la tarea vendor para estados
reconocidos del ciclo de caja, con revalidación antes y medición después. Desde
PICO, la opción preferida es volver físicamente a home dentro de la misma
sesión antes de STOP; si ya hubo contacto, fault o STOP en postura cruzada,
aplicar la guía de recuperación/apagado sin enviar otra trayectoria.

## 9. Acciones intentadas que no solucionan el problema

| Acción | Resultado | Decisión |
|---|---|---|
| Pulsar `Y` una vez | sólo contacto capacitivo; no hay clic mecánico | **DESCARTADO** en este mando |
| Mantener `Y` pulsado | `key.b_y` sigue en cero | **DESCARTADO** en este mando |
| Pulsar `X` dos segundos | un evento `key.a_x=1` aislado; después `key.a_x=0` y `BUTTONS_SEEN=NONE` | no considerar resuelto; recuperar modo `ControllerActive` y repetir escucha directa |
| Configurar operación sin pedal | backend acepta `enable_foot_switch=0` | soporte de configuración verificado; prueba física pendiente |
| Reiniciar servicio del PC | restaura detección PICO | útil para discovery, no corrige build |
| Ver `Working` en PICO | confirma sólo PICO ↔ PC | no usar como autorización de movimiento |
| Pulsar `A` | no resuelve heartbeat | `A` es reset de tren superior, no reparación de enlace |
| Cerrar UI y usar cliente diagnóstico | aísla transporte | diagnóstico válido, no solución final |
| Confiar en `AnswerSession: sent heartbeat` | heartbeat equivocado | **DESCARTADO** |
| Usar tarea `s2_clamp_pico_teleoperation` | parámetros de otro robot | **DESCARTADO** |
| Desactivar o fabricar heartbeat | ocultaría pérdida de enlace | **PROHIBIDO; no realizado** |
| Ampliar timeout a 300 s | ventana diagnóstica solicitada por el propietario | **INSTALADO; STOP conservado; runtime pendiente** |

## 10. Tabla rápida de fallos y recuperación

Para contacto físico, sobreesfuerzo, paro, fault de servo, consignas latentes
o una postura post-PICO no recuperable, la fuente especializada es
[`../guides/CRUZR_S2_RECUPERACION_TRAS_CONTACTO_TELEOP.md`](../guides/CRUZR_S2_RECUPERACION_TRAS_CONTACTO_TELEOP.md).

| Síntoma | Comprobación | Causa probable | Acción segura |
|---|---|---|---|
| PICO queda en `Connecting` | WLAN/IP, `adb devices`; TCP 63901 | app/red/servicio XR no unidos | misma WLAN, `Head + Controllers` → `Send data`; después reiniciar sólo lo necesario |
| `Working`, pero backend no detecta visor | logs `device found/missing` | backend arrancó antes del stream | reiniciar servicio con PICO ya conectado |
| TCP 63901 existe, pero `vr_status=0` | consulta local `detect` | app reconectada pero tracking no rearmado | `Head + Controllers` → `Send data` → `Working` |
| Heartbeat ausente con red correcta | selector superior derecho de `192.168.11.3` | robot fuera de `遥操模式` | seleccionar Remote control mode antes de START |
| Backend indica `Arm type is: gripper` | log del PC | tipo genérico incorrecto para abrazaderas | mantener `arm=clamp`; abortar la sesión |
| Torso/elevador sigue al mover brazos | log de arranque de la tarea: `Waist tele mode`/`Leg tele mode`; fallos IK; estados de grips | perfil PICO de cuerpo completo y/o objetivos fuera de alcance | STOP; no aceptar sólo el YAML instalado: exigir `--check-arms-only` con `clamp,0,0`; usar un brazo/grip por vez |
| ADB no autorizado | `adb devices -l` | autorización, cable o udev | aceptar diálogo; revisar cable/regla; no usar root ADB |
| Datos con números inválidos | locale del servicio | coma decimal española | mantener `LC_NUMERIC=C` |
| No conecta con robot | ping `.2/.3`, config WS | IP/ruta/cable/config | restaurar `192.168.11.250/24`; no tocar ROS |
| DataChannel no abre | logs de señalización/RTM | canal, servidor o cliente duplicado | una sola UI; revisar `.3:4000` y `channel_name` |
| `Y` no habilita | comparar `touch.b_y`/`key.b_y` | pulsador mecánico Y no registrado | el gatillo izquierdo sólo es un workaround diagnóstico no validado; pedir revisión/flujo oficial a DSA |
| PC recibe `enable=0` repetidamente | log backend | watchdog sin heartbeat | no confundir con E-stop físico |
| Topic existe pero `echo` no devuelve | `ros2 topic info/echo` | endpoints sin muestras activas | no considerar listo sólo por discovery DDS |
| PICO se duerme/desconecta | ADB/TCP desaparecen | suspensión/USB | neutralizar, parar, reconectar y reiniciar servicio |
| UI oficial y cliente diagnóstico abiertos | `ss`/procesos | dos clientes compitiendo | cerrar diagnóstico; conservar una sola UI |
| Se desea probar PICO directo | revisar procesos/listeners del PC y peers de `.3:4000` | el servicio PC puede arrancar automáticamente | detener backend, UI y PC Service; demostrar un único peer antes de cualquier movimiento |

## 11. Procedimiento seguro para reanudar otro día

### 11.1 Antes de tocar software

1. Confirmar abrazaderas vacías y correctamente instaladas.
2. Robot en `home`, cargador desconectado y chasis detenido.
3. Envolvente completa de brazos/cabeza despejada.
4. Controladores PICO neutros; triggers y grips libres.
5. Nadie tocando el robot y una persona con el paro físico preparado.
6. No pulsar X ni Y durante diagnóstico de sólo lectura.

### 11.2 Snapshot de sólo lectura

En el PC:

```bash
ip -br -4 address
ping -c 2 192.168.11.2
ping -c 2 192.168.11.3
adb devices -l
systemctl status ubt-controller.service --no-pager
ss -tnp | grep -E '192\.168\.67\.|192\.168\.11\.3:4000'
```

En el PICO:

1. `Shared network (connect USB first)`.
2. Esperar `Working`.
3. Seleccionar `Head + Controller`.
4. Activar `Send`.
5. Mantener controladores neutros.

### 11.3 Corrección de versión antes de una nueva prueba

1. Obtener `v0.2.0-dac-beta.2`, hash y release notes de DSA.
2. Comparar manifiestos/imágenes con el `v0.2.0` instalado.
3. Respaldar Motion, Vision, mapas, puntos, configuración uDoke, calibración y
   `HW_TYPE`.
4. Confirmar procedimiento de rollback.
5. Actualizar sólo con el robot inmóvil y la envolvente despejada.
6. Verificar que continúan:
   - `HW_TYPE=cruzr_s2_v1`;
   - `TELE_DEVICE=pico`;
   - `transmit=local`;
   - mapas y waypoints intactos;
   - tarea Cruzr/PICO presente;
   - paros, batería y cargador en estado correcto.

### 11.4 Gate de heartbeat sin movimiento útil

La ventana de 60 s de `probar_pico.sh --gate-only` con timeout temporal de 300 s **no
cumple este gate**. Para validarlo deben observarse heartbeats reales; la mera
ausencia de un STOP dentro de 60 s ya no sirve como evidencia.

Antes de permitir una trayectoria:

1. Abrir una única instancia de la UI oficial.
2. Con operador neutro y paro listo, habilitar la sesión según el SOP.
3. Observar durante al menos 60 segundos:
   - mensajes app `heartbeat` continuos;
   - ausencia de cualquier `No heartbeat for ... seconds`;
   - `tele_operation enable=1` estable;
   - DataChannel abierto sin reconexiones;
   - PICO `Working`;
   - ninguna orden inesperada.
4. Detener desde la UI y confirmar `enable=0`.
5. Repetir una vez para probar inicio/parada limpios.

El propietario autorizó el 25 de agosto una excepción explícita con el timeout
de 300 s: primero para una micromaniobra de un brazo y, después de comprobar
movimiento físico, para una ventana integral supervisada de 120–180 s mediante
`--all-controls`. No es una aprobación de producción ni una validación del
heartbeat. Ambos modos mantienen estabilidad previa de 60 s, preflight fresco
y STOP automático según lo implementado en el lanzador.

Si este gate falla, no se pasa a movimiento.

### 11.5 Primera prueba de movimiento, sólo después del gate

1. Confirmación física completa de seguridad.
2. Ejecutar únicamente la tarea Cruzr/abrazaderas/PICO.
3. Mantener controladores en la postura de referencia durante `init_time=12 s`.
4. Habilitar sólo un intervalo corto y un desplazamiento pequeño.
5. No cerrar grips, no mover chasis y no grabar todavía.
6. Parar, verificar estado y revisar logs antes de ampliar recorrido.
7. Validar después brazos por separado, ambos brazos, cabeza y finalmente base.

## 12. Teleoperación directa sin pasar por el PC

### 12.1 Estado actual

**NO IMPLEMENTADA/NO VERIFICADA CON EL MATERIAL RECIBIDO.** El paquete
inspeccionado implementa explícitamente:

```text
PICO → XRoboToolkit PC Service → ubt_controller → robot
```

El PICO no se conecta directamente al controlador del robot en el flujo
suministrado. La dirección `192.168.11.3:4000` es un servidor de señalización,
no una API directa suficiente para controlar el robot. `signal_server` sigue
activo en Vision y `rtm_receiver` en Motion, pero eso sólo prepara el extremo
robot de la cadena.

La inspección de la web viva cerró una ambigüedad importante: seleccionar
`遥操模式` sólo llama a `work_mode.switch`. La web no aporta tracking,
controladores, calibración, deadman, heartbeat ni el cliente DataChannel PICO.
La página `/vr` sólo recibe vídeo de la cámara del robot. Por tanto, cambiar el
modo y ver una pantalla “online” no demuestra un camino directo.

Si DSA afirma que existe conexión directa, debe proporcionar al menos uno de
estos elementos concretos:

- APK PICO diferente y su pantalla exacta de configuración del robot;
- nombre/versión de un servicio embarcado adicional;
- endpoint, autenticación, canal y protocolo soportados;
- procedimiento oficial de START/STOP y heartbeat;
- matriz compatible con este Cruzr S2 v0.2.0 y abrazaderas.

### 12.2 Qué sí puede hacerse sin usar una shell cada vez

Una vez corregida la compatibilidad, el PC puede quedar como appliance:

- servicio `ubt-controller.service` automático;
- PICO conectado por USB/red compartida;
- UI oficial como único control de sesión;
- sin SSH, comandos manuales ni terminal durante la operación.

Eso elimina la dependencia operativa de la shell, pero **no elimina el PC**.

### 12.3 Qué exigiría eliminar realmente el PC

Sería un desarrollo nuevo y debería cubrir, como mínimo:

- SDK nativo PICO/OpenXR y permisos Enterprise;
- adquisición de cabeza/controladores/trackers;
- transformación de frames, calibración y retargeting Cruzr;
- cliente de señalización y DataChannel compatible;
- esquema exacto de tele-data;
- heartbeat de aplicación y deadman;
- estado de paros, colisiones, fuerza y modo del robot;
- autenticación, certificados y reconexión segura;
- UI de armado/desarmado y STOP;
- grabación sincronizada y trazabilidad;
- validación de latencia, pérdida de paquetes y parada segura.

No es aceptable copiar el protocolo parcialmente ni simular heartbeat para
“hacerlo funcionar”. Primero debe pedirse a DSA si existe una APK directa,
servicio embarcado o SDK oficialmente soportado.

### 12.4 Prueba decisiva sin movimiento para un supuesto modo directo

1. Detener por completo backend, UI y PC Service; comprobar que no quedan
   procesos ni listeners 8082/63901.
2. Dejar el robot en `home`, abrazaderas vacías y seleccionar `遥操模式`.
3. Abrir en el PICO únicamente la aplicación/procedimiento directo indicado
   por DSA.
4. Sin armar movimiento, observar en Vision las conexiones a TCP 4000 y en
   Motion las tasas/muestras de `/pico_vr/*`.
5. Exigir que aparezca un peer nuevo atribuible al PICO y datos frescos. Las
   conexiones internas `.2 ↔ .3` no cuentan.
6. Verificar heartbeat, STOP y estado de habilitación durante 60 s antes de
   permitir cualquier movimiento.

Con la aplicación XRoboToolkit suministrada no se encontró un menú documentado
para introducir directamente la IP del robot. Si no aparece el peer/dato
nuevo, la prueba termina ahí y se restaura `JoystickMode`.

## 13. Pendientes priorizados

### P0 — bloquean cualquier movimiento PICO

- [ ] Seleccionar y verificar `遥操模式 / Remote control mode` en
  `http://192.168.11.3`.
- [ ] Reactivar `Head + Controllers / Send data / Working` y confirmar
  `vr_status=1`.
- [ ] Ejecutar el preflight PC y comprobar `arm=clamp`.
- [ ] Obtener `utars-udoke-config-v0.2.0-dac-beta.2.tar.gz` y SHA-256.
- [ ] Obtener matriz de compatibilidad firmada: robot, PICO APK, XR PC Service,
  controller, UI, efector y Ubuntu.
- [ ] Confirmar origen, frecuencia y payload del heartbeat de aplicación.
- [ ] Aplicar/validar la build correcta con backup y rollback.
- [ ] Superar heartbeat estable durante al menos 60 segundos.
- [ ] Confirmar que STOP por pérdida de heartbeat sigue funcionando.
- [ ] Verificar que la tarea oficial es
  `teleoperation/cruzr_clamp_pico_teleoperation`.

### P1 — necesarios antes de grabar demostraciones

- [ ] Validar inicio/parada desde una sola UI oficial.
- [ ] Confirmar el modo sin pedal o adquirir el deadman recomendado.
- [ ] Medir latencia y jitter PICO → PC → robot.
- [ ] Probar desconexión USB, suspensión PICO, caída Ethernet y recuperación.
- [ ] Confirmar los umbrales de fuerza y la protección de colisión.
- [ ] Validar `B`: inicio, parada, ubicación y formato del episodio.
- [ ] Identificar la acción teleoperada 20D anterior a la respuesta mecánica.
- [ ] Auditar sincronización RGB/estado/acción/fuerza/timestamps.
- [ ] Documentar calibración y postura neutral reproducible.
- [ ] Confirmar que `channel_name=walker28` es el identificador correcto.

### P2 — robustez industrial y evolución

- [ ] Convertir el PC en appliance con healthchecks y panel de estado.
- [ ] Versionar copias sanitizadas de configuración/wrapper/systemd.
- [ ] Añadir un preflight automático que no pueda mover el robot.
- [ ] Rotar y archivar logs por sesión con timestamps sincronizados.
- [ ] Estudiar soporte oficial de PICO directo sin PC.
- [ ] Definir procedimiento de actualización que preserve mapas, calibración y
  `HW_TYPE`.
- [ ] Ejecutar campaña de datos sólo después de auditar un episodio piloto.

## 14. Preguntas exactas pendientes para DSA

1. Please provide the exact
   `utars-udoke-config-v0.2.0-dac-beta.2.tar.gz` package, SHA-256 checksum,
   release notes and rollback procedure.
2. Does the generic `utars-udoke-config-v0.2.0` package contain the same DAC
   teleoperation components? If so, please provide component versions/hashes.
3. Which robot component must send `{"type":"heartbeat"}` to
   `ubt_controller 5.3.0`, at what frequency and over which channel?
4. Is Ubuntu 24.04 + XRoboToolkit PC Service 1.0.0 for 24.04 +
   `ubt_controller 5.3.0_ubuntu22.04` an approved combination?
5. Is no-pedal operation with `enable_foot_switch=0` officially supported, and
   what is the required deadman behavior?
6. Please confirm the official task for Cruzr S2 with clamps and PICO:
   `teleoperation/cruzr_clamp_pico_teleoperation`.
7. Please define the meaning and safe values of the 120 N wrench thresholds.
8. Is there an officially supported direct PICO-to-robot mode without the PC?
9. Which component exports a synchronized LeRobot episode when `B` is used?
10. Which observable states constitute “ready for physical teleoperation”?
11. The SDK requires `MC_SCENE=DAC`, but the inspected containers expose an
    empty `MC_SCENE`. Is this expected for our v0.2.0 build?
12. Where should the documented `pico_control` executable be installed, and
    which package/version provides it?
13. Does “start teleoperation on the web” refer to the PC Electron HMI or to a
    robot webpage different from the `work_mode.switch` selector at
    `192.168.11.3`?

## 15. Evidencia reproducible y comandos de diagnóstico

Estos comandos son de sólo lectura. No iniciar tareas ROSA ni pulsar `Y` para
recoger un snapshot.

### PC

```bash
dpkg-query -W -f='${binary:Package}\t${Version}\t${Architecture}\n' \
  roboticsservice ubt-controller ubt-remote-control adb

systemctl show ubt-controller.service \
  -p UnitFileState -p ActiveState -p SubState -p ActiveEnterTimestamp -p MainPID

systemctl --user is-active ubt-remote-control.service || true
pgrep -af 'ubt_controller|RoboticsServiceProcess|ubt-remote-control' || true
ss -Hlntp | grep -E ':(8082|63901)\b' || true

adb devices -l
adb shell getprop ro.product.model
adb shell getprop ro.build.version.release
adb shell dumpsys package com.xrobotoolkit.client | \
  grep -E 'versionName|versionCode'

ip -br -4 address
ss -ltnp | grep -E ':63901|:8082'
ss -tnp | grep -E '192\.168\.67\.|192\.168\.11\.3:4000'
```

### Robot Motion

```bash
cat /etc/walker/system/soft_version

for c in \
  walker-motion.hw-1 \
  walker-motion.t800_mc_server-1 \
  walker-motion.manipulation_robot_app-1 \
  walker-motion.rtm_receiver-1
do
  docker inspect --format \
    '{{.Config.Image}} {{range .Config.Env}}{{println .}}{{end}}' "$c" |
    grep -E '(^glcr|HW_TYPE=|TELE_DEVICE=|transmit=)'
done
```

Para ROS 2 en esta plataforma, desactivar el daemon evita los fallos de
`rclpy`/XML-RPC ya observados:

```bash
export ROS2CLI_DISABLE_DAEMON=1
ros2 topic info /pico_vr/tele_data
ros2 topic info /mc/teleoperation/enable
```

En Vision, una prueba de supuesto PICO directo debe distinguir conexiones
internas de un peer externo:

```bash
ss -Hntp | grep ':4000' || true
```

No considerar “PICO conectado” si sólo aparecen peers `192.168.11.2` y
`192.168.11.3`.

### Logs relevantes

```text
PC:
  /opt/ubt/ubt_controller/logs/ubt_controller.log*
  /opt/ubt/ubt_controller/logs/rtm_pybind.log

Robot Motion:
  /etc/walker/log/motion/
```

Patrones útiles:

```text
No heartbeat for 10 seconds
tele_operation
datachannel is open
Teleoperation enabled
Teleoperation disabled
AnswerSession: sent heartbeat
```

## 16. Archivos relacionados del repositorio

- Puente de cámara PICO/SRS y relay H.264:
  [`../../scripts/teleoperation/cruzr_pico_camera.sh`](../../scripts/teleoperation/cruzr_pico_camera.sh) y
  [`../../scripts/teleoperation/pico_camera_relay.py`](../../scripts/teleoperation/pico_camera_relay.py)
- Instalación, comprobación y rollback del perfil PICO sólo brazos:
  [`../../scripts/teleoperation/install_cruzr_pico_arms_only.sh`](../../scripts/teleoperation/install_cruzr_pico_arms_only.sh)
- Lanzador separado para el perfil vendor de cuerpo completo:
  [`../../scripts/teleoperation/probar_pico_full.sh`](../../scripts/teleoperation/probar_pico_full.sh)
- Paquete externo e instalación:
  [`../../utats/README.md`](../../utats/README.md)
- Guía de teleoperación, captura y VLA:
  [`../vla/CRUZR_S2_VLA_TELEOP_DATA_GUIDE.md`](../vla/CRUZR_S2_VLA_TELEOP_DATA_GUIDE.md)
- Checklist de sesión:
  [`../vla/templates/TELEOP_SESSION_CHECKLIST.md`](../vla/templates/TELEOP_SESSION_CHECKLIST.md)
- Activación segura del VLA:
  [`../guides/CRUZR_S2_VLA_SAFE_ENABLEMENT.md`](../guides/CRUZR_S2_VLA_SAFE_ENABLEMENT.md)
- Catálogo verificado de capacidades y tareas instaladas:
  [`../guides/CATALOGO_FUNCIONALIDADES_CRUZR_S2.md`](../guides/CATALOGO_FUNCIONALIDADES_CRUZR_S2.md)
- Arranque y recuperación específicos de v0.2.0:
  [`../guides/CRUZR_V020_BOOT_GUARD.md`](../guides/CRUZR_V020_BOOT_GUARD.md)
- Preguntas y estado de soporte con DSA:
  [`../support/UBTECH_SUPPORT_TRACKER.md`](../support/UBTECH_SUPPORT_TRACKER.md)
- Informe de actualización base:
  [`../../upgrade.txt`](../../upgrade.txt)
- Resumen enviable de la actualización:
  [`../../upgrade_summary.txt`](../../upgrade_summary.txt)
- Regla udev PICO:
  [`../../config/udev/51-pico-ubt.rules`](../../config/udev/51-pico-ubt.rules)

El SOP PDF suministrado se conserva localmente dentro de `utats/` y está
ignorado por Git debido a su tamaño/origen externo.

## 17. Registro de cambios y pruebas futuras

Añadir cada sesión al principio de esta tabla. No borrar resultados fallidos:
son parte de la evidencia.

| Fecha/hora | Cambio o prueba | Resultado | Evidencia | Próxima decisión |
|---|---|---|---|---|
| 2026-08-28 09:48 PC/Motion | primer `--prepare-full` real abortado y bug local corregido | el preflight confirmó paros 0/0, cargador desconectado, articulaciones inmóviles y tarea clamp, pero el flujo abortó antes de restaurar el YAML: `BACKEND_LOG=…` intentó reasignar una constante shell de sólo lectura y Python no recibió la ruta. Se sustituyó el nombre de entorno por `BACKEND_LOG_PATH`. El parser real de sólo lectura reconstruyó `operation_type=1` y el check posterior demostró perfil aún arms-only `4e8d79a4…`, `clamp/0/0`; sin cambio parcial, recarga, START ni movimiento | salida del operador; diff del instalador; `bash -n`; `git diff --check`; `PASSIVE_OPERATION_TYPE=1`; `--check-arms-only` | volver a ejecutar `probar_pico_full.sh --prepare-full`; no recargar TeleopMode hasta que termine con `FULL_BODY_CONFIG_RESTORED=1` y exista una confirmación física nueva |
| 2026-08-28 PC/repositorio | lanzador separado de teleoperación full-body | se creó `probar_pico_full.sh` sin modificar `probar_pico.sh`. El nuevo flujo distingue preparación, recarga y movimiento; exige YAML vendor `5f08b30c…`, tarea viva `clamp/waist=1/leg=2`, Wi-Fi sin Ethernet sujeto, preflight/neutralidad/Y oficiales y STOP. Vigila en vivo el log Motion y aborta ante IK, fuerza o EtherCAT; los clicks que conmutan protección quedan prohibidos. El comprobador de STOP del gestor de perfil dejó de abrir WebSocket y reconstruye estado pasivamente para evitar la carrera auto-START 4.7.0. El check full real rechazó de forma esperada el hash arms-only activo y el check original confirmó `clamp/0/0`; no se restauró YAML, no se recargó TeleopMode, no hubo START ni movimiento | diff de tres scripts; `bash -n`; `git diff --check`; ayudas; rechazo no-TTY; checks reales de perfil; `probar_pico.sh` sin diff. `shellcheck` no está instalado | si se decide probar: ejecutar primero `probar_pico_full.sh --prepare-full`; después, con confirmación física nueva, recargar `teleop→auto_task→teleop`, ejecutar `--check` y sólo entonces `--teleoperate`. Restaurar arms-only y recargar al terminar |
| 2026-08-27 10:43–10:49 PC / 16:43–16:49 robot | arranque controlado después del trip FT | chasis, `KEY1` y arranque trasero se activaron con paro accionado; Control Center quedó en `WaitEStopRelease`. Tras liberar con robot estable no hubo movimiento inesperado. La consulta de estado a Docker activó `docker.service` por socket; no envió movimiento. Motion cargó ambos contenedores, readiness x86 3/3 y cámaras 2/2; self-check global `passed=true`, `StartMotion` exitoso y estado final `AutoTaskMode`. El check de ciclo aprobó actuadores Operation Enabled, gates de error/velocidad/delta, paros 0/0, cargador fuera, baterías suficientes y action server. El check de recuperación bloqueó sólo la clasificación de postura. Boot guard terminó `unexpected_control_state_unknown`, `RECOVERY_ELIGIBLE=0`, sin reiniciar ni mover | confirmaciones físicas; ping/SSH; systemd/Docker; logs Motion/Control Center; journal boot guard; ambos checks versionados | infraestructura recuperada sin movimiento. No ejecutar home por clasificación `unknown`; no teleoperar hasta cambiar a `teleop`, demostrar de nuevo `clamp,waist=0,leg=0`, postura/zona y preflight fresco. Revisar el parser del boot guard para `AutoTaskMode` antes de confiar en su estado visual |
| 2026-08-27 10:25–10:40 PC / 16:25–16:40 robot | diagnosticar robot inmóvil después de tomar una caja y completar apagado | el cliente oficial mantuvo enable y recibió 5.931 muestras de cada mando y 5.931 poses a 90 Hz; no hubo segundo Y, pérdida XR, watchdog ni error del script antes del `Ctrl+C`. A las 16:25:59 Motion midió `Force-X=-305,6…-307,0 N` en FT izquierda, superó el umbral `[120,120,120] N`, registró `Excessive force` y abortó la tarea. Después aparecieron servo 5003 `0x1001/0x2007`, saltos de consigna en ambos hombros y EtherCAT SAFEOP ERROR. Ambos checks versionados terminaron `exit 25`. El operador confirmó caja retirada y robot estable y autorizó apagado completo. `/emb/pm_shutdown` respondió `success=True`; Control Center transitó `TeleopMode→WaitShutdownReady→Shutdown→Term`. Motion/Vision dejaron de responder; tras confirmar pantalla y luces apagadas, el operador pulsó `KEY1` y luego apagó el chasis. Indicador verde apagado, robot estable | salida adjunta; logs PC; Motion `robot_app`, `rosa_control_node`, `ecmaster`; `docker inspect`; checks; respuesta ShutDown; log persistente Control Center; red; confirmaciones físicas | robot completamente apagado. Antes de encender, confirmar paro, abrazaderas, zona, cargador y persona; después descubrir todo desde cero y exigir action server, controladores, errores cero, Operation Enabled, velocidades cero y posición/consigna coincidentes. No home/teleop antes de esos gates |
| 2026-08-27 10:12–10:17 PC/PICO | diagnosticar `operation_type=2` previo y eliminar carrera de auto-START | dos conexiones locales de lectura coincidieron con el ciclo `Broadcasting publisher states`: a las 10:12:28.614 y 10:12:48.983 el backend registró `device detected online, starting remote operation` y `Pico publisher start` sin recibir `collect operation_type=2`. Es comportamiento/race de 4.7.0, no otro cliente persistente: cada socket se cerró en ~30 ms y no había UI ni `pico_control`. El segundo fue detectado por CHECK 7/7; cleanup envió STOP y el último `Pico publisher stop` fue 10:12:54.828. Se añadió `backend_passive_state_json`, que reconstruye `vr_status` desde la última transición y operación desde el último start/stop posterior al arranque vigente de systemd. `wait_for_pico_tracking_ready`, CHECK 7/7 y cleanup final ya no abren WebSocket; este queda sólo para START oficial autorizado o STOP de emergencia. `--check` real 10:17 terminó con `CLIENT_CONNECTIONS_DELTA=0` y `PUBLISHER_STARTS_DELTA=0`; bloqueó porque PICO había pasado a `vr_status=0` a las 10:15:26. `bash -n`, shellcheck y `git diff --check` aprobaron; no hubo movimiento | log backend con conexiones/broadcasts/start/stop; contadores antes/después de `--check`; procesos, sockets, validaciones estáticas | reactivar Working y ejecutar primero `PICO_TELEOP_CAMERA=off ./scripts/teleoperation/probar_pico.sh --check`. Debe mostrar `BACKEND_STATE_SOURCE=passive-log-no-websocket`; sólo después, con estado físico fresco, repetir `--teleoperate` |
| 2026-08-27 10:06–10:07 PC/PICO/Motion | primer intento de brazo izquierdo tras habilitar bimanual | arms-only `4e8d79a4…` y tarea viva `hand=clamp,waist=0,leg=0`; preflight: paros 0/0, baterías 56,5/67,7 %, cargador fuera y joints inmóviles. La primera pulsación Y apareció como `Left.b_button=true` 10:07:06.046–.324 y produjo `enable=1` a .050. El grip izquierdo ya estaba parcialmente apretado durante esa pulsación y luego llegó a `squeeze=1.0`. Al primer intento de movimiento, XR publicó un segundo intervalo independiente `b_button=true` desde 10:07:12.312 y el callback cambió a `enable=0` a .317; el derecho estuvo neutro. El monitor solicitó STOP, que quedó confirmado, sin fallos IK y con velocidad articular final cero. No es un fallo del brazo ni del modo bimanual: el protocolo recibió un segundo Y. No se cambió software ni se envió otra orden | salida adjunta del operador; `/opt/ubt/ubt_controller/logs/ubt_controller.log` (estados izquierdo/derecho y callbacks); bloque Motion de la sesión; estado final de joints | próxima prueba: ambos grips neutros hasta `ENABLE_OFICIAL_CONFIRMADO=1`; después usar sólo el grip lateral manteniendo el pulgar lejos de Y. No ignorar posteriores Y mientras siga siendo una vía de STOP; cualquier remapeo exige antes elegir y validar otra parada en el visor |
| 2026-08-27 después de 09:59 PC | propietario confirma torso quieto y habilita control bimanual | la sesión arms-only previa tuvo cero fallos IK y el solapamiento que disparó STOP duró sólo ~45 ms. Por autorización explícita, `--teleoperate` acepta por defecto uno o ambos grips/brazos cuando el gate vuelve a demostrar `clamp,waist=0,leg=0`. Se eliminó únicamente el STOP por solapamiento: permanecen preflight, neutralidad, Y, enlaces, tracking, cámara opcional, watchdog, STOP final/Ctrl+C y límites/collision del robot. El script registra `BIMANUAL_GRIPS_ACTIVE=1/0`; `PICO_ALLOW_BIMANUAL=0` restaura el comportamiento estricto. Ayuda, valor inválido, sintaxis y diff validados; no hubo START ni movimiento durante el cambio | confirmación física del operador, logs de la sesión anterior, diff de scripts, `bash -n`, ayuda y rechazo de variable inválida | próxima prueba con confirmación física fresca: recorridos pequeños y sincronizados de ambos brazos; soltar inmediatamente ante resistencia, retardo o cualquier movimiento del torso |
| 2026-08-27 09:58–09:59 PC/PICO/Motion | primer START con arms-only; guard bimanual | preflight: paros 0/0, baterías 57,6/68,7 %, cargador fuera, joints inmóviles y tarea clamp PICO. Y habilitó y la ventana permaneció activa 29 s. El gate local vio ambos grips altos únicamente de 09:59:26.872 a .917 (~45 ms; cinco frames derechos) y envió STOP. Motion conservó `hand=clamp,waist=0,leg=0`, registró cero fallos `CalcS2Right/Left…failed`; dos líneas `ik_restart_time_` fueron contadores de estado, no errores. Estado final `operation_type=1`, UI/cámara detenidas y velocidad máxima articular 0. No hay evidencia de que el vendor limite la teleoperación a un brazo: el rechazo de cualquier solapamiento es una política local añadida tras el incidente anterior | salida del operador, log backend, bloque Motion 15:58–15:59, hash/modos y `/mc/joint_states` final | preguntar al operador si el torso permaneció quieto. Si se autoriza bimanual, sustituir el rechazo instantáneo por una prueba escalonada y un umbral sostenido; no eliminar protección sin esa decisión |
| 2026-08-27 09:50–09:54 PC/Motion/Vision | recargar y demostrar el perfil arms-only | con confirmación física fresca, `--check-reload-ready` verificó paros 0/0, baterías 58,5/69,5 %, cargador fuera, `HW_TYPE=cruzr_s2_v1`, tarea PICO e inmovilidad. Control Center informó modo `teleop`; se invocó su mismo RPC `cc.api.work_mode.switch` hacia `auto_task`, se confirmó cero acciones y velocidad articular máxima 0, y luego se volvió a `teleop`. Motion recargó el hash `4e8d79a4…` y el último bloque demuestra `hand=clamp,waist=0,leg=0`. El preflight final repitió seguridad e inmovilidad con baterías 58,0/69,0 %. Backend final `vr_status=0`, `operation_type=1`, UI inactiva y sin `pico_control`; no hubo START ni movimiento | confirmación del operador, RPC `status.get`/`work_mode.switch`, joint states/acción, ambos preflights, `--check-arms-only`, hashes y estado WebSocket final | reactivar Head + Controllers / Working; ejecutar `--check` y luego una prueba corta de un solo brazo. No usar ambos grips ni extender alcance; STOP ante cualquier movimiento de torso |
| 2026-08-27 09:36–09:45 PC/Motion | causa del movimiento de torso aislada y overlay arms-only instalado | Motion demostró que ejecutó `teleoperation/cruzr_clamp_pico_teleoperation`, `Hand type: clamp`, pero con `Waist tele mode: 1`, `Leg tele mode: 2` y CoreMode 7 de cuerpo completo. Los perfiles PICO Cruzr inspeccionados comparten 1/2, mientras perfiles exoesqueleto admiten 0/0. La sesión problemática mantuvo ambos grips altos casi continuamente y produjo fallos IK repetidos (`CalcS2Right… failed` 1106; izquierda 316 en los logs revisados), por lo que cintura/elevador compensaron objetivos bimanuales fuera de alcance. La etiqueta PC `gripper` queda como discrepancia pendiente, no como causa demostrada. Con PC en STOP se respaldó el YAML vendor (`5f08b30c…`) e instaló un overlay que cambia sólo waist/leg a 0 (`4e8d79a4…`), sin reinicio, modo ni movimiento. La acción viva aún reporta clamp/1/2. `--teleoperate` exige ahora hash + clamp/0/0 antes de START y envía STOP si ambos grips se aprietan; `--check-arms-only` rechazó correctamente el estado vivo | YAMLs Motion, bloques de arranque y fallos IK de `robot_app`, estados de grips del backend, hashes, estado WS STOP, instalador `--check`, `bash -n`, `git diff --check` | con estado físico fresco y persona al paro, salir/reentrar en TeleopMode para recargar; ejecutar sólo `--check-arms-only`. No mover hasta ver `ARMS_ONLY_LOADED=hand:clamp,waist:0,leg:0`; después prueba corta de un solo brazo |
| 2026-08-27 09:25–09:33 PC/PICO/Motion | oscilación grande del torso durante teleoperación oficial y regresión ADB tras retirar USB | `pico_control` envió `arm_type=clamp`, pero el backend 4.7.0 registró `Arm type is: gripper` a las 09:25:51. Ambos grips estuvieron activos simultáneamente desde 09:25:55.992 hasta 09:26:33.725; el operador observó movimiento pronunciado adelante/atrás del torso, ausente en sesiones anteriores. STOP quedó confirmado a las 09:26:34 con `operation_type=1` y `enable=0`; UI inactiva y sin proceso `pico_control`. La causa se resolvió en la entrada posterior 09:36–09:45: Motion sí usó clamp, pero con cintura/elevador activos y fallos IK bajo mando bimanual. Separadamente, ADB TCP 5555 funcionó y verificó el serial mientras el USB estaba conectado, pero el puerto cerró al retirar el cable. Se añadió un fallback limitado a cámara `off`: exige peer XR 63901, serial esperado en el backend y después `vr_status=1`; no omite identidad ni tracking. El `--check` real avanzó hasta 7/7 y bloqueó por `vr_status=0`, sin START | log `/opt/ubt/ubt_controller/logs/ubt_controller.log`, `rtm_pybind.log`, procesos, sockets 63901, prueba TCP 5555, salida del operador, `bash -n`, `git diff --check` y preflight real sin START | **SUPERADO POR EL DIAGNÓSTICO POSTERIOR:** recargar y demostrar arms-only antes de otra prueba |
| 2026-08-27 14:11–15:01 PC/Motion/Vision | recuperación desde teleoperación con caja prescindible | la recuperación normal bloqueó `unknown`; 4003 quedó en FAULT `0x1001/0x0238`. Una tarea temporal de brazo derecho 50 mm/6 s terminó `MoveToGoalFailed/status=6` sin mover, pero dejó consignas latentes de 0,0166–0,1043 rad. El preflight bloqueó antes de llamar al rearmado 4003 y se amplió para rechazar también `abs(cmd_pos-position)>0,01`. El operador apagó completamente, retiró la caja y usó `KEY1`; los brazos descendieron sin trayectoria. En el siguiente arranque el boot guard leyó seguridad `1,0,0` y acabó `failed` por `CONTROL_STATE=unknown`. Tras liberar el paro, Motion quedó sano: servidor de acción 1, controladores de manipulación/FT/IMU `running`, cargador `conn_status=2`/0 A, todos los ejes sin error y `status=0x1237`, velocidades cero y posición/consigna dentro de ±0,003 rad de cero. **Home articular ya alcanzado; no se envió home ni se llamó a rearmado** | confirmaciones físicas; resultados de acción; logs `robot_app`/`rosa_control_node`/`ecmaster` y boot guard; `/mc/actuator_state`; `ListControllers`; `action info`; servicio de cargador; `bash -n`; `git diff --check` | no usar `KEY1` como recuperación. Mantener el robot inmóvil; revalidar Control Center/boot guard y preflight completo desde este home antes de otra teleoperación |
| 2026-08-26 13:49 PC | ampliar ventana oficial de brazos | por orden del propietario, `PICO_OFFICIAL_TELEOP_SECONDS` pasa de 120 a 300 s por defecto; se conserva rango 120–300, watchdog vendor sin modificar y STOP por fin, fallo o Ctrl+C. No se inició teleoperación durante el cambio | diff de scripts/docs, `bash -n`, ayuda y `git diff --check` | usar el mismo comando `--teleoperate`; confirmar físicamente zona/postura antes de cada ventana |
| 2026-08-26 13:47–13:49 PC/PICO | retirar USB y migrar control/ADB a Wi-Fi Cruzr | antes de desconectar se confirmó STOP y se habilitó ADB TCP. Tras retirar USB, ADB quedó `192.168.42.212:5555`; se reinició sólo XRoboToolkit, el operador reactivó Head + Controllers / Working y Unity registró destino `192.168.42.215:63901`. Socket directo establecido `.212→.215`, `vr_status=1` y preflight 7/7; Motion/Vision por Ethernet, Internet por DSA. El socket `.51` previo quedó temporalmente obsoleto en kernel pero no fue el seleccionado por el preflight. Sin START ni movimiento durante la migración | ADB/serial/IP, `ss`, logcat Unity, rutas y salida 7/7 | ejecutar `PICO_TELEOP_CAMERA=off ./scripts/teleoperation/probar_pico.sh --teleoperate` sólo con confirmación física fresca; vigilar latencia/pérdida Wi-Fi |
| 2026-08-26 13:35 PC/PICO/Vision | corregir espera de cámara en el nuevo lanzador | Vision creó el stream SRS y heartbeat, pero el relay apuntaba a la concesión histórica `.42.211`; el PICO actual era `.42.212` y el listener 12345 no podía alcanzarse. La prueba se canceló antes de START. Se sustituyó la IP fija por descubrimiento de `wlan0` mediante serial ADB, con `usb0` como fallback y override explícito; el padre pasa el destino descubierto al relay. `--check` validó `.42.212` por Wi-Fi Cruzr, sintaxis/compilación/diff correctos y cero procesos residuales | salida del operador, ADB `wlan0`, ruta kernel, procesos, `bash -n`, `py_compile`, `git diff --check`, `cruzr_pico_camera.sh --check` | reactivar Head + Controllers / Working; ejecutar `probar_pico.sh --teleoperate`; al aparecer la espera abrir Camera → Request PC camera data y comprobar primer keyframe |
| 2026-08-26 13:18–13:33 PC/PICO/Motion | validar protocolo oficial 4.7.0 y crear lanzador físico reproducible | enlace híbrido pasó 7/7 y preflight Motion mostró paros 0/0, baterías 69–76 %, cargador fuera y joints inmóviles. `pico_control --arm_type clamp` abrió P2P; Y izquierdo produjo `Left.b_button=true` y callback `enable=1`; grip derecho llegó a 1.0. El cliente confirmó STOP/operation_type=1. El rearme visto después lo causó el `wscat --wait 1` diagnóstico mantenido abierto, patrón retirado; STOP canónico final quedó estable. El backend registró `gripper`, aceptado por el propietario sólo para mover brazos, no efector. Añadido `probar_pico.sh --teleoperate` con cámara, preflight, neutralidad, Y, 120 s, monitor y STOP; sintaxis/diff, límites y cancelación previa validados sin nuevo START. Estado final STOP, inmóvil; luego el PICO volvió a `vr_status=0` | logs `ubt_controller`/`rtm_pybind`, salida `pico_control`, TCP, preflight Motion, `bash -n`, `git diff --check`, pruebas no-TTY/duración y cancelación | activar de nuevo Head + Controllers / Send data / Working y ejecutar únicamente `./scripts/teleoperation/probar_pico.sh --teleoperate`; confirmar si el primer grip movió físicamente el brazo |
| 2026-08-26 11:13–11:15 PC/red | sustituir cable y restaurar Ethernet recomendada por UBTECH | el cable nuevo negoció 1000 Mb/s full con autonegociación. Se sustituyó en `eno1` el perfil ajeno `netplan-eno1`/`.250.200` por el perfil persistente `cruzr-s2`/`.11.250`, never-default, y se fijó autonegociación explícita. Motion `.2` respondió en 0,236–0,382 ms y Vision `.3` en 0,364–0,912 ms, 0 % pérdida; ambas rutas usan `eno1`. Internet sigue por `wlo1`/DSA y Wi-Fi Cruzr permanece activa para PICO/fallback. `--check` aceptó el enlace y sólo falló en CHECK 5/7 por ausencia del stream PICO 63901. No hubo START ni movimiento | `ethtool`, sysfs carrier, `nmcli`, IP/rutas, ping forzado, ruta Internet y preflight 4.7.0 | ponerse el PICO, activar Head + Controllers / Send data / Working y repetir sólo `--check`; no tocar todavía modos físicos |
| 2026-08-26 10:31–10:50 PC/PICO/red | migración completa 5.3.0 parcheado → 4.7.0 oficial solicitada por UBTECH | backup íntegro sin logs vivos `c085fc4b…`; DEB 4.7.0 `4f2b728b…`; servicio enmascarado durante purge/install y dejado parado hasta verificar. Binario instalado coincide con vendor `e88b83b7…`; drop-ins `arm=clamp`, locale y lifecycle presentes; backend luego arrancado sin UI ni START. WebSocket final `vr_status=0`, `operation_type=1` y sin campo `enable_control`. Scripts adaptados a versión/hash 4.7.0 y enlace Ethernet/Wi-Fi real; cualquier modo físico solicita STOP y se bloquea antes de START. `--check` alcanza 5/7 y falla sólo porque PICO no abre TCP 63901. El visor estaba `Asleep`; wake y relaunch ADB dejaron la app activa pero no sustituyen ponérselo/activar Working. Ethernet `eno1`/`.11.250` negoció 10 Mb/s full pero ARP `.2/.3` falló tras bounce; perfil inactivo, Wi-Fi Cruzr funciona y DSA conserva default Internet. No hubo movimiento | `dpkg-query`, `dpkg -V`, hashes DEB/binarios/tar, systemd/drop-ins/listeners, WS 8082, ADB/power/pid PICO, `ss`, `ip`, `nmcli`, `ethtool`, ARP/ping forzado, `bash -n`, ayudas y prueba de bloqueo físico | ponerse el PICO y activar Head + Controllers / Send data / Working; ejecutar sólo `probar_pico.sh --check`. Después observar sin START el Y/enable oficial y resolver `enable_foot_switch=1`; no habilitar movimiento hasta adaptar y verificar el gate. Reparar/cambiar cable/puerto Ethernet antes de una captura precisa. Exportar y auditar un episodio piloto para resolver la contradicción `只支持遥操作` frente a la afirmación verbal de UBTECH |
| 2026-08-25 13:23–13:39 PC/Vision | integrar cámara principal del robot en XRoboToolkit durante teleoperación | el APK vendor abre `MediaDecoder` TCP 12345 y consume longitud big-endian + H.264 Annex-B. Se añadió un puente separado de control que inicia `/sensor/camera/stereo_left/image/raw` por `/streaming/start`, mantiene su heartbeat, demultiplexa SRS HTTP-FLV/AVCC sin re-encodear y limpia stream/publicadores al salir. Los gates físicos esperan primer keyframe (`PICO_CAMERA_LIVE_BEFORE_START=1`) antes del preflight Motion final y START. Fuente real: 1.367.328 bytes/64 frames/3 keyframes; receptor PICO simulado: 36 unidades y 2 keyframes con SPS/PPS; cierre final `SRS_STREAMS=0` y cero heartbeat residual. Robot permaneció STOP; no hubo START ni movimiento | APK/IL2CPP/Java vendor, `video_source.yml`, servicio `rosa_msgs/srv/VideoStream`, configuración SRS, logs `rtc_streaming`, captura FLV, parser puro Python, receptor TCP simulado, `bash -n`, `py_compile`, ayudas y `git diff --check` | encender/reconectar PICO `.42.211`, conservar `Head + Controllers`/`Working`, ejecutar primero `cruzr_pico_camera.sh --run --camera main`, activar `Camera` → `Request PC camera data` y confirmar visualmente imagen/latencia; sólo después repetir `probar_pico.sh --all-controls` con preflight físico fresco |
| 2026-08-25 12:59–13:04 PC/PICO | segundo intento integral abortado por reset del adaptador USB Wi-Fi | el gate fresco/neutro pasó, pero las 758 muestras conservaron trigger izquierdo 0 y no hubo flanco. A las 12:59:43 desapareció `0bda:b812`/`wlx80afcad40bd6`; reenumeró un segundo después y recuperó Cruzr a las 12:59:50. Nunca hubo `enable=1`; STOP final. USB autosuspend ya estaba desactivado, pero Wi-Fi powersave estaba activo y existían fallos LPS/tx report del firmware. Perfil `Cruzr S2-0669 1` fijado persistentemente a `powersave=disable`, reconectado con STOP y verificado `Power save: off`; DSA conservada. Los bucles armados abortan ahora inmediatamente ante pérdida de interfaz/carrier/IP/ruta o `vr_status`. `--check` 7/7 final OK, sin movimiento | log backend, journal kernel/NetworkManager, conteo de muestras, `lsusb`, `ethtool`, sysfs power, `iw`, `nmcli`, rutas, ADB/TCP/WS, `bash -n`, `git diff --check` | repetir una vez `--all-controls`; si reaparece un `USB disconnect`, cambiar adaptador/puerto o driver antes de otra teleoperación física |
| 2026-08-25 12:53–12:56 PC/PICO | falso positivo del gate de neutralidad | el intento abortó antes de START porque el parser reutilizó estados Left/Right de las 12:31:26 con ambos grips altos; no existían muestras de mando a las 12:53. Se corrigió el orden: START mantiene `enable_control=0`, el script exige muestras nuevas de ambos mandos posteriores a la línea inicial, valida neutralidad y sólo entonces permite el toque. Ausencia de muestras o entrada activa solicita STOP. Estado final confirmado `vr_status=1`, `operation_type=1`, `enable_control=0`, UI inactiva; sin movimiento | salida del operador, números de línea/timestamps del log backend, STOP WS, logs históricos que muestran Left/Right neutros inmediatamente después de `Arm type is: clamp`, `bash -n` y `git diff --check` | repetir una sola vez `--all-controls`; esperar `CONTROLLER_INPUTS_FRESH=1` y `CONTROLLER_INPUTS_NEUTRAL=1` antes de `TOQUE AHORA` |
| 2026-08-25 12:27–12:44 PC/PICO | primer `--all-controls` llegó a enable pero abortó; corrección de gatillo por flanco | una sola pulsación cruda duró 0,567 s y el backend de nivel alternó `enable 0→1→0`; el script detectó la pérdida y envió STOP, sin trip de heartbeat. A las 12:31 se detectó otra sesión inesperadamente activa con ambos grips altos y se envió STOP inmediato. Se sustituyó el mapeo por pulso sólo en flanco ascendente, más gates de neutralidad y liberación; activo `5083e9f0…`, backup de nivel/300 s `40b440f4…`. A las 12:44 `--check` recuperó ADB/stream y pasó 7/7; final `vr_status=1`, `operation_type=1`, `enable_control=0`, UI inactiva; sin START ni movimiento durante la corrección | timestamps y estados del log backend, STOP WS, test aislado `[0,1,1,1,0,1]`, build Python 3.10 reproducible, hashes, `bash -n`, systemd, listeners y preflight 7/7 | repetir una sola vez `--all-controls` con preflight físico fresco; el operador aprieta y suelta una vez cuando aparezca TOQUE AHORA |
| 2026-08-25 12:20–12:25 PC/PICO/Motion/Vision | propietario ordena usar Wi-Fi del robot para todos los dispositivos concernientes al robot, salvo Internet | perfil `Cruzr S2-0669 1` conserva DHCP y recibe ruta persistente `192.168.11.0/24 via 192.168.42.2`, `ipv4.never-default=yes` e `ignore-auto-dns=yes`; toda `.11.0/24` y `.42.0/24` robot pasan por `wlx80afcad40bd6`; la única ruta por defecto/Internet sigue en `wlo1`/`DSA CORPORATE`. El lanzador PICO descubre ruta/IP, exige ese SSID y ya no requiere `eno1`; se migraron los dos scripts heredados que bloqueaban por Ethernet. `--check-motion-ready` pasó en 16 s con paros 0/0, baterías 64,8/66,1 %, cargador fuera, joints inmóviles y tarea PICO. Los checks generales alcanzaron Vision/topics y Motion por Wi-Fi; `install_wave_both_arms.sh --check` pasó. Sin START ni movimiento | NetworkManager persistente/runtime, rutas kernel, inventario IP versionado, ping/TCP Motion/Vision/Internet, ADB/63901, `--check` 7/7, `--check-motion-ready`, checks generales y `bash -n` | repetir `--all-controls` desde cero sólo con confirmación física fresca; conservar `DSA CORPORATE` como default y no reintroducir dependencia Ethernet |
| 2026-08-25 12:17–12:20 PC | primer intento de `--all-controls`, abortado antes de START | tras la confirmación, el preflight Motion agotó 35 s y no envió START. Diagnóstico: `eno1` perdió físicamente portadora e IP (`NO-CARRIER`, `carrier=0`); la ruta a `.2/.3` cayó por `DSA CORPORATE` y SSH/ICMP fallaron. Ambas Wi-Fi del PC y PICO permanecieron conectadas. El preflight revalida ahora carrier, IP, ruta, ping y TCP 22 inmediatamente antes de consultar paros; el mismo caso falla en menos de un segundo con causa explícita | salida del operador, `ip`, sysfs, NetworkManager, ping/TCP/SSH, `bash -n`, `--check-motion-ready`, `git diff --check`; backend seguía STOP | **SUPERADO:** el propietario eligió Wi-Fi Cruzr para todos los dispositivos del robot; no reconectar ni volver a exigir Ethernet |
| 2026-08-25 12:08–12:16 PC/PICO | propietario autoriza probar todos los comandos del headset por ≥2 min | añadido `probar_pico.sh --all-controls`: preflight completo, 60 s neutros, ventana activa predeterminada de 120 s y configurable 120–180 s, mapa de controles, avisos de retorno a modo en sitio/cierre de captura/restauración por pares, resumen de entradas y STOP automático; gatillo izquierdo permanece reservado a enable/Y; backend estaba desarmado; no se envió START ni hubo movimiento durante el cambio. Una caída transitoria dejó ADB offline y dos sockets XR; el backend pasó a `device missing`/`vr_status=0` pese a la pantalla Working. Reiniciar sólo XRoboToolkit y reseleccionar Head+Controllers/Send data recuperó `vr_status=1`; el `--check` final pasó con stream directo, clamp/300 s y backend desarmado | `bash -n`, compilación del parser, ayudas de ambos scripts, límites 119/181 rechazados, modo válido bloqueado sin TTY, `git diff --check`, `adb`, ARP, `nmap`, `nmcli`, logcat, journal, WS 8082 y `--check` 7/7 | ejecutar una sola vez y localmente `./scripts/teleoperation/probar_pico.sh --all-controls` tras confirmar de nuevo la zona física; verificar visualmente modo en sitio e inmovilidad antes de recuperación |
| 2026-08-25 11:46–11:53 PC/PICO | migración a WLAN local sin túnel XR | `wlo1` conservó `DSA CORPORATE`; `wlx80afcad40bd6` y PICO usaron `Cruzr S2-0669` (`.215`/`.211`); XR conectó directo a TCP 63901, reverse quedó vacío, `vr_status=1`, `operation_type=1`, `enable_control=0`; lanzador acepta ADB USB o Wi-Fi por serial físico; sin movimiento | NetworkManager/IP/ping bidireccional, log Unity, `ss`, WS 8082, reverse vacío, `bash -n`, `--check` completo | retirar USB; tras reinicio redescubrir DHCP y ADB TCP; conservar `DSA CORPORATE`; repetir sólo `--check` antes de cualquier gate físico |
| 2026-08-25 17:14–17:20 Motion | recuperación a home después de movimiento PICO | el STOP del PC dejó `operation_type=1`, `enable_control=0`, pero la tarea TeleopMode siguió activa; el operador seleccionó `auto_task` y home terminó; reportó paso casi rozando con abrazaderas bajas. Corrección local: `--home` usa ahora la tarea v0.2.0 `cruzr/open_arm_before_home` (SHA `ec2c187c…`), que abre primero ambos brazos y luego hace cero; el detector reconoce postura teleoperada y esta nueva tarea como home | WebSocket Control Center `workMode=teleop`, acción activa, logs Motion, XML/hash de fábrica, reporte del operador; `bash -n`, ayudas, `git diff --check` y `cruzr_blue_workbin_cycle.sh --check` sin movimiento | validar físicamente la secuencia nueva sólo desde una postura PICO mínima, abrazaderas vacías, envolvente libre y persona en el paro; no volver a usar `cruzr/home` directo tras teleoperación |
| 2026-08-25 10:50–10:52 PC/Motion | propietario autoriza teleoperación física real; lanzador de micromovimiento | `probar_pico.sh` sin argumentos selecciona brazo derecho; `--move-left-arm` el izquierdo; 60 s estables, grip exclusivo, 2–3 cm/5 s máximo, STOP al soltar/fallar; XR recuperado a `vr_status=1`; preflight Motion exacto OK (paros 0,0; batería 77,2/77,8 %; cargador fuera; joints inmóviles; task Cruzr/PICO); cancelación seca dejó STOP; no se envió START físico | scripts, `bash -n`, ayuda, no-TTY, cancelación TTY, WS 8082, ADB, ROS 2 y log Motion | ejecutar localmente primero brazo derecho sólo con confirmación física fresca; reportar postura/recorrido/alarmas antes de probar el izquierdo |
| 2026-08-25 10:38 PC / 16:37–16:38 Motion | primera ventana runtime con timeout 300 s | DataChannel abrió antes de enable; `enable=1` y `CoreMode 7` sostenidos ~46,1 s; protección y chequeos de fuerza de ambos brazos activos; cero movimiento con 4.530 muestras por mando y grips siempre `false/0.0`; tres pulsaciones finales alternaron `0→1→0`, el script envió STOP; final `operation_type=1`, `enable_control=0`, Motion `NotTele`; a las 10:43 `vr_status=0` | `ubt_controller.log`, `rtm_pybind.log`, `robot_app`, traza del lanzador y confirmación del operador | no repetir `probar_pico.sh` como prueba de movimiento; rearmar XR y completar primero el gate de 60 s con un solo toque; diseñar aparte una micromaniobra supervisada de un brazo usando grip y nuevo preflight físico |
| 2026-08-25 10:35 PC | observabilidad del lanzador | `--check` muestra 7 etapas con timestamp; timeouts de 5 s para ADB/systemd/journal/WS; `CRUZR_TELEOP_DEBUG=1` da línea/comando; fallo simulado explícito; estado final STOP y `vr_status=1` | salida normal, traza con serial inexistente, `bash -n`, `git diff --check`, WS 8082 | el operador puede repetir `--check`; no ejecutar gate hasta completar confirmación física |
| 2026-08-25 10:29 PC/PICO | recuperación de reconexión VR | causa: app dirigida a `127.0.0.1:63901`, reverse ausente y socket viejo; restaurado `adb reverse`, reiniciada sólo XRoboToolkit; TCP establecido, `vr_status=1`, `ControllerActive`; backend `operation_type=1`, `enable_control=0`, UI inactiva; `--check` completo OK | ADB, `sys.usb.config=mtp,adb`, `ss`, log Unity, WS 8082 y lanzador canónico | no pulsar gatillo ni ejecutar ventana hasta confirmar preflight físico actual y `遥操模式` |
| 2026-08-25 10:20 PC | timeout heartbeat 10→300 s autorizado por el propietario | parche reproducible instalado; sólo cambia el operando del comparador, conserva STOP; activo `40b440…`, backup 10 s `0f0d3414…`; backend/UI/XR detenidos, unidad `inactive/dead` y habilitada; sin runtime ni movimiento | validación bytecode Python 3.10, SHA-256, estado systemd, procesos y listeners | repetir preflight físico/lógico; arrancar sólo localmente; `probar_pico.sh` es ventana diagnóstica de 60 s y no valida heartbeat |
| 2026-08-25 durante inspección 10:13 PC | incidencia de inspección local | una heredoc mal formada ejecutó fugazmente el backup vendor fuera de su directorio; abortó antes de inicializar por ausencia de `pem/vr_key.pem`; no sustituyó archivos, no abrió listeners, no cambió el servicio y no hubo movimiento | excepción local `FileNotFoundError`, hashes y snapshot posterior de procesos/systemd | usar sólo lectura binaria mediante `Path.read_bytes`; ya corregido en la sesión |
| 2026-08-25 después del gate 09:53 | origen del heartbeat y opción de omitir watchdog | UI 4.1.0 revalidada sin emisor; `Publisher.callback` recibe el tipo `heartbeat` por el canal inverso RTM del robot; desactivar/puentear watchdog descartado | source maps de `app.asar`, bytecode instalado de `publisher.py` | pedir backend PC compatible o componente oficial si el robot debe permanecer inmutable |
| 2026-08-25 09:53 PC | primer gate con lanzador local y toque único | START 09:53:46.142; `enable=1` 09:53:49.845; watchdog 09:53:56.718 (`10,576 s` desde START, `6,873 s` desde enable); `enable=0` 09:53:57.224; final `operation_type=1`, `enable_control=0`, UI inactiva; sin movimiento físico y con voz del robot | salida del operador, `ubt_controller.log`, consulta WS y systemd | no repetir; resolver con proveedor el heartbeat de aplicación |
| 2026-08-25 después del gate 09:53 | corrección de aborto local | se observó que `Ctrl+C` durante la confirmación enviaba STOP pero el `read` podía continuar; handler cambiado a STOP + salida 130/143; sin prueba física durante el cambio | salida del operador, `bash -n`, prueba aislada del handler y `git diff --check` | conservar el aborto duro; no usar el gate hasta resolver heartbeat |
| 2026-08-25 después del gate 09:44 | lanzador local solicitado por el operador | añadido `scripts/teleoperation/probar_pico.sh`; briefing, orden local y progreso cada 5 s, ejecución delegada al gate canónico; sin prueba física | `bash -n`, bloqueo no-TTY y `git diff --check` | el operador lo ejecuta manualmente desde el terminal local; no coordinar el toque por chat |
| 2026-08-25 después del gate 09:44 | eliminación de latencia del chat en el procedimiento | añadido `--gate-local`: TTY obligatorio, señal local posterior al armado, monitor 60 s y STOP automático; sin ejecución física durante el cambio | `bash -n`, `--help`, `git diff --check` | ejecutar desde terminal local con dos personas; conservar el chat sólo para revisar logs |
| 2026-08-25 09:44 PC / 15:44 robot | segundo gate, gatillo mantenido | entrada cruda fija en `trigger_value=1.0`/`b_button=true`, pero `enable` alternó cada ~0,51 s por repetición del conmutador Y; STOP automático; movimiento físico pendiente de confirmación explícita del operador | log PC `ubt_controller.log`, estado final WS | confirmar resultado físico; corregir a un toque menor de 0,5 s; no repetir hasta validar script y preflight |
| 2026-08-25 09:39 PC / 15:39 robot | primer gate actual con PICO por ADB reverse | gatillo→`b_button=true`→`enable=1`→Motion `CoreMode 7`; las pulsaciones repetidas alternaron `enable`; STOP automático, sin movimiento físico; TTS de activación oído | log PC `ubt_controller.log`, log Motion `robot_app`, confirmación visual del operador | aislar semántica de Y antes del gate de 60 s |
| 2026-08-25 | migración de scripts locales al runtime v0.2.0 | sintaxis/XML/hashes y `--check` válidos; sin instalación ni movimiento; gate de cargador bloqueó como debía | scripts y hashes del robot | conservar cambios; desconectar cargador sólo antes de una prueba física autorizada |
| 2026-08-25 | inspección de la web viva del robot | el selector sólo ejecuta `work_mode.switch`; `/vr` sólo recibe cámara; no hay cliente PICO directo visible | assets servidos por `192.168.11.3` | pedir a DSA APK/módulo/procedimiento directo exacto |
| 2026-08-25 | recuperación tras teleoperación y separación de clientes | `cruzr/home` terminó `SUCCEED/status=4`; `JoystickMode` restaurado; stack PC detenido sin procesos/listeners | log de Motion, ROSA, systemd, `pgrep`, `ss` | nuevo preflight desde estado conocido; no arrancar dos clientes |
| 2026-08-25 | auditoría de v0.2.0 | `signal_server` y `rtm_receiver` activos; `MC_SCENE` vacío; `pico_control` ausente; nombres ROS/canal no renombrados | contenedores/env/procesos/búsqueda local | aclarar diferencias del SDK con DSA |
| 2026-08-24 12:28 | reinicio ordenado del stack PC y rearme del PICO | preflight completo aprobado: red, ADB, TCP 63901, tracking `vr_status=1`, backend 5.3.0 y `arm=clamp`; UI inactiva | lanzador local, systemd, WebSocket 8082 | obtener gate físico fresco y validar heartbeat durante 60 s |
| 2026-08-24 12:25 | selección manual del modo web exigido por DSA | selector superior muestra `遥操模式`; el PICO aún devuelve `vr_status=0` | captura web y preflight local | rearmar `Head + Controllers / Send data / Working` y repetir gate |
| 2026-08-24 12:08–12:15 | perfil PC `arm=clamp`, UI bajo demanda y preflight reproducible | red/ADB/TCP/backend válidos; tras reiniciar app falta rearmar tracking (`vr_status=0`) | systemd, WebSocket 8082, ADB, TCP 63901 | activar tracking y `遥操模式`; ejecutar gate único |
| 2026-08-24 12:13 | DSA responde al diagnóstico | exige cambiar la web del robot a `遥操模式` | chat de soporte | probar ese prerrequisito antes de atribuir fallo a build |
| 2026-08-24 11:04 | reinicio de `ubt-controller.service` con PICO conectado | XR detectado tras 21 s; servicio activo | systemd, ADB, TCP 63901 | no pulsar `Y`; resolver build |
| 2026-08-24 10:45–11:07 | pruebas repetidas de START/`Y` y diagnóstico WS | DataChannel abre; `enable=1` temporal; watchdog envía STOP | logs PC/robot | falta heartbeat app |
| 2026-08-24 | inspección de binarios cerrados | watchdog 10 s y tipo `heartbeat` confirmados; ping de señalización diferenciado | bytecode/bibliotecas locales | solicitar DAC beta.2 |
| 2026-08-21 | instalación stack PC/PICO | paquetes instalados; PICO Working | apt/dpkg/ADB | mejorar orden de arranque |
| 2026-08-21 | locale C + espera TCP 63901 + udev | poses legibles y discovery reproducible | diffs systemd/run.sh; regla udev | conservar y validar tras upgrade |

Plantilla para una nueva entrada:

```text
Fecha/hora:
Objetivo:
Estado físico y preflight:
Versiones/hashes:
Cambio exacto:
Comandos o UI utilizados:
Resultado esperado:
Resultado observado:
Logs/timestamps:
Movimiento físico ocurrido: sí/no
Rollback realizado:
Decisión y siguiente gate:
```

## 18. Criterio para declarar la teleoperación resuelta

No basta con que el brazo se mueva una vez. El problema se considerará resuelto
sólo cuando se cumpla todo lo siguiente:

- build exacta y matriz de versiones verificadas;
- PICO y PC reconectan de forma reproducible;
- heartbeat de aplicación estable;
- START/STOP funcionan desde una única UI;
- pérdida de PICO, PC o Ethernet provoca parada segura;
- no hay clientes diagnósticos ni bypasses activos;
- tarea Cruzr/abrazaderas correcta;
- primera prueba limitada sin movimientos inesperados;
- logs y timestamps permiten explicar cada transición;
- un episodio piloto se graba, detiene, exporta y audita;
- DSA confirma los parámetros de seguridad pendientes.

## 19. Relevo mínimo para una nueva sesión de Codex

No reconstruir el diagnóstico desde cero ni reinstalar paquetes. La nueva
sesión debe leer primero este archivo completo y respetar los cambios sin
commit que pueda mostrar `git status`.

### 19.1 Hechos que ya no deben volver a investigarse

- La web de `192.168.11.3` cambia el modo, pero no implementa el cliente PICO.
- `/vr` es recepción de vídeo, no teleoperación de entrada.
- `signal_server` y `rtm_receiver` existen y están activos en el robot.
- El camino PICO → PC → robot llegó hasta DataChannel y datos; falla el
  heartbeat de aplicación esperado por el PC.
- `Working` en PICO, `TeleopMode` en web y topics existentes son condiciones
  parciales, no autorización de movimiento.
- No se renombraron topics, colas ni canales de teleoperación. El perfil de
  carga redirigió temporalmente tres entradas del costmap y el último
  preflight las mostró restauradas (`CARGO_PERCEPTION_PROFILE=disabled`).
- El último estado de movimiento verificado es `home`; no asumir que el
  cargador o la conexión física siguen igual.
- El stack PC está activo para el flujo suministrado: XR y backend activos, UI
  inactiva, `vr_status=1`, `operation_type=1`, `enable_control=0`. No iniciar
  un cliente directo en paralelo.

### 19.2 Primer snapshot, sin movimiento

```bash
cd /home/lacuna/proyectos/Robots/Humanoide
git status --short

systemctl is-active ubt-controller.service || true
systemctl is-enabled ubt-controller.service || true
systemctl --user is-active ubt-remote-control.service || true
pgrep -af 'ubt_controller|RoboticsServiceProcess|ubt-remote-control' || true
ss -Hlntp | grep -E ':(8082|63901)\b' || true

ip -br -4 address
ping -c 2 192.168.11.2
ping -c 2 192.168.11.3
adb devices -l
```

Si se pretende probar PICO directo, el resultado esperado antes de empezar es
que no haya backend/UI/PC Service ni listeners 8082/63901. Si se pretende usar
el flujo suministrado con PC, arrancarlos mediante el preflight versionado y
usar una sola UI.

### 19.3 Próxima decisión técnica

La prioridad no es mover el robot, sino resolver una de estas rutas:

1. **Ruta soportada con PC:** obtener/confirmar DAC beta.2, origen del
   heartbeat y `pico_control`; superar el gate de 60 s.
2. **Ruta directa:** recibir de DSA el APK/módulo/procedimiento exacto y
   demostrar peer/datos/heartbeat sin movimiento según 12.4.

No cambiar `MC_SCENE`, no instalar un paquete DAC supuesto, no simular
heartbeat y no ejecutar teleoperación física hasta que una de esas rutas quede
demostrada.

### 19.4 Texto para iniciar un chat nuevo

```text
Lee completamente docs/teleoperation/CRUZR_S2_PICO_TELEOP_SOURCE_OF_TRUTH.md
antes de actuar. Es la fuente de verdad del Cruzr S2 real. Conserva el
worktree existente y no reinicies el diagnóstico. Empieza con el snapshot de
la sección 19.2, sin mover el robot, y continúa únicamente desde la decisión
pendiente de la sección 19.3.
```


### PICO-MOTION-FIRST-RECORD-20261014 — VERIFICADO archivo local, reproducción pendiente

14-10-2026 Europe/Madrid. Operador confirma record --help en contenedor Motion y realiza grabación con abrazaderas. El recorder agrega timestamp al nombre: prueba_pico_01_20261014_192429.motion (50bytes reportados, contenido no inspeccionado) y prueba_pico_01_20261014_192800.motion (5,2MB). El intento de docker cp usando basename sin timestamp falló por archivo inexistente. Operador copió el segundo al PC.

Revisión local sin robot ni reproducción: /home/lacuna/grabaciones_cruzr/prueba_pico_01_20261014_192800.motion, SHA2560191fb331c6f2ebc5be0cfb5f8d6c9a2369600e6a07b77dc14d3d990c0003af9. JSON robotUtars/sourceutars_teleop, grupos head(2),left_arm(7),right_arm(7); cada grupo8421 muestras, duración16,84s, tiempos crecientes y q finitos. Brazo izquierdo constante, derecho cambia y cabeza cambia; no es archivo sólo de brazo derecho. No incluye cintura/elevador/chasis/dedos en este archivo. q inicial brazos no cero (postura PICO, no HOME); final no retorna al mismo inicio. No inferir q como medido vs consigna sin contrato del recorder. Validación estructural no verifica límites/collision ni autoriza reproducción; movimientos y objeto durante toma reportados sólo por operador.

Evidencia resumen y hashes documentales: ../Humanoide-vla-evidence/20261014_PICO_MOTION_FIRST_RECORD/. Archivo grande conservado fuera de Git en ruta PC indicada. Cambios sólo documentación con before/after; no config, deploy, servicios, movimiento ni modo. Pendiente auditar trayectoria/entrada/salida y cabeza antes de cualquier player autorizado, con estado físico fresco. No commit/push.


### PICO-MOTION-REPLAY-20261014 — intento físico autorizado; reproducción FALLIDA

14-10-2026 Europe/Madrid. Usuario autoriza reproducir y confirma condiciones físicas, interrumpe preparación y luego autoriza continuar. Receta y resultado [PICO_MOTION_PRUEBA_01_20261014](PICO_MOTION_PRUEBA_01_20261014.md). Original motion conservado; editor vendor genera copia con posiciones idénticas y tiempos2x (33,68s), hash1e8d7ac8250708907e4c962c66a5c7a06fb34b6f7389059cc52f09ff561d65cb. SDK joint_order y joint_states por nombre eliminan falsa diferencia al comparar raw motores; preflight fresco máxdelta0,002876rad, reposo, actuadores habilitados sin fallos, paros0/0, cargador0, baterías28,6/36,8%, controladores activos y sin acción Motion activa. Modo últimoobservadojoystick, sin cambio por agente.

Una llamada player --robot utars --input copia_lenta --loop1 a11:52:51Z termina en1s con std::bad_any_cast. Wrapper rc0 pero stderr abortado: NO éxito. No retry, no HOME. Telemetría posterior velocidades0 y cambio máximo0,000095874rad; no certificación continua de parada ni trayectoria. Causa SDK concreta PENDIENTE. No parche del SDK ni reducción de gates. Evidencia, comandos, hashes/estado before-after documentales en ../Humanoide-vla-evidence/20261014_PICO_REPLAY_PRECHECK/. Reversión: borrar sólo derivada temporal y cambios documentales de ficha si se desea; original no alterado. No commit/push.


### PICO-PLAYER-LOOP-20261014 — VERIFICADO causa y corrección de invocación

14-10-2026 Europe/Madrid. Se confirma que bad_any_cast del único intento player fue causado por --loop1 añadido en comando del agente: parser guarda explícito como string y lo extrae int. Default1síint. Ocurre antes de rosa::init/cliente/archivo. Se corrige receta omitiendo --loop (una pasada por defecto). No cambia SDK vendor. Dos pruebas con interposer de diagnóstico que termina obligatoriamente ANTES de init: opción explícita reproduce aborto, omisión alcanza marcador rc86. Cero movimiento/cliente en diagnóstico. Compilación temporal eliminada. Fuente versionada scripts/teleoperation/pico_player_parser_probe.cpp, ELF pinned8744a30ecce20c414dcf67b60d9aa7ac486bab752d5eee3de08a7336d65ddf0d.

[Receta, trazabilidad y comandos corregidos](PICO_MOTION_PRUEBA_01_20261014.md). Evidencia ../Humanoide-vla-evidence/20261014_PICO_PLAYER_BAD_ANY_DIAG/; before/after documental y SHA256SUMS. Reproducción de trayectoria con comando corregido PENDIENTE; no retomar físicamente bajo esta petición de diagnóstico/corrección. No configuración persistente robot/PC ni alteración motion. No commit/push.


### PICO-XR-USB-20261014 — túnel configurado; flujo USB pendiente de interfaz PICO

14-10-2026 Europe/Madrid. Usuario solicita XR por USB. PICO físico PA94Y0MGKB070822G descubierto device usb1-4, XRoboToolkit1.1.1. Backend sistema ubt-controller activo, UI inactiva, puertos8082/63901 disponibles. STOPoperation_type1 comprobado por log pasivo sin abrir WebSocket (conexiónWS4.7.0 puede arrancar publisher). Antes reverse vacío; cambio autorizado sólo `adb -s PA94Y0MGKB070822G reverse tcp:63901 tcp:63901`, después UsbFfs mappingcorrecto. Sin start de teleop/robot ni cambio de red Motion/Vision.

Fuente/receta scripts/teleoperation/configure_pico_xr_usb.sh: --check pasivo, --configure mismo mapping con identidadUSB/STOP/listener, --remove elimina sólo puerto63901. Invocar con bash; script no ejecuta controlrobot. --help,--check,bash-n verificados. Túnel ADB transitorio; puede perderse al desconectar/reiniciar. PCserviceIP en gafas debe ser127.0.0.1. Solicitud al operador: introducirIP, conectar y Head+Controllers/Senddata sinY/START. En última consulta aún TCP directoWi-Fi42.211→42.215:63901; no confundir reverse existente con flujoUSB yaactivo. EstadoXRUSB/tracking pendiente hasta observarpeerloopback e identidadtracking; conservarWi-Firobot paraPC→Motion si noEthernet.

Reversión: --remove (con backendSTOP) y restaurar PCserviceIP de interfazPICO al valor real de Wi-Fi si se desea volver; no eliminarotrosreverse. No se cambia firmware/SDK/servicios ni restriccionescargador. Evidencia before/after reverse, estado, sockets, check y hashes: ../Humanoide-vla-evidence/20261014_PICO_XR_USB/. before/afterdocumentales y nuevo scriptPC. No commit/push.


Actualización PICO-XR-USB-20261014 — VERIFICADO transporte y tracking: operador confirma Connected/Working tras introducir127.0.0.1. Socket posterior sólo loopback127.0.0.1→127.0.0.1:63901 y mappingUsbFfs. Diagnóstico canónico PICO_TELEOP_CAMERA=off probar_pico.sh --check a15:32:31CEST pasa7/7 rc0: identidadPICO porADBUSB, trackingvr_status1, backend4.7vendorhashintacto, UIinactiva y STOP. PC→Motion/Vision descubierto Etherneteno1/IP192.168.11.250; no se cambió esa conexión por el agente. No START ni movimiento. Conservado sólo túnelADB63901; estado operativoUSB confirmado, permiso físico no inferido.


### PICO-RECORD-06-COPY-20261014 — VERIFICADO copia local

14-10-2026 Europe/Madrid. Usuario solicita traer prueba_pico_06_20261014_214758.motion al repo local. Archivo encontrado en RAÍZ del contenedor Motion walker-motion.manipulation_robot_app-1 (/prueba_pico_06_20261014_214758.motion), no /tmp/pico_grabaciones ni carpeta host. Copia por SSH/dockerexeccat a recordings/pico/prueba_pico_06_20261014_214758.motion,11403700bytes, SHA256a615d38f941b03f3b615408e981b4120d46bd40f3247c56234fc0825dd68537b idéntico al remoto. Original remoto intacto, destino nuevo sin sobrescribir. Inspector local pasa validación estructural; no replay ni orden de robot. .gitignore añade /recordings/pico/*.motion para conservar archivos grandes localmente sin incluir enGit. Respaldo antes, copia verificada, inspección y hashes en ../Humanoide-vla-evidence/20261014_PICO_RECORD_06_COPY/. Fuente reproducible: dockerexeccat de ruta original y comparaciónSHA256; scripts/teleoperation/inspect_pico_motion.py para inspección. Reversión: retirar sólo copia y línea nueva de ignore/notas si procede, preservando original remoto y cambios posteriores. No commit/push.


**15-10-2026 10:42 CEST — continuación PICO v4, pendiente conexión XR.**
Operador pide seguir. Chequeo PC con cámaraoff y Etherneteno1 se detiene enCHECK2:
ADB no muestra dispositivos y no se detecta peerXR activo en63901. El clienteADB
arranca automáticamente su servidor localtcp5037 (antes detenido); no se cambia
configuración persistente. configure_pico_xr_usb.sh --check confirma visor físico
PA94Y0MGKB070822G ausente porUSB. No se configura túnel ni se envía START, modo
robot, HOME o movimiento. Tarea TeleopMode v4 todavía sin cargar; robot permanece
en modo anterior. Se solicita al operador elecciónUSB/Wi-Fi y preparar visor.
Reanudación: establecer XR y tracking neutro, comprobar STOP y seguridad frescos,
cargar modo v4 sólo brazos y verificar0/0 antes de ensayo. Evidencia privada
20261015_PICO_V4_PROFILE/pico-connection-before-mode.json ycc-before-pico-mode.json.
ServidorADB transitorio; dejarlo activo permite continuar, sin autorizar control.


**15-10-2026 10:46 CEST — PICO-V4-PROFILE: USB reconectado; XR pendiente de interfaz.**
Operador eligeUSB. PICO PA94Y0MGKB070822G reconocido deviceusb1-3.
Reverse anterior vacío; con backendSTOP confirmado por log pasivo, receta
`bash scripts/teleoperation/configure_pico_xr_usb.sh --configure` instala sólo
`tcp:63901 tcp:63901`; --check posterior confirma túnel e identidad.
Check PC descubre XRoboToolkit cerrado. Se abre únicamente su actividad
com.xrobotoolkit.client/com.unity3d.player.UnityPlayerActivity mediante ADB;
rc0. No modifica APK/configuración persistente, no START ni modo/movimiento robot.
Se pide al operador IP127.0.0.1, conectar, Head+Controllers/Senddata, sinY/grips.
Connected/Working y tracking aún pendientes. Evidencia usb-before.json,
usb-configure.json,usb-after-check.json,xr-activity.json,xr-open-app.json en
20261015_PICO_V4_PROFILE privado. Rollback transporte: con backendSTOP,
`bash scripts/teleoperation/configure_pico_xr_usb.sh --remove` retira sólo63901;
volver a IPWi-Fi real en interfaz si se elige otro transporte. Túnel transitorio,
puede desaparecer al desconectar/reiniciar. No se cerró app ni se quitó túnel.


### 15-10-2026 — apagado completo y nuevo arranque supervisado (OBSERVADO)

El guard de CC con SPS completó Motion 3/3 y cámaras 2/2; CC alcanzó
`WaitEStopRelease`. Con brazos asegurados contra caída, manos vacías y paro
principal pulsado, se solicitó una única vez `/emb/pm_shutdown`
(`emb_task_msgs/srv/ShutDown`, deadline_sec=15, confirm_str=confirm-to-shutdown).
Respuesta `success=True`; evidencia privada `shutdown-logical-request.json` en
`../Humanoide-vla-evidence/20261015_PICO_V4_PROFILE/`. El operador confirmó
pantalla y luces superiores apagadas, después apagado completo de ambas partes,
indicador verde del chasis apagado y brazos estables. Recuperación fuera de HOME
con soportes; no se envió HOME ni se alteraron límites o protección de saltos.

El operador informa nuevo encendido en orden chasis → KEY1 → botón de encendido
y mantiene el paro principal pulsado. Consulta de lectura descubre de nuevo
Motion y Vision activos (`reboot-container-discovery.json`). Se comprueba
arranque sin liberar el paro ni activar PICO. HOME actual, eliminación de
consignas latentes y funcionamiento físico de PICO v4 siguen PENDIENTES.

Verificación posterior del nuevo arranque: gate Motion 3/3, cámaras 2/2 con
timestamps avanzando; HW_TYPE efectivo SPS tanto en app Motion como en CC.
CC nativo alcanza `WaitEStopRelease`, principal=1 y servos=0. No se libera paro
ni se envía movimiento. Avisos MQTT rc14 y consulta de versión embedded agotada
observados; no se atribuyen automáticamente a fallo de brazos. Evidencia:
`reboot-first-readiness.json`, `reboot-cc-profile.json`, `reboot-native-cc.json`.


### 15-10-2026 — HOME tras ciclo completo (VERIFICADO)

El operador informa liberación del paro principal y HOME normal. Lectura nueva
confirma StartMotion terminado con éxito y CC en AutoTaskMode. Telemetría:
{"axis_count": 20, "max_abs_position_rad": 0.002684466378799872, "max_cmd_position_delta_rad": 0.002684466378799983, "max_velocity": 0.0, "faults": []}. Las diferencias anteriores de ~1,57 rad ya no
aparecen en esta muestra. Evidencia privada reboot-home-verification.json y
reboot-home-summary.json en 20261015_PICO_V4_PROFILE. Sin órdenes nuevas del
agente. No demuestra todavía inicialización PICO v4 correcta. Selfcheck general
passed=true, con avisos individuales audio_loopback y señal Wi-Fi; MQTT rc14
persiste. No se alteró ni omitió ninguna comprobación. Próximo paso: comprobar
seguimiento USB y continuidad de inicialización v4 antes de activar teleop.


### PICO-V4-SSH-ALLOWLIST-20261015 — transporte de lista de hardware (15-10-2026)

Tras HOME, USB XR vuelve a enviar HEAD+CONTROLLERS (vr_status=1), enlace robot
Ethernet eno1 y backend STOP. Check v4 rechazó erróneamente HW_TYPE SPS: SSH
concatena argumentos remotos y separaba la lista con espacios en dos argumentos.
Se corrige sólo transporte de expected_hw_types a un token separado por comas y
se reconstruye la lista en remoto. Se conserva la misma lista permitida por
perfil: clamp sólo base; v4 base/SPS. Sin cambio de gates físicos o hardware.
Fuente PC scripts/teleoperation/cruzr_pico_teleop_pc.sh; prueba de regresión en
test_pico_motion_preflight_diagnostics.py simula reconstrucción SSH y rechazo
de hardware desconocido. 16 tests pasan y bash -n correcto. Backup externo
20261015_PICO_V4_PROFILE/before-ssh-hw-list-fix; reversión del fragmento desde
esa copia, sin reinstalar cambios ajenos del archivo. Activación próxima
ejecución del script; no requiere reiniciar robot/PC. Sin START ni cambio de
modo durante estas comprobaciones. Control de manos desde XR aún no habilitado.

Check real posterior: HW_TYPE SPS aceptado; siguiente gate rechaza correctamente
ACTIVE_TASK_ERROR=cruzr/home (rc26). Aún no se ha cargado tarea PICO v4.
Tracking USB vr_status=1 y STOP confirmados; no START ni cambio de modo.


### 15-10-2026 — tarea PICO v4 inicializada (VERIFICADO; sesión manual pendiente)

Con confirmación física actual: manos vacías, recorrido libre, soportes retirados,
cargador fuera, otros mandos detenidos y persona junto al paro. Lecturas nuevas
pre-v4-mode-safety.json: paros0/0, batería64,1/67,1%, cargador0, módulos sin
bloqueo. Cuerpo20D en reposo sinfaults/delta máximo0,002589rad y siete estados
v4 válidos por mano. Perfil v4 instalado con init_time12, init_resettrue,
anticolisióntrue, cintura0/elevador0, sin modificar parámetros de inicialización.

Cambio autorizado mediante cc.api.work_mode.switch workMode=teleop aceptado.
Ahora sí selecciona teleoperation/cruzr_v4_pico_teleoperation, Hand typev4,
waist0/leg0. Vigilancia de hardware durante inicialización no observa nuevos
'jump command', SAFEOP ERROR ni avisos de fuerza/fault del patrón vigilado.
Telemetría final:20D, velocidad0, sinerror_code y delta máximo0,00342212rad
(~0,20°); ambos brazos alcanzan consignas iniciales v4. Operador confirma ambos
brazos estables. Perfil cargado SHA01a5ca8acba16bbe136a3bdbcb4a593667d672f8ee9613b98631699fc429b582.
No demuestra aún respuesta a grips/gatillos ni ensayo de agarre.

Evidencia privada: v4-mode-switch-after-reboot.json, v4-init-app-log.json,
v4-init-hw-watch-0..7.json, v4-mode-status-after-init.json y
v4-init-actuator-check/summary.json. Estado vigente teleop, PC STOP, sinSTART.
No HOME adicional, reboot ni reset. Para salir, usar STOP oficial y transición
controlada; no apagar desde la postura PICO sin recuperación adecuada.

Durante check posterior tracking cae a vr_status0: USB reverse aún válido,
XRoboToolkit resumed, pero Android mWakefulness=Asleep. Operador despierta y
se coloca el visor; se repite check antes de START. No se deshabilita tracking,
watchdog o suspensión del dispositivo. No seleccionar seguimiento óptico Hands:
perfil actual Head+Controllers, cliente hand con enable_hand_pose0.


### PICO-XR-USB-20261015 — recuperación tras suspensión (OBSERVADO)

Tras reactivar Send data, check aún vr_status0. Captura privada
xr-current-screen.png confirma Head/Controller/Send seleccionados, Hands no,
PC127.0.0.1 yWorking; visorAwake yTCP/reverse activos. Journal del PC registra
`device missing` a11:26:41 Europe/Madrid; reconexión efectiva aún no demostrada.
No atribuir el bloqueo a una configuración incorrecta del operador ni afirmar
que Working equivale a seguimiento válido.

Se reinicia sólo app PICO com.xrobotoolkit.client mediante ADB force-stop y
am start de UnityPlayerActivity. Sin reinicio de PC/robot ni START, backendSTOP,
tarea v4 permanece cargada. Evidencia xr-app-restart-after-sleep.json; capturas
y logs privados fueraGit. Receta reproducible: confirmar backendSTOP con
configure_pico_xr_usb.sh --check, adb -s PA94Y0MGKB070822G shell am force-stop
com.xrobotoolkit.client; adb -s PA94Y0MGKB070822G shell am start -n
com.xrobotoolkit.client/com.unity3d.player.UnityPlayerActivity; reconectar
127.0.0.1 yactivar Head+Controllers/Send data; repetir probar_pico_v4.sh --check.
No se cambiaron ajustes persistentes de suspensión ni binarios. Reversión:
cerrar app si no se usa; no restaurar sesiones de control transitorias.
Resultado de recuperación PENDIENTE al registrar este punto.


### 15-10-2026 — XR recuperado y corrección de lector ROS (VERIFICADO)

Tras reinicio de app y reconexión del operador, vr_status1 comprobado. App con
Shared network ha activado redUSB: PICO192.168.224.184→PC192.168.224.6:63901,
ruta por enxdabcd609068b, sysfs usb1/1-3:1.0. PC→robot sigue eno1/.11.250.
No se cambió NetworkManager desde el agente; el reverse anterior queda
configurado pero el stream actual usa redUSB directa. No llamarlo Wi-Fi.

Preflight real pasa paros, baterías63,3/66,3%, cargador fuera, reposo, tarea
v4 activa, una acción. Lector de manos aborta por AMENT_TRACE_SETUP_FILES no
definida al source del setupROS bajo nounset. Se corrige únicamente ese source
en check_v4_hand_states de scripts/teleoperation/cruzr_pico_teleop_pc.sh:
carga con set -Eeo pipefail y restaura set -u inmediatamente después; sin
omitir lectura, nombres/velocidades/timestamps. Prueba de regresión con
variable opcional ausente, 17tests pasan y bash -n correcto. Backup previo en
before-v4-ros-setup-fix, misma evidencia externa. Activación próxima ejecución;
reversión selectiva del fragmento desde backup. Sin cambios robot/SDK.

Se abre lanzador oficial v4, ventana120s, mismo cliente vendor hand y
enable_hand_pose0, cámaraoff. Perfil cargado0/0 ytracking1 comprobados.
Confirmación textual basada en condiciones físicas que el operador acaba de
confirmar. Al registrar este punto está revalidando preflight antes de START;
resultado, enable y efectos físicos aún PENDIENTES. No se marca ensayo completo.

Ensayo11:33–11:34 Europe/Madrid: preflight completo, V4_HAND_STATES_OK,
START oficial arm_typehand/enable_hand_pose0 y mandos frescos/neutros. No se
observa Y/enable1 en15s; cliente solicita STOP y confirma operation_type1.
Sin habilitación física demostrada. Operador confirma estar preparado para
siguiente aviso; se reintenta una ventana idéntica, sin ampliar timeout.


### 15-10-2026 — primer control PICO v4 con respuesta física confirmada

Segundo intento oficial ~11:35 Europe/Madrid: preflight nuevo pasa, estados
v4 válidos, mandos frescos/neutros; START arm_typehand y Y/enable1 observados.
Ventana120s, sólo brazos/manos, cabeza según perfil, cintura/elevador0. El
operador confirma: «Sí, brazo y mano responden bien», siguiendo grip y apertura/
cierre con gatillo, ensayo en vacío. Consulta de logs durante sesión sin los
patrones de salto/Excessive force/SAFEOP/fault en alcance recogido; no equivale
a certificar cualquier trayectoria. Evidencias v4-physical-test-operator-report
y v4-session-live-log-check.json. Captura/dataset/replay con v4 NO ensayados.
Sesión aún activa al registrar; STOP final pendiente de verificación. No
modificaciones de parámetros de movimiento ni protecciones durante la prueba.


### 15-10-2026 11:37 Europe/Madrid — PICO v4 probado en vacío; STOP final verificado

Ventana oficial120s terminada con código0. Cliente envía operation_type1 y
confirma OFFICIAL_TELEOP_STOP_CONFIRMED1; UI detenida, sinnuevoHOME ni cambio
de modo. CC mantiene teleop, brazos en postura final PICO, NO declarar HOME.
Lectura final cuerpo20D: velocidad0, sinfaults, delta máximo0,00235399rad.
Manos: dos muestras avanzando por lado, siete nombres correctos, velocidades
≤0,02rad/s, V4_HAND_STATES_OK. Estado estable medido después de STOP.

Resultado: inicialización v4 correcta y operador confirma movimiento de brazo
porgrip y apertura/cierre de mano porgatillo. No se ensayó agarre de objeto,
seguimiento óptico de dedos, captura ni replayv4. Sin cambio de límites, fuerza,
watchdogs o anticolisión. Fuente de control PCvendorarmhand y perfil v4 0/0.
Se conserva baseline globalPCclamp: override del cliente hand comprobado ahora
en esta sesión. Evidence v4-session-final-actuators/summary/hands.json y
v4-official-session-backend.log (privados). Fuentes exactas respaldadas en
after-v4-teleop-verified-sources conSHA256SUMS.

Repetición con tarea v4 ya cargada y condiciones físicas comprobadas:
PICO_TELEOP_CAMERA=off CRUZR_IFACE=eno1 CRUZR_PC_IP=192.168.11.250
PICO_OFFICIAL_TELEOP_SECONDS=120 bash scripts/teleoperation/probar_pico_v4.sh
--teleoperate (una única línea). El script exige confirmación y gates de nuevo;
Y una vez sólo al aviso, sin grip/gatillo hasta enableconfirmado. Si tras
reinicio está auto_task/HOME, hace falta cargar tarea v4 de forma supervisada;
no sustituir automáticamente por clamp ni saltarse ACTIVE_TASK_ERROR.
Mantener visor despierto/puesto; tras sueño, Working solo no demuestra vr_status1.


### PICO-V4-COMPLETE-CAPTURE-20261015 — grabador pasivo complementario

15-10-2026 Europe/Madrid. Fuente nueva PC:
`scripts/teleoperation/record_pico_v4_complete.sh`; SHA256 dc6735d24ec3dba975f8e4f2d97f1c2773c1352e3c48120e39c65f4e9678fde8.
Motivo: record nativo sólo conserva posiciones mandadas, insuficientes para
cierre cur observado en toma01. Nuevo lanzador añade ROSbag con mensajes
completos de manos (órdenes/estados MC y EtherCAT), órdenes cabeza/brazos,
estado articular del cuerpo y estados medidos de manos. Mantener .motion nativo
en paralelo si se necesita formatoSDK. Bag incluye datos para estudiar modos/
esfuerzos; no es un player ni transforma automáticamente bag a.motion.

Descubrimiento actual: walker-ros.ros2-1 incluye ros2bag con sqlite3; topics
y tipos contrastados. --check predeterminado consulta herramientas y canales
manos, sin escribir ni iniciar captura. --record NOMBRE exige terminal, nombre
alfanumérico/_/-, usaSSH interactivo conocido hacia walker@192.168.11.2.
No SDKedit, parámetros del robot, START, cambio de modo o reproducción.
QoS best_effort/volatile keep_last2000 por topic, caché16MiB; suscripción
compatible con publishers BEST_EFFORT. QoS se escribe sólo para sesión nueva.

Archivos nuevos sesión: /tmp/pico_v4_capture_NOMBRE_UTC_PID en ROScontainer,
rosbag/sqlite+metadata yqos.yaml. TrasCtrl+C exporta a hostMotion
/home/walker/grabaciones_v4_completas/NOMBRE_UTC_PID y ejecuta baginfo. Rechaza
sobrescritura. No depende de mantener sólo /tmp: copiahost comprobada.
Reversión: conservar/exportar grabaciones, retirar selectivamente lanzador y
sus carpetas de prueba si se decide; no restaurar estado transitorio de control.
No servicio/autostart instalado ni configuración persistente de robot/PC cambiada.

VALIDACIÓN: bash-n y --help correctos; --check real pasa. --record ensayado
pasivamente, Ctrl+C limpia/cierra, copiahost ybaginfo terminan rc0. Prueba
8,4006s, 9190mensajes, sqlite8.175.616B, cuenta manos medidas832/830,
whole_joint_states4184, buscmd834/832, busstate840/838. No mensajes de
órdenesMC en esta captura en reposo; captura durante teleop aún PENDIENTE.
No afirmar que una simple creación de bag garantiza cobertura de toda demo:
revisar recuentos y rango de dedos en toma corta activa antes de reproducción.
Carpeta host /home/walker/grabaciones_v4_completas/
comprobacion_pasiva_20261015T100041Z_431556. SHA256 DB
a36c35802f2ae67cdc890b14e2ceaa3fdff5a82f4e7bde15bc33f046cded85a8.
Evidencia privada v4-complete-capture-tools.json y
v4-complete-capture-passive-proof.json con hashes yrecuentos.

Procedimiento para operador desde raíz repoPC:

```bash
bash scripts/teleoperation/record_pico_v4_complete.sh --record prueba_v4_02
```

Dejar abierto hasta Subscribed, mantener grabador.motion anterior en otra
terminal si se requiere. Iniciar teleop v4 por procedimiento ya comprobado y
hacer toma corta en vacío con condiciones físicas actuales. Ctrl+C sólo en
terminal de grabación guarda/copia; no detiene teleop. Revisar datos antes de
repetición. No ejecutar ros2bagplay sobre topics de mando directamente: el
reproductor/continuidad/modos de esfuerzo requieren adaptación y validación
propias. Reproducción bag completa y nueva toma activa PENDIENTES.
