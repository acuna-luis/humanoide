# Cruzr S2 v0.2.0 boot-readiness guard

**2026-09-10 — Incidente posterior, distinto de la carrera de arranque:**
Tras pasar a PICO y accionar E-stop para instalar la trayectoria, hw se reinició
y quedó esperando arranque; manipulación espera ListControllers. Liberar el
paro no recuperó las acciones. Usuario confirma brazos PICO estables/sin
contacto. La espera instalada en CC se conserva y no es un recuperador después
de cualquier paro. No reiniciar CC para probar desde PICO: puede lanzar HOME
interno. [Diagnóstico y preparación pendiente](../incidents/2026-09-10_PICO_RECARGA_SIN_MOTION.md).

**2026-09-10 — VERIFICADO: self-check, StartMotion y HOME tras liberar el paro.**
La nueva instancia pasó selfcheck=true/error0 y StartMotion succ; estado final
AutoTaskMode (15:08:17 UTC+8). Lectura fresca: paros0/0, cargador0, fault_current
vacío; HOME20D máximo0,002972 rad, brazos0,000959 rad, velocidad0, actuadores
habilitados/sin fallos. Servidor de acciones1 y writers RobotCommand0; VLA
detenido. El usuario cree terminado el arranque. No se enviaron movimientos
adicionales durante la comprobación. Recuperación software cerrada; confirmación
visual del anillo y repetición de arranque en frío pendientes. La prevención
nueva permanece instalada; el guard antiguo sigue deshabilitado.
Evidencia: `../Humanoide-vla-evidence/20260910T064413Z_BOOT-READONLY/after-release/`.

**2026-09-10 — Prevención de arranque instalada; E-stop aún pulsado.**
La nueva intervención confirma la carrera: CC hizo self-check unos 51 s antes
de arrancar el servicio de Motion. [Diagnóstico, instalación, validación y
rollback](../incidents/2026-09-10_ARRANQUE_CONTROL_CENTER_MOTION.md).
Ahora el comando de arranque de CC espera tres respuestas reales de Motion y
después ejecuta el comando original de UBTECH. Mantiene su autodiagnóstico y
HOME interno. Cambió sólo ese comando en compose; se recreó sólo CC bajo paro
confirmado. El registro nuevo demuestra respuestas3/3 y WaitEStopRelease.
El guard systemd antiguo permanece **disabled/inactive**; su comportamiento
descrito más abajo es histórico y no debe confundirse con la prevención nueva.
Comprobación previa terminada rc0: tres respuestas x86, seis cámaras en dos
rondas, versión v0.2.0 y seguridad1/0/0. Se indica al operador liberar el paro
bajo la supervisión ya confirmada. Pendientes confirmación de liberación,
self-check/StartMotion, postura, anillo y repetición de arranque en frío.

**2026-09-09 11:11 UTC — VERIFICADO: anillo blanco y recuperación operativa tras liberar E-stop:**
el propietario confirmó paro liberado y anillo blanco. Lectura nueva: principal0,
fault_current vacío; instancia nueva de CC muestra selfcheck passed=true/error0,
StartMotion succ y transición SelfChecking→JoystickMode. Postura fresca: 20D
válidos, MEASURED_HOME=1, máximo absoluto0,002780 rad (brazos0,000959),
velocidad0 y delta consigna0,002780 rad. Sin nuevos movimientos enviados por
el agente en esta verificación. El fallo histórico 02029001 permanece archivado
con resolve3/Restart (id55); no se forzó el color ni se modificó la base.
Caso de anillo rojo CERRADO. Esto no valida el flujo completo sin AprilTag ni
elimina la deuda separada del error auxiliar VSLAM durante navegación.
Evidencia: `../Humanoide-vla-evidence/20260909T110505Z_CC-RESTART-RED-RING/`.

