# Escenario 1 con supervisión continua

**28-09-2026, Europe/Madrid — BOX-01-EXEC-OPTIMISTIC. Implementado en el PC;
VERIFICADO offline y en lectura. Ensayo físico PENDIENTE.**
Entrada: [`optimistic_scenario1.sh`](../../scripts/optimistic_scenario1.sh).
Usa `policy=assume` y `execution_profile=optimistic_v1`, conserva la geometría
y las tareas de [improved](FORCE_IMPROVED_SCENARIO1.md). No mide si la caja quedó
sujeta o liberada: registra esa condición como **asumida** tras éxito técnico.
Un resultado terminal sin error no demuestra presencia, apoyo ni liberación.

## Qué cambia

El lector nativo mantiene muestras en `live-health.json`; cada transición valida
esos datos sin iniciar otra adquisición completa de todas las señales. No guarda
un permiso reutilizable de «todo correcto». Un dato inválido, caducado, un fallo
o la desaparición de una fuente impiden continuar; un fallo detectado queda
retenido durante la sesión aunque después llegue una muestra correcta.

| Punto del flujo | Comprobación vigente |
| --- | --- |
| Inicio, entrada de reanudación y HOME final | Adquisición completa, igual que el perfil normal; HOME medido cuando corresponde |
| Entre etapas físicas | Descubrimiento de contenedores y hashes, instantánea continua válida, acción libre y reposo articular |
| Después de una acción | Dos muestras articulares con sellos crecientes, fuente y recepción posteriores a su resultado |
| Durante la acción | Salud continua, heartbeat, lease y supervisión del cliente; el movimiento articular esperado no se confunde con reposo |
| `verify_held` / `verify_released` | Registro de suposición, sin ventanas FT ni confirmación presencial |

Se conservan paros, estado de servo, cargador, carga de ambas baterías ≥20 %,
actuadores habilitados y sin fault, cobertura corporal 20D y estado del
controlador. La recepción de paro/servo puede tener edad ≤5 s, acorde con la
cadencia observada de sus canales; cargador, batería, controlador y actuadores
mantienen ≤2 s. También se comprueba la edad de la fuente articular. El archivo
debe haberse actualizado hace ≤1 s, usando reloj de pared y monotónico.
`receipt_ages` conserva edades reales y límites aplicados; no rejuvenece señales.
El estado de acción conserva su
QoS retenido: no se presenta como un mensaje periódico nuevo cada dos segundos.
Entre etapas debe indicar acción libre. Se exige una fuente por canal de salud
y un servicio de controlador; una fuente duplicada o perdida provoca fallo.

La escritura de la instantánea es atómica, con intervalo objetivo de 0,05 s
(hasta 20 Hz, sujeto a planificación); se consulta
el controlador aproximadamente cada segundo. Los duplicados articulares idénticos
no renuevan su edad; conflictos y regresiones fallan. El watchdog comprueba salud
y renueva el lease; un fallo revoca su renovación y activa el cierre existente.
La cancelación solicita sólo el UUID propio y no demuestra parada física.

La frontera puede esperar **hasta 0,5 s** para reunir las dos muestras posteriores
al resultado y confirmar reposo/consigna. Si no lo consigue, falla sin enviar
la etapa siguiente. Un fault o dato caducado no usa esa espera para quedar
dispensado. El descubrimiento y los hashes siguen ejecutándose; su coste previo
era del orden de 0,2 s, no un tiempo garantizado. No hay ahorro total medido de
este perfil ni un objetivo garantizado de cinco segundos entre etapas.

Navegación, llegada 2 cm/2° en get1 y 5 cm/3° en put1, correcciones supervisadas,
percepción SPS y estabilidad de sus dos capturas no cambian. Tampoco cambian
el [selector y límite XYZ](FRONT_BOX_DEPTH_GATE_20260928.md) del paquete instalado
`bf145fa17e1116fc`: una selección fuera de límites falla sin escoger otra caja.
Los bloqueos, plazos, resultado de aplicación, checkpoints y HOME medido siguen
vigentes. Este perfil reduce esperas de adquisición entre etapas; no elimina
las verificaciones bloqueantes ni convierte FT sin cualificar en evidencia.

## Uso y reanudación

```bash
# Plan local, sin conectar:
./scripts/optimistic_scenario1.sh --plan
# Sin argumentos equivale a --check; consulta, sin movimiento:
./scripts/optimistic_scenario1.sh --check
# Ejecución sin preguntas, tras comprobar las condiciones físicas actuales:
./scripts/optimistic_scenario1.sh --run
# Pausa tras el agarre, con sujeción asumida:
./scripts/optimistic_scenario1.sh --run --stop-after grasp
# Revisar una continuación sin mover ni consumir el origen:
./scripts/optimistic_scenario1.sh --resume /ruta/checkpoint.json --check
# Continuar ese checkpoint con el mismo perfil:
./scripts/optimistic_scenario1.sh --resume /ruta/checkpoint.json
```

