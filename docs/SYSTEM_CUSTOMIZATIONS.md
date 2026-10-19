# Registro de adaptaciones del sistema Cruzr S2

### HOME-FAILED-20261016 — diagnóstico sin cambios de control

- **Fecha/zona/estado:** 16-10-2026 Europe/Madrid. HOME del operador abortado, OBSERVADO. Origen de discontinuidad y fallo de cabeza PENDIENTE; no recuperación ejecutada.
- **Verificado en registros:** antes del goal59860eee… hay avisos de salto >0,087rad y ambos motores de cabeza con error4099/0x1003. HOME v8 SHA256d9e9462792b41300d352604b53ea2a4890a9382e942321990708f6ded2e26ccb intacto; primeros ajustes1s fallan, errores máximos12,26° izquierda/28,64° derecha, cuerpo abortado. No se llega a bajada/cierre. No afirmar que más tiempo o tolerancia lo resolverían.
- **Estado posterior/límites:** cinco mensajes pasivos conservan fallos de cabeza y diferencias consigna/posición. Captura usable_capture=false por aviso ROSA no JSON; no certifica salud/reposo. Operador responde sin contacto/resistencia/objeto/movimiento inesperado; postura final PENDIENTE.
- **Cambios, destino y reversión:** sólo informe e índices del repositorio PC. No escrituras de robot/PC/PICO fuera de documentación, ni START/STOP/HOME/rearme/reinicio/modo/limitaciones modificadas por el agente. Reversión de ejecución no procede.
- **Evidencia/reanudación:** ../Humanoide-vla-evidence/20261016T105501Z_HOME_MOVE_TO_GOAL_FAILED_READONLY/; XML, logs app/HW anteriores/durante/posteriores, captura, findings, before/after y hashes. [Informe](incidents/2026-10-16_HOME_MOVE_TO_GOAL_FAILED.md). Preparar recuperación desde postura actual y resolver fallos/consignas pendientes antes de otra acción física; sin reintento automático.

### PICO-RIGHT-DIRECTION-20261016 — investigación sin cambios de sistema

- **Fecha/zona/estado:** 16-10-2026 Europe/Madrid. Operador comunica brazo derecho hacia fuera al mandar hacia dentro; OBSERVADO. Causa PENDIENTE; aclaración mano completa/codo solicitada sin pedir repetir movimiento.
- **Verificado:** backend STOP/tracking1, XR USB y robot Ethernet. YAML v4 mismo SHA01a5ca8…/limb_mode2, escala1 en ambos brazos y colisión activa. En fragmento de log Motion: 297 IK derecha fallidos, cero del mismo patrón izquierda; no es recuento completo. Los xyzrpy del error son objetivos, no poses físicas medidas. No prueban inversión de signo.
- **Cambios/destino/reversión:** sólo informe local e índices; ninguna escritura de robot/PC/PICO, START/STOP/HOME, reset, modo, calibración o parámetros. Reversión de ejecución no procede. No se sustituye el mapper ni se aplica negación de un eje.
- **Evidencia/reanudación:** ../Humanoide-vla-evidence/20261016T104612Z_PICO_RIGHT_ARM_DIRECTION_READONLY/; backup documental, perfil, log Motion acotado y fragment-summary.json, logs PC y fuentes before/after. [Informe](incidents/2026-10-16_PICO_BRAZO_DERECHO_DIRECCION.md). Aclarar mano/codo y comparar referencias/poses de forma pasiva u offline; no otra prueba física desde esta revisión.

### PICO-USB-RETURN-20261016 — restablecer XR USB tras prueba inalámbrica

- **Fecha/zona/estado:** 16-10-2026 Europe/Madrid. Mapping USB INSTALADO y VERIFICADO; tracking USB actual VERIFICADO mediante socket loopback/vr_status1 y check v4 rc0. Operador confirma Working por USB y reconecta Ethernet. Usuario solicita volver al cable y se conserva su selección de cámara off. Sin movimiento iniciado por el agente.
- **Destino/fuente:** PICO PA94Y0MGKB070822G transport7 y ADB PC; sólo reverse tcp63901→63901, inicialmente ausente. Fuente versionada scripts/teleoperation/configure_pico_xr_usb.sh, hash conservado en evidencia. --check, --configure y --check real con identidad física, listener XR y STOP pasivo verificados. No se crea forward de cámara ni ADB TCP.
- **Dependencias/activación:** USB autorizado y aplicación XRoboToolkit; operador debe cambiar PC service IP de .42.215 a127.0.0.1 y activar Head+Controllers/Send con visor puesto. Comprobar peer loopback con PICO_PC_IP127.0.0.1 y vr_status1 antes de afirmar transporte/seguimiento efectivos.
- **Hallazgo de red/resolución:** inicialmente Ethernet eno1 carrier0, sin dirección IPv4 y NM unavailable; ruta al robot por Wi-Fi wlx80afcad40bd6/.42.215 vía .42.2. Operador elige reconectar Ethernet; después carrier1 y ruta directa eno1/.11.250, verificadas. El agente no modifica NetworkManager, rutas, servicios, APK o perfil robot. No START/STOP/HOME/cambio de modo enviados.
- **Verificación final:** --check v4 completo, cámara off/PICO_PC_IP127.0.0.1/eno1/.11.250, rc0 y MOTION_READY_CHECK_OK1. STOP, tracking1, paros0/0, baterías69,7/73,1%, cargador fuera, velocidad articular cero; SPS y cruzr_v4_pico_teleoperation, manos avanzantes válidas y perfil sólo brazos cargado SHA01a5ca8…/waist0/leg0. No certifica una trayectoria futura ni sustituye confirmaciones físicas del próximo lanzador.
- **Backup/rollback/evidencia:** ../Humanoide-vla-evidence/20261016T102402Z_PICO_USB_RETURN/, documentos before, reverse vacío, consultas de carrier/ruta, configure/after-check y hash de receta. --remove bajo STOP sólo retira reverse63901; restaurar IP Wi-Fi de aplicación si se desea. Mapping transitorio, no servicio ni autoarranque instalado. Cámara sigue off.

### PICO-WIFI-MIGRATION-20261016 — seguimiento Wi-Fi y descarte de socket USB obsoleto

**Selección posterior del operador:** prueba sin cámara; confirma sesión cerrada
con STOP. No requiere USB temporal ni ADB, que quedan fuera de esta variante.
Check v4 posterior rechaza vr_status0; peer Wi-Fi y ruta Ethernet conservados.
Se solicita visor puesto y reactivar Head+Controllers/Send; receta exacta añadida
a PICO_WIFI_SIN_USB.md. Sin nuevos cambios de ejecución ni movimiento por el
agente. Evidencia no-camera-selection.json en la carpeta de esta ficha.

- **Fecha/zona/estado:** 16-10-2026 Europe/Madrid. Seguimiento por Wi-Fi VERIFICADO en primer check 7/7 a 12:04, vr_status1/STOP e identidad esperada. El operador confirma Connected/Working con PC service IP 192.168.42.215; PICO observado 192.168.42.211. PC → robot permanece por Ethernet eno1/.11.250. Sin ensayo físico iniciado por el agente.
- **Cambio/destino/fuente:** PC scripts/teleoperation/cruzr_pico_teleop_pc.sh, función discover_pico_stream; nuevo test_pico_stream_discovery.py. Se recorren todos los sockets XR, se exige IP local aún asignada y se respetan hints explícitos. El socket USB .224.6→.224.184 quedaba ESTAB tras desaparecer la interfaz. No se cierra la sesión ajena ni se altera el protocolo vendor, identidad, tracking o gate ADB de vídeo.
- **Aplicación/dependencias/verificación:** nueva ejecución del lanzador; Bash/ip/ss/awk/grep existentes. Doce pruebas offline, incluido socket USB obsoleto anterior al Wi-Fi y compatibilidad loopback, más bash -n correctos. Primer check real camera off valida XR; no certifica vídeo ni tarea física actual. ADB ausente y 5555 cerrado; check intentó reconexión Wi-Fi sin éxito, sin configurar dispositivo.
- **Estado de control posterior:** a 12:05 el segundo check rechaza operation_type2. Lectura detecta --teleoperate y pico_control de otra sesión; UI local inactiva. Se solicita STOP al operador antes de modificar transporte. No START/STOP/HOME/cambio de modo enviados por esta intervención. ADB TCP y prueba de cámara inalámbrica PENDIENTES. Relectura final: operation_type1 (STOP) y vr_status0; ADB aún ausente. STOP posterior ya comprobado, pendientes USB temporal y reactivar tracking.
- **Backup/evidencia/receta:** ../Humanoide-vla-evidence/20261016T100303Z_PICO_WIFI_MIGRATION/ con before de fuentes/docs, estado/red/pings, check posterior y procesos. [Receta sin USB](teleoperation/PICO_WIFI_SIN_USB.md). No cambio de perfiles NetworkManager, rutas, servicios/autoarranque o firmware.
- **Reversión/reanudación:** restauración selectiva de función desde before preservando cambios posteriores; volver a USB con receta existente bajo STOP. Reanudar desde verificación de STOP y eventual USB temporal para habilitar ADB Wi-Fi, sin omitir ADB cuando el lanzador solicita vídeo. Conservar los ajustes de baja latencia.

### PICO-VIDEO-LOW-LATENCY-20261016 — reducir retención de vídeo en PC y SRS

- **Fecha/zona/estado:** 16-10-2026 Europe/Madrid. INSTALADO en fuentes PC, CARGADO en SRS y VERIFICADO mediante pruebas locales/lectura de configuración y log de recarga. Operador confirma «Se ve y el retraso es mucho menor» en prueba real sólo vídeo; mejora OBSERVADA, milisegundos finales PENDIENTES de medir. Petición explícita del operador tras comunicar ~3 s de desfase.
- **Objetivo/fuentes:** PC `scripts/teleoperation/{pico_camera_sbs.py,pico_camera_relay.py,cruzr_pico_camera.sh}`; receta nueva `configure_pico_srs_latency.py`, pruebas test_pico_video_latency.py y extensión de test_pico_camera_sbs.py. [Aplicación, verificación y reversión](teleoperation/PICO_VIDEO_BAJA_LATENCIA.md).
- **Destino robot:** Vision 192.168.11.3 / walker-backend.srs-1 / /usr/local/srs/conf/rtmp2rtc.conf. Misma imagen SRS v5.0.213 e instancia 6c2ab0163814…; sin recreación. Se añaden TCP_NODELAY, min_latency, GOP cache off, cola de consumidor 1 s, merged write 20 ms y merged read off. Capa escribible del contenedor; reaplicar selectivamente después de recrear, no se cambió Compose ni autoarranque.
- **PC/dependencias:** GStreamer/libav/x264 existentes, stdlib Python, ADB y SSH del proyecto. Decoder de un hilo por slices; cola de una imagen RAW con descarte antiguo, ramas de un buffer; sin lookahead/B-frames, x264 baseline/GOP6, TCP sin Nagle y buffer acotado. Fuente ROS solicita GOP de medio segundo al iniciar nuevo stream. No instala paquetes, modifica binarios vendor ni cambia XR/control, red o protecciones.
- **Aplicación:** --check previo; servidor sin streams antes de escribir; backup externo, candidato validado por SRS -t, doble comprobación de instancia/inactividad y hash anterior, HUP y readback. Log confirma reload tcp_nodelay/min_latency/play/publish y gop_cache=0; recarga completa exitosa. Nuevos procesos PC usan los cambios. No START/Y/HOME/cambio de modo enviados.
- **Verificación:** 24 pruebas offline y sintaxis Python/Bash correctas. Benchmark sintético en tiempo real a 12 fps: conversión PC 1,273 s → 0,027 s de mediana y primer frame 1,297 s → 0,043 s. No equivale a latencia extremo a extremo. Imagen completa e igual por ojo verificada en vídeo sintético. Ensayo real: 437 frames / 74 keyframes / ~12,4 fps y mejora visual confirmada por operador. Shellcheck no disponible; no garantías de latencia máxima.
- **Corrección de continuidad:** la prueba terminó con timeout del heartbeat de vídeo. El publicador anterior Empty no coincide con CameraPusher::handleHeartbeat(std_msgs::msg::String); callback sólo actualiza steady_clock. Se corrige el lanzador a std_msgs/msg/String a 2 Hz. El grafo vivo confirma un suscriptor nativo String y la recepción de `{data: heartbeat}`. Prueba sin visor completada: 113 publicaciones, >55 s, sin nuevo timeout y stop explícito code=0; después sin streams SRS ni publicador de esta prueba. No se modifica el timeout ni un watchdog de control del robot.
- **Backup/evidencia/hashes:** `../Humanoide-vla-evidence/20261016T093737Z_PICO_VIDEO_LOW_LATENCY/`: before, benchmark antes/después, srs-apply/{original.conf,installed.conf,receipt.json,validation.txt,reload.log}, after/hashes. Config original f17d118c5de55838650975f8275aad354725b18ecf6d941c58ef07dfd5f269af → instalada 753d219b2732eef4422d4b2703e18eaf2c2047c487e53ecae3a152dde2a1b67d. Evidencia privada fuera de Git; conservar cambios preparados previamente por el usuario.
- **Reversión/reanudación:** --restore carpeta de srs-apply sólo con streams cerrados y misma instancia/hashes; deja nuevo recibo, sin restauración automática ante error. Revertir selectivamente fuentes PC desde before preservando trabajo posterior, conservando la corrección del heartbeat String. Prueba sólo vídeo mediante --run de cruzr_pico_camera.sh; mantener robot inmóvil y Listen sin alternar. No mantener el relay independiente junto al próximo lanzador de teleoperación.

### PICO-CAMERA-LATENCY-20261016 — incidencia de latencia; sin adaptación aplicada

- **Fecha/zona/estado:** 16-10-2026 Europe/Madrid. Operador comunica unos 3 s de desfase; OBSERVADO, sin medición instrumental. La imagen está verificada; su latencia para teleoperación sigue PENDIENTE.
- **Inspección:** Ethernet eno1 hacia Vision, PICO USB / app PID 13513. Al consultar ya no hay relay PC, conexión de vídeo ni streams SRS. Conversión SBS a 2560×720 con recodificación x264 zerolatency y colas por defecto; sus límites no equivalen a latencia medida. MediaDecoder registra `No input buffer available: -1` antes de EOF. Causa exacta PENDIENTE; no atribuir automáticamente a Wi-Fi, GOP ni a una suma de colas paralelas.
- **Destino/versiones:** lectura de fuentes PC de cámara, propiedades GStreamer instaladas, SRS v5.0.213 / conf/rtmp2rtc.conf y logcat de XRoboToolkit 1.1.1. Sin modificaciones de ejecución, paquetes, red, APK, código de vídeo o robot. No START/STOP/HOME/cambio de modo enviados.
- **Evidencia/respaldo:** `../Humanoide-vla-evidence/20261016T093449Z_PICO_CAMERA_LATENCY_READONLY/`, consultas, findings.json, hashes de fuentes y before documental. Reversión de ejecución no procede, sólo consultas. Se conserva todo cambio anterior, incluido el trabajo preparado en el índice Git por el usuario.
- **Reanudación:** medir extremo a extremo con evento visual y robot inmóvil; comparar SRS, conversión PC y render PICO antes de aplicar cambios. Mantener movimiento pausado durante el diagnóstico. [Estado especializado](teleoperation/CRUZR_S2_PICO_TELEOP_SOURCE_OF_TRUTH.md).

### PICO-CAMERA-STALE-ACCEPT-20261016 — recuperación del receptor y vídeo integrado

**Resultado final VERIFICADO:** el operador confirma «Ya aparece la imagen» en
el comando de teleoperación con cámara `main` y layout `mono-sbs-zed`. El PID
13513 acepta el relay tras una activación limpia de Listen y el PC registra
TCP establecido a `127.0.0.1:12345`. La sesión pertenece al operador; el agente
no envió START, Y, HOME ni cambios de modo. Mantener la ventana abierta y no
volver a alternar Listen. La latencia y los movimientos físicos no se validan
en esta intervención. Evidencia final: `operator-integrated-video-success.json`,
`success-video-sockets.json` y `receiver-actual-command-live.log` en la carpeta
privada indicada debajo.

**Actualización de aplicación:** primer drenaje liberó puerto; captura continua
registra Listen limpia seguida de cierre/reapertura que recreaEADDRINUSE. Se
corrige texto duplicado en padre/hijo: abrir una sola vez al avisoWAIT, dejar
ventana abierta. Segunda recuperaciónEOF bloqueada antes de actuar (USB se
reenumeró y perdiómappings; luego sin cierre reciente enlog). Se restauran sólo
forward12345/reverse63901 y se reinicia app bajoSTOP, comprobando puerto ausente
antes/después. PID6887→13513, nuevo intento con vídeo confirmado. Sinrobotrestart,
HOME/START, nuevas publicaciones de control ni APK modificado.

- **Fecha/zona/estado:** 16-10-2026 Europe/Madrid. Causa nativa VERIFICADA (timeout al detener el hilo y EADDRINUSE; el hilo antiguo acepta y sale). Recuperación de vídeo APLICADA; reintento integrado con imagen VERIFICADA por el operador.
- **Destino/fuente:** PICO aplicación com.xrobotoolkit.client1.1.1; PC scripts/teleoperation/release_pico_camera_stale.py y extensión receiver/test. Sólo se reinició la app bajoSTOP y se descartó un socket de vídeo averiado; no se modifica APK/SDK/firmware/configrobot o protecciones.
- **Motivo/aplicación:** LISTEN podía pertenecer a hilo viejo inválido. Con prueba de fallo del mismoPID y confirmación/registro reciente de ventana cerrada, el helper revalida identidad/mapping/PID/noESTAB/noPCrelay/control/STOP, manda una EOFvacía sólo12345 y exige que el puerto desaparezca. No sondeo de receptor sano, no retry automático. [Receta exacta y límites](teleoperation/CRUZR_S2_PICO_TELEOP_SOURCE_OF_TRUTH.md).
- **Versión/dependencias/verificación:** APKlocal/vendorv1.1.1; funcionesJava no cierran accept bloqueado coninterrupt. Helpersstdlib+ADB/ss/logcat+checkSTOPpasivo existente. Extensión del checker lee PID/últimoListen y errores; lifecycleunavailable si ring sinmarcadores no certifica ciclo.19 pruebas offline/sintaxis/diff pasan. --check manual+recuperación real EOF sinpayload, remoteEOF=true/listenerclosed=true; controlcommandsfalse. No claves/publisher físico/force ni límites cambiados.
- **Respaldo/evidencia:** ../Humanoide-vla-evidence/20261016T090843Z_PICO_CAMERA_REPEATED_CLOSE, before de fuentes/docs, amstop/start PID6257→6887, logs, recibo previo y final, after/SHA256. Reiniciar app por sí solo no bastó en la interacción observada; fragmento no prueba toda la vida del PID.
- **Reversión/reanudación:** no restaurar socket roto; activar un único ZEDMINI/Listen nuevo y comprobar vídeo real por el lanzador. Restaurar selectivamente fuentesPC desdebefore si se descarta el código. Reverse63901/forward12345 conservados. No repetir release con PID/log antiguos ni aplicarlo a una sesión activa; helper bloquea esas condiciones.

### PICO-CAMERA-RECEIVER-20261016 — comprobar receptor remoto antes de usar forward

- **Fecha/zona/estado:** 16-10-2026 Europe/Madrid. Fallo BrokenPipe observado/STOP confirmado; inspección sólo lectura y correcciónPC instalada en fuentes.13 pruebas offline pasan (9receiver+4SBS), sintaxis/diffcheck pasan. Check real negativo valida rechazo de forward presente/PICO sinLISTEN12345, sin abrirSRS. Nuevo intento integrado/control del operador PENDIENTE.
- **Objetivo/destino/fuente:** evitar declarar disponible la cámara porque el forwardADB aceptaTCP mientras el decoder remoto está cerrado. PC `scripts/teleoperation/pico_camera_receiver.py`, test homónimo, integración en cruzr_pico_camera.sh y mensaje en pico_camera_relay.py. Sin cambios de firmware/SDK/APK, Motion/Vision ni nuevas publicaciones de control.
- **Dependencias/aplicación:** adb/USB o targetADB válido, identidadserial, forward existente y ss enPICO; consultas getprop/forward--list/ss, espera acotada y no sondasTCP. --check una lectura; --run espera antes de abrirSRS; --stop conserva disponibilidad aunque visor ya esté cerrado.
- **Hallazgo/límites:** decoder oficialv1.1.1 aceptauna conexión porListen. Causa exacta del cierre reportado no conservada; reapertura/cierre o reutilización son inferencia. ReceptorPICO observado abierto después del fallo, sinstreams ni procesosPC activos. RelojAndroid aparece enmayo2026, no sincronizado; no se modifica.
- **Respaldo/rollback/evidencia:** `../Humanoide-vla-evidence/20261016T090215Z_PICO_CAMERA_BROKEN_PIPE/`, before de código/docs, logoperador/logcat/mappings/ss/procesos/SRS y hashesafter. Revertir selectivamente comprobaciónPC/mensaje desdebefore si se descarta; no repetir instalación, HOME, arranque o cambiar watchdogs. MappingUSB previo conservado; sin ensayo de START por el agente.

### PICO-CAMERA-USB-20261016 — vídeo mono del robot en los dos ojos

- **Fecha/zona/estado:** 16-10-2026 Europe/Madrid. INSTALADO/CARGADO y vídeo real VERIFICADO. Usuario confirma imagen completa/estable en ambos ojos; contadores375frames/16keyframes/11,9fps en el corte. Check pasivo7/7, XRvr_status1/STOP; ningún START. Vista independiente terminada por EOF; revisión posterior no encuentra relayPC ni streamsSRS. Intento integrado posterior abortó por BrokenPipe antes de START, tratado en PICO-CAMERA-RECEIVER-20261016.
- **Objetivo/destino/fuente:** PC `scripts/teleoperation/{cruzr_pico_camera.sh,pico_camera_relay.py,pico_camera_sbs.py}`, ayuda UI de cruzr_pico_teleop_pc.sh; PICO sólo forward ADB12345 transitorio. No cambio de SDK, firmware, APK o perfil de movimiento. Vision sólo servicios temporales de streaming/heartbeat al ejecutar vídeo.
- **Cambio/dependencias:** layout opcional mono-sbs-zed duplica mono en ambos ojos a2560×720, usando plugins GStreamer ya instalados (sin h264parse, ausente). Default passthrough conservado. UI real1.1.1 Remote Vision→ZEDMINI→Listen→IPPC; cliente13579 falla de forma independiente al decoder12345, no se inventa servidor13579.
- **Respaldo/versión/evidencia:** `../Humanoide-vla-evidence/20261016T084628Z_PICO_CAMERA_USB/`, before de fuentes/docs, inventario previo/recibo forward, APK1.1.1 y referencias oficiales tagv1.1.1 commit9f775b535d781618bd2bb7ef8d6c414c0531387c. Hashes después y resultado en esa carpeta. GUI no coincide con instrucciones históricas Request PC camera data, corregidas.
- **Aplicación/activación prevista:** con listener del visor abierto, `adb -s PA94Y0MGKB070822G forward --no-rebind tcp:12345 tcp:12345`; `bash scripts/teleoperation/cruzr_pico_camera.sh --check --camera main --pico-ip 127.0.0.1 --layout mono-sbs-zed` y --run. Aplicación real completada; [receta y transición a teleop](teleoperation/CRUZR_S2_PICO_TELEOP_SOURCE_OF_TRUTH.md). Relay sólo vídeo, nunca START. Ver receta completa de teleoperación para conexión con lanzador y propiedad única del stream.
- **Reversión/límites:** Ctrl+C en dueño del vídeo o --stop de esa fuente, comprobar fin de heartbeat/stream y retirar sólo forward12345; conservar reverseXR63901. Restaurar exclusivamente fuentes PC desde before si se descarta la adaptación. Same mono en ambos ojos no aporta profundidad; render verificado visualmente por operador; latencia no medida. Cuatro pruebas offline pasan (FLV real sintético, dimensiones2560×720, igualdad de ojos, proporciones, timeout/cierre), sintaxis/diffcheck pasan. Heartbeat máximo900s; no prometer duración ilimitada.

### PICO-XR-USB-20261016 — restablecer túnel XR tras encendido

- **Fecha/zona/estado:** 16-10-2026 Europe/Madrid. Mapping INSTALADO/VERIFICADO. Tras confirmación del operador de Connected/Working y Senddata, check pasivo PC7/7 rc0 con identidad correcta, vr_status1 y STOP. Sin ensayo físico ni START.
- **Objetivo/destino:** PICO PA94Y0MGKB070822G y ADB del PC; únicamente reverse tcp63901→PCtcp63901. Red Motion/Vision por eno1/.11.250 conservada; no servicios robot cambiados.
- **Fuente/dependencias/aplicación:** `scripts/teleoperation/configure_pico_xr_usb.sh --configure`; requiere USB autorizado, identidad, backend STOP pasivo y listener63901. Hash de receta en evidencia. Headset debe usar127.0.0.1, Head+Controllers y Senddata; no Hands óptico para el control por gatillos.
- **Antes/verificación:** reverse vacío, visor Awake, app activa y socket de redUSB192.168.224.184→192.168.224.6. Después --check verifica túnel. `PICO_TELEOP_CAMERA=off CRUZR_IFACE=eno1 CRUZR_PC_IP=192.168.11.250 bash scripts/teleoperation/probar_pico_v4.sh --check` bloquea por vr_status0; actualización10:34: `PICO_EFFECTOR=v4` con `cruzr_pico_teleop_pc.sh --check` pasa7/7; coexisten loopbackADB y socket previo redUSB. USB/tracking verificados; teleop v4 cargada no certificada por este check de PC.
- **Respaldo/evidencia/rollback:** `../Humanoide-vla-evidence/20261016T083300Z_PICO_USB_CONFIG/`, inventario before/after y copias documentales. `--remove` retira sólo63901 bajo STOP; IP anterior de sesión observada .224.6, ajuste visible de app previo PENDIENTE. Reverse transitorio, puede perderse al desconectar; receta versionada permite reaplicar. No firmware, SDK, límites ni autoarranque modificados.

### SWITCH-EFFECTOR-RESTORE-20261016 — restauración de capas sin sobrescribir montajes

- **Fecha/zona/estado:** 16-10-2026 Europe/Madrid. Fallo observado y causa verificada; corrección local y pruebas offline completadas. Reanudación ejecutada: Motion verificado, Vision restauración efectiva vacía, ambos arrancados bajo paro y WaitEStopRelease confirmado. Operador confirma retirada de soportes y liberación; HOME nativo completado y VERIFICADO (dos muestras avanzantes, velocidad0, sin fallos, delta máximo0,002876rad), controlador dexterous_hand_controller running y siete ejes con marcas avanzantes por mano. Resultado PERFIL_Y_HOME_VERIFICADOS=v4 y complete=true en ambos hosts; marcadores cerrados por validación. Sin reinicio físico ni HOME adicional.
- **Destino/fuente:** PC `scripts/hands/{switch_effector,effector_profile_remote}.py`; backend inyectado por SSH en Motion/Vision, sin instalar servicios nuevos. [Receta versionada](guides/CAMBIO_EFECTOR_ABRAZADERAS_MANOS_V4.md). Pruebas `test_effector_mount_restore.py` y `test_effector_resume.py`; 42 pruebas offline pasan, más sintaxis Python/Bash y git diff --check. También se corrigió que una transición a Fault prevalezca sobre un mensaje anterior WaitEStopRelease.
- **Cambio:** filtro por destinos de todos los Mounts en backup/restore/verify, tar validado contra manifest y reempaquetado sin overrides PAX de ruta; copia vacía omitida. `--resume-from` reutiliza la sesión original y verifica backups externos, fuentes, IDs/contrato y estado detenido; conserva Motion restaurado y termina Vision antes de arrancar bajo paro.
- **Dependencias/activación:** mismas imágenes/perfil/guard revisados, ROS de ambos hosts disponible, brazos asegurados, principal pulsado/servos liberado/cargador desconectado; liberación manual para HOME. No se omiten gates físicos.
- **Respaldo/evidencia:** `../Humanoide-vla-evidence/EFFECTOR-20261016T081258Z-1bddf143/` y `recovery/before/`; originales externos SHA256 Motion `f2ca31bb4b1f410343225e78a7a27a48a638a955eacf947728297d7f504f080c`, Vision `e0402c12262ab176f4d89b3b11bf0da3fec0ef435f5a4348b5e6740062a6c8ea`. Reanudación `EFFECTOR-20261016T082431Z-0cf31f55` enlaza la anterior. Hashes de fuentes y resultado final se guardan en evidencia de recuperación.
- **Reversión:** conservar originales y marcador; volver selectivamente a fuentes previas sólo tras revisar fase, bajo paro y con las mismas imágenes. No restaurar historiales sobre mounts, repetir recreación, borrar `active.json` ni ejecutar HOME para probar. Revertir sólo el código PC no revierte el perfil ya instalado en el robot.

### SWITCH-EFFECTOR-20261015 — cambio coordinado de efector

- **Fecha/estado:** 15-10-2026 Europe/Madrid. Herramienta PC PREPARADA; no instalada como servicio y no aplicada físicamente. Perfil actual del robot no cambiado por esta entrega.
- **Motivo/fuente:** eliminar pasos manuales repetidos entre perfiles clamp/base y manos v4/SPS. [Receta y recuperación](guides/CAMBIO_EFECTOR_ABRAZADERAS_MANOS_V4.md).
- **Destino:** entrada PC `scripts/hands/cambiar_efector.sh`; orquestador switch_effector.py, planes effector_profile_config.py y backend effector_profile_remote.py en scripts/hands. Tests en test_switch_effector.py.
- **Dependencias:** SSH del proyecto y known_hosts existentes, Python/PyYAML PC y hosts, Docker/Compose y ROS2/ROSA instalados. Reutiliza la corrección ENI v4 revisada y el clasificador HOME original. No instala paquetes, imágenes ni firmware.
- **Aplicación:** --check consulta; --apply requiere terminal y confirmaciones, HOME previo o recuperación con brazos asegurados, paros/cargador/baterías medidos. Cambia HW_TYPE en compose/DB Motion y compose/metafile CC Vision, sin cambiar otros servicios Vision. Conserva imágenes/montajes/configuración y respalda capas modificadas antes de recrear; no habilita VLA/debug.
- **Activación/verificación:** mantiene principal pulsado hasta WaitEStopRelease. Liberación manual puede iniciar HOME nativo. Éxito solo tras fuentes y procesos coherentes, dos muestras HOME20D avanzantes/reposo/sin fallos, controladores activos y estados v4 cuando corresponde. Guard/ENI desconocidos se rechazan. No hay ensayo de --apply del script nuevo en esta entrega.
- **Pruebas:** 29 casos offline, sintaxis Python/Bash y --check reales para ambos destinos. --verify pasivo rechaza movimiento/postura fuera de HOME; no se interpreta como fallo causado por la herramienta. Sin cambios remotos durante estas pruebas.
- **Respaldo/reversión:** índices previos, fuentes y hashes en `../Humanoide-vla-evidence/20261015_SWITCH_EFFECTOR_TOOL/`. Futuras aplicaciones crean respaldos privados por sesión en PC y `/home/walker/.local/share/cruzr-effector-switch/ID/` de cada host. Marcador active.json bloquea reaplicar una sesión incompleta. Reversión selectiva requiere revisión de fase; nunca restauración/control automáticos ante fallo.
- **Continuación:** ensayo supervisado con hardware correcto en ambos sentidos. Un fallo intermedio conserva evidencia; --verify --finish-session solo cierra sesión/destino coincidentes tras validar estado y archivos. Configuración documentada en la guía, sin depender del chat.



**15-10-2026 — RETURN-CLAMP-20261015: perfil base CARGADO; arranque/HOME VERIFICADOS.**
Usuario solicita retirar dependencia v4 tras desmontar manos. Compose Motion y
selector CC/metafile Vision vuelven al perfil de abrazaderas; DB Motion ya base,
conservada. Lectura confirma que controlador base no carga dexterous_hand_controller.
Actualización: operador confirma paro pulsado/brazos asegurados; nueve Motion
y CC recreados con mismas imágenes, Cmd/montajes y resto del entorno. Archivos
personalizados restaurados/hash verificados; hw/app base running/restart0. Guard
CC Motion3/3/cámaras2/2, liberación confirmada por operador; SelfCheck y
StartMotion succ→JoystickMode. HOME20D medido, velocidad0, sin fallos de
actuadores y delta máximo0,002972rad. Muñecas vacías; no reinicio físico necesario.
No volver a usar PICO v4 hasta reinstalar manos y recuperar perfil SPS. Recetas nuevas restore_clamp_environment.py y
activate_clamp_profile.py; respaldos privados en 20261015_RETURN_CLAMP.
[Aplicación, límites, evidencia y reversión](incidents/2026-10-15_ARRANQUE_SIN_MANOS.md).


### HANDS-REMOVED-BOOT-20261015 — diagnóstico sin efectores

15-10-2026 Europe/Madrid, OBSERVADO/VERIFICADO solo lectura. Muñecas vacías;
HW/CC siguen SPS y falla carga dexterous_hand_controller, StartMotion→Fault.
No se instaló ni revirtió perfil alguno. Selección automática last_eni observada
ahora noimu, frente al unified_noimu de manos; no restaurar a ciegas.
[Informe](incidents/2026-10-15_ARRANQUE_SIN_MANOS.md), evidencia privada
20261015_HANDS_REMOVED_BOOT. Cambios solo documentales, copia anterior
before-docs; reversión selectiva de informe/enlaces. Recuperación y traslado
pendientes; no se certifica perfil operativo sin efectores.


### BOTELLA-VISION-GRASP-20261015 — plan de botella; sin adaptación instalada

**Resumen 15-10-2026:** [proceso de trabajo](plan_botella_resumen.md) y
[PDF](plan_botella_resumen.pdf), 4 páginas con portada e índice. Resume fases,
criterios y alternativas; mantiene los estados pendientes del plan completo.
Generación: `bash scripts/docs/build_botella_pdf.sh docs/plan_botella_resumen.md docs/plan_botella_resumen.pdf`.
La receta admite origen/destino opcionales y conserva los predeterminados del
plan completo. Sintaxis Bash, enlaces locales y extracción del texto final
verificados. Solo archivos locales; respaldo/hash en la subcarpeta privada
`20261015_BOTTLE_PLAN/resumen/`. Reversión: retirar resumen/PDF/enlaces y
restaurar la receta desde su copia anterior, preservando otros cambios.


**Ampliación documental 15-10-2026:** exportación [PDF](plan_botella.pdf), 29 páginas A4.
Receta versionada: `scripts/docs/build_botella_pdf.sh`, reutiliza el renderer existente
y Chrome headless; requiere `markdown_it`. Solo genera archivos locales; sin cambios
en el robot. Verificados sintaxis Bash, metadatos PDF y extracción de texto hasta
referencias/límite final. Reversión: retirar PDF/receta y esta entrada; Markdown intacto.
Hashes y copia de índices anteriores: `../Humanoide-vla-evidence/20261015_BOTTLE_PLAN/pdf/`.

- **Fecha/zona y estado:** 15-10-2026, Europe/Madrid. Documento creado; integración PENDIENTE.
- **Motivo:** definir un procedimiento reproducible para detectar una botella y adaptar un agarre con manos v4.
- **Destino/fuente:** repositorio PC, [docs/plan_botella.md](plan_botella.md); enlaces de seguimiento en PROJECT_SOURCE_OF_TRUTH y catálogo funcional. Ningún cambio de configuración en Motion/Vision/PICO.
- **Dependencias propuestas:** cámaras SHM/CameraInfo, PC con Docker, segmentador COCO, calibración RGB-D/base/TCP e integración nativa de planificación/prensión todavía pendientes. No conecta VLA físico.
- **Aplicación/activación:** documento disponible; las recetas son instrucciones futuras, no despliegue. Reanudar por fase 0 y primera captura estática. No ejecutar bloques físicos junto con bloques de lectura.
- **Verificación:** 40 comprobaciones de sintaxis Bash/Python, 10 enlaces locales y 6 casos aislados de conversión SHM pasan. Docker/YOLO/capturador ROS completo y agarre adaptativo no ensayados. Consultas remotas de tipos, codificación y QoS solo lectura.
- **Respaldo/reversión:** anteriores índices en `../Humanoide-vla-evidence/20261015_BOTTLE_PLAN/before-doc-index/`; revertir exclusivamente la entrada documental y retirar el plan si se descarta. No hay servicio/modelo instalado que revertir.
- **Versión/hash/evidencia:** SHA256 del plan en `../Humanoide-vla-evidence/20261015_BOTTLE_PLAN/validation.json`; esquemas/QoS/inventario en esa carpeta privada. Se conserva la distinción entre datos observados y recetas propuestas.


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
[Estado, receta, respaldos y reversión de manos v4](teleoperation/PICO_MANOS_V4_20261015.md).
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
La reproducción corregida de la copia lenta terminó con is_finished=true y bag played successfully; operador confirma funcionamiento perfecto. No HOME enviado. Procedimiento reutilizable [grabación/reproducción PICO](teleoperation/PICO_GRABAR_REPRODUCIR_PROCEDIMIENTO.md) e inspector local scripts/teleoperation/inspect_pico_motion.py para no repetir investigación del SDK en cada toma. Reutilizar orden articular por nombres, evitar --loop1 en build conocida, leer nombre real con timestamp y preparar derivados sólo cuando necesarios. Mantener confirmación física y preflight fresco; no reutilizar salud/postura histórica. Cuatro pruebas del inspector pasan y grabación real validada estructuralmente. Read-only local en esta intervención, sin otro replay ni configuración robot. Nueva guía, inspector/tests y enlaces PC. Before/after, hashes y validación ../Humanoide-vla-evidence/20261014_PICO_REPLAY_WORKFLOW/. Reversión selectiva documental/herramienta, sin modificar SDK ni motion; no commit/push.


**08-10-2026 — INCIDENT-LOGBOOK-20261005-08. VERIFICADO documental.**
[Bitácora unificada de fallos del 5 al 8 de octubre](incidents/BITACORA_FALLOS_2026-10-05_A_2026-10-08.md): reportes del operador, causas demostradas, hipótesis, cambios y pendientes; anexo CSV con139 ejecuciones locales fallidas (no139 causas ni todas reportadas en chat). Fuentes especializadas conservadas. Observación actual de copia local: min_correction_m0,01m y max_abs_command_delta0,015rad, ediciones manuales del usuario sin cambio por esta recopilación; no sustituir valores históricos de cada ensayo. Sólo documentación PC, sin consulta/orden al robot ni alteración de parámetros. Fuentes, inventario, before/after y hashes en ../Humanoide-vla-evidence/20261008_FAILURE_LOGBOOK/. Reversión selectiva de esta ficha y dos documentos nuevos. No commit/push.


**07-10-2026 — BOX-MARGIN-CONSOLE-20261007. VERIFICADO offline; instaladoPC.**
Usuario pide cambiar20mm. Margen real actual editado porusuario inside_margin_m
0,002(2mm) se conserva; antes CLI/ready mostraban20mm fijo. CLI leePOLICY y
supervisor incorpora inside_margin_m enevento ready; consola muestra margen
real delevento, sininventar20mm enlogs antiguos (fallbackmargenconfigurado).
Cambios sólo presentacióneventos, sin alterar planificación/gates/valoresusuario.
Fuentes: scenario1_cli.py,scenario1_runtime.py,scenario1_console.py ytestconsola.
35testsconsola pasan y --plan localcorrecto; sin ejecución/consulta robot.
El runtime se transmite en próxima ejecución normal, carga/prueba remotaPENDIENTES.
Evidencia before/after, tests.log,plan.log,SHA256SUMS:
../Humanoide-vla-evidence/20261007_BOX_MARGIN_CONSOLE/. Reversión selectiva de
fuentes desdesu before/, conservando cambiosusuario posteriores. No commit/push.

**07-10-2026 — BOX-BASE-UNSTABLE-DIAG. OBSERVADO offline.**
Intento112123_977522 tras llegadaajuste8,1mm falla durantecapturavisual.
Historialmapa de request30 aúltima request39 cambia10,435197mm, giro0,052642°;
última pareja39 cambia≈10,439mm en~90,528ms. stable_base admite5mm/1°,
porloque rechazo esdesplazamiento aparente, no toleranciaarrival. No se distingue
movimientoreal desaltoSLAM; no debaja delcontrol de estabilidad oautorreintento.
Configuraciónactual observada editada poroperador: inside_margin_m0,002 y
max_arrival_distance_m0,018; nocambiada porelagente, pruebas físicas deestas
relajacionesno certificadas. Sólolectura diario/código ydocumentaciónPC.
Evidencia yrespaldo documental selectivo: ../Humanoide-vla-evidence/20261007_BOX_ALIGNMENT_BASE_UNSTABLE_DIAG/.
No ROS/movimiento/configuraciónremota. Estadofísicoactual pendiente.

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

**07-10-2026 — MAP-FUSION-SAVE-VERIFIED-20261007. VERIFICADO por lectura.**
Nuevo utars_nav_map guardaLiDAR+VSLAM; save_mapSAVE_MAP_SUCCEED y6/6hashes
principalescorrectos,90poses/285archivosvisuales. Carga posteriorfusion termina
LOAD_MAP_FINISHED; último navegadorWAITRELOCATE. Guardado correcto demostrado,
relocalización/calidad física y próximo arranque pendientes. No acciones/movimiento
ni cambio remoto delagente.
[Ficha y evidencia](incidents/2026-10-05_UTARS_NAV_MAP_LOCALIZATION.md#map-fusion-save-verified-20261007--captura-visual-persistida).

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

**06-10-2026 — MAP-WEB-EXPLICIT-FUSION-20261006. INSTALADO/HTTP VERIFICADO.**
Por autorización del usuario, dos bundlesweb de inicio normal añaden explícitamente
map_type:fusion. Backups/hash originales y receta versionada conservados;
2tests/sintaxisJS/checkapply/HTTP correctos. Sin reinicios/órdenesROS/mapeo/movimiento.
Operador debe recargarCtrl+Shift+R; captura/guardado yarranque pendientes para mañana.
Persiste reinicio, puede perderse al recrear contenedor: reaplicar sólocompatible.
[Ficha, fuentes y reversión](incidents/2026-10-05_UTARS_NAV_MAP_LOCALIZATION.md#map-web-explicit-fusion-20261006--inicio-normal-con-tipo-explícito).

**06-10-2026 — MAP-FUSION-CONFIG-AUDIT-20261006. OBSERVADO por lectura.**
Revisados env/arranque/montajes, paquetesnav y145configuracionespersistentes:
no ajuste admitido encontrado para fijarfusion. Assetsweb no incluyenmap_type;
el inicio requiere petición explícita para evitar herenciauslam. Sólo auditoría,
sin modificaciones/remapeo/movimiento. Implementación yvalidación PENDIENTES.
[Ficha y evidencia](incidents/2026-10-05_UTARS_NAV_MAP_LOCALIZATION.md#map-fusion-config-audit-20261006--configuración-desplegada-revisada).

**06-10-2026 — MAP-TYPE-INHERITED-USLAM-20261006. OBSERVADO por lectura.**
Nav tras reinicio selecciona mapa sin visual y registra fallbackuslam/Last use
map_type:uslam. Inicio web posterior omite tipo; captura sóloLiDAR concuerda con
herenciauslam. Peticiónfusion debe ser explícita desde inicio, no sólo guardado.
Datos/receta revisables, sin enviar orden o cambiar UI/robot. Causa original de
ausencia visual e implementación/prueba física PENDIENTES.
[Ficha y evidencia](incidents/2026-10-05_UTARS_NAV_MAP_LOCALIZATION.md#map-type-inherited-uslam-20261006--origen-del-cambio-de-captura).

**06-10-2026 — MAP-WEB-MODE-20261006. VERIFICADO por lectura.**
Web desplegada inicia mapping_start con map_name/mapping_mode normal pero sin
map_type; usa ROSLIB/WebSocket. UI delega elecciónfusion/uslam al navegador;
log confirma campo ausente y secuencia reciente sólo LiDAR. Cambio de valor tras
reinicio PENDIENTE, no se atribuye a operación del usuario. Sin cambios remotos.
[Ficha y evidencia](incidents/2026-10-05_UTARS_NAV_MAP_LOCALIZATION.md#map-web-mode-20261006--ui-omite-map_type).

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

**06-10-2026 — MAP-RECREATED-CHECK-20261006. OBSERVADO, sólo lectura.**
Mapa recreado por operador: guardado LiDAR23:39:14 nativo correcto; sin componente
visual y sin get1/put1 (listas vacías). Navegador termina guardado enWAITSETMAP,
último nombre activo vacío. Escenario NO listo; selección, destinos y validación
pendientes. new6 descartado para recuperación por aclaración del operador.
Sin cambios remotos/carga/movimiento del agente.
[Ficha y evidencia](incidents/2026-10-05_UTARS_NAV_MAP_LOCALIZATION.md#map-recreated-check-20261006--guardado-lidar-escenario-pendiente).

**06-10-2026 — MAP-VISUAL-RECOVERY-CANDIDATE-20261006. OBSERVADO por lectura.**
Encontrado /etc/walker/map/new6/vslam:492 archivos/141 poses; seis archivos
principales coinciden con SHA256 de manifiestos. Captura visual persistida bajo
otro nombre; mapa vigente LiDAR carece de vslam. Hay candidata íntegra, pero
compatibilidad de marcos y recuperación operativa PENDIENTES. No se restauró,
cargó ni modificó el robot; hipótesis de sólo memoria no confirmada.
[Ficha, límites y evidencia](incidents/2026-10-05_UTARS_NAV_MAP_LOCALIZATION.md#map-visual-recovery-candidate-20261006--new6-persistido).

**06-10-2026 — NAV-VSLAM-MAP-DIR-20261006. OBSERVADO, sólo lectura.**
Mapa vigente tiene LiDAR/get1/put1 pero no componente visual; VSLAM informa
tracker sin inicializar y save_auto_update_map falla MAP_DIR_ERROR. Directorio
accesible, disco con espacio. Navegación puede terminar status4 incorporando ese
fallo auxiliar; escenario aborta. No se determina modo efectivo ni causa del
cambio de mapa; reparación PENDIENTE. Sin cambios remotos o movimiento.
[Ficha y evidencia](incidents/2026-10-05_UTARS_NAV_MAP_LOCALIZATION.md#nav-vslam-map-dir-20261006--mapa-visual-ausente).

**06-10-2026 — BOX-GET1-DISTANCE-DIAG. OBSERVADO offline.**
Diario134210_433140: llegada get1 reporta9,7mm/0,33°. Tras dos ajustes,
última pose archivada queda15,304mm del get1 de ESTA ejecución
(X−0,166060932/Y0,800009887/yaw−3,113288720); no son coordenadas de mapas
anteriores ni una lectura física actual. Caja X0,804998160→0,776323314→
0,779033661m base_link. Primer objetivo34,998mm mejora28,675mm; segundo
6,323mm (<ventana terminal12mm) termina con residual8,476mm y nueva caja
2,710mm más lejos. NO_IMPROVEMENT aborta antes del agarre: exteriorXYZ
admite últimaX, pero margen interior exigeX≤0,77m. Sin cambios de ejecutor,
órdenes o conexión al robot. Mejora de planificación de objetivos pequeños
sigue PENDIENTE; no se aplica el mínimo20mm propuesto anteriormente en el chat.
Evidencia/backups documentales selectivos:
../Humanoide-vla-evidence/20261006_BOX_GET1_DISTANCE_DIAG/.

**06-10-2026 — BOX-01-VISUAL-ALIGN-ENVELOPE-DIAG. OBSERVADO offline.**
Diario132500_391413: caja X0,837857869/Y0,086008026/Z0,926560129m base_link.
Preparación exige X≤0,77m: solicitud X+67,857869mm>50mm por objetivo;
aborta antes de navegación correctiva/agarre. Es límite de un objetivo,
distinto del presupuesto acumulado del intento131056. Llegada get1 válida
no demuestra alcance de caja. Sin órdenes/conexión ni modificación de límites;
estado físico actual PENDIENTE. Evidencia y respaldo documental selectivo:
../Humanoide-vla-evidence/20261006_BOX_ALIGNMENT_ENVELOPE_DIAG/.

**06-10-2026 — BOX-01-VISUAL-ALIGN-LIMIT-DIAG. OBSERVADO offline.**
Diario131056_357497: X inicial0,808542620m solicita+38,542620mm;
llegada residual10,197mm/0,438°. Nueva X0,783235489m cumple gate exterior,
pero queda13,235489mm fuera del margen interior (Xmáx0,77m). Segundo objetivo
llevaría el total solicitado a51,778109mm>50mm; aborta después de UN ajuste
por presupuesto acumulado, no por agotar dos intentos. Mejora visual25,307130mm.
No se alcanzó agarre. Lectura de diario local, sin conexión/comandos al robot;
postura/parada/caja actuales PENDIENTES. No se cambian límites ni planificador.
Evidencia/backups/hashes: ../Humanoide-vla-evidence/20261006_BOX_ALIGNMENT_LIMIT_DIAG/.
Reversión sólo documental selectiva desde before/, preservando cambios ajenos.

**06-10-2026 — NAV-RELOCATE-FAILED-20261006. OBSERVADO, sólo lectura.**
Intento121855 entra FSM_WAITRELOCATE; relocalización global aborta status6 antes
de enviar get1. No se alcanza recogida. Logs pasivos posteriores muestran fallos
USLAM/LiDAR y VSLAM LOST; no se atribuyen por UUID al intento inicial. Destinos
presentes, causa raíz y recuperación PENDIENTES. Sin órdenes o cambios remotos.
[Diagnóstico y continuación](incidents/2026-10-05_UTARS_NAV_MAP_LOCALIZATION.md#nav-relocate-failed-20261006--fallo-previo-a-get1).

**06-10-2026 — TELEOP-PREFLIGHT-SIGPIPE-20261006. VERIFICADO offline.**
Preflight del operador13:08:58 rc141, sin START. Reproducido SIGPIPE en selección
`find | sort | head` con inventario voluminoso; sustituido head por sed que
consume toda la salida.7 tests pasan, errores/gates preservados. Causa del
intento real INFERENCIA; validación remota PENDIENTE. Sólo fuentes PC modificadas,
sin conexión, START o movimiento del agente.
[Ficha, comprobación y reversión](teleoperation/CRUZR_S2_PICO_TELEOP_SOURCE_OF_TRUTH.md#teleop-preflight-sigpipe-20261006--selección-de-log-motion).

**06-10-2026 — TELEOP-PREFLIGHT-DIAG-20261006. OBSERVADO / VERIFICADO offline.**
PICO sin ADB, XR activo; --check camera=off rc0 a11:30, ruta Ethernet válida.
Intento del operador11:31 aborta antes de START con causa genérica; requisito
concreto de ese intento PENDIENTE. Lectura posterior Motion rc0 a11:34:56;
a11:41:59 Ethernet ya sin portadora/IP y ruta vía Wi-Fi: requisito eno1 bloquea
correctamente. Diagnóstico PC añade código/requisito y canal ROS fallido,
sin cambiar gates.5 tests offline correctos; sin START, modo o instalación remota
del agente. Reponer enlace físico y --check-motion-ready antes de nueva ventana.
[Ficha, activación y reversión](teleoperation/CRUZR_S2_PICO_TELEOP_SOURCE_OF_TRUTH.md#teleop-preflight-diag-20261006--diagnóstico-previo-a-start).

**06-10-2026 — BOX-01-VISUAL-ALIGN-INSIDE-MARGIN. VERIFICADO offline.**
Intento090347 acepta X0,786254m sin ajustar; agarre posterior rechaza0,790663m
(variación4,409mm). Preparación optimista ahora exige margen interior20mm en
X/Y aunque la caja cumpla el gate nativo: X[0,43;0,77]/Y[−0,37;0,37]m.
Replay solicita X+16,254mm antes del agarre; nueva visión/progreso/presupuestos
siguen obligatorios. Gate SPS original y aborto tras fallo nativo intactos.
Consola muestra ajustes0. 725 pruebas pertinentes correctas; revisión instalada
PC, carga remota y ensayo físico PENDIENTES. Sin conexión ni movimiento del agente.
[Ficha y activación](box_handling/BOX_AXIS_REPOSITION_20261002.md#box-01-visual-align-inside-margin--06-10-2026).

**06-10-2026 — NAV-GET1-20261006. VERIFICADO técnico.**
Tras confirmación física actual del operador, `optimistic_scenario1.sh --check
--stop-after get1` rc0 y `--run --stop-after get1` rc0. Destinos ya presentes en
el mapa nuevo; get1 X1,090119m/Y−0,523853m/yaw0,013935rad. Navegación status4,
FSM_WAITNAVIGATE y dos poses frescas: 7,049mm/0,427° dentro de 20mm/2°.
Dos muestras posteriores de odometría muestran velocidad cero. Sólo navegación;
sin agarre, depósito, HOME enviado ni configuración remota persistente cambiada.
VSLAM_LOCATION_LOST auxiliar persiste; precisión física independiente y nueva
medición HOME final PENDIENTES. Avisos de lease pertenecen al cierre tras éxito.
[Ficha de ejecución y reversión](box_handling/GET1_PUT1_MAPA_Y_EJECUTOR.md#nav-get1-20261006--traslado-al-destino-del-mapa-nuevo).

**05-10-2026 — MAP-HEAD-RELOCALIZE-20261005. OBSERVADO, sólo lectura.**
Tras nuevo guardado, cabeza movida por vnav_head_processor/navigation durante
relocation_start fusion. Navegador termina barrido con stop_rotate y centro0/0;
Motion confirma IsReached, cabezaREADY. Relocalización exteriorstatus4/READY/
FSM_WaitNavigate, mientras VSLAM aúnLOCATION_LOST: no demuestra recuperación
visual ni precisión física. Mapa nuevo2471puntos/56poses; lectura4443/38 anterior
ya histórica. Sin acciones, movimientos o cambios remotos del agente.
[Secuencia, UUID, límites y evidencia](incidents/2026-10-05_UTARS_NAV_MAP_LOCALIZATION.md#actualización-posterior--cabeza-y-relocalización-del-mapa-nuevo).

**05-10-2026 — VOICE-MAPPING-08. OBSERVADO; traducción no integrada.**
Cartografía emite TTS chino: «cerrando bucle; reduzca velocidad/espere» y «bucle
completado; continúe mapeando o guarde». Literales en libmapping2d_lidar.so,
fuera de adaptadores de workers/Control Center/freno; estas últimas bibliotecas
sí están cargadas. Cartografía del operador posteriormente guarda2D/visual y
FSM_Mapping SUCCEEDED; calidad/localización posterior no comprobadas.
Sin audio nuevo, movimiento, reinicio o cambios remotos del agente.
[Textos, origen, evidencia y continuación](voice/AVISOS_MAPEO_CHINO_20261005.md).

**05-10-2026 — MAP-QUALITY-20261005. OBSERVADO, sólo lectura.**
Última relocalización utars_nav_map falla; VSLAM=LOCATION_LOST y pose visual
no fiable. Mapa visual presente4443puntos/38poses, pero candidatos no superan
consistencia de solver (ejemplo17<20). Cobertura/calibración/causa PENDIENTES.
API y archivos actuales no contienen destinos: get1/put1 ausentes; escenario1
bloqueado por Require one unique get1. No copiar coordenadas de un marco antiguo.
Sin relocalización/movimiento, reinicio ni edición del mapa por el agente.
[Hallazgos, límites, evidencia y continuación](incidents/2026-10-05_UTARS_NAV_MAP_LOCALIZATION.md).

**05-10-2026 — VOICE-VOLUME-READONLY. OBSERVADO, sin cambios.**
cruzr_say_english.sh envía volume=100; PulseAudio en Vision y dentro de
walker-voice.speech_service-1 muestra salida predeterminada100%, mute=no.
Salida analógica activa: alsa_output.platform-sound.analog-stereo. Consulta sólo
lectura; sin audio ni cambio de volumen. Amplificación adicional no ensayada.
Receta manual tras acceso SSH a walker@192.168.11.3:
`pactl set-sink-volume alsa_output.platform-sound.analog-stereo 110%`;
reversión al valor observado: mismo comando con100%. Puede distorsionar.
Evidencia y respaldo documental: ../Humanoide-vla-evidence/20261005_VOICE_VOLUME_READONLY/.


**05-10-2026 — VOICE-TTS-HELLO-MATEO. VERIFICADO técnico; escucha PENDIENTE.**
Petición explícita: decir «Hello Mateo». Vision192.168.11.3: docker ps descubre
walker-voice.speech_service-1; --check confirma sys_task_msgs/action/Tts y un
servidor. Comando versionado: ./scripts/cruzr_say_english.sh "Hello Mateo";
objetivo0cbb2742-6939-4e17-a1f6-743c2177c220 aceptado, desc=Success, status=4.
Wrapper sale27 por exigir texto SUCCEED; no se repite la reproducción. Revisión
de esa validación PENDIENTE. Fuente SHA256442760e137480abb38e232396aa79d9f84c34b1f4b359d2565c1028b797a58c7.
Sólo audio transitorio; sin movimiento, instalación, reinicio ni configuración
remota modificada. Escucha humana no confirmada; estado físico no inferido.
Evidencia/resultado y respaldo documental before/after:
../Humanoide-vla-evidence/20261005_HELLO_MATEO/.
Reversión documental selectiva desde before/; no hay configuración que restaurar.


**01-10-2026 — BOX-01-TABLE90: adaptación probada y HOME medido.**
Instalados/cargados XML/YAML3e142cd1…; ensayo supervisado en tres tramos cubre
las diez etapas. Depósito/apertura SUCCEED; operador confirma caja estable sobre
mesa90 y liberada. HOME SUCCEED, dos muestras MEASURED_HOME=1, velocidad0,
máximo absoluto corporal0,002684rad. Final --check rc0 confirma salud/HOME,
modelo y tareas. Ciclo optimistic90 habilitado sólo para hash del perfil probado;
seis pines incluyen HOME nativo. Caja/agarre/XY/torso/controles originales intactos.
577 pruebas pertinentes correctas; legacy17 errores preexistentes excluidos.
Mapa utars activo, robot HOME y caja en destino. Sin reinicio, commit ni push.
Una prueba física con confirmación de operador no es certificado continuo ni
calibración independiente. [Fuentes, evidencia y reversión](box_handling/SCENARIO1_TABLE90_CANDIDATE.md).


**01-10-2026 — BOX-01-TABLE90: agarre real y ensayo acotado preparado.**
Check instalado rc0 confirma hashes/tareas/modelo y HOME. Navegación a get1,
visión y agarre frontal nativos terminan SUCCEED; operador confirma caja sujeta,
completamente separada y estable. No depósito ni HOME todavía. Checkpoint:
`../Humanoide-vla-evidence/20261001_SCENARIO1_TABLE90/grasp-trial/checkpoint.json`.
Lectura fresca de `/mc/whole_joint_states`: articulaciones nombradas, velocidades0.
IK condicional desde esa postura, con regularización de continuidad0,001:
61/61 muestras por perfil original/90 convergen; sin excesos de velocidad por
diferencias finitas. No certifica interpolación nativa ni escena exterior.
Se añade `--stop-after deposit`: termina tras tarea nativa/apertura, antes de
asumir liberación o enviar HOME. Ciclo completo sigue bloqueado; ensayo acotado
supervisado autorizado por el usuario, conservando controles nativos y pines.
576 pruebas pertinentes correctas (17 errores legacy excluidos ya reproducidos
en baseline). [Estado y recetas](box_handling/SCENARIO1_TABLE90_CANDIDATE.md).


**23-09-2026 — VOICE-BRAKE-07: idioma del aviso de freno instalado.**
Frase exacta de backend_service_vision→WAV español; lógica/condición del freno
intactas.7 hashes correctos, prueba nativa y a través del entrypoint instalado
pasan, cero objetivos/audio. Paro1 verificado. Carga real al próximo inicio del
backend y escucha PENDIENTES; sin restart ni movimiento. Rollback independiente.
[Fuentes, evidencia y reversión](voice/AVISO_FRENO_ES_ROLLBACK_20260923.md).


**23-09-2026 — VOICE-BOOT-06: anuncio inglés automático retirado.**
Watcher conserva comprobaciones y visual; sólo se retira announce() de --watch.
Aviso nativo español intacto.31 tests pasan y hash remoto verificado; sin restart
ni reproducción. Efectivo al próximo watcher; prueba de nuevo encendido pendiente.
[Fuente, respaldo y rollback](voice/RETIRADA_AVISO_INGLES_20260923.md).


**23-09-2026 — VOICE-BOOT-05: primera reproducción real confirmada.**
Reinicio realizado por operador. Silencio inicial: guard esperando Motion0→3/3
antes de ejecutar Control Center; cámaras6topics2/2 con timestamps crecientes.
Después registra carga VOICE_CC y conversión a FILE español. Speech Service recibe
/etc/walker/voice/control_center_es_v1/audio_es/cc_016.wav, goal
021f9637-e809-4195-bcee-ae44c9dcf6e8; callbacks de inicio y fin y envío de éxito.
Operador confirma escuchar en español «Gire y libere el botón de parada de emergencia».
Queda verificada carga real y escucha de ese aviso, no de todos los24 ni batería.
Paro leído1 durante diagnóstico; CC alcanza WaitEStopRelease. No liberación,
reinicio, reproducción ni movimiento ordenados por agente; sólo consultas.
Los mensajes de shutdown de PID942 pertenecen al proceso anterior, no a fallo del
nuevo arranque. No inferir fallo por nivel E de callbacks: describen inicio/fin.
Evidencia: /home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260923T094542Z_VOICE_BOOT_CHECK.

**23-09-2026 11:39 CEST — VOICE-BOOT-05 instalada con rollback.**
Control Center:24 avisos fijos a WAV español, patrón de batería a TTS inglés;
mensajes desconocidos preservados.32 archivos verificados; guard de hashes y
LD_PRELOAD antes del exec, gates originales idénticos por comparación AST.
Paro1 antes/después. Prueba nativa de objetivos pasa, cero audio/movimiento.
Proceso actual aún sin adaptador; carga al próximo inicio y escucha PENDIENTES.
No reinicios ni cambios de red. Recibo externo20260923_VOICE_CC_DEPLOY/receipt.json;
backup persistente /etc/walker/voice/deployments/cruzr-voice-20260923T093840Z.
[Fuentes, compatibilidad, validación y rollback](voice/CONTROL_CENTER_ES_ROLLBACK_20260923.md).


**23-09-2026 — VOICE-BOOT-05: conexión recuperada, causa contrastada en vivo.**
Control Center del último arranque registra avisos chinos vía tts_impl.cpp;
24 WAV españoles nuevos generados localmente con Piper (mono16kHz PCM16,
señal/duración verificadas), traducciones inglesas preparadas y cuatro ejemplos
numéricos de batería separados como dinámicos. No están instalados ni conectados.
Catálogo: docs/voice/catalogo_control_center_20260923.json. Paquete PC:
/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260923_VOICE_CC_AUDIO (ESCUCHAR.html y audio_es/manifest.json).
Los949+7 archivos ES03/EN04 pasan comparación SHA tras reinicio: no se perdieron.
Paro principal leído0; no se solicita pulsarlo antes de preparar integración y
revisar postura. No se modificó ni reinició ningún servicio ni se reprodujo audio.
Inspección nativa: processRequest construye Tts_Goal TTS1 con texto y velocidad/
volumen; llamada directa a ActionClient::start. El adaptador de workers no cubre
esa función; base.conf/cc.conf no muestran selector voice/locale/language/tts.
No se ha validado todavía una integración del cliente de Control Center: no
instalar ahí el adaptador anterior suponiendo que funcione. Pendiente diseñar y
probar conversión de objetivos preservando callbacks y voz de fallos, respaldar
cliente/lanzador y preparar rollback antes de cualquier despliegue.
Evidencia de lectura y desensamblado: /home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260923T093159Z_VOICE_CC.
Cambios sólo PC (catálogo, WAV, HTML y documentación); rollback local selectivo,
conservar respaldos ES03/EN04. Sin commit/push.

**23-09-2026 11:30 CEST — PC-01: Wi-Fi USB desconectada, diagnóstico de lectura.**
A las11:03:33 el adaptador Realtek0bda:b812/rtw88_8822bu pierde asociación
(reason2 PREV_AUTH_NOT_VALID); después repite failed to download firmware /
failed to leave ips state. NetworkManager registra ssid-not-found a11:03:48.
Adaptador presente y rfkill sin bloqueo; no demuestra avería física ni identifica
la causa inicial de la desautenticación. Ya hubo errores USB -71 a09:27.
Ethernet eno1 sigue NO-CARRIER/carrier off pese a cable conectado según operador.
Los planes VOICE-ES-03/EN-04 (949+7 rutas) no incluyen red/driver/firmware;
no hay evidencia de relación causal con audio. No se puede comprobar aún el AP
del robot. No se modificó red, driver, servicios ni robot.
Evidencia: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260923T093026Z_PC_WIFI_AUDIT`. Reanudar comprobando enlace Ethernet y recuperación del
adaptador USB; diagnóstico del arranque/audio sigue pendiente de conectividad.

**23-09-2026 — VOICE-BOOT-05: cobertura de arranque incompleta.**
Operador escucha chino tras reinicio. Logs históricos identifican TTS propio de
Control Center (`tts_impl.cpp`), fuera del adaptador de workers VOICE-EN-04 y
los XML de VOICE-ES-03. 28 textos observados inventariados; no catálogo exhaustivo.
Lectura del último arranque pendiente por timeout SSH a Vision. No se modificó
robot ni se reprodujo audio. [Auditoría y pendientes](voice/AUDITORIA_ARRANQUE_20260923.md).


**23-09-2026 — VOICE-EN-04: ruta TTS dinámica integrada e instalada.**
Adaptador local para TtsClient:346 traducciones/fragmentos; texto/números en EN;
FILE español intacto. Chino desconocido conserva objetivo original y registra
aviso, sin ocultar errores. Lanzador de ae_bt_worker carga biblioteca con hashes
fijados; no se toca biblioteca vendor. Siete rutas verificadas. Paro1 mantenido.
Prueba nativa de ABI/enlace y prueba del lanzador correctas, cero objetivos/audio.
Sin workers activos en lectura previa; se aplica al próximo worker. Primera tarea
real/escucha pendientes; sin reinicios. Rollback independiente devuelve lanzador
y elimina sólo archivos de esta capa, preservando el paquete español anterior.
Recibo externo: ../Humanoide-vla-evidence/20260923_VOICE_DYNAMIC/install/receipt.json.
Respaldo persistente: /etc/walker/voice/deployments/cruzr-voice-20260923T085523Z.
[Detalles, límites y rollback](voice/TTS_DINAMICO_EN_Y_ROLLBACK_20260923.md).

**23-09-2026 — VOICE-ES-03: avisos españoles instalados en disco.**
Autorizado con paro principal pulsado, comprobado antes de cada grupo.
291 WAV +2 JSON en /etc/walker/voice/es_local_v1;600 XML ahora usan FILE español;
56 rutas de audio hablado sustituidas. Música/efectos intactos.949 hashes finales
verificados. Sin reproducción, recarga, reinicio ni movimiento. Dinámicos60
conservan ruta nativa (puede hablar chino); EN sólo preparado, no integrado.
Rollback ejecutable con recibo y originales inmediatos persistentes:
/etc/walker/voice/deployments/cruzr-voice-20260923T083811Z;
copia externa ../Humanoide-vla-evidence/20260923_VOICE_INSTALL/run/.
Fuentes build_spanish_install.py/deploy_voice_assets.py y test, bajo scripts/voice.
Cuatro tests pasan. Instalado: sí; carga/reproducción: PENDIENTES.
[Instalación, límites y comando de rollback](voice/INSTALACION_Y_ROLLBACK_20260923.md).

**23-09-2026 — VOICE-ES-02: respaldo verificado y síntesis local preparados.**
Inventario vivo:344 textos TtsClient distintos,284 fijos (274 chinos),60 variables.
291 WAV ES locales Piper:284 textos +7 propuestas de audios hablados transcritos
con Whisper local. TTS EN preparado con language=en;600 copias XML sólo texto.
Música/efectos conservados por petición explícita. No se instaló/reprodujo nada
ni se enviaron movimientos. Audición humana/idioma efectivo del dispatcher e
integración de variables dinámicas pendientes; respuesta infantil breve ambigua.
Seis tar externos con4278 entradas verificadas +ejecutable TTS separado;173 rutas
de audio entre contenedores,21 hashes distintos. Identidades Docker/metadata
privadas, permisos y hashes preservados. Ensayo de rollback offline de XML/audio;
no restauración remota. Primer tar con log transitorio cambiante rechazado y
conservado como fallo; sólo originals_verified/ es válido.
Paquete, modelos/atribución, entorno y hashes:
`../Humanoide-vla-evidence/20260923_VOICE_ROLLBACK`.
Fuentes/receta/alcance y rollback: `docs/voice/VOZ_LOCAL_Y_ROLLBACK_20260923.md`,
`scripts/voice/`; catálogo actual JSON y traducciones adicionales versionados.
Cambio persistente sólo PC: Piper1.8.0 añadido al entorno privado de voz y modelos
Piper/Whisper descargados; GPU4070 disponible, generación/transcripción en CPU.
Reversión selectiva de archivos nuevos PC; preservar backups para cualquier
instalación posterior. Ningún cambio en SDK original ni robot. Sin commit/push.

[Paquete local y rollback](voice/VOZ_LOCAL_Y_ROLLBACK_20260923.md).

**22-09-2026 — VOICE-ES-01: catálogo y paquete ES/EN preparados en PC.**
109 textos fijos y19 variables TtsClient inventariados en snapshot16-09;
traducciones ES/EN y57 copias XML inglesas (sólo literales tts; variables intactas).
Más aviso local de arranque ya inglés:110 audios ES y110 EN, cada uno WAV PCM16
mono16kHz y MP3. Decodificación/duración/señal verificadas; no escucha humana.
22 rutas WAV originales del inventario previo listadas, sin copia/transcripción:
el robot perdió conexión y el operador confirmó apagado/desconectado.
Inventario exhaustivo actual, mensajes compilados/dinámicos y escucha originales
PENDIENTES. No se cambió ni reprodujo nada en el robot. Catálogo y recetas en
`docs/voice/CATALOGO_VOZ_ES_EN.md`; fuentes `scripts/voice/` y TSV versionados.
Paquete, reproductor HTML, ZIP, hashes, versiones y fallos de conexión en
`../Humanoide-vla-evidence/20260922_VOICE_ES_FULL`.
Entorno PC privado `../Humanoide-vla-evidence/voice-tools-venv` (Edge TTS, PyAV,
soundfile; faster-whisper instalado pero no utilizado, sin modelo descargado).
Síntesis remota de textos traducidos, sin envío de grabaciones. Dependencias
fijadas en requirements-frozen.txt. Instalado/cargado/probado en robot: NO.
Reversión: retirar sólo archivos nuevos/entorno privado y revertir notas
selectivamente; no hay configuración remota a restaurar.

**22-09-2026 14:31 CEST — HOME-V8-AUTO-01: nuevo arranque, liberación preparada.**
Usuario reinició todo manteniendo el paro. Boot Motion nuevo
bd5efdb3-f7e0-40b2-a519-50c8ffa893de; contenedores redescubiertos.
HOME remoto conserva SHA d9e9462792b41300d352604b53ea2a4890a9382e942321990708f6ded2e26ccb.
`cruzr_boot_ready.sh --check` rc0: Motion3/3, seis cámaras2/2 con timestamps
crecientes, RELEASE_TECHNICAL_CHECK=passed. Contrato: arranque inicial CC,
paro principal pulsado, secundario liberado y cargador desconectado.
Operador confirma brazos abajo, abrazaderas instaladas/vacías, sin sujeciones,
recorrido libre, ruedas bloqueadas, control exclusivo y persona junto al paro.
Comprobación técnica y física previas completas; se indica liberar manualmente.
Liberación, ejecución HOME v8 automático, salud20D y fin del arranque PENDIENTES.
El agente sólo leyó; no envió acciones, rearme ni reinicio. Evidencia:
`../Humanoide-vla-evidence/20260922T123059Z_V8_BOOT_CHECK`.

**22-09-2026 — HOME-V8-AUTO-01: v8 INSTALADA como HOME automático.**
Tras nueva petición «hazlo ahora», paro principal1/servo0, cargador0 y hashes
verificados. home.xml sustituido atómicamente por el XML exacto ensayado:
SHA256 `d9e9462792b41300d352604b53ea2a4890a9382e942321990708f6ded2e26ccb`.
Postcheck confirma v8 y paro mantenido. Sin movimiento ni reinicio del agente.
13,45s nominales; prueba física previa de tarea separada satisfactoria.
Carga de esta sustitución y prueba durante arranque PENDIENTES. Motion seguía
esperando ListControllers; instalación no implica recuperación de ese servicio.

El rechazo anterior se resolvió contrastando los diarios retenidos: mismo boot,
medición HOME reciente, contador del diario original sin cambios, cero tareas
en todos sus sucesores, salida anterior por heartbeat y nueva instancia esperando
controladores. El instalador admite esta continuidad sólo para escritura bajo
paro; no declara salud actual ni autoriza liberación o movimiento. Registro
HOME original intacto. Se rechazan tareas nuevas, diario ausente/inconsistente,
cambio de boot, caducidad o historia de reinicio no explicada.

Destino: Motion, walker-motion.manipulation_robot_app-1,
`/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config/cruzr/home.xml`.
Backup robot: `/etc/walker/trajectory-overlays/20260922T122256.171279Z_home_body_first`.
Backup externo previo: `install/home.v7.before.xml` en
`../Humanoide-vla-evidence/20260922T122230Z_HOME_V8_RESUME`;
recibo, postcheck, continuidad, fuentes y SHA256SUMS en la misma evidencia.
Fuente/receta: `scripts/teleoperation/install_home_v8_auto.py --install --evidence /RUTA/NUEVA`;
requiere medición previa según su guía. Preflight de cajas reconoce hash v8 exacto.
Reversión: bajo paro y sin acciones, comprobar hash v8 y restaurar únicamente
home.before.xml del backup (v7 SHA1e6e2fb7…a6f03), verificar hash tras escritura.
No se realizó reversión ni activación. Mantener paro hasta preparar recuperación
controlada de servicios/arranque; no usar liberación como prueba del fallo.

**22-09-2026 — HOME-V8-AUTO-01: sustitución detenida antes de escribir.**
Operador confirmó paro principal pulsado tras HOME medido. Preflight verificó
paro principal1, servo0, cargador0 y hashes originales. El guard de continuidad
rechazó la instalación: cambió robot_app_log. Log anterior termina con fatal
heartbeat delta_t=5,04583s a20:19:47.723727 (hora nativa); nueva instancia
20:19:48 espera ListControllers. Contenedores robot_app y HW muestran arranque
reciente. Causa de la pérdida de heartbeat PENDIENTE; no atribuirla al XML v8.
No se ejecutó escritura, reinicio ni movimiento del agente. Hash remoto final
confirma HOME v7 intacto. Mantener paro; instalación/activación v8 automáticas
PENDIENTES hasta resolver continuidad/estado. No falsear el registro HOME ni
liberar el paro sólo para superar el instalador. Evidencia:
`../Humanoide-vla-evidence/20260922T121856Z_HOME_V8_AUTO` (install/status.json,
identity-after-stop.json, logs y home-final-hash.json).

**22-09-2026 — HOME-V8-AUTO-01: promoción solicitada, instalación PENDIENTE.**
Usuario pide v8 como HOME automático tras ensayo satisfactorio. Preparado
`install_home_v8_auto.py`: exige HOME medido reciente, misma instancia/sin
nuevas tareas, paro principal pulsado, hash v7/MetaMove y copia externa antes
de sustituir atómicamente home.xml por los bytes exactos de la candidata.
Nueva medida: HOME20D, velocidad cero, máximo 0,002876 rad. Se solicita al
operador pulsar el paro principal; aún no se ha escrito ni reiniciado el robot.
Preflight del ciclo admite el hash exacto v8 conservando chequeo MetaMove.
Tres tests de candidata, sintaxis shell y diff-check correctos.
Evidencia: `../Humanoide-vla-evidence/20260922T121856Z_HOME_V8_AUTO`.

**22-09-2026 14:12 CEST — HOME-V8-CANDIDATE-01: prueba física completada.**
Una ejecución de la tarea separada devuelve SUCCEED/status4; HOME medido en los
20 ejes, velocidad cero, máximo absoluto 0,002876 rad. Operador confirma recorrido
normal, sin contacto, tirones ni ruidos anormales, y estabilidad final.
Tiempo observado desde inicio del árbol hasta último MetaMove: 15,059 s;
nominal 13,45 s conservado. Hubo 202 rechazos iniciales de consigna durante
0,402 s antes de entrar en el límite del hombro; no se modificaron protecciones.
Instalada, cargada y probada desde esta postura concreta; no recuperación general.
HOME automático sigue en v7; sin reinicio ni rearme de Control Center.
Salida de su Fault previo NO verificada. [Prueba, evidencia y límites](teleoperation/CRUZR_HOME_V8_CANDIDATA.md).

**22-09-2026 — HOME-V8-CANDIDATE-01 instalada de forma aditiva, sin movimiento.**
Tarea separada home_v8_early_roll_CANDIDATE reparte apertura−0,05/−0,15rad
con el primer ajuste de codo; mantiene13,45s nominales y destinos finalesv7.
No es condicional ni recuperación general. Lectura actual y barridos501,
3tests offline correctos; sincronización/seguimiento y prueba física pendientes.
HOME automáticov7 intacto; sin reinicios, task_list ni acciones. Candidata
instalada, carga nativa pendiente. [Fuentes, límites, backup y receta](teleoperation/CRUZR_HOME_V8_CANDIDATA.md).

**22-09-2026 — VOICE-ES-01: inventario para todos los avisos en español.**
Localizados textos TtsClient, WAV y aviso de arranque propio en inglés.
Conversión no instalada; soporte TTS español pendiente. Primera lectura SSH
correcta; consulta posterior de voces bloqueada por timeout de conexión.
Sin audio, micrófonos, reinicios ni cambios remotos. [Inventario y pendientes](guides/CRUZR_S2_VOZ_ESPANOL.md).

**22-09-2026 — BOX-01-ORIGINAL-SCRIPT: variante local con tareas anteriores.**
Creado por petición explícita [force_excenario1.original.sh](../scripts/force_excenario1.original.sh)
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

**22-09-2026 — BOX-01-FRONT-SPS: IK alternativa, no prueba de imposibilidad.**
Operador confirma caja sobre un apoyo. Análisis estático demuestra que la
comprobación IK observada se activa al salir del intervalo original; excesoX
3,55mm en el último intento. Priorizar validación de colocación con margen,
sin ampliar límites, inventar pose ni reactivar el avance corto que retrocedió.
No hay parche de recogida probado. Sólo análisis/imagen histórica y documentación.
[Detalle, receta y evidencia](incidents/2026-09-22_CAJA_FRONTAL_COTA_BAJA.md).

**22-09-2026 — BOX-01-FRONT-SPS: repetición55965b96 y auditoría del original.**
Pose frontal entregada sin alterar; Motion X0,803550/Z0,181595m, límites/IK
rechazados. En la misma captura índice0 corresponde a una lateral: restaurar
Singapore no compararía el mismo objetivo. Trayectoria YAML preservada, pero
equivalencia de ambas vías perceptivas para la misma caja aún PENDIENTE.
Priorizar esa comparación antes de prescribir otra trayectoria. Sólo lectura
y documentación; no nuevas órdenes ni cambios de scripts/robot.
[Registro y evidencia](incidents/2026-09-22_CAJA_FRONTAL_COTA_BAJA.md).

**2026-09-16 — HOME-BODY-FIRST-04:** instalado HOME de20 s con cuerpo a cero
antes de apertura/bajada/cierre de brazos, por petición del propietario y con
paro confirmado. Hash e3d06564…69dc49c; diez tests locales pasan. Sin acciones
de movimiento; ensayo físico pendiente. Sustituye open_v3 como archivo vigente.
Reinicio de manipulación completado y hash verificado; carga funcional pendiente:
Motion espera ListControllers y CC WaitStartMotion. Mantener paro; recuperación
por ciclo completo supervisado v0.2.0 antes de ensayo.
[Receta, respaldo y estado](teleoperation/CRUZR_HOME_CUERPO_PRIMERO.md).


**Relevo para la próxima sesión — 2026-09-14:** leer primero el [estado consolidado y secuencia de reanudación](vla/RELEVO_VLA_20260914.md). HOME→READY→ENTRY está probado por el operador; shadow funciona. TRIAL_02 abortó por timeout al cambiar a SDK, con cero frames y sin acuse; el controlador final es desconocido. Prioridad: consultar controlador y logs antes de reintentar. No repetir ensayos ni asumir estado físico a partir del historial.


**2026-09-14 — Corregida la selección de controlador del ensayo mínimo (VLA-01).**
El intento `ENTRY410_ONE_POINT_TRIAL_01-6l8y73xw` publicó 134 consignas en
1,33 s, con brazos inmóviles, y terminó por `Tracking error: R_shoulder_pitch_joint`.
ROSA nativo confirmó `manipulation_controller=running` y ambos SDK `initialized`:
el ejecutor anterior omitía el cambio de controlador. La captura posterior
coincide con el inicio. Se añadió inventario nativo, cambio mediante
`/mc/motion_sdk/switch_to_vla` sólo en `--run`, respuesta positiva y feedback SDK
20D fresco antes de publicar. Conserva chasis y mantiene explícitamente los
seis ejes fuera de los brazos. Sin aumento de tolerancias, reinicio, HOME ni
reintento automático; al acabar conserva SDK activo. Diecisiete tests locales
pasan; --check y --observe en vivo pasan sin activación ni publicador.
**Cambio de controlador y ejecución corregida pendientes de prueba física.**
Plan vigente: `controller-fixed-plan`; el plan anterior queda obsoleto por hash.
[Detalles, comando y reversión](vla/ENSAYO_MINIMO_PUNTO_VLA_ENTRY410.md).


**2026-09-14 — Corregidos directorio de evidencias y admisión del ensayo mínimo.**
El intento guardado terminó antes de crear el publicador; la segunda invocación
falló por directorio existente. Ahora cada nueva invocación conserva el anterior
y obtiene una ruta única. El diagnóstico identificó pequeñas variaciones de
encoders de rueda; se usa velocidad≤0,01rad/s más deriva≤0,002rad, y admisión
articular≤0,01rad/s con posición inicial≤0,002rad durante1s. No se cambian
trayectoria ni límites de seguimiento. Quince tests pasan; --observe pasó en
vivo con cero publicadores creados. Plan regenerado: admission-fixed-plan.
Ensayo físico del prefijo todavía no ejecutado por el agente.
[Comando vigente, evidencia y reversión](vla/ENSAYO_MINIMO_PUNTO_VLA_ENTRY410.md).


**2026-09-14 — Ensayo mínimo VLA preparado, aún no ejecutado.**
Replay parcial del primer punto del chunk2 desde ENTRY410: ambos brazos,
25 % de la transición, máximo 1,396°, 4 s; no agarre ni chunk completo.
El punto completo mantiene un par mano derecha/mesa sin resolver; el prefijo
conserva 1018 pares certificados y los 54 avisos internos históricos, sin nuevos
fallos geométricos. Trece tests y --check pasan. Ejecutor SDK con lectura de
salud/paros/cargador/postura, seguimiento y llegada; sin reintentos ni HOME.
No requiere instalar XML, recargar o reiniciar. Scripts del operador intactos.
[Comando, límites, reproducción y estado pendiente](vla/ENSAYO_MINIMO_PUNTO_VLA_ENTRY410.md).


**Continuación vigente — 2026-09-14: ENTRY medido y shadow task 0 completado.**
98 muestras inmóviles, error final máximo 0,1593° respecto a ENTRY410. Seis
propuestas y seis aceptaciones por el perfil shadow existente de 14 ejes de
brazos; primer cambio máximo 6,1643° (umbral shadow 0,35 rad), sin envío físico.
Inferencia caliente mediana 0,436 s; arranque exterior 79,394 s. Caja completa
visible en la cámara. Sesión cerrada: ambos contenedores VLA exited y cero
publicadores de movimiento. No se cambiaron tareas ni umbrales. Siguiente:
adaptar el ejecutor físico a ENTRY410 y resolver entrada al primer punto;
no repetir HOME/READY/ENTRY ni confundir aceptación shadow con agarre probado.
[Ensayo, tiempos, reproducción y evidencia](vla/ENSAYO_READY_ENTRY410_20260914.md).


**Actualización vigente — 2026-09-14: READY→ENTRY410 probado físicamente,
5/5 etapas con éxito según el operador y sus cinco resultados Motion SUCCEED.**
HOME→READY nuevo y READY→ENTRY410 quedan completados para los ensayos comunicados.
Se conserva `force_entry.sh` del operador. Siguiente: lectura fresca y propuestas
VLA task 0 en shadow desde ENTRY; el agarre VLA aún no se ha probado.
[Registro del ensayo, Goal ID y evidencia](vla/ENSAYO_READY_ENTRY410_20260914.md).


**Actualización vigente — 2026-09-14: HOME→READY nuevo probado físicamente,
5/5 etapas con éxito.** El propietario aporta los cinco resultados Motion
`SUCCEED` (state 1101001, status 4) y confirma el ensayo exitoso desde HOME.
Se cierra el pendiente de primera ejecución del acceso
`ready410_h63_access_01..05_forward` para este ensayo. Se registra lentitud:
122 s nominales; duración real no cronometrada. La ejecución fue mediante ROSA
directo con un `force_ready.sh` modificado por el operador; el agente conserva
ese archivo. ENTRY/VLA y el monitor Python no quedan probados por este ensayo.
Esta actualización prevalece sobre los estados históricos de READY pendiente.
[Resultados, cinco Goal ID, alcance y evidencia](vla/ENSAYO_HOME_READY_NUEVO_20260914.md).


Última consolidación: **2026-09-11, Europe/Madrid**. Política obligatoria:
[`AGENTS.md`](../AGENTS.md). Procedimiento de respaldo y reaplicación:
[guía de actualización](guides/CRUZR_REAPLICAR_CAMBIOS_TRAS_ACTUALIZACION.md).

Este índice identifica el **estado deseado vigente**, sus fuentes y cómo
recuperarlo. La [fuente global](PROJECT_SOURCE_OF_TRUTH.md) y las guías enlazadas
conservan las verificaciones e incidencias. Esta consolidación es documental:
no constituye un inventario nuevo en vivo ni demuestra la postura actual.
Las fechas de las evidencias importan. Al cambiar una adaptación, actualizar
su ficha y añadir el evento a la fuente global, sin borrar la historia.

`VERIFICADO` describe sólo la comprobación indicada. `OBSERVADO` puede proceder
del operador. `PENDIENTE` no equivale a instalado ni validado. Una actualización
no convierte automáticamente los ajustes anteriores en requisitos nuevos.

## Orden y alcance

| ID | Adaptación / datos | Destino | Tratamiento tras actualizar |
|---|---|---|---|
| OPS-01 | Registro obligatorio y respaldo ampliado | Repositorio del PC | Conservar fuentes y revisar cobertura antes de actualizar |
| SYS-01 | Firmware, hardware y servicios opcionales | Ambos ordenadores | Redescubrir; conservar perfil del efector real |
| BOOT-01 | Espera preventiva de Control Center | Vision: host + compose | Revisar contrato/binario; aplicar al compose nuevo |
| BOOT-02 | Voz inglesa una vez por encendido | Vision: host + systemd | Reinstalar fuentes/unidad si siguen compatibles |
| BOOT-03 | Vídeo `巡检` durante la espera inicial | Vision: host + contenedor web | Revisar página/recurso; preparar indicación apagada |
| BOOT-04 | Vigilante de self-check bloqueado por caída del monitor | Vision: host + systemd | Revisar firma/contratos CC; reinstalar si sigue la carrera |
| MOT-01 | HOME interno con brazos abiertos, 20 s | Motion: XML dentro del contenedor | Revisar **antes del primer HOME** |
| MOT-02 | PICO→HOME abierto; 4× por defecto | PC + tareas de Motion | Reinstalar cada perfil requerido y su registro |
| ANL-01 | Comparadores y planificador HOME general offline | PC, sólo análisis | Conservar fuentes, dependencias, modelos y evidencia; no se instala en el robot |
| MOT-03 | PICO sólo brazos | Motion: YAML dentro del contenedor | Comparar original/overlay y carga efectiva |
| MOT-04 | Tareas READY/recovery adaptadas a S2 | Motion: XML + task_list | Revisar por tarea; no restaurar task_list entero |
| MOT-05 | HOME original de fábrica como `cruzr/originalhome` | Motion: XML + task_list | Reinstalar si se desea conservar; no sustituye `cruzr/home` |
| PC-01 | Ethernet y Wi-Fi de robot | PC: NetworkManager | Conservar/exportar; redescubrir interfaces |
| PC-02 | Controller 4.7, UI 4.1, XR y udev | PC + PICO | Recuperar versiones/configuración sin autoSTART |
| PC-03 | Credencial SSH privada para los tres scripts migrados | Sólo PC, fuera de Git | Recuperar de copia privada o usar variable de entorno |
| VLA-01 | Paquete VLA y adaptaciones S2 | PC + Motion + Vision | Inferencia/shadow; contenedores detenidos |
| NAV-01 | Mapas, mesas, referencias y geometría | Robot + `config/` del PC | Conservar datos; comprobar vigencia física |
| NAV-02 | Percepción temporal de carga | Vision: configuración de navegación | Conservar original; no activar al restaurar |

La copia de una tarea en la capa escribible de Docker suele sobrevivir a un
reinicio del mismo contenedor, pero **puede desaparecer al recrearlo**, aunque
no cambie la versión del firmware. Los scripts locales tampoco bastan si sus
XML o entradas de `task_list.yaml` no están instalados/cargados en Motion.

## Fichas vigentes

### OPS-01 — Política de registro y respaldo reproducible

- **VERIFICADO local 2026-09-10:** `AGENTS.md` exige documentar todo cambio
  persistente o temporal en robot, PC y PICO durante la misma intervención.
  Este registro y la guía de reaplicación reúnen las adaptaciones conocidas.
- **Fuentes/destinos:** [`AGENTS.md`](../AGENTS.md), este documento, la guía
  enlazada arriba y [`preupgrade_backup_remote.sh`](../scripts/upgrade/preupgrade_backup_remote.sh)
  en el repositorio. El script se copia y ejecuta en cada host sólo al preparar
  un respaldo; no se instaló como servicio del robot.
- **Cambio del respaldo:** añade boot, systemd, overlays, backups de tareas,
  configuraciones dentro de contenedores detenidos, inventario de cambios,
  estado parcial explícito, permisos privados desde el inicio y checksums
  relativos para comprobar la copia externa. No es una imagen de disco.
- **Higiene de Git, 2026-09-10:** los dos paquetes originales
  `cruzr_s2_description/` y `cruzr_s2_description_splint/` son entradas externas
  ignoradas, conservadas completas en disco (130 archivos, aproximadamente
  107 MB). `.gitignore` también cubre credenciales privadas, entornos/cachés
  Python, salidas de colcon y grabaciones ROS. Conservar esos modelos y las
  evidencias fuera de Git para reproducir los análisis; un clon no los incluye.
  El índice previo y los hashes de los modelos están respaldados en
  `../Humanoide-vla-evidence/20260910T122441Z_COMMIT-CLEANUP/`.
- **Reaplicar/verificar:** conservar la carpeta de trabajo, no sólo el commit;
  seguir la guía de respaldo. Cuatro pruebas offline con Docker simulado:
  captura y permisos/checksums, rechazo de sobrescritura, copia fallida,
  nombres nuevos e inventario fallido. Sintaxis Bash y enlaces locales
  comprobados. **PENDIENTE:** primera captura con esta versión en ambos hosts.
- **Backup/reversión:**
  `../Humanoide-vla-evidence/20260910T110924Z_SYSTEM-CHANGE-POLICY/` conserva
  anteriores, fuentes finales y hashes. Los anteriores de AGENTS/README/script
  proceden de HEAD porque estaban limpios al iniciar esta solicitud; los de
  las guías/fuente global preservan el trabajo pendiente previo. Para revertir,
  retirar sólo esta sección/enlaces o restaurar selectivamente el script;
  no sobrescribir documentación posterior. El script anterior tiene menor
  cobertura de respaldo. Ningún servicio ni parámetro del robot fue cambiado.

### PC-03 — Credencial SSH privada del PC

- **Cambio local 2026-09-10:** se retira la contraseña literal de
  `cruzr_blue_workbin_cycle.sh`, `teleoperation/cruzr_pico_to_home_owner.sh` y
  `vla/audit_vla_live_preflight_e6_0g.sh`, todos bajo `scripts/`. Sus ramas
  SSH_ASKPASS usan [`cruzr_ssh_askpass.py`](../scripts/lib/cruzr_ssh_askpass.py).
  No se cambió la contraseña del robot ni se abrió una conexión para migrarla.
- **Prioridad:** `CRUZR_SSH_PASSWORD` no vacío; en su ausencia,
  `CRUZR_SSH_PASSWORD_FILE` o `.secrets/cruzr_ssh_password` en la raíz del repo.
  El archivo debe pertenecer al usuario actual, ser regular, sin enlace
  simbólico ni permisos para grupo/otros y contener una única línea no vacía.
  Un archivo inválido rechaza la autenticación, sin alternativa embebida.
- **Recrear:** recuperar la credencial desde un respaldo privado o escribirla
  en el archivo con un editor local. Directorio `.secrets/` con permisos `700`
  y archivo con `600`; no ponerla en documentación ni argumentos de comandos.
  También puede proporcionarla el entorno existente. `--help` y las pruebas
  locales no necesitan leer la credencial. No ejecutar el helper directamente
  en una terminal registrada: su stdout es la respuesta destinada a SSH.
- **Respaldo/reversión:** durante esta migración se conservó la credencial
  existente en el archivo privado ignorado y se respaldaron los tres scripts
  en `20260910T122441Z_COMMIT-CLEANUP/before-auth/`, dentro del directorio externo
  indicado en OPS-01. Conservar esa copia con acceso restringido. Para cambiar
  la fuente, usar el entorno o el archivo indicado; no reintroducirla en Git.
- **Verificación:** ocho pruebas offline de prioridad, contenido, permisos,
  archivos especiales, ramas reales ASKPASS y ayuda sin credencial.
  **Alcance:** sólo estos tres scripts; no se migraron todos los scripts antiguos
  ni se reescribió el historial de Git. Queda pendiente una migración general
  y decidir la rotación de credenciales ya presentes en el historial.

### SYS-01 — Baseline y servicios opcionales

- **Estado/evidencia:** baseline v0.2.0 documentado en la unidad
  `WAE001UBT60000669`; abrazaderas, `HW_TYPE=cruzr_s2_v1`. Motion
  `192.168.11.2`, Vision `192.168.11.3`. El perfil histórico de manos v4
  `cruzr_s2_v1_sps` no corresponde a estas abrazaderas.
- **Destinos:** `/etc/walker/system`, configuración uDoke de cada host,
  imágenes y políticas de reinicio Docker. `TELE_DEVICE=pico`, `transmit=local`;
  `MC_SCENE` observado vacío, build DAC del SOP no demostrada.
- **Cambios documentados:** plantillas `main.x86`/`main.orin` sin comando y
  MQTT cloud defectuoso detenidos, sin reinicio automático; MQTT local/upilot
  conservados. No confundirlos con todos los servicios MQTT.
- **Reaplicar/verificar:** comparar `docker inspect`, imágenes/digests,
  variables y servicios con la nueva entrega. Sólo reproducir esos workarounds
  si sigue existiendo el problema. Registrar nombres reales, nunca seleccionar
  un contenedor sólo por una IP o un nombre histórico.
- **Backup/reversión:** compose, inspect y políticas anteriores en el respaldo
  de ambos hosts. Reversión selectiva según versión; no restaurar todo el
  compose antiguo. Netdata no saludable y frecuencia GPU discrepante son
  deudas de proveedor, no correcciones locales aplicadas.
- **Detalle:** [fuente global, sección 4](PROJECT_SOURCE_OF_TRUTH.md#4-cambios-persistentes-realizados-en-el-robot).

### BOOT-01 — Espera preventiva de Control Center

- **VERIFICADO 2026-09-10:** evita iniciar CC antes de respuestas funcionales
  de Motion; ampliado a seis cámaras con marcas crecientes. Arranque en frío
  observado con la espera de Motion; no elimina self-check ni HOME del arranque.
- **Fuente → destino:**
  [`cruzr_cc_start_when_ready.py`](../scripts/upgrade/cruzr_cc_start_when_ready.py)
  → Vision `/etc/walker/boot/cruzr_cc_start_when_ready.py`;
  `/home/walker/.config/udoke/walker/compose.yml`, sólo
  `services.system.control_center.command` →
  `python3 /etc/walker/boot/cruzr_cc_start_when_ready.py --start`.
- **Compatibilidad:** v0.2.0, hash del binario CC y contratos de servicios
  comprobados por el script. Una versión distinta exige revisar el código;
  no cambiar sólo el hash esperado para conseguir que pase.
- **Reaplicación/activación:** receta BOOT en la guía; helper
  [`patch_cc_readiness_compose.py`](../scripts/upgrade/patch_cc_readiness_compose.py)
  prepara exclusivamente ese cambio. Activación en encendido supervisado;
  modificar el archivo no demuestra que el contenedor actual use el comando.
- **Verificación:** [`cruzr_boot_ready.sh --check`](../scripts/cruzr_boot_ready.sh)
  durante la primera espera; comprobar identidad/log de CC, respuestas y cámaras.
- **Backup:** `compose.yml.before-cc-ready-20260910T065831Z` junto al compose;
  wrapper anterior en `/etc/walker/boot/`. Rollback selectivo para próximo
  arranque: retirar el comando wrapper sólo tras resolver/revisar la carrera.
  **El guard antiguo permanece deshabilitado.**
- **Detalle/evidencia:** [guía boot](guides/CRUZR_V020_BOOT_GUARD.md),
  `../Humanoide-vla-evidence/20260910T064413Z_BOOT-READONLY/` y
  `20260910T081749Z_BOOT-VOICE/`.

### BOOT-02 — Aviso hablado de arranque

- **VERIFICADO 2026-09-10:** el usuario oyó claramente “Ready to release the
  emergency stop.”; TTS real status4/Success. Una ejecución por boot observada.
- **Fuentes:** [`cruzr_boot_voice.py`](../scripts/upgrade/cruzr_boot_voice.py) en
  Vision `/etc/walker/boot/`; [`cruzr-boot-voice.service`](../scripts/upgrade/cruzr-boot-voice.service)
  en `/etc/systemd/system/`, enabled, Type=simple, User=walker, grupo docker,
  Restart=no. Depende de BOOT-01 y del módulo BOOT-03 en la versión actual.
- **Reaplicar:** receta BOOT; `daemon-reload` y `enable` preparan el siguiente
  arranque, no ejecutar `--watch` como comprobación de instalación.
  ROS 2 para UInt8/paros; ROSA/TTS sólo según contratos comprobados.
- **Verificar/revertir:** `--check` no reproduce voz; `--check --announce`
  es una prueba de audio explícita. Deshabilitar esta unidad retira el aviso;
  conservar el wrapper preventivo. No reiniciar CC para probar el sonido.
- **Estado transitorio:** `/etc/walker/boot/cc_ready_voice_boot_id` identifica
  el boot ya intentado. No copiarlo como configuración al restaurar, ni
  borrarlo para forzar un segundo aviso durante una recuperación.
- **Backup/evidencia:** `/etc/walker/boot/backups/20260910T102219Z_BOOT-VISUAL/`;
  [guía de voz y pantalla](guides/CRUZR_AVISO_VOZ_ARRANQUE.md).

### BOOT-03 — Pantalla con `巡检`

- **VERIFICADO 2026-09-10:** vídeo real `inspection.mp4`, anillo azul con barrido.
  23 pruebas Python, Node y Chromium; captura de pantalla real. **PENDIENTE:**
  próximo encendido completo con voz y vídeo combinados.
- **Fuentes:** [`cruzr_boot_visual.py`](../scripts/upgrade/cruzr_boot_visual.py) y
  [`cruzr-boot-ready.js`](../scripts/upgrade/cruzr-boot-ready.js) →
  Vision `/etc/walker/boot/`; el preparador añade el JS a `index.html` en
  `/usr/share/nginx/html` de `walker-web.web-expression-1`.
- **Contrato:** imagen observada `expression-web:v0.2.20`; index original
  SHA256 `fb294b019cfef37b3e3d9441da099c3b76af8ceb062c7e4cdf121be18cc93566`.
  Recurso nativo servido en `http://127.0.0.1:5000/expression/inspection.mp4`.
  Sólo se superpone a `breath`, otras expresiones tienen prioridad; caduca
  en 12 s sin renovaciones válidas. No modifica la base de fallos.
- **Reaplicar:** `cruzr_boot_voice.py --prepare-display` en Vision, después de
  revisar la imagen/página. Deja la indicación apagada. Un index desconocido
  se rechaza. El navegador cargará el añadido en el próximo arranque; no
  cerrar a la fuerza LoadingScreen, que es el proceso de la sesión kiosk.
- **Verificar/revertir:** `--check --visual` prueba explícita sin voz; se retira
  al perder requisitos. Restaurar selectivamente `index.before.html`/fuentes
  del backup, según la guía. No reiniciar Motion/CC. No restaurar el JSON de
  permiso visual ni la unidad temporal de preview como estado de arranque.
- **Backup/evidencia:** `/etc/walker/boot/backups/20260910T102219Z_BOOT-VISUAL/`,
  `../Humanoide-vla-evidence/20260910T102219Z_BOOT-VISUAL/`.

### BOOT-04 — Vigilante de self-check bloqueado

- **2026-09-18 Europe/Madrid — INSTALADO y habilitado para el próximo arranque;
  detección VERIFICADA en vivo (`--check`: `STUCK=1`) sobre el incidente real.
  Recuperación completa VERIFICADA el mismo día (arranque manual del servicio
  sobre el bloqueo real, hora robot CST): 14:58:47 voz pedir E-stop → 14:59:17
  paro 2/2 → 14:59:30 reinicio sólo CC → 15:00:45 nueva WaitEStopRelease →
  15:00:52 voz lista → liberación humana 15:01:08 → self-check y StartMotion OK,
  `JoystickMode` 15:01:54. Cero comandos de movimiento del vigilante.**
- **Motivo:** [incidente 2026-09-18](incidents/2026-09-18_SELFCHECK_MONITOR_SIGSEGV.md):
  SIGSEGV del proveedor en `self_check_monitor` durante el self-check deja CC
  en `SelfChecking` sin timeout ni StartMotion.
- **Fuentes → destino (Vision):**
  [`cruzr_selfcheck_watchdog.py`](../scripts/upgrade/cruzr_selfcheck_watchdog.py)
  (SHA `d9c8652c…acbd78`) → `/etc/walker/boot/`;
  [`cruzr-selfcheck-watchdog.service`](../scripts/upgrade/cruzr-selfcheck-watchdog.service)
  (SHA `3ba1836d…aca6a`) → `/etc/systemd/system/`, enabled, User=walker,
  grupo docker, Restart=no. Tests: [`test_cruzr_selfcheck_watchdog.py`](../scripts/upgrade/test_cruzr_selfcheck_watchdog.py).
- **Dependencias:** importa BOOT-01/BOOT-02 instalados (`cruzr_cc_start_when_ready.py`
  `19f06f68…`, `cruzr_boot_voice.py` `a76e57ca…`); la receta los verifica por hash.
- **Contrato:** actúa sólo si CC (camino de arranque inicial) lleva ≥120 s en
  `SelfChecking`, sin `selfcheck result` ni `StartMotion`, y
  `walker-system.self_check_monitor-1` arrancó después de entrar en SelfChecking.
  Entonces pide por voz pulsar el E-stop, exige principal=1 y cargador=0 dos
  lecturas seguidas y proceso CC idéntico, reinicia **sólo**
  `walker-system.control_center-1`, espera la nueva `WaitEStopRelease` inicial
  (1/0/0) y anuncia por voz. Una vez por arranque del host
  (`/etc/walker/boot/selfcheck_watchdog_boot_id`, estado transitorio: no copiar).
  Nunca libera paros, llama StartMotion, cambia modos ni mueve. La liberación
  y el HOME interno posteriores siguen siendo decisión del operador.
- **Reaplicar:** [`install_selfcheck_watchdog.sh`](../scripts/upgrade/install_selfcheck_watchdog.sh)
  (tests locales, hashes de dependencias, backup, `enable` sin `start`).
- **Verificar:** en Vision `python3 /etc/walker/boot/cruzr_selfcheck_watchdog.py --check`
  (sólo lectura) y `journalctl -u cruzr-selfcheck-watchdog -b`.
- **Revertir:** `sudo systemctl disable --now cruzr-selfcheck-watchdog.service`,
  borrar los dos archivos y `daemon-reload`. Backups:
  `/etc/walker/boot/backups/20260918T065359Z_BOOT-04/` (instalación inicial,
  `absent.txt`) y `20260918T065433Z_BOOT-04/` (reinstalación idéntica).
- **Tras actualizar CC/self_check_manager:** revisar si el proveedor corrigió la
  carrera o cambió estados/log; si el hash del CC cambia, `--control-snapshot`
  devuelve error y el vigilante no actúa.

### MOT-01 — HOME interno abierto, 20 segundos

- **2026-09-18 — body-first v7 (13,45 s) INSTALADO (12:44 Madrid, E-stop pulsado,
  cargador 0, MetaMove esperado; verificado por hash) por decisión del propietario,
  con ensayo físico supervisado por él. Primer arranque FALLÓ por postura previa
  fuera de HOME (hombro izq. fuera de límite; no por la estructura v7). Ensayo
  supervisado desde brazos al frente/cuerpo flexionado VERIFICADO 19:01 CST: SUCCEED
  15,06 s, 0 avisos de límite, seguimiento máx. 0,012 rad, sin fallos. Ver
  [incidente](incidents/2026-09-18_HOME_V7_ARRANQUE_HOMBRO_FUERA_LIMITE.md).
  Arranque completo con v7 desde HOME VERIFICADO 19:13 CST: self-check OK,
  StartMotion/LimbMotion succ en 15,1 s, `AutoTaskMode`, 11 MetaMove correctos,
  final |q| ≤ 0,00288 rad. Captura (3.635 muestras): brazos error ≤ 0,0052 rad,
  vmax 0,17 rad/s, 0 fallos; muestras deshabilitadas sólo antes de StartMotion.
  Cabeza: salto desde la postura baja de arranque (−0,694, fuera de límite blando)
  con 118 consignas rechazadas, error 0,047 rad y pico 1,19 rad/s; mismo tramo
  que v4/v5, no introducido por v7. Evidencia `../Humanoide-vla-evidence/20260918_V7_BOOT_HOME_TRACE/`.**
  **Instalador (18-09, 19:18 CST):** `--install` exige además un registro
  `--measure-home` (E-stop liberado, 20D ≤ 0,02 rad, motores habilitados) del mismo
  boot y log de `robot_app`, < 30 min y sin `BTree task` posterior
  (`../Humanoide-vla-evidence/HOME_POSTURE_LATEST.json`, estado transitorio: no
  restaurar). Procedimiento en [la guía body-first](teleoperation/CRUZR_HOME_CUERPO_PRIMERO.md).
  Sustituye a v5-18s
  (`adc24aba…`, backup `/etc/walker/trajectory-overlays/20260918T104358.711252Z_home_body_first_v5/home.before.xml`;
  evidencia `../Humanoide-vla-evidence/20260918T104425.242019Z_INTERNAL-HOME-CHANGE/`).
  Fuente [`cruzr_internal_home_body_first_v7_13s.xml`](../scripts/teleoperation/tasks/cruzr_internal_home_body_first_v7_13s.xml)
  SHA `1e6e2fb7ddc598dc3793d093c283c82063507df0e53b70a18e161cab883a6f03`.
  Cambios frente a v5-18s: (1) cada brazo ejecuta en secuencia codos −0,03 (1 s) y
  apertura −0,2 (1,8 s) **en paralelo** con cabeza/elevador/cintura (3,75 s,
  `Sequence` dentro de `Parallel`, patrón usado por 22 tareas del proveedor);
  (2) bajada 7 s (antes 10 s). Cierre 2,7 s. El pico de la bajada no supera el pico
  ya ejecutado desde el mismo inicio por el HOME directo de fábrica o por v4 (test).
  Barrido `--v7` (cuerpo→brazos, brazos→cuerpo, diagonal): mínimo PICO 133,1 mm
  (cota 68,9), brazos abajo y `separate_right` 181,6 mm. Evidencia
  `../Humanoide-vla-evidence/20260918_V7_AUDIT/`. Candidata intermedia v6 (16,45 s,
  bajada 10 s) sólo en repo: `tasks/cruzr_internal_home_body_first_v6_16s_CANDIDATE.xml`
  (`1472de86…`). La v5-18s sigue reconocida por el contrato workbin para revertir.
- **2026-09-18 — body-first v5 (18,25 s) INSTALADO y luego SUSTITUIDO por v7 (12:12 Madrid, E-stop pulsado,
  cargador 0, MetaMove esperado); verificado por hash. Primer arranque y ensayo
  físico PENDIENTES.** Sustituye a la v5 de 21,5 s (`212f3ad8…`, instalada 11:52 y
  nunca ejecutada), que a su vez sustituyó a la v4 (`e3d06564…`).
  Backups: v4 `/etc/walker/trajectory-overlays/20260918T095221.811178Z_home_body_first_v5/home.before.xml`;
  v5-21s `/etc/walker/trajectory-overlays/20260918T101211.525540Z_home_body_first_v5/home.before.xml`.
  Evidencia `../Humanoide-vla-evidence/20260918T095250.040820Z_INTERNAL-HOME-CHANGE/` y
  `20260918T101234.670337Z_INTERNAL-HOME-CHANGE/`. Revertir: reinstalar el `home.before.xml`
  elegido bajo E-stop.
  Motivo: [incidente codo fuera de límite](incidents/2026-09-18_HOME_ARRANQUE_CODO_FUERA_LIMITE.md)
  y peticiones del propietario (abrir la mitad, acelerar). Cambios frente a v4:
  (1) ambos codos `delta −0,03 rad` en paralelo con cabeza/elevador/cintura
  (3,75 s, threshold 5); (2) apertura mitad: `delta` roll −0,2 en 1,8 s (v4 −0,4 en
  2,5 s); (3) bajada 10 s con roll −0,3 (v4 −0,6); (4) cierre 2,7 s (v4 3,75 s).
  Total 18,25 s. Velocidad/aceleración pico quintic de los tramos fijos ≤ v4
  (comprobado en test); la bajada conserva los 10 s de v4.
  Fuente [`cruzr_internal_home_body_first_v5_18s.xml`](../scripts/teleoperation/tasks/cruzr_internal_home_body_first_v5_18s.xml)
  SHA `adc24aba387ceb94a229db14d28668a04e7b9a64432ffa9989dd7145cc9cbf4c`,
  generador `cruzr_internal_home_body_first.py` (v4 byte-idéntico).
  **Barrido offline** [`audit_body_first_v5_opening.py`](../scripts/teleoperation/audit_body_first_v5_opening.py),
  501 muestras, abrazadera ↔ enlaces que no son de su brazo: desde PICO mínimo
  133,1 mm (v4 164,3; cota condicional 68,9 vs 101,9); brazos abajo 171,9 mm;
  `separate_right` real 181,6 mm. Calibración: HOME directo de fábrica 2,7–10,2 mm
  desde PICO (coincide con el acercamiento real). Sólo geometría archivada; sin
  seguimiento, frenado, carga ni obstáculos. Evidencia
  `../Humanoide-vla-evidence/20260918_V5_18S_AUDIT/` (y `20260918_V5_HALF_OPENING_AUDIT/`, 21,5 s).
  [`cruzr_install_internal_home_body_first.py`](../scripts/teleoperation/cruzr_install_internal_home_body_first.py)
  instala v5-18s desde open-v3, v4 o v5-21s; [`cruzr_blue_workbin_cycle.sh`](../scripts/cruzr_blue_workbin_cycle.sh)
  reconoce `body-first-v5-18s`. Tests body-first y contrato workbin pasan.
  **Norma operativa:** no pulsar E-stop ni apagar con los brazos fuera de HOME;
  terminar cada escenario con `cruzr/home`. v5 sólo cubre los codos.

- **VERIFICADO instalado y proceso recargado 2026-09-10; ensayo físico PENDIENTE.**
  Sustituye `cruzr/home`: apertura relativa, bajar abiertos, cuerpo HOME y
  cierre con brazos abajo. No es una recuperación universal tras contacto.
- **Fuente:** [`cruzr_internal_home_open_v3_20s.xml`](../scripts/teleoperation/tasks/cruzr_internal_home_open_v3_20s.xml).
  Motion, `walker-motion.manipulation_robot_app-1`:
  `/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config/cruzr/home.xml`.
  SHA256 instalado `05174d2b4cf003b9b1c5274cd445b0d4faefe4276c5fbe8e59e68e6b64ee8cbe`.
- **Reaplicación:** [`cruzr_install_internal_home.py`](../scripts/teleoperation/cruzr_install_internal_home.py)
  `--check` local → `--preflight` → `--install`. `--reload` es una operación
  separada que reinicia manipulación. Requiere brazos abajo/vacíos, paro
  mantenido y contrato MetaMove exacto; seguir [su guía](teleoperation/CRUZR_HOME_INTERNO_APERTURA.md).
- **Verificación:** hash de XML y MetaMove, registro de carga e instancia del
  proceso; luego ensayo físico supervisado independiente. No liberar el paro
  por haber terminado una copia o recarga.
- **Integración PC corregida 10-09-2026:** conservar también
  [`cruzr_blue_workbin_cycle.sh`](../scripts/cruzr_blue_workbin_cycle.sh) y
  [`audit_vla_live_preflight_e6_0g.sh`](../scripts/vla/audit_vla_live_preflight_e6_0g.sh).
  El contrato reconoce este HOME exacto y exige MetaMove exacto; un hash
  desconocido se rechaza sin diagnosticar automáticamente un fallo de arranque.
  Seis regresiones nuevas y cinco previas pasan; preflight PICO4× completo
  verificado en vivo con cero movimientos. Backup PC y log:
  `../Humanoide-vla-evidence/20260910T114627Z_HOME-PREFLIGHT-CONTRACT/`.
  No requiere instalación/recarga remota. Revertir sólo estos scripts devuelve
  el rechazo local; no restaura el HOME antiguo del robot.
- **Backup:** `/etc/walker/trajectory-overlays/20260910T100528.529307Z_home_open_v3/`.
  Restaurar `home.before.xml` devuelve el HOME directo que causó acercamiento
  al cuerpo: **no es un rollback automático seguro**.

### MOT-02 — Ejecutor PICO→HOME abierto

- **Ensayo H02, 11-09-2026 — VERIFICADO físicamente en `pico_body_zero`,
  abrazaderas vacías, perfil4× de20s.** XML
  `config/cruzr/pico_to_home_open_v2_4x.xml` del gestor Motion,
  SHA `6dd482a70e8ec55e02f125eb442b483a12a7c591959e72965214fcc9e02027dc`.
  Instalación exacta, registro anterior al proceso y preflight comprobados.
  Un objetivo SUCCEED/4; 2.103 muestras válidas, ningún fault/deshabilitado,
  HOME final0,00297209rad máximo/velocidad0. Operador: «resultado ok, suave y sin
  contacto, libres, sigamos». Sin cambios de XML, ejecutor, modo o protección;
  no instalación/recarga/reinicio. No se valida cuerpo flexionado o retorno
  general, otros perfiles/cargas ni frenado. Receta, destino completo, alcance,
  límites y siguiente captura: [H02](teleoperation/CRUZR_HOME_ENSAYOS_SUPERVISADOS.md).
  Evidencia y backups documentales ANL-01:
  `../Humanoide-vla-evidence/20260911T084247Z_H02-PICO-SUPERVISED/`.
  Sin rollback remoto; conservar evidencia, restaurar documentos selectivamente
  desde `before/` si fuera necesario sin borrar trabajo previo/posterior.

- **Mejora PC 10-09-2026:** salida sin movimiento `ALREADY_HOME_MEASURED`
  después de preflight y dos lecturas nuevas sanas; tolerancia HOME0,005rad y
  velocidad≤0,002rad/s.22pruebas pasan. No reduce tiempos ni apertura del XML.
  Backup selectivo del ejecutor/pruebas/docs en
  `../Humanoide-vla-evidence/20260910T120838Z_ADAPTIVE-HOME/before/`;
  restaurarlo sólo si se quiere retirar esta salida, preservando cambios posteriores.
  No requiere instalación ni recarga remota. Prueba real de esta salida pendiente:
  la lectura actual encontró principal1/servo0 y no produjo JointState utilizable.
- **OBSERVADO:** el usuario confirmó que open_v2 original funciona. **VERIFICADO**
  perfiles locales 1×/3×/4×; 4× instalado por el usuario y comprobado por hash.
  La deuda de ensayo4× para `pico_body_zero` queda cubierta por H02; otras
  referencias/condiciones permanecen fuera de ese resultado.
- **Fuente/receta:** [`cruzr_pico_to_home_owner.sh`](../scripts/teleoperation/cruzr_pico_to_home_owner.sh)
  y [guía open_v2](teleoperation/CRUZR_PICO_HOME_OPEN_V2.md). Por defecto 4×,
  20 s; 1×=80 s y 3×=26,666 s. Cada velocidad tiene XML/tarea propios.
- **Destino:** directorio `config/cruzr/` y `config/task_list.yaml` del gestor
  de tareas indicado en MOT-01. Tareas `cruzr/pico_to_home_open_v2`,
  `cruzr/pico_to_home_open_v2_3x`, `cruzr/pico_to_home_open_v2_4x`.
  No demuestra que 3× esté instalado por existir en el repositorio.
- **Reaplicar/verificar:** `--check --speed 4` local; `--install --speed 4`
  con requisitos de su guía. `--reload` separado. `--preflight --speed 4`
  sólo es válido en una referencia PICO reconocida con Motion operativo;
  no debe pasar desde brazos abajo. No enviar `--run` para verificar copia.
- **Backup/reversión:** `/home/walker/cruzr-owner-backups/`, manifiesto por
  operación con XML/task_list anterior. Retirar sólo esa entrada/archivo,
  preservando tareas posteriores. No recuperar la antigua ruta directa.

### ANL-01 — Comparación y planificación offline de geometría y tiempos

- **Preparador desde postura actual, 11-09-2026 Europe/Madrid — IMPLEMENTADO
  Y PROBADO; recuperación física H03 NO resuelta.** Nuevo PC
  `scripts/teleoperation/cruzr_prepare_recovery.py` y `test_prepare_recovery.py`.
  Usa captura pasiva existente y dos JointState; evita dependencia de PICO y
  conserva cada articulación medida. Sin --run/transporte de movimiento o
  modificación de robot/protecciones. Prueba live inicial detectó signos de
  motores distintos del URDF; descartado su falso START_OUTSIDE_LIMITS.
  Corrección: sólo JointState canónico para planificar, motores para salud.
  Diez pruebas pasan; live corregido101muestras válidas, control libre/paros0/0,
  START_GEOMETRY_REJECTED/54avisos. No significa contacto físico ni permiso.
  Dependencias: venv general-home existente, ninguna instalación nueva.
  Fuente reproducible, aplicación sólo PC, verificación y límites en
  [recuperación sin teleoperación](teleoperation/CRUZR_RECUPERACION_SIN_TELEOPERACION.md).
  Docs global/PICO/ensayos/README/índice actualizados: el operador no dispone
  de teleoperación; la petición de preparar PICO queda retirada.
  Fuentes anteriores/posteriores, hashes, pruebas, lecturas y resultados:
  `../Humanoide-vla-evidence/20260911T092355Z_RECOVERY-FROM-CURRENT/`.
  Reversión: retirar esos dos archivos nuevos/guía y restaurar selectivamente
  sus notas desde `before/`, preservando otros cambios. No existe rollback
  remoto ni tarea instalada/cargada; no restaurar el prototipo de signos erróneos.

- **H03, 11-09-2026 Europe/Madrid — lectura y análisis, SIN movimiento.**
  Capturada postura asimétrica real, sana e inmóvil; no es una referencia PICO.
  Candidato de HOME interno: mínimo nominal36,599mm abrazadera derecha–codo,
  sin separación demostrada al aplicar5° independientes (resto−8,330mm).
  Modelo completo START_GEOMETRY_REJECTED/54avisos; no contactos reales
  demostrados. No se alteran márgenes, geometría, restricciones o ejecutores.
  Cambios PC: fuentes global/PICO, guía de ensayos e índice; ninguna dependencia
  nueva. Consultas robot de lectura, sin cambio remoto que activar/restaurar.
  Evidencia, programa PC/argumentos, fuentes, resultados y backups documentales:
  `../Humanoide-vla-evidence/20260911T085902Z_H03-ASYMMETRIC-READONLY/`.
  Reproducción, alcance y recuperación solicitada:
  [H03](teleoperation/CRUZR_HOME_ENSAYOS_SUPERVISADOS.md).
  Reversión: documentos selectivos desde `before/`, sin borrar otros cambios.

- **H02, 11-09-2026:** segundo ensayo supervisado registrado, ahora desde
  `pico_body_zero` con perfil4×. Resultado y reproducción en MOT-02 y
  [ensayos supervisados](teleoperation/CRUZR_HOME_ENSAYOS_SUPERVISADOS.md).
  Cambios PC: guía de ensayos, fuente global/PICO, guía de captura e índice.
  Ningún cambio de dependencias, geometría, criterios de aceptación o ejecutor.
  Backup previo/fuentes posteriores/hashes y evidencia:
  `../Humanoide-vla-evidence/20260911T084247Z_H02-PICO-SUPERVISED/`.
  La captura está validada para este movimiento; no mide una cota de parada.

- **Ensayo H01, 11-09-2026 Europe/Madrid — EJECUTADO; operador confirma
  «suave sin contacto». H01 cerrado para el caso ensayado.** Una acción `cruzr/home` sobre Motion `.11.2`, contenedor
  `walker-motion.manipulation_robot_app-1`, v0.2.0. Desde HOME medido, abrazaderas
  vacías y condiciones confirmadas, apertura/cierre de brazos bajos con XML
  `/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config/cruzr/home.xml`
  SHA `05174d2b4cf003b9b1c5274cd445b0d4faefe4276c5fbe8e59e68e6b64ee8cbe`.
  Fuente intacta `scripts/teleoperation/tasks/cruzr_internal_home_open_v3_20s.xml`.
  Instalado y ejecutado; Motion SUCCEED/4, HOME final 0,00278034 rad máximo,
  velocidad0; 2.103 muestras válidas, ningún fault/deshabilitado. No frenado
  medido ni aprobación general. Captura pasiva validada durante movimiento.
  Sin instalación, recarga, reinicio ni modificación persistente remota.
  Dependencias y modelo sin cambios; no hay restauración remota pendiente.
  Antes del envío se corrigió un lector auxiliar YAML tras abortar con cero
  órdenes; evidencia fallida preservada. Fuente reproducible, controles previos,
  comando exacto, alcance y reanudación en
  [CRUZR_HOME_ENSAYOS_SUPERVISADOS.md](teleoperation/CRUZR_HOME_ENSAYOS_SUPERVISADOS.md).
  Cambios PC: ese documento y actualización de índice/SOT global/PICO/captura.
  Cierre observacional posterior: «suave sin contacto», sin nuevas órdenes.
  Backup y registro de esa confirmación:
  `../Humanoide-vla-evidence/20260911T084056Z_H01-OPERATOR-CONFIRMATION/`.
  Evidencia, fuentes, comandos, hashes y backup de documentos:
  `../Humanoide-vla-evidence/20260911T082510Z_SUPERVISED-HOME-PREPARATION/`.
  Reversión documental: restauración selectiva desde `before/`, preservando
  modificaciones anteriores y posteriores; conservar el registro del ensayo.
  Después de firmware, repetir descubrimiento/compatibilidad y gates; no
  reproducir automáticamente el movimiento ni tomar esta evidencia por vigente.

- **Interfaces y bucle nativo, 11-09-2026 Europe/Madrid — VERIFICADO offline;
  punto 1 de calificación NO CERRADO.** Destino PC `scripts/teleoperation/`:
  modificación de `audit_home_interfaces.py` y `test_home_interfaces.py`;
  nuevos `general_home/contact_witnesses.py`, `general_home/native_collision_policy.py`,
  `audit_home_interface_sweeps.py`, `audit_native_collision_policy.py`,
  `test_interface_sweeps.py`, `test_native_collision_policy.py`.
  Objetivo: comprobar si interfaces de reposo justifican excepciones generales.
  Corregidos puntos FCL fuera de la intersección; reconstrucción sobre ambos
  triángulos a 10 nm. Contraejemplos CAD: 8 en dominio URDF y 4 en ±0,5 rad;
  primeras cifras 13/9 DESCARTADAS por testigos sin verificar. 64 pruebas pasan,
  ninguna omitida. El modelo mantiene 45 formas/982 pares/2 mm/54 rechazos.
  Bucle revisado de `librobot.so` SHA `7322b075…` interpreta grupos sintéticos,
  distancia sustituida y llamadas interceptadas; no es el contrato de control
  activo ni autoriza excepciones de CAD. Datos mecánicos pendientes: zonas
  permitidas por interfaz y dominio, o modelo de colisión validado equivalente.
  Dependencias: venv ANL-01 existente; ninguna instalación/servicio/permiso nuevo.
  Aplicación/activación: sólo comandos PC de la
  [receta versionada](teleoperation/CRUZR_HOME_GEOMETRIA_Y_MOTION.md#resultado-de-la-revisión-de-interfaces-11-09-2026).
  Se descubrieron contenedores y archivaron bibliotecas desde Motion mediante
  lecturas; manifiesto identifica host, contenedor, ruta, fecha y SHA completo.
  No movimiento, recarga, reinicio, cambio de modo ni mutación remota.
  Evidencia/backup de trabajo previo, fuentes posteriores y hashes:
  `../Humanoide-vla-evidence/20260911T075508Z_HOME-INTERFACE-CLOSURE/`.
  Verificación: cinco suites, auditoría de interfaces, dos barridos y traza nativa.
  Reversión: restaurar selectivamente los dos archivos modificados de `before/`,
  retirar los seis nuevos si no tienen consumidores y actualizar documentos,
  preservando trabajo previo/posterior. La reversión recuperaría testigos FCL
  no verificados: no usarlos como zonas de exclusión. No hay rollback remoto.
  Tras firmware/CAD nuevo, volver a archivar/revisar: nunca ampliar la lista de
  hashes para aceptar una build sin inspección. No instalar las bibliotecas
  privadas ni estos auditores sobre Motion.

- **Interfaces y prismas del elevador, 11-09-2026 Europe/Madrid — VERIFICADO offline:**
  objetivo: conservar huecos entre componentes sin perder volumen del CAD e
  identificar la causa de cada rechazo. Destino PC, `scripts/teleoperation/`:
  modificación de `general_home/geometry.py`; nuevos `general_home/prism_enclosure.py`,
  `audit_home_interfaces.py`, `test_prism_enclosure.py`, `test_home_interfaces.py`.
  Venv existente, sin dependencias/servicios/permisos nuevos. No hay instalación
  ni activación en Motion. Cinco prismas abiertos reconocidos en el tercer tramo
  del elevador; envolventes generales11→10. Conserva45formas/982pares/margen2mm,
  sin exenciones nuevas. Persisten54avisos en las tres referencias;52pruebas pasan.
  Diagnóstico diferencia superficies originales de volumen/margen y limita
  explícitamente sus testigos; no autoriza trayectorias ni mejoras de velocidad.
  [Receta versionada, resultados y límites](teleoperation/CRUZR_HOME_GEOMETRIA_Y_MOTION.md#refinamiento-del-elevador-y-diagnóstico-de-interfaces-11-09-2026).
  Aplicación: fuentes PC y comandos offline de la receta. Verificación: auditoría
  completa y tres suites, fuentes/CAD con hashes antes/después. Evidencia,
  backups de archivos previamente no incluidos en commit y fuentes posteriores:
  `../Humanoide-vla-evidence/20260911T073642Z_HOME-INTERFACE-REFINEMENT/`.
  Reversión: restaurar sólo el cambio de `geometry.py` desde `before/`, retirar
  los cuatro archivos nuevos si ya no tienen consumidores y ajustar documentos,
  preservando trabajo previo/posterior. No hay rollback remoto: no se conectó
  al robot. Tras firmware/CAD nuevos, volver a auditar y comparar hashes;
  estos resultados no se heredan a otra geometría ni constituyen calibración.

- **Cobertura rígida muñeca/útil, 11-09-2026 Europe/Madrid — VERIFICADA offline:**
  objetivo: comprobar unión de formas nativas y conservar todo el CAD. Destino
  sólo PC, bajo `scripts/teleoperation/`: nuevos `audit_wrist_clamp_union.py`,
  `general_home/native_arm_frames.py`, `general_home/union_coverage.py`,
  `test_wrist_clamp_union.py`, `render_wrist_clamp_review.py` y
  `general_home/wrist_clamp_review.html`. Venv ANL-01 existente, sin dependencias,
  servicios, permisos o activación nuevos. Sin instalación/recarga remota.
  Ocho pruebas pasan; cobertura de frontera/volumen en CAD completa con complemento
  conservador. Formas nativas solas dejan vértices fuera hasta8,64mm. No cambia
  `RobotGeometry`, pares, márgenes, XML ni calificación física. Visor Chromium
  comprobado en ambos lados y tamaños de pantalla, sin errores JS/WebGL.
  [Receta reproducible y límites](teleoperation/CRUZR_HOME_GEOMETRIA_Y_MOTION.md#unión-muñeca-y-abrazadera-11-09-2026).
  Lectura remota y copias privadas de configuración/bibliotecas; ninguna mutación
  ni movimiento. Modelo nominal de archivos contrastado; memoria calibrada y
  montaje físico PENDIENTES. Evidencia/backups/fuentes completas/checksums:
  `../Humanoide-vla-evidence/20260911T070352Z_WRIST-CLAMP-UNION/`.
  Aplicación: ejecutar auditor y renderizador con archivos privados según receta;
  no copiar el complemento a Motion. Reversión: retirar sólo esos seis archivos
  nuevos y su documentación, preservando cambios previos/posteriores; `before/`
  contiene los documentos previos. No hay rollback remoto. Después de firmware,
  volver a archivar configuración/URDF/bibliotecas y revisar cambios; el emulador
  rechaza hashes desconocidos. No ampliar hashes permitidos sin auditar la build.

- **Auditoría nativa, 11-09-2026 Europe/Madrid — VERIFICADA offline:**
  objetivo: contrastar interfaces del CAD con formas del proveedor antes de
  sustituir geometría. Fuentes nuevas PC bajo `scripts/teleoperation/`:
  `audit_native_collision_geometry.py`, `general_home/native_geometry.py` y
  `test_native_geometry.py`. Sin dependencias nuevas: venv ANL-01 existente.
  No instalación/activación remota; el comando trabaja sólo con archivos locales.
  Cinco pruebas pasan, incluida extracción de tres bibliotecas con hashes fijados
  y comparación de constantes de abrazadera repetidas. La S2Clamp aislada deja
  vértices del CAD fuera44,396mm L/44,395mm R bajo correspondencia URDF y anclaje
  supuesto; falta la unión muñeca+abrazadera y la selección/anclaje reales.
  No cambia modelo operativo, pares, márgenes, XML ni aprobaciones físicas.
  [Receta, hashes runtime y límites](teleoperation/CRUZR_HOME_GEOMETRIA_Y_MOTION.md#extracción-de-las-formas-nativas-11-09-2026).
  Evidencia privada/backup/fuentes posteriores/checksums:
  `../Humanoide-vla-evidence/20260911T063949Z_NATIVE-COLLISION-INTERFACES/`.
  Reversión: retirar sólo esos tres archivos nuevos y sus entradas documentales,
  conservando cambios ajenos/posteriores; `before/` guarda los documentos previos.
  No hay rollback remoto. Tras firmware, copiar bibliotecas de nuevo y contrastar
  hashes; el auditor rechaza builds no revisadas. No cambiar hashes para forzar
  aceptación ni reinstalar defaults extraídos sobre configuración activa.

- **Corrección del lector, 11-09-2026 — VERIFICADA en HOME real:**
  `general_home/passive_trace_remote.py` usa ahora JSON nativo multilínea;
  `--print-compact` produce texto no JSON y se retira. Enmarca objetos antes
  de parsear, evitando reparsar cada línea; termina un objeto en curso durante
  un máximo de0,5s al cierre y rechaza truncados/estancados. Quince pruebas
  de `test_home_motion_trace.py` pasan, con subprocesses ficticios de corte y
  timeout. Captura real en HOME:252 muestras articulares, ambos paros0, sin
  errores de lectura/análisis; hueco máximo22,875ms. La captura previa del
  arranque falló y no acredita seguimiento o frenado. Se conservan los intentos.
  Destino sólo PC, sin nuevas dependencias ni instalaciones/configuración
  remotas. El arranque CC llegó a HOME tras liberación humana supervisada,
  sin comandos de movimiento del agente; confirmación visual final pendiente.
  Fuentes, hashes, backup/rollback selectivo en
  `../Humanoide-vla-evidence/20260911T062619Z_BOOT-AFTER-CONFIRMATION/`:
  restaurar sólo lector/pruebas desde `before/` si se retira la corrección;
  las versiones anteriores no sirven para medir movimiento nativo. Preservar
  documentos históricos y cambios posteriores. No hay rollback remoto.
  [Receta actualizada](teleoperation/CRUZR_HOME_CAPTURA_Y_PROGRESO_INDEPENDIENTE.md).
- **Ampliación 11-09-2026, Europe/Madrid — VERIFICADA local y lectura de paros;
  ejecución física PENDIENTE.** Objetivo: comprobar progreso independiente de
  ejes y recoger evidencia sin mover. Fuentes PC: `cruzr_plan_home.py`,
  `general_home/planner.py`, `capture_home_motion_trace.py`,
  `analyze_home_motion_trace.py`, `general_home/passive_trace_remote.py`,
  `general_home/trace_analysis.py` y pruebas `test_general_home.py` /
  `test_home_motion_trace.py`, todas bajo `scripts/teleoperation/`.
  [Receta y alcance](teleoperation/CRUZR_HOME_CAPTURA_Y_PROGRESO_INDEPENDIENTE.md).
- **Destino/dependencias/activación:** sólo archivos PC; no hay nuevas
  dependencias, cambios de permisos de sistema, servicios o autoarranque.
  Planificador usa el venv previo. Lector/analizador usan stdlib; captura
  requiere SSH privado PC-03 y contenedores descubiertos con ROSA/ROS 2.
  El lector se transmite por stdin a Python del host Motion y crea únicamente
  suscripciones temporales, limitadas dentro de cada contenedor. Sin instalación
  remota ni acoplamiento a los mandos. Capturar no inicia ni detiene acciones.
- **Verificación y runtime observado:** 90 pruebas offline pasan; auditoría
  completa conserva 54 conflictos por referencia y once envolventes. Captura
  de ocho segundos: principal `1`, servo `0`, sin muestras articulares; rechazo
  correcto, no se acredita seguimiento/parada. Primer intento ROSA en paros
  falló; corregido a ROS 2 y preservada evidencia de ambos intentos.
  Control Center de este arranque llegó a `WaitEStopRelease`. Se copiaron nueve
  archivos runtime; el perfil JSON/MetaClamp deshabilita autocolisión/anomalías
  y no se usó como adaptador. Sin movimiento, cambio de modo, reinicio, recarga,
  rearme, instalación o modificación de configuración remota. MOT-01/MOT-02
  siguen intactos; no hay nuevo ejecutor físico general instalado/cargado/probado.
- **Versiones, backup, reversión y firmware:**
  `../Humanoide-vla-evidence/20260911T054510Z_GENERAL-HOME-COMPLETION/` contiene
  `before/`, `before.sha256.json`, fuentes posteriores con
  `after.sha256.json`, `runtime-manifest-complete.json` y pruebas/capturas.
  Los hashes de fuentes locales incluyen el trabajo sin commit. Retirar
  selectivamente los cinco archivos nuevos de captura/análisis/pruebas y
  restaurar sólo los cambios de esta ampliación en planificador/docs desde
  `before/`, preservando todo cambio ajeno/posterior. No hay rollback remoto;
  los lectores caducan solos y no son servicios. Tras firmware, repetir
  descubrimiento, contrastar `.msg`, IDs, significado de `cmd_pos`, clientes
  y formatos con una captura pasiva antes de interpretar datos nuevos.
  Conservar runtime/CAD/evidencia privada fuera de Git. No reutilizar un
  informe como autorización ni confundir captura con mecanismo de parada.
- **Ampliación 10-09-2026, Europe/Madrid — VERIFICADA offline; ejecución física
  PENDIENTE:** corrección topológica exacta de dos piezas y unión numérica acotada
  a 10 nm en otras cinco, conservando todos los triángulos y descontando el error
  de las distancias. Once envolventes restantes, 54 pares de conflicto/margen
  conservados por referencia (30 invariantes condicionados y 24 móviles).
  Nuevo visor `render_home_geometry_review.py`/`general_home/geometry_review.html`.
  `audit_motion_interpolation.py` y `general_home/native_spline.py` contrastan
  1.312 casos del binario numérico real mediante emulación, sin `dlopen` ni ROS;
  `audit_home_runtime_contract.py` registra límites y conversiones de marcos
  en archivos archivados. Nueva temporización opcional offline `cubic-rest`.
- **Destino/instalación de esta ampliación:** sólo fuentes y documentación del
  PC y `unicorn==2.1.4` en `.venv/general-home`, fijado en `requirements.txt`.
  Son nueve dependencias fijadas en total. No se modifica Python del sistema,
  SDK/CAD original, MOT-01/MOT-02 ni ningún archivo del robot. Las consultas SSH
  copiaron configuración/bibliotecas a evidencia privada por Wi-Fi. Paro leído
  en `1`; suscripción de actuadores sin muestra y consultas finales con timeout
  SSH. No se ejecutó movimiento, cambio de modo, recarga ni reinicio.
- **Verificación de esta ampliación:** 37 pruebas del paquete + 38 regresiones
  pasan. Auditoría numérica: error máximo 2,67e-15 rad, pero no prueba de despacho,
  seguimiento, frenado ni estabilidad. Visor comprobado en Chrome: vista de
  robot completo, selección HOME/muñeca y cambio de geometría, sin errores WebGL.
  [Resultado completo y recetas](teleoperation/CRUZR_HOME_GEOMETRIA_Y_MOTION.md).
- **Backup/rollback/firmware:**
  `../Humanoide-vla-evidence/20260910T142312Z_HOME-GEOMETRY-MOTION-QUALIFICATION/`,
  `before/` y `before.sha256.json`, runtime copiado con manifiestos, auditorías,
  HTML privado y `verification-final.json`. Para retirar sólo esta ampliación,
  restaurar selectivamente los archivos existentes desde `before/`, retirar
  los tres auditores/visor y módulos nuevos de esta ampliación y recrear el venv
  con los requisitos anteriores; preservar el planificador previo y cambios
  posteriores. No hay rollback remoto. Tras firmware, volver a copiar/auditar
  configuraciones, marcos, símbolos y hash del interpolador: un hash distinto
  se rechaza. Nunca ampliar la lista de hashes sin revisar/emular el nuevo código.
  Conservar CAD, bibliotecas copiadas y HTML fuera de Git en backup privado.
- **Planificador general implementado, VERIFICADO offline 10-09-2026,
  Europe/Madrid; integración física PENDIENTE.** Objetivo: buscar desde una
  postura20D asimétrica, sin forzar PICO ni una apertura fija. Fuentes:
  [`cruzr_plan_home.py`](../scripts/teleoperation/cruzr_plan_home.py),
  `scripts/teleoperation/general_home/`, `test_general_home.py` y los dos
  ejemplos `config/examples/cruzr_general_home_*.example.json`.
- **Destino y dependencias PC:** nuevo entorno aislado
  `/home/lacuna/proyectos/Robots/Humanoide/.venv/general-home`, Python3.12.3;
  Cython3.3.0, networkx3.6.1, NumPy2.5.3, python-fcl0.7.0.11, PyYAML6.0.3,
  rtree1.4.1, SciPy1.18.1 y trimesh5.1.0. Versiones fijadas y receta reproducible
  de venv/pip en [README](../scripts/teleoperation/general_home/README.md).
  Usa el paquete original splint local, ignorado por Git, sin modificarlo.
  No altera Python del sistema ni instala paquetes en Motion/Vision.
- **Verificación/estado:**28pruebas funcionales y38regresiones previas pasan;
  auditoría de45geometrías/982pares
  internos. Conserva ocho pares rígidos fuera del chequeo interno, mantiene sus
  piezas contra el resto. El modelo devuelve54conflictos de geometría/margen
  en cada referenciaHOME/PICO, con18envolventes de mallas abiertas. La escena
  sintética da73conflictos enPICO; no representa el taller. Se rechaza la
  planificación desde esa entrada. No son contactos físicos demostrados.
  Los informes tienen hashes completos de código/entradas/modelo y versiones.
- **Activación pendiente:** no existe exportación de trayectoria/ejecutor
  físico general. Resolver modelo y montaje, Motion/interpolación y supervisor,
  dinámica/estabilidad/parada, escena actual e integración HOME del arranque.
  No cambia MOT-01/MOT-02 ni el tiempo operativo20s. Cero SSH/ROS/movimientos,
  instalaciones remotas, recargas o reinicios en esta implementación.
- **Backup/evidencia/reversión de esta ampliación:**
  `../Humanoide-vla-evidence/20260910T134348Z_GENERAL-HOME-IMPLEMENTATION/`,
  con documentos anteriores en `before/`, `model-audit-final.json` y
  `pico-example-plan.json`. No existían el paquete, los ejemplos ni este venv.
  Para retirar: eliminar selectivamente esas fuentes nuevas y sólo
  `.venv/general-home`, restaurar sus entradas documentales preservando cambios
  posteriores. No requiere rollback en el robot. Tras firmware, conservar
  fuentes/pins y volver a contrastar modelo y contrato; no restaurar un informe
  anterior como permiso de movimiento.
- **Revisión general VERIFICADA offline 10-09-2026:**
  [HOME desde posturas generales](teleoperation/CRUZR_HOME_DESDE_POSTURA_GENERAL.md).
  Estudio splint/4.000 posturas, límites, cobertura y uniones rígidas; arquitectura
  propuesta para planificación, escena, validación y ejecución. No implementa
  todavía un ejecutor general ni altera MOT-01/MOT-02. Evidencia y reproducción
  en `../Humanoide-vla-evidence/20260910T124156Z_GENERAL-HOME-3D-REVIEW/`.
  Respaldo documental en `before/`; reversión sólo documental selectiva.
  No requiere instalar ni recargar nada para reproducir esta revisión.
- **Ampliación VERIFICADA local 10-09-2026:**
  [`plan_clamp_home_adaptive.py`](../scripts/teleoperation/plan_clamp_home_adaptive.py)
  y `test_plan_clamp_home_adaptive.py` implementan apertura según postura y lado,
  etapas omitidas sólo por igualdad y tiempos según desplazamiento. Ocho pruebas
  pasan; siete casos nominales auditados. No está integrado ni instalado en HOME
  automático. Error5°/parada/interpolación dejan la activación física pendiente.
  [Detalle](teleoperation/CRUZR_HOME_ADAPTATIVO.md), backup y evidencia:
  `../Humanoide-vla-evidence/20260910T120838Z_ADAPTIVE-HOME/`.
  Para reproducir se usa el mismo snapshot explícito del08-09; para retirarlo,
  quitar esas dos fuentes nuevas sin revertir rutas Motion.
- **VERIFICADO local 10-09-2026; sin activar candidatas.** Compara rutas PICO/HOME
  actuales y alternativas sin emitir XML ni comandos de robot. Perfil vigente20s.
- **Fuentes:**
  [`review_clamp_trajectory_optimization.py`](../scripts/teleoperation/review_clamp_trajectory_optimization.py)
  y su prueba `test_review_clamp_trajectory_optimization.py`; usa NumPy ya
  disponible, modelos de trayectoria existentes y snapshots explícitos.
- **Resultado:** candidato prioritario20→16,25s cuando cuerpo ya está a cero;
  exige comprobar asentamiento real. No hay aprobación física ni cota de parada.
  Ocho pruebas pasan; fuentes operativas conservan hashes previos.
- **Reproducir y límites:** [informe](reports/2026-09-10_OPTIMIZACION_TRAYECTORIAS_ABRAZADERAS.md).
  Evidencia/modelos/hashes:
  `../Humanoide-vla-evidence/20260910T113554Z_CLAMP-TRAJECTORY-OPTIMIZATION/` y
  snapshot original del08-09 indicado allí. Conservarlos fuera de una actualización.
- **Activación/reversión:** no requiere despliegue. Para retirar el comparador,
  quitar selectivamente sus fuentes nuevas y referencias; no revertir archivos
  del robot ni la corrección independiente del preflight MOT-01.

### MOT-03 — PICO limitado a brazos

- **VERIFICADO histórico 2026-08-27:** `clamp, waist_mode=0, leg_mode=0`, torso
  quieto. Fuente/receta [`install_cruzr_pico_arms_only.sh`](../scripts/teleoperation/install_cruzr_pico_arms_only.sh)
  `--check`, `--install`, `--rollback`; rechaza hashes desconocidos.
- **Destino Motion:**
  `/opt/walker/manipulation_meta_tasks/share/manipulation_meta_tasks/config/meta_teleoperation/cruzr_clamp_pico_tele.yaml`.
  Vendor `5f08b30c…3fc62a` → overlay `4e8d79a4…117a44`; hashes completos
  protegidos en el instalador. Sólo cambian modos de cintura/piernas.
- **Backup:** `/home/walker/.local/share/cruzr-pico-arms-only/`, vendor y overlay.
  Restaurar YAML vendor retira la limitación; no hacerlo durante teleoperación.
- **Activación/verificación:** copiar YAML no demuestra carga. Revisar modos
  del nuevo log y exclusividad de control. La antigua receta de cambio
  `teleop→auto_task→teleop` puede iniciar HOME: **no ejecutarla automáticamente
  tras restaurar**, especialmente con brazos elevados. Seguir guía actual.
- **Detalle:** [fuente PICO](teleoperation/CRUZR_S2_PICO_TELEOP_SOURCE_OF_TRUTH.md).

### MOT-04 — READY, recovery y tareas auxiliares

- **2026-09-14 — uso de tarea existente, sin adaptación persistente:**
  una preparación de cabeza `cruzr/move_head_lower`, SUCCEED/status4; final
  pitch−0,430665rad, velocidades0, resto de ángulos sin cambio entre extremos.
  Cabeza observación y brazos/cuerpo HOME; no HOME20D completo. Captura pasiva
  RGB/nube/TF nueva, escena parcial observada. No instalar/reaplicar postura
  transitoria tras firmware. Fuente/receta, objetivo, destino, hashes, evidencia
  y continuidad: [observación actual](vla/OBSERVACION_ENTRY_20260914.md).

- **2026-09-11, Europe/Madrid — prueba temporal de observación VERIFICADA:**
  única acción instalada `cruzr/move_head_lower`, yaw0/pitch−0,43rad en2s,
  SHA `f3a73626f97b471d4a0a03c98c24de32243651116c497328e69b5ddc57ea46c1`.
  Uso reproducible: `cruzr_blue_workbin_cycle.sh --check` y, tras condiciones
  físicas actuales, `--prepare-vision --yes`. Acción SUCCEED/4, cabeza final
  −0,430473rad e inmóvil; otros ángulos sin cambio entre extremos. Caja completa
  en RGB VLA; detector de lectura aporta pose en cámara, no aprobación de avance.
  Destino: Motion, XML existente bajo config/cruzr/move_head_lower.xml del
  paquete manipulation_task_manager; ninguna modificación de archivo/servicio.
  Estado final cabeza en observación, cuerpo/brazos HOME; no HOME20D completo.
  Restauración no ordenada: conservar observación; no usar HOME genérico ante
  la mesa. Estado inicial/backup documental, fuentes y hashes en
  `../Humanoide-vla-evidence/20260911T111951Z_VLA-OBSERVATION-HEAD/`.
  No hubo instalación/recarga/reinicio ni inferencia/publicación VLA. Los
  mecanismos y dependencias del wrapper existente se mantienen.

- **VERIFICADO histórico:** corrección de cintura de dos valores a uno para
  S2 en READY y recovery; otras tareas de pruebas registradas individualmente.
- **Fuentes:** [`scripts/vla/runtime/tasks/`](../scripts/vla/runtime/tasks/),
  [`patch_vla_ready_s2_waist_e6_0p.sh`](../scripts/vla/patch_vla_ready_s2_waist_e6_0p.sh)
  y demás instaladores de [la guía VLA](guides/CRUZR_S2_VLA_SAFE_ENABLEMENT.md).
  READY usa `s2_vla_e6_0_ready_s2.xml`, hash `c767f739…e2a9b2`;
  destino `config/s2_bio_vla/s2_vla_pick_large_teleop_ready.xml` del gestor.
- **Reaplicar:** inventariar XML y entradas reales a partir del respaldo.
  Revisar primero `--help`/`--check` del instalador de cada tarea y su guía.
  El parche READY tiene requisitos de HOME y paros liberados: no incluirlo
  en un bloque genérico de instalación bajo E-stop. Un hash de task_list
  distinto exige revisión, no anular la comprobación.
- **Backup:** `/home/walker/cruzr-vla/backups/`, incluidos E6.0P/E6.0Q;
  copia de ambos directorios de configuración de manipulación en el respaldo.
  Comparar/revertir sólo la tarea afectada. Ni el fichero presente ni una
  prueba antigua autorizan ejecutar todos los árboles recuperados.

### MOT-05 — HOME original de fábrica como `cruzr/originalhome`

- **2026-09-18 Europe/Madrid — PREPARADO en PC; instalación en robot PENDIENTE.**
  Añade el HOME original UBTECH como tarea adicional; `cruzr/home` sigue siendo
  el HOME propio (body-first v4, SHA `e3d0656424a3611d89262ae645f127d975920fd09c437f9ef9c07725d69dc49c`,
  comprobado por lectura el 18-09). No modifica `home.xml`.
- **Fuente:** [`cruzr_home_original_factory.xml`](../scripts/teleoperation/tasks/cruzr_home_original_factory.xml),
  SHA `50d819d6d6190280c6efee1dc275877362c3f7c807ec733fbc3c7ed217daed88`, idéntico
  a `scripts/hands/factory_tasks.sha256` y a
  `../Humanoide-vla-evidence/20260910T095255Z_HOME-ROUTE-REVIEW/home-original.xml`.
  Cabeza, elevador, cintura y ambos brazos a cero en paralelo, 6 s: es la
  trayectoria directa que acercó los brazos al cuerpo (ver MOT-01).
- **Destino:** Motion, `walker-motion.manipulation_robot_app-1`:
  `config/cruzr/originalhome.xml` y entrada `cruzr_originalhome` en
  `config/task_list.yaml` (mismos `json_args` que `cruzr_home`: `TimeRatio 0.5`).
- **Reaplicación:** [`cruzr_install_original_home.sh`](../scripts/teleoperation/cruzr_install_original_home.sh)
  `--check` → `--status` → `--install` → `--reload`. Install y reload exigen
  E-stop accionado, cargador desconectado y confirmación escrita en terminal.
  El script nunca envía la tarea.
- **Verificación:** `--status` debe dar `INSTALL_STATE=exact` y
  `TASK_PROCESS_ORDER=after-task-list`. Ejecución física: no ensayada.
- **Dependencias:** la recarga cambia el hash de `task_list.yaml` y la identidad
  del proceso; las etapas `entry410` cualificadas deben volver a cualificarse.
- **Backup/reversión:** `/home/walker/cruzr-owner-backups/<token>-originalhome/`
  con `task_list.yaml` anterior. Retirar sólo la entrada `cruzr_originalhome` y
  el XML, conservando entradas posteriores, y recargar bajo E-stop.

### PC-01 — Red de trabajo

- **VERIFICADO histórico 2026-08-26:** perfil Ethernet `cruzr-s2`, `eno1`,
  `192.168.11.250/24`, autonegociación 1 Gb/s full duplex, never-default.
  Wi-Fi USB `wlx80afcad40bd6`, perfil observado `Cruzr S2-0669 1`:
  DHCP en `.42.0/24`, ruta `.11.0/24` vía `.42.2`, never-default,
  ignore-auto-DNS y powersave deshabilitado. Internet por `wlo1`.
- **Fuente/receta y evidencia:** sección de conexión de la
  [fuente PICO](teleoperation/CRUZR_S2_PICO_TELEOP_SOURCE_OF_TRUTH.md).
  Guardar perfiles reales en backup privado de
  `/etc/NetworkManager/system-connections/`, rutas y salida de `nmcli`.
- **Reaplicar/verificar:** importar sólo perfiles del robot si se perdieron;
  adaptar interfaz/UUID al PC actual. Comprobar IP, ruta preferida, DHCP y
  persistencia sin alterar el perfil de Internet. No fijar la IP DHCP del
  PICO o PC basándose en una observación antigua.
- **Rollback:** perfiles anteriores privados; no publicar claves Wi-Fi.
  Los resets del adaptador Realtek son una deuda de hardware/conectividad,
  no se solucionan restaurando una trayectoria.

### PC-02 — Teleoperación, servicios y permisos

- **VERIFICADO histórico:** `ubt-controller 4.7.0`, UI `4.1.0`, XRoboToolkit
  PC Service `1.0.0.0`; control de abrazaderas y STOP oficiales.
- **Fuentes/receta:** [`install_ubt_controller_4_7.sh`](../scripts/teleoperation/install_ubt_controller_4_7.sh),
  [fuente PICO](teleoperation/CRUZR_S2_PICO_TELEOP_SOURCE_OF_TRUTH.md),
  [`config/systemd/`](../config/systemd/) y [`config/udev/`](../config/udev/).
  Instalador del backend `--run` requiere sus paquetes y condiciones; no
  ejecutarlo sólo por actualizar firmware del robot si el PC sigue intacto.
- **Destinos:** `/opt/ubt-controller`, `/opt/ubt-remote-control`, servicio
  `ubt-controller.service`, drop-ins `10-numeric-locale`, `20-cruzr-clamp`,
  `30-service-lifecycle`; unidad de usuario `ubt-remote-control.service`;
  `/etc/udev/rules.d/51-pico-ubt.rules` (vendor 2d40, plugdev/uaccess).
  Revisar DISPLAY/XAUTHORITY/UID de la unidad UI en otro PC.
- **Ajustes:** locale numérico C; `arm=clamp`; apagado SIGTERM/mixed/15 s;
  UI a demanda sin reinicio automático. Backend `transmit=local`,
  `signal_server=ws://192.168.11.3:4000`, `channel_name=walker28`.
- **Verificación:** versiones/hashes, `systemctl cat`, estado STOP y writers.
  **Abrir el WebSocket de controller 4.7 puede disparar START**: no usar una
  conexión de UI/cliente como consulta de sólo lectura. No arrancar UI al restaurar.
- **Backup/reversión:** `/opt/` específico, unidades/drop-ins y configuración
  del usuario en copia externa privada. Instalador conserva paquete anterior
  en Descargas; no reponer automáticamente el 5.3 parcheado retirado.

### VLA-01 — Instalación y adaptaciones S2

**Último intento TRIAL_02, 2026-09-14:** solicitud de switch_to_vla con timeout
sin acuse; cero frames. Estado efectivo del controlador PENDIENTE de consulta.
No se ejecutó recuperación automática. [Relevo y diagnóstico siguiente](vla/RELEVO_VLA_20260914.md).

**Estado vigente 2026-09-14, corrección de controlador:** el intento del operador
publicó sin seguimiento porque SDK estaba initialized y manipulación running.
El ejecutor PC ahora usa inventario ROSA nativo y switch_to_vla (sólo --run),
con feedback SDK 20D antes de publicar y seis ejes retenidos explícitamente.
Plan vigente controller-fixed-plan; no modifica XML/firmware ni reinicia.
--observe no activa controladores; el cambio y el prefijo corregidos quedan
pendientes de ensayo físico. Tras --run SDK queda activo, sin vuelta automática.
[Fuentes, evidencia, aplicación, verificación y rollback](vla/ENSAYO_MINIMO_PUNTO_VLA_ENTRY410.md).

**Corrección de ensayo mínimo 2026-09-14:** evidencias únicas sin sobrescribir,
diagnóstico de admisión y modo --observe. Nueva admisión con deriva de ruedas
acotada comprobada en vivo sin publicador; no requiere cambios robot. Plan
anterior admission-fixed-plan (sustituido); [receta](vla/ENSAYO_MINIMO_PUNTO_VLA_ENTRY410.md).

**Preparación 2026-09-14:** ejecutor PC de prefijo de un punto VLA grabado
(25 %, ≤1,396°, 4 s), comprobado localmente; sin ensayo físico aún. Sin
instalación robot. [Receta y reversión](vla/ENSAYO_MINIMO_PUNTO_VLA_ENTRY410.md).

**Continuación 2026-09-14:** sesión task 0 desde ENTRY410, seis propuestas
aceptadas en shadow; salto inicial máximo 6,1643°, sin ejecución física.
Contenedores restaurados a exited, cero publicadores. Receta, tiempos y
fuentes en [registro del ensayo](vla/ENSAYO_READY_ENTRY410_20260914.md).

**Último resultado 2026-09-14:** también READY→ENTRY410 completado físicamente
por el operador, cinco SUCCEED. Reanudar en lectura/validación shadow task 0,
sin repetir el acceso. [Evidencia](vla/ENSAYO_READY_ENTRY410_20260914.md).

**Estado actualizado 2026-09-14:** acceso al READY nuevo probado físicamente
por el operador, cinco tareas con SUCCEED. Pendiente optimizar duración
(122 s nominales). VLA físico/ENTRY no probados por este ensayo.
[Registro e identidad del script actual](vla/ENSAYO_HOME_READY_NUEVO_20260914.md).

**2026-09-14 13:50 UTC — Nuevo ciclo completo comunicado; comprobación técnica de liberación correcta.**
`cruzr_boot_ready.sh --check` devuelve0, Motion3/3, cámaras2/2 en seis topics
con marcas crecientes y RELEASE_TECHNICAL_CHECK=passed. Cero comandos de movimiento.
Sustituye WaitStartMotion como último resultado técnico de arranque. Liberación
condicionada a brazos abajo/vacíos/estables y zona libre con persona junto al paro;
puede iniciar HOME interno. Liberación y fin de arranque aún no observados.
No aprueba ENTRY410 ni verifica todavía su ejecución. Evidencia:
`../Humanoide-vla-evidence/20260914T135018Z_ENTRY410-BOOT-RELEASE/`. BOOT-01/VLA-01.


**2026-09-14 — ENTRY410 instalada en Motion y contenedor recargado una vez; paro mantenido.**
Diez XML y registro82ac1bc8…d2e434e verificados; respaldo copiado y comprobado en PC.
Principal1 verificado antes de instalar/recargar. Motion reiniciado13:32:04UTC;
hashes intactos. No se envió ninguna tarea o movimiento. Control Center queda
en WaitStartMotion y el guard responde not_initial_boot_release: NO liberar
paro ni repetir recarga. Pendiente recuperación de arranque supervisada, carga
efectiva y ensayo. VLA-01; recibos/backups en la ficha enlazada.
[Ficha vigente](vla/EJECUTOR_ENTRY410_POR_ETAPAS.md).

**2026-09-14 — Instalación ENTRY410 preparada; pendiente paro principal pulsado.**
Instalador en disco con respaldo, preservación literal de registro y reversión
ante fallo; no recarga ni ejecuta. Plan vivo sin conflictos para diez tareas,
registro c4873861…78c84f1 →82ac1bc8…d2e434e. Quince tests pasan. No se ha instalado
ni movido; requiere E-stop principal activo antes de aplicar. VLA-01.
[Ficha](vla/EJECUTOR_ENTRY410_POR_ETAPAS.md).

**2026-09-14 — Ejecutor específico ENTRY410 implementado; integración física pendiente.**
Una etapa por invocación, XML/extremos/hashes comprobados, extremo20D fresco,
trazas, cancelación solicitada ante fallo y sin reintentos. Paquete aditivo de
diez XML preparado sólo en PC. Once tests y diez etapas reales verificados.
Consulta pasiva confirma ArmTask y servidor ROS2; Motion usa SWIG sin rclpy,
por lo que admisión de archivos queda en Motion y cliente en contenedor ROS.
Sin goal enviado, instalación o recarga. Contrato de habilitación basado en
evidencia, instalación/carga y prueba del transporte/monitor aún pendientes;
no se genera autorización automática ni se usa el ejecutor040 retirado. VLA-01.
[Ficha y reproducción](vla/EJECUTOR_ENTRY410_POR_ETAPAS.md).

**2026-09-14 — Condiciones físicas confirmadas; preflight vivo correcto, ensayo ENTRY410 no ejecutado.**
Operador confirma HOME, abrazaderas vacías/sin contacto, ruedas bloqueadas,
cargador desconectado, sin otros mandos, recorrido libre y persona junto al paro.
Auditor vivo sólo lectura: batería83,1/83,6%, paros0/0, velocidad0, control exclusivo
y preflight canónico correctos. ENTRY410 sólo dispone de generador de borradores;
el ejecutor E6.1C antiguo es de ENTRY040 y su auditor está retirado con salida78.
La confirmación física no transforma esos borradores en un ejecutor validado.
No se instaló, recargó ni movió. Evidencia:
`../Humanoide-vla-evidence/20260914T125702Z_ENTRY410-PHYSICAL-PRECHECK/`.
Reproducir lectura con `scripts/vla/audit_vla_live_preflight_e6_0g.sh --check --expect-released`.
No hay cambio remoto que revertir; respaldo documental en `before/`. VLA-01.


**2026-09-14 — Reutilización de cálculos de trayectorias documentada.**
Separados métodos, pruebas reutilizables por inclusión de dominio y resultados
que dependen de escena/ejecución. Incluye matriz de cambios, flujo de reutilización,
recetas, uso de cámaras y recuperación tras firmware. Los 220 mm, ±1° y50 mm no
son valores universales; las exclusiones de ENTRY no se generalizan. Cambio sólo
documental, sin modificar modelos, filtros, tareas o robot. ANL-01 / VLA-01.
[Guía y recetas](vla/REUTILIZACION_CALCULOS_TRAYECTORIAS.md).

**2026-09-14 — Retroceso confirmado a unos 220 mm: margen externo recuperado en el modelo.**
Recalculados acceso y retorno de ENTRY410, también desde nueva lectura pasiva:
1018 pares certificados, 54 marcas internas y cero pendientes. Pasa abrazadera
derecha–tablero bajo las hipótesis ±1°/+50 mm. 361 muestras inmóviles, paros0/0,
sin errores observados. Etapas offline75 s revisadas, sin instalar o mover.
Exclusiones internas del propietario conservadas; incertidumbre física total y
ensayo de ejecución/parada siguen separados del resultado geométrico. VLA-01.
[Ficha](vla/REVISION_ENTRY410_MESA725_20260914.md).

**2026-09-14 — ENTRY410 anclada a separación medida de 160 mm desde punta del chasis.**
Modelo de escena desplazado −59,71 mm en X, conservando giros estimados por cámara.
Registrada la exclusión offline solicitada de 13 pares internos, sin alterar
protecciones ni informes brutos. Nuevo contraejemplo verificado: abrazadera
derecha frente al tablero expandido 50 mm, con error articular máximo 0,956°.
No es contacto físico observado; impide aprobar el margen externo de esta
configuración. Seis tests pasan, sin movimiento ni cambios remotos. VLA-01.
[Ficha](vla/REVISION_ENTRY410_MESA725_20260914.md).

**2026-09-14 — Diagnóstico adicional ENTRY410: no corregir la extrínseca con el residuo RGB/nube.**
El desacuerdo de 25,70 mm se conserva bajo la transformación común cámara–robot.
El plano de profundidad depende fuertemente de la región: extrapola fondos de
65,5–80,0 cm frente a los 84 cm asumidos. No se cambió calibración ni geometría.
Localizadas las 13 interfaces pendientes: diez uniones directas y tres pares
entre elevador/cintura/torso/cabeza; ninguna con abrazaderas, sin exenciones nuevas.
Nueva herramienta offline, siete tests pasan. Sin intervención remota. VLA-01.
[Diagnóstico y reproducción](vla/REVISION_ENTRY410_MESA725_20260914.md).

**2026-09-14 — ENTRY410 recalculada para la escena de 72,5 cm.**
Acceso y retorno: 1018 intervalos certificados y 54 infracciones del margen del
modelo, sin intervalos pendientes. Once separaciones continuas de superficies
CAD demostradas en el dominio410; 13 interfaces móviles con intersecciones aún
sin justificación mecánica. Preparadas cinco etapas (75 s READY→ENTRY) y sus
inversas, sólo borradores. Nueva lectura inmóvil y hashes Motion contrastados.
RGB y profundidad discrepan 25,70 mm de mediana en el tablero: registro físico,
cobertura completa y ejecución/parada siguen pendientes. 16 tests pasan.
Sin movimiento, instalación, recarga ni VLA físico. VLA-01.
[Ficha de esta revisión](vla/REVISION_ENTRY410_MESA725_20260914.md).

**2026-09-14 — Mesa ajustada por el operador a 72,5 cm; ENTRY410 se conserva.**
Confirmación «72,5, hecho»: dimensión suelo–superficie del tablero, precisión no
aportada. Perfiles offline actualizados y selección repetida para 0,725 m.
Nueva captura pasiva en Vision: RGB completo de caja/mesa y nube de 9179 puntos,
marcas imagen/nube coincidentes. No demuestra zona libre ni postura articular.
La escena cambió: revisiones geométricas con mesa de 80 cm quedan históricas;
registro y revisión de la nueva escena pendientes. No se ha movido, instalado,
recargado o cambiado ninguna protección del robot. VLA-01.
[Evidencia y reversión](vla/SELECCION_ENTRY410_20260914.md#actualización-mesa-confirmada-a-725-cm).

**2026-09-14 — ENTRY410 seleccionada como base de adaptación para mesa de 80 cm.**
Comparadas 360/380/410 con sus parquets y primeros fotogramas originales.
Posturas prácticamente equivalentes: diferencia máxima de muñeca 0,701 mm.
Apoyo de entrenamiento inferido: 64,18 / 64,17 / 72,65 cm; 410 queda más cerca
bajo hipótesis comunes, sin certificar alturas. Las tres conservan acceso y
retorno con 1018 pares certificados y 54 avisos. Selección sólo offline:
config/vla/offline/selected_entry_adaptation.json; ENTRY runtime sin cambios.
Conservar trabajo de360 como referencia, sin heredar automáticamente su validación.
Sin consulta o movimiento del robot, instalación o cambio del checkpoint. VLA-01.
[Ficha de selección](vla/SELECCION_ENTRY410_20260914.md).

**2026-09-14 — ENTRY360 por etapas y once fronteras CAD resueltas de forma continua.**
Nuevo método de órbitas resuelve lifter2/torso; las otras diez parejas sin cruce
se prueban por subdivisión angular. Permanecen trece interfaces con cruces CAD,
sin exenciones. Propuesta offline READY→360 en cinco etapas, 75 s nominales:
1018 pares certificados, mismos 54 avisos, sin timeout; incluye 90/90 contra escena.
Hashes actuales de YAML/URDF/cúbica coinciden; seis límites de cabeza/cuerpo
comprobados con ±1°. Comparar suelo/tablero en una captura da 75,47–82,11 cm:
no establece cota metrológica ni justifica recolocar la mesa. Borradores no
instalados; seguimiento, parada y correspondencia mecánica siguen pendientes.
18 tests pasan. Sin movimiento, instalación, recarga ni cambio de protecciones. VLA-01.
[Ficha y reproducción](vla/ENTRY360_ETAPAS_E_INTERFACES_20260914.md).

**2026-09-14 — Preparación de ensayo ENTRY360, no cualificado físicamente.**
PC: nuevos `prepare_entry360_trial_review.py`, su test y
`review_entry_from_passive_state.py`; ámbito sólo offline. Se corrige el texto
ENTRY440 fijado en el auditor genérico de interfaces. Revisión actual de acceso
/retorno: 1018 certificados, 54 avisos, 0 pendientes; 696 muestras de interfaces.
Dataset360 verificado; altura inferida64 cm, pendiente para mesa80 cm.
Propuesta cúbica65 s con caps de diseño no cualificados; no genera XML instalable
ni transporte de ejecución. 15 tests pasan; antiguo auditor040 conserva salida78.
Motion/Vision: lectores temporales finalizados, 354 mensajes pasivos y nueva
captura RGB/nube/TF. Sin movimiento, instalación, recarga o cambio persistente.
Fuentes, destinos, hashes, dependencias existentes, backups y reversión:
[ficha](vla/REVISION_PRUEBA_ENTRY360_20260914.md).

**2026-09-14 — Contraejemplo ENTRY440/escena50mm, sólo PC.**
Nuevos buscador/verificador `scripts/vla/search_entry_fixture_witness.py`,
explicador/vista3D `scripts/vla/explain_entry_fixture_witness.py` y test.
Selector offline `screen_entry_fixture_candidates.py`: 113 extremos revisados;
ENTRY360/380/410 pasan geometría de acceso/retorno (mismos 54 avisos), pendiente
compatibilidad con mesa de 80 cm y VLA. No se cambia candidato del ejecutor.
Dos testigos articulares dentro de ±1° recomputados con intersección del modelo;
el extremo también falla. La traslación explícita49,95mm de la caja original
reproduce contacto hipotético. No observación física ni autorización VLA.
11 tests y rechazo de postura inválida pasan. Se corrige el orden invertido de
puntos próximos FCL en el explicador comprobando pertenencia a superficies.
Sin conexión al robot, instalación, recarga ni configuración física modificada.
Fuentes, hashes, dependencias existentes, backups, estado, reproducción y
reversión: [ficha](vla/CONTRAEJEMPLO_ENTRY50_20260914.md).

**2026-09-14 — Perfil de incertidumbre de escena y comprobaciones pasivas.**
PC: perfil `config/vla/offline/entry_scene_uncertainty_review.json` con 50 mm
provisionales, ampliación de revisores, FK relativo, comparación de planos y
capturador RGB/nube/TF con marcas. Sin aplicar al ejecutor: separación mínima
2 mm conservada, aprobación física falsa. 11 tests y 192 comparaciones pasan.
Motion/Vision: sólo suscripciones temporales, finalizadas; 356 muestras válidas
y nueva captura sincronizada por marcas. No movimiento, instalación o recarga.
Correspondencia de escena y parada aún no validadas; no se habilita VLA.
Fuentes, destinos, hashes, backups, estado y restauración:
[ficha](vla/CIERRE_Y_TOLERANCIAS_ENTRY_20260914.md).

**2026-09-14 — Interpretación de interfaces ENTRY440, sólo PC.**
Nuevos `audit_entry_route_interfaces.py`, `prove_entry_interface_boundaries.py`
y sus tests. Clasificación de 54 avisos: 30 invariantes, 10 fronteras separadas
continuamente, 13 cruces CAD de referencias y 1 prueba continua pendiente.
696 muestras, sin testigo nuevo fuera de cajas de referencia; no prueba física.
Seis tests pasan. Sin cambios de pares, geometría, margen ni instalación remota.
Destino, fuentes, dependencias existentes, backups, hashes, reproducción y
reversión: [ficha](vla/INTERFACES_ENTRY440_20260914.md). VLA físico sigue pendiente.

**2026-09-14 — Subdivisión de incertidumbre y validación geométrica ENTRY440.**
Módulo/test PC nuevos `entry_subdivided_scene_bounds.py`, revisores offline
ampliados con `--uncertainty-partition-nodes`; ninguna instalación en robot.
Acceso y retorno vacío: 1018 certificados, 54 avisos nominales, 0 pendientes,
sin cambiar proxy, ±1° o margen 2 mm. Treinta tests pasan. Aprobación física
pendiente por registro, interfaces y seguimiento/parada; no se habilita VLA.
Fuentes, destino, backups, hashes, aplicación y reversión en
[ficha de validación](vla/VALIDACION_ENTRY440_20260914.md). Sin cambios remotos.

**2026-09-14 — Ampliación offline del análisis ENTRY, no instalada en robot.**
Se añaden ajuste visual de útiles, revisión de acceso/retorno con hipótesis de
escena, cotas direccionales con resto de segundo orden y recomprobador de
contraejemplos. Revisor existente ampliado con `--directional-bounds` explícito.
ENTRY372 tiene intersección demostrada en el modelo a <1°; alternativa ENTRY440
conserva un par de escena sin demostrar y 54 interfaces nominales. No aprobado.
28 tests y 3216 comparaciones pasan. No movimiento, consultas, instalación,
recarga o nuevas dependencias. Fuentes, destino PC, hashes, backups, aplicación,
reversión y evidencia: [ficha detallada](vla/CIERRE_GEOMETRICO_ENTRY_20260914.md).
Registro visual, interfaces y seguimiento/parada permanecen pendientes;
no se cambia el estado de habilitación física del VLA.

- **2026-09-14 — comparación de superficie visible, PC:** nuevos
  `scripts/vla/inspect_entry_table_observation.py` y su test. Lectura offline
  de nube/regiones, ajuste robusto y comparación con proxy, sin sustituir escena
  ni límites de error. Tres tests pasan. Identificada naturaleza horizontal del
  ejemplo2,107mm. No consultas/cambios remotos. Fuente, dependencias, evidencia,
  hashes, receta y rollback: [registro de mesa](vla/REGISTRO_MESA_ENTRY_20260914.md).
  Estado: análisis parcial observado; calibración y ENTRY PENDIENTES.

- **2026-09-14 — uso de tarea existente, sin adaptación persistente:**
  una preparación de cabeza `cruzr/move_head_lower`, SUCCEED/status4; final
  pitch−0,430665rad, velocidades0, resto de ángulos sin cambio entre extremos.
  Cabeza observación y brazos/cuerpo HOME; no HOME20D completo. Captura pasiva
  RGB/nube/TF nueva, escena parcial observada. No instalar/reaplicar postura
  transitoria tras firmware. Fuente/receta, objetivo, destino, hashes, evidencia
  y continuidad: [observación actual](vla/OBSERVACION_ENTRY_20260914.md).

- **2026-09-14 — captura pasiva y preflight, sin adaptación nueva:** cámara
  estéreo actual recorta caja/base y borde cercano de mesa. `--check` canónico
  termina sin movimiento; preparación de cabeza sólo revisada, no ejecutada.
  Evidencia/receta de captura/comando preflight/hashes:
  `../Humanoide-vla-evidence/20260914T081839Z_ENTRY-CAMERA-CHECK/`.
  No requiere reaplicación ni rollback remoto; observación, no calibración.

- **2026-09-14, Europe/Madrid — hipótesis mesa/caja−20mm, PC:**
  `scripts/vla/review_vla_entry_error_bound.py` añade `--scene-z-offset-mm`
  (default0); nuevo `test_review_vla_entry_error_bound.py`. Traslación explícita
  de escena, sin cambiar fuentes originales, márgenes o ejecutores. Afinado exige
  igual escenario. Ruta372 sigue1016/54/2; ejemplo derecho2,107→3,408mm, sin
  demostrar mínimo global ni aprobar ENTRY.20tests pasan; sin paquetes nuevos,
  robot consultado/modificado o movimiento. Dependencias, fuentes/hash, backup,
  receta y rollback: [ficha](vla/ENTRY_MESA_MENOS20MM_20260914.md).
  Evidencia privada `../Humanoide-vla-evidence/20260914T080700Z_ENTRY-TABLE-MINUS20MM/`.
  Estado: herramienta PC verificada; modificación física de mesa NO realizada.

- **2026-09-14, Europe/Madrid — cotas locales y censo con incertidumbre, PC:**
  destino `scripts/vla/`: tres revisores modificados, helpers nuevos
  `entry_local_displacement_bounds.py`, `entry_interval_boxes.py`, sus dos tests,
  y `screen_entry_uncertainty.py`. Radio finito por postura, consultas selectivas
  y cajas FK por intervalos; conserva1072pares,±1° explícito/2mm y default5°.
  Ruta372:1016/54/2 en11,527s; censo69 sin aprobación.25 tests y regresión real
  pasan. Consultas pasivas nuevas a Motion/Vision: HOME inmóvil, ambos VLA
  detenidos. No movimiento, instalación, reinicio ni cambio de límites remotos.
  Backups/fuentes/hashes, dependencias existentes, receta reproducible y rollback:
  [ficha detallada](vla/ENTRY_COTAS_LOCALES_20260914.md). Evidencia privada
  `../Humanoide-vla-evidence/20260914T072438Z_ENTRY-LOCAL-BOUNDS/`.
  Estado: herramientas PC verificadas; ENTRY y VLA físico PENDIENTES.

- **2026-09-14, Europe/Madrid — afinado PC del escenario±1°:**
  Modificado `scripts/vla/review_vla_entry_error_bound.py`; nuevos
  `scripts/vla/refine_entry_pair_distances.py` y su test. Añade refinamiento
  opcional de sólidos y verificación de correspondencia/proveniencia; conserva
  todos los pares, modelo y márgenes. Predeterminado del revisor sigue5°.
  [Motivo, resultado, receta y rollback](vla/ERROR_ARTICULAR_TRAZAS_20260914.md#afinado-posterior-del-escenario-1).
  Probado sólo offline:997/54/21, dieciséis tests pasan. Dependencias existentes
  de `.venv/general-home`; sin paquetes nuevos ni instalación/carga física.
  Sin consulta, cambio, reinicio, publicación o movimiento remoto. Backup y
  fuentes/hashes: `../Humanoide-vla-evidence/20260914T070658Z_ENTRY-ERROR1-REFINEMENT/`.
  Reaplicar sólo tres fuentes PC y receta; rollback del revisor desde `before/`
  y retirada selectiva de helper/test/entradas, preservando cambios anteriores.

- **2026-09-14, Europe/Madrid — revisión de seguimiento y sensibilidad PC:**
  Nuevos `scripts/vla/review_tracking_error_traces.py` y test homónimo con
  prefijo `test_`; sólo Python estándar y decodificador canónico existente.
  [Motivo, resultados, receta, límites y rollback](vla/ERROR_ARTICULAR_TRAZAS_20260914.md).
  Se ejecutaron offline sobre diez capturas archivadas y se compararon cuatro
  escenarios con el revisor existente, sin modificarlo. Cinco tests pasan.
  H01/H02 máximo0,444207°/0,433667°; ocho ejes dinámicamente observados.
  ±1° es hipótesis de estudio, no cambio runtime ni aprobación física.
  Robot/PC: sin paquetes, servicios, control, despliegue o consulta remota.
  Sólo herramientas/resultado/documentación PC; no probado físicamente.
  Backups, fuentes exactas y hashes:
  `../Humanoide-vla-evidence/20260914T065216Z_TRACKING-SENSITIVITY/`.
  Reaplicar las dos fuentes y receta con trazas privadas verificadas; retirar
  sólo esas fuentes/informe y revertir sus entradas usando `before/` para
  rollback, preservando todo el trabajo anterior. No hay rollback remoto.

- **2026-09-14, Europe/Madrid — segunda revisión PC del error de acceso:**
  `scripts/vla/prepare_vla_entry_bundle.py` evita repetir pares ya sin resolver
  y conserva testigos de incertidumbre; test ampliado a11casos. Nuevo
  `scripts/vla/review_vla_entry_error_bound.py`, sólo archivos/CPU local.
  [Resultado, receta, límites y rollback](vla/ENTRY_Y_RECUPERACION_20260914.md#segunda-revisión-separar-tiempo-resolución-e-incertidumbre).
  Escenario5° y margen2mm intactos; cálculo terminado en26,490s con325pares
  sin resolver,54avisos nominales y693certificados; no aprobación física.
  Dependencias existentes, ningún paquete nuevo. Sin instalación, carga,
  consulta o cambio remoto en esta segunda intervención. Probado sólo offline.
  Fuentes exactas/hashes/backups en
  `../Humanoide-vla-evidence/20260914T062738Z_VLA-ERROR-BOUND-CLOSURE/`.
  Reaplicar sólo archivos PC y receta; rollback de dos fuentes existentes con
  `before/` y retirada de la herramienta nueva, preservando el resto del trabajo.

- **2026-09-14, Europe/Madrid — herramientas PC, ejecución sólo offline:**
  `scripts/vla/survey_vla_entry_scene.py`, `scripts/vla/prepare_vla_entry_bundle.py`,
  `scripts/vla/test_prepare_vla_entry_bundle.py` y
  `config/vla/offline/entry80_rim_annotations_20260914.json`, todos nuevos.
  [Motivo, fuentes, recetas, resultados, límites y reversión](vla/ENTRY_Y_RECUPERACION_20260914.md).
  Dependencias existentes: `.venv/general-home` y `.venv/vla-scene`; no paquetes
  nuevos. Censo150, candidata372 y tres rutas revisadas conservando todos los
  pares; diez tests nuevos y ocho del ranking pasan. Modelo completo/escena/
  seguimiento no cerrados; no probado físicamente ni habilitado VLA.
  Robot: sólo descubrimiento y suscripciones acotadas a estados/cámara/TF;
  no cambio persistente, reinicio, instalación, publicación física o arranque VLA.
  Estado leído HOME, inmóvil, writers0 y VLA detenidos. Sin rollback remoto.
  Evidencia, fuentes exactas, versiones, hashes y documentos previos:
  `../Humanoide-vla-evidence/20260914T055526Z_VLA-ENTRY80-OFFLINE/`.
  `sources-filtered-run/` conserva la versión de las tres rutas;
  `final-sources/` añade el final HOME, validado aparte. Reaplicación: recuperar
  los cuatro archivos PC y ejecutar las recetas del informe con los archivos
  privados; no instalarlos en el robot. Rollback: retirar sólo esos archivos
  y sus referencias documentales usando `before/`, preservando cambios ajenos.

- **2026-09-11, Europe/Madrid — comparación de entradas offline en PC/Vision:**
  tres fuentes nuevas PC: `scripts/vla/evaluate_vla_entry_candidates.py`,
  `scripts/vla/audit_vla_entry_candidate_geometry.py` y
  `scripts/vla/estimate_vla_entry_support_height.py`. Sin versiones anteriores.
  [Motivo, fuentes, receta, resultados y reversión](vla/DECISION_ENTRY_VLA_20260911.md).
  Dependencias existentes: helpers/evaluador, entorno general-home y la imagen
  NVIDIA; no nuevos paquetes.15inferencias completadas, cinco tests del helper
  pasan; extremos aún rechazados. No probado físicamente ni habilitado VLA.
  Vision: contenedor temporal `cruzr-vla-entry-offline-1239`, network=none,
  checkpoint/overlay:ro, staging propio `/tmp/cruzr-vla-entry-offline.6HO18F4m`.
  Exit0; contenedor y staging retirados tras exportar. Sin cambios persistentes
  remotos ni arranque de los contenedores VLA de operación.
  Backup previo, fuentes completas/versiones/hashes y evidencia reproducible:
  `../Humanoide-vla-evidence/20260911T123920Z_VLA-ENTRY-CANDIDATE-DECISION/`.
  Rollback: retirar sólo tres fuentes nuevas y ediciones de esta intervención
  con `before/`, preservando trabajo anterior. No hay activación física.

- **2026-09-11, Europe/Madrid — instalado y cargado en Vision, probado en shadow:**
  reparación de evidencia `shm_msgs/String` en
  `scripts/vla/runtime/cruzr_s2_inference_shadow.py`. Destino y backup exactos,
  versiones, dependencias, activación y reversión en
  [prueba mesa80](vla/PRUEBA_VLA_MESA80_20260911.md).
  SHA anterior840c93e2…b7cac22 →173b55da…cce67b81. Cambian sólo frame_id/encoding
  del JSON; checkpoint, perfil P14, límites y comandos físicos intactos.
  Nuevo instalador `scripts/vla/install_shadow_inference_adapter.py` exige
  hash previo y contenedor detenido, respalda y sustituye un único archivo.
  Nuevo test de evidencia;9 tests pasan. No hay dependencias nuevas.
  Primer arranque temporal:0chunks por fallo de serialización; sesión detenida.
  Segundo arranque con corrección:2chunks, ambos rechazados por discontinuidad
  (máximo81,039° frente a5,73°);2RGB+20D guardados y hashes verificados.
  Final ambos contenedores exited/restart=no, cero RobotCommand y postura sin
  cambio entre extremos. **No probado físicamente ni habilitado flujo VLA.**
  Evidencia, fuentes completas y backups documentales:
  `../Humanoide-vla-evidence/20260911T122137Z_VLA-TABLE80-SHADOW/`.

- **2026-09-11, Europe/Madrid — instalado en PC y probado offline:**
  `scripts/vla/analyze_vla_entry_fixture_sweep.py`,
  `scripts/vla/refine_vla_entry_fixture_sweep.py` y
  `scripts/vla/scene_decode_requirements.txt`, sin versiones anteriores.
  Motivo: comparar acceso a ENTRY430/438 frente a tablero/caja, sin movimiento.
  Analizador admite límites explícitos `--obstacles-json`, valida forma,
  finitud y orden; refiner conserva límites. Resultados no otorgan aprobación.
  Dependencias geométricas existentes en `.venv/general-home`; entorno nuevo
  `/home/lacuna/proyectos/Robots/Humanoide/.venv/vla-scene`, creado con
  `--system-site-packages`, añade PyAV18.1.0/PyArrow25.0.1 para vídeo/parquet.
  [Aplicación, verificación, reversión y límites](vla/REVISION_ENTRY_CON_MESA_20260911.md).
  Ambas recetas reprodujeron exactamente resultados anteriores; nueva escena
  se guarda aparte tras recolocación manual por operador. Sin activación remota,
  reinicio, XML, publicador físico o prueba de brazos; ENTRY40 permanece vigente.
  Fuentes completas, versiones, hashes, capturas y backups en
  `../Humanoide-vla-evidence/20260911T114330Z_VLA-ENTRY-SCENE/`.
  Reversión selectiva: retirar nuevo entorno y tres fuentes nuevas, restaurar
  sólo ediciones de esta intervención desde `before/`; preservar trabajo previo.

- **2026-09-11, Europe/Madrid — añadido y VERIFICADO offline en PC:**
  [`rank_vla_entry_postures.py`](../scripts/vla/rank_vla_entry_postures.py) y
  `scripts/vla/test_rank_vla_entry_postures.py`, sin versión anterior.
  Motivo: revisar ENTRY inclinada sin alterar un frame20D ni el checkpoint.
  150 entradas task0,113 con filtro≤5° y límites válidos; ocho tests pasan.
  Dependencias existentes Python3/NumPy/PyYAML, helper FK versionado, URDF
  splint externo y reporte E6.0Z de hash congelado. Sin nuevas instalaciones.
  [Receta, resultado y pendientes](vla/REVISION_ENTRY_ERGUIDA_20260911.md).
  Fuentes/versiones/hashes y backups documentales en
  `../Humanoide-vla-evidence/20260911T103734Z_VLA-ENTRY-UPRIGHT/`.
  No requiere activación/recarga ni destino remoto; no probado físicamente.
  Rollback: retirar dos fuentes nuevas y deshacer sólo esta edición documental
  mediante `before/`; preservar cambios previos. ENTRY40 y perfiles intactos.

- **VERIFICADO histórico:** imágenes y `checkpoint-40000` instalados; dos
  contenedores detenidos, `restart=no`. Inferencia produce chunks; no existe
  autorización de publicación física por restaurar el paquete.
- **Fuente:** [`install_ubtech_vla.sh`](../scripts/vla/install_ubtech_vla.sh),
  [`scripts/vla/runtime/`](../scripts/vla/runtime/) y
  [guía de activación](guides/CRUZR_S2_VLA_SAFE_ENABLEMENT.md).
  Perfil S2 20D, `/mc/whole_joint_states` de lectura, metadatos/modelo y
  validadores locales. Binarios/checkpoints del paquete externo, fuera de Git.
- **Destino:** `/home/walker/cruzr-vla/` en ambos hosts; montajes de
  `cruzr-vla-inference` y `cruzr-vla-control`. El backup ligero no incluye
  automáticamente todas las imágenes ni pesos: conservar el paquete original
  y copia del workspace modificado/metadata con sus hashes por separado.
- **Reaplicar/verificar:** `--check`, después etapas necesarias `--stage`,
  `--load-images`, `--create-containers`, `--verify` según guía. Crear
  contenedores **detenidos**; revisar compatibilidad antes de reutilizar perfil.
- **Rollback:** backup de workspace/inspect/manifiestos y originales de cada
  overlay; preservar `restart=no`, sin habilitar clientes de movimiento.

### NAV-01 — Mapas, transferencia, referencias y geometría

- **OBSERVADO reciente:** trabajo en `MESAS2`, `CRUZR_MAP_TYPE=uslam`;
  `test_route_01` es otro mapa histórico/default, no sustituye MESAS2.
  Guardar nombre, tipo, fingerprint, puntos con orientación y referencias.
- **Datos:** `/etc/walker/map`, `/etc/walker/task`, calibración del robot;
  PC [`config/cruzr_mesa2_drop.json`](../config/cruzr_mesa2_drop.json), sus
  backups y `config/clamp_*.json`. Referencias AprilTag y evidencia de montaje
  en guías y carpeta externa. Guardar también modelos locales no versionados
  que se usaron en cálculos de colisión; no regenerarlos de una foto.
  Las carpetas `cruzr_s2_description` y `cruzr_s2_description_splint` se
  revisaron sin modificarlas el 10-09: base con pinzas de dedos, splint con
  abrazaderas cuyas mallas ya estaban en el runtime archivado. Ambas comparten
  nombre ROS; no hay instalación nueva ni sustitución automática de los
  modelos de los auditores. [Informe y manifiesto](reports/2026-09-10_MODELOS_CRUZR_S2_DESCRIPTION.md).
- **Fuentes de comportamiento:**
  [`cruzr_blue_workbin_table_transfer.sh`](../scripts/cruzr_blue_workbin_table_transfer.sh),
  [`cruzr_blue_workbin_table_transfer_no_tag.sh`](../scripts/cruzr_blue_workbin_table_transfer_no_tag.sh),
  [guía sin AprilTag](guides/TRANSFERENCIA_CAJA_ENTRE_MESAS_SIN_APRILTAG.md) y
  [guía con AprilTag](guides/TRANSFERENCIA_CAJA_ENTRE_MESAS_CON_APRILTAG.md).
  Umbral local de batería 20 % en ciclo/ruta; no es un ajuste del firmware.
- **Reaplicar/verificar:** recuperar mapa/perfil correctos; volver a comprobar
  localización, waypoint, altura/disposición real y transformaciones. El
  modo `--check` de algunos flujos puede cargar mapa/relocalizar: leer su
  alcance antes de usarlo como verificación. No reenseñar mesa 2 desde PRE;
  `--teach-mesa2` se hace en la pose real de depósito. Medir desde la referencia
  definida, no interpretar el error al waypoint como distancia hasta la mesa.
- **Rollback:** copia previa del perfil/mapa. Restaurar datos no renueva una
  validación física ni levanta bloqueos derivados de contacto. Conservar
  fechas, incertidumbres y condiciones de los modelos.

### NAV-02 — Perfil temporal de percepción con carga

- **Adaptación temporal:** [`cruzr_cargo_perception_profile.sh`](../scripts/cruzr_cargo_perception_profile.sh)
  `--check`, `--enable`, `--restore`. Desvía RGB-D de la caja durante tránsito;
  mantiene LiDAR, odometría, mapa, bumpers y paros.
- **Destino Vision:** `walker-nav.vnav_perception-1`,
  `/opt/walker/nav_perception2d_config_utars/share/nav_perception2d_config_utars/config/perception/perception_params.yaml`.
  Estado/backup en `/home/walker/.config/udoke/cruzr-cargo-perception-profile`.
  Contrasta LiDAR en `walker-nav.freepnc_task-1`.
- **Reaplicar/verificar:** guardar original y transacción, pero recuperar
  configuración **normal**, no el perfil de carga activado. `--restore`
  reinicia el componente indicado por el script; no es una consulta inocua.
  Una transacción interrumpida exige resolverla antes de volver a habilitar.
- **Rollback/evidencia:** restauración byte a byte y hashes del script; guía
  de transferencia y registro de la ejecución que habilitó el perfil.

## Retirado, temporal o no aprobado para reinstalar

| Elemento | Estado vigente / razón |
|---|---|
| `cruzr-v020-boot-guard.service` y `/usr/local/sbin/cruzr-v020-boot-guard` | **DESCARTADO como autoarranque actual**: disabled/inactive; reemplazado por BOOT-01. El guard histórico podía reiniciar CC y mover. Conservar sólo evidencia/backup. |
| Ruta directa antigua `cruzr/pico_to_home_owner` | **Retirada tras contacto**; sustituida por open_v2. No recuperar por similitud del nombre. |
| `cruzr_internal_home_open_v3_6s_DRAFT.xml` | **Borrador local**, no instalado ni validado. El HOME interno vigente es de 20 s. |
| Parches de backend 5.3 (GRIPPER→CLAMP, trigger Y, watchdog) | **Retirados** al usar 4.7 oficial. No aplicar a su binario. |
| `cruzr-boot-visual-preview.service`, JSON del visor, registro de boot | **Transitorios**: no habilitar/restaurar para el próximo arranque. |
| Reinicio LightDM del 10-09 para recargar el visor | **Intervención puntual**, no modificación de autologin ni requisito de cada arranque. |

## Plantilla obligatoria para cambios nuevos

Copiar una ficha, asignar un ID estable y añadirla al índice. Para cambios
temporales basta enlazar la intervención y dejar claro el estado final; si
permanecen activos pasan a tener ficha vigente.

```text
ID / nombre:
Fecha y zona / autor o intervención:
Motivo y comportamiento esperado:
Estado: VERIFICADO / OBSERVADO / INFERENCIA / PENDIENTE / DESCARTADO
Destino: PC/PICO/Motion/Vision, host, contenedor, ruta/servicio/clave exacta
Versión, imagen/digest, hardware y dependencias compatibles:
Antes: valor/hash, backup privado externo y checksum
Después: valor/hash, fuente o receta versionada (incluye cambios sin commit)
Aplicación: comando/receta y requisitos; efecto sobre procesos/control
Activación: si necesita recarga/reinicio; separado de instalar y de mover
Verificación: prueba, salida/evidencia, instalado/cargado/ensayo físico
Reversión: pasos selectivos, backup y límites de la reversión
Tras actualizar: conservar / revisar y reaplicar / recalibrar / no restaurar
Evidencia y pendientes concretos; ficha que reemplaza, si existe:
```

Un registro sólo está cerrado cuando otro operador puede localizar la fuente,
el estado anterior, el procedimiento y la evidencia sin consultar el chat.
No marcar como completos los componentes que sólo se han revisado en papel.

## 2026-09-14 — VLA-01: comprobación posterior al arranque completo

VERIFICADO: el preflight vivo con paros liberados termina correctamente;
20 articulaciones, velocidad máxima cero, baterías75,5/77,1%, cargador
desconectado, ambos paros0, servidor de manipulación disponible, sin otros
publicadores de control y contenedores VLA detenidos. Los diez XML instalados
y el registro conservan los hashes del recibo después del reinicio. Esto
verifica archivos persistentes, no la identidad efectiva de tareas cargadas.
HOME es la postura comunicada ahora por el usuario; este preflight no demuestra
por sí solo coincidencia de las20 posiciones con el extremo HOME.

PENDIENTE: el ejecutor de cinco etapas comienza en READY. El wrapper
`scripts/vla/cruzr_vla_ready_pose.sh` mantiene bloqueado HOME→READY y exige
validación independiente. No ejecutar etapa1 desde HOME. También sigue sin
emitirse la habilitación de ensayo documentada en el ejecutor ENTRY410.
No se enviaron movimientos, no se reinició ningún servicio y no se modificó
el robot en esta comprobación. El arranque correcto no elimina estos pendientes.
Evidencia: `../Humanoide-vla-evidence/20260914T135826Z_ENTRY410-POSTBOOT/`,
con preflight, hashes posteriores al arranque y respaldo documental.
Punto de reanudación: resolver el acceso HOME→READY y la habilitación del
ensayo, conservando el robot en su estado actual; no repetir el ciclo de
encendido para resolver un requisito del ejecutor.

## 2026-09-14 — VLA-01: acceso medido a READY calculado por grupos

OBSERVADO: captura pasiva posterior al arranque, 14:07:23–14:07:33 UTC,
347 muestras articulares, ambos paros0, sin incidencias del analizador.
VERIFICADO OFFLINE: `scripts/vla/prepare_home_ready_access.py` genera cinco
tramos desde la última postura medida hasta el READY exacto del informe410.
Comprueba identidad de traza, ausencia de movimiento/fallos en toda la traza,
variación articular≤0,002rad, identidad del modelo y fuentes inmutables durante
el cálculo. Genera diez XML DRAFT para ambos sentidos; no instala ni publica.

Resultado bajo las hipótesis del informe GAP220:1018 pares con intervalos
geométricos certificados,54 con violación del margen del modelo,0 pendientes
y sin timeout. Los54 pares son exactamente los mismos del informe de etapas
ENTRY410; no se convierten en aprobados ni se eliminan del resultado. La
correspondencia de pares no transfiere automáticamente pruebas de otro tramo.
Duración propuesta136s: cabeza20, cintura1, elevador1, brazo izquierdo57 y
derecho57. Son tiempos de propuesta, no una medición ni una ejecución aprobada.

PENDIENTE: comprobar límites dinámicos/configuración efectiva, correspondencia
runtime de grupos, identidad cargada y protocolo del ensayo. Los XML de acceso
NO están instalados, el wrapper activo permanece bloqueado y no se ha emitido
habilitación física. No hubo reinicios ni movimientos. No es aún una ruta
HOME→ENTRY ejecutable.

Evidencia externa: `../Humanoide-vla-evidence/20260914_HOME_READY_ACCESS/`
(traza, análisis, access/review.json, diez borradores, comparación y fuentes).
Tests: cinco casos de admisión de postura pasan, incluidos movimiento anterior,
deriva con velocidad cero, fallo y dato no finito; los tres tests existentes
de construcción por grupos también pasan. No cubren movimiento real.
Receta reproducible: `docs/vla/ACCESO_HOME_READY_20260914.md`. Reversión local:
retirar selectivamente las dos fuentes nuevas y restaurar documentos desde
`before/` de la evidencia, preservando otros cambios. Ningún cambio persistente
en el robot.

## 2026-09-14 — contraste vivo de configuración HOME→READY

VERIFICADO: consultas de lectura a Motion recuperaron YAML y URDF, con hashes
idénticos al contrato archivado. Tipo, lado y dimensión de los cinco grupos
coinciden. Las20 articulaciones cumplen límites de posición (incluido el error
del informe) y velocidad para el perfil cúbico propuesto. Los seis ejes de
cabeza/cuerpo cumplen además la aceleración configurada. No se localizaron
fuentes MetaMove en los dos paquetes consultados; esto no demuestra su ausencia
en todo el sistema. El orden articular efectivo dentro de MetaMove y su
interpolador no quedan demostrados por tipo/lado/dimensión.

PENDIENTE concreto: las14 articulaciones de brazo no tienen aceleración en
estos archivos. No se infiere un límite ni se marca la ejecución como aprobada.
No hubo cambios, instalaciones, reinicios ni movimientos del robot.
Evidencia: `../Humanoide-vla-evidence/20260914_HOME_READY_CONTRAST/`. La primera
lectura normalizó saltos de línea y falló la comprobación hash; se conservó y
se repitió con bytes exactos en base64 (`runtime-bytes.json`), cuyos hashes
pasan. `limits-comparison.json` conserva cada eje y sus resultados.

Reproducción local:
```bash
.venv/general-home/bin/python scripts/vla/contrast_home_ready_limits.py \
 --review ../Humanoide-vla-evidence/20260914_HOME_READY_ACCESS/access/review.json \
 --snapshot ../Humanoide-vla-evidence/20260914_HOME_READY_CONTRAST/runtime-bytes.json \
 --output /tmp/contraste-ready-nuevo.json
```

Cambio persistente sólo PC: nuevo comparador offline y este registro VLA-01.
Reversión: retirar el comparador y restaurar documentos desde before/ de la
evidencia, preservando cambios ajenos. No habilita el wrapper de movimiento.

## 2026-09-14 — VLA-01: contraste de bibliotecas internas Motion

VERIFICADO: se copiaron al PC mediante lectura las bibliotecas actuales
libmeta_move.so, libinterpolation_path_planner.so y libs2_arm_kinematics.so.
Hashes en binary-hashes.json. La biblioteca de interpolación tiene SHA256
1267e370614d5350706caa061a24c162e3333248b9b1af74b8ea319a3d5ee329.
El emulador existente verifica1312 casos de su rutina numérica: error máximo
2,6645352591003757e-15 frente a Hermite cúbica; con velocidad cero en extremos
q=q0+(q1-q0)*(3u²−2u³). Este resultado NO verifica el despacho de MetaMove,
sincronización, configuración de velocidades extremas ni control físico.

Búsqueda en YAML de cinco paquetes instalados: los perfiles CruzrS2 examinados
no declaran aceleración de brazos. Hay valores en perfiles WalkerS2/S3, pero
no son límites acreditados para esta unidad y no se reutilizan. No se encontró
una tabla explícita joint_names/joint_order en esa búsqueda. Los símbolos
exponen SetJointLimits; su existencia no demuestra los valores cargados.

PENDIENTE: demostrar el orden efectivo y la llamada completa de MetaMove, y
obtener límites efectivos de brazos. El análisis numérico del interpolador
queda cerrado en su alcance limitado. No se habilitó ejecución ni se enviaron
movimientos, instalaciones, reinicios o cambios de protecciones.
Evidencia: ../Humanoide-vla-evidence/20260914_MOTION_INTERNAL_CONTRAST/.
Las bibliotecas privadas quedan fuera de Git. Sólo cambios documentales enPC;
respaldo en before/. Revertir únicamente esta adición documental si se necesita.

Reproducción offline:
```bash
.venv/general-home/bin/python scripts/teleoperation/audit_motion_interpolation.py \
 --binary ../Humanoide-vla-evidence/20260914_MOTION_INTERNAL_CONTRAST/libinterpolation_path_planner.so \
 --output /tmp/interpolacion-contraste-nuevo.json
```

## 2026-09-14 — VLA-01: límites compilados y decisión de habilitación

VERIFICADO: se extrajo sin cargar código vendor la tabla de7 registros de48
bytes en VA0x2fe20 de libs2_arm_kinematics.so (SHA2562a41cf55…ad251c).
Las ramas izquierda/derecha del constructor copian esa tabla y llaman a
SetJointLimits; los primeros dos doubles son límites de posición. Se mantienen
sin calificar los nombres de los cuatro campos escalares restantes. Los
límites compilados NO se presentan como lectura efectiva de la memoria del
controlador: pueden existir sustituciones posteriores. Tres tests locales
verifican extracción por segmento ELF, rechazo de hash distinto y datos mutables.

HALLAZGO: todos los extremos nominales del acceso quedan dentro de estos
límites bajo la correspondencia propuesta. Sin embargo, el error independiente
±1° produce máximos0,01639868/0,01841203rad en codoL/R frente a0,01rad compilado.
El error positivo que cabe desde los máximos nominales es0,63338°/0,51803°.
Esto es una incompatibilidad del dominio de error revisado con esos defaults,
no una colisión física observada ni prueba de que la trayectoria nominal falle.
No se redujo el error para conseguir un resultado favorable. El contraste
anterior con URDF/YAML era incompleto frente a estos defaults compilados.

Consulta viva: bibliotecas MetaMove, interpolación y cinemáticaS2 mapeadas
en PID66. No se adjuntó depurador ni se suspendió el proceso. Los topics
individuales de brazo/cintura/elevador no devolvieron estado; rosa puede
terminar con código0 y mensaje de error en stderr, por lo que no se tomó ese
código como éxito. /mc/whole_joint_states y /mc/joint_states sí dieron estados
con nombres, pero en órdenes diferentes. Esto confirma la necesidad de
mapear por nombre y no prueba el orden interno de MetaMove.

DECISIÓN: no habilitar todavía. No se fabricó una habilitación ni se cambiaron
protecciones. Siguen sin demostrarse orden/despacho efectivo de MetaMove,
límites efectivos frente a defaults y seguimiento/parada para el ensayo.
No hubo objetivos de movimiento, instalación o recarga del robot. Los borradores
de acceso permanecen sólo en PC. Evidencia y decisión explícita:
`../Humanoide-vla-evidence/20260914_MOTION_INTERNAL_CONTRAST/enablement-decision.json`.

Nuevo extractor reproducible:
```bash
.venv/general-home/bin/python scripts/vla/extract_s2_compiled_limits.py \
 --binary ../Humanoide-vla-evidence/20260914_MOTION_INTERNAL_CONTRAST/libs2_arm_kinematics.so \
 --review ../Humanoide-vla-evidence/20260914_HOME_READY_ACCESS/access/review.json \
 --output /tmp/limites-compilados-nuevo.json
```

Registro global VLA-01: cambios persistentes sólo PC (extractor, tests y docs).
Respaldo de esta adición en before-final/ de la evidencia, copia de fuentes
y hashes. Reversión: retirar selectivamente las dos fuentes nuevas y restaurar
esta adición documental desde el respaldo, preservando el trabajo previo.

## 2026-09-14 — corrección del criterio de banda de error (VLA-01)

CORRECCIÓN de la conclusión anterior: el desbordamiento de la banda±1°
respecto a los límites compilados NO es por sí solo un incumplimiento de
consignas ni invalida una envolvente geométrica calculada sobre esa banda
más amplia. No se debe exigir sin distinguir que toda la banda geométrica
sea una consigna admisible. Tampoco se puede deducir seguimiento o parada
seguros del límite configurado. Se conservan los resultados previos como
historia, pero se retira ese desbordamiento como motivo suficiente de bloqueo.

VERIFICADO: las consignas nominales de los14 ejes de brazo siguen dentro
de los límites de posición compilados, bajo la correspondencia propuesta.
Las20 articulaciones pasan posición/velocidad nominal con YAML/URDF y perfil
cúbico. No se modifican límites, trayectorias, tiempos ni la banda±1°; no se
recorta esa banda a los límites. El análisis geométrico anterior no se repite
porque sus entradas geométricas y su dominio de error no han cambiado.

Cambios locales: extract_s2_compiled_limits.py distingue nominal_inside y
uncertainty_inside mediante position_domains; contrast_home_ready_limits.py
añade el resultado nominal sin cambiar la semántica de su campo previo.
Seis tests pasan: extracción ELF, hash, datos mutables, desbordamiento de banda
sin incumplimiento nominal, incumplimiento nominal real y errores no válidos.
Nuevos informes en ../Humanoide-vla-evidence/20260914_LIMIT_DOMAIN_CORRECTION/.

La habilitación física sigue sin emitirse por los pendientes independientes:
orden/despacho efectivo de MetaMove y contrato de seguimiento/parada del
ensayo, identidad/configuración efectiva frente a defaults y revisión de
los campos dinámicos de brazo. No se modifica ningún gate ni se presenta
una corrección lógica como ensayo físico completado. No hubo comandos al robot.

Registro global: sóloPC; backups anteriores en before/ de la evidencia.
Reversión: restaurar selectivamente estas fuentes/documentos desde before/
preservando otras modificaciones. Las fuentes de reproducción son los mismos
comandos de contraste y extracción documentados arriba, con directorio de
salida nuevo. Evidencia de decisión actual: decision.json.

## 2026-09-14 — VLA-01: ensayo físico de cabeza MetaMove y fallo de admisión

AUTORIZACIÓN: usuario confirmó HOME, abrazaderas vacías, cabeza/cuello libres,
ruedas bloqueadas, cargador desconectado, ningún mando y persona junto al paro.
Se verificó preflight vivo y XML oficial fijo cruzr/move_head_lower, SHA256
f3a73626…ea46c1, cabeza [yaw=0,pitch=−0,43]rad en2s. Revisión geométrica desde
estado nominal por nombre:1018 pares certificados,54 solapamientos del modelo
ya conservados,0 pendientes. No se reutilizó etapa1 ENTRY410 desde HOME.

EJECUTADO: una sola petición de acción, aceptada. La cabeza pasó de−0,00297209
a−0,42817239rad. Giro constante0,00057524rad; cambio observado máximo de otros
18 ejes0rad.312 muestras de motor; separación máxima entre muestras globales
0,03178306s. Velocidad máxima observada de pitch0,339292rad/s y discrepancia
máxima cmd_pos/posición0,364709°. cmd_pos es solicitado SIN LIMITAR, no la
consigna efectiva del servo: estos valores no califican el seguimiento futuro.
El usuario confirmó posteriormente suavidad y ausencia de contacto.

RESULTADO DEL EJECUTOR: FAILED_NO_RETRY, NO éxito validado. A1,97046s desde
dispatch, se detectó que la última muestra del paro principal tenía más de3s
y se solicitó cancelación. Se recibió respuesta, pero el registro de esta
versión no incluía código/lista de goals de la cancelación ni resultado final
de la acción. No se puede atribuir la detención a cancelación ni afirmar que
el E-stop se ejercitó. No hubo reintento ni HOME automático.

VERIFICACIÓN POSTERIOR: captura pasiva10s/348 muestras, sin incidencias, ambos
paros0 y velocidad máxima0 en todos los ejes. Estado al cierre: brazos/cuerpo
en su postura previa y cabeza baja estable, NO HOME completo. El E-stop físico
no fue accionado durante este ensayo según lo observado en los topics.

CORRECCIÓN PC: el monitor inicial admitía una sola muestra fresca de paro sin
comprobar su cadencia; eso permitió iniciar aunque su canal no sostenía el
umbral de3s. Ahora exige al menos dos muestras y comprueba intervalos antes
de dispatch. El intervalo posterior observado4,495s se rechaza antes de mover
en la regresión offline. Se mantiene el umbral3s: no se aceleran republicaciones
de valores cacheados ni se cambia el robot. Se registrarán además UUID del
goal, respuesta completa de cancelación y resultado tardío si está disponible.
Seis tests de envolvente/cadencia pasan. No se probó físicamente esa nueva
versión, no se volvió a ejecutar. Resolver la disponibilidad/semántica del
canal de paro sigue pendiente para este monitor.

Alcance cerrado: ejecución física del segundo componente de MetaMove/head y
detención posterior observada en este ensayo. NO califica cancelación, E-stop,
seguimiento/parada de brazos/elevador ni habilita ENTRY410.

Evidencias: ../Humanoide-vla-evidence/20260914_METAMOVE_TRIAL_PREP/;
../Humanoide-vla-evidence/20260914_METAMOVE_HEAD_CHECK/;
../Humanoide-vla-evidence/20260914_METAMOVE_HEAD_RUN/ (incluye fuentes EXACTAS
del ensayo antes de corregirlas, intent/result/trace/analysis);
../Humanoide-vla-evidence/20260914_METAMOVE_HEAD_AFTER/ (captura y regresión).
Fuente reproducible: docs/vla/ENSAYO_METAMOVE_CABEZA_20260914.md.

Registro global: robot sólo recibió la tarea citada y solicitud de cancelación;
ninguna instalación, recarga, cambio de fichero/firmware/protección. PC: nuevos
revisor, ejecutor de cabeza, monitor, analizador y tests. Reversión de código:
retirar selectivamente estos archivos nuevos y restaurar docs desde before-docs/
de la evidencia, preservando cambios ajenos. La postura física no se revierte
restaurando archivos: cualquier retorno requiere su propia orden comprobada.

## 2026-09-14 17:12 Europe/Madrid — VLA-01: nueva comprobación del paro antes de HOME→READY→ENTRY

El usuario confirma supervisión activa y solicita la secuencia. Captura pasiva
nueva de15s:601 muestras de actuadores, tres mensajes de cada paro, ambos0,
sin incidencias del analizador. Los intervalos de recepción siguen siendo
4,495–4,498s, superiores al máximo3s del monitor. Esto no demuestra fallo del
paro físico; demuestra que el canal observado no cumple la admisión continua
actual. No se envió HOME, READY, ENTRY ni cancelación, ni se alteró el robot.
La captura no acredita por sí sola coincidencia con HOME por nombre articular.
No se amplía el umbral ni se sustituye la evidencia por la presencia del operador.
Pendiente resolver la disponibilidad/semántica del canal y la habilitación del
acceso y etapas antes de ejecutar la secuencia solicitada.
Evidencia: `../Humanoide-vla-evidence/20260914_ENTRY_REQUEST_STOP_RECHECK/`
(captura, análisis y cadence.json). Sólo registro documental en PC, sin cambios
remotos que revertir; copias documentales previas en before/ de esa evidencia.

## 2026-09-14 — VLA-01: semántica del topic de paro identificada

VERIFICADO estáticamente en unova_power/server13cea0b9…e1a6d: la rama CAN0x5b
publica cambios de ambos paros y suprime duplicados hasta reiniciar un contador
cada11 tramas. La cadencia4,5s no demuestra avería del paro; el monitor local
lo había tratado incorrectamente como heartbeat continuo3s. No se aumentaTTL
ni se cambia firmware/reporte/protección; notificación física y parada no quedan
probadas por análisis estático. ENTRY comprueba ahora cadencia antes de dispatch,
como el ensayo de cabeza, para evitar iniciar y fallar después. Doce tests pasan.
Sin HOME, READY, ENTRY, instalaciones o reinicios remotos. Auditor y dependencias
Capstone5.0.6/pyelftools0.32 sólo enPC/evidencia privada, sin SDK modificado.
Ver `docs/vla/ESTADO_PARO_Y_CADENCIA_20260914.md` para receta, hashes, evidencia,
respaldo/reversión y pendientes. Observación de pulsación estática solicitada;
no confundir solicitud con pulsación realizada ni liberar automáticamente.

Resultado de la ventana pasiva15:43:04–15:44:04UTC:2852 muestras de actuadores,
13 mensajes por paro, todos0; sin incidencias del analizador. No se observó
pulsación. La petición al operador sigue pendiente, no equivale a ejecución.
La ventana terminó y no mide eventos posteriores. No se envió movimiento.

## 2026-09-14 — VLA-01: rendimiento VLA medido en escena fija

Adaptador shadow instrumentado e instalado enVision con backup/hash anterior;
no se alteran pesos, frecuencia ni mando. Inicialización27,467s; primera
iteración1,697s; cinco siguientes mediana0,444s/máximo0,474s. Fuente runtime
verificada DEFAULT_HZ=0.2:5s entre inferencias; cálculo del modelo caliente
mediana0,401s. Sincronización de buffer0,243ms; evidencia RGB43,779ms.
Son tiempos anidados de pared, no sumar ni tratar como garantía de plazo.

Task0 durante30,029s: seis chunks, seis rechazos por saltos iniciales en ocho
ejes. Estado leído por nombre: cuerpo/brazos cerca deHOME, cabeza−0,428268rad,
velocidades0. No es ENTRY ni ensayo físico VLA. La primera orquestación fue
interrumpida antes del trigger; se recuperó estado y usó modelo ya cargado,
reiniciando sólo validador shadow agotado. Cierre verificado ambos contenedores
VLA exited, cero publicadores de RobotCommand; ningún movimiento enviado.

Fuente/receta, instalación, backup/rollback, evidencia, límites y secuencia
física pendiente: docs/vla/PRUEBA_VLA_ESCENA_FIJA_Y_TIEMPOS.md. Cambios PC:
benchmark_vla_shadow.py y adaptador instrumentado; Vision sólo adaptador propio
sha86f6a2ee…23fe7, backup remoto sufijo20260914T161513486568Z y copiaPC.
No se modifica SDK, Motion, tiempo de trayectoria ni protecciones. Se ha medido
shadow, no se habilitó acceso aENTRY ni agarre físico. Evidencia privada:
../Humanoide-vla-evidence/20260914_VLA_TIMING/.

## 2026-09-14 — VLA-01: acceso desde estado articular por nombre

VERIFICADO: captura nueva sólo lectura,98 pares de estados en5s, nombres
articulares completos, marcas de fuente crecientes y salud de actuadores.
Cabeza pitch−0,428268rad; cuerpo/brazos próximos a cero, inmóviles. El preparador
usa ahora /mc/whole_joint_states por nombre para geometría; los actuadores se
usan para salud/velocidad y no para inferir signo o posición articular.
El monitor ENTRY se corrigió con la misma separación y exige ambas fuentes
frescas, nombres completos/únicos, datos finitos y actuadores habilitados.
No confundir esta correspondencia del estado con el orden interno MetaMove.

Acceso medido→READY:1018 pares certificados,54 avisos internos conocidos,
0UNRESOLVED, sin timeout, duración nominal123s. Los54 avisos se conservan.
Contraste offline con snapshots archivados: posición/velocidad nominal20D
correctas; brazos nominales dentro de defaults compilados. No es lectura actual
de límites efectivos ni verifica aceleración de brazos, despacho o parada.
Veinte tests pasan, incluyendo orden permutado, nombres ausentes/duplicados,
no finitos y desacoplamiento entre posiciones motor y posiciones articulares.

Cambio PC: capture_named_entry_state.py, prepare_home_ready_access.py,
runtime/entry410_single_stage_remote.py y test_entry_named_state.py. Sin
instalación/reinicio ni movimiento remoto; no se generó habilitación física.
XML de acceso nuevos siguen siendo borradores locales, NO instalados.
La CLI del preparador exige ahora --named-capture; el antiguo --trace no se
usa para geometría. measured_start se conserva sólo como helper histórico.

Reproducción:
```bash
python3 scripts/vla/capture_named_entry_state.py --output-dir /ruta/captura-nueva
.venv/general-home/bin/python scripts/vla/prepare_home_ready_access.py \
 --reference ../Humanoide-vla-evidence/20260914T124504Z_ENTRY410-GAP220/route-review.json \
 --named-capture /ruta/captura-nueva/capture.json --output-dir /ruta/acceso-nuevo
```

Evidencia: ../Humanoide-vla-evidence/20260914_ENTRY_NAMED_STATE/ con captura,
access/review.json, límites, fuentes y hashes. Los backups están en before/.
Reversión sóloPC: restaurar selectivamente fuentes propias desde before/ y
retirar fuentes nuevas; no restaurar el monitor antiguo para habilitar movimiento.
Después de una actualización, contrastar ambos schemas/nombres y rehacer
captura/revisión; no transportar un contrato de otro robot/firmware.

PENDIENTE: semántica temporal y prueba de notificación física del paro,
despacho/carga efectivos de los grupos y contrato del ensayo. No hay GOAL
HOME/READY/ENTRY enviado. No se reclama retorno seguro desde cualquier postura.

Observación de paro solicitada 2026-09-14T16:40:45.820007+00:00: captura
pasiva independiente acotada a120s en stop-transition/ de la evidencia
ENTRY_NAMED_STATE; no publica ni cancela acciones. Pulsación del operador
pendiente de respuesta. No confundir solicitud con ejecución ni liberar el paro.


## 2026-09-14 18:47 Europe/Madrid — paro reconocido y fallo de hardware (VLA-01 / BOOT-01)

**OBSERVADO.** El operador confirmó el paro principal pulsado durante el ensayo
pasivo, sin órdenes de movimiento. A las 16:40:43.395 UTC Control Center registró
`EstopPressed`, `Ready -> WaitStartMotion` y `disableAllMotionAbility`.
El registro del hardware también recibió el paro y, a las 16:40:43.732 UTC,
terminó con `terminate called without an active exception`, `SIGABRT`, con
`std::thread::~thread()` en la pila. Esto documenta un fallo del proceso;
la causa exacta en el código del proveedor sigue PENDIENTE.
Docker muestra un reinicio de `walker-motion.hw-1` (16:40:44.028 UTC) y otro de
`walker-motion.manipulation_robot_app-1` (16:40:48.723 UTC). No se ordenaron
reinicios desde esta intervención. El hardware espera `/mc/rosa_control/start`;
Motion espera ListControllers; no hay servidor de manipulación ni estados
articulares actuales. Los logs del proveedor imprimen UTC+8: su fecha local
2026-09-15 00:40 corresponde al 2026-09-14 16:40 UTC.

La captura terminó: 26 mensajes de cada paro, principal=1 y segundo=0,
ninguna muestra de actuadores, `usable_capture=false` y una suscripción
interrumpida con exit=137. El registro del monitor no contiene el flanco 0->1;
no mide latencia desde el botón ni distancia de parada. Queda comprobada la
recepción funcional del paro en Control Center y hardware, sin aprobar por ello
el seguimiento/parada de brazos ni ENTRY/VLA físico. No repetir una pulsación
sólo para recuperar el flanco que faltó en esta captura.

Estado de reanudación: mantener el paro pulsado; recuperación mediante el ciclo
completo supervisado de la guía v0.2.0, sin improvisar StartMotion ni liberar
ahora para intentar recuperar el servidor. Después del ciclo, redescubrir
procesos, endpoints y estados; no reutilizar identidades de carga anteriores.
No se instalaron cambios remotos ni se modificaron límites o watchdogs.
Evidencia privada: `../Humanoide-vla-evidence/20260914_ENTRY_NAMED_STATE/`
(`stop-transition/capture.json`, `stop-transition/trace.jsonl`,
`after-estop/cc.json`, `inspect.json`, `hwlog.json`, `motionlog.json`,
`actions.json`, `joints.json`). Copia documental previa en
`before-stop-documentation/`; manifiesto `after-estop/SHA256SUMS`.


## 2026-09-14 18:58 Europe/Madrid — recuperación tras ciclo completo (BOOT-01 / VLA-01)

**VERIFICADO por lectura; ciclo realizado por el operador.** Tras confirmar el
usuario el nuevo encendido y HOME, Control Center registra SelfCheck y
StartMotion completados, entrada en JoystickMode a las 16:55:13 UTC. A las
16:57 UTC vuelven el servidor de manipulación (1) y los estados articulares:
20 ejes de cuerpo/brazos/cabeza próximos a cero (máximo 0,002877 rad),
velocidades medidas cero; ambos paros=0, cargador=0, baterías 53,2/54,4 %.
VLA control e inferencia siguen detenidos con restart=no; publicadores de
/mc/sdk/robot_command=0. No se enviaron movimientos ni reinicios.
La recuperación operativa está verificada; no demuestra corregida la caída
SIGABRT al pulsar el paro ni aprueba ENTRY/VLA físico. No hace falta repetir
el ensayo de pulsación para comprobar recepción. Antes de ejecutar, renovar
la identidad de tareas/procesos y las condiciones de la prueba tras el arranque.
Evidencia: ../Humanoide-vla-evidence/20260914T165743Z_ESTOP-AVAILABLE/
(results.json y evidence.sha256); copia documental previa en before-docs/.


## 2026-09-14 — solicitud de continuación física tras recuperación (VLA-01)

Operador autoriza continuar y confirma condiciones y supervisión junto al paro.
El preflight canónico de este arranque termina PASS_READ_ONLY_LIVE_AUDIT_PHYSICAL_GATES_REMAIN:
20 actuadores habilitados/inmóviles, ambos paros liberados, sin cargador,
servidor disponible, VLA detenido y cero publicadores de comandos SDK.
Evidencia: ../Humanoide-vla-evidence/20260914T165743Z_ESTOP-AVAILABLE/preflight-resume.log.

Revisión del ejecutor: entry410_single_stage_remote.py exige cadencia máxima3s
tanto en admisión como durante movimiento; el canal observado repite cada~4,5s.
Cuatro regresiones test_entry410_stop_cadence.py pasan y mantienen el rechazo.
Esta incompatibilidad local no se resuelve con más confirmaciones físicas ni
con repetir el paro. Se requiere un diseño de monitor coherente con el canal
de eventos y supervisión de salud, revisado antes de movimiento; no se amplió
un timeout para permitir la ejecución. HOME→READY nuevo sigue como borrador
según la revisión de acceso; el preflight del READY instalado no valida ese
nuevo acceso. No se creó una habilitación ficticia ni se enviaron acciones.
La autorización del operador está recibida; la prueba sigue sin ejecutarse
por integración pendiente, no por falta de permiso.


## 2026-09-14 — VLA-01: timeout de comunicación del paro ajustado a 6 s

**VIGENTE, VERIFICADO en tests y admisión de cabeza sólo lectura.** Por petición
explícita del operador se sustituye el umbral local de3s por6s en
`scripts/vla/runtime/entry410_single_stage_remote.py` y
`scripts/vla/runtime/metamove_head_probe.py`, constante STOP_STATE_TIMEOUT_S.
Es un margen de ingeniería provisional sobre la repetición observada~4,5s,
NO un máximo garantizado por UBTECH ni una cota de parada física. La detección
por nuestro monitor de pérdida exclusiva de este canal puede tardar hasta6s;
los controles de salud/estados articulares siguen exigiendo0,5s. Un mensaje
de paro activo se rechaza al procesarlo sin esperar6s. No se altera ningún
paro físico, firmware, watchdog del robot, límite ni protección de Motion.

Se aplica el mismo valor en admisión por cadencia y comprobación de antigüedad.
Se mantienen dos observaciones previas; la ventana de adquisición se ajusta
a14s para admitir dos repeticiones y estabilización. Se rechazan valores
activos/inválidos, edades negativas/no finitas y pérdidas superiores a6s.
Doce tests pasan (cadencia observada, interrupción, mensaje activo fresco,
reloj inválido y envolvente de cabeza). Ejecución transitoria del helper de
cabeza con --check: HEAD_PROBE_READ_ONLY_PASSED, cero movimientos/instalaciones
y sin reinicio. Esto cierra la incompatibilidad3s/4,5s para esta admisión;
no prueba movimiento con el nuevo monitor, parada física, ENTRY ni corrige
el SIGABRT observado al pulsar E-stop. Se mantienen los gates restantes.

Destino persistente: sólo PC, dos helpers y tests. Los ejecutores envían el
helper al contenedor ROS por stdin en cada invocación: no requiere install
ni reload del robot. Las habilitaciones ligadas a hashes deben revisarse con
estas fuentes; no se regeneran autorizaciones automáticamente.
Reproducción: `python3 -m unittest discover -s scripts/vla -p 'test*stop*.py'`
y `python3 -m unittest discover -s scripts/vla -p 'test_metamove_head_probe.py'`.
Evidencia y hashes: ../Humanoide-vla-evidence/20260914_STOP_TIMEOUT_6S/
(summary.json, live-check.json, sources/, SHA256SUMS). Copia previa en before/.
Reversión: restaurar selectivamente estos archivos desde before/, conservando
trabajo ajeno; volver a3s restablece la incompatibilidad conocida. No hay
estado remoto persistente que restaurar. Este registro sustituye la decisión
anterior de mantener3s, conservada como historia.


## 2026-09-14 — VLA-01: ensayo físico de cabeza con monitor 6s completado

**VERIFICADO por Motion y telemetría; observación final del operador PENDIENTE.**
Usuario autoriza prueba física y confirma condiciones y supervisión junto al
paro. Revisión renovada desde HOME medido con fuentes actuales:1018 pares
certificados,54 avisos internos retenidos, sin UNRESOLVED. Preflight y --check
pasan. Una sola ejecución de `cruzr/move_head_lower` (0;−0,43rad,2s), sin
reintento, instalación, recarga ni movimiento solicitado de brazos/chasis.
Motion responde SUCCEED a2,341s del envío; comprobación de estabilidad
completada a3,342s, incluyendo1s de observación posterior. Cabeza final
pitch−0,430761rad/yaw0, velocidad final de todos los ejes0. Máxima desviación
medida en otros ejes de cuerpo/brazos0,0000959rad.

Resultado: HEAD_PROBE_SUCCEEDED_AND_SETTLED; no cancelación ni falso vencimiento
del canal de paro durante el ensayo. Ambos monitores locales usan6s; éste
sólo prueba físicamente el de cabeza, no el ejecutor ENTRY. No se accionó el
paro ni se midió distancia de frenado; no valida brazos/elevador o ENTRY.
Estado final: cuerpo/brazos conservan postura inicial y cabeza bajada; NO HOME
completo. No se envió retorno automático. VLA no se arrancó.

Receta: `.venv/general-home/bin/python scripts/vla/run_metamove_head_probe.py`
con --check primero, --run --physical-confirmed sólo con revisión nueva válida
y confirmación actual; --review y --evidence-dir requieren rutas concretas
como las conservadas en esta evidencia. El primer intento con Python del
sistema falló antes de conectar por falta de fcl; usar el entorno indicado.
Evidencia: ../Humanoide-vla-evidence/20260914_HEAD_TIMEOUT6_TRIAL/
(review.json, current-joints.json, check/, run/, summary.json, SHA256SUMS).
Copia documental previa: before-docs/. La ejecución es un cambio temporal de
postura: restaurar archivos no la revierte; cualquier retorno es otra acción.


### 2026-09-14 — confirmación física del ensayo de cabeza

El operador confirma «sí» a bajada suave, sin contacto y robot estable.
Queda completado este ensayo de cabeza con monitor local de comunicación6s:
éxito de Motion, estado final inmóvil y observación física concordante.
Se sustituye el PENDIENTE de observación del registro anterior. No extiende
la validación a ENTRY, brazos, elevador, cancelación o distancia de parada.
Robot permanece con cabeza bajada; no se envió ningún movimiento adicional.
Evidencia actualizada: ../Humanoide-vla-evidence/20260914_HEAD_TIMEOUT6_TRIAL/summary.json.


## 2026-09-14 — VLA-01: acceso READY renovado tras ensayo de cabeza

Captura nueva de98 muestras por nombre en5s, postura inmóvil tras bajar cabeza.
Revisión medida→READY:1018 pares CERTIFIED_AFFINE_INTERVALS,54 avisos internos
retenidos,0 UNRESOLVED, sin timeout; cinco etapas/123s nominales. Se generaron
diez XML locales, ambos sentidos desde extremos exactos.
Lectura nueva de los dos archivos de configuración de Motion y contraste:
tipo/lado/dimensión coinciden; posiciones (incluida banda de error) y velocidades
calculadas cumplen los límites de esos archivos. Sigue sin aceleración para
los14 ejes de brazo; la lectura de configuración no demuestra el orden
efectivo MetaMove ni la configuración cargada en memoria. No se instalaron
tareas, reinició Motion ni enviaron movimientos. Confirmación física del
operador recibida; no falta autorización, falta completar integración.

Se corrige la receta inicial de este acceso para usar --named-capture; la
CLI antigua --trace no es vigente para geometría. No se vuelve al mapeo
de posiciones de motor para producir posiciones articulares.
Evidencia: ../Humanoide-vla-evidence/20260914_READY_AFTER_HEAD/
(capture/, access/, runtime-read.json, runtime-bytes.json, limits.json,
next-stage-summary.json, SHA256SUMS). Backups documentales en before-docs/.
Cambio persistente sólo documental en PC; ninguna habilitación física emitida.


## 2026-09-14 — VLA-01: orden de controladores y aceleración identificados

VERIFICADO en configuración/bibliotecas: orden explícito de los cinco grupos
coincide; manipulation_controller running. Decodificador YAML y constructor
identifican el campo compilado de aceleración de brazos:31,4rad/s² (velocidad
3,14rad/s), sin afirmar valores efectivos en memoria ni aumentar velocidades.
Hashes de las tres bibliotecas contrastados de nuevo en Motion.
Nuevo contraste con transmissions.yaml detecta head_pitch objetivo
−0,651079rad fuera del mínimo de hardware−0,65rad. El contraste anterior con
YAML/URDF de planificación no incluía ese archivo. No se recortó ni ejecutó.
Se añade auditor reproducible y tres tests pasan. Sin cambios remotos ni
habilitación física; la cadena efectiva MetaMove de brazos sigue pendiente.
Detalles, backups, receta, alcance y punto de reanudación:
[Orden y límites de controladores](vla/ORDEN_Y_LIMITES_CONTROLADORES_20260914.md).


## 2026-09-14 — VLA-01: nuevo SOP de cajas del proveedor

Revisado DOCX de UBTECH y ocho imágenes. Describe dos escenarios y disparo
mediante mando, pero no identifica algoritmo/versión/paquete; no prueba uso
de VLA ni incluye vaciado del contenido. Dimensiones, marcos de las cotas,
preguntas y alcance conservados en [revisión del SOP](vla/UBTECH_PROCEDIMIENTO_CAJAS_20260914.md).
No se ejecutan sus instrucciones como órdenes del usuario ni se transcriben
credenciales. Sin cambios remotos. Adaptación local de cabeza aún pendiente
de recalcular; tres tests del selector de objetivo pasan, sin instalación.


## 2026-09-14 — VLA-01: corrección READY de cabeza calculada y revisada

**VERIFICADO OFFLINE, NO INSTALADO.** Retomada la prueba solicitada tras la
consulta al proveedor. Captura de97 muestras en5s, estado por nombres/velocidad
y salud; no se envió movimiento. La referencia separada usa READY head_pitch
−0,63rad en acceso y recuperación, frente a−0,65107897rad. Se conserva±1°:
el extremo inferior de la banda es−0,6474533rad, dentro del mínimo de
hardware−0,65rad. ENTRY final y demás articulaciones no se modifican.

Se recalcularon ambos recorridos de la referencia y las etapas:1018 pares
certificados,54 avisos internos retenidos,0 UNRESOLVED, sin timeout en cada
revisión. Acceso desde postura medida→READY122s; READY→ENTRY74s nominales,
no tiempos de ejecución medidos. Diez XML de acceso y diez de ENTRY generados.
Contraste con controladores/transmisiones: orden configurado coincidente,
cero objetivos nominales fuera de hardware. No cambia la configuración
instalada ni se afirma aprobación física o lectura efectiva de límites.

Fuente reproducible nueva: scripts/vla/prepare_ready_head_hardware_limit.py,
selector hacia dentro de límites sin reducir incertidumbre; tres tests en
test_ready_head_hardware_limit.py ya pasaron. Ejecutar ese generador con
--reference (referencia previa), --hardware-snapshot (hardware-configs.json)
y --output NUEVO.json; después prepare_home_ready_access.py con captura
por nombre y prepare_entry410_stages.py con contrato/hashes registrados.
Las rutas, hashes y resultados quedan en
../Humanoide-vla-evidence/20260914_READY_HEAD_CORRECTED/
(reference.json, capture/, access/, stages410/, limits.json, SHA256SUMS).
Los hashes del contrato/runtime de ENTRY se reutilizaron de la revisión
anterior; requieren contraste vivo antes de instalar o habilitar.

PENDIENTE: el acceso nuevo no tiene aún instalación/ejecutor calificado;
la generación local de XML no lo convierte en tarea disponible. No instalar
o ejecutar el paquete anterior con head_pitch−0,651079rad. La cadena
efectiva de despacho/parada de brazos sigue fuera del alcance del ensayo de
cabeza. No solicitar otro paro/reinicio hasta disponer del paquete y del
procedimiento concreto completos. No se envió ningún movimiento adicional.

Cambio persistente sóloPC: generador, tests y registros; no instalados en
robot. Backup documental en before-docs/; las referencias anteriores se
conservan intactas. Reversión selectiva de estos nuevos archivos; no volver a
la referencia anterior para ejecutar un objetivo fuera del límite hardware.


## 2026-09-14 — VLA-01: paquete READY −0,63 / ENTRY410 preparado

VERIFICADO PC/LECTURA VIVA; NO INSTALADO NI PROBADO FÍSICAMENTE. Preparador,
contrato, instalador de 20 tareas aditivas y ejecutor de una etapa implementados.
42 tests pasan. Acceso medido→READY 122 s y READY→ENTRY 74 s nominales;
98 muestras actuales inmóviles. Cada revisión conserva 1018 pares certificados,
54 avisos internos, cero UNRESOLVED y sin timeout. La configuración hardware y
runtime conserva sus hashes revisados. Preflight actual PASS, baterías45,3/46,8%,
paros liberados, cargador desconectado, VLA parado y comandosSDK sin publicadores.

Plan remoto de lectura comprobado: registro82ac1bc8…2e434e → previsto9d40ede9…5440fa;
20 nombres nuevos sin sobrescritura. No se ejecutó instalación, recarga o movimiento.
Se mantiene la distinción entre archivo preparado, instalado, cargado y ensayo
físico. Falta instalación con paro comprobado, activación supervisada, evidencia
de carga y protocolo/validación de despacho, seguimiento y parada de brazos.
No se emite habilitación a partir de un booleano ni de la prueba anterior de cabeza.

Receta versionada, archivos afectados, dependencias, backups/reversión, comandos
y punto de reanudación: [Paquete READY410 corregido](vla/PAQUETE_READY410_CORREGIDO.md). Evidencia privada completa:
../Humanoide-vla-evidence/20260914_READY410_EXECUTOR/.


## 2026-09-14T20:02:55.861758+02:00 — VLA-01: paquete READY410 instalado en disco

**VERIFICADO: INSTALADO EN DISCO; CARGA Y PRUEBA FÍSICA PENDIENTES.**
Operador confirma paro principal pulsado, brazos abajo, abrazaderas vacías y
estables. Preflight activo pasó; se ejecutó una sola instalación aditiva del
paquete ready410_head063. Veinte XML y registro final verificados por una lectura
independiente. No se ordenó recarga, reinicio, cambio de modo ni movimiento.

Destino Motion192.168.11.2, contenedor walker-motion.manipulation_robot_app-1,
/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config/:
20 s2_bio_vla/ready410_h63_*.xml nuevos y adición a task_list.yaml.
Registro anterior 82ac1bc898451767c734bbb9c5b57c7e2c82a7e9fa6d1f4cc3f099854d2e434e;
registro instalado 9d40ede9537d53f655e99aec883fd75fcd94828883398268c21b6c652b5440fa.
Backup robot: /var/tmp/cruzr-entry410-backups/entry410-1789408853100542285.
Copia externa verificada de backup, paquete, receipt, XML y registro actual:
../Humanoide-vla-evidence/20260914_READY410_EXECUTOR/install/external-copy/.
Receipt, verificación independiente, preflight y hashes en el directorio install/.

Fuente reproducible y comandos: scripts/vla/install_ready410_trial.py con
package/bundle.json e install-plan.json de la misma evidencia. No repetir la
instalación: rechaza los nombres ya presentes. Fuentes completas y revisiones
conservadas fuera del robot en sources/, access/, entry/ y package/.
Reversión requiere paro comprobado y ausencia de cambios posteriores: restaurar
exactamente el registro respaldado y retirar sólo los20 archivos de receipt;
si el registro ya cambió, preparar una reversión selectiva revisada. No revertir
ni recargar automáticamente. Activar después mediante ciclo completo supervisado
de arranque v0.2.0; verificar nueva instancia y carga de tareas antes del ensayo.
Mantener el paro hasta completar la preparación del siguiente arranque.
La instalación no valida despacho/seguimiento/parada de brazos ni VLA físico.


## 2026-09-14 — BOOT-01/VLA-01: nuevo arranque y XML del proveedor

VERIFICADO SÓLO LECTURA. Tras ciclo completo comunicado por el operador,
cruzr_boot_ready.sh --check termina0: Motion3/3, cámaras2/2 en seis topics con
marcas crecientes, RELEASE_TECHNICAL_CHECK=passed. Se verifican los20 XML
ready410_h63 y registro9d40ede9…5440fa después del nuevo arranque;
Motion StartedAt2026-09-14T18:07:30.421188Z. Archivos íntegros y proceso nuevo
no equivalen a prueba de despacho. Se indicó liberar E-stop con las condiciones
físicas confirmadas conservadas; liberación, HOME y resultado posterior aún
PENDIENTES. No se enviaron movimientos, recargas o reinicios.

XML recibido utars_task_zhucheng_env_20260428_start.xml analizado sin instalar:
flujo get1→put2/get2→put1, boxSize[0.4,0.3,0.22], targetPos z0.7/1.2,
putHeight0.7/1.2, tareas zhucheng/clamp_cruzr, put_cruzr_low/high y auxiliares.
Incluye dos subárboles no adjuntos; no contiene enlace explícito al checkpoint
ni prueba qué backend usa. El proveedor afirma VLA integrado; la descripción
local dice acción generalizada de Motion: contrastar las dependencias, no asumir.
No incluye dumping (proveedor ya indicó desarrollarlo). Resumen y preguntas
actualizadas en docs/vla/UBTECH_PROCEDIMIENTO_CAJAS_20260914.md.
Evidencia, copia fuente, hashes y backups documentales:
../Humanoide-vla-evidence/20260914_READY410_BOOT_AND_VENDOR/.
Cambios persistentes sólo documentación PC; cero cambios remotos.


## 2026-09-14 — VLA-01: HOME posterior al arranque comprobado

VERIFICADO por captura nueva de98 muestras: 20D inmóviles y salud válida,
máximo absoluto0,00306796rad; head_pitch−0,00306796rad. Servidor de acciones1.
No demuestra por sí solo despacho de las tareas nuevas. Cero órdenes enviadas.
Comparación con el acceso instalado: éste parte de head_pitch−0,43085685rad;
tras el HOME interno la diferencia es0,42778889rad, fuera de tolerancia0,02.
Sólo la cabeza difiere del inicio revisado. No ejecutar el acceso directamente
ni cambiar su tolerancia. El siguiente acceso previsto necesita primero la
bajada de cabeza al inicio revisado mediante la tarea existente, con su ensayo
verificado y comprobaciones actuales; no se ha ordenado esa bajada aquí.
READY es el siguiente objetivo; la habilitación específica del ensayo de brazos
sigue pendiente, separada de instalación y de la prueba anterior de cabeza.
Evidencia: ../Humanoide-vla-evidence/20260914_READY410_AFTER_HOME/.
No cambios remotos ni reinicios. Backups documentales en docs-before/.


## 2026-09-14 — VLA-01: cabeza bajada y dependencias del proveedor encontradas

VERIFICADO por Motion/telemetría. Usuario autoriza «adelante con todo» tras HOME
confirmado y preparación presencial. Revisión nueva y --check pasan; se ejecuta
una vez cruzr/move_head_lower (2s). SUCCEED a2,3314s y estable a3,3322s;
head_pitch final−0,430569rad, velocidades finales cero. Sin reintento, cancelación,
recarga o movimiento solicitado de brazos/chasis. Observación visual posterior
PENDIENTE. Estado: cabeza bajada; no denominarlo HOME completo. El inicio del
acceso vuelve a ser compatible en cabeza; no se emitió habilitación de brazos.
Sigue faltando evidencia del protocolo de ensayo/seguimiento/parada de brazos.

LECTURA VIVA del proveedor: el XML enviado coincide byte a byte con
/opt/walker/task_manager/share/task_manager/config/cruzr_s2/utars_task_zhucheng_env_20260428_start.xml
(Vision, walker-system.ae_bt_master-1). Ambos includes existen allí y se copiaron
al PC. Las cuatro tareas Motion solicitadas también existen y se leyeron.
clamp_cruzr llama MetaMove, MetaLook transport_vision/pointclouds_vision,
MetaClamp force_init/clamp_cruzr_zc, MetaCruzrMove delta_pose−0.5;0;0 y
bodyback_cruzr_zc. put_cruzr_low incluye apertura y retroceso−0.4;0;0.
No se ejecutaron. Ruta visible de visión y control de movimiento; no hay enlace
visible a checkpoint-40000. No basta para certificar todos los binarios internos.
YAML MetaClamp localizado: request.duration6,frequency500,box_size[.4,.3,.22],
trayectorias VISION/RELATIVE, control de fuerza bimanual; su opción
request.enable_self_collision_check aparece false. Estado del proveedor leído,
NO modificación ni autorización para desactivar nuestras comprobaciones.
Esta configuración usa otras poses e incluye chasis; no es equivalente al
acceso READY/ENTRY ni una prueba física del VLA instalado.

Evidencia privada, fuentes XML/YAML con hashes y respaldo documental:
../Humanoide-vla-evidence/20260914_READY410_HEAD_PREP/.
Cambio remoto sólo la postura de cabeza por la tarea citada. Sin archivos remotos
modificados. Reversión de documentos no revierte la postura; requiere otra orden
revisada. No se envió HOME ni se activó inferencia/control VLA.


## 2026-09-14 — VLA-01: force_ready.sh para revisión técnica

VERIFICADO LOCAL. Por petición del usuario se revisó scripts/force_home.sh y se
creó scripts/force_ready.sh. Wrapper de run_ready410_trial.py, exclusivo del
manifiesto access, una etapa1..5 hacia delante. Sin argumentos muestra ayuda;
con review/step usa --check local por defecto. --run y --preflight exigen la
habilitación y evidencia del ejecutor existente. No añade bypass ni credenciales,
no envía cruzr/ready original y no modifica force_home.sh. READY conserva−0,63rad.
Nueve comprobaciones CLI locales y bash -n pasan; shellcheck no está instalado.
No consultas remotas, movimientos, instalaciones o recargas en esta intervención.
Documento/receta: docs/vla/FORCE_READY_REVISION_TECNICA.md. La habilitación
física de brazos sigue pendiente; el nombre force no la concede.
Backup documental/evidencia: ../Humanoide-vla-evidence/20260914_FORCE_READY_REVIEW/.
Reversión selectiva: retirar los dos archivos nuevos y este registro; no afecta
estado remoto. No commit ni push. Fuentes y hashes conservados en esa evidencia.


## 2026-09-14 — VLA-01: revisión del bloqueo y corrección del monitor READY

VERIFICADO LOCAL/LECTURA. Autorización del dueño conservada. UBTECH respondió al
incidente completo indicando reinicio tras E-stop; no se usa ese comportamiento
como exigencia genérica de reparación previa. Se separa ensayo vacío supervisado
de validación general. Evidencia PICO→HOME del11-09 incorporada como observación
(2103 muestras, error máximo0,007568924rad), no como cota futura de READY.

Dos defectos concretos corregidos: el monitor exige progreso común de todos los
ejes dentro del segmento revisado, no sólo cajas articulares independientes;
las tolerancias de posición del contrato no pueden superar la banda geométrica
del informe (±1° en este caso), aunque sean menores que el techo genérico0,02.
31 tests pasan. Nuevas revisiones mantienen1018 pares certificados,54 avisos
internos retenidos y cero UNRESOLVED. 20 XML regenerados idénticos al receipt de
instalación: no hace falta reinstalar ni reiniciar por este cambio sóloPC.
No se envió movimiento ni se emitió habilitación ficticia.

Paquete vigente para revisión local:
../Humanoide-vla-evidence/20260914_READY_COMMISSIONING_REVIEW/package/access.json
El paquete anterior de READY410_EXECUTOR contiene hashes de fuentes anteriores;
no usarlo con el monitor modificado ni editar manualmente sus hashes.
Protocolo propuesto, evidencia y alcance pendientes en
[Revisión de habilitación](vla/REVISION_HABILITACION_READY_20260914.md).
Fuentes cambiadas: runtime/entry410_single_stage_remote.py, entry410_stage_contract.py,
ready410_trial_contract.py y test_entry410_corridor.py, bajo scripts/vla/.
Backups before/, evidencia, fuentes y SHA256SUMS en el directorio citado.
Reversión selectiva de fuentes desde backup; no se recomienda volver al monitor
que admite combinaciones fuera del segmento. Estado físico sólo leído: cabeza
bajada alrededor−0,430665rad, resto próximo a HOME, inmóvil. No VLA físico ni
READY ejecutado. La parada y la ejecución efectiva nuevas no se declaran probadas.


### VENDOR-01 — Archivo de referencia de flujos y procedimientos UBTECH

- **Fecha/estado:** 2026-09-16, Europe/Madrid; ARCHIVADO y VERIFICADO por hashes,
  sintaxis e integridad documental. No instalado/cargado/probado físicamente
  como consecuencia de esta incorporación. Petición expresa del propietario.
- **Motivo:** conservar en Git los dos escenarios del SOP y otros flujos del
  robot, junto a documentos accesibles, sin depender de Descargas ni del chat.
- **Destino PC:** `vendor/ubtech/cruzr_s2/snapshot_20260916/` (85 XML/YAML,
  manifest y catálogo); `docs/vendor/ubtech/box_handling/` (dos DOCX saneados,
  dos extracciones Markdown, procedencia y tabla de escenarios); índices README.
- **Origen:** Vision `walker-system.task_manager-1`,
  `/opt/walker/task_manager/share/task_manager/config/cruzr_s2/`; Motion
  `walker-motion.manipulation_robot_app-1`, configuración de
  manipulation_task_manager y MetaClamp de manipulation_meta_tasks.
  Las rutas completas, hashes e identidades de imágenes v0.2.0 figuran en
  manifest.json. La copia incluye el HOME instalado, posiblemente adaptado:
  no tratarla como paquete original de fábrica ni como restauración automática.
- **Selección:** 54 XML principales (incluido default), tres XML compartidos y
  un YAML; 13 tareas Motion y 14 parámetros MetaClamp para los dos escenarios.
  Otros recursos internos, mapas, plugins y modelos no se incluyen. No se
  afirma compatibilidad con otra versión de firmware ni completitud binaria.
- **Documentos:** original chino y traducción española recibida; se retiró un
  párrafo de credenciales por documento. Imágenes, estructura de namespaces y
  demás partes conservadas byte a byte; originales privados intactos.
  provenance.json distingue hash original y hash de la copia saneada.
- **Aplicación reproducible:** `scripts/vendor/import_ubtech_box_workflows.py`,
  sólo lectura remota; receta en `vendor/ubtech/cruzr_s2/README.md`.
  Python 3 + lxml y helper SSH existente; usar directorios nuevos. El importador
  rechaza originales privados dentro del repo y no sobrescribe destinos.
- **Activación:** ninguna; no contiene despliegue, reinicio ni ejecución de
  tareas. Último selector remoto observado seguía en default_task_config.xml.
- **Verificación:** 70 XML bien formados, 15 YAML con sintaxis válida, 85 hashes
  coincidentes, includes XML presentes, enlaces de índices comprobados;
  dos DOCX conservan figuras y texto excepto credenciales. Tag vendor !wxyz
  preservado; se verificó sintaxis YAML sin cargar semántica propietaria.
  Tres copias descargadas de zhucheng_env son idénticas; no se duplicaron.
- **Respaldo/evidencia:** `../Humanoide-vla-evidence/20260916_VENDOR_ARCHIVE/`:
  originales privados, before-docs, verification.json, importador y SHA256SUMS.
  Hallazgo remoto previo: `20260916_SCENARIO1_DISCOVERY/`.
- **Reversión:** retirar selectivamente los directorios/índices/importador nuevos
  y estos enlaces, preservando cambios previos; robot sin cambios que revertir.
- **Pendiente:** selección y cualificación de flujos para nuestra escena; no se
  consideran resueltas por archivarlos. No se hizo commit ni push en esta tarea.

## BOX-01 — Variante de caja única a estantería inclinada

**2026-09-16 — BOX-01: variante de una caja a estantería inclinada, sólo diseño offline.**
Medidas del operador: caja603×397×217 mm, base570 mm, destino1000→830 mm en600 mm,
hueco1250×500 mm y tope presente. Perfil y cálculo de pendiente/envolvente creados;
elevación30 mm propuesta, desencaje real pendiente. Sin XML ejecutable, instalación,
SSH ni movimiento. Registro/IK/barrido y ensayo siguen pendientes.
[Diseño, reproducción y límites](box_handling/SINGLE_BOX_INCLINED_RACK.md).

Destino PC exclusivamente; fuentes y receta, dependencias Python3, verificación, backup y reversión en la ficha enlazada. Estado: preparado offline; NO instalado/cargado/probado.

**2026-09-16 — BOX-01-EXEC: reparación del ejecutor de agarre derecho, sólo PC.**
**ESTADO SUSTITUIDO: ejecución suspendida tras el incidente siguiente.**
Se corrigió `scripts/force_separate_right_cruzr.sh`: carga compatible del setup
UBTECH con `COLCON_TRACE` opcional, eliminación de un `done` huérfano, timeout
de 45 s y comprobación explícita de `SUCCEED/status=4`. `bash -n` pasa; no se
envió movimiento durante esa corrección. En el primer ensayo posterior, la
preparación articular terminó y MetaClamp devolvió `7101003`: los logs indican
`Transport vision is not running`, por lo que no hubo agarre. El script añade
ahora el prerrequisito original `vision/enable_transport_vision_switch`, espera
un segundo y valida por separado ambos resultados, sin reintentos. Esta segunda
corrección está verificada sólo localmente; su ejecución física queda pendiente.
Backup y diff en
`../Humanoide-vla-evidence/20260916_FORCE_SEPARATE_FIX/`. Reversión: restaurar
el archivo de `before/`; no hay estado remoto que revertir.

**2026-09-16 — BOX-01-EXEC: suspensión inicial tras postura peligrosa (histórica).**
El ensayo del operador llegó a flexión peligrosa del torso con E-stop y
retirada de cajas. La versión que habilita visión NO queda validada.
Destino exacto PC: `scripts/force_separate_right_cruzr.sh`; salida78 antes de
SSH/ROSA, sin opción para omitirla. No se modificaron XML/YAML, límites,
servicios o configuración remota. Después, el operador comunica reinicio y
HOME; comprobación pasiva confirma HOME inmóvil, paros0/0, cargador0 y sin
errores de actuadores. El agente no ejecutó ese reinicio ni HOME.
Fuente/receta reproducible: copiar la versión suspendida del script; activación
inmediata local sin instalación ni recarga. Verificación con sentinelas de
clientes remotos y sintaxis Bash. Backup previo, logs y hashes en
`../Humanoide-vla-evidence/20260916T084847Z_SEPARATE_RIGHT_INCIDENT/`.
No restaurar operativamente el ejecutor anterior; sólo conservarlo para análisis.
El bloqueo local no desregistra la tarea del robot: no llamar get1 mediante otro
cliente. La reanudación requiere revisar coordenadas, torso y barrido corporal.
[Ficha completa y evidencia](incidents/2026-09-16_SEPARATE_RIGHT_POSTURA_PELIGROSA.md).

**2026-09-16 — BOX-01-EXEC / MOT-04: get1 exitoso tras corregir disposición.**
Estado vigente: operador confirma base780mm, longitudinal590mm y lateral160mm
hacia fuera; separate_right goal cf10d446-d7cc-49e7-85fd-6c8329920adc SUCCEED.
Script modificado por el usuario en fffe749, sin bloqueo anterior; se preserva.
Antes: agente ejecutó sólo cabeza−0,43rad y habilitó transport vision, ambos con
SUCCEED; dos detecciones sin agarre. Sin XML/YAML instalado/recargado, sin cambios
de límites ni movimiento de base. Visión queda habilitada. La postura del ensayo
posterior no se restablece automáticamente, pues puede haber caja sujeta.
Perfil PC actualizado a780mm y cálculo offline regenerado; no habilita depósitos.
Destino exacto, fuentes/hashes, goals, activación, reproducción, verificación,
backup/reversión y pendientes: [ficha del ensayo](box_handling/GET1_PROVEEDOR_ENSAYO_20260916.md).

**2026-09-16 — BOX-01-EXEC, aclaración documental del mapa:** la dependencia
original NavigationLocation fija utars_nav_map y abre/inicializa brazos al
comenzar. Se documenta referencia, mismos puntos/ori­entación y continuación
después de get1. Sin seleccionar/crear/renombrar mapas, cambiar XML ni ejecutar
robot. Fuente y receta de adaptación pendiente en la ficha del ensayo.

## MAP-GET1 / BOX-01-EXEC — Punto y ciclo de una caja

**2026-09-16 — MAP-GET1 / BOX-01-EXEC:** `get1` guardado y releído en
`utars_nav_map`: X0,543184372094m, Y−1,77098915045m, yaw−1,53310485885rad.
Usuario completó localización; guardado sin movimientos del agente. `put1`
aún falta. Ejecutor PC ampliado a separación→retroceso20cm→put1→depósito→HOME,
con `--check` y abortos; sólo validación offline, sin ejecutar el ciclo.
[Estado, reproducción, respaldo y límites](box_handling/GET1_PUT1_MAPA_Y_EJECUTOR.md).

## BOX-01-EXEC — Diagnóstico posterior Iceoryx

**2026-09-16 — Incidente posterior: separación abortó con Iceoryx, salida137.**
Tras navegar a get1, visión detectó la caja; RouDi retiró aplicaciones por
heartbeats ausentes ~1,5s y Motion abortó con CHUNK_LOCKING_ERROR/SIGABRT.
Docker reinició manipulación e IMU; no fue timeout45s. Operador confirma caja
apoyada, robot inmóvil, sin pulsar paro; JointStates posterior con velocidades0.
X_BaseBox0,810808m excede por10,808mm el límite0,8m, hallazgo distinto sin vínculo
causal demostrado con el crash. Sólo diagnóstico; no se reinició ni movió nada.
[Informe y continuación](incidents/2026-09-16_SEPARATE_RIGHT_137_ICEORYX.md).

2026-09-16, actualización posterior: dos intentos get1 devolvieron
ClampBoxOutOfReach7101100; X ligeramente fuera de0.8m y fallo IK101 conjunto.
Pose posterior próxima a get1 (7,84mm); HOME intermedio no resolvió alcance.
put1 ya existe. No hubo cambios remotos; diagnóstico adicional en
`docs/incidents/2026-09-16_SEPARATE_RIGHT_137_ICEORYX.md`.

## BOX-01-DEPOSIT-HEIGHT — 2026-09-16, diagnóstico sin cambios remotos

**2026-09-16 — VERIFICADO: depósito WRC original no adaptado a superficie de 100 cm.**
YAML instalado y trayectoria registrada ordenan Z de manos ≈1,10→0,65→0,45 m;
`1.2` corresponde al torso, no a la estantería. Los 90 cm del documento son
horizontales desde rueda derecha a parte inferior del mueble, no altura ni la
misma referencia física que los 59 cm de recogida. No corregirlo acercando el
mueble. Usuario comunica reinicio; HOME posterior no medido por el agente.
Diagnóstico sin movimientos ni cambios remotos; variante de depósito pendiente.
[Análisis y referencias](box_handling/DEPOSITO_WRC_ALTURA_100CM.md).

2026-09-16 11:56 UTC — Tras reinicio completo comunicado por operador,
comprobación sólo lectura `cruzr_boot_ready.sh --check` rc0: Motion3/3,
cámaras2/2 en seis topics con marcas crecientes y RELEASE_TECHNICAL_CHECK=passed.
Preflight del instalador confirma principal1, servo0, cargador0, MetaMove esperado
y HOME body-first-v4-20s exacto. Se indica liberación supervisada manteniendo
brazos abajo/vacíos y zona libre. Puede ejecutar HOME interno; liberación,
fin de arranque y ensayo de trayectoria aún pendientes. Cero movimientos del
agente. Evidencia: ../Humanoide-vla-evidence/20260916T115604.369673Z_INTERNAL-HOME-CHANGE/.

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
Fuente/receta/criterio/límites: [selección frontal](box_handling/SELECCION_CAJA_FRONTAL.md).
Instalado/cargado/probado físicamente: NO; pruebas locales:8 correctas y
replay aproximado elige caja baja derecha. No modifica prioridades en robot.
Destino local scripts/box_handling/select_front_box.py y test asociado;
stdlib Python, sin dependencias nuevas. Reversión: retirar esos archivos y sus
referencias documentales; no requiere rollback remoto. Scripts originales intactos.
Backup documental, binarios leídos, hashes y replay: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260921T110500Z_FRONT_BOX_SELECTION`.
PENDIENTE: enlace nativo/adaptador por tarea, frescura/TF, alcance/IK y ensayo.

## BOX-01-FRONT — actualización del ejecutor, 2026-09-21 13:18 Europe/Madrid

Estado: instalado sólo en PC; --check-front cargado temporalmente y probado
con percepción real; agarre no integrado ni probado. Script sin argumentos
se detiene antes de SSH (rc78) porque MetaClamp conserva índice0.
Destinos: scripts/force_escenario1.sh, scripts/box_handling/probe_front_box.py
y test_probe_front_box.py; reutiliza select_front_box.py. Ningún archivo
remoto, servicio, parámetro ni binario modificado. Motivo: evitar que la
selección frontal diagnóstica se confunda con la consumida por el agarre.
Receta, dependencias, aplicación/activación, verificación, reversión y punto
de reanudación: [ejecutor con comprobación frontal](box_handling/SELECCION_CAJA_FRONTAL.md#ejecutor-con-comprobacion-frontal).
13 tests, sintaxis y diff pasan; consulta real goal2c9d1d54 selecciona frontal
con TF exacto. Cero movimientos. Cierre de integración nativa PENDIENTE.
Backup de versiones locales anteriores, fuentes finales y SHA256SUMS:
`/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260921T111708Z_FRONT_SCRIPT`. No usar el commit como sustituto de estos backups
de trabajo aún sin commit. Efecto de consulta: imágenes vendor automáticas.

### BOX-01-FRONT — auditoría nativa 2026-09-21 13:28 Europe/Madrid

No se activó integración nueva. Selector/diagnóstico PC siguen vigentes;
run bloqueado rc78, MetaClamp sin cambios. Auditoría read-only de SDK,
configuraciones y bindings; entonces se propuso obtener fuente/build.
La decompilación posterior identifica la vía SPS y sustituye esa conclusión.
Proceso de introspección Python temporal sufrió segfault al cerrar contexto
no inicializado; posible core dump sin localizar, servicios Motion conservan
Up3hours. No reinicios ni órdenes mecánicas. Evidencia y requisitos exactos:
[selección frontal](box_handling/SELECCION_CAJA_FRONTAL.md), auditoría nativa.
Evidencia privada y copias previas: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260921T112801Z_FRONT_NATIVE_INTEGRATION_AUDIT`.


## BOX-01-FRONT-DECOMPILE — 2026-09-21, Europe/Madrid

**VERIFICADO estático/lectura, instalado sólo PC.** Ghidra12.1.3 aislado en
`/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/tools/ghidra_12.1.3_PUBLIC`,
Java21 existente; tres scripts de análisis en scripts/box_handling. No binarios
vendor ni SDK modificados. Hallazgo: special_box_name activa SPS; dos consultas
y caché por nombre/id. GetVisionBoxHistory usa box/0. Esta vía sustituye la
conclusión de que obtener fuentes es necesariamente el siguiente requisito.
No adaptador/tarea instalado o cargado en robot; prueba física PENDIENTE.
No habilitación SPS, reinicio ni movimiento. Ejecutor continúa bloqueado rc78.

Motivo, versiones/hashes, destinos exactos, fuentes reproducibles, aplicación,
verificación, reversión y punto de reanudación:
[decompilación de selección](box_handling/DECOMPILACION_SELECCION_CAJA.md).
Evidencia privada y backup documental before/:
`/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260921T112932Z_FRONT_DECOMPILE`.
Las salidas son pseudocódigo, no fuente recompilable. Se corrigió un análisis
inicial con inferencia no-return errónea; usar clamp-refined. Reversión sólo
local y selectiva de herramientas; no rollback remoto necesario.


## BOX-01-FRONT-SPS — 2026-09-21, Europe/Madrid

**VIGENTE: INSTALADO, CARGADO Y PROBADO EN PERCEPCIÓN NATIVA; AGARRE FÍSICO PENDIENTE.**
Sustituye el bloqueo de integración de BOX-01-FRONT. Dos wrappers PC llaman
la variante local_front_box/separate_right_cruzr; confirmación física actual
más preflight, paquete ligado a hashes, sin autoarranque o reintentos. No se
modifica el SDK original ni se parchean bibliotecas, fuerzas o trayectorias.

Paquete del21-09:1fbe634748083afe; sustituido por a66aa93932ef9bdb el22-09 (actualización inferior). Motion192.168.11.2: host
/var/tmp/cruzr-front-box/1fbe634748083afe; en contenedores
walker-motion.manipulation_robot_app-1 y walker-ros.ros2-1:
/opt/cruzr-front-box/1fbe634748083afe. Tres archivos aditivos de tarea/config
bajo config/local_front_box y config/meta_clamp/local_front_box de Motion.
No cambia task_list.yaml; carga dinámica comprobada sin reiniciar.

Fuentes, hashes completos, dependencias, aplicación, activación, comprobación,
reversión y estado por destino: [integración SPS](box_handling/INTEGRACION_CAJA_FRONTAL_SPS.md).
Instalador reproducible scripts/box_handling/front_box_integration.py --install;
fuente de YAML/XML es el snapshot versionado del proveedor, original cotejado.
Clases propias resuelven el orden de endpoints y GetResult anticipado del
binding Python; las librerías ROSA instaladas permanecen intactas.

Tres pruebas MetaLook SUCCEED: fb548cf0,755685a3 y aed5add0, caja frontal baja índice1,
pose nativa coincidente. Sin trayectoria de recogida, navegación o HOME.
49 tests locales verificados, sintaxis/diff correctos. Preflight20D pasó,
velocidades0, paros0/0, cargador desconectado y baterías73,8/72,7%.
Efectos transitorios: SPS queda inicializado y caché box/0 contiene la última
pose de diagnóstico; no usar check-sps con una caja sujeta. Servidores/procesos
auxiliares cerrados al salir. No restaurar una pose vieja en la caché.

Se conservan paquetes intermedios inactivos y logs de dos fallos perceptivos
corregidos. No hubo reinicios. Copia externa de paquetes/sesiones, before/
con archivos del operador y SHA256SUMS:
/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260921T114523Z_FRONT_SPS_INTEGRATION.
Punto de reanudación: revisar montaje físico actual y ensayar recogida/ciclo;
la selección correcta no certifica margen de alcance ni barrido entre cajas.


### BOX-01-FRONT-SPS — actualización 2026-09-22, Europe/Madrid

**VIGENTE: paquete `a66aa93932ef9bdb` INSTALADO; supervisor de lectura CARGADO Y
VERIFICADO; agarre físico PENDIENTE.** Corrige falso rechazo rc78 al no existir
clientes/servidores SPS: rc0/salida vacía se admite sólo con grafo poblado válido
y endpoint ausente. Otro servidor, error o descubrimiento inconsistente bloquean.

Destinos Motion192.168.11.2: `/var/tmp/cruzr-front-box/a66aa93932ef9bdb`;
contenedores `walker-motion.manipulation_robot_app-1` y `walker-ros.ros2-1`,
`/opt/cruzr-front-box/a66aa93932ef9bdb`. Se conservan los XML/YAML compartidos
sin alteración y el paquete previo `1fbe634748083afe` inactivo. No autoarranque,
reinicios, cambio de controladores, parámetros, bibliotecas ni movimiento.
Fuentes PC: `scripts/box_handling/front_sps_session.py`,
`front_box_integration.py`, `test_front_sps.py`. Sin nuevas dependencias.

Aplicar mediante el integrador `--install`; activar al invocar el wrapper,
que calcula ID por fuentes; verificar con `--check-runtime` (sin adaptadores,
tareas ni cambio de caché). Comprobación real rc0;21 tests locales y sintaxis/diff
correctos. El preflight técnico físico del wrapper sigue siendo obligatorio.
Hashes, receta completa, estado, límites y reversión selectiva:
[integración SPS](box_handling/INTEGRACION_CAJA_FRONTAL_SPS.md#correccion-del-descubrimiento-sps-2026-09-22).
Backup anterior local/remoto y evidencia externa con SHA256SUMS:
`/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260922T063716Z_FRONT_SPS_DISCOVERY`.
Reanudar con ensayo supervisado tras revisión presencial; ciclo no probado aquí.


### BOX-01-FRONT-SPS — incidente del ensayo 2026-09-22, Europe/Madrid

Paquete vigente `a66aa93932ef9bdb` sin modificaciones. INSTALADO/CARGADO;
consumo real de selección por MetaClamp VERIFICADO, **agarre físico FALLIDO**.
Cambia el estado de ensayo pendiente: recogida rechazada por alcance/IK y
posterior aborto Iceoryx del cliente/adaptador. No hubo reinicios de contenedores;
comunicación posterior degradada y postura preparatoria fuera de HOME.
Usuario confirma inmovilidad/caja apoyada/abrazaderas vacías, éxito anterior sin
laterales y soporte de otras dos cajas; pide no nuevas medidas.

Diagnóstico remoto sólo lectura; ninguna nueva instalación, tarea perceptiva,
orden de movimiento, reinicio, cambio de límites, prioridades o watchdogs.
Únicos cambios PC: informe y enlaces documentales, reversión con before/.
Evidencia, consultas reproducibles, copias previas, hashes, estado y punto de
reanudación en [incidente22-09](incidents/2026-09-22_FRONTAL_SPS_ALCANCE_ICEORYX.md).
La corrección del descubrimiento sigue vigente; no resuelve alcance ni Iceoryx.


## COMM-01-NO-SHM — 2026-09-22, Europe/Madrid

**DIAGNÓSTICO/ENSAYO TEMPORAL; NO INSTALADO en servicios persistentes.**
Motivo: mensaje UBTECH sobre Iceoryx/CycloneDDS y fallo22-09. Motion ya tiene
ROSA_MIDDLE_WARE=cyclone; biblioteca permite ROSA_USE_SHM=OFF. Override probado
sólo en docker exec de consulta: descubre ArmTask, estado de actuadores expira.
ROSA_USE_SHM=OFF ya existente en Vision self_check_service conservado.

Sin modificación remota persistente, reinicios, cambios de protecciones,
apagado ni movimiento. Se terminaron sólo dos consultas propias colgadas
(PID2533/2609), comando cotejado; finalizaron Z. Archivos PC modificados:
informe y enlaces documentales; bibliotecas leídas permanecen fuera de Git.
Receta reproducible, destinos exactos, hashes, dependencias, estado, evidencia,
backup, reversión y siguiente paso:
[informe de comunicación](support/CRUZR_CYCLONE_SIN_SHM_20260922.md).
Aplicación persistente, carga de servicios con OFF y prueba física PENDIENTES.


### COMM-01-NO-SHM / BOX-01-FRONT-SPS — aplicación22-09, Europe/Madrid

**VIGENTE: INSTALADO, CARGADO EN CLIENTES NUEVOS; PRINCIPALES SIN RECARGAR.**
Por «hazlo» se añade OFF al setup de Motion/HW; entrypoints comprobados cargan
ese archivo. Mismos contenedores, sin cambios de compose, reinicios o movimiento.
No se desactiva Iceoryx globalmente ni se alteran watchdogs. Nuevo paquete SPS
`a9eaf948512d2eb4` instalado, anterior a66aa conservado. Runtime check real rc0;
no prueba salud20D ni agarre. JSON de lecturas usa nivel ERROR por consulta.

Destinos exactos, hashes antes/después, instalador versionado con check/install/
rollback, backup externo verificado, dependencias, activación y limitación de
persistencia ante recreación: [ficha vigente COMM-01](support/CRUZR_CYCLONE_SIN_SHM_20260922.md#aplicacion-autorizada-del22-09-estado-vigente).
PC: supervisor/test SPS, instalador/test de upgrade, ambos ejecutores y ciclo
base para lecturas JSON, documentación. Sin cambios a tareas/trayectorias.
Reanudar tras confirmar brazos realmente asegurados, paro y procedimiento de
apagado/arranque supervisado; no se ha pedido repetir medidas de la caja.


### COMM-01-NO-SHM — preparación de activación,22-09 09:17 Europe/Madrid

Operador confirma HOME y brazos asegurados; lectura articular nueva compatible
con HOME e inmovilidad. Paros0/0: pendiente pulsación/confirmación del principal
antes del apagado controlado. Sólo diagnóstico y documentación; ningún reinicio,
apagado ni nuevo cambio remoto. Instalación anterior conservada, principales
sin recargar. [Estado y evidencia](support/CRUZR_CYCLONE_SIN_SHM_20260922.md).


### COMM-01-NO-SHM / BOOT-01 — 2026-09-22 09:31 CEST, carga tras encendido

**INSTALADO y CARGADO en robot_app/HW, verificado en entorno de procesos.**
Operador realizó la secuencia manual y comunica encendido con paro. Se conservan
IDs de contenedores y hashes setup/HOME; nueva fecha StartedAt07:26:09Z.
OFF/cyclone en robot_app PID64, rosa_control_node PID65 y ambos lanzadores PID1.
Boot check rc0 (Motion3/3, cámaras2/2, liberación técnica válida). Sólo lecturas
del agente; no nuevos cambios remotos ni movimiento. La configuración cargada
no demuestra aún salud20D/StartMotion ni resuelve alcance/IK de la caja.
Confirmación física de preparación para HOME pendiente antes de liberar.
Backup anterior conservado; rollback y límites de persistencia sin cambios.
[Evidencia y reanudación](support/CRUZR_CYCLONE_SIN_SHM_20260922.md).


### COMM-01-NO-SHM / BOOT-01 — 2026-09-22 09:38 CEST, recuperación y QoS

**Principales CARGADOS, arranque/HOME y lectura20D VERIFICADOS.** Operador
liberó; CC selfcheck sin error, StartMotion succ, JoystickMode. Ambas consultas
actuator_state del ciclo PC corregidas a BEST_EFFORT/VOLATILE y tipo explícito
para coincidir con publicador real. El defecto RELIABLE agotaba8s incluso
con tipo explícito; consulta corregida y preflight completo pasan. No se
relajan verificaciones ni se toca el publicador. Sin nuevas mutaciones remotas.
Fuente reproducible/activación: usar script PC actualizado, --check; no necesita
recarga. Backup del archivo anterior y hash final en evidencia; reversión
selectiva de esas consultas. Gate20D5tests, sintaxis/diff, lectura real y SPS
runtime correctos. Alcance/IK y agarre siguen sin resolver/validar.
[Receta, destinos, evidencia y reanudación](support/CRUZR_CYCLONE_SIN_SHM_20260922.md).


### BOX-01-FRONT-SPS — 2026-09-22 09:46 CEST, diagnóstico geométrico posterior

**Movimiento temporal de cabeza PROBADO, selección frontal VERIFICADA; agarre
PENDIENTE.** Sin archivos remotos nuevos. Receta versionada --prepare-vision
--yes de ciclo base; hash/XML originales verificados y preflight correcto.
Efecto actual: cabeza−0,430473rad, brazos cerca de HOME, inmóvil20D sin faults;
no restitución automática. Percepción genera sus imágenes diagnósticas normales.
Dos lecturas índice1 frontal baja, X≈0,80m en el borde permitido. Mapa vacío
y FSM_WAITSETMAP: no se navegó. Propuesto ensayo de avance5cm antes de nueva
medición, pendiente comprobación física de espacio/ruedas y preparación técnica.
Destinos, fuentes reproducibles, UUID, hashes, backup/reversión, límites y
evidencia: [registro de caja](box_handling/GET1_PUT1_MAPA_Y_EJECUTOR.md).


### BOX-01-FRONT-SPS / NAV-01 — 2026-09-22 09:55 CEST, ensayo de aproximación interrumpido

**Mapa cargado/localizado VERIFICADO; objetivo5cm FALLIDO y detenido.**
Operador confirmó espacio y ruedas navegación. Map_set+relocation nativos en
Motion/ROS2 cargan utars_nav_map; cabeza retornó cerca de HOME durante ese
proceso. Un navigation_start frontal fue interrumpido por retroceso5,11mm;
stop aceptado y postlectura independiente inmóvil, HOME/salud20D. Desplazamiento
neto7,503mm atrás. Sin agarre/reintento ni cambios de waypoints/protecciones.
Fuentes PC nuevas prepare_front_map.py/front_nudge.py/test_front_nudge.py.
Sin instalación permanente remota; efecto en ejecución mapa/localización/pose.
Helper actual --run bloqueado tras este incidente; --check sólo lectura.
Tres tests/sintaxis/diff pasan. Backups/hashes, destinos, receta, verificación,
rollback sin restitución física automática y punto de reanudación:
[ensayo de aproximación](box_handling/GET1_PUT1_MAPA_Y_EJECUTOR.md).


### NAV-01-ARC-DIAG / BOX-01-FRONT-SPS — 22-09-2026 10:10 CEST

Diagnóstico estático VERIFICADO: ArcPrecise inicia velocidad interna en
odom_vx−0,05; desde reposo reproduce primera consigna−0,04m/s. Nuevos archivos
PC InspectArcPrecise.java, analyze_arc_precise_start.py y perfil candidato
arc_precise_forward_only.candidate.yaml. **Sólo preparados; sin instalar,
cargar, probar físicamente ni cambiar runtime remoto.** Backups antes/después,
hashes, dependencias, receta offline, verificación y reversión en
[registro NAV-01-ARC-DIAG](box_handling/ARC_PRECISE_ARRANQUE_20260922.md).
El operador pide centrarse en el agarre; candidato aparcado, no próximo paso
obligatorio. Revisión de pose consumida, fallo IK y maniobra asimétrica sin
modificar tarea ni protecciones: [revisión del agarre](incidents/2026-09-22_FRONTAL_SPS_ALCANCE_ICEORYX.md#revision-centrada-en-el-agarre-22-09-2026).
Punto de reanudación vigente: trayectoria/alcance de caja frontal baja entre
laterales. No reiterar la selección ya demostrada ni dar el agarre por resuelto.


### BOX-01-FRONT-SPS / BOX-01-FRONT-STACK — 22-09-2026 10:58 CEST

Estado vigente: paquete `74f5507e44addd71`, sustituye `a9eaf948512d2eb4` como
selección usada por los wrappers. **Instalado y cargado/probado en percepción
nativa; agarre físico PENDIENTE.** Causa: empate angular de caja y soporte en
misma pila; objetivo superior frontal confirmado por operador. Selección por
columnas coherentes22±4cm, diámetroXY≤8cm, altura sólo dentro de columna;
rechazos entre pilas y controles físicos conservados. Diagnósticos incluyen
captura/TF en rechazos y FRONT_SPS_CAUSE en terminal.

Destinos Motion192.168.11.2 host `/var/tmp/cruzr-front-box/74f5507e44addd71/`,
contenedores Motion y ROS2 `/opt/cruzr-front-box/74f5507e44addd71/`. Instalador
versionado additive; ninguna tarea creada/sobrescrita, ningún reinicio ni
trayectoria; originales y límites intactos. Prueba nativa detect_only SUCCEED
actualizó cachébox/0, sesión cerrada. Preflight20D sano y quieto; no asumirHOME.
Backup externo de paquete anterior y fuentes PC, manifiesto con hashes,
receta, dependencias, verificación, rollback selectivo y evidencia:
[incidente y ficha](incidents/2026-09-22_FRONTAL_PILA_AMBIGUA.md).


### BOX-01-FRONT-SPS — 22-09-2026 11:22 CEST, recogida a cota baja fallida

Sin cambio remoto ni de adaptación instalada: paquete74f5507e44addd71 vigente.
Selección frontal consumida por Motion en goal52efbb3b…; escena nueva con
punto de cajaZ≈0,174m y X≈0,804m. Falla rangoX y búsqueda IK011; no extrapolar
el éxito perceptivo aZ≈0,794m a esta recogida. Agente sólo lee y documenta;
ningún cambio de script, límites, tareas, navegación o runtime. Backups,
replay, foto/poses exactas, estado y reanudación:
[informe de cota baja](incidents/2026-09-22_CAJA_FRONTAL_COTA_BAJA.md).


### BOX-01-FRONT-SPS — 22-09-2026 11:31 CEST, repetición de fallo de cota baja

Sin cambios remotos, de código o de adaptación: paquete74f5507e44addd71.
Lectura y replay confirman correcta selección/entrega del goale2b1c122…;
rechaza alcanceX e IK011 con punto aZ0,178277m. Sólo actualización documental,
backup/evidencia y reanudación en [incidente](incidents/2026-09-22_CAJA_FRONTAL_COTA_BAJA.md).
Próximo trabajo pendiente: validación de trayectoria baja, no reintento ciego.

### 28-09-2026 — diagnóstico HOME y comparación local de escenarios

VERIFICADO sólo lectura; sin nueva adaptación instalada, cambio operativo o
movimiento. `Task is running` tras inicio PICO explica por inferencia el rechazo
HOME; cliente remoto seguía abierto, estado terminal/salud/paros PENDIENTES.
[Recuperación](guides/CRUZR_S2_RECUPERACION_TRAS_CONTACTO_TELEOP.md) y
[comparación Canada/WRC–Zhucheng](vla/UBTECH_PROCEDIMIENTO_CAJAS_20260914.md#comparación-con-force_escenario1sh--28-09-2026).
Sólo notas PC; respaldo previo en `../Humanoide-vla-evidence/20260928T053746Z_FORCE_HOME_WAIT/before-docs-root/`
y `../Humanoide-vla-evidence/20260928T060905Z_SCENARIO_COMPARISON/before-docs/`.
Reversión: retirar selectivamente estas notas, sin restaurar estados de control.

### BOX-01-EXEC — 28-09-2026, revisión de mejoras sin implementación

Sólo documentación PC: [propuestas y hallazgo del paso vertical del selector](box_handling/GET1_PUT1_MAPA_Y_EJECUTOR.md#revisión-de-mejoras--28-09-2026).
Prueba sintética local confirma rechazo de dos detecciones separadas0,10m;
compatibilidad con cajas encajadas reales PENDIENTE de medidas. Sin cambios de
código, instalación, activación, robot o runtime. Backup previo y hashes de
fuentes: `../Humanoide-vla-evidence/20260928_FORCE_ESCENARIO1_REVIEW/`.
Reversión: retirar selectivamente estas notas y el enlace global desde before,
sin sobrescribir trabajo ajeno. No se modifica el estado instalado/cargado de BOX-01.

### BOX-01-EXEC-IMPROVED — 28-09-2026, Europe/Madrid

Estado: implementado en PC; VERIFICADO offline, integración/ensayo físico PENDIENTES.
Objetivo: ejecutor independiente con geometría actual, conforme a instrucción del
usuario, y supervisión de acciones/etapas. Destino: `scripts/force_improved_scenario1.sh`
y módulos/perfil/tests nuevos `scripts/box_handling/scenario1_*`/`test_scenario1_*`.
Fuentes, receta reproducible, dependencias, activación explícita y límites:
[guía del ejecutor](box_handling/FORCE_IMPROVED_SCENARIO1.md).

Instalado sólo en PC; entrada ejecutable. No cargado ni probado físicamente en
robot; no hubo conexión, instalación, cambio de configuración ni movimiento.
99 pruebas offline pasan, junto con sintaxis, ayuda/plan y diffcheck. Script
original y SPS conservan sus hashes. Backup documental, hashes finales y evidencia:
`../Humanoide-vla-evidence/20260928_IMPROVED_SCENARIO1_BUILD/`.
Rollback: retirar las fuentes nuevas y revertir selectivamente notas desde before;
no restaurar estados físicos ni sobreescribir cambios ajenos. Deuda: validar
--check en instalación real y después las etapas supervisadas; no atribuir
validación de alcance/depósito a las comprobaciones de percepción.

### BOX-01-EXEC-IMPROVED — corrección --check, 28-09-2026 09:06 CEST

Estado vigente: fuente PC corregida, preflight de lectura probado en robot;
ciclo físico PENDIENTE. Motivo: etiquetas Compose vendor cualificadas no
reconocidas y estado de acción retenido que el lector VOLATILE no recibía.
Destino: `scripts/box_handling/scenario1_checks.py`, `scenario1_runtime.py`,
`scenario1_cli.py` y sus tests. Añadidos aliases exactos, QoS canónico para el
estado de acciones y diagnóstico que distingue --check de ejecución interrumpida.

VERIFICADO:106 tests offline; --check real pasa hashes/controladores/salud/HOME
y retorna55 por mapa vacío/FSM_WAITSETMAP. Instalado sólo en PC; código de
consulta transmitido en memoria. Sin instalación persistente, cambios de mapas,
servicios/SDK, percepción, ArmTask, cancelación o movimiento en robot.
[Fuentes, comandos, evidencia, límites y rollback](box_handling/FORCE_IMPROVED_SCENARIO1.md#corrección-de-descubrimiento-y-estado--28-09-2026).
Backup antes de editar y hashes finales:
`../Humanoide-vla-evidence/20260928T070318Z_SCENARIO1_DISCOVERY_FIX/`.
Reversión: reposición selectiva desde before, conservando otros cambios.
Deuda: preparación autorizada de mapa y ensayo supervisado; el estado observado
no constituye autorización ni confirmación física reutilizable.

### BOX-01-EXEC-IMPROVED — políticas ask/assume/sensors, 28-09-2026, Europe/Madrid

Estado vigente: fuentes instaladas en PC; ensayo físico y cualificación sensorial
PENDIENTES. Motivo: petición de ejecución sin confirmaciones en cada etapa,
conservando una variante interactiva. Destinos exactos PC:
`scripts/ask_improved_scenario1.sh`, `scripts/force_improved_scenario1.sh`,
`scripts/force_improved_scenario1_autochecked.sh`, módulos/plantilla/tests
`scripts/box_handling/scenario1_*` y `test_scenario1_*`. Checkpoint v2 registra
la procedencia operador/asumida/sensores, sin promover suposiciones a medidas;
v1 sigue perteneciendo a ask. Reanudación sólo con la misma política.

La variante autochecked usa ROS2/rclpy estándar en el contenedor descubierto:
FT L/R WrenchStamped y whole_joint_states. Perfil por postura separado del
perfil geométrico, incluido con hash en el contexto; plantilla pending sin
umbrales inventados. `--run` requiere referencias cualificadas antes de conectar.
Visión conserva doble captura y TF del agarre; comprobación visual autónoma de
separación/liberación NO implementada. FT no demuestra esos hechos directamente.
No se alteran XML/YAML/SDK, protecciones ni geometría del proveedor.

Aplicación/activación: fuentes ejecutables ya disponibles; sin argumentos sólo
--check, movimiento sólo mediante --run/--resume. Receta, contratos, límites,
pruebas y calibración pendiente en la [guía](box_handling/FORCE_IMPROVED_SCENARIO1.md).
Respaldo ANTES de editar, fuentes previas y posteriores con hashes/evidencia:
`../Humanoide-vla-evidence/20260928T072132Z_SCENARIO1_POLICIES/`.
No requiere instalación persistente en robot; el recolector se transmite en
memoria y usa un directorio temporal /tmp/cruzr-scenario1-* con leases y salida.
Reversión: restaurar selectivamente fuentes previas de before; retirar sólo los
dos wrappers, recolector, evaluador y plantilla nuevos. Conservar los checkpoints
y no convertir políticas a mano. No sobrescribir cambios posteriores del usuario.
Deuda: calibración positiva/negativa por postura y montaje, validación física del
ciclo y cualquier verificación visual posterior al agarre.

VERIFICADO en esta ampliación:173 tests offline, sintaxis Bash, ayuda/plan de las
tres entradas y diffcheck. Shellcheck no instalado. --check real09:32 CEST recibe
16 muestras FT por muñeca en0,30s y27 articulares (22 nombres), con desfase L/R0;
HOME20D medido, paros0/0, cargador0, baterías83/84,6%. Mapa observado
utars_nav_map/FSM_WAITNAVIGATE; esta intervención no lo cargó ni relocalizó.
Retorno55 exclusivamente por perfil sensorial pendiente. No prueba agarre,
liberación ni contacto. Colector temporal finalizado; sin acciones físicas.
Evidencia de consulta:
`../Humanoide-vla-evidence/20260928T073255Z_IMPROVED_SCENARIO1_355885/`.
Fuentes exactas de esa consulta registradas por hash; las últimas mejoras de
integración (espera acotada/exclusión posicional de ruedas) se verifican offline.
Posiciones integradas de ruedas excluidas de la postura calibrada; su velocidad
sigue comprobándose. No hay datos cualificados de carga, tara o compensación
gravitatoria que permitan activar todavía el perfil sensorial distribuido.

### BOX-01-EXEC-IMPROVED — diagnóstico de latencia, 28-09-2026, Europe/Madrid

Estado histórico: diagnóstico VERIFICADO por código y diario local; la
optimización vigente se registra en la ficha siguiente.
Usuario ejecutó ciclo20260928T074311Z, con10 etapas completas y HOME20D medido;
no se confirma físicamente la caja, pues la política era assume. Intervalos
visión→agarre9,162s, agarre→retroceso18,317s y depósito→HOME20,988s. Hay11 pasadas
completas de descubrimiento/dependencias/salud: una inicial y una en cada etapa.
Los verify de caja asumida repiten chequeos que vuelve a hacer la siguiente
acción. El diagnóstico no envió consultas remotas ni movimiento.

Sólo cambian docs/PROJECT_SOURCE_OF_TRUTH.md, este índice y
[la guía con receta y resultados](box_handling/FORCE_IMPROVED_SCENARIO1.md#latencia-entre-etapas-observada--28-09-2026).
Ejecutor instalado/cargado sin cambios; sin activación o ensayo nuevo del agente.
Evidencia fuente: ../Humanoide-vla-evidence/20260928T074311Z_IMPROVED_SCENARIO1_382679/.
Backup previo, informe y hashes documentales:
../Humanoide-vla-evidence/20260928T074936Z_SCENARIO1_LATENCY_REVIEW/.
Reversión: retirar selectivamente estas notas desde before, preservando cambios
ajenos; no hay estado operativo que restaurar. Deuda: optimizar reutilización de
clientes/lecturas y redundancias conservando muestras frescas y requisitos técnicos.

### BOX-01-EXEC-IMPROVED — supervisión optimizada, 28-09-2026 10:07 CEST, Europe/Madrid

Motivo: petición «optimiza» tras observar pausas entre etapas. Estado vigente:
fuentes instaladas en PC y helpers cargados temporalmente para consultas reales;
VERIFICADO en lectura y offline, ciclo físico optimizado PENDIENTE. Se sustituyen
procesos de consulta repetidos por sesiones persistentes y se omite únicamente
el chequeo técnico duplicado de las dos verificaciones asumidas. Se mantienen
resultados, leases, salud fresca antes de cada etapa física, hashes completos,
llegada y HOME medido. Geometría, XML/YAML del proveedor y límites intactos.

Destinos PC modificados: `scripts/box_handling/scenario1_runtime.py`,
`scenario1_cli.py`, `scenario1_action_client.py`, `scenario1_checks.py` y
`test_scenario1_runtime.py`. Nuevos: `scenario1_dependencies.py`,
`scenario1_health_worker.py`, `scenario1_session.py`, y pruebas
`test_scenario1_dependencies.py`, `test_scenario1_health_worker.py`,
`test_scenario1_session.py`, `test_scenario1_action_session.py`,
`test_scenario1_optimization.py`, todos bajo `scripts/box_handling/`.
Documentación actualizada en la fuente global, este índice y la
[guía reproducible](box_handling/FORCE_IMPROVED_SCENARIO1.md#optimización-de-supervisión--28-09-2026).
Los tres wrappers utilizan estos módulos sin cambiar sus políticas.

Destino remoto temporal: host Motion y contenedores descubiertos
`walker-motion.manipulation_robot_app-1` / `walker-ros.ros2-1`; supervisor/helper
en memoria y directorios `/tmp/cruzr-scenario1-*` con leases. Dependencias:
ROSA instalado, tipos/QoS y `ListControllers` descubiertos, ROS2 para FT,
bundle SPS y hashes HOME/tareas/bibliotecas ya exigidos. Sin instalación o
servicios nuevos en robot. Activación: la siguiente invocación carga las fuentes
PC; por defecto sólo `--check`. Receta de medición sin movimiento:
`./scripts/force_improved_scenario1.sh --check --benchmark-checks 3`.

VERIFICADO: 242 pruebas offline, sintaxis Python/Bash, ayuda/plan y diffcheck;
shellcheck ausente. `--check` assume devuelve 0; tres rondas adicionales completas
de lectura tardan 2,945 / 4,485 / 4,495 s, pareja mapa/estado 0,106–0,113 s.
La consulta autochecked recibe FT/articulaciones y devuelve 55 por referencias
pendientes. No hay movimiento, carga/relocalización de mapa ni ciclo ejecutado
por el agente. La primera prueba reveló el requisito `wait_service(0)` nativo,
corregido y verificado antes de las mediciones finales. Se conservan evidencias
del fallo y del éxito; los helpers terminaron al cerrar sus sesiones.

Backup anterior, fuentes exactas posteriores, hashes/versiones e informe:
`../Humanoide-vla-evidence/20260928T075234Z_SCENARIO1_OPTIMIZATION/`
(`before/`, `after/`, `before-sha256.json`, `after-sha256.json`,
`changed-files.json`, `verification.json`). Consultas reales:
`20260928T075850Z_IMPROVED_SCENARIO1_423527/` (fallo inicial),
`20260928T080205Z_IMPROVED_SCENARIO1_432098/` (check reparado),
`20260928T080528Z_IMPROVED_SCENARIO1_442692/` (mediciones),
`20260928T080634Z_IMPROVED_SCENARIO1_446664/` (sensores), bajo el mismo directorio
externo de evidencias. Cada consulta conserva sus hashes propios.

Reversión: restaurar selectivamente archivos modificados desde `before/` y
retirar sólo los nuevos de `changed-files.json`, preservando trabajo posterior,
checkpoints y evidencias; no restaurar estados transitorios ni lanzar tareas.
No hay configuración persistente remota que revertir. Punto de reanudación:
medir el próximo ciclo físico autorizado. Deuda: latencia y cancelación durante
movimiento real, validación de la llegada con el nuevo lector durante navegación,
y cualificación sensorial por postura; las mediciones de lectura no las prueban.

### BOX-01-EXEC-IMPROVED — corrección de pose, 28-09-2026 10:16 CEST, Europe/Madrid

Estado vigente: instalado en fuentes PC, cargado temporalmente y VERIFICADO en
lectura; ciclo físico posterior PENDIENTE. Motivo: dos intentos del usuario
agotaron el plazo del lector de pose al terminar `navigate_get1`. El lector
introducido al optimizar exigía un publicador único, pero la unidad muestra dos
y transmite poses frescas. La comprobación anterior `--check` no probaba pose.

Destinos modificados bajo `scripts/box_handling/`: `scenario1_health_worker.py`,
`scenario1_checks.py`, `scenario1_runtime.py`, `scenario1_cli.py`,
`test_scenario1_health_worker.py`, `test_scenario1_optimization.py`; nueva prueba
`test_scenario1_pose_preflight.py`. También fuente global, este índice y
[guía/receta](box_handling/FORCE_IMPROVED_SCENARIO1.md#corrección-de-pose-con-dos-publicadores--28-09-2026).
Pose admite uno o más publicadores como el lector anterior; salud conserva la
unicidad. Se mantienen dos muestras nuevas/crecientes, VOLATILE, edad máxima,
marco map y tolerancia 5 cm/3°. Se comprueba el canal en `--check`, benchmark y
antes de navegar, y se vuelve a medir llegada después del movimiento.

Dependencias: ROSA y tipos/QoS ya instalados, sin cambios de SDK/XML/YAML,
efector, mapa o localización. Aplicación: la siguiente invocación de cualquiera
de las tres entradas usa los módulos corregidos. Activación de lectura:
`./scripts/force_improved_scenario1.sh --check --benchmark-checks 3`.
Host remoto Motion / contenedores descubiertos sin modificar; sólo procesos
temporales y sesiones `/tmp/cruzr-scenario1-*`, terminados tras comprobar.

VERIFICADO: 250 tests offline y consulta real con retorno 0; cuatro pares de
poses frescas, publisher_count 2, adquisición 0,14–0,20 s. La captura paralela
ROSA/ROS2 demuestra flujo nuevo y coherente, pero no atribuye mensajes a cada
GID: no inferir que el segundo publicador sólo retiene información antigua.
Los intentos fallidos no enviaron agarre ni acciones Motion. Sus checkpoints
siguen fallidos y no reanudables. El agente no envió movimientos ni reinicios.

Evidencia de causa: `../Humanoide-vla-evidence/20260928T081314Z_POSE_DISCOVERY/`.
Check final: `../Humanoide-vla-evidence/20260928T081557Z_IMPROVED_SCENARIO1_475758/`.
Backup anterior, fuentes finales, hashes/versiones e informe reproducible:
`../Humanoide-vla-evidence/20260928T081354Z_SCENARIO1_POSE_FIX/`
(`before/`, `after/`, `before-sha256.json`, `after-sha256.json`,
`changed-files.json`, `verification.json`). Reversión selectiva desde `before/`
y retirada de la prueba nueva; preservar cambios ajenos y evidencias. No hay
configuración remota persistente que restaurar. Esa reversión reinstala el
defecto y no debe confundirse con recuperación física. Deuda: ensayo físico
posterior y validación de localización visual; `VSLAM_LOCATION_LOST` no queda
resuelto por corregir el lector.

### BOX-01-EXEC-IMPROVED — retirada de mesa73, 28-09-2026 11:08 CEST, Europe/Madrid

Estado vigente: adaptación de altura RETIRADA por solicitud del usuario antes
del ensayo. Restaurados exactamente desde el respaldo previo PC:
`scripts/box_handling/scenario1_cli.py`, `scenario1_contract.py` y
`scenario1_runtime.py`; hashes comprobados. Retirados los nuevos
`scenario1_deposit.py`, `scenario1_deposit_install.py`,
`test_scenario1_deposit.py` de ese directorio y
`config/box_handling/scenario1_put1.json`. Conservadas todas las mejoras previas,
incluida pose con dos publicadores, y cambios ajenos. El depósito vuelve a
`wrc_cruzr/put_cruzr_wrc_low`; no hay altura73 activa ni instalador nuevo.

Origen reproducible: `../Humanoide-vla-evidence/20260928T090113Z_SCENARIO1_TABLE73_BUILD/before/`
y `before-sha256.json`. Reversión efectuada, archivos descartados archivados y
comprobaciones: `../Humanoide-vla-evidence/20260928T090823Z_SCENARIO1_TABLE73_ROLLBACK/`
(`rollback.json`, `discarded/`, `unit-tests.txt`). Fuentes del estado vigente
coinciden con el respaldo, sin depender del estado de HEAD. Verificación: 250
tests offline, plan original y diffcheck. No instalación ni comandos físicos
durante preparación o reversión; sólo lecturas técnicas previas en
`20260928T085846Z_SCENARIO1_TABLE73_READONLY/` bajo el mismo directorio externo.

No hay estado operativo remoto que restaurar. No reactivar automáticamente el
perfil retirado; un trabajo futuro requiere completar su registro geométrico y
una nueva petición del usuario. La prueba de73cm está cancelada. Detalle y punto
vigente de uso en la [guía](box_handling/FORCE_IMPROVED_SCENARIO1.md#adaptación-a-mesa-de-73-cm-revertida--28-09-2026).


### BOX-01-EXEC-IMPROVED — llegada get1 2 cm/2°, 28-09-2026 12:10 CEST, Europe/Madrid

Estado vigente: instalado en fuentes PC; cargado en robot y probado físicamente
PENDIENTES. Objetivo autorizado: endurecer exclusivamente el criterio de llegada
a `get1`, utilizando las dos muestras ya existentes. Distancia planar ≤0,02 m,
giro ≤2°; `put1` conserva ≤0,05 m/3°. Un fallo interrumpe antes de visión/agarre;
no añade correcciones, reintentos, lecturas ni pausas.

Destino exacto PC bajo `/home/lacuna/proyectos/Robots/Humanoide/`:
`scripts/box_handling/scenario1_checks.py`, `scenario1_runtime.py`,
`test_scenario1_checks.py`, `test_scenario1_pose_preflight.py`; fuente global,
guía de transferencia y [guía/receta específica](box_handling/FORCE_IMPROVED_SCENARIO1.md#tolerancia-de-get1-de-2-cm-y-2--28-09-2026).
Constante reproducible `ARRIVAL_TOLERANCES`; todos los destinos se pasan
explícitamente al validador. Eventos y errores registran los límites aplicados.

Dependencias: lector de pose, supervisión y contratos existentes; ningún cambio
de SDK, mapa, localización, XML/YAML, parámetros de navegación o robot. Las tres
entradas mejoradas usan automáticamente las fuentes en su siguiente invocación;
no hay recarga de servicios. Las entradas antiguas conservan su criterio.
VERIFICADO: 259 pruebas locales, sintaxis, ayuda, plan y `git diff --check`.
Resultado exacto y alcance en `verification.json` y `unit-tests.txt`
del directorio de evidencia. No se ejecutaron consultas remotas ni movimientos.

Backup de contenido anterior, HEAD de referencia, estado Git, fuentes finales
y SHA256 completos en
`../Humanoide-vla-evidence/20260928T101004Z_SCENARIO1_GET1_TOLERANCE/`
(`before/`, `after/`, `before-sha256.json`, `after-sha256.json`,
`changed-files.json`, `verification.json`). Reversión selectiva desde `before/`
conservando cambios ajenos/posteriores; no hay rollback remoto. No se modifican
el tag `v0.0.1` ni los archivos no versionados del trabajo de altura pendiente.
Punto de reanudación: comprobar el estado físico actual y efectuar un ensayo
de llegada autorizado antes de declarar repetibilidad o tiempos físicos.


### BOX-01-EXEC-IMPROVED — navegación exclusiva a get1, 28-09-2026 12:19 CEST, Europe/Madrid

Estado: instalado en fuentes PC, cargado temporalmente y PROBADO FÍSICAMENTE
para una navegación exclusiva. Nueva opción `--stop-after get1`; una única
etapa, mantiene preflight/lease/locks/doble muestra y omite arranque SPS. No
permite continuar desde ese checkpoint hacia agarre. Motivo: medir el error de
llegada 2 cm/2° sin ejecutar la recogida.

Destinos PC bajo `/home/lacuna/proyectos/Robots/Humanoide/`:
`scripts/box_handling/scenario1_cli.py`, `scenario1_contract.py`,
`scenario1_runtime.py`, `test_scenario1_contract.py` y nuevo
`test_scenario1_navigation_only.py`; fuente global y guías de transferencia/ejecutor.
Dependencias: las mismas de la supervisión vigente, sin instalar tareas/SDK ni
cambiar mapa/controladores. Activación, receta y rollback en la
[guía](box_handling/FORCE_IMPROVED_SCENARIO1.md#prueba-de-navegación-exclusiva-a-get1--28-09-2026).

VERIFICADO: 269 pruebas del ejecutor, plan, diffcheck; check y postcheck reales
rc0. Una navegación autorizada goal3e98a8d1… da dos errores3,882/3,883mm y
0,439/0,440°. Postcheck3,923mm/0,284°, HOME20D/velocidad articular0,
paros0/0/cargador0. Acción12,086s; etapa15,832s. Medición por localización del
mapa, sin referencia física externa; repetibilidad PENDIENTE. Persiste aviso
auxiliarVSLAM_LOCATION_LOST. No inferir reparación de visión ni mejora del
controlador a partir de este único ensayo.

Destino en ejecución: Motion192.168.11.2, contenedores redescubiertos e
identificados en `run/context.json`; scripts/procesos temporales
`/tmp/cruzr-scenario1-*`, terminados. Sólo una navigation_start, sin agarre,
apertura, HOME, SPS, reintentos, edición de mapa ni relocalización explícita.
Robot termina junto a get1; no se restaura automáticamente su posición inicial.

Backup previo que conserva el cambio2cm/2°, fuentes finales/hashes, autorización
y evidencia en
`../Humanoide-vla-evidence/20260928T101642Z_SCENARIO1_GET1_TRIAL/`
(`before/`, `after/`, `before-sha256.json`, `after-sha256.json`,
`changed-files.json`, `verification.json`, `arrival-report.json`,
`check/`, `run/`, `postcheck/`). Software reversible selectivamente desde
`before/`, retirando sólo el test nuevo y preservando cambios ajenos. Sin
rollback remoto persistente ni recuperación física automática. Punto de
reanudación: consultar estado fresco antes de una siguiente tarea autorizada.


### BOX-01-EXEC-IMPROVED — ajuste acotado de get1, 28-09-2026 12:35 CEST, Europe/Madrid

Estado vigente: instalado en fuentes PC; supervisor/lectores cargados
temporalmente y verificados en lectura; maniobra correctiva física PENDIENTE.
Motivo autorizado: corregir automáticamente un residual de get1 y continuar
únicamente cuando las dos poses cumplan 2 cm/2°. Hasta dos ajustes después de
un resultado exitoso, entrada máxima5cm/5°, vigilancia de posición/odometría,
velocidad, recorrido, progreso y reposo final. Fallos técnicos no reintentables;
put1 conserva su comportamiento. La llegada que ya cumple no añade consultas.

Destino PC exacto bajo `/home/lacuna/proyectos/Robots/Humanoide/`:
`scripts/box_handling/scenario1_checks.py`, `scenario1_runtime.py`,
`scenario1_action_client.py`, `scenario1_cli.py`, nuevo
`scenario1_nav_correction.py`; tests nuevos `test_scenario1_nav_correction.py`,
`test_scenario1_correction_transport.py`, `test_scenario1_navigation_correction.py`
y ajuste de `test_scenario1_pose_preflight.py`. Documentación global, guía de
transferencia y [fuente/receta especializada](box_handling/FORCE_IMPROVED_SCENARIO1.md#ajuste-automático-acotado-de-get1--28-09-2026).
Dependencias: supervisión previa, API ROSA revisada y topics nativos
`/nav/robot_pose` y `/mc/odom`. El CLI incorpora el guard en memoria en ambos
procesos; se activa con la próxima invocación de cualquiera de las tres entradas.
Sin cambios persistentes de robot, SDK, XML/YAML, mapa o controlador.

Verificación: 355 pruebas offline en `unit-tests.txt`/`verification.json`,
plan local y --check remoto rc0; prueba de lectores con dos publicadores de mapa
y uno de odometría, datos nuevos/estacionarios y guard de reposo satisfecho,
sin objetivos físicos. Motion
192.168.11.2, roles redescubiertos en `check/context.json`; supervisor bajo
`/tmp/cruzr-scenario1-*` y colector nativo en memoria, ambos finalizados.
No ejecución física de correcciones ni de ciclo/agarre/HOME en esta intervención.
La precisión se refiere a la localización del mapa, sin medición externa.

Evidencia y hashes completos:
`../Humanoide-vla-evidence/20260928T102716Z_SCENARIO1_GET1_CORRECTION/`
(`before/`, `after/`, `before-sha256.json`, `after-sha256.json`,
`changed-files.json`, `verification.json`, `unit-tests.txt`, `check/`,
`probe.stdout`, `probe-final.stdout`, `probe-final-source-hashes.json`). El respaldo incluye cambios locales
previos. Reversión selectiva desde `before/`, retirar sólo módulo/tests nuevos
de esta adaptación y conservar trabajo posterior; sin rollback operativo remoto.
No tocar v0.0.1 ni la adaptación de altura pendiente. Punto de reanudación:
ensayo correctivo autorizado con estado físico fresco; cancelación/alcance de
frenado y tiempo real siguen pendientes. Receta y límites en la guía enlazada.


### BOX-01-EXEC-IMPROVED — sello articular, 28-09-2026 12:50 CEST, Europe/Madrid

Estado: instalado en fuentes PC y cargado temporalmente en Motion para lectura;
ciclo físico corregido y causa exacta del fallo PENDIENTES. Motivo: usuario
reporta `Nonadvancing actuator source timestamp` en salud de retreat después
del agarre. Diario104306 confirma cero despachos posteriores al agarre. Usuario
confirma caja sujeta/separada; se conserva checkpoint fallido, no reanudable.

Destino PC bajo `/home/lacuna/proyectos/Robots/Humanoide/`:
`scripts/box_handling/scenario1_health_worker.py`,
`scripts/box_handling/test_scenario1_health_worker.py`, registro global y guías.
Fuente, receta, dependencias y límites en la
[guía especializada](box_handling/FORCE_IMPROVED_SCENARIO1.md#sello-articular-repetido-o-regresivo-antes-de-retreat--28-09-2026).
Descarta sólo duplicados articulares idénticos sin renovar frescura ni contar
otra muestra. Conserva bloqueo de regresiones/conflictos/congelación y añade
diagnóstico de sellos/hashes. Activación en próxima invocación de las tres
entradas, a través del módulo embebido; no instalación ni reinicio remoto.

Verificación: 31 tests del lector y 364 pruebas de regresión completa en evidencia; 10 s/500 mensajes
nativos y 5 peticiones salud no reproducen fallo. Nuevo lector exige dos muestras
nuevas por petición, valida salud/controlador, observa velocidad 0/no HOME.
No se ejecutó --check inicial con requisito HOME ni se movió el robot.
Destino temporal: Motion 192.168.11.2/contenedor redescubierto en
`stamp-probe.stdout` y `health-qualification.stdout`; procesos de sólo lectura
en memoria terminados. Sin modificaciones persistentes de robot/SDK/tareas.

Respaldo previo que preserva ajustes get1, fuentes finales, hashes y resultados:
`../Humanoide-vla-evidence/20260928T104807Z_SCENARIO1_ACTUATOR_TIMESTAMP/`
(`before/`, `after/`, `before-sha256.json`, `after-sha256.json`,
`changed-files.json`, `verification.json`, `unit-tests.txt`,
`incident-reference.json`, `stamp-probe.json`, `health-qualification.json`).
Reversión selectiva del módulo/test desde `before/`, conservar trabajo posterior
y actualizar documentación; sin rollback operativo remoto. Causa original no
distinguible con el antiguo diagnóstico. Reanudar mediante preparación específica
de recuperación desde caja sujeta, con estado físico fresco y autorización de
movimiento; no editar checkpoint para ocultar su fallo ni reiniciar ciclo/HOME.


### BOX-01-EXEC-IMPROVED — resume por etapa, 28-09-2026 13:12 CEST, Europe/Madrid

Estado vigente: instalado en PC y cargado temporalmente en Motion para --check;
continuación física PENDIENTE. Motivo autorizado: permitir --resume desde
cualquier etapa. Fallos/etapas inciertas/saltos requieren --box-state y
--recovery-confirmed; siguen vigentes postura, salud, odometría estacionaria,
localización de entrada y contexto. Mismo perfil/política/boot/contenedores y
dependencias. Registro v3 guarda sólo segmento real y origen, sin modificar ni
ocultar el fallo anterior. Archivo de procedencia no ejecutable como checkpoint;
origen consumido sólo antes de arm y primera etapa revalida la entrada.

Destino PC exacto bajo `/home/lacuna/proyectos/Robots/Humanoide/`:
`scripts/box_handling/scenario1_cli.py`, `scenario1_contract.py`,
`scenario1_runtime.py`; nuevos `scenario1_resume.py`, `scenario1_resume_worker.py`,
`test_scenario1_resume.py`, `test_scenario1_resume_worker.py`,
`test_scenario1_resume_runtime.py`; registro global y guías. Fuente y receta:
[reanudación por etapa](box_handling/FORCE_IMPROVED_SCENARIO1.md#reanudación-por-etapa--28-09-2026).
Activación automática con próxima invocación; helper nativo embebido en memoria.
Dependencias: lector y contratos existentes, API ROSA y `/mc/odom`; referencias
FT cualificadas adicionales para la entrada autochecked. No modificación del
SDK/robot/mapa/XML/YAML ni reinicio de servicios. SPS sólo si el tramo incluye agarre.

418 pruebas offline correctas; detalle en unit-tests.txt/verification.json. --plan real del
incidente 104306 selecciona retreat→navigate_put1→deposit→verify_released→home→
verify_home. --check correspondiente rc0, salud sin exigir HOME para held,
dos poses get1 a 11,240 mm/0,156° y dos odometrías quietas. Sin arm, consumo,
etapas ni objetivos físicos. Procesos de lectura en Motion 192.168.11.2,
contenedores redescubiertos/contexto coincidente, terminados. La comprobación
de lectura no se registra como ejecución física ni autorización de movimiento.

Backup previo, versiones/hashes exactos y resultados:
`../Humanoide-vla-evidence/20260928T110310Z_SCENARIO1_RESUME_STAGES/`
(`before/`, `after/`, `before-sha256.json`, `after-sha256.json`,
`changed-files.json`, `unit-tests.txt`, `verification.json`, `check-retreat/`, `check-final/`).
Reversión selectiva de CLI/contrato/runtime a before y retirada sólo de dos
módulos/tres tests nuevos, preservando cambios previos/posteriores; actualizar
documentación. No rollback de configuración remota ni borrado de marcadores de
consumo para repetir un movimiento. Punto de reanudación: operador comprueba
estado físico actual y elige etapa; continuación física de recuperación pendiente.


### BOX-01-EXEC-IMPROVED — bloqueo corrección free_nav, 28-09-2026 13:29 CEST, Europe/Madrid

Estado vigente: fuentes PC instaladas; carga al próximo inicio; maniobra
correctiva automática BLOQUEADA. Solicitud: evitar repetición del incidente
112349. Causa observada: norma angular0,26143>0,25rad/s durante corrección pese
solicitar0,15. Variante nativa no cualificada; se conservan todos los límites,
2cm/2° de llegada y flujo normal cuando cumple. Ante residual persistente,
bloqueo antes del segundo objetivo y del agarre, con residual y motivo legibles.
Esta ficha sustituye la disponibilidad correctiva de12:35 sin borrar su historia.

Destino exacto PC bajo `/home/lacuna/proyectos/Robots/Humanoide/`:
`scripts/box_handling/scenario1_nav_correction.py`, `scenario1_runtime.py`,
`scenario1_action_client.py`, `scenario1_cli.py`; tests
`test_scenario1_nav_correction.py`, `test_scenario1_navigation_correction.py`,
`test_scenario1_correction_transport.py`, `test_scenario1_policies.py`; guías/global/este índice.
Fuente y receta reproducibles: [sección de la incidencia](box_handling/FORCE_IMPROVED_SCENARIO1.md#bloqueo-de-corrección-free_nav-por-velocidad--28-09-2026).
Aplicación/activación: próximos arranques de las tres entradas incorporan
módulos PC en memoria; `--plan` expone el bloqueo. No instalador remoto, edición
del proveedor ni reinicio. Dependencias y configuración previa conservadas.
No activar ni reducir límites usando overrides; no existe flag de excepción.

Verificación: regresión de velocidad exacta y bloqueo antes de arm/send,
llegadas dentro y fuera de tolerancia, fallo duradero y ausencia de agarre.
428 pruebas correctas, sintaxis/planes y hashes exactos en `verification.json`; prueba física
PENDIENTE. No conexiones ni objetivos físicos del agente en esta intervención.
El registro ahora conserva muestra/sellos/fase/umbrales ante exceso; no da por
verificados el estado físico o localización visual actuales.

Backup y evidencia (incluyen trabajo local previo sin commit):
`../Humanoide-vla-evidence/20260928T112641Z_SCENARIO1_CORRECTION_VELOCITY/`,
`before/`, `after/`, manifests SHA256 y `changed-files.json`.
Reversión selectiva desde before conserva cambios ajenos; reactivaría una
maniobra incompatible observada y no resuelve el fallo. Sin rollback remoto.
Deuda/punto de reanudación: controlador de ajuste con límites efectivos de todas
las fases, activación y ensayo específico todavía PENDIENTES. No restaurar el
candidato ArcPrecise ni relanzar free_nav bajo otra velocidad JSON por esta ficha.


### BOX-01-EXEC-IMPROVED — reactivación supervisada get1, 28-09-2026 14:02 CEST, Europe/Madrid

Estado vigente: habilitado en fuentes PC con validación física PENDIENTE.
Petición explícita: que el robot se posicione, relajando velocidad cuando sea
adecuado. Sustituye el bloqueo13:29. Perfil supervisor adaptado a curva Arc y
giro final; llegada2cm/2° sigue obligatoria. No modificación de control nativo.

Destino PC bajo `/home/lacuna/proyectos/Robots/Humanoide/`:
`scripts/box_handling/scenario1_nav_correction.py`, `scenario1_cli.py`, tests
`test_scenario1_nav_correction.py`, `test_scenario1_navigation_correction.py`,
`test_scenario1_correction_transport.py`, `test_scenario1_policies.py`,
fuente global, guía de transferencia, guía del ejecutor y este índice.
Fuente/receta: [reactivación supervisada](box_handling/FORCE_IMPROVED_SCENARIO1.md#reactivación-supervisada-del-ajuste-get1--28-09-2026).
Activación al próximo inicio de las tres entradas mediante módulos en memoria;
`--plan` muestra parámetros y validación física pendiente. Dependencias previas,
navegación/anticolisión nativa y DDS conservados. No reinicio, instalación
remota ni cambios de SDK/mapa/tareas; efector y altura pendientes ajenos intactos.

Límites medidos: angular0,60rad/s,1,20 sólo con dosposesfrescas≤2cm y
linear≤0,02m/s; cotalinear0,10m/s. Giro geométrico2×bearing+errorfinal+15°,
cap195°, acumulado cap400° integrado sinwrap; centro8cm/ruta12cm conservados;
empeoramiento15mm, acción30s,total70s,máximo2. Progreso reconoce orientación
hacia desplazamiento y luego yawfinal, sin renovación por oscilación del umbral.
Controles de salud/HOME, reposo antes/después, edad, cancelación y fallo duradero
conservados. Los límites no garantizan convergencia ni frenado y no acotan el
barrido exterior; prueba física acotada pendiente con zona libre para giro.

Verificación local:446 pruebas correctas, AST/bash, --help/--plan de las tres entradas; resultados
exactos en `verification.json`. Sin conexiones ni objetivos físicos del agente.
Backup/hash de trabajo previo y fuentes finales:
`../Humanoide-vla-evidence/20260928T115136Z_SCENARIO1_CORRECTION_REENABLE/`.
Reversión selectiva de archivos de `changed-files.json` desde `before/`,
preservando cambios posteriores y registrando estado; devuelve bloqueo total.
No rollback físico ni modificación de checkpoints fallidos. Pendiente ensayo
`--stop-after get1` y continuación de ciclo, con estado físico fresco.


### BOX-01-EXEC-IMPROVED — consola resumida, 28-09-2026 14:43 CEST, Europe/Madrid

Estado vigente: **instalado en fuentes PC; VERIFICADO offline; prueba física
PENDIENTE**. Motivo: JSON de feedback a unos 50 Hz dificulta leer el progreso.
Se presentan etapas en español, tiempos redondeados, feedback normal repetido a
un máximo de 1 Hz por objetivo y avisos inmediatos, incluidos los de cancelación
posteriores al fallo. `--verbose` recupera todos los eventos en consola;
`events.jsonl` siempre conserva el flujo original completo antes del formateo.

Destino bajo `/home/lacuna/proyectos/Robots/Humanoide/`:
`scripts/box_handling/scenario1_console.py` (nuevo), `scenario1_cli.py`, nuevo
`test_scenario1_console.py` y ajustes de dobles de conexión en tests policies,
navigation_only y resume_runtime; fuente global, guía de transferencia, guía del
ejecutor y este índice. Fuente/receta reproducible:
[consola resumida](box_handling/FORCE_IMPROVED_SCENARIO1.md#consola-resumida--28-09-2026).
Dependencia: Python estándar; tres wrappers existentes. Activación al siguiente
inicio; formateador sólo PC, no enviado al robot. Hash incluido en evidencia de
cada ejecución. No cambia trayectorias, controles, límites ni protocolo remoto.

Versión/hash: `before-sha256.json` y `after-sha256.json`; backup y fuentes en
`../Humanoide-vla-evidence/20260928T123214Z_SCENARIO1_CONSOLE/`, directorios
`before/` y `after/`. `verification.json` y `unit-tests.txt` registran el resultado
exacto de las pruebas locales, más planes/ayuda y sintaxis; `console-sample.txt`
contiene una muestra sintética. Sin conexiones, cambios remotos ni movimientos.
Reversión: restauración selectiva de `changed-files.json` desde `before/` y
retirada de los archivos nuevos después de restaurar el cliente, preservando
trabajo posterior; actualizar esta ficha. No restaurar checkpoints ni estados
transitorios. Validación de la presentación en una próxima ejecución real queda
pendiente; no hay deuda de instalación remota. Sin commit/push.


### BOX-01-EXEC-IMPROVED — incidente de caja del fondo, 28-09-2026, Europe/Madrid

**VERIFICADO:** la sesión144311 prefirió por menor ángulo una caja baja posterior
X1,192 m frente a otra cercana0,794 m. Motion registró fuera de límiteX0,8 m,
continuó IK/trayectoria y descendió las manos haciaZ0,11 en su marco interno.
El operador pulsó E-stop; error articular posterior y reinicios automáticos de
hw/manipulación. La captura RGB-D guardada confirma la disposición. No hay una
corrección instalada ni validación de alcance por el selector; estabilidad entre
capturas no sustituye selección de la pila deseada ni límite duro de ejecución.
Contención operativa: no repetir montaje/agarre ni reanudar/HOME desde esta postura.

Destino de esta intervención: documentación PC, informe
[ULTIMA_CAJA_FONDO_ESTOP](incidents/2026-09-28_ULTIMA_CAJA_FONDO_ESTOP.md), fuente
global, guías de transferencia/recuperación/ejecutor y este índice. No cambios
persistentes de control, parámetros, servicios, contenedores ni tareas. No
reinicios, rearme, apagado ni objetivos enviados por el agente. Las lecturas
Docker/archivos y copia de imágenes no activaron detección ni movimiento.

Evidencia, versiones, recetas de consultas y hashes:
`../Humanoide-vla-evidence/20260928T145208Z_LOWEST_BOX_ESTOP/`.
Incluye antes/después documental, fuentes PC, cuatro sesiones, configuración
viva, logs, RGB-D/estéreo y reportes comparativos. Verificación: reproducción
local de selección, contraste de poses/logs/cámara y orden de etapas; no ensayo
físico del agente. La consulta posterior de paros falló por No route to host;
no afirmar apagado. Operador confirma estabilidad y abrazaderas vacías;
apagado y nuevo encendido con E-stop realizados después por el operador, que
confirma conservar la postura inclinada. Recuperación física PENDIENTE; no
liberar paro para ejecutar HOME interno. Lectura del nuevo arranque separada
de las evidencias anteriores.

Activación: sólo información operativa/documental; scripts de control siguen
sin modificación. Dependencias y límites técnicos conservados; recomendaciones
de selección vinculada a pila y rechazo efectivo fuera de alcance pendientes de
implementar/revisar/ensayar. Reversión documental selectiva desde `before/`,
preservando cambios posteriores; no hay rollback remoto ni de checkpoints.
No retirar evidencia del incidente para presentar el montaje como validado.


HOME-V8-AUTO-01 relacionado, lectura posterior al nuevo encendido: home.xml vivo
SHA d9e9462792b41300d352604b53ea2a4890a9382e942321990708f6ded2e26ccb,
boot Motion cd0b8a7b-94d6-4fa2-a56b-561d13a603f2. Primera fase v8 mueve cuerpo
3,75 s en paralelo con ajustes de brazos desde el inicio, luego bajada7 s y
cierre2,7 s; no es torso primero con brazos inmóviles. No hay gate de distancia
al suelo ni validación de la postura de las fotos. Se actualiza también
`docs/teleoperation/CRUZR_HOME_V8_CANDIDATA.md`, con backup en la evidencia del
incidente. Telemetría posterior verifica principal1/servo0, HW esperando start
y manipulación esperando ListControllers. Sólo lectura, sin liberar paro ni
llamar start/HOME. Recuperación física pendiente.


BOX-01-EXEC-IMPROVED, actualización28-09-2026 17:11 CEST: operador confirma
abrazadera apoyada en suelo tras nuevo encendido. Sólo consulta pasiva:
principal1/servo0, ActuatorState Writer0, sin JointState/muestra de20ejes. No
trayectoria remota ni HOME autorizados desde ese contacto; recuperación
presencial/servicio UBTECH pendiente. Sin objetivo, servicios o cambios remotos.
Evidencia y backup documental:
`../Humanoide-vla-evidence/20260928T151006Z_RECOVERY_POSTURE_READONLY/`.
Destino PC: informe del incidente, fuente global, guía de recuperación y este
índice; no software modificado. Receta de lectura: funciones execute/ros de
`scripts/collect_estop_available_readonly.py` con comandos exactos guardados en
`results.json`. Hashes antes/después, verificación documental y rollback selectivo
preservando cambios posteriores; no hay activación ni rollback remoto. Paquete
preparado para soporte, sin comunicación enviada a terceros.


### BOX-01-FRONT-SPS / BOX-01-FRONT-DEPTH-GATE — 28-09-2026, Europe/Madrid

**INSTALADO** `bf145fa17e1116fc`, reemplaza la selección angular exclusiva de
`74f5507e44addd71` para nuevas sesiones. Motivo: incidente144311 entregó caja
posterior1,192 m; Motion permitió IK pese al aviso de límite0,8 m.
Fuentes cambiadas PC: `scripts/box_handling/select_front_box.py` y
`front_sps_contract.py`; pruebas de selector/contrato, dos suites nuevas y fixture
numérica saneada de cuatro sesiones. Scripts de entrada calculan ID desde fuentes.

Regla: agrupar pilas como antes, ordenar delante/detrás sólo dentro de franja
Y80 mm y cimasZ40 mm, rechazar cadenas/alturas ambiguas; después comprobar posición
seleccionada. Gate exact-time base_link XYZ [.41,.79]/[-.39,.39]/[.01,1.49] m,
reserva10 mm, en ambas respuestas SPS. No filtrar por alcance para elegir otra
caja, no alterar medición ni ampliar límites originales. El margen no es una
cota calibrada de TF ni certificación IK/colisión. Sin consultas adicionales.

Destino Motion: host `/var/tmp/cruzr-front-box/bf145fa17e1116fc/` y
`/opt/cruzr-front-box/bf145fa17e1116fc/` en contenedores redescubiertos
`walker-motion.manipulation_robot_app-1` y `walker-ros.ros2-1`.
Instalación aditiva: seis fuentes, manifiesto/recibo; tareas compartidas ya iguales,
created_tasks=[], sin originales sobrescritos, reinicios ni comandos de movimiento.
Dependencias XML/YAML/binarios y verificación por hashes conservadas. Carga de
adaptador al próximo ciclo; el paquete previo queda como evidencia histórica.
Ensayo físico con paquete nuevo PENDIENTE. Operador comunica HOME recuperado,
no nueva medición HOME del agente. No se tocaron procesos de percepción residuales.

Evidencia/copia antes/después/manifiestos:
`../Humanoide-vla-evidence/20260928T153324Z_FRONT_BOX_DEPTH_GATE/`.
Bundle SHA256 `2aacf0d3cab182f596ee0c4b7f2eeb2b9ebab3f01e0b69bd62641af4a1abcd28`.
Receta reproducible, resultados de tests/lecturas, activación y rollback selectivo:
[FRONT_BOX_DEPTH_GATE_20260928](box_handling/FRONT_BOX_DEPTH_GATE_20260928.md).
Revertir sólo fuentes de esta adaptación preservando trabajo posterior devuelve
el ID anterior, pero reintroduce el defecto: no usarlo para repetir el incidente.
No restaurar checkpoints/cachés ni borrar tareas compartidas. Sin commit/push.


### BOX-01-EXEC-OPTIMISTIC — 28-09-2026, Europe/Madrid

**IMPLEMENTADO en PC; carga temporal y lectura real VERIFICADAS; ensayo físico
PENDIENTE.** Nueva entrada `scripts/optimistic_scenario1.sh`, policy`assume`,
execution_profile`optimistic_v1`. Motivo: eliminar la repetición de adquisiciones
completas de salud que consume≈3–5 s entre etapas; no crear un permiso ciego.
Se mantienen preflight, entrada de recuperación y HOME final completos, identidad
por hashes/contenedores, dos muestras articulares posteriores al resultado en
reposo, éxitos de aplicación, llegada2cm/2° y selector/rechazoXYZ SPS.

Fuentes PC modificadas: CLI, runtime, contrato, reanudación y lector de salud
`scenario1_*.py`; nuevos `scenario1_live_health.py`, wrapper y tres suites de
pruebas. Transmisión en memoria al iniciar, al host Motion y al proceso nativo
ROSA en `walker-motion.manipulation_robot_app-1`; no instalación permanente,
recarga de servicios ni cambio de los seis módulos SPS`bf145fa17e1116fc`.
`live-health.json` temporal, reemplazo atómico20Hz, modo0644 en sesión privada0700
para compartir root del contenedor con walker del host. Segundos cliente y
consultas ListControllers son sólo lectura; cadencia de consulta≈1 s.

Cadencias medidas pasivamente durante16,09 s: paro principal/servo4,4889–4,4920 s,
cargador/baterías≈0,253 s, actuadores≈0,020 s, pose≈0,096 s; estado de acción
retenido. Presupuesto de edad de recepción sólo para los dos paros5 s; los demás
canales/controlador y fuente articular2 s, archivo1 s. Edad real archivada, sin
renovarla al consultar ni tomar muestras repetidas como nuevas. Cualquier fallo,
fuente perdida/duplicada o congelación rechaza; un fallo observado queda retenido.
El watchdog comprueba el archivo durante acciones y revoca el lease ante fallo.
No modifica la respuesta física del paro, control de fuerza, límites o calibra
FT. La ausencia de fuerza medida no se presenta como verificación de sujeción.

583 pruebas pasan. `--check --benchmark-checks 1` real termina rc0/CHECK_OK,
con HOME20D medido; no se armaron etapas ni adaptadores SPS. En reposo: adquisición
completa2,491728 s frente a continua0,003216 s; discover+hashes0,226823 s.
No es medida del ciclo con movimiento. Ensayos anteriores preservados: permiso
600 del snapshot impedía lectura del host y fue corregido con regresión;
caducidad global2 s rechazaba el canal normal de paro antes de medir su período.
Cierre deliberado revoca leases; mensajes de error de los workers al salir siguen
en el registro, deuda de presentación existente, no éxito de movimiento.

Evidencia reproducible y backup íntegro antes/después:
`../Humanoide-vla-evidence/20260928T155443Z_OPTIMISTIC_SCENARIO1/`.
Incluye `cadence-readonly.py`, resultados/console de tres checks, métricas y hashes
finales. Receta de activación es invocar el nuevo wrapper; contexto y checkpoint
impiden cruzar normal/optimista incluso con recuperación confirmada. Reversión:
retirar entrada nueva y restaurar selectivamente los cinco módulos PC respaldados,
luego validador/pruebas nuevos si no se referencian; preservar cambios posteriores,
checkpoints y la corrección SPS. No restaurar estados transitorios del robot.
[Fuente, uso, pruebas y rollback](box_handling/OPTIMISTIC_SCENARIO1.md).
Sin commit/push y sin movimiento, reinicio ni apagado realizados por el agente.

### BOX-01-SPS-PREFLIGHT — 28-09-2026 18:35 CEST, Europe/Madrid

**IMPLEMENTADO PC; VERIFICADO offline y en lectura remota.** Motivo:
edición local de rango produjo ID665dc3bff417b03a ausente en Motion y una
excepción FileNotFoundError antes de etapas. El operador eligió restaurar
X=[0,41;0,79] m: `scripts/box_handling/front_sps_contract.py` vuelve al bundle
instalado`bf145fa17e1116fc` (SHA256 idéntico al registro BOX-01-FRONT-DEPTH-GATE).
No se aplica la ampliación local X=[0,35;0,90] ni se adapta el rango al objeto.

`scripts/box_handling/scenario1_dependencies.py` y su prueba distinguen paquete
SPS ausente/incompleto (`SPS_PACKAGE_MISSING`) de otra dependencia ausente
(`DEPENDENCY_MISSING`); informan receta y conservan fallo, lectura completa y
hashes. Sin fallback, descarga ni instalación automática. Fuente transmitida en
memoria al contenedor Motion/ROS2 por el ejecutor; no requiere reinstalar SPS.
141 pruebas pertinentes correctas. Hashes host/ambos contenedores coinciden;
no instalación ni reinicio. Primer preflight rc78 por acción ocupada o estado
no verificable; lectura posterior terminal4/un publicador; segundo preflight
rc0, CHECK_SPS_RUNTIME_OK. Sin adaptadores ni tareas/movimiento. No mide HOME
ni valida trayectorias. Respaldo anterior, bundle y comandos/resultados
en `../Humanoide-vla-evidence/20260928T163456Z_SPS_PACKAGE_PREFLIGHT/`.
Reversión selectiva sólo del módulo de diagnóstico y su prueba desde`before/`;
no restaurar el rango anterior del backup, descartado por petición del operador.
[Receta, detalles y pendientes](box_handling/FRONT_BOX_DEPTH_GATE_20260928.md#configuración-local-y-paquete-ausente--28-09-2026-1835-cest).

### BOX-01-POSITION-CONSOLE — 29-09-2026, Europe/Madrid

**Ampliación vigente: rechazo con XYZ completo.** El intento110554 del operador
demostró que sólo se imprimían las medidas aceptadas, porque el gate abortaba
antes de emitir `detected`. Fuente PC adicional `scenario1_perception.py` y
su prueba; runtime transitorio observa `validate_position` original, registra
posición/límites ante ValueError y relanza la misma excepción. La consola muestra
XYZ/margen/exceso también del rechazo; no recalcula objetivo ni modifica límites.
Errores de registro no reemplazan el fallo de control. No requiere instalar:
fuentes del bundle`bf145fa17e1116fc` idénticas; carga sólo en la siguiente sesión.
153 pruebas y replay offline exacto del intento correctos, X81,73/Y13,13/Z8,81 cm
y excesoX27,3 mm. Sin conexión/movimientos del agente; prueba física nueva pendiente.
Backup adicional y hashes antes/después:
`../Humanoide-vla-evidence/20260929T110941Z_BOX_REJECTION_CONSOLE/`.
Revertir sólo esta ampliación: restaurar selectivamente consola/runtime/percepción
y sus pruebas desde ese`before/`; conserva el rechazo original y el formato de
aceptadas. No restaurar estados remotos ni checkpoints.

**IMPLEMENTADO PC; VERIFICADO offline; observación en ciclo físico PENDIENTE.**
Motivo: mostrar también cajas dentro de rango, con XYZ en cm e intervalos
efectivos y margen al límite más cercano en mm. Fuentes:
`scripts/box_handling/scenario1_console.py`, `scenario1_runtime.py` y sus dos
pruebas. Destino: consola PC y runtime temporal transmitido en memoria al host
Motion en la siguiente invocación de improved/optimistic. No instalación remota,
recarga de servicios ni modificación de las seis fuentes SPS`bf145fa17e1116fc`.

Se reenvía `selection.jsonl` durante feedback/resultados Motion y al cierre,
sin líneas parciales ni duplicar registros. La consola muestra una vez la pose
final de la segunda captura validada, usando datos/base_link/intervalos del
evento; no vuelve a captar ni cambia decisiones. Sin esperas de sensores,
watchdog nuevo o modificación de límites. Un aviso de registro no autoriza
movimiento ni cambia resultado/checkpoint. --verbose mantiene los eventos.

114 pruebas PASS, --plan y replay offline de captura histórica correctos.
Sin conexión ni movimiento realizados por el agente. Base Git88b17026…;
backup antes/después, hashes, pruebas y replay en
`../Humanoide-vla-evidence/20260929T102432Z_BOX_POSITION_CONSOLE/`.
Reversión selectiva de ambos módulos y pruebas desde`before/`, preservando
trabajo posterior; no rollback del paquete SPS ni cambios de checkpoint.
[Formato, receta de verificación y alcance](box_handling/FORCE_IMPROVED_SCENARIO1.md#medidas-de-caja-en-consola--29-09-2026).

## BOX-01-VISUAL-ALIGN — 02-10-2026, Europe/Madrid

**02-10-2026 — BOX-01-VISUAL-ALIGN-ODOM-PROGRESS.** Intento094521 pasa
HOME/get1 y solicita ajusteX21,200mm; cancela a4,008s por falta de progreso.
Mapa termina a27,095mm, pero odometría registra42,601mm de recorrido y25,800mm
netos, con residual local4,600mm al desplazamiento solicitado. Discrepancia
OBSERVADA, causa física/localización PENDIENTE. El guard de recogida ahora cuenta
mejoras netas≥2mm hacia ese desplazamiento en odometría, desde la postura fresca
de envío, sin cambiar objetivo ni llegada en mapa. Conserva watchdog4s y todos
los límites; odometría no autoriza llegada, giro rápido ni agarre. 727 pruebas
pertinentes pasan; instalado PC, nueva carga/ensayo PENDIENTES. Sin movimientos
del agente. Tras cancelación sigue exigida recuperación/comprobación presencial.
Destino exacto PC: scripts/box_handling/scenario1_nav_correction.py,
test_scenario1_nav_correction.py y fixture box_alignment_odom_progress_20261002.json.
CLI vigente transmite guard en memoria al cliente nativo Motion redescubierto;
no instala/reinicia servicios ni cambia SDK/vendor/SPS. Reutiliza dos muestras
nuevas por stream y postura estacionaria previas al envío; sólo box_pickup y
odom→base_link/base_footprint. El objetivo local es diagnóstico del desplazamiento
relativo; no se publica TF ni objetivo. Sólo mejoras de distancia≥2mm al mejor
error anterior renuevan progreso; no cuentan recorrido, retroceso, sobrepaso ni
oscilación repetida. No se renueva durante reposo terminal. get1 sin cambios.
Mapa fresco, presupuestos de ambos frames, empeoramiento, velocidades, salud,
lease, llegada y percepción siguen obligatorios. Logs añaden pickup_odometry y
progress_source; el progreso inicial en mapa mantiene su concesión única previa.
Fuente reproducible, hashes y verificación/activación/reversión: expediente
siguiente. Backup exacto before/ y after/ (incluye árbol con cambios sin commit),
manifiestos y resultados: ../Humanoide-vla-evidence/20261002_BOX_ALIGNMENT_ODOM_PROGRESS/.
Reversión selectiva guard/test/notas desde before/, retirar sólo fixture nueva,
preservar revisiones previas y cambios posteriores; sin rollback de checkpoints.
[Receta y limitaciones](box_handling/BOX_AXIS_REPOSITION_20261002.md#revisión-de-progreso-odométrico-del-intento094521).

**02-10-2026 — BOX-01-HOME-DIAGNOSTIC. OBSERVADO en el intento093621:**
HOME inicial rechazado exclusivamente por head_pitch1002=−0,430761rad;
brazos/torso≤0,000959rad, velocidad0 y consignas dentro del gate en dos muestras.
Compatible con la cabeza de observación del intento anterior (INFERENCIA).
Inicio sin etapas ni objetivos; el fallo de lease posterior pertenece al cierre.
El error PC ahora identifica ejes/posiciones fuera de HOME y conserva el bloqueo
20D original: no envía recuperación ni HOME automático. Estado físico actual y
recuperación presencial PENDIENTES.
Destino exacto: PC, scripts/box_handling/scenario1_runtime.py y
scripts/box_handling/test_scenario1_runtime.py; cargados en memoria por el CLI
existente en la próxima sesión autorizada. Instalado PC; carga remota y prueba
física del nuevo mensaje PENDIENTES. HOME clasificador/20D/tolerancia0,02rad,
salud, lease, watchdog y tarea HOME sin cambios. Depende del clasificador original,
cuya tabla de aliases reutiliza después de validar por completo la muestra.
Verificación:719 pruebas pertinentes y5 del clasificador pasan; plan/sintaxis/diff
correctos. No se ha conectado ni movido el robot en esta intervención.
Registro técnico home_not_measured incluye sello, ejes y clasificación rechazada;
mensaje conserva HOME_NOT_MEASURED y exige recuperación presencial.
Fuentes reproducibles/versiones SHA256 y receta: enlace siguiente. Respaldos
exactos del árbol local previo (incluyendo modificaciones sin commit) y final:
../Humanoide-vla-evidence/20261002_BOX_HOME_DIAGNOSTIC/.
Reversión selectiva desde before/ de runtime/test/notas; conservar cambios
anteriores de asociación y posteriores del usuario. Sin remoto, SDK, commit ni push.
[Diagnóstico, aplicación y verificación](box_handling/BOX_AXIS_REPOSITION_20261002.md#diagnóstico-home-del-intento093621).

**Revisión BOX-01-VISUAL-ALIGN-ASSOCIATION,02-10-2026:** fuentes PC en
scripts/box_handling/scenario1_box_alignment.py, scenario1_runtime.py,
scenario1_cli.py y test/fixture asociados. La
asociación entre posturas compara medias de dos detecciones coherentes en
odometría local; mapa sigue guiando/validando navegación. Reutiliza informes
de reposo existentes antes/después y parser original scenario1_resume_worker,
añadido al payload supervisor antes del planificador. No agrega consultas ni
publicadores. Exige dos muestras nuevas, fuentes frescas, reposo/estabilidad,
odom→base_link/base_footprint, mismos frames y tiempos que encierran las imágenes.
Conserva2cm/3°, gateXYZ y última pose original; promedio nunca es autorización
ni pose física. El ensayo092429 completó llegada6,8mm y visiónX0,743580m:
comparación previa en mapa29,626mm, nueva local19,290mm/2,120° en replay.
No prueba identidad física/calibración; agarre no enviado. Vigente: instalado
PC y VERIFICADO con715 pruebas pertinentes; carga/ensayo nuevos PENDIENTES.
Activación: próxima sesión optimista autorizada transmite helpers en memoria
a Motion/cliente nativo redescubierto, sin instalación/reinicio/remoto/SDK/vendor.
Respaldos exactos previos/finales, SHA256 y resultados:
../Humanoide-vla-evidence/20261002_BOX_ALIGNMENT_ODOM_ASSOCIATION/.
Rollback selectivo de tres fuentes/test/notas desde before/, retirar fixture
nueva, conservar cambios posteriores; sin restaurar estados remotos/checkpoint.
[Fuentes, dependencia, receta y límites](box_handling/BOX_AXIS_REPOSITION_20261002.md#revisión-de-asociación-del-intento092429).
Sin conexión/movimiento, commit ni push del agente.

**Revisión BOX-01-VISUAL-ALIGN-ARRIVAL,02-10-2026:** precisión terminal PC
5→12mm, yaw2° conservado; dos poses nuevas estables y después doble detección
obligatoria. El guard conserva umbral5mm para giro rápido y todos los límites
de movimiento/frescura/presupuesto. Motivo: intento091156 terminaSUCCEEDED y
reposo, poses finales9,630mm/0,452°; el gate PC abortaba antes de validar la caja.
Separa llegada terminal de criterio XYZ de recogida, que permanece intacto.
Nueva policy congelada explicita12mm/2°. Caja fuera de gate usa, si hay mejora,
el segundo objetivo ya autorizado≤50mm solicitados totales; fallos/identidad/
no mejora siguen abortando. Consola muestra residual y anuncia nueva medición.
Fuentes/destinos PC: scripts/box_handling/scenario1_box_alignment.py,
scenario1_runtime.py, scenario1_console.py, test_scenario1_box_alignment.py y
fixtures/box_alignment_arrival_20261002.json. Próxima sesión autorizada transmite
helpers al host/cliente Motion redescubierto en memoria. Sin cambios de vendor,
SDK, YAML/XML, paquete SPS, mapa ni parámetros remotos. Instalado/verificado PC
con708 pruebas pertinentes; nueva carga/prueba física PENDIENTES. El diario
confirma cargadas revisiones previas y navegación/reposo, no agarre ni detección
posterior. Configuración12mm del proveedor es histórica, no recotejada hoy.
Backup/hashes íntegros antes/después, fixture saneada y resultados:
../Humanoide-vla-evidence/20261002_BOX_ALIGNMENT_VISUAL_ARRIVAL/.
Rollback selectivo desde before/ de tres fuentes/test/notas; retirar fixture
nueva, preservar cambios posteriores, sin restaurar estados remotos/checkpoint.
[Fuentes, receta y detalle](box_handling/BOX_AXIS_REPOSITION_20261002.md#revisión-de-llegada-del-intento091156).
Sin conexión/movimientos del agente, commit ni push.

**Revisión BOX-01-VISUAL-ALIGN-FRESH,02-10-2026:** runtime PC consulta reposo
en health worker persistente por comando base, con lector /mc/odom creado una
vez bajo QoS SensorData/bestEffort/volatile/keepLast5. Importa en memoria la
Acquisition original de scenario1_resume_worker; no la modifica ni conserva
muestras entre peticiones. Mantiene dos muestras nuevas, un publicador,0,5s,
0,003m/s/0,01rad/s, estabilidad5mm/1° y plazo5s; health/pose y reanudación
standalone conservan su flujo. La caché de salud no recibe odometría. Motivo:
consulta posterior al procesamiento tarda0,903s en el intento085958, imagen
caduca a≥2,219s. Mantiene edad máxima2s y registra edad real antes de decidir.
Destinos: PC scripts/box_handling/scenario1_runtime.py, scenario1_health_worker.py,
scenario1_cli.py y tests correspondientes. Dependencia pura adicional transmitida
en payload health: scenario1_resume_worker.py, sin ROSA al importar. Activación:
próxima sesión autorizada crea lector al primer base; --check no lo crea.
Instalado PC y VERIFICADO offline con700 pruebas; nueva carga/ensayo PENDIENTES.
Sin instalación remota, cambios de parámetros, reinicios, movimientos, commit/push.
Respaldo exacto previo y final, hashes, resultados y diagnóstico:
../Humanoide-vla-evidence/20261002_BOX_ALIGNMENT_FRESH_DISPATCH/.
Rollback selectivo desde before/ de esos tres scripts, tests y notas; preserva
cambios posteriores, no restaura checkpoints ni estados físicos/remotos.
[Fuentes, receta y evidencia](box_handling/BOX_AXIS_REPOSITION_20261002.md#revisión-de-frescura-del-intento085958).

**Revisión BOX-01-VISUAL-ALIGN-PROGRESS,02-10-2026:** guard PC reconoce una
única recuperación inicial de distancia≥2mm desde un máximo≥2mm por encima
de la entrada. Sólo box_pickup, antes de progreso neto/fase final; get1 conserva
su regla previa. No amplía4s sin progreso, límites físicos, edades ni gates.
Archiva últimas poses de cada frame, referencia de progreso y uso de recuperación.
Consola conserva código0 de cancelación y advertencia de parada no comprobada.
Motivo: intento084706 cancela tras4,009s con distancia22,301mm, después del
retorno desde29,501mm; solicitud inicial22,774mm. Adquisición temporal anterior
OBSERVADA en este ensayo; corrección completa/agarre no demostrados. Fuente
reproducible: scenario1_nav_correction.py, scenario1_console.py y tests/fixture
box_alignment_progress_20261002.json. Destinos: PC, mismos paths scripts/
box_handling; próxima sesión transmite guard en memoria al cliente Motion
redescubierto, sin instalación remota/reinicio. Instalado en PC y VERIFICADO
offline; carga/ensayo de revisión PENDIENTES. Backups íntegros antes/después,
SHA256 y resultados690 pruebas:
../Humanoide-vla-evidence/20261002_BOX_ALIGNMENT_PROGRESS/.
Restaurar selectivamente guard/consola/tests previos, retirar fixture nueva y
revertir estas notas preservando cambios posteriores. Sin estados remotos.
[Diagnóstico, dependencias, evidencia y reversión](box_handling/BOX_AXIS_REPOSITION_20261002.md#revisión-de-progreso-del-intento084706).
Sin conexión/movimientos del agente, commit ni push.

**Revisión BOX-01-VISUAL-ALIGN-TIME,02-10-2026:** fuentes PC supervisor,
planificador temporal y test actualizados para adquirir poses mientras procesa
visión. Dos sellos a≤0,5s de cada imagen y estabilidad de todas las muestras;
referencia nueva para objetivo, detección≤2s después del reposo. Mantiene gates,
workers, hashes, límites físicos y protocolo de salud/reanudación. Nuevo hilo
espera sólo la captura, sin ROS writers; el hilo principal consulta la sesión
de salud. Límite12s por captura y256 muestras, evidencias antes del rechazo.
Corrige el fallo083606 posterior a cabeza, sin agarre ni corrección enviados.
VERIFICADO offline; carga/ensayo de revisión PENDIENTES. Backup íntegro del
árbol local previo y hashes antes/después:
../Humanoide-vla-evidence/20261002_BOX_ALIGNMENT_TIME_PAIR/.
Reversión selectiva y diagnóstico:
[revisión temporal](box_handling/BOX_AXIS_REPOSITION_20261002.md#revisión-temporal-del-intento083606).
Sin conexión, cambios remotos ni movimientos del agente; sin commit/push.

IMPLEMENTADO en PC; VERIFICADO offline; carga remota/prueba física PENDIENTES.
Motivo: llegada get1 correcta no garantiza caja dentro del gate; intento081640
rechazado por X0,790928m, exceso0,928mm. Optimistic añade preparación de cabeza
y observación visual antes del agarre nativo, torso/brazos HOME, detecciones
coherentes y TF exacta. Sólo corrige X/Y incumplidos con free_nav supervisado:
dos objetivos,50mm solicitados acumulados,20mm hacia dentro del límite original,
llegada5mm/2°, nueva detección y asociación geométrica en mapa antes de agarrar.
Z fuera de rango y cualquier fallo de acción/salud/guard siguen abortando.
No cambia gateXYZ, tareas vendor, SDK ni paquete SPSbf145fa17e1116fc.

Destinos PC: scripts/optimistic_scenario1.sh y scripts/box_handling/
scenario1_box_alignment.py, scenario1_runtime.py, scenario1_nav_correction.py,
scenario1_cli.py, scenario1_console.py; tests y fixture saneada relacionados.
Activación: próxima invocación optimista autorizada; transmisión en memoria al
host Motion/cliente nativo en el contenedor redescubierto, procesos temporales.
Dependencia extra de cabeza verificada por hash antes de usar y en --check;
se conserva la identidad persistida de dependencias para reanudaciones anteriores.
Fuentes/hash, aplicación, requisitos, límites reales del guard, verificación,
estado instalado/cargado/probado, pendientes, evidencia y receta de rollback:
[expediente BOX-01-VISUAL-ALIGN](box_handling/BOX_AXIS_REPOSITION_20261002.md).
Backup externo íntegro antes/después y manifiestos SHA256:
../Humanoide-vla-evidence/20261002_BOX_AXIS_REPOSITION/.
Revertir selectivamente fuentes PC respaldadas y retirar archivos nuevos,
sin tocar estados remotos ni checkpoints. Sólo cambios locales; sin conexión,
movimiento, instalación remota, reinicios, commit ni push.

## BOX-01-TABLE90-CANDIDATE — 01-10-2026, Europe/Madrid

VIGENTE: instalado, cargado y probado físicamente con mismo montaje declarado.
Delta de mesa +45cm; dos Z absolutas de manos0,65→1,10m, final relativo0,90m.
Perfil optimistic por defecto90; standard original. Paquete3e142cd1… aditivo en
Motion, contenedor walker-motion.manipulation_robot_app-1. Originales intactos.
Seis pines de modelo/HOME y hash de perfil probado; controles nativos conservados.
Ciclo completo habilitado tras depósito/liberación confirmados y HOME medido.
El expediente registra estado anterior, paths exactos, hashes, dependencias,
recetas versionadas de instalación/lectura, activación por primera tarea real,
comprobaciones, alcance de prueba, backup y reversión condicionada a hashes.
Cambio de ejecución adicional: mapa utars_nav_map y relocalización global;
conservado, sin editar puntos ni rollback automático. Diez etapas físicas en
tramos grasp-trial/deposit-trial/home-trial, rc0; un check stale rechazado y
repetido sin modificar gates. Robot queda HOME, caja apoyada en destino.
577 pruebas pertinentes y final --check rc0; legado17 errores ajenos reproducidos.
Backups externos: ../Humanoide-vla-evidence/20261001_SCENARIO1_TABLE90/
(before/, continuation-before/, after/, install/, physical-validation.json).
No restart, paquetes nuevos, cambios de SDK, commit ni push.
[Registro completo y reanudación](box_handling/SCENARIO1_TABLE90_CANDIDATE.md).


### BOX-TINY-CORRECTION-DIAG-20261007 — OBSERVADO (Europe/Madrid)

Revisión de sólo lectura del ensayo `20261007T114551Z_OPTIMISTIC_SCENARIO1_1037361`: llegada a get1 9,5 mm / 0,46°. Caja X previa 0,790496832870 m; solicitud de ajuste X 2,496832870 mm hacia el límite interior 0,788 m (margen efectivo 2 mm; el texto antiguo de 20 mm no refleja esa política). Las dos mediciones de llegada conservan exactamente el error solicitado de 2,496832870 mm y yaw 0°, aceptados por tolerancia 20 mm / 2°. Odometría antes y después conserva la misma posición: no se observa desplazamiento del chasis. Nueva X 0,790102098093 m: mejora visual 0,394734777 mm; permanece 0,102098093 mm fuera del máximo nativo 0,79 m y 2,102098093 mm fuera del límite interior. `BOX_ALIGNMENT_NO_IMPROVEMENT` interrumpe antes del agarre. La tolerancia de llegada permite dar por terminado un ajuste menor que ella sin desplazamiento; variación de detección no demuestra movimiento físico de la caja. Los errores posteriores de lease son consecuencias del cierre. No se cambiaron políticas ni se enviaron órdenes al robot. Evidencia: `../Humanoide-vla-evidence/20261007_BOX_TINY_CORRECTION_DIAG/` y events.jsonl del ensayo. Pendiente: resolver la relación entre correcciones pequeñas y tolerancia de llegada; no hay autorización de movimiento en esta revisión.


### BOX-ALIGNMENT-MIN-STEP-20261007 — instalado en PC; prueba física PENDIENTE

2026-10-07 (Europe/Madrid). Autorización: modificar el escenario para evitar objetivos de corrección pequeños que terminan sin desplazamiento, caso `20261007T114551Z_OPTIMISTIC_SCENARIO1_1037361`. Fuente reproducible: `scripts/box_handling/scenario1_box_alignment.py`, `scenario1_console.py` y `scenario1_cli.py`; pruebas en `test_scenario1_box_alignment.py` y `test_scenario1_console.py`. Sólo se cambiaron fuentes locales del PC, sin comandos de robot ni despliegue remoto.

`POLICY.min_correction_m=.025`: para cada eje X/Y afectado cuya corrección necesaria es menor o igual que `max_arrival_distance_m`, se solicita `max(min_correction_m, corrección_necesaria + max_arrival_distance_m + min_improvement_m)` con su signo original. Se verifica que la posición proyectada permanece dentro del margen interior en ambos sentidos y se conserva el control vectorial de 50 mm por paso, 50 mm acumulados y dos intentos del runtime. Los ejes sin violación no se corrigen. Un objetivo así no puede aprobarse en el punto original dentro de la tolerancia de llegada. Las detecciones y límites nativos de agarre, asociación, salud y watchdogs se conservan. La detección nueva sigue decidiendo el agarre; el cálculo no prueba espacio físico libre, exactitud del mapa o estabilidad de la caja.

El archivo del usuario observado al comenzar esta intervención contiene margen interior 20 mm, llegada 12 mm y progreso mínimo 2 mm; se preservaron esos valores. Con la política histórica del ensayo (margen 2 mm, llegada 20 mm, progreso 3 mm), la solicitud original de 2,496833 mm pasa a 25,496833 mm. El objetivo es más profundo, sin ampliar el rango XYZ. La consola normal imprime ahora X/Y/Z en cm de cada observación validada, identificando base_link y que Z no es altura al suelo; el banner explica el mínimo configurado.

Activación: el ejecutor carga estos archivos en la siguiente ejecución autorizada. Revisar primero `./scripts/optimistic_scenario1.sh --plan` y `--check`; tras una interrupción comprobar estado físico y usar la recuperación adecuada, sin repetir automáticamente el ciclo. No se efectuó ensayo físico. Verificación sintética: 94 pruebas de alineación/consola y 123 de SPS/navegación/runtime superadas (217 total); --plan y git diff --check correctos. Aviso de ResourceWarning de un lock temporal en las pruebas relacionadas, sin fallos. Resultados exactos en la evidencia. Rollback selectivo: retirar sólo `min_correction_m` y el bloque adicional de `displacement`, y los cambios de presentación; los archivos previos completos están respaldados para comparación, sin sobrescribir cambios posteriores del usuario. Dependencias: gate XYZ de front_sps_contract y políticas actuales de navegación/runtime.

Backup antes/estado después, hashes SHA256, pruebas y plan: `../Humanoide-vla-evidence/20261007_BOX_ALIGNMENT_MIN_STEP/`. Pendiente: verificar físicamente avance, detección posterior y agarre, con zona despejada y controles físicos de AGENTS.md. No commit ni push.


### HEALTH-POST-GRASP-DELTA-20261008 — VERIFICADO en evidencia histórica del robot

2026-10-08, Europe/Madrid. Petición: diagnosticar fallo durante demo sin mover ni cambiar robot/PC. Sólo consultas SSH de lectura a Motion/Vision: docker ps, inspect, archivos existentes de /tmp y docker logs acotados. Sin ROS/ROSA acciones, publicaciones, reinicios ni configuración. Se preservaron los cambios locales.

Ensayo `20261008T082522Z_OPTIMISTIC_SCENARIO1_1659473`: recogida goal `5130c75e-2c37-4aaf-af45-b4f48dcb2cd6` devuelve status4/SUCCEED a 08:26:34,298 UTC (10:26:34 CEST). Log Motion confirma `Clamp box succeed` y `BTree tick succeeded` (log nativo UTC+8 16:26:34). Checkpoint completa grasp/verify_held (sujeción asumida) y falla antes de retreat; no se lanzó retroceso por este ejecutor.

Snapshot conservado en Motion `/tmp/cruzr-scenario1-zq6fa4uz/live-health.json`, escrito 1791447995257351540 ns, dos muestras de actuadores después del resultado: todas las velocidades reportadas son 0.0; no error_code en articulaciones afectadas, status4663. Diferencia cmd_pos-position: brazo izquierdo 4003 =0,010812102450 rad (0,619488°); brazo derecho 5002 =0,011170135544 rad (0,640002°), ambos superiores al gate estacionario 0,01 rad (0,572958°). Ésta es la causa concreta de `LIVE_HEALTH_SETTLING`, no velocidad residual en esas muestras. Muestras de fuente a 41,58/21,58 ms del error final, status de la acción4 y snapshot sin error latched. Replay offline con tiempos históricos reproduce exactamente LiveHealthPending. No es lectura del estado físico actual, ni prueba de sujeción o ausencia de contacto.

`scenario1_runtime.quick_health()` espera 0,5 s; `scenario1_live_health.validate_snapshot()` rechaza reposo si velocidad >0,02 o delta >0,01. El script no distingue en consola cuál de esas condiciones falla. Ampliar sólo el tiempo no garantiza resolver una diferencia estacionaria. No se relajó ningún gate. Diferencia de criterios entre éxito nativo y validación posterior explica que Motion termine bien y el escenario interrumpa. Causa física del pequeño error de seguimiento (carga, calibración/contacto/control) PENDIENTE; no atribuir a Wi-Fi o mapa. Los errores de lease son posteriores al aborto.

Observación separada: al consultar a 08:32 UTC los contenedores Motion manipulation_robot_app y hw ya se habían reiniciado, con StartedAt08:29:34/08:29:29 y RestartCount1; este agente no los reinició. No confundir estado después del reinicio con el fallo anterior. Dependencias actuales redescubiertas mediante docker ps. No cambios persistentes del sistema remoto. Evidencia saneada de consultas, snapshot histórico, logs y replay: `../Humanoide-vla-evidence/20261008_HEALTH_TRANSITION_READONLY/`, SHA256SUMS. Cambios locales únicamente este registro; before/after documentales conservados. Pendiente revisar el criterio posterior al agarre con carga y registrar diagnóstico detallado de joint/delta sin ocultar fallos; cualquier cambio de lógica o movimiento requiere nueva petición y condiciones físicas actuales.


### MOTION-BOOT-FT-WATCHDOG-20261008 — OBSERVADO; arranque incompleto

08-10-2026 Europe/Madrid. Usuario informa reinicio sin HOME. Diagnóstico sólo lectura: docker ps/inspect/logs y consultas ROSA pasivas con timeout; sin HOME, enable, reset, reinicio ni cambio de configuración. Arranque redescubierto: manipulation_robot_app StartedAt08:43:29Z, hw08:43:30Z, ambos RestartCount1.

Logs nativos (hora mostrada por robot): 16:43:28,875 dispositivo EtherCAT `SubDevice_6002 [KunWeiTech FT Sensors]` en `SAFEOP ERROR`, `Sync manager watchdog` (0x1b). Master no logra OP (`0x98110024`), se desinicializa y hw registra traza fatal en servoEnableCB. A16:43:29,463 manipulation_robot_app falla al esperar/iniciar force_torque_sensor_controller y termina con `Failed to initialize robot_rosa_client or setup sensor controller`; posteriormente se reinicia el proceso. No evidencia de HOME completado en el arranque consultado. Es fallo de cadena hardware/controlador, independiente del gate Python de diferencia cmd_pos del ensayo anterior. Raíz física del watchdog (sensor, conexión, alimentación, sincronización) PENDIENTE, no diagnosticada por estos logs.

Consulta /mc/actuator_state --once timeout5 rc124 sin muestra. Servicio list_controllers tipo redescubierto rosa_control_msgs/srv/ListControllers: timeout5 rc124 esperando disponibilidad; una primera consulta con tipo estándar controller_manager_msgs fue incompatible, no constituye evidencia de estado. Contenedores Up no demuestra control operativo. Hay desfase de reloj observado entre host/CLI: conservar tiempos de origen, no inferir coincidencia exacta de segundos.

Evidencia: `../Humanoide-vla-evidence/20261008_RESTART_NO_HOME_READONLY/` con resultados de consultas y SHA256SUMS. No configuración ni movimiento del robot/PC. Cambios únicamente documentales, backup before/after. Pendiente recuperar/discutir inicialización FT/EtherCAT sin anular watchdog; verificar caja sujeta/apoyada/retirada y trayectoria antes de cualquier HOME. No reiterar ciclo de cajas con control no confirmado.


### MOTION-BOOT-FOLLOWUP-20261008 — OBSERVADO, HOME pendiente

08-10-2026 Europe/Madrid. Operador reinicia de nuevo; agente sigue arranque sólo con docker ps/top/logs y servicio pasivo list_controllers con timeout5. No start, servo enable, HOME, publicación, restart ni configuración. Vision ya publica servicios mientras Motion inicia contenedores; hw proceso rosa_control_node espera `/mc/rosa_control/start` (log nuevo16:51:35 y16:53:16). Manipulation espera repetidamente list_controllers, consulta pasiva rc124.

Control Center nuevo registra boot ready y transición a WaitEStopRelease a16:52:23 hora nativa; servo_estop reportado released, no confirmación equivalente del paro principal en la evidencia compacta. Anuncio pide girar/liberar paro. A16:52:30 heartbeat marca ethercat slave offline. Hasta últimas consultas16:53:21 no transición posterior observada ni HOME confirmado. No confundir errores6002 del arranque16:43 (persisten en docker logs) con el nuevo arranque: no se observó repetición nueva del watchdog. El heartbeat offline mientras hw espera start no demuestra por sí solo sensor averiado. Se solicita al operador estado físico de ambos paros y caja sin tocar controles; respuesta pendiente.

Evidencia y recetas de consultas en `../Humanoide-vla-evidence/20261008_BOOT_FOLLOWUP_READONLY/`, SHA256SUMS, backup before/after documental. No cambios persistentes robot/PC aparte de documentación. Pendiente: condición que libera WaitEStopRelease y completar inicialización hardware/sensores/controladores y HOME medido; no liberar paros sin revisar caja, trayectoria y persona junto al paro porque puede iniciar movimiento automático. No se afirma listo para ciclo.


Actualización de MOTION-BOOT-FOLLOWUP-20261008, misma intervención: operador informa E-stop liberado. CC lo detecta a16:53:34 hora nativa y pasa WaitEStopRelease→EnterWorkMode→SelfChecking. Controladores se inicializan; consulta list_controllers rc0 confirma force_torque_sensor_controller y manipulation_controller running. Audio_loopback del self-check pasa false, mientras alimentación/cámaras/relojes/ficheros/servo_power pasan true en el informe; no se anula ninguna comprobación por el agente. Motion registra BTree tick succeeded a16:54:12. Durante trayectoria inicial de cabeza hay rechazos de comandos menores que límite−0,688727rad, sin inferir estado actual desde esos mensajes.

Consulta pasiva de actuadores necesita QoS best_effort (default reliable no recibía y timeout124, no significa ausência de telemetría); ayuda de CLI contrastada y evidenciada. Primera muestra fresca: HOME20D=1, máx posición0,002493rad, velocidad0, delta0,002493 y sin error_code. Segunda muestra posterior: brazos en HOME (máx0,000959rad), velocidad0, sin fallos, pero cabeza1002 posición−0,430665rad y consigna−0,43; HOME20D=0. No atribuir esa nueva consigna al agente, que no mandó órdenes. No declarar estado actual full HOME ni autorización de movimiento; hardware/controladores sí disponibles en la consulta. Ambas muestras/hashes/classificaciones guardadas. Estado de caja no informado. Fin del seguimiento del arranque solicitado con resultado técnico y límite de postura explícito.


### NAV-POSE-TIMEOUT-20261008 — OBSERVADO; diagnóstico sólo lectura

Ensayo `20261008T102504Z_OPTIMISTIC_SCENARIO1_1953293` aborta preflight, antes de etapa1: request2 pose, cero muestras frescas, dos publicadores detectados, TimeoutError. `scenario1_health_worker` admite >=1 publicador de pose porque existen dos vendor en esta unidad: el 2 no provoca el rechazo. controller_received:false/safety_received:[] son campos genéricos que no se requieren en adquisición pose, no demuestran otro fallo de salud. Requiere dos poses nuevas con timestamps válidos/avanzantes.

Consulta pasiva posterior en Vision /nav/robot_pose, best_effort, tipo PoseStamped, timeout5 rc124 sin muestra. Logs VSLAM actuales muestran solve_pose_mode=localization(Reloc) y comparación de características contra mapa; indica búsqueda de relocalización, sin probar por sí solo causa raíz o calidad del mapa. Inferencia: la localización todavía no ofrece pose utilizable. Guardados get_map_name SUCCESS y FSM_WAITNAVIGATE no certifican posición conocida. Ajuste mínimo10mm editado por usuario no intervino; no hubo movimiento solicitado por este ensayo. No se envió acción ROS ni se alteró configuración/remoto. Error lease posterior es cierre.

Fecha08-10-2026 Europe/Madrid. Evidencia local eventos del ensayo y consultas/registro de logs en `../Humanoide-vla-evidence/20261008_POSE_TIMEOUT_READONLY/`, SHA256SUMS, before/after documental. Pendiente comprobar localización recuperada/pose nueva antes de navegación, sin eliminar el requisito de pose.


### BOOT-WAIT-MAIN-ESTOP-20261008 — OBSERVADO en último encendido

08-10-2026 Europe/Madrid. Usuario informa nuevo arranque sin HOME. Consultas únicamente lectura SSH/docker; sin comandos de movimiento, restart, servicio de arranque ni configuración. Inicio consultas con SSH255 a ambos hosts; rutaPC momentánea por red10.183, luego Wi-Fi vuelve a192.168.42.215 y ruta.11 via.42.2. eno1DOWN. No atribuir esos timeouts al hardware, se recuperó enlace sin intervención del agente.

Nuevo arranque: Motion hw/manipulation StartedAt10:41:07Z restart0; VisionCC10:39:24Z. Logs docker persisten fallos6002 de18:35 hora nativa del encendido anterior, no son repetición demostrada en nuevo arranque18:41. Guard CC inicialmente MOTION_RESPONSES0/3, luego1/3,2/3 y3/3, MOTION_READY1; cámaras2/2, seis topics con timestamps avanzantes. CCvendor inició y registra boot ready a18:42:06 hora nativa. Paro principal is_estop:pressed/state1; servo_estop released/state0. FSM llega WaitEStopRelease: éste es el bloqueo actual antes de HOME. No se afirma HOME enviado ni completado, ni fallo nuevo de sensor.

Evidencia `../Humanoide-vla-evidence/20261008_NO_HOME_LATEST_READONLY/`, SHA256SUMS y before/after documental. No cambios persistentes robot/PC salvo documentación. Reanudación: operador verifica objeto sujeto/apoyado/retirado, recorrido/personas y persona junto al paro antes de liberar, porque liberación puede continuar secuencia automática y movimiento. No enviar HOME adicional en paralelo. Estado físico de caja pendiente.


### BOOT-HOME-AFTER-RELEASE-20261008 — VERIFICADO técnico en muestra

08-10-2026 Europe/Madrid. Operador informa paro liberado; seguimiento agente sólo lectura SSH/docker y suscripción best_effort /mc/actuator_state. CC detecta state0 a18:43:03 hora nativa, pasa EnterWorkMode/SelfChecking, StartMotion a18:43:16 y LimbMotion a18:43:25. StartMotion succ a18:43:42 y pasa JoystickMode. La transición JoystickMode no demuestra por sí sola ausencia de HOME: muestra pasiva posterior rc0 confirma HOME20D=1, máxposición0,002780rad, brazos0,001055rad, velocidad0 y sin error_code. Robot final en joystick (no auto_task); no se cambió modo ni se envió HOME por agente. Selfcheck audio_loopback false (similitud0,027757<0,4), resto de12checkslistados pasa; secuencia nativa continúa, no modificación de checks por agente. No declarar autorización física/caja libre desde telemetría.

Evidencia consultas, muestra original/clasificación, logs y SHA256SUMS en `../Humanoide-vla-evidence/20261008_AFTER_ESTOP_RELEASE_READONLY/`. Cambios sólo documentales con before/after. Pendiente: localización para get1 y modo adecuado al escenario si operador solicita ejecución; no arranque automático del ciclo.


### BOOT-STATUS-1314-20261008 — OBSERVADO, espera paro principal

08-10-2026 Europe/Madrid. Nuevo seguimiento sólo lectura de arranque solicitado por usuario; docker inspect/logs, sin acciones, HOME, reinicio ni configuración. Motion hw/manipulation StartedAt11:14:05Z restart0; CC11:12:29Z. Guard pasa MOTION3/3 y CAMERA2/2 (seis topics avanzantes). CCvendor bootready y WaitEStopRelease, log nativo19:14:57: paro principal state1, servo_estop state0. Hasta última consulta hardware sigue esperando /mc/rosa_control/start (19:17:33). HOME no enviado/completado observado. No confundir HOME del arranque previo con éste. No fallo nuevo6002 en evidencia compacta; no certificado estado físico. Antes de liberar paro comprobar objeto/recorrido/persona junto al paro ya que secuencia puede mover automáticamente. Evidencia `../Humanoide-vla-evidence/20261008_BOOT_STATUS_CURRENT_READONLY/`, SHA256SUMS, before/after documental. Sin cambios de sistema salvo documentación.


### PICO-MOTION-FIRST-RECORD-20261014 — VERIFICADO archivo local, reproducción pendiente

14-10-2026 Europe/Madrid. Operador confirma record --help en contenedor Motion y realiza grabación con abrazaderas. El recorder agrega timestamp al nombre: prueba_pico_01_20261014_192429.motion (50bytes reportados, contenido no inspeccionado) y prueba_pico_01_20261014_192800.motion (5,2MB). El intento de docker cp usando basename sin timestamp falló por archivo inexistente. Operador copió el segundo al PC.

Revisión local sin robot ni reproducción: /home/lacuna/grabaciones_cruzr/prueba_pico_01_20261014_192800.motion, SHA2560191fb331c6f2ebc5be0cfb5f8d6c9a2369600e6a07b77dc14d3d990c0003af9. JSON robotUtars/sourceutars_teleop, grupos head(2),left_arm(7),right_arm(7); cada grupo8421 muestras, duración16,84s, tiempos crecientes y q finitos. Brazo izquierdo constante, derecho cambia y cabeza cambia; no es archivo sólo de brazo derecho. No incluye cintura/elevador/chasis/dedos en este archivo. q inicial brazos no cero (postura PICO, no HOME); final no retorna al mismo inicio. No inferir q como medido vs consigna sin contrato del recorder. Validación estructural no verifica límites/collision ni autoriza reproducción; movimientos y objeto durante toma reportados sólo por operador.

Evidencia resumen y hashes documentales: ../Humanoide-vla-evidence/20261014_PICO_MOTION_FIRST_RECORD/. Archivo grande conservado fuera de Git en ruta PC indicada. Cambios sólo documentación con before/after; no config, deploy, servicios, movimiento ni modo. Pendiente auditar trayectoria/entrada/salida y cabeza antes de cualquier player autorizado, con estado físico fresco. No commit/push.


### PICO-MOTION-REPLAY-20261014 — intento físico autorizado; reproducción FALLIDA

14-10-2026 Europe/Madrid. Usuario autoriza reproducir y confirma condiciones físicas, interrumpe preparación y luego autoriza continuar. Receta y resultado [PICO_MOTION_PRUEBA_01_20261014](teleoperation/PICO_MOTION_PRUEBA_01_20261014.md). Original motion conservado; editor vendor genera copia con posiciones idénticas y tiempos2x (33,68s), hash1e8d7ac8250708907e4c962c66a5c7a06fb34b6f7389059cc52f09ff561d65cb. SDK joint_order y joint_states por nombre eliminan falsa diferencia al comparar raw motores; preflight fresco máxdelta0,002876rad, reposo, actuadores habilitados sin fallos, paros0/0, cargador0, baterías28,6/36,8%, controladores activos y sin acción Motion activa. Modo últimoobservadojoystick, sin cambio por agente.

Una llamada player --robot utars --input copia_lenta --loop1 a11:52:51Z termina en1s con std::bad_any_cast. Wrapper rc0 pero stderr abortado: NO éxito. No retry, no HOME. Telemetría posterior velocidades0 y cambio máximo0,000095874rad; no certificación continua de parada ni trayectoria. Causa SDK concreta PENDIENTE. No parche del SDK ni reducción de gates. Evidencia, comandos, hashes/estado before-after documentales en ../Humanoide-vla-evidence/20261014_PICO_REPLAY_PRECHECK/. Reversión: borrar sólo derivada temporal y cambios documentales de ficha si se desea; original no alterado. No commit/push.


### PICO-PLAYER-LOOP-20261014 — VERIFICADO causa y corrección de invocación

14-10-2026 Europe/Madrid. Se confirma que bad_any_cast del único intento player fue causado por --loop1 añadido en comando del agente: parser guarda explícito como string y lo extrae int. Default1síint. Ocurre antes de rosa::init/cliente/archivo. Se corrige receta omitiendo --loop (una pasada por defecto). No cambia SDK vendor. Dos pruebas con interposer de diagnóstico que termina obligatoriamente ANTES de init: opción explícita reproduce aborto, omisión alcanza marcador rc86. Cero movimiento/cliente en diagnóstico. Compilación temporal eliminada. Fuente versionada scripts/teleoperation/pico_player_parser_probe.cpp, ELF pinned8744a30ecce20c414dcf67b60d9aa7ac486bab752d5eee3de08a7336d65ddf0d.

[Receta, trazabilidad y comandos corregidos](teleoperation/PICO_MOTION_PRUEBA_01_20261014.md). Evidencia ../Humanoide-vla-evidence/20261014_PICO_PLAYER_BAD_ANY_DIAG/; before/after documental y SHA256SUMS. Reproducción de trayectoria con comando corregido PENDIENTE; no retomar físicamente bajo esta petición de diagnóstico/corrección. No configuración persistente robot/PC ni alteración motion. No commit/push.


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


### PICO-V4-TAKE05-20261015 — captura activa validada; reproducción pendiente

Archivo hostMotion /home/walker/grabaciones_v4_completas/
prueba_v4_05_20261015T101134Z_462191/rosbag/rosbag_0.db3.
SHA256 be1bc75a17c9e06c97cddff6ef320c371eef9d7a197b66e11fc9b3fdbb462bcb
coincide en copia host y original ROScontainer. Duración44,33s,159430mensajes,
97,9MiB; sqlitequick_checkok. Sólo lectura; no reproducción ni movimiento.

Nuevo inspector PC scripts/teleoperation/inspect_pico_v4_bag.py: abre SQLite
mode=ro, verifica metadata/DBúnica, estabilidad del archivo y quick_check,
deserializa sin crear nodoROS, resume campos position/velocity/effort/torque,
modos, dimensiones/finitos y tiempos; hashSHA256. Requiere entornoROScon tipos,
no se instala paquete adicional. Fuente guardada en evidencia conhash; fuente
reproducible versionada. Reversión retirar helper, conservar grabaciones.
Validación real toma05 completa y compilación Python; no confundir esta revisión
de datos con admisión de replay o certificación de trayectoria.

Resultados: movimiento cabeza/ambos brazos; estadoswhole22149 contienen
head_pitch/head_yaw aunque topic separado /mc/head/joint_states tiene0.
No significa pérdida de cabeza: órdeneshead22169 y medición enwhole. Manoizq
medida4394 muestras, rango máximo1,262869rad(~72,36°), ordencorriente/torque
rango1,1 y modos5/7 observados, unidades/semántica exacta pendientes. Mandos
de posición permanecen constantes como toma01; ahora sí se conservan las
variaciones reales/órdenes completas. Manodcha4394muestras, rango máximo
0,023394rad(~1,34°); orden position/torque constante, modo5. No afirmar ciclo
amplio de apertura/cierre de ambas manos: en derecha casi no hubo variación.
Ambasórdenesmano22168muestras porlado; ordencada brazo22169.

Sin valores nofinitos/dimensiones incoherentes ni retrocesos de tiempos en
canales analizados. Mayorhueco de recepción~31,8ms; whole incluye19cabeceras
repetidas. No afirmar captura sinpérdida o continuidad perfecta. Evidencia
v4-take05-analysis.json, -analysis-receipt.json, -first-messages.json y
-host-copy-checksum.json. Primera consulta de tipos falló por quoting del
fragmento Python, corregido con shlex.quote; sin efectosrobot.
Resultado captura activa útil para preparar replay, incluido cierreizquierdo;
reproducción adaptada y revisión de modos5/7 siguen PENDIENTES.


### PICO-V4-GEOMETRIC-REPLAY-20261015 — derivado preparado, ejecución pendiente

Usuario solicita reproducir toma05 y confirma manos vacías, trayectoria libre,
cargador fuera, persona junto al paro y otros mandos detenidos. Estado técnico
leído: CCJoystickMode, PCSTOP/UIinactiva/sinpico_control; cuerpo/manos reposo,
sinfaults/deltaactuador máximo0,003284rad, paros0/0, batería56,3/60,5%,
cargador0, móduloslibres. SDK OutlineSdkPlay tiene1server/0clientes; controladores
manipulation/force_torque/dexterous_hand running. Primera consulta a endpoint
ROS2supuesto de controllers falló sin invocar movimiento; descubrimiento real
/mc/controller_manager/list_controllers rosa_control_msgs/srv/ListControllers
y consulta correcta. No asumir nombres/tipos antiguos.

Preparación geométrica: scripts/teleoperation/pico_v4_bag_to_motion.py, sin
publicadores ni cambiosSDK. Consume bagSHAverificado sólo lectura; cabeza y
brazos desde órdenes por nombre, dedos desde posiciones medidas. Valida nombres,
finitos, tiempos estrictos, SQLite yhash; salida exclusiva nueva. Usa cabeceras
con origen común para sincronía, retiene primera/última postura hasta cubrir
ventana común, factor2 tiempos (mitadvelocidad), sin cambio de posiciones.
No reproducecorriente/torque ni modos5/7 originales. Se ha comunicado al usuario
que esta prueba vacía repite geometría, sin demostrar sujeción o fuerza.
SDKinstalado soporta --robot utars_with_v4_hand; ordencontrastado YAML instalado.
Playerhash8744a30ecce20c414dcf67b60d9aa7ac486bab752d5eee3de08a7336d65ddf0d.
No --loop por bugconocido; no se modifica SDK/interpone código para ejecutar.

Derivado88,6730752s, SHA256
c2aa12373b4209a77cdc594787f475762b130b468c7fda403473b95f414b2003.
HostMotion .../prueba_v4_05_20261015T101134Z_462191/derived/
take05_geometry_slow.motion; appMotion /tmp/pico_v4_replay_take05_20261015/
take05_geometry_slow.motion. Hashes comparados después de copiar; originalbag
intacto. Archivo .motion no conserva el esfuerzodeagarre; no confundirlo con
réplica exacta de mando corriente. Mayorpaso por muestra0,03682rad en dedos;
brazos≤0,003287rad, cabeza0,004rad; interpolaciónSDK a mitadvelocidad.
Comparacióninicio por nombres: cabeza0,004410rad, brazoizq0,005340,
brazodcha0,005435, manoizq0,001151, manodcha0,003643 (<0,02rad).

Evidencia take05-conversion/receipt.json, take05-derived-stage.json,
take05-replay-current-state.json, take05-initial-comparison.json,
take05-pc-control-exclusion.json y take05-running-controllers.json.
Recrear: ejecutar convertidor en entornoROS con tipos del bag y --time-scale2
--expected-sha256 del original, copiar derivado nuevo al appMotion y comparar
hash; freshpreflight + físico antes de ejecutar una sola vez playerSDK.
Reversión: conservarbag original, retirar selectivamente derivado/helper si se
descarta; sinconfiguraciónpersistente de robot cambiada. Ensayo físico de este
derivado aún PENDIENTE; no se envió movimiento por la preparación.


### PICO-V4-GEOMETRIC-REPLAY-20261015 — PROBADO FÍSICAMENTE, terminado

15-10-2026 Europe/Madrid: 12:21:54–12:23:24. Una ejecución del
player oficial --robot utars_with_v4_hand --input
/tmp/pico_v4_replay_take05_20261015/take05_geometry_slow.motion, sin--loop.
returncode0, stderrvacío, resultado textual `Action finished with
is_finished=true, bag has been played successfully`. Usuario confirma durante
la pasada que repite bien movimiento y cierreizquierdo, sin resistencia ni
movimiento inesperado reportado. Hardwarelogs de vigilancia sin patrones de
salto/SAFEOP/sobreesfuerzo/fault en el alcanceconsultado.

Postflight nuevo: velocidadmáxima0 en cuerpo ydedos, sinerror_code, delta
actuador/consignamáximo0.003044677rad. Errores respecto
al final del derivado porgrupo: {"head": 0.0013271863844168674, "left_arm": 0.002721995185922088, "right_arm": 0.003044676516222866, "left_hand": 0.005752515730995, "right_hand": 0.0013422536705656185}. Máximo
~0,005753rad en manoizquierda. Estado medido enreposo, conserva postura final
de la toma; NO HOME. Sin nuevos objetivos, cambios de modo o reinicios alfinal.
Clienteplayer terminó; PICO/web se mantuvieron sin mando durante replay.

Queda demostrada reproducción GEOMÉTRICA en vacío de cabeza/brazos/dedos a
mitadvelocidad. No se reproduce el esfuerzo original ni se valida agarrar una
pieza. La escasa variación de mano derecha pertenece a esta toma; no se añade
un cierre inventado. Bagoriginal y sus corrientes/modos se conservan intactos.
No se reprodujeron directamente topics ROS/EtherCAT ni se desactivaron
protecciones; se usó SDK nativo ya instalado. No extrapolar a replay de fuerza
o retención de objetos.

Evidencia: take05-replay-result.json, .stdout/.stderr.log,
take05-replay-postflight.json y -postflight-summary.json, comparacióninicio
y archivos de conversión/stage. Fuentes reproducibles del convertidor nuevo y
los helpers de captura/inspección en repo; before/after/hash externos en esta
carpeta privada. No commit/push.

Próximas tomas con mismoSDK/perfil: reutilizar conversor, nombres/orden y
recetaSDK comprobados; no repetir investigación binaria/interposer. Sí validar
bag/hash/cobertura/rangos, derivado y comparaciónactual de postura/repose/
paros/cargador/fallos/exclusividad. No usar rawactuator para compararq: comparar
por nombres con whole_joint_states y estados reales de manos. No--loop1.
Cambios de efector/software requieren redescubrimiento del contrato.


### REPO-PUBLISH-20261015 — rama y preparación de publicación

15-10-2026 Europe/Madrid. Usuario autoriza crear rama, commits y push de los
cambios de esta carpeta. Se crea feat/pico-v4-workflows-and-scenario-fixes desde
HEADf9b4a6f, sinworktreealternativo, reset o pérdida de ediciones previas.
Inventario y copia externa de todos los cambios al iniciar: evidencia privada
20261015_GIT_PUBLISH_104359Z (working-tree.patch, working-files.tar.gz, status y
secret-scan). Escáner de credenciales sobre añadidos/archivosnuevos sin hallazgos;
ningún.binario/grabación/copia privada se incorpora. Los dos archivos de bloqueo
.entry410-stage.lock y .metamove-head-probe.lock permanecen locales sinseguimiento.

Se conservan cambiosmanuales existentes max_corrections7 y toleranciasalud
0,015rad. Correcciones adicionales para coherencia: consola lee max_corrections
del POLICY; prueba de dosajustes espera49mm (25+24), no50mm. Sin cambiar
trayectorias/límites por esta publicación ni consultar/moverrobot.
Validación local:178tests de escenarios/runtime/salud/teleop/captura/mapa y
18testsbootguard; sintaxis32Python/6Bash, gitdiff--check. shellcheck no instalado.
Agrupación: escenarios, mapas, teleop/manosv4/captura/replay y documentación
transversal. Pushnormal a rama nueva de origin; sinforce ysinmodificar ramas
existentes. Estado de publicación se comprueba contra referencia remota antes
de informar éxito. Reversión Git mediante commits selectivos; robot intacto.