**2026-09-09 11:09 UTC — VERIFICADO: preparación para liberar E-stop tras retirar aviso rojo:**
`/usr/local/sbin/cruzr-v020-boot-guard --check` terminó rc0 en la instancia nueva.
Tres pruebas funcionales x86, dos rondas de las seis cámaras, versión v0.2.0,
CONTROL_STATE=WaitEStopRelease y SAFETY_STATE=1 0 0 (principal/servo/cargador).
Fue sólo --check, sin otro reinicio ni órdenes de movimiento. Se indica al
operador liberar el paro bajo la supervisión ya confirmada; puede iniciar
HOME interno. Pendientes self-check/StartMotion, ausencia de fallos después de
liberar y confirmación visual del anillo. No declarar recuperación operativa
completa por el mero vaciado de fault_current.

**2026-09-09 11:05 UTC — VERIFICADO: aviso histórico 02029001 archivado tras reinicio único de Control Center:**
operador confirmó E-stop principal pulsado; lectura VOLATILE dio principal1,
servo0. Se ejecutó una sola vez `docker restart --time 5 walker-system.control_center-1`,
rc0. StartedAt cambió de 05:20:04Z a 11:05:01Z (reloj robot, desfasado del PC).
La nueva instancia registró `Found unresolved fault code=02029001, will mark
as resolved with Restart`; fault_current quedó vacío y fault_history incorporó
id55/code2029001/resolve3. No se editó la base, no se simuló resolución ni se
forzó expresión facial. Archivo de mapa MESAS3 fallido no se recuperó; se archivó
su aviso histórico. La causa auxiliar VSLAM de navegación es un asunto separado.
Secuencia nueva: WaitBootReady succ → Recover succ → WaitEStopRelease.
E-stop continúa1. Preparación de arranque en comprobación antes de liberar.
Sin reiniciar Motion/hw, sin comandos de brazos/chasis; el propio Control Center
puede iniciar self-check/StartMotion y HOME interno tras liberar el paro.
Resultado visual blanco y recuperación operativa posterior aún PENDIENTES.
Evidencia: `../Humanoide-vla-evidence/20260909T110505Z_CC-RESTART-RED-RING/`.

**2026-09-09 11:01–11:03 UTC — OBSERVADO, anillo rojo después de HOME:**
lectura SQLite readonly de Control Center muestra únicamente 02029001,
iniciado en 1788935580688 ms: fallo de guardado de mapa durante cartografía.
Los avisos de batería 00001001 ya constan resueltos (resolve1); no son la causa
actual. Catálogo instalado asigna 02029001 a guardado de mapa, solución pendiente.
No hay otros códigos activos en esa consulta. Servicios y contenedores
redescubiertos por Wi-Fi. No se modificó la expresión, la base de fallos ni
se ejecutó fault_solve (el binario lo describe como simulación).
El binario contiene processUnresolvedFaults y el mensaje de archivado de fallos
pendientes como Restart al inicializar; el historial tiene resoluciones tipo3.
INFERENCIA: reiniciar sólo Control Center puede retirar este aviso histórico;
se debe verificar después, sin afirmar recuperado el blanco antes de observarlo.
Intervención preparada: único reinicio de walker-system.control_center-1,
con E-stop principal físicamente presionado por el operador y verificado por
lectura antes de reiniciar; después comprobar nueva instancia y estado de
arranque antes de liberar. Razón: CC puede disparar HOME/StartMotion interno,
como consta en CRUZR_V020_BOOT_GUARD.md. No se ha reiniciado ningún servicio.
La confirmación de corredor libre sigue vigente para esa disposición; esta
petición del paro no vuelve a preguntar por el espacio.
Evidencia: `../Humanoide-vla-evidence/20260909T110137Z_RED-RING/`.

**08-09, recuperación operativa y HOME verificados:** [resultado](../incidents/2026-09-08_HOME_TRAS_RECUPERAR_CONTROL_CENTER.md).
Tras reinicio único de CC y liberación supervisada, self-check/StartMotion
correctos y JoystickMode. HOME20D máximo0,003068 rad, velocidad0, actuadores
sanos; servidor1, VLA detenido/writers0. Confirmación visual posterior pendiente.
Sustituye Fault como estado vigente; causa watchdog6002/SIGSEGV sigue abierta,
sin otro restart de hw ni HOME publicado por agente. Sin monitor persistente.