`--resume` sin `--check`/`--plan` autoriza ejecución; por sí solo no es diagnóstico.
Tras fallo, interrupción o salto se mantienen `--from-stage`, `--box-state` y
`--recovery-confirmed`, además de las condiciones de entrada documentadas en
[reanudación por etapa](FORCE_IMPROVED_SCENARIO1.md#reanudación-por-etapa--28-09-2026).
Se debe usar siempre esta misma entrada para checkpoints optimistas.

Los checkpoints incluyen `execution_profile=optimistic_v1`; el contexto remoto
lo fija también. Los antiguos sin campo significan `standard_v1`. No se permite
pasar de uno a otro, ni siquiera con `--recovery-confirmed`; el contrato rechaza
el cruce antes de SSH. No editar el campo, el origen ni su marcador de consumo.
`policy=assume` y perfil de ejecución son identidades distintas: compartir una
política no hace intercambiables las reanudaciones. `--verbose` conserva la
consola técnica; `events.jsonl` siempre mantiene el detalle completo.

## Fuentes, verificación y reversión

Fuentes: [CLI](../../scripts/box_handling/scenario1_cli.py),
[supervisor](../../scripts/box_handling/scenario1_runtime.py),
[lector nativo](../../scripts/box_handling/scenario1_health_worker.py),
[validador continuo](../../scripts/box_handling/scenario1_live_health.py),
[contrato](../../scripts/box_handling/scenario1_contract.py) y
[reanudación](../../scripts/box_handling/scenario1_resume.py).
La fuente PC se transmite en memoria al iniciar; sólo crea procesos y evidencia
temporales de sesión. No instala archivos persistentes en el robot, modifica
autoarranque, reinicia servicios ni sustituye el paquete SPS instalado.

Pruebas reproducibles sin robot:

```bash
python3 -B -m unittest scripts.box_handling.test_scenario1_execution_profile \
  scripts.box_handling.test_scenario1_live_health \
  scripts.box_handling.test_scenario1_optimistic
bash -n scripts/optimistic_scenario1.sh
./scripts/optimistic_scenario1.sh --plan
```

Suite final: **583 pruebas correctas**, sin fallos ni errores, en 7,176 s
(`tests.json`), incluidas las regresiones de permisos y caducidad por canal.
El contrato y la reanudación incluyen 14 pruebas nuevas de identidad.

Medición pasiva de **16,09 s**, sin acciones (`cadence-result.json`): paro y servo,
4 mensajes cada uno, intervalos 4,4889–4,4920 s; cargador y batería, 64 mensajes
cada uno, media ≈0,253 s; actuadores, 801 mensajes, media ≈0,020 s; estado de
acción, un mensaje retenido. Justifica el límite de 5 s sólo para paro/servo;
no modifica el paro físico ni ignora una activación/fault cuando se recibe.
Inicio, reanudación y HOME final conservan la adquisición completa de datos nuevos.

Los dos primeros `--check` terminaron con código 78, sin solicitar movimiento:
`robot-check/` y `check-console.log` conservan el fallo de acceso al archivo
creado por root con 0600; se corrigió a 0644 dentro de la sesión privada 0700.
`robot-check-benchmark/` y `check-benchmark-console.log` conservan el rechazo
por edad de paro >2 s, previo a medir y ajustar su cadencia. No se presentan
como comprobaciones satisfactorias.

Tercera comprobación, `--check --benchmark-checks 1`: **código 0, CHECK_OK**,
HOME 20D medido al inicio y en la ronda adicional. No se armó ni ejecutó ninguna
etapa; las consultas de navegación fueron `get_map` / `check_state`, de lectura.
Evidencia: `robot-check-final/events.jsonl`, `check-final-console.log` y
`check-final-result.json`. Tiempos medidos con el robot en reposo:

| Consulta | Tiempo |
| --- | ---: |
| Salud completa inicial | 4,414627 s |
| Salud completa en la ronda adicional | 2,491728 s |
| Validación de salud continua en esa ronda | 0,003216 s |
| Descubrimiento de contenedores, conservado | 0,080831 s |
| Comprobación de hashes, conservada | 0,145992 s |

La comparación mide lecturas en reposo, no una transición posterior a movimiento
ni el ahorro de un ciclo completo. En el cierre, después de `ready`, la revocación
deliberada de leases produjo mensajes de lease vencido/stop y salidas 2/78 de los
trabajadores; el supervisor terminó con 0. Queda pendiente mejorar esos mensajes
de cierre: no se describe la ejecución como libre de diagnósticos de error.

Evidencia, pruebas y backup:
`../Humanoide-vla-evidence/20260928T155443Z_OPTIMISTIC_SCENARIO1/`.
Para revertir, retirar la entrada nueva y restaurar selectivamente CLI, runtime,
lector de salud, contrato y reanudación desde `before/`; retirar después el
validador nuevo y sus pruebas si ya no tienen referencias. Preservar cambios
posteriores, evidencia y checkpoints; no restaurar estados de control ni deshacer
SPS `bf145fa17e1116fc`. Actualizar esta ficha y el índice global al revertir.
