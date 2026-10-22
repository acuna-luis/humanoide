# Corrección visual del chasis antes de recoger

## Referencia de retoma held después de alinear — 22-10-2026

**BOX-ALIGNED-PICKUP-RESUME-20261022 — corrección en PC y check real de lectura
VERIFICADOS, sin movimiento; retoma física PENDIENTE.** La alineación cambia la
ubicación real de recogida respecto a get1 nominal. El origen limpio 807763
guarda como referencia mapa x=−0,7090384790175741m,
y=0,24621047424731896m, yaw=3,0940205263894724rad. La retoma 832193 midió
x=−0,7111343965902477m, y=0,24439768099719342m,
yaw=3,089475988660553rad: ≈2,77 mm de la referencia, pero 50,824 mm del nominal.
El rechazo anterior no demuestra que la caja se desplazase esa distancia.

`resume_pickup_reference.py` deriva una referencia histórica sólo de un
segmento limpio held inmediatamente después del agarre y verify_held:
alineación completa con presupuestos/llegadas y asociación de caja válidos,
parejas visual/mapa coherentes, terminales nativos correctos e identidades
de goal/request, contexto/perfil iguales y sin navegación posterior al referencia.
La prueba compacta conserva hashes y se deriva otra vez en el runtime; si
falta o contradice evidencia, se aborta. No convierte la sujeción asumida en
medida ni la pose antigua en muestra fresca.

Se cambia únicamente la comparación de entrada `held → retreat` frente a esa
referencia verificada; siguen 20 mm / 2°, dos poses nuevas, odometría en reposo,
mapa listo, salud y contexto actuales. No cambia get1, no hay nuevo objetivo
de navegación al referencia y no se repite ningún agarre. Para orígenes sin
alineación se conserva el comportamiento nominal. `resume_arrival` registra
la procedencia y el valor usado. El origen es 807763, no el checkpoint fallido
832193. Con `--stop-after put1` sólo se prevé retirada y llegada con caja
sujeta: depósito de 74 cm / HOME siguen fuera del segmento.

Validación: 98 pruebas focales PASS. El `--check` real final acepta entrada
a 2,2 mm / 0,26°, mapa listo y reposo, termina `RESUME_CHECK_OK` sin enviar
órdenes de movimiento ni consumir/modificar el origen. Evidencia en `live-check-final/`;
la ejecución de retirada y navegación queda para el operador.