**08-09, reinicio de Control Center autorizado y completado:** propietario pidió
reiniciar lo necesario y confirmó E-stop principal presionado. Lectura desde
Vision verifica data1 antes de una única llamada docker restart --time5 a
walker-system.control_center-1. rc0; nueva instancia y log muestran
waitBootReady→Recover→WaitEStopRelease, principal pressed/servo released.
No se reinició hw de nuevo: ya estaba reiniciado automáticamente y esperando
/mc/rosa_control/start. No se llamó start, servo enable, reset ni HOME.
Cambio volátil de proceso; sin archivos/configuración modificados en robot,
sin rollback automático porque reanudar puede mover. Mantener paro hasta nueva
comprobación y liberación supervisada. Esto restaura espera de arranque, NO
prueba resuelto el watchdog6002 ni HOME. Relojes hosts/PC con desfase; comparar
instancia/PID y secuencia, no ordenar timestamps de hosts distintos a ciegas.
Evidencia: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260908T083040Z_SERVICE-RECOVERY/`. Sin monitor persistente.

**08-09, EtherCAT diagnosticado:** [secuencia y límites](../incidents/2026-09-08_DIAGNOSTICO_ECAT_6002.md).
6002 identificado como FT derecho; enumerado antes del watchdog0x1b durante
SAFEOP→OP. Master falla y hw sufre SIGSEGV; Docker lo reinicia una vez,
sin restaurar Motion. OOMfalse. Causa física/software primaria aún no aislada;
no demuestra sobrecarga ni sensor averiado. Sólo lectura; no reparaciones ni
reintentos. Pendiente revisión técnica de bus/sensor y fallo software.

**08-09, resultado tras liberación supervisada: FALLO StartMotion.** Self-check
passed=true/error0, pero StartMotion fail reason19 y Control Center Fault.
Log hw: sensor FT KunWeiTech EtherCAT 6002 queda SAFEOP ERROR (0x14),
Sync manager watchdog (0x1b); no alcanza OP, master error0x98110024. Después
fallo del proceso hw y timeout de /mc/servo/enable. Manipulación espera
ListControllers; servidor de acciones0, actuadores sin muestra (timeout7s).
Paros0/0 y cargador0 en consulta. No asignar lado físico a6002 sin cotejar mapa;
no interpretar watchdog como prueba de daño o repetir reinicio a ciegas.
Readiness previo x86/cámaras sí pasó; no garantizaba inicialización EtherCAT.
HOME/estado físico de servos no verificables. Sólo diagnóstico desde agente:
ningún HOME, rearme, restart o cambio de protecciones. Sin monitor persistente.
Evidencia: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260908T082533Z_BOOT-AFTER-RELEASE/`.

