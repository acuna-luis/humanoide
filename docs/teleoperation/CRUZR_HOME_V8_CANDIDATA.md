# HOME v8 candidata: apertura inicial repartida

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

22-09-2026, Europe/Madrid. HOME-V8-CANDIDATE-01.
**INSTALADA, CARGADA Y PROBADA FÍSICAMENTE desde la postura del incidente.**
Prueba única del 22-09 a las 14:12 CEST: SUCCEED/status4 y HOME20D medido.
Operador confirma recorrido normal y estable. HOME automático sigue siendo v7;
no se ha validado esta candidata desde todas las posturas ni durante arranque.

## Diseño y diferencia respecto a la propuesta inicial

MetaMove permite objetivos relativos constantes; no se ha validado una condición
nativa de lectura articular dentro del XML. No se implementó la corrección
condicional inicialmente propuesta. Se preparó una variante de ensayo acotada:
en cada brazo, primera etapa1s delta[0;−0,05;0;−0,03;0;0;0], segunda1,8s
delta[0;−0,15;0;0;0;0;0]. Apertura total−0,20rad y flexión codo−0,03rad,
idénticos a v7 después de ambas etapas. Se conservan cuerpo3,75s en paralelo,
bajada7s y cierre2,7s. Total nominal max(3,75;1+1,8)+7+2,7=13,45s.
No garantiza igual duración real: arranque de nodos/controladores y rechazo
inicial de consignas influyen. No es una recuperación general desde fuera
de límites ni desde postura desconocida, contacto o carga.

## Comprobación previa

Lectura nueva canónica whole_joint_states y actuadores:20ejes, sin errores
reportados, velocidad máxima0. Hombro izquierdo canónico0,116870161rad;
primer destino0,066870161rad, menor que límite superior0,0987266. No se alteran
límites ni se falsifica la pose; los primeros comandos interpolados pueden
seguir fuera del intervalo y ser rechazados hasta entrar. La prueba posterior completó esta transición desde la postura medida;
no demuestra seguimiento válido desde cualquier postura.

Barridos de geometría archivada desde esta postura,501muestras por segmento,
en dos órdenes seriales extremos cuerpo→brazos y brazos→cuerpo: mínima cota
condicional24,907mm. Conservan pares locales reportados por el auditor original.
**Límite:** esos dos órdenes no acotan matemáticamente toda sincronización
concurrente; no incluyen obstáculos externos, frenado, seguimiento ni validación
actual de montaje físico. No certifican seguridad de ejecución. Barrido inicial
101muestras insuficiente por cota de muestreo conservado en evidencia.
Tres pruebas offline: estructura/tiempo, destino del hombro del incidente y
conservación de destinos finales desde HOME/referenciaPICO; ensayo físico descrito abajo.

## Archivos, instalación y verificación

- XML: scripts/teleoperation/tasks/cruzr_home_v8_early_roll_CANDIDATE.xml.
- Auditor: scripts/teleoperation/review_home_v8_early_roll.py.
- Gestor: scripts/teleoperation/stage_home_v8_candidate.py.
- Tests: scripts/teleoperation/test_home_v8_candidate.py.

Destino Motion, contenedor walker-motion.manipulation_robot_app-1:
`/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config/cruzr/home_v8_early_roll_CANDIDATE.xml`.
SHA256 `d9e9462792b41300d352604b53ea2a4890a9382e942321990708f6ded2e26ccb`.
Respaldo remoto `/etc/walker/trajectory-overlays/20260922T120727.629089Z_home_v8_candidate` conserva home.v7.before.xml y receipt.json.
Copia externa antes de escritura y evidencia completa: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260922T120451Z_HOME_V8_CANDIDATE`.
Destino previamente ausente; escritura sin sobrescribir con enlace atómico y
verificación de contenido. BaseHOMEv7 SHA1e6e2fb7…a6f03 y MetaMove
SHAbfeab1c7…ccc69 exigidos. Durante la instalación: cero reinicios, acciones y cambios de modos.
No se modificó task_list; la prueba posterior verificó carga y ejecución por nombre.
No llamar originalhome ni reiniciar CC para activar esta candidata.

Receta de instalación aditiva (sin ejecución):

```bash
python3 scripts/teleoperation/stage_home_v8_candidate.py \
  --install-candidate --evidence /RUTA/PRIVADA/NUEVA
