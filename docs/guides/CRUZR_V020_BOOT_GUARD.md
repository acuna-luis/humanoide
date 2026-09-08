# Cruzr S2 v0.2.0 boot-readiness guard

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
