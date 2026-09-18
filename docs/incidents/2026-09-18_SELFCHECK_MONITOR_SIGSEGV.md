# 2026-09-18 — Arranque bloqueado en SelfChecking por caída de self_check_monitor

Lectura remota únicamente; sin reinicios, cambios ni comandos de movimiento.
Horas del robot en CST (China, UTC+8), 6 h por delante de Europe/Madrid:
14:29 del robot = 08:29 en Madrid.

## Síntoma

Tras encender y liberar el E-stop, la cabeza siguió en la postura baja de
arranque y no se ejecutó el HOME interno.

## Secuencia observada

| Hora | Evento |
|---|---|
| 14:24 | Arranque de Motion y Vision. |
| 14:27:38 | Control Center: `waitBootReady → WaitEStopRelease` (principal pulsado, servo liberado). |
| 14:28:52 | Gate CC: voz «Ready to release the emergency stop». |
| 14:29:03 | E-stop liberado: `EnterWorkMode → SelfChecking`, modo joystick OK. |
| 14:29:03–09 | Comprobaciones aarch64/x86 de archivos, sistema y SN pasan; `audio_loopback_check` falla (0,3465 < 0,40, no bloqueante: el 17-09 también falló y el resultado global fue `passed`). |
| 14:29:08 | **`self_check_monitor_node` (Vision) SIGSEGV** en `rosa::ReaderBase::activateImpl` / callback iceoryx. |
| 14:29:09 | Docker reinicia `walker-system.self_check_monitor-1` (RestartCount=1). |
| ≥14:41 | Control Center sigue en `SelfChecking` sin `selfcheck result`; nunca llama `StartMotion`. |

En Motion, `rosa_control_node` espera `/mc/rosa_control/start` desde 14:26:45 y
`robot_app` repite `ListControllers: service not available`: sin StartMotion no
hay controladores, servidor de acción ni HOME.

En arranques correctos (17-09) el resultado del self-check llega ~12 s después
de entrar en `SelfChecking`. El SIGSEGV sólo aparece en el log de este arranque.

`cruzr-v020-boot-guard --check`: x86 3/3, cámaras 2/2, v0.2.0,
`CONTROL_STATE=unknown`, seguridad `0 0 0`, `RECOVERY_ELIGIBLE=0`. El guard no
cubre este caso (sólo la carrera `Fault` conocida).

## Causa raíz

Condición de carrera en el middleware ROSA/iceoryx del proveedor (binario
cerrado `self_check_manager`, imagen `zs2_vision-v0.2.0`):

1. `sensor_fps_check` crea ~15 lectores iceoryx temporales (`CheckTopicData`,
   `persistent: 0`) sobre temas `/…/fps` que el monitor ya tiene suscritos de
   forma permanente. El hilo listener de iceoryx (tid 140) atiende ambos.
2. 14:29:08.548–08.575: todas las comprobaciones terminan a la vez y los
   lectores temporales se destruyen en paralelo (`~ReaderAdapter`, `~ReaderBase`)
   desde varios hilos.
3. 14:29:08.602: el listener invoca el callback de un lector ya destruido
   (`rosa::ReaderBase::activateImpl` lambda ← `iox::popo::NotificationInfo`):
   use-after-free → SIGSEGV.
4. Docker reinicia el contenedor, pero la meta de self-check de Control Center
   se pierde con el proceso; CC no tiene timeout y queda en `SelfChecking`.

Frecuencia: 1 caída en 59 logs de `self_check_monitor_node` conservados.
La configuración (`check_config.xml`) no expone `persistent`; no hay ajuste
que elimine la carrera sin quitar comprobaciones de sensores. Corrección real:
proveedor (informe preparado el 18-09; envío PENDIENTE). Mitigación propia instalada: BOOT-04 en
`docs/SYSTEM_CUSTOMIZATIONS.md` (detecta el bloqueo, pide E-stop, reinicia sólo
CC; la liberación sigue siendo humana).

## Evidencia (Vision)

- `/etc/walker/log/system/cc_main.20260918_142735.835.log`
- `/etc/walker/log/system/self_check_monitor_node.20260918-142509.71.log` (stack trace)
- `/etc/walker/log/system/self_check_service.20260918-142509.72.log`
- Motion: `/etc/walker/log/motion/robot_app.20260918-142644.64.log`,
  `rosa_control_node.20260918-142643.65.log`

## Recuperación

PENDIENTE. No se ha reiniciado nada. Opción documentada: apagado/encendido
completo supervisado con E-stop pulsado y `scripts/cruzr_boot_ready.sh --check`
antes de liberar. Reiniciar sólo Control Center con el paro liberado podría
lanzar self-check, StartMotion y HOME sin nueva confirmación: pulsar antes el
E-stop.

Sin relación con MOT-05: `cruzr/originalhome` no estaba instalado y `cruzr/home`
seguía siendo body-first v4 (`e3d06564…`).
