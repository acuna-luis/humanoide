# Auditoría de voces de arranque, paro y apagado

**23-09-2026 — VOICE-BRAKE-07: idioma del aviso de freno instalado.**
Frase exacta de backend_service_vision→WAV español; lógica/condición del freno
intactas.7 hashes correctos, prueba nativa y a través del entrypoint instalado
pasan, cero objetivos/audio. Paro1 verificado. Carga real al próximo inicio del
backend y escucha PENDIENTES; sin restart ni movimiento. Rollback independiente.
[Fuentes, evidencia y reversión](AVISO_FRENO_ES_ROLLBACK_20260923.md).


**23-09-2026 — aviso chino intermedio identificado (VOICE-BOOT-05, cobertura pendiente).**
Speech Service registra a17:57:09.435 (hora nativa) el TTS
«当前抱闸被锁死，请操作底盘解抱闸按钮，解锁抱闸», goal
1d8b0278-a42a-4ed1-ad21-5d47ea3feeee. Significado: «El freno del chasis está
bloqueado; utilice el botón de liberación del freno del chasis para desbloquearlo».
Es traducción del aviso observado, no instrucción de desbloqueo en esta revisión.
Queda entre WAV español cc_006/autocomprobación superada (17:57:02.520) y
cc_007/control de movimiento iniciado (17:57:11.358). No aparece entre las
emisiones processRequest del CC consultadas; cliente emisor exacto PENDIENTE.
No queda cubierto por los24 textos de CC; añadirlo sólo al catálogo no garantiza
interceptar otro cliente. También existe TTS chino a17:54:31 sobre tarea no
asignada, anterior a esa secuencia, pendiente de integración separada.
Sólo lectura; no se modificó freno, red, servicios ni audios. Evidencia: /home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260923T095843Z_VOICE_CHINESE_GAP.

**23-09-2026 11:39 CEST — VOICE-BOOT-05 instalada con rollback.**
Control Center:24 avisos fijos a WAV español, patrón de batería a TTS inglés;
mensajes desconocidos preservados.32 archivos verificados; guard de hashes y
LD_PRELOAD antes del exec, gates originales idénticos por comparación AST.
Paro1 antes/después. Prueba nativa de objetivos pasa, cero audio/movimiento.
Proceso actual aún sin adaptador; carga al próximo inicio y escucha PENDIENTES.
No reinicios ni cambios de red. Recibo externo20260923_VOICE_CC_DEPLOY/receipt.json;
backup persistente /etc/walker/voice/deployments/cruzr-voice-20260923T093840Z.
[Fuentes, compatibilidad, validación y rollback](CONTROL_CENTER_ES_ROLLBACK_20260923.md).


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

23-09-2026, Europe/Madrid. VOICE-BOOT-05. Diagnóstico; ninguna modificación remota.

## Hallazgo y alcance

OBSERVADO por el operador: tras liberar paro, apagar y encender manteniendo paro,
los avisos escuchados siguen en chino. No hay grabación ni registro del último
reinicio disponible todavía. SSH a Vision agotó ConnectTimeout; no se infiere
apagado a partir del fallo de conexión.

VERIFICADO en registros históricos de Control Center: `cc processRequest()`
emite `start tts, text:...` desde `tts_impl.cpp:187`, incluidos avisos de arranque,
paro y apagado. VOICE-EN-04 sólo se carga mediante el lanzador de ae_bt_worker;
no adapta esta ruta propia de Control Center. VOICE-ES-03 cambia XML TtsClient y
muestras grabadas, no estos mensajes. Reiniciar no amplía ese alcance.
La instalación anterior fue incompleta respecto a todos los avisos solicitados.
No está demostrado que los archivos instalados se hayan perdido tras reiniciar.

## Inventario observado

