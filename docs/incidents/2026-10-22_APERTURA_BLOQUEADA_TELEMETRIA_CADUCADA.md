# Apertura bloqueada al adquirir telemetría — 22-10-2026

## Recuperación HOME autorizada y ejecutada — 22-10-2026

**BOX-TABLE74-EMPTY-HOME-RECOVERY-20261022 — VERIFICADO en telemetría.**
Esta actualización supera la frontera pendiente descrita en el diagnóstico
histórico inferior. El usuario informa pines/caja liberados; confirma abrazaderas
vacías/sin enganches, caja estable fuera del barrido, recorrido brazos/torso/
elevador libre, cargador fuera, ambos paros liberados, ruedas inmovilizadas,
ningún otro controlador y persona junto al paro. Autoriza un único HOME y
advierte brazos aún en postura de agarre y torso inclinado. No se infiere una
apertura lateral ejecutada ni se fabrica un journal de esa fase.

La rama ya contiene b92d004 (unificación del otro hilo). Esta intervención
**no modifica programa, perfiles ni tareas instaladas** ni prueba el depósito
nuevo. Se usa exclusivamente la tarea HOME conocida d9e9462792b41300d352604b53ea2a4890a9382e942321990708f6ded2e26ccb.
Su XML leído del robot empieza con cuerpo a cero y ajuste/apertura de brazos
en paralelo, después baja brazos y los recoge: no se describe como torso primero.
El operador confirma barrido libre también para esta postura.

Preflight de lectura e inmediato: inventario de contenedores/boot coincide con
la toma; hashes de dependencias y cadena de tareas intactos; controladores
correctos/acción libre; dos muestras20D habilitadas sin fault, velocidad0,
consigna–posición máximo0,001558 rad. HOME=0 y posición máxima2,141533 rad,
consistente con postura de agarre; no acredita clearance. Baterías56,0/56,3 %,
paros0/0 y cargador0. No reinicio, rearme, navegación ni nueva apertura.

Se ejecutó **una** llamada a `scripts/force_home.sh`, goal
`b559d0c5-d184-4b2a-b233-e6353abb6d73`, SUCCEED/status4/state1101001.
Comando16,593907356 s monotónicoPC (incluye transporte/CLI; no duración física
instrumentada). Postflight: dos muestras20D HOME=1, velocidad0,
máximo absoluto0,002109 rad, máximo brazos0,000959 rad; habilitados/sin fault.
SOC55,8/56,1 %, paros0/0, cargador0. Sin reintento ni otra trayectoria.
**Confirmación visual final del operador PENDIENTE** al registrar esta nota.

El journal de pin-relief conserva siete archivos originales byte a byte y la
toma original conserva `status=interrupted`. Antes de HOME se añadió sólo
`pin-relief/physical-run/trial.json.consumed.json`, apuntando al nuevo recibo
`home-attempt.json`: ya no admite apertura/retoma desde esa frontera después
de HOME. No borrar consumo ni volver a ejecutar el ciclo interrumpido.

### Receta y evidencia de esta recuperación

Evidencia externa:
`../Humanoide-vla-evidence/20261022_HOME_RECOVERY_164730Z/`.
Contiene autorización, inventarios/preflight/consultas inmediatas/postflight,
HOME instalado leído, recibo de intención único, UUID/resultado nativo,
consola, hashes, fuentes PC usadas y respaldo documental `before/`.
`recover_once.py` conserva la invocación exacta y rechaza un recibo preexistente.
Su contenido queda versionado abajo como receta histórica: **no reutilizar
su ruta, fuente o autorización** para otro movimiento. Otro ensayo requiere
nuevo estado/contexto/autorización y evidencia nueva. No autoriza reutilizar
fuentes de otros hilos sin revisar sus hashes.