**08-09, siguiente arranque preparado para liberación supervisada:** operador
confirma brazos abajo, abrazaderas vacías, estabilidad/sin contacto, recorrido
libre, ruedas bloqueadas y persona junto al paro. Primera consulta Motion
agotada; posterior descubrimiento observa contenedores recién iniciados.
Guard instalado leído y ejecutado sólo --check: rc0, v0.2.0, WaitEStopRelease,
x86 funcional 3/3, seis cámaras 2/2, seguridad 1/0/0 (principal/servo/cargador).
No reinicio ni movimiento desde agente. Condiciones técnicas previas satisfechas
para liberar el principal bajo supervisión confirmada; puede iniciar HOME
interno. Pendientes self-check/StartMotion y medición 20D posteriores; no se
considera HOME ni recuperación final completada. No monitor persistente.
Evidencia: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260908T082050Z_BOOT-BEFORE-RELEASE/guard-check.log`.

## Control Center configuration review — 2026-09-07

Read-only inspection confirmed its startup loads base.conf and cc.conf. Neither
installed file contains a HOME/StartMotion suppression option. This is limited
to those files, not proof that no vendor interface exists. No configuration,
ROS call or restart was performed. Guard remains disabled, active/exited;
internal HOME is still not contained. Hashes and scope are recorded in
`docs/incidents/2026-09-07_DIAGNOSTICO_ARRANQUE_SOLO_LECTURA.md`.

## Authorized containment — 2026-09-07 ~09:44 UTC

Vision guard automatic startup is now **disabled**, explicitly authorized by
the operator. Only `systemctl disable cruzr-v020-boot-guard.service` was run,
without --now, stop, restart or mask. The multi-user.target.wants symlink was
removed; installed unit and script hashes are unchanged. Subsequent read-only
snapshot confirms UnitFileState=disabled and unchanged execution timestamps
(active/exited oneshot). Backups before/after: 20260907T093815Z_BOOT-READONLY and
20260907T094421Z_BOOT-READONLY, external evidence root; latter manifest verified.

This does NOT inhibit Control Center's internal HOME or manual guard execution.
Do not release E-stop or reboot as validation. Re-enabling the unit is a possible
rollback but requires review and fresh authorization; it was not performed.
Older enabled/status statements below are historical, superseded here.

## Live read-only verification — 2026-09-07 09:38 UTC

Vision service remains enabled, active/exited (oneshot completed). Installed
script SHA-256 `6c3cbe48bb7cd177b8e2a446118c3f78ed1dea5083c0839714ce93ff5b89287b`.
It lacks the repository incident-block branch for --run; no deployment was done.
Copies and metadata preserved in `20260907T093815Z_BOOT-READONLY/` outside Git.
No guard execution, ROS calls or service restart was performed. Disabling only
automatic startup is proposed pending specific approval; it would not block
vendor Control Center HOME. See the read-only boot diagnostic incident note.

> **07-09 — contención local implementada:** [estado de recalificación](../incidents/2026-09-07_REQUALIFICACION_CLAMPS.md).
> Doce variantes de lanzamiento rechazadas en tests sin conexión; no cubre
> HOME interno del arranque, UI/PICO ni el guard instalado en Vision.
> E-stop mantenido; no liberar ni reiniciar para probar. Inspección reportada:
> daño sólo en carcasa; clamps restauradas. Geometría bilateral y barrido
> pendientes; E6.0K retirado para nuevos PASS. No hubo despliegue ni movimiento.

## Safety correction — 2026-09-07

The [contact audit](../incidents/2026-09-07_AUDITORIA_CONTACTOS_HOME.md) found
that vendor `StartMotion` invoked `cruzr/home` on both September 4 boots.
The first HOME produced excessive left FT and failed. Restarting from READY,
an asymmetric pose or contact is therefore **not** a universally safe recovery.
The instructions below describe historical behaviour, not permission to retry.
Releasing E-stop at boot may lead to movement without a PC-issued HOME goal.

This guard and Control Center must be included in trajectory/incident interlock
review. The audit did not disable or change either service; the guard was
observed active/enabled on September 7. No entries were returned by its journal
for the incident interval, which does not establish whether it intervened.

## Purpose

After the offline v0.2.0 upgrade, the Vision computer can start Control Center
before the Motion computer has published its x86 self-check services. Control
Center then records `Service not available`, finishes self-check with
`passed=false`, enters `Fault`, shows a red face circle and leaves the head in
its lowered boot pose.

The guard installed on the Vision computer addresses only this confirmed race.
It does not modify the UBTECH images, uDoke configuration, Docker Compose,
maps, calibration, `HW_TYPE`, end-effector configuration or VLA state.

## Behaviour

At every Vision-computer boot, the guard:

1. waits for the Vision ROS and Control Center containers;
2. waits for Control Center to publish its version and verifies that the
   installed system is exactly v0.2.0;
   it reads the current persistent ROSA log and therefore does not depend on
   Docker JSON logs surviving an unclean power cut;
3. waits for the Motion computer's x86 self-check services and motion actions;
   because DDS may advertise stale names before the x86 server is functional,
   readiness requires three successful lightweight `file_presence_check`
   responses separated by 15 seconds;
4. requires two successful rounds of real image samples from all six cameras
   used by the vendor self-check;
5. reads the latest Control Center state and classifies the original failure;
6. exits without changes if the state is already `JoystickMode`, or if it is
   safely waiting in `WaitEStopRelease` for a person to release the physical
   E-stop;
7. proceeds only when the state is exactly `Fault`, the log matches the known
   v0.2.0 readiness race, power/servo/overcurrent checks passed and both
   emergency stops and the charger report `0`;
8. restarts only `walker-system.control_center-1`;
9. waits for a new container start timestamp and a new persistent log before
   evaluating recovery, preventing stale `Fault` data from the old process;
10. requires self-check success, `StartMotion` success and `JoystickMode`;
11. sends the official `cruzr/move_head_home` task after rechecking the safety
   inputs.

The service has finite timeouts and performs at most one recovery per boot. It
does not retry indefinitely and does not bypass a failed safety input.

Do not use the internal `KEY1` as a standalone normal shutdown control. Use the
approved shutdown sequence for the robot; an abrupt body-computer power cut can
corrupt Docker JSON logs and interrupt filesystem writes.

After an emergency stop during normal operation, releasing the E-stop does not
necessarily restore Motion. On 2026-09-03 this unit remained in
`WaitStartMotion` with zero manipulation action servers. A single press of the
external rear Power/Start button was logged as `Power click` and only announced
the battery level; it did not generate `ButtonStartMotion`. Section 5.3.3 of the
vendor manual prescribes powering off and restarting the complete robot after
an emergency stop. Do not repeat the Power-button press or invoke `StartMotion`
over ROS as an improvised recovery; perform the supervised full power cycle.

That supervised restart was completed on the same date with the E-stop held.
Control Center correctly entered `WaitEStopRelease`; after the operator
released it, self-check and `StartMotion` passed and the terminal state was
`JoystickMode`. The first guard revision did not recognize
`WaitEStopRelease`, timed out with `CONTROL_STATE=unknown` and performed no
recovery. The current revision treats this state as a safe terminal defer:
`--run` records `NO_ACTION=waiting_for_physical_estop_release` and exits
without restarting a container or commanding the head.

On 2026-09-04, releasing the E-stop again left Motion without its joint-state
stream or manipulation action server. A second complete supervised power cycle
was performed with the main E-stop held during startup. After release, the
Vision guard reported `JoystickMode`, all graph/camera probes passed, and the
Motion preflight recovered `ACTUATORS_OPERATION_ENABLED=1`, joint state and the
action server. This confirms the full power cycle as the recovery used on this
unit; isolated Power/KEY1 presses remain unsupported.

## Files installed on Vision

- `/usr/local/sbin/cruzr-v020-boot-guard`
- `/etc/systemd/system/cruzr-v020-boot-guard.service`
- `/usr/local/share/doc/cruzr-v020-boot-guard.md`

## Status and logs

These commands run **on the Vision computer**, not on the Ubuntu control PC.
From the control PC, the read-only check is:

```bash
ssh walker@192.168.11.3 '/usr/local/sbin/cruzr-v020-boot-guard --check'
```

Running the repository copy directly on the PC will only inspect the PC's
Docker instance and can misleadingly report `containers_not_ready`.

```bash
sudo systemctl status cruzr-v020-boot-guard.service
sudo journalctl -u cruzr-v020-boot-guard.service -b --no-pager
sudo /usr/local/sbin/cruzr-v020-boot-guard --check
```

`--check` is read-only: it does not restart a container or command movement.

## Rollback

```bash
sudo systemctl disable --now cruzr-v020-boot-guard.service
sudo rm /etc/systemd/system/cruzr-v020-boot-guard.service
sudo rm /usr/local/sbin/cruzr-v020-boot-guard
sudo rm /usr/local/share/doc/cruzr-v020-boot-guard.md
sudo systemctl daemon-reload
```

Disable and review this workaround before applying a future UBTECH system
upgrade. Versions other than v0.2.0 are skipped automatically.