Receta condicional y precauciones de estado:
[Optimistic](OPTIMISTIC_SCENARIO1.md#referencia-de-retoma-tras-la-alineación-visual--22-10-2026).
Fuentes CLI/runtime/helper y pruebas; backups, hashes y evidencia en
`../Humanoide-vla-evidence/20261022T104831Z_ALIGNED_PICKUP_RESUME_FIX/`.
No se han tocado límites, SPS, XML/YAML, fuerzas, trayectorias de brazos,
servicios o configuración del robot para esta corrección.

## 22-10-2026: inestabilidad de pose después del segundo ajuste

**BOX-ALIGN-BASE-UNSTABLE-20261022 — 22-10-2026, Europe/Madrid.
VERIFICADO en el diario; causa y estado físico actual PENDIENTES.**
El ensayo `20261022T101928Z_OPTIMISTIC_SCENARIO1_772739` llega al segundo
ajuste de chasis. Su acción termina con status4 y el guard registra reposo
(`settled=true`, sin fallo); esto no sustituye la validación posterior de
llegada. La pareja nueva de poses en mapa cambia **5,9303950105 mm en
90,029824 ms** y dispara `pose_references.stable_base` /
`BOX_ALIGNMENT_BASE_UNSTABLE`, cuyo máximo es 5 mm. Los residuales al objetivo
de ambas poses son **10,219183/16,133301 mm**: la segunda excede también la
tolerancia de llegada de 12 mm. El primer rechazo efectivo es estabilidad,
no agotamiento de reintentos ni un error del brazo.

El diario conserva cuatro `base_result` válidos de odometría. Los dos
publicadores de mapa observados corresponden al funcionamiento esperado del
proveedor; su número no demuestra conflicto. `LOCATION_LOST` /
`VSLAM_LOCATION_LOST` aparecen como textos auxiliares junto a un terminal
`navigation_start SUCCEEDED`: sin estado fresco adicional no permiten
concluir que la localización se perdió. Los mensajes de lease son posteriores
al rechazo y pertenecen al cierre; no se amplían leases o tolerancias.

No se despachó `grasp` nativo. Antes del rechazo sólo se ejecutaron visión,
cabeza y navegación; no hubo separación de caja, bodyback, retirada, depósito
o HOME. Se conserva el checkpoint fallido con `box_state=unknown`. Este
análisis sólo lee evidencias y no introduce cambios de software, objetivos o
parámetros. No se vuelve a lanzar el ciclo desde ese estado.

La consulta posterior por SSH devolvió código255 / `Connection refused`.
El operador confirma «Sí, está reiniciándose»; no se ha comprobado el final
del arranque, HOME, paros ni la situación actual de la caja. La reanudación
requiere redescubrir servicios y estados, comprobar las condiciones físicas
actuales y estudiar la estabilidad mapa/odom conservando los límites de
5 mm y 12 mm. No se prescribe HOME ni repetición automática.

Evidencia privada: diario original
`../Humanoide-vla-evidence/20261022T101928Z_OPTIMISTIC_SCENARIO1_772739/`,
`events.jsonl` (terminal/reposo1444–1448, poses1449–1451, rechazo1452–1453,
cierre1454–1461); análisis y backup documental en
`../Humanoide-vla-evidence/20261022T093744Z_EMPTY_ARM_CONTROL_DIAGNOSTIC/alignment-failure-772739-readonly/`.

### Separación completa en vacío: hallazgo estático, sin activar

La revisión local de MetaClamp identifica los campos nativos
`sim_box_position` (3 valores) y `sim_box_orientation` (4, orden w,x,y,z).
Se consumen bajo `CLAMP_SIM`, leído del entorno por el constructor y con
alcance de proceso; no se ha demostrado una activación por goal, y cambiar
el entorno del cliente no cambia el servidor existente. Además, en la rama
inspeccionada cambia la geometría de colisión: nube real con el flag falso,
lectura de `obstacles` YAML con el flag verdadero. No equivale a desactivar
todas las protecciones, pero impide afirmar que sólo sustituye la pose.

**No activado, no instalado ni probado físicamente.** Falta confirmar marcos
Base/Body, routing de `separate_box`, contrato6D y efectos completos. Se
conservan SPS, fuerzas, límites y entorno del servidor. La preparación nativa
por separado completada anteriormente no valida esta separación.
`native-clamp-simulation-contract.json` conserva fuentes, hashes y referencias
de la revisión estática; el ELF inspeccionado tiene SHA256
`d6bc61a493f7d790150fdbd673108121f46589fef56620de4a9023dcc2ba520a`.

## Corrección del retorno de salud tras la primera prueba real

**BOX-01-ALIGN-HEALTH-RETURN-20261022 — 22-10-2026, Europe/Madrid.** El operador
ejecutó el port con cinco ajustes configurados. La llegada a get1 y visión
terminaron; antes de cualquier bajada de cabeza, ajuste visual o agarre se
produjo un `NoneType` en la comprobación de postura. El consumidor nuevo
`pickup_posture(self.health())` esperaba un informe, mientras que el método
de esta rama terminaba tras validar y registrar sin devolver nada. El donante
sí incluía el retorno. No fue un fallo de sensores, distancia o fuerza.

Se añade sólo `return report` al final de `Runtime.health()`, después de todas
sus validaciones. No se devuelve el resumen de consola ni se genera un informe
sustitutivo. La reproducción con el informe real guardado falla antes y pasa
la comprobación inicial después. Las pruebas nuevas ejercitan ese método real;
el mock del ensayo offline anterior ocultaba la omisión.
La regresión carga también el método anterior exacto en memoria: produce un
fallo y tres errores. Tras la corrección pasan las seis pruebas nuevas y las
127 del conjunto focal de salud, ejecutor, alineación e invariantes de brazos.

Ejecución fallida: `../Humanoide-vla-evidence/20261022T083157Z_OPTIMISTIC_SCENARIO1_507743/`.
Corrección y backup: `../Humanoide-vla-evidence/20261022T083405Z_ALIGNMENT_HEALTH_RETURN_FIX/`.
El checkpoint se conserva fallido/`unknown`. Los errores de lease son
posteriores y no se corrigen ampliando plazos. Este arreglo local todavía no
se ha probado físicamente; no se envió otra orden al robot. Antes de otra
ejecución, comprobar de nuevo el estado físico y usar `--check`. La sintaxis
y los límites de intentos no cambian.

## Port acotado a la rama de mesa74 — 22-10-2026

**BOX-01-VISUAL-ALIGN-PORT-20261022. IMPLEMENTADO en PC; pruebas del port
correctas, errores globales previos documentados; carga en el robot y prueba
física PENDIENTES.** Fecha/zona:22-10-2026,
Europe/Madrid. Petición: trasladar sólo la aproximación visual del chasis de
`feriabarcelona`, con contador configurable y sin cambiar el agarre nativo.
No se ha conectado ni movido el robot durante este port. No se infiere su
postura actual del ensayo previo ni de haber cambiado de rama.

### Procedencia y diferencia con el donante

Rama receptora `feat/scenario1-deposit-table-74cm`, base de esta intervención
`8107664669c187ecd31179c086cd29749d2b83b9`; donante
`feriabarcelona@0cbc32095be3e752de91db6a9ed91d165e02186a`.
Se adapta su planificación visual, supervisión de navegación, adquisición
persistente de odometría y conexión al ejecutor actual. No es un merge completo:
no se trae depósito90/69,5cm, cambios de brazos ni recuperación automática
`NO_PROGRESS` del donante. Una cancelación o desenlace incierto aborta; no se
resetean ni recrean workers para intentar de nuevo.

El rechazo previo de esta rama fue X=`0,7908843151889853 m`, exceso0,884315mm
sobre0,79m, después de preparar cabeza/brazos. Esto explica por qué comprobar
la caja antes del goal nativo puede evitar aquella preparación innecesaria;
no demuestra que la siguiente detección vaya a coincidir ni resuelve el
plegado/divergencia izquierda del22Oct. La prueba+2° en vacío sólo validó ese
recorrido pequeño. Véase el [ensayo de recogida](OPTIMISTIC_SCENARIO1.md#22-10-2026-recogida-detenida-en-preparación-destino-de-74-cm-pendiente).

### Contador y límites

`--box-alignment-attempts N` admite enteros **0..7**, por defecto **7 en
Optimistic**. Las otras entradas que comparten el CLI conservan0 por defecto;
pueden seleccionar N explícitamente.
N es el máximo de objetivos del **chasis antes de un único agarre**; no son
reintentos de brazos. Cero omite esta fase y conserva la entrada original del
agarre: esa entrada sí puede preparar cabeza/brazos antes de rechazar SPS.

| Condición | Valor mantenido |
| --- | --- |
| Gate SPS exterior en `base_link` | X[0,41;0,79], Y[−0,39;0,39], Z[0,01;1,49]m; reserva10mm frente al intervalo nativo |
| Margen de aproximación adicional | 20mm hacia dentro: X[0,43;0,77], Y[−0,37;0,37]m; Z no se corrige con elevador |
| Objetivo por corrección | Norma XY≤50mm; yaw final conservado |
| Suma solicitada / plazo de fase | ≤100mm / ≤120s, independientes deN; cada objetivo se reserva antes de despacharlo |
| Llegada antes de volver a observar | Éxito técnico, reposo y dos poses nuevas≤12mm/2° |
| Continuidad de caja | Pareja coherente≤20mm/3°; asociación geométrica entre posturas en odometría local≤20mm/3° |
| Progreso visual | Mejora≥2mm del exceso respecto al margen interior cuando siga fuera |
| Imagen / emparejamiento temporal | Segunda captura≤2s; TF del sello exacto; poses emparejadas≤0,5s y base estable≤5mm/1° |
| Vigilancia por acción | ≤30s, excursión≤80mm, recorrido≤120mm, sin progreso≤4s; mapas/odom, velocidades, salud y lease conservados |

100mm solicitados no acotan la trayectoria real, holgura ni frenado. Subir N
no amplía distancia/plazo ni permite corregir un objetivo mayor de50mm.
Los dos ajustes de llegada a get1 conservan su contrato independiente.

### Secuencia y preparación real de los brazos

1. Antes de mover, exigir abrazaderas declaradas vacías, brazos/torso HOME medidos,
   actuadores sanos/en reposo y condiciones presenciales actuales.
2. Verificar y ejecutar sólo `cruzr/move_head_lower`: cabeza0/−0,43rad,
   brazos/torso siguen en HOME. Su XML existente conserva SHA256
   `f3a73626f97b471d4a0a03c98c24de32243651116c497328e69b5ddc57ea46c1`.
3. Obtener dos detecciones nuevas, TF exacta, odometría anterior/posterior y
   poses de mapa contemporáneas. `enable_vision` es un `MetaLook` de transporte;
   no debe confundirse con esta bajada de cabeza ni con el goal de agarre.
4. Si falta margen interior, calcular objetivoXY de chasis desde la medida
   actual, conservar yaw, navegar con vigilancia y volver a medir tras éxito,
   reposo y llegada. Sólo entonces puede haber otro objetivo dentro deN.
5. Cuando cumple margen, guardar una referencia de comparación y enviar una
   sola vez `local_front_box/separate_right_cruzr`. **Ese goal nativo conserva
   sus3s iniciales de cabeza y ambos brazos**, seguidos por separación y
   `bodyback`. El port no altera esa preparación ni convierte la fase visual
   en una trayectoria exclusivamente de chasis de principio a fin.
6. El adaptador transitorio adquiere dos capturas nuevas en la petición SPS
   nativa, después de preparar brazos. Aplica coherencia, TF, frescura, XYZ
   originales y comparación con la referencia. Nunca entrega esa referencia
   antigua como pose, recorta coordenadas ni elige otra caja para pasar el gate.

Por ello un rechazo posterior todavía puede dejar postura preparatoria.
`--stop-after grasp` se detiene tras `verify_held` asumido sólo si la recogida
termina; confirmar físicamente la sujeción antes de transportar o liberar.
Un fallo no es una pausa exitosa ni autoriza reiniciar el ciclo o enviar HOME.

### Frescura y fuentes preservadas

La lectura de reposo usa el worker de salud persistente, con adquisición nueva
en cada petición. Evita lanzar otro proceso ROSA después de recibir la imagen:
el diagnóstico histórico del donante observó0,903s de coste y una imagen ya
mayor de2s. Se mantiene el límite2s; un procesamiento lento sigue abortando.
No se rejuvenecen sellos ni se reutilizan muestras antiguas como permiso.

Fuentes del port: `scenario1_box_alignment.py`, `scenario1_runtime.py`,
`scenario1_nav_correction.py`, `scenario1_health_worker.py` y
`scenario1_cli.py`, bajo `scripts/box_handling/`, con sus pruebas. Se transmiten
en memoria en la siguiente sesión mediante el lanzador existente; no requieren
instalar SPS ni reiniciar servicios. `TASKS`, `motion_stage`, SDK, fuerza,
XML/YAML y once fuentes protegidas se contrastan por hash con ambas ramas.
El builder conserva paquete **bf145fa17e1116fc** y los mismos XML/YAML generados;
las coincidencias de software no demuestran resuelta la causa física izquierda.

`box-alignment-policy.json` registra N/política de la sesión; el payload lo
transmite y las retomas impresas lo conservan. `events.jsonl` registra medidas,
frescura, asociación, objetivos/contador y motivo de límite. Los archivos de
intención/referencia de Motion son transitorios, no autorizaciones reutilizables.
No editar checkpoint, consumed ni valores de la política para recuperar permiso.
La consola muestra preparación de cabeza, intento/N, XYZ en centímetros,
llegada y margen listo; esas etiquetas no anuncian recogida completada.

La fixture versionada
`scripts/box_handling/fixtures/box_alignment_arm_invariants_20261022.json` y
`test_scenario1_box_alignment_arm_invariants.py` fijan por bytes las once
fuentes protegidas y el paquete generado. No convierten esa identidad de
software en cualificación del movimiento físico.

### Revisión local y uso condicional

```bash
# Plan local, sin conectar; muestra N y pausa tras recogida:
./scripts/optimistic_scenario1.sh --table-height-cm 74 \
  --box-alignment-attempts 3 --plan --stop-after grasp
# Comprobación técnica; no inicia detección, bajada de cabeza ni navegación:
./scripts/optimistic_scenario1.sh --table-height-cm 74 \
  --box-alignment-attempts 3 --check --stop-after grasp
```

Sólo en una sesión nueva, después de resolver la postura preparatoria anterior,
medir HOME y comprobar efector/caja libres, cargador, paros, ruedas en navegación,
recorrido completo, control exclusivo y persona junto al paro:

```bash
./scripts/optimistic_scenario1.sh --table-height-cm 74 \
  --box-alignment-attempts 3 --run --stop-after grasp
```

El comando no es una indicación de ejecutar ahora desde el fallo. La mesa74
sigue con depósito/apertura/HOME no ejecutables; este port no resuelve sus
alturas o desenganche ni habilita el ciclo completo.

### Verificación, evidencia y reversión

**Verificación local completada, sin suite global completamente verde.** La
ejecución de51 módulos realiza921 pruebas:904 pasan y17 producen errores,
todos en `test_scenario1_deposit_install`. Los17 se reproducen con los mismos
nombres en una copia aislada del HEAD previo`8107664`; no son regresiones
nuevas del port. El instalador y su configuración no se modifican en este
alcance. Las pruebas focales del cambio pasan. Después se añaden y ejecutan
correctamente otras2 pruebas de invariantes por bytes; no estaban incluidas
en las921. Las pruebas del donante no se presentan como pruebas de esta revisión.
No ha habido SSH,
captura nueva, navegación, recogida ni cambios del robot en esta intervención;
carga y comportamiento físico del port siguen PENDIENTES.

Recetas exactas y resultados en `scenario1-regression-final-receipt.json`,
`baseline-deposit-installer-complete-receipt.json` y recibos focales del directorio
de evidencia. Revisión focal reproducible, sin robot:

```bash
python3 -B -m unittest \
  scripts.box_handling.test_scenario1_box_alignment \
  scripts.box_handling.test_scenario1_box_alignment_runtime \
  scripts.box_handling.test_scenario1_box_alignment_cli \
  scripts.box_handling.test_scenario1_box_alignment_guard \
  scripts.box_handling.test_scenario1_box_alignment_console \
  scripts.box_handling.test_scenario1_health_base \
  scripts.box_handling.test_scenario1_box_alignment_arm_invariants
git diff --check
```

Evidencia privada:
`../Humanoide-vla-evidence/20261022T080944Z_BOX_ALIGNMENT_ONLY_PORT/`.
`context.json` fija ambos HEAD; `arm-invariants-before.json` conserva once
archivos/SHA y paquete generado; `before/` y `before-sha256.json` guardan el
estado previo. `before-alignment-docs/manifest.json` respalda esta guía como
ausente y la versión anterior de Optimistic. Las verificaciones locales y
fuentes finales se conservan allí antes de cerrar el cambio.

Reversión con todos los ejecutores detenidos: restaurar selectivamente los
archivos modificados del port desde sus backups y retirar sólo módulos/tests
nuevos sin referencias, preservando cambios de mesa74 y trabajo posterior.
Alternativa operativa `--box-alignment-attempts 0`: omite sólo esta fase,
manteniendo los gates y los movimientos originales. No restaura postura física,
checkpoints, sesiones, mapa ni un estado anterior del robot. Sin push.