```python
"""One operator-authorized native HOME, no retry or alternate motion."""
from pathlib import Path
from contextlib import ExitStack
import fcntl, hashlib, json, subprocess, time
from scripts.box_handling import scenario1_table74_home as h
from scripts.box_handling import scenario1_table74_current_release_run as r
ROOT=Path(__file__).resolve().parent
SOURCE=Path('/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20261022T162111Z_TABLE74_SUPERVISED_CYCLE_1476072/pin-relief/physical-run')
RECEIPT=ROOT/'home-attempt.json'
if RECEIPT.exists(): raise RuntimeError('Existing HOME intent; no repeat allowed')
profile=json.loads(h.PROFILE_PATH.read_text())
proof,info,hashes=r.load_predecessor(SOURCE,profile)
payload=h.cli.make_payload('check',profile,info['source'])
script=h.cli.ROOT/'scripts/force_home.sh'
script_hash=hashlib.sha256(script.read_bytes()).hexdigest()
reader=h.Reader(ROOT,False)
with ExitStack() as stack:
 for name in ('/tmp/cruzr_blue_workbin_cycle.lock','/tmp/cruzr-improved-scenario1.lock','/tmp/cruzr-table74-supervised-cycle.lock'):
  lock=stack.enter_context(open(name,'a'));fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 found=reader.inventory(info['context'],'immediate-inventory')
 reader.files(info,payload,found,'immediate-files')
 health=reader.health(found,'immediate-health')
 h.cli.atomic_json(ROOT/'immediate-verified.json',health)
 reader.inventory(info['context'],'immediate-final-inventory')
 fresh,_,fresh_hashes=r.load_predecessor(SOURCE,profile)
 if fresh!=proof or fresh_hashes!=hashes or hashlib.sha256(script.read_bytes()).hexdigest()!=script_hash:
  raise RuntimeError('Source or HOME wrapper changed; no dispatch')
 receipt=dict(phase='intent',automatic_retry=False,task='cruzr/home',
  operator_authorization='operator-authorization.json',
  manual_release_declared=True,opening_action_executed_by_agent=False,
  source=str(SOURCE),source_hashes=hashes,wrapper_sha256=script_hash,
  intent_pc_ns=time.time_ns(),result=None,measured_home=False)
 with RECEIPT.open('x') as stream: json.dump(receipt,stream,indent=2);stream.write('\n')
 # The previous phase can no longer authorize a subsequent opening after HOME.
 h.cli.claim_resume(SOURCE/'trial.json',RECEIPT)
 print('DISPATCH_ONE_HOME',flush=True)
 started=time.monotonic_ns()
 try:
  process=subprocess.run([str(script)],capture_output=True,text=True,timeout=90)
  h.cli.atomic_json(ROOT/'native-result.json',dict(returncode=process.returncode,stdout=process.stdout,stderr=process.stderr))
  print(process.stdout,flush=True)
  result=h.validate_result(process.returncode,process.stdout)
  receipt.update(phase='native_succeeded',result=result,command_elapsed_s=(time.monotonic_ns()-started)/1e9)
  h.cli.atomic_json(RECEIPT,receipt)
  post=reader.health(found,'postflight',require_home=True)
  reader.inventory(info['context'],'postflight-inventory')
  h.cli.atomic_json(ROOT/'postflight-verified.json',post)
  receipt.update(phase='succeeded',measured_home=True,finished_pc_ns=time.time_ns(),classifications=post['classifications'],safety=post['safety'])
  h.cli.atomic_json(RECEIPT,receipt)
  print('RECOVERY_SUCCESS '+json.dumps(dict(result=result,classifications=post['classifications'],safety=post['safety'])),flush=True)
 except BaseException as exc:
  receipt.update(phase='failed_or_unconfirmed',error=type(exc).__name__+': '+str(exc),finished_pc_ns=time.time_ns())
  h.cli.atomic_json(RECEIPT,receipt)
  print('NO_RETRY '+str(exc),flush=True)
  raise
```

