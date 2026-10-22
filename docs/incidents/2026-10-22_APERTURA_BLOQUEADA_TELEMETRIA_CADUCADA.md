# Apertura bloqueada al adquirir telemetría — 22-10-2026

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
