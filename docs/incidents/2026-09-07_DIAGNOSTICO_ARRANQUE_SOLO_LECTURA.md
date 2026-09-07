# Diagnóstico conectado de arranque — 07-09-2026

## Actualización posterior: cambio autorizado y verificado

El operador autorizó expresamente deshabilitar sólo el arranque automático del
guard de Vision, sin detener ni reiniciar servicios. El 07-09, antes de la
captura de 09:44:21 UTC (~11:44 Madrid), se ejecutó por SSH únicamente:

`sudo -n systemctl disable cruzr-v020-boot-guard.service`

Salida 0: retirado el enlace exacto
`/etc/systemd/system/multi-user.target.wants/cruzr-v020-boot-guard.service`,
cuyo destino se había verificado como
`/etc/systemd/system/cruzr-v020-boot-guard.service`. No se usó `--now`, stop,
restart ni mask. No se ejecutó el guard ni se modificó Control Center.

Verificación posterior: **UnitFileState=disabled**; ActiveState=active,
SubState=exited, mismo ExecMainStartTimestamp y ActiveEnterTimestamp que antes.
Esto es un oneshot terminado, no un proceso que permanezca trabajando.
Hashes del script y unidad idénticos a la captura anterior. No se borraron
esos archivos: sólo el enlace de autoarranque. El cambio es reversible mediante
reenabling de la unidad, **sin hacerlo durante el incidente ni sin nueva revisión
y autorización**, pues devolvería la automatización de arranque. No se necesita
reiniciar el robot para comprobar UnitFileState.

Copias previas: `20260907T093815Z_BOOT-READONLY/`. Copias y estado posteriores:
`20260907T094421Z_BOOT-READONLY/`, en la raíz externa de evidencias. Manifiesto
posterior verificado. El campo remote_configuration_changes=0 del colector
describe sólo esa captura de lectura, **no el cambio autorizado precedente**.

**Alcance cerrado:** autoarranque de este workaround local deshabilitado.
**No cerrado:** HOME interno de Control Center, ejecución manual del guard,
registro geométrico, recorridos y autorización física. Deshabilitar no equivale
a mask; la unidad aún existe. No se alteraron paros, FT, watchdogs ni límites.

## Alcance y procedencia

Primera consulta conectada de esta continuación, **sólo lectura**. Ruta PC a
Motion observada: `192.168.11.2 via 192.168.42.2 dev wlx80afcad40bd6`, IP PC
`192.168.42.215`. SSH identifica hosts `motion` y `vision`; se reutiliza el
mecanismo askpass del proyecto sin publicar credenciales. No se ejecutó el
script de recuperación: sólo su rama de suministro de credencial a SSH.

Colector versionado `scripts/collect_boot_diagnostic_readonly.py`. Consultas
fijas: hostname, uptime, propiedades limitadas de systemd, `docker ps -a` y
lectura de los dos archivos del guard. **Sin ROS, docker exec, guard --check/run,
restart, start/stop, recarga, escritura de configuración remota ni movimiento.**
La actividad SSH puede dejar registros normales de acceso; no se afirma que
el host no registre nada. No se verificó postura, paros, cargador o salud física.

Captura: 2026-09-07 09:38:15 UTC (~11:38 España peninsular), evidencia local:
`/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260907T093815Z_BOOT-READONLY/`.
Incluye JSON por host, copias del guard, resumen, colector y manifiesto SHA-256.
Las horas de uptime/systemd son literales del host; no confundir CST con Madrid.

## Hallazgos actuales

| Elemento | Lectura | Alcance |
|---|---|---|
| Vision guard | enabled; active/exited; ExecMainStatus=0 | Habilitado para siguientes arranques; ejecución de oneshot terminada |
| Unidad systemd | ExecStart del guard con --run; RemainAfterExit=yes | No implica ejecución continua ni movimiento actual |
| Guard instalado | SHA-256 `6c3cbe48bb7cd177b8e2a446118c3f78ed1dea5083c0839714ce93ff5b89287b` | No contiene el bloqueo añadido al repositorio |
| Diferencia contra repositorio | Falta únicamente la rama --run que termina con exit 78 por incidente | Bloqueo local no desplegado |
| Control Center | Contenedor en ejecución en Vision | No se deduce estado interno ni paros a partir de docker ps |
| Manipulation robot app | Contenedor en ejecución en Motion | No demuestra actuadores habilitados ni postura |
| VLA control / inference | Ambos Exited (137), antigüedad reportada 3 días | No arrancados por este diagnóstico; no inferir causa del código 137 |
| Guard en Motion | Unidad/archivos no encontrados | Coincide con que este guard se instaló en Vision |

El contenido de la copia instalada conserva ramas que pueden reiniciar Control
Center y enviar `cruzr/move_head_home` si se cumplen sus condiciones. No se
ejecutaron esas ramas ni se atribuye movimiento actual a ellas. La comparación
`diff` se efectuó entre la copia conservada y el repositorio local.

## Acción propuesta, todavía NO realizada

Deshabilitar **únicamente su arranque automático** en Vision, conservando copia
y evidencia previa, sin parar/reiniciar servicios ni ejecutar el guard.
Es una modificación remota y se solicita autorización específica antes de hacerla.
La lectura posterior de UnitFileState verificaría la deshabilitación; no un
reinicio del robot. No se propone hacer disable --now ni cambiar Control Center.

Esta acción sólo contiene el workaround local. **No intercepta el HOME interno
de Control Center ni vuelve seguro liberar E-stop.** No se eliminarán servicios
de seguridad ni se editará la máquina de estados vendor para aparentar readiness.
Si se autorizase la acción, documentar copia exacta, resultado y reversión
controlada; no ejecutar una reversión que reactive movimiento durante incidente.