**29-10-2026 — actualización:** un nuevo rechazo en preflight mostró el mismo
mensaje. La observación pasiva posterior halló intervalos de recepción de paros
de 4,926–4,931 s. Se ha preparado una espera acotada de ventana coherente sin
ampliar el límite inicial de 2 s; la causa concreta de cada rechazo sigue sin
identificarse y la validación en flujo real está pendiente. [Detalle y estado
vigente](../box_handling/OPTIMISTIC_SCENARIO1.md#ventana-fresca-de-seguridad--29-10-2026).

**BOX-TABLE74-OPEN-STALE-20261022 — VERIFICADO offline / causa temporal concreta PENDIENTE.**
Zona de registro: Europe/Madrid. Petición del usuario: analizar por qué se detuvo
el ciclo aunque no cambiaron las condiciones. Sólo lectura local y reproducción
offline; sin SSH, cambios operativos, reanudación, apertura ni HOME.

## Resultado comprobado

Toma `20261022T162111Z_TABLE74_SUPERVISED_CYCLE_1476072`.
`cycle.json` conserva `status=interrupted`, `phase_boundary=pin_relief`,
`in_flight=lateral_open` y referencia al journal de alivio. Son estado lógico
y frontera de ejecución, no una medición de apoyo/pines o postura actual.

- Recogida/traslado, aproximación, precontact y support registran etapas completadas.
- Alivio: goal `da91bcf4-3eea-4a7a-985e-28bab30d7d1d`, SUCCEED/status4,
  estado1101001, etapa5,454 s; journal `phase=succeeded`, sin error.
- Apertura: adquisición `health`5,860017 s; worker responde error en request1
  y rc78: `ValueError: Collected safety samples became stale`.
- No hay `ready`, eventos `action` ni `trial.json` de apertura. Por el orden
  del ejecutor, no se llegó a armar/despachar esa acción. Tampoco existe carpeta HOME.
- `pin-relief/physical-run/trial.json.consumed.json` no existe al consultar.
  No se modifica el journal ni su consumo; esto no autoriza por sí solo retoma.
- Journal del ciclo241,859700491 s hasta interrupción. No es ciclo completo,
  ni ahorro demostrado respecto a la referencia323,879 s terminada en HOME.

Los mensajes Docker inconcluyentes pertenecen al diagnóstico adicional de
la fase previa; el rechazo aquí tiene otra causa explícita, la adquisición
inicial del worker. Los errores de lease/cierre posteriores no sustituyen esa causa.

## Mecanismo y límite de la atribución

`scenario1_health_worker.Acquisition.complete()` exige cuatro recibos nuevos
posteriores a la petición, dos muestras articulares recientes, controlador y
estado de acción. Aplica `MAX_AGE_NS=2_000_000_000` a **todos** los canales de
seguridad. Si el primer canal envejece mientras llega otro, falla inmediatamente
cuando reúne el conjunto, sin esperar una ventana posterior coherente.
La comparación usa edades de recepción; mensajes de paro/batería sin header
no se presentan como muestras con sello de origen.

El monitor continuo `scenario1_live_health.py` ya distingue5 s para estop/servo
y2 s para el resto. La cadencia histórica medida en la unidad fue
4,4889–4,4920 s para ambos paros, frente a≈0,253 s para batería/cargador.
La adquisición inicial mantiene el límite uniforme de2 s. Es una inconsistencia
**VERIFICADA**, independiente de que los valores físicos permanezcan constantes.

En `Runtime.run`, salud inicial precede a `start_live_monitor()`: en apertura
se abre otra sesión y falla antes de activar su monitor continuo. La supervisión
de la fase de alivio no se reutiliza como monitor persistente de esta sesión.

La reconstrucción de la fuente embebida del health worker (incluyendo sus cinco
módulos auxiliares) coincide con el SHA de la toma:
`8f7761d7bfc9049b5492b8832cecf1a36f9bb75724d97e40f1a8cf86a0dddfb2`.
No comparar ese pin directamente con el SHA del archivo .py: incluye el cargador.

**INFERENCIA:** desfase de llegada de publicaciones lentas o demora de adquisición
puede explicar el rechazo intermitente sin cambio de geometría ni estado.
La excepción no conserva nombre del canal, recibos o edades; no permite afirmar
que fue exactamente estop/servo, ni descartar otro retraso o interrupción de datos.
Los5,860017 s son tiempo de adquisición, no antigüedad demostrada de una muestra.
No hay evidencia aquí de colisión/fault de servo como causa del aborto, pero
la ausencia de ese diagnóstico tampoco certifica el estado físico actual.

## Reproducción offline y propuesta

Sin ROSA ni robot, este ejemplo reproduce el mismo texto con valores invariantes:

```bash
python3 -B - <<'PYREPRO'
from scripts.box_handling import scenario1_health_worker as w
start = 10_000_000_000
c = w.Acquisition({'request_id': 'repro', 'command': 'health'}, start, 1)
for key in ('estop', 'charger', 'battery'):
    c.add(key, {'data': 0}, start+100_000_000, 2)
for key in ('servo', 'charger', 'battery'):
    c.add(key, {'data': 0}, start+3_000_000_000, 3)
for ns in (start+2_980_000_000, start+3_000_000_000):
    sec, nanosec = divmod(ns, 10**9)
    c.add('actuator', {'header': {'stamp': {'sec': sec, 'nanosec': nanosec}}}, ns, 4)
try:
    c.complete(start+3_000_000_000, {}, {})
except ValueError as error:
    assert str(error) == 'Collected safety samples became stale'
    print('REPRODUCIDO:', error)
else:
    raise AssertionError('Se esperaba rechazo por edad')
PYREPRO
```

Esto reproduce el mecanismo, **no** la secuencia real de recibos no archivada.
Propuesta pendiente: instrumentar el rechazo con canal/edades/plazos; adquirir
una ventana coherente de datos nuevos con límites por canal justificados y
sin reutilizar estados anteriores a la petición. No aumentar todos los límites
ni omitir errores. La sesión compartida propuesta evita además recrear esta
adquisición en cada fase, conservando observación continua y entradas frescas.
No se aplica arreglo de código en una solicitud de análisis.

Punto de reanudación: último alivio auténtico, antes de apertura. Estado físico
actual, contexto y continuación específica PENDIENTES; no reiniciar recogida,
repetir alivio ni enviar HOME desde esta lectura.

Evidencia/backup documental fuera de Git:
`../Humanoide-vla-evidence/20261022_OPEN_STALE_DIAGNOSTIC_163801Z/`:
`diagnostic.json`, hashes y `before/`. Fuentes originales de la toma intactas.
Cambios de esta intervención: sólo este incidente y referencias documentales.
Reversión: retirar únicamente estas entradas, preservando otros trabajos en curso.