```

Antes de volver a instalar o actualizar: revisar compatibilidad, hashes y
nombres de contenedor; el gestor rechaza cambios en HOME/MetaMove o un destino
con contenido distinto. Reversión: con ninguna acción de esa candidata activa,
retirar exclusivamente el XML candidato si conserva el hash indicado. No
restaurar home.xml: no se cambió. Conservar los respaldos/evidencia.

## Prueba física — 22-09-2026, 14:12 CEST

Autorización explícita de instalación/prueba y confirmación presencial: abrazaderas
instaladas y vacías, sin apoyos externos, zona libre, ruedas bloqueadas, cargador
desconectado, paros liberados, control exclusivo y persona junto al paro.
Preflight `./scripts/cruzr_blue_workbin_cycle.sh --check` correcto: 20 ejes sanos,
velocidad cero, baterías 36,8/39,5 %, paros 0/0. Hashes de candidata, HOME v7 y
MetaMove contrastados. Cero escritores SDK y bloqueo de módulo vacío.
Muestra canónica fresca a menos de 0,000096 rad de la postura auditada.

Se ejecutó una sola vez `cruzr/home_v8_early_roll_CANDIDATE`, goal
`a74c21fa-0942-4912-87c4-446cf32fe36c`, sin reintento ni otra trayectoria.
Resultado SUCCEED/1101001/status4; once MetaMove SUCCESS.
Inicio del árbol 12:12:18.207591 UTC; último MetaMove 12:12:33.266610 UTC:
**15,059019 s observados**, frente a 13,45 s nominales. Cliente/SSH: 16,910484 s.
Comparable al ensayo v7 archivado (~15,06 s), no garantía temporal general.

**Limitación observada:** 202 rechazos ValidateCmdWithLimit iniciales en el
hombro izquierdo, de 12:12:19.062970 a 12:12:19.465026 UTC (0,402056 s).
La interpolación parte fuera del intervalo; después entra y completa.
No se ampliaron límites ni se omitió su comprobación.

Lectura posterior independiente `/mc/actuator_state`, tipo explícito y QoS
best_effort/volatile: 20 ejes, 14 de brazos; MEASURED_HOME=1, posición absoluta
máxima 0,002876 rad (brazos 0,000959), velocidad cero, delta consigna 0,002876.
Operador confirma «Sí, recorrido normal y estable» al preguntar por ausencia de
contacto, tirones y ruidos, brazos abajo y abrazaderas vacías.

La captura pasiva conserva 2097 muestras de actuadores y 9 de cada paro, pero
el colector devuelve código 3/usable_capture=false por una línea INFO previa
al JSON. No se presenta como captura íntegramente validada; los originales
quedan intactos. La primera consulta de postura falló por posición de una
variable de entorno tras timeout (127); se corrigió antes del movimiento y
se conserva tanto el fallo como la lectura válida.

Evidencia externa y copia documental antes/después:
`/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260922T121134Z_HOME_V8_TRIAL`.
Incluye dispatch.json, goal-result.txt, motion-log.json, post-actuators.json,
post-home.txt, trace/, trial-summary.json y SHA256SUMS.

### Receta del ensayo realizado

Tras las comprobaciones anteriores y confirmación física específica, dentro
del contenedor Motion descubierto (con setup cargado), se usó una única llamada:

```bash
source /opt/walker/setup.bash
export ROS2CLI_DISABLE_DAEMON=1
timeout 40 rosa action send_goal /mc/manipulation/action mc_task_msgs/action/ArmTask \
  '{"task_name":"cruzr/home_v8_early_roll_CANDIDATE","yaml_args":"{}"}'
```

Es documentación del ensayo, no una orden para repetir desde otra postura.
El timeout del cliente no demuestra parada física. La captura usa
`scripts/teleoperation/capture_home_motion_trace.py`; clasificación posterior
con `scripts/lib/cruzr_home_posture_gate.py` sobre la muestra de actuadores.

## Estado y punto de reanudación

Robot medido en HOME y operador confirma estable. No se envió otra trayectoria,
reinicio ni rearme. La salida de Fault de Control Center NO quedó verificada:
HOME articular y estado de Control Center son comprobaciones independientes.
La candidata sigue separada; `cruzr/home` conserva v7 y su hash original.
Integración automática y validación de otras posturas/arranque PENDIENTES.
La reversión del XML descrita arriba no revierte una postura física; no es
necesaria otra orden de movimiento para cerrar este ensayo.

## HOME-V8-AUTO-01 — receta de promoción (instalación completada arriba)

Fuente reproducible: `scripts/teleoperation/install_home_v8_auto.py`.
La promoción conserva exactamente el XML probado, incluido su nombre interno;
el destino `cruzr/home.xml` determina la tarea automática. Dependencias:
instalador v7 existente, auditor v8, clasificador HOME, SSH/Docker/ROSA/ROS2.
No envía acciones, no libera paros ni reinicia procesos.

```bash
python3 scripts/teleoperation/install_home_v8_auto.py --check
python3 scripts/teleoperation/install_home_v8_auto.py --measure-home --evidence /RUTA/NUEVA/measure
# Sólo después de confirmar paro principal pulsado, conservando HOME:
python3 scripts/teleoperation/install_home_v8_auto.py --preflight --evidence /RUTA/NUEVA/preflight
python3 scripts/teleoperation/install_home_v8_auto.py --install --evidence /RUTA/NUEVA/install
```

La medición se obtuvo antes de pedir el paro: HOME20D, inmóvil, máximo 0,002876 rad.
Instalación remota PENDIENTE; el siguiente paso depende de esa confirmación y
lectura del paro. Fuentes y respaldo PC previo en
`../Humanoide-vla-evidence/20260922T121856Z_HOME_V8_AUTO`.
El ciclo base reconoce el hash exacto v8 y mantiene la comprobación de MetaMove.
No se habilita un hash desconocido ni se cambia la trayectoria de recogida.
Reversión PC: restauración selectiva del preflight desde before/; retirada del
nuevo instalador. Reversión remota, si se instala: bajo paro y sin acciones,
restaurar el home.xml v7 respaldado con comparación previa del hash v8;
verificar hash v7 tras escritura. No restaurar si alguien modificó el destino.
Carga automática y ensayo durante encendido pendientes; no inferirlos del
ensayo de la tarea separada ni reiniciar para comprobarlos sin preparación.
