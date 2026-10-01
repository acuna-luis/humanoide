# HOME: cuerpo a cero antes de los brazos

**30-09-2026 — BOX-01-HOME-RETRY-01: supervisor optimistic, XML intacto.**
El ejecutor PC puede repetir una vez HOME completo tras7104050/status6 y nuevas
comprobaciones de salud/reposo, por solicitud del operador. Conserva presupuesto
en checkpoints y HOME final medido. No modifica HOMEv8 automático, deltas,
tiempos ni límites, ni demuestra la trayectoria desde cualquier postura parcial.
Implementado/verificado offline; sin conexión, movimiento ni nueva instalación
HOME. Recuperación física PENDIENTE.
[Alcance, verificación y reversión](../box_handling/OPTIMISTIC_SCENARIO1.md#un-reintento-de-home-tras-aborto-confirmado--30-09-2026).

**30-09-2026 — HOMEv8: fallo observado del primer tramo del elevador.**
Mismo XML d9e94627… y MetaMove bfeab1c7… releídos; en un ciclo tras depósito,
el elevador no alcanza0 en3,75s y aborta con7104050/status6. Brazos sólo completan
ajustes relativos iniciales. Muestras posteriores inmóviles/habilitadas/sin
error de servo, pero cuerpo/brazos fuera de HOME. Causa interna y recuperación
PENDIENTES; no basta omitir el gate final ni asumir que repetir deltas sea seguro.
Sin cambios de XML, tiempos, tolerancias o control en esta revisión.
[Diagnóstico y evidencia](../box_handling/OPTIMISTIC_SCENARIO1.md#home-abortado-en-el-elevador--30-09-2026).

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
Salida de su Fault previo NO verificada. [Prueba, evidencia y límites](CRUZR_HOME_V8_CANDIDATA.md).

**22-09-2026 — HOME-V8-CANDIDATE-01 instalada de forma aditiva, sin movimiento.**
Tarea separada home_v8_early_roll_CANDIDATE reparte apertura−0,05/−0,15rad
con el primer ajuste de codo; mantiene13,45s nominales y destinos finalesv7.
No es condicional ni recuperación general. Lectura actual y barridos501,
3tests offline correctos; sincronización/seguimiento y prueba física pendientes.
HOME automáticov7 intacto; sin reinicios, task_list ni acciones. Candidata
instalada, carga nativa pendiente. [Fuentes, límites, backup y receta](CRUZR_HOME_V8_CANDIDATA.md).

**22-09-2026 — Revisión HOMEv7: fallo del primer paso de codo confirmado.**
XML y MetaMove remotos coinciden con fuentes/hashes previstos. El primer delta
izquierdo conserva hombro roll0,116678 fuera de máximo0,0987266:500 consignas
rechazadas, codo izquierdo no completa; derechoSUCCESS. Se abortan cuerpo/cabeza
en paralelo. Misma limitación que18-09, no recuperación universal. Operador
confirma estable/vacío/sin contacto; sólo revisión, ninguna orden física.
[Secuencia, evidencia y recuperación aún pendiente](../incidents/2026-09-22_ARRANQUE_HOME_INCOMPLETO.md).

## Histórico: v7 (13,45 s), instalado 2026-09-18 y sustituido 22-09

`cruzr/home` = [`cruzr_internal_home_body_first_v7_13s.xml`](../../scripts/teleoperation/tasks/cruzr_internal_home_body_first_v7_13s.xml)
(SHA `1e6e2fb7…`). Primer tramo (3,75 s): cabeza/elevador/cintura a cero y, en
paralelo, cada brazo en secuencia codo −0,03 rad (1 s) y apertura de hombro
−0,2 rad (1,8 s); bajada abiertos a roll −0,3 en 7 s; cierre a cero en 2,7 s.
Historia, barridos, ensayos y backups: MOT-01 en
[`SYSTEM_CUSTOMIZATIONS.md`](../SYSTEM_CUSTOMIZATIONS.md) e incidentes del 18-09.

**Instalar/reinstalar** (`cruzr_install_internal_home_body_first.py`):

1. `--check` (local).
2. Con el robot en HOME y el **E-stop liberado**: `--measure-home` (sólo lectura;
   con el paro pulsado Motion no publica posiciones).
3. Sin lanzar ninguna tarea, pulsar el E-stop: `--preflight` → `--install`
   (exige registro de HOME < 30 min, mismo arranque y ninguna tarea después).
4. Apagado/encendido con E-stop pulsado; liberar tras «Ready…».

**Límite conocido:** el paso de codos no cubre otras articulaciones. Si una queda
fuera de su límite blando (p. ej. tras un E-stop en plena tarea), el HOME de
arranque falla sin mover ese brazo: recuperar con una orden puntual sólo sobre
esa articulación, verificada y supervisada.

## Histórico: v4 (20 s), 2026-09-16

2026-09-16, Europe/Madrid — HOME-BODY-FIRST-04.
Petición del propietario: modificar y cargar cruzr/home. Operador confirma
E-stop pulsado y HOME; lectura previa verifica principal1, servo0, cargador0,
MetaMove con hash esperado y XML anterior exacto. No se envían acciones.

## Cambio y alcance

Orden: cabeza/elevador/cintura a cero (3,75 s), apertura relativa de ambos
hombros (2,5 s), bajada abiertos (10 s), cierre de brazos abajo (3,75 s).
Total20 s, mismas consignas y tiempos que open_v3, sólo se reordena el cuerpo.
Al enderezar se conservan ángulos de brazos, no su posición cartesiana.
Afecta también HOME automático de arranque y llamadas de otros flujos.
No valida posturas arbitrarias, carga sujeta, proximidad a muebles ni parada.
Los barridos geométricos de open_v3 no califican este nuevo orden.

Fuente: `scripts/teleoperation/tasks/cruzr_internal_home_body_first_v4_20s.xml`.
Generador/validador: `scripts/teleoperation/cruzr_internal_home_body_first.py`.
Destino Motion, contenedor `walker-motion.manipulation_robot_app-1`:
`/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config/cruzr/home.xml`.
Antes SHA256 `05174d2b4cf003b9b1c5274cd445b0d4faefe4276c5fbe8e59e68e6b64ee8cbe`.
Después SHA256 `e3d0656424a3611d89262ae645f127d975920fd09c437f9ef9c07725d69dc49c`.
La tarea y task_list conservan nombre/registro; no se cambian protecciones.
Preflight de `cruzr_blue_workbin_cycle.sh` reconoce el hash exacto nuevo y exige
la misma biblioteca MetaMove; desconocidos siguen rechazados.

## Reproducción

Desde raíz del repositorio, con condiciones físicas revisadas y paro mantenido:

```bash
python3 scripts/teleoperation/cruzr_install_internal_home_body_first.py --check
python3 scripts/teleoperation/cruzr_install_internal_home_body_first.py --preflight
python3 scripts/teleoperation/cruzr_install_internal_home_body_first.py --install
python3 scripts/teleoperation/cruzr_install_internal_home_body_first.py --reload
```

Instalación atómica con control de hash concurrente y respaldo. Instalador sólo
acepta open_v3 exacto o esta versión; tras firmware distinto debe revisarse.
Reload reinicia exclusivamente manipulación; no llama StartMotion ni libera
el paro. Una recarga no demuestra operatividad ni autoriza liberar el E-stop.
Seguir guía CRUZR_V020_BOOT_GUARD si queda WaitStartMotion.

Respaldo robot: `/etc/walker/trajectory-overlays/20260916T114457.191983Z_home_body_first_v4/`.
Copia externa previa: `../Humanoide-vla-evidence/20260916T114256Z_HOME_BODY_FIRST/home.json`
(contiene el XML leído). Evidencia instalación:
`../Humanoide-vla-evidence/20260916T114519.052551Z_INTERNAL-HOME-CHANGE/`.
Evidencia recarga:
`../Humanoide-vla-evidence/20260916T114548.005531Z_INTERNAL-HOME-CHANGE/`.
Los relojes PC/robot difieren; usar recibos e identidad de proceso.

Reversión: bajo paro y condiciones revisadas, restaurar sólo home.xml desde
home.before.xml del respaldo, verificar SHA anterior y recargar con el
instalador histórico `cruzr_install_internal_home.py --reload`. No ejecutar
HOME ni reiniciar automáticamente al revertir. Conservar cambios ajenos.

Verificación local: diez pruebas (secuencia sin comandos de brazo en primera
etapa, preservación de consignas/tiempos, hash, rechazos, instalación atómica,
conflictos concurrentes y contrato canónico). Sintaxis Bash correcta.
INSTALADO verificado por hash tras escribir. Prueba física PENDIENTE.
Resultado final de recarga y disponibilidad: véase actualización al final.

## Resultado posterior

VERIFICADO: reinicio único de manipulación, StartedAt pasó de
2026-09-16T11:41:44.036544394Z a2026-09-16T11:45:26.685601422Z.
Hash nuevo intacto y paro mantenido después. RECARGA solicitada/completada como
reinicio de proceso; carga funcional de tareas PENDIENTE porque Motion espera
ListControllers y Control Center permanece WaitStartMotion tras el paro.
No liberar para probar: procede ciclo completo supervisado según guía v0.2.0.
No se reinició Control Center/hardware ni se envió StartMotion, HOME o rearme.

2026-09-16 11:56 UTC — Tras reinicio completo comunicado por operador,
comprobación sólo lectura `cruzr_boot_ready.sh --check` rc0: Motion3/3,
cámaras2/2 en seis topics con marcas crecientes y RELEASE_TECHNICAL_CHECK=passed.
Preflight del instalador confirma principal1, servo0, cargador0, MetaMove esperado
y HOME body-first-v4-20s exacto. Se indica liberación supervisada manteniendo
brazos abajo/vacíos y zona libre. Puede ejecutar HOME interno; liberación,
fin de arranque y ensayo de trayectoria aún pendientes. Cero movimientos del
agente. Evidencia: ../Humanoide-vla-evidence/20260916T115604.369673Z_INTERNAL-HOME-CHANGE/.