28 textos distintos en los logs históricos examinados; incluye cuatro ejemplos
numéricos de batería. No es el inventario exhaustivo de todos los mensajes posibles.
Las traducciones siguientes son propuestas de contenido, no instrucciones para
el operador ni audio instalado. No ejecutar los mensajes de paro/reinicio como
procedimiento de recuperación.

| Original observado | Significado en español |
|---|---|
| 正在恢复上次异常状态 | Recuperando el estado anómalo anterior. |
| 恢复完成 | Recuperación completada. |
| 正在准备 | Preparando. |
| 准备完成 | Preparación completada. |
| 开始自检 | Iniciando autocomprobación. |
| 自检通过 | Autocomprobación superada. |
| 运控启动成功 | Control de movimiento iniciado correctamente. |
| 已进入遥控模式 | Modo de control remoto activado. |
| 开始充电 | Iniciando carga. |
| 退出遥控模式 | Saliendo del modo de control remoto. |
| 已进入遥操模式 | Modo de teleoperación activado. |
| 退出遥操模式 | Saliendo del modo de teleoperación. |
| 开始选择工作模式，当前处于遥操模式 | Selección de modo de trabajo; actualmente en teleoperación. |
| 退出模式切换 | Saliendo de la selección de modo. |
| 急停已按下 | Paro de emergencia pulsado. |
| 请旋转并松开急停按钮 | Gire y libere el botón de parada de emergencia. |
| 急停已释放 | Paro de emergencia liberado. |
| 运控启动失败 | Fallo al iniciar el control de movimiento. |
| 正在关机 | Apagando. |
| 自检失败 | Autocomprobación fallida. |
| 请在确保安全的情况下，按下急停键，继续关机流程 | Cuando sea seguro, pulse el paro de emergencia para continuar el apagado. |
| 请先重启运控再执行操作 | Reinicie primero el control de movimiento antes de realizar la operación. |
| 当前电池电量分别是67%，75%。 | Las baterías están al 67 % y al 75 %. |
| 已进入自动任务模式 | Modo de tareas automáticas activado. |
| 退出自动任务模式 | Saliendo del modo de tareas automáticas. |
| 当前电池电量分别是78%，80%。 | Las baterías están al 78 % y al 80 %. |
| 当前电池电量分别是72%，73%。 | Las baterías están al 72 % y al 73 %. |
| 当前电池电量分别是58%，70%。 | Las baterías están al 58 % y al 70 %. |

## Evidencia y siguiente comprobación

Evidencia privada: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260923T091349Z_VOICE_BOOT_AUDIT`. `cc-utterances.json` conserva la primera línea y archivo
por texto; `discovery.json` registra el intento SSH. Fuente histórica:
`20260907T053541Z_CONTACT-AUDIT/vision/etc/walker/log/system/cc_main*.log`.

Pendiente: recuperar conexión, redescubrir contenedores, obtener log del arranque
actual y emisiones del servicio de voz; verificar los hashes instalados después
del reinicio; identificar configuración/API real de idioma del cliente de Control
Center y sonidos de autocomprobación. Revisar también extensiones/rutas omitidas:
el respaldo inicial de textos no incluía `.conf` ni binarios generales.
No sustituir audio de autocomprobación sin revisar su comparación/validación.

No se instala el adaptador de workers en Control Center a ciegas: su símbolo y
ruta son distintos. Cualquier integración debe conservar mensajes de fallo,
respaldo inmediato y rollback independiente, sin alterar la máquina de estados.
No hubo reproducción, reinicio, liberación, movimiento ni cambio de configuración.
Rollback de este diagnóstico: sólo notas locales; respaldos previos en before-docs.

**23-09-2026 11:17 CEST — conectividad comprobada:** Ethernet `eno1` y Wi-Fi
del robot `wlx80afcad40bd6` están DOWN; sólo DSA CORPORATE está activa. La ruta
a Vision usa la puerta de enlace corporativa, y SSH agota timeout. No demuestra
un fallo de Vision: falta conexión local al robot. Ningún cambio de red o robot.
