# Paso de brazo derecho para SmolVLA mediante MetaMove — 10-11-2026

## Lectura de guardia con escritura bloqueada — 10-11-2026

**PREPARADO Y PROBADO LOCALMENTE; NO PROBADO EN MOTION.** La lectura del
canal de la guardia se separó de la renovación durable del lease: el lector
puede recibir alertas y ACK de solicitud de cancelación aunque el fsync de una
renovación esté bloqueado. Una cola llena invalida la admisión y mantiene el
canal prioritario; una renovación tardía no debe rearmar el latido ni publicar
una muestra vencida. La auditoría independiente no halló otro defecto
inequívoco después de corregir las carreras detectadas. Pasan 38 tests del
puente, 14 del check pasivo y 29 del coordinador, todos locales.

Una renovación positiva ya iniciada puede persistir hasta su vencimiento
original, como máximo 0,5 s, y la revocación en disco puede quedar pendiente.
El ACK recibido solo acredita la solicitud; ni la cancelación física, ni el
frenado, ni la entrega tardía de una orden en tránsito quedan demostrados. No
hay evidencia de que fsync causara el incidente 731084. Los bindings anteriores
deben regenerarse por cambio de fuentes. El usuario indicó que avisará tras
cargar y desconectar; no consta si comenzó la carga. No hubo acción física
SmolVLA. [Fuentes, backup y límites](../SYSTEM_CUSTOMIZATIONS.md#arm-pico-fsync-transport-20261110).

## Cancelación sintética interrumpida por batería — 10-11-2026

**PREFLIGHT RECHAZADO, CERO GOALS Y MOVIMIENTO.** Tras comunicar el usuario que
desconectó el cargador, una consulta puntual del topic de carga mostró `0` y
ambas baterías informaron descarga a 26,2 % y 28,4 %. La referencia articular
reciente indicó velocidades publicadas cero y los hashes URDF/SPS coincidieron
con los leídos en Motion. El check aislado terminó antes del UUID y de cualquier
goal con `battery_invalid_or_below_30_percent`: el supervisor exige al menos
30 % en cada batería. No se probó la cancelación ni se modificó el umbral.

El postcheck observó sin procesos sintéticos y hashes originales del marker y
XML intactos; también observó un daemon ros2-cli, cuya procedencia no se
identificó. La lectura es puntual y no prueba exclusividad futura o frenado.
El usuario debe cargar ambas baterías por encima del umbral y desconectar antes
de reanudar; no cambiar protecciones ni inferir estado actual de estos registros.
[Detalle, respaldos y evidencia](../SYSTEM_CUSTOMIZATIONS.md#smolvla-synthetic-cancel-battery-20261110).

## Cancelación sintética y estado del cargador — 10-11-2026

**DOS CHECKS INTERRUMPIDOS ANTES DEL GOAL; NINGÚN MOVIMIENTO.** Se preparó un
servidor de acción ArmTask ficticio bajo un namespace aleatorio ajeno a
`/mc/manipulation/action`, y una copia efímera de la guardia con las cuatro
referencias de acción remapeadas a ese servidor. La prueba utiliza telemetría
real y no ejecuta la tarea real ni verifica frenado. El código no cambia la
guardia productiva, los límites ni el marker de 731084.

En el primer intento, la guardia informó `preflight_failed`; el lector resumió
ese evento sin conservar su motivo. Se añadió al harness diagnóstico un lector
que conserva el campo sin modificar la línea y se hizo una única repetición. La
segunda confirmó `charger_connected_or_unknown`: la condición del monitor
requiere `/emb/chrg_input_status == 0` y una consulta posterior independiente
observó `data: 2`. Se desconoce qué significa 2 según el proveedor; no afirmar
que el cargador esté conectado solo por esa lectura. No hubo goal sintético,
goal físico ni cancelación; se interrumpió antes del handoff de UUID.
Otra lectura puntual, sin salida archivada, mostró `charge_status: charging`
en ambas baterías, aproximadamente 24,1 % y 26,3 %, con corrientes −7,9 A y
−7,5 A; esto no determina por sí solo el significado del 2 ni el estado físico
del cable.
Una lectura puntual independiente sin archivo del servicio distinto
`/emb/get_chrg_status` devolvió `success=true`, `volt=0`, `current=0`,
`charge_status=0` y `conn_status=2`; su semántica y equivalencia con el topic
no están demostradas y los campos deben contrastarse con los de baterías.

Comprobaciones posteriores observaron solo procesos habituales en Motion y
Vision, ningún contenedor propio en Ada, y los SHA previos de marker/XML
intactos. Son lecturas puntuales. La prueba del watchdog sigue pendiente; no
modificar, saltar o falsificar la comprobación de cargador. Evidencias, fuentes,
backups y reproducción en la [ficha](../SYSTEM_CUSTOMIZATIONS.md#smolvla-synthetic-cancel-20261110).

## Modelo y guardia reales sin meta — 10-11-2026

**OBSERVADO EN MOTION Y ADA; SIN UUID EN GUARDIA, META, STAGING,
CANCELACIÓN O MOVIMIENTO.** `--check --guard-heartbeat --model-diagnostic`
arrancó la guardia real y el worker de lectura de huellas; solo después inició
una inferencia real de SmolVLA mientras el PC respondía a los latidos. La
propuesta se contrastó con el estado y tarea de muñeca, se conservó una decisión
y llegó un permiso por el canal PC→Motion. El token UUID sintético fue solo
correlación en ese canal; nunca se entregó a la guardia o a un servidor ROS.
PASS con 195 latidos, 0 goals, 0 handoffs UUID y 0 solicitudes de cancelación.
La muñeca propuesta fue +0,18760588965888958 rad; el candidato acotado era
+0,01 rad sobre la referencia, y NO se envió. Latencia PC 0,736325 s, sin medir
Vision→PC; la muestra ha caducado y no habilita control. El modelo también
propuso cambios grandes en otros ejes, que esta prueba no transmite.

El check no comparte el lock de ensayo ni incluye el coordinador/worker de
envío físico: no valida exclusividad distribuida, el envío real, la cancelación,
el watchdog con UUID/goal, frenado, trayectoria, dedos ni la tarea de pelota.
La excepción 731084 no se ejecutó; marker y XML permanecen; la causa del fallo
anterior sigue desconocida y `model_wrist_dispatch_not_enabled` sigue activo.
Lectura independiente de procesos posteriores y trazas, SHA, respaldo y
reproducción en [la ficha](../SYSTEM_CUSTOMIZATIONS.md#smolvla-live-guard-permit-20261110).

## Integración de modelo y admisión 731084 — 10-11-2026

**PREPARADO EN PC; INTEGRACIÓN SOLO SIMULADA; GATE FÍSICO CERRADO.** El PC
puede asociar un flujo completo de una predicción al objetivo fijo de muñeca,
comprobando 20 ejes, dirección, amplitud, hashes declarados y presupuesto de
edad en el reloj del PC. Un permiso se vincula a UUID y tarea; no establece
antigüedad desde Vision, autenticidad del modelo, trayectoria o parada. El
worker/coordinador consumieron este protocolo solo con transporte y actuador
falsos. La predicción no acciona la mano ni demuestra la tarea de pelota.

La admisión reservada para 731084 conserva el marker de aquel intento y crea
un nuevo intent bajo el mismo lock. Se comprueba el UUID histórico cancelado,
identidades y estado puntual; después de la consulta se exige una nueva muestra
estacionaria y permiso vigente antes de ACK. Es una **excepción específica** al
bloqueo anterior, no una recuperación completa: la causa sigue desconocida y
los demás launchers siguen bloqueados por el marker. La nueva tarea usa staging
`O_EXCL` con XML distinto; el XML de 731084 no se borra ni reutiliza.

Se preparó revocación asíncrona y reintento de cancelación sobre estado activo
del UUID propio. Su comportamiento físico, el envío en vuelo y el frenado no
están verificados. La ruta `--model-live --incident-731084` termina todavía en
`model_wrist_dispatch_not_enabled` antes de conexión. Los tests y la revisión
no sustituyen habilitación ni condiciones actuales del operador.
[Versiones, pruebas, backups y pendientes](../SYSTEM_CUSTOMIZATIONS.md#smolvla-scoped-731084-20261110).

## Recuperación preparada de 731084 — 10-11-2026

**CHECK EN MOTION PASÓ SIN CAMBIOS; ARCHIVADO NO EJECUTADO.** Se preparó una herramienta para
la sesión 731084 que valida el UUID exacto y la evidencia histórica de status
5, junto con marker, journal, lease y XML de esa sesión. La evidencia de
cancelación está fijada por SHA; una lista actual vacía no se trata como
cancelación. La variante antigua, ligada a la sesión previa sin UUID, no sirve
para este caso. Pasan doce pruebas locales y revisión independiente sin hallazgo
concreto. La lectura histórica y los tests no certifican parada física.

El archivador futuro mantiene el bloqueo duradero `RECOVERY-...-intent.json`
que rechazan los lanzadores cooperantes, incluso si completa el archivado. No
habilita por sí solo movimiento ni SmolVLA. Un primer check en Motion fue rechazado por un proceso Python. Otro check pasó
tras verificar el socket y grafo del daemon ROS, observando solo publishers
estándar y sin clientes de acción o servicio; esta observación no autentica el
proceso ni acredita exclusividad. Se verificó el XML exacto, sin archivarlo;
el temporal del transporte se eliminó. `--archive` conserva el rechazo de todo
Python y no se ha ejecutado. Una consulta puntual posterior observó marker y XML
intactos, UUID estado 5, velocidades cero, sin errores de 20 actuadores y sin
procesos adicionales en los dos contenedores; no se guardó esa salida y no
acredita exclusividad ni parada física. No hubo nuevas órdenes de movimiento.

La causa de pérdida de guardia sigue sin identificar y permanecen pendientes
la cancelación coordinada con un envío en vuelo y el despacho de SmolVLA.
[Fuentes, hashes y límites](../SYSTEM_CUSTOMIZATIONS.md#arm-pico-731084-archive-prep-20261110).

## Latido de guardia sin goal — 10-11-2026

**OBSERVADO EN MOTION; SIN UUID, GOAL, CANCELACIÓN NI MOVIMIENTO.** Con
referencia articular leída y binding de revisión limitado, el check opcional
`--guard-heartbeat` terminó con `PASS_PC_HOST_GUARD_HEARTBEAT_NO_GOAL`: envió
30 pulsos en 3 s y exigió ACK de parada, fin de la guardia y revocación del
lease. Después no se observaron procesos Python en los dos contenedores; el
marker de 731084 y su XML conservaban identidad. El inventario y la muestra
son puntuales, no garantizan exclusividad o estado físico futuro.

No existe ACK por pulso y, sin un UUID entregado, el watchdog no exige
caducidad de ese latido. No se comprobó cancelación, frenado ni trayectoria;
la causa de 731084 sigue sin identificar y la política SmolVLA no se ejecutó.
El check no toma el lock del ensayo ni retira el marker, que sigue bloqueando
la vía de movimiento. Evidencia, SHA256 y reproducción en la
[ficha](../SYSTEM_CUSTOMIZATIONS.md#arm-pico-guard-passive-20261110).

## Predicción única y supervisión — 10-11-2026

**VERIFICADO EN SIMULACIÓN; DESPACHO FÍSICO DE SMOLVLA BLOQUEADO.**
`run_ball_live_shadow.py --one-shot --max-samples 1` entrega como máximo una
observación al modelo, cierra su entrada y drena la captura hasta su fin normal;
el resumen sólo aparece si los procesos y las cuentas terminan correctamente.
`prepare_ball_native_arm_step.py --stream --wrist-candidate --wrist-output`
exige una predicción completa y un resumen coherente antes de publicar el
directorio nuevo o mostrar el candidato. La adaptación conserva los otros seis
ejes del brazo en la medición, limita `R_wrist_roll_joint` a +0,01 rad durante
4 s y rechaza propuestas negativas o inferiores a +0,01 rad. No interpreta
ni acciona la mano; registra la salida original y la aplicada. Esto no es la
política íntegra ni la tarea de coger, elevar y soltar la pelota.

El directorio contiene manifiesto, XML, URDF, transmisiones, decisión y receipt.
Sus hashes y aritmética se pueden verificar con un SHA256 externo del receipt;
el hash de imagen no conserva sus píxeles. Esta consistencia no autentica al
productor ni demuestra frescura actual, sincronización con Vision o seguridad
de trayectoria. El binding opcional conserva la evidencia exacta y rechaza
`--run` cuando está presente. **Un binding antiguo sin evidencia de modelo no
identifica la procedencia de su candidato** y no debe usarse para eludir ese
bloqueo. La verificación del artefacto usa código local que el propio binding
no acredita; tampoco acredita firmware ni runtime externos.

El coordinador cuenta feedback y lo resume, evitando un `fsync` por mensaje,
sin eliminar la comprobación por mensaje de guardia, lease y UUID. El check
pasivo opcional `--guard-heartbeat` exige el binding revisado, usa clientes de
descubrimiento y supervisa latido y cierre de la guardia sin crear goal ni
solicitar cancelación. No demuestra que cada pulso se recibiera, el vencimiento
del watchdog, una cancelación real ni la trayectoria. El resumen de feedback se
ha probado en simulación; el check de latido pasó después en Motion sin goal.

La causa de `guard_lost_during_trial` en 731084 permanece **PENDIENTE**;
no se ha demostrado que el volumen del feedback ni un `fsync` fueran su causa.
El XML y marker de esa sesión siguen retenidos; no repetir, enviar HOME o
limpiarlos automáticamente. Una nueva consulta de sólo lectura observó el UUID
con status 5 y marker retenido; la muestra articular no publicó velocidades.
No hubo movimiento nuevo. Los cambios de control siguen sin prueba física;
el check de latido tiene el alcance indicado arriba. Para evidencia, hashes, backup y deuda:
[ficha](../SYSTEM_CUSTOMIZATIONS.md#smolvla-wrist-oneshot-20261110).

## Diagnóstico de pérdida de guardia — 10-11-2026

**VERIFICADO EN TESTS LOCALES, no probado en Motion.** Tras el intento 731084,
`GuardPipe` conserva en memoria un registro acotado de eventos de guardia y el
primer `OPERATOR_ALERT`, sin incorporar E/S en el lector. Si llega EOF después
de una alerta, se conserva el primer fallo. El coordinador captura de forma
acotada ese motivo, eventos recientes, última muestra validada y estado de
progreso/latido. Una vez intentada la cancelación, emite un resumen pequeño al
operador antes de fsync del journal. La captura usa fallback si algún dato es
inválido; no garantiza que todos los eventos o la razón existan o lleguen.

Se ejecutaron 76 tests locales: lease/puente 30, coordinador 20, lanzador host
4, arranque de streams 15 y comprobación pasiva 7. Auditoría independiente sin
defecto nuevo inequívoco. No hubo una nueva consulta o movimiento del robot ni
un `--check` real de estas fuentes; el efecto del diagnóstico durante un fallo
real sigue PENDIENTE. stderr nativo de guardia continúa en `DEVNULL`; los datos
de 731084 ya descartados no se recuperan y su causa sigue sin identificar.

**Limitación abierta:** la secuencia anterior revoca el lease mediante
`lease.fail()` antes de solicitar cancelación; esa operación incluye `fsync`
síncrono. Si el disco se bloquea, la solicitud podría demorarse. No hay
evidencia de que ese bloqueo ocurriera en 731084; el cambio de diagnóstico no
altera ni prueba la secuencia de control. Una cancelación, respuesta o muestra
de reposo no certifica distancia de frenado. El XML y marker de 731084 siguen
retenidos; no repetir, enviar HOME ni limpiarlos automáticamente. No se ha
habilitado SmolVLA físico.

Fuentes versionadas, hashes exactos, backup selectivo y límites adicionales:
[ficha](../SYSTEM_CUSTOMIZATIONS.md#arm-pico-guard-diagnostics-20261110).

## Intento supervisado interrumpido 731084 — 10-11-2026

**OBSERVADO: acción aceptada y luego estado cancelado; éxito de tarea y causa
del fallo no demostrados.** Tras confirmación actual del operador se ejecutó
una sola tarea nativa de muñeca derecha, sin retorno automático. La sesión
`731084b3e4f94527a37de07297724bf1` preparó el XML SHA256
`d4c704e6ab369d250658a596cd6a5704258accf130971d3046748a8d132b616b`
en Motion (receipt dev 45/inode 3584597). El goal
`2e20ea8d-34d9-4e4d-9192-e5e0c11e921d` se envió y fue aceptado; el último
feedback conservado decía RUNNING a 3,29 s. El coordinador falló con
`guard_lost_during_trial` y el journal registró
`independent_cancel_unconfirmed` / `guard_cancel_request_timeout`.
Una lectura posterior del estado ROS para ese mismo UUID mostró status 5,
cancelado. El log de Motion registra para el mismo UUID `HandleGoal` a
20:17:59,622915, inicio del XML a 20:17:59,632869, `HandleCancel` a
20:18:03,138975 y árbol cancelado a 20:18:03,537316, según el reloj de Motion
no sincronizado. Acredita recepción de una solicitud de cancelación; no
establece quién la solicitó, por qué ni la distancia de frenado. El mismo log
registra en `component_group.cpp:483` los siete objetivos exactos del
manifiesto y duración de 4 s; el controlador de manipulación ya estaba
running. Tras `HandleCancel` se registró `MetaMove TickEnd`. Esto demuestra la
interpretación de esa consigna en el log, no éxito ni seguimiento exacto de
los siete ejes físicos.

La muestra articular posterior situó `R_wrist_roll_joint` en
`0,011121360712170899` rad: `+0,009875001` rad respecto a la referencia.
`R_elbow_roll_joint` cambió `+0,002205097` rad, por encima del umbral de
deriva observacional `LOCKED_DRIFT_RAD=0,002`; la muestra por sí sola no
identifica la causa de la interrupción o evolución entre muestras. Todas las
velocidades publicadas eran cero en esa muestra. La consulta ROS2 posterior
de actuadores pasó `check_actuators`: 20 actuadores corporales habilitados y
sin error. La primera consulta nativa de actuadores había agotado tiempo. El
operador confirmó robot inmóvil y sin contacto ni movimientos inesperados.
La lectura de procesos posterior no mostraba Python en los contenedores app y
ROS; no certifica exclusividad posterior o parada general.

La razón precisa del fallo permanece **PENDIENTE**: el error visible era
genérico y stderr de guardia se descartó. No atribuir la cancelación al codo o
a una protección concreta sin evidencia. Las lecturas adicionales de logs de
hardware/ROS no revelaron la causa y no permiten inferir qué ocurrió dentro de
la guardia cuyo stderr se descartó. La tarea XML y el marker
`/var/tmp/cruzr-pico-v4-wrist-control/PENDING_OR_UNRESOLVED.json` permanecen;
el journal y stderr del worker también se conservan. El lease
`/tmp/pico-wrist-live-xdhdhgsd/arm-lease-731084b3e4f94527a37de07297724bf1.json`
tenía `deadline=0.0`. No repetir, enviar HOME
ni borrar archivos automáticamente. El procedimiento usado para la sesión
anterior `ccfbd5...`, interrumpida antes de UUID, no es válido para esta
acción aceptada. Cualquier retorno físico exige otra acción revisada.

Evidencia privada en
`../Humanoide-vla-evidence/PICO_NATIVE_WRIST_TRIAL/run-731084b3e4f94527a37de07297724bf1/`:
`host-stdout.log`, `host-stderr.log`, `post-attempt-readonly.json`,
`remote-state-readonly.json`, `actuators-readonly.json`,
`motion-log-tail-readonly.json`, `retained-state-readonly.json` y
`lease-readonly.json`; hashes y respaldo
documental en [la ficha](../SYSTEM_CUSTOMIZATIONS.md#arm-pico-attempt-731084-20261110).
Esto no ejecutó el modelo ni valida la tarea de la pelota y la mano v4.

## Reanudación de muñeca preparada — 10-11-2026

**PREPARADA, NO EJECUTADA.** Después del archivado del intento interrumpido se
tomó una muestra nueva en `../Humanoide-vla-evidence/PICO_WRIST_RESUME_20261110T121336Z/`,
se regeneró un candidato de muñeca y se vinculó a fuentes actuales. El XML
resultante conserva SHA256 `d4c704e6ab369d250658a596cd6a5704258accf130971d3046748a8d132b616b`;
binding `binding/review-binding.json` SHA256
`935a6116fa34f3deb71b7ee827bb11028a8af07fc50e12163decdb1e1db78f5d`.
El loader aislado y comparación de fuentes/candidato pasaron; el check pasivo
`check-70f3e2e6e874483ab644a8a3839c985e` terminó sin goal.

La muestra tenía velocidades publicadas cero, muñeca derecha
`0,0012463593901570836`, cabeza `−0,43066510619889375` y codos L/R
`2,879377812660591`/`−2,8787066960658914` rad. Los codos siguen cerca de sus
límites SPS ±`2,88` rad y el margen diagnóstico `0,002` rad no se satisface.
La captura no prueba la escena actual, interpolación o parada. Antes de una
prueba hace falta comprobar condiciones físicas vigentes, exclusividad y
guardia; la tarea de muñeca no es una acción del modelo SmolVLA.
Hashes, backups y continuidad: [ficha](../SYSTEM_CUSTOMIZATIONS.md#arm-pico-resume-prep-20261110).

## Archivado selectivo realizado — 10-11-2026

La utilidad de recuperación de la sesión interrumpida devolvió rc 0 y
`ARCHIVED_ONE_FAILED_STAGE`, sin órdenes de movimiento ni HOME. Registró un
receipt `complete` SHA256
`9118761347f02db516c555039c6c5fcc700f87a5ccbdcdfcd72c1039dab2c8cf`.
El marker se conserva como
`/var/tmp/cruzr-pico-v4-wrist-control/ARCHIVED-PENDING-ccfbd5afa50744649c4d9982601013ae.json`,
junto al intent archivado y los receipts; no aparecen los nombres activos de
marker e intent en la lectura posterior.

Una lectura independiente comprobó que el XML original ya no está en su nombre
de tarea y que se conserva como
`/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config/diagnostics/.pico_v4_wrist_d4c704e6ab369d25.xml.archived-ccfbd5afa50744649c4d9982601013ae`,
con dev 45/inode 3584590, UID 0/modo 0600 y SHA256
`d4c704e6ab369d250658a596cd6a5704258accf130971d3046748a8d132b616b`.
No se declara limpieza del lease o de otros directorios. Las observaciones de
acciones y procesos son puntuales y no prueban exclusividad ni parada física.

Evidencia privada en
`../Humanoide-vla-evidence/PICO_NATIVE_WRIST_TRIAL/run-ccfbd5afa50744649c4d9982601013ae/`:
`archive-run.stdout` SHA256 `118081dc483c89ce917862efcd673b5e7c3149ee6c1f1cc955add2446759b0a0`
y `archive-after-readonly.json` `f177c3842faccbd28bb79a3b77a114673ecfa561e1cb1eb06b019f6d31890fdd`.
El backup documental previo, continuidad y reversión selectiva pendiente están
en la [ficha](../SYSTEM_CUSTOMIZATIONS.md#arm-pico-archive-ccfbd5-20261110).
No repetir la operación ni borrar receipts automáticamente. La utilidad no
implementa `--restore`; antes de una reversión habría que preparar un
procedimiento reproducible que restituya primero el marker bajo lock y luego,
sin sobrescritura y comprobando inode y hash, el nombre original del XML.
El archivado no habilita SmolVLA ni demuestra la tarea de la pelota.

## Recuperación selectiva preparada — 10-11-2026

**ESTADO HISTÓRICO PREVIO AL ARCHIVADO.** La utilidad versionada
`scripts/vla/runtime/archive_failed_pico_wrist_stage.py` está limitada a la
sesión `ccfbd5afa50744649c4d9982601013ae` y al XML, inode y SHA del receipt.
No llama servicios ROS de movimiento. Su `--check` bloquea temporalmente el
lock existente, valida marker, journal sin UUID, lease vencido, XML y la
actividad observada. El check final devolvió `CHECKED_NO_CHANGES` y estado de
acción `[4]`, sin Python observado en los dos contenedores. Es una captura
puntual, no demuestra exclusividad externa ni parada física.

La operación `--archive`, entonces preparada y después realizada según la
sección anterior, escribe un intent
durable, crea un hardlink privado del XML exacto en su FS y retira su nombre
original, registra el receipt, vuelve a revisar actividad/journal/marker/lease
y archiva el marker en el FS host. Después escribe receipt complete durable y
archiva el intent. El coordinador actualizado rechaza tanto en adquisición como
con lock retenido cualquier intent de recuperación incompleto. Si hay caída
entre FS, marker o intent deben mantener bloqueado el lanzador actualizado;
el nombre original del marker puede faltar y deberá revisarse manualmente.
Ni esta operación ni su receipt prueban que un servo esté parado.

Reproducción desde el PC con acceso autorizado a Motion. Comprobar primero el
SHA256 de la fuente y repetir `--check`; ninguna de esas órdenes mueve el robot:

```bash
sha256sum scripts/vla/runtime/archive_failed_pico_wrist_stage.py
ssh -T -o StrictHostKeyChecking=yes walker@192.168.11.2 \
  'python3 -B - --check' < scripts/vla/runtime/archive_failed_pico_wrist_stage.py
```

SHA esperado: `90504a9ddd2d29a8e48ddd83eba862fea05a3a51a9e543e35c094d70a113b0a1`.
Para el archivado efectivo, sólo tras revisar la evidencia, los checks y la
ausencia de otros controles, la misma llamada usa `--archive` en lugar de
`--check`. Guardar su receipt y registrar el estado antes de volver a probar.
Si la conexión o cualquier fase falla, no reintentar ni borrar archivos de
forma automática; inspeccionar ambos FS, el marker y el intent durable.

Pasan 12 tests locales de archiver y 17 del coordinador. La evidencia del
check final, hashes, backup y límites están en la
[ficha](../SYSTEM_CUSTOMIZATIONS.md#arm-pico-archive-prep-20261110).

## Aislamiento del canal JSON del worker — 10-11-2026

Tras el `JSONDecodeError` de la sesión interrumpida, el bundle del worker
conserva un descriptor duplicado exclusivamente para `WorkerChannel` y
redirige el descriptor 1 a stderr antes de importar o iniciar ROSA. Así, las
escrituras de bibliotecas nativas al stdout del proceso no se mezclan con los
eventos JSON enviados al coordinador. `BRIDGE_READY` se emite y vacía antes
de cambiar los descriptores; la salida nativa queda en el log de stderr.

Pasan 78 pruebas locales, incluidas escrituras simuladas directas al fd 1,
handshake UUID y cancelación simulada. Una prueba puntual en Motion, con
`rosa.init()` y cierre sin nodo ni goal, dejó el JSON de prueba sólo en stdout
y el log nativo en stderr; su evidencia `rosa-fd-isolation-readonly.json` tiene
SHA256 `1c38a1c6ec9be9923a3e5aab5be001ff51f3e1e943a7e899191f24bcc7f98acd`.
No ejercita el worker completo ni el despacho. La prueba separada de `rosa.init()`
mostró una línea de salida compatible con la hipótesis de contaminación, pero
no identifica el contenido de la línea que se perdió en el intento. Este fix
no se ha probado físicamente, no acredita frenado ni activa SmolVLA. Las
fuentes cambiaron: bindings anteriores no identifican esta versión y se debe
crear y comprobar uno nuevo antes de cualquier uso. El XML y marker del intento
anterior fueron archivados posteriormente; no hubo reintento ni movimiento. Fuentes, backup,
evidencia y recuperación pendiente: [ficha](../SYSTEM_CUSTOMIZATIONS.md#arm-pico-worker-json-fd-20261110).

## Intento interrumpido de muñeca — 10-11-2026

La sesión `ccfbd5afa50744649c4d9982601013ae` inició la ruta supervisada de
una tarea estática de muñeca derecha, **sin ejecutar la política SmolVLA**.
El worker creó el XML nativo y emitió receipt; a continuación el coordinador
falló con `JSONDecodeError` al interpretar su stdout. Los eventos retenidos
no incluyen solicitud de UUID, envío, aceptación ni resultado. La línea no
JSON fue descartada antes de escribirse en el journal, por lo que se desconoce
su contenido.

El worker revisado espera el ACK del coordinador tras la solicitud de UUID,
y la API ROSA fijada llama al servicio de goal después de esa espera. Por ello
los registros y ese protocolo **apoyan la inferencia** de que el fallo ocurrió
antes del envío; no son una observación directa del servicio ni acreditan el
estado físico en todo momento. El operador indicó no haber visto movimiento
ni anomalías. En una muestra posterior de articulaciones la muñeca derecha
era `0,0012463593901570836` rad, igual al inicio del candidato, y todas las
velocidades publicadas eran 0; el único goal de estado observado era anterior
y mostraba `status=4`. No atribuirlo a este intento.

El receipt y una lectura independiente identifican el XML staged
`/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config/diagnostics/pico_v4_wrist_d4c704e6ab369d25.xml`,
SHA256 `d4c704e6ab369d250658a596cd6a5704258accf130971d3046748a8d132b616b`,
dev 45/inode 3584590, modo 0600/UID 0. El directorio creado fue dev 45/inode
3584589. El host conserva `/var/tmp/cruzr-pico-v4-wrist-control/` con marker,
lock, journal y stderr, y `/tmp/pico-wrist-live-3k5e3w2k/` con intent y lease;
éste se leyó con `deadline=0.0`. La lectura puntual de procesos mostró app
con `rosa` y `robot_app` y ROS con `bash`, sin Python visible en esos dos
contenedores. El XML y marker se archivaron posteriormente como se registra
arriba; no se ha enviado HOME.

Un experimento temporal separado de `rosa.init()`/`rosa.shutdown()`, sin nodo
ni goal, mostró que la biblioteca imprime una línea nativa en stdout. Esa
línea sería incompatible con JSONL y ofrece una hipótesis plausible; **no
permite identificar la línea descartada**. Evidencia privada en
`../Humanoide-vla-evidence/PICO_NATIVE_WRIST_TRIAL/run-ccfbd5afa50744649c4d9982601013ae/`:
`host-stdout.log` SHA256 `a59e9ada3d6d9949972d9064e9163a273d105dc1222fcfe48c37ad757aba0c93`,
`host-stderr.log` `9514c5b74ac7da5fdc814bf9af8d9f61e3591ca0dabfd89e80519ab21e47771c`,
`remote-receipts-readonly.json` `4d01274ea56b72b363022e35fc49c87704269de0cba8d40e2446805a12b027cb`,
`post-attempt-readonly.json` `d56004c470b422a40f81a4befab11a5b473b78c591230a1713ba847ea03bfa75`,
`inventory-readonly.json` `c483d92ebb94ee8c7c17c613ec69d415017fe80a3e20a6aeb905e1bb935313be` y
`rosa-init-readonly.json` `bbb546e657a91184a85cf71dcf14bec4f05a20d3ae33b7026a135a66652afbb1`.
El registro remoto usa un reloj distinto: no usarlo para inferir edad de datos
en el PC sin sincronización. El backup documental y la deuda están en la
[ficha](../SYSTEM_CUSTOMIZATIONS.md#arm-pico-attempt-ccfbd5-20261110).

No reintentar, enviar HOME ni borrar automáticamente. Una reanudación requiere
revisar el protocolo, los procesos y el marker/lease/XML registrados; cualquier
limpieza debe ser selectiva y quedar documentada.

## Sesión acotada de muñeca — 10-11-2026

**PREPARADA LOCALMENTE; EJECUCIÓN FÍSICA PENDIENTE.** El cargador aislado
comprueba los bytes del proyecto y los datos retenidos antes de importar el
ejecutor. Los bootstraps de Motion comprueban fuente, payload y sesión antes
de ejecutar; guardia, coordinador y worker enlazan el UUID con el lease. El
cliente nativo comprueba el manifiesto y XML staged, acepta sólo el goal de
esa tarea y consume un único intento antes de enviar. Ante resultado incierto
no hay reintento ni HOME automático. Esta cadena asume procesos confiados y
no autentica frente a quien controle Python o SSH.

El `--run` del cargador puede enviar una única tarea de muñeca si se aporta
confirmación física actual y pasan los checks; no es una ejecución de
SmolVLA. El despacho directo `arm.main(dry_run=False)` permanece bloqueado.
Debe usarse un binding nuevo que corresponda exactamente a las fuentes y
candidato: la copia histórica no habilita estas fuentes.

Una captura reciente y su candidato están en
`../Humanoide-vla-evidence/PICO_WRIST_FRESH_20261110T120131Z/`. El XML fija
los siete ejes derechos desde esa captura y añade 0,01 rad a la muñeca. Los
codos L/R estaban en `2,879377812660591`/`−2,8787066960658914` rad ante
límites SPS ±`2,88` rad; extremos nominales dentro, pero no cumplen el margen
diagnóstico de `0,002` rad. La muestra y margen no garantizan trayectoria,
geometría de mano v4 ni parada. Antes de mover, verificar de nuevo el estado
del robot y el despeje real de mano, dedos, antebrazo, mesa, aro y cables, con
operador junto al paro y sin otro controlador activo.

Pasan 147 tests locales; el check `check-cb9bfa4427c5491fbcc983da3a631ec3`
pasó PC→Motion con cero goals y sin movimiento. El check no despacha ni prueba
cancelación o frenado; la prueba conjunta usa guardia/ROSA/staging simulados.
En lectura de inventario, UID efectivo de app y worker fue 0 y los tres hashes
de URDF/SPS/MetaMove coincidieron; baterías observadas 54,0/56,3 %. La
importación aislada y comparación con el binding del candidato pasaron.
Identidad de fuentes, hashes del candidato,
backup y punto de reanudación: [ficha](../SYSTEM_CUSTOMIZATIONS.md#arm-pico-scoped-session-20261110).

Para reproducir la importación aislada sin enviar órdenes:

```bash
python3 -I -B scripts/vla/verified_pico_wrist_pc_loader.py --check \
  --binding ../Humanoide-vla-evidence/PICO_WRIST_FRESH_20261110T120131Z/binding \
  --binding-sha256 02045c05a65cbf9681d0ec02480519dc6bdaa85eea8a3687f7c551489e79736e
```

El binding conserva el documento existente al crearlo, anterior a este
registro. Su hash acredita esa copia y las fuentes retenidas, no un revisor,
una condición física o la configuración efectiva en ejecución. El ensayo
requiere verificación actual y supervisión presencial; no ejecutar el `--run`
sin esas condiciones.

## Telemetría emparejada y cotejo nominal — 10-11-2026

**VERIFICADO LOCAL, SIN ÓRDENES.** El adaptador empareja las posiciones
articulares y la imagen como antes y añade las velocidades 20D disponibles y
el instante monotónico PC en que procesó el registro articular. Si faltan
velocidades conserva el shadow, pero no las sustituye por ceros. El relay
conserva esa muestra para asociarla a la predicción por `image_sha256` y
`image_source_ns`; rechaza sellos de imagen duplicados o no crecientes y
predicciones sin observación pendiente. Un productor antiguo sin los campos
nuevos continúa funcionando en shadow; metadata parcialmente presente falla.

El conversor existente `prepare_ball_native_arm_step.py --stream` conserva su
vista previa antigua si no recibe parámetros nominales. Con todos los
parámetros siguientes activa el cotejo opcional:

```text
--urdf RUTA --transmissions RUTA --max-state-age-ns ENTERO
--max-prediction-age-ns ENTERO --min-sps-margin-rad VALOR
```

También requiere `--max-step-rad` y `--duration-s` explícitos. En esta vía se
exigen velocidades y nombres 20D, orden de modelo igual al orden nominal de
brazo, postura PICO/head-down estacionaria, sellos de recepción y predicción
válidos en el mismo reloj PC y coherencia de los siete deltas con la muestra.
Se rechaza cualquier delta mayor que la cota aportada. Se revisan los siete
extremos de brazo con el URDF y los 20 extremos con las transmisiones SPS
aportadas; la duración elegida se usa para el promedio mínimo necesario, no
para certificar picos. El margen opcional es de diagnóstico definido por el
llamador, no se añade como límite del fabricante.

La salida conserva `physical_control_qualified=false` y
`physical_commands_sent=0`. El sello PC sólo indica cuándo el adaptador
procesó el registro; no mide cuánto tardó desde Vision ni calibra relojes.
No se verifica interpolación real, escena, geometría de mano, fuerza,
controlador, frenado ni el orden efectivo del decoder del servidor. El formato
y el resultado nominal no habilitan un despacho y la guardia debe verificar
el estado de nuevo justo antes de éste.
Pasan 33 tests locales y el manifiesto anterior de muñeca sigue recalculando
igual. Sin inferencia, captura, modificación del robot ni movimiento en esta
intervención. Rutas, hashes y backup están en la
[ficha](../SYSTEM_CUSTOMIZATIONS.md#smolvla-paired-nominal-20261110).

## Carga verificada de fuentes — 10-11-2026

**Estado de esta versión histórica: preparado y probado localmente; gate físico cerrado.** El cargador
`scripts/vla/verified_pico_wrist_pc_loader.py`, ejecutado con Python aislado,
comprueba el binding, su índice y las copias retenidas antes de compilar e
importar los módulos Python del proyecto. El bootstrap que genera
`scripts/vla/pico_wrist_verified_stream.py` comprueba exactamente los bytes de
la fuente y del payload, además de la sesión, antes de ejecutar el bundle; no
lee por adelantado los latidos posteriores del descriptor. La vía de host
propuesta pasa a guardia y worker los hashes de fuente del índice ya
verificado. Las pruebas de esos procesos son locales y no habilitan movimiento.

Pasaron 71 tests locales: `test_verified_pico_wrist_pc_loader` (12),
`test_pico_wrist_verified_stream` (9), `test_pico_wrist_stream_start` (15),
`test_pico_wrist_docker_launcher` (4), `test_run_pico_wrist_native_trial`
(18), `test_pico_wrist_review_binding` (6) y `test_check_pico_wrist_full_passive`
(7). La importación aislada pasó con el binding
`../Humanoide-vla-evidence/PICO_WRIST_VERIFIED_LOAD_20261110/binding-final/`,
SHA256 `6b9974e6e3af5b31b15cc369818ec7d5adad850f11c095def4a81ced6248eb1e`.
El check `check-d8ad18cd316e4ebe83a3eeb3ae0a6b84` pasó sin goals; utiliza modo
pasivo y no prueba el arranque verificado físico, `--run` o cancelación real.

El binding conserva una copia de la revisión anterior a este registro; no es
una aprobación ni demuestra la configuración o páginas cargadas en Motion.
El bootstrap PC que comienza antes de verificarse, el intérprete, las
bibliotecas y procesos externos, ROS/SDK y el script shell de askpass no quedan
atestados. La comparación de los bytes tampoco verifica escena o parada.
En esa versión los gates incondicionales y
`reviewed_bundle_attestation_not_implemented` bloqueaban el despacho. La
[sesión acotada posterior](#sesión-acotada-de-muñeca--10-11-2026) integra la
vía de una muñeca sin habilitar control directo ni VLA. No se instaló ni
ejecutó una tarea física ni SmolVLA.

Reproducción de importación, desde la raíz del repositorio:

```bash
python3 -I -B scripts/vla/verified_pico_wrist_pc_loader.py --check \
  --binding ../Humanoide-vla-evidence/PICO_WRIST_VERIFIED_LOAD_20261110/binding-final \
  --binding-sha256 6b9974e6e3af5b31b15cc369818ec7d5adad850f11c095def4a81ced6248eb1e
```

Evidencia, fuentes, hashes y backup previo en la
[ficha](../SYSTEM_CUSTOMIZATIONS.md#arm-pico-verified-load-20261110). Esta
receta no conecta al robot ni cambia su postura.

## Latido y cierre de guardia — 10-11-2026

**Estado de esta versión histórica: comprobación local completada; gate físico cerrado.** En el modo de
guardia previsto para cancelar por UUID, el monitor incorpora un plazo de
latido del supervisor, con identificación de sesión y secuencia. El puente
emite el latido tras muestras válidas y mientras el lease sigue vigente. El
cierre normal requiere observar estado terminal y reposo antes de aceptar el
mensaje de parada de guardia; si la salida es incierta, se mantiene la
advertencia y no se declara una parada física. Una solicitud de cancelación o
una muestra inmóvil no certifica distancia de frenado.

En esta versión pasaron 89 tests: `test_arm_from_pico_supervised`
(23), `test_arm_native_lease_bridge` (26), `test_pico_wrist_native_coordinator`
(15), `test_pico_wrist_docker_launcher` (3), `test_run_pico_wrist_native_trial`
(17) y `test_pico_wrist_trial_admission` (5). El check integrado
`check-429a4a835ee14e25ab8f0800c8ca091c` pasó PC→Motion con cero goals y
`guard_can_cancel=False`: **no ejercita el latido activo, la cancelación ni la
detención física**. Los hashes exactos de esa ejecución están en su
`sources-sha256.json` y en la [ficha](../SYSTEM_CUSTOMIZATIONS.md#arm-pico-guard-heartbeat-20261110).

La habilitación del ejecutor de muñeca sigue pendiente: el lanzador importa
módulos antes de comprobar sus archivos; un borrador que verificaba el bundle
después de ejecutar su inicialización fue retirado. Una solución debe vincular
los bytes que se cargan con la sesión antes de permitir el despacho. No se ha instalado ni ejecutado tarea
física ni SmolVLA. Las fuentes previas están respaldadas en
`../Humanoide-vla-evidence/ARM_PICO_GUARD_HEARTBEAT_20261110/before-ed9f7fc.tar`.

Para reproducir los tests, ejecutar `python3 -B -m unittest discover -s
scripts/vla -p 'test_NOMBRE.py' -q` para cada archivo indicado. El check pasivo
se ejecuta con `python3 -B scripts/vla/run_pico_wrist_native_trial.py --check`
y las rutas `--manifest`, `--urdf` y `--transmissions` de la preparación
`../Humanoide-vla-evidence/PICO_WRIST_PREP_20261110T103237Z_078897/`.
Esas pruebas no habilitan la salida física.

## Handoff de argumentos ArmTask — 10-11-2026

**VERIFICADO ESTÁTICAMENTE, no probado mediante envío de meta.** El proceso
`robot_app` y sus bibliotecas se leyeron desde el contenedor Motion
`walker-motion.manipulation_robot_app-1`, sin escribir en el robot, crear un
goal o moverlo. La IDL actual `ArmTask.action` (SHA256
`64ecf688b57d21ed5415721522f8d85f3a2981e31e43479c3fa7460e64351150`)
declara dos strings: `task_name` y `yaml_args` con JSON. La fuente generada
`ArmTask.cxx` (SHA256
`1af37bdf750595219476602de7b1bfefb8a3710816b0cbd80fac1c9abb4e87be`)
y el copy constructor compilado de `libmc_task_msgs.so` SHA256
`a6307c253e024593c8f31d3c73bad9df2681beb5b481a2a79ad115483db61ea2`,
offsets `0x217860–0x2178b7`, sitúan el segundo string en desplazamiento `0x20`.

En `libuser_interfaces.so` SHA256
`595d5f843900d9a1cd23e638dd90c95e55f3967a218752280af0d7c186bcdc0f`,
`UserInterfacesClient::HandleAccepted` offsets `0x3a948–0x3a9b4` copia los
strings del goal a los offsets `0` y `0x20` del cliente y fija su estado a 1.
En `robot_app` SHA256
`fb77e863303d8964e9821bd9efadb2dba86807ed4ec265d56ec7bb1e39bdeff4`,
`main::{lambda()#6}` comprueba ese estado en `0x5ad38–0x5ad45`, copia el
segundo string en `0x5c401–0x5c452`, lo analiza con el parser JSON en
`0x5c64e`, conserva el resultado en `0x5c6c7–0x5c6ff` y llama a
`Blackboard::set` con la clave `task_json_args` en `0x5ca34–0x5ca57`.
El `libmeta_move.so` con hash `bfeab1c7a295b58cd96fddd20916fc3f7fe16bd8c8ad1e77720f48aad34ccc69`
lee esa clave y los campos `component_names`, `goals`, `mode`, `durations`.
Esto relaciona estáticamente la entrada del goal con la lectura de MetaMove;
no demuestra que el formato concreto se acepte o se ejecute correctamente.

En la observación del 10-11 a las 11:35:57 UTC el PID 65 dentro del contenedor
tenía `/proc/65/exe` con el hash anterior y mostraba en `/proc/65/maps` las
tres bibliotecas con inodes 4217087, 4219086 y 4215362, coincidentes con las
rutas y hashes de disco. Esto vincula las rutas al proceso en ese momento; no
es un hash de páginas en RAM ni acredita configuración dinámica. Los extractos
y `process-map-snapshot.json` están en
`../Humanoide-vla-evidence/MOTION_ROBOT_APP_ARG_HANDOFF_3344c4e217e8/`, con
`SHA256SUMS`. Las copias `robot_app` y `libuser_interfaces.so` se comprobaron
contra sus hashes remotos; el constructor de `libmc_task_msgs.so` se extrajo
por lectura remota y se asoció al hash observado, sin copia completa de esa
biblioteca. El respaldo de documentos anteriores está en `before-docs/`.

Receta de lectura: desde la raíz usar `collect_estop_available_readonly.execute`
para descubrir `docker ps`, y en el contenedor redescubierto leer `sha256sum`
y `base64 -w0` de `robot_app` y `libuser_interfaces.so`; decodificar en una
carpeta privada y comparar hash antes de analizar. Leer `ArmTask.action` y el
constructor en `.../mc_task_msgs/share/mc_task_msgs/src/mc_task_msgs/action/ArmTask.cxx`.
Sobre las copias ejecutar `objdump -d -C` para los intervalos anteriores;
el constructor de `libmc_task_msgs.so` se puede leer con el mismo `objdump`
en el contenedor. Para proceso, comparar `/proc/<pid>/exe` y
`/proc/<pid>/maps` con `stat` y SHA256 de las rutas; `process-map-snapshot.json`
conserva la consulta concreta. Son sólo lecturas: no llamar a los servicios de
ejecución durante esta investigación.

Siguen pendientes la aceptación dinámica, orden efectivo de las siete juntas,
trayectoria, geometría v4, exclusividad, frenado y mando de mano. No se ha
abierto el gate físico ni probado el ciclo de SmolVLA.

## Guardia previa y entrega incierta — 10-11-2026

**Estado: comprobado en simulación y parcialmente en integración pasiva.** El ensayo
candidato es una sola tarea nativa estática de muñeca derecha; no consume ni
ejecuta acciones de SmolVLA. No se ha abierto el gate físico ni el de
atestación y no se ha realizado prueba física de estos cambios.

Antes de confirmar el UUID al worker, el coordinador llama a
`check_guard_before_dispatch`: exige el mismo lease y referencia, muestra
fresca de la guardia, 20 articulaciones inmóviles junto a la referencia y
comprobaciones existentes de envolvente y objetivos estacionarios SPS. La
guardia y el lease deben continuar activos durante el envío; una comprobación
previa no demuestra parada ni elimina las carreras físicas del handshake.
El módulo local `scripts/vla/pico_wrist_trial_admission.py` también contiene
comprobaciones de estructura de informe físico y de identidad del candidato;
no acredita por sí mismo la procedencia o actualidad del informe y no es un
permiso de movimiento. Los bundles host deben incluirlo antes del coordinador.

El lanzador local distingue una entrega de fuente incompleta de una entrega
potencialmente ejecutada tras el sentinel. En caso incierto intenta observar el
mismo proceso y comunicar la incertidumbre sin reintentar ni enviar HOME; una
salida del proceso o una cancelación no prueban detención física. También
verifica una secuencia de eventos y el UUID antes de comunicar éxito. La
observación no está garantizada ante caída del PC o terminación forzada; estas
comprobaciones no constituyen una prueba de parada.

Se completaron 66 pruebas locales: 17 del lanzador, 5 de admisión, 15 del
coordinador, 7 del check pasivo y 22 del puente de lease. El check integrado
`check-e613e5a37ab14beda72d817adb0d4eb0` pasó PC→Motion con la versión actual
del coordinador y de admisión; no ejecuta la rama física del lanzador. El
snapshot privado de fuentes y entradas tiene SHA-256
`8d72f944615a8e42bf18675e50c147fd8b5b373a965b327a7b5c6ae2b583b466` y coincide
con fuentes actuales; la copia documental incluida precede a este registro.
No acredita autorización, runtime cargado ni movimiento. La trayectoria real, geometría de mano,
distancia de parada y referencias próximas a límites nominales SPS siguen sin
cualificar. No se registran nuevas instalaciones o movimientos en el robot.

## Revisión del lanzador — 10-11-2026

El `--check` del lanzador llama ahora a la comprobación pasiva integrada PC→
Motion→guardia y cliente nativo de lectura. Con las fuentes actualizadas pasó
sin crear meta ni movimiento; el proceso y `/tmp` temporal no se observaron
tras terminar. Evidencia privada
`../Humanoide-vla-evidence/PICO_FULL_PASSIVE_CHECK/check-5377068e140c41adb7d978c292ef327a/`:
`stdout.jsonl` SHA256 `bd2777d7ecc6eed971d23b1f1f3d3c6b57f9b0fb9f4408eb8e2af80c1af8f92a`,
`sources-sha256.json` `fe925978f51d41ec10ae88dbfa549fdbc548ea3103f139c1b5d1655c21023a37`.

Se corrigieron dos fallos observados al revisar la rama futura: si se bloquea
el journal, el progreso del coordinador deja de renovar el lease; si la entrega
de código o payload al proceso hijo puede haber sido parcial, se conserva su
handle y resultado incierto, sin asumir que matarlo frene el robot. Una espera
de guardia de hasta26 s respeta el TTL independiente de preflight30 s. La
prueba local de disco bloqueado fue corregida para esperar el rechazo o
expiración efectiva del archivo, sin confundir una bandera en memoria con una
escritura ya terminada. Son pruebas con procesos simulados, no medidas de
frenado o certificados de latencia.

La copia vinculada `../Humanoide-vla-evidence/PICO_WRIST_REVIEW_BINDING_FINAL_20261110/`
tiene binding SHA256 `734032a629b8fb5a16cd22118e879652b3f2acc3ebe8ace778d941045ad043b1`;
una comparación local observó coincidencia de fuentes controladas y de los
bytes del manifiesto, URDF y SPS. El texto vinculado es una instantánea de
esta guía, no una aprobación ni una revisión integral del runtime. Una copia
anterior queda histórica tras los cambios. El lanzador exige esa comprobación
de integridad, pero `physical_release_gate` y la atestación técnica siguen
bloqueados: no se ha instalado ni enviado la tarea, ni validado físicamente la
trayectoria, mano v4, parada o aplicación de SmolVLA.

112 tests locales de las familias wrist, guardia, lease y comprobación pasan;
el código y el check pasivo no acreditan que la política alcance la pelota.

## Comprobación integrada pasiva — 10-11-2026

Se ejecutó una única comprobación PC→host Motion con desafío y latido,
guardia ROS2, lease en `/tmp` compartido y proceso de solo lectura en el
contenedor nativo. Este último contrastó las huellas de las clases ROSA
instaladas y validó el formato de la meta; un UUID sintético se comunicó
únicamente al guardia. Resultado `PASS_PC_HOST_GUARD_READONLY_NATIVE`, sin
crear ni enviar un goal. El guardia creó clientes ROS efímeros para descubrir
interfaces, pero no llamó a envío ni cancelación. Los procesos y el directorio
temporal se observaron retirados al finalizar.

Evidencia privada `../Humanoide-vla-evidence/PICO_FULL_PASSIVE_CHECK/check-daed9efa9c0641e0ba656fc2cd077e5a/`:
`stdout.jsonl` SHA256 `87de0fd70ad37e96ff0753546a85d94a75204a3bc4754fd5bed63b140313b8fd`,
`sources-sha256.json` `c0eef07d763eea02a45afdacf0bc7bd21acb6f23668b902fba18489f2cbb8a0a`.
Seis tests locales del comprobador pasan. Su receta es:

```bash
python3 -B scripts/vla/check_pico_wrist_full_passive.py --check \
  --manifest ../Humanoide-vla-evidence/PICO_WRIST_PREP_20261110T103237Z_078897/candidate/manifest.json \
  --urdf ../Humanoide-vla-evidence/PICO_WRIST_PREP_20261110T103237Z_078897/runtime.urdf \
  --transmissions ../Humanoide-vla-evidence/PICO_WRIST_PREP_20261110T103237Z_078897/transmissions.yaml
```

También se conectó una comprobación de integridad al lanzador: compara los
bytes de fuentes/bundles controlados y las tres entradas con una copia local
vinculada a la guía técnica. Binding privado
`../Humanoide-vla-evidence/PICO_WRIST_REVIEW_BINDING_INTEGRATED_20261110/`,
SHA256 `5c61f48fa838a96df3a4009fa21a0dcc4dfffe6fb29e581162fd0ec83f9b7ce0`.
Seis tests del binding y ocho del lanzador pasan; la comparación puntual
actual devolvió coincidencia. El texto vinculado es la guía existente, no una
aprobación ni una revisión independiente; no demuestra identidad del revisor,
runtime en memoria o firmware. La copia anterior es histórica y no coincide
con el lanzador modificado.

El cliente ROSA aún no ha ejecutado una meta de esta prueba y no se han probado
ni staging ni cancelación física. Siguen cerrados el gate físico y la
atestación de revisión técnica del lanzador; la geometría/montaje de la mano
v4 y la trayectoria real siguen sin cualificar. Los resultados pasivos no
habilitan el VLA, no garantizan frenado y no justifican modificar protecciones.

## Lanzador candidato — 10-11-2026

**Revisión posterior de fuentes:** el lanzador prepara la conservación de
bytes y hashes de ocho fuentes PC controladas, además de bundles y entradas.
Se corrigió la ruta del lector de E-stop y se comprueba que esas fuentes se
puedan leer. Esto no acredita los módulos ya cargados, Python, ROSA, SDK ni
todo el entorno. No se ha generado una aprobación externa ni se requiere
inferirla de un hash; la vinculación a la revisión técnica real sigue pendiente.

Se preparó un lanzador que combina la tarea nativa local de muñeca, el cliente
ROSA de cajas, un monitor de cuerpo/manos/paros, lease y un latido de desafío
PC–Motion. La instalación propuesta es aditiva y conserva recibo; una marca
global impide repetir automáticamente un intento incierto. El monitor verifica
los seis objetivos que se esperan quietos contra la postura y avisos SPS
actuales, además de la meta de muñeca. Una cancelación independiente del UUID
propio puede solicitarse ante fallo; si se recibe posteriormente estado activo,
se permite una segunda solicitud al mismo UUID sin reenviar el movimiento.
El estado posterior puede ser antiguo; ninguna respuesta certifica frenado.

Pasan 94 tests locales en total, con procesos o ROS simulados (incluidos
preparador y plan). La guardia final y su intercambio de UUID sintético/lease
pasaron una prueba pasiva en Motion: cero metas y movimientos. Evidencia
`../Humanoide-vla-evidence/ARM_NATIVE_BRIDGE_CHECK/check-fe7cb1c412de437b9ddbd783337b3623/`,
`stdout.log` SHA256 `d8a9590b0b81a302d9c481f2b1b20bc595c968e53688ad6f8490507a3391d243`,
`sources-sha256.json` `a952464f7130fd0eaf5e91acd77ee5075840321860618ab2032df16c2c6e5f9b`.
La prueba pasiva no ejecutó el lanzador físico, staging, cliente ROSA real ni
cancelación de una trayectoria.

**No está listo para mover:** `physical_release_gate` y la atestación de
bundles revisados siguen cerrados. La tarea no está instalada; falta verificar
el lanzador integrado, atestar el código efectivamente revisado, revisar la
geometría y el recorrido v4, y establecer un procedimiento frente a pérdida
de cliente/guardia y parada física. El canal de estado no demuestra exclusividad
distribuida y un latido no prueba que el operador vea alertas. No se ha hecho
staging ni se ha mandado ningún movimiento; no habilita SmolVLA físico.

## Puente de supervisión y cliente nativo — 10-11-2026

`arm_native_lease_bridge.py` prepara un lease de duración experimental 0,5 s,
renovado sólo con telemetría válida, y una asociación del UUID al guardia antes
de devolver la petición al cliente ROSA. La fuente archivada del SDK muestra que
`create_goal_request` termina antes de `call_async`; se conserva el cotejo de
huellas del cliente de cajas. El puente pide ACK del UUID exacto antes del
envío, y si falla el intercambio retira la referencia local y no envía.

El monitor funciona ahora como proceso pasivo continuo, acepta un UUID exacto
antes de la comunicación de una meta y continúa rechazando otras acciones.
Un comprobador ejecutó monitor y coordinador en Motion, usando el mismo reloj
monotónico: un UUID sintético obtuvo ACK y, al terminar el monitor, se observó
la revocación del lease. No se creó ni envió una meta, ni se instaló tarea.
Procesos y directorio temporal terminaron. Evidencia privada
`../Humanoide-vla-evidence/ARM_NATIVE_BRIDGE_CHECK/check-83127cadbf8e4e579c29d1931cebc92d/`:
`stdout.log` SHA256 `3df383804eb9f97ffd6ff66b8f9399996dcf741abf52ef11de21642f4960100f`,
`sources-sha256.json` `f3a9a8266fe32adfa5dd7b1d79e3885bd9b23efc1b4a0dfceaad550c5f2416eb`.
Pasan 14 tests de monitor, 17 de puente y cinco de comprobador con procesos o
ROS simulados. `physical_release_gate` sigue bloqueando el acceso físico.
La prueba no usa el cliente ROSA real ni comprueba un lease entre contenedores,
la trayectoria, cancelación o frenado de un objetivo físico.

Una comprobación separada creó un marcador privado temporal en `/tmp` de Motion:
los contenedores ROS2 y de manipulación lo leyeron correctamente, sus namespaces
de reloj monotónico coincidieron con el host y la lectura de cada reloj quedó
entre las dos lecturas locales que acotaban su consulta. El marcador se retiró.
Es una observación puntual de ruta y reloj, no una prueba del lease o cliente
ROSA entre contenedores. Receta: `python3 -B scripts/vla/check_motion_lease_shared.py --check`.
Evidencia `shared-tmp-clock.json`, SHA256
`4feec448cbe6faf4149bc1742a02ee5c6a111feaea9b19078064728e46148f38`, en
el mismo directorio de evidencia.

Receta de la comprobación pasiva, con la muestra archivada; una repetición debe
volver a verificar la postura actual y no convierte esa muestra en permiso:

```bash
python3 -B scripts/vla/check_arm_native_bridge_live.py --check \
  --manifest ../Humanoide-vla-evidence/PICO_WRIST_PREP_20261110T103237Z_078897/candidate/manifest.json \
  --urdf ../Humanoide-vla-evidence/PICO_WRIST_PREP_20261110T103237Z_078897/runtime.urdf \
  --transmissions ../Humanoide-vla-evidence/PICO_WRIST_PREP_20261110T103237Z_078897/transmissions.yaml
```

La comprobación mantiene guardia y coordinador en un contenedor; se observó
por separado ruta temporal y reloj compartidos con el contenedor nativo, pero
el lease todavía no se ha probado entre los dos. La
detección 0,5 s, ACK 0,4 s y expiración
son valores experimentales, no límites de parada. `GuardPipe.exchange` limita
la escritura al pipe y la espera del ACK, con prueba simulada de pipe lleno;
la interfaz genérica acepta otros callbacks y no puede imponerles ese plazo.
Si muere el cliente ROSA, un
lease que éste deja de leer no cancela por sí solo una consigna aceptada. La
cancelación y la respuesta del servidor no certifican frenado; continuar
requiere supervisión física y tratamiento de resultado incierto.

## Preparación nativa de muñeca — 10-11-2026

Con el patrón del ensayo de brazo de cajas se preparó una sola acción
`MetaMove` derecha: la referencia procede de una muestra 20D; el objetivo
varía únicamente `R_wrist_roll_joint` +0,01 rad en 4 s. No es una propuesta
SmolVLA ni se programó un retorno automático. El preparador rechaza extremos
fuera del URDF o las transmisiones SPS; la comprobación de velocidad es de
promedio necesario y no acredita picos, trayectoria o colisión.

La muestra tenía los dos codos dentro de sus límites nominales y márgenes
aproximados0,000622 y0,001293 rad. El valor0,002 rad del informe es una banda
diagnóstica, no un límite oficial ni una decisión automática de admisión. No
se ha establecido incertidumbre total, comportamiento del planificador o
distancia de parada. El monitor independiente alerta si un eje inmóvil se
aproxima a la mitad de su margen nominal; no garantiza que el servo se detenga.

Paquete privado en `../Humanoide-vla-evidence/PICO_WRIST_PREP_20261110T103237Z_078897/`:
`candidate/task.xml` SHA256 `70544f68d66f77ea7d4be163f6d517fba9a572127dcaa71e0c7dfe8f0e2abdca`,
`candidate/manifest.json` `adcffeafa262dbb8a07e736fb8fadd295885e0a9f9dd6525eaf73a8f759ad576`,
`stage-plan-v2.json` `07d690dacbc38010e7de51e2bfd99cf70526458e6135964eb1ca0303adc1eca1`.
El plan v2 usa `/tmp` y exige comprobar que host y contenedor comparten la
ruta; `stage-plan.json` anterior se conserva como evidencia obsoleta.
No se instaló ni ejecutó; el plan es solo local. La muestra no acredita las
condiciones físicas al intentar mover. Once tests del preparador/plan pasan.

Validación reproducible del paquete existente:

```bash
python3 -B scripts/vla/prepare_pico_wrist_native_probe.py --check \
  ../Humanoide-vla-evidence/PICO_WRIST_PREP_20261110T103237Z_078897/candidate/manifest.json \
  --urdf ../Humanoide-vla-evidence/PICO_WRIST_PREP_20261110T103237Z_078897/runtime.urdf \
  --transmissions ../Humanoide-vla-evidence/PICO_WRIST_PREP_20261110T103237Z_078897/transmissions.yaml
```

El cliente de cajas y el monitor de corredor aún no se han probado juntos con
una meta real; falta ese lanzador, así como revisar despeje real de mano v4,
trayectoria y parada. Ningún parámetro `--run` de
estas piezas habilita el movimiento. La preparación no cumple por sí sola los
gates del VLA físico.

## Referencia del ciclo de cajas — 10-11-2026

Por indicación del usuario se consultó el ciclo de cajas ya probado. El
[registro de mesa74](../guides/TRANSFERENCIA_CAJA_ENTRE_MESAS_CON_APRILTAG.md)
describe un ciclo físico completo de 323,879 s con depósito, HOME y confirmación
del operador. La prueba usaba abrazaderas y tareas concretas para cajas. El
catálogo atribuye el agarre operativo a percepción 6D y tareas nativas; el
proveedor afirma un VLA integrado en otro flujo, pero el XML examinado no
identifica checkpoint ni demuestra que fuera el ejecutado en ese ciclo.

Además, el [diagnóstico nativo de brazos](../box_handling/EMPTY_ARM_DIAGNOSTIC_20261022.md#preparación-nativa-completa-de-un-brazo)
probó físicamente el brazo derecho por separado mediante dos `MetaMove` y
retorno. Motion informó status 4, `SUCCEED`, código 1101001, y el operador
observó movimiento normal. En la traza conservada hay 1.299 muestras 20D;
el menor error máximo de los siete ejes respecto al objetivo fijo fue
0,002095673 rad en una muestra. Esto respalda el orden y seguimiento de ese
XML fijo en aquella postura con abrazaderas, no acredita objetivos dinámicos,
parada ni la geometría de manos v4. Las tareas temporales del ensayo se
retiraron: no ejecutar sus rutas históricas.

La comparación lee `candidate.joint_order` y `candidate.outbound_joint_target_rad`
del manifiesto `../Humanoide-vla-evidence/20261022T093744Z_EMPTY_ARM_CONTROL_DIAGNOSTIC/native-right-final/manifest.json`
(SHA256 `8d2c823193c8e3bd7e0d83ee83740142e841ee97a452f750a66227c2465d329c`),
busca cada muestra `/mc/whole_joint_states` por nombre en `native-right-trace.jsonl`
(SHA256 `37d2a12618eb512f8f115759b56ccd210542d023c42565953f38e015ee7f0c48`),
calcula el máximo error absoluto de los siete ejes por muestra y toma el mínimo.
El resultado es una observación puntual, no una cota de seguimiento futuro.

El cliente de cajas `scripts/box_handling/scenario1_action_client.py` usa la
misma acción `/mc/manipulation/action` con `task_name` y `yaml_args`; comprueba
aceptación, UUID, tiempo y cancelación, y declara que cancelar no certifica
parada física. Su criterio de éxito exige status 4, `SUCCEED` y código
1101001. El candidato de brazo ahora adopta ese criterio. Una prueba pasa su
orden hipotética por `validate_goal` del cliente de cajas y compara criterios
de resultado, además de las simulaciones anteriores: nueve tests de brazo y
37 del cliente de cajas pasan. La aceptación del formato por ese validador
no prueba que Motion acepte o ejecute la tarea dinámica.

No se ejecutó movimiento ni se modificó el cliente de cajas. El candidato
SmolVLA usa rclpy, no el cliente ROSA de cajas, por lo que sólo se reutilizó
el contrato, no se afirma una validación física de su transporte. Permanecen
abiertos geometría y trayectoria con mano v4, paso de argumentos al nodo,
parada efectiva y gates de VLA; la salida física sigue bloqueada.

## Candidato de ejecución y cancelación — 10-11-2026

Se amplió el runtime pasivo con una rama candidata: genera una meta desde
el estado medido para `right_arm` con una variación de 0,01 rad en muñeca,
envía como máximo una acción con UUID asignado, supervisa articulaciones y
solicita cancelación de ese UUID ante anomalías. La recepción desconocida,
fallo de enlace o respuesta de cancelación no demuestran parada; no reintentar
ni ordenar HOME automáticamente. El valor, duración y corredor son
experimentales, no límites certificados ni una trayectoria revisada.

La ejecución real permanece bloqueada al entrar en el runtime mediante
`physical_release_gate`, y el comprobador local rechaza `--run`. En tests se
sustituye esta función únicamente dentro del proceso simulado, sin ROS real:
una acción simulada llegó al objetivo y una activación de paro mientras se
esperaba aceptación provocó solicitud de cancelación del UUID exacto. Siete
tests locales pasan. **No se ejecutó el candidato en el robot.**

Siguen pendientes: comportamiento real de `yaml_args`, planificación y
movimiento con manos v4, cobertura geométrica y escena, y parada; tampoco
existe un lanzador físico habilitado para este candidato. Este ensayo no
conecta SmolVLA ni demuestra ejecución física de la política.

## Monitor pasivo de brazo — 10-11-2026

El operador confirmó manos v4 vacías, postura PICO con cabeza bajada, zona
libre, ruedas bloqueadas, cargador desconectado, ambos paros accesibles y
persona junto al paro, sin otro control activo. La batería observada en la
lectura puntual era 68,6/71,1 %. Esa confirmación y lectura no acreditan
condiciones posteriores.

Se adaptó el monitor de cabeza a esta referencia y se preparó un comprobador
pasivo. Éste valida controladores y ausencia de publicador SDK, hash de la
tarea dinámica, estado de articulaciones, salud de actuadores, manos, ambos
paros y comunicación de supervisión. Un único `--check` en Motion pasó y
terminó sin comandos. No quedó proceso de monitor observado. Cuatro tests
locales pasan; comprueban además el rechazo de movimientos excesivos en una
función de corredor, pero el check en vivo no mueve el eje ni prueba esa
función durante una trayectoria. El paso de muñeca de 0,01 rad y umbrales del
código son hipótesis experimentales, no límites certificados.

En la revisión inicial el código no incluía envío. La rama candidata posterior
incluye envío y cancelación sólo comprobados en simulación; `--run` y
`dry_run=False` están bloqueados. La recepción de
argumentos de `move_components_json`, planificador y parada física siguen
pendientes. La autorización del usuario existe, pero esta observación no
cumple los gates de ejecución del VLA ni valida geometría de manos o escena.
Receta pasiva: `python3 -B scripts/vla/check_arm_from_pico_supervised.py --check`.
No repetirla para suplantar la verificación necesaria antes de un movimiento.

## Tarea dinámica nativa encontrada — 10-11-2026

La consulta de catálogo de Motion devolvió `move_components_json` como
disponible para mano v4. Su XML instalado, SHA256
`bfcfc097dfefb3e81fcb2acc913d7db55545b3ea3b853b345b9ba1836c01b797`,
contiene una sola acción `MetaMove json_args="true"`. El `libmeta_move.so`
instalado, SHA256 `bfeab1c7a295b58cd96fddd20916fc3f7fe16bd8c8ad1e77720f48aad34ccc69`,
coincide con la copia analizada. En ésta, `GetRequestFromXmlNode` lee ese
booleano y llama a `UpdateRequestFromBlackboard`, que consulta `task_json_args`,
lee `component_names` como lista de nombres y `goals` como matriz de números;
también contiene lecturas de `mode` y `durations`. El archivo de descripción
de Cruzr leído en Motion declara un componente `right_arm`. El componente
configurado y la carga efectiva del proceso no quedan demostrados por el archivo.

El conversor genera ahora `candidate_dynamic_task`: nombre de tarea y una
hipótesis de argumentos para un solo brazo, con una fila de siete objetivos,
modo 0 y duración experimental. Es un **borrador**, no un ejecutor: el paso de
`ArmTask.yaml_args` al blackboard tiene evidencia estática posterior, pero
faltan demostrarlo dinámicamente, la identidad/carga efectiva de la tarea y la
semántica y trayectorias del
planificador, límites, control exclusivo y parada. No se envía la tarea, no se
instala ni recarga nada, y `--run` continúa bloqueado. El catálogo por sí solo
no prueba carga o efecto físico. La consulta del catálogo se reproduce con la
receta de la guía del puente, cambiando el filtro por `move_components_json`.
Se conservaron la sesión shadow previa y se probaron siete tests locales; no
se repitió entrenamiento, captura ni movimiento.

**Estado: conversión en vivo verificada sin control físico; ejecución PENDIENTE.** El
usuario solicitó acortar la prueba y reutilizar lo ya disponible. Las tareas
de fábrica y `scripts/custom_tasks/heart_v4_fingers.xml` muestran el formato
`MetaMove`, `type="arm"`, `location="right"` y `joint_angles` de siete valores.
Esto abre una vía para estudiar objetivos sucesivos con el controlador de
manipulación, sin asumir que haya que alimentar el SDK directo a 100 Hz.

[`prepare_ball_native_arm_step.py`](../../scripts/vla/prepare_ball_native_arm_step.py)
lee un resultado shadow JSONL completo mediante el auditor existente. Verifica
el checkpoint y la estructura, deriva el estado de los siete ejes de brazo a
partir de la predicción y su diferencia registrada, y limita cada diferencia
al valor solicitado por quien ejecuta el análisis. Emite por stdout un JSON con
los valores originales y limitados, el orden hipotético y un único XML candidato
`MetaMove type="arm" location="right"`. No instala archivos en Motion, no
crea clientes ROS, no envía órdenes y `--run` devuelve 2 sin conectar.

La opción `--stream` procesa el flujo real de `run_ball_live_shadow.py` por
stdin y produce un borrador por cada predicción, tras verificar checkpoint,
secuencia, sellos, estructura y cierre del flujo. Conserva el escalar de mano
sin interpretarlo como orden. No instala tareas ni publica a actuadores. Si el
flujo termina incompleto o contiene datos incompatibles, devuelve error; ya
puede haber impreso borradores anteriores, que tampoco habilitan movimiento.

Este es un **borrador para revisar, no una tarea habilitada**:

* El orden de siete ejes y el significado de las metas del modelo aún no se
  han cualificado para esa ruta `MetaMove` en esta unidad.
* El parámetro de salto y la duración son experimentales; no son límites de
  seguridad ni comprueban velocidad, aceleración, colisión o parada. Recortar
  una propuesta altera la política y puede impedir completar la tarea.
* Una grabación no acredita estado actual; el flujo en vivo tampoco acredita
  latencia física completa o sincronía. No contiene control de dedos ni
  detección de agarre o apoyo.
* La ejecución de `MetaMove` en esta postura, la aceptación del formato y su
  cancelación/retorno siguen sin verificarse; no instalar ni ejecutar este XML
  como resultado del diagnóstico.

Reproducción con el shadow ya existente, sin repetir captura o inferencia:

```bash
python3 -B scripts/vla/prepare_ball_native_arm_step.py \
  --check ../Humanoide-vla-evidence/20261109_SMOLVLA_LIVE_SHADOW/live-run.jsonl \
  --sample 0 --max-step-rad 0.05 --duration-s 4
python3 -B -m unittest discover -s scripts/vla -p 'test_prepare_ball_native_arm_step.py' -v
```

El ejemplo de 0,05 rad y 4 s es sólo para revisar el formato, no una elección
validada para mover el brazo. Con esa primera muestra se produjeron siete
diferencias candidatas limitadas a 0,05 rad; `physical_control_qualified=false`
y `physical_commands_sent=0`. Los cuatro tests locales pasan. La muestra es
del 09-11, anterior al movimiento de cabeza; no describe la escena actual.
Entrada SHA256 `5be819ea4a7941c3b136c40aa66494bbda42c5b6b116fbe431686cf2b85e8131`.

## Observaciones actuales — prueba integrada sin movimiento

Con el checkpoint ya entrenado y la cámara del robot se ejecutó un único flujo
de 5 s a 1 Hz. La inferencia en Ada entregó cuatro predicciones y la conversión
generó cuatro borradores de una acción derecha cada uno; no se enviaron órdenes.
La mayor diferencia original propuesta−estado fue 1,157168 rad; cada diferencia
del borrador se recortó al parámetro experimental 0,05 rad y la duración se
fijó experimentalmente en 4 s. Estos valores no son límites certificados. La
inferencia tardó 0,168–0,564 s; adaptador PC a predicción 0,271–0,687 s, sin
incluir transporte Vision→PC. No se guardaron imágenes ni se verificó que el
modelo identifique la pelota. El modelo vio las imágenes recibidas; eso no
demuestra un ciclo cerrado ni un agarre.

Se comprobaron localmente 7 tests. El colector de Vision y el contenedor
temporal de Ada habían terminado al concluir. Evidencia privada en
`../Humanoide-vla-evidence/20261110_NATIVE_LIVE_3ndpJ8/`: `shadow.jsonl`
SHA256 `ed178695efa640def802d854a9cc8738d33374191351f3563b4ff72333087fc1`,
`native-preview.jsonl` `a9eba4fe6a756ce9d91688570e709058993656cab32f59acc28ae6089c2514bd`,
`source.py` `37a057432ab181e399613451f2c8d38472254e88212e146dc8b8f965d3f7478f`
y `shadow-stderr.log` `f788aef7b645aba82d1ac2ed3bf547ed17d0a1dfd05ee5c0aea681a7fefd6e4b`.

La cadena ROS `R_shoulder_pitch→roll→yaw→elbow_roll→elbow_yaw→wrist_pitch→roll`
del URDF de Motion leído coincide con el orden de salida del modelo; el URDF
leído en texto normalizado a LF tenía SHA256
`a4bf032f2c8314c8d0f320357bbc7da8b75b846c1d44fb05b37ed0cb3bb0acfc`.
**Corrección 10-11:** el hash de los bytes reales en Motion es
`c01acb400366ec154a852e75853bc2b5cf4807d5bd217a89578b8f4cd8ae1760`;
contiene 721 finales CRLF. `execute()` normalizó los finales al devolver texto;
el hash anterior no identifica los bytes exactos en disco. Verificado mediante
`sha256sum` y normalización explícita dentro del contenedor.
Es una consistencia estática de la cadena cinemática, no demuestra que el
parser de `MetaMove` aplique ese mismo orden o que el archivo sea el usado por
el controlador en ejecución.

Para reproducir la conexión en observación, comprobar antes las fuentes fijadas
según [la receta shadow](../../scripts/vla/SMOLVLA_BALL_LIVE_SHADOW.md) y,
desde la raíz, usar sus argumentos de servidor existentes con `--seconds 5
--fps 1` y canalizar stdout a:

```bash
python3 -B scripts/vla/prepare_ball_native_arm_step.py --stream --max-step-rad 0.05 --duration-s 4
```

El paso limita cada articulación individual, cambia la salida del modelo y
no garantiza una trayectoria real, colisiones, agarre, parada o éxito físico.

Para pasar a un ciclo físico sigue faltando conectar los pasos al control del
robot, comprobar el orden y la parada de la tarea de brazo, y disponer
de una orden de mano con límites/confirmación de agarre y suelta. Ver la
[auditoría del SDK y mano](SMOLVLA_SDK_COMMAND_AGE_20261110.md).
